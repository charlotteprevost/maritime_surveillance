"""
Harvest SAR cell locations from GFW 4Wings heatmap tiles in MVT format.

When ``POST /v3/4wings/report`` returns SAR presence v4 rows without ``lat``/``lon``,
GFW still exposes the same signal as raster/MVT grid cells. Decoding MVT yields
polygon or point geometries per cell; we use cell centroids as map points.

Docs: Global Fishing Watch — 4Wings tile heatmap (format=MVT) + Interaction API.
"""
from __future__ import annotations

import logging
import time
from typing import Any, Dict, List, Optional, Set, Tuple

try:
    import mercantile
    from mapbox_vector_tile import decode as mvt_decode

    _MVT_DEPS_OK = True
except ImportError:  # pragma: no cover - optional until pip install
    mercantile = None  # type: ignore[assignment]
    mvt_decode = None  # type: ignore[assignment]
    _MVT_DEPS_OK = False

DATASET_SAR_PRESENCE = "public-global-sar-presence:latest"


def _eez_bounds_latlon(entry: Dict[str, Any]) -> Optional[Tuple[float, float, float, float]]:
    bbox = entry.get("bbox")
    if not bbox or len(bbox) != 2:
        return None
    (a0, a1), (b0, b1) = bbox
    south = min(a0, b0)
    north = max(a0, b0)
    west = min(a1, b1)
    east = max(a1, b1)
    return west, south, east, north


def _tile_xy_to_latlon(z: int, x: int, y: int, px: float, py: float, extent: float) -> Tuple[float, float]:
    """MVT coordinates 0..extent with y downward → WGS84."""
    assert mercantile is not None
    bounds = mercantile.bounds(x, y, z)
    lon = bounds.west + (px / extent) * (bounds.east - bounds.west)
    lat = bounds.north - (py / extent) * (bounds.north - bounds.south)
    return lat, lon


def _ring_centroid(ring: List[Any]) -> Tuple[float, float]:
    sx = sy = 0.0
    n = 0
    for pt in ring:
        if not pt or len(pt) < 2:
            continue
        sx += float(pt[0])
        sy += float(pt[1])
        n += 1
    if n == 0:
        return 0.0, 0.0
    return sx / n, sy / n


def _geometry_to_tile_xy(geom: Any) -> Optional[Tuple[float, float]]:
    if not geom or not isinstance(geom, dict):
        return None
    t = geom.get("type")
    coords = geom.get("coordinates")
    if not coords:
        return None
    if t == "Point":
        return float(coords[0]), float(coords[1])
    if t == "Polygon" and coords:
        ring = coords[0]
        if ring:
            return _ring_centroid(ring)
    if t == "MultiPolygon":
        best: Optional[Tuple[float, float]] = None
        best_n = -1
        for poly in coords:
            if not poly:
                continue
            ring = poly[0]
            if not ring:
                continue
            cx, cy = _ring_centroid(ring)
            if len(ring) > best_n:
                best_n = len(ring)
                best = (cx, cy)
        return best
    if t == "LineString" and coords:
        mid = coords[len(coords) // 2]
        return float(mid[0]), float(mid[1])
    return None


def _props_weight(props: Dict[str, Any]) -> int:
    if not props:
        return 1
    for key in ("detections", "value", "Value", "sum", "count", "hours"):
        if key in props:
            try:
                v = int(float(props[key]))
                return max(v, 1)
            except (TypeError, ValueError):
                continue
    return 1


def _first_int(props: Dict[str, Any], keys: List[str]) -> Optional[int]:
    for k in keys:
        if k not in props:
            continue
        try:
            return int(props.get(k))
        except (TypeError, ValueError):
            continue
    return None


def decode_mvt_tile_to_points(
    mvt_bytes: bytes, z: int, x: int, y: int
) -> List[Tuple[float, float, int, str, Optional[int]]]:
    """Return (lat, lon, weight, dedupe_id, interaction_cell) per feature."""
    out: List[Tuple[float, float, int, str, Optional[int]]] = []
    if not _MVT_DEPS_OK or not mvt_decode or not mercantile:
        return out
    if not mvt_bytes or len(mvt_bytes) < 12:
        return out
    try:
        tile = mvt_decode(mvt_bytes)
    except Exception as e:
        logging.debug("MVT decode failed z=%s/%s/%s: %s", z, x, y, e)
        return out

    if not isinstance(tile, dict):
        return out

    for _layer_name, layer in tile.items():
        if not isinstance(layer, dict):
            continue
        extent = float(layer.get("extent") or 4096)
        for feat in layer.get("features") or []:
            if not isinstance(feat, dict):
                continue
            geom = feat.get("geometry")
            xy = _geometry_to_tile_xy(geom)
            if xy is None:
                continue
            px, py = xy
            lat, lon = _tile_xy_to_latlon(z, x, y, px, py, extent)
            props = feat.get("properties") if isinstance(feat.get("properties"), dict) else {}
            w = _props_weight(props)
            raw_id = props.get("id")
            cid = str(raw_id or f"{z}/{x}/{y}/{int(px)}_{int(py)}")
            interaction_cell = _first_int(props, ["cell", "cell_id", "cellIndex", "id"])
            out.append((lat, lon, w, cid, interaction_cell))
    return out


def tiles_covering_bounds(west: float, south: float, east: float, north: float, zoom: int) -> List[Any]:
    assert mercantile is not None
    return list(mercantile.tiles(west, south, east, north, zooms=[zoom]))


def harvest_sar_points_from_mvt(
    client: Any,
    eez_ids: List[str],
    start_date: str,
    end_date: str,
    matched: Optional[bool],
    eez_entries: Dict[str, Any],
    zoom_level: int = 7,
    max_tiles: int = 64,
    tile_delay_s: float = 0.12,
    interval: str = "DAY",
    temporal_aggregation: bool = False,
) -> List[Dict[str, Any]]:
    """
    Fetch MVT heatmap tiles overlapping EEZ bbox(es) and emit centroid points.

    ``matched`` follows SAR filter semantics (False = dark / unmatched AIS).
    """
    if not _MVT_DEPS_OK:
        logging.warning("Install mercantile and mapbox-vector-tile to enable MVT SAR points.")
        return []

    filters: Optional[str] = None
    if matched is True:
        filters = "matched='true'"
    elif matched is False:
        filters = "matched='false'"

    date_range = f"{start_date},{end_date}"
    seen: Set[str] = set()
    points: List[Dict[str, Any]] = []

    tiles_acc: List[Any] = []
    seen_xy: Set[Tuple[int, int, int]] = set()
    for eid in eez_ids:
        key = str(eid)
        entry = eez_entries.get(key) or eez_entries.get(eid)
        if not entry:
            logging.warning("No local EEZ catalog entry for %s; skip MVT coverage", eid)
            continue
        b = _eez_bounds_latlon(entry)
        if not b:
            continue
        west, south, east, north = b
        for t in tiles_covering_bounds(west, south, east, north, zoom_level):
            tid = (t.z, t.x, t.y)
            if tid in seen_xy:
                continue
            seen_xy.add(tid)
            tiles_acc.append(t)

    if len(tiles_acc) > max_tiles:
        logging.info("MVT SAR: limiting tiles %s → %s (max_mvt_tiles)", len(tiles_acc), max_tiles)
        tiles_acc = tiles_acc[:max_tiles]

    for i, t in enumerate(tiles_acc):
        if i > 0 and tile_delay_s > 0:
            time.sleep(tile_delay_s)
        try:
            raw = client.get_heatmap_mvt_tile(
                t.z,
                t.x,
                t.y,
                dataset=DATASET_SAR_PRESENCE,
                date_range=date_range,
                filters=filters,
                interval=interval,
                temporal_aggregation=temporal_aggregation,
            )
        except Exception as e:
            logging.warning("MVT tile fetch failed %s/%s/%s: %s", t.z, t.x, t.y, e)
            continue

        for lat, lon, w, cid, interaction_cell in decode_mvt_tile_to_points(raw, t.z, t.x, t.y):
            if cid in seen:
                continue
            seen.add(cid)
            points.append(
                {
                    "latitude": lat,
                    "longitude": lon,
                    "detections": w,
                    # Tiles are aggregated over the request window; per-cell day is unknown.
                    "date": None,
                    "date_start": start_date,
                    "date_end": end_date,
                    "matched": matched,
                    "vessel_id": None,
                    "source": "gfw_mvt_cell",
                    "location_accuracy": "approx",
                    "tile_z": t.z,
                    "tile_x": t.x,
                    "tile_y": t.y,
                    "interaction_cell": interaction_cell,
                }
            )

    logging.info(
        "MVT SAR points: %s cell centroids from %s tiles (z=%s)",
        len(points),
        len(tiles_acc),
        zoom_level,
    )
    return points

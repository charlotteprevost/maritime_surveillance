"""
Configuration Routes - App config and EEZ data.
"""
import os
import logging
from flask import Blueprint, jsonify, current_app, request
from utils.ttl_cache import cache_enabled, make_cache_key, get_cached_response, set_cached_response

configs_bp = Blueprint("configs", __name__)


@configs_bp.route("/api/health", methods=["GET"])
@configs_bp.route("/healthz", methods=["GET"])
def health_check():
    """Health check endpoint for Render.com monitoring."""
    try:
        # Check if app data is loaded
        EEZ_DATA = current_app.config.get("EEZ_DATA")
        CONFIGS = current_app.config.get("CONFIG")
        
        # Check if GFW client is initialized (optional, don't fail if not set)
        gfw_client = current_app.config.get("GFW_CLIENT")
        
        return jsonify({
            "status": "healthy",
            "config_loaded": EEZ_DATA is not None and CONFIGS is not None,
            "gfw_client_initialized": gfw_client is not None
        }), 200
    except Exception as e:
        logging.error(f"Health check failed: {e}")
        return jsonify({
            "status": "unhealthy",
            "error": str(e)
        }), 503


@configs_bp.route("/api/configs", methods=["GET"])
def get_configs():
    """Get app configuration."""
    try:
        # Cache: configs are stable and fetched often by the frontend.
        if cache_enabled(request.args):
            key = make_cache_key(request.method, request.path, request.args)
            cached = get_cached_response(key)
            if cached:
                payload, status = cached
                return jsonify(payload), status

        EEZ_DATA = current_app.config.get("EEZ_DATA")
        CONFIGS = current_app.config.get("CONFIG")
        
        if not EEZ_DATA or not CONFIGS:
            return jsonify({"error": "Config not loaded"}), 503

        # Get backend URL from environment variable or use default
        backend_url = os.getenv("BACKEND_URL", "http://localhost:5000")
        
        out = {
            "SAR_TILE_STYLE": getattr(CONFIGS, "SAR_TILE_STYLE", {}),
            "ISO3_TO_COUNTRY": getattr(CONFIGS, "ISO3_TO_COUNTRY", {}),
            "DEFAULTS": getattr(CONFIGS, "DEFAULTS", {}),
            "EEZ_DATA": EEZ_DATA.get("eez_entries", {}),
            "backendUrl": backend_url
        }
        if cache_enabled(request.args):
            set_cached_response(key, out, 200, ttl_seconds=3600)
        return jsonify(out)
    except Exception as e:
        logging.error(f"Error loading configs: {e}")
        return jsonify({"error": str(e)}), 500


@configs_bp.route("/api/eez-boundaries", methods=["GET"])
def get_eez_boundaries():
    """Get EEZ boundary GeoJSON for selected EEZ IDs."""
    try:
        from utils.api_helpers import parse_eez_ids

        # Cache: boundaries are stable and expensive to fetch/compute.
        if cache_enabled(request.args):
            key = make_cache_key(request.method, request.path, request.args)
            cached = get_cached_response(key)
            if cached:
                payload, status = cached
                return jsonify(payload), status
        
        eez_ids = parse_eez_ids(request.args, "eez_ids")
        
        if not eez_ids:
            return jsonify({"error": "No EEZ IDs provided"}), 400
        
        client = current_app.config.get("GFW_CLIENT")
        if not client:
            return jsonify({"error": "API client not initialized"}), 500
        
        # Fetch boundaries from GFW API or use bbox fallback
        boundaries = []
        EEZ_DATA = current_app.config.get("EEZ_DATA", {}).get("eez_entries", {})
        
        logging.info(f"Fetching boundaries for {len(eez_ids)} EEZ(s): {eez_ids}")
        
        for eez_id in eez_ids:
            boundary_geometry = None
            
            # Try GFW API first
            try:
                boundary_geometry = client.get_eez_boundary(eez_id)
                if boundary_geometry:
                    logging.info(f"Got boundary from GFW API for EEZ {eez_id}")
                    # Verify it's a valid geometry
                    if isinstance(boundary_geometry, dict) and boundary_geometry.get("type") in ["Polygon", "MultiPolygon"]:
                        # Good, use it
                        pass
                    else:
                        logging.warning(f"GFW API returned invalid geometry type for EEZ {eez_id}: {boundary_geometry.get('type') if isinstance(boundary_geometry, dict) else type(boundary_geometry)}")
                        boundary_geometry = None  # Will fall back to bbox
            except Exception as e:
                logging.warning(f"Failed to fetch boundary from GFW API for EEZ {eez_id}: {e}")
                boundary_geometry = None
            
            # Fallback: use bbox from EEZ data
            if not boundary_geometry:
                eez_info = EEZ_DATA.get(str(eez_id), {})
                if not eez_info:
                    logging.warning(f"EEZ {eez_id} not found in EEZ_DATA")
                elif eez_info.get("bbox"):
                    bbox = eez_info["bbox"]
                    # Bbox format: [[min_lat, min_lon], [max_lat, max_lon]]
                    # GeoJSON coordinates: [lon, lat]
                    if len(bbox) >= 2 and len(bbox[0]) >= 2 and len(bbox[1]) >= 2:
                        min_lat, min_lon = bbox[0]
                        max_lat, max_lon = bbox[1]
                        
                        # Check if this region crosses the International Date Line
                        # (bbox spans from near -180 to near 180)
                        crosses_date_line = (min_lon < -170 and max_lon > 170)
                        
                        if crosses_date_line:
                            # For date-line crossing regions, bbox fallback creates inaccurate boundaries
                            # The bbox is just a rectangular extent, not the actual EEZ shape
                            # For accurate boundaries, we need the GFW API to return the actual geometry
                            # Skip bbox fallback for date-line crossing regions
                            logging.warning(f"EEZ {eez_id} ({eez_info.get('label', 'unknown')}) crosses the International Date Line. Bbox fallback cannot accurately represent the boundary. GFW API boundary is required for proper visualization.")
                            boundary_geometry = None  # Don't create inaccurate bbox boundary
                        else:
                            # Normal case: create a simple rectangle from bbox
                            boundary_geometry = {
                                "type": "Polygon",
                                "coordinates": [[
                                    [min_lon, min_lat],  # [lon, lat] bottom-left
                                    [max_lon, min_lat],  # [lon, lat] bottom-right
                                    [max_lon, max_lat],  # [lon, lat] top-right
                                    [min_lon, max_lat],  # [lon, lat] top-left
                                    [min_lon, min_lat]   # close polygon
                                ]]
                            }
                            logging.info(f"Created bbox boundary for EEZ {eez_id} (label: {eez_info.get('label', 'unknown')})")
                    else:
                        logging.warning(f"Invalid bbox format for EEZ {eez_id}: {bbox}")
                else:
                    logging.warning(f"No bbox data available for EEZ {eez_id}")
            
            if boundary_geometry:
                boundaries.append({
                    "eez_id": eez_id,
                    "geometry": boundary_geometry
                })
                logging.info(f"Added boundary for EEZ {eez_id} to response")
            else:
                logging.warning(f"Could not create boundary for EEZ {eez_id}")
        
        logging.info(f"Returning {len(boundaries)} boundaries")
        out = {"boundaries": boundaries}
        if cache_enabled(request.args):
            set_cached_response(key, out, 200, ttl_seconds=86400)
        return jsonify(out)
    except Exception as e:
        logging.error(f"Error fetching EEZ boundaries: {e}")
        return jsonify({"error": str(e)}), 500

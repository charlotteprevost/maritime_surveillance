import requests
import time
import logging
import os
import requests_cache
import requests
import logging
import hashlib
import json

from functools import lru_cache
from schemas.filters import SarFilterSet


from configs.config import WINGS_API
# Set up request caching (to avoid repeated hits to the same API)
requests_cache.install_cache("gfw_cache", expire_after=86400)  # 1 day cache

# Create a requests Session with retries/backoff
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# module-level session with retry policy
_session = requests.Session()
_retry_strategy = Retry(
    total=4,
    backoff_factor=0.5,
    status_forcelist=(429, 500, 502, 503, 504),
    allowed_methods=("HEAD", "GET", "OPTIONS", "POST", "PUT", "DELETE"),
)
_adapter = HTTPAdapter(max_retries=_retry_strategy)
_session.mount("https://", _adapter)
_session.mount("http://", _adapter)

# Token cache
_GFW_TOKEN = None
_GFW_TOKEN_EXP = None


def get_gfw_token():
    """
    Get GFW API token from environment variable
    """
    # Backwards-compatible simple getter (keeps original behavior)
    return get_gfw_token_cached()


def get_gfw_token_cached():
    """
    Return cached GFW token read from environment. If the token is a JWT
    with an exp claim we'll parse that and avoid reusing an expired token.
    """
    global _GFW_TOKEN, _GFW_TOKEN_EXP
    token = os.getenv("GFW_API_TOKEN")
    if not token:
        raise ValueError("GFW_API_TOKEN environment variable not set")

    # If token unchanged and not expired, return cached
    if _GFW_TOKEN == token:
        if _GFW_TOKEN_EXP:
            try:
                import time as _time
                if _time.time() < _GFW_TOKEN_EXP - 60:
                    return _GFW_TOKEN
                # expired -> fallthrough to reset
            except Exception:
                pass
        else:
            return _GFW_TOKEN

    # New token or expired -> cache and try to parse expiry
    _GFW_TOKEN = token
    _GFW_TOKEN_EXP = None
    try:
        parts = token.split('.')
        if len(parts) == 3:
            import base64 as _base64
            import json as _json
            payload_b64 = parts[1]
            payload_b64 += '=' * (-len(payload_b64) % 4)
            payload_bytes = _base64.urlsafe_b64decode(payload_b64)
            payload = _json.loads(payload_bytes)
            exp = payload.get('exp')
            if exp:
                _GFW_TOKEN_EXP = int(exp)
    except Exception:
        # If parsing fails, we just keep token without expiry
        _GFW_TOKEN_EXP = None

    return _GFW_TOKEN


def gfw_request(method, url, params=None, json=None, headers=None, timeout=30):
    """
    Wrapper for HTTP requests to GFW that injects Authorization header
    and uses retries/backoff. Returns a requests.Response and raises on bad status.
    """
    token = get_gfw_token_cached()
    hdrs = {"Authorization": f"Bearer {token}"}
    # default JSON content type for POST/PUT
    if method.upper() in ("POST", "PUT"):
        hdrs.setdefault("Content-Type", "application/json")
    if headers:
        hdrs.update(headers)

    resp = _session.request(method=method, url=url, params=params, json=json, headers=hdrs, timeout=timeout)
    resp.raise_for_status()
    return resp


def parse_eez_ids(args, key="eez_ids", prioritize_parents=True):
    """
    Parse EEZ IDs from request args supporting multiple formats:
      - repeated params: ?eez_ids=1&eez_ids=2
      - comma-separated string: ?eez_ids=1,2,3
      - JSON array string: ?eez_ids=[1,2,3]

    Handles hierarchical EEZ selection:
      - If a parent EEZ (e.g., "France - All Territories") is selected, include all its child EEZs.
      - If a child EEZ (e.g., "France") is deselected, exclude it even if the parent is selected.

    Returns a list of strings (IDs) or an empty list.
    """
    # Parse EEZ IDs using existing logic
    eez_ids = []
    values = args.getlist(key)
    if values:
        if len(values) == 1:
            single = values[0].strip()
            if single.startswith("[") and single.endswith("]"):
                try:
                    import json as _json
                    arr = _json.loads(single)
                    eez_ids = sorted([str(x) for x in arr])
                except Exception:
                    pass
            elif "," in single:
                eez_ids = sorted([s.strip() for s in single.split(",") if s.strip()])
            else:
                eez_ids = [single]
        else:
            eez_ids = sorted([str(v) for v in values if v])
    else:
        single = args.get(key)
        if single:
            single = single.strip()
            if single.startswith("[") and single.endswith("]"):
                try:
                    import json as _json
                    arr = _json.loads(single)
                    eez_ids = sorted([str(x) for x in arr])
                except Exception:
                    pass
            elif "," in single:
                eez_ids = sorted([s.strip() for s in single.split(",") if s.strip()])
            else:
                eez_ids = [single]

    # Handle hierarchical EEZ selection
    parent_to_children = {
        "France - All Territories": {"France", "French Guiana", "Guadeloupe", "Martinique"},
        "Dominican Republic - All Territories": {"Dominican Republic"},
        # Add other parent-child mappings here
    }

    selected = set(eez_ids)
    final_selection = set()

    for eez_id in selected:
        if eez_id in parent_to_children:  # Parent EEZ selected
            final_selection.update(parent_to_children[eez_id])
        final_selection.add(eez_id)  # Always include explicitly selected EEZs

    # Exclude explicitly deselected child EEZs
    for parent, children in parent_to_children.items():
        if parent in selected:
            final_selection.update(children)  # Include all children of the parent
            final_selection.difference_update(children - selected)  # Remove deselected children

    # Ensure parent EEZs are excluded if their children are explicitly selected
    for parent, children in parent_to_children.items():
        if children.intersection(selected):
            final_selection.discard(parent)

    return sorted(final_selection)


def parse_filters_from_request(args):
    """
    Parse filters from request.args. for filters[0] param in get-tile-url
    """
    # Extract relevant filter params from request.args
    filter_data = {
        "flag": args.getlist("flag"),
        "geartype": args.getlist("geartype"),
        "shiptype": args.getlist("shiptype"),
        "matched": args.get("matched"),
        "neural_vessel_type": args.get("neural_vessel_type"),
        "vessel_id": args.get("vessel_id"),
    }
    # Remove empty values
    filter_data = {k: v for k, v in filter_data.items() if v}
    # Validate and parse
    return SarFilterSet(**filter_data)


def sar_filterset_to_gfw_string(filters: SarFilterSet) -> str:
    """
    Convert filters to GFW string for filters[0] param in get-tile-url
    """
    parts = []
    if filters.matched is not None:
        parts.append(f"matched={'true' if filters.matched else 'false'}")
    if filters.flag:
        flags = ",".join(f"'{f}'" for f in filters.flag)
        parts.append(f"flag in ({flags})")
    if filters.geartype:
        geartypes = ",".join(f"'{g}'" for g in filters.geartype)
        parts.append(f"geartype in ({geartypes})")
    if filters.shiptype:
        shiptypes = ",".join(f"'{s}'" for s in filters.shiptype)
        parts.append(f"shiptype in ({shiptypes})")
    if filters.neural_vessel_type:
        parts.append(f"neural_vessel_type='{filters.neural_vessel_type}'")
    if filters.vessel_id:
        parts.append(f"vessel_id='{filters.vessel_id}'")
    return "&".join(parts)


def fetch_detections_for_eez(eez_id, start, end, filters):
    """
    Fetch detection data from Global Fishing Watch 4Wings Report API.

    Args:
        eez_id: int
        start: str (YYYY-MM-DD)
        end: str (YYYY-MM-DD)
        filters: list of str

    Returns:
        parsed JSON response (dict)
    """
    url = WINGS_API["report"]
    headers = {
        "Authorization": f"Bearer {get_gfw_token()}",
        "Content-Type": "application/json"
    }
    params = {
        "spatial-resolution": "HIGH",
        "temporal-resolution": "HOURLY",
        "datasets[0]": "public-global-sar-presence:latest",
        "date-range": f"{start},{end}",
        "format": "JSON"
    }
    for i, f in enumerate(filters):
        params[f"filters[{i}]"] = f

    payload = {
        "region": {
            "dataset": "public-eez-areas",
            "id": eez_id
        }
    }

    time.sleep(0.25)  # GFW rate limiting: 1 request every 250ms
    response = gfw_request("POST", url, params=params, json=payload)
    return response.json()


# def fetch_summary_report(eez_id, start, end, group_by="GEARTYPE", filters=None):
#     """
#     Calls /v3/4wings/report to get grouped SAR detections (e.g. by gear type or flag).
#     """
#     url = WINGS_API["report"]
#     headers = {
#         "Authorization": f"Bearer {get_gfw_token()}",
#         "Content-Type": "application/json"
#     }
#     params = {
#         "datasets[0]": "public-global-sar-presence:latest",
#         "format": "JSON",
#         "temporal-resolution": "ENTIRE",  # aggregate over full date range
#         "spatial-resolution": "HIGH",
#         "group-by": group_by,
#         "date-range": f"{start},{end}"
#     }

#     if filters:
#         for i, f in enumerate(filters):
#             params[f"filters[{i}]"] = f

#     payload = {
#         "region": {
#             "dataset": "public-eez-areas",
#             "id": eez_id
#         }
#     }

#     response = requests.post(url, headers=headers, params=params, json=payload)
#     response.raise_for_status()
#     return response.json()


def fetch_bins(z, start, end, filters=None):
    """
    Calls /v3/4wings/bins/{z} to get value breakpoints for the SAR dataset.

    Args:
        z (int): Zoom level
        start, end (str): YYYY-MM-DD
        filters (list): GFW-style filter strings

    Returns:
        dict: Response from GFW API (e.g. { "stepsByZoom": { "z": [...] } })
    """
    url = f"{WINGS_API['bins']}/{z}"
    headers = {
        "Authorization": f"Bearer {get_gfw_token()}"
    }

    params = {
        "datasets[0]": "public-global-sar-presence:latest",
        "interval": "DAY",  # could parameterize later
        "date-range": f"{start},{end}"
    }

    if filters:
        for i, f in enumerate(filters):
            params[f"filters[{i}]"] = f

    response = gfw_request("GET", url, params=params)
    return response.json()


def fetch_all_bins(zoom_levels, start, end, filters=None):
    """
    Fetches bin breakpoints for multiple zoom levels.

    Args:
        zoom_levels (list of int): Zoom levels to query
        start, end (str): YYYY-MM-DD
        filters (list): Optional filters

    Returns:
        dict: { "stepsByZoom": { "1": [...], "2": [...], ... } }
    """
    all_bins = {}

    for z in zoom_levels:
        try:
            response = fetch_bins(z, start, end, filters)
            if "stepsByZoom" in response:
                all_bins[str(z)] = response["stepsByZoom"].get(str(z), [])
        except Exception as e:
            all_bins[str(z)] = {"error": str(e)}

    return { "stepsByZoom": all_bins }


def fetch_events(eez_id, start, end, event_types=None, filters=None):
    """
    Calls /v3/events with region filter to fetch event data.
    """
    url = f"{WINGS_API['events']}"
    headers = {
        "Authorization": f"Bearer {get_gfw_token()}",
        "Content-Type": "application/json"
    }

    payload = {
        "datasets": ["public-global-fishing-events:latest"],
        "startDate": start,
        "endDate": end,
        "region": {
            "dataset": "public-eez-areas",
            "id": eez_id
        }
    }

    if event_types:
        payload["types"] = event_types

    if filters:
        payload.update(filters)

    response = gfw_request("POST", url, json=payload)
    return response.json()

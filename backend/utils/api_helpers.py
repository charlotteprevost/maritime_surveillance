"""
API Helper Functions for Request Parsing and Filter Conversion

This module provides utility functions for parsing request parameters
and converting filter objects to GFW API-compatible strings.

Note: GFW API requests are handled by GFWApiClient in gfw_client.py.
This module focuses on request parsing and data transformation utilities.
"""

from schemas.filters import SarFilterSet


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
    # Normalize common user inputs:
    # - geartype / shiptype are often sent as uppercase (e.g., "TRAWLERS"), but enums are lowercase.
    # - flag values are ISO3 uppercase and should be preserved.
    geartype_raw = args.getlist("geartype")
    shiptype_raw = args.getlist("shiptype")

    filter_data = {
        "flag": args.getlist("flag") or None,
        "geartype": [g.strip().lower() for g in geartype_raw if isinstance(g, str) and g.strip()] or None,
        "shiptype": [s.strip().lower() for s in shiptype_raw if isinstance(s, str) and s.strip()] or None,
        "matched": args.get("matched"),
        "neural_vessel_type": args.get("neural_vessel_type"),
        "vessel_id": args.get("vessel_id"),
    }
    # Convert matched string to boolean if present
    if "matched" in filter_data and filter_data["matched"] is not None:
        filter_data["matched"] = filter_data["matched"].lower() in ("true", "1", "yes")
    
    # Remove empty values and None
    filter_data = {k: v for k, v in filter_data.items() if v is not None and v != ""}
    # Validate and parse
    return SarFilterSet(**filter_data)


def sar_filterset_to_gfw_string(filters: SarFilterSet) -> str:
    """
    Convert filters to GFW string for filters[0] param in get-tile-url
    """
    def _val(x):
        # Enums in this project are `str, Enum` but stringify to "Enum.NAME" by default.
        # We need the underlying value for API filters.
        return getattr(x, "value", x)

    parts = []
    # Per GFW API v3 4Wings filter examples, matched is expressed as a *string*:
    #   matched='false' or matched='true'
    if filters.matched is not None:
        parts.append(f"matched='{'true' if filters.matched else 'false'}'")
    if filters.flag:
        flags = ",".join(f"'{f}'" for f in filters.flag)
        parts.append(f"flag in ({flags})")
    if filters.geartype:
        geartypes = ",".join(f"'{_val(g)}'" for g in filters.geartype)
        parts.append(f"geartype in ({geartypes})")
    if filters.shiptype:
        shiptypes = ",".join(f"'{_val(s)}'" for s in filters.shiptype)
        parts.append(f"shiptype in ({shiptypes})")
    if filters.neural_vessel_type:
        parts.append(f"neural_vessel_type='{_val(filters.neural_vessel_type)}'")
    if filters.vessel_id:
        parts.append(f"vessel_id='{filters.vessel_id}'")
    # Multiple conditions belong in a single filters[0] expression.
    return " AND ".join(parts)



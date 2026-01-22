"""
Bins Routes - wrapper around GFW 4Wings bins endpoint.

Used to fetch value breakpoints for styling/legends when rendering heatmaps.
"""

from flask import Blueprint, request, jsonify, current_app
import logging
import traceback

from configs.config import DATASETS
from utils.api_helpers import parse_filters_from_request, sar_filterset_to_gfw_string
from utils.ttl_cache import cache_enabled, make_cache_key, get_cached_response, set_cached_response, default_ttl_seconds


bins_bp = Blueprint("bins", __name__)


@bins_bp.route("/api/bins/<int:zoom_level>", methods=["GET"])
def get_bins(zoom_level: int):
    """
    Proxy the GFW /4wings/bins/{zoom} endpoint.

    Required query params:
    - start_date (YYYY-MM-DD)
    - end_date (YYYY-MM-DD)

    Optional:
    - interval (default DAY)
    - num_bins (default 9)
    - SAR filters (flag, geartype, shiptype, matched, neural_vessel_type, vessel_id)
    """
    try:
        if cache_enabled(request.args):
            key = make_cache_key(request.method, request.path, request.args)
            cached = get_cached_response(key)
            if cached:
                payload, status = cached
                return jsonify(payload), status

        start_date = request.args.get("start_date")
        end_date = request.args.get("end_date")
        if not start_date or not end_date:
            return jsonify({"error": "Missing required parameters: start_date, end_date"}), 400

        interval = (request.args.get("interval") or "DAY").upper()
        try:
            num_bins = int(request.args.get("num_bins", 9))
        except Exception:
            num_bins = 9

        client = current_app.config.get("GFW_CLIENT")
        if not client:
            return jsonify({"error": "API client not initialized"}), 500

        try:
            filters_obj = parse_filters_from_request(request.args)
            filters_str = sar_filterset_to_gfw_string(filters_obj) if filters_obj else None
        except Exception as e:
            return jsonify({"error": f"Invalid filters: {e}"}), 400

        date_range = f"{start_date},{end_date}"
        bins = client.get_bins(
            zoom_level=zoom_level,
            dataset=DATASETS["sar"],
            interval=interval,
            filters=filters_str,
            date_range=date_range,
            num_bins=num_bins,
        )
        if cache_enabled(request.args):
            set_cached_response(key, bins, 200, ttl_seconds=default_ttl_seconds())
        return jsonify(bins)
    except Exception:
        logging.error(f"Error in get_bins: {traceback.format_exc()}")
        return jsonify({"error": "Failed to fetch bins"}), 500


"""
Insights Routes - Vessel insights and risk indicators.
"""
from flask import Blueprint, request, jsonify, current_app
import logging
import traceback
from schemas.insights import InsightsRequest
from pydantic import ValidationError
from configs.config import DATASETS
from utils.ttl_cache import cache_enabled, default_ttl_seconds, get_cached_response, set_cached_response
import json

insights_bp = Blueprint("insights", __name__)


@insights_bp.route("/api/insights", methods=["POST"])
def get_insights():
    """Get vessel insights (gaps, IUU, coverage)."""
    try:
        data = request.get_json()
        query = InsightsRequest(**data)
    except ValidationError as ve:
        return jsonify({"error": ve.errors()}), 422

    try:
        # Cache: Insights calls are often repeated for the same vessel set + date range.
        # Keyed by request payload (stable JSON).
        cache_key = None
        if cache_enabled(request.args):
            try:
                cache_key = "POST:/api/insights:" + json.dumps(data, sort_keys=True, separators=(",", ":"))
                cached = get_cached_response(cache_key)
                if cached:
                    payload, status = cached
                    return jsonify(payload), status
            except Exception:
                cache_key = None

        client = current_app.config.get("GFW_CLIENT")
        if not client:
            return jsonify({"error": "API client not initialized"}), 500

        includes = [getattr(inc, "value", inc) for inc in (query.includes or [])]
        includes = [
            "VESSEL-IDENTITY-IUU-VESSEL-LIST" if str(inc).upper() == "IUU" else inc
            for inc in includes
        ] or ["FISHING", "VESSEL-IDENTITY-IUU-VESSEL-LIST"]

        vessels_payload = [v.model_dump() for v in query.vessels]
        # Ensure datasetId is present (fallback to identity dataset)
        for v in vessels_payload:
            if "datasetId" not in v:
                v["datasetId"] = DATASETS["identity"]

        insights_data = client.get_vessel_insights(
            vessels=vessels_payload,
            start_date=query.startDate,
            end_date=query.endDate,
            includes=includes
        )

        out = {
            "insights": insights_data,
            "query": query.model_dump()
        }
        if cache_key and cache_enabled(request.args):
            set_cached_response(cache_key, out, 200, ttl_seconds=default_ttl_seconds())
        return jsonify(out)
    except Exception as e:
        logging.error(f"Error in get_insights: {traceback.format_exc()}")
        return jsonify({"error": str(e)}), 400

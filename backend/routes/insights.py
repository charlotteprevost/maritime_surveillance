"""
Insights Routes - Vessel insights and risk indicators.
"""
from flask import Blueprint, request, jsonify, current_app
import logging
import traceback
from schemas.insights import InsightsRequest
from pydantic import ValidationError
from configs.config import DATASETS

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
        client = current_app.config.get("GFW_CLIENT")
        if not client:
            return jsonify({"error": "API client not initialized"}), 500

        includes = query.includes or ["FISHING", "VESSEL-IDENTITY-IUU-VESSEL-LIST"]
        includes = [
            "VESSEL-IDENTITY-IUU-VESSEL-LIST" if inc.upper() == "IUU" else inc
            for inc in includes
        ]

        vessels_payload = [
            {"datasetId": DATASETS["identity"], "vesselId": vid}
            for vid in query.vessel_ids
        ]

        insights_data = client.get_vessel_insights(
            vessels=vessels_payload,
            start_date=query.start_date,
            end_date=query.end_date,
            includes=includes
        )

        return jsonify({
            "insights": insights_data,
            "query": query.dict()
        })
    except Exception as e:
        logging.error(f"Error in get_insights: {traceback.format_exc()}")
        return jsonify({"error": str(e)}), 400

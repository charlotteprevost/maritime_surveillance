"""
Analytics Routes - Dark vessel analytics and risk scoring.
"""
from flask import Blueprint, request, jsonify, current_app
import logging
import traceback
from utils.api_helpers import parse_eez_ids
from services.dark_vessel_service import DarkVesselService

analytics_bp = Blueprint("analytics", __name__)


@analytics_bp.route("/api/analytics/dark-vessels", methods=["GET"])
def get_dark_vessel_analytics():
    """Get analytics dashboard data for dark vessels."""
    try:
        eez_ids = parse_eez_ids(request.args, "eez_ids")
        start_date = request.args.get("start_date")
        end_date = request.args.get("end_date")

        if not eez_ids or not start_date or not end_date:
            return jsonify({"error": "Missing required parameters"}), 400

        client = current_app.config.get("GFW_CLIENT")
        if not client:
            return jsonify({"error": "API client not initialized"}), 500

        service = DarkVesselService(client)
        dark_vessels = service.get_dark_vessels(
            eez_ids=eez_ids,
            start_date=start_date,
            end_date=end_date
        )

        # Calculate statistics
        stats = {
            "total_dark_vessels": dark_vessels["summary"]["unique_vessels"],
            "sar_detections": dark_vessels["summary"]["total_sar_detections"],
            "gap_events": dark_vessels["summary"]["total_gap_events"],
            "eez_count": len(eez_ids),
            "date_range": f"{start_date},{end_date}"
        }

        return jsonify({
            "statistics": stats,
            "vessel_ids": dark_vessels["combined"][:100],  # Limit to 100 for response size
            "summary": dark_vessels["summary"]
        })
    except Exception as e:
        logging.error(f"Error in analytics: {traceback.format_exc()}")
        return jsonify({"error": str(e)}), 500


@analytics_bp.route("/api/analytics/risk-score/<vessel_id>", methods=["GET"])
def get_risk_score(vessel_id):
    """Get risk score for a specific vessel."""
    try:
        start_date = request.args.get("start_date")
        end_date = request.args.get("end_date")

        if not start_date or not end_date:
            return jsonify({"error": "Missing date parameters"}), 400

        client = current_app.config.get("GFW_CLIENT")
        if not client:
            return jsonify({"error": "API client not initialized"}), 500

        service = DarkVesselService(client)
        risk = service.calculate_risk_score(vessel_id, start_date, end_date)

        return jsonify(risk)
    except Exception as e:
        logging.error(f"Error calculating risk: {traceback.format_exc()}")
        return jsonify({"error": str(e)}), 500

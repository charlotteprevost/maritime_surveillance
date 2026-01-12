"""
Vessel Routes - Vessel details and information.
"""
from flask import Blueprint, request, jsonify, current_app
import logging
import traceback
from schemas.vessel_detail import VesselDetailQueryParams
from pydantic import ValidationError

vessels_bp = Blueprint("vessels", __name__)


@vessels_bp.route("/api/vessels/<string:vessel_id>", methods=["GET"])
def get_vessel(vessel_id):
    """Get vessel details."""
    try:
        query = VesselDetailQueryParams(**request.args)
    except ValidationError as ve:
        return jsonify({"error": ve.errors()}), 422

    try:
        client = current_app.config.get("GFW_CLIENT")
        if not client:
            return jsonify({"error": "API client not initialized"}), 500

        vessel_data = client.get_vessel_details(vessel_id)
        return jsonify({
            "vessel_id": vessel_id,
            "data": vessel_data
        })
    except Exception as e:
        logging.error(f"Error in get_vessel: {traceback.format_exc()}")
        return jsonify({"error": str(e)}), 400

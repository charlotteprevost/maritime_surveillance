"""
AIS Gap Events Routes - Vessels that turn off AIS.
"""
from flask import Blueprint, request, jsonify, current_app
import logging
import traceback
from utils.api_helpers import parse_eez_ids

gaps_bp = Blueprint("gaps", __name__)


@gaps_bp.route("/api/gaps", methods=["GET"])
def get_gaps():
    """Get AIS gap events (dark vessel periods)."""
    try:
        eez_ids = parse_eez_ids(request.args, "eez_ids")
        start_date = request.args.get("start_date")
        end_date = request.args.get("end_date")
        intentional_only = request.args.get("intentional_only", "true").lower() == "true"
        limit = int(request.args.get("limit", 1000))

        if not start_date or not end_date:
            return jsonify({"error": "Missing date parameters"}), 400

        client = current_app.config.get("GFW_CLIENT")
        if not client:
            return jsonify({"error": "API client not initialized"}), 500

        all_gaps = []
        for eez_id in eez_ids:
            try:
                # API requires both limit and offset together, or neither
                # If limit is provided, offset must also be provided (default to 0)
                gaps = client.get_gap_events(
                    start_date=start_date,
                    end_date=end_date,
                    eez_id=eez_id,
                    intentional_only=intentional_only,
                    limit=limit if limit and limit > 0 else None,
                    offset=0 if limit and limit > 0 else None
                )
                if "entries" in gaps:
                    all_gaps.extend(gaps["entries"])
            except Exception as e:
                logging.warning(f"Failed gaps for EEZ {eez_id}: {e}")

        return jsonify({
            "gaps": all_gaps,
            "total": len(all_gaps),
            "date_range": f"{start_date},{end_date}",
            "eez_ids": eez_ids
        })
    except Exception as e:
        logging.error(f"Error in get_gaps: {traceback.format_exc()}")
        return jsonify({"error": str(e)}), 500

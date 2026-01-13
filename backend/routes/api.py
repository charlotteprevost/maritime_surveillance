"""
Main API Routes - Registers all route blueprints.
Legacy endpoints removed, using modular structure.
"""
from flask import Blueprint
from routes.detections import detections_bp
from routes.analytics import analytics_bp
from routes.vessels import vessels_bp
from routes.insights import insights_bp
from routes.configs import configs_bp

# Main blueprint that registers all sub-blueprints
api_routes = Blueprint("api_routes", __name__)

# Register all route modules
api_routes.register_blueprint(detections_bp)
api_routes.register_blueprint(analytics_bp)
api_routes.register_blueprint(vessels_bp)
api_routes.register_blueprint(insights_bp)
api_routes.register_blueprint(configs_bp)

# General events endpoint (supports fishing, encounters, port visits, loitering)
from flask import request, jsonify, current_app
import logging
from configs.config import EVENTS_API

@api_routes.route("/api/events", methods=["GET"])
def get_events():
    """Get events - supports fishing, encounters, port visits, loitering with region filtering."""
    try:
        start_date = request.args.get("start_date")
        end_date = request.args.get("end_date")
        event_types = request.args.getlist("event_types") or ["fishing"]  # Default to fishing instead of gaps
        region = request.args.get("region")  # EEZ ID
        flags = request.args.getlist("flags")

        if not start_date or not end_date:
            return jsonify({"error": "Missing date parameters"}), 400

        client = current_app.config.get("GFW_CLIENT")
        if not client:
            return jsonify({"error": "API client not initialized"}), 500

        datasets = [EVENTS_API["datasets"].get(et) for et in event_types if et in EVENTS_API["datasets"]]
        if not datasets:
            # Fallback to fishing events if no valid event types provided
            datasets = [EVENTS_API["datasets"]["fishing"]]

        # Build region filter if provided
        region_filter = None
        if region:
            region_filter = {
                "dataset": "public-eez-areas",
                "id": int(region) if region.isdigit() else region
            }

        events_data = client.get_all_events(
            datasets=datasets,
            start_date=start_date,
            end_date=end_date,
            flags=flags if flags else None,
            region=region_filter
        )

        return jsonify(events_data.get("entries", []))
    except Exception as e:
        logging.error(f"Error in get_events: {e}")
        return jsonify({"error": str(e)}), 500
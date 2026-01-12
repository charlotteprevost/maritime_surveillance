"""
Main API Routes - Registers all route blueprints.
Legacy endpoints removed, using modular structure.
"""
from flask import Blueprint
from routes.detections import detections_bp
from routes.gaps import gaps_bp
from routes.analytics import analytics_bp
from routes.vessels import vessels_bp
from routes.insights import insights_bp
from routes.configs import configs_bp

# Main blueprint that registers all sub-blueprints
api_routes = Blueprint("api_routes", __name__)

# Register all route modules
api_routes.register_blueprint(detections_bp)
api_routes.register_blueprint(gaps_bp)
api_routes.register_blueprint(analytics_bp)
api_routes.register_blueprint(vessels_bp)
api_routes.register_blueprint(insights_bp)
api_routes.register_blueprint(configs_bp)

# Keep minimal legacy endpoints for backward compatibility
from flask import request, jsonify, current_app
import logging
from configs.config import WINGS_API, DATASETS, EVENTS_API
from utils.api_helpers import parse_filters_from_request, sar_filterset_to_gfw_string, parse_eez_ids
from schemas.interaction import InteractionRequest

@api_routes.route("/api/summary", methods=["GET"])
def get_summary():
    """Simplified summary - group by flag/EEZ only."""
    try:
        eez_ids = parse_eez_ids(request.args, "eez_ids")
        start_date = request.args.get("start_date")
        end_date = request.args.get("end_date")
        group_by = request.args.get("group_by", "flag")

        if not eez_ids or not start_date or not end_date:
            return jsonify({"error": "Missing required parameters"}), 400

        try:
            filters_obj = parse_filters_from_request(request.args)
        except Exception as e:
            return jsonify({"error": f"Invalid filters: {e}"}), 400

        filters_str = sar_filterset_to_gfw_string(filters_obj)
        client = current_app.config.get("GFW_CLIENT")
        if not client:
            return jsonify({"error": "API client not initialized"}), 500

        summaries = []
        for eez_id in eez_ids:
            try:
                report = client.create_report(
                    dataset=DATASETS["sar"],
                    start_date=start_date,
                    end_date=end_date,
                    filters=filters_str,
                    eez_id=eez_id,
                    temporal_resolution="DAILY"  # Valid: DAILY, MONTHLY, ENTIRE
                )
                summaries.append({"eez_id": eez_id, "data": report.get("data", [])})
            except Exception as e:
                logging.warning(f"Failed summary for EEZ {eez_id}: {e}")
                summaries.append({"eez_id": eez_id, "error": str(e)})

        return jsonify({
            "summaries": summaries,
            "group_by": group_by,
            "date_range": f"{start_date},{end_date}"
        })
    except Exception as e:
        logging.error(f"Error in get_summary: {e}")
        return jsonify({"error": str(e)}), 500

@api_routes.route("/api/bins/<int:z>", methods=["GET"])
def get_bins(z):
    """Get bins for heatmap at zoom level."""
    try:
        start_date = request.args.get("start_date")
        end_date = request.args.get("end_date")
        interval = request.args.get("interval", "DAY")

        if not start_date or not end_date:
            return jsonify({"error": "Missing date parameters"}), 400

        try:
            filters_obj = parse_filters_from_request(request.args)
        except Exception as e:
            return jsonify({"error": f"Invalid filters: {e}"}), 400

        filters_str = sar_filterset_to_gfw_string(filters_obj)
        client = current_app.config.get("GFW_CLIENT")
        if not client:
            return jsonify({"error": "API client not initialized"}), 500

        bins_data = client.get_bins(
            zoom_level=z,
            dataset=DATASETS["sar"],
            interval=interval,
            filters=filters_str,
            date_range=f"{start_date},{end_date}"
        )
        return jsonify(bins_data)
    except Exception as e:
        logging.error(f"Error in get_bins: {e}")
        return jsonify({"error": str(e)}), 500

@api_routes.route("/api/interaction", methods=["POST"])
def interaction():
    """Get interaction data for map clicks."""
    try:
        data = request.get_json()
        query = InteractionRequest(**data)
        
        client = current_app.config.get("GFW_CLIENT")
        if not client:
            return jsonify({"error": "API client not initialized"}), 500

        interaction_data = client.get_interaction_data(
            zoom_level=query.z,
            x=query.x,
            y=query.y,
            cells=",".join(map(str, query.cells)),
            dataset=DATASETS["sar"],
            date_range=f"{query.start_date},{query.end_date}"
        )

        vessel_ids = []
        if isinstance(interaction_data, dict) and "entries" in interaction_data:
            for entry in interaction_data["entries"]:
                if isinstance(entry, list):
                    for item in entry:
                        if "id" in item:
                            vessel_ids.append(item["id"])

        return jsonify({
            "interaction_data": interaction_data,
            "vessel_ids": vessel_ids,
            "coordinates": {"z": query.z, "x": query.x, "y": query.y, "cells": query.cells}
        })
    except Exception as e:
        logging.error(f"Error in interaction: {e}")
        return jsonify({"error": str(e)}), 400

@api_routes.route("/api/events", methods=["GET"])
def get_events():
    """Get events - supports gaps and other event types with region filtering."""
    try:
        start_date = request.args.get("start_date")
        end_date = request.args.get("end_date")
        event_types = request.args.getlist("event_types") or ["gaps"]
        region = request.args.get("region")  # EEZ ID
        flags = request.args.getlist("flags")

        if not start_date or not end_date:
            return jsonify({"error": "Missing date parameters"}), 400

        client = current_app.config.get("GFW_CLIENT")
        if not client:
            return jsonify({"error": "API client not initialized"}), 500

        datasets = [EVENTS_API["datasets"].get(et) for et in event_types if et in EVENTS_API["datasets"]]
        if not datasets:
            datasets = [EVENTS_API["datasets"]["gaps"]]

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
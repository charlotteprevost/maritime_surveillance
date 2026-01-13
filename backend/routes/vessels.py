"""
Vessel Routes - Vessel details and information.
"""
from flask import Blueprint, request, jsonify, current_app
import logging
import traceback
from typing import List, Optional
from schemas.vessel_detail import VesselDetailQueryParams
from pydantic import ValidationError

vessels_bp = Blueprint("vessels", __name__)


@vessels_bp.route("/api/vessels/<string:vessel_id>", methods=["GET"])
def get_vessel(vessel_id):
    """Get vessel details with optional includes (OWNERSHIP, AUTHORIZATIONS, REGISTRIES_INFO)."""
    try:
        query = VesselDetailQueryParams(**request.args)
    except ValidationError as ve:
        return jsonify({"error": ve.errors()}), 422

    try:
        client = current_app.config.get("GFW_CLIENT")
        if not client:
            return jsonify({"error": "API client not initialized"}), 500

        # Get includes parameter (comma-separated list)
        includes_param = request.args.get("includes", "")
        includes = [inc.strip() for inc in includes_param.split(",") if inc.strip()] if includes_param else None
        
        # Get enhanced vessel details with includes
        vessel_data = client.get_vessel_details(
            vessel_id,
            includes=includes if includes else None
        )
        
        return jsonify({
            "vessel_id": vessel_id,
            "data": vessel_data,
            "includes": includes if includes else []
        })
    except Exception as e:
        logging.error(f"Error in get_vessel: {traceback.format_exc()}")
        return jsonify({"error": str(e)}), 400


@vessels_bp.route("/api/vessels/<string:vessel_id>/timeline", methods=["GET"])
def get_vessel_timeline(vessel_id):
    """Get complete vessel activity timeline (fishing, port visits, encounters, loitering, gaps)."""
    try:
        start_date = request.args.get("start_date")
        end_date = request.args.get("end_date")
        
        if not start_date or not end_date:
            return jsonify({"error": "start_date and end_date are required"}), 400

        client = current_app.config.get("GFW_CLIENT")
        if not client:
            return jsonify({"error": "API client not initialized"}), 500

        # Vessel object for filtering
        vessel = {
            "datasetId": "public-global-vessel-identity:latest",
            "vesselId": vessel_id
        }
        
        timeline = {
            "vessel_id": vessel_id,
            "start_date": start_date,
            "end_date": end_date,
            "events": {}
        }
        
        # Get all event types in parallel (or sequentially if needed)
        event_datasets = {
            "fishing": "public-global-fishing-events:latest",
            "port_visits": "public-global-port-visits-events:latest",
            "encounters": "public-global-encounters-events:latest",
            "loitering": "public-global-loitering-events:latest",
            "gaps": "public-global-gaps-events:latest"
        }
        
        for event_type, dataset in event_datasets.items():
            try:
                events = client.get_all_events(
                    datasets=[dataset],
                    vessels=[vessel],
                    start_date=start_date,
                    end_date=end_date
                )
                
                # Extract entries from response
                if isinstance(events, dict):
                    timeline["events"][event_type] = events.get("entries", [])
                elif isinstance(events, list):
                    timeline["events"][event_type] = events
                else:
                    timeline["events"][event_type] = []
                    
                logging.info(f"Found {len(timeline['events'][event_type])} {event_type} events for vessel {vessel_id}")
            except Exception as e:
                logging.warning(f"Failed to fetch {event_type} events for vessel {vessel_id}: {e}")
                timeline["events"][event_type] = []
        
        # Calculate summary statistics
        total_events = sum(len(events) for events in timeline["events"].values())
        timeline["summary"] = {
            "total_events": total_events,
            "fishing_events": len(timeline["events"].get("fishing", [])),
            "port_visits": len(timeline["events"].get("port_visits", [])),
            "encounters": len(timeline["events"].get("encounters", [])),
            "loitering_events": len(timeline["events"].get("loitering", [])),
            "gap_events": len(timeline["events"].get("gaps", []))
        }
        
        return jsonify(timeline)
    except Exception as e:
        logging.error(f"Error in get_vessel_timeline: {traceback.format_exc()}")
        return jsonify({"error": str(e)}), 400

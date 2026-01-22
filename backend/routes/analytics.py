"""
Analytics Routes - Dark vessel analytics and risk scoring.
"""
from flask import Blueprint, request, jsonify, current_app
import logging
import traceback
from utils.api_helpers import parse_eez_ids
from services.dark_vessel_service import DarkVesselService
from utils.ttl_cache import cache_enabled, make_cache_key, get_cached_response, set_cached_response, default_ttl_seconds

analytics_bp = Blueprint("analytics", __name__)


@analytics_bp.route("/api/analytics/dark-vessels", methods=["GET"])
def get_dark_vessel_analytics():
    """Get analytics dashboard data for dark vessels with enhanced statistics."""
    try:
        if cache_enabled(request.args):
            key = make_cache_key(request.method, request.path, request.args)
            cached = get_cached_response(key)
            if cached:
                payload, status = cached
                return jsonify(payload), status

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

        # Calculate basic statistics
        summary = dark_vessels.get("summary", {}) if isinstance(dark_vessels, dict) else {}
        # NOTE: SAR presence data generally does not include vessel identity.
        # We therefore expose "total_dark_vessels" as the number of unique detection points as a proxy.
        unique_points = summary.get("unique_detection_points")
        if unique_points is None:
            unique_points = summary.get("total_sar_detections", 0)
        stats = {
            "total_dark_vessels": unique_points,
            "sar_detections": summary.get("total_sar_detections", 0),
            "eez_count": len(eez_ids),
            "date_range": f"{start_date},{end_date}"
        }
        
        # Get 4Wings Stats API for better aggregated statistics (global stats, not region-specific)
        # Note: 4Wings Stats API provides global statistics, not filtered by region
        # Use this for overall context, but rely on Events Stats for region-specific data
        wings_stats = {}
        try:
            # Get SAR detection statistics from 4Wings Stats API (global aggregated statistics)
            # This provides value ranges and distributions useful for visualization
            sar_stats = client.get_stats(
                dataset="public-global-sar-presence:latest",
                filters="matched=false",  # Dark vessels only
                date_range=f"{start_date},{end_date}"
            )
            if isinstance(sar_stats, dict):
                wings_stats["sar_global"] = {
                    "total": sar_stats.get("total", 0),
                    "value_range": sar_stats.get("valueRange", {}),
                    "average": sar_stats.get("average", 0),
                    "statistics": sar_stats
                }
                logging.info(f"4Wings Stats API returned global SAR stats: total={sar_stats.get('total', 0)}")
        except Exception as e:
            logging.warning(f"Failed to get 4Wings Stats for SAR: {e}")
        
        # Get enhanced statistics from Events Stats API
        enhanced_stats = {}
        try:
            # Build region filter for first EEZ (or combine if multiple)
            region_filter = {
                "dataset": "public-eez-areas",
                "id": int(eez_ids[0]) if eez_ids[0].isdigit() else eez_ids[0]
            }
            
            # Get statistics for different event types
            event_datasets = {
                "fishing": "public-global-fishing-events:latest",
                "port_visits": "public-global-port-visits-events:latest",
                "encounters": "public-global-encounters-events:latest",
                "loitering": "public-global-loitering-events:latest"
            }
            
            for event_type, dataset in event_datasets.items():
                try:
                    # Use get_all_events instead of get_events_stats for date-filtered statistics
                    # The /events/stats endpoint doesn't support date filtering (start-date/end-date)
                    # Use /events endpoint with date filters and count results instead
                    events_data = client.get_all_events(
                        datasets=[dataset],
                        start_date=start_date,
                        end_date=end_date,
                        region=region_filter,
                        limit=1,  # Just need count, so minimal limit
                        offset=0
                    )
                    # Extract count from events response
                    if isinstance(events_data, dict):
                        # Get total count from pagination metadata or count entries
                        entries = events_data.get("entries", [])
                        total = events_data.get("total", len(entries))
                        enhanced_stats[event_type] = {
                            "count": total if isinstance(total, int) else len(entries),
                            "data": {"total": total if isinstance(total, int) else len(entries)}
                        }
                except Exception as e:
                    logging.warning(f"Failed to get {event_type} stats: {e}")
                    enhanced_stats[event_type] = {"count": 0, "error": str(e)}
        except Exception as e:
            logging.warning(f"Failed to get enhanced stats: {e}")
            enhanced_stats = {"error": str(e)}

        out = {
            "statistics": stats,
            "wings_statistics": wings_stats,  # 4Wings Stats API aggregated statistics
            "enhanced_statistics": enhanced_stats,  # Events Stats API
            # SAR-only view: no vessel IDs available.
            "vessel_ids": [],
            "summary": summary
        }
        if cache_enabled(request.args):
            set_cached_response(key, out, 200, ttl_seconds=default_ttl_seconds())
        return jsonify(out)
    except Exception as e:
        logging.error(f"Error in analytics: {traceback.format_exc()}")
        return jsonify({"error": str(e)}), 500


@analytics_bp.route("/api/analytics/risk-score/<vessel_id>", methods=["GET"])
def get_risk_score(vessel_id):
    """Get risk score for a specific vessel."""
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
            return jsonify({"error": "Missing date parameters"}), 400

        client = current_app.config.get("GFW_CLIENT")
        if not client:
            return jsonify({"error": "API client not initialized"}), 500

        service = DarkVesselService(client)
        risk = service.calculate_risk_score(vessel_id, start_date, end_date)
        if cache_enabled(request.args):
            set_cached_response(key, risk, 200, ttl_seconds=default_ttl_seconds())
        return jsonify(risk)
    except Exception as e:
        logging.error(f"Error calculating risk: {traceback.format_exc()}")
        return jsonify({"error": str(e)}), 500

"""
SAR Detections Routes - Dark vessel detection via SAR imagery.
"""
from flask import Blueprint, request, jsonify, current_app
import logging
import traceback
from datetime import datetime, timedelta
from configs.config import WINGS_API, DATASETS
from utils.api_helpers import parse_filters_from_request, sar_filterset_to_gfw_string, parse_eez_ids
from services.dark_vessel_service import DarkVesselService

detections_bp = Blueprint("detections", __name__)



@detections_bp.route("/api/tiles/proxy/<path:tile_path>", methods=["GET"])
def proxy_tile(tile_path):
    """Proxy tile requests to GFW API with authentication."""
    from flask import Response
    import requests
    
    # Transparent 1x1 PNG for error responses
    transparent_png = b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15\xc4\x89\x00\x00\x00\nIDATx\x9cc\x00\x01\x00\x00\x05\x00\x01\r\n-\xdb\x00\x00\x00\x00IEND\xaeB`\x82'
    
    try:
        client = current_app.config.get("GFW_CLIENT")
        if not client:
            logging.error("GFW_CLIENT not initialized in tile proxy")
            return Response(transparent_png, mimetype='image/png', 
                          headers={'Cache-Control': 'public, max-age=300', 
                                  'Access-Control-Allow-Origin': '*'}), 200
        
        # Reconstruct the full GFW tile URL
        # tile_path format: "heatmap/8/128/100" (Leaflet replaces {z}/{x}/{y} with actual values)
        # The path should be: /4wings/tile/heatmap/{z}/{x}/{y}
        # Ensure it starts with /4wings/tile/
        if tile_path.startswith("4wings/tile/"):
            full_path = f"/{tile_path}"
        elif tile_path.startswith("heatmap/"):
            # Path is already "heatmap/{z}/{x}/{y}", just add the prefix
            full_path = f"/4wings/tile/{tile_path}"
        else:
            # Legacy format: "heatmap8/128/100" - need to insert / after heatmap
            # This shouldn't happen with the fixed URL format, but handle it for backwards compatibility
            if tile_path.startswith("heatmap") and not tile_path.startswith("heatmap/"):
                # Insert / after "heatmap" (e.g., "heatmap8" -> "heatmap/8")
                parts = tile_path.split("/", 1)
                if len(parts) == 2:
                    full_path = f"/4wings/tile/heatmap/{parts[1]}"
                else:
                    full_path = f"/4wings/tile/{tile_path}"
            else:
                full_path = f"/4wings/tile/heatmap/{tile_path}"
        
        # Add query parameters from request
        query_string = request.query_string.decode('utf-8')
        if query_string:
            full_path += f"?{query_string}"
        
        logging.debug(f"Proxying tile request: {full_path}")
        
        # Fetch tile from GFW API with authentication
        headers = {
            "Authorization": f"Bearer {client.api_token}",
            "Accept": "image/png,image/*,*/*"
        }
        
        url = f"{client.BASE_URL}{full_path}"
        response = requests.get(url, headers=headers, timeout=30)
        
        # Handle 404 gracefully - tiles may not exist for all zoom levels/coordinates
        if response.status_code == 404:
            logging.debug(f"Tile not found (404): {full_path} - this is normal for some tiles")
            return Response(
                transparent_png,
                mimetype='image/png',
                headers={
                    'Cache-Control': 'public, max-age=300',
                    'Access-Control-Allow-Origin': '*',
                    'Content-Type': 'image/png'
                }
            )
        
        # Handle other HTTP errors
        if response.status_code >= 400:
            logging.warning(f"HTTP {response.status_code} error proxying tile: {full_path}")
            # Return transparent PNG for any HTTP error to prevent map breaking
            return Response(
                transparent_png,
                mimetype='image/png',
                headers={
                    'Cache-Control': 'public, max-age=300',
                    'Access-Control-Allow-Origin': '*',
                    'Content-Type': 'image/png'
                }
            )
        
        # Success - return the image with proper headers
        return Response(
            response.content,
            mimetype='image/png',
            headers={
                'Cache-Control': 'public, max-age=3600',
                'Access-Control-Allow-Origin': '*',
                'Content-Type': 'image/png'
            }
        )
    except requests.exceptions.RequestException as e:
        # Handle network/request errors
        logging.warning(f"Request error proxying tile {tile_path}: {e}")
        return Response(
            transparent_png,
            mimetype='image/png',
            headers={
                'Cache-Control': 'public, max-age=300',
                'Access-Control-Allow-Origin': '*',
                'Content-Type': 'image/png'
            }
        )
    except Exception as e:
        # Handle any other unexpected errors
        logging.error(f"Unexpected error proxying tile {tile_path}: {e}", exc_info=True)
        return Response(
            transparent_png,
            mimetype='image/png',
            headers={
                'Cache-Control': 'public, max-age=300',
                'Access-Control-Allow-Origin': '*',
                'Content-Type': 'image/png'
            }
        )


@detections_bp.route("/api/detections", methods=["GET"])
def get_detections():
    """Get SAR detections (dark vessels) - combines SAR + gap events."""
    try:
        eez_ids = parse_eez_ids(request.args, "eez_ids")
        start_date = request.args.get("start_date")
        end_date = request.args.get("end_date")
        interval = request.args.get("interval", "DAY")
        temporal_aggregation = request.args.get("temporal_aggregation", "false")

        try:
            filters_obj = parse_filters_from_request(request.args)
        except Exception as e:
            return jsonify({"error": f"Invalid filters: {e}"}), 400

        if not eez_ids or not start_date or not end_date:
            return jsonify({"error": "Missing required parameters"}), 400

        # Build tile URL
        style_id = getattr(current_app.config.get("CONFIG"), "SAR_TILE_STYLE", {}).get("id", "")
        filters_str = sar_filterset_to_gfw_string(filters_obj)
        # WINGS_API['tile'] ends with '/heatmap', so we need to add '/' before {z}
        tile_url = (
            f"{WINGS_API['tile']}"
            f"/{{z}}/{{x}}/{{y}}?format=PNG"
            f"&temporal-aggregation={temporal_aggregation}"
            f"&interval={interval}"
            f"&datasets[0]={DATASETS['sar']}"
            f"&filters[0]={filters_str}"
            f"&date-range={start_date},{end_date}"
            f"&style={style_id}"
        )

        client = current_app.config.get("GFW_CLIENT")
        if not client:
            return jsonify({"error": "API client not initialized"}), 500

        # Use service to get dark vessels (SAR + gaps)
        # Try both intentional and all gaps to get maximum coverage
        logging.info(f"Fetching dark vessels for {len(eez_ids)} EEZ(s): {eez_ids}")
        service = DarkVesselService(client)
        dark_vessels = service.get_dark_vessels(
            eez_ids=eez_ids,
            start_date=start_date,
            end_date=end_date,
            include_sar=True,
            include_gaps=True,
            intentional_gaps_only=False  # Get all gaps, not just intentional ones
        )
        logging.info(f"Dark vessels fetched: {dark_vessels.get('summary', {})}")

        # Get SAR summaries per EEZ (skip if filters_str contains matched filter - API has issues)
        # Note: Summaries are optional and failures won't block the response
        # API has a 366-day limit, so we need to chunk the date range for summaries too
        summaries = []
        start = datetime.strptime(start_date, "%Y-%m-%d")
        end = datetime.strptime(end_date, "%Y-%m-%d")
        days_diff = (end - start).days + 1
        
        if days_diff > 366:
            # Chunk summaries into 365-day chunks (API max is 366)
            from datetime import timedelta
            summary_chunks = []
            current_start = start
            while current_start < end:
                current_end = min(current_start + timedelta(days=365), end)
                summary_chunks.append((
                    current_start.strftime("%Y-%m-%d"),
                    current_end.strftime("%Y-%m-%d")
                ))
                current_start = current_end + timedelta(days=1)
        else:
            summary_chunks = [(start_date, end_date)]
        
        for eez_id in eez_ids:
            eez_summaries = []
            for chunk_start, chunk_end in summary_chunks:
                try:
                    # Don't use matched filter in summary - API has type issues with boolean filters
                    # We'll get all data and filter client-side if needed
                    summary_filters = None if "matched" in filters_str else filters_str
                    logging.info(f"Fetching summary for EEZ {eez_id}, chunk {chunk_start} to {chunk_end}")
                    report = client.create_report(
                        dataset=DATASETS["sar"],
                        start_date=chunk_start,
                        end_date=chunk_end,
                        filters=summary_filters,
                        eez_id=eez_id
                    )
                    eez_summaries.append({"chunk": f"{chunk_start},{chunk_end}", "summary": report})
                    logging.info(f"Summary fetched for EEZ {eez_id}, chunk {chunk_start} to {chunk_end}")
                except Exception as e:
                    logging.warning(f"Failed summary for EEZ {eez_id}, chunk {chunk_start} to {chunk_end}: {e}")
                    eez_summaries.append({"chunk": f"{chunk_start},{chunk_end}", "error": str(e)})
            summaries.append({"eez_id": eez_id, "chunks": eez_summaries})

        # Use proxied tile URL instead of direct GFW URL (requires auth)
        # The frontend will request tiles through our backend proxy
        # tile_url format: "https://gateway.api.globalfishingwatch.org/v3/4wings/tile/heatmap{z}/{x}/{y}?..."
        # We need: "/api/tiles/proxy/heatmap{z}/{x}/{y}?..."
        # Replace the full GFW base URL with our proxy endpoint
        # Note: {z}/{x}/{y} are Leaflet placeholders that will be replaced by the frontend
        gfw_base = "https://gateway.api.globalfishingwatch.org/v3/4wings/tile/"
        proxied_tile_url = tile_url.replace(
            gfw_base,
            '/api/tiles/proxy/'
        )
        
        # Build response with base data
        response_data = {
            "tile_url": proxied_tile_url,  # Use proxied URL
            "summaries": summaries,
            "dark_vessels": dark_vessels,
            "filters": filters_obj.dict(),
            "date_range": f"{start_date},{end_date}"
        }
        
        # Option 3: Batch endpoint with feature flags - extract data once
        include_clusters = request.args.get("include_clusters", "false").lower() == "true"
        include_routes = request.args.get("include_routes", "false").lower() == "true"
        include_stats = request.args.get("include_stats", "false").lower() == "true"
        
        # Extract data once to avoid redundant lookups
        sar_detections = dark_vessels.get("sar_detections", []) if (include_clusters or include_routes) else []
        gap_events = dark_vessels.get("gap_events", []) if include_routes else []
        date_range_str = f"{start_date},{end_date}"
        common_params = {"eez_ids": eez_ids, "date_range": date_range_str}
        
        # Include proximity clusters if requested
        if include_clusters:
            try:
                clusters = service.detect_proximity_clusters(
                    sar_detections=sar_detections,
                    max_distance_km=float(request.args.get("max_distance_km", 5.0)),
                    same_date_only=request.args.get("same_date_only", "true").lower() == "true"
                ) if sar_detections else []
                
                clustered_count = sum(c["detection_count"] for c in clusters)
                response_data["clusters"] = {
                    "clusters": clusters,
                    "total_clusters": len(clusters),
                    "total_vessels_in_clusters": sum(c["vessel_count"] for c in clusters),
                    "high_risk_clusters": sum(1 for c in clusters if c["risk_indicator"] == "high"),
                    "medium_risk_clusters": sum(1 for c in clusters if c["risk_indicator"] == "medium"),
                    "parameters": {**common_params, "max_distance_km": float(request.args.get("max_distance_km", 5.0)), "same_date_only": request.args.get("same_date_only", "true").lower() == "true"},
                    "summary": {
                        "total_sar_detections": len(sar_detections),
                        "clustered_detections": clustered_count,
                        "clustering_rate": f"{(clustered_count / len(sar_detections) * 100):.1f}%" if sar_detections else "0%"
                    }
                } if sar_detections else {"clusters": [], "total_clusters": 0, "total_vessels_in_clusters": 0, "message": "No SAR detections found"}
            except Exception as e:
                logging.warning(f"Failed to compute clusters: {e}")
                response_data["clusters"] = {"error": str(e)}
        
        # Include predicted routes if requested
        if include_routes:
            try:
                routes = service.predict_routes(
                    sar_detections=sar_detections,
                    gap_events=gap_events,
                    max_time_hours=float(request.args.get("max_time_hours", 48.0)),
                    max_distance_km=float(request.args.get("max_distance_km_route", 100.0)),
                    min_route_length=int(request.args.get("min_route_length", 2))
                )
                response_data["routes"] = {
                    "routes": routes,
                    "total_routes": len(routes),
                    "parameters": {**common_params, "max_time_hours": float(request.args.get("max_time_hours", 48.0)), "max_distance_km": float(request.args.get("max_distance_km_route", 100.0)), "min_route_length": int(request.args.get("min_route_length", 2))}
                }
            except Exception as e:
                logging.warning(f"Failed to compute routes: {e}")
                response_data["routes"] = {"error": str(e)}
        
        # Include statistics if requested
        if include_stats:
            try:
                summary = dark_vessels.get("summary", {})
                response_data["statistics"] = {
                    "statistics": {
                        "total_dark_vessels": summary.get("unique_vessels", 0),
                        "sar_detections": summary.get("total_sar_detections", 0),
                        "gap_events": summary.get("total_gap_events", 0),
                        "eez_count": len(eez_ids),
                        "date_range": date_range_str
                    },
                    "enhanced_statistics": {
                        "note": "Enhanced statistics available via /api/analytics/dark-vessels endpoint to avoid timeouts."
                    }
                }
            except Exception as e:
                logging.warning(f"Failed to compute statistics: {e}")
                response_data["statistics"] = {"error": str(e)}
        
        return jsonify(response_data)
    except Exception as e:
        logging.error(f"Error in get_detections: {traceback.format_exc()}")
        return jsonify({"error": str(e)}), 500


@detections_bp.route("/api/detections/proximity-clusters", methods=["GET"])
def get_proximity_clusters():
    """
    Detect clusters of dark vessels close to each other at the same time.
    This can indicate dark trade activity (transshipment, rendezvous, illegal transfers).
    
    Risk Levels (based on maritime security frameworks):
    - High Risk (3+ vessels): Coordinated illicit activities, complex STS transfers
    - Medium Risk (2 vessels): Bilateral STS transfers or rendezvous
    
    See DARK_TRADE_RISK_THRESHOLDS.md for detailed citations and rationale.
    """
    try:
        eez_ids = parse_eez_ids(request.args, "eez_ids")
        start_date = request.args.get("start_date")
        end_date = request.args.get("end_date")
        max_distance_km = float(request.args.get("max_distance_km", 5.0))
        same_date_only = request.args.get("same_date_only", "true").lower() == "true"

        if not eez_ids or not start_date or not end_date:
            return jsonify({"error": "Missing required parameters: eez_ids, start_date, end_date"}), 400

        if max_distance_km <= 0 or max_distance_km > 50:
            return jsonify({"error": "max_distance_km must be between 0 and 50"}), 400

        client = current_app.config.get("GFW_CLIENT")
        if not client:
            return jsonify({"error": "API client not initialized"}), 500

        # Get dark vessels (SAR detections)
        service = DarkVesselService(client)
        dark_vessels = service.get_dark_vessels(
            eez_ids=eez_ids,
            start_date=start_date,
            end_date=end_date,
            include_sar=True,
            include_gaps=False,  # Only need SAR for proximity detection
            intentional_gaps_only=False
        )

        sar_detections = dark_vessels.get("sar_detections", [])
        logging.info(f"Proximity cluster request: {len(sar_detections)} SAR detections, max_distance={max_distance_km}km, same_date_only={same_date_only}")
        
        if not sar_detections:
            return jsonify({
                "clusters": [],
                "total_clusters": 0,
                "total_vessels_in_clusters": 0,
                "message": "No SAR detections found for proximity analysis"
            })

        # Detect proximity clusters
        clusters = service.detect_proximity_clusters(
            sar_detections=sar_detections,
            max_distance_km=max_distance_km,
            same_date_only=same_date_only
        )

        # Calculate summary statistics
        total_vessels_in_clusters = sum(c["vessel_count"] for c in clusters)
        high_risk_clusters = [c for c in clusters if c["risk_indicator"] == "high"]
        medium_risk_clusters = [c for c in clusters if c["risk_indicator"] == "medium"]

        return jsonify({
            "clusters": clusters,
            "total_clusters": len(clusters),
            "total_vessels_in_clusters": total_vessels_in_clusters,
            "high_risk_clusters": len(high_risk_clusters),
            "medium_risk_clusters": len(medium_risk_clusters),
            "parameters": {
                "max_distance_km": max_distance_km,
                "same_date_only": same_date_only,
                "eez_ids": eez_ids,
                "date_range": f"{start_date},{end_date}"
            },
            "summary": {
                "total_sar_detections": len(sar_detections),
                "clustered_detections": sum(c["detection_count"] for c in clusters),
                "clustering_rate": f"{(sum(c['detection_count'] for c in clusters) / len(sar_detections) * 100):.1f}%" if sar_detections else "0%"
            }
        })
    except Exception as e:
        logging.error(f"Error in get_proximity_clusters: {traceback.format_exc()}")
        return jsonify({"error": str(e)}), 500


@detections_bp.route("/api/detections/routes", methods=["GET"])
def get_predicted_routes():
    """
    Predict likely routes dark vessels use by connecting detections temporally and spatially.
    
    This endpoint is maintained for backward compatibility. For better performance,
    use /api/detections with include_routes=true parameter (Option 3: Batch endpoint).
    """
    try:
        eez_ids = parse_eez_ids(request.args, "eez_ids")
        start_date = request.args.get("start_date")
        end_date = request.args.get("end_date")
        max_time_hours = float(request.args.get("max_time_hours", 48.0))
        max_distance_km = float(request.args.get("max_distance_km", 100.0))
        min_route_length = int(request.args.get("min_route_length", 2))

        if not eez_ids or not start_date or not end_date:
            return jsonify({"error": "Missing required parameters: eez_ids, start_date, end_date"}), 400

        if max_time_hours <= 0 or max_time_hours > 168:  # Max 1 week
            return jsonify({"error": "max_time_hours must be between 0 and 168"}), 400

        if max_distance_km <= 0 or max_distance_km > 500:
            return jsonify({"error": "max_distance_km must be between 0 and 500"}), 400

        client = current_app.config.get("GFW_CLIENT")
        if not client:
            return jsonify({"error": "API client not initialized"}), 500

        # Get dark vessels (SAR + gaps)
        service = DarkVesselService(client)
        dark_vessels = service.get_dark_vessels(
            eez_ids=eez_ids,
            start_date=start_date,
            end_date=end_date,
            include_sar=True,
            include_gaps=True,
            intentional_gaps_only=False
        )

        sar_detections = dark_vessels.get("sar_detections", [])
        gap_events = dark_vessels.get("gap_events", [])
        
        logging.info(f"Route prediction request: {len(sar_detections)} SAR detections, {len(gap_events)} gap events")

        # Predict routes
        routes = service.predict_routes(
            sar_detections=sar_detections,
            gap_events=gap_events,
            max_time_hours=max_time_hours,
            max_distance_km=max_distance_km,
            min_route_length=min_route_length
        )

        return jsonify({
            "routes": routes,
            "total_routes": len(routes),
            "parameters": {
                "max_time_hours": max_time_hours,
                "max_distance_km": max_distance_km,
                "min_route_length": min_route_length,
                "eez_ids": eez_ids,
                "date_range": f"{start_date},{end_date}"
            }
        })
    except Exception as e:
        logging.error(f"Error in get_predicted_routes: {traceback.format_exc()}")
        return jsonify({"error": str(e)}), 500

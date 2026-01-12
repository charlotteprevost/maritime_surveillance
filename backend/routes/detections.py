"""
SAR Detections Routes - Dark vessel detection via SAR imagery.
"""
from flask import Blueprint, request, jsonify, current_app
import logging
import traceback
from configs.config import WINGS_API, DATASETS
from utils.api_helpers import parse_filters_from_request, sar_filterset_to_gfw_string, parse_eez_ids
from services.dark_vessel_service import DarkVesselService

detections_bp = Blueprint("detections", __name__)



@detections_bp.route("/api/tiles/proxy/<path:tile_path>", methods=["GET"])
def proxy_tile(tile_path):
    """Proxy tile requests to GFW API with authentication."""
    try:
        client = current_app.config.get("GFW_CLIENT")
        if not client:
            return jsonify({"error": "API client not initialized"}), 500
        
        # Reconstruct the full GFW tile URL
        # tile_path format: "heatmap{z}/{x}/{y}" where {z}, {x}, {y} are Leaflet placeholders
        # The frontend will replace these with actual zoom/x/y values
        # Ensure it starts with /4wings/tile/
        if not tile_path.startswith("4wings/tile/"):
            full_path = f"/4wings/tile/{tile_path}"
        else:
            full_path = f"/{tile_path}"
        
        # Add query parameters from request
        query_string = request.query_string.decode('utf-8')
        if query_string:
            full_path += f"?{query_string}"
        
        logging.info(f"Proxying tile request: {full_path}")
        
        # Fetch tile from GFW API with authentication
        # Use requests directly since we need binary image data
        import requests
        headers = {
            "Authorization": f"Bearer {client.api_token}",
            "Accept": "image/png,image/*,*/*"
        }
        
        url = f"{client.BASE_URL}{full_path}"
        response = requests.get(url, headers=headers, timeout=30)
        
        # Handle 404 gracefully - tiles may not exist for all zoom levels/coordinates
        if response.status_code == 404:
            logging.debug(f"Tile not found (404): {full_path} - this is normal for some tiles")
            # Return a transparent 1x1 PNG instead of error
            from flask import Response
            transparent_png = b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15\xc4\x89\x00\x00\x00\nIDATx\x9cc\x00\x01\x00\x00\x05\x00\x01\r\n-\xdb\x00\x00\x00\x00IEND\xaeB`\x82'
            return Response(
                transparent_png,
                mimetype='image/png',
                headers={
                    'Cache-Control': 'public, max-age=300',  # Cache missing tiles for 5 minutes
                    'Access-Control-Allow-Origin': '*',
                    'Content-Type': 'image/png'
                }
            )
        
        response.raise_for_status()
        
        # Return the image with proper headers
        from flask import Response
        return Response(
            response.content,
            mimetype='image/png',
            headers={
                'Cache-Control': 'public, max-age=3600',
                'Access-Control-Allow-Origin': '*',
                'Content-Type': 'image/png'
            }
        )
    except requests.exceptions.HTTPError as e:
        # Handle other HTTP errors (500, etc.) gracefully
        if e.response.status_code == 404:
            logging.debug(f"Tile not found: {full_path}")
            # Return transparent PNG
            from flask import Response
            transparent_png = b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15\xc4\x89\x00\x00\x00\nIDATx\x9cc\x00\x01\x00\x00\x05\x00\x01\r\n-\xdb\x00\x00\x00\x00IEND\xaeB`\x82'
            return Response(transparent_png, mimetype='image/png', headers={'Cache-Control': 'public, max-age=300', 'Access-Control-Allow-Origin': '*'})
        logging.warning(f"HTTP error proxying tile: {e.response.status_code} - {full_path}")
        # Return transparent PNG for any HTTP error to prevent map breaking
        from flask import Response
        transparent_png = b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15\xc4\x89\x00\x00\x00\nIDATx\x9cc\x00\x01\x00\x00\x05\x00\x01\r\n-\xdb\x00\x00\x00\x00IEND\xaeB`\x82'
        return Response(transparent_png, mimetype='image/png', headers={'Cache-Control': 'public, max-age=300', 'Access-Control-Allow-Origin': '*'})
    except Exception as e:
        logging.warning(f"Error proxying tile: {e} - {full_path}")
        # Return transparent PNG instead of error to prevent map breaking
        from flask import Response
        transparent_png = b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15\xc4\x89\x00\x00\x00\nIDATx\x9cc\x00\x01\x00\x00\x05\x00\x01\r\n-\xdb\x00\x00\x00\x00IEND\xaeB`\x82'
        return Response(transparent_png, mimetype='image/png', headers={'Cache-Control': 'public, max-age=300', 'Access-Control-Allow-Origin': '*'})


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
        tile_url = (
            f"{WINGS_API['tile']}"
            f"{{z}}/{{x}}/{{y}}?format=PNG"
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
        logging.info(f"Fetching dark vessels for {len(eez_ids)} EEZ(s): {eez_ids}")
        service = DarkVesselService(client)
        dark_vessels = service.get_dark_vessels(
            eez_ids=eez_ids,
            start_date=start_date,
            end_date=end_date,
            include_sar=True,
            include_gaps=True
        )
        logging.info(f"Dark vessels fetched: {dark_vessels.get('summary', {})}")

        # Get SAR summaries per EEZ (skip if filters_str contains matched filter - API has issues)
        # Note: Summaries are optional and failures won't block the response
        summaries = []
        for eez_id in eez_ids:
            try:
                # Don't use matched filter in summary - API has type issues with boolean filters
                # We'll get all data and filter client-side if needed
                summary_filters = None if "matched" in filters_str else filters_str
                logging.info(f"Fetching summary for EEZ {eez_id}")
                report = client.create_report(
                    dataset=DATASETS["sar"],
                    start_date=start_date,
                    end_date=end_date,
                    filters=summary_filters,
                    eez_id=eez_id
                )
                summaries.append({"eez_id": eez_id, "summary": report})
                logging.info(f"Summary fetched for EEZ {eez_id}")
            except Exception as e:
                logging.warning(f"Failed summary for EEZ {eez_id}: {e}")
                summaries.append({"eez_id": eez_id, "error": str(e)})

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
        
        return jsonify({
            "tile_url": proxied_tile_url,  # Use proxied URL
            "summaries": summaries,
            "dark_vessels": dark_vessels,
            "filters": filters_obj.dict(),
            "date_range": f"{start_date},{end_date}"
        })
    except Exception as e:
        logging.error(f"Error in get_detections: {traceback.format_exc()}")
        return jsonify({"error": str(e)}), 500

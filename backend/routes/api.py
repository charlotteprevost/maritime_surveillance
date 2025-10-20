# routes/api.py

from flask import Blueprint, request, jsonify, current_app, Response
from datetime import datetime, timezone
import logging
import traceback
import requests
import os
from configs.config import WINGS_API, DATASETS, EVENTS_API, VESSELS_API, INSIGHTS_API
from schemas.interaction import InteractionRequest
from schemas.vessel_detail import VesselDetailQueryParams
from schemas.insights import InsightsRequest
from pydantic import ValidationError
from urllib.parse import quote_plus
from utils.api_helpers import (
    parse_filters_from_request,
    sar_filterset_to_gfw_string,
    get_gfw_token,
    fetch_detections_for_eez,
    parse_eez_ids,
    gfw_request,
)
import json

api_routes = Blueprint("api_routes", __name__)

# --------------------------
# 🔍 Configs
# --------------------------

@api_routes.route("/api/configs", methods=["GET"])
def get_configs():
    print("get_configs()...")
    try: 
        print("Getting EEZ_DATA...")
        EEZ_DATA = current_app.config.get("EEZ_DATA")
        if not EEZ_DATA:
            return jsonify({"error": "EEZ_DATA not loaded"}), 503
    except Exception as e:
        logging.error(f"Error loading EEZ_DATA: {e}")
        return jsonify({"error": f"Failed to load EEZ_DATA: {str(e)}"}), 500
    
    try:
        print("Getting CONFIGS...")
        CONFIGS = current_app.config["CONFIG"]
        if not CONFIGS:
            return jsonify({"error": "CONFIGS not loaded"}), 503
    except Exception as e:
        logging.error(f"Error loading CONFIGS: {e}")
        return jsonify({"error": f"Failed to load CONFIGS: {str(e)}"}), 500

    print("Returning configs...")
    return jsonify({
        "SAR_TILE_STYLE": getattr(CONFIGS, "SAR_TILE_STYLE", {}),
        "ISO3_TO_COUNTRY": getattr(CONFIGS, "ISO3_TO_COUNTRY", {}),
        "DEFAULTS": getattr(CONFIGS, "DEFAULTS", {}),
        "EEZ_DATA": EEZ_DATA.get("eez_entries", {}),
    })

# --------------------------
# 🔍 EEZ Data
# --------------------------

# @api_routes.route("/api/eez-data", methods=["GET"])
# def get_eez_data():
#     """
#     Returns EEZ entries.
#     """
#     try:        
#         EEZ_DATA = current_app.config.get("EEZ_DATA")
#         if not EEZ_DATA:
#             return jsonify({"error": "EEZ data not loaded"}), 503
#     except Exception as e:
#         logging.error(f"Error loading EEZ data: {e}")
#         return jsonify({"error": f"Failed to load EEZ data: {str(e)}"}), 500
#     return jsonify(EEZ_DATA)

# --------------------------
# 🔍 ISO3 to Country
# --------------------------

# @api_routes.route("/api/iso3-to-country", methods=["GET"])

# def get_iso3_to_country():
#     """
#     Returns ISO3 to country mapping.
#     """
#     try:
#         ISO3_TO_COUNTRY = current_app.config.get("ISO3_TO_COUNTRY")
#         if not ISO3_TO_COUNTRY:
#             return jsonify({"error": "ISO3 to country mapping not loaded"}), 503
#     except Exception as e:
#         logging.error(f"Error loading ISO3 to country mapping: {e}")
#         return jsonify({"error": f"Failed to load ISO3 to country mapping: {str(e)}"}), 500
#     return jsonify(ISO3_TO_COUNTRY)


# --------------------------
# 🔍 SAR Detections (Main Endpoint)
# --------------------------

@api_routes.route("/api/detections", methods=["GET"])
def get_detections():
    """
    Main endpoint to fetch SAR detections from GFW 4Wings API
    Returns heatmap tiles and detection data
    """
    print("get_detections()...")
    try:
        # Get parameters (accept repeated params, comma-separated, or JSON array)
        eez_ids = parse_eez_ids(request.args, "eez_ids")
        start_date = request.args.get("start_date")
        end_date = request.args.get("end_date")
        interval = request.args.get("interval", "DAY")
        temporal_aggregation = request.args.get("temporal_aggregation", "false")
        
        # Parse filters
        try:
            filters_obj = parse_filters_from_request(request.args)
        except Exception as e:
            return jsonify({"error": f"Invalid filters: {e}"}), 400

        if not eez_ids or not start_date or not end_date:
            return jsonify({"error": "Missing required parameters: eez_ids, start_date, end_date"}), 400

        # Build tile URL for heatmap
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

        # Get summary data for each EEZ
        summaries = []
        for eez_id in eez_ids:
            try:
                summary = fetch_detections_for_eez(eez_id, start_date, end_date, [filters_str])
                summaries.append({
                    "eez_id": eez_id,
                    "summary": summary
                })
            except Exception as e:
                logging.warning(f"Failed to fetch summary for EEZ {eez_id}: {e}")
                summaries.append({
                    "eez_id": eez_id,
                    "summary": {"error": str(e)}
                })

        return jsonify({
            "tile_url": tile_url,
            "summaries": summaries,
            "filters": filters_obj.dict(),
            "date_range": f"{start_date},{end_date}"
        })

    except Exception as e:
        logging.error(f"Error in get_detections: {e}")
        return jsonify({"error": str(e)}), 500

# --------------------------
# 🔍 Summary Reports
# --------------------------

@api_routes.route("/api/summary", methods=["GET"])
def get_summary():
    """
    Get summary statistics and reports from GFW 4Wings API
    """
    try:
        eez_ids = parse_eez_ids(request.args, "eez_ids")
        start_date = request.args.get("start_date")
        end_date = request.args.get("end_date")
        group_by = request.args.get("group_by", "flag")  # flag, geartype, shiptype, neural_vessel_type
        
        if not eez_ids or not start_date or not end_date:
            return jsonify({"error": "Missing required parameters"}), 400

        # Parse filters
        try:
            filters_obj = parse_filters_from_request(request.args)
        except Exception as e:
            return jsonify({"error": f"Invalid filters: {e}"}), 400

        filters_str = sar_filterset_to_gfw_string(filters_obj)
        
        # Build report request
        url = WINGS_API["report"]
        headers = {
            "Authorization": f"Bearer {get_gfw_token()}",
            "Content-Type": "application/json"
        }
        
        params = {
            "spatial-resolution": "HIGH",
            "temporal-resolution": "DAILY",
            "datasets[0]": DATASETS["sar"],
            "date-range": f"{start_date},{end_date}",
            "format": "JSON",
            "group-by": group_by,
            "filters[0]": filters_str
        }

        summaries = []
        for eez_id in eez_ids:
            payload = {
                "region": {
                    "dataset": "public-eez-areas",
                    "id": eez_id
                }
            }
            try:
                response = gfw_request("POST", url, params=params, json=payload)
                summaries.append({
                    "eez_id": eez_id,
                    "data": response.json()
                })
            except Exception as e:
                logging.warning(f"Failed to fetch summary for EEZ {eez_id}: {e}")
                summaries.append({
                    "eez_id": eez_id,
                    "error": str(e)
                })

        return jsonify({
            "summaries": summaries,
            "group_by": group_by,
            "date_range": f"{start_date},{end_date}"
        })

    except Exception as e:
        logging.error(f"Error in get_summary: {e}")
        return jsonify({"error": str(e)}), 500

# --------------------------
# 🔍 Generate Style
# --------------------------

# generate-style endpoint removed from this file; use routes/generate_style.py

# --------------------------
# 🔍 Bins Data
# --------------------------

@api_routes.route("/api/bins/<int:z>", methods=["GET"])
def get_bins(z):
    """
    Fetch bins data at specific zoom level
    """
    try:
        start_date = request.args.get("start_date")
        end_date = request.args.get("end_date")
        interval = request.args.get("interval", "DAY")
        num_bins = request.args.get("num_bins", "1000")
        
        if not start_date or not end_date:
            return jsonify({"error": "Missing date parameters"}), 400

        # Parse filters
        try:
            filters_obj = parse_filters_from_request(request.args)
        except Exception as e:
            return jsonify({"error": f"Invalid filters: {e}"}), 400

        filters_str = sar_filterset_to_gfw_string(filters_obj)
        
        # Build bins request
        url = f"{WINGS_API['bins']}/{z}"
        headers = {
            "Authorization": f"Bearer {get_gfw_token()}",
            "Content-Type": "application/json"
        }
        
        params = {
            "datasets[0]": DATASETS["sar"],
            "interval": interval,
            "num-bins": num_bins,
            "filters[0]": filters_str,
            "date-range": f"{start_date},{end_date}"
        }
        response = gfw_request("GET", url, params=params)
        return jsonify(response.json())

    except Exception as e:
        logging.error(f"Error in get_bins: {e}")
        return jsonify({"error": str(e)}), 500

@api_routes.route("/api/bins/all", methods=["GET"])
def get_all_bins():
    """
    Fetch bins data across all zoom levels
    """
    try:
        start_date = request.args.get("start_date")
        end_date = request.args.get("end_date")
        interval = request.args.get("interval", "DAY")
        num_bins = request.args.get("num_bins", "1000")
        
        if not start_date or not end_date:
            return jsonify({"error": "Missing date parameters"}), 400

        # Parse filters
        try:
            filters_obj = parse_filters_from_request(request.args)
        except Exception as e:
            return jsonify({"error": f"Invalid filters: {e}"}), 400

        filters_str = sar_filterset_to_gfw_string(filters_obj)
        
        # Build bins request for all zoom levels
        url = f"{WINGS_API['bins']}/*"
        headers = {
            "Authorization": f"Bearer {get_gfw_token()}",
            "Content-Type": "application/json"
        }
        
        params = {
            "datasets[0]": DATASETS["sar"],
            "interval": interval,
            "num-bins": num_bins,
            "filters[0]": filters_str,
            "date-range": f"{start_date},{end_date}"
        }
        response = gfw_request("GET", url, params=params)
        return jsonify(response.json())

    except Exception as e:
        logging.error(f"Error in get_all_bins: {e}")
        return jsonify({"error": str(e)}), 500

# --------------------------
# 🔍 Events
# --------------------------

@api_routes.route("/api/events", methods=["GET"])
def get_events():
    """
    Fetch vessel activity events from GFW Events API
    """
    try:
        start_date = request.args.get("start_date")
        end_date = request.args.get("end_date")
        vessels = request.args.getlist("vessels")
        region = request.args.get("region")  # EEZ ID
        flags = request.args.getlist("flags")
        event_types = request.args.getlist("event_types", ["fishing", "encounters", "loitering", "port_visits"])
        
        if not start_date or not end_date:
            return jsonify({"error": "Missing date parameters"}), 400

        # Build events request
        url = EVENTS_API["base"]
        headers = {
            "Authorization": f"Bearer {get_gfw_token()}",
            "Content-Type": "application/json"
        }
        
        params = {
            "startDate": start_date,
            "endDate": end_date,
            "format": "JSON"
        }
        
        # Add optional parameters
        if vessels:
            for i, vessel in enumerate(vessels):
                params[f"vessels[{i}]"] = vessel
        if region:
            params["region"] = region
        if flags:
            for i, flag in enumerate(flags):
                params[f"flags[{i}]"] = flag

        # Build datasets list
        datasets = []
        for event_type in event_types:
            if event_type in EVENTS_API["datasets"]:
                datasets.append(EVENTS_API["datasets"][event_type])
        
        if datasets:
            for i, dataset in enumerate(datasets):
                params[f"datasets[{i}]"] = dataset

        response = gfw_request("GET", url, params=params)
        return jsonify(response.json())

    except Exception as e:
        logging.error(f"Error in get_events: {e}")
        return jsonify({"error": str(e)}), 500

# --------------------------
# 🔍 SAR Tile Heatmap (Legacy)
# --------------------------

@api_routes.route("/api/get-tile-url", methods=["GET"])
def get_tile_url():
    # Get the style ID from the config
    styleId = getattr(current_app.config.get("CONFIG"), "SAR_TILE_STYLE")["id"]
    # Set these to defaults for now
    interval = request.args.get("interval", "DAY")
    temporal_aggregation = request.args.get("temporal-aggregation", False)
    # Frontend user chooses date range
    date_range = request.args.get("date_range")

    # Parse and validate filters from request
    try:
        filters_obj = parse_filters_from_request(request.args)
    except Exception as e:
        return jsonify({"error": f"Invalid filters: {e}"}), 400

    # HARDCODED FILTERS
    # Always use SAR dataset
    dataset = "public-global-sar-presence:latest"
    # Always require matched=false unless overridden
    if filters_obj.matched is None:
        filters_obj.matched = False

    # Convert filters to GFW string
    filters_str = sar_filterset_to_gfw_string(filters_obj)

    # Build the GFW tile URL (use placeholders {z}/{x}/{y} for tile URL templates)
    urlString = (
        f"{WINGS_API['tile']}"
        + "{z}/{x}/{y}?format=PNG"
        + f"&temporal-aggregation={temporal_aggregation}"
        + f"&interval={interval}"
        + f"&datasets[0]={dataset}"
        + f"&filters[0]={filters_str}"
        + f"&date-range={date_range}"
        + f"&style={styleId}"
    )
    return urlString

# --------------------------
# 🔍 Interaction
# --------------------------

@api_routes.route("/api/interaction", methods=["POST"])
def interaction():
    try:
        data = request.get_json()
        query = InteractionRequest(**data)
        
        # Extract parameters
        z = query.z
        x = query.x
        y = query.y
        cells = query.cells
        start_date = query.start_date
        end_date = query.end_date
        eez_ids = query.eez_ids
        
        # Build interaction request to GFW
        url = f"{WINGS_API['bins']}/{z}/{x}/{y}"
        headers = {
            "Authorization": f"Bearer {get_gfw_token()}",
            "Content-Type": "application/json"
        }
        
        params = {
            "datasets[0]": DATASETS["sar"],
            "interval": "DAY",
            "date-range": f"{start_date},{end_date}",
            "cells": cells
        }
        
        # Add EEZ filters if specified
        if eez_ids:
            params["region"] = ",".join(map(str, eez_ids))

        response = gfw_request("GET", url, params=params)
        interaction_data = response.json()
        
        # Extract vessel IDs from interaction data
        vessel_ids = []
        if "data" in interaction_data:
            for item in interaction_data["data"]:
                if "vessel_id" in item:
                    vessel_ids.append(item["vessel_id"])
        
        return jsonify({
            "interaction_data": interaction_data,
            "vessel_ids": vessel_ids,
            "coordinates": {"z": z, "x": x, "y": y, "cells": cells}
        })
        
    except Exception as e:
        logging.error(f"Error in interaction: {e}")
        return jsonify({"error": str(e)}), 400

# --------------------------
# 🔍 Vessels
# --------------------------

@api_routes.route("/api/vessels/<string:vessel_id>", methods=["GET"])
def get_vessel(vessel_id):
    try:
        query = VesselDetailQueryParams(**request.args)
        
        # Build vessel request to GFW
        url = f"{VESSELS_API['get_by_id']}/{vessel_id}"
        headers = {
            "Authorization": f"Bearer {get_gfw_token()}",
            "Content-Type": "application/json"
        }
        
        params = {
            "datasets": DATASETS["identity"],
            "format": "JSON"
        }
        
        # Add optional parameters
        if query.include_events:
            params["include"] = "events"
        if query.include_tracks:
            params["include"] = "tracks"

        response = gfw_request("GET", url, params=params)
        vessel_data = response.json()
        
        return jsonify({
            "vessel_id": vessel_id,
            "data": vessel_data
        })
        
    except Exception as e:
        logging.error(f"Error in get_vessel: {e}")
        return jsonify({"error": str(e)}), 400

# --------------------------
# 🔍 Insights
# --------------------------

@api_routes.route("/api/insights", methods=["POST"])
def get_insights():
    try:
        data = request.get_json()
        query = InsightsRequest(**data)
        
        # Build insights request to GFW
        url = INSIGHTS_API["base"]
        headers = {
            "Authorization": f"Bearer {get_gfw_token()}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "vessels": query.vessel_ids,
            "startDate": query.start_date,
            "endDate": query.end_date,
            "includes": query.includes or ["FISHING", "GAP", "IUU"]
        }
        
        # Add optional parameters
        if query.region:
            payload["region"] = query.region
        if query.flags:
            payload["flags"] = query.flags

        response = gfw_request("POST", url, json=payload)
        insights_data = response.json()

        return jsonify({
            "insights": insights_data,
            "query": query.dict()
        })
        
    except Exception as e:
        logging.error(f"Error in get_insights: {e}")
        return jsonify({"error": str(e)}), 400

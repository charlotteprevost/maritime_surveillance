"""
GFW API Client for Maritime Surveillance Application

This module provides a wrapper around the Global Fishing Watch API v3,
handling authentication, request formatting, and response parsing.
"""

import requests
import logging
import requests_cache
from typing import Dict, List, Optional, Any, Union
from datetime import datetime, timedelta
import json
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry


class GFWApiClient:
    """
    Client for interacting with the Global Fishing Watch API v3.
    
    Handles authentication, request formatting, and provides
    high-level methods for common API operations used in this maritime
    surveillance application.
    """
    
    BASE_URL = "https://gateway.api.globalfishingwatch.org/v3"
    
    def __init__(self, api_token: str, enable_cache: bool = True):
        """
        Initialize GFW API client with auth, retry logic, and optional caching.
        
        Args:
            api_token: GFW API token
            enable_cache: Enable request caching (default: True, 1 day expiry)
        """
        self.api_token = api_token
        
        # Set up session with retry strategy
        self.session = requests.Session()
        retry_strategy = Retry(
            total=4,
            backoff_factor=0.5,
            status_forcelist=(429, 500, 502, 503, 504),
            allowed_methods=("HEAD", "GET", "OPTIONS", "POST", "PUT", "DELETE"),
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        self.session.mount("https://", adapter)
        self.session.mount("http://", adapter)
        
        # Set default headers
        self.session.headers.update({
            "Authorization": f"Bearer {api_token}",
            "Content-Type": "application/json"
        })
        
        # Enable request caching if requested
        if enable_cache:
            requests_cache.install_cache("gfw_cache", expire_after=86400)  # 1 day cache
        
    def _make_request(self, method: str, endpoint: str, **kwargs) -> requests.Response:
        """
        Make authenticated request to GFW API.
        
        Args:
            method: HTTP method (GET, POST, etc.)
            endpoint: API endpoint (without base URL)
            **kwargs: Additional arguments for requests
            
        Returns:
            Response object
            
        Raises:
            requests.RequestException: If request fails
        """
        url = f"{self.BASE_URL}/{endpoint.lstrip('/')}"
        
        try:
            response = self.session.request(method, url, **kwargs)
            response.raise_for_status()
            return response
        except requests.RequestException as e:
            # Log detailed error information for debugging
            error_msg = f"GFW API request failed: {method} {url} - {e}"
            if hasattr(e.response, 'status_code'):
                error_msg += f" (Status: {e.response.status_code})"
            if hasattr(e.response, 'text') and e.response.text:
                try:
                    error_body = e.response.json()
                    error_msg += f" - Response: {json.dumps(error_body, indent=2)}"
                except:
                    error_msg += f" - Response: {e.response.text[:500]}"
            logging.error(error_msg)
            raise
    
    def get_detection_summary(self, 
                            dataset: str,
                            filters: Optional[str] = None,
                            date_range: Optional[str] = None,
                            interval: str = "HOUR") -> Dict[str, Any]:
        """
        Get detection summary from 4Wings Report API.
        
        Args:
            dataset: Dataset to query (e.g., "public-global-sar-presence:latest")
            filters: Filter string for dataset
            date_range: Date range in format "YYYY-MM-DD,YYYY-MM-DD"
            interval: Time interval (HOUR, DAY, etc.)
            
        Returns:
            Detection summary
        """
        params = {
            "datasets[0]": dataset,
            "format": "JSON",
            "temporal-resolution": "ENTIRE",
            "spatial-resolution": "HIGH"
        }
        
        if filters:
            params["filters[0]"] = filters
        if date_range:
            params["date-range"] = date_range
        if interval:
            params["interval"] = interval
            
        response = self._make_request("POST", "/4wings/report", params=params)
        return response.json()
    
    def get_all_events(self,
                      datasets: List[str],
                      vessels: Optional[List[str]] = None,
                      start_date: Optional[str] = None,
                      end_date: Optional[str] = None,
                      flags: Optional[List[str]] = None,
                      region: Optional[Dict[str, Any]] = None,
                      limit: Optional[int] = 1,
                      offset: Optional[int] = 0,
                      **filters) -> Dict[str, Any]:
        """
        Get events from Events API.
        Uses POST for complex queries (regions, vessel groups, filters per API docs).
        
        Args:
            datasets: List of datasets to query
            vessels: List of vessel IDs to filter by
            start_date: Start date in YYYY-MM-DD format
            end_date: End date in YYYY-MM-DD format
            flags: List of ISO3 country codes
            region: Region dict with dataset and id keys
            limit: Maximum number of results (must be >= 1 if provided)
            offset: Offset for pagination (must be >= 0 if provided)
            **filters: Additional filter parameters (gapIntentionalDisabling, etc.)
            
        Returns:
            Events
        """
        payload = {
            "datasets": datasets
        }
        
        # Only include limit/offset if both are provided and valid
        # API requires both to be present together, and limit >= 1, offset >= 0
        if limit is not None and offset is not None:
            if isinstance(limit, int) and isinstance(offset, int) and limit >= 1 and offset >= 0:
                payload["limit"] = limit
                payload["offset"] = offset
        
        if vessels:
            payload["vessels"] = vessels
        if start_date:
            payload["startDate"] = start_date
        if end_date:
            payload["endDate"] = end_date
        if flags:
            payload["flags"] = flags
        if region:
            payload["region"] = region
            
        # Add any additional filters (convert snake_case to camelCase for API)
        for key, value in filters.items():
            # Convert gap_intentional_disabling to gapIntentionalDisabling
            if key == "gap_intentional_disabling":
                payload["gapIntentionalDisabling"] = value
            else:
                payload[key] = value
        
        response = self._make_request("POST", "/events", json=payload)
        return response.json()
    
    def get_vessel_details(self, 
                          vessel_id: str, 
                          dataset: str = "public-global-vessel-identity:latest",
                          includes: Optional[List[str]] = None,
                          registries_info_data: Optional[str] = None) -> Dict[str, Any]:
        """
        Get detailed vessel information from Vessels API.
        Per API docs: /vessels/{vesselId} with optional includes.
        
        Args:
            vessel_id: GFW vessel ID
            dataset: Dataset to query (per API docs, use datasets[0] query param)
            includes: Optional list of includes (OWNERSHIP, AUTHORIZATIONS, etc.)
            registries_info_data: NONE, DELTA, or ALL
            
        Returns:
            Vessel details data
        """
        params = {"dataset": dataset}  # Per API docs: single vessel uses "dataset" param
        
        if includes:
            for i, inc in enumerate(includes):
                params[f"includes[{i}]"] = inc
        if registries_info_data:
            params["registries-info-data"] = registries_info_data
            
        response = self._make_request("GET", f"/vessels/{vessel_id}", params=params)
        return response.json()
    
    def get_vessel_insights(self,
                           vessels: List[Dict[str, str]],
                           start_date: str,
                           end_date: str,
                           includes: List[str]) -> Dict[str, Any]:
        """
        Get vessel insights from Insights API.
        
        Args:
            vessels: List of vessel objects with datasetId and vesselId
            start_date: Start date in YYYY-MM-DD format
            end_date: End date in YYYY-MM-DD format
            includes: List of insight types to include
            
        Returns:
            Vessel insights
        """
        payload = {
            "vessels": vessels,
            "startDate": start_date,
            "endDate": end_date,
            "includes": includes
        }
        
        response = self._make_request("POST", "/insights/vessels", json=payload)
        return response.json()
    
    def search_vessels(self,
                      query: Optional[str] = None,
                      where: Optional[str] = None,
                      dataset: str = "public-global-vessel-identity:latest",
                      limit: int = 20,
                      includes: Optional[List[str]] = None) -> Dict[str, Any]:
        """
        Search for vessels using Vessels Search API.
        
        Args:
            query: Free-text search query
            where: Structured query string
            dataset: Dataset to search
            limit: Maximum number of results
            includes: Additional information to include
            
        Returns:
            Search results data
        """
        params = {
            "datasets[0]": dataset,
            "limit": limit
        }
        
        if query:
            params["query"] = query
        if where:
            params["where"] = where
        if includes:
            for i, include in enumerate(includes):
                params[f"includes[{i}]"] = include
                
        response = self._make_request("GET", "/vessels/search", params=params)
        return response.json()
    
    def get_bins(self,
                 zoom_level: int,
                 dataset: str,
                 interval: str = "DAY",
                 filters: Optional[str] = None,
                 date_range: Optional[str] = None,
                 num_bins: int = 9) -> Dict[str, Any]:
        """
        Get binned value breakpoints for given zoom level.
        
        Args:
            zoom_level: Zoom level for bins
            dataset: Dataset to query
            interval: Time interval
            filters: Filter string
            date_range: Date range
            num_bins: Number of bins
            
        Returns:
            Bins
        """
        params = {
            "datasets[0]": dataset,
            "interval": interval,
            "num-bins": num_bins
        }
        
        if filters:
            params["filters[0]"] = filters
        if date_range:
            params["date-range"] = date_range
            
        response = self._make_request("GET", f"/4wings/bins/{zoom_level}", params=params)
        return response.json()
    
    def get_interaction_data(self,
                            zoom_level: int,
                            x: int,
                            y: int,
                            cells: str,
                            dataset: str,
                            filters: Optional[str] = None,
                            date_range: Optional[str] = None,
                            limit: Optional[int] = None) -> Dict[str, Any]:
        """
        Get detailed data by tile and cell index
        
        Args:
            zoom_level: Zoom level
            x: X coordinate of the tile
            y: Y coordinate of the tile
            cells: Cell indexes separated by comma
            dataset: Dataset to query
            filters: Filter string
            date_range: Date range
            limit: Maximum number of items
            
        Returns:
            Interaction
        """
        params = {
            "datasets[0]": dataset
        }
        
        if filters:
            params["filters[0]"] = filters
        if date_range:
            params["date-range"] = date_range
        if limit:
            params["limit"] = limit
            
        response = self._make_request("GET", f"/4wings/interaction/{zoom_level}/{x}/{y}/{cells}", params=params)
        return response.json()
    
    def generate_png(self,
                    datasets: List[str],
                    interval: str = "10DAYS",
                    filters: Optional[List[str]] = None,
                    date_range: Optional[str] = None,
                    color: str = "#002457") -> Dict[str, Any]:
        """
        Generate PNG-style heatmap tiles
        
        Args:
            datasets: List of datasets to visualize
            interval: Time resolution
            filters: List of filter strings
            date_range: Date range
            color: Hex color for the ramp
            
        Returns:
            PNG generation response data
        """
        params = {
            "interval": interval,
            "color": color
        }
        
        for i, dataset in enumerate(datasets):
            params[f"datasets[{i}]"] = dataset
            
        if filters:
            for i, filter_str in enumerate(filters):
                params[f"filters[{i}]"] = filter_str
                
        if date_range:
            params["date-range"] = date_range
            
        response = self._make_request("POST", "/4wings/generate-png", params=params)
        return response.json()
    
    def get_stats(self,
                 dataset: str,
                 fields: Optional[List[str]] = None,
                 filters: Optional[str] = None,
                 date_range: Optional[str] = None) -> Dict[str, Any]:
        """
        Get global statistics for dataset
        
        Args:
            dataset: Dataset to query
            fields: Fields to include
            filters: Filter string
            date_range: Date range
            
        Returns:
            Statistics
        """
        params = {
            "datasets[0]": dataset
        }
        
        if fields:
            params["fields"] = ",".join(fields)
        if filters:
            params["filters[0]"] = filters
        if date_range:
            params["date-range"] = date_range
            
        response = self._make_request("GET", "/4wings/stats", params=params)
        return response.json()
    
    def get_gap_events(self,
                      start_date: str,
                      end_date: str,
                      vessels: Optional[List[str]] = None,
                      eez_id: Optional[str] = None,
                      intentional_only: bool = True,
                      limit: Optional[int] = None,
                      offset: Optional[int] = None) -> Dict[str, Any]:
        """
        Get AIS gap events (dark vessel periods)
        Uses POST for region filtering (per API docs).
        
        Args:
            start_date: Start date YYYY-MM-DD
            end_date: End date YYYY-MM-DD
            vessels: Optional vessel IDs
            eez_id: Optional EEZ region ID
            intentional_only: Filter for intentional AIS disabling
            limit: Max results (must be >= 1 if provided)
            offset: Pagination offset (must be >= 0 if provided)
            
        Returns:
            Gap events
        """
        dataset = "public-global-gaps-events:latest"
        
        # Use POST for region filtering (per API docs: POST for complex queries with regions)
        if eez_id:
            payload = {
                "datasets": [dataset],
                "startDate": start_date,
                "endDate": end_date
            }
            
            # Only include limit/offset if both are provided and valid
            # API requires both to be present together, and limit >= 1, offset >= 0
            # IMPORTANT: Do NOT include limit/offset if either is None, 0, or negative
            # The API will return all results if pagination params are omitted
            # Explicitly check and only add if both are valid integers >= 1 and >= 0 respectively
            if (limit is not None and offset is not None and 
                isinstance(limit, int) and isinstance(offset, int) and 
                limit >= 1 and offset >= 0):
                payload["limit"] = limit
                payload["offset"] = offset
            # Otherwise, explicitly do NOT include pagination params (API will return all results)
            # This ensures None values are never serialized to JSON
            
            if intentional_only:
                payload["gapIntentionalDisabling"] = "true"
            if vessels:
                payload["vessels"] = vessels
            
            # Region in POST body (not query params)
            payload["region"] = {
                "dataset": "public-eez-areas",
                "id": int(eez_id) if eez_id.isdigit() else eez_id
            }
            
            # Defensive: Remove any None values from payload before sending
            # This ensures no None values accidentally get serialized to JSON
            # Note: This filters top-level keys only; nested dicts (like region) are preserved
            payload = {k: v for k, v in payload.items() if v is not None}
            
            response = self._make_request("POST", "/events", json=payload)
        else:
            # Use GET for simple queries without regions
            params = {
                "datasets[0]": dataset,
                "start-date": start_date,
                "end-date": end_date
            }
            
            # Only include limit/offset if both are provided and valid
            # IMPORTANT: Do NOT include limit/offset if either is None, 0, or negative
            # The API will return all results if pagination params are omitted
            # Explicitly check and only add if both are valid integers >= 1 and >= 0 respectively
            if (limit is not None and offset is not None and 
                isinstance(limit, int) and isinstance(offset, int) and 
                limit >= 1 and offset >= 0):
                params["limit"] = limit
                params["offset"] = offset
            # Otherwise, explicitly do NOT include pagination params (API will return all results)
            # This ensures None values are never added to query params
            
            if intentional_only:
                params["gap-intentional-disabling"] = "true"
            if vessels:
                for i, v in enumerate(vessels):
                    params[f"vessels[{i}]"] = v
            
            # Defensive: Remove any None values from params before sending
            # This ensures no None values accidentally get added to query string
            params = {k: v for k, v in params.items() if v is not None}
            
            response = self._make_request("GET", "/events", params=params)
        
        return response.json()
    
    def create_report(self,
                     dataset: str,
                     start_date: str,
                     end_date: str,
                     filters: Optional[str] = None,
                     eez_id: Optional[str] = None,
                     spatial_resolution: str = "HIGH",
                     temporal_resolution: str = "DAILY",
                     format: str = "JSON",
                     group_by: Optional[str] = None) -> Dict[str, Any]:
        """
        Create 4Wings report for detections
        Per API docs: temporal-resolution must be DAILY, MONTHLY, or ENTIRE (not HOURLY).
        
        Args:
            dataset: Dataset ID
            start_date: Start date YYYY-MM-DD
            end_date: End date YYYY-MM-DD
            filters: Filter string
            eez_id: Optional EEZ ID
            spatial_resolution: HIGH or LOW
            temporal_resolution: DAILY, MONTHLY, or ENTIRE (per API docs)
            format: JSON, CSV, or TIF
            group_by: Optional grouping (FLAG, GEARTYPE, VESSEL_ID, etc.)
            
        Returns:
            Report
        """
        # Query params (per API docs)
        params = {
            "datasets[0]": dataset,
            "format": format,
            "temporal-resolution": temporal_resolution,
            "spatial-resolution": spatial_resolution,
            "date-range": f"{start_date},{end_date}"
        }
        
        if filters:
            params["filters[0]"] = filters
        if group_by:
            params["group-by"] = group_by
        
        # Body for POST (region goes in body, not params per API docs)
        json_data = None
        if eez_id:
            json_data = {
                "region": {
                    "dataset": "public-eez-areas",
                    "id": int(eez_id) if eez_id.isdigit() else eez_id
                }
            }
            
        response = self._make_request("POST", "/4wings/report", params=params, json=json_data)
        return response.json()
    
    def get_eez_boundary(self, eez_id: str) -> Optional[Dict[str, Any]]:
        """
        Get EEZ boundary GeoJSON from GFW API.
        
        Args:
            eez_id: EEZ ID
            
        Returns:
            GeoJSON geometry or None if not available
        """
        try:
            # Try to fetch from GFW datasets API
            # Endpoint: /v3/datasets/public-eez-areas/{id}
            response = self._make_request("GET", f"/datasets/public-eez-areas/{eez_id}")
            data = response.json()
            
            # Extract geometry from response - handle various response formats
            if "geometry" in data:
                geometry = data["geometry"]
                if geometry and isinstance(geometry, dict):
                    return geometry
            elif "geojson" in data:
                geojson = data["geojson"]
                if geojson and isinstance(geojson, dict):
                    # If it's a full GeoJSON Feature or FeatureCollection, extract geometry
                    if geojson.get("type") == "Feature":
                        return geojson.get("geometry")
                    elif geojson.get("type") == "FeatureCollection":
                        # For FeatureCollection, return the first feature's geometry
                        features = geojson.get("features", [])
                        if features and len(features) > 0:
                            return features[0].get("geometry")
                    else:
                        return geojson
            elif "type" in data and data["type"] in ["Polygon", "MultiPolygon", "Point", "LineString"]:
                # Response is already a geometry
                return data
            elif "features" in data:
                # Response is a FeatureCollection
                features = data.get("features", [])
                if features and len(features) > 0:
                    return features[0].get("geometry")
            
            logging.warning(f"Could not extract geometry from GFW API response for EEZ {eez_id}. Response keys: {list(data.keys()) if isinstance(data, dict) else 'not a dict'}")
            return None
        except Exception as e:
            logging.warning(f"Could not fetch EEZ boundary from GFW API for {eez_id}: {e}")
            return None

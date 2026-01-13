"""
Dark Vessel Service - Core logic for detecting and analyzing dark vessels.
Combines SAR detections with AIS gap events.
"""
import logging
import time
import json
import math
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timedelta


class DarkVesselService:
    """Service for dark vessel detection and analysis."""
    
    def __init__(self, gfw_client):
        """Initialize with GFW API client."""
        self.client = gfw_client
    
    def _split_date_range(self, start_date: str, end_date: str, chunk_days: int = 30) -> List[tuple]:
        """
        Split a date range into chunks of chunk_days (default 30 days).
        Returns list of (start, end) date tuples.
        """
        start = datetime.strptime(start_date, "%Y-%m-%d")
        end = datetime.strptime(end_date, "%Y-%m-%d")
        chunks = []
        
        current_start = start
        while current_start < end:
            current_end = min(current_start + timedelta(days=chunk_days - 1), end)
            chunks.append((
                current_start.strftime("%Y-%m-%d"),
                current_end.strftime("%Y-%m-%d")
            ))
            current_start = current_end + timedelta(days=1)
        
        return chunks
    
    def get_dark_vessels(self,
                        eez_ids: List[str],
                        start_date: str,
                        end_date: str,
                        include_sar: bool = True,
                        include_gaps: bool = True,
                        intentional_gaps_only: bool = True) -> Dict[str, Any]:
        """
        Get dark vessels: SAR detections (matched=false) + AIS gap events.
        
        Automatically chunks date ranges > 30 days into 30-day chunks to avoid API limits.
        
        Returns combined results with vessel IDs cross-referenced.
        """
        results = {
            "sar_detections": [],
            "gap_events": [],
            "combined": [],
            "summary": {}
        }
        
        # Check if date range needs chunking (> 30 days)
        start = datetime.strptime(start_date, "%Y-%m-%d")
        end = datetime.strptime(end_date, "%Y-%m-%d")
        days_diff = (end - start).days + 1
        
        if days_diff > 30:
            logging.info(f"Date range ({days_diff} days) exceeds 30 days, splitting into chunks")
            date_chunks = self._split_date_range(start_date, end_date, chunk_days=30)
            logging.info(f"Split into {len(date_chunks)} chunks: {date_chunks}")
        else:
            date_chunks = [(start_date, end_date)]
        
        # Get SAR detections (unmatched vessels)
        # Serialize requests to avoid 429 errors (API token not enabled for concurrent reports)
        if include_sar:
            for i, eez_id in enumerate(eez_ids):
                for chunk_start, chunk_end in date_chunks:
                    try:
                        # Add delay between requests to avoid concurrent report limit
                        if i > 0 or date_chunks.index((chunk_start, chunk_end)) > 0:
                            time.sleep(1.0)  # 1 second delay between report requests
                        
                        logging.info(f"Fetching SAR detections for EEZ {eez_id}, chunk {chunk_start} to {chunk_end}")
                        
                        # Use matched='false' filter per GFW API docs (quoted string, not boolean)
                        # API format: filters[0]=matched='false'
                        report = self.client.create_report(
                            dataset="public-global-sar-presence:latest",
                            start_date=chunk_start,
                            end_date=chunk_end,
                            filters="matched='false'",  # Per API docs: use quoted string 'false'
                            eez_id=eez_id,
                            spatial_resolution="HIGH",
                            temporal_resolution="DAILY"  # API docs: DAILY, MONTHLY, or ENTIRE (not HOURLY)
                        )
                        
                        # Parse report response structure per GFW API docs:
                        # Response has "entries" array, each entry is a dict with dataset version as key
                        # e.g., entries[0]["public-global-sar-presence:v3.0"] = array of detections
                        # Each detection has: date, detections (count), lat, lon
                        chunk_detections = []
                        if "entries" in report and len(report["entries"]) > 0:
                            for entry in report["entries"]:
                                # Find the dataset key (e.g., "public-global-sar-presence:v3.0")
                                dataset_key = None
                                for key in entry.keys():
                                    if "sar-presence" in key.lower():
                                        dataset_key = key
                                        break
                                
                                if dataset_key and isinstance(entry[dataset_key], list):
                                    detections = entry[dataset_key]
                                    # Each detection has: date, detections (count), lat, lon
                                    # Convert to our expected format
                                    for det in detections:
                                        if "lat" in det and "lon" in det:
                                            # Convert to our format with latitude/longitude
                                            converted_det = {
                                                "latitude": det["lat"],
                                                "longitude": det["lon"],
                                                "date": det.get("date"),
                                                "detections": det.get("detections", 1),
                                                "matched": False  # Already filtered by API
                                            }
                                            chunk_detections.append(converted_det)
                            
                            results["sar_detections"].extend(chunk_detections)
                            logging.info(f"Found {len(chunk_detections)} SAR detections for EEZ {eez_id}, chunk {chunk_start} to {chunk_end}")
                        else:
                            logging.debug(f"No entries in report for EEZ {eez_id}, chunk {chunk_start} to {chunk_end}. Report keys: {list(report.keys())}")
                            if "total" in report:
                                logging.debug(f"Report total: {report['total']}")
                    except Exception as e:
                        logging.warning(f"Failed SAR detection for EEZ {eez_id}, chunk {chunk_start} to {chunk_end}: {e}")
        
        # Get AIS gap events
        if include_gaps:
            for eez_id in eez_ids:
                for chunk_start, chunk_end in date_chunks:
                    try:
                        logging.info(f"Fetching gap events for EEZ {eez_id}, chunk {chunk_start} to {chunk_end}, intentional_only={intentional_gaps_only}")
                        
                        # CRITICAL: Do NOT pass limit/offset at all - API requires both together or neither
                        # Passing None might still serialize to null/0, so we don't include them in the call
                        gaps = self.client.get_gap_events(
                            start_date=chunk_start,
                            end_date=chunk_end,
                            eez_id=eez_id,
                            intentional_only=intentional_gaps_only
                            # Explicitly NOT passing limit or offset - let API return all results
                        )
                        
                        # Handle different response structures
                        gap_list = []
                        if isinstance(gaps, dict):
                            gap_list = gaps.get("entries") or (gaps.get("data") if isinstance(gaps.get("data"), list) else [gaps["data"]] if "data" in gaps else []) or gaps.get("results", [])
                        elif isinstance(gaps, list):
                            gap_list = gaps
                        if isinstance(gap_list, list) and len(gap_list) > 0 and not isinstance(gap_list[0], dict):
                            gap_list = [gap_list] if gap_list else []
                        
                        if gap_list:
                            results["gap_events"].extend(gap_list)
                            logging.info(f"Found {len(gap_list)} gap events for EEZ {eez_id}, chunk {chunk_start} to {chunk_end}")
                        else:
                            logging.debug(f"No gap events for EEZ {eez_id}, chunk {chunk_start} to {chunk_end}")
                    except Exception as e:
                        logging.error(f"✗ Failed gap events for EEZ {eez_id}, chunk {chunk_start} to {chunk_end}: {e}", exc_info=True)
        
        # Cross-reference vessel IDs (SAR API doesn't return vessel_id, only gap events do)
        vessel_ids = {vid for item in results["sar_detections"] + results["gap_events"] 
                     if (vid := self._extract_vessel_id(item))}
        
        results["combined"] = list(vessel_ids)
        results["summary"] = {
            "total_sar_detections": len(results["sar_detections"]),
            "total_gap_events": len(results["gap_events"]),
            "unique_vessels": len(vessel_ids),
            "unique_detection_points": len(results["sar_detections"]),  # Number of unique detection locations
            "eez_count": len(eez_ids),
            "note": "SAR detections are location points, not individual vessels. unique_vessels only counts vessels from gap events."
        }
        
        return results
    
    def calculate_risk_score(self, vessel_id: str, start_date: str, end_date: str) -> Dict[str, Any]:
        """
        Calculate enhanced risk score for a vessel based on:
        - Gap frequency
        - IUU status
        - Fishing intensity
        - Encounter frequency
        - Port visit patterns
        
        Returns score 0-100.
        """
        try:
            vessel = {"datasetId": "public-global-vessel-identity:latest", "vesselId": vessel_id}
            
            # Get insights for vessel
            insights = self.client.get_vessel_insights(
                vessels=[vessel],
                start_date=start_date,
                end_date=end_date,
                includes=["GAP", "VESSEL-IDENTITY-IUU-VESSEL-LIST"]
            )
            
            score = 0
            factors = {}
            
            # Gap events increase risk (0-50 points)
            if "gap" in insights:
                gap_count = insights["gap"].get("periodSelectedCounters", {}).get("events", 0)
                gap_score = min(gap_count * 10, 50)  # Max 50 points for gaps
                score += gap_score
                factors["gap_events"] = gap_count
                factors["gap_score"] = gap_score
            
            # IUU listing increases risk (0-50 points)
            if "vesselIdentity" in insights:
                iuu_listed = insights["vesselIdentity"].get("iuuVesselList", {}).get("totalTimesListedInThePeriod", 0)
                if iuu_listed > 0:
                    iuu_score = 50  # High risk if IUU listed
                    score += iuu_score
                    factors["iuu_listed"] = True
                    factors["iuu_count"] = iuu_listed
                    factors["iuu_score"] = iuu_score
                else:
                    factors["iuu_listed"] = False
            
            # Get additional activity data for risk calculation
            try:
                # Fishing intensity (0-15 points)
                fishing_events = self.client.get_all_events(
                    datasets=["public-global-fishing-events:latest"],
                    vessels=[vessel],
                    start_date=start_date,
                    end_date=end_date
                )
                fishing_count = len(fishing_events.get("entries", [])) if isinstance(fishing_events, dict) else 0
                fishing_score = min(fishing_count * 0.5, 15)  # Max 15 points
                score += fishing_score
                factors["fishing_events"] = fishing_count
                factors["fishing_score"] = fishing_score
            except Exception as e:
                logging.warning(f"Failed to get fishing events for risk calculation: {e}")
                factors["fishing_events"] = 0
                factors["fishing_score"] = 0
            
            try:
                # Encounter frequency (0-20 points) - frequent encounters = potential transshipment
                encounters = self.client.get_all_events(
                    datasets=["public-global-encounters-events:latest"],
                    vessels=[vessel],
                    start_date=start_date,
                    end_date=end_date
                )
                encounter_count = len(encounters.get("entries", [])) if isinstance(encounters, dict) else 0
                encounter_score = min(encounter_count * 2, 20)  # Max 20 points
                score += encounter_score
                factors["encounters"] = encounter_count
                factors["encounter_score"] = encounter_score
            except Exception as e:
                logging.warning(f"Failed to get encounters for risk calculation: {e}")
                factors["encounters"] = 0
                factors["encounter_score"] = 0
            
            try:
                # Port visits (0-15 points) - many port visits could indicate suspicious activity
                port_visits = self.client.get_all_events(
                    datasets=["public-global-port-visits-events:latest"],
                    vessels=[vessel],
                    start_date=start_date,
                    end_date=end_date
                )
                port_count = len(port_visits.get("entries", [])) if isinstance(port_visits, dict) else 0
                port_score = min(port_count * 0.3, 15)  # Max 15 points
                score += port_score
                factors["port_visits"] = port_count
                factors["port_score"] = port_score
            except Exception as e:
                logging.warning(f"Failed to get port visits for risk calculation: {e}")
                factors["port_visits"] = 0
                factors["port_score"] = 0
            
            # Calculate risk level
            risk_level = "low"
            if score >= 70:
                risk_level = "high"
            elif score >= 40:
                risk_level = "medium"
            
            return {
                "vessel_id": vessel_id,
                "risk_score": min(score, 100),
                "risk_level": risk_level,
                "factors": factors,
                "insights": insights,
                "date_range": f"{start_date},{end_date}"
            }
        except Exception as e:
            logging.error(f"Error calculating risk for {vessel_id}: {e}")
            return {"vessel_id": vessel_id, "risk_score": 0, "risk_level": "unknown", "error": str(e)}
    
    def _haversine_distance(self, lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        """
        Calculate distance between two points using Haversine formula.
        Returns distance in kilometers.
        """
        R = 6371  # Earth's radius in kilometers
        
        lat1_rad = math.radians(lat1)
        lat2_rad = math.radians(lat2)
        delta_lat = math.radians(lat2 - lat1)
        delta_lon = math.radians(lon2 - lon1)
        
        a = (math.sin(delta_lat / 2) ** 2 +
             math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(delta_lon / 2) ** 2)
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
        
        return R * c
    
    def detect_proximity_clusters(self,
                                 sar_detections: List[Dict[str, Any]],
                                 max_distance_km: float = 5.0,
                                 same_date_only: bool = True) -> List[Dict[str, Any]]:
        """
        Detect clusters of SAR detections that are close to each other at the same time.
        This can indicate dark trade activity (transshipment, rendezvous, illegal transfers).
        
        Risk assessment based on established maritime security frameworks:
        - High Risk (3+ vessels): Indicates coordinated illicit activities, complex STS transfers
          (Sources: Lloyd's List Intelligence, Kpler Risk & Compliance, LSE Research)
        - Medium Risk (2 vessels): May indicate bilateral STS transfers or rendezvous
          (Sources: Lloyd's List Intelligence, Windward Maritime Intelligence)
        
        See DARK_TRADE_RISK_THRESHOLDS.md for detailed citations and rationale.
        
        Args:
            sar_detections: List of SAR detection dictionaries with lat/lon/date
            max_distance_km: Maximum distance in km to consider vessels "close" (default 5km)
                             Based on typical STS transfer distances (0.5-2nm) with buffer
            same_date_only: If True, only cluster detections on the same date (default True)
        
        Returns:
            List of cluster dictionaries, each containing:
            - center_latitude, center_longitude: Center point of cluster
            - date: Date of cluster
            - vessel_count: Number of vessels in cluster (from detections count)
            - detections: List of detection points in cluster
            - max_distance_km: Maximum distance between any two points in cluster
            - risk_indicator: "high" if 3+ vessels, "medium" if 2 vessels, "low" otherwise
        """
        if not sar_detections:
            logging.debug("No SAR detections provided for clustering")
            return []
        
        logging.info(f"Detecting proximity clusters from {len(sar_detections)} SAR detections (max_distance={max_distance_km}km, same_date_only={same_date_only})")
        
        clusters = []
        processed = set()
        
        # Group by date if same_date_only
        if same_date_only:
            detections_by_date = {}
            for det in sar_detections:
                date = det.get("date")
                # Handle both string dates and None values
                if date:
                    if date not in detections_by_date:
                        detections_by_date[date] = []
                    detections_by_date[date].append(det)
                else:
                    # If no date, use "unknown" as key
                    if "unknown" not in detections_by_date:
                        detections_by_date["unknown"] = []
                    detections_by_date["unknown"].append(det)
            
            # Process each date separately (only if 2+ detections for that date)
            for date, date_detections in detections_by_date.items():
                if len(date_detections) >= 2:  # Only process if 2+ detections for this date
                    clusters.extend(self._find_clusters_for_date(
                        date_detections, 
                        max_distance_km, 
                        date if date != "unknown" else None
                    ))
        else:
            # Process all detections together (only if 2+ total detections)
            if len(sar_detections) >= 2:
                clusters = self._find_clusters_for_date(sar_detections, max_distance_km, None)
        
        # Sort by vessel count (descending) and date
        clusters.sort(key=lambda x: (-x["vessel_count"], x.get("date", "")))
        
        logging.info(f"Found {len(clusters)} proximity clusters from {len(sar_detections)} SAR detections")
        if clusters:
            logging.info(f"Cluster summary: {sum(c['vessel_count'] for c in clusters)} total vessels in clusters")
            logging.info(f"Risk breakdown: {sum(1 for c in clusters if c['risk_indicator'] == 'high')} high, {sum(1 for c in clusters if c['risk_indicator'] == 'medium')} medium")
        
        return clusters
    
    def _find_clusters_for_date(self,
                               detections: List[Dict[str, Any]],
                               max_distance_km: float,
                               date: Optional[str]) -> List[Dict[str, Any]]:
        """
        Find clusters within a set of detections using a graph-based approach.
        Detections are clustered if they form a connected component where each detection
        is within max_distance_km of at least one other detection in the cluster.
        """
        clusters = []
        processed = set()
        
        # Build distance graph: for each detection, find all nearby detections
        # This ensures we find all connected components (clusters)
        for i, det1 in enumerate(detections):
            if i in processed:
                continue
            
            # Get coordinates for det1
            lat1 = det1.get("latitude") or det1.get("lat")
            lon1 = det1.get("longitude") or det1.get("lon")
            
            if lat1 is None or lon1 is None:
                continue
            
            # Start a new cluster with det1
            cluster_detections = [det1]
            cluster_indices = [i]
            
            # Use breadth-first search to find all connected detections
            # A detection is added if it's within max_distance_km of ANY detection already in cluster
            queue = [i]  # Queue of indices to check for neighbors
            visited_in_cluster = {i}  # Track what we've already checked in this cluster
            
            while queue:
                current_idx = queue.pop(0)
                current_det = detections[current_idx]
                current_lat = current_det.get("latitude") or current_det.get("lat")
                current_lon = current_det.get("longitude") or current_det.get("lon")
                
                if current_lat is None or current_lon is None:
                    continue
                
                # Check all other detections for proximity to current detection
                for j, det2 in enumerate(detections):
                    if j in processed or j in visited_in_cluster:
                        continue
                    
                    lat2 = det2.get("latitude") or det2.get("lat")
                    lon2 = det2.get("longitude") or det2.get("lon")
                    
                    if lat2 is None or lon2 is None:
                        continue
                    
                    # Check if det2 is within max_distance_km of current detection
                    distance = self._haversine_distance(current_lat, current_lon, lat2, lon2)
                    
                    if distance <= max_distance_km:
                        # Add to cluster and continue searching from this detection
                        cluster_detections.append(det2)
                        cluster_indices.append(j)
                        visited_in_cluster.add(j)
                        queue.append(j)
            
            # Only create cluster if 2+ detections found
            if len(cluster_detections) >= 2:
                # Validate all detections have coordinates (defensive check)
                valid_detections = []
                for d in cluster_detections:
                    lat = d.get("latitude") or d.get("lat")
                    lon = d.get("longitude") or d.get("lon")
                    if lat is not None and lon is not None:
                        valid_detections.append((lat, lon, d))
                
                # Skip cluster if we don't have at least 2 valid detections
                if len(valid_detections) < 2:
                    logging.warning(f"Skipping cluster with {len(cluster_detections)} detections but only {len(valid_detections)} have valid coordinates")
                    continue
                
                # Calculate cluster center (average of all valid points)
                total_lat = sum(lat for lat, lon, d in valid_detections)
                total_lon = sum(lon for lat, lon, d in valid_detections)
                center_lat = total_lat / len(valid_detections)
                center_lon = total_lon / len(valid_detections)
                
                # Calculate total vessel count (sum of detections counts from valid detections)
                total_vessels = sum(d.get("detections", 1) for lat, lon, d in valid_detections)
                
                # Calculate max distance within cluster (using valid detections only)
                max_dist = 0
                for i, (lat1, lon1, d1) in enumerate(valid_detections):
                    for j, (lat2, lon2, d2) in enumerate(valid_detections[i+1:], start=i+1):
                        dist = self._haversine_distance(lat1, lon1, lat2, lon2)
                        max_dist = max(max_dist, dist)
                
                # Determine risk indicator
                risk_indicator = "low"
                if total_vessels >= 3:
                    risk_indicator = "high"
                elif total_vessels >= 2:
                    risk_indicator = "medium"
                
                cluster = {
                    "center_latitude": center_lat,
                    "center_longitude": center_lon,
                    "date": date or valid_detections[0][2].get("date") if valid_detections else None,
                    "vessel_count": total_vessels,
                    "detection_count": len(valid_detections),
                    "detections": [d for lat, lon, d in valid_detections],  # Only include valid detections
                    "max_distance_km": round(max_dist, 2),
                    "risk_indicator": risk_indicator,
                    "description": f"{total_vessels} dark vessel(s) detected within {max_distance_km}km - possible transshipment/rendezvous"
                }
                
                clusters.append(cluster)
                
                # Mark all detections in cluster as processed
                processed.update(cluster_indices)
        
        return clusters
    
    def predict_routes(self,
                      sar_detections: List[Dict[str, Any]],
                      gap_events: List[Dict[str, Any]],
                      max_time_hours: float = 48.0,
                      max_distance_km: float = 100.0,
                      min_route_length: int = 2) -> List[Dict[str, Any]]:
        """
        Predict likely routes dark vessels use by connecting detections temporally and spatially.
        
        Uses statistical analysis to connect:
        - SAR detections that are close in time and space
        - Gap events from the same vessel (if vessel IDs available)
        - Pattern recognition for common routes
        
        Args:
            sar_detections: List of SAR detection points
            gap_events: List of gap events (may have vessel IDs)
            max_time_hours: Maximum time difference (hours) to connect detections (default 48h)
            max_distance_km: Maximum distance (km) to connect detections (default 100km)
            min_route_length: Minimum number of points to form a route (default 2)
        
        Returns:
            List of route dictionaries, each containing:
            - route_id: Unique identifier for the route
            - points: List of [lat, lon, timestamp] points along the route
            - total_distance_km: Total route distance
            - duration_hours: Time span of the route
            - confidence: Confidence score (0-1) based on temporal/spatial consistency
            - vessel_id: Vessel ID if available (from gap events), None for SAR-only routes
        """
        if not sar_detections and not gap_events:
            logging.debug("No detections provided for route prediction")
            return []
        
        logging.info(f"Predicting routes from {len(sar_detections)} SAR detections and {len(gap_events)} gap events")
        
        routes = []
        
        # Helper to extract coordinates and timestamp
        def extract_point_data(item):
            """Extract lat, lon, and timestamp from detection/gap event."""
            # Extract coordinates
            lat = (item.get("latitude") or item.get("lat") or 
                   item.get("lat_center") or item.get("center_lat") or
                   item.get("startLat") or item.get("endLat") or item.get("centerLat"))
            lon = (item.get("longitude") or item.get("lon") or
                   item.get("lon_center") or item.get("center_lon") or
                   item.get("startLon") or item.get("endLon") or item.get("centerLon"))
            
            # Try geometry/coordinates
            if (lat is None or lon is None) and item.get("geometry"):
                geom = item["geometry"]
                if geom.get("type") == "Point" and isinstance(geom.get("coordinates"), list):
                    lon = geom["coordinates"][0]
                    lat = geom["coordinates"][1]
            
            if lat is None or lon is None or not (-90 <= lat <= 90) or not (-180 <= lon <= 180):
                return None
            
            # Extract timestamp/date
            timestamp = None
            date_str = item.get("date") or item.get("timestamp") or item.get("start") or item.get("end")
            if date_str:
                try:
                    # Try parsing various date formats
                    if isinstance(date_str, str):
                        if "T" in date_str:
                            timestamp = datetime.fromisoformat(date_str.replace("Z", "+00:00"))
                        else:
                            timestamp = datetime.strptime(date_str, "%Y-%m-%d")
                    else:
                        timestamp = date_str
                except:
                    pass
            
            vid = self._extract_vessel_id(item)
            return {
                "lat": lat, "lon": lon, "timestamp": timestamp, "date": date_str,
                "vessel_id": vid, "source": "gap" if vid else "sar"
            }
        
        # Extract all points with valid coordinates
        all_points = []
        for det in sar_detections:
            point = extract_point_data(det)
            if point:
                all_points.append(point)
        
        for gap in gap_events:
            point = extract_point_data(gap)
            if point:
                all_points.append(point)
        
        if len(all_points) < min_route_length:
            logging.debug(f"Not enough valid points ({len(all_points)}) for route prediction")
            return []
        
        # Sort points by timestamp (or date if no timestamp)
        def get_sort_key(point):
            if point["timestamp"]:
                return point["timestamp"]
            elif point["date"]:
                try:
                    return datetime.strptime(point["date"], "%Y-%m-%d")
                except:
                    return datetime.min
            return datetime.min
        
        all_points.sort(key=get_sort_key)
        
        # Group points by vessel ID (if available) for gap events
        vessel_routes = {}  # vessel_id -> list of points
        
        # First, process gap events with vessel IDs (these are more reliable)
        for point in all_points:
            if point["vessel_id"]:
                vid = point["vessel_id"]
                if vid not in vessel_routes:
                    vessel_routes[vid] = []
                vessel_routes[vid].append(point)
        
        # Create routes from gap events (same vessel, chronological)
        for vessel_id, points in vessel_routes.items():
            if len(points) >= min_route_length:
                # Sort by timestamp
                points.sort(key=get_sort_key)
                
                # Connect consecutive points if they're reasonable
                route_points = []
                for i, point in enumerate(points):
                    if i == 0:
                        route_points.append([point["lat"], point["lon"], point.get("timestamp") or point.get("date")])
                    else:
                        prev_point = points[i-1]
                        distance = self._haversine_distance(
                            prev_point["lat"], prev_point["lon"],
                            point["lat"], point["lon"]
                        )
                        
                        # Calculate time difference
                        time_diff_hours = None
                        if prev_point["timestamp"] and point["timestamp"]:
                            time_diff = (point["timestamp"] - prev_point["timestamp"]).total_seconds() / 3600
                            time_diff_hours = abs(time_diff)
                        elif prev_point["date"] and point["date"]:
                            try:
                                d1 = datetime.strptime(prev_point["date"], "%Y-%m-%d")
                                d2 = datetime.strptime(point["date"], "%Y-%m-%d")
                                time_diff_hours = abs((d2 - d1).total_seconds() / 3600)
                            except:
                                pass
                        
                        # Add point if within reasonable distance and time
                        if distance <= max_distance_km:
                            if time_diff_hours is None or time_diff_hours <= max_time_hours:
                                route_points.append([point["lat"], point["lon"], point.get("timestamp") or point.get("date")])
                            else:
                                # Time gap too large, start new route segment
                                if len(route_points) >= min_route_length:
                                    routes.append(self._create_route_from_points(route_points, vessel_id))
                                route_points = [[point["lat"], point["lon"], point.get("timestamp") or point.get("date")]]
                        else:
                            # Distance too large, start new route segment
                            if len(route_points) >= min_route_length:
                                routes.append(self._create_route_from_points(route_points, vessel_id))
                            route_points = [[point["lat"], point["lon"], point.get("timestamp") or point.get("date")]]
                
                # Add final route segment
                if len(route_points) >= min_route_length:
                    routes.append(self._create_route_from_points(route_points, vessel_id))
        
        # Now process SAR-only detections (no vessel IDs) using statistical clustering
        sar_points = [p for p in all_points if not p["vessel_id"]]
        
        if len(sar_points) >= min_route_length:
            # Group SAR points by temporal proximity and connect spatially
            sar_routes = self._connect_sar_points(sar_points, max_time_hours, max_distance_km, min_route_length)
            routes.extend(sar_routes)
        
        # Sort routes by confidence and length
        routes.sort(key=lambda r: (-r.get("confidence", 0), -len(r.get("points", []))))
        
        logging.info(f"Predicted {len(routes)} routes from {len(all_points)} detection points")
        
        return routes
    
    def _create_route_from_points(self, points: List[List], vessel_id: Optional[str] = None) -> Dict[str, Any]:
        """Create a route dictionary from a list of [lat, lon, timestamp] points."""
        if len(points) < 2:
            return None
        
        # Calculate total distance
        total_distance = 0
        for i in range(len(points) - 1):
            lat1, lon1 = points[i][0], points[i][1]
            lat2, lon2 = points[i+1][0], points[i+1][1]
            total_distance += self._haversine_distance(lat1, lon1, lat2, lon2)
        
        # Calculate duration
        duration_hours = None
        if len(points) > 1:
            first_time = points[0][2]
            last_time = points[-1][2]
            if first_time and last_time:
                try:
                    if isinstance(first_time, datetime) and isinstance(last_time, datetime):
                        duration_hours = abs((last_time - first_time).total_seconds() / 3600)
                    elif isinstance(first_time, str) and isinstance(last_time, str):
                        d1 = datetime.strptime(first_time[:10], "%Y-%m-%d")
                        d2 = datetime.strptime(last_time[:10], "%Y-%m-%d")
                        duration_hours = abs((d2 - d1).total_seconds() / 3600)
                except:
                    pass
        
        # Calculate confidence based on:
        # - Number of points (more = higher confidence)
        # - Temporal consistency (closer in time = higher confidence)
        # - Spatial consistency (reasonable distances = higher confidence)
        confidence = min(len(points) / 10.0, 1.0)  # More points = higher confidence, capped at 1.0
        
        if duration_hours and duration_hours > 0:
            avg_speed_kmh = total_distance / duration_hours
            # Reasonable vessel speeds are 10-50 km/h, penalize unrealistic speeds
            if 5 <= avg_speed_kmh <= 60:
                confidence *= 1.0
            elif avg_speed_kmh < 5:
                confidence *= 0.8  # Very slow, might be drifting
            else:
                confidence *= 0.6  # Unrealistically fast
        
        route_id = f"route_{len(points)}_{hash(tuple(p[0:2] for p in points)) % 10000}"
        
        return {
            "route_id": route_id,
            "points": points,
            "total_distance_km": round(total_distance, 2),
            "duration_hours": round(duration_hours, 2) if duration_hours else None,
            "confidence": round(confidence, 2),
            "vessel_id": vessel_id,
            "point_count": len(points)
        }
    
    def _connect_sar_points(self,
                           points: List[Dict[str, Any]],
                           max_time_hours: float,
                           max_distance_km: float,
                           min_route_length: int) -> List[Dict[str, Any]]:
        """
        Connect SAR detection points into routes using temporal and spatial proximity.
        Since SAR points don't have vessel IDs, we use statistical methods to connect them.
        """
        routes = []
        processed = set()
        
        for i, point1 in enumerate(points):
            if i in processed:
                continue
            
            # Start a new route from this point
            route_points = [[point1["lat"], point1["lon"], point1.get("timestamp") or point1.get("date")]]
            processed.add(i)
            
            # Find next point in sequence
            current_point = point1
            found_next = True
            
            while found_next:
                found_next = False
                best_next = None
                best_score = 0
                best_idx = None
                
                for j, point2 in enumerate(points):
                    if j in processed or j == i:
                        continue
                    
                    # Calculate distance
                    distance = self._haversine_distance(
                        current_point["lat"], current_point["lon"],
                        point2["lat"], point2["lon"]
                    )
                    
                    if distance > max_distance_km:
                        continue
                    
                    # Calculate time difference
                    time_diff_hours = None
                    if current_point["timestamp"] and point2["timestamp"]:
                        time_diff = (point2["timestamp"] - current_point["timestamp"]).total_seconds() / 3600
                        if time_diff > 0:  # Only future points
                            time_diff_hours = time_diff
                    elif current_point["date"] and point2["date"]:
                        try:
                            d1 = datetime.strptime(current_point["date"], "%Y-%m-%d")
                            d2 = datetime.strptime(point2["date"], "%Y-%m-%d")
                            time_diff = (d2 - d1).total_seconds() / 3600
                            if time_diff > 0:
                                time_diff_hours = time_diff
                        except:
                            pass
                    
                    if time_diff_hours is None or time_diff_hours > max_time_hours:
                        continue
                    
                    # Score based on distance and time (closer and sooner = better)
                    # Lower distance and time = higher score
                    score = 1.0 / (1.0 + distance) * 1.0 / (1.0 + time_diff_hours)
                    
                    if score > best_score:
                        best_score = score
                        best_next = point2
                        best_idx = j
                
                if best_next and best_idx is not None:
                    route_points.append([best_next["lat"], best_next["lon"], 
                                       best_next.get("timestamp") or best_next.get("date")])
                    processed.add(best_idx)
                    current_point = best_next
                    found_next = True
                else:
                    break
            
            # Create route if we have enough points
            if len(route_points) >= min_route_length:
                route = self._create_route_from_points(route_points, None)
                if route:
                    routes.append(route)
        
        return routes
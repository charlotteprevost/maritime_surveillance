"""
Dark Vessel Service - Core logic for detecting and analyzing dark vessels.
Combines SAR detections with AIS gap events.
"""
import logging
import time
from typing import Dict, List, Optional, Any
from datetime import datetime


class DarkVesselService:
    """Service for dark vessel detection and analysis."""
    
    def __init__(self, gfw_client):
        """Initialize with GFW API client."""
        self.client = gfw_client
    
    def get_dark_vessels(self,
                        eez_ids: List[str],
                        start_date: str,
                        end_date: str,
                        include_sar: bool = True,
                        include_gaps: bool = True,
                        intentional_gaps_only: bool = True) -> Dict[str, Any]:
        """
        Get dark vessels: SAR detections (matched=false) + AIS gap events.
        
        Returns combined results with vessel IDs cross-referenced.
        """
        results = {
            "sar_detections": [],
            "gap_events": [],
            "combined": [],
            "summary": {}
        }
        
        # Get SAR detections (unmatched vessels)
        # Serialize requests to avoid 429 errors (API token not enabled for concurrent reports)
        if include_sar:
            for i, eez_id in enumerate(eez_ids):
                try:
                    # Add delay between requests to avoid concurrent report limit
                    if i > 0:
                        time.sleep(1.0)  # 1 second delay between report requests
                    
                    # Try without matched filter first - the API seems to have issues with boolean filters
                    # We can filter unmatched vessels on the client side if needed
                    report = self.client.create_report(
                        dataset="public-global-sar-presence:latest",
                        start_date=start_date,
                        end_date=end_date,
                        filters=None,  # Don't use matched filter - API has type issues with boolean filters
                        eez_id=eez_id,
                        spatial_resolution="HIGH",
                        temporal_resolution="DAILY"  # API docs: DAILY, MONTHLY, or ENTIRE (not HOURLY)
                    )
                    # Parse report data and filter for unmatched vessels (matched=false)
                    if "data" in report:
                        # Filter for unmatched vessels on client side since API has issues with boolean filters
                        unmatched = [det for det in report["data"] if det.get("matched") is False or det.get("matched") == "false"]
                        results["sar_detections"].extend(unmatched)
                except Exception as e:
                    logging.warning(f"Failed SAR detection for EEZ {eez_id}: {e}")
        
        # Get AIS gap events
        if include_gaps:
            for eez_id in eez_ids:
                try:
                    # Don't pass limit/offset to avoid pagination issues - let API return all results
                    # API requires both limit and offset together, so pass None for both
                    gaps = self.client.get_gap_events(
                        start_date=start_date,
                        end_date=end_date,
                        eez_id=eez_id,
                        intentional_only=intentional_gaps_only,
                        limit=None,  # Don't paginate - get all results
                        offset=None  # Must be None if limit is None (API requirement)
                    )
                    if "entries" in gaps:
                        results["gap_events"].extend(gaps["entries"])
                except Exception as e:
                    logging.warning(f"Failed gap events for EEZ {eez_id}: {e}")
        
        # Cross-reference vessel IDs
        vessel_ids = set()
        for det in results["sar_detections"]:
            if "vessel_id" in det:
                vessel_ids.add(det["vessel_id"])
        for gap in results["gap_events"]:
            if "vesselId" in gap:
                vessel_ids.add(gap["vesselId"])
        
        results["combined"] = list(vessel_ids)
        results["summary"] = {
            "total_sar_detections": len(results["sar_detections"]),
            "total_gap_events": len(results["gap_events"]),
            "unique_vessels": len(vessel_ids),
            "eez_count": len(eez_ids)
        }
        
        return results
    
    def calculate_risk_score(self, vessel_id: str, start_date: str, end_date: str) -> Dict[str, Any]:
        """
        Calculate risk score for a vessel based on gap frequency, location, IUU status.
        Returns score 0-100.
        """
        try:
            # Get insights for vessel
            insights = self.client.get_vessel_insights(
                vessels=[{"datasetId": "public-global-vessel-identity:latest", "vesselId": vessel_id}],
                start_date=start_date,
                end_date=end_date,
                includes=["GAP", "VESSEL-IDENTITY-IUU-VESSEL-LIST"]
            )
            
            score = 0
            factors = {}
            
            # Gap events increase risk
            if "gap" in insights:
                gap_count = insights["gap"].get("periodSelectedCounters", {}).get("events", 0)
                score += min(gap_count * 10, 50)  # Max 50 points for gaps
                factors["gap_events"] = gap_count
            
            # IUU listing increases risk
            if "vesselIdentity" in insights:
                iuu_listed = insights["vesselIdentity"].get("iuuVesselList", {}).get("totalTimesListedInThePeriod", 0)
                if iuu_listed > 0:
                    score += 50  # High risk if IUU listed
                    factors["iuu_listed"] = True
            
            return {
                "vessel_id": vessel_id,
                "risk_score": min(score, 100),
                "factors": factors,
                "insights": insights
            }
        except Exception as e:
            logging.error(f"Error calculating risk for {vessel_id}: {e}")
            return {"vessel_id": vessel_id, "risk_score": 0, "error": str(e)}

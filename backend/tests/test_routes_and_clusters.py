import os
import sys
import pytest

# Ensure the app module is importable from the parent directory
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from app import app as flask_app
from utils.gfw_client import GFWApiClient


@pytest.fixture
def client():
    flask_app.config["TESTING"] = True
    flask_app.config["GFW_CLIENT"] = GFWApiClient("test-token", enable_cache=False)
    return flask_app.test_client()


def _mock_sar_presence_report(requests_mock, detections):
    """
    Mock a minimal 4Wings SAR presence report response with the expected entries structure.
    `detections` should be a list of dicts with keys: date, lat, lon, detections.
    """
    requests_mock.post(
        "https://gateway.api.globalfishingwatch.org/v3/4wings/report",
        json={
            "entries": [
                {
                    # Key name must contain "sar-presence" for the service parser
                    "public-global-sar-presence:v3.0": detections
                }
            ]
        },
        status_code=200,
    )


def test_routes_missing_required_params(client):
    res = client.get("/api/detections/routes?start_date=2025-04-01&end_date=2025-04-05")
    assert res.status_code == 400


def test_routes_happy_path_builds_one_route(client, requests_mock):
    # Two points within ~15km and 24h -> should connect into a route of length 2
    _mock_sar_presence_report(
        requests_mock,
        detections=[
            {"date": "2025-04-01", "detections": 1, "lat": 10.0, "lon": 20.0},
            {"date": "2025-04-02", "detections": 1, "lat": 10.1, "lon": 20.1},
        ],
    )

    res = client.get(
        "/api/detections/routes?eez_ids=France&start_date=2025-04-01&end_date=2025-04-05"
    )
    assert res.status_code == 200
    assert "routes" in res.json
    assert isinstance(res.json["routes"], list)
    assert len(res.json["routes"]) >= 1

    route0 = res.json["routes"][0]
    assert route0.get("point_count") == 2
    assert route0.get("points") and len(route0["points"]) == 2
    assert "confidence" in route0


def test_proximity_clusters_invalid_max_distance(client):
    res = client.get(
        "/api/detections/proximity-clusters?eez_ids=France&start_date=2025-04-01&end_date=2025-04-05&max_distance_km=100"
    )
    assert res.status_code == 400


def test_proximity_clusters_happy_path_finds_medium_cluster(client, requests_mock):
    # Two detections same date and within ~2km -> should cluster into 1 medium-risk cluster
    _mock_sar_presence_report(
        requests_mock,
        detections=[
            {"date": "2025-04-01", "detections": 1, "lat": 0.0, "lon": 0.0},
            {"date": "2025-04-01", "detections": 1, "lat": 0.0, "lon": 0.018},
        ],
    )

    res = client.get(
        "/api/detections/proximity-clusters?eez_ids=France&start_date=2025-04-01&end_date=2025-04-05&max_distance_km=5.0&same_date_only=true"
    )
    assert res.status_code == 200
    assert "clusters" in res.json
    assert isinstance(res.json["clusters"], list)
    assert res.json["total_clusters"] == 1

    cluster0 = res.json["clusters"][0]
    assert cluster0["risk_indicator"] == "medium"
    assert cluster0["vessel_count"] == 2


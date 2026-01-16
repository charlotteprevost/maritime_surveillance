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
    # Ensure the API client is initialized for endpoints that require it
    flask_app.config["GFW_CLIENT"] = GFWApiClient("test-token", enable_cache=False)
    return flask_app.test_client()


def test_sar_ais_association_summary(client, requests_mock):
    url = "https://gateway.api.globalfishingwatch.org/v3/4wings/report"

    def match_unmatched(request):
        # filters[0]=matched='false' (URL-encoded)
        return "filters%5B0%5D=matched%3D%27false%27" in request.url

    def match_matched(request):
        # filters[0]=matched='true' (URL-encoded)
        return "filters%5B0%5D=matched%3D%27true%27" in request.url

    requests_mock.post(
        url,
        additional_matcher=match_unmatched,
        json={
            "entries": [
                {
                    "public-global-sar-presence:v3.0": [
                        {"date": "2025-04-01", "detections": 3, "lat": 10.0, "lon": 20.0},
                        {"date": "2025-04-02", "detections": 1, "lat": 11.0, "lon": 21.0},
                    ]
                }
            ]
        },
        status_code=200,
    )
    requests_mock.post(
        url,
        additional_matcher=match_matched,
        json={
            "entries": [
                {
                    "public-global-sar-presence:v3.0": [
                        {"date": "2025-04-01", "detections": 2, "lat": 12.0, "lon": 22.0}
                    ]
                }
            ]
        },
        status_code=200,
    )

    res = client.get(
        "/api/detections/sar-ais-association?eez_ids=France&start_date=2025-04-01&end_date=2025-04-05"
    )
    assert res.status_code == 200
    data = res.json

    assert "matched" in data and "unmatched" in data and "totals" in data
    assert data["unmatched"]["points"] == 2
    assert data["unmatched"]["total_detections"] == 4
    assert data["matched"]["points"] == 1
    assert data["matched"]["total_detections"] == 2

    assert data["totals"]["points"] == 3
    assert data["totals"]["total_detections"] == 6

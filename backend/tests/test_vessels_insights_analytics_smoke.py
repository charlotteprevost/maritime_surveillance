import os
import sys
import pytest
from requests_mock import ANY

# Ensure the app module is importable from the parent directory
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from app import app as flask_app
from utils.gfw_client import GFWApiClient


@pytest.fixture
def client():
    flask_app.config["TESTING"] = True
    flask_app.config["GFW_CLIENT"] = GFWApiClient("test-token", enable_cache=False)
    return flask_app.test_client()


def test_vessel_details_upstream_failure_is_json(client, requests_mock):
    # get_vessel_details -> GET /vessels/{id}
    requests_mock.get(ANY, status_code=500, json={"error": "Boom"})
    # Avoid 422 from strict query param validation by omitting includes here
    res = client.get("/api/vessels/test-vessel-id")
    # current behavior returns 400 with {"error": "..."} on exceptions
    assert res.status_code in (400, 500)
    assert isinstance(res.json, dict)
    assert "error" in res.json


def test_vessel_timeline_missing_dates(client):
    res = client.get("/api/vessels/test-vessel-id/timeline")
    assert res.status_code == 400
    assert "error" in res.json


def test_vessel_timeline_upstream_failures_degrade_to_empty_lists(client, requests_mock):
    # timeline fetches multiple event datasets via POST /events
    requests_mock.post(ANY, status_code=500, json={"error": "Fail"})
    res = client.get("/api/vessels/test-vessel-id/timeline?start_date=2025-04-01&end_date=2025-04-05")
    assert res.status_code == 200
    assert "events" in res.json
    assert isinstance(res.json["events"], dict)
    # all event lists should exist (filled with [] on failure)
    for k in ["fishing", "port_visits", "encounters", "loitering", "gaps"]:
        assert k in res.json["events"]
        assert isinstance(res.json["events"][k], list)


def test_insights_validation_error(client):
    # Missing required fields should trigger 422
    res = client.post("/api/insights", json={})
    assert res.status_code == 422
    assert "error" in res.json


def test_insights_upstream_failure_is_json(client, requests_mock):
    requests_mock.post(ANY, status_code=500, json={"error": "Boom"})
    res = client.post(
        "/api/insights",
        json={
            "includes": ["FISHING"],
            "startDate": "2025-04-01",
            "endDate": "2025-04-05",
            "vessels": [{"vesselId": "abc"}],
        },
    )
    assert res.status_code in (400, 500)
    assert "error" in res.json


def test_analytics_dark_vessels_missing_params(client):
    res = client.get("/api/analytics/dark-vessels")
    assert res.status_code == 400


def test_analytics_dark_vessels_smoke_ok_with_minimal_sar_report(client, requests_mock):
    # get_dark_vessels -> create_report (POST /4wings/report)
    requests_mock.post(
        "https://gateway.api.globalfishingwatch.org/v3/4wings/report",
        json={"entries": []},
        status_code=200,
    )
    # events in enhanced stats use POST /events; allow them to fail (caught and converted to 0)
    requests_mock.post(ANY, status_code=500, json={"error": "Fail"})

    res = client.get(
        "/api/analytics/dark-vessels?eez_ids=France&start_date=2025-04-01&end_date=2025-04-05"
    )
    assert res.status_code == 200
    assert "statistics" in res.json
    assert "summary" in res.json
    assert "vessel_ids" in res.json
    assert isinstance(res.json["vessel_ids"], list)


def test_analytics_risk_score_missing_dates(client):
    res = client.get("/api/analytics/risk-score/test-vessel-id")
    assert res.status_code == 400


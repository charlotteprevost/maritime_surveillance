import os
import sys
import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from app import app as flask_app

@pytest.fixture
def client():
    flask_app.config["TESTING"] = True
    return flask_app.test_client()

# --------------------------
# 🔍 Error Handling Tests
# --------------------------

def test_missing_country(client):
    res = client.get("/api/detections?start=2025-04-01&end=2025-04-05")
    assert res.status_code == 400
    assert "No country provided" in res.json.get("error", "")

def test_detections_invalid_country(client):
    res = client.get("/api/detections?country=Atlantis&start=2024-01-01&end=2024-01-07")
    assert res.status_code in (400, 404)
    assert "Invalid or ambiguous country" in res.json.get("error", "")

def test_multiple_countries_invalid(client):
    res = client.get("/api/detections?country=France&country=Spain&start=2025-04-01&end=2025-04-05")
    assert res.status_code == 400
    assert "Invalid or ambiguous country" in res.json["error"]

def test_missing_start(client):
    res = client.get("/api/detections?country=France&end=2025-04-10")
    assert res.status_code == 400 or res.status_code == 200  # depends on default handling

def test_missing_end(client):
    res = client.get("/api/detections?country=France&start=2025-04-01")
    assert res.status_code == 400 or res.status_code == 200  # depends on default handling

def test_invalid_date_format(client):
    res = client.get("/api/detections?country=France&start=bad&end=2025-05-01")
    assert res.status_code == 400
    assert "Invalid date format" in res.json.get("error", "")

def test_exceeds_max_range(client):
    res = client.get("/api/detections?country=France&start=2024-01-01&end=2025-05-01")
    assert res.status_code == 400
    assert "Date range cannot exceed" in res.json.get("error", "")

def test_start_after_end(client):
    res = client.get("/api/detections?country=France&start=2025-05-10&end=2025-04-10")
    assert res.status_code == 400
    assert "Start date must be before end date" in res.json.get("error", "")

def test_unknown_country(client):
    res = client.get("/api/detections?country=Atlantis&start=2025-04-01&end=2025-04-05")
    assert res.status_code in (400, 404)

# --------------------------
# ✅ Valid Scenarios
# --------------------------

def test_valid_no_data(client, requests_mock):
    requests_mock.post(
        "https://gateway.api.globalfishingwatch.org/v3/4wings/report",
        json={"entries": []},
        status_code=200,
    )
    res = client.get("/api/detections?country=France&start=2025-04-01&end=2025-04-05")
    assert res.status_code == 200
    assert res.json["type"] == "FeatureCollection"
    assert isinstance(res.json["features"], list)

def test_valid_with_filters(client, requests_mock):
    requests_mock.post(
        "https://gateway.api.globalfishingwatch.org/v3/4wings/report",
        json={"entries": []},
        status_code=200,
    )
    res = client.get("/api/detections?country=France&start=2025-04-01&end=2025-04-05&geartype=TRAWLERS&neural_vessel_type=Likely%20Fishing&shiptype=FISHING")
    assert res.status_code == 200
    assert res.json["type"] == "FeatureCollection"

def test_gfw_api_failure(client, requests_mock):
    # Simulate GFW failing across all EEZs
    requests_mock.post(
        "https://gateway.api.globalfishingwatch.org/v3/4wings/report",
        status_code=500,
        json={"error": "Boom"}
    )

    res = client.get("/api/detections?country=France&start=2025-04-01&end=2025-04-05")
    assert res.status_code == 200
    assert res.json["type"] == "FeatureCollection"
    assert res.json["features"] == []
    assert "failed_eezs" in res.json
    assert isinstance(res.json["failed_eezs"], list)
    assert all("error" in eez for eez in res.json["failed_eezs"])


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

def test_bins_missing_start(client):
    res = client.get("/api/bins/3?end=2025-04-30")
    assert res.status_code == 400
    assert "Missing" in res.json.get("error", "")

def test_bins_missing_end(client):
    res = client.get("/api/bins/3?start=2025-04-01")
    assert res.status_code == 400
    assert "Missing" in res.json.get("error", "")

def test_bins_gfw_api_error(client, requests_mock):
    requests_mock.get(
        "https://gateway.api.globalfishingwatch.org/v3/4wings/bins/3",
        status_code=500,
        json={"error": "Something exploded"}
    )
    res = client.get("/api/bins/3?start=2025-04-01&end=2025-04-30")
    assert res.status_code == 500
    assert "error" in res.json

# --------------------------
# ✅ Success Cases
# --------------------------

def test_bins_minimal_valid(client, requests_mock):
    bins_data = {
        "stepsByZoom": {
            "3": [{"value": 0}, {"value": 2}, {"value": 5}]
        }
    }

    requests_mock.get(
        "https://gateway.api.globalfishingwatch.org/v3/4wings/bins/3",
        json=bins_data,
        status_code=200,
    )

    res = client.get("/api/bins/3?start=2025-04-01&end=2025-04-30")
    assert res.status_code == 200
    data = res.json
    assert "stepsByZoom" in data
    assert "3" in data["stepsByZoom"]
    assert isinstance(data["stepsByZoom"]["3"], list)
    assert data["stepsByZoom"]["3"][1]["value"] == 2

def test_bins_with_filters(client, requests_mock):
    bins_data = {
        "stepsByZoom": {
            "3": [{"value": 0}, {"value": 3}, {"value": 8}]
        }
    }

    requests_mock.get(
        "https://gateway.api.globalfishingwatch.org/v3/4wings/bins/3",
        json=bins_data,
        status_code=200,
    )

    res = client.get("/api/bins/3?start=2025-04-01&end=2025-04-30&geartype=TRAWLERS&neural_vessel_type=Likely%20Fishing&matched=false")
    assert res.status_code == 200
    assert "stepsByZoom" in res.json
    assert isinstance(res.json["stepsByZoom"]["3"], list)

def test_bins_values_ascending(client, requests_mock):
    bins_data = {
        "stepsByZoom": {
            "3": [{"value": 1}, {"value": 5}, {"value": 10}]
        }
    }

    requests_mock.get(
        "https://gateway.api.globalfishingwatch.org/v3/4wings/bins/3",
        json=bins_data,
        status_code=200,
    )

    res = client.get("/api/bins/3?start=2025-04-01&end=2025-04-30")
    values = [step["value"] for step in res.json["stepsByZoom"]["3"]]
    assert values == sorted(values)

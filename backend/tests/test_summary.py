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
# 🔍 Error Handling
# --------------------------

def test_missing_all_params(client):
    res = client.get("/api/summary")
    assert res.status_code == 400
    assert "Missing" in res.json["error"]

def test_missing_start(client):
    res = client.get("/api/summary?country=France&end=2025-04-10")
    assert res.status_code == 400
    assert "Missing" in res.json["error"]

def test_missing_end(client):
    res = client.get("/api/summary?country=France&start=2025-04-01")
    assert res.status_code == 400
    assert "Missing" in res.json["error"]

def test_unknown_country(client):
    res = client.get("/api/summary?country=Narnia&start=2025-04-01&end=2025-04-10")
    assert res.status_code in (400, 404)
    assert "Invalid or ambiguous country" in res.json["error"]

def test_summary_invalid_group_by(client):
    res = client.get("/api/summary?country=France&start=2024-01-01&end=2024-01-07&group_by=INVALID")
    assert res.status_code == 400
    assert "Invalid group_by" in res.json["error"]

# --------------------------
# ✅ Summary Success Cases
# --------------------------

def test_summary_with_data_and_empty(client, requests_mock):
    # Simulate one EEZ returning data, one returning empty
    mock_json_with_summary = {
        "summary": [{"label": "TRAWLERS", "value": 42}]
    }
    mock_json_empty = {
        "summary": []
    }

    # Set up mocks for two different EEZs (calls match in order)
    requests_mock.post(
        "https://gateway.api.globalfishingwatch.org/v3/4wings/report",
        [
            {"status_code": 200, "json": mock_json_with_summary},  # EEZ 1
            {"status_code": 200, "json": mock_json_empty}          # EEZ 2
        ]
    )

    res = client.get("/api/summary?country=France&start=2025-04-01&end=2025-04-10&group_by=GEARTYPE")
    assert res.status_code == 200
    data = res.json

    assert "summaries" in data
    assert "empty_eezs" in data
    assert isinstance(data["summaries"], list)
    assert isinstance(data["empty_eezs"], list)
    assert data["summaries"][0]["summary"][0]["label"] == "TRAWLERS"

def test_summary_filters_applied(client, requests_mock):
    requests_mock.post(
        "https://gateway.api.globalfishingwatch.org/v3/4wings/report",
        status_code=200,
        json={
            "summary": [{"label": "DRIFTNETS", "value": 10}]
        }
    )

    res = client.get("/api/summary?country=France&start=2025-04-01&end=2025-04-10&geartype=DRIFTNETS")
    assert res.status_code == 200
    assert any(s["summary"][0]["label"] == "DRIFTNETS" for s in res.json["summaries"])

def test_summary_all_eezs_empty(client, requests_mock):
    requests_mock.post(
        "https://gateway.api.globalfishingwatch.org/v3/4wings/report",
        json={"summary": []},
        status_code=200,
    )

    res = client.get("/api/summary?country=France&start=2025-04-01&end=2025-04-10")
    assert res.status_code == 200
    assert res.json["summaries"] == []
    assert isinstance(res.json["empty_eezs"], list)

def test_summary_api_failure_logged_but_graceful(client, requests_mock):
    requests_mock.post(
        "https://gateway.api.globalfishingwatch.org/v3/4wings/report",
        json={"error": "Boom"},
        status_code=500
    )

    res = client.get("/api/summary?country=France&start=2025-04-01&end=2025-04-10")
    assert res.status_code == 200
    assert res.json["summaries"] == []
    assert isinstance(res.json["empty_eezs"], list)
    assert "error" in res.json["empty_eezs"][0]  # Show error was caught
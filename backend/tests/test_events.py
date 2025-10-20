import os
import sys
import pytest
from requests_mock import ANY


sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from app import app as flask_app

@pytest.fixture
def client():
    flask_app.config["TESTING"] = True
    return flask_app.test_client()

# --------------------------
# 🔍 Error Handling
# --------------------------

def test_events_missing_country(client):
    res = client.get("/api/events?start=2025-04-01&end=2025-04-10")
    assert res.status_code == 400
    assert "Missing" in res.json["error"]

def test_events_missing_start(client):
    res = client.get("/api/events?country=France&end=2025-04-10")
    assert res.status_code == 400
    assert "Missing" in res.json["error"]

def test_events_invalid_country(client):
    res = client.get("/api/events?country=Narnia&start=2025-04-01&end=2025-04-10")
    assert res.status_code in (400, 404)
    assert "Invalid or ambiguous country" in res.json["error"]

def test_events_invalid_type(client):
    res = client.get("/api/events?country=France&start=2025-04-01&end=2025-04-10&type=INVALID")
    assert res.status_code == 400
    assert "Invalid event type" in res.get_json().get("error", "")


def test_events_gfw_failure(client, requests_mock):
    requests_mock.post(
        ANY,
        status_code=500,
        json={"error": "Fail"}
    )
    res = client.get("/api/events?country=France&start=2025-04-01&end=2025-04-10&type=FISHING")
    assert res.status_code == 200
    assert "failed_eezs" in res.json
    assert isinstance(res.json["failed_eezs"], list)
    assert res.json["events"] == []


# --------------------------
# ✅ Valid Scenarios
# --------------------------
def test_events_minimal_valid(client, requests_mock):
    mock_response = {"entries": [{"id": "evt1", "type": "FISHING"}]}
    requests_mock.post(ANY, json=mock_response, status_code=200)

    res = client.get("/api/events?country=France&start=2025-04-01&end=2025-04-10&type=FISHING")
    assert res.status_code == 200
    assert "events" in res.json
    assert res.json["events"][0]["type"] == "FISHING"

def test_events_with_filters(client, requests_mock):
    mock_response = {"entries": [{"id": "evt2", "type": "GAP"}]}
    requests_mock.post(ANY, json=mock_response, status_code=200)

    res = client.get("/api/events?country=France&start=2025-04-01&end=2025-04-10&type=GAP&vessel_type=FISHING")
    assert res.status_code == 200
    assert res.json["events"][0]["type"] == "GAP"

def test_events_multiple_types(client, requests_mock):
    mock_response = {"entries": [{"id": "evtA", "type": "FISHING"}, {"id": "evtB", "type": "GAP"}]}
    requests_mock.post(ANY, json=mock_response, status_code=200)

    res = client.get("/api/events?country=France&start=2025-04-01&end=2025-04-10&type=FISHING&type=GAP")
    types = {e["type"] for e in res.json["events"]}
    assert "FISHING" in types and "GAP" in types

def test_events_empty_but_successful(client, requests_mock):
    requests_mock.post(ANY, json={"entries": []}, status_code=200)
    res = client.get("/api/events?country=France&start=2025-04-01&end=2025-04-10&type=PORT_VISIT")
    assert res.status_code == 200
    assert "events" in res.json
    assert isinstance(res.json["events"], list)

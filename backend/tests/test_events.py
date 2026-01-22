import os
import sys
import pytest
from requests_mock import ANY


sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from app import app as flask_app  # noqa: E402
from utils.gfw_client import GFWApiClient  # noqa: E402


@pytest.fixture
def client():
    """
    Provide a Flask test client configured in testing mode.
    """
    flask_app.config["TESTING"] = True
    flask_app.config["GFW_CLIENT"] = GFWApiClient("test-token", enable_cache=False)
    return flask_app.test_client()


# --------------------------
# 🔍 Error Handling Tests
# --------------------------


def test_events_missing_start_date(client):
    """
    A missing start_date should result in a 400 response with an informative error.
    """
    res = client.get("/api/events?end_date=2025-04-10&event_types=FISHING")
    assert res.status_code == 400
    assert "Missing" in res.json.get("error", "")


def test_events_missing_end_date(client):
    """
    A missing end_date should result in a 400 response with an informative error.
    """
    res = client.get("/api/events?start_date=2025-04-01&event_types=FISHING")
    assert res.status_code == 400
    assert "Missing" in res.json.get("error", "")


def test_events_invalid_event_type(client, requests_mock):
    """
    Supplying an unrecognized event type should fall back to returning all events without error.
    """
    requests_mock.post(
        ANY,
        json={"entries": []},
        status_code=200,
    )
    res = client.get(
        "/api/events?start_date=2025-04-01&end_date=2025-04-10&event_types=INVALID"
    )
    # The API should not error on unknown event types
    assert res.status_code == 200


def test_events_gfw_failure(client, requests_mock):
    """
    If the underlying events endpoint returns an error, the events API should gracefully
    return an empty list rather than raising an exception.
    """
    requests_mock.post(
        ANY,
        status_code=500,
        json={"error": "Fail"},
    )
    res = client.get(
        "/api/events?start_date=2025-04-01&end_date=2025-04-10&event_types=FISHING"
    )
    # Even when upstream fails, we should get a 200 with an empty list
    assert res.status_code == 200
    assert isinstance(res.json, list)
    assert res.json == []


# --------------------------
# ✅ Valid Scenarios
# --------------------------


def test_events_minimal_valid(client, requests_mock):
    """
    A minimal valid query should return a list of events. The underlying API call
    is mocked to return a single fishing event.
    """
    requests_mock.post(
        ANY,
        json={"entries": [{"id": "evt1", "type": "FISHING"}]},
        status_code=200,
    )
    res = client.get(
        "/api/events?start_date=2025-04-01&end_date=2025-04-10&event_types=FISHING"
    )
    assert res.status_code == 200
    assert isinstance(res.json, list)
    assert res.json[0]["type"] == "FISHING"


def test_events_with_filters(client, requests_mock):
    """
    Filters such as vessel IDs should be accepted. The mocked API returns a GAP event
    which should be propagated through the response.
    """
    requests_mock.post(
        ANY,
        json={"entries": [{"id": "evt2", "type": "GAP"}]},
        status_code=200,
    )
    res = client.get(
        "/api/events?start_date=2025-04-01&end_date=2025-04-10&event_types=GAP&vessels=123456"
    )
    assert res.status_code == 200
    assert res.json[0]["type"] == "GAP"


def test_events_multiple_types(client, requests_mock):
    """
    Multiple event_types parameters should be accepted and combined. The response
    should include events of both types.
    """
    requests_mock.post(
        ANY,
        json={"entries": [
            {"id": "evtA", "type": "FISHING"},
            {"id": "evtB", "type": "GAP"},
        ]},
        status_code=200,
    )
    res = client.get(
        "/api/events?start_date=2025-04-01&end_date=2025-04-10&event_types=FISHING&event_types=GAP"
    )
    assert res.status_code == 200
    types = {e["type"] for e in res.json}
    assert "FISHING" in types and "GAP" in types


def test_events_empty_but_successful(client, requests_mock):
    """
    When the underlying API returns no events, the response should be an empty list.
    """
    requests_mock.post(
        ANY,
        json={"entries": []},
        status_code=200,
    )
    res = client.get(
        "/api/events?start_date=2025-04-01&end_date=2025-04-10&event_types=PORT_VISIT"
    )
    assert res.status_code == 200
    assert isinstance(res.json, list)
    assert res.json == []
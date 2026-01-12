import os
import sys
import pytest

# Insert the project root into the Python path so that the Flask app can be imported
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from app import app as flask_app  # noqa: E402


@pytest.fixture
def client():
    """
    Fixture to provide a Flask test client with TESTING flag enabled.
    """
    flask_app.config["TESTING"] = True
    return flask_app.test_client()


# --------------------------
# 🔍 Error Handling Tests
# --------------------------


def test_summary_missing_all_params(client):
    """
    A request without any required parameters should return a 400 with a helpful error.
    The summary endpoint requires at least an EEZ identifier, a start date and an end date.
    """
    res = client.get("/api/summary")
    assert res.status_code == 400
    assert "Missing" in res.json.get("error", "")


def test_summary_missing_start_date(client):
    """
    When the start_date is omitted the API should respond with a 400 error.
    """
    res = client.get("/api/summary?eez_ids=123&end_date=2025-04-10")
    assert res.status_code == 400
    assert "Missing" in res.json.get("error", "")


def test_summary_missing_end_date(client):
    """
    When the end_date is omitted the API should respond with a 400 error.
    """
    res = client.get("/api/summary?eez_ids=123&start_date=2025-04-01")
    assert res.status_code == 400
    assert "Missing" in res.json.get("error", "")


def test_summary_api_failure_logged_but_graceful(client, requests_mock):
    """
    If the underlying GFW report API returns an error, the summary endpoint should
    still return a 200 OK response and surface the error inside the per‑EEZ summary.
    """
    # Mock the call to the GFW report endpoint to simulate an upstream failure.
    requests_mock.post(
        "https://gateway.api.globalfishingwatch.org/v3/4wings/report",
        json={"error": "Boom"},
        status_code=500,
    )
    res = client.get(
        "/api/summary?eez_ids=123&start_date=2025-04-01&end_date=2025-04-10"
    )
    # Even on upstream failure the endpoint should respond with a 200
    assert res.status_code == 200
    assert "summaries" in res.json
    assert isinstance(res.json["summaries"], list)
    # The first (and only) EEZ summary should contain an error entry
    assert "error" in res.json["summaries"][0]


# --------------------------
# ✅ Success Scenarios
# --------------------------


def test_summary_with_data_and_empty(client, requests_mock):
    """
    Simulate two EEZs where one returns summary data and the other returns an empty list.
    The summaries list should preserve order and include both results.
    """
    # First EEZ returns data
    mock_json_with_data = {"data": [{"label": "TRAWLERS", "value": 42}]}
    # Second EEZ returns no data
    mock_json_empty = {"data": []}
    # Configure sequential responses to the report endpoint
    requests_mock.post(
        "https://gateway.api.globalfishingwatch.org/v3/4wings/report",
        [
            {"status_code": 200, "json": mock_json_with_data},
            {"status_code": 200, "json": mock_json_empty},
        ],
    )
    res = client.get(
        "/api/summary?eez_ids=1&eez_ids=2&start_date=2025-04-01&end_date=2025-04-10&group_by=GEARTYPE"
    )
    assert res.status_code == 200
    data = res.json
    assert "summaries" in data
    assert isinstance(data["summaries"], list)
    # First entry should contain the non‑empty summary for EEZ 1
    assert data["summaries"][0]["data"][0]["label"] == "TRAWLERS"
    # Second entry should have an empty data list
    assert data["summaries"][1]["data"] == []


def test_summary_filters_applied(client, requests_mock):
    """
    When filters are provided they should be passed through to the report call.
    The returned data should reflect the filter criteria.
    """
    requests_mock.post(
        "https://gateway.api.globalfishingwatch.org/v3/4wings/report",
        status_code=200,
        json={"data": [{"label": "DRIFTNETS", "value": 10}]},
    )
    res = client.get(
        "/api/summary?eez_ids=1&start_date=2025-04-01&end_date=2025-04-10&geartype=DRIFTNETS"
    )
    assert res.status_code == 200
    # Ensure at least one summary contains the filtered geartype
    assert any(s["data"][0]["label"] == "DRIFTNETS" for s in res.json["summaries"])


def test_summary_all_eezs_empty(client, requests_mock):
    """
    If all EEZs return empty data the endpoint should still return a summaries list
    containing empty lists for each EEZ.
    """
    requests_mock.post(
        "https://gateway.api.globalfishingwatch.org/v3/4wings/report",
        json={"data": []},
        status_code=200,
    )
    res = client.get(
        "/api/summary?eez_ids=1&start_date=2025-04-01&end_date=2025-04-10"
    )
    assert res.status_code == 200
    # All summaries should have empty data lists
    for summary in res.json["summaries"]:
        assert summary["data"] == []
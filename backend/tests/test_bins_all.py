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

def test_bins_all_missing_start(client):
    res = client.get("/api/bins/all?end=2025-04-30")
    assert res.status_code == 400
    assert "Missing" in res.json["error"]

def test_bins_all_missing_end(client):
    res = client.get("/api/bins/all?start=2025-04-01")
    assert res.status_code == 400
    assert "Missing" in res.json["error"]

def test_bins_all_missing_dates(client):
    res = client.get("/api/bins/all?zooms=1,2,3")
    assert res.status_code == 400
    assert "Missing" in res.json["error"]

def test_bins_all_invalid_zooms(client):
    res = client.get("/api/bins/all?start=2025-04-01&end=2025-04-30&zooms=one,two")
    assert res.status_code == 400
    assert "Invalid zoom" in res.json["error"]

def test_bins_all_gfw_failure_for_some_zooms(client, requests_mock):
    def bin_response(z):
        return {
            "stepsByZoom": {
                str(z): [{"value": 1}, {"value": 5}]
            }
        }

    # ZOOM 2 = success, ZOOM 3 = failure
    requests_mock.get("https://gateway.api.globalfishingwatch.org/v3/4wings/bins/2", json=bin_response(2), status_code=200)
    requests_mock.get("https://gateway.api.globalfishingwatch.org/v3/4wings/bins/3", json={"error": "Fail"}, status_code=500)

    res = client.get("/api/bins/all?start=2025-04-01&end=2025-04-30&zooms=2,3")
    assert res.status_code == 200
    data = res.json["stepsByZoom"]

    assert isinstance(data["2"], list)
    assert isinstance(data["3"], dict)
    assert "error" in data["3"]

def test_bins_all_response_format(client):
    res = client.get("/api/bins/all?start=2024-01-01&end=2024-01-07&zooms=1,2")
    json_data = res.get_json()
    assert "stepsByZoom" in json_data
    assert isinstance(json_data["stepsByZoom"], dict)
    for zoom, data in json_data["stepsByZoom"].items():
        assert isinstance(zoom, str)
        assert isinstance(data, list)
        assert len(data) == 2
        assert isinstance(data[0], dict)
        assert isinstance(data[1], dict)
# --------------------------
# ✅ Valid Cases
# --------------------------

def test_bins_all_minimal_default_zooms(client, requests_mock):
    # Default zooms 1–6 expected
    for z in range(1, 7):
        requests_mock.get(
            f"https://gateway.api.globalfishingwatch.org/v3/4wings/bins/{z}",
            json={ "stepsByZoom": { str(z): [{"value": 1}, {"value": 10}] } },
            status_code=200
        )

    res = client.get("/api/bins/all?start=2025-04-01&end=2025-04-30")
    assert res.status_code == 200
    bins = res.json["stepsByZoom"]

    for z in range(1, 7):
        assert str(z) in bins
        assert isinstance(bins[str(z)], list)

def test_bins_all_custom_zooms(client, requests_mock):
    for z in [2, 4, 6]:
        requests_mock.get(
            f"https://gateway.api.globalfishingwatch.org/v3/4wings/bins/{z}",
            json={ "stepsByZoom": { str(z): [{"value": 0}, {"value": z * 5}] } },
            status_code=200
        )

    res = client.get("/api/bins/all?start=2025-04-01&end=2025-04-30&zooms=2,4,6")
    assert res.status_code == 200
    bins = res.json["stepsByZoom"]
    for z in ["2", "4", "6"]:
        assert z in bins
        assert bins[z][1]["value"] == int(z) * 5

def test_bins_all_with_filters(client, requests_mock):
    requests_mock.get(
        "https://gateway.api.globalfishingwatch.org/v3/4wings/bins/3",
        json={ "stepsByZoom": { "3": [{"value": 2}, {"value": 6}] } },
        status_code=200
    )

    res = client.get("/api/bins/all?start=2025-04-01&end=2025-04-30&zooms=3&geartype=TRAWLERS&neural_vessel_type=Likely%20Fishing")
    assert res.status_code == 200
    assert "stepsByZoom" in res.json
    assert isinstance(res.json["stepsByZoom"]["3"], list)

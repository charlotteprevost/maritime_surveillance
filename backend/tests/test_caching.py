import os
import sys
import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from app import app as flask_app
from utils.gfw_client import GFWApiClient


@pytest.fixture
def client(monkeypatch):
    # Enable cache for tests
    monkeypatch.setenv("MS_CACHE_ENABLED", "true")
    monkeypatch.setenv("MS_CACHE_FORCE_IN_TESTS", "true")
    monkeypatch.setenv("MS_CACHE_DEFAULT_TTL_SECONDS", "300")
    flask_app.config["TESTING"] = True
    flask_app.config["GFW_CLIENT"] = GFWApiClient("test-token", enable_cache=False)
    return flask_app.test_client()


def test_bins_is_cached(client, requests_mock):
    url = "https://gateway.api.globalfishingwatch.org/v3/4wings/bins/3"
    requests_mock.get(url, json={"stepsByZoom": {"3": [{"value": 1}]}} , status_code=200)

    r1 = client.get("/api/bins/3?start_date=2025-04-01&end_date=2025-04-05")
    assert r1.status_code == 200
    assert len(requests_mock.request_history) == 1

    r2 = client.get("/api/bins/3?start_date=2025-04-01&end_date=2025-04-05")
    assert r2.status_code == 200
    # Second call should not hit upstream
    assert len(requests_mock.request_history) == 1


def test_sar_ais_association_is_cached(client, requests_mock):
    # This endpoint calls /4wings/report twice (matched true/false)
    url = "https://gateway.api.globalfishingwatch.org/v3/4wings/report"
    requests_mock.post(url, json={"entries": []}, status_code=200)

    r1 = client.get("/api/detections/sar-ais-association?eez_ids=France&start_date=2025-04-01&end_date=2025-04-05")
    assert r1.status_code == 200
    first_calls = len(requests_mock.request_history)
    assert first_calls >= 2

    r2 = client.get("/api/detections/sar-ais-association?eez_ids=France&start_date=2025-04-01&end_date=2025-04-05")
    assert r2.status_code == 200
    assert len(requests_mock.request_history) == first_calls


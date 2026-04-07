"""
Live checks against the Global Fishing Watch API gateway.

These are integration tests, not mocks. They validate that the shapes we rely on
(or document as broken) still match production behavior.

Run (from `backend/`): opt in so a stray `GFW_API_TOKEN` does not hit the network on every `pytest -q`.

    export GFW_API_TOKEN="your_token"
    export GFW_API_HEALTH=1
    pytest -m gfw_health -v tests/test_gfw_api_health.py

Load token from repo-root `.env`:

    set -a && source ../.env && set +a && GFW_API_HEALTH=1 pytest -m gfw_health -v tests/test_gfw_api_health.py
"""
from __future__ import annotations

import os

import pytest
import requests

pytestmark = pytest.mark.gfw_health

BASE = "https://gateway.api.globalfishingwatch.org/v3"
REPORT = f"{BASE}/4wings/report"

# EEZ / regions aligned with GFW docs + eez_data_improved.json
EEZ_ALGERIA = 8378
EEZ_CHILE_DOC_EXAMPLE = 8465
MPA_NASCA_DOC_ID = 555745302


def _token() -> str:
    return (os.environ.get("GFW_API_TOKEN") or "").strip()


def _health_env_ok() -> tuple[bool, str]:
    flag = os.environ.get("GFW_API_HEALTH", "").strip().lower()
    if flag not in ("1", "true", "yes"):
        return False, "Set GFW_API_HEALTH=1 to run live GFW API health tests"
    if not _token():
        return False, "GFW_API_TOKEN not set"
    return True, ""


_ok, _skip_msg = _health_env_ok()
if not _ok:
    pytest.skip(_skip_msg, allow_module_level=True)


def _headers() -> dict[str, str]:
    return {
        "Authorization": f"Bearer {_token()}",
        "Content-Type": "application/json",
    }


def test_legacy_sar_report_without_aggregation_is_rejected():
    """
    Documented Example-8 shape (HOURLY + region body, no spatial-aggregation / group-by)
    currently returns 422 on :latest (resolves to sar-presence v4.x).
    If this starts returning 200 with lat/lon points again, our app can simplify.
    """
    params = {
        "spatial-resolution": "HIGH",
        "temporal-resolution": "HOURLY",
        "datasets[0]": "public-global-sar-presence:latest",
        "date-range": "2022-01-01,2022-01-06",
        "format": "JSON",
        "filters[0]": "matched='false'",
    }
    body = {"region": {"dataset": "public-eez-areas", "id": EEZ_CHILE_DOC_EXAMPLE}}
    r = requests.post(REPORT, params=params, json=body, headers=_headers(), timeout=120)
    assert r.status_code == 422
    data = r.json()
    assert data.get("statusCode") == 422
    # Error text has been stable; relax if GFW rewords it
    assert any(
        "group-by" in str(m).lower() or "sar-presence" in str(m).lower()
        for m in (data.get("messages") or [])
    )


def test_sar_presence_v4_report_succeeds_with_aggregation_and_vessel_groupby():
    """
    Working report shape for SAR on current gateway: spatial-aggregation=true,
    group-by=VESSEL_ID, HOURLY (see GFW support / our probes).
    Response rows may omit lat/lon (aggregated); we only assert HTTP + JSON envelope.
    """
    params = {
        "datasets[0]": "public-global-sar-presence:latest",
        "format": "JSON",
        "temporal-resolution": "HOURLY",
        "spatial-resolution": "HIGH",
        "spatial-aggregation": "true",
        "group-by": "VESSEL_ID",
        "date-range": "2024-06-01,2024-06-05",
        "filters[0]": "matched='false'",
    }
    body = {"region": {"dataset": "public-eez-areas", "id": EEZ_ALGERIA}}
    r = requests.post(REPORT, params=params, json=body, headers=_headers(), timeout=120)
    assert r.status_code == 200, r.text[:500]
    data = r.json()
    assert "entries" in data
    assert isinstance(data["entries"], list)
    assert len(data["entries"]) >= 1
    first = data["entries"][0]
    assert isinstance(first, dict)
    sar_key = next((k for k in first if "sar-presence" in k.lower()), None)
    assert sar_key, f"expected sar-presence dataset key in {list(first.keys())}"
    rows = first[sar_key]
    assert isinstance(rows, list)
    if rows:
        row = rows[0]
        assert isinstance(row, dict)
        assert "date" in row and "detections" in row


def test_sar_presence_matched_true_rows_include_vessel_identity_fields():
    """Matched SAR rows should carry vessel metadata (still no lat/lon in v4 grouped JSON)."""
    params = {
        "datasets[0]": "public-global-sar-presence:latest",
        "format": "JSON",
        "temporal-resolution": "HOURLY",
        "spatial-resolution": "HIGH",
        "spatial-aggregation": "true",
        "group-by": "VESSEL_ID",
        "date-range": "2024-06-01,2024-06-05",
        "filters[0]": "matched='true'",
    }
    body = {"region": {"dataset": "public-eez-areas", "id": EEZ_ALGERIA}}
    r = requests.post(REPORT, params=params, json=body, headers=_headers(), timeout=120)
    assert r.status_code == 200, r.text[:500]
    data = r.json()
    rows = data["entries"][0]
    sar_key = next(k for k in rows if "sar-presence" in k.lower())
    points = rows[sar_key]
    assert isinstance(points, list)
    if not points:
        pytest.skip("No matched SAR rows in Algeria window (data-dependent)")
    row = points[0]
    assert "vesselId" in row


def test_fishing_effort_legacy_report_without_groupby_is_rejected():
    """Doc Example 4 shape often 422 on fishing-effort v4 without group-by."""
    params = {
        "spatial-resolution": "LOW",
        "temporal-resolution": "ENTIRE",
        "spatial-aggregation": "false",
        "datasets[0]": "public-global-fishing-effort:latest",
        "date-range": "2022-05-01,2022-12-01",
        "format": "JSON",
    }
    body = {"region": {"dataset": "public-mpa-all", "id": MPA_NASCA_DOC_ID}}
    r = requests.post(REPORT, params=params, json=body, headers=_headers(), timeout=120)
    assert r.status_code == 422


def test_fishing_effort_v4_report_with_groupby_succeeds(require_gfw_token):
    params = {
        "spatial-resolution": "LOW",
        "temporal-resolution": "ENTIRE",
        "spatial-aggregation": "true",
        "group-by": "VESSEL_ID",
        "datasets[0]": "public-global-fishing-effort:latest",
        "date-range": "2022-05-01,2022-06-01",
        "format": "JSON",
    }
    body = {"region": {"dataset": "public-mpa-all", "id": MPA_NASCA_DOC_ID}}
    r = requests.post(REPORT, params=params, json=body, headers=_headers(), timeout=120)
    assert r.status_code == 200, r.text[:500]
    data = r.json()
    assert "entries" in data and data["entries"]


def test_sar_interaction_cell_endpoint_succeeds():
    """Doc Example 2: SAR interaction for a fixed global cell."""
    url = f"{BASE}/4wings/interaction/0/0/0/1049"
    params = {
        "datasets[0]": "public-global-sar-presence:latest",
        "date-range": "2019-01-01,2019-12-31",
    }
    r = requests.get(url, params=params, headers={"Authorization": f"Bearer {_token()}"}, timeout=60)
    assert r.status_code == 200, r.text[:500]
    data = r.json()
    assert "entries" in data

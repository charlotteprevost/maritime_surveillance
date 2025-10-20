# import os
# import sys
# import pytest
# import hashlib
# import json

# sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
# from app import app as flask_app
# from utils.api_helpers import get_style_cache_key

# @pytest.fixture
# def client():
#     flask_app.config["TESTING"] = True
#     return flask_app.test_client()

# # --------------------------
# # 🔍 Error Handling
# # --------------------------

# def test_generate_style_missing_payload(client):
#     res = client.post("/api/generate-style", json={})
#     assert res.status_code == 400
#     assert "Missing" in res.json["error"]

# def test_generate_style_invalid_date_format(client):
#     res = client.post("/api/generate-style", json={
#         "date_range": "2025-04-01/2025-04-30",
#         "interval": "DAY"
#     })
#     assert res.status_code == 422

# def test_generate_style_missing_dates(client):
#     res = client.post("/api/generate-style", json={
#         "interval": "MONTH"
#     })
#     assert res.status_code == 400
#     assert "Missing" in res.json["error"]

# def test_generate_style_missing_start(client):
#     res = client.post("/api/generate-style", json={
#         "end": "2025-04-30"
#     })
#     assert res.status_code == 400
#     assert "Missing" in res.json["error"]

# def test_generate_style_missing_end(client):
#     res = client.post("/api/generate-style", json={
#         "start": "2025-04-01"
#     })
#     assert res.status_code == 400
#     assert "Missing" in res.json["error"]

# def test_generate_style_invalid_interval(client):
#     res = client.post("/api/generate-style", json={
#         "start": "2024-01-01",
#         "end": "2024-01-07",
#         "interval": "INVALID"
#     })
#     assert res.status_code in (400, 200)
#     assert "Invalid interval" in res.json.get("error", "")

# def test_generate_style_invalid_color(client):
#     res = client.post("/api/generate-style", json={
#         "date_range": "2025-04-01,2025-04-30",
#         "color": "not-a-color"
#     })
#     assert res.status_code == 422

# def test_generate_style_gfw_failure(client, requests_mock):
#     requests_mock.post(
#         "https://gateway.api.globalfishingwatch.org/v3/4wings/generate-png",
#         status_code=500,
#         json={"error": "Boom"}
#     )

#     res = client.post("/api/generate-style", json={
#         "start": "2025-04-01",
#         "end": "2025-04-30"
#     })
#     assert res.status_code == 500
#     assert "error" in res.json

# # --------------------------
# # ✅ Valid Scenarios
# # --------------------------
# def test_generate_style_valid_minimal_payload(client, requests_mock):
#     mock_response = {
#         "colorRamp": {
#             "stepsByZoom": {
#                 "3": [{"color": "rgba(0,100,255,51)", "value": 5}]
#             }
#         }
#     }

#     requests_mock.post(
#         "https://gateway.api.globalfishingwatch.org/v3/4wings/generate-png",
#         json=mock_response,
#         status_code=200
#     )

#     res = client.post("/api/generate-style", json={
#         "date_range": "2025-04-01,2025-04-30"
#     })

#     assert res.status_code == 200
#     assert "style_id" in res.json
#     assert "tile_url" in res.json
#     assert res.json["colorRamp"]["stepsByZoom"]

# def test_generate_style_full_filters(client, requests_mock):
#     requests_mock.post(
#         "https://gateway.api.globalfishingwatch.org/v3/4wings/generate-png",
#         json={"colorRamp": {"stepsByZoom": {"2": [{"color": "rgba(0,0,0,255)", "value": 1}]}}},
#         status_code=200
#     )

#     payload = {
#         "date_range": "2025-04-01,2025-04-30",
#         "interval": "DAY",
#         "filters": {
#             "matched": False,
#             "neural_vessel_type": "Likely Fishing",
#             "geartype": ["driftnets", "tuna_purse_seines"],
#             "shiptype": ["carrier"],
#             "flag": ["USA", "CHN"]
#         }
#     }

#     res = client.post("/api/generate-style", json=payload)
#     assert res.status_code == 200
#     assert "tile_url" in res.json

# def test_generate_style_same_payload_same_cache_key():
#     filters = ["geartype='TRAWLERS'", "matched='false'"]
#     key1, id1 = get_style_cache_key("2025-01-01", "2025-01-31", filters, interval="DAY", color="#000000")
#     key2, id2 = get_style_cache_key("2025-01-01", "2025-01-31", filters, interval="DAY", color="#000000")
#     assert id1 == id2 and key1 == key2


# def test_generate_style_returns_style_id(client, requests_mock):
#     mock_response = {
#         "colorRamp": {
#             "stepsByZoom": {
#                 "3": [
#                     {"color": "rgba(0,100,255,51)", "value": 5},
#                     {"color": "rgba(0,100,255,102)", "value": 10}
#                 ]
#             }
#         }
#     }

#     requests_mock.post(
#         "https://gateway.api.globalfishingwatch.org/v3/4wings/generate-png",
#         json=mock_response,
#         status_code=200
#     )

#     res = client.post("/api/generate-style", json={
#         "start": "2025-04-01",
#         "end": "2025-04-30"
#     })
#     assert res.status_code == 200
#     assert "style_id" in res.json
#     assert "colorRamp" in res.json

# def test_generate_style_filters_affect_cache_key():
#     filters_a = ["geartype='TRAWLERS'", "matched='false'"]
#     filters_b = ["geartype='DRIFTNETS'", "matched='false'"]

#     key_a, id_a = get_style_cache_key("2025-04-01", "2025-04-30", filters=filters_a)
#     key_b, id_b = get_style_cache_key("2025-04-01", "2025-04-30", filters=filters_b)

#     assert id_a != id_b
#     assert hashlib.sha256(key_a.encode()).hexdigest() == id_a

# def test_generate_style_identical_inputs_same_style_id():
#     filters = ["geartype='TRAWLERS'", "matched='false'"]

#     key1, id1 = get_style_cache_key("2025-04-01", "2025-04-30", filters)
#     key2, id2 = get_style_cache_key("2025-04-01", "2025-04-30", filters)

#     assert id1 == id2
#     assert key1 == key2

# def test_generate_style_custom_color_interval(client, requests_mock):
#     mock_response = {
#         "colorRamp": {
#             "stepsByZoom": {
#                 "1": [{"color": "rgba(255,0,0,102)", "value": 100}]
#             }
#         }
#     }

#     requests_mock.post(
#         "https://gateway.api.globalfishingwatch.org/v3/4wings/generate-png",
#         json=mock_response,
#         status_code=200
#     )

#     res = client.post("/api/generate-style", json={
#         "start": "2025-04-01",
#         "end": "2025-04-30",
#         "interval": "10DAYS",
#         "color": "#ff0000"
#     })
#     assert res.status_code == 200
#     assert res.json["style_id"]
#     assert res.json["colorRamp"]["stepsByZoom"]


# def test_generate_style_valid_minimal_payload(client, requests_mock):
#     mock_response = {
#         "colorRamp": {
#             "stepsByZoom": {
#                 "3": [{"color": "rgba(0,100,255,51)", "value": 5}]
#             }
#         }
#     }

#     requests_mock.post(
#         "https://gateway.api.globalfishingwatch.org/v3/4wings/generate-png",
#         json=mock_response,
#         status_code=200
#     )

#     res = client.post("/api/generate-style", json={
#         "date_range": "2025-04-01,2025-04-30"
#     })

#     assert res.status_code == 200
#     assert "style_id" in res.json
#     assert "tile_url" in res.json
#     assert res.json["colorRamp"]["stepsByZoom"]

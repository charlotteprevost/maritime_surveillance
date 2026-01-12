#!/bin/bash
# Quick test script for API endpoints
# Usage: ./test_endpoints.sh

BASE_URL="http://localhost:5000"
EEZ_ID="8493"  # Canada
START_DATE="2024-01-01"
END_DATE="2024-01-07"

echo "🧪 Testing Dark Vessel Detection API Endpoints"
echo "=============================================="
echo ""

echo "1️⃣ Testing /api/configs"
curl -s "${BASE_URL}/api/configs" | python3 -m json.tool | head -20
echo ""
echo ""

echo "2️⃣ Testing /api/detections (Canada EEZ)"
curl -s -G "${BASE_URL}/api/detections" \
  --data-urlencode "eez_ids=[\"${EEZ_ID}\"]" \
  --data-urlencode "start_date=${START_DATE}" \
  --data-urlencode "end_date=${END_DATE}" | python3 -m json.tool | head -30
echo ""
echo ""

echo "3️⃣ Testing /api/gaps (AIS gap events)"
curl -s -G "${BASE_URL}/api/gaps" \
  --data-urlencode "eez_ids=[\"${EEZ_ID}\"]" \
  --data-urlencode "start_date=${START_DATE}" \
  --data-urlencode "end_date=${END_DATE}" \
  --data-urlencode "intentional_only=true" | python3 -m json.tool | head -30
echo ""
echo ""

echo "4️⃣ Testing /api/analytics/dark-vessels"
curl -s -G "${BASE_URL}/api/analytics/dark-vessels" \
  --data-urlencode "eez_ids=[\"${EEZ_ID}\"]" \
  --data-urlencode "start_date=${START_DATE}" \
  --data-urlencode "end_date=${END_DATE}" | python3 -m json.tool | head -30
echo ""
echo ""

echo "✅ Tests complete!"


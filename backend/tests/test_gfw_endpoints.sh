#!/bin/bash

mkdir -p output

# Load token
if [ -f "./.env" ]; then
  export $(grep -v '^#' .env | xargs)
else
  echo "❌ .env not found"
  exit 1
fi

if [ -z "$GFW_API_TOKEN" ]; then
  echo "❌ GFW_API_TOKEN not set"
  exit 1
fi

EEZ_ID=48944
START_DATE="2020-01-01"
END_DATE="2020-12-31"
AUTH="Authorization: Bearer $GFW_API_TOKEN"
BASE="https://gateway.api.globalfishingwatch.org/v3"

log_request() {
  echo -e "\n📡 $1 $2"
  if [ "$1" == "POST" ]; then
    echo "📦 Payload:"
    echo "$3" | jq .
  fi
}

run_and_save() {
  local name="$1"
  local method="$2"
  local url="$3"
  local data="$4"
  local output="output/${name}.json"

  log_request "$method" "$url" "$data"

  echo "$START_DATE" "$END_DATE" "$EEZ_ID"
  echo "$LIMIT" "$OFFSET"



  if [ "$method" == "POST" ]; then
    RESPONSE=$(curl --globoff -s -X POST "$url" -H "$AUTH" -H "Content-Type: application/json" --data-raw "$data")
  else
    RESPONSE=$(curl --globoff -s "$url" -H "$AUTH")
  fi

  echo "$RESPONSE" | tee "$output" | jq .
  echo "✅ Saved to $output"
}

# 1. /4wings/report
run_and_save "report" "POST" \
  "$BASE/4wings/report?group-by=GEARTYPE&format=JSON&temporal-resolution=ENTIRE&spatial-resolution=HIGH&datasets[0]=public-global-sar-presence:latest&date-range=$START_DATE,$END_DATE" \
  '{"region": {"dataset":"public-eez-areas","id":'"$EEZ_ID"'}}'

# 2. /4wings/bins/3
run_and_save "bins_3" "GET" \
  "$BASE/4wings/bins/3?datasets[0]=public-global-sar-presence:latest&interval=DAY&temporal-aggregation=false&num-bins=9&date-range=$START_DATE,$END_DATE" ""

# 3. /4wings/generate-png
run_and_save "generate_png" "POST" \
  "$BASE/4wings/generate-png?datasets[0]=public-global-sar-presence:latest&interval=DAY&date-range=$START_DATE,$END_DATE&color=%23361c0c" \
  "{}"

# 4. /events (FISHING + GAP, paginated)
echo -e "\n🧭 /events (paginated)"
LIMIT=100
OFFSET=0
ALL_EVENTS="[]"

while :; do
  echo "📤 Offset=$OFFSET"

  if [[ -z "$START_DATE" || -z "$END_DATE" || -z "$LIMIT" || -z "$OFFSET" || -z "$EEZ_ID" ]]; then
    echo "❌ ERROR: One or more required vars are unset."
    exit 1
  fi

  REQUEST_PAYLOAD=$(jq -n --arg start "$START_DATE" \
                         --arg end "$END_DATE" \
                         --arg region_dataset "public-eez-areas" \
                         --argjson region_id "$EEZ_ID" \
                         --argjson limit "$LIMIT" \
                         --argjson offset "$OFFSET" \
                         '{
  datasets: ["public-global-fishing-events:latest"],
  startDate: $start,
  endDate: $end,
  types: ["FISHING", "GAP"],
  region: { dataset: $region_dataset, id: $region_id },
  limit: $limit,
  offset: $offset
}')


  echo "📡 POST $BASE/events"
  echo "📦 Payload:"; echo "$REQUEST_PAYLOAD" | jq .

  RESPONSE=$(curl --globoff -s -X POST "$BASE/events" \
    -H "$AUTH" \
    -H "Content-Type: application/json" \
    --data-raw "$REQUEST_PAYLOAD")

  echo "$RESPONSE" | tee "output/events_page_${OFFSET}.json" | jq .

  if echo "$RESPONSE" | jq -e '.statusCode == 422' > /dev/null; then
    echo "❌ 422 error — stopping pagination"
    break
  fi

  ENTRIES=$(echo "$RESPONSE" | jq '.entries // []')
  COUNT=$(echo "$ENTRIES" | jq 'length')

  if [[ "$COUNT" -eq 0 ]]; then break; fi

  ALL_EVENTS=$(echo "$ALL_EVENTS $ENTRIES" | jq -s 'flatten')
  OFFSET=$((OFFSET + LIMIT))
done

echo "$ALL_EVENTS" | jq . > output/events_all.json
echo "✅ All events saved to output/events_all.json"


# 5. /vessels/search
run_and_save "vessels_search" "GET" \
  "$BASE/vessels/search?query=368045130&datasets[0]=public-global-vessel-identity:latest&includes[0]=MATCH_CRITERIA&includes[1]=OWNERSHIP&includes[2]=AUTHORIZATIONS" ""

# 6. /vessels lookup by ID
VESSEL_ID_1="3312b30d6-65b6-1bdb-6a78-3f5eb3977e58"
VESSEL_ID_2="126221ace-e3b5-f4ed-6150-394809737c55"
run_and_save "vessels_detail" "GET" \
  "$BASE/vessels?datasets[0]=public-global-vessel-identity:latest&ids[0]=$VESSEL_ID_1&ids[1]=$VESSEL_ID_2" ""

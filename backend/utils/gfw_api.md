<style>
details {
  margin-bottom: 1em;
  border: 1px solid #ccc;
  border-radius: 6px;
  padding: 0.5em;
  background-color: #f9f9f9;
}
summary {
  font-weight: bold;
  cursor: pointer;
}
</style>

## Getting Started

To use the GFW APIs:

1. [Get an API Token](https://globalfishingwatch.org/our-apis/) and keep it private.
2. Example: Basic vessel search using your token:

```bash
curl --location --request GET 'https://gateway.api.globalfishingwatch.org/v3/vessels/search?query=368045130&datasets[0]=public-global-vessel-identity:latest' \
  -H "Authorization: Bearer YOUR_API_TOKEN"
```

3. Explore each endpoint (see Table of Contents below).

---

## 🔹 Table of Contents

### 1. [General API Documentation](#general-api-documentation)

* [Key Concepts](#key-concepts-api-dataset-and-vessel-id)
  * API Dataset
  * Specific Dataset Versions
  * Vessel ID
* [Error Codes](#error-codes)
* [Response Format](#responses-format)
* [Data Caveats](#data-caveats)
  * Apparent FISHING
  * Encounter Events
  * Loitering Events
  * Port Visits
  * AIS Off (GAP) Events
  * SAR Vessel Detections
  * SAR Fixed Infrastructure
  * Insights Indicators
* [Reference Data](#reference-data)
  * Gear Types
  * Vessel Types
  * Regions (EEZs, MPAs, RFMOs)
  * Registry Codes and Sources
* [SDKs](#sdks)
* [Attribution & License](#attribution-and-citation)
* [Rate Limits](#rate-limits)
* [API Token](#api-token)
* [Release Notes](#api-release-notes)

### 2. [4Wings API (Map Visualization)](#4wings-api---map-visualization)

* `/4wings/generate-png`
* `/4wings/tile/heatmap/{z}/{x}/{y}`
* `/4wings/bins/{z}`
* `/4wings/interaction/{z}/{x}/{y}/{cells}`
* `/4wings/report` (GET & POST)
* `/4wings/last-report`
* `/4wings/stats`

### 3. [Events API](#old-events-api)

* [Introduction](#introduction)
* `/events` (GET)
* `/events` (POST)
* `/events/{eventId}`
* `/events/stats`

### 4. [Vessels API](#vessels-api)

* `/vessels/search`
  * Basic Search (e.g., MMSI, IMO)
  * Advanced Search (`where` filters)
* `/vessels`
* `/vessels/{vesselId}`

### 5. [Insights API](#insights-api)

* `/insights/vessels` (POST)\
  * Insight Types:
    * Apparent fishing in no-take MPAs
    * FISHING in unauthorized areas
    * AIS Off events
    * RFMO IUU vessel listing
    * AIS coverage

### 6. [Datasets API](#datasets-api)

* `/datasets/public-fixed-infrastructure-filtered:latest/context-layers/{z}/{x}/{y}`

# Version 3 API

We release a new version of our API (version 3) that includes several enhancements and features to improve your experience and enable even greater integration possibilities.

- Expanded Functionality: We have introduced new endpoints and extended existing functionalities to provide you with additional capabilities:
  - Get information about all vessel types and get extra information from public registries: Introducing an enhanced Vessel API! Now, besides the AIS self reported data, you can also access identity and authorization data from both public regional and national registries for vessels of all types.
  - A new Insights API with indicators related to vessels including AIS off events: that fuses historical AIS activity and authorizations into "vessel insights," designed to support risk assessment, streamline planning, and facilitate IUU fishing detection.
  - Other improvements: Elevate your experience with the newly empowered 4Wings Report API, offering advanced functionality for detailed region-specific analysis and a variety of additional encounter events, reinforcing our commitment to innovation.
- Improved Documentation: We updated the API documentation to make it more comprehensive and user-friendly, making it easier for you to understand and implement the new features effectively. We have also provided a Migration Guide and code samples to assist you during the transition.
For more details, check the release notes

### GFW Postman collection for Version 3

Download our Postman collection for Version 3 here to test some of the endpoints.
Remember to:
- Add your API Access TOKEN, you can get one from here
- Update variable `base_url` with https://gateway.api.globalfishingwatch.org/

---

## General API Documentation

### Key Concepts

#### API Datasets

Global FISHING Watch (GFW) APIs rely on named datasets that group information by purpose and version. Use the `latest` alias to always access the most up-to-date dataset version.

Example:

```bash
public-global-fishing-effort:latest
```

In the response, you will find the resolved version (e.g., `public-global-fishing-effort:v3.0`) in the `x-datasets` response header.

### 4Wings API

| Dataset                               | Description|
| ------------------------------------- | ---------- |
| `public-global-fishing-effort:latest` | AIS-based fishing effort (2012 to 96 hours ago). Filterable by `flag`, `geartype`, `vessel_id`.|
| `public-global-sar-presence:latest`   | SAR-detected vessels (2017 to 5 days ago). Filterable by `matched`, `flag`, `vessel_id`, `neural_vessel_type`, `geartype`, `shiptype`. |

### Events API

| Dataset                                   | Description                        |
| ----------------------------------------- | ---------------------------------- |
| `public-global-fishing-events:latest`     | AIS-based apparent fishing events. |
| `public-global-encounters-events:latest`  | Encounters between vessels.        |
| `public-global-loitering-events:latest`   | Loitering behavior by vessel type. |
| `public-global-port-visits-events:latest` | Port visit detections.             |
| `public-global-gaps-events:latest`        | AIS-off gaps (prototype quality).  |

### Vessels API

| Dataset                                | Description |
| -------------------------------------- | ----------- |
| `public-global-vessel-identity:latest` | Aggregated identity data from AIS and 40+ vessel registries. |

#### Vessel ID

Each vessel is identified using a unique internal ID (`vesselId`) developed by GFW. This allows linking inconsistent AIS records over time.

* In the `/vessels` API, this is in `selfReportedInfo.id`.
* This ID is used across **Events**, **Insights**, and **4Wings** APIs.

### Datasets API

| Dataset                                       | Description |
| --------------------------------------------- | ----------- |
| `public-fixed-infrastructure-filtered:latest` | SAR-based offshore infrastructure detections. |

### Versions

✅ Latest version:

* `:v3.0` → Standard across all APIs as of April 2024
* `:v3.1` → For port visits (new anchorage location method)

🟥 Deprecated:

* `:v20231026` → Legacy format from previous data pipeline

ℹ️ Legacy datasets will return `422` if queried directly. Old versions are maintained for 3 months after deprecation.


---

### Error Codes

| Code | Meaning              | Description                               |
| ---- | -------------------- | ----------------------------------------- |
| 200  | OK                   | Request succeeded                         |
| 202  | Accepted             | Request queued for processing             |
| 204  | No Content           | Successful, but no data (e.g. empty tile) |
| 401  | Unauthorized         | Invalid or missing API token              |
| 403  | Forbidden            | Token lacks required permissions          |
| 404  | Not Found            | Dataset or resource does not exist        |
| 422  | Unprocessable Entity | Invalid input, e.g. zoom > 12             |
| 429  | Too Many Requests    | Rate limit exceeded                       |
| 503  | Service Unavailable  | API under maintenance                     |

<details>
<summary>Common Error Examples</summary>

**404 – Dataset not found**

```json
{
  "statusCode": 404,
  "error": "Not Found",
  "messages": [
    {
      "title": "Not Found",
      "detail": "Dataset with id public-global-fishing-effort:latest not found"
    }
  ]
}
```

**422 – Missing field**

```json
{
  "statusCode": 422,
  "error": "Unprocessable Entity",
  "messages": [
    {
      "title": "Query",
      "detail": "Query param dataset is required"
    }
  ]
}
```

**429 – Too many reports**

```json
{
  "statusCode": 429,
  "error": "Too Many Requests",
  "messages": [
    {
      "title": "Too Many Requests",
      "detail": "You can only generate one report at the same time."
    }
  ]
}
```

</details>

---

### Responses Format

Multi-record responses follow this schema:

```json
{
  "total": 123,
  "limit": 20,
  "offset": 0,
  "nextOffset": 20,
  "metadata": {},
  "entries": [ ... ]
}
```

---

### Data Caveats

Global FISHING Watch provides **apparent** activity data inferred from AIS. All outputs should be validated in context and are subject to known limitations.

#### Apparent FISHING

* Estimated by vessel movement patterns.
* Events < 20 mins or < 0.5 km are excluded.
* Use caution when near boundaries or at high speed.

#### Encounters

* Require proximity < 500m for ≥ 2 hrs
* Both vessels must move at < 2 knots

#### Loitering

* Single vessel behavior, not paired
* Applies only to carrier/support vessels

#### Port Visits

* Derived from port entry, stop, gap, exit patterns
* Confidence levels from 2 (low) to 4 (high)

#### AIS Off (GAPs)

* GAPs ≥ 12 hrs + ≥ 50 nm from shore + high reception = possible intentional disabling
* Shorter gaps may reflect poor satellite coverage

#### Infrastructure/SAR Detections

* Close to shore or <15m vessels often missed
* False positives may occur due to radar noise

---

### Reference Data

<details>
<summary>Gear Types</summary>

* TUNA_PURSE_SEINES
* DRIFTNETS
* TROLLERS
* SET_LONGLINES
* PURSE_SEINES
* POTS_AND_TRAPS
* OTHER_FISHING
* DREDGE_FISHING
* SET_GILLNETS
* FIXED_GEAR
* TRAWLERS
* FISHING
* SEINERS
* SQUID_JIGGER
* POLE_AND_LINE
* DRIFTING_LONGLINES

</details>

<details>
<summary>Vessel Types</summary>

* carrier
* seismic_vessel
* passenger
* other
* support
* bunker
* gear
* cargo
* fishing
* discrepancy

</details>

<details>
<summary>Regions (EEZs, MPAs, RFMOs)</summary>

#### Get EEZs:

```bash
GET /v3/datasets/public-eez-areas/context-layers
```

#### Get MPAs:

```bash
GET /v3/datasets/public-mpa-all/context-layers
```

#### Get RFMOs:

```bash
GET /v3/datasets/public-rfmo/context-layers
```

</details>

---

### SDKs

<details>
<summary>R: `gfwr`</summary>

* Full API v3 support
* Structured event, effort, and vessel queries
* Migration details available in changelog

[GitHub: gfwr](https://github.com/GlobalFISHINGWatch/gfwr)

</details>

<details>
<summary>Python: `gfw-api-python-client`</summary>

* Native API v3 support
* Jupyter examples
* Built-in auth, pagination, filters
* Integrates with `pandas` / `geopandas`

[GitHub: python client](https://github.com/GlobalFISHINGWatch/gfw-api-python-client)

</details>

---

### Attribution & License

Use of the GFW API requires proper attribution. For web and reports, use:

> “Powered by Global FISHING Watch.” [globalfishingwatch.org](https://globalfishingwatch.org)

For research or citation:

> “Global FISHING Watch. 2024, updated daily. \[API Dataset Name], \[DATE RANGE]. Accessed YYYY-MM-DD at [https://globalfishingwatch.org/our-apis/.”](https://globalfishingwatch.org/our-apis/.”)

---

### Rate Limits

🟢 50,000 API calls / day
🟢 1.55 million / month
🔴 Use of your API Token in public-facing code (e.g., JavaScript frontend) is prohibited.

---


---


---

## 4Wings API - Map Visualization

**Note:** Use `--globoff` in curl when the URL contains `[]` or `{}` to avoid shell expansion.

### Supported Operations

* Visualize AIS/SAR datasets as PNG or MVT tiles
* Generate fishing/SAR reports in CSV, JSON, or TIFF formats
* Interact with gridded datasets by cell
* Retrieve report stats or results

---

### POST `/4wings/generate-png`

* Generate PNG-style heatmap tiles from selected datasets

#### HTTP Request

```http
POST https://gateway.api.globalfishingwatch.org/v3/4wings/generate-png
```

#### URL Parameters

| Name          | Description                                                       | Required | Type     |
| ------------- | ----------------------------------------------------------------- | -------- | -------- |
| `datasets[0]` | Dataset to visualize. <br> `datasets[0]=public-global-sar-presence:latest` **OR**<br> `datasets[0]=public-global-fishing-effort:latest` **OR**<br> `datasets[0]=public-global-sar-presence:latest&datasets[1]=public-global-fishing-effort:latest`| ✅       | `string` |
| `interval`    | Time resolution (`DAY`, `10DAYS`, `HOUR`, `MONTH`, `YEAR`)<br> if `interval=HOUR`, then `date-range` must be less than 20 days<br>if `interval=DAY`, then `date-range` must be less than 1 year<br>if `interval=10DAYS` then `date-range` must be less than several years depending on the dataset | ❌       | `string` |
| `filters[0]`  | Dataset filter.<br><br>**BOTH** datasets:<br>• `flag in ('{iso3}', '{iso3}', etc)`<br>• `geartype`<br>• `vessel_id` (e.g. `vessel_id='033998426-6dd0-d8d2-aedf-0756991c6027'`)<br><br>**ONLY** `sar-presence` dataset:<br>• `matched=bool`<br>• `neural_vessel_type`<br>• `shiptype`| ❌       | `string` |
| `date-range`  | Comma-separated start and end (`YYYY-MM-DD,YYYY-MM-DD`)           | ❌       | `string` |
| `color`       | Hex color for ramp <br>(default: `color=#002457`)                           | ❌       | `string` |

`geartype` values:
* tuna_purse_seines
* driftnets
* trollers
* set_longlines
* purse_seines
* pots_and_traps
* other_fishing
* dredge_fishing
* set_gillnets
* fixed_gear
* trawlers
* fishing
* seiners
* squid_jigger
* pole_and_line
* drifting_longlines

EXAMPLE: `geartype in ("tuna_purse_seines", "driftnets")`


`shiptype` values (no request examples provided):
* carrier
* seismic_vessel
* passenger
* other
* support
* bunker
* gear
* cargo
* fishing
* discrepancy

EXAMPLE: `shiptype in ("carrier", "cargo", "fishing")`


`neural_vessel_type` values (only ONE):
* "Likely non-fishing"
* "Likely Fishing"
* "Unknown"

---

#### Examples

<details>
  <summary>EXAMPLE 1: AIS FISHING Effort, 10-day interval</summary>

```bash
curl --location --request POST 'https://gateway.api.globalfishingwatch.org/v3/4wings/generate-png?interval=10DAYS&datasets[0]=public-global-fishing-effort:latest&color=%23361c0c&date-range=2020-01-01,2020-01-31' \
  -H 'Authorization: Bearer YOUR_API_TOKEN'
```

</details>

<details>
  <summary>EXAMPLE 2: Filter by gear type (driftnets + purse seines)</summary>

```bash
curl --location --request POST 'https://gateway.api.globalfishingwatch.org/v3/4wings/generate-png?interval=10DAYS&datasets[0]=public-global-fishing-effort:latest&filters[0]=geartype in ("tuna_purse_seines","driftnets")

> **Note:** Filter expressions follow SQL-style syntax (e.g. `geartype in ("tuna_purse_seines", "driftnets")`).&date-range=2020-01-01,2020-01-31' \
  -H 'Authorization: Bearer YOUR_API_TOKEN'
```

</details>

---

### GET `/4wings/tile/heatmap/{z}/{x}/{y}`

* Fetch PNG or MVT tiles using coordinates and a style string.

#### URL Parameters

| Name          | Description                          | Required | Type     |
| ------------- | ------------------------------------ | -------- | -------- |
| `z`, `x`, `y` | Tile zoom and index                  | ✅        | `number` |
| `format`      | Tile format (`PNG`, `MVT`)           | ❌        | `string` |
| `datasets[0]` | Dataset                              | ✅        | `string` |
| `interval`    | Time interval (e.g. `DAY`)           | ❌        | `string` |
| `filters[0]`  | Filters like `flag`, `matched`, etc. | ❌        | `string` |
| `date-range`  | Date range                           | ❌        | `string` |
| `style`       | Style string from `/generate-png`    | ❌        | `string` |

#### Example

<details>
  <summary>EXAMPLE: Download PNG tile with applied style</summary>

```bash
curl --location 'https://gateway.api.globalfishingwatch.org/v3/4wings/tile/heatmap/2/3/1?format=PNG&interval=10DAYS&datasets[0]=public-global-fishing-effort:latest&date-range=2020-01-01,2020-01-31&style=YOUR_STYLE_STRING' \
  -H 'Authorization: Bearer YOUR_API_TOKEN' \
  -o "tile.png"
```

</details>

---

### GET `/4wings/bins/{z}`

* Get binned value breakpoints for a given zoom level.

#### URL Parameters

| Name                   | Description                    | Required |
| ---------------------- | ------------------------------ | -------- |
| `z`                    | Zoom level                     | ✅        |
| `datasets[0]`          | Dataset                        | ✅        |
| `interval`             | Interval (`DAY`, `HOUR`, etc.) | ❌        |
| `filters[0]`           | Filter string                  | ❌        |
| `date-range`           | Date range                     | ❌        |
| `num-bins`             | Number of bins                 | ❌        |
| `temporal-aggregation` | `true/false`                   | ❌        |

#### Example

<details>
  <summary>EXAMPLE: Get bin breakpoints for zoom 1 (AIS effort)</summary>

```bash
curl --location --globoff 'https://gateway.api.globalfishingwatch.org/v3/4wings/bins/1?datasets[0]=public-global-fishing-effort:latest&interval=DAY&num-bins=9' \
  -H 'Authorization: Bearer YOUR_API_TOKEN'
```

</details>

---

### GET `/4wings/interaction/{z}/{x}/{y}/{cells}`

* Get detailed data by tile and cell index

#### URL Parameters

| Name                   | Description                         | Required        | Format | Type |
| ---------------------- | ----------------------------------- | --------------- | ------ | ---- |
| `z`                    | Zoom level (from 0 to 12)           | ✅              | number | path  |
| `x`                    | X index (lat) of the tile           | ✅              | number | path  |
| `y`                    | Y index (lon) of the tile           | ✅              | number | path  |
|`cells`                 | Indexes of cells separated by comma (e.g. 107,1,2)	|✅| string | path  |
| `datasets[0]`          | Dataset                             | ✅              | string | query |
| `filters[0]`           | Filter expression                   | ❌              | string | query |
| `date-range`           | Date range                          | ❌              | string | query |
| `limit`                | Limit number of items               | ❌              | number | query |

<details>
  <summary>EXAMPLE: Drill down on AIS cell</summary>

```bash
curl --location -g 'https://gateway.api.globalfishingwatch.org/v3/4wings/interaction/1/0/0/107?date-range=2021-01-01,2021-12-31&datasets[0]=public-global-fishing-effort:latest' \
  -H 'Authorization: Bearer YOUR_API_TOKEN'
```

</details>

---

### `GET|POST /4wings/report`

* Download aggregated reports as CSV, JSON, or TIFF

#### Required Parameters

| Name                           | Description                                | Required |
| ------------------------------ | ------------------------------------------ | -------- |
| `datasets[0]`                  | Dataset                                    | ✅        |
| `format`                       | Output format (`CSV`, `JSON`, `TIF`)       | ✅        |
| `temporal-resolution`          | `DAILY`, `MONTHLY`, `ENTIRE`               | ✅        |
| `date-range`                   | `YYYY-MM-DD,YYYY-MM-DD`                    | ✅        |
| `spatial-resolution`           | Grid: `LOW` (10°), `HIGH` (0.1°)           | ❌        |
| `group-by`                     | `FLAG`, `GEARTYPE`, `VESSEL_ID`, etc.      | ❌        |
| `region-dataset` / `region-id` | For GET requests, predefined region lookup | ❌        |

#### POST Only

| Name      | Description                        |
| --------- | ---------------------------------- |
| `geojson` | Custom GeoJSON polygon             |
| `region`  | Region object with optional buffer |

<details>
  <summary>EXAMPLE: POST report grouped by gear type in EEZ (JSON)</summary>

```bash
curl --location --globoff 'https://gateway.api.globalfishingwatch.org/v3/4wings/report?spatial-resolution=LOW&temporal-resolution=MONTHLY&group-by=GEARTYPE&datasets[0]=public-global-fishing-effort:latest&date-range=2022-01-01,2022-05-01&format=JSON' \
  -H 'Authorization: Bearer YOUR_API_TOKEN' \
  -H 'Content-Type: application/json' \
  --data-raw '{"region":{"dataset":"public-eez-areas","id":5690}}'
```

</details>

---

### GET `/4wings/last-report`

* Fetch the last completed report (within 30 min cache)

#### Response Variants

| Case               | Description                |
| ------------------ | -------------------------- |
| `status: running`  | Report is still generating |
| `status: complete` | Report returned            |
| `422`              | Missing required params    |
| `404`              | No report cached           |

---

### GET `/4wings/stats`

* Global statistics (AIS only) for effort, flags, vessel count

#### URL Parameters

| Name          | Description                       | Required |
| ------------- | --------------------------------- | -------- |
| `datasets[0]` | Dataset                           | ✅        |
| `fields`      | `FLAGS,VESSEL-IDS,ACTIVITY-HOURS` | ❌        |
| `filters[0]`  | AIS filters                       | ❌        |
| `date-range`  | `YYYY-MM-DD,YYYY-MM-DD`           | ❌        |

<details>
  <summary>EXAMPLE: Get global fishing effort summary</summary>

```bash
curl --location -g 'https://gateway.api.globalfishingwatch.org/v3/4wings/stats?datasets[0]=public-global-fishing-effort:latest&fields=FLAGS,VESSEL-IDS,ACTIVITY-HOURS&date-range=2022-01-01,2022-12-31' \
  -H 'Authorization: Bearer YOUR_API_TOKEN'
```

</details>

---


---

## Events API

The Events API allows querying for maritime events such as fishing activity, encounters, port visits, loitering, and AIS gaps (AIS turned off). You can filter by vessel, region, type, duration, confidence, and more.

---

### Supported Event Types and respective Datasets

| Type         | Description                                 | Dataset ID                               |
| ------------ | ------------------------------------------- | ---------------------------------------- |
| `FISHING`    | Apparent fishing effort                     | `public-global-fishing-events:latest`    |
| `ENCOUNTER`  | Proximity between two vessels               | `public-global-encounters-events:latest` |
| `LOITERING`  | Loitering behavior (e.g., circling/slowing) | `public-global-loitering-events:latest`  |
| `PORT_VISIT` | Visits or stops near ports                  | `public-global-port-visits-events:latest`|
| `GAP`        | AIS off periods (intentional or not)        | `public-global-gaps-events:latest`       |


---

### GET `/v3/events`

Use GET for client-side filtering (e.g., browser cache support).

#### HTTP Request

```http
GET https://gateway.api.globalfishingwatch.org/v3/events
```

#### URL Parameters ALL

| Name                        | Type      | Required | Description                                                |
| --------------------------- | --------- | -------- | ---------------------------------------------------------- |
| `limit`                     | number    | Yes      | Number of results to return                                |
| `offset`                    | number    | Yes      | Offset for pagination (where to start in the list of results).<br>Used for pagination. It starts at 0. For example, if you request limit=5 and there are 10 results in total:<br>→ offset=0 gets the first 5 (page 1)<br>→ offset=5 gets the next 5 (page 2).|
| `sort`                      | string    | No       | Sort by field with `+` or `-` prefix (e.g., `-start`)      |
| `datasets[0]`               | string    | Yes      | Dataset(s) for event type (see above)                      |
| `vessels`                   | string[]  | No       | Vessel ID(s) to filter                                     |
| `types`                     | string[]  | No       | Filter by event types (Why needed since we're querying the proper dataset??)|
| `start-date`                | string    | No       | Start date (inclusive), format `YYYY-MM-DD`                |
| `end-date`                  | string    | No       | End date (exclusive), format `YYYY-MM-DD`                  |
| `include-regions`           | boolean   | No       | Whether to include region matches (default: true)          |
| `encounter-types`           | string[]  | No       | Encounter pair types<br>Choose any number:<br>'FISHING-CARRIER', 'FISHING-SUPPORT', 'FISHING-BUNKER', 'FISHING-FISHING', 'FISHING-TANKER', 'CARRIER-BUNKER', 'BUNKER-SUPPORT'      |
| `vessel-types`              | string[]  | No       | Vessel types. Choose any number:<br>BUNKER, CARGO, DISCREPANCY, CARRIER, FISHING, GEAR, OTHER, PASSENGER, SEISMIC_VESSEL, SUPPORT|
| `gap-intentional-disabling` | string    | No       | `true` for intentional gaps, `false` for unintentional |


#### Query Parameters ONLY PORT VISITS
| Name                        | Type      | Required | Description                                                          |
| --------------------------- | --------- | -------- | -------------------------------------------------------------------- |
| `confidences`               | string[]  | No       | Port visit confidence levels: `2`, `3`, `4`  (e.g. confidences=["2","3"])|

---

#### Example

```bash
curl --location --request GET 'https://gateway.api.globalfishingwatch.org/v3/events?datasets[0]=public-global-fishing-events:latest&vessels[0]=V123&start-date=2021-01-01&end-date=2021-01-31&limit=1&offset=0' \
  -H "Authorization: Bearer YOUR_API_TOKEN"
```

---

### POST `/v3/events`

Use POST for complex queries (regions, vessel groups, filters).

#### HTTP Request

```http
POST https://gateway.api.globalfishingwatch.org/v3/events
```

#### Query Parameters

Same as `GET` (`limit`, `offset`, `sort`).

---

#### Body Parameters

| Name                      | Type      | Required | Description                                    |
| ------------------------- | --------- | -------- | ---------------------------------------------- |
| `datasets[0]`             | string\[] | Yes      | Datasets to search                             |
| `vessels`                 | string\[] | No       | Vessel ID(s)                                   |
| `types`                   | string\[] | No       | Event types (`FISHING`, `PORT_VISIT`, etc.)    |
| `startDate`               | string    | No       | Start date (`YYYY-MM-DD`)                      |
| `endDate`                 | string    | No       | End date (`YYYY-MM-DD`)                        |
| `duration`                | number    | No       | Min event duration (in minutes)                |
| `vesselTypes`             | string\[] | No       | Vessel type filter                             |
| `flags`                   | string\[] | No       | Filter by ISO3 country flags                   |
| `vesselGroups`            | string\[] | No       | Custom vessel groups                           |
| `geometry`                | object    | No       | GeoJSON polygon                                |
| `region.dataset`          | string    | No       | Region dataset ID (e.g., `public-eez-areas`)   |
| `region.id`               | string    | No       | Region ID                                      |
| `confidences`             | string\[] | No       | For port visits: confidence `2`, `3`, `4`      |
| `encounterTypes`          | string\[] | No       | Encounter pair types (e.g., `FISHING-CARRIER`) |
| `gapIntentionalDisabling` | string    | No       | `"true"` (intentional), `"false"` (not)        |

---

#### Example

```bash
curl --location --request POST 'https://gateway.api.globalfishingwatch.org/v3/events?offset=0&limit=1' \
--header 'Authorization: Bearer YOUR_API_TOKEN' \
--header 'Content-Type: application/json' \
--data-raw '{
  "datasets": ["public-global-fishing-events:latest"],
  "startDate": "2021-01-01",
  "endDate": "2021-01-31",
  "flags": ["CHN"],
  "geometry": {
    "type": "Polygon",
    "coordinates": [[[120.36, 26.72], [122.36, 26.72], [122.36, 28.32], [120.36, 28.32], [120.36, 26.72]]]
  }
}'
```

---

### GET `/v3/events/{eventId}`

Retrieve a specific event by ID.

```http
GET https://gateway.api.globalfishingwatch.org/v3/events/{eventId}
```

#### URL Parameters

| Name      | Type    | Required | Description |
| --------- | ------- | -------- | ----------- |
| `dataset` | string  | Yes      | Dataset where the event lives                 |
| `raw`     | boolean | No       | If `true`, returns full unparsed event object |

---

### POST `/v3/events/stats`

Get statistics on event frequency by flag, vessel, and time.

```http
POST https://gateway.api.globalfishingwatch.org/v3/events/stats
```

#### Body Parameters

| Name                 | Type      | Required                          | Description                  |
| -------------------- | --------- | --------------------------------- | ---------------------------- |
| `datasets[0]`        | string\[] | Yes                               | Datasets to query            |
| `vessels`            | string\[] | No                                | Vessel ID filter             |
| `types`              | string\[] | No                                | Event types                  |
| `startDate`          | string    | No                                | Start date                   |
| `endDate`            | string    | No                                | End date                     |
| `confidences`        | string\[] | No                                | Port visit confidence filter |
| `vesselGroups`       | string\[] | No                                | Group filters                |
| `geometry`           | object    | No                                | GeoJSON polygon              |
| `region.dataset`     | string    | No                                | Region dataset               |
| `region.id`          | string    | No                                | Region ID                    |
| `encounterTypes`     | string\[] | No                                | Encounter pair types         |
| `vesselTypes`        | string\[] | No                                | Vessel type filter           |
| `timeseriesInterval` | string    | Yes (if `includes = TIME_SERIES`) | `DAY`, `MONTH`, `YEAR`       |
| `includes`           | string\[] | No                                | `TOTAL_COUNT`, `TIME_SERIES` |

---

#### Response Fields

| Field        | Type      | Description                           |
| ------------ | --------- | ------------------------------------- |
| `numEvents`  | number    | Total matching events                 |
| `numFlags`   | number    | Number of distinct flags              |
| `numVessels` | number    | Number of distinct vessels            |
| `flags`      | string\[] | ISO3 codes of detected flags          |
| `timeseries` | object\[] | List of `{ date, value }` if included |

---


---

## Vessels API

Global Fishing Watch combines identity records from over 30 public vessel registries, pairing them with predictions from a convolutional neural network trained on AIS behavior patterns. The result is a harmonized vessel identity database covering 400,000+ vessels annually, including tens of thousands of industrial fishing vessels.

**Caution on identity conflicts**

When registry and inference data conflict, Global Fishing Watch assigns the vessel to the broadest matching class. If the conflict concerns whether a vessel is fishing or not, no class is assignedgfw_vessel_identity_data.

**Search and retrieve vessel identity data from AIS + public registries.**

* Supports free-text or structured queries
* Includes registry, self-reported, and inferred metadata
* Compatible with AIS, IMO, callsign, shipname, etc.

---

### `GET /vessels/search`

**Search for vessels using identifiers or filters**

Vessels may be classified in one of four ways:
- Known: registered fishing vessels from public or partner registries
- Inferred: classified via machine learning using AIS behavior
- Self-reported: vessels that identify as fishing via AIS shiptype
- Likely gear: AIS devices likely attached to gear rather than vessels (e.g., “NET MARK”)

#### Query Parameters

| Parameter      | Description                                                      | Required |
| -------------- | ---------------------------------------------------------------- | -------- |
| `datasets[0]`  | Dataset to search (e.g., `public-global-vessel-identity:latest`) | ✅        |
| `query`        | Free-text (MMSI, IMO, callsign, shipname)                        | ❌        |
| `where`        | Structured query (`imo="123456"` AND `flag='ESP'`)               | ❌        |
| `match-fields` | `SEVERAL_FIELDS`, `NO_MATCH`, `ALL`                              | ❌        |
| `includes[0]`  | Additional info: `OWNERSHIP`, `AUTHORIZATIONS`, `MATCH_CRITERIA` | ❌        |
| `limit`        | Results per page (default: 20, max: 50)                          | ❌        |
| `since`        | Token for paginated results                                      | ❌        |
| `binary`       | If `true`, return protobuf format                                | ❌        |

#### Description

Use `/vessels/search` to find a vessel ID, then query `/vessels` or `/vessels/{id}` for full details.

#### Examples

<details>
  <summary>EXAMPLE 1: Basic MMSI Search</summary>

```bash
curl --location 'https://gateway.api.globalfishingwatch.org/v3/vessels/search?query=368045130&datasets[0]=public-global-vessel-identity:latest&includes[0]=MATCH_CRITERIA&includes[1]=OWNERSHIP&includes[2]=AUTHORIZATIONS' \
  -H 'Authorization: Bearer YOUR_API_TOKEN'
```

</details>

<details>
  <summary>EXAMPLE 2: Structured Search with `where`</summary>

```bash
curl --location 'https://gateway.api.globalfishingwatch.org/v3/vessels/search?where=ssvid="775998121" AND shipname="DON TITO"&datasets[0]=public-global-vessel-identity:latest&includes[0]=MATCH_CRITERIA&includes[1]=OWNERSHIP' \
  -H 'Authorization: Bearer YOUR_API_TOKEN'
```

</details>

---

### `GET /vessels`

**Retrieve full identity details for multiple vessel IDs**

#### Query Parameters

| Parameter              | Description                                            | Required |
| ---------------------- | ------------------------------------------------------ | -------- |
| `datasets[0]`          | Dataset (e.g., `public-global-vessel-identity:latest`) | ✅        |
| `ids[0]...`            | Vessel IDs (from `/search`)                            | ✅        |
| `includes[0]`          | `POTENTIAL_RELATED_SELF_REPORTED_INFO`, etc.           | ❌        |
| `registries-info-data` | `NONE`, `DELTA`, or `ALL`                              | ❌        |
| `match-fields`         | Filter match level                                     | ❌        |
| `vessel-groups`        | Filter by group ID                                     | ❌        |
| `binary`               | Proto buffer format                                    | ❌        |

#### Example

<details>
  <summary>EXAMPLE: Fetch 3 vessels (2 fishing + 1 carrier)</summary>

```bash
curl --location 'https://gateway.api.globalfishingwatch.org/v3/vessels?datasets[0]=public-global-vessel-identity:latest&ids[0]=8c7304226-6c71-edbe-0b63-c246734b3c01&ids[1]=6583c51e3-3626-5638-866a-f47c3bc7ef7c&ids[2]=71e7da672-2451-17da-b239-857831602eca' \
  -H 'Authorization: Bearer YOUR_API_TOKEN'
```

</details>

---

### `GET /vessels/{vesselId}`

* Get full metadata for a single vessel

#### Path & Query Parameters

| Parameter              | Description                     | Required |
| ---------------------- | ------------------------------- | -------- |
| `vesselId`             | Vessel ID (from `/search`)      | ✅        |
| `dataset`              | Dataset to query                | ✅        |
| `includes[0]`          | Add self-reported or match data | ❌        |
| `registries-info-data` | `NONE`, `DELTA`, or `ALL`       | ❌        |
| `binary`               | Proto buffer                    | ❌        |
| `match-fields`         | Match filter                    | ❌        |

#### Example

<details>
  <summary>EXAMPLE: Fetch details for vessel ID `c54923...`</summary>

```bash
curl --location 'https://gateway.api.globalfishingwatch.org/v3/vessels/c54923e64-46f3-9338-9dcb-ff09724077a3?dataset=public-global-vessel-identity:latest' \
  -H 'Authorization: Bearer YOUR_API_TOKEN'
```

</details>

---

## Insights API

**Evaluate vessel behavior across AIS activity, authorizations, and public IUU lists.**

* Designed for risk assessment (IUU potential, insurance underwriting, port inspections)
* Links directly with `/events` for details on gaps, fishing, etc.

**Important Data Considerations**

Limitations exist in registry coverage across flag states. GFW identity data is more complete for large vessels (>24m) and those registered in nations with open registries. GFW continues to expand coverage and visibility into small-scale and underrepresented fleetsgfw_vessel_identity_data.

---

### `POST /v3/insights/vessels`

Retrieve high-level insights across selected vessels and time ranges.

#### Body Parameters

| Parameter     | Description                                                                        | Required |
| ------------- | ---------------------------------------------------------------------------------- | -------- |
| `includes[0]` | Types of insights: `FISHING`, `GAP`, `COVERAGE`, `VESSEL-IDENTITY-IUU-VESSEL-LIST` | ✅        |
| `startDate`   | Format: `YYYY-MM-DD`                                                               | ✅        |
| `endDate`     | Format: `YYYY-MM-DD`                                                               | ✅        |
| `vessels[0]`  | Vessel object `{ datasetId, vesselId }`                                            | ✅        |

> Note: No query parameters. All inputs go in the request body.

#### Insight Types

* `FISHING`: Apparent fishing events (including in RFMO areas or no-take MPAs)
* `GAP`: AIS off periods (a.k.a. gaps)
* `COVERAGE`: AIS transmission coverage percentage
* `VESSEL-IDENTITY-IUU-VESSEL-LIST`: RFMO-listed IUU vessels

---

#### Examples

<details>
  <summary>EXAMPLE 1: FISHING INSIGHTS (MPAs / RFMO)</summary>

```bash
curl --location 'https://gateway.api.globalfishingwatch.org/v3/insights/vessels' \
  -H 'Authorization: Bearer YOUR_API_TOKEN' \
  -H 'Content-Type: application/json' \
  --data '{
    "includes": ["FISHING"],
    "startDate": "2020-01-01",
    "endDate": "2020-12-31",
    "vessels": [
      {
        "datasetId": "public-global-vessel-identity:latest",
        "vesselId": "785101812-2127-e5d2-e8bf-7152c5259f5f"
      }
    ]
}'
```

</details>

<details>
  <summary>EXAMPLE 2: AIS OFF EVENTS (GAP)</summary>

```bash
curl --location 'https://gateway.api.globalfishingwatch.org/v3/insights/vessels' \
  -H 'Authorization: Bearer YOUR_API_TOKEN' \
  -H 'Content-Type: application/json' \
  --data '{
    "includes": ["GAP"],
    "startDate": "2022-07-11",
    "endDate": "2023-07-11",
    "vessels": [
      {
        "datasetId": "public-global-vessel-identity:latest",
        "vesselId": "2339c52c3-3a84-1603-f968-d8890f23e1ed"
      }
    ]
}'
```

</details>

<details>
  <summary>EXAMPLE 3: IUU LISTING (VESSEL-IDENTITY-IUU-VESSEL-LIST)</summary>

```bash
curl --location 'https://gateway.api.globalfishingwatch.org/v3/insights/vessels' \
  -H 'Authorization: Bearer YOUR_API_TOKEN' \
  -H 'Content-Type: application/json' \
  --data '{
    "includes": ["VESSEL-IDENTITY-IUU-VESSEL-LIST"],
    "startDate": "2020-01-01",
    "endDate": "2024-04-10",
    "vessels": [
      {
        "datasetId": "public-global-vessel-identity:latest",
        "vesselId": "2d26aa452-2d4f-4cae-2ec4-377f85e88dcb"
      }
    ]
}'
```

</details>

---


---

## Datasets API

**Access SAR-detected offshore infrastructure (oil, wind, unknown) in MVT format.**

* Based on satellite imagery and deep learning classification
* Same dataset as Paolo et al. (2024), *Nature*
* Filtered version of raw SAR data (noise removed, multi-month persistence required)

**Note**: These layers complement broader vessel classification efforts, including the identification of offshore industrial activity zones. Similar deep learning approaches are used in vessel identity classification, as explained in Global Fishing Watch’s vessel identity data white papergfw_vessel_identity_data.

---

### `GET /v3/datasets/public-fixed-infrastructure-filtered:latest/user-context-layers/{z}/{x}/{y}`

Retrieve SAR-detected offshore structures by tile coordinates in vector tile (MVT) format.

#### Path Parameters

| Parameter | Description                     | Required | Type   |
| --------- | ------------------------------- | -------- | ------ |
| `z`       | Zoom level (recommended: `0–9`) | ✅        | number |
| `x`       | Tile column (longitude)         | ✅        | number |
| `y`       | Tile row (latitude)             | ✅        | number |

#### Response Fields

| Field                  | Description                                               |
| ---------------------- | --------------------------------------------------------- |
| `structure_id`         | Unique identifier across time for each detected structure |
| `lat`, `lon`           | Geographic coordinates                                    |
| `label`                | Predicted structure type: `oil`, `wind`, `unknown`        |
| `structure_start_date` | First detection (epoch)                                   |
| `structure_end_date`   | Most recent detection (epoch)                             |
| `label_confidence`     | Label reliability: `high`, `medium`, `low`                |

---

### How is this different from the Public Map and Data Download Portal?

This endpoint returns a **filtered subset** used in the Public Map:

* Excludes data labeled as `noise` or `lake_maracaibo`
* Includes only structures:

  * Seen for ≥ 3 months
  * With predicted `noise_probability < 0.3`
* Additional filtering applied to remove known false positives in:

  * **Chile:** lat -50.6 to -41.51, lon -80.44 to -75.71
  * **Canada:** lat 50.6 to 74.02, lon -115.8 to -60.53
  * **Norway (S):** lat 64.2 to 67.43, lon 10.58 to 16.06
  * **Norway (N):** lat 67.63 to 71.19, lon 12.44 to 31.08

---

### Use Cases

**🛰 Maritime Awareness**

* Map and monitor offshore oil/wind development
* Detect hotspots of ocean industrialization

**🛥 Vessel Monitoring**

* Group vessels based on platform interaction
* Study infrastructure support vessels
* Analyze fishing proximity to structures

**📍 MPA & Spatial Planning**

* Understand overlap between industry and proposed protected areas
* Identify stakeholder conflicts during MPA designation

**🌊 Environmental Impact**

* Localize pollution events near platforms
* Differentiate between vessel and infrastructure discharges

---

### Example: Get SAR Fixed Infrastructure by Tile Coordinates

<details>
<summary>EXAMPLE 1: Download zoom 1 tile at x=0, y=1</summary>

```bash
curl --location 'https://gateway.api.globalfishingwatch.org/v3/datasets/public-fixed-infrastructure-filtered:latest/user-context-layers/1/0/1' \
  -H 'Authorization: Bearer YOUR_API_TOKEN' \
  -o 'sar_fixed_infrastructure.mvt'
```

If successful, the response will be a `.mvt` vector tile containing fixed offshore infrastructure data.

</details>

---

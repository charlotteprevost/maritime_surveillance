## /v3/4wings

### 4wings Filter Values

**`geartype` values:**

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

**EXAMPLE**: `geartype in ("tuna_purse_seines", "driftnets")`

---

**`shiptype` values:**
(no request examples provided)

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

**EXAMPLE**: `shiptype in ("carrier", "cargo", "fishing")`

---

**`neural_vessel_type` values (pick only ONE):**

* "Likely non-fishing"
* "Likely Fishing"
* "Unknown"

---

### POST `/4wings/generate-png`

**Generate PNG-style heatmap tiles from selected datasets**

#### HTTP Request

```http
POST https://gateway.api.globalfishingwatch.org/v3/4wings/generate-png
```

#### URL Parameters

| Name          | Description                                                       | Required | Type     |
| ------------- | ----------------------------------------------------------------- | -------- | -------- |
| `datasets[0]` | Dataset to visualize. <br> `datasets[0]=public-global-sar-presence:latest` **OR**<br> `datasets[0]=public-global-fishing-effort:latest` **OR**<br> `datasets[0]=public-global-sar-presence:latest&datasets[1]=public-global-fishing-effort:latest`| Yes       | `string` |
| `interval`    | Time resolution (`DAY`, `10DAYS`, `HOUR`, `MONTH`, `YEAR`)<br> if `interval=HOUR`, then `date-range` must be less than 20 days<br>if `interval=DAY`, then `date-range` must be less than 1 year<br>if `interval=10DAYS` then `date-range` must be less than several years depending on the dataset | No       | `string` |
| `filters[0]`  | Dataset filters.<br><br>**BOTH** datasets:<br>• `flag in ('{iso3}', '{iso3}', etc)`<br>• `geartype`<br>• `vessel_id` (e.g. `vessel_id='033998426-6dd0-d8d2-aedf-0756991c6027'`)<br><br>**ONLY** `sar-presence` dataset:<br>• `matched=bool`<br>• `neural_vessel_type`<br>• `shiptype`| No       | `string` |
| `date-range`  | Comma-separated start and end (`YYYY-MM-DD,YYYY-MM-DD`)           | No       | `string` |
| `color`       | Hex color for ramp <br>(default: `color=#002457`)                           | No       | `string` |

#### Examples

<details>
  <summary>EXAMPLE 1: AIS FISHING Effort, 10-day interval</summary>

```bash
curl --location --request POST 'https://gateway.api.globalfishingwatch.org/v3/4wings/generate-png?interval=10DAYS&datasets[0]=public-global-fishing-effort:latest&color=%23361c0c&date-range=2020-01-01,2020-01-31' \
  -H 'Authorization: Bearer YOUR_API_TOKEN'
```

```json
{
  "colorRamp": {
    "stepsByZoom": {
      "0": [
        {
          "color": "rgba(22,63,137,25)",
          "value": 26
        },
        {
          "color": "rgba(22,63,137,102)",
          "value": 384
        },
        {
          "color": "rgba(22,63,137,255)",
          "value": 1936
        },
        {
          "color": "rgba(22,63,137,0)",
          "value": 0
        },
        {
          "color": "rgba(22,63,137,76)",
          "value": 186
        },
        {
          "color": "rgba(22,63,137,127)",
          "value": 822
        },
        {
          "color": "rgba(22,63,137,153)",
          "value": 1114
        },
        {
          "color": "rgba(22,63,137,178)",
          "value": 1502
        },
        {
          "color": "rgba(22,63,137,51)",
          "value": 88
        }
      ],
      "1": [
        {
          "color": "rgba(22,63,137,127)",
          "value": 205
        },
        {
          "color": "rgba(22,63,137,178)",
          "value": 375
        },
        {
          "color": "rgba(22,63,137,51)",
          "value": 22
        },
        {
          "color": "rgba(22,63,137,76)",
          "value": 46
        },
        {
          "color": "rgba(22,63,137,102)",
          "value": 96
        },
        {
          "color": "rgba(22,63,137,255)",
          "value": 484
        },
        {
          "color": "rgba(22,63,137,0)",
          "value": 0
        },
        {
          "color": "rgba(22,63,137,25)",
          "value": 6
        },
        {
          "color": "rgba(22,63,137,153)",
          "value": 278
        }
      ],
      "10": [
        {
          "color": "rgba(22,63,137,255)",
          "value": 0
        }
      ],
      "11": [
        {
          "color": "rgba(22,63,137,255)",
          "value": 0
        }
      ],
      "12": [
        {
          "color": "rgba(22,63,137,255)",
          "value": 0
        }
      ],
      "2": [
        {
          "color": "rgba(22,63,137,25)",
          "value": 1
        },
        {
          "color": "rgba(22,63,137,51)",
          "value": 5
        },
        {
          "color": "rgba(22,63,137,76)",
          "value": 11
        },
        {
          "color": "rgba(22,63,137,153)",
          "value": 69
        },
        {
          "color": "rgba(22,63,137,178)",
          "value": 93
        },
        {
          "color": "rgba(22,63,137,255)",
          "value": 121
        },
        {
          "color": "rgba(22,63,137,0)",
          "value": 0
        },
        {
          "color": "rgba(22,63,137,102)",
          "value": 24
        },
        {
          "color": "rgba(22,63,137,127)",
          "value": 51
        }
      ],
      "3": [
        {
          "color": "rgba(22,63,137,178)",
          "value": 23
        },
        {
          "color": "rgba(22,63,137,255)",
          "value": 30
        },
        {
          "color": "rgba(22,63,137,25)",
          "value": 0
        },
        {
          "color": "rgba(22,63,137,51)",
          "value": 1
        },
        {
          "color": "rgba(22,63,137,76)",
          "value": 2
        },
        {
          "color": "rgba(22,63,137,102)",
          "value": 6
        },
        {
          "color": "rgba(22,63,137,127)",
          "value": 12
        },
        {
          "color": "rgba(22,63,137,153)",
          "value": 17
        }
      ],
      "4": [
        {
          "color": "rgba(22,63,137,102)",
          "value": 1
        },
        {
          "color": "rgba(22,63,137,127)",
          "value": 3
        },
        {
          "color": "rgba(22,63,137,153)",
          "value": 4
        },
        {
          "color": "rgba(22,63,137,178)",
          "value": 5
        },
        {
          "color": "rgba(22,63,137,255)",
          "value": 7
        },
        {
          "color": "rgba(22,63,137,76)",
          "value": 0
        }
      ],
      "5": [
        {
          "color": "rgba(22,63,137,127)",
          "value": 0
        },
        {
          "color": "rgba(22,63,137,255)",
          "value": 1
        }
      ],
      "6": [
        {
          "color": "rgba(22,63,137,255)",
          "value": 0
        }
      ],
      "7": [
        {
          "color": "rgba(22,63,137,255)",
          "value": 0
        }
      ],
      "8": [
        {
          "color": "rgba(22,63,137,255)",
          "value": 0
        }
      ],
      "9": [
        {
          "color": "rgba(22,63,137,255)",
          "value": 0
        }
      ]
    }
  },
  "url": "https://gateway.api.globalfishingwatch.org/v3/4wings/tile/heatmap/{z}/{x}/{y}?format=PNG&interval=10DAYS&datasets[0]=public-global-fishing-effort:latest&filters[0]=geartype in (\"tuna_purse_seines\",\"driftnets\")&date-range=2020-01-01,2020-01-31&style=eyJjb2xvciI6WzIyLDYzLDEzN10sInJhbXAiOlswLDI2LjE2NjM4ODg4ODg4ODg5Myw4OC4yMjgwNTU1NTU1NTU2MSwxODYuMzI1ODMzMzMzMzMzMywzODQuODIwNTU1NTU1NTU1Niw4MjIuOTk1NTU1NTU1NTU0OCwxMTE0LjMyNDcyMjIyMjIyMjEsMTUwMi4wNjA4MzMzMzMzMzMyLDE5MzYuNzA0MTY2NjY2NjY1XX0="
}
```

</details>

<details>
  <summary>EXAMPLE 2: Filter by gear type (driftnets + purse seines)</summary>

```bash
curl --location --request POST 'https://gateway.api.globalfishingwatch.org/v3/4wings/generate-png?interval=10DAYS&datasets[0]=public-global-fishing-effort:latest&filters[0]=geartype in ("tuna_purse_seines","driftnets")

> **Note:** Filter expressions follow SQL-style syntax (e.g. `geartype in ("tuna_purse_seines", "driftnets")`).&date-range=2020-01-01,2020-01-31' \
  -H 'Authorization: Bearer YOUR_API_TOKEN'
```

```json
{
  "colorRamp": {
    "stepsByZoom": {
      "0": [
        {
          "color": "rgba(22,63,137,0)",
          "value": 0
        },
        {
          "color": "rgba(22,63,137,102)",
          "value": 384
        },
        {
          "color": "rgba(22,63,137,178)",
          "value": 1502
        },
        {
          "color": "rgba(22,63,137,255)",
          "value": 1944
        },
        {
          "color": "rgba(22,63,137,25)",
          "value": 26
        },
        {
          "color": "rgba(22,63,137,51)",
          "value": 88
        },
        {
          "color": "rgba(22,63,137,76)",
          "value": 186
        },
        {
          "color": "rgba(22,63,137,127)",
          "value": 677
        },
        {
          "color": "rgba(22,63,137,153)",
          "value": 1047
        }
      ],
      "1": [
        {
          "color": "rgba(22,63,137,0)",
          "value": 0
        },
        {
          "color": "rgba(22,63,137,51)",
          "value": 22
        },
        {
          "color": "rgba(22,63,137,102)",
          "value": 96
        },
        {
          "color": "rgba(22,63,137,153)",
          "value": 261
        },
        {
          "color": "rgba(22,63,137,255)",
          "value": 486
        },
        {
          "color": "rgba(22,63,137,25)",
          "value": 6
        },
        {
          "color": "rgba(22,63,137,76)",
          "value": 46
        },
        {
          "color": "rgba(22,63,137,127)",
          "value": 169
        },
        {
          "color": "rgba(22,63,137,178)",
          "value": 375
        }
      ],
      "10": [
        {
          "color": "rgba(22,63,137,255)",
          "value": 0
        }
      ],
      "11": [
        {
          "color": "rgba(22,63,137,255)",
          "value": 0
        }
      ],
      "12": [
        {
          "color": "rgba(22,63,137,255)",
          "value": 0
        }
      ],
      "2": [
        {
          "color": "rgba(22,63,137,255)",
          "value": 121
        },
        {
          "color": "rgba(22,63,137,25)",
          "value": 1
        },
        {
          "color": "rgba(22,63,137,76)",
          "value": 11
        },
        {
          "color": "rgba(22,63,137,102)",
          "value": 24
        },
        {
          "color": "rgba(22,63,137,127)",
          "value": 42
        },
        {
          "color": "rgba(22,63,137,178)",
          "value": 93
        },
        {
          "color": "rgba(22,63,137,0)",
          "value": 0
        },
        {
          "color": "rgba(22,63,137,51)",
          "value": 5
        },
        {
          "color": "rgba(22,63,137,153)",
          "value": 65
        }
      ],
      "3": [
        {
          "color": "rgba(22,63,137,102)",
          "value": 6
        },
        {
          "color": "rgba(22,63,137,127)",
          "value": 10
        },
        {
          "color": "rgba(22,63,137,153)",
          "value": 16
        },
        {
          "color": "rgba(22,63,137,178)",
          "value": 23
        },
        {
          "color": "rgba(22,63,137,255)",
          "value": 30
        },
        {
          "color": "rgba(22,63,137,25)",
          "value": 0
        },
        {
          "color": "rgba(22,63,137,51)",
          "value": 1
        },
        {
          "color": "rgba(22,63,137,76)",
          "value": 2
        }
      ],
      "4": [
        {
          "color": "rgba(22,63,137,102)",
          "value": 1
        },
        {
          "color": "rgba(22,63,137,127)",
          "value": 2
        },
        {
          "color": "rgba(22,63,137,153)",
          "value": 4
        },
        {
          "color": "rgba(22,63,137,178)",
          "value": 5
        },
        {
          "color": "rgba(22,63,137,255)",
          "value": 7
        },
        {
          "color": "rgba(22,63,137,76)",
          "value": 0
        }
      ],
      "5": [
        {
          "color": "rgba(22,63,137,127)",
          "value": 0
        },
        {
          "color": "rgba(22,63,137,255)",
          "value": 1
        }
      ],
      "6": [
        {
          "color": "rgba(22,63,137,255)",
          "value": 0
        }
      ],
      "7": [
        {
          "color": "rgba(22,63,137,255)",
          "value": 0
        }
      ],
      "8": [
        {
          "color": "rgba(22,63,137,255)",
          "value": 0
        }
      ],
      "9": [
        {
          "color": "rgba(22,63,137,255)",
          "value": 0
        }
      ]
    }
  }
}
```

</details>

---

### GET `/4wings/tile/heatmap/{z}/{x}/{y}`

**Fetch PNG or MVT tiles using coordinates and a style string**

#### URL Parameters

| Name                   | Description                         | Required        | Format | Type |
| ---------------------- | ----------------------------------- | --------------- | ------ | ---- |
| `z`                    | Zoom level (from 0 to 12)           | Yes              | `number` | path  |
| `x`                    | X index (lat) of the tile           | Yes              | `number` | path  |
| `y`                    | Y index (lon) of the tile           | Yes              | `number` | path  |
| `temporal-aggregation` | Aggregates the data temporaly in the tile.| No      | boolean  | query |
| `interval`    | Time resolution (`DAY`, `10DAYS`, `HOUR`, `MONTH`, `YEAR`)<br> if `interval=HOUR`, then `date-range` must be less than 20 days<br>if `interval=DAY`, then `date-range` must be less than 1 year<br>if `interval=10DAYS` then `date-range` must be less than several years depending on the dataset | No       | `string` | query |
| `datasets[0]` | Dataset to visualize. <br> `datasets[0]=public-global-sar-presence:latest` **OR**<br> `datasets[0]=public-global-fishing-effort:latest` **OR**<br> `datasets[0]=public-global-sar-presence:latest&datasets[1]=public-global-fishing-effort:latest`| Yes       | `string` | query |
| `filters[0]`  | Dataset filters.<br><br>**BOTH** datasets:<br>• `flag in ('{iso3}', '{iso3}', etc)`<br>• `geartype`<br>• `vessel_id` (e.g. `vessel_id='033998426-6dd0-d8d2-aedf-0756991c6027'`)<br><br>**ONLY** `sar-presence` dataset:<br>• `matched=bool`<br>• `neural_vessel_type`<br>• `shiptype`| No       | `string` | query |
| `date-range`  | Comma-separated start and end (`YYYY-MM-DD,YYYY-MM-DD`)        | No | `string` | query |
| `format`      | Tile format (`PNG`, `MVT`)           | No        | `string`  | query |
| `style`       | Style string from `/generate-png`    | No / Yes for `PNG`      | `string`  | query |

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

### GET `/4wings/interaction/{z}/{x}/{y}/{cells}`

**Get detailed data by tile and cell index**

#### Path & Query Parameters

| Name                   | Description                         | Required        | Format | Type |
| ---------------------- | ----------------------------------- | --------------- | ------ | ---- |
| `z`                    | Zoom level (from 0 to 12)           | Yes              | `number` | path  |
| `x`                    | X index (lat) of the tile           | Yes              | `number` | path  |
| `y`                    | Y index (lon) of the tile           | Yes              | `number` | path  |
|`cells`                 | Indexes of `MVT` cells separated by comma (e.g. 107,1,2)	| Yes | `string` | path  |
| `limit`                | Limit number of items to return     | No              | `number` | query |
| `datasets[0]` | Dataset to visualize. <br> `datasets[0]=public-global-sar-presence:latest` **OR**<br> `datasets[0]=public-global-fishing-effort:latest` **OR**<br> `datasets[0]=public-global-sar-presence:latest&datasets[1]=public-global-fishing-effort:latest`| Yes       | `string` | query |
| `filters[0]`  | Dataset filters.<br><br>**BOTH** datasets:<br>• `flag in ('{iso3}', '{iso3}', etc)`<br>• `geartype`<br>• `vessel_id` (e.g. `vessel_id='033998426-6dd0-d8d2-aedf-0756991c6027'`)<br><br>**ONLY** `sar-presence` dataset:<br>• `matched=bool`<br>• `neural_vessel_type`<br>• `shiptype`| No       | `string` | query |
| `date-range`  | Comma-separated start and end (`YYYY-MM-DD,YYYY-MM-DD`)        | No | `string` | query |

<details>
  <summary>EXAMPLE: Drill down on AIS cell</summary>

```bash
curl --location -g 'https://gateway.api.globalfishingwatch.org/v3/4wings/interaction/1/0/0/107?date-range=2021-01-01,2021-12-31&datasets[0]=public-global-fishing-effort:latest' \
  -H 'Authorization: Bearer YOUR_API_TOKEN'
```

```json
{
  "total": 1,
  "limit": null,
  "offset": null,
  "nextOffset": null,
  "metadata": {},
  "entries": [
    [
      {
        "hours": 11.455833333333334,
        "id": "f2134364c-c3d5-8ee9-ddd4-5511c0500a50"
      },
      {
        "hours": 9.895,
        "id": "f042d0bcf-fe96-cad5-5833-36b4aff2e87a"
      },
      {
        "hours": 12.617222222222221,
        "id": "e2d464a53-35ed-f059-c7e2-1ac76e12c9cc"
      },
      {
        "hours": 1.6769444444444446,
        "id": "daa9e5914-4d3c-6242-6648-b1adbc93305b"
      },
      {
        "hours": 1.238611111111111,
        "id": "c88e21112-2a09-4d56-196e-ff9cb26f76c9"
      },
      {
        "hours": 0.053055555555555564,
        "id": "b8de3c8e8-84f0-ba2f-528c-ff877e2d0e9e"
      },
      {
        "hours": 3.5319444444444446,
        "id": "b5d3439b6-6d19-5385-9d6b-08a0dfd60fa7"
      },
      {
        "hours": 18.993333333333332,
        "id": "ab75d8a33-3f93-62eb-0c86-38d8c742eff3"
      },
      {
        "hours": 9.597777777777777,
        "id": "a812d4320-0608-5ad0-1929-d5206eda123a"
      },
      {
        "hours": 34.2575,
        "id": "9eab37595-5bf1-471e-2e38-c070ebb00a7a"
      },
      {
        "hours": 47.11222222222222,
        "id": "9cf14ce31-144f-dda7-ded3-743bec9e41db"
      },
      {
        "hours": 9.228888888888891,
        "id": "9aed1677e-ef23-f541-58eb-8d755d410df4"
      },
      {
        "hours": 5.095000000000001,
        "id": "70a3ff9ca-ab64-12b2-6446-34cdf14000c6"
      },
      {
        "hours": 5.3925,
        "id": "6b3129a20-009f-1741-5877-a714ea11cf2b"
      },
      {
        "hours": 16.631666666666664,
        "id": "68ab5e789-96a1-fd61-016c-92bd413a9682"
      },
      {
        "hours": 10.718055555555555,
        "id": "65aaba596-62eb-49af-910d-f7d9d47a2d06"
      },
      {
        "hours": 9.872222222222222,
        "id": "3f7c46fe4-45f8-0685-a7e5-60d531c7c352"
      },
      {
        "hours": 8.126666666666667,
        "id": "2ab8c04ff-f0e3-a3f1-7ef4-2428604174e0"
      },
      {
        "hours": 38.58861111111111,
        "id": "1abad9a58-8758-383e-8c58-6c8029ecaa44"
      },
      {
        "hours": 10.016388888888889,
        "id": "184b291b6-619c-748c-1f32-5fe46616d0dc"
      },
      {
        "hours": 0.11166666666666666,
        "id": "1738bc096-6373-5ae6-8bd0-dd31ecf6c0eb"
      },
      {
        "hours": 2.338888888888889,
        "id": "098ac6ed6-65a9-260b-fb84-8c932eb977ae"
      },
      {
        "hours": 47.81805555555555,
        "id": "050743514-4618-79b3-8643-96ada9281517"
      },
      {
        "hours": 17.753055555555555,
        "id": "04b95cb83-31d8-06e7-0845-8691696643f5"
      }
    ]
  ]
}
```

</details>

---
---

## /v3/vessels

### GET `/vessels/{vesselId}`

**Get full metadata for a single vessel**

#### Path & Query Parameters

| Parameter              | Description                     | Required | Format | Type |
| ---------------------- | ------------------------------- | -------- | -------- | ------ |
| `vesselId`             | Unique vessel ID (from `/interaction`) | Yes | string | path |
| `datasets[0]`          | `public-global-vessel-identity:latest` | Yes | string | query |
| `includes[0]`    ???   | Add extra information to response      | No | array    | query |
| `registries-info-data` | How much registry info is included in the response:<br>NONE: no registry info (default)<br>DELTA: only changes over time<br>ALL: full registry data<br>Example: `DELTA` | No | enum: `NONE`, `DELTA`, `ALL` | query |
| `binary`               | If true, returns response in binary format (Protocol Buffers). Improves performance but needs decoding.<br>Default: `false`  | No | boolean | query |
| `match-fields`         | Match filter                    | No | array | query |
| match-fields | Filter by match level for registry matching. Options:<br>• SEVERAL_FIELDS<br>• NO_MATCH<br>• ALL<br>Example:<br>['SEVERAL_FIELDS', 'NO_MATCH'] | No | array | query |
#### Example

<details>
  <summary>EXAMPLE: Fetch details for vessel ID `c54923...`</summary>

```bash
curl --location 'https://gateway.api.globalfishingwatch.org/v3/vessels/c54923e64-46f3-9338-9dcb-ff09724077a3?dataset=public-global-vessel-identity:latest' \
  -H 'Authorization: Bearer YOUR_API_TOKEN'
```

```json
{
  "dataset": "public-global-vessel-identity:v20230623",
  "registryInfoTotalRecords": 0,
  "registryInfo": [],
  "registryOwners": [],
  "registryAuthorizations": [],
  "selfReportedInfo": [
    {
      "id": "c54923e64-46f3-9338-9dcb-ff09724077a3",
      "ssvid": "775998121",
      "shipname": "DON TITO",
      "nShipname": "DONTITO",
      "flag": "VEN",
      "callsign": "YD23136",
      "imo": null,
      "geartype": null,
      "shiptype": "OTHER_NON_FISHING",
      "messagesCounter": 1103,
      "positionsCounter": 430,
      "shiptypesByYear": [
        {
          "shiptype": "OTHER_NON_FISHING",
          "years": [2021, 2022, 2023]
        }
      ],
      "sourceCode": ["AIS"],
      "matchFields": "NO_MATCH",
      "transmissionDateFrom": "2021-08-06T10:49:26Z",
      "transmissionDateTo": "2023-09-21T14:52:16Z"
    }
  ]
}
```
</details>


---
---

## /v3/insights

### POST `/v3/insights/vessels`

**Retrieve high-level insights across selected vessels and time ranges**

> Note: **No URL query parameters.** All inputs go in the request body.

#### Body Parameters

| Parameter     | Description | Required | Type |
| ------------- | ----------- | -------- | ---- |
| `"includes"` | Types of insights:<br>`"FISHING"`, `"GAP"`, `"COVERAGE"`, `"VESSEL-IDENTITY-IUU-VESSEL-LIST"`| Yes| body |
| `"startDate"`   | `"YYYY-MM-DD"`| Yes| body |
| `"endDate"`     | `"YYYY-MM-DD"`| Yes| body |
| `"vessels"`  | Vessel object `{ "datasetId"="string", "vesselId"="string" }`| Yes| body |


#### Insight Types

* `FISHING`: Apparent fishing events (including in RFMO areas or no-take MPAs)
* `GAP`: AIS off periods (a.k.a. gaps)
* `COVERAGE`: AIS transmission coverage percentage
* `VESSEL-IDENTITY-IUU-VESSEL-LIST`: RFMO-listed IUU vessels


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

```json
{
    "period": {
        "startDate": "2020-01-01",
        "endDate": "2020-12-31"
    },
    "apparentFishing": {
        "datasets": [
            "public-global-fishing-events:v3.0"
        ],
        "historicalCounters": {
            "events": 2546,
            "eventsInRFMOWithoutKnownAuthorization": 0,
            "eventsInNoTakeMPAs": 18
        },
        "periodSelectedCounters": {
            "events": 523,
            "eventsInRFMOWithoutKnownAuthorization": 0,
            "eventsInNoTakeMPAs": 18
        },
        "eventsInRfmoWithoutKnownAuthorization": [],
        "eventsInNoTakeMpas": [
            "9864ab75303cfc44fe4542fa755987e8",
            "77d84fa537395a6c29fc8509e337e82b",
            "9f053082b086a5c66fd87d54fb456bb9",
            "20db28e5e09ce91c347a54637460fb19",
            "2a937121e418ef38889fc9395461ee68",
            "b920508f737e8b9c678e3fef74a6799a",
            "e62a86cc34b5eba3826a02ee1fa6f846",
            "1ce80b9f862d28c2f470561021eac8bb",
            "a530632e0c5221a931520c60593b33bf",
            "031c029d9ab3ab2b4f7151df2b0a13c7",
            "d24003cbd7bf9b4cddb174a967136635",
            "9f7972a6b56d99f60d0586cf4545cabf",
            "8ed2cc511fb59e96e5549d902a65e176",
            "97bbac02d35fa9e2a3dc196502ef47b8",
            "29a91f15fd844bd0fc344d47d3490a9d",
            "877f42def050b3784e4a9d1387503220",
            "11d484a2d0e397fcf5a8a5a9cb9124a8",
            "af534af9aec9149add9f66265296de7d"
        ]
    }
}
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

```json
{
    "period": {
        "startDate": "2022-07-11",
        "endDate": "2023-07-11"
    },
    "gap": {
        "datasets": [
            "public-global-gaps-events:v3.0"
        ],
        "historicalCounters": {
            "events": 1,
            "eventsGapOff": 1
        },
        "periodSelectedCounters": {
            "events": 1,
            "eventsGapOff": 1
        },
        "aisOff": [
            "9ce75aa2a483a06f41155132b83dc744"
        ]
    }
}
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

```json
{
    "period": {
        "startDate": "2020-01-01",
        "endDate": "2024-04-10"
    },
    "vesselIdentity": {
        "datasets": [
            "public-global-vessel-identity:v3.0"
        ],
        "iuuVesselList": {
            "valuesInThePeriod": [
                {
                    "from": "2020-01-01T00:00:00Z",
                    "to": "2024-03-01T00:00:00Z"
                }
            ],
            "totalTimesListed": 1,
            "totalTimesListedInThePeriod": 1
        }
    }
}
```

</details>

---

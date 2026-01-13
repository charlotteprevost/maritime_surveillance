# Maritime Surveillance - Internal Documentation

**Private Notes and Development Documentation**

This document contains internal development notes, feature audits, API analysis, debugging guides, and technical implementation details. This is NOT for public consumption.

---

## Table of Contents

1. [Application Architecture Flowchart](#application-architecture-flowchart)
2. [Feature Audit](#feature-audit)
3. [Project Kanban](#project-kanban)
4. [GFW API Enhancements](#gfw-api-enhancements)
5. [GFW API Data Questions](#gfw-api-data-questions)
6. [Data Clarification](#data-clarification)
7. [Dark Trade Risk Thresholds](#dark-trade-risk-thresholds)
8. [GFW API Utilization Audit](#gfw-api-utilization-audit)
9. [Cluster Debugging Guide](#cluster-debugging-guide)
10. [Segmentation Fault Fix](#segmentation-fault-fix)
11. [Caching and Deployment](#caching-and-deployment)
12. [GFW API Data Summary](#gfw-api-data-summary)
13. [Project Handoff Details](#project-handoff-details)

---

## Application Architecture Flowchart

```mermaid
flowchart TD
    Start([User Opens Frontend]) --> Init[Frontend Initialization]
    Init --> FetchConfig[Fetch Configs & EEZ Data]
    FetchConfig --> BuildUI[Build EEZ Select & UI]
    BuildUI --> InitMap[Initialize Leaflet Map]
    InitMap --> WaitInput[Wait for User Input]
    
    WaitInput --> UserSelect[User Selects EEZ + Dates]
    UserSelect --> ApplyFilters[User Clicks Apply Filters]
    
    ApplyFilters --> BuildRequest[Build Batch API Request]
    BuildRequest --> SetFeatureFlags[Set Feature Flags: include_clusters, include_routes, include_stats]
    SetFeatureFlags --> SendRequest[Send to Backend API]
    
    SendRequest --> FlaskApp[Flask App Receives Request]
    FlaskApp --> RouteHandler[Route Handler]
    
    RouteHandler --> DetectionsRoute{Which Endpoint?}
    
    DetectionsRoute -->|/api/detections (Batch)| DarkVesselService[DarkVesselService.get_dark_vessels]
    DetectionsRoute -->|/api/analytics| AnalyticsRoute[Analytics Route Handler]
    DetectionsRoute -->|/api/vessels| VesselsRoute[Vessels Route Handler]
    DetectionsRoute -->|/api/insights| InsightsRoute[Insights Route Handler]
    DetectionsRoute -->|/api/configs| ConfigsRoute[Configs Route Handler]
    
    DarkVesselService --> DateChunking{Date Range > 30 days?}
    DateChunking -->|Yes| SplitDates[Split into 30-day chunks]
    DateChunking -->|No| UseDates[Use date range as-is]
    SplitDates --> UseDates
    
    UseDates --> GFWClient[GFWApiClient]
    GFWClient --> CheckCache{Cache Available?}
    CheckCache -->|Yes| CachedSession[Use CachedSession]
    CheckCache -->|No| RegularSession[Use Regular Session]
    
    CachedSession --> GFWAPI[GFW API v3]
    RegularSession --> GFWAPI
    
    GFWAPI --> SARData[SAR Detections Data]
    
    SARData --> ProcessSAR[Process SAR Detections]
    
    ProcessSAR --> CheckClusters{include_clusters?}
    CheckClusters -->|Yes| ComputeClusters[Compute Proximity Clusters (BFS)]
    CheckClusters -->|No| CheckRoutes
    ComputeClusters --> ClusterData[Cluster Data with Risk Levels]
    
    ProcessSAR --> CheckRoutes{include_routes?}
    CheckRoutes -->|Yes| ComputeRoutes[Compute Route Predictions]
    CheckRoutes -->|No| CheckStats
    ComputeRoutes --> RouteData[Predicted Route Data]
    
    ProcessSAR --> CheckStats{include_stats?}
    CheckStats -->|Yes| ComputeStats[Compute Basic Statistics]
    CheckStats -->|No| BuildResponse
    ComputeStats --> StatsData[Statistics Data]
    
    ClusterData --> BuildResponse[Build Batch JSON Response]
    RouteData --> BuildResponse
    StatsData --> BuildResponse
    ProcessSAR --> BuildResponse
    
    BuildResponse --> ReturnJSON[Return JSON Response]
    
    ReturnJSON --> FrontendReceive[Frontend Receives Response]
    FrontendReceive --> UpdateMap[Update Map with Data]
    
    UpdateMap --> AddSARMarkers[Add SAR Markers to Cluster Group]
    UpdateMap --> CheckDisplayClusters{Display Clusters?}
    CheckDisplayClusters -->|Yes| DisplayClusters[Display Cluster Circles]
    CheckDisplayClusters -->|No| CheckDisplayRoutes
    DisplayClusters --> CheckDisplayRoutes
    
    UpdateMap --> CheckDisplayRoutes{Display Routes?}
    CheckDisplayRoutes -->|Yes| DisplayRoutes[Display Route Polylines]
    CheckDisplayRoutes -->|No| UpdateStats
    DisplayRoutes --> UpdateStats
    
    AddSARMarkers --> UpdateStats[Update Analytics Dashboard]
    
    UpdateStats --> ShowStats[Display: SAR Count, EEZ Count, Total Clusters, High Risk Clusters, Medium Risk Clusters]
    ShowStats --> ShowSuccess[Show Success Message]
    ShowSuccess --> WaitInput
    
    AnalyticsRoute --> GFWClient
    VesselsRoute --> GFWClient
    InsightsRoute --> GFWClient
    ConfigsRoute --> ReturnConfig[Return Config Data]
    ReturnConfig --> FrontendReceive
    
    style Start fill:#e1f5ff
    style GFWAPI fill:#fff4e6
    style DarkVesselService fill:#e8f5e9
    style ComputeClusters fill:#2196f3
    style ComputeRoutes fill:#9c27b0
    style BuildResponse fill:#4caf50
    style UpdateMap fill:#f3e5f5
    style UpdateStats fill:#fff9c4
```

### Architecture Components

- **Frontend Layer** (`frontend/`):
  - `main.js`: Map initialization, event handling, marker display
  - `utils.js`: EEZ selection, date validation, API helpers
  - `index.html`: UI structure
  - `style.css`: Styling

- **Backend Layer** (`backend/`):
  - `app.py`: Flask app initialization, CORS, route registration
  - `routes/`: API endpoint handlers
    - `api.py`: Main route registration
    - `detections.py`: SAR detections, clusters, routes, tiles
    - `gaps.py`: Gap events
    - `analytics.py`: Analytics and risk scoring
    - `vessels.py`: Vessel details and timelines
    - `insights.py`: Vessel insights
    - `configs.py`: Configuration and EEZ boundaries
  - `services/`:
    - `dark_vessel_service.py`: Core business logic (dark vessel detection, clustering, route prediction, risk scoring)
  - `utils/`:
    - `gfw_client.py`: GFW API client wrapper with caching and retry logic
  - `configs/`:
    - `config.py`: API endpoints, datasets, configuration

- **Data Flow**:
  1. User input → Frontend builds request
  2. Frontend → Backend API endpoint
  3. Backend → Route handler → Service layer
  4. Service → GFW API client → GFW API v3
  5. GFW API → Returns data
  6. Client → Processes & caches data
  7. Service → Combines & analyzes data
  8. Route → Returns JSON response
  9. Frontend → Updates map & dashboard

---

## Feature Audit

### ✅ Fully Implemented Features

#### 1. Dark Vessel Detection ✅
- **Status**: Fully implemented
- **Backend**: `DarkVesselService.get_dark_vessels()` combines SAR detections (matched=false) with AIS gap events
- **Frontend**: Displays detections as markers on map
- **Location**: 
  - Backend: `backend/services/dark_vessel_service.py`
  - Frontend: `frontend/main.js` - `addDarkVesselMarkers()`

#### 2. Interactive Heatmaps ✅
- **Status**: Fully implemented
- **Backend**: Tile proxy endpoint `/api/tiles/proxy/<path>` handles GFW 4Wings API authentication
- **Frontend**: Leaflet tile layer displays heatmap with error handling
- **Location**:
  - Backend: `backend/routes/detections.py` - `proxy_tile()`
  - Frontend: `frontend/main.js` - `updateMapWithDetections()`

#### 3. EEZ-based Filtering ✅
- **Status**: Fully implemented
- **Backend**: Multi-EEZ support with boundary fetching
- **Frontend**: Multi-select dropdown with boundary visualization on map
- **Location**:
  - Backend: `backend/routes/configs.py` - `/api/eez-boundaries`
  - Frontend: `frontend/utils.js` - `buildEEZSelect()`, `frontend/main.js` - `updateEEZBoundaries()`

#### 4. Real-time Data ✅
- **Status**: Fully implemented
- **Backend**: Uses latest GFW datasets (`public-global-sar-presence:latest`, `public-global-gaps-events:latest`)
- **Frontend**: Fetches data based on user-selected date ranges
- **Note**: Data typically available up to 5 days in arrears (GFW limitation)

#### 5. Responsive UI ✅
- **Status**: Basic implementation exists
- **CSS**: Media queries for mobile devices (`@media (max-width: 768px)`)
- **Location**: `frontend/css/style.css` lines 533-566
- **Note**: Needs testing and potential improvements for better mobile experience

#### 6. Vessel Tracking ✅
- **Status**: Fully implemented
- **Backend**: 
  - ✅ `/api/vessels/<vessel_id>` endpoint with `includes` parameter (OWNERSHIP, AUTHORIZATIONS, REGISTRIES_INFO)
  - ✅ `/api/vessels/<vessel_id>/timeline` endpoint combining all event types (fishing, port visits, encounters, loitering, gaps)
  - ✅ `get_vessel_details()` in `GFWApiClient` with enhanced includes
  - ✅ Activity events endpoint `/api/events` exists
- **Frontend**: 
  - ✅ Formatted vessel details modal with:
    - Vessel identity (name, flag, type, length, MMSI, IMO)
    - Ownership information
    - Authorizations/licenses
    - Risk assessment section
    - Activity timeline summary
    - Raw JSON in collapsible section
  - ✅ Click vessel ID in marker popup → shows formatted vessel details
  - ⚠️ Vessel path/track visualization on map (not yet implemented)
- **Location**:
  - Backend: `backend/routes/vessels.py` - `/api/vessels/<id>` and `/api/vessels/<id>/timeline`
  - Frontend: `frontend/main.js` - `showVesselDetails()`, `showVesselModal()`

#### 7. Risk Assessment ✅
- **Status**: Fully implemented
- **Backend**: 
  - ✅ `DarkVesselService.calculate_risk_score()` method with enhanced factors
  - ✅ `/api/analytics/risk-score/<vessel_id>` endpoint exists
  - ✅ Calculates risk based on weighted factors:

| Risk Factor | Weight | Range | Data Source | API Response Field |
|-------------|--------|-------|-------------|-------------------|
| Gap frequency | 0-50 points | Based on gap events per time period | Insights API (`GAP` include) | `gap.periodSelectedCounters.events` or `gap.periodSelectedCounters.eventsGapOff` |
| IUU status | 0-50 points | Binary (IUU or not) | Insights API (`VESSEL-IDENTITY-IUU-VESSEL-LIST` include) | `vesselIdentity.iuuVesselList.totalTimesListedInThePeriod` |
| Fishing intensity | 0-15 points | Based on fishing events count | Events API (fishing events) | Event count from `/events` endpoint |
| Encounter frequency | 0-20 points | Based on encounters count | Events API (encounter events) | Event count from `/events` endpoint |
| Port visit patterns | 0-15 points | Based on port visits count | Events API (port visit events) | Event count from `/events` endpoint |
| **Total Score** | **0-100** | Weighted sum | All sources combined | - |

**Note**: The Insights API also provides `gap.aisOff` (array of gap event IDs) and `gap.historicalCounters` (all-time counts) which could be used for enhanced risk assessment.
  - ✅ Returns risk level (low/medium/high) and factor breakdown
- **Frontend**: 
  - ✅ Risk score display in vessel details modal with color coding
  - ✅ Risk factors breakdown showing contribution of each factor
  - ✅ Color-coded risk levels (red=high, orange=medium, green=low)
  - ⚠️ Risk filtering/sorting options (not yet implemented)
- **Location**:
  - Backend: `backend/services/dark_vessel_service.py` - `calculate_risk_score()`
  - Backend: `backend/routes/analytics.py` - `/api/analytics/risk-score/<vessel_id>`
  - Frontend: `frontend/main.js` - `showVesselModal()` with risk display

#### 8. Analytics Dashboard ✅
- **Status**: Fully implemented
- **Backend**: 
  - ✅ `/api/analytics/dark-vessels` endpoint with enhanced statistics
  - ✅ Returns statistics: total detections, SAR detections, gap events, EEZ count
  - ✅ Enhanced statistics from Events Stats API (fishing, port visits, encounters, loitering)
  - ✅ 4Wings Stats API integration for global aggregated statistics
- **Frontend**: 
  - ✅ Analytics dashboard panel with statistics cards
  - ✅ Statistics display showing:
    - Total Detections (SAR + gaps)
    - SAR Points (location points)
    - Gap Events (with vessel IDs)
    - EEZs Monitored
  - ✅ Enhanced statistics section (fishing, port visits, encounters, loitering)
  - ✅ Detailed statistics in collapsible section
  - ✅ "What This Means" legend explaining the data
  - ⚠️ Charts/graphs for trends (not yet implemented - would need time-series data)
  - ⚠️ Export statistics functionality (not yet implemented)
- **Location**:
  - Backend: `backend/routes/analytics.py` - `/api/analytics/dark-vessels`
  - Frontend: `frontend/index.html` - Analytics Dashboard section
  - Frontend: `frontend/main.js` - `updateSummaryStats()`

### Summary
- **Fully Working (8/8)**: ✅ All core features implemented
- **Recent Enhancements**: Vessel timeline, risk assessment, analytics dashboard all completed
- **Future Enhancements**: Vessel path visualization, risk filtering, export functionality

---

## Project Kanban

### 🔴 CRITICAL - Core Dark Vessel Detection

#### DONE ✅
- [x] **1.0** Create GFW API Client (`utils/gfw_client.py`) - FULLY API COMPLIANT
- [x] **1.1** Implement AIS Gap Events API Integration
- [x] **1.2** Enhance Dark Vessel Detection Endpoint
- [x] **1.5** Fix GFW Client Integration Issues
- [x] **1.6** Create Service Layer
- [x] **1.7** Modular Architecture
- [x] **1.8** Analytics Dashboard
- [x] **1.9** API Compliance
- [x] **1.10** Code Cleanup

#### TODO
- [ ] **1.3** Optimize EEZ Zone Selection UI
- [ ] **1.4** Enhance Insights API Integration

### 🟡 HIGH - Visualization & Performance

#### TODO
- [ ] **2.1** Optimize Map Rendering Performance
- [ ] **2.2** Enhanced Dark Vessel Visualization
- [ ] **2.3** Real-time Map Updates
- [ ] **2.4** Interactive Vessel Timeline

### 🟢 MEDIUM - Analytics & Intelligence

#### TODO
- [ ] **3.1** Enhance Dark Vessel Analytics Dashboard
- [ ] **3.2** Enhance Vessel Risk Assessment Module
- [ ] **3.3** Export & Reporting
- [ ] **3.4** Pattern Detection

### 🔵 LOW - Automation & Modularity

#### TODO
- [ ] **4.1** Automated Dark Vessel Monitoring
- [ ] **4.2** Enhanced Modular Architecture
- [ ] **4.3** Configuration Management
- [ ] **4.4** API Rate Limiting & Caching

### ✅ API Compliance Status

All endpoints are fully compliant with GFW API v3:
- ✅ 4Wings API: POST with region in body, temporal resolution DAILY/MONTHLY/ENTIRE
- ✅ Events API: POST for regions, GET for simple queries
- ✅ Vessels API: Correct parameter names and includes format
- ✅ Insights API: Proper POST body format

---

## GFW API Enhancements

### Available GFW API v3 Endpoints

1. **Map Visualization - 4Wings API** ✅ (Already using)
2. **Vessels API** ✅ (Already using)
3. **Events API** ✅ (Already using)
4. **Insights API** ✅ (Already using)
5. **Datasets API** ⚠️ (Partially using)
6. **Bulk Download API** ❌ (Not using)

### Implementation Priority

| Priority | Enhancement | Status | Description |
|----------|-------------|--------|-------------|
| **High** | Vessel Timeline | ✅ DONE | Use fishing events, port visits, encounters, loitering |
| **High** | Enhanced Vessel Details | ✅ DONE | Use `includes` parameter (OWNERSHIP, AUTHORIZATIONS, REGISTRIES_INFO) |
| **High** | Risk Score UI | ✅ DONE | Display existing risk scores in vessel modal |
| **High** | Analytics Dashboard UI | ✅ DONE | Display existing statistics with enhanced stats |
| **Medium** | Enhanced Risk Calculation | ✅ DONE | Add fishing/encounter/port risk factors |
| **Medium** | Time-Series Analytics | ⏳ TODO | Add daily/weekly breakdowns |
| **Medium** | Vessel Path Visualization | ⏳ TODO | Map vessel movement over time |
| **Low** | Export Functionality | ⏳ TODO | CSV/JSON export of analytics |
| **Low** | Historical Trends | ⏳ TODO | Long-term trend analysis |
| **Low** | Comparative Analytics | ⏳ TODO | Compare multiple EEZs |

---

## GFW API Data Questions

### 1. Earliest Date Available for Queries

| Aspect | Details | Notes |
|--------|---------|-------|
| **Current Implementation** | `2017-01-01` (updated from 2022-01-01) | Frontend validation |
| **GFW API Reality** | SAR data available from ~2017-2018, AIS gaps earlier | API-dependent |
| **Recommendation** | Test with earlier dates, handle API errors gracefully | Error handling in place |

### 2. Multiple Detections Per Time/Location

| Aspect | Details | Impact |
|--------|---------|--------|
| **Answer** | SAR detections are aggregated - one record can represent multiple vessels | Single point = multiple vessels |
| **Field** | `detections` (plural) indicates count at that location | Use this for accurate counts |
| **Implication** | Need to use `detections` field for accurate vessel counts | Not 1:1 with vessels |

### 3. Getting Vessel IDs for SAR Detections

| Aspect | Details | Alternative |
|--------|---------|-------------|
| **Limitation** | SAR detections do NOT have vessel IDs (fundamental limitation) | Cannot be changed |
| **Solution** | Cross-reference with AIS gap events (temporal/spatial matching) | Manual correlation |
| **Alternative** | Use `matched=true` filter for matched SAR detections (has vessel IDs) | But these aren't "dark" vessels |

### 4. Showing Likely Routes Dark Vessels Use

| Strategy | Description | Complexity | Accuracy |
|----------|-------------|------------|----------|
| **Strategy 1** | Gap Event Route Reconstruction (connect consecutive gaps for same vessel) | Low | Medium |
| **Strategy 2** | SAR Detection Hotspot Analysis (connect nearby hotspots) | Medium | Low |
| **Strategy 3** | Port-to-Port Route Inference (gaps between port visits) | Medium | High |
| **Strategy 4** | Statistical Route Prediction (ML-based) | High | High |

---

## Data Clarification

### The Issue
- **"Dark Vessels: 0"** but **"SAR Detections: 65,139"** seems contradictory

### What's Actually Happening

| Data Type | Has Vessel IDs? | What We Can Show | Count Example |
|-----------|----------------|------------------|---------------|
| **SAR Detections** | No (location points only) | Location and date only | 65,139 = 65,139 detection points |
| **Gap Events** | Yes (vessel identity available) | Full vessel details (name, flag, type, risk score, timeline) | 0 = 0 unique vessels with IDs |
| **"Dark Vessels: 0"** | N/A | Unique vessels with identifiable IDs (only from gap events) | Counts only gap events |

### Recommendations

| Change | Status | Impact |
|--------|--------|--------|
| Changed "Dark Vessels" to "Total Detections" (SAR + gaps) | ✅ Done | Clarifies that SAR detections are included |
| Made it clear that SAR detections are location points | ✅ Done | Users understand no vessel IDs available |
| Focus on gap events for full vessel details | ✅ Done | Directs users to gap events for vessel information |

---

## Dark Trade Risk Thresholds

### Risk Level Categorization

| Risk Level | Vessel Count | Marker Color | Rationale | Supporting Sources |
|------------|--------------|--------------|-----------|-------------------|
| **High Risk** | 3+ vessels | Red (`#cc0000`) | Coordinated illicit activities, complex STS transfers | Lloyd's List Intelligence, Kpler, LSE Research |
| **Medium Risk** | 2 vessels | Orange (`#ff9900`) | Bilateral ship-to-ship transfers or rendezvous | Lloyd's List Intelligence, Windward Maritime, Kpler 2025 Insights |
| **Low Risk** | 1 vessel | Yellow (`#ffcc00`) | Single vessel detection | N/A (not currently used in clustering) |

### Proximity Distance Threshold

| Parameter | Default Value | Rationale | Configurable |
|-----------|---------------|----------|--------------|
| `max_distance_km` | 5 km | Ship-to-ship transfers typically occur within 0.5-2nm (0.9-3.7km), with buffer | Yes (via API parameter) |
| `same_date_only` | `true` | Clustering by date ensures temporal relevance | Yes (via API parameter) |

**Note**: Distance threshold may vary based on vessel types, location, and operational context. Typical STS transfer distances are 0.5-2 nautical miles (0.9-3.7 km).

### Implementation
- **Backend**: `backend/services/dark_vessel_service.py` - `detect_proximity_clusters()`
- **Endpoint**: `/api/detections/proximity-clusters`
- **Visualization**: Red (high), Orange (medium) circle markers with connecting lines

---

## GFW API Utilization Audit

| Status | API Endpoint | Usage | Notes |
|--------|--------------|-------|-------|
| ✅ **Using** | 4Wings Reports API | Active | SAR detection reports |
| ✅ **Using** | 4Wings PNG Tiles | Active | Heatmap visualization |
| ✅ **Using** | Events API (GET/POST) | Active | Gap events, fishing, port visits, encounters, loitering |
| ✅ **Using** | Events Stats API | Active | Aggregated event statistics |
| ✅ **Using** | Vessels API (by ID) | Active | Vessel details and metadata |
| ✅ **Using** | Insights API | Active | IUU status, risk indicators |
| ✅ **Using** | EEZ Boundaries | Active | Region filtering and visualization |
| ✅ **Using** | 4Wings Stats API | Active | Global aggregated statistics (integrated in analytics) |
| ⚠️ **Implemented, Not Used** | Bins API | Method exists | Not integrated in analytics dashboard |
| ⚠️ **Implemented, Not Used** | Interaction API | Method exists | Not used in frontend (click-to-detail) |
| ⚠️ **Implemented, Not Used** | Generate PNG | Method exists | Never called |
| ❌ **Not Implemented** | MVT Tiles | - | Vector tiles for better performance |
| ❌ **Not Implemented** | SAR Fixed Infrastructure | - | Exclude fixed structures from detections |
| ❌ **Not Implemented** | Vessel Search | - | Search by name/flag/MMSI |
| ❌ **Not Implemented** | Batch Vessel Lookup | - | Lookup multiple vessels at once |
| ❌ **Not Implemented** | RFMO Boundaries | - | Regional Fisheries Management Organization boundaries |
| ❌ **Not Implemented** | MPA Boundaries | - | Marine Protected Area boundaries |
| ❌ **Not Implemented** | Bulk Download API | - | Large dataset downloads |
| ❌ **Not Implemented** | Get Event by ID | - | Fetch specific event by ID |

### Recommendations for Better Geospatial Statistics
1. **Immediate**: ✅ Use 4Wings Stats API (now integrated)
2. **Immediate**: Use Bins API for better heatmap color scaling
3. **Immediate**: Add Interaction API for click-to-detail
4. **Short-term**: Add SAR Fixed Infrastructure context layer
5. **Short-term**: Implement MVT tiles for better performance

---

## Cluster Debugging Guide

### Issues Identified

#### 1. Gap Events Not Appearing

| Issue | Possible Causes | Debug Steps | Solution |
|-------|----------------|-------------|----------|
| **No gap events visible** | No gap events in date range/region | Check backend logs: `"Gap events API returned total: X"` | Try different date range or region |
| **Gap events without coordinates** | Coordinate extraction failing | Check browser console: `"Gap event missing coordinates"` warnings | Verify gap event structure in console |
| **Coordinate extraction failing** | Field names don't match expected format | Verify structure: `startLat`/`startLon`, `endLat`/`endLon`, `centerLat`/`centerLon`, or `geometry.coordinates` | Check backend coordinate extraction logic |

#### 2. Dark Trade Clusters Not Appearing

| Issue | Possible Causes | Debug Steps | Solution |
|-------|----------------|-------------|----------|
| **No clusters visible** | 5km threshold too small | Check backend logs: `"Detecting proximity clusters from X SAR detections"` | Increase `max_distance_km` (e.g., 10km, 20km) |
| **Same-date filtering too restrictive** | Detections on different dates | Check browser console: `"Proximity clusters data:"` log | Set `same_date_only=false` |
| **No detections within threshold** | Detections genuinely >5km apart | Verify SAR detections have valid coordinates | Increase threshold or check data aggregation |
| **API call failing silently** | Backend error not surfaced | Check backend logs for errors | Verify API endpoint is working |

### Quick Fixes to Try

| Fix | Command/Parameter | When to Use |
|-----|-------------------|-------------|
| **Increase Cluster Distance** | `max_distance_km=10` or `max_distance_km=20` | When detections are spread out |
| **Disable Same-Date Filtering** | `same_date_only=false` | When clusters span multiple days |
| **Check Gap Event Structure** | Inspect console logs | When gap events exist but don't display |

### Math/Physics Check
- **Haversine formula**: ✅ Correct for calculating distances on Earth's surface
- **BFS (Breadth-First Search)**: ✅ Correct for finding connected components
- **5km threshold**: Based on typical STS transfer distances (0.5-2nm = 0.9-3.7km)

**The math is correct** - if clusters aren't appearing, it's likely:
1. Detections are genuinely >5km apart
2. Detections are on different dates (if same_date_only=true)
3. Data aggregation makes detections appear further apart than actual vessels

---

## Segmentation Fault Fix

### Problem
The application was experiencing segmentation faults (segfaults), likely caused by:

| Cause | Description | Impact |
|-------|------------|--------|
| **Global `requests_cache.install_cache()`** | Using global cache installation causes conflicts when multiple client instances are created | Segfaults on client initialization |
| **SQLite cache corruption** | The cache database (`gfw_cache.sqlite`) can become corrupted | Segfaults on cache access |
| **Memory issues** | Large datasets accumulating without limits | Memory-related crashes |

### Solution

| Solution | Implementation | Benefit |
|----------|----------------|---------|
| **Session-Scoped Caching** | Changed from global `install_cache()` to session-scoped `CachedSession` | Prevents conflicts between multiple client instances |
| **Optional Caching** | Added `DISABLE_CACHE=1` environment variable | Allows graceful fallback if caching causes issues |
| **Error Handling** | Improved error handling around cache initialization | Gracefully falls back to non-cached sessions |

### How to Fix Segfaults

| Option | Command | When to Use | Success Rate |
|--------|---------|-------------|--------------|
| **Option 1: Disable Caching** | `export DISABLE_CACHE=1` then `python app.py` | Quick fix, immediate relief | High |
| **Option 2: Clear Cache** | `rm backend/gfw_cache.sqlite*` then `python app.py` | If cache is corrupted | Medium |
| **Option 3: Reinstall** | `pip uninstall requests-cache && pip install requests-cache` | If library is corrupted | Low |

### Testing
After applying fixes, test the application:
```bash
cd backend
export GFW_API_TOKEN=your_token_here
python app.py
```

Then test an endpoint:
```bash
curl http://localhost:5000/api/configs
```

If segfaults persist, use `DISABLE_CACHE=1` to run without caching.

---

## Caching and Deployment

### Current Caching Implementation

Your application **already has caching built-in** to avoid repetitive API queries! Here's how it works:

#### How Caching Works

| Aspect | Details | Impact |
|--------|---------|--------|
| **Automatic Caching** | `GFWApiClient` uses `requests_cache` with SQLite backend | No manual cache management needed |
| **Cache Duration** | API responses cached for **1 day (86400 seconds)** | Reduces API calls, improves performance |
| **Cache Storage** | Cached responses stored in `backend/gfw_cache.sqlite` | Persistent across app restarts |
| **Cache Scope** | Same query parameters = cached response (no new API call) | Identical queries return instantly |

#### Cache Configuration

| Setting | Value | Location | Configurable |
|---------|-------|----------|--------------|
| **Cache File** | `backend/gfw_cache.sqlite` | `backend/utils/gfw_client.py` | Yes (change path) |
| **Expiry** | 1 day (86400 seconds) | `backend/utils/gfw_client.py` | Yes (change `expire_after`) |
| **Backend** | SQLite database | `backend/utils/gfw_client.py` | No (hardcoded) |
| **Enabled** | By default | `backend/utils/gfw_client.py` | Yes (`DISABLE_CACHE=1`) |

#### What Gets Cached

| Request Type | Cached? | Cache Key | Example |
|--------------|---------|-----------|---------|
| **GET requests** | ✅ Yes | URL + query parameters | `/v3/events?datasets[0]=...` |
| **POST requests** | ✅ Yes | URL + request body | `/v3/events` with JSON payload |
| **Tile requests** | ✅ Yes | Full tile URL | `/4wings/tile/heatmap/8/128/100?...` |
| **Error responses** | ❌ No | - | 404, 500 errors not cached |

### Deployment: Yes, You Need a Server

**Yes, you need to deploy your backend server.** The Flask app runs on a server and serves API endpoints to your frontend.

#### Architecture

```
Frontend (GitHub Pages/Netlify)
    ↓ HTTP requests
Backend Server (Render/Railway/Fly.io)
    ↓ API calls
GFW API (Global Fishing Watch)
```

#### Backend Deployment Options

**Render.com (Recommended for Free Tier)**
- Free tier available
- Easy deployment from GitHub
- Persistent storage (cache file persists)
- `render.yaml` already configured

**Railway**
- Free tier with $5/month credit
- Easy deployment
- Persistent storage

**Fly.io**
- Generous free tier
- Global edge network
- Good performance
- Volumes needed for persistent storage

### Cache Management

#### Enabling/Disabling Cache

**Disable caching** (if experiencing segfaults):
```bash
export DISABLE_CACHE=1
python app.py
```

**Enable caching** (default):
```bash
# Don't set DISABLE_CACHE, or set to 0
export DISABLE_CACHE=0
python app.py
```

#### Clearing Cache

**Clear cache file:**
```bash
cd backend
rm gfw_cache.sqlite*
```

### Cache Configuration Options

#### Adjust Cache Duration

Edit `backend/utils/gfw_client.py`:

```python
self.session = requests_cache.CachedSession(
    cache_name=cache_name,
    backend='sqlite',
    expire_after=86400  # Change this (seconds)
)
```

**Options:**
- `86400` = 1 day (current)
- `3600` = 1 hour
- `604800` = 7 days
- `None` = Never expire

---

## GFW API Data Summary

### Overview
This section details all Global Fishing Watch (GFW) API v3 endpoints currently used in the Maritime Surveillance application, the data we receive from each, and the statistics/analytics we generate.

### GFW API Endpoints Currently Used (8 total)

| # | Endpoint | Method | Purpose | Data Received | Vessel IDs? | Used In |
|---|----------|--------|---------|---------------|-------------|---------|
| 1 | `/4wings/report` | POST | SAR detection reports | Location coordinates, date, detection count | No | `DarkVesselService.get_dark_vessels()` |
| 2 | `/events` (Gap Events) | POST/GET | AIS gap events | Vessel IDs, coordinates, duration, timestamps | Yes | `DarkVesselService.get_dark_vessels()` |
| 3 | `/events` (All Events) | POST | Fishing, port visits, encounters, loitering | Event counts per type | Yes | `backend/routes/analytics.py` |
| 4 | `/4wings/stats` | GET | Global aggregated statistics | Totals, averages, value ranges | N/A | `backend/routes/analytics.py` |
| 5 | `/4wings/tile/heatmap/{z}/{x}/{y}` | GET | Heatmap visualization tiles | PNG images (256x256) | N/A | `backend/routes/detections.py` (proxy) |
| 6 | `/vessels/{vesselId}` | GET | Vessel details and metadata | Identity, ownership, authorizations | Yes | `backend/routes/vessels.py` |
| 7 | `/insights/vessels` | POST | IUU status and risk indicators | Risk scores, compliance status, gap insights, IUU listings | Yes | `backend/routes/insights.py`, `DarkVesselService.calculate_risk_score()` |
| 8 | `/datasets/public-eez-areas/{id}` | GET | EEZ boundary geometries | GeoJSON polygons | N/A | `backend/routes/configs.py` |

### Insights API Usage Examples

The Insights API is used for vessel risk assessment. Here are examples of the API calls and responses:

#### GAP Insights (AIS Off Events)

**Request Example:**
```bash
POST /v3/insights/vessels
{
    "includes": ["GAP"],
    "startDate": "2022-07-11",
    "endDate": "2023-07-11",
    "vessels": [{"datasetId": "public-global-vessel-identity:latest", "vesselId": "..."}]
}
```

**Response Structure:**
```json
{
    "gap": {
        "periodSelectedCounters": {
            "events": 1,
            "eventsGapOff": 1
        },
        "historicalCounters": {
            "events": 1,
            "eventsGapOff": 1
        },
        "aisOff": ["9ce75aa2a483a06f41155132b83dc744"]
    }
}
```

**How We Use This:**
- Field: `gap.periodSelectedCounters.events` for gap count in risk scoring
- Risk Weight: 0-50 points (10 points per gap event, max 50)
- Potential: Could use `eventsGapOff` for more specific AIS-off events, or `historicalCounters` for all-time comparison

#### IUU Vessel List Insights

**Request Example:**
```bash
POST /v3/insights/vessels
{
    "includes": ["VESSEL-IDENTITY-IUU-VESSEL-LIST"],
    "startDate": "2020-01-01",
    "endDate": "2024-04-10",
    "vessels": [{"datasetId": "public-global-vessel-identity:latest", "vesselId": "..."}]
}
```

**Response Structure:**
```json
{
    "vesselIdentity": {
        "iuuVesselList": {
            "valuesInThePeriod": [{"from": "2020-01-01T00:00:00Z", "to": "2024-03-01T00:00:00Z"}],
            "totalTimesListed": 1,
            "totalTimesListedInThePeriod": 1
        }
    }
}
```

**How We Use This:**
- Field: `vesselIdentity.iuuVesselList.totalTimesListedInThePeriod` for IUU status
- Risk Weight: 0-50 points (50 if listed, 0 if not)
- Potential: Could use `valuesInThePeriod` to show time ranges when vessel was listed

### Statistics Generated

#### Core Statistics

| Statistic | Description | Source | Vessel IDs? |
|----------|-------------|--------|-------------|
| Total dark vessels | Unique vessels with dark activity | Gap events only | Yes |
| SAR detections | Location points (not vessel count) | SAR Report API | No |
| Gap events | Vessel-based gap events | Events API | Yes |
| EEZ count | Number of EEZs monitored | User selection | N/A |

#### Enhanced Statistics

| Statistic | Description | Source | Used For |
|----------|-------------|--------|----------|
| Fishing events | Count of fishing events | Events API | Risk assessment |
| Port visits | Count of port visit events | Events API | Risk assessment |
| Encounters | Count of vessel encounter events | Events API | Risk assessment (transshipment indicator) |
| Loitering events | Count of loitering events | Events API | Risk assessment |
| Global SAR statistics | Global totals, averages, value ranges | 4Wings Stats API | Context and comparison |

#### Proximity Cluster Statistics

| Statistic | Description | Calculation |
|-----------|-------------|-------------|
| Total clusters | Total number of proximity clusters | BFS algorithm result |
| High risk clusters | Clusters with 3+ vessels | Filter by vessel count |
| Medium risk clusters | Clusters with 2 vessels | Filter by vessel count |
| Vessels in clusters | Total vessels involved in clusters | Sum of cluster vessel counts |
| Spatial spread | Maximum distance between vessels in clusters | Haversine distance calculation |

#### Risk Scoring

| Factor | Weight | Range | Description |
|--------|--------|-------|-------------|
| Gap frequency | 0-50 points | Based on gap events per time period | How often AIS is disabled |
| IUU status | 0-50 points | Binary (IUU or not) | Known illegal fishing status |
| Fishing intensity | 0-15 points | Based on fishing events count | Activity level |
| Encounter frequency | 0-20 points | Based on encounters count | Transshipment indicator |
| Port visit patterns | 0-15 points | Based on port visits count | Suspicious port behavior |
| **Total Score** | **0-100** | Weighted sum | Final risk assessment |

### Data Volume Estimates

| Query Type | EEZs | Date Range | SAR Detections | Gap Events | Clusters | Response Size |
|------------|------|------------|----------------|------------|----------|--------------|
| **Typical** | 1 | 30 days | 100-10,000+ points | 0-500 events | 0-100 clusters | ~100KB - 5MB |
| **Large** | Multiple | 90 days | 10,000-100,000+ points | 0-5,000 events | 0-1,000 clusters | ~1MB - 50MB* |

*Chunked into 30-day periods automatically

### Data Processing & Aggregation

| Process | Algorithm/Method | Default Value | Configurable |
|---------|------------------|---------------|--------------|
| **Date Range Chunking** | Automatic splitting | 30-day chunks | Yes (change `chunk_days`) |
| **Proximity Clustering** | BFS with Haversine distance | 5km threshold | Yes (`max_distance_km`) |
| **Risk Scoring** | Multi-factor weighted calculation | 0-100 scale | Yes (adjust weights) |
| **Caching** | SQLite-based request caching | 1 day expiry | Yes (`expire_after`) |

---

## Project Handoff Details

### Architecture Overview

**Backend Structure:**
- Flask app with modular route structure
- Service layer for business logic
- GFW API client wrapper with caching
- Date range chunking for large queries
- Proximity clustering algorithm (BFS)

**Frontend Structure:**
- Vanilla JavaScript (no frameworks)
- Leaflet.js for mapping
- Responsive CSS design
- Analytics dashboard
- Vessel detail modals

### Key Implementation Details

#### Date Range Chunking

| Aspect | Details | Location |
|--------|---------|----------|
| **Location** | `backend/services/dark_vessel_service.py` - `_split_date_range()` | Service layer |
| **Logic** | Splits ranges >30 days into 30-day chunks + remainder | Automatic |
| **Reason** | GFW API rate limits and performance | API constraints |
| **Example** | 90-day range → 3 chunks of 30 days each | Transparent to user |

#### Proximity Clustering Algorithm

| Aspect | Details | Notes |
|--------|---------|-------|
| **Location** | `backend/services/dark_vessel_service.py` - `detect_proximity_clusters()` | Service layer |
| **Algorithm** | BFS (Breadth-First Search) for connected components | Ensures connectivity |
| **Distance Calculation** | Haversine formula (accurate for Earth's surface) | Great-circle distance |
| **Key Point** | Ensures all detections in a cluster are connected within threshold | Logical consistency |
| **Default Threshold** | 5km maximum distance | Configurable via API |

#### Coordinate Extraction

| Data Type | Field Names Checked | Fallback Options |
|-----------|-------------------|------------------|
| **SAR Detections** | `latitude`/`longitude`, `lat`/`lon` | `lat_center`/`lon_center`, `y`/`x` |
| **Gap Events** | `startLat`/`startLon`, `endLat`/`endLon`, `centerLat`/`centerLon` | `geometry.coordinates`, nested structures |

#### Tile Proxy

| Aspect | Details | Location |
|--------|---------|----------|
| **Why** | GFW tiles require authentication, browsers block cross-origin requests | CORS/authentication |
| **Solution** | Backend proxy endpoint handles authentication | `/api/tiles/proxy/<path>` |
| **Location** | `backend/routes/detections.py` - `proxy_tile()` | Route handler |
| **Error Handling** | Returns transparent 1x1 PNG for 404s | Graceful degradation |

#### EEZ Boundary Handling

| Issue | Solution | Location |
|-------|----------|----------|
| **Date-Line Crossing** | Filtered out in frontend (Alaska, Russia, etc.) | `frontend/utils.js` |
| **MultiPolygon** | Some EEZs cross date line, handled gracefully | GeoJSON parsing |
| **Bbox Fallback** | Used for date-line-crossing regions | Map fitting logic |

### Known Issues & Limitations

| Issue | Description | Impact | Workaround |
|-------|-------------|--------|------------|
| **SAR Detections Have No Vessel IDs** | Location points only, no vessel identity | Cannot fetch vessel details for SAR-only detections | Use gap events for vessel details |
| **Gap Events May Not Appear** | Depends on region and date range | Some regions have better AIS coverage than others | Try different regions or date ranges |
| **Many SAR Detections, Few Gap Events** | Most dark vessels never had AIS in the first place | Gap events only show vessels that WERE broadcasting AIS then turned it off | This is normal - gap events require AIS tracking before the gap, and the transition must happen during your date range |
| **Date Range Limitations** | Data available up to 5 days in arrears (GFW limitation) | Cannot query very recent dates | Use dates 5+ days in the past |
| **Marker Limiting** | Frontend limits to 10,000 markers for performance | Large datasets may not show all markers | Narrow date range or EEZ selection |
| **Proximity Cluster Algorithm** | 5km threshold may be too small for aggregated SAR data | Some clusters may not be detected | Increase `max_distance_km` parameter |
| **Heatmap Tiles May Be Empty** | Tiles may be transparent if no data for date range | Heatmap not visible | Try different date range with known data |

### Understanding SAR vs Gap Events

**Why you see many SAR detections but few gap events:**

#### SAR Detections (Many)
- Ships detected by radar **without AIS**
- Includes:
  - Ships that **never had AIS** (illegal/unregistered vessels, small boats)
  - Ships that turned AIS off **before your observation period**
  - Ships in areas with **poor AIS coverage**
  - Ships that operate entirely "dark" (never turn AIS on)
- **No vessel identity** (can't tell which ship it is)

#### Gap Events (Few)
- Ships that **WERE broadcasting AIS, then intentionally disabled it**
- Requires:
  1. Ship to have been broadcasting AIS (tracked in system)
  2. Transition (AIS on → AIS off) to happen **during your observation period**
  3. System to detect this transition
- **Has vessel identity** (we know which ship it is)

#### The Math
If you see **1,000 SAR detections** but **10 gap events**:
- **~990 vessels** are operating entirely without AIS (never had it, or turned it off outside your window)
- **~10 vessels** turned AIS off during your observation period

#### Why Gap Events Are Rare
1. **Most dark vessels start dark** - They never turn AIS on
2. **Gap events require AIS coverage** - System must track vessel before it goes dark
3. **Timing matters** - Transition must happen during your observation window
4. **Geographic coverage** - AIS coverage varies (better near coasts, worse in remote areas)

#### Our Implementation
- `/api/detections` uses `intentional_gaps_only=False` (gets all gaps)
- `/api/gaps` defaults to `intentional_only=true` (intentional AIS disabling only)
- **This is normal behavior** - Most dark vessels never had AIS to begin with

### Future Enhancements (Not Yet Implemented)

| Priority | Enhancement | Description | Estimated Effort |
|----------|-------------|-------------|-----------------|
| **High** | Vessel Path Visualization | Show vessel movement/track on map over time | Medium |
| **High** | Risk Filtering | Filter detections by risk score in UI | Low |
| **High** | Marker Clustering | Cluster markers for better performance with large datasets | Medium |
| **High** | Enhanced Mobile UI | Improve responsive design testing and mobile experience | Low |
| **Medium** | Export Functionality | CSV/GeoJSON export of detection data | Low |
| **Medium** | Time-Series Charts | Trend visualization if historical data available | Medium |
| **Medium** | Interaction API Integration | Click-to-detail for heatmap cells | Low |
| **Medium** | Bins API Integration | Better heatmap color scaling per zoom level | Low |
| **Low** | Vessel Search | Search by name/flag/MMSI | Medium |
| **Low** | RFMO/MPA Boundaries | Additional context layers | Low |
| **Low** | SAR Fixed Infrastructure | Exclude fixed structures from detections | Medium |
| **Low** | MVT Tiles | Vector tiles for better performance | High |

### Key Decisions & Rationale

| Decision | Rationale | Alternative Considered |
|----------|-----------|------------------------|
| **BFS for Clustering** | Ensures all detections in a cluster are connected within threshold (logical consistency) | K-means, DBSCAN (rejected: don't ensure connectivity) |
| **5km Threshold** | Based on typical ship-to-ship transfer distances (0.5-2nm = 0.9-3.7km), with buffer | 2km, 10km (rejected: too small/large) |
| **Date Chunking** | GFW API limits and performance - splitting >30 days improves reliability | Single large query (rejected: API timeouts) |
| **Tile Proxy** | GFW tiles require authentication, browsers block cross-origin requests | Direct tile access (rejected: CORS issues) |
| **Manual Aggregation** | 4Wings Stats API provides global stats, not region-specific | Use Stats API only (rejected: no region filtering) |
| **Separate SAR and Gap Events** | SAR has no vessel IDs (location points), gaps have vessel IDs (full details available) | Combine into single endpoint (rejected: different data structures) |

---

## Data Flow Optimization Analysis

### Current Data Flow Issues

The current API data flow has several inefficiencies that result in redundant API calls and duplicate data processing:

#### Problem 1: Redundant `get_dark_vessels()` Calls

**Current Flow:**
1. Frontend calls `/api/detections` → calls `get_dark_vessels()` → fetches SAR + Gaps from GFW
2. Frontend calls `/api/detections/proximity-clusters` → calls `get_dark_vessels()` again → fetches SAR again
3. Frontend calls `/api/detections/routes` → calls `get_dark_vessels()` again → fetches SAR + Gaps again
4. Frontend calls `/api/analytics/dark-vessels` → calls `get_dark_vessels()` again → fetches SAR + Gaps again

**Impact:**
- Same GFW API calls made 4 times with identical parameters
- Same data processing (date chunking, filtering) repeated 4 times
- Even with HTTP caching (`requests_cache`), there's still overhead in:
  - Service method invocations
  - Data structure creation
  - Response serialization
  - Network round trips (even if cached)

#### Problem 2: Separate Statistics Fetching

**Current Flow:**
- `/api/analytics/dark-vessels` fetches Events API data separately
- Statistics could be calculated from already-fetched dark vessel data
- Additional API calls for fishing, port visits, encounters, loitering events

#### Problem 3: Frontend Sequential Requests

**Current Flow:**
```javascript
// 1. Main detections
fetch('/api/detections') 
  → updateMapWithDetections()
    → fetchProximityClusters()  // 2. Clusters (separate request)
    → fetchPredictedRoutes()    // 3. Routes (separate request)
// 4. Analytics (if needed, separate request)
```

**Impact:**
- 4 separate HTTP requests
- 4 separate backend processing cycles
- Slower user experience
- Higher server load

### Optimization Recommendations

#### Option 1: Unified Endpoint (Recommended)

**Create a single endpoint that returns all needed data:**

```python
@detections_bp.route("/api/detections/unified", methods=["GET"])
def get_unified_detections():
    """Get all detection data in a single response: SAR, Gaps, Clusters, Routes, Stats."""
    # Single call to get_dark_vessels()
    dark_vessels = service.get_dark_vessels(...)
    
    # Process clusters from already-fetched SAR data
    clusters = service.detect_proximity_clusters(
        sar_detections=dark_vessels["sar_detections"]
    )
    
    # Process routes from already-fetched data
    routes = service.predict_routes(
        sar_detections=dark_vessels["sar_detections"],
        gap_events=dark_vessels["gap_events"]
    )
    
    # Calculate statistics from already-fetched data
    stats = calculate_stats(dark_vessels)
    
    return jsonify({
        "dark_vessels": dark_vessels,
        "clusters": clusters,
        "routes": routes,
        "statistics": stats,
        "tile_url": tile_url
    })
```

**Benefits:**
- Single `get_dark_vessels()` call
- Single data processing cycle
- Single HTTP request from frontend
- Faster response time
- Lower server load

**Trade-offs:**
- Larger response payload (but still manageable)
- Less granular error handling (but can be improved)

#### Option 2: Service-Level Memoization

**Add memoization to `DarkVesselService`:**

```python
from functools import lru_cache
from hashlib import md5
import json

class DarkVesselService:
    _cache = {}
    
    def _cache_key(self, eez_ids, start_date, end_date, include_sar, include_gaps):
        """Generate cache key for memoization."""
        key_data = {
            "eez_ids": sorted(eez_ids),
            "start_date": start_date,
            "end_date": end_date,
            "include_sar": include_sar,
            "include_gaps": include_gaps
        }
        return md5(json.dumps(key_data, sort_keys=True).encode()).hexdigest()
    
    def get_dark_vessels(self, ...):
        cache_key = self._cache_key(eez_ids, start_date, end_date, include_sar, include_gaps)
        
        if cache_key in self._cache:
            logging.info(f"Returning cached dark vessels for {cache_key[:8]}")
            return self._cache[cache_key]
        
        # ... existing logic ...
        
        self._cache[cache_key] = results
        return results
```

**Benefits:**
- Prevents duplicate processing within same request cycle
- Works with existing endpoint structure
- Minimal code changes

**Trade-offs:**
- Still requires multiple HTTP requests from frontend
- Cache management complexity
- Memory usage for cached data

#### Option 3: Batch Endpoint with Optional Features

**Create endpoint that accepts feature flags:**

```python
@detections_bp.route("/api/detections", methods=["GET"])
def get_detections():
    include_clusters = request.args.get("include_clusters", "false").lower() == "true"
    include_routes = request.args.get("include_routes", "false").lower() == "true"
    include_stats = request.args.get("include_stats", "false").lower() == "true"
    
    dark_vessels = service.get_dark_vessels(...)
    
    response = {"dark_vessels": dark_vessels, "tile_url": tile_url}
    
    if include_clusters:
        response["clusters"] = service.detect_proximity_clusters(...)
    
    if include_routes:
        response["routes"] = service.predict_routes(...)
    
    if include_stats:
        response["statistics"] = calculate_stats(...)
    
    return jsonify(response)
```

**Frontend:**
```javascript
const params = new URLSearchParams({
  ...filters,
  include_clusters: 'true',
  include_routes: showRoutes ? 'true' : 'false',
  include_stats: 'true'
});
const response = await fetch(`/api/detections?${params}`);
```

**Benefits:**
- Single endpoint, flexible features
- Backward compatible (existing calls still work)
- Single `get_dark_vessels()` call
- Frontend controls what to fetch

**Trade-offs:**
- Slightly more complex endpoint logic
- Response size varies by flags

### Recommended Approach

**Hybrid: Option 3 (Batch Endpoint) + Option 2 (Service Memoization)**

1. **Implement Option 3** for immediate improvement:
   - Single endpoint with feature flags
   - Single `get_dark_vessels()` call
   - Frontend makes one request instead of four

2. **Add Option 2** for additional safety:
   - Service-level memoization as backup
   - Prevents duplicate processing if endpoints called separately
   - Useful for future API consumers

### Performance Impact Estimate

**Current (4 requests):**
- Request 1: `/api/detections` → ~2-5s
- Request 2: `/api/detections/proximity-clusters` → ~2-5s
- Request 3: `/api/detections/routes` → ~2-5s
- Request 4: `/api/analytics/dark-vessels` → ~2-5s
- **Total: ~8-20s** (sequential) or ~2-5s (parallel, but still 4x server load)

**Optimized (1 request):**
- Request 1: `/api/detections?include_clusters=true&include_routes=true&include_stats=true` → ~3-6s
- **Total: ~3-6s** (single request, single processing cycle)

**Improvement: ~60-70% faster, ~75% less server load**

### Implementation Priority

1. **High Priority**: Implement Option 3 (Batch Endpoint)
   - Immediate performance improvement
   - Minimal code changes
   - Backward compatible

2. **Medium Priority**: Add Option 2 (Service Memoization)
   - Additional safety net
   - Helps with future API consumers
   - Prevents edge cases

3. **Low Priority**: Consider Option 1 (Unified Endpoint)
   - If Option 3 doesn't meet needs
   - More breaking changes
   - Requires frontend refactoring

---

**Last Updated**: January 2026
**Status**: Internal Development Documentation

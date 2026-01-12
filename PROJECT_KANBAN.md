# 🚢 Dark Vessel Detection System - Project Kanban

## 🎯 Project Goal
Build a fully functioning system to detect and analyze vessels that turn off their AIS (dark vessels) using GFW API, EEZ zones, with focus on: **Zone Selection**, **Visuals**, **Speed**, **Automation**, **Modularity**, and **Analytics**.

---

## 📋 KANBAN BOARD

### 🔴 **1. CRITICAL - Core Dark Vessel Detection**

#### **TODO**
- [ ] **1.3** Optimize EEZ Zone Selection UI
  - Multi-select dropdown with search/filter
  - Visual EEZ boundaries on map (some zone boundaries need fixing)

- [ ] **1.4** Enhance Insights API Integration
  - Improve `/api/insights` endpoint for dark vessels
  - AIS coverage percentage calculation
  - Gap event analysis

#### **DONE** ✅
- [x] **1.0** Create GFW API Client (`utils/gfw_client.py`)
  - ✅ Basic client structure with authentication
  - ✅ Core API methods implemented
  - ✅ **FULLY API COMPLIANT** (see API Compliance section below)

- [x] **1.1** Implement AIS Gap Events API Integration
  - ✅ `/api/gaps` endpoint created (`routes/gaps.py`)
  - ✅ Filter by `gap-intentional-disabling=true` for intentional AIS off
  - ✅ Support EEZ filtering and date ranges
  - ✅ Uses POST with region in body (API compliant)

- [x] **1.2** Enhance Dark Vessel Detection Endpoint
  - ✅ `/api/detections` now combines SAR + GAP events
  - ✅ `matched=false` filter for SAR detections
  - ✅ Cross-reference SAR detections with AIS gap events
  - ✅ Uses `DarkVesselService` for unified analysis

- [x] **1.5** Fix GFW Client Integration Issues
  - ✅ Removed async/await patterns (synchronous client)
  - ✅ Proper error handling for missing client
  - ✅ All routes use direct client method calls

- [x] **1.6** Create Service Layer
  - ✅ `DarkVesselService` created (`services/dark_vessel_service.py`)
  - ✅ `get_dark_vessels()` combines SAR + gaps
  - ✅ `calculate_risk_score()` for risk assessment

- [x] **1.7** Modular Architecture
  - ✅ Split routes into separate modules:
    - `routes/detections.py` - SAR detections
    - `routes/gaps.py` - Gap events
    - `routes/analytics.py` - Analytics dashboard
    - `routes/vessels.py` - Vessel details
    - `routes/insights.py` - Vessel insights
    - `routes/configs.py` - Configuration
  - ✅ Main router in `routes/api.py`

- [x] **1.8** Analytics Dashboard
  - ✅ `/api/analytics/dark-vessels` - Overall statistics
  - ✅ `/api/analytics/risk-score/<vessel_id>` - Per-vessel risk

- [x] **1.9** API Compliance
  - ✅ Events API: POST for regions, GET for simple queries
  - ✅ 4Wings Report: Fixed temporal resolution (DAILY/MONTHLY/ENTIRE)
  - ✅ Vessel Details: Correct parameter names
  - ✅ Gap Events: Proper POST body format
  - ✅ All endpoints fully compliant with GFW API v3 docs

- [x] **1.10** Code Cleanup
  - ✅ Removed `old_app.py` and `old_api.py`
  - ✅ Created `.gitignore` for proper file management
  - ✅ Removed legacy endpoints (`/api/get-tile-url`, `/api/bins/all`)
  - ✅ Fixed EEZ data structure (only main countries marked as parents)

---

### 🟡 **2. HIGH - Visualization & Performance**

#### **TODO**
- [ ] **2.1** Optimize Map Rendering Performance
  - Implement tile caching for heatmaps
  - Use MVT format instead of PNG where possible
  - Lazy load detection markers (only visible viewport)
  - **Priority: HIGH** - Speed requirement
  - **Status**: Performance optimization needed

- [ ] **2.2** Enhanced Dark Vessel Visualization
  - ✅ Basic color-coding implemented (frontend/main.js)
  - [ ] Time-lapse animation for gap events
  - [ ] Vessel trail visualization showing AIS on/off periods
  - [ ] Enhanced risk level visualization
  - **Priority: HIGH** - Visual requirement
  - **Status**: Partially done - needs enhancement

- [ ] **2.3** Real-time Map Updates
  - WebSocket or polling for new detections
  - Auto-refresh every 5-15 minutes
  - Visual indicators for "live" vs "historical" data
  - **Priority: MEDIUM**

- [ ] **2.4** Interactive Vessel Timeline
  - Show AIS transmission history per vessel
  - Gap event visualization (when/where AIS was off)
  - Overlay SAR detections on timeline
  - **Priority: MEDIUM**

---

### 🟢 **3. MEDIUM - Analytics & Intelligence**

#### **TODO**
- [ ] **3.1** Enhance Dark Vessel Analytics Dashboard
  - ✅ Basic analytics endpoint exists (`/api/analytics/dark-vessels`)
  - [ ] Add gap duration statistics (avg, max, min)
  - [ ] Enhanced EEZ distribution charts
  - [ ] Time-series trends visualization
  - **Priority: MEDIUM** - Analytics requirement
  - **Status**: Basic version done - needs enhancement

- [ ] **3.2** Enhance Vessel Risk Assessment Module
  - ✅ Basic risk scoring exists (`/api/analytics/risk-score/<vessel_id>`)
  - [ ] Integrate Insights API `VESSEL-IDENTITY-IUU-VESSEL-LIST`
  - [ ] Combine gap events + IUU listings + fishing in MPAs
  - [ ] Enhanced risk score calculation (0-100)
  - **Priority: MEDIUM**
  - **Status**: Basic version done - needs enhancement

- [ ] **3.3** Export & Reporting
  - Export dark vessel list to CSV/GeoJSON
  - Generate PDF reports with maps and statistics
  - Scheduled email reports
  - **Priority: LOW**

- [ ] **3.4** Pattern Detection
  - Identify vessels with repeated gap patterns
  - Detect suspicious behavior (gaps near MPAs, RFMOs)
  - Cluster analysis for coordinated dark vessel activity
  - **Priority: LOW**

---

### 🔵 **4. LOW - Automation & Modularity**

#### **TODO**
- [ ] **4.1** Automated Dark Vessel Monitoring
  - Scheduled tasks (Celery/APScheduler) to check for new gaps
  - Alert system for high-risk vessels
  - Daily/weekly summary reports
  - **Priority: MEDIUM** - Automation requirement
  - **Status**: Future enhancement

- [ ] **4.2** Enhanced Modular Architecture
  - ✅ Routes split into separate modules (DONE)
  - ✅ Service layer created (DONE)
  - [ ] Create data models (`models/dark_vessel.py`, `models/gap_event.py`)
  - [ ] Separate validation schemas
  - **Priority: LOW** - Already modular, minor improvements

- [ ] **4.3** Configuration Management
  - Move hardcoded values to config files
  - Environment-based settings (dev/staging/prod)
  - Feature flags for experimental features
  - **Priority: LOW**

- [ ] **4.4** API Rate Limiting & Caching
  - Implement Redis caching for frequent queries
  - Smart cache invalidation
  - Request queuing for rate limits
  - **Priority: LOW**

---

## ✅ **API Compliance Status**

### **Fixed Issues**

#### 1. **Events API with Regions**
- **Issue**: Using GET with query params for region filtering  
- **Fix**: Use POST with region in body
- `get_gap_events()` now uses POST when `eez_id` is provided
- Region format: `{"dataset": "public-eez-areas", "id": <eez_id>}`

#### 2. **4Wings Report API**
- **Issue**: Using `HOURLY` for temporal-resolution  
- **Fix**: Changed to `DAILY` (per API docs)
- Valid values: `DAILY`, `MONTHLY`, `ENTIRE` (not HOURLY)
- Region properly sent in POST body (not query params)

#### 3. **Vessel Details API**
- **Issue**: Using wrong parameter name  
- **Fix**: Use `dataset` not `datasets[0]` for single vessel
- Single vessel: `/vessels/{vesselId}?dataset=...`
- Multiple vessels: `/vessels?datasets[0]=...&ids[0]=...`

#### 4. **Gap Events API**
- **Issue**: Using GET with region in query params  
- **Fix**: Use POST when region is provided
- Parameter: `gapIntentionalDisabling` (camelCase in POST body)

#### 5. **Filter Parsing**
- **Issue**: `neural_vessel_type` defaulting to wrong value  
- **Fix**: Set default to `None` (not dataset name)
- Valid values: "Likely non-fishing", "Likely Fishing", "Unknown"

### **API Compliance Checklist**

#### ✅ **4Wings API**
- [x] Report: POST with region in body
- [x] Temporal resolution: DAILY/MONTHLY/ENTIRE (not HOURLY)
- [x] Tiles: Proper format parameter
- [x] Bins: Correct parameter names
- [x] Interaction: Cells in path, datasets[0] in query

#### ✅ **Events API**
- [x] GET for simple queries (no regions)
- [x] POST for complex queries (with regions)
- [x] Region in POST body: `{"dataset": "...", "id": ...}`
- [x] Gap events: `gapIntentionalDisabling` in POST body
- [x] Date format: `startDate`/`endDate` in POST, `start-date`/`end-date` in GET

#### ✅ **Vessels API**
- [x] Single vessel: `dataset` parameter
- [x] Multiple vessels: `datasets[0]` parameter
- [x] Search: Proper query/where parameters
- [x] Includes: Array format `includes[0]`, `includes[1]`, etc.

#### ✅ **Insights API**
- [x] POST only (no query params)
- [x] Body format: `includes`, `startDate`, `endDate`, `vessels`
- [x] Vessel format: `{"datasetId": "...", "vesselId": "..."}`

---

## 🧪 **Testing Guide**

### **Servers**
- **Backend**: http://localhost:5000
- **Frontend**: http://localhost:8080

### **Test Endpoints**

#### 1. **Configs** (No params needed)
```bash
curl http://localhost:5000/api/configs
```

#### 2. **Detections** (Dark vessels)
```bash
curl -G "http://localhost:5000/api/detections" \
  --data-urlencode "eez_ids=[\"8493\"]" \
  --data-urlencode "start_date=2024-12-01" \
  --data-urlencode "end_date=2024-12-07"
```

#### 3. **Gap Events**
```bash
curl -G "http://localhost:5000/api/gaps" \
  --data-urlencode "eez_ids=[\"8493\"]" \
  --data-urlencode "start_date=2024-12-01" \
  --data-urlencode "end_date=2024-12-07" \
  --data-urlencode "intentional_only=true"
```

#### 4. **Analytics**
```bash
curl -G "http://localhost:5000/api/analytics/dark-vessels" \
  --data-urlencode "eez_ids=[\"8493\"]" \
  --data-urlencode "start_date=2024-12-01" \
  --data-urlencode "end_date=2024-12-07"
```

### **Common EEZ IDs**
- `8493` - Canada
- `5677` - France  
- `8456` - United States
- `5696` - United Kingdom
- `8486` - China

### **Notes**
- **Date Range**: Use recent dates (within last 30 days) for best results
- **EEZ IDs**: Use numeric IDs from `/api/configs` response
- **GFW Token**: Make sure `GFW_API_TOKEN` is set in `.env` for full functionality
- **Multiple EEZs**: Use `["8493","5677"]` format (comma-separated IDs)

---

## 📊 **API Endpoints**

### **ESSENTIAL (Must Have)** ✅
1. ✅ `/api/detections` - SAR detections + GAP events (ENHANCED)
2. ✅ `/api/gaps` - AIS gap events (IMPLEMENTED)
3. ✅ `/api/vessels/<id>` - Vessel details (EXISTS)
4. ✅ `/api/insights` - Vessel insights (EXISTS)
5. ✅ `/api/configs` - Configuration (EXISTS)

### **IMPORTANT (Should Have)** ✅
6. ✅ `/api/events` - Events API (SIMPLIFIED for gaps)
7. ✅ `/api/analytics/dark-vessels` - Combined dark vessel analysis (NEW)
8. ✅ `/api/analytics/risk-score/<id>` - Risk scoring (NEW)
9. ✅ `/api/eez-data` - EEZ boundaries (via configs)

### **NICE TO HAVE (Can Wait)**
10. ✅ `/api/bins/<z>` - Heatmap bins (EXISTS)
11. ⚠️ `/api/interaction` - Map click details (EXISTS, can enhance)
12. ✅ `/api/summary` - Summary stats (SIMPLIFIED)

### **REMOVED** ✅
- ✅ `/api/get-tile-url` - Legacy endpoint (REMOVED)
- ✅ `/api/bins/all` - Redundant (REMOVED)

---

## 🏗️ **Architecture**

### **File Structure**
```
backend/
├── routes/
│   ├── api.py           # Main router
│   ├── detections.py     # SAR detections
│   ├── gaps.py          # Gap events
│   ├── analytics.py     # Analytics dashboard
│   ├── vessels.py       # Vessel details
│   ├── insights.py      # Insights
│   └── configs.py       # Config
├── services/
│   └── dark_vessel_service.py  # Core logic
└── utils/
    └── gfw_client.py    # GFW API client
```

### **Key Features**
1. **Dark Vessel Detection:** SAR (matched=false) + AIS gaps
2. **Risk Scoring:** Based on gap frequency + IUU status
3. **Modular Architecture:** Easy to extend/maintain
4. **Performance:** Removed async overhead, direct calls
5. **Analytics:** Dashboard with statistics

---

## 🗑️ **Cleanup Summary**

### **Files Removed**
- ✅ `backend/old_app.py` - Legacy code removed
- ✅ `backend/routes/old_api.py` - Legacy code removed
- ✅ `.DS_Store` - macOS system files removed

### **Files Ignored (via .gitignore)**
- Python cache files (`__pycache__/`, `*.pyc`)
- Database files (`*.sqlite`, `*.db`)
- IDE & OS files (`.vscode/`, `.DS_Store`)
- Environment files (`.env`, `.env.local`)
- Build & test files (`dist/`, `build/`, `venv/`)

---

## 📝 **Implementation Summary**

### **Completed Modifications**

1. **Fixed Async Issues** 
   - Removed `asyncio.run()` calls - GFW client is synchronous
   - All routes now use direct client method calls

2. **Created AIS Gap Events Endpoint** (`/api/gaps`)
   - New endpoint for dark vessel detection via AIS gaps
   - Filters by intentional disabling (`gap-intentional-disabling=true`)
   - Supports EEZ filtering and date ranges

3. **Enhanced Dark Vessel Detection** (`/api/detections`)
   - Now combines SAR detections + AIS gap events
   - Uses `DarkVesselService` for unified analysis
   - Returns cross-referenced vessel IDs

4. **Created Service Layer**
   - `DarkVesselService` - core dark vessel logic
   - `get_dark_vessels()` - combines SAR + gaps
   - `calculate_risk_score()` - risk assessment (0-100)

5. **Modular Route Architecture**
   - Split monolithic `api.py` into separate route files
   - Each route handles specific functionality

6. **Analytics Dashboard** (`/api/analytics/*`)
   - `/api/analytics/dark-vessels` - Overall statistics
   - `/api/analytics/risk-score/<vessel_id>` - Per-vessel risk

7. **Enhanced GFW Client**
   - Added methods for gap events and reports
   - Fully compliant with GFW API v3

8. **Removed Legacy Code**
   - Deleted old API files
   - Removed deprecated endpoints

9. **Frontend Updates**
   - Updated to use new dark vessel endpoints
   - Enhanced summary stats with gap events
   - Color-coded markers by risk level
   - Fixed EEZ selection (only main countries show group options)

---

## 🎯 **Next Steps (Priority Order)**

### 🔴 **1. HIGH PRIORITY: Optimize EEZ Zone Selection UI**
- Multi-select dropdown with search/filter
- Visual EEZ boundaries on map
- Quick-select presets
- **Estimated Time**: 4-6 hours

### 🟡 **2. HIGH PRIORITY: Enhanced Dark Vessel Visualization**
- Time-lapse animation for gap events
- Vessel trail visualization
- Enhanced risk level color-coding
- **Estimated Time**: 6-8 hours

### 🟡 **3. HIGH PRIORITY: Map Rendering Performance**
- Tile caching
- Lazy loading markers
- MVT format optimization
- **Estimated Time**: 4-6 hours

### 🟢 **4. MEDIUM PRIORITY: Enhanced Analytics Dashboard**
- Gap duration statistics
- Time-series trends
- Enhanced charts
- **Estimated Time**: 6-8 hours

### 🟢 **5. MEDIUM PRIORITY: Export Functionality**
- CSV/GeoJSON export
- PDF reports
- **Estimated Time**: 4-6 hours

---

## ✅ **Success Criteria**

### **Phase 1 (Core) - COMPLETE** ✅
- ✅ GFW API client working (FULLY COMPLIANT)
- ✅ AIS gap events integrated
- ✅ Dark vessel detection working (SAR + GAP combined)
- ⚠️ EEZ selection optimized (BASIC - needs enhancement)
- ✅ Basic visualization working

### **Phase 2 (Performance) - IN PROGRESS**
- ⚠️ Map rendering < 1s
- ⚠️ API responses < 2s
- ⚠️ Enhanced visualizations

### **Phase 3 (Analytics) - PLANNED**
- ⚠️ Analytics dashboard
- ⚠️ Risk scoring
- ⚠️ Export functionality

### **Phase 4 (Automation) - FUTURE**
- ⚠️ Scheduled monitoring
- ⚠️ Alert system
- ⚠️ Modular architecture

---

**Last Updated:** 2024-12-20
**Status:** ✅ Phase 1 COMPLETE → Phase 2 (Visualization & Performance) IN PROGRESS

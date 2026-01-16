# Maritime Surveillance

Explore “dark” maritime activity using Global Fishing Watch SAR detections, with lightweight clustering and best‑effort route inference.

## What it does
- **SAR detections**: unmatched SAR points (no vessel identity)
- **Dark traffic clusters**: proximity grouping (heuristic “risk” labels)
- **Route prediction**: temporal + spatial linking of SAR points (not confirmed tracks)
- **EEZ filtering**: pick one or more EEZs and a date range, then load data

## How route prediction works (short)
Routes are inferred by chaining detections within a **time window** and **distance window**:
- **Distance**: great‑circle distance (Haversine)
- **Link rule**: connect to the “best next” point that is close in space and time (greedy)
- **Confidence**: increases with point count and is penalized for unrealistic implied speeds

Defaults (can be tuned in requests): **48 hours**, **100 km**, **min 2 points**.

## Run it locally

### Backend
```bash
cd backend
pip install -r requirements.txt
export GFW_API_TOKEN="..."
export FRONTEND_ORIGINS="http://localhost:8080"
python app.py
```

### Frontend
```bash
cd frontend
python -m http.server 8080
```
Open `http://localhost:8080`.

## Deploy (high level)

### Backend (Render)
- Root dir: `backend`
- Build: `pip install -r requirements.txt`
- Start: `python app.py`
- Health check: `/healthz`
- Env:
  - `GFW_API_TOKEN` (required)
  - `BACKEND_URL=https://<service>.onrender.com`
  - `FRONTEND_ORIGINS=https://<your-gh-username>.github.io,http://localhost:8080` (**origins only; no paths**)

### Frontend (GitHub Pages via `/docs`)
This repo serves the Pages site from `docs/` (copy of `frontend/`).

## Key backend env vars
- **GFW_API_TOKEN**: required
- **FRONTEND_ORIGINS**: comma‑separated origins (no paths), e.g. `https://charlotteprevost.github.io`
- **BACKEND_URL**: the public backend base URL (Render)

## Repo layout
- `backend/`: Flask API (routes + services)
- `frontend/`: static UI (Leaflet + vanilla JS)
- `docs/`: GitHub Pages build output (static copy)

# Maritime Surveillance

I built this to quickly explore “dark” maritime activity using Global Fishing Watch SAR detections, plus some lightweight clustering and route guesses.

## What it does
- **SAR detections**: unmatched SAR points (no vessel identity)
- **Dark traffic clusters**: proximity grouping to highlight patterns
- **Route prediction**: best‑effort connections between SAR points (not a confirmed track)
- **EEZ filtering**: pick one or more EEZs and a date range, then load data

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

## Deploy
- Backend (Render): see `DEPLOYMENT_RENDER.md` / `RENDER_CONFIG.md`
- Frontend (GitHub Pages): see `DEPLOYMENT_GITHUB_PAGES.md`

## Env vars (backend)
- **GFW_API_TOKEN**: required
- **FRONTEND_ORIGINS**: comma-separated origins (no paths), e.g. `https://charlotteprevost.github.io`

## Repo layout
- `backend/`: Flask API
- `frontend/`: static UI (Leaflet)
- `docs/`: GitHub Pages build output

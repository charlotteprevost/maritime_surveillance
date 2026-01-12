# Maritime Surveillance App

A web application for detecting and monitoring dark vessels using Global Fishing Watch (GFW) APIs and Synthetic Aperture Radar (SAR) data.

## 🎯 Features

- **Dark Vessel Detection**: Identify vessels not broadcasting AIS signals by combining SAR detections with AIS gap events
- **Interactive Heatmaps**: Visualize vessel detection density using GFW 4Wings API
- **EEZ-based Filtering**: Filter detections by Exclusive Economic Zones with multi-select support
- **Vessel Tracking**: Get detailed vessel information and activity events
- **Risk Assessment**: Calculate risk scores for vessels based on gap frequency and IUU status
- **Analytics Dashboard**: View summary statistics and trends
- **Real-time Data**: Access to latest SAR and AIS data from GFW
- **Responsive UI**: Works on desktop and mobile devices

## 🏗️ Architecture

- **Backend**: Flask API with GFW API integration
- **Frontend**: Leaflet.js map with modern responsive design
- **Data Sources**: Global Fishing Watch SAR presence, gap events, and vessel data
- **Service Layer**: Modular architecture with dedicated service for dark vessel logic
- **API Compliance**: Fully compliant with GFW API v3 specifications

## 🚀 Quick Start

### Prerequisites

1. **GFW API Token**: Get your API token from [Global Fishing Watch](https://globalfishingwatch.org/our-apis/tokens)
2. **Python 3.8+**: Required for the Flask backend
3. **Node.js**: Optional, for frontend development

### Backend Setup

1. **Navigate to backend directory**:
   ```bash
   cd backend
   ```

2. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

3. **Set environment variables**:
   Create a `.env` file in the `backend` directory:
   ```bash
   # Required
   GFW_API_TOKEN=your_gfw_api_token_here
   BACKEND_URL=http://localhost:5000
   FRONTEND_ORIGINS=http://localhost:8080,http://localhost:5000
   
   # Optional (with defaults)
   FLASK_DEBUG=false
   PORT=5000
   HOST=0.0.0.0
   ```
   
   Or export directly:
   ```bash
   export GFW_API_TOKEN="your_gfw_api_token_here"
   export BACKEND_URL="http://localhost:5000"
   export FRONTEND_ORIGINS="http://localhost:8080,http://localhost:5000"
   ```

4. **Run the Flask app**:
   ```bash
   python app.py
   ```

   The backend will be available at `http://localhost:5000`

### Frontend Setup

1. **Navigate to frontend directory**:
   ```bash
   cd frontend
   ```

2. **Open in browser**:
   - Simply open `index.html` in a web browser
   - Or serve with a local server: `python -m http.server 8080`

   The frontend will automatically connect to the backend at `http://localhost:5000`

## 📡 API Endpoints

### Core Endpoints

- **`GET /api/detections`** - Main endpoint for fetching dark vessel detections (SAR + gap events)
  - Parameters: `eez_ids`, `start_date`, `end_date`, `matched=false`
  - Returns: Combined SAR detections and AIS gap events

- **`GET /api/gaps`** - AIS gap events (intentional AIS disabling)
  - Parameters: `eez_ids`, `start_date`, `end_date`, `intentional_only=true`
  - Returns: Gap events filtered by region and date

- **`GET /api/analytics/dark-vessels`** - Analytics dashboard
  - Parameters: `eez_ids`, `start_date`, `end_date`
  - Returns: Summary statistics for dark vessels

- **`GET /api/analytics/risk-score/<vessel_id>`** - Vessel risk assessment
  - Parameters: `start_date`, `end_date`
  - Returns: Risk score (0-100) and contributing factors

- **`GET /api/vessels/<id>`** - Get vessel details and metadata
- **`GET /api/insights`** - Get vessel insights and risk assessments
- **`GET /api/events`** - Fetch vessel activity events

### Utility Endpoints

- **`GET /api/configs`** - Get application configuration (EEZ data, defaults, etc.)
- **`GET /api/bins/<z>`** - Get data bins for specific zoom levels

## 🗺️ Usage

1. **Select EEZ(s)**: Choose one or more Exclusive Economic Zones to monitor
   - Use multi-select dropdown to choose multiple zones
   - Group options available for countries with multiple territories (e.g., "United States (All territories)")
   - Individual territories also available (e.g., "Alaska", "Hawaii")

2. **Set Date Range**: Select start and end dates (max 30 days)
   - Use recent dates for best results (data available up to 5 days ago)

3. **Apply Filters**: Click "Apply Filters" to fetch detection data

4. **Explore Map**: 
   - Heatmap shows detection density
   - Color-coded markers show risk levels:
     - Red: High risk (both SAR + GAP)
     - Orange: Medium risk (SAR only or GAP only)
     - Yellow: Low risk (single detection)
   - Click markers for vessel details and events

5. **View Summary**: Check detection statistics in the right panel
   - Total dark vessels detected
   - SAR detections count
   - Gap events count
   - Unique vessels identified

## 🔧 Configuration

### GFW API Settings

The app uses several GFW datasets:
- **SAR Presence**: `public-global-sar-presence:latest` (filter: `matched=false` for dark vessels)
- **Gap Events**: `public-global-gaps-events:latest` (filter: `gap-intentional-disabling=true`)
- **Vessel Identity**: `public-global-vessel-identity:latest`
- **Fishing Events**: `public-global-fishing-events:latest`
- **Port Visits**: `public-global-port-visits-events:latest`

### Filter Options

- **Vessel Type**: Fishing, cargo, passenger, etc.
- **Gear Type**: Trawlers, longliners, seiners, etc.
- **Flag State**: Vessel registration country
- **Matched Status**: AIS-on vs AIS-off vessels (`matched=false` for dark vessels)

## 🧪 Testing

### Test Endpoints

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

### Common EEZ IDs

- `8493` - Canada
- `5677` - France  
- `8456` - United States
- `5696` - United Kingdom
- `8486` - China

Check `/api/configs` for full list.

### Notes

- **Date Range**: Use recent dates (within last 30 days) for best results
- **EEZ IDs**: Use numeric IDs from `/api/configs` response
- **GFW Token**: Make sure `GFW_API_TOKEN` is set in `.env` for full functionality
- **Multiple EEZs**: Use `["8493","5677"]` format (comma-separated IDs)
- **URL Encoding**: Square brackets `[]` in URLs need to be URL-encoded or use `--data-urlencode`

## 🚀 Deployment

### Backend Deployment

The backend can be deployed to various platforms. Ensure you set the following environment variables:

**Required:**
- `GFW_API_TOKEN` - Your Global Fishing Watch API token
- `BACKEND_URL` - Your backend service URL (e.g., `https://your-backend.onrender.com`)
- `FRONTEND_ORIGINS` - Comma-separated list of allowed frontend origins (e.g., `https://your-username.github.io`)

**Optional:**
- `FLASK_DEBUG` - Set to `"false"` for production
- `PORT` - Server port (default: 5000, but platforms like Render use 10000)
- `HOST` - Server host (use `0.0.0.0` for production)

### Frontend Deployment

The frontend is static HTML/JS and can be deployed to:
- **GitHub Pages** (recommended for free hosting)
- **Netlify**
- **Vercel**
- Any static file hosting service

Update `frontend/config.js` or ensure the backend URL is correctly configured to point to your deployed backend.

### Deployment Platforms

See the [Deployment Platforms](#-deployment-platforms) section below for recommended free hosting options.

## 🚨 Rate Limiting

GFW API has rate limits:
- **4Wings API**: 1 request per 250ms
- **Events API**: 100 requests per minute
- **Vessel API**: 1000 requests per hour

The app includes automatic rate limiting and request caching.

## ✅ API Compliance

All endpoints are fully compliant with GFW API v3:

- **Events API**: POST for regions, GET for simple queries
- **4Wings Report**: Temporal resolution DAILY/MONTHLY/ENTIRE (not HOURLY)
- **Vessel Details**: Correct parameter names (`dataset` for single vessel)
- **Gap Events**: Proper POST body format with `gapIntentionalDisabling`
- **Filter Parsing**: Correct handling of `matched` and `neural_vessel_type` parameters

See `PROJECT_KANBAN.md` for detailed compliance checklist.

## 🐛 Troubleshooting

### Common Issues

1. **"GFW_API_TOKEN not set"**
   - Ensure you've set the environment variable in `.env` file
   - Check that your token is valid
   - Restart the Flask app after setting the token

2. **"No detections found"**
   - Verify your date range is within available data (up to 5 days ago)
   - Check that selected EEZs have data coverage
   - Ensure filters aren't too restrictive
   - Try a different date range or EEZ

3. **Map not loading**
   - Check browser console for JavaScript errors
   - Verify backend is running and accessible at `http://localhost:5000`
   - Check network tab for failed API calls
   - Ensure frontend is using correct backend URL (configured in `frontend/config.js`)

4. **422 Client Error from GFW API**
   - Check that date range is valid (not in the future)
   - Verify EEZ IDs are correct numeric values
   - Ensure filter format is correct (see API Compliance section)

### Debug Mode

Enable debug logging:
```bash
export FLASK_DEBUG=true
export FLASK_ENV=development
python app.py
```

### Environment Variables Reference

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `GFW_API_TOKEN` | Yes | - | Global Fishing Watch API token |
| `BACKEND_URL` | Yes* | `http://localhost:5000` | Backend service URL (used in API responses) |
| `FRONTEND_ORIGINS` | Yes* | `http://localhost:8080,http://localhost:5000` | Comma-separated CORS origins |
| `FLASK_DEBUG` | No | `false` | Enable Flask debug mode |
| `PORT` | No | `5000` | Server port |
| `HOST` | No | `0.0.0.0` | Server host binding |
| `QGIS_PATH` | No | `/Applications/QGIS-LTR.app/...` | QGIS installation path (local dev only) |
| `PROJECT_PATH` | No | `""` | QGIS project path (local dev only) |

*Required for production deployment

## 📁 Project Structure

```
backend/
├── routes/
│   ├── api.py           # Main router
│   ├── detections.py     # SAR detections
│   ├── gaps.py          # Gap events
│   ├── analytics.py     # Analytics dashboard
│   ├── vessels.py       # Vessel details
│   ├── insights.py      # Insights
│   └── configs.py       # Configuration
├── services/
│   └── dark_vessel_service.py  # Core dark vessel logic
├── utils/
│   └── gfw_client.py    # GFW API client
└── configs/
    └── config.py        # Application configuration
frontend/
├── main.js              # Main application logic
├── utils.js             # Utility functions
├── config.js            # Frontend configuration
└── index.html           # Main HTML file
```

## 🔮 Future Enhancements

- [ ] Enhanced EEZ selection UI with search and visual boundaries
- [ ] Time-lapse animation for gap events
- [ ] Vessel trail visualization
- [ ] Export functionality (CSV, GeoJSON)
- [ ] Enhanced analytics with charts and trends
- [ ] Real-time data streaming
- [ ] User authentication and saved searches
- [ ] Machine learning-based risk assessment
- [ ] Automated monitoring and alerts

## 🌐 Deployment Platforms

### Free Backend Hosting Options

1. **Render** (Recommended)
   - ✅ Free tier available
   - ✅ Automatic deployments from GitHub
   - ✅ Environment variable management
   - ✅ HTTPS included
   - ⚠️ Free tier spins down after 15 minutes of inactivity
   - 📝 See `backend/render.yaml` for configuration

2. **Railway**
   - ✅ Free tier with $5/month credit
   - ✅ Fast deployments
   - ✅ No cold starts
   - ✅ Easy GitHub integration
   - ⚠️ Credit-based pricing (may incur small costs)

3. **Fly.io**
   - ✅ Generous free tier
   - ✅ Global edge deployment
   - ✅ Fast cold starts
   - ✅ Great for Python apps
   - ⚠️ Requires credit card (but free tier is truly free)

4. **PythonAnywhere**
   - ✅ Free tier available
   - ✅ Python-focused
   - ✅ Easy setup
   - ⚠️ Limited to Python 3.8/3.9
   - ⚠️ Slower than other options

5. **Heroku** (Alternative)
   - ⚠️ No longer has a free tier
   - ✅ Excellent documentation
   - ✅ Easy deployment
   - 💰 Paid plans start at $5/month

6. **Replit**
   - ✅ Free tier available
   - ✅ In-browser IDE
   - ✅ Easy GitHub integration
   - ⚠️ Best for development/testing

### Free Frontend Hosting Options

1. **GitHub Pages** (Recommended)
   - ✅ Completely free
   - ✅ Automatic HTTPS
   - ✅ Custom domains supported
   - ✅ Easy deployment via GitHub Actions
   - ✅ Perfect for static sites

2. **Netlify**
   - ✅ Free tier with generous limits
   - ✅ Automatic deployments
   - ✅ Edge functions available
   - ✅ Great performance

3. **Vercel**
   - ✅ Free tier available
   - ✅ Excellent performance
   - ✅ Automatic deployments
   - ✅ Edge network

4. **Cloudflare Pages**
   - ✅ Free tier available
   - ✅ Global CDN
   - ✅ Fast deployments
   - ✅ Great for static sites

### Recommended Setup

**For this project:**
- **Backend**: Render or Railway (both have good free tiers)
- **Frontend**: GitHub Pages (completely free, perfect for static sites)

**Deployment Steps:**
1. Push backend to GitHub
2. Deploy backend to Render/Railway
3. Set environment variables in deployment platform
4. Push frontend to GitHub
5. Enable GitHub Pages for frontend
6. Update frontend `config.js` with backend URL

## 📚 Resources

- [Global Fishing Watch API Documentation](https://globalfishingwatch.org/our-apis)
- [4Wings API Guide](https://globalfishingwatch.org/our-apis/4wings)
- [Maritime Domain Awareness](https://globalfishingwatch.org/our-work/maritime-domain-awareness)
- [Leaflet.js Documentation](https://leafletjs.com/)
- [Render Documentation](https://render.com/docs)
- [Railway Documentation](https://docs.railway.app/)
- [Fly.io Documentation](https://fly.io/docs/)

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🙏 Acknowledgments

- Global Fishing Watch for providing the SAR and vessel data APIs
- Leaflet.js community for the mapping library
- OpenStreetMap contributors for base map tiles

---

**Last Updated:** 2025-01-05
**Status:** Production Ready - Backend configured for deployment, frontend ready for GitHub Pages

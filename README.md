# Maritime Surveillance App

A web application for detecting and monitoring dark vessels using Global Fishing Watch (GFW) APIs and Synthetic Aperture Radar (SAR) data.

## 🎯 Features

- **Dark Vessel Detection**: Identify vessels not broadcasting AIS signals
- **Interactive Heatmaps**: Visualize vessel detection density using GFW 4Wings API
- **EEZ-based Filtering**: Filter detections by Exclusive Economic Zones
- **Vessel Tracking**: Get detailed vessel information and activity events
- **Real-time Data**: Access to latest SAR and AIS data from GFW
- **Responsive UI**: Works on desktop and mobile devices

## 🏗️ Architecture

- **Backend**: Flask API with GFW API integration
- **Frontend**: Leaflet.js map with modern responsive design
- **Data Sources**: Global Fishing Watch SAR presence and vessel data
- **Caching**: Request caching to optimize API calls

## 🚀 Quick Start

### Prerequisites

1. **GFW API Token**: Get your API token from [Global Fishing Watch](https://globalfishingwatch.org/our-apis/tokens)
2. **Python 3.8+**: Required for the Flask backend
3. **Node.js**: Optional, for frontend development

### Backend Setup

1. **Navigate to backend directory**:
   ```bash
   cd webapps/maritime/backend
   ```

2. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

3. **Set environment variables**:
   ```bash
   export GFW_API_TOKEN="your_gfw_api_token_here"
   ```

4. **Run the Flask app**:
   ```bash
   python app.py
   ```

   The backend will be available at `http://localhost:5000`

### Frontend Setup

1. **Navigate to frontend directory**:
```bash
   cd webapps/maritime/frontend
   ```

2. **Open in browser**:
   - Simply open `index.html` in a web browser
   - Or serve with a local server: `python -m http.server 8000`

## 📡 API Endpoints

### Core Endpoints

- **`/api/detections`** - Main endpoint for fetching SAR detections
- **`/api/summary`** - Get summary statistics and reports
- **`/api/events`** - Fetch vessel activity events
- **`/api/vessels/<id>`** - Get vessel details and metadata
- **`/api/insights`** - Get vessel insights and risk assessments

### Utility Endpoints

- **`/api/configs`** - Get application configuration
- **`/api/eez-data`** - Get EEZ boundary data
- **`/api/generate-style`** - Generate custom heatmap styles
- **`/api/bins/<z>`** - Get data bins for specific zoom levels

## 🗺️ Usage

1. **Select EEZ(s)**: Choose one or more Exclusive Economic Zones to monitor
2. **Set Date Range**: Select start and end dates (max 30 days)
3. **Apply Filters**: Click "Apply Filters" to fetch detection data
4. **Explore Map**: 
   - Heatmap shows detection density
   - Red dots show individual vessel detections
   - Click dots for vessel details and events
5. **View Summary**: Check detection statistics in the right panel

## 🔧 Configuration

### GFW API Settings

The app uses several GFW datasets:
- **SAR Presence**: `public-global-sar-presence:latest`
- **Vessel Identity**: `public-global-vessel-identity:latest`
- **Fishing Events**: `public-global-fishing-events:latest`
- **Port Visits**: `public-global-port-visits-events:latest`

### Filter Options

- **Vessel Type**: Fishing, cargo, passenger, etc.
- **Gear Type**: Trawlers, longliners, seiners, etc.
- **Flag State**: Vessel registration country
- **Matched Status**: AIS-on vs AIS-off vessels

## 🚨 Rate Limiting

GFW API has rate limits:
- **4Wings API**: 1 request per 250ms
- **Events API**: 100 requests per minute
- **Vessel API**: 1000 requests per hour

The app includes automatic rate limiting and request caching.

## 🐛 Troubleshooting

### Common Issues

1. **"GFW_API_TOKEN not set"**
   - Ensure you've set the environment variable
   - Check that your token is valid

2. **"No detections found"**
   - Verify your date range is within available data
   - Check that selected EEZs have data coverage
   - Ensure filters aren't too restrictive

3. **Map not loading**
   - Check browser console for JavaScript errors
   - Verify backend is running and accessible
   - Check network tab for failed API calls

### Debug Mode

Enable debug logging:
```bash
export FLASK_DEBUG=true
export FLASK_ENV=development
```

## 🔮 Future Enhancements

- [ ] Advanced vessel clustering and heatmap toggles
- [ ] Real-time data streaming
- [ ] Export functionality (CSV, GeoJSON)
- [ ] User authentication and saved searches
- [ ] Integration with other maritime data sources
- [ ] Machine learning-based risk assessment

## 📚 Resources

- [Global Fishing Watch API Documentation](https://globalfishingwatch.org/our-apis)
- [4Wings API Guide](https://globalfishingwatch.org/our-apis/4wings)
- [Maritime Domain Awareness](https://globalfishingwatch.org/our-work/maritime-domain-awareness)

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

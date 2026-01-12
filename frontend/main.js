import config from './config.js';
import {
  buildEEZSelect,
  fetchConfigs,
  getSelectedEEZIds,
  renderSelectionInfo,
  showError,
  showSuccess,
  validateDateRange
} from './utils.js';
const { debugLog } = config;

let map, layerGroup, heatmapLayer, eezBoundaryLayer;
let currentFilters = {};

// Initialize the application
async function init() {
  try {
    // Fetch configurations and EEZ data
    await fetchConfigs();

    debugLog.log('Configs fetched successfully');
    debugLog.log('CONFIGS:', window.CONFIGS);

    // Build EEZ dropdown
    buildEEZSelect();

    // Initialize map
    initMap();

    // Set up event listeners
    setupEventListeners();

    // Set default dates
    setDefaultDates();

  } catch (error) {
    console.error('Initialization failed:', error);
    showError('Failed to initialize application');
  }
}

function initMap() {
  // Initialize the map centered on a global view
  map = L.map('map').setView([20, 0], 2);

  // Add base tile layer
  L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
    attribution: '© OpenStreetMap contributors'
  }).addTo(map);

  // Set up legend
  setupLegend();

  // Set up layer group for detections
  layerGroup = L.layerGroup().addTo(map);

  // Set up layer group for EEZ boundaries
  eezBoundaryLayer = L.layerGroup().addTo(map);
  debugLog.log('EEZ boundary layer initialized');
}

function setupEventListeners() {
  // About toggle
  document.getElementById('about-toggle').addEventListener('click', toggleAbout);

  // Date inputs
  document.getElementById('start').addEventListener('change', validateDates);
  document.getElementById('end').addEventListener('change', validateDates);

  // EEZ selection (only register once)
  document.getElementById('eez-select').addEventListener('change', onEEZChange);

  // Apply filters button
  document.getElementById('applyFilters').addEventListener('click', applyFilters);

  // Add event listener for enter key
  document.getElementById('start').addEventListener('keypress', (e) => {
    if (e.key === 'Enter') {
      applyFilters();
    }
  });

  document.getElementById('end').addEventListener('keypress', (e) => {
    if (e.key === 'Enter') {
      applyFilters();
    }
  });
}

function setDefaultDates() {

  const today = new Date();

  // end must be today minus 7 days 
  const end = new Date(today.getTime() - 7 * 24 * 60 * 60 * 1000);
  // start must be end date minus 7 days
  const start = new Date(end.getTime() - 7 * 24 * 60 * 60 * 1000);


  // date value must conform to the required format, "yyyy-MM-dd"
  const endDate = end.toISOString().split('T')[0];
  const startDate = start.toISOString().split('T')[0];
  debugLog.log('End date:', endDate);
  debugLog.log('Start date:', startDate);

  document.getElementById('start').value = startDate;
  document.getElementById('end').value = endDate;

  validateDates();
}

function validateDates() {
  const start = document.getElementById('start').value;
  const end = document.getElementById('end').value;
  const applyBtn = document.getElementById('applyFilters');

  if (start && end) {
    if (validateDateRange(start, end)) {
      applyBtn.disabled = false;
      showSuccess('Date range is valid');
    } else {
      applyBtn.disabled = true;
    }
  } else {
    applyBtn.disabled = true;
  }
}

function onEEZChange() {
  // Use setTimeout to ensure the selection has stabilized after group handler runs
  setTimeout(() => {
    const selectedEEZs = getSelectedEEZIds();

    // live popup summary (countries + EEZs)
    renderSelectionInfo(selectedEEZs);

    // Update EEZ boundaries on map
    updateEEZBoundaries(selectedEEZs);

    const applyBtn = document.getElementById('applyFilters');
    if (selectedEEZs.length > 0) {
      validateDates();
      showSuccess(`Selected ${selectedEEZs.length} EEZ(s)`);
      applyBtn.disabled = false;
    } else {
      applyBtn.disabled = true;
    }
  }, 0);
}

async function updateEEZBoundaries(eezIds) {
  debugLog.log('updateEEZBoundaries called with:', eezIds);

  // Ensure layer is initialized
  if (!eezBoundaryLayer) {
    console.error('eezBoundaryLayer not initialized!');
    return;
  }

  // Clear existing boundaries
  eezBoundaryLayer.clearLayers();

  if (!eezIds || eezIds.length === 0) {
    debugLog.log('No EEZ IDs provided, cleared boundaries');
    return;
  }

  try {
    // Fetch boundaries from backend
    const params = new URLSearchParams({
      eez_ids: JSON.stringify(eezIds)
    });

    const response = await fetch(`${config.backendUrl}/api/eez-boundaries?${params}`);
    if (!response.ok) {
      throw new Error(`HTTP ${response.status}: ${response.statusText}`);
    }

    const data = await response.json();
    debugLog.log('EEZ boundaries response:', data);

    if (!data.boundaries || data.boundaries.length === 0) {
      console.warn('No boundaries returned from API');
      return;
    }

    // Add each boundary to the map
    data.boundaries.forEach(boundary => {
      debugLog.log('Processing boundary for EEZ:', boundary.eez_id);
      if (boundary.geometry) {
        try {
          const geoJsonLayer = L.geoJSON(boundary.geometry, {
            style: {
              color: '#3388ff',
              weight: 3,
              opacity: 0.9,
              fillColor: '#3388ff',
              fillOpacity: 0.15
            }
          });

          // Add label with EEZ name
          const eezInfo = window.CONFIGS?.EEZ_DATA?.[boundary.eez_id];
          if (eezInfo) {
            geoJsonLayer.bindTooltip(eezInfo.label, {
              permanent: false,
              direction: 'center',
              className: 'eez-boundary-label'
            });
          }

          geoJsonLayer.addTo(eezBoundaryLayer);
          debugLog.log('Added boundary layer for EEZ:', boundary.eez_id, 'Total layers:', eezBoundaryLayer.getLayers().length);

          // Verify the layer was added and get its bounds
          const layerBounds = geoJsonLayer.getBounds();
          if (layerBounds && layerBounds.isValid()) {
            debugLog.log('Boundary bounds for', boundary.eez_id, ':', layerBounds.toBBoxString());
          } else {
            console.warn('Invalid bounds for boundary', boundary.eez_id);
          }
        } catch (error) {
          console.error('Error adding boundary to map:', error, boundary);
        }
      } else {
        console.warn('Boundary missing geometry for EEZ:', boundary.eez_id);
      }
    });

    // Fit map to show all boundaries after adding them
    const layers = eezBoundaryLayer.getLayers();
    if (data.boundaries.length > 0 && layers.length > 0) {
      // Collect bounds from all layers
      let combinedBounds = null;
      layers.forEach(layer => {
        if (layer.getBounds) {
          const layerBounds = layer.getBounds();
          if (layerBounds && layerBounds.isValid()) {
            if (!combinedBounds) {
              combinedBounds = layerBounds;
            } else {
              combinedBounds.extend(layerBounds);
            }
          }
        }
      });

      if (combinedBounds && combinedBounds.isValid()) {
        map.fitBounds(combinedBounds, { padding: [50, 50] });
        debugLog.log('Fitted map to boundaries:', combinedBounds.toBBoxString());
      } else {
        console.warn('Invalid or missing bounds for boundaries');
      }
    } else {
      console.warn('No layers added to boundary layer group');
    }
  } catch (error) {
    console.error('Failed to fetch EEZ boundaries:', error);
    // Don't show error to user - boundaries are optional
  }
}

async function applyFilters() {
  const startDate = document.getElementById('start').value;
  const endDate = document.getElementById('end').value;
  console.log('Start date:', startDate);
  console.log('End date:', endDate);

  const selectedEEZs = getSelectedEEZIds();
  console.log('Selected EEZs:', selectedEEZs);

  if (!selectedEEZs.length || !startDate || !endDate) {
    showError('Please select EEZ(s) and date range');
    return;
  }

  // Show loading spinner
  document.getElementById("loading-spinner").classList.remove("hidden");

  try {
    // Build filters object - default to dark vessels (matched=false)
    const filters = {
      eez_ids: JSON.stringify(selectedEEZs),
      start_date: startDate,
      end_date: endDate,
      interval: 'DAY',
      temporal_aggregation: 'false',
      matched: 'false' // Dark vessels only
    };

    // Store current filters
    currentFilters = filters;

    debugLog.log('Filters being sent to backend:', filters);

    // Build the absolute URL using the configured backend URL
    // Priority: window.CONFIGS.backendUrl (from API) > config.backendUrl (local dev fallback)
    const backendUrl = (window.CONFIGS && window.CONFIGS.backendUrl) || config.backendUrl;
    if (!backendUrl) {
      throw new Error('Backend URL not configured. Please ensure the backend is running and accessible.');
    }
    const url = new URL('/api/detections', backendUrl);
    url.search = new URLSearchParams(filters);

    // Fetch detections from backend with timeout
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), 120000); // 2 minute timeout

    let response;
    try {
      response = await fetch(url.toString(), { signal: controller.signal });
      clearTimeout(timeoutId);
    } catch (error) {
      clearTimeout(timeoutId);
      if (error.name === 'AbortError') {
        throw new Error('Request timed out after 2 minutes. Please try with a smaller date range or fewer EEZs.');
      }
      throw error;
    }

    if (!response.ok) {
      throw new Error(`HTTP ${response.status}: ${response.statusText}`);
    }

    const data = await response.json();
    debugLog.log('Detection data received:', {
      dark_vessels: data.dark_vessels?.summary,
      sar_detections_count: data.dark_vessels?.sar_detections?.length || 0,
      gap_events_count: data.dark_vessels?.gap_events?.length || 0,
      summaries_count: data.summaries?.length,
      has_tile_url: !!data.tile_url
    });

    // Update map with new data (tiles may fail due to CORS, but that's OK)
    updateMapWithDetections(data);

    // Update summary stats with dark vessel data
    updateSummaryStats(data.summaries, data.dark_vessels);

    const vesselCount = data.dark_vessels?.summary?.unique_vessels || 0;
    showSuccess(`Loaded ${vesselCount} dark vessel${vesselCount !== 1 ? 's' : ''}`);

  } catch (error) {
    console.error('Error applying filters:', error);
    showError('Failed to fetch detection data: ' + error.message);
  } finally {
    // Hide loading spinner
    document.getElementById("loading-spinner").classList.add("hidden");
  }
}

function updateMapWithDetections(data) {
  // Clear existing layers
  if (heatmapLayer) {
    map.removeLayer(heatmapLayer);
  }
  layerGroup.clearLayers();

  // Add heatmap layer (handle CORS/ORB errors gracefully)
  if (data.tile_url) {
    try {
      // Ensure tile URL uses backend server, not frontend
      const backendUrl = (window.CONFIGS && window.CONFIGS.backendUrl) || config.backendUrl;
      if (!backendUrl) {
        console.warn('Backend URL not available, skipping tile layer');
        return;
      }
      let tileUrl = data.tile_url;

      // If tile URL is relative, prepend backend URL
      if (tileUrl.startsWith('/')) {
        tileUrl = backendUrl + tileUrl;
      } else if (!tileUrl.startsWith('http')) {
        tileUrl = backendUrl + '/' + tileUrl;
      }

      heatmapLayer = L.tileLayer(tileUrl, {
        attribution: "Powered by Global Fishing Watch",
        opacity: 0.7,
        errorTileUrl: 'data:image/gif;base64,R0lGODlhAQABAIAAAAAAAP///yH5BAEAAAAALAAAAAABAAEAAAIBRAA7', // Transparent 1x1 pixel
        crossOrigin: false // Don't use CORS for proxied tiles
      });

      // Handle tile loading errors
      heatmapLayer.on('tileerror', function (error, tile) {
        console.warn('Tile loading error:', error);
        // Don't show error to user - tiles are optional
      });

      heatmapLayer.addTo(map);
      debugLog.log('Added heatmap tile layer:', tileUrl);
    } catch (error) {
      console.warn('Failed to add heatmap layer:', error);
      // Don't show error - tiles are optional, detections still work
    }
  }

  // Add detection markers from dark_vessels data
  if (data.dark_vessels) {
    addDarkVesselMarkers(data.dark_vessels);
  }

  // Also try summaries if available (fallback)
  if (data.summaries && data.summaries.length > 0) {
    addDetectionDots(data.summaries);
  }

  // Set up click handlers for interaction
  setupMapInteraction();

  // Fit map to EEZ bounds if available
  fitMapToEEZs(data.summaries);
}

function addDarkVesselMarkers(darkVessels) {
  let markerCount = 0;

  // Log the structure to understand what we're working with
  debugLog.log('Dark vessels data structure:', {
    has_sar: !!darkVessels.sar_detections,
    sar_count: darkVessels.sar_detections?.length || 0,
    has_gaps: !!darkVessels.gap_events,
    gap_count: darkVessels.gap_events?.length || 0,
    sar_sample: darkVessels.sar_detections?.[0],
    gap_sample: darkVessels.gap_events?.[0]
  });

  // Add SAR detections (unmatched vessels)
  if (darkVessels.sar_detections && Array.isArray(darkVessels.sar_detections)) {
    darkVessels.sar_detections.forEach((detection, index) => {
      // SAR detections might have lat/lon or different structure
      // Check various possible field names
      const lat = detection.latitude || detection.lat || detection.lat_center ||
        detection.center_lat || detection.y || detection[1];
      const lon = detection.longitude || detection.lon || detection.lon_center ||
        detection.center_lon || detection.x || detection[0];

      // Also check if it's an array format [lon, lat]
      let finalLat = lat;
      let finalLon = lon;
      if (Array.isArray(detection) && detection.length >= 2) {
        finalLon = detection[0];
        finalLat = detection[1];
      }

      if (finalLat != null && finalLon != null && !isNaN(finalLat) && !isNaN(finalLon)) {
        const marker = L.circleMarker([finalLat, finalLon], {
          radius: 6,
          fillColor: '#ff8800', // Orange for SAR only
          color: '#cc6600',
          weight: 2,
          opacity: 0.8,
          fillOpacity: 0.6
        });

        const popupContent = `
          <div class="detection-popup">
            <h4>SAR Detection (Unmatched)</h4>
            <p><strong>Location:</strong> ${finalLat.toFixed(4)}, ${finalLon.toFixed(4)}</p>
            ${detection.vessel_id ? `<p><strong>Vessel ID:</strong> <a href="#" class="vessel-link" data-vessel="${detection.vessel_id}">${detection.vessel_id}</a></p>` : ''}
            <p><strong>Type:</strong> SAR Detection</p>
          </div>
        `;

        marker.bindPopup(popupContent);
        layerGroup.addLayer(marker);
        markerCount++;
      } else if (index < 3) {
        // Log first few to debug structure
        console.warn('SAR detection missing coordinates:', detection);
      }
    });
  }

  // Add gap events (AIS gaps)
  if (darkVessels.gap_events && Array.isArray(darkVessels.gap_events)) {
    darkVessels.gap_events.forEach((gap, index) => {
      // Gap events might have different structure
      const lat = gap.latitude || gap.lat || gap.startLat || gap.endLat ||
        gap.centerLat || gap.y;
      const lon = gap.longitude || gap.lon || gap.startLon || gap.endLon ||
        gap.centerLon || gap.x;

      if (lat != null && lon != null && !isNaN(lat) && !isNaN(lon)) {
        const marker = L.circleMarker([lat, lon], {
          radius: 6,
          fillColor: '#ff8800', // Orange for gap only
          color: '#cc6600',
          weight: 2,
          opacity: 0.8,
          fillOpacity: 0.6
        });

        const popupContent = `
          <div class="detection-popup">
            <h4>AIS Gap Event</h4>
            <p><strong>Location:</strong> ${lat.toFixed(4)}, ${lon.toFixed(4)}</p>
            ${gap.vesselId ? `<p><strong>Vessel ID:</strong> <a href="#" class="vessel-link" data-vessel="${gap.vesselId}">${gap.vesselId}</a></p>` : ''}
            <p><strong>Type:</strong> AIS Gap</p>
            ${gap.start ? `<p><strong>Start:</strong> ${gap.start}</p>` : ''}
            ${gap.end ? `<p><strong>End:</strong> ${gap.end}</p>` : ''}
          </div>
        `;

        marker.bindPopup(popupContent);
        layerGroup.addLayer(marker);
        markerCount++;
      } else if (index < 3) {
        // Log first few to debug structure
        console.warn('Gap event missing coordinates:', gap);
      }
    });
  }

  debugLog.log(`Added ${markerCount} dark vessel markers to map`);
  if (markerCount === 0) {
    console.warn('No markers added - check data structure in console above');
  }
}

function addDetectionDots(summaries) {
  summaries.forEach(summary => {
    if (summary.summary && summary.summary.data) {
      summary.summary.data.forEach(detection => {
        if (detection.latitude && detection.longitude) {
          // Color-code by risk: red for high risk, orange for medium
          const marker = L.circleMarker([detection.latitude, detection.longitude], {
            radius: 6,
            fillColor: detection.risk_score > 50 ? '#cc0000' : '#ff8800',
            color: detection.risk_score > 50 ? '#990000' : '#cc6600',
            weight: 2,
            opacity: 0.8,
            fillOpacity: 0.6
          });

          // Add popup with detection info
          const popupContent = `
            <div class="detection-popup">
              <h4>Vessel Detection</h4>
              <p><strong>Time:</strong> ${detection.timestamp || 'Unknown'}</p>
              <p><strong>Location:</strong> ${detection.latitude.toFixed(4)}, ${detection.longitude.toFixed(4)}</p>
              ${detection.vessel_id ? `<p><strong>Vessel ID:</strong> <a href="#" class="vessel-link" data-vessel="${detection.vessel_id}">${detection.vessel_id}</a></p>` : ''}
              <button class="get-events-btn" data-lat="${detection.latitude}" data-lng="${detection.longitude}">Get Events</button>
            </div>
          `;

          marker.bindPopup(popupContent);
          layerGroup.addLayer(marker);
        }
      });
    }
  });
}

function setupMapInteraction() {
  // Handle vessel link clicks
  document.addEventListener('click', async (e) => {
    if (e.target.classList.contains('vessel-link')) {
      e.preventDefault();
      const vesselId = e.target.dataset.vessel;
      await showVesselDetails(vesselId);
    }

    if (e.target.classList.contains('get-events-btn')) {
      const lat = parseFloat(e.target.dataset.lat);
      const lng = parseFloat(e.target.dataset.lng);
      await getEventsForLocation(lat, lng);
    }
  });
}

async function showVesselDetails(vesselId) {
  try {
    const backendUrl = (window.CONFIGS && window.CONFIGS.backendUrl) || config.backendUrl;
    if (!backendUrl) {
      throw new Error('Backend URL not configured');
    }
    const vesselUrl = new URL(`/api/vessels/${vesselId}`, backendUrl);
    const response = await fetch(vesselUrl.toString());
    const data = await response.json();

    // Show vessel details in a modal or popup
    showVesselModal(data);

  } catch (error) {
    console.error('Error fetching vessel details:', error);
    showError('Failed to fetch vessel details');
  }
}

async function getEventsForLocation(lat, lng) {
  try {
    const filters = {
      ...currentFilters,
      lat: lat,
      lng: lng
    };
    const backendUrl = (window.CONFIGS && window.CONFIGS.backendUrl) || config.backendUrl;
    if (!backendUrl) {
      throw new Error('Backend URL not configured');
    }
    const eventsUrl = new URL('/api/events', backendUrl);
    eventsUrl.search = new URLSearchParams(filters);
    const response = await fetch(eventsUrl.toString());
    const data = await response.json();

    // Show events in a popup
    showEventsPopup(lat, lng, data);

  } catch (error) {
    console.error('Error fetching events:', error);
    showError('Failed to fetch events');
  }
}

function showVesselModal(vesselData) {
  // Create and show a modal with vessel information
  const modal = document.createElement('div');
  modal.className = 'vessel-modal';
  modal.innerHTML = `
    <div class="modal-content">
      <span class="close">&times;</span>
      <h2>Vessel Details</h2>
      <pre>${JSON.stringify(vesselData, null, 2)}</pre>
    </div>
  `;

  document.body.appendChild(modal);

  // Close modal functionality
  modal.querySelector('.close').onclick = () => modal.remove();
  modal.onclick = (e) => {
    if (e.target === modal) modal.remove();
  };
}

function showEventsPopup(lat, lng, eventsData) {
  const popup = L.popup()
    .setLatLng([lat, lng])
    .setContent(`
      <div class="events-popup">
        <h4>Events at this location</h4>
        <pre>${JSON.stringify(eventsData, null, 2)}</pre>
      </div>
    `)
    .openOn(map);
}

function updateSummaryStats(summaries, darkVessels) {
  const summarySection = document.getElementById('summary-stats');
  const summaryList = document.getElementById('summary-list');

  if (!summaries || summaries.length === 0) {
    summarySection?.classList.add('hidden');
    return;
  }

  summarySection?.classList.remove('hidden');

  // Use dark vessel summary if available
  const stats = darkVessels?.summary || {};
  const totalVessels = stats.unique_vessels || 0;
  const sarDetections = stats.total_sar_detections || 0;
  const gapEvents = stats.total_gap_events || 0;

  summaryList.innerHTML = `
    <li><strong>Dark Vessels:</strong> ${totalVessels}</li>
    <li><strong>SAR Detections:</strong> ${sarDetections}</li>
    <li><strong>AIS Gap Events:</strong> ${gapEvents}</li>
    <li><strong>EEZs:</strong> ${summaries.length}</li>
  `;
}

function fitMapToEEZs(summaries) {
  if (!summaries || summaries.length === 0) return;

  // Get EEZ bounds from the data
  const bounds = [];
  summaries.forEach(summary => {
    if (summary.summary && summary.summary.data) {
      summary.summary.data.forEach(detection => {
        if (detection.latitude && detection.longitude) {
          bounds.push([detection.latitude, detection.longitude]);
        }
      });
    }
  });

  if (bounds.length > 0) {
    map.fitBounds(bounds, { padding: [20, 20] });
  }
}

function toggleAbout() {
  const aboutContainer = document.getElementById('about-container');
  aboutContainer.classList.toggle('collapsed');
}

function setupLegend() {
  const legend = L.control({ position: "topright" });

  legend.onAdd = function () {
    const div = L.DomUtil.create("div", "map-legend");
    div.innerHTML = `
      <strong style="text-decoration:underline;">Legend</strong><br/>
      <i class="legend-dot" style="background:#cc0000;"></i> Vessel Detection<br>
      <i class="legend-dot" style="background:#ff4444;"></i> Heatmap<br><br>

      <strong>Detection Density</strong><br/>
      <div class="ramp-bar"></div>
      <div class="ramp-labels">
        <span>Low</span><span>High</span>
      </div>
    `;
    return div;
  };

  legend.addTo(map);
}

// Initialize when DOM is loaded
document.addEventListener('DOMContentLoaded', init);

import {
  buildEEZSelect,
  fetchConfigs,
  getSelectedEEZIds,
  validateDateRange,
  renderSelectionInfo,
  showError,
  showSuccess
} from './utils.js';

let map, layerGroup, heatmapLayer;
let currentFilters = {};

// Initialize the application
async function init() {
  try {
    // Fetch configurations and EEZ data
    await fetchConfigs();
    
    console.log('Configs fetched successfully');
    console.log(window.CONFIGS);
    
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
}

function setupEventListeners() {

  
  // About toggle
  document.getElementById('about-toggle').addEventListener('click', toggleAbout);
  
  // Date inputs
  document.getElementById('start').addEventListener('change', validateDates);
  document.getElementById('end').addEventListener('change', validateDates);
  
  // EEZ selection
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

  document.getElementById('eez-select').addEventListener('change', onEEZChange);
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
  console.log('End date:', endDate);
  console.log('Start date:', startDate);

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
  const selectedEEZs = getSelectedEEZIds();

  // live popup summary (countries + EEZs)
  renderSelectionInfo(selectedEEZs);

  const applyBtn = document.getElementById('applyFilters');
  if (selectedEEZs.length > 0) {
    validateDates();
    showSuccess(`Selected ${selectedEEZs.length} EEZ(s)`);
    applyBtn.disabled = false;
  } else {
    applyBtn.disabled = true;
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
    // Build filters object
    const filters = {
      eez_ids: JSON.stringify(selectedEEZs), // Ensure eez_ids are sent as a JSON array
      start_date: startDate,
      end_date: endDate,
      interval: 'DAY',
      temporal_aggregation: 'false',
      matched: 'false' // Default to dark vessels
    };

    // Store current filters
    currentFilters = filters;

    console.log('Filters being sent to backend:', filters);

    // Build the absolute URL using the configured backend URL
    const base = window.CONFIGS && window.CONFIGS.backendUrl ? window.CONFIGS.backendUrl : '';
    const url = new URL('/api/detections', base || window.location.origin);
    url.search = new URLSearchParams(filters);

    // Fetch detections from backend
    const response = await fetch(url.toString());

    if (!response.ok) {
      throw new Error(`HTTP ${response.status}: ${response.statusText}`);
    }

    const data = await response.json();

    // Update map with new data
    updateMapWithDetections(data);

    // Update summary stats
    updateSummaryStats(data.summaries);

    showSuccess(`Loaded detections for ${selectedEEZs.length} EEZ(s)`);

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
  
  // Add heatmap layer
  if (data.tile_url) {
    heatmapLayer = L.tileLayer(data.tile_url, {
    attribution: "Powered by Global Fishing Watch",
    opacity: 0.7
  }).addTo(map);
  }
  
  // Add detection dots if available
  if (data.summaries && data.summaries.length > 0) {
    addDetectionDots(data.summaries);
  }
  
  // Set up click handlers for interaction
  setupMapInteraction();
  
  // Fit map to EEZ bounds if available
  fitMapToEEZs(data.summaries);
}

function addDetectionDots(summaries) {
  summaries.forEach(summary => {
    if (summary.summary && summary.summary.data) {
      summary.summary.data.forEach(detection => {
        if (detection.latitude && detection.longitude) {
          const marker = L.circleMarker([detection.latitude, detection.longitude], {
            radius: 6,
            fillColor: '#ff4444',
            color: '#cc0000',
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
    const base = window.CONFIGS && window.CONFIGS.backendUrl ? window.CONFIGS.backendUrl : '';
    const vesselUrl = new URL(`/api/vessels/${vesselId}`, base || window.location.origin);
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
    const base = window.CONFIGS && window.CONFIGS.backendUrl ? window.CONFIGS.backendUrl : '';
    const eventsUrl = new URL('/api/events', base || window.location.origin);
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

function updateSummaryStats(summaries) {
  const summarySection = document.getElementById('summary-stats');
  const summaryList = document.getElementById('summary-list');
  
  if (!summaries || summaries.length === 0) {
    summarySection.classList.add('hidden');
    return;
  }
  
  summarySection.classList.remove('hidden');
  
  // Calculate totals
  let totalDetections = 0;
  let totalVessels = 0;
  
  summaries.forEach(summary => {
    if (summary.summary && summary.summary.data) {
      totalDetections += summary.summary.data.length;
      // Count unique vessels
      const vessels = new Set(summary.summary.data.map(d => d.vessel_id).filter(Boolean));
      totalVessels += vessels.size;
    }
  });
  
  summaryList.innerHTML = `
    <li><strong>Total Detections:</strong> ${totalDetections}</li>
    <li><strong>Unique Vessels:</strong> ${totalVessels}</li>
    <li><strong>EEZs Covered:</strong> ${summaries.length}</li>
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

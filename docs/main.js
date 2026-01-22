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

let map, layerGroup, heatmapLayer, eezBoundaryLayer, proximityClusterLayer, routeLayer;
let markerClusterGroup, sarClusterGroup;
let currentFilters = {};
let markerData = { sar: [] }; // Store marker data for viewport filtering
let currentClusterData = null; // Store cluster data for toggle functionality
let debounceTimer = null;
let showRoutes = false; // Toggle for route visualization
let showDetections = true; // Toggle for SAR + Gap detections
let showClusters = false; // Toggle for proximity clusters (default: off)

function collapseSidebarForLoading() {
  const sidebar = document.getElementById('sidebar');
  if (!sidebar) return;
  sidebar.classList.add('collapsed');
  document.body.classList.add('sidebar-collapsed');
  const sidebarToggle = document.getElementById('sidebar-toggle');
  if (sidebarToggle) sidebarToggle.textContent = '⟱';
  setTimeout(() => map?.invalidateSize?.(), 300);
}

function attachAnalyticsOverlay() {
  const stats = document.getElementById('summary-stats');
  const mapContainer = document.querySelector('.map-container');
  if (!stats || !mapContainer) return;
  stats.classList.add('map-analytics-overlay');
  mapContainer.appendChild(stats);
}

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

    // Move analytics cards to bottom-center overlay on the map
    attachAnalyticsOverlay();

    // Default: sidebar starts expanded in docs build, so show the "collapse" arrow.
    const sidebarToggle = document.getElementById('sidebar-toggle');
    if (sidebarToggle) sidebarToggle.textContent = '⟰';

    // Initialize display toggles state from checkboxes
    const detectionsCheckbox = document.getElementById('show-detections');
    const clustersCheckbox = document.getElementById('show-clusters');
    const routesCheckbox = document.getElementById('show-routes');
    if (detectionsCheckbox) showDetections = detectionsCheckbox.checked;
    if (clustersCheckbox) showClusters = clustersCheckbox.checked;
    if (routesCheckbox) showRoutes = routesCheckbox.checked;

    // Set up about menu
    setupAboutMenu();

    // Set up HTML tooltips
    setupHTMLTooltips();

    // Set default dates
    setDefaultDates();

  } catch (error) {
    console.error('Initialization failed:', error);
    showError('Failed to initialize application');
  }
}

function initMap() {
  // Initialize the map centered on a global view
  // Best practice: Set maxBounds to prevent panning too far from valid data areas
  const maxBounds = L.latLngBounds(
    L.latLng(-85, -180), // Southwest corner
    L.latLng(85, 180)    // Northeast corner
  );

  map = L.map('map', {
    center: [20, 0],
    zoom: 2,
    minZoom: 2,
    maxZoom: 18,
    maxBounds: maxBounds,
    maxBoundsViscosity: 1.0, // Prevent panning outside bounds
    zoomControl: true,
    attributionControl: true,
    // Best practice: Enable smooth zoom for better UX
    zoomAnimation: true,
    zoomAnimationThreshold: 4,
    // Best practice: Enable fade animation for smoother transitions
    fadeAnimation: true,
    // Best practice: Enable marker zoom animation
    markerZoomAnimation: true
  });

  // Ensure map resizes when container size changes
  // Best practice: Use window resize event for responsive behavior
  let resizeTimer;
  window.addEventListener('resize', () => {
    clearTimeout(resizeTimer);
    resizeTimer = setTimeout(() => {
      map.invalidateSize();
    }, 250); // Debounce resize events
  });

  // Initial size validation
  setTimeout(() => {
    map.invalidateSize();
  }, 100);

  // Add base tile layer with best practices
  const osmLayer = L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
    attribution: '© <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',
    maxZoom: 19,
    minZoom: 2,
    subdomains: ['a', 'b', 'c'], // Use multiple subdomains for better performance
    // Best practice: Add error tile URL for better error handling
    errorTileUrl: 'data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iMjU2IiBoZWlnaHQ9IjI1NiIgeG1sbnM9Imh0dHA6Ly93d3cudzMub3JnLzIwMDAvc3ZnIj48cmVjdCB3aWR0aD0iMjU2IiBoZWlnaHQ9IjI1NiIgZmlsbD0iI2VlZSIvPjx0ZXh0IHg9IjUwJSIgeT0iNTAlIiBmb250LWZhbWlseT0iQXJpYWwiIGZvbnQtc2l6ZT0iMTQiIGZpbGw9IiM5OTkiIHRleHQtYW5jaG9yPSJtaWRkbGUiIGR5PSIuM2VtIj5UaWxlIGxvYWQgZXJyb3I8L3RleHQ+PC9zdmc+',
    // Best practice: Set tile size explicitly
    tileSize: 256,
    // Best practice: Enable crossOrigin for CORS
    crossOrigin: true,
    // Best practice: Add zoom offset if needed
    zoomOffset: 0
  });

  osmLayer.addTo(map);

  // Best practice: Add scale control for maritime applications
  L.control.scale({
    imperial: false, // Use metric (km) for maritime
    metric: true,
    position: 'bottomleft',
    maxWidth: 200
  }).addTo(map);

  // Best practice: Handle tile layer errors
  osmLayer.on('tileerror', (error, tile) => {
    console.warn('Tile load error:', error, tile);
    // Error tile URL will be used automatically
  });

  // Set up legend
  setupLegend();

  // Set up layer group for detections (legacy, kept for compatibility)
  layerGroup = L.layerGroup().addTo(map);

  // Set up marker cluster groups for better performance
  sarClusterGroup = L.markerClusterGroup({
    maxClusterRadius: 50, // Cluster markers within 50px
    spiderfyOnMaxZoom: true,
    showCoverageOnHover: true,
    zoomToBoundsOnClick: true,
    chunkedLoading: true, // Load markers in chunks for better performance
    chunkInterval: 200, // Process markers every 200ms
    chunkDelay: 50, // Delay between chunks
    iconCreateFunction: function (cluster) {
      const count = cluster.getChildCount();
      let size = 'small';
      let color = '#ff8800'; // Orange for small clusters

      if (count > 100) {
        size = 'large';
        color = '#cc0000'; // Red for large clusters
      } else if (count > 50) {
        size = 'medium';
        color = '#ff6600'; // Orange-red for medium clusters
      }

      return new L.DivIcon({
        html: '<div style="background-color:' + color + '; color:white; border-radius:50%; width:40px; height:40px; display:flex; align-items:center; justify-content:center; font-weight:bold; border:3px solid white; box-shadow:0 2px 4px rgba(0,0,0,0.3);">' + count + '</div>',
        className: 'marker-cluster',
        iconSize: L.point(40, 40)
      });
    }
  });

  // Add cluster group to map (will be toggled by display options)
  map.addLayer(sarClusterGroup);

  // Set up layer group for EEZ boundaries
  eezBoundaryLayer = L.layerGroup().addTo(map);
  debugLog.log('EEZ boundary layer initialized');

  // Set up layer group for proximity clusters (dark trade indicators)
  proximityClusterLayer = L.layerGroup().addTo(map);
  debugLog.log('Proximity cluster layer initialized');

  // Set up layer group for predicted routes
  routeLayer = L.layerGroup().addTo(map);
  debugLog.log('Route layer initialized');
}

function setupEventListeners() {
  // Sidebar toggle functions
  function toggleSidebar() {
    const sidebar = document.getElementById('sidebar');
    if (sidebar) {
      sidebar.classList.toggle('collapsed');
      // Update body class for CSS selector
      if (sidebar.classList.contains('collapsed')) {
        document.body.classList.add('sidebar-collapsed');
      } else {
        document.body.classList.remove('sidebar-collapsed');
      }
      const sidebarToggle = document.getElementById('sidebar-toggle');
      if (sidebarToggle) sidebarToggle.textContent = sidebar.classList.contains('collapsed') ? '⟱' : '⟰';
      // Invalidate map size when sidebar toggles
      setTimeout(() => map.invalidateSize(), 300);
    }
  }

  // Sidebar toggle button (in header, when collapsed)
  const sidebarToggle = document.getElementById('sidebar-toggle');
  if (sidebarToggle) {
    sidebarToggle.addEventListener('click', toggleSidebar);
  }

  // Sidebar close button (caret on right side of sidebar)
  const sidebarClose = document.getElementById('sidebar-close');
  if (sidebarClose) {
    sidebarClose.addEventListener('click', toggleSidebar);
  }

  // About toggle
  document.getElementById('about-toggle').addEventListener('click', toggleAbout);

  // Date inputs
  const validateDatesHandler = () => {
    if (typeof validateDates === 'function') validateDates();
  };
  document.getElementById('start').addEventListener('change', validateDatesHandler);
  document.getElementById('end').addEventListener('change', validateDatesHandler);

  // EEZ selection (only register once)
  document.getElementById('eez-select').addEventListener('change', onEEZChange);

  // Apply filters button
  document.getElementById('applyFilters').addEventListener('click', applyFilters);

  // Display option toggles
  const detectionsCheckbox = document.getElementById('show-detections');
  if (detectionsCheckbox) {
    detectionsCheckbox.addEventListener('change', (e) => {
      showDetections = e.target.checked;
      toggleDetectionsVisibility();
    });
  }

  const clustersCheckbox = document.getElementById('show-clusters');
  if (clustersCheckbox) {
    clustersCheckbox.addEventListener('change', (e) => {
      showClusters = e.target.checked;
      toggleClustersVisibility();
    });
  }

  const routeCheckbox = document.getElementById('show-routes');
  if (routeCheckbox) {
    routeCheckbox.addEventListener('change', (e) => {
      showRoutes = e.target.checked;
      if (showRoutes && currentFilters.eez_ids && currentFilters.start_date && currentFilters.end_date) {
        fetchPredictedRoutes(currentFilters);
      } else if (!showRoutes && routeLayer) {
        routeLayer.clearLayers();
      }
    });
  }

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

  if (typeof validateDates === 'function') validateDates();
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
      if (typeof validateDates === 'function') validateDates();
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
        // Best practice: Fit bounds with proper options
        map.fitBounds(combinedBounds, {
          padding: [50, 50],
          maxZoom: 12, // Prevent zooming in too far
          animate: true,
          duration: 0.5
        });
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

  // If validation passed, collapse sidebar so the user can see loading + map updates.
  collapseSidebarForLoading();

  // Show loading spinner
  const loadingSpinner = document.getElementById("loading-spinner");
  const progressBarFill = document.getElementById("progress-bar-fill");
  const spinnerText = document.querySelector(".spinner-text");

  loadingSpinner.classList.remove("hidden");

  // Calculate total days for progress tracking
  const start = new Date(startDate);
  const end = new Date(endDate);
  const totalDays = Math.ceil((end - start) / (1000 * 60 * 60 * 24)) + 1;
  const totalChunks = Math.ceil(totalDays / 30); // Backend chunks into 30-day pieces
  const selectedEEZCount = selectedEEZs.length;

  // Estimate total time: ~2-3 seconds per chunk per EEZ (conservative estimate)
  const estimatedSecondsPerChunk = 3;
  const estimatedTotalSeconds = totalChunks * selectedEEZCount * estimatedSecondsPerChunk;

  // Update progress text
  if (spinnerText) {
    spinnerText.textContent = `Loading ${totalDays} days of data across ${selectedEEZCount} EEZ(s)...`;
  }

  // Start progress animation (time-based estimate)
  let progressStartTime = Date.now();
  let progressInterval = null;

  const updateProgress = () => {
    const elapsed = (Date.now() - progressStartTime) / 1000; // seconds
    const estimatedProgress = Math.min(95, (elapsed / estimatedTotalSeconds) * 100); // Cap at 95% until done
    if (progressBarFill) {
      progressBarFill.style.width = `${estimatedProgress}%`;
      progressBarFill.style.animation = 'none'; // Disable animation, use actual width
    }
  };

  // Update progress every 500ms
  progressInterval = setInterval(updateProgress, 500);
  updateProgress(); // Initial update

  try {
    // Build filters object - default to dark vessels (matched=false)
    // Option 3: Batch endpoint with feature flags - include clusters, routes, and stats in single request
    const filters = {
      eez_ids: JSON.stringify(selectedEEZs),
      start_date: startDate,
      end_date: endDate,
      interval: 'DAY',
      temporal_aggregation: 'false',
      matched: 'false', // Dark vessels only
      include_clusters: 'true', // Include proximity clusters in batch response
      include_routes: showRoutes ? 'true' : 'false', // Include routes if enabled
      include_stats: 'true', // Include statistics in batch response
      max_distance_km: '5.0', // For clusters
      same_date_only: 'true', // For clusters
      max_time_hours: '48.0', // For routes
      max_distance_km_route: '100.0', // For routes
      min_route_length: '2' // For routes
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

    // Fetch detections from backend with dynamic timeout based on date range and EEZ count
    // Base timeout: 2 minutes, add 30 seconds per 30-day chunk, 20 seconds per EEZ
    // For batch requests with clusters/routes/stats, add extra time
    const baseTimeout = 120000; // 2 minutes base
    const chunkTimeout = totalChunks * 30000; // 30 seconds per chunk
    const eezTimeout = selectedEEZCount * 20000; // 20 seconds per EEZ
    const batchOverhead = 60000; // 1 minute for batch processing (clusters, routes, stats)
    const dynamicTimeout = baseTimeout + chunkTimeout + eezTimeout + batchOverhead;
    const timeoutMinutes = Math.ceil(dynamicTimeout / 60000);

    debugLog.log(`Request timeout set to ${timeoutMinutes} minute(s) (${totalDays} days, ${totalChunks} chunks, ${selectedEEZCount} EEZ(s))`);

    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), dynamicTimeout);

    let response;
    try {
      response = await fetch(url.toString(), { signal: controller.signal });
      clearTimeout(timeoutId);
    } catch (error) {
      clearTimeout(timeoutId);
      if (error.name === 'AbortError') {
        throw new Error(`Request timed out after ${timeoutMinutes} minute(s). The date range (${totalDays} days across ${selectedEEZCount} EEZ(s)) may be too large. Please try with a smaller date range or fewer EEZs.`);
      }
      throw error;
    }

    if (!response.ok) {
      throw new Error(`HTTP ${response.status}: ${response.statusText}`);
    }

    // Clear progress interval and set to 100%
    if (progressInterval) {
      clearInterval(progressInterval);
    }
    if (progressBarFill) {
      progressBarFill.style.width = '100%';
    }
    if (spinnerText) {
      spinnerText.textContent = 'Processing data...';
    }

    const data = await response.json();
    const summary = data.dark_vessels?.summary || {};
    const detectionCount = summary.total_sar_detections || 0;

    debugLog.log('Detection data received:', {
      summary,
      sar_detections_count: data.dark_vessels?.sar_detections?.length || 0,
      summaries_count: data.summaries?.length,
      has_tile_url: !!data.tile_url,
      cluster_count: data.clusters?.total_clusters || 0
    });

    // Update map and stats
    updateMapWithDetections(data);
    // Pass clusters data along with statistics
    const batchStats = {
      clusters: data.clusters,
      statistics: data.statistics
    };
    updateSummaryStats(data.summaries, data.dark_vessels, batchStats);

    // SAR report API returns detection points, not vessel IDs
    if (detectionCount > 0) {
      const message = `Loaded ${detectionCount.toLocaleString()} SAR detection points`;
      showSuccess(message);
    } else {
      showSuccess('Query completed, but no detections found for selected criteria');
    }

  } catch (error) {
    console.error('Error applying filters:', error);
    showError('Failed to fetch detection data: ' + error.message);
  } finally {
    // Clear progress interval if still running
    if (progressInterval) {
      clearInterval(progressInterval);
    }
    // Reset progress bar
    if (progressBarFill) {
      progressBarFill.style.width = '0%';
      progressBarFill.style.animation = 'progress 2s ease-in-out infinite'; // Restore animation
    }
    // Hide loading spinner
    loadingSpinner.classList.add("hidden");
  }
}

function updateMapWithDetections(data) {
  // Clear existing layers
  if (heatmapLayer) {
    map.removeLayer(heatmapLayer);
  }
  layerGroup.clearLayers();
  if (sarClusterGroup) {
    sarClusterGroup.clearLayers();
  }
  if (proximityClusterLayer) {
    proximityClusterLayer.clearLayers();
  }
  if (routeLayer) {
    routeLayer.clearLayers();
  }

  // Clear stored marker data
  markerData = { sar: [] };

  // Heatmap layer disabled - user only wants to see SAR detection dots and clusters

  // Add detection markers from dark_vessels data
  if (data.dark_vessels) {
    // Store marker data for viewport filtering
    markerData = {
      sar: data.dark_vessels.sar_detections || []
    };
    if (showDetections) {
      addDarkVesselMarkers(data.dark_vessels);
      // Ensure layers are on map when showing detections
      if (sarClusterGroup && !map.hasLayer(sarClusterGroup)) {
        map.addLayer(sarClusterGroup);
      }
      // Also ensure layerGroup is on map (contains same markers for compatibility)
      if (layerGroup && !map.hasLayer(layerGroup)) {
        map.addLayer(layerGroup);
      }
    } else {
      // Ensure layers are removed from map when not showing detections
      if (sarClusterGroup && map.hasLayer(sarClusterGroup)) {
        map.removeLayer(sarClusterGroup);
      }
      // Also remove layerGroup to hide all individual markers
      if (layerGroup && map.hasLayer(layerGroup)) {
        map.removeLayer(layerGroup);
      }
    }

    // Option 3: Use batch data if available, otherwise fall back to separate requests
    // Store cluster data even if not displaying, so we can show it when toggle is turned on
    if (data.clusters && data.clusters.clusters) {
      currentClusterData = data.clusters;
      if (showClusters) {
        // Use clusters from batch response
        debugLog.log('Using clusters from batch response');
        displayProximityClusters(data.clusters.clusters, data.clusters);
        if (data.clusters.total_clusters > 0) {
          showSuccess(`Found ${data.clusters.total_clusters} proximity cluster(s) - potential dark trade activity`);
        }
      }
    } else if (showClusters) {
      // Fall back to separate request (backward compatibility)
      fetchProximityClusters(currentFilters);
    }

    // Use routes from batch response if available
    if (showRoutes && data.routes && data.routes.routes) {
      // Use routes from batch response
      debugLog.log('Using routes from batch response');
      displayPredictedRoutes(data.routes.routes, data.routes);
      if (data.routes.total_routes > 0) {
        showSuccess(`Found ${data.routes.total_routes} predicted route(s)`);
      }
    } else if (showRoutes) {
      // Fall back to separate request (backward compatibility)
      fetchPredictedRoutes(currentFilters);
    }
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

  // Performance: Limit markers to prevent browser crash
  // For large datasets, we'll sample or cluster
  const MAX_MARKERS = 10000;  // Maximum markers to display
  const totalDetections = darkVessels.sar_detections?.length || 0;
  const shouldLimitMarkers = totalDetections > MAX_MARKERS;

  if (shouldLimitMarkers) {
    console.warn(`Too many detections (${totalDetections}). Limiting to ${MAX_MARKERS} markers for performance.`);
    showError(`Found ${totalDetections.toLocaleString()} detections. Displaying first ${MAX_MARKERS.toLocaleString()} for performance. Consider narrowing your date range or EEZ selection.`);
  }

  // Log the structure to understand what we're working with
  debugLog.log('SAR detections data structure:', {
    has_sar: !!darkVessels.sar_detections,
    sar_count: darkVessels.sar_detections?.length || 0,
    sar_sample: darkVessels.sar_detections?.[0]
  });

  // Helper function to extract coordinates from various formats
  function extractCoordinates(item) {
    // Try direct lat/lon fields first
    let lat = item.latitude || item.lat || item.lat_center || item.center_lat || item.y;
    let lon = item.longitude || item.lon || item.lon_center || item.center_lon || item.x;


    // Try geometry/coordinates (GeoJSON format)
    if ((lat == null || lon == null) && item.geometry) {
      const geom = item.geometry;
      if (geom.type === 'Point' && Array.isArray(geom.coordinates) && geom.coordinates.length >= 2) {
        lon = geom.coordinates[0];
        lat = geom.coordinates[1];
      }
    }

    // Try coordinates array directly
    if ((lat == null || lon == null) && Array.isArray(item.coordinates) && item.coordinates.length >= 2) {
      lon = item.coordinates[0];
      lat = item.coordinates[1];
    }

    // Try if item itself is an array [lon, lat]
    if ((lat == null || lon == null) && Array.isArray(item) && item.length >= 2) {
      lon = item[0];
      lat = item[1];
    }

    // Validate coordinates
    if (lat != null && lon != null && !isNaN(lat) && !isNaN(lon)) {
      // Check if coordinates are in valid range
      if (lat >= -90 && lat <= 90 && lon >= -180 && lon <= 180) {
        return { lat, lon };
      }
    }

    return null;
  }

  // Add SAR detections (unmatched vessels)
  if (darkVessels.sar_detections && Array.isArray(darkVessels.sar_detections)) {
    // Limit SAR detections if too many
    const sarDetections = shouldLimitMarkers
      ? darkVessels.sar_detections.slice(0, MAX_MARKERS)
      : darkVessels.sar_detections;

    sarDetections.forEach((detection, index) => {
      // Stop if we've reached the limit
      if (markerCount >= MAX_MARKERS) {
        return;
      }

      const coords = extractCoordinates(detection);

      if (coords) {
        const marker = L.circleMarker([coords.lat, coords.lon], {
          radius: 6,
          fillColor: '#ffd700', // Yellow for individual SAR detections
          color: '#ffa500', // Orange border
          weight: 2,
          opacity: 0.8,
          fillOpacity: 0.6
        });

        const vesselId = detection.vessel_id || detection.vesselId || detection.id;
        const popupContent = `
          <div class="detection-popup">
            <h4>SAR Detection (Dark Vessel)</h4>
            <p><strong>Location:</strong> ${coords.lat.toFixed(4)}, ${coords.lon.toFixed(4)}</p>
            <p><strong>Type:</strong> SAR Detection (vessel detected by radar, not broadcasting AIS)</p>
            ${detection.date ? `<p><strong>Date:</strong> ${detection.date}</p>` : ''}
            ${detection.detections ? `<p><strong>Detections at this location:</strong> ${detection.detections}</p>` : ''}
            ${vesselId ? `
              <p><strong>Vessel ID:</strong> <a href="#" class="vessel-link" data-vessel="${vesselId}">${vesselId}</a></p>
              <p><small>Click vessel ID to view details</small></p>
            ` : `
              <p><small style="color: #666;">⚠️ No vessel ID - SAR detections are location points without vessel identity</small></p>
            `}
          </div>
        `;

        // Best practice: Configure popup with proper options
        marker.bindPopup(popupContent, {
          maxWidth: 300,
          className: 'detection-popup',
          closeButton: true,
          autoPan: true,
          autoPanPadding: [50, 50],
          keepInView: true
        });

        // Best practice: Add keyboard accessibility
        marker.on('click', () => {
          marker.openPopup();
        });

        // Use cluster group for better performance
        sarClusterGroup.addLayer(marker);
        // Also add to legacy layerGroup for compatibility
        layerGroup.addLayer(marker);
        markerCount++;
      } else if (index < 5) {
        // Log first few to debug structure
        debugLog.warn('SAR detection missing coordinates. Available fields:', Object.keys(detection));
        debugLog.warn('Sample detection:', JSON.stringify(detection, null, 2).substring(0, 500));
      }
    });
  }

  debugLog.log(`Added ${markerCount} SAR detection markers to map (using clustering for performance)`);

  // Log cluster statistics
  if (sarClusterGroup) {
    console.log(`📊 SAR markers: ${sarClusterGroup.getLayers().length} individual markers (will cluster automatically)`);
  }

  // Clear previous proximity clusters
  if (proximityClusterLayer) {
    proximityClusterLayer.clearLayers();
  }

  if (markerCount === 0) {
    const hasData = darkVessels.sar_detections?.length > 0;
    if (hasData) {
      console.warn('No markers added despite having data - coordinates may be missing or in unexpected format');
      console.warn('Check console logs above for sample data structures');
      showError('Detections found but coordinates are missing. Check console for details.');
    } else {
      debugLog.log('No detections found for selected date range and EEZs');
      // Check if dates are in the future or too recent
      const endDate = document.getElementById('end')?.value;
      if (endDate) {
        const end = new Date(endDate + 'T00:00:00'); // Add time to avoid timezone issues
        const today = new Date();
        today.setHours(0, 0, 0, 0); // Reset to midnight for accurate day comparison
        const daysDiff = Math.floor((end.getTime() - today.getTime()) / (1000 * 60 * 60 * 24));

        if (daysDiff > 0) {
          showError(`Selected end date is ${daysDiff} day${daysDiff !== 1 ? 's' : ''} in the future. GFW data is typically available up to 5-7 days in arrears. Please select dates from the past.`);
        } else if (daysDiff >= -6) {
          // Data from 0-6 days ago may not be available yet
          showError(`Selected end date is only ${Math.abs(daysDiff)} day${Math.abs(daysDiff) !== 1 ? 's' : ''} ago. GFW data is typically available 5-7 days after the date. Please select dates at least 7 days in the past.`);
        } else {
          // Dates are valid (7+ days ago), but no detections found
          debugLog.log(`Date range is valid (${Math.abs(daysDiff)} days ago). No detections may indicate: no dark vessels in selected EEZs, or data structure issues.`);
        }
      }
    }
  }
}

async function fetchProximityClusters(filters) {
  /**
   * Fetch and display proximity clusters - vessels close to each other at the same time.
   * This indicates potential dark trade activity (transshipment, rendezvous, illegal transfers).
   * 
   * Risk assessment based on established maritime security frameworks:
   * - High Risk (3+ vessels): Red markers - coordinated illicit activities
   * - Medium Risk (2 vessels): Orange markers - bilateral transfers/rendezvous
   * 
   * See DARK_TRADE_RISK_THRESHOLDS.md for detailed citations.
   */
  if (!filters || !filters.eez_ids || !filters.start_date || !filters.end_date) {
    debugLog.warn('Cannot fetch proximity clusters - missing filters:', filters);
    return;
  }

  debugLog.log('Fetching proximity clusters with filters:', filters);

  try {
    const params = new URLSearchParams({
      eez_ids: filters.eez_ids,
      start_date: filters.start_date,
      end_date: filters.end_date,
      max_distance_km: '5.0',  // 5km default - based on typical STS transfer distances (0.5-2nm) with buffer
      same_date_only: 'true'   // Only cluster detections on the same date (reduces false positives)
    });

    const response = await fetch(`${config.backendUrl}/api/detections/proximity-clusters?${params}`);
    if (!response.ok) {
      throw new Error(`HTTP ${response.status}: ${response.statusText}`);
    }

    const data = await response.json();
    debugLog.log('Proximity clusters data:', data);
    debugLog.log(`Proximity clusters response: ${data.total_clusters || 0} clusters, ${data.total_vessels_in_clusters || 0} vessels`);

    // Store cluster data for toggle functionality
    if (data.clusters) {
      currentClusterData = Array.isArray(data.clusters) ? { clusters: data.clusters, total_clusters: data.clusters.length } : data;
    }

    if (data.clusters && data.clusters.length > 0) {
      displayProximityClusters(data.clusters, data);
      showSuccess(`Found ${data.clusters.length} proximity cluster(s) - potential dark trade activity`);
    } else {
      debugLog.log(`No proximity clusters found. Total SAR detections: ${data.summary?.total_sar_detections || 0}`);
      if (data.summary?.total_sar_detections > 0) {
        debugLog.log('Note: SAR detections exist but no clusters found. This could mean:');
        debugLog.log('  - Detections are too far apart (>5km)');
        debugLog.log('  - Detections are on different dates (if same_date_only=true)');
        debugLog.log('  - Need to adjust max_distance_km parameter');
      }
    }
  } catch (error) {
    debugLog.warn('Failed to fetch proximity clusters:', error);
    // Don't show error to user - proximity clusters are optional
  }
}

function displayProximityClusters(clusters, clusterData) {
  /**
   * Display proximity clusters on the map with special markers and connecting lines.
   */
  if (!proximityClusterLayer) {
    console.warn('Proximity cluster layer not initialized');
    return;
  }

  // Sort clusters so high-risk (red) ones are processed last (rendered on top)
  const sortedClusters = [...clusters].sort((a, b) => {
    const aRisk = a.risk_indicator === 'high' ? 3 : a.risk_indicator === 'medium' ? 2 : 1;
    const bRisk = b.risk_indicator === 'high' ? 3 : b.risk_indicator === 'medium' ? 2 : 1;
    return aRisk - bRisk; // Low risk first, high risk last (rendered on top)
  });

  sortedClusters.forEach((cluster, index) => {
    const centerLat = cluster.center_latitude;
    const centerLon = cluster.center_longitude;
    const vesselCount = cluster.vessel_count;
    const riskIndicator = cluster.risk_indicator;
    const maxDistance = cluster.max_distance_km;
    const date = cluster.date;

    // Color based on risk level (based on maritime security frameworks)
    let color = '#ff9900'; // Orange for medium risk (2 vessels)
    if (riskIndicator === 'high') {
      color = '#cc0000'; // Red for high risk (3+ vessels) - coordinated illicit activities
    } else if (riskIndicator === 'low') {
      color = '#ffcc00'; // Yellow for low risk (2 vessels) - bilateral transfers
    }

    // Calculate marker size based on vessel count
    const markerRadius = Math.min(10 + vesselCount * 2, 20);

    // Create a div icon with number inside the circle
    const clusterIcon = L.divIcon({
      className: 'cluster-marker',
      html: `<div style="
        width: ${markerRadius * 2}px;
        height: ${markerRadius * 2}px;
        border-radius: 50%;
        background-color: ${color};
        border: 2px solid #000;
        display: flex;
        align-items: center;
        justify-content: center;
        font-weight: bold;
        font-size: ${markerRadius > 15 ? '12px' : '10px'};
        color: white;
        text-shadow: 1px 1px 2px rgba(0,0,0,0.8);
        box-shadow: 0 2px 4px rgba(0,0,0,0.3);
      ">${vesselCount}</div>`,
      iconSize: [markerRadius * 2, markerRadius * 2],
      iconAnchor: [markerRadius, markerRadius]
    });

    // Create marker with the icon
    const clusterMarker = L.marker([centerLat, centerLon], {
      icon: clusterIcon,
      zIndexOffset: riskIndicator === 'high' ? 1000 : riskIndicator === 'medium' ? 500 : 0 // High risk on top
    });

    // Create popup with cluster information
    const popupContent = `
      <div class="cluster-popup">
        <h4 style="color: ${color}; margin-top: 0;">🚨 Dark Trade Cluster</h4>
        <p><strong>Risk Level:</strong> <span style="color: ${color}; font-weight: bold;">${riskIndicator.toUpperCase()}</span></p>
        <p><strong>Vessels:</strong> ${vesselCount} dark vessel(s) detected</p>
        <p><strong>Date:</strong> ${date || 'Unknown'}</p>
        <p><strong>Max Distance:</strong> ${(cluster.max_distance_km || maxDistance).toFixed(2)} km</p>
        <p style="margin-top: 10px; padding-top: 10px; border-top: 1px solid #ddd; font-size: 0.9em;">
          <strong>What This Means:</strong> Multiple vessels detected without AIS within close proximity (${(cluster.max_distance_km || maxDistance).toFixed(2)}km) on the same date. This pattern may indicate transshipment, rendezvous, illegal fishing coordination, or other suspicious activity.
        </p>
        <p style="margin-top: 8px; padding-top: 8px; border-top: 1px solid #eee; font-size: 0.85em; color: #666;">
          <em>Risk assessment based on maritime security frameworks. Sources: <a href="https://www.lloydslistintelligence.com/about-us" target="_blank" rel="noopener noreferrer">Lloyd's List Intelligence</a>, <a href="https://www.kpler.com" target="_blank" rel="noopener noreferrer">Kpler</a>, <a href="https://www.lse.ac.uk" target="_blank" rel="noopener noreferrer">LSE</a>.</em>
        </p>
      </div>
    `;

    // Best practice: Configure popup with proper options
    clusterMarker.bindPopup(popupContent, {
      maxWidth: 350,
      className: 'cluster-popup',
      closeButton: true,
      autoPan: true,
      autoPanPadding: [50, 50],
      keepInView: true
    });

    // Draw lines connecting all detections in the cluster
    if (cluster.detections && cluster.detections.length >= 2) {
      const detectionPoints = cluster.detections
        .map(d => {
          const lat = d.latitude || d.lat;
          const lon = d.longitude || d.lon;
          return lat && lon ? [lat, lon] : null;
        })
        .filter(p => p !== null);

      if (detectionPoints.length >= 2) {
        // Draw lines between all pairs of detections (thinner, more subtle)
        for (let i = 0; i < detectionPoints.length; i++) {
          for (let j = i + 1; j < detectionPoints.length; j++) {
            const line = L.polyline(
              [detectionPoints[i], detectionPoints[j]],
              {
                color: color,
                weight: 1.5,
                opacity: 0.4,
                dashArray: '3, 3'
              }
            );
            proximityClusterLayer.addLayer(line);
          }
        }

        // Draw a much smaller circle based on actual cluster spread
        // Calculate actual bounding radius from detections (much smaller than maxDistance)
        let actualMaxDist = 0;
        for (let i = 0; i < detectionPoints.length; i++) {
          for (let j = i + 1; j < detectionPoints.length; j++) {
            const p1 = L.latLng(detectionPoints[i]);
            const p2 = L.latLng(detectionPoints[j]);
            const dist = p1.distanceTo(p2); // Distance in meters
            actualMaxDist = Math.max(actualMaxDist, dist);
          }
        }

        // Use actual cluster spread with small padding, clamped between 100m and 1.5km
        // This makes clusters much more visible and accurate to actual vessel positions
        const clusterRadius = Math.min(Math.max(actualMaxDist * 0.55, 100), 1500);

        const clusterCircle = L.circle([centerLat, centerLon], {
          radius: clusterRadius, // Much smaller - actual cluster spread, not maxDistance
          color: color,
          weight: 2,
          opacity: 0.6,
          fillColor: color,
          fillOpacity: 0.18
        });
        proximityClusterLayer.addLayer(clusterCircle);

        // Option 2: Draw small circles around each detection point (alternative visualization)
        // Uncomment to use instead of large circle:
        /*
        detectionPoints.forEach(point => {
          const detectionCircle = L.circleMarker(point, {
            radius: 4,
            fillColor: color,
            color: color,
            weight: 1,
            opacity: 0.6,
            fillOpacity: 0.3
          });
          proximityClusterLayer.addLayer(detectionCircle);
        });
        */
      }
    }

    proximityClusterLayer.addLayer(clusterMarker);
  });

  // Update analytics dashboard with cluster statistics
  if (clusterData) {
    updateClusterStats(clusterData);
  }

  debugLog.log(`Displayed ${clusters.length} proximity clusters on map`);
}

async function fetchPredictedRoutes(filters) {
  /**
   * Fetch and display predicted routes for dark vessels.
   * Uses statistical analysis to connect detections temporally and spatially.
   */
  if (!filters || !filters.eez_ids || !filters.start_date || !filters.end_date) {
    debugLog.warn('Cannot fetch predicted routes - missing filters:', filters);
    return;
  }

  debugLog.log('Fetching predicted routes with filters:', filters);

  try {
    const params = new URLSearchParams({
      eez_ids: filters.eez_ids,
      start_date: filters.start_date,
      end_date: filters.end_date,
      max_time_hours: '48.0',  // Connect detections within 48 hours
      max_distance_km: '100.0',  // Connect detections within 100km
      min_route_length: '2'  // Minimum 2 points to form a route
    });

    const response = await fetch(`${config.backendUrl}/api/detections/routes?${params}`);
    if (!response.ok) {
      throw new Error(`HTTP ${response.status}: ${response.statusText}`);
    }

    const data = await response.json();
    debugLog.log('Predicted routes data:', data);

    if (data.routes && data.routes.length > 0) {
      displayPredictedRoutes(data.routes, data);
      showSuccess(`Found ${data.routes.length} predicted route(s)`);
    } else {
      debugLog.log('No routes predicted from detections');
    }
  } catch (error) {
    debugLog.warn('Failed to fetch predicted routes:', error);
    // Don't show error to user - routes are optional
  }
}

async function fetchSarAisAssociation(filters) {
  /**
   * Fetch SAR presence match summary (SAR matched vs unmatched to AIS) for the current EEZ/date range.
   * This is a quantitative “cooperative vs non-cooperative” view; it does not provide vessel identity.
   */
  if (!filters || !filters.eez_ids || !filters.start_date || !filters.end_date) return null;

  try {
    const params = new URLSearchParams({
      eez_ids: filters.eez_ids,
      start_date: filters.start_date,
      end_date: filters.end_date
    });
    const response = await fetch(`${config.backendUrl}/api/detections/sar-ais-association?${params}`);
    if (!response.ok) throw new Error(`HTTP ${response.status}: ${response.statusText}`);
    return await response.json();
  } catch (e) {
    debugLog.warn('Failed to fetch SAR↔AIS association summary:', e);
    return null;
  }
}

function displayPredictedRoutes(routes, routeData) {
  /**
   * Display predicted routes on the map as polylines.
   */
  if (!routeLayer) {
    console.warn('Route layer not initialized');
    return;
  }

  routes.forEach((route, index) => {
    if (!route.points || route.points.length < 2) {
      return;
    }

    // Convert points to [lat, lon] format for Leaflet
    const latlngs = route.points.map(p => [p[0], p[1]]);

    // Determine color based on confidence and vessel ID
    let color = '#888888'; // Default gray for SAR-only routes
    let weight = 2;
    let opacity = 0.6;

    // All routes are SAR-only (statistical predictions)
    color = '#ff8800'; // Orange
    weight = 2;
    opacity = 0.6;

    // Adjust opacity based on confidence
    if (route.confidence) {
      opacity = Math.max(0.3, Math.min(0.9, route.confidence));
    }

    // Create polyline for the route with best mapping practices
    const dashArray = route.vessel_id ? null : '8, 4'; // Dashed for SAR-only routes (better visibility)
    const polyline = L.polyline(latlngs, {
      color: color,
      weight: 3, // Slightly thicker for better visibility
      opacity: Math.max(0.5, Math.min(0.8, opacity)), // Better contrast range
      smoothFactor: 1.0,
      dashArray: dashArray,
      className: route.vessel_id ? 'route-polyline-vessel' : 'route-polyline-sar',
      // Best practice: Add interactive styling
      interactive: true,
      bubblingMouseEvents: true
    });

    // Create popup with route information
    const popupContent = `
      <div class="route-popup">
        <h4>Predicted Route</h4>
        <p><strong>Points:</strong> ${route.point_count || route.points.length}</p>
        <p><strong>Distance:</strong> ${route.total_distance_km || 'N/A'} km</p>
        ${route.duration_hours ? `<p><strong>Duration:</strong> ${route.duration_hours.toFixed(1)} hours</p>` : ''}
        <p><strong>Confidence:</strong> ${((route.confidence || 0) * 100).toFixed(0)}%</p>
        ${route.vessel_id ? `<p><strong>Vessel ID:</strong> <a href="#" class="vessel-link" data-vessel="${route.vessel_id}">${route.vessel_id}</a></p>` : '<p><em>SAR-only route (no vessel ID)</em></p>'}
        <p><small>Route predicted using temporal and spatial analysis</small></p>
      </div>
    `;

    // Best practice: Configure popup with proper options
    polyline.bindPopup(popupContent, {
      maxWidth: 300,
      className: 'route-popup',
      closeButton: true,
      autoPan: true,
      autoPanPadding: [50, 50],
      keepInView: true
    });
    routeLayer.addLayer(polyline);

    // Add start/end markers with best mapping practices
    // Best practice: Use standard colors (green for start, red for end) for universal recognition
    if (latlngs.length > 0) {
      // Start marker - green circle with arrow/triangle indicator (best practice: green = start/go)
      const startIcon = L.divIcon({
        className: 'route-start-marker',
        html: `<div style="
          position: relative;
          width: 16px;
          height: 16px;
          background-color: #22c55e;
          border: 3px solid white;
          border-radius: 50%;
          box-shadow: 0 2px 4px rgba(0,0,0,0.4), 0 0 0 1px rgba(0,0,0,0.2);
        ">
          <div style="
            position: absolute;
            top: -8px;
            left: 50%;
            transform: translateX(-50%);
            width: 0;
            height: 0;
            border-left: 4px solid transparent;
            border-right: 4px solid transparent;
            border-bottom: 6px solid #22c55e;
          "></div>
        </div>`,
        iconSize: [16, 16],
        iconAnchor: [8, 8]
      });
      const startMarker = L.marker(latlngs[0], {
        icon: startIcon,
        zIndexOffset: 1000, // Ensure start marker appears above route line
        interactive: true
      });
      startMarker.bindTooltip('Route Start', {
        permanent: false,
        direction: 'top',
        offset: [0, -10],
        className: 'route-tooltip'
      });
      routeLayer.addLayer(startMarker);

      if (latlngs.length > 1) {
        // End marker - red square/diamond (best practice: red = stop/end)
        const endIcon = L.divIcon({
          className: 'route-end-marker',
          html: `<div style="
            position: relative;
            width: 16px;
            height: 16px;
            background-color: #ef4444;
            border: 3px solid white;
            transform: rotate(45deg);
            box-shadow: 0 2px 4px rgba(0,0,0,0.4), 0 0 0 1px rgba(0,0,0,0.2);
          "></div>`,
          iconSize: [16, 16],
          iconAnchor: [8, 8]
        });
        const endMarker = L.marker(latlngs[latlngs.length - 1], {
          icon: endIcon,
          zIndexOffset: 1000, // Ensure end marker appears above route line
          interactive: true
        });
        endMarker.bindTooltip('Route End', {
          permanent: false,
          direction: 'top',
          offset: [0, -10],
          className: 'route-tooltip'
        });
        routeLayer.addLayer(endMarker);
      }
    }
  });

  debugLog.log(`Displayed ${routes.length} predicted routes on map`);
}

function updateClusterStats(clusterData) {
  /**
   * Update the analytics dashboard with proximity cluster statistics.
   */
  const statsSection = document.getElementById('analytics-stats');
  if (!statsSection || !clusterData) return;

  // Add cluster statistics to the detailed stats section
  const clusterStatsHtml = `
    <div style="margin-top: 15px; padding-top: 15px; border-top: 2px solid #ddd;">
      <h4 style="color: #cc0000; margin-bottom: 10px;">🚨 Dark Trade Clusters</h4>
      <div style="display: grid; grid-template-columns: repeat(4, 1fr); gap: 10px;">
        <div class="stat-card" style="background: #fff3cd;">
          <div class="stat-value">${clusterData.total_clusters || 0}</div>
          <div class="stat-label">Total Clusters</div>
        </div>
        <div class="stat-card" style="background: #f8d7da;">
          <div class="stat-value">${clusterData.high_risk_clusters || 0}</div>
          <div class="stat-label">High Risk (3+ vessels)</div>
        </div>
        <div class="stat-card" style="background: #fff3cd;">
          <div class="stat-value">${clusterData.medium_risk_clusters || 0}</div>
          <div class="stat-label">Medium Risk (2 vessels)</div>
        </div>
        <div class="stat-card">
          <div class="stat-value">${clusterData.total_vessels_in_clusters || 0}</div>
          <div class="stat-label">Vessels in Clusters</div>
        </div>
      </div>
      <p style="margin-top: 10px; font-size: 0.9em; color: #666;">
        <strong>What this means:</strong> Clusters indicate multiple dark vessels detected within ${clusterData.parameters?.max_distance_km || 5}km of each other on the same date. 
        This may indicate transshipment, rendezvous, or other suspicious dark trade activity. See "About this data" for detailed explanations and glossary.
        <br/><small style="font-style: italic; margin-top: 5px; display: block;">Risk assessment based on maritime security frameworks. Sources: <a href="https://www.lloydslist.com" target="_blank" rel="noopener noreferrer">Lloyd's List Intelligence</a>, <a href="https://www.kpler.com" target="_blank" rel="noopener noreferrer">Kpler</a>, <a href="https://www.lse.ac.uk" target="_blank" rel="noopener noreferrer">LSE Research</a>.</small>
      </p>
    </div>
  `;

  // Append to stats section (or create if doesn't exist)
  const existingClusterStats = statsSection.querySelector('.cluster-stats');
  if (existingClusterStats) {
    existingClusterStats.innerHTML = clusterStatsHtml;
  } else {
    const clusterStatsDiv = document.createElement('div');
    clusterStatsDiv.className = 'cluster-stats';
    clusterStatsDiv.innerHTML = clusterStatsHtml;
    statsSection.appendChild(clusterStatsDiv);
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

    // Get enhanced vessel details with includes
    const vesselUrl = new URL(`/api/vessels/${vesselId}`, backendUrl);
    vesselUrl.searchParams.set('includes', 'OWNERSHIP,AUTHORIZATIONS,REGISTRIES_INFO');
    const vesselResponse = await fetch(vesselUrl.toString());
    const vesselData = await vesselResponse.json();

    // Get vessel timeline
    const timelineUrl = new URL(`/api/vessels/${vesselId}/timeline`, backendUrl);
    timelineUrl.searchParams.set('start_date', currentFilters.start_date || '2017-01-01');
    timelineUrl.searchParams.set('end_date', currentFilters.end_date || new Date().toISOString().split('T')[0]);
    let timelineData = null;
    try {
      const timelineResponse = await fetch(timelineUrl.toString());
      timelineData = await timelineResponse.json();
    } catch (e) {
      debugLog.warn('Failed to fetch vessel timeline:', e);
    }

    // Get risk score
    const riskUrl = new URL(`/api/analytics/risk-score/${vesselId}`, backendUrl);
    riskUrl.searchParams.set('start_date', currentFilters.start_date || '2017-01-01');
    riskUrl.searchParams.set('end_date', currentFilters.end_date || new Date().toISOString().split('T')[0]);
    let riskData = null;
    try {
      const riskResponse = await fetch(riskUrl.toString());
      riskData = await riskResponse.json();
    } catch (e) {
      debugLog.warn('Failed to fetch risk score:', e);
    }

    // Show vessel details in a modal with all data
    showVesselModal(vesselData, timelineData, riskData);

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

function showVesselModal(vesselData, timelineData, riskData) {
  // Extract vessel information
  const vessel = vesselData.data || {};
  const vesselId = vesselData.vessel_id || 'Unknown';

  // Format vessel details
  const vesselInfo = vessel.vessel || {};
  const identity = vesselInfo.identity || {};
  const ownership = vesselInfo.ownership || {};
  const authorizations = vesselInfo.authorizations || [];

  // Risk score display
  let riskDisplay = '';
  if (riskData && riskData.risk_score !== undefined) {
    const riskLevel = riskData.risk_level || 'unknown';
    const riskColor = riskLevel === 'high' ? '#cc0000' : riskLevel === 'medium' ? '#ff8800' : '#00aa00';
    riskDisplay = `
      <div class="risk-score-section" style="background: ${riskColor}20; border-left: 4px solid ${riskColor}; padding: 10px; margin: 10px 0;">
        <h3>Risk Assessment</h3>
        <p><strong>Risk Score:</strong> <span style="font-size: 24px; color: ${riskColor};">${riskData.risk_score}/100</span> (${riskLevel.toUpperCase()})</p>
        ${riskData.factors ? `
          <div class="risk-factors">
            <strong>Risk Factors:</strong>
            <ul>
              ${riskData.factors.gap_events ? `<li>Gap Events: ${riskData.factors.gap_events} (${riskData.factors.gap_score || 0} pts)</li>` : ''}
              ${riskData.factors.iuu_listed ? `<li>IUU Listed: Yes (${riskData.factors.iuu_score || 0} pts)</li>` : ''}
              ${riskData.factors.fishing_events ? `<li>Fishing Events: ${riskData.factors.fishing_events} (${riskData.factors.fishing_score || 0} pts)</li>` : ''}
              ${riskData.factors.encounters ? `<li>Encounters: ${riskData.factors.encounters} (${riskData.factors.encounter_score || 0} pts)</li>` : ''}
              ${riskData.factors.port_visits ? `<li>Port Visits: ${riskData.factors.port_visits} (${riskData.factors.port_score || 0} pts)</li>` : ''}
            </ul>
          </div>
        ` : ''}
      </div>
    `;
  }

  // Timeline display
  let timelineDisplay = '';
  if (timelineData && timelineData.events) {
    const summary = timelineData.summary || {};
    timelineDisplay = `
      <div class="timeline-section">
        <h3>Activity Timeline</h3>
        <div class="timeline-stats">
          <p><strong>Total Events:</strong> ${summary.total_events || 0}</p>
          <ul>
            <li>Fishing Events: ${summary.fishing_events || 0}</li>
            <li>Port Visits: ${summary.port_visits || 0}</li>
            <li>Encounters: ${summary.encounters || 0}</li>
            <li>Loitering Events: ${summary.loitering_events || 0}</li>
          </ul>
        </div>
      </div>
    `;
  }

  // Create and show a modal with formatted vessel information
  const modal = document.createElement('div');
  modal.className = 'vessel-modal';
  modal.innerHTML = `
    <div class="modal-content">
      <span class="close">&times;</span>
      <h2>Vessel Details: ${vesselId}</h2>
      
      <div class="vessel-info-section">
        <h3>Identity</h3>
        <p><strong>Name:</strong> ${identity.name || 'Unknown'}</p>
        <p><strong>Flag:</strong> ${identity.flag || 'Unknown'}</p>
        <p><strong>Type:</strong> ${identity.vesselType || 'Unknown'}</p>
        <p><strong>Length:</strong> ${identity.lengthM ? identity.lengthM + 'm' : 'Unknown'}</p>
        <p><strong>MMSI:</strong> ${identity.mmsi || 'N/A'}</p>
        <p><strong>IMO:</strong> ${identity.imo || 'N/A'}</p>
      </div>
      
      ${ownership.ownerName ? `
        <div class="vessel-info-section">
          <h3>Ownership</h3>
          <p><strong>Owner:</strong> ${ownership.ownerName}</p>
          ${ownership.ownerAddress ? `<p><strong>Address:</strong> ${ownership.ownerAddress}</p>` : ''}
        </div>
      ` : ''}
      
      ${authorizations.length > 0 ? `
        <div class="vessel-info-section">
          <h3>Authorizations (${authorizations.length})</h3>
          <ul>
            ${authorizations.slice(0, 5).map(auth => `<li>${auth.source || 'Unknown'}: ${auth.authorizationType || 'N/A'}</li>`).join('')}
            ${authorizations.length > 5 ? `<li>... and ${authorizations.length - 5} more</li>` : ''}
          </ul>
        </div>
      ` : ''}
      
      ${riskDisplay}
      ${timelineDisplay}
      
      <div class="vessel-info-section">
        <h3>Raw Data</h3>
        <details>
          <summary>View Raw JSON</summary>
          <pre style="max-height: 300px; overflow: auto;">${JSON.stringify(vesselData, null, 2)}</pre>
        </details>
      </div>
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

async function updateSummaryStats(summaries, darkVessels, batchStats = null) {
  const summarySection = document.getElementById('summary-stats');

  if (!summaries || summaries.length === 0) {
    summarySection?.classList.add('hidden');
    return;
  }

  summarySection?.classList.remove('hidden');

  // Get actual counts from dark_vessels data (arrays) or summary
  const sarDetections = darkVessels?.sar_detections?.length || darkVessels?.summary?.total_sar_detections || 0;

  // Get cluster counts from batchStats if available
  const clusterCount = batchStats?.clusters?.total_clusters || 0;
  const highRiskClusters = batchStats?.clusters?.high_risk_clusters || 0;
  const mediumRiskClusters = batchStats?.clusters?.medium_risk_clusters || 0;

  // Get EEZ count from summaries or dark_vessels summary
  let eezCount = summaries?.length || 0;
  if (darkVessels?.summary?.eez_count) {
    eezCount = darkVessels.summary.eez_count;
  } else if (typeof currentFilters !== 'undefined' && currentFilters?.eez_ids) {
    try {
      const eezIds = Array.isArray(currentFilters.eez_ids)
        ? currentFilters.eez_ids
        : JSON.parse(currentFilters.eez_ids || '[]');
      eezCount = eezIds.length;
    } catch (e) {
      // Fall back to summaries length
    }
  }

  // Update stat cards with correct data
  document.getElementById('stat-sar-detections').textContent = sarDetections.toLocaleString();

  // Update SAR↔AIS association (matched %) if the card exists
  const matchedPctEl = document.getElementById('stat-sar-matched-pct');
  if (matchedPctEl) {
    matchedPctEl.textContent = '—';
    if (typeof currentFilters !== 'undefined' && currentFilters?.eez_ids && currentFilters?.start_date && currentFilters?.end_date) {
      const assoc = await fetchSarAisAssociation(currentFilters);
      const pct = assoc?.totals?.matched_detections_pct;
      if (typeof pct === 'number' && Number.isFinite(pct)) {
        matchedPctEl.textContent = `${pct.toFixed(1)}%`;
      }
    }
  }

  document.getElementById('stat-eez-count').textContent = eezCount;
  const clusterStatEl = document.getElementById('stat-clusters');
  const clusterLabelEl = document.getElementById('stat-clusters-label');
  if (clusterStatEl && clusterLabelEl) {
    clusterStatEl.textContent = clusterCount.toLocaleString();
    // Format label as "X (Y high risk, Z medium risk)"
    if (clusterCount > 0) {
      clusterLabelEl.innerHTML = `Dark Traffic Clusters<br/><small style="font-size: 0.75em; font-weight: normal;">${highRiskClusters.toLocaleString()} high risk, ${mediumRiskClusters.toLocaleString()} medium risk</small>`;
    } else {
      clusterLabelEl.textContent = 'Dark Traffic Clusters';
    }
  }

  // Log enhanced stats if available (for future use)
  if (batchStats && batchStats.statistics && batchStats.statistics.enhanced_statistics) {
    debugLog.log('Enhanced statistics available:', batchStats.statistics.enhanced_statistics);
  }
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
    // Best practice: Fit bounds with proper options
    const boundsLatLng = L.latLngBounds(bounds);
    if (boundsLatLng.isValid()) {
      map.fitBounds(boundsLatLng, {
        padding: [20, 20],
        maxZoom: 12, // Prevent zooming in too far
        animate: true,
        duration: 0.5
      });
    }
  }
}

function toggleAbout() {
  const aboutContainer = document.getElementById('about-container');
  aboutContainer.classList.toggle('collapsed');
}

function setupHTMLTooltips() {
  // Set up HTML tooltips for stat cards with data-tooltip-html attribute
  const statCards = document.querySelectorAll('.stat-card[data-tooltip-html]');
  statCards.forEach(card => {
    const tooltipHTML = card.getAttribute('data-tooltip-html');
    if (tooltipHTML) {
      const tooltipDiv = document.createElement('div');
      tooltipDiv.className = 'custom-tooltip';
      tooltipDiv.innerHTML = tooltipHTML;
      card.appendChild(tooltipDiv);

      // Mobile + keyboard support: tap/click toggles tooltip, tap outside closes.
      // Desktop hover still works via CSS.
      card.setAttribute('tabindex', '0');
      card.setAttribute('role', 'button');
      card.setAttribute('aria-expanded', 'false');
    }
  });

  const closeAll = () => {
    document.querySelectorAll('.stat-card.tooltip-open').forEach(c => {
      c.classList.remove('tooltip-open');
      c.setAttribute('aria-expanded', 'false');
    });
  };

  statCards.forEach(card => {
    card.addEventListener('click', (e) => {
      e.stopPropagation();
      const isOpen = card.classList.contains('tooltip-open');
      closeAll();
      if (!isOpen) {
        card.classList.add('tooltip-open');
        card.setAttribute('aria-expanded', 'true');
      }
    });

    card.addEventListener('keydown', (e) => {
      if (e.key === 'Enter' || e.key === ' ') {
        e.preventDefault();
        card.click();
      }
      if (e.key === 'Escape') {
        closeAll();
      }
    });
  });

  document.addEventListener('click', closeAll, { passive: true });
}

function setupAboutMenu() {
  const menuItems = document.querySelectorAll('.about-menu-item');
  const sections = document.querySelectorAll('.about-menu-section');

  menuItems.forEach(item => {
    item.addEventListener('click', () => {
      const targetSection = item.getAttribute('data-section');

      // Remove active class from all items and sections
      menuItems.forEach(mi => mi.classList.remove('active'));
      sections.forEach(sec => sec.classList.remove('active'));

      // Add active class to clicked item and corresponding section
      item.classList.add('active');
      const targetElement = document.getElementById(targetSection);
      if (targetElement) {
        targetElement.classList.add('active');
      }
    });
  });
}

function setupLegend() {
  const legend = L.control({ position: "topright" });

  legend.onAdd = function () {
    const div = L.DomUtil.create("div", "map-legend");
    div.innerHTML = `
      <div class="legend-header" style="display: flex; align-items: center; justify-content: space-between; cursor: pointer; margin-bottom: 4px;">
        <strong style="text-decoration:underline; font-size: 0.85rem; margin: 0;">Map Legend</strong>
        <span class="legend-toggle" style="font-size: 0.9rem; color: #2a5298; user-select: none;">▼</span>
      </div>
      <div class="legend-content">
      <div class="legend-section" style="border-top: 1px solid #ddd; padding-top: 4px; margin-top: 4px;">
        <div style="display:flex; align-items:center; margin: 3px 0;">
          <div style="width:32px; display:flex; align-items:center; justify-content:center; flex-shrink:0; margin-right:8px;">
            <div style="width:12px; height:12px; background:#ffd700; border-radius:50%; border:2px solid #ffa500;"></div>
          </div>
          <span style="font-size: 0.75rem; text-align:left;"><strong>SAR Detection</strong></span>
        </div>
      </div>
      
      <div class="legend-section" style="border-top: 1px solid #ddd; padding-top: 4px;">
        <strong style="font-size: 0.8rem;">Dark Traffic Clusters:</strong>
        <div style="display:flex; align-items:center; margin: 3px 0;">
          <div style="width:32px; display:flex; align-items:center; justify-content:center; flex-shrink:0; margin-right:8px;">
            <div style="width:20px; height:20px; background:#cc0000; border-radius:50%; border:2px solid #000; box-shadow:0 2px 4px rgba(0,0,0,0.3); display:flex; align-items:center; justify-content:center; color:white; font-weight:bold; font-size:0.6rem;">3</div>
          </div>
          <span style="font-size: 0.75rem; text-align:left;">Small cluster (High Risk)</span>
        </div>
        <div style="display:flex; align-items:center; margin: 3px 0;">
          <div style="width:32px; display:flex; align-items:center; justify-content:center; flex-shrink:0; margin-right:8px;">
            <div style="width:32px; height:32px; background:#ff9900; border-radius:50%; border:2px solid #000; box-shadow:0 2px 4px rgba(0,0,0,0.3); display:flex; align-items:center; justify-content:center; color:white; font-weight:bold; font-size:0.7rem;">8</div>
          </div>
          <span style="font-size: 0.75rem; text-align:left;">Large cluster (Medium Risk)</span>
        </div>
      </div>
      
      <div class="legend-section" style="border-top: 1px solid #ddd; padding-top: 4px;">
        <div style="display:flex; align-items:center; margin: 3px 0;">
          <div style="width:32px; display:flex; align-items:center; justify-content:center; flex-shrink:0; margin-right:8px;">
            <div style="display:flex; align-items:center; gap: 2px;">
              <div style="position:relative; width:12px; height:12px; background:#22c55e; border:2px solid white; border-radius:50%; box-shadow:0 1px 2px rgba(0,0,0,0.3);">
                <div style="position:absolute; top:-4px; left:50%; transform:translateX(-50%); width:0; height:0; border-left:3px solid transparent; border-right:3px solid transparent; border-bottom:4px solid #22c55e;"></div>
              </div>
              <div style="width:20px; height:3px; background:#ff8800; background-image: repeating-linear-gradient(to right, #ff8800 0, #ff8800 4px, transparent 4px, transparent 8px); flex-shrink:0; border-radius:1px;"></div>
              <div style="width:12px; height:12px; background:#ef4444; border:2px solid white; transform:rotate(45deg); box-shadow:0 1px 2px rgba(0,0,0,0.3);"></div>
            </div>
          </div>
          <span style="font-size: 0.75rem; text-align:left;"><strong>Route Prediction</strong> (Start → End)</span>
        </div>
      </div>
      
      <div class="legend-section" style="border-top: 1px solid #ddd; padding-top: 4px;">
        <div style="display:flex; align-items:center; margin: 3px 0;">
          <div style="width:32px; display:flex; align-items:center; justify-content:center; flex-shrink:0; margin-right:8px;">
            <div style="width:24px; height:2px; background:#3388ff;"></div>
          </div>
          <span style="font-size: 0.75rem; text-align:left;">EEZ Boundary</span>
        </div>
      </div>
      </div>
    `;

    // Add toggle functionality
    const header = div.querySelector('.legend-header');
    const content = div.querySelector('.legend-content');
    const toggle = div.querySelector('.legend-toggle');
    let isExpanded = true;

    header.addEventListener('click', () => {
      isExpanded = !isExpanded;
      if (isExpanded) {
        content.style.display = 'block';
        toggle.textContent = '▼';
      } else {
        content.style.display = 'none';
        toggle.textContent = '▶';
      }
    });

    return div;
  };

  legend.addTo(map);
}

function toggleDetectionsVisibility() {
  if (!sarClusterGroup) return;

  if (showDetections) {
    if (!map.hasLayer(sarClusterGroup)) map.addLayer(sarClusterGroup);
    // Also ensure layerGroup is on map (contains same markers for compatibility)
    if (layerGroup && !map.hasLayer(layerGroup)) map.addLayer(layerGroup);
  } else {
    if (map.hasLayer(sarClusterGroup)) map.removeLayer(sarClusterGroup);
    // Also remove layerGroup to hide all detection markers
    if (layerGroup && map.hasLayer(layerGroup)) map.removeLayer(layerGroup);
  }
}

function toggleClustersVisibility() {
  if (!proximityClusterLayer) return;

  if (showClusters) {
    // If we have stored cluster data, display it
    if (currentClusterData && currentClusterData.clusters) {
      displayProximityClusters(currentClusterData.clusters, currentClusterData);
    } else if (currentFilters.eez_ids && currentFilters.start_date && currentFilters.end_date) {
      // If no stored data but we have filters, fetch clusters
      fetchProximityClusters(currentFilters);
    }
    // Ensure layer is on map
    if (!map.hasLayer(proximityClusterLayer)) map.addLayer(proximityClusterLayer);
  } else {
    // Hide clusters but keep the data for when toggle is turned back on
    if (map.hasLayer(proximityClusterLayer)) {
      proximityClusterLayer.clearLayers();
      map.removeLayer(proximityClusterLayer);
    }
  }
}

// Initialize when DOM is loaded
document.addEventListener('DOMContentLoaded', init);

// main.js — refactored EEZ detection logic with a single unified EEZ_LOOKUP map

let map;
let layerGroup;
window.filterSettings = {};
window.EEZ_LOOKUP = {
  byLabel: {},     // e.g. "Mayotte" → { iso3: "FRA", id: 1234, label: "Mayotte" }
  byISO3: {},      // e.g. "FRA" → ["Mayotte", "Guadeloupe"]
  iso3ToName: {}   // e.g. "FRA" → "France"
};

function classifyEEZ(label) {
  const l = label.toLowerCase();
  if (l.includes("overlapping claim")) return "overlapping";
  if (l.includes("joint regime")) return "joint";
  return "sovereign";
}

function generateColor(type) {
  if (type === "overlapping") return "#cc0000";
  if (type === "joint") return "#009933";
  if (type === "sovereign") return "#924eda";
  return "#ffdb27";
}

function setupMap() {
  map = L.map("map", {
    maxBounds: [[-80, -180], [80, 180]],
    maxBoundsViscosity: 1.0,
    worldCopyJump: false,
    minZoom: 2,
    maxZoom: 12
  }).setView([20, 0], 2);

  L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
    attribution: "© OpenStreetMap contributors"
  }).addTo(map);

  layerGroup = L.layerGroup().addTo(map);

  const showLoading = () => document.getElementById("loading-spinner").classList.remove("hidden");
  const hideLoading = () => document.getElementById("loading-spinner").classList.add("hidden");

  window.refreshMap = async function () {
    const { eez_labels, startDate, endDate } = window.filterSettings;
    if (!eez_labels || eez_labels.length === 0) return;

    const progressBar = document.getElementById("progress-bar");
    const progressFill = document.getElementById("progress-bar-fill");
    progressBar.classList.remove("hidden");
    progressFill.style.width = "0%";

    layerGroup.clearLayers();
    showLoading();

    let pending = eez_labels.length;
    const total = pending;

    eez_labels.forEach(label => {
      const params = new URLSearchParams({ country: label, start: startDate, end: endDate });
      const url = `http://localhost:5000/api/detections?${params.toString()}`;

      fetch(url)
        .then(res => res.json())
        .then(geojson => {
          if (geojson.features && geojson.features.length > 0) {
            const geoLayer = L.geoJSON(geojson, {
              pointToLayer: (feature, latlng) => {
                const props = feature.properties;
                const color = generateColor(props.eez_type);
                return L.circleMarker(latlng, {
                  radius: 4,
                  fillColor: color,
                  color: "#222",
                  weight: 1,
                  fillOpacity: 0.8
                });
              },
              onEachFeature: (feature, layer) => {
                const p = feature.properties;
                const entry = window.EEZ_LOOKUP.byLabel[p.label] || {};
const eezCountry = entry.iso3 && window.EEZ_LOOKUP.iso3ToName[entry.iso3] || 'Unknown';
const eezLabel = entry.label || 'Unknown';
const eezCode = entry.id || 'Unknown';
                const popupLines = [
  `EEZ Country: ${eezCountry}`,
  `EEZ Label: ${eezLabel}`,
  `EEZ Code: ${eezCode}`,
  `Date: ${new Date(p.date).toUTCString()}`,
                  `Detections: ${p.detections}`
                ];
                if (p.vessel_type) popupLines.push(`Vessel Type: ${p.vessel_type}`);
                if (p.geartype) popupLines.push(`Gear Type: ${p.geartype}`);
                if (p.neural_vessel_type) popupLines.push(`Neural Vessel Type: ${p.neural_vessel_type}`);
                if (p.neural_vessel_type_confidence) popupLines.push(`Neural Vessel Type Confidence: ${p.neural_vessel_type_confidence}`);
                layer.bindPopup(popupLines.join('<br>'));
              }
            });
            geoLayer.addTo(layerGroup);
          }

          const progress = ((total - --pending) / total) * 100;
          progressFill.style.width = `${progress}%`;

          if (pending === 0) {
            try {
              const layers = layerGroup.getLayers();
              const bounds = L.latLngBounds([]);
              layers.forEach(l => {
                if (typeof l.getBounds === "function") bounds.extend(l.getBounds());
                else if (typeof l.getLatLng === "function") bounds.extend(l.getLatLng());
              });
              if (bounds.isValid()) map.fitBounds(bounds, { padding: [20, 20], maxZoom: 6 });
            } catch (err) {
              console.error("Error computing bounds:", err);
            } finally {
              hideLoading();
              progressBar.classList.add("hidden");
            }
          }
        })
        .catch(err => {
          console.error("Fetch error for", label, err);
          const progress = ((total - --pending) / total) * 100;
          progressFill.style.width = `${progress}%`;
          if (pending === 0) {
            hideLoading();
            progressBar.classList.add("hidden");
          }
        });
    });
  };

  const legend = L.control({ position: "topright" });
  legend.onAdd = function () {
    const div = L.DomUtil.create("div", "map-legend");
    div.innerHTML = `
      <strong style="text-decoration:underline;margin-bottom:20px;">Legend</strong><br/>
      <i class="legend-dot" style="background:#cc0000;"></i> Overlapping EEZ<br>
      <i class="legend-dot" style="background:#009933;"></i> Joint EEZ<br>
      <i class="legend-dot" style="background:#924eda;"></i> Sovereign EEZ<br>
    `;
    return div;
  };
  legend.addTo(map);
}

async function setupUI() {
  const start = document.getElementById("start");
  const end = document.getElementById("end");
  const apply = document.getElementById("applyFilters");
  const countrySelect = document.getElementById("country-select");

  const EEZ_REGIONS = await fetch("/utils/eez_all.json").then(r => r.json());
  const byLabel = window.EEZ_LOOKUP.byLabel;
  const byISO3 = window.EEZ_LOOKUP.byISO3;
  const iso3ToName = window.EEZ_LOOKUP.iso3ToName;

  EEZ_REGIONS.forEach(entry => {
    const { label, iso3, id } = entry;
    if (label.includes("/") || label.toLowerCase().includes("joint") || label.toLowerCase().includes("overlapping")) return;
    byLabel[label] = { label, iso3, id };
    if (!byISO3[iso3]) byISO3[iso3] = [];
    byISO3[iso3].push(label);
    if (!iso3ToName[iso3] || label === iso3) iso3ToName[iso3] = label;
  });

  const aboutToggle = document.getElementById("about-toggle");
  const aboutContainer = document.getElementById("about-container");
  aboutToggle.addEventListener("click", () => {
    const isOpen = !aboutContainer.classList.contains("collapsed");
    aboutContainer.classList.toggle("collapsed");
    aboutToggle.innerHTML = isOpen
      ? "About this data <span style='font-size:0.85em'>▲</span>"
      : "About this data <span style='font-size:0.85em'>▼</span>";
  });

  countrySelect.innerHTML = '';
  Object.entries(byISO3)
    .sort(([aIso3], [bIso3]) => (iso3ToName[aIso3] || aIso3).localeCompare(iso3ToName[bIso3] || bIso3))
    .forEach(([iso3, labels]) => {
      const friendlyName = iso3ToName[iso3] || iso3;
      if (labels.length === 1) {
        const group = document.createElement("optgroup");
        group.label = friendlyName;
        group.setAttribute("data-iso3", iso3);
        const opt = document.createElement("option");
        opt.value = labels[0];
        opt.textContent = labels[0];
        group.appendChild(opt);
        countrySelect.appendChild(group);
      } else {
        const group = document.createElement("optgroup");
        group.label = friendlyName;
        group.setAttribute("data-iso3", iso3);
        labels.sort().forEach(label => {
          const opt = document.createElement("option");
          opt.value = label;
          opt.textContent = label;
          group.appendChild(opt);
        });
        countrySelect.appendChild(group);
      }
    });

  apply.disabled = false;

  const today = new Date();
  const initialEnd = new Date(today);
  const initialStart = new Date(today);
  initialEnd.setDate(today.getDate() - 5);
  initialStart.setDate(today.getDate() - 12);
  const fmt = d => d.toISOString().split("T")[0];
  start.value = fmt(initialStart);
  end.value = fmt(initialEnd);

  apply.addEventListener("click", () => {
    const selectedLabel = countrySelect.value;
    const optgroup = countrySelect.selectedOptions[0].parentElement;
    const iso3 = optgroup.tagName === "OPTGROUP"
      ? optgroup.getAttribute("data-iso3")
      : byLabel[selectedLabel]?.iso3;

    if (!selectedLabel || !start.value || !end.value) return alert("Please fill all fields");
    if (new Date(end.value) - new Date(start.value) > 30 * 86400000) return alert("Date range cannot exceed 30 days");

    const eez_labels = optgroup.tagName === "OPTGROUP"
      ? [selectedLabel]
      : [selectedLabel];

    window.filterSettings = { iso3, eez_labels, startDate: start.value, endDate: end.value };
    window.refreshMap();
  });
}

document.addEventListener("DOMContentLoaded", async () => {
  await setupUI();
  setupMap();
});


import config from './config.js';

/**
 * Fetch application configurations from the backend
 */
export async function fetchConfigs() {
  try {
    const response = await fetch(`${config.backendUrl}/api/configs`);
    if (!response.ok) {
      throw new Error(`HTTP ${response.status}: ${response.statusText}`);
    }

    const data = await response.json();
    window.CONFIGS = data;
    return data;
  } catch (error) {
    console.error('Failed to fetch CONFIGS:', error);
    throw error;
  }
}

/**
 * Build the EEZ <select multiple>:
 *  - Options include one logical group per parent: "<Parent> (All territories)"
 *  - Options include every individual EEZ (parent and children) without "(Sovereign)"
 *  - All options sorted alphabetically by label
 *  - Selecting a logical group selects/deselects its members; child changes do NOT affect group
 */
export function buildEEZSelect() {
  if (window.__EEZ_SELECT_BUILT__) return;
  window.__EEZ_SELECT_BUILT__ = true;

  const eezSelect = document.getElementById("eez-select");
  if (!eezSelect || !window.CONFIGS?.EEZ_DATA) return;

  eezSelect.multiple = true;
  if (!eezSelect.size) eezSelect.size = 5;

  const eezArray = Object.entries(window.CONFIGS.EEZ_DATA).map(([id, v]) => ({
    id: v.id ?? id,
    label: v.label,
    iso3_codes: Array.isArray(v.iso3_codes) ? v.iso3_codes : [],
    is_parent: !!v.is_parent,
  }));

  console.log("eezArray", eezArray);

  const childrenByIso = new Map();
  for (const e of eezArray) {
    for (const iso of e.iso3_codes) {
      if (!childrenByIso.has(iso)) childrenByIso.set(iso, []);
      childrenByIso.get(iso).push(e);
    }
  }

  console.log("childrenByIso", childrenByIso);

  const optionRows = [];
  // individual EEZ rows
  for (const e of eezArray) {
    optionRows.push({ value: e.id, label: e.label, type: "individual_eez" });
  }
  // logical groups
  for (const parent of eezArray.filter(e => e.is_parent)) {
    const parentIso = parent.iso3_codes?.[0];
    const members = new Set([parent.id, ...((parentIso && childrenByIso.get(parentIso)) || []).map(c => c.id)]);
    optionRows.push({
      value: `group:${parent.id}`,
      label: `${parent.label} (All territories)`,
      type: "logical_group",
      eezIds: Array.from(members),
      description: "Selects parent + all territories",
    });
  }

  console.log("optionRows", optionRows);

  optionRows.sort((a, b) => a.label.localeCompare(b.label, undefined, { sensitivity: "base" }));

  const prev = new Set(Array.from(eezSelect.selectedOptions || []).map(o => o.value));
  const frag = document.createDocumentFragment();

  for (const row of optionRows) {
    const opt = document.createElement("option");
    opt.value = row.value;
    opt.textContent = row.label;
    opt.dataset.type = row.type;
    if (row.type === "logical_group") {
      opt.dataset.eezIds = JSON.stringify(row.eezIds);
      opt.dataset.description = row.description;
    } else {
      // IMPORTANT: carry the EEZ id for individuals
      opt.dataset.eezId = row.value;
    }
    if (prev.has(opt.value)) opt.selected = true;
    frag.appendChild(opt);
  }
  eezSelect.replaceChildren(frag);

  // Apply group → member selection mirroring (members only change when the group itself is toggled)
  eezSelect.addEventListener("change", () => {
    const options = Array.from(eezSelect.options);
    options.forEach(opt => {
      if (opt.dataset.type !== "logical_group") return;
      const memberIds = JSON.parse(opt.dataset.eezIds || "[]");
      const groupOn = opt.selected;
      memberIds.forEach(id => {
        const member = options.find(o => o.value === id);
        if (member) member.selected = groupOn;
      });
    });
  });
}


/**
 * Show information about the selected logical group
 */
export function renderSelectionInfo(selectedIds) {
  // remove previous info
  const existing = document.querySelector('.selection-info');
  if (existing) existing.remove();

  const eezData = window.CONFIGS?.EEZ_DATA || {};
  const isoToCountry = window.CONFIGS?.ISO3_TO_COUNTRY || {};

  // Build rows with country chips
  const rows = selectedIds
    .map(id => {
      const e = eezData[id];
      if (!e) return null;
      const countries = (e.iso3_codes || []).map(c => isoToCountry[c] || c);
      return {
        id,
        label: e.label,
        countries: Array.from(new Set(countries)).join(', ')
      };
    })
    .filter(Boolean)
    .sort((a, b) => a.label.localeCompare(b.label, undefined, { sensitivity: 'base' }));

  const infoDiv = document.createElement('div');
  infoDiv.className = 'selection-info';
  infoDiv.innerHTML = `
    <div class="info-content">
      <h4>Selected EEZs (${rows.length})</h4>
      <div class="eez-list">
        ${rows.map(r => `
          <div class="eez-row">
            <div class="eez-label"><strong>${r.label}</strong></div>
            <div class="eez-countries">${r.countries ? `<em>${r.countries}</em>` : ''}</div>
          </div>
        `).join('')}
      </div>
      <button class="close-info">×</button>
    </div>
  `;

  const filtersPanel = document.querySelector('.filters-panel') || document.getElementById('filters');
  (filtersPanel?.parentNode || document.body).insertBefore(infoDiv, filtersPanel?.nextSibling || null);

  infoDiv.querySelector('.close-info').addEventListener('click', () => infoDiv.remove());
}


/**
 * Get all EEZ IDs for the current selection
 * This handles both individual selections and logical groups
 */
export function getSelectedEEZIds() {
  const eezSelect = document.getElementById('eez-select');
  if (!eezSelect) return [];

  const ids = new Set();

  // iterate all selected <option>s
  for (const opt of Array.from(eezSelect.selectedOptions || [])) {
    if (opt.dataset.type === 'logical_group') {
      try {
        JSON.parse(opt.dataset.eezIds || '[]').forEach(id => ids.add(String(id)));
      } catch { /* noop */ }
    } else if (opt.dataset.type === 'individual_eez') {
      // individual eez id lives in data-eez-id, value === id too
      ids.add(opt.dataset.eezId || opt.value);
    }
  }

  return Array.from(ids);
}



/**
 * Validate date range (max 30 days) up until 7 days ago
 */
export function validateDateRange(startDate, endDate) {
  if (!startDate || !endDate) {
    showError('Missing date(s)');
    return false;
  }

  const today = new Date();
  const sevenDaysAgo = new Date(today.getTime() - 7 * 24 * 60 * 60 * 1000);

  // End date cannot be newer than 7 days ago
  if (endDate > sevenDaysAgo) {
    showError('End date must be before ' + sevenDaysAgo.toLocaleDateString());
    return false;
  }

  // Start must be before end
  if (startDate > endDate) {
    showError('Start date must be before end date');
    return false;
  }

  // Range cannot exceed 30 days
  const thirtyDays = 30 * 24 * 60 * 60 * 1000;
  if (endDate - startDate > thirtyDays) {
    showError('Error:' + '\nstart date: ' + startDate + '\nend date: ' + endDate);
    return false;
  }
  
  return true;
}


/**
 * Format date for display
 */
export function formatDate(dateString) {
  const date = new Date(dateString);
  return date.toLocaleDateString('en-US', {
    year: 'numeric',
    month: 'short',
    day: 'numeric'
  });
}

/**
 * Show error message to user
 */
export function showError(message, duration = 5000) {
  const errorDiv = document.createElement('div');
  errorDiv.className = 'error-message';
  errorDiv.textContent = message;
  
  document.body.appendChild(errorDiv);
  
  setTimeout(() => {
    if (errorDiv.parentNode) {
      errorDiv.remove();
    }
  }, duration);
}

/**
 * Show success message to user
 */
export function showSuccess(message, duration = 3000) {
  const successDiv = document.createElement('div');
  successDiv.className = 'success-message';
  successDiv.textContent = message;
  
  document.body.appendChild(successDiv);
  
  setTimeout(() => {
    if (successDiv.parentNode) {
      successDiv.remove();
    }
  }, duration);
}


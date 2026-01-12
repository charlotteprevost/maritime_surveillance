import config from './config.js';
const { debugLog } = config;

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
 * Check if an EEZ crosses the International Date Line based on its bbox
 * @param {Object} eezData - EEZ data object with bbox property
 * @returns {boolean} - True if the EEZ crosses the date line
 */
function crossesDateLine(eezData) {
  const bbox = eezData.bbox;
  if (!bbox || !Array.isArray(bbox) || bbox.length < 2) {
    return false;
  }
  
  // Bbox format: [[min_lat, min_lon], [max_lat, max_lon]]
  if (bbox[0].length >= 2 && bbox[1].length >= 2) {
    const min_lon = bbox[0][1];
    const max_lon = bbox[1][1];
    
    // Check if it crosses the date line (min_lon < -170 and max_lon > 170)
    return min_lon < -170 && max_lon > 170;
  }
  
  return false;
}

/**
 * Build the EEZ <select multiple>:
 *  - Options include one logical group per parent: "<Parent> (All territories)"
 *  - Options include every individual EEZ (parent and children) without "(Sovereign)"
 *  - All options sorted alphabetically by label
 *  - Selecting a logical group selects/deselects its members; child changes do NOT affect group
 *  - EEZs that cross the International Date Line are excluded (cannot be accurately represented)
 */
export function buildEEZSelect() {
  if (window.__EEZ_SELECT_BUILT__) return;
  window.__EEZ_SELECT_BUILT__ = true;

  const eezSelect = document.getElementById("eez-select");
  if (!eezSelect || !window.CONFIGS?.EEZ_DATA) return;

  // Ensure multiple mode is enabled
  eezSelect.multiple = true;
  if (!eezSelect.size) eezSelect.size = 5;

  // Remove placeholder option if it exists
  const placeholder = eezSelect.querySelector('option[value=""]');
  if (placeholder) placeholder.remove();

  // Filter out EEZs that cross the date line
  const eezData = window.CONFIGS.EEZ_DATA;
  const dateLineCrossingIds = new Set();
  
  const eezArray = Object.entries(eezData)
    .filter(([id, v]) => {
      // Check if this EEZ crosses the date line
      if (crossesDateLine(v)) {
        dateLineCrossingIds.add(String(v.id ?? id));
        debugLog.log(`Excluding EEZ ${id} (${v.label}) - crosses International Date Line`);
        return false; // Exclude from list
      }
      return true; // Include in list
    })
    .map(([id, v]) => ({
      id: String(v.id ?? id), // Ensure ID is string
      label: v.label,
      iso3_codes: Array.isArray(v.iso3_codes) ? v.iso3_codes : [],
      is_parent: !!v.is_parent,
      bbox: v.bbox // Keep bbox for later use if needed
    }));

  debugLog.log("eezArray", eezArray);

  const childrenByIso = new Map();
  for (const e of eezArray) {
    // Skip if this EEZ crosses the date line
    if (dateLineCrossingIds.has(e.id)) continue;
    
    for (const iso of e.iso3_codes) {
      if (!childrenByIso.has(iso)) childrenByIso.set(iso, []);
      childrenByIso.get(iso).push(e);
    }
  }

  debugLog.log("childrenByIso", childrenByIso);

  const optionRows = [];
  // individual EEZ rows
  for (const e of eezArray) {
    optionRows.push({ value: e.id, label: e.label, type: "individual_eez" });
  }

  // logical groups - only create ONE group per ISO3 code for the main country entry
  const iso3ToCountry = window.CONFIGS?.ISO3_TO_COUNTRY || {};
  const processedIsos = new Set();

  for (const parent of eezArray.filter(e => e.is_parent)) {
    // Skip if parent crosses the date line
    if (dateLineCrossingIds.has(parent.id)) continue;
    
    const parentIso = parent.iso3_codes?.[0];
    if (!parentIso || processedIsos.has(parentIso)) continue;

    const members = childrenByIso.get(parentIso) || [];
    // Filter out members that cross the date line
    const validMembers = members.filter(m => !dateLineCrossingIds.has(m.id));
    
    // Only create a group if there are actually multiple valid EEZs with this ISO3 code
    if (validMembers.length > 1) {
      // Find the main country entry (the one whose label matches the country name)
      const countryName = iso3ToCountry[parentIso];

      // Only create group option if this parent's label matches the country name
      // This prevents creating groups for individual territories like "Alaska"
      if (countryName && parent.label === countryName) {
        // Only include valid members (not crossing date line)
        const memberIds = new Set([parent.id, ...validMembers.map(c => c.id)]);
        optionRows.push({
          value: `group:${parent.id}`,
          label: `${parent.label} (All territories)`,
          type: "logical_group",
          eezIds: Array.from(memberIds),
          description: "Selects parent + all territories",
        });
        processedIsos.add(parentIso);
      }
    }
  }

  debugLog.log("optionRows", optionRows);

  optionRows.sort((a, b) => a.label.localeCompare(b.label, undefined, { sensitivity: "base" }));

  // Preserve current selections
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
      // IMPORTANT: carry the EEZ id for individuals - use the actual ID
      opt.dataset.eezId = String(row.value); // Store as string
    }
    if (prev.has(opt.value)) opt.selected = true;
    frag.appendChild(opt);
  }
  eezSelect.replaceChildren(frag);

  // Apply group → member selection mirroring (members only change when the group itself is toggled)
  // Track previous selection state to detect what changed
  let previousSelection = new Set(Array.from(eezSelect.selectedOptions).map(o => o.value));
  let isProcessingGroupChange = false;

  // Handle clicks to ensure multi-select works properly without requiring Ctrl/Cmd
  // In standard multi-select, clicking without modifier keys replaces selection
  // We want it to toggle instead (like checkboxes)
  eezSelect.addEventListener("mousedown", (e) => {
    // Ensure multiple mode is enabled
    if (!eezSelect.multiple) {
      eezSelect.multiple = true;
    }

    // If clicking on an option without modifier keys, manually toggle it
    const option = e.target;
    if (option.tagName === 'OPTION' && !e.ctrlKey && !e.metaKey && !e.shiftKey) {
      e.preventDefault(); // Prevent default single-select behavior

      // Toggle the option's selected state
      option.selected = !option.selected;

      // Trigger change event manually
      eezSelect.dispatchEvent(new Event('change', { bubbles: true }));
    }
  });

  eezSelect.addEventListener("change", (e) => {
    // Ensure multiple mode is still enabled (defensive)
    if (!eezSelect.multiple) {
      eezSelect.multiple = true;
      debugLog.warn('Select was not in multiple mode, fixed it');
    }

    // Prevent recursive calls
    if (isProcessingGroupChange) return;

    const currentSelection = new Set(Array.from(eezSelect.selectedOptions).map(o => o.value));
    const options = Array.from(eezSelect.options);

    // Find what changed - only process groups that were actually toggled
    const changedGroups = [];
    options.forEach(opt => {
      if (opt.dataset.type !== "logical_group") return;
      const wasSelected = previousSelection.has(opt.value);
      const isSelected = currentSelection.has(opt.value);
      if (wasSelected !== isSelected) {
        changedGroups.push({ opt, isSelected });
      }
    });

    // Only process groups that actually changed (not individual selections)
    if (changedGroups.length > 0) {
      isProcessingGroupChange = true;

      changedGroups.forEach(({ opt, isSelected }) => {
        try {
          const memberIds = JSON.parse(opt.dataset.eezIds || "[]");
          memberIds.forEach(id => {
            const member = options.find(o => {
              // Match by value (for individual EEZs) or dataset.eezId
              const idStr = String(id);
              return o.value === idStr || o.dataset.eezId === idStr;
            });
            if (member && member.dataset.type === "individual_eez") {
              member.selected = isSelected;
            }
          });
        } catch (e) {
          debugLog.warn('Failed to process group selection:', e);
        }
      });

      isProcessingGroupChange = false;
    }

    // Update previous selection state AFTER processing
    previousSelection = new Set(Array.from(eezSelect.selectedOptions).map(o => o.value));

    // Debug: log current selection state
    debugLog.log('Change event - Selected options:', Array.from(eezSelect.selectedOptions).map(o => o.value));
  });
}


/**
 * Show information about the selected logical group
 */
export function renderSelectionInfo(selectedIds) {
  // remove previous info (ensure we only have one)
  const existing = document.querySelectorAll('.selection-info');
  existing.forEach(el => el.remove());

  if (selectedIds.length === 0) {
    return; // Don't show anything if nothing is selected
  }

  const eezData = window.CONFIGS?.EEZ_DATA || {};
  const isoToCountry = window.CONFIGS?.ISO3_TO_COUNTRY || {};

  // Build rows with country chips - use Set to prevent duplicates
  const seenIds = new Set();
  const rows = selectedIds
    .map(id => {
      // Skip if we've already seen this ID
      if (seenIds.has(String(id))) return null;
      seenIds.add(String(id));

      const e = eezData[String(id)];
      if (!e) {
        debugLog.warn('EEZ data not found for ID:', id);
        return null;
      }
      const countries = (e.iso3_codes || []).map(c => isoToCountry[c] || c);
      return {
        id: String(id),
        label: e.label,
        countries: Array.from(new Set(countries)).join(', ')
      };
    })
    .filter(Boolean)
    .sort((a, b) => a.label.localeCompare(b.label, undefined, { sensitivity: 'base' }));

  if (rows.length === 0) {
    return; // Don't show if no valid rows
  }

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
  if (!eezSelect) {
    debugLog.warn('EEZ select element not found');
    return [];
  }

  // Ensure multiple mode is enabled (defensive check)
  if (!eezSelect.multiple) {
    debugLog.warn('Select was not in multiple mode, fixing...');
    eezSelect.multiple = true;
  }

  const ids = new Set();
  const selectedOptions = Array.from(eezSelect.selectedOptions || []);

  // Debug: log all options and their selected state
  if (selectedOptions.length === 0) {
    debugLog.log('No options selected. Total options:', eezSelect.options.length);
  }

  // iterate all selected <option>s
  for (const opt of selectedOptions) {
    // Skip placeholder/empty options
    if (!opt.value || opt.value === '') {
      debugLog.log('Skipping empty option:', opt);
      continue;
    }

    if (opt.dataset.type === 'logical_group') {
      try {
        const memberIds = JSON.parse(opt.dataset.eezIds || '[]');
        memberIds.forEach(id => {
          const cleanId = String(id);
          if (cleanId && !cleanId.startsWith('group:')) {
            ids.add(cleanId);
          }
        });
      } catch (e) {
        debugLog.warn('Failed to parse group EEZ IDs:', e);
      }
    } else if (opt.dataset.type === 'individual_eez') {
      // individual eez id lives in data-eez-id, value === id too
      const eezId = opt.dataset.eezId || opt.value;
      if (eezId && eezId !== '' && !eezId.startsWith('group:')) {
        ids.add(String(eezId));
      } else {
        debugLog.warn('Invalid EEZ ID:', eezId, 'from option:', opt);
      }
    } else {
      debugLog.warn('Option has no type:', opt.value, opt.dataset);
    }
  }

  const cleanIds = Array.from(ids);
  debugLog.log('Selected EEZ IDs:', cleanIds, 'from', selectedOptions.length, 'selected options');

  // If we have selected options but no IDs, something is wrong
  if (selectedOptions.length > 0 && cleanIds.length === 0) {
    console.error('Selected options but no IDs extracted:', selectedOptions.map(o => ({
      value: o.value,
      type: o.dataset.type,
      eezId: o.dataset.eezId
    })));
  }

  return cleanIds;
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


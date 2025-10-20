import { applyFilters } from '../main';

describe('applyFilters', () => {
  beforeEach(() => {
    document.body.innerHTML = `
      <input id="start" value="2025-10-01" />
      <input id="end" value="2025-10-07" />
      <select id="eez-select" multiple>
        <option value="Alaska">Alaska</option>
        <option value="Hawaii">Hawaii</option>
      </select>
      <div id="loading-spinner" class="hidden"></div>
    `;

    global.fetch = jest.fn(() =>
      Promise.resolve({
        ok: true,
        json: () => Promise.resolve({ summaries: [], tile_url: '' }),
      })
    );
  });

  afterEach(() => {
    jest.clearAllMocks();
  });

  it('sends correct filters to the backend', async () => {
    document.getElementById('eez-select').value = 'Alaska';

    await applyFilters();

    expect(global.fetch).toHaveBeenCalledWith(
      expect.stringContaining('eez_ids=%5B%22Alaska%22%5D') // Encoded JSON array
    );
  });

  it('shows error if no EEZs are selected', async () => {
    document.getElementById('eez-select').value = '';

    const showError = jest.fn();
    global.showError = showError;

    await applyFilters();

    expect(showError).toHaveBeenCalledWith('Please select EEZ(s) and date range');
  });
});
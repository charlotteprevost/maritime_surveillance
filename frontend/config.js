// frontend/config.js
const config = {
  // Auto-detect backend URL
  // For GitHub Pages: backend will be on a different domain (e.g., Render, Railway)
  // The backend URL should be set via window.CONFIGS.backendUrl from /api/configs
  // This is just a fallback for local development
  backendUrl: (() => {
    // Check if we're in local development
    if (window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1') {
      return 'http://localhost:5000';
    }
    // For production (GitHub Pages), backend URL will come from window.CONFIGS.backendUrl
    // which is set by the backend's /api/configs endpoint
    // If not available yet, return null and let the code handle it
    return null;
  })(),

  // Debug mode: set to true for development, false for production
  // Can be overridden via URL parameter: ?debug=true
  debug: (() => {
    const urlParams = new URLSearchParams(window.location.search);
    if (urlParams.get('debug') === 'true') return true;
    if (urlParams.get('debug') === 'false') return false;
    // Default: debug in localhost, off in production
    return window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1';
  })()
};

// Debug logging utility
const debugLog = {
  log: (...args) => {
    if (config.debug) console.log(...args);
  },
  warn: (...args) => {
    if (config.debug) console.warn(...args);
  },
  error: (...args) => {
    // Always log errors, even in production
    console.error(...args);
  },
  info: (...args) => {
    if (config.debug) console.log(...args);
  }
};

// Export debug utility
config.debugLog = debugLog;

export default config;
// frontend/config.js
const config = {
  // Auto-detect backend URL
  // For GitHub Pages: backend will be on a different domain (e.g., Render, Railway)
  // The backend URL should be set via window.CONFIGS.backendUrl from /api/configs
  // This is just a fallback for local development
  backendUrl: (() => {
    const urlParams = new URLSearchParams(window.location.search);
    const override = urlParams.get('backend');
    if (override) return override;

    const host = window.location.hostname;
    const isLocalhost = host === 'localhost' || host === '127.0.0.1';
    const isPrivateIp = (
      host.startsWith('10.') ||
      host.startsWith('192.168.') ||
      /^172\.(1[6-9]|2\d|3[0-1])\./.test(host)
    );

    // Local dev: same machine or LAN (so phones can hit the local backend)
    if (isLocalhost) return 'http://localhost:5000';
    if (isPrivateIp) return `http://${host}:5000`;

    // Production fallback (Render)
    return 'https://maritime-surveillance.onrender.com';
  })(),

  // Debug mode: set to true for development, false for production
  // Can be overridden via URL parameter: ?debug=true
  debug: (() => {
    const urlParams = new URLSearchParams(window.location.search);
    if (urlParams.get('debug') === 'true') return true;
    if (urlParams.get('debug') === 'false') return false;
    // Default: debug in localhost/LAN, off in production
    const host = window.location.hostname;
    const isLocalhost = host === 'localhost' || host === '127.0.0.1';
    const isPrivateIp = (
      host.startsWith('10.') ||
      host.startsWith('192.168.') ||
      /^172\.(1[6-9]|2\d|3[0-1])\./.test(host)
    );
    return isLocalhost || isPrivateIp;
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
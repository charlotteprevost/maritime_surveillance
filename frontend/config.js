// frontend/config.js
const config = {
    // Auto-detect backend URL
    backendUrl: (() => {
      if (window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1') {
        // Local dev
        return 'http://localhost:5000';
      } else {
        // Production -> use backend domain
        return window.location.origin;
      }
    })()
  };
  
  export default config;
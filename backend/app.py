# backend/app.py

"""
Flask application initialization for the Maritime Surveillance backend.

This module sets up CORS, loads application configuration and EEZ data,
initializes a GFW API client (if available), and registers the API routes.
The GFW API token should be provided via the `GFW_API_TOKEN` environment
variable; if absent, the client will not be initialized and API calls may
not function as expected.
"""

import os
import json
import importlib.util

from flask import Flask
from flask_cors import CORS
from dotenv import load_dotenv

from routes.api import api_routes


# Load environment variables from a .env file if present
load_dotenv()

# --- Initialize Flask app ---
app = Flask(__name__)

# Configure CORS: allow requests from configured frontend origins.
# Default to "*" so local/mobile dev origins (LAN IPs, etc) can call the API.
# If you want to restrict this in production, set FRONTEND_ORIGINS to a comma-separated list.
frontend_origins = os.getenv("FRONTEND_ORIGINS", "*")
origin_list = [o.strip() for o in frontend_origins.split(",") if o.strip()]

# Flask-CORS treats origins="*" as allow-all, but origins=["*"] may not behave as expected.
# For local/LAN development, treat localhost-only origins as allow-all so mobile devices
# on the same network can access the API via LAN IP.
localhost_only = all(
    "localhost" in o or "127.0.0.1" in o
    for o in origin_list
) if origin_list and origin_list != ["*"] else False
cors_origins = "*" if (origin_list == ["*"] or localhost_only) else origin_list
# NOTE: Flask-CORS resource keys are regex patterns; "/api/*" does NOT match "/api/configs".
# Use "/api/.*" to match all API routes.
CORS(app, resources={r"/api/.*": {"origins": cors_origins}})


# --- Initialize the GFW API client ---
# The client is stored in app.config so that it can be accessed from within route handlers
try:
    # Attempt to import a custom GFW API client. This client should wrap
    # the external Global Fishing Watch API and handle authentication.
    from utils.gfw_client import GFWApiClient  # type: ignore

    api_token = os.getenv("GFW_API_TOKEN")
    if api_token:
        # Instantiate the client with the provided token
        app.config["GFW_CLIENT"] = GFWApiClient(api_token)
    else:
        # If no token is provided, do not initialize the client
        app.config["GFW_CLIENT"] = None
except ImportError:
    # If the GFW client module is missing, store None to avoid errors
    app.config["GFW_CLIENT"] = None


# --- Register Blueprint for API routes ---
app.register_blueprint(api_routes)


def load_app_data():
    """
    Load the EEZ dataset and configuration into the application context.

    EEZ data is expected to be stored in `utils/eez_data_improved.json`.
    Additional configuration (such as default filters and color ramps) is
    loaded from `configs/config.py`. These objects are stored on
    `app.config` for easy access in routes.
    """
    base_dir = os.path.dirname(__file__)
    # Load EEZ data
    eez_data_path = os.path.join(base_dir, "utils", "eez_data_improved.json")
    with open(eez_data_path, "r", encoding="utf-8") as f:
        app.config["EEZ_DATA"] = json.load(f)
    # Load additional configuration module
    config_path = os.path.join(base_dir, "configs", "config.py")
    spec = importlib.util.spec_from_file_location("config", config_path)
    config_module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(config_module)  # type: ignore
    app.config["CONFIG"] = config_module


if __name__ == "__main__":
    import logging
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)
    
    logger.info("Starting server...")
    logger.info("Loading app data...")
    load_app_data()
    logger.info("App data loaded successfully.")
    
    # Get configuration from environment variables
    debug_mode = os.getenv("FLASK_DEBUG", "False").lower() == "true"
    port = int(os.getenv("PORT", 5000))
    host = os.getenv("HOST", "0.0.0.0")
    
    # Start the Flask server
    app.run(host=host, port=port, debug=debug_mode)
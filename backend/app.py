# backend/app.py
from flask import Flask
from flask_cors import CORS
from dotenv import load_dotenv
from routes.api import api_routes
import os
import json
import importlib.util

load_dotenv()

# --- Initialize Flask app ---
app = Flask(__name__)
# Read allowed frontend origins from environment; default to common local dev ports
frontend_origins = os.getenv("FRONTEND_ORIGINS", "http://localhost:8080,http://localhost:5000")
origin_list = [o.strip() for o in frontend_origins.split(",") if o.strip()]
CORS(app, resources={r"/api/*": {"origins": origin_list}})

# --- Register Blueprint from routes/detections.py ---
app.register_blueprint(api_routes)

def load_app_data():
    base_dir = os.path.dirname(__file__)
    eez_data_path = os.path.join(base_dir, "utils", "eez_data_improved.json")
    with open(eez_data_path, "r", encoding="utf-8") as f:
        app.config["EEZ_DATA"] = json.load(f)
    config_path = os.path.join(base_dir, "configs", "config.py")
    spec = importlib.util.spec_from_file_location("config", config_path)
    config_module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(config_module)
    app.config["CONFIG"] = config_module

if __name__ == "__main__":
    print("Starting server...")
    print("Loading app data...")
    load_app_data()
    print("App data loaded successfully.")
    app.run(debug=True)

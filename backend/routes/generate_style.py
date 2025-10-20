# routes/api.py

from flask import Blueprint, request, jsonify, current_app
from datetime import datetime, timezone
import traceback

from configs.config import WINGS_API
from schemas.generate_png import GeneratePngRequest
from pydantic import ValidationError
from urllib.parse import quote_plus
from utils.api_helpers import (
    build_gfw_filters,
    get_style_cache_key,
    generate_style_cached,
)

generate_style_route = Blueprint("generate_style_route", __name__)

# --------------------------
# 🔍 Generate Style (for the heatmap)
# ONLY NEEDED ONCE FOR EACH COLOR SCHEME
# --------------------------

# The data will come from the frontend in this format:
# {
#     "start": "2025-04-01",
#     "end": "2025-04-30",
#     "interval": "DAY",
#     "color": "#002457",
#     "filters": [{"flag": ["GB"]}]
# } 
# The start and end will be in the format YYYY-MM-DD
# The interval will be one of DAY, MONTH, YEAR
# The color will be a hex color code
# The filters will be a list of filters
# The dataset will be the dataset to use
@generate_style_route.route("/api/generate-style", methods=["POST"])
def generate_style():
    try:
        data = request.get_json()
        query = GeneratePngRequest(**data)
        filters_str = build_gfw_filters(query.filters)

        cache_key, style_id = get_style_cache_key(
            dataset=query.dataset,
            date_range=query.date_range,
            filters=filters_str,
            interval=query.interval or "DAY",
            color=query.color
        )
        current_app.logger.info(f"Generated style ID: {style_id}")
        style_cache = generate_style_cached(cache_key)
        current_app.logger.info(f"Style cache: {style_cache}")

        base_url = WINGS_API["tile"]
        tile_url = f"{base_url}/{{z}}/{{x}}/{{y}}?format=PNG"
        interval = query.interval or "DAY"
        tile_url += f"&interval={interval}&datasets[0]={query.dataset}"
        tile_url += f"&filters[0]={quote_plus(filters_str)}&date-range={query.date_range}&style={style_id}"

        return jsonify({
            "style_id": style_id,
            "tile_url": tile_url,
            "colorRamp": style_cache.get("colorRamp")
        }), 200

    except ValidationError as ve:
        return jsonify({"error": ve.errors()}), 422

    except Exception as e:
        current_app.logger.error(f"Unhandled error in /api/generate-style: {traceback.format_exc()}")
        return jsonify({"error": "Internal server error"}), 500

from flask import Blueprint, request, jsonify, current_app
import logging
import time
from datetime import datetime, timezone
from collections import defaultdict
import json

from utils.api_helpers import build_gfw_filters, fetch_detections_for_eez, fetch_summary_report, fetch_bins, fetch_all_bins, get_style_cache_key, generate_style_cached, fetch_events
from utils.eez_utils import classify_eez, resolve_country_names_to_iso3, get_all_eezs, resolve_iso3_to_country, resolve_label_to_eez_ids

api_routes = Blueprint("api_routes", __name__)


@api_routes.route("/api/detections")
def get_detections():
    from datetime import datetime, timezone
    args = request.args

    eez_ids = args.getlist("eez_id", type=int)
    if not eez_ids:
        return jsonify({"error": "No EEZ ID(s) provided"}), 400

    fmt = "%Y-%m-%d"
    try:
        now = datetime.now(timezone.utc)
        past = now.replace(day=max(1, now.day - 7))
        start_str = args.get("start", past.strftime(fmt))
        end_str = args.get("end", now.strftime(fmt))
        start = datetime.strptime(start_str, fmt)
        end = datetime.strptime(end_str, fmt)

        if (end - start).days > 30:
            return jsonify({"error": "Date range cannot exceed 30 days"}), 400
        if start > end:
            return jsonify({"error": "Start date must be before end date"}), 400
    except Exception:
        return jsonify({"error": "Invalid date format"}), 400

    vessel_type = args.get("vessel_type")
    neural_type = args.get("neural_vessel_type")
    geartype = args.get("geartype")

    filters = build_gfw_filters(neural_type=neural_type, geartype=geartype, vessel_type=vessel_type)
    eezs = [e for e in get_all_eezs(current_app.config) if e["id"] in eez_ids]

    if not eezs:
        return jsonify({"error": "No matching EEZs found"}), 404


    added = False

    features = []
    empty_eezs = []
    failed_eezs = []

    for eez in eezs:
        try:

            # test for wrong eez_id
            print(f"\n\nFetching for WRONG\n\n")
            data_wrong = fetch_detections_for_eez(eez["id"]*1000, start_str, end_str, filters)
            print("\n\ndata_wrong: ", data_wrong, "\n\n")

            # If there are no detections, the entries object will look something like this:
            # 'entries': [{'public-global-sar-presence:v3.0': None}]
            # If there are detections, the entries object will look something like this:
            # 'entries': 
            #   [{'public-global-sar-presence:v3.0': 
            #       [{
            #           'lat': 1.23456, 
            #           'lon': 7.89012,
            #           'date': '2025-01-01',
            #           'detections': 1,
            #           'vesselIDs': 1
            #       }]
            #   }]
            # We need to check if the value is a list and if it is, we need to check if it is not empty
            # If it is empty, we need to add the eez to the empty_eezs list
            # If it is not empty, we need to add the detections to the features list
            # If the value is not a list, we need to add the eez to the failed_eezs list

            
            # logging.info(f"Fetching for {eez['label']} ({eez['id']})")
            # time.sleep(0.25)
            # data = fetch_detections_for_eez(eez["id"], start_str, end_str, filters)

            # if data.get("entries") is None:
            #     empty_eezs.append({"id": eez["id"], "label": eez["label"], "country": eez["iso3"]})
            # else:
            #     for entry in data.get("entries", []):
            #         for det_list in entry.values():
            #             if isinstance(det_list, list):
            #                 for det in det_list:
            #                     if "lat" in det and "lon" in det:
            #                         features.append({
            #                             "type": "Feature",
            #                             "geometry": {"type": "Point", "coordinates": [det["lon"], det["lat"]]},
            #                             "properties": {
            #                                 "eez_id": eez["id"],
            #                                 "country": eez.get("iso3"),
            #                                 "label": eez["label"],
            #                                 "eez_type": classify_eez(eez["label"]),
            #                                 "date": det.get("date"),
            #                                 "detections": det.get("detections", 1),
            #                                 "vessel_type": det.get("vessel_type"),
            #                                 "geartype": det.get("geartype"),
            #                                 "neural_vessel_type": det.get("neural_vessel_type"),
            #                                 "neural_vessel_type_confidence": det.get("neural_vessel_type_confidence")
            #                             }
            #                         })
            #                         added = True
            #             else:
            #                 print("no detections found for entry: ", entry)
            # if not added:
            #     empty_eezs.append({"id": eez["id"], "label": eez["label"], "country": eez["iso3"]})
        except Exception as e:
            logging.warning(f"Failed for EEZ {eez['id']}: {e}")
            failed_eezs.append({"id": eez["id"], "label": eez["label"], "error": str(e)})

    return jsonify({
        "type": "FeatureCollection",
        "features": features,
        "empty_eezs": empty_eezs,
        "failed_eezs": failed_eezs
    })


@api_routes.route("/api/summary", methods=["GET"])
def get_summary():
    args = request.args
    # country = args.get("country")
    eez_ids = args.getlist("eez_ids", type=int)
    if not eez_ids:
        return jsonify({"error": "No EEZ ID(s) provided"}), 400
    eezs = [e for e in get_all_eezs(current_app.config) if e["id"] in eez_ids]
    if not eezs:
        return jsonify({"error": "No EEZs found"}), 404
    iso3 = eezs[0]["iso3"]
    start = args.get("start")
    end = args.get("end")
    group_by = args.get("group_by", "GEARTYPE").upper()
    if group_by not in {"GEARTYPE", "FLAG", "VESSEL_ID", "SHIPTYPE"}:
        return jsonify({"error": "Invalid group_by"}), 400

    if not start or not end:
        return jsonify({"error": "Missing start or end date"}), 400

    # Optional filters
    matched = args.get("matched", "false")
    geartype = args.get("geartype")
    shiptype = args.get("shiptype")
    neural_vessel_type = args.get("neural_vessel_type")

    filters = build_gfw_filters(
        matched=matched,
        geartype=geartype,
        vessel_type=shiptype,
        neural_type=neural_vessel_type
    )

    summaries = []
    empty_eezs = []

    for eez in eezs:
        try:
            result = fetch_summary_report(eez["id"], start, end, group_by, filters)
            summary = result.get("summary", [])

            if summary:
                summaries.append({
                    "eez_id": eez["id"],
                    "label": eez["label"],
                    "summary": summary
                })
            else:
                empty_eezs.append({
                    "id": eez["id"],
                    "label": eez["label"]
                })

        except Exception as e:
            empty_eezs.append({
                "id": eez["id"],
                "label": eez["label"],
                "error": str(e)
            })

    return jsonify({
        "group_by": group_by,
        "summaries": summaries,
        "empty_eezs": empty_eezs
    })


@api_routes.route("/api/bins/<int:z>", methods=["GET"])
def get_bins(z):
    args = request.args
    start = args.get("start")
    end = args.get("end")

    if not start or not end:
        return jsonify({"error": "Missing required parameters"}), 400

    matched = args.get("matched", "false")
    geartype = args.get("geartype")
    shiptype = args.get("shiptype")
    neural_vessel_type = args.get("neural_vessel_type")

    filters = build_gfw_filters(
        matched=matched,
        geartype=geartype,
        vessel_type=shiptype,
        neural_type=neural_vessel_type
    )

    try:
        bins = fetch_bins(z, start, end, filters)
        return jsonify(bins)
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500


@api_routes.route("/api/bins/all", methods=["GET"])
def get_all_bins():
    args = request.args
    start = args.get("start")
    end = args.get("end")
    zooms = args.get("zooms", "1,2,3,4,5,6")

    if not start or not end:
        return jsonify({"error": "Missing required parameters"}), 400

    try:
        zoom_levels = [int(z.strip()) for z in zooms.split(",") if z.strip().isdigit()]
        if not zoom_levels:
            raise ValueError("No valid zoom levels")
    except ValueError:
        return jsonify({"error": "Invalid zoom levels"}), 400

    matched = args.get("matched", "false")
    geartype = args.get("geartype")
    shiptype = args.get("shiptype")
    neural_vessel_type = args.get("neural_vessel_type")

    filters = build_gfw_filters(
        matched=matched,
        geartype=geartype,
        vessel_type=shiptype,
        neural_type=neural_vessel_type
    )

    try:
        bins = fetch_all_bins(zoom_levels, start, end, filters)
        return jsonify(bins)
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500


@api_routes.route("/api/generate-style", methods=["GET"])
def get_heatmap_style():
    args = request.args
    start = args.get("start")
    end = args.get("end")
    interval = args.get("interval", "DAY")
    valid_intervals = {"DAY", "HOUR", "10DAYS", "MONTH"}
    if interval.upper() not in valid_intervals:
        return jsonify({"error": "Invalid interval"}), 400
    color = args.get("color", "#002457")


    if not start or not end:
        return jsonify({"error": "Missing required parameters"}), 400

    # Filters
    matched = args.get("matched", "false")
    geartype = args.get("geartype")
    shiptype = args.get("shiptype")
    neural_vessel_type = args.get("neural_vessel_type")

    filters = build_gfw_filters(
        matched=matched,
        geartype=geartype,
        vessel_type=shiptype,
        neural_type=neural_vessel_type
    )

    try:
        cache_key, style_id = get_style_cache_key(
            start=start, end=end, filters=filters, interval=interval, color=color
        )
        style = generate_style_cached(cache_key)

        return jsonify({
            "style_id": style_id,
            "colorRamp": style["colorRamp"]
        })

    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500


@api_routes.route("/api/events")
def get_events():
    from utils.api_helpers import get_gfw_token
    import requests

    # Extract query args
    eez_ids = request.args.getlist("eez_ids", type=int)
    if not eez_ids:
        return jsonify({"error": "No EEZ ID(s) provided"}), 400
    eezs = [e for e in get_all_eezs(current_app.config) if e["id"] in eez_ids]
    if not eezs:
        return jsonify({"error": "No EEZs found"}), 404
    iso3 = eezs[0]["iso3"]
    start = request.args.get("start")
    end = request.args.get("end")
    types = request.args.getlist("type")
    vessel_type = request.args.get("vessel_type")

    if not start or not end:
        return jsonify({"error": "Missing start or end date"}), 400

    datasets_map = {
        "FISHING": "public-global-fishing-events:latest",
        "ENCOUNTER": "public-global-encounters-events:latest",
        "LOITERING": "public-global-loitering-events:latest",
        "PORT_VISIT": "public-global-port-visits-events:latest",
        "GAP": "public-global-gaps-events:latest"
    }

    datasets = list({datasets_map[t] for t in types if t in datasets_map})
    if not datasets:
        return jsonify({"error": "No valid event types provided"}), 400

    # Prepare body
    post_body = {
        "datasets": datasets,
        "startDate": start,
        "endDate": end,
        "region": {"dataset": "public-eez-areas", "id": eez_ids},
    }
    if types:
        post_body["types"] = types
    if vessel_type:
        post_body["vesselTypes"] = [vessel_type]

    # Call GFW
    res = requests.post(
        "https://gateway.api.globalfishingwatch.org/v3/events?limit=1000&offset=0",
        headers={"Authorization": f"Bearer {get_gfw_token()}"},
        json=post_body,
    )

    if res.status_code != 200:
        return jsonify({"error": "GFW API failed", "status": res.status_code}), 502

    return jsonify({"events": res.json().get("entries", []), "failed_eezs": []})


@api_routes.route("/api/eez-list", methods=["GET"])
def get_eez_list():
    from utils.eez_utils import get_all_eezs

    grouped = defaultdict(list)
    eezs = get_all_eezs(current_app.config)

    for e in sorted(eezs, key=lambda x: (x["iso3"], x["label"])):
        grouped[e["iso3"]].append(e["label"])

    # Format: { FRA: { iso3: 'FRA', name: 'France', subregions: ['France (Only)', 'Réunion', ...] }, ... }
    output = []
    for iso3, labels in grouped.items():
        base_label = next((l for l in labels if l.lower() == resolve_iso3_to_country(iso3).lower()), labels[0])
        entry = {
            "iso3": iso3,
            "group": f"{resolve_iso3_to_country(iso3)} (All EEZs)",
            "subregions": [{"label": l} for l in sorted(labels)]
        }
        output.append(entry)

    return jsonify(output)


@api_routes.route("/api/eez-options", methods=["GET"])
def get_eez_options():
    """
    Serve preprocessed EEZ dropdown structure based on eez_dropdown_final.json
    """
    try:
        with open("configs/eez_dropdown_final.json") as f:
            dropdown_data = json.load(f)
        return jsonify(dropdown_data)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

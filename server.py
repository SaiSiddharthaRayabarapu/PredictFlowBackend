from flask import Flask, request, jsonify, Response
from flask_cors import CORS
import subprocess
import os
import json

app = Flask(__name__)

# ✅ Allow frontend access
CORS(app, resources={r"/*": {"origins": "*"}})

BASE_DIR = os.path.dirname(os.path.abspath(__file__))


# =============================
# GACHIBOWLI BOUNDARY
# =============================
MIN_LAT = 17.418
MAX_LAT = 17.470
MIN_LNG = 78.320
MAX_LNG = 78.380


def is_inside_gachibowli(lat, lng):
    return MIN_LAT <= lat <= MAX_LAT and MIN_LNG <= lng <= MAX_LNG


# =============================
# RUN SIMULATION
# =============================
@app.route("/run_simulation", methods=["POST"])
def run_simulation():

    try:

        data = request.json

        scenario = data.get("scenario", "mall")
        visitors = int(data.get("visitors", 2000))
        lat = float(data.get("lat", 17.4401))
        lng = float(data.get("lng", 78.3489))

        print("Scenario:", scenario)
        print("Visitors/hr:", visitors)
        print("Location:", lat, lng)

        # =============================
        # LOCATION VALIDATION
        # =============================
        if not is_inside_gachibowli(lat, lng):
            return jsonify({
                "status": "error",
                "message": "Selected location is outside Gachibowli simulation zone"
            }), 400

        # =============================
        # RUN ML SCRIPT
        # =============================
        subprocess.run(
            [
                "python",
                "ml_simulation.py",
                scenario,
                str(visitors),
                str(lat),
                str(lng)
            ],
            check=True
        )

        output_file = os.path.join(BASE_DIR, "output.json")

        vehicle_count = 0

        if os.path.exists(output_file):
            with open(output_file) as f:
                output = json.load(f)
                vehicle_count = output.get("total_vehicles_per_hour", 0)

        vehicle_count = int(vehicle_count)

        return jsonify({
            "status": "success",
            "map_url": "https://predictflowbackend.onrender.com/map",
            "vehicle_count": vehicle_count,
            "visitors_per_hour": visitors
        })

    except Exception as e:

        print("ERROR:", e)

        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500


# =============================
# SERVE MAP (IFRAME SAFE)
# =============================
@app.route("/map")
def serve_map():

    map_path = os.path.join(BASE_DIR, "ml_traffic_prediction.html")

    if not os.path.exists(map_path):
        return "Map not generated yet"

    with open(map_path, "r", encoding="utf-8") as f:
        html = f.read()

    response = Response(html, mimetype="text/html")

    # ✅ allow iframe
    response.headers["X-Frame-Options"] = "ALLOWALL"

    return response


# =============================
# START SERVER (RENDER READY)
# =============================
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
import osmnx as ox
import folium
import joblib
import pandas as pd
import json
import sys
import math


# =============================
# INPUT FROM SERVER
# =============================
SCENARIO = sys.argv[1] if len(sys.argv) > 1 else "mall"
visitors = int(sys.argv[2]) if len(sys.argv) > 2 else 2000
lat = float(sys.argv[3]) if len(sys.argv) > 3 else 17.4401
lng = float(sys.argv[4]) if len(sys.argv) > 4 else 78.3489

center_point = (lat, lng)

print("Scenario:", SCENARIO)
print("Visitors/hr:", visitors)
print("Location:", center_point)


# =============================
# GACHIBOWLI BOUNDARY CHECK
# =============================
GACHIBOWLI_CENTER = (17.4401, 78.3489)
MAX_RADIUS_KM = 4


def haversine(lat1, lon1, lat2, lon2):
    R = 6371
    dLat = math.radians(lat2 - lat1)
    dLon = math.radians(lon2 - lon1)

    a = (
        math.sin(dLat / 2) ** 2
        + math.cos(math.radians(lat1))
        * math.cos(math.radians(lat2))
        * math.sin(dLon / 2) ** 2
    )

    return 2 * R * math.atan2(math.sqrt(a), math.sqrt(1 - a))


distance_from_center = haversine(
    lat, lng,
    GACHIBOWLI_CENTER[0],
    GACHIBOWLI_CENTER[1]
)

if distance_from_center > MAX_RADIUS_KM:

    print("ERROR: Location outside Gachibowli boundary")

    output_data = {
        "error": "Selected location outside simulation zone"
    }

    with open("output.json", "w") as f:
        json.dump(output_data, f)

    sys.exit()


# =============================
# LOAD MODEL
# =============================
model = joblib.load("traffic_model.pkl")
feature_columns = joblib.load("model_features.pkl")

print("Downloading road network...")

graph = ox.graph_from_point(center_point, dist=2000, network_type="drive")
edges = ox.graph_to_gdfs(graph, nodes=False)

print("Total edges:", len(edges))


# =============================
# BASELINE TRAFFIC
# =============================
def baseline_traffic(road_type):

    if road_type in ["motorway", "trunk"]:
        return 40
    elif road_type == "primary":
        return 32
    elif road_type == "secondary":
        return 24
    elif road_type == "tertiary":
        return 18
    else:
        return 10


# =============================
# IMPACT
# =============================
def predict_impact(distance):

    decay = max(0.3, 1 - (distance / 1200))
    return visitors * 0.01 * decay


traffic_values = []
total_vehicles = 0


# =============================
# CALCULATE TRAFFIC
# =============================
for _, row in edges.iterrows():

    highway = row["highway"]
    road_type = highway[0] if isinstance(highway, list) else highway

    road_center = row["geometry"].centroid
    road_point = (road_center.y, road_center.x)

    distance = ox.distance.great_circle(
        lat, lng,
        road_point[0],
        road_point[1]
    )

    base = baseline_traffic(road_type)
    impact = predict_impact(distance)

    traffic = base + impact
    traffic = max(5, min(300, traffic))

    vehicles = int(traffic * 0.6)

    total_vehicles += vehicles
    traffic_values.append(traffic)


edges["traffic"] = traffic_values


# =============================
# COLOR
# =============================
def get_color(traffic):

    if traffic < 25:
        return "green"
    elif traffic < 45:
        return "orange"
    else:
        return "red"


# =============================
# DARK MAP (MATCH INPUT MAP)
# =============================
m = folium.Map(
    location=center_point,
    zoom_start=17,
    tiles="OpenStreetMap"
)

# =============================
# DRAW ROADS
# =============================
for _, row in edges.iterrows():

    color = get_color(row["traffic"])

    folium.GeoJson(
        row["geometry"],
        style_function=lambda x, color=color: {
            "color": color,
            "weight": 5,
            "opacity": 0.95
        },
    ).add_to(m)


# =============================
# MARKER
# =============================
folium.Marker(
    location=(lat, lng),
    popup="Selected Location"
).add_to(m)


# =============================
# SAVE MAP
# =============================
map_file = "ml_traffic_prediction.html"
m.save(map_file)


# =============================
# OUTPUT
# =============================
total_vehicles = int(total_vehicles)

output_data = {
    "map_file": map_file,
    "total_vehicles_per_hour": total_vehicles,
    "visitors_per_hour": visitors
}

with open("output.json", "w") as f:
    json.dump(output_data, f)

print("Total vehicles/hr:", total_vehicles)
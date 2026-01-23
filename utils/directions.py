import requests
attractions_ = attractions[:2]
coords_str = ";".join([f"{loc.lon},{loc.lat}" for loc in attractions_])
mapbox_access_token = os.getenv("MAPBOX_TOKEN")
if not mapbox_access_token:
    raise ValueError("MAPBOX_TOKEN not found in .env file.")
url = f"https://api.mapbox.com/directions/v5/mapbox/driving/{coords_str}"
params = {
    "access_token": mapbox_access_token,
    "geometries": "geojson",
    "overview": "full",
    "alternatives": "false"
}
response = requests.get(url, params=params)
data = response.json()

if response.status_code != 200:
    raise Exception(f"Mapbox Error: {data.get('message')}")

dir_cache = {
    (attractions_[0].id, attractions_[1].id): response.json()
}

serializable_cache = {
    f"{k[0]}-{k[1]}": v 
    for k, v in dir_cache.items()
}

import json
filename = "cached_directions.json"
with open(filename, "w", encoding="utf-8") as f:
    json.dump(serializable_cache, f)
    

import os
from supabase import create_client, Client
from pathlib import Path
import json

url: str = os.environ.get("SUPABASE_URL")
key: str = os.environ.get("SUPABASE_KEY")
supabase: Client = create_client(url, key)

def find_json_files(directory_path):
    # Create a Path object
    path = Path(directory_path)
    
    # Use glob to find all files ending in .json
    # Use rglob('*.json') if you want to search subfolders recursively
    json_files = list(path.glob('*.json'))
    
    return json_files

data_folder="./attraction_files/"
files = find_json_files(data_folder)

reformatted_attractions = []
for file in files:
    with open(file, "r", encoding="utf-8") as file:
        attractions = json.load(file)

        for attraction in attractions["data"]:
            if "geo" in attraction:
                a = {
                    "name": attraction["name"],
                    "myswitzerland_id": attraction["identifier"],
                    "photo": attraction.get("photo"),
                    "abstract": attraction.get("abstract"),
                    "url": attraction.get("url"),
                    "lat": attraction["geo"]["latitude"],
                    "lon": attraction["geo"]["longitude"]
                }
                reformatted_attractions.append(a)

supa_response = (
    supabase.table("attractions").insert(reformatted_attractions).execute()
)
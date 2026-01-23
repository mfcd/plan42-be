import json
from pathlib import Path

class LocalDirectionsCache:
    def __init__(self, filename="cached_directions.json"):
        self.filename = filename
        # Load the cache immediately upon initialization
        self.directions = self.load_cache()

    def save_cache(self):
        # Convert tuple keys (101, 202) -> string keys "101-202"
        serializable_cache = {
            f"{k[0]}-{k[1]}": v
            for k, v in self.directions.items()
        }
        with open(self.filename, "w", encoding="utf-8") as f:
            json.dump(serializable_cache, f, indent=4)

    def load_cache(self):
        # Check if the file exists before trying to open it
        path = Path(self.filename)
        if not path.exists():
            print(f"No cache file found at {self.filename}. Starting fresh.")
            return {}

        try:
            with open(self.filename, "r", encoding="utf-8") as f:
                data = json.load(f)        
            # Convert string keys "101-202" back to tuple (101, 202)
            return {
                (int(k.split('-')[0]), int(k.split('-')[1])): v 
                for k, v in data.items()
            }
        
        except (json.JSONDecodeError, ValueError) as e:
            print(f"Error loading cache: {e}. Returning empty cache.")
            return {}

    def get(self, id_a, id_b):
        """Helper to retrieve from state"""
        return self.directions.get((id_a, id_b))

    def add(self, id_a, id_b, data):
        """Helper to add and save"""
        self.directions[(id_a, id_b)] = data
        self.save_cache()
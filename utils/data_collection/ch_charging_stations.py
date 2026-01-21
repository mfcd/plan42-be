import requests
from requests.exceptions import HTTPError, ConnectionError, Timeout, RequestException
import json

url = "https://data.geo.admin.ch/ch.bfe.ladestellen-elektromobilitaet/data/ch.bfe.ladestellen-elektromobilitaet.json"

try:
    response = requests.get(url)
    response.raise_for_status()   # raises error for 4xx/5xx

    data = response.json()        # parsed JSON → dict / list

    with open(f"EVSE.json", "w", encoding="utf-8") as f:
        json.dump(response.json(), f)

except HTTPError as http_err:
    print(f"HTTP error occurred: {http_err}")  # e.g. 404 Not Found
except ConnectionError as conn_err:
    print(f"Connection error occurred: {conn_err}")
except Timeout as timeout_err:
    print(f"Timeout error occurred: {timeout_err}")
except RequestException as req_err:
    print(f"An ambiguous error occurred: {req_err}")


import os
import requests
import csv
import json
from requests.exceptions import HTTPError, ConnectionError, Timeout, RequestException


API_KEY = os.environ.get("MYSWITZERLAND_API_KEY")  # set this in your shell
BASE_URL = "https://opendata.myswitzerland.io/v1/attractions"  # check docs for exact path

HEADERS = {
    "Accept": "application/json",
    "x-api-key": API_KEY  # header name per docs; verify in API reference
}


def output_page_as_file(response_json, page:int = 0):
    with open(f"attractions_{page}.json", "w", encoding="utf-8") as f:
        json.dump(response_json, f)

def fetch_page(page: int = 0):
    hitsPerPage = 50
    params = {
        "hitsPerPage": hitsPerPage,
        "page": page,
    }

    try:
        resp = requests.get(BASE_URL, headers=HEADERS, params=params, timeout=30)
        resp.raise_for_status()
        output_page_as_file(resp.json(), page)
        print
        
    except HTTPError as http_err:
        print(f"HTTP error occurred: {http_err}")  # e.g. 404 Not Found
    except ConnectionError as conn_err:
        print(f"Connection error occurred: {conn_err}")
    except Timeout as timeout_err:
        print(f"Timeout error occurred: {timeout_err}")
    except RequestException as req_err:
        print(f"An ambiguous error occurred: {req_err}") 

for i in range(50):
    fetch_page(i)


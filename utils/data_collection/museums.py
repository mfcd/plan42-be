import os
import requests
import csv


API_KEY = os.environ.get("MYSWITZERLAND_API_KEY")  # set this in your shell
BASE_URL = "https://opendata.myswitzerland.io/v1/attractions"  # check docs for exact path

HEADERS = {
    "Accept": "application/json",
    "x-api-key": API_KEY  # header name per docs; verify in API reference
}

def fetch_page(page: int = 0):
    hitsPerPage = 50

    params = {
        "hitsPerPage": hitsPerPage,
        "page": page,
    }
    
    resp = requests.get(BASE_URL, headers=HEADERS, params=params, timeout=30)
    resp.raise_for_status()
    return resp.json()











def extract_rows(attractions: list):
    """Extract name and lat/lon from the API items."""
    rows = []
    for item in attractions:
        # adapt field names to actual schema from docs
        name = item.get("name")
        geo = item.get("geo") or item.get("location") or {}
        lat = geo.get("latitude")
        lon = geo.get("longitude")

        if name and lat is not None and lon is not None:
            rows.append({
                "name": name,
                "latitude": lat,
                "longitude": lon
            })
    return rows

def main():
    if not API_KEY:
        raise RuntimeError("Set MYSWITZERLAND_API_KEY in your environment.")

    all_rows = []
    offset = 0
    limit = 100

    while True:
        data = fetch_page(offset, limit)
        # adapt to real response structure; often something like data["items"] or data["results"]
        items = data.get("items") or data.get("results") or []

        if not items:
            break

        rows = extract_rows(items)
        all_rows.extend(rows)

        # stopping condition – if fewer than limit items, assume last page
        if len(items) < limit:
            break

        offset += limit

    # write to CSV
    out_file = "swiss_attractions_with_coordinates.csv"
    with open(out_file, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["name", "latitude", "longitude"])
        writer.writeheader()
        writer.writerows(all_rows)

    print(f"Wrote {len(all_rows)} rows to {out_file}")

if __name__ == "__main__":
    main()
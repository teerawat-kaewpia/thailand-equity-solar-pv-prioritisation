# -*- coding: utf-8 -*-
"""
Download Thailand power grid infrastructure (HV lines, substations, towers, plants)
from OpenStreetMap via the public Overpass API.
No API key / account needed - this is a free public service.

Large queries (lines/cables/plants) are split into north/south halves of the
Thailand bbox to avoid 504 Gateway Timeout on the shared public instance,
with longer pauses between requests to avoid 429 Too Many Requests.
"""
import requests, json, time
from pathlib import Path

OUT_DIR = Path(__import__("os").environ.get("ENERGY_DATA_ROOT", r"D:\Clude Code GIS\Energy")) / "Energy map" / "GridNetwork_OSM"
OUT_DIR.mkdir(parents=True, exist_ok=True)

OVERPASS_URL = "https://overpass-api.de/api/interpreter"

# Full Thailand bbox: south,west,north,east = 5.5,97.5,20.5,105.7
# Split at lat 13.0 into south half and north half to shrink each query.
BBOX_SOUTH = "5.5,97.5,13.0,105.7"
BBOX_NORTH = "13.0,97.5,20.5,105.7"
BBOX_FULL = "5.5,97.5,20.5,105.7"

JOBS = [
    ("power_lines_south", f'way["power"="line"]({BBOX_SOUTH});out geom;'),
    ("power_lines_north", f'way["power"="line"]({BBOX_NORTH});out geom;'),
    ("power_cables_south", f'way["power"="cable"]({BBOX_SOUTH});out geom;'),
    ("power_cables_north", f'way["power"="cable"]({BBOX_NORTH});out geom;'),
    ("plants", f'(way["power"="plant"]({BBOX_FULL});node["power"="plant"]({BBOX_FULL}););out geom;'),
]

def fetch(query_body, name, retries=3):
    query = f"[out:json][timeout:300];{query_body}"
    for attempt in range(1, retries + 1):
        print(f"\n[{name}] Querying Overpass API (attempt {attempt}/{retries})...")
        try:
            r = requests.post(
                OVERPASS_URL, data={"data": query}, timeout=400,
                headers={"User-Agent": "DER-Thailand-Research/1.0 (academic, non-commercial)"}
            )
            r.raise_for_status()
            data = r.json()
            out_path = OUT_DIR / f"{name}_raw.json"
            out_path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
            print(f"  Elements: {len(data.get('elements', [])):,}  -> saved {out_path.name}")
            return True
        except Exception as e:
            print(f"  ERROR [{name}] attempt {attempt}: {e}")
            if attempt < retries:
                wait = 60 * attempt
                print(f"  Waiting {wait}s before retry...")
                time.sleep(wait)
    return False

print("="*60)
print("Download Thailand power grid data from OSM (Overpass API)")
print("="*60)

for name, q in JOBS:
    out_path = OUT_DIR / f"{name}_raw.json"
    if out_path.exists():
        print(f"\n[{name}] SKIP - already downloaded")
        continue
    fetch(q, name)
    time.sleep(30)  # longer pause to avoid 429 on the shared public instance

print("\nDone. Next step: run convert_grid_osm_to_geojson.py")

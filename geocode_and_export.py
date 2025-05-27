#!/usr/bin/env python3
import os
import pandas as pd
import json
from geopy.geocoders import Nominatim
from geopy.extra.rate_limiter import RateLimiter

# ─── Configuration ─────────────────────────────────────────────────────────────
INPUT_CSV       = "data/UML May 20.csv"
CACHE_FILE      = "data/geocode_cache.json"
OUTPUT_GEOJSON  = "data/units.geojson"

# ─── Ensure directories exist ──────────────────────────────────────────────────
os.makedirs(os.path.dirname(INPUT_CSV), exist_ok=True)
os.makedirs(os.path.dirname(CACHE_FILE), exist_ok=True)

# ─── Load your CSV ─────────────────────────────────────────────────────────────
df = pd.read_csv(INPUT_CSV, dtype=str)

# Build full_address from your actual column names
df["full_address"] = (
    df["Street Address"].fillna("") + " " +
    df["Street Address2"].fillna("") + ", " +
    df["Street Address City"].fillna("") + ", " +
    df["Street Address State"].fillna("") + " " +
    df["Street Address Zip"].fillna("")
).str.strip()

# ─── Load or initialize cache ──────────────────────────────────────────────────
if os.path.exists(CACHE_FILE):
    cache = json.load(open(CACHE_FILE))
else:
    cache = {}

geolocator = Nominatim(user_agent="corp_locator")
geocode    = RateLimiter(geolocator.geocode, min_delay_seconds=1)

lats, lons = [], []
for addr in df["full_address"]:
    if addr in cache:
        lat, lon = cache[addr]
    else:
        loc = geocode(addr)
        lat, lon = (loc.latitude, loc.longitude) if loc else (None, None)
        cache[addr] = (lat, lon)
    lats.append(lat)
    lons.append(lon)

# ─── Save updated cache ───────────────────────────────────────────────────────
with open(CACHE_FILE, "w") as f:
    json.dump(cache, f, indent=2)

df["latitude"]  = lats
df["longitude"] = lons

# ─── Build & write GeoJSON ────────────────────────────────────────────────────
features = []
for _, row in df.dropna(subset=["latitude","longitude"]).iterrows():
    features.append({
        "type": "Feature",
        "geometry": {
            "type": "Point",
            "coordinates": [row["longitude"], row["latitude"]],
        },
        "properties": {
            "unit_number":  row.get("Unit Number", ""),
            "unit_name":    row.get("Unit Name", ""),
            "company":      row.get("Company Name", ""),
            "opening_date": row.get("Opening Date", ""),
        }
    })

geojson = {"type": "FeatureCollection", "features": features}
with open(OUTPUT_GEOJSON, "w") as f:
    json.dump(geojson, f, indent=2)

print(f"Exported {len(features)} locations to {OUTPUT_GEOJSON}")

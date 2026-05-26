from __future__ import annotations

import re
from pathlib import Path

import pandas as pd
from geopy.geocoders import Nominatim
from geopy.extra.rate_limiter import RateLimiter

ROOT = Path(__file__).resolve().parents[1]

PROCESSED_DIR = ROOT / "HTV-housing_transaction_viewer" / "data" / "processed"

GENERAL_FILE = PROCESSED_DIR / "Generalinformationofschools.csv"
RANKED_FILE = PROCESSED_DIR / "schools_ranked_geocoded.csv"

OUTPUT_FILE = PROCESSED_DIR / "schools_master.csv"


# =========================================================
# Helpers
# =========================================================

def clean_school_name(name: str) -> str:
    if pd.isna(name):
        return ""

    name = str(name).upper().strip()

    replacements = {
        "PRIMARY SCHOOL": "PRI SCH",
        "SECONDARY SCHOOL": "SEC SCH",
        "JUNIOR COLLEGE": "JC",
        "SCHOOL": "SCH",
    }

    for old, new in replacements.items():
        name = name.replace(old, new)

    name = re.sub(r"[^A-Z0-9 ]", "", name)
    name = re.sub(r"\s+", " ", name)

    return name.strip()


def geocode_postal_code(postal_code: str, geocode):
    """
    Singapore postal code geocoding.
    """
    if pd.isna(postal_code):
        return None, None

    postal_code = str(postal_code).strip()

    if not postal_code:
        return None, None

    try:
        query = f"Singapore {postal_code}"

        location = geocode(query)

        if location:
            return location.latitude, location.longitude

    except Exception as e:
        print(f"Geocode failed for {postal_code}: {e}")

    return None, None


# =========================================================
# Load datasets
# =========================================================

general_df = pd.read_csv(GENERAL_FILE, low_memory=False)
ranked_df = pd.read_csv(RANKED_FILE, low_memory=False)

print(f"General schools: {len(general_df)}")
print(f"Ranked schools: {len(ranked_df)}")


# =========================================================
# Normalize names for joining
# =========================================================

general_df["join_name"] = general_df["school_name"].apply(clean_school_name)

ranked_df["join_name"] = ranked_df["name"].apply(clean_school_name)


# =========================================================
# Merge
# =========================================================

merged = general_df.merge(
    ranked_df[
        [
            "join_name",
            "rank",
            "score",
            "gender",
            "ip",
            "ibdp",
            "sap",
            "affiliated",
            "programmes",
            "lat",
            "lon",
        ]
    ],
    on="join_name",
    how="left",
)

print(f"Merged rows: {len(merged)}")


# =========================================================
# Geocode missing coordinates
# =========================================================

missing_before = merged["lat"].isna().sum()

print(f"Missing lat/lon BEFORE geocoding: {missing_before}")

geolocator = Nominatim(user_agent="sg_school_mapper")
geocode = RateLimiter(geolocator.geocode, min_delay_seconds=1)

for idx, row in merged.iterrows():

    lat = row.get("lat")
    lon = row.get("lon")

    if pd.notna(lat) and pd.notna(lon):
        continue

    postal = row.get("postal_code")

    geo_lat, geo_lon = geocode_postal_code(postal, geocode)

    if geo_lat and geo_lon:
        merged.at[idx, "lat"] = geo_lat
        merged.at[idx, "lon"] = geo_lon

        print(
            f"Geocoded: {row.get('school_name')} "
            f"-> {geo_lat}, {geo_lon}"
        )

missing_after = merged["lat"].isna().sum()

print(f"Missing lat/lon AFTER geocoding: {missing_after}")


# =========================================================
# Final cleanup
# =========================================================

merged["lat"] = pd.to_numeric(merged["lat"], errors="coerce")
merged["lon"] = pd.to_numeric(merged["lon"], errors="coerce")

merged = merged.drop_duplicates(subset=["school_name"])


# =========================================================
# Save
# =========================================================

merged.to_csv(OUTPUT_FILE, index=False)

print(f"\nSaved master dataset:")
print(OUTPUT_FILE)
"""
Build fast-read CSV slices under data/processed/ for the Streamlit app and GitHub.

Usage:
  python scripts/build_processed_data.py           # full build (geocodes new keys)
  python scripts/build_processed_data.py --fast    # skip new geocoding (use cache only)
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import time
from pathlib import Path

import pandas as pd
import requests

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from data_sources import load_dataset  # noqa: E402
from rental_model import load_rent_vs_buy_scenario, load_savings_projection  # noqa: E402
from schools import load_schools, programme_tags  # noqa: E402

PROCESSED_DIR = ROOT / "data" / "processed"
CACHE_PATH = PROCESSED_DIR / "geocode_cache.csv"
GEOCODE_DELAY_SEC = 1.05


def ensure_dir():
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)


def load_geocode_cache() -> dict[str, tuple[float, float]]:
    if not CACHE_PATH.exists() or CACHE_PATH.stat().st_size == 0:
        return {}
    df = pd.read_csv(CACHE_PATH)
    if df.empty:
        return {}
    out = {}
    for _, row in df.iterrows():
        if pd.notna(row.get("lat")) and pd.notna(row.get("lon")):
            out[str(row["key"])] = (float(row["lat"]), float(row["lon"]))
    return out


def save_geocode_cache(cache: dict[str, tuple[float, float]]):
    rows = [{"key": k, "lat": v[0], "lon": v[1]} for k, v in sorted(cache.items())]
    pd.DataFrame(rows).to_csv(CACHE_PATH, index=False)


def geocode_query(query: str) -> tuple[float, float] | None:
    url = "https://nominatim.openstreetmap.org/search"
    params = {"q": query, "format": "json", "limit": 1}
    try:
        r = requests.get(url, params=params, headers={"User-Agent": "SG-Housing-Viewer-Build/1.0"}, timeout=25)
        r.raise_for_status()
        data = r.json()
        if data:
            return float(data[0]["lat"]), float(data[0]["lon"])
    except Exception as exc:
        print(f"  geocode fail: {query[:50]}... ({exc})", file=sys.stderr)
    return None


def extract_sg_postal(text: str) -> str | None:
    m = re.search(r"S\((\d{6})\)", str(text))
    return m.group(1) if m else None


def geocode_key(key: str, query: str, cache: dict, fast: bool) -> tuple[float, float] | None:
    if key in cache:
        return cache[key]
    if fast:
        return None
    time.sleep(GEOCODE_DELAY_SEC)
    loc = geocode_query(query)
    if loc:
        cache[key] = loc
    return loc


def build_area_geocodes(cache: dict, fast: bool) -> dict[str, tuple[float, float]]:
    """Geocode unique areas and towns from transactions."""
    print("Building area geocode mapping …")
    frames = [load_dataset("hdb_resale"), load_dataset("private_property")]
    frames = [f for f in frames if not f.empty]
    df = pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()
    if df.empty:
        return {}
    
    # Get unique area names and towns
    unique_areas = pd.concat([df["area_name"], df["town"]]).unique()
    unique_areas = [str(a).strip() for a in unique_areas if pd.notna(a) and str(a).strip()]
    unique_areas = sorted(set(unique_areas))
    
    area_coords = {}
    for area in unique_areas:
        key = f"area:{area}"
        loc = geocode_key(key, f"{area}, Singapore", cache, fast)
        if loc:
            area_coords[area] = loc
        else:
            area_coords[area] = None
    
    print(f"  geocoded {sum(1 for v in area_coords.values() if v)}/{len(area_coords)} areas")
    return area_coords


def build_transactions(area_coords: dict | None = None):
    print("Building transactions_all.csv …")
    frames = [load_dataset("hdb_resale"), load_dataset("private_property")]
    frames = [f for f in frames if not f.empty]
    df = pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()
    if df.empty:
        print("  WARNING: no transaction data")
        return
    
    # Add geocoding if area coordinates are available
    if area_coords:
        df["lat"] = df["area_name"].map(lambda x: area_coords.get(str(x).strip(), (None, None))[0] if pd.notna(x) else None)
        df["lon"] = df["area_name"].map(lambda x: area_coords.get(str(x).strip(), (None, None))[1] if pd.notna(x) else None)
    
    path = PROCESSED_DIR / "transactions_all.csv"
    df.to_csv(path, index=False)
    print(f"  saved {len(df):,} rows")

    print("Building transaction_index.csv …")
    index = (
        df.groupby(["dataset", "town", "street_name", "property_type"], as_index=False)["price"]
        .agg(record_count="count", first_year=("year", "min"), last_year=("year", "max"), median_price="median")
    )
    index = index.sort_values(["town", "street_name", "dataset"])
    index.to_csv(PROCESSED_DIR / "transaction_index.csv", index=False)
    print(f"  saved {len(index):,} index rows")

    print("Building price_medians.csv …")
    recent = df[df["year"] >= df["year"].max() - 5]
    med = (
        recent.groupby(["year", "housing_kind", "size_label", "area_name"], as_index=False)["price"]
        .agg(median_price="median", sales="count")
    )
    med.to_csv(PROCESSED_DIR / "price_medians.csv", index=False)
    print(f"  saved {len(med):,} summary rows")


def build_schools_ranked(cache: dict, fast: bool):
    print("Building schools_ranked.csv …")
    df = load_schools()
    if df.empty:
        return
    df["programmes"] = df.apply(programme_tags, axis=1)
    df.to_csv(PROCESSED_DIR / "schools_ranked.csv", index=False)

    print("Building schools_ranked_geocoded.csv …")
    rows = []
    for _, row in df.iterrows():
        name = row["name"]
        key = f"sec:{name}"
        loc = geocode_key(key, f"{name}, Singapore", cache, fast)
        rows.append({**row.to_dict(), "lat": loc[0] if loc else None, "lon": loc[1] if loc else None})
    out = pd.DataFrame(rows)
    out.to_csv(PROCESSED_DIR / "schools_ranked_geocoded.csv", index=False)
    print(f"  geocoded {out['lat'].notna().sum()}/{len(out)}")


def build_moe_primary(cache: dict, fast: bool):
    print("Building schools_moe_primary.csv …")
    path = ROOT / "data" / "Generalinformationofschools.csv"
    if not path.exists():
        return
    raw = pd.read_csv(path)
    raw = raw[raw["mainlevel_code"].astype(str).str.contains("PRIMARY", case=False, na=False)]
    rows = []
    for _, row in raw.iterrows():
        postal = str(row.get("postal_code", "")).strip()
        key = f"moe:{postal}"
        loc = geocode_key(key, f"Singapore {postal}", cache, fast)
        rows.append(
            {
                "school_name": row.get("school_name"),
                "postal_code": postal,
                "level": row.get("mainlevel_code"),
                "lat": loc[0] if loc else None,
                "lon": loc[1] if loc else None,
            }
        )
    out = pd.DataFrame(rows)
    out.to_csv(PROCESSED_DIR / "schools_moe_primary.csv", index=False)
    print(f"  geocoded {out['lat'].notna().sum()}/{len(out)}")


def build_supermarkets():
    print("Building supermarkets.csv …")
    src = ROOT / "data" / "singapore_all_pois.csv"
    if not src.exists():
        return
    df = pd.read_csv(src)
    df = df[df["category"].astype(str).str.lower() == "supermarket"].copy()
    df = df.rename(columns={"name": "name"})
    df[["name", "brand", "address", "lat", "lon"]].to_csv(PROCESSED_DIR / "supermarkets.csv", index=False)
    print(f"  saved {len(df)}")


def build_hawkers(cache: dict, fast: bool):
    print("Building hawker_centres.csv …")
    src = ROOT / "data" / "ListofGovernmentMarketsHawkerCentres.csv"
    if not src.exists():
        return
    raw = pd.read_csv(src)
    rows = []
    for _, row in raw.iterrows():
        name = row.get("name_of_centre", "")
        addr = row.get("location_of_centre", "")
        key = f"hawker:{name}"
        postal = extract_sg_postal(addr)
        query = f"Singapore {postal}" if postal else f"{addr}, Singapore"
        loc = geocode_key(key, query, cache, fast)
        rows.append(
            {
                "name": name,
                "address": addr,
                "type": row.get("type_of_centre"),
                "lat": loc[0] if loc else None,
                "lon": loc[1] if loc else None,
            }
        )
    out = pd.DataFrame(rows)
    out.to_csv(PROCESSED_DIR / "hawker_centres.csv", index=False)
    print(f"  geocoded {out['lat'].notna().sum()}/{len(out)}")


def build_pharmacies(cache: dict, fast: bool):
    print("Building pharmacies.csv …")
    src = ROOT / "data" / "ListingofLicensedPharmacies.csv"
    if not src.exists():
        return
    raw = pd.read_csv(src).head(80)
    rows = []
    for _, row in raw.iterrows():
        name = row.get("pharmacy_name", "")
        addr = row.get("pharmacy_address", "")
        key = f"pharma:{name}"
        postal = extract_sg_postal(addr)
        query = f"Singapore {postal}" if postal else f"{addr}, Singapore"
        loc = geocode_key(key, query, cache, fast)
        rows.append(
            {
                "name": name,
                "address": addr,
                "lat": loc[0] if loc else None,
                "lon": loc[1] if loc else None,
            }
        )
    out = pd.DataFrame(rows)
    out.to_csv(PROCESSED_DIR / "pharmacies.csv", index=False)
    print(f"  geocoded {out['lat'].notna().sum()}/{len(out)}")


def build_rental_income():
    print("Building rental / savings slices …")
    scenario = load_rent_vs_buy_scenario()
    if scenario:
        meta = {k: v for k, v in scenario.items() if k != "timeline"}
        (PROCESSED_DIR / "rent_vs_buy_meta.json").write_text(json.dumps(meta, indent=2), encoding="utf-8")
        scenario["timeline"].to_csv(PROCESSED_DIR / "rent_vs_buy_timeline.csv", index=False)
        print("  rent_vs_buy saved")
    savings = load_savings_projection()
    if savings is not None and not savings.empty:
        savings.to_csv(PROCESSED_DIR / "savings_projection.csv", index=False)
        print("  savings_projection saved")


def run(fast: bool = False):
    ensure_dir()
    cache = load_geocode_cache()
    print(f"Geocode cache: {len(cache)} entries · fast={fast}")

    area_coords = build_area_geocodes(cache, fast)
    build_transactions(area_coords)
    build_schools_ranked(cache, fast)
    build_moe_primary(cache, fast)
    build_supermarkets()
    build_hawkers(cache, fast)
    build_pharmacies(cache, fast)
    build_rental_income()

    save_geocode_cache(cache)
    print("\nPROCESSED_DATA_COMPLETE: data/processed/")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--fast", action="store_true", help="Use geocode cache only; do not call API")
    args = parser.parse_args()
    run(fast=args.fast)

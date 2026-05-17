import csv
import datetime
import json
import os
import requests
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
LATEST_DIR = ROOT / "data" / "latest"
ARCHIVE_DIR = ROOT / "data" / "archive"

# Data sources configuration
DATA_SOURCES = [
    {
        "name": "hdb_resale",
        "sources": [
            {"type": "data_gov_sg", "collection_id": "189", "query": "hdb resale"},
            {"type": "csv_download", "url": "https://data.gov.sg/datasets/d_8b84c4ee58e3cfc0ece0d773c8ca6abc/downloads/d_8b84c4ee58e3cfc0ece0d773c8ca6abc_DATA.csv"},
        ],
    },
    {
        "name": "private_property",
        "sources": [
            {"type": "data_gov_sg", "dataset_id": "d_7c69c943d5f0d89d6a9a773d2b51f337"},
            {"type": "csv_download", "url": "https://data.gov.sg/datasets/d_7c69c943d5f0d89d6a9a773d2b51f337/downloads/d_7c69c943d5f0d89d6a9a773d2b51f337_DATA.csv"},
        ],
    },
]


def ensure_directories():
    LATEST_DIR.mkdir(parents=True, exist_ok=True)
    ARCHIVE_DIR.mkdir(parents=True, exist_ok=True)


def fetch_from_data_gov_sg(collection_id=None, dataset_id=None):
    """Fetch data from data.gov.sg API or collection."""
    try:
        if collection_id:
            # Search collections
            url = f"https://api-production.data.gov.sg/v2/public/api/collections?q={collection_id}"
            r = requests.get(url, timeout=30, headers={"User-Agent": "SG-Housing-Viewer/1.0"})
            r.raise_for_status()
            data = r.json()
            collections = data.get("data", {}).get("collections", [])
            if collections:
                return pd.DataFrame(collections)
        elif dataset_id:
            # Try to fetch from dataset URL
            url = f"https://data.gov.sg/api/action/package_show?id={dataset_id}"
            r = requests.get(url, timeout=30, headers={"User-Agent": "SG-Housing-Viewer/1.0"})
            if r.status_code == 200:
                return r.json()
    except Exception as exc:
        print(f"Warning: data.gov.sg fetch failed: {exc}", file=sys.stderr)
    return None


def fetch_from_csv_url(url):
    """Download and parse CSV from URL."""
    try:
        r = requests.get(url, timeout=30, headers={"User-Agent": "SG-Housing-Viewer/1.0"})
        r.raise_for_status()
        from io import StringIO
        df = pd.read_csv(StringIO(r.text))
        return df
    except Exception as exc:
        print(f"Warning: CSV download failed from {url}: {exc}", file=sys.stderr)
    return None


def normalize_hdb_resale(df):
    """Normalize HDB resale data to standard format."""
    if df is None or df.empty:
        return df
    df = df.copy()
    
    # Standardize column names
    column_mapping = {
        "resale_price": "price",
        "transacted_price": "price",
        "price": "price",
        "town": "town",
        "planning_area": "town",
        "area": "town",
        "month": "transaction_date",
        "transaction_date": "transaction_date",
        "sale_date": "transaction_date",
        "floor_area_sqm": "size_sqm",
        "area_sqm": "size_sqm",
        "remaining_lease": "lease_remaining",
        "lease": "lease_remaining",
        "flat_type": "property_type",
        "street_name": "street_name",
        "block": "street_name",
    }
    
    for old_name, new_name in column_mapping.items():
        if old_name in df.columns:
            df[new_name] = df[old_name]
    
    # Ensure required columns exist
    if "property_type" not in df.columns:
        df["property_type"] = "HDB Resale"
    if "town" not in df.columns:
        df["town"] = "Unknown"
    if "dataset" not in df.columns:
        df["dataset"] = "HDB Resale"
    
    # Convert types
    df["price"] = pd.to_numeric(df.get("price", 0), errors="coerce")
    df["transaction_date"] = pd.to_datetime(df.get("transaction_date"), errors="coerce")
    df["size_sqm"] = pd.to_numeric(df.get("size_sqm"), errors="coerce")
    
    # Add derived columns
    if "transaction_date" in df.columns:
        df["year"] = df["transaction_date"].dt.year
        df["quarter"] = df["transaction_date"].dt.to_period("Q").astype(str)
    
    # Select and return standard columns
    standard_cols = [
        "dataset",
        "property_type",
        "town",
        "street_name",
        "transaction_date",
        "price",
        "size_sqm",
        "lease_remaining",
        "year",
        "quarter",
    ]
    existing_cols = [col for col in standard_cols if col in df.columns]
    return df[existing_cols].dropna(subset=["price", "town"])


def normalize_private_property(df):
    """Normalize private property data to standard format."""
    if df is None or df.empty:
        return df
    df = df.copy()
    
    # Standardize column names
    column_mapping = {
        "price": "price",
        "transacted_price": "price",
        "resale_price": "price",
        "town": "town",
        "planning_area": "town",
        "location": "town",
        "property_type": "property_type",
        "type_of_area": "property_type",
        "property_category": "property_type",
        "transaction_date": "transaction_date",
        "month": "transaction_date",
        "sale_date": "transaction_date",
        "completion_date": "transaction_date",
        "floor_area_sqm": "size_sqm",
        "area_sqm": "size_sqm",
        "floor_area": "size_sqm",
        "lease_commence_date": "lease_remaining",
        "tenure": "lease_remaining",
        "project_name": "street_name",
    }
    
    for old_name, new_name in column_mapping.items():
        if old_name in df.columns:
            df[new_name] = df[old_name]
    
    # Ensure required columns exist
    if "property_type" not in df.columns:
        df["property_type"] = "Private Property"
    if "town" not in df.columns:
        df["town"] = "Unknown"
    if "dataset" not in df.columns:
        df["dataset"] = "Private Property"
    
    # Convert types
    df["price"] = pd.to_numeric(df.get("price", 0), errors="coerce")
    df["transaction_date"] = pd.to_datetime(df.get("transaction_date"), errors="coerce")
    df["size_sqm"] = pd.to_numeric(df.get("size_sqm"), errors="coerce")
    
    # Add derived columns
    if "transaction_date" in df.columns:
        df["year"] = df["transaction_date"].dt.year
        df["quarter"] = df["transaction_date"].dt.to_period("Q").astype(str)
    
    # Select and return standard columns
    standard_cols = [
        "dataset",
        "property_type",
        "town",
        "street_name",
        "transaction_date",
        "price",
        "size_sqm",
        "lease_remaining",
        "year",
        "quarter",
    ]
    existing_cols = [col for col in standard_cols if col in df.columns]
    return df[existing_cols].dropna(subset=["price", "town"])


def fetch_source(source_config):
    """Fetch from a single source, trying fallbacks."""
    for attempt in source_config["sources"]:
        try:
            if attempt["type"] == "data_gov_sg":
                result = fetch_from_data_gov_sg(
                    collection_id=attempt.get("collection_id"),
                    dataset_id=attempt.get("dataset_id"),
                )
                if result is not None:
                    print(f"SUCCESS: Fetched from data.gov.sg: {attempt}")
                    return result
            elif attempt["type"] == "csv_download":
                result = fetch_from_csv_url(attempt["url"])
                if result is not None and not result.empty:
                    print(f"SUCCESS: Fetched CSV from: {attempt['url']}")
                    return result
        except Exception as exc:
            print(f"ATTEMPT_FAILED: {attempt} error: {exc}", file=sys.stderr)
    return None


def save_csv(name, df, normalizer_func):
    """Save normalized data to CSV."""
    if df is None or df.empty:
        print(f"Warning: No data to save for {name}")
        return
    
    # Normalize data
    normalized = normalizer_func(df)
    if normalized.empty:
        print(f"Warning: Normalized data is empty for {name}")
        return
    
    today = datetime.date.today().isoformat()
    latest_path = LATEST_DIR / f"{name}.csv"
    archive_path = ARCHIVE_DIR / f"{name}_{today}.csv"
    
    normalized.to_csv(latest_path, index=False, quoting=csv.QUOTE_NONNUMERIC)
    normalized.to_csv(archive_path, index=False, quoting=csv.QUOTE_NONNUMERIC)
    print(f"SAVED: {latest_path} ({len(normalized)} rows)")
    print(f"ARCHIVED: {archive_path}")


def run():
    ensure_directories()
    for source_config in DATA_SOURCES:
        print(f"\nFetching {source_config['name']}...")
        raw_data = fetch_source(source_config)
        
        if raw_data is None:
            print(f"FAILED: Could not fetch {source_config['name']} from any source")
            continue
        
        # Convert to DataFrame if needed
        if not isinstance(raw_data, pd.DataFrame):
            if isinstance(raw_data, dict):
                raw_data = pd.DataFrame([raw_data])
            else:
                raw_data = pd.DataFrame(raw_data)
        
        # Choose normalizer based on name
        if "hdb" in source_config["name"].lower():
            save_csv(source_config["name"], raw_data, normalize_hdb_resale)
        else:
            save_csv(source_config["name"], raw_data, normalize_private_property)


if __name__ == "__main__":
    try:
        run()
        print("\nDATA_REFRESH_COMPLETE: All sources processed")
    except Exception as exc:
        print(f"FATAL_ERROR: {exc}", file=sys.stderr)
        sys.exit(1)

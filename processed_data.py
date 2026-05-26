"""
Fast loaders for pre-built CSVs in data/processed/ (commit these to GitHub).

Run: python scripts/build_processed_data.py
"""

from __future__ import annotations

import json
import math
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent
PROCESSED_DIR = ROOT / "data" / "processed"


def _read_csv(name: str) -> pd.DataFrame:
    """Read from parquet first (if available), fall back to CSV."""
    path = PROCESSED_DIR / name
    parquet_path = PROCESSED_DIR / name.replace(".csv", ".parquet")
    
    # Try parquet first
    if parquet_path.exists():
        try:
            return pd.read_parquet(parquet_path, engine="pyarrow")
        except Exception:
            pass  # Fall back to CSV
    
    # Fall back to CSV
    if not path.exists():
        return pd.DataFrame()
    return pd.read_csv(path, low_memory=False)


def haversine_km(lat1: float, lon1: float, lat2: pd.Series, lon2: pd.Series) -> pd.Series:
    import numpy as np

    phi1 = math.radians(lat1)
    phi2 = np.radians(lat2.astype(float))
    dphi = np.radians(lat2.astype(float) - lat1)
    dlam = np.radians(lon2.astype(float) - lon1)
    a = np.sin(dphi / 2) ** 2 + math.cos(phi1) * np.cos(phi2) * np.sin(dlam / 2) ** 2
    return np.round(6371 * 2 * np.arctan2(np.sqrt(a), np.sqrt(1 - a)), 2)


def nearest_places(
    places: pd.DataFrame,
    home_lat: float,
    home_lon: float,
    *,
    top_n: int = 12,
    name_col: str = "name",
) -> pd.DataFrame:
    if places.empty or "lat" not in places.columns or "lon" not in places.columns:
        return pd.DataFrame()
    df = places.dropna(subset=["lat", "lon"]).copy()
    df["distance_km"] = haversine_km(home_lat, home_lon, df["lat"], df["lon"])
    cols = [c for c in [name_col, "distance_km", "rank", "score", "gender", "programmes", "level", "brand", "address", "within_1km"] if c in df.columns or c == name_col]
    if name_col not in df.columns and "school_name" in df.columns:
        name_col = "school_name"
    out_cols = [c for c in [name_col, "distance_km", "rank", "score", "gender", "programmes", "level", "brand", "address"] if c in df.columns]
    return df.sort_values("distance_km").head(top_n)[out_cols]


def load_transactions() -> pd.DataFrame:
    df = _read_csv("transactions_all.csv")
    if df.empty:
        return df
    if "transaction_date" in df.columns:
        df["transaction_date"] = pd.to_datetime(df["transaction_date"], errors="coerce")
    return df


def load_price_medians() -> pd.DataFrame:
    return _read_csv("price_medians.csv")


def load_schools_ranked() -> pd.DataFrame:
    return _read_csv("schools_ranked.csv")


def load_schools_ranked_geocoded() -> pd.DataFrame:
    return _read_csv("schools_ranked_geocoded.csv")

def load_general_information_of_schools() -> pd.DataFrame:
    return _read_csv("Generalinformationofschools.csv")

def load_schools_moe_primary() -> pd.DataFrame:
    return _read_csv("schools_moe_primary.csv")


def load_supermarkets() -> pd.DataFrame:
    return _read_csv("supermarkets.csv")


def load_hawker_centres() -> pd.DataFrame:
    return _read_csv("hawker_centres.csv")


def load_pharmacies() -> pd.DataFrame:
    return _read_csv("pharmacies.csv")

def load_transaction_index() -> pd.DataFrame:
    return _read_csv("transaction_index.csv")

def load_schools_master() -> pd.DataFrame:
    return _read_csv("schools_master.csv")

def load_savings_projection() -> pd.DataFrame:
    return _read_csv("savings_projection.csv")


def load_rent_vs_buy_timeline() -> pd.DataFrame:
    return _read_csv("rent_vs_buy_timeline.csv")


def load_rent_vs_buy_meta() -> dict:
    path = PROCESSED_DIR / "rent_vs_buy_meta.json"
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def ranked_schools_near(home_lat: float, home_lon: float, top_n: int = 20) -> pd.DataFrame:
    df = load_schools_ranked_geocoded()
    if df.empty or df["lat"].isna().all():
        return pd.DataFrame()
    near = nearest_places(df, home_lat, home_lon, top_n=top_n, name_col="name")
    if near.empty:
        return near
    if "name" in near.columns:
        near = near.rename(columns={"name": "school"})
    near["within_1km"] = near["distance_km"].apply(
        lambda d: "Yes — priority band" if d <= 1.0 else ("Within 2 km" if d <= 2.0 else "")
    )
    return near


def moe_primary_near(home_lat: float, home_lon: float, top_n: int = 12) -> pd.DataFrame:
    df = load_schools_moe_primary()
    near = nearest_places(df, home_lat, home_lon, top_n=top_n, name_col="school_name")
    if near.empty:
        return near
    near["within_1km"] = near["distance_km"].apply(
        lambda d: "Yes — higher P1 priority" if d <= 1.0 else ("Within 2 km" if d <= 2.0 else "")
    )
    return near

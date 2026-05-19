"""Amenity search: Find nearby pharmacies, hawker centres, and other POIs."""

from __future__ import annotations

from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent
PHARMACIES_CSV = ROOT / "data" / "ListingofLicensedPharmacies.csv"
HAWKER_CSV = ROOT / "data" / "ListofGovernmentMarketsHawkerCentres.csv"
POIS_CSV = ROOT / "data" / "singapore_all_pois.csv"


def load_pharmacies() -> pd.DataFrame:
    """Load pharmacy data and standardize columns."""
    if not PHARMACIES_CSV.exists():
        return pd.DataFrame()
    
    df = pd.read_csv(PHARMACIES_CSV)
    df.columns = [c.strip().lower() for c in df.columns]
    
    # Standardize location columns if present
    if "location" in df.columns:
        df.rename(columns={"location": "address"}, inplace=True)
    
    return df


def load_hawker_centres() -> pd.DataFrame:
    """Load hawker centre data and standardize columns."""
    if not HAWKER_CSV.exists():
        return pd.DataFrame()
    
    df = pd.read_csv(HAWKER_CSV)
    df.columns = [c.strip().lower() for c in df.columns]
    
    return df


def load_pois() -> pd.DataFrame:
    """Load all POIs and standardize columns."""
    if not POIS_CSV.exists():
        return pd.DataFrame()
    
    df = pd.read_csv(POIS_CSV)
    df.columns = [c.strip().lower() for c in df.columns]
    
    return df


def filter_pois_by_type(pois_df: pd.DataFrame, poi_type: str) -> pd.DataFrame:
    """Filter POIs by type (e.g., 'supermarket', 'mrt_station')."""
    if pois_df.empty or "type" not in pois_df.columns:
        return pd.DataFrame()
    
    return pois_df[pois_df["type"].str.lower() == poi_type.lower()].copy()


def haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Calculate straight-line distance in km between two points."""
    import math
    R = 6371 #km
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lon2 - lon1)
    a = math.sin(delta_phi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda / 2) ** 2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return R * c


def count_amenities_within_radius(
    home_lat: float,
    home_lon: float,
    amenities_df: pd.DataFrame,
    radius_km: float = 1.0,
    lat_col: str = "latitude",
    lon_col: str = "longitude",
) -> int:
    """
    Count amenities within a radius of home location.
    
    Args:
        home_lat: Home latitude
        home_lon: Home longitude
        amenities_df: DataFrame with amenity locations
        radius_km: Search radius in kilometers
        lat_col: Column name for latitude
        lon_col: Column name for longitude
    
    Returns:
        Count of amenities within radius
    """
    if amenities_df.empty or lat_col not in amenities_df.columns or lon_col not in amenities_df.columns:
        return 0
    
    count = 0
    for _, row in amenities_df.iterrows():
        try:
            lat = float(row[lat_col])
            lon = float(row[lon_col])
            dist = haversine_distance(home_lat, home_lon, lat, lon)
            if dist <= radius_km:
                count += 1
        except (ValueError, TypeError):
            continue
    
    return count


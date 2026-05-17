"""Nearby amenities — reads pre-built data/processed/*.csv."""

from __future__ import annotations

import pandas as pd

from processed_data import (
    load_hawker_centres,
    load_pharmacies,
    load_schools_moe_primary,
    load_supermarkets,
    nearest_places,
)

__all__ = [
    "load_supermarkets",
    "load_moe_schools",
    "load_hawker_centres",
    "load_pharmacies",
    "nearest_from_coords",
]


def load_moe_schools() -> pd.DataFrame:
    return load_schools_moe_primary()


def nearest_from_coords(home_lat, home_lon, places, lat_col="lat", lon_col="lon", name_col="name", top_n=8):
    if places.empty:
        return pd.DataFrame()
    return nearest_places(places, home_lat, home_lon, top_n=top_n, name_col=name_col)

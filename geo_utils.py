"""Geocoding and distance helpers."""

from __future__ import annotations

import math

import requests
import streamlit as st


@st.cache_data
def geocode_place(query: str):
    if not query:
        return None
    url = "https://nominatim.openstreetmap.org/search"
    params = {"q": query + ", Singapore", "format": "json", "limit": 1}
    response = requests.get(url, params=params, headers={"User-Agent": "SG-Housing-Viewer/1.0"}, timeout=20)
    response.raise_for_status()
    result = response.json()
    if not result:
        return None
    return float(result[0]["lat"]), float(result[0]["lon"])


@st.cache_data
def geocode_postal(postal_code: str):
    code = str(postal_code).strip()
    if not code or code == "nan":
        return None
    return geocode_place(f"Singapore {code}")


def haversine_distance(lat1, lon1, lat2, lon2):
    rad = math.radians
    dlat = rad(lat2 - lat1)
    dlon = rad(lon2 - lon1)
    a = math.sin(dlat / 2) ** 2 + math.cos(rad(lat1)) * math.cos(rad(lat2)) * math.sin(dlon / 2) ** 2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return 6371 * c


@st.cache_data
def geocode_school(school_name: str):
    loc = geocode_place(school_name)
    if loc:
        return loc
    return geocode_place(f"{school_name} Singapore")


def google_distance(origin: str, destination: str, api_key: str):
    if not origin or not destination or not api_key:
        return None
    url = "https://maps.googleapis.com/maps/api/distancematrix/json"
    params = {"origins": origin, "destinations": destination, "key": api_key, "mode": "transit"}
    response = requests.get(url, params=params, timeout=20)
    response.raise_for_status()
    data = response.json()
    if data.get("status") != "OK":
        return None
    element = data["rows"][0]["elements"][0]
    if element.get("status") != "OK":
        return None
    return {
        "distance_text": element["distance"]["text"],
        "duration_text": element["duration"]["text"],
    }

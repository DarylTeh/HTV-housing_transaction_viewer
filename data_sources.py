"""
Shared housing data loading for the Streamlit app and daily refresh script.

Toggle data source (local Excel workbooks vs live API) by changing DATA_SOURCE_MODE
or setting environment variable HTV_DATA_SOURCE to "local_xlsx" or "live_api".
"""

from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Any

import pandas as pd
import requests

ROOT = Path(__file__).resolve().parent
LATEST_DIR = ROOT / "data" / "latest"

# --- Toggle: swap "local_xlsx" <-> "live_api" when the daily API refresh is ready ---
DATA_SOURCE_MODE = os.environ.get("HTV_DATA_SOURCE", "local_xlsx").strip().lower()
# Use CSV snapshots when "1" or when xlsx files are absent (good for Streamlit Cloud).
PREFER_CSV_CACHE = os.environ.get("HTV_PREFER_CSV", "auto").strip().lower()

LOCAL_XLSX_SOURCES = {
    "hdb_resale": [
        {"path": "data/All_HDB(2012-2026).xlsx", "sheet": "Resaleflatpricesbasedonregistra"},
    ],
    "private_property": [
        {"path": "data/All_URA(2020-2025).xlsx", "sheet": "Sales", "format": "ura_modern"},
        {"path": "data/All_URA(2010-2017).xlsx", "sheet": "Condo", "format": "ura_legacy"},
        {"path": "data/All_URA(2010-2017).xlsx", "sheet": "Landed", "format": "ura_legacy"},
        {"path": "data/All_URA(2010-2017).xlsx", "sheet": "EC", "format": "ura_legacy"},
    ],
}

LOCAL_CSV_PATTERNS = {
    "hdb_resale": ["data/Resale Flat Prices*.csv"],
    "private_property": ["data/CondoResidentialTransaction*.csv", "data/ECResidentialTransaction*.csv"],
}

# Placeholder for future live API sources (data.gov.sg). Add entries here, then set DATA_SOURCE_MODE = "live_api".
LIVE_API_SOURCES = {
    "hdb_resale": [
        # Example: {"type": "csv_download", "url": "https://..."},
    ],
    "private_property": [],
}


def find_column(df: pd.DataFrame, candidates: list[str], default: str | None = None) -> str | None:
    for candidate in candidates:
        if candidate in df.columns:
            return candidate
    return default


def read_local_xlsx(path: str, sheet_name: str) -> pd.DataFrame | None:
    abs_path = ROOT / path
    if not abs_path.exists():
        print(f"Local file not found: {abs_path}", file=sys.stderr)
        return None
    try:
        return pd.read_excel(abs_path, sheet_name=sheet_name, engine="openpyxl")
    except Exception as exc:
        print(f"Warning: local xlsx read failed for {path} [{sheet_name}]: {exc}", file=sys.stderr)
        return None


def fetch_from_csv_url(url: str) -> pd.DataFrame | None:
    try:
        response = requests.get(url, timeout=30, headers={"User-Agent": "SG-Housing-Viewer/1.0"})
        response.raise_for_status()
        from io import StringIO

        return pd.read_csv(StringIO(response.text))
    except Exception as exc:
        print(f"Warning: CSV download failed from {url}: {exc}", file=sys.stderr)
        return None


def _read_parquet_file(path: Path) -> pd.DataFrame:
    """Read a parquet file, with fallback to CSV if parquet doesn't exist."""
    parquet_path = path.with_suffix(".parquet")
    
    # Try parquet first if it exists
    if parquet_path.exists():
        try:
            return pd.read_parquet(parquet_path, engine="pyarrow")
        except Exception as exc:
            print(f"Warning: Parquet read failed for {parquet_path}: {exc}", file=sys.stderr)
            # Fall through to CSV
    
    # Fall back to CSV
    return _read_csv_file(path)


def _read_csv_file(path: Path) -> pd.DataFrame:
    try:
        return pd.read_csv(path, low_memory=False)
    except UnicodeDecodeError:
        try:
            return pd.read_csv(path, encoding="ISO-8859-1", low_memory=False)
        except Exception as exc:
            print(f"Warning: CSV read failed for {path}: {exc}", file=sys.stderr)
            return pd.DataFrame()
    except Exception as exc:
        print(f"Warning: CSV read failed for {path}: {exc}", file=sys.stderr)
        return pd.DataFrame()


def _parse_sale_year(series: pd.Series) -> pd.Series:
    years = pd.to_numeric(series, errors="coerce")
    return years.where(years >= 1900, years + 2000)


def _as_number(series: pd.Series) -> pd.Series:
    return pd.to_numeric(
        series.astype(str).str.replace(r"[,$]", "", regex=True),
        errors="coerce",
    )


def normalize_ura_modern(df: pd.DataFrame) -> pd.DataFrame:
    """URA private sales 2020–2025 (Sales sheet)."""
    if df is None or df.empty:
        return pd.DataFrame()

    out = pd.DataFrame()
    out["street_name"] = df.get("Project Name", df.get("Street Name", "")).astype(str)
    out["price"] = _as_number(df.get("Transacted Price ($)"))
    out["size_sqm"] = _as_number(df.get("Area (SQM)"))
    sqft = _as_number(df.get("Area (SQFT)"))
    out["size_sqm"] = out["size_sqm"].fillna(sqft * 0.092903)

    sale_date = pd.to_datetime(df.get("Sale Date"), format="%b-%y", errors="coerce")
    if sale_date.isna().all() and "Sale Month" in df.columns and "Sale Year" in df.columns:
        years = _parse_sale_year(df["Sale Year"])
        composed = df["Sale Month"].astype(str).str.strip() + "-" + years.astype("Int64").astype(str)
        sale_date = pd.to_datetime(composed, format="%b-%Y", errors="coerce")
    out["transaction_date"] = sale_date

    district = pd.to_numeric(df.get("Postal District"), errors="coerce")
    out["district_num"] = district
    out["town"] = district.apply(lambda d: f"District {int(d)}" if pd.notna(d) else "Unknown")
    out["property_type"] = df.get("Property Type", df.get("Type of Area", "Private")).astype(str)
    out["lease_remaining"] = df.get("Tenure", "")
    out["dataset"] = "Private Property"
    return _finalize_frame(out)


def normalize_ura_legacy(df: pd.DataFrame) -> pd.DataFrame:
    """URA private sales 2010–2017 (Condo / Landed / EC sheets)."""
    if df is None or df.empty:
        return pd.DataFrame()

    out = pd.DataFrame()
    out["street_name"] = df.get("Project Name", df.get("Street Name", "")).astype(str)
    # Values are already in SGD despite the column label suggesting thousands.
    out["price"] = _as_number(df.get("Price ($ '000)"))
    sqft = _as_number(df.get("Area (Sqft)"))
    out["size_sqm"] = sqft * 0.092903
    date_col = "Date of Option Exercised / Sales Agreement Signed"
    out["transaction_date"] = pd.to_datetime(df.get(date_col), errors="coerce")

    district = pd.to_numeric(df.get("Postal District"), errors="coerce")
    out["district_num"] = district
    out["town"] = district.apply(lambda d: f"District {int(d)}" if pd.notna(d) else "Unknown")
    out["property_type"] = df.get("Type", "Private").astype(str)
    out["lease_remaining"] = df.get("Tenure", "")
    out["dataset"] = "Private Property"
    return _finalize_frame(out)


def normalize_hdb_resale(df: pd.DataFrame) -> pd.DataFrame:
    if df is None or df.empty:
        return pd.DataFrame()

    out = pd.DataFrame()
    out["town"] = df.get("town", "Unknown")
    out["street_name"] = df.get("street_name", df.get("block", "")).astype(str)
    out["flat_type"] = df.get("flat_type", "")
    out["property_type"] = out["flat_type"].replace("", "HDB").fillna("HDB")
    out["price"] = _as_number(df.get("resale_price", df.get("price")))
    out["size_sqm"] = _as_number(df.get("floor_area_sqm"))
    out["lease_remaining"] = df.get("remaining_lease", "")
    out["transaction_date"] = pd.to_datetime(df.get("month", df.get("transaction_date")), errors="coerce")
    out["dataset"] = "HDB Resale"
    return _finalize_frame(out)


def _finalize_frame(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df["price"] = pd.to_numeric(df["price"], errors="coerce")
    df["transaction_date"] = pd.to_datetime(df["transaction_date"], errors="coerce")
    df["year"] = df["transaction_date"].dt.year
    df["quarter"] = df["transaction_date"].dt.to_period("Q").astype(str)

    cols = [
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
    existing = [c for c in cols if c in df.columns]
    cleaned = df[existing].dropna(subset=["price"])
    cleaned = cleaned[cleaned["price"] > 0]
    return cleaned


def _normalize_hdb_csv(df: pd.DataFrame) -> pd.DataFrame:
    if df is None or df.empty:
        return pd.DataFrame()

    out = pd.DataFrame()
    out["town"] = df.get("town", "Unknown").astype(str)
    out["street_name"] = df.get("street_name", df.get("block", "")).astype(str)
    out["flat_type"] = df.get("flat_type", "").astype(str)
    out["property_type"] = out["flat_type"].replace("", "HDB").fillna("HDB")
    out["price"] = _as_number(df.get("resale_price", df.get("price")))
    out["size_sqm"] = _as_number(df.get("floor_area_sqm", df.get("size_sqm")))
    out["lease_remaining"] = df.get("remaining_lease", df.get("lease_remaining", ""))
    out["transaction_date"] = pd.to_datetime(df.get("month", df.get("transaction_date")), errors="coerce")
    out["dataset"] = "HDB Resale"
    return _finalize_frame(out)


def _load_local_csv_dataset(name: str) -> pd.DataFrame:
    patterns = LOCAL_CSV_PATTERNS.get(name, [])
    frames: list[pd.DataFrame] = []
    for pattern in patterns:
        for path in ROOT.glob(pattern):
            if not path.exists():
                continue
            raw = _read_parquet_file(path)
            if raw.empty:
                continue
            if name == "hdb_resale":
                normalized = _normalize_hdb_csv(raw)
            elif name == "private_property":
                normalized = normalize_ura_modern(raw)
            else:
                normalized = pd.DataFrame()
            if not normalized.empty:
                frames.append(normalized)
    if frames:
        return pd.concat(frames, ignore_index=True)
    return pd.DataFrame()


def _deduplicate_transactions(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return df
    subset = [c for c in ["transaction_date", "town", "street_name", "price", "size_sqm", "property_type", "dataset"] if c in df.columns]
    if not subset:
        return df
    return df.drop_duplicates(subset=subset)


def _load_local_xlsx_dataset(name: str) -> pd.DataFrame:
    entries = LOCAL_XLSX_SOURCES.get(name, [])
    frames: list[pd.DataFrame] = []
    for entry in entries:
        raw = read_local_xlsx(entry["path"], entry["sheet"])
        if raw is None or raw.empty:
            continue
        fmt = entry.get("format")
        if name == "hdb_resale":
            normalized = normalize_hdb_resale(raw)
        elif fmt == "ura_modern":
            normalized = normalize_ura_modern(raw)
        elif fmt == "ura_legacy":
            normalized = normalize_ura_legacy(raw)
        else:
            normalized = normalize_ura_modern(raw)
        if not normalized.empty:
            frames.append(normalized)
    if frames:
        return pd.concat(frames, ignore_index=True)
    return pd.DataFrame()


def _load_live_api_dataset(name: str) -> pd.DataFrame:
    entries = LIVE_API_SOURCES.get(name, [])
    frames: list[pd.DataFrame] = []
    for entry in entries:
        if entry.get("type") == "csv_download" and entry.get("url"):
            raw = fetch_from_csv_url(entry["url"])
            if raw is not None and not raw.empty:
                if name == "hdb_resale":
                    frames.append(normalize_hdb_resale(raw))
                else:
                    frames.append(normalize_ura_modern(raw))
    if frames:
        return pd.concat(frames, ignore_index=True)
    return pd.DataFrame()


def _xlsx_configured(name: str) -> bool:
    return any((ROOT / entry["path"]).exists() for entry in LOCAL_XLSX_SOURCES.get(name, []))


def _should_use_csv_cache(name: str) -> bool:
    csv_path = LATEST_DIR / f"{name}.csv"
    parquet_path = LATEST_DIR / f"{name}.parquet"
    if not csv_path.exists() and not parquet_path.exists():
        return False
    if PREFER_CSV_CACHE == "1":
        return True
    if PREFER_CSV_CACHE == "0":
        return False
    # auto: cache when xlsx sources are missing (e.g. Streamlit Cloud with committed cache only)
    return not _xlsx_configured(name)


def load_dataset(name: str) -> pd.DataFrame:
    if DATA_SOURCE_MODE == "live_api":
        live = _load_live_api_dataset(name)
        if not live.empty:
            return _enrich(live)
        print(f"Live API returned no data for {name}; falling back to local sources.", file=sys.stderr)

    if _should_use_csv_cache(name):
        # Try parquet first, then CSV
        parquet_path = LATEST_DIR / f"{name}.parquet"
        if parquet_path.exists():
            try:
                df = pd.read_parquet(parquet_path, engine="pyarrow")
                if not df.empty:
                    return _enrich(df)
            except Exception as exc:
                print(f"Warning: Parquet cache read failed for {name}: {exc}", file=sys.stderr)
        
        csv_path = LATEST_DIR / f"{name}.csv"
        try:
            df = pd.read_csv(csv_path, low_memory=False)
            if not df.empty:
                return _enrich(df)
        except Exception as exc:
            print(f"Warning: CSV cache read failed for {name}: {exc}", file=sys.stderr)

    xlsx_df = _load_local_xlsx_dataset(name)
    csv_df = _load_local_csv_dataset(name)
    if not xlsx_df.empty and not csv_df.empty:
        merged = pd.concat([xlsx_df, csv_df], ignore_index=True)
        return _enrich(_deduplicate_transactions(merged))
    if not xlsx_df.empty:
        return _enrich(xlsx_df)
    if not csv_df.empty:
        return _enrich(csv_df)

    return pd.DataFrame()


def _enrich(df: pd.DataFrame) -> pd.DataFrame:
    if df is None or df.empty:
        return pd.DataFrame()
    from housing_constants import enrich_area_labels
    from property_groups import add_property_groups

    return add_property_groups(enrich_area_labels(df))


def load_all_transactions() -> pd.DataFrame:
    """Load and combine HDB resale and private property transactions."""
    hdb = load_dataset("hdb_resale")
    private = load_dataset("private_property")
    frames = [df for df in (hdb, private) if not df.empty]
    if not frames:
        return pd.DataFrame()
    combined = pd.concat(frames, ignore_index=True)
    return _enrich(combined)


def save_latest_csv(name: str, df: pd.DataFrame) -> Path | None:
    if df is None or df.empty:
        return None
    LATEST_DIR.mkdir(parents=True, exist_ok=True)
    path = LATEST_DIR / f"{name}.csv"
    df.to_csv(path, index=False)
    return path

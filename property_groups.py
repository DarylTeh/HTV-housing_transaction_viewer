"""
Simple property labels for first-time buyers: HDB / Condo / Landed + size band (sqft).
"""

from __future__ import annotations

import pandas as pd

SQM_TO_SQFT = 10.764

HOUSING_KINDS = ["HDB", "Condo", "EC", "Landed"]

# Raw URA / HDB types rolled into "Landed"
LANDED_RAW_TYPES = {
    "Terrace House",
    "Terrace",
    "Semi-Detached House",
    "Semi-detached",
    "Detached House",
    "Detached",
    "Strata Terrace",
    "Strata Semi-detached",
    "Strata Detached",
}

HDB_SIZE_LABELS: dict[str, str] = {
    "1 ROOM": "1-room (~330 sqft)",
    "2 ROOM": "2-room (~500–720 sqft)",
    "3 ROOM": "3-room (~530–1,250 sqft)",
    "4 ROOM": "4-room (~750–1,900 sqft)",
    "5 ROOM": "5-room (~1,050–1,800 sqft)",
    "EXECUTIVE": "Executive (~1,350–2,600 sqft)",
    "MULTI-GENERATION": "Multi-generation (~1,400–1,900 sqft)",
}

CONDO_SIZE_BANDS = [
    (0, 55, "Studio / 1-bed (~400–590 sqft)"),
    (55, 85, "2-bed (~590–915 sqft)"),
    (85, 120, "3-bed (~915–1,290 sqft)"),
    (120, 10_000, "4-bed+ (~1,290+ sqft)"),
]

LANDED_SIZE_BANDS = [
    (0, 250, "Terrace (~1,200–2,700 sqft)"),
    (250, 400, "Semi-detached (~2,700–4,300 sqft)"),
    (400, 10_000, "Detached bungalow (~4,300+ sqft)"),
]


def _sqm_band(sqm: float, bands: list[tuple]) -> str:
    if pd.isna(sqm):
        return bands[0][2]
    for lo, hi, label in bands:
        if lo <= sqm < hi:
            return label
    return bands[-1][2]


def housing_kind_for_row(property_type: str, dataset: str) -> str:
    if dataset == "HDB Resale":
        return "HDB"
    pt = str(property_type).strip().lower()
    if "executive condominium" in pt or pt == "ec":
        return "EC"
    if property_type in LANDED_RAW_TYPES:
        return "Landed"
    if any(k in pt for k in ("terrace", "semi-detached", "semi detached", "detached", "bungalow")):
        return "Landed"
    return "Condo"


def size_label_for_row(property_type: str, dataset: str, size_sqm: float) -> str:
    kind = housing_kind_for_row(property_type, dataset)
    if kind == "HDB":
        return HDB_SIZE_LABELS.get(str(property_type).strip(), "HDB flat")
    if kind == "Landed":
        if property_type in ("Semi-Detached House", "Semi-detached", "Strata Semi-detached"):
            return "Semi-detached (~2,700–4,300 sqft)"
        if property_type in ("Detached House", "Detached", "Strata Detached"):
            return "Detached bungalow (~4,300+ sqft)"
        return _sqm_band(size_sqm, LANDED_SIZE_BANDS)
    return _sqm_band(size_sqm, CONDO_SIZE_BANDS)


def add_property_groups(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return df
    out = df.copy()
    out["housing_kind"] = [
        housing_kind_for_row(pt, ds) for pt, ds in zip(out["property_type"], out["dataset"])
    ]
    out["size_label"] = [
        size_label_for_row(pt, ds, sqm)
        for pt, ds, sqm in zip(out["property_type"], out["dataset"], out.get("size_sqm", pd.Series([None] * len(out))))
    ]
    return out


def size_options_for_kinds(df: pd.DataFrame, kinds: list[str]) -> list[str]:
    if not kinds:
        kinds = HOUSING_KINDS
    subset = df[df["housing_kind"].isin(kinds)]
    order_hdb = list(HDB_SIZE_LABELS.values())
    order_condo = [b[2] for b in CONDO_SIZE_BANDS]
    order_landed = [b[2] for b in LANDED_SIZE_BANDS]
    preferred = order_hdb + order_condo + order_landed
    present = subset["size_label"].dropna().unique().tolist()
    return [label for label in preferred if label in present] + sorted(set(present) - set(preferred))


def default_sizes_for_kinds(df: pd.DataFrame, kinds: list[str]) -> list[str]:
    """Sensible defaults: common flat types for HDB, 3-bed for condo."""
    options = size_options_for_kinds(df, kinds)
    picks = []
    for label in ["3-room (~530–1,250 sqft)", "4-room (~750–1,900 sqft)", "3-bed (~915–1,290 sqft)"]:
        if label in options:
            picks.append(label)
    return picks or options[: min(3, len(options))]

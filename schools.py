"""School list — prefers data/processed/schools_ranked.csv."""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from processed_data import load_schools_ranked

ROOT = Path(__file__).resolve().parent
SCHOOL_CSV = ROOT / "data" / "school_list.csv"


def load_schools() -> pd.DataFrame:
    processed = load_schools_ranked()
    if not processed.empty:
        return processed
    if not SCHOOL_CSV.exists():
        return pd.DataFrame()
    df = pd.read_csv(SCHOOL_CSV)
    df = df.loc[:, ~df.columns.str.match(r"^Unnamed")].copy()
    df.columns = [c.strip().lower() for c in df.columns]
    df["name"] = df["name"].astype(str).str.strip()
    df = df[df["name"].ne("") & df["name"].ne("nan")].reset_index(drop=True)
    df.insert(0, "rank", range(1, len(df) + 1))
    df["score"] = pd.to_numeric(df["score"], errors="coerce")
    return df


def programme_tags(row: pd.Series) -> str:
    tags = []
    for col, label in (("ip", "IP"), ("ibdp", "IB"), ("sap", "SAP"), ("affiliated", "Affiliated")):
        val = row.get(col)
        if pd.notna(val) and str(val).strip():
            tags.append(label)
    return ", ".join(tags) if tags else "—"

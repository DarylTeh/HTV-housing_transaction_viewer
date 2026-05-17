"""Rent vs buy — prefers data/processed/ slices from RentalIncome.xlsx."""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from processed_data import load_rent_vs_buy_meta, load_rent_vs_buy_timeline, load_savings_projection as load_savings_csv

ROOT = Path(__file__).resolve().parent
RENTAL_XLSX = ROOT / "data" / "RentalIncome.xlsx"


def load_rent_vs_buy_scenario() -> dict | None:
    meta = load_rent_vs_buy_meta()
    timeline = load_rent_vs_buy_timeline()
    if meta and not timeline.empty:
        first = timeline.iloc[0]
        return {
            **meta,
            "starting_monthly_rent": float(first.get("monthly_rent", 0)),
            "starting_monthly_instalment": float(first.get("monthly_instalment", 0)),
            "timeline": timeline,
        }

    if not RENTAL_XLSX.exists():
        return None
    try:
        raw = pd.read_excel(RENTAL_XLSX, sheet_name="Rental", engine="openpyxl", header=None)
        meta_xl = pd.read_excel(RENTAL_XLSX, sheet_name="HomeLoan", engine="openpyxl", header=None)
        timeline = pd.read_excel(RENTAL_XLSX, sheet_name="Rental", engine="openpyxl", header=10)
    except Exception:
        return None

    purchase_price = 1_500_000.0
    try:
        price_cell = raw.iloc[5, 2]
        if pd.notna(price_cell) and float(price_cell) > 100_000:
            purchase_price = float(price_cell)
    except (ValueError, TypeError, IndexError):
        pass

    loan_amount, interest_rate, tenure_years = 900_000.0, 0.025, 30
    try:
        loan_amount = float(meta_xl.iloc[0, 1])
        interest_rate = float(meta_xl.iloc[1, 1])
        tenure_years = int(float(meta_xl.iloc[2, 1]))
    except (ValueError, TypeError, IndexError):
        pass

    timeline = timeline.dropna(subset=["Year"]).copy()
    timeline["year"] = timeline["Year"].astype(int)
    timeline["monthly_rent"] = pd.to_numeric(timeline["Rent-M"], errors="coerce")
    timeline["monthly_instalment"] = pd.to_numeric(timeline["Instal-M"], errors="coerce")
    timeline["property_value"] = pd.to_numeric(timeline["Price"], errors="coerce")
    first = timeline.iloc[0]
    return {
        "property_label": "Condo (worked example from RentalIncome.xlsx)",
        "purchase_price": purchase_price,
        "loan_amount": loan_amount,
        "interest_rate": interest_rate,
        "tenure_years": tenure_years,
        "starting_monthly_rent": float(first["monthly_rent"]),
        "starting_monthly_instalment": float(first["monthly_instalment"]),
        "timeline": timeline[["year", "monthly_rent", "monthly_instalment", "property_value"]],
    }


def load_savings_projection() -> pd.DataFrame | None:
    df = load_savings_csv()
    if not df.empty:
        return df
    if not RENTAL_XLSX.exists():
        return None
    try:
        df = pd.read_excel(RENTAL_XLSX, sheet_name="Savings", engine="openpyxl", header=1)
        df = df.rename(
            columns={
                "Yr": "year",
                "Age": "age",
                "Start": "start_balance",
                "Mthly": "monthly_save",
                "End": "end_balance",
            }
        )
        keep = [c for c in ["year", "age", "start_balance", "monthly_save", "end_balance"] if c in df.columns]
        df = df.dropna(subset=["year"]).copy()
        for col in keep:
            df[col] = pd.to_numeric(df[col], errors="coerce")
        return df[keep]
    except Exception:
        return None

"""Load rent-vs-buy scenario from RentalIncome.xlsx (educational workbook)."""

from __future__ import annotations

from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent
RENTAL_XLSX = ROOT / "data" / "RentalIncome.xlsx"


def load_rent_vs_buy_scenario() -> dict | None:
    """
    Parse the 'Rental' sheet: a worked condo example ($1.5M) comparing monthly rent vs mortgage.
    Returns None if the file is missing or unreadable.
    """
    if not RENTAL_XLSX.exists():
        return None
    try:
        raw = pd.read_excel(RENTAL_XLSX, sheet_name="Rental", engine="openpyxl", header=None)
        meta = pd.read_excel(RENTAL_XLSX, sheet_name="HomeLoan", engine="openpyxl", header=None)
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

    loan_amount = 900_000.0
    interest_rate = 0.025
    tenure_years = 30
    try:
        loan_amount = float(meta.iloc[0, 1])
        interest_rate = float(meta.iloc[1, 1])
        tenure_years = int(float(meta.iloc[2, 1]))
    except (ValueError, TypeError, IndexError):
        pass

    cols = {c: c for c in timeline.columns}
    year_col = cols.get("Year", "Year")
    rent_col = cols.get("Rent-M", "Rent-M")
    instal_col = cols.get("Instal-M", "Instal-M")
    price_col = cols.get("Price", "Price")

    timeline = timeline.dropna(subset=[year_col]).copy()
    timeline["year"] = timeline[year_col].astype(int)
    timeline["monthly_rent"] = pd.to_numeric(timeline[rent_col], errors="coerce")
    timeline["monthly_instalment"] = pd.to_numeric(timeline[instal_col], errors="coerce")
    timeline["property_value"] = pd.to_numeric(timeline[price_col], errors="coerce")

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

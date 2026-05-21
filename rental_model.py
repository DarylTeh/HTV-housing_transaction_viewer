"""Load rent-vs-buy scenario from RentalIncome.xlsx (educational workbook)."""

from __future__ import annotations

from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent
RENTAL_XLSX = ROOT / "data" / "RentalIncome.xlsx"
RENTAL_CSV = ROOT / "data" / "RentalIncome.csv"


def _load_rental_csv() -> pd.DataFrame | None:
    if not RENTAL_CSV.exists():
        return None
    try:
        raw = pd.read_csv(RENTAL_CSV, header=None)
    except Exception:
        return None
    if raw.empty:
        return None
    if str(raw.iat[0, 0]).strip().lower() in {"yr", "year"}:
        raw.columns = raw.iloc[0].astype(str).tolist()
        raw = raw.iloc[1:].reset_index(drop=True)
    return raw


def load_rent_vs_buy_scenario() -> dict | None:
    """
    Parse the 'Rental' sheet: a worked condo example ($1.5M) comparing monthly rent vs mortgage.
    Returns None if the file is missing or unreadable.
    """
    raw = None
    meta = None
    timeline = None
    if RENTAL_XLSX.exists():
        try:
            raw = pd.read_excel(RENTAL_XLSX, sheet_name="Rental", engine="openpyxl", header=None)
            meta = pd.read_excel(RENTAL_XLSX, sheet_name="HomeLoan", engine="openpyxl", header=None)
            timeline = pd.read_excel(RENTAL_XLSX, sheet_name="Rental", engine="openpyxl", header=10)
        except Exception:
            raw = None
            meta = None
            timeline = None

    if (timeline is None or timeline.empty) and RENTAL_CSV.exists():
        timeline = _load_rental_csv()

    if timeline is None or timeline.empty:
        return None

    purchase_price = 1_500_000.0
    if raw is not None:
        try:
            price_cell = raw.iloc[5, 2]
            if pd.notna(price_cell) and float(price_cell) > 100_000:
                purchase_price = float(price_cell)
        except (ValueError, TypeError, IndexError):
            pass

    loan_amount = 900_000.0
    interest_rate = 0.025
    tenure_years = 30
    if meta is not None:
        try:
            loan_amount = float(meta.iloc[0, 1])
            interest_rate = float(meta.iloc[1, 1])
            tenure_years = int(float(meta.iloc[2, 1]))
        except (ValueError, TypeError, IndexError):
            pass

    def _find_column(candidates: list[str]) -> str | None:
        for candidate in candidates:
            if candidate in timeline.columns:
                return candidate
        return None

    year_col = _find_column(["Year", "Yr"])
    rent_col = _find_column(["Rent-M", "Mthly", "Rent"])
    instal_col = _find_column(["Instal-M", "Instal", "Mthly"])
    price_col = _find_column(["Price", "End", "property_value"])

    if year_col is None or rent_col is None or instal_col is None or price_col is None:
        return None

    timeline = timeline.dropna(subset=[year_col]).copy()
    timeline["year"] = timeline[year_col].astype(int)
    timeline["monthly_rent"] = pd.to_numeric(timeline[rent_col], errors="coerce")
    timeline["monthly_instalment"] = pd.to_numeric(timeline[instal_col], errors="coerce")
    timeline["property_value"] = pd.to_numeric(timeline[price_col], errors="coerce")

    first = timeline.iloc[0]
    scenario = {
        "property_label": "Condo (worked example from RentalIncome.xlsx)",
        "purchase_price": purchase_price,
        "loan_amount": loan_amount,
        "interest_rate": interest_rate,
        "tenure_years": tenure_years,
        "starting_monthly_rent": float(first["monthly_rent"]),
        "starting_monthly_instalment": float(first["monthly_instalment"]),
        "timeline": timeline[["year", "monthly_rent", "monthly_instalment", "property_value"]],
    }
    return scenario


def load_savings_projection() -> pd.DataFrame | None:
    scenario = load_rent_vs_buy_scenario()
    if not scenario:
        return None
    return scenario["timeline"].copy()

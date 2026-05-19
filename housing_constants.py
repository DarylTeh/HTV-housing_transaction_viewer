"""Singapore housing reference data: districts, ABSD, glossary."""

from __future__ import annotations

# Postal district number -> (friendly area name, market region label)
DISTRICT_INFO: dict[int, tuple[str, str]] = {
    1: ("Raffles Place / Marina Bay", "Core Central (CCR)"),
    2: ("Chinatown / Tanjong Pagar", "Core Central (CCR)"),
    3: ("Queenstown / Tiong Bahru", "Rest of Central (RCR)"),
    4: ("Telok Blangah / Harbourfront", "Rest of Central (RCR)"),
    5: ("Clementi / Pasir Panjang", "Rest of Central (RCR)"),
    6: ("Beach Road / High Street", "Rest of Central (RCR)"),
    7: ("Bugis / Rochor", "Rest of Central (RCR)"),
    8: ("Little India / Farrer Park", "Rest of Central (RCR)"),
    9: ("Orchard / River Valley", "Core Central (CCR)"),
    10: ("Tanglin / Bukit Timah", "Core Central (CCR)"),
    11: ("Novena / Thomson", "Core Central (CCR)"),
    12: ("Balestier / Toa Payoh", "Outside Central (OCR)"),
    13: ("MacPherson / Potong Pasir", "Outside Central (OCR)"),
    14: ("Geylang / Paya Lebar", "Outside Central (OCR)"),
    15: ("Marine Parade / Katong", "Rest of Central (RCR)"),
    16: ("Bedok / Upper East Coast", "Outside Central (OCR)"),
    17: ("Loyang / Changi", "Outside Central (OCR)"),
    18: ("Tampines / Pasir Ris", "Outside Central (OCR)"),
    19: ("Hougang / Punggol", "Outside Central (OCR)"),
    20: ("Bishan / Ang Mo Kio", "Outside Central (OCR)"),
    21: ("Upper Bukit Timah / Clementi Park", "Outside Central (OCR)"),
    22: ("Jurong / Boon Lay", "Outside Central (OCR)"),
    23: ("Bukit Panjang / Choa Chu Kang", "Outside Central (OCR)"),
    24: ("Lim Chu Kang / Tengah", "Outside Central (OCR)"),
    25: ("Woodlands / Admiralty", "Outside Central (OCR)"),
    26: ("Upper Thomson / Springleaf", "Outside Central (OCR)"),
    27: ("Yishun / Sembawang", "Outside Central (OCR)"),
    28: ("Seletar / Yio Chu Kang", "Outside Central (OCR)"),
}

# ABSD rate on purchase price (simplified; verify with IRAS before transacting)
ABSD_RATES: dict[str, dict[str, float]] = {
    "Singapore Citizen": {"1st": 0.0, "2nd": 0.20, "3rd+": 0.30},
    "Permanent Resident": {"1st": 0.05, "2nd": 0.30, "3rd+": 0.35},
    "Foreigner": {"1st": 0.60, "2nd": 0.60, "3rd+": 0.60},
}

GLOSSARY: dict[str, str] = {
    "HDB": "Housing & Development Board flats — subsidised public housing for eligible Singapore households.",
    "BTO": "Build-To-Order — new HDB flats sold before they are built, usually with grants for eligible buyers.",
    "Resale flat": "An existing HDB flat sold on the open market by the current owner.",
    "MSR": "Mortgage Servicing Ratio — HDB loans typically cap monthly repayments at 30% of gross income.",
    "TDSR": "Total Debt Servicing Ratio — banks cap total monthly debt at 55% of gross income for property loans.",
    "ABSD": "Additional Buyer's Stamp Duty — extra tax on property purchases depending on residency and how many homes you own.",
    "EC": "Executive Condominium — hybrid housing with HDB-like eligibility at launch, privatises after ~10 years.",
    "CCR / RCR / OCR": "Core Central, Rest of Central, Outside Central — URA market segments for private property.",
    "Leasehold": "You own the home for a fixed period (e.g. 99 years); value may fall as the lease runs down.",
    "Freehold": "Ownership without a fixed lease expiry (still subject to government rules and redevelopment).",
}


def parse_district_number(town: str) -> int | None:
    if not isinstance(town, str) or not town.startswith("District "):
        return None
    try:
        return int(town.replace("District ", "").strip())
    except ValueError:
        return None


def enrich_area_labels(df):
    """Add area_name and region columns; keep town as the filter key."""
    import pandas as pd

    out = df.copy()
    if "town" not in out.columns:
        out["area_name"] = out.get("town", "Unknown")
        out["region"] = ""
        return out

    def labels(town):
        num = parse_district_number(str(town))
        if num and num in DISTRICT_INFO:
            name, region = DISTRICT_INFO[num]
            return pd.Series([f"D{num} — {name}", region])
        return pd.Series([town, "HDB town" if out.loc[out["town"] == town, "dataset"].iloc[0] == "HDB Resale" else ""])

    # Vectorised apply per row is slow; map unique towns instead
    unique = out["town"].unique()
    mapping = {}
    for town in unique:
        num = parse_district_number(str(town))
        if num and num in DISTRICT_INFO:
            name, region = DISTRICT_INFO[num]
            mapping[town] = (f"D{num} — {name}", region)
        elif str(town) != "Unknown":
            mapping[town] = (str(town), "HDB town")
        else:
            mapping[town] = ("Unknown", "")

    out["area_name"] = out["town"].map(lambda t: mapping.get(t, (t, ""))[0])
    out["region"] = out["town"].map(lambda t: mapping.get(t, ("", ""))[1])
    return out


def absd_rate(residency: str, property_count_tier: str) -> float:
    tier_key = property_count_tier if property_count_tier in ("1st", "2nd") else "3rd+"
    return ABSD_RATES.get(residency, ABSD_RATES["Foreigner"]).get(tier_key, 0.60)


def calculate_absd(property_price: float, residency: str, property_count_tier: str) -> dict:
    rate = absd_rate(residency, property_count_tier)
    amount = property_price * rate
    return {"rate": rate, "amount": amount, "tier": property_count_tier}

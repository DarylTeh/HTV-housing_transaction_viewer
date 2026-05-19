from __future__ import annotations
from rules.absd_rules import absd_rate, highest_absd_rate


def determine_absd_tier(existing_property_count: int, keep_existing: bool, sell_within_6_months: bool) -> str:
    if keep_existing:
        next_count = existing_property_count + 1
    elif sell_within_6_months:
        next_count = max(existing_property_count, 0)
    else:
        next_count = existing_property_count + 1
    if next_count <= 1:
        return "1st"
    if next_count == 2:
        return "2nd"
    return "3rd+"


def calculate_absd(
    purchase_price: float,
    buyers: list[dict],
    keep_existing: bool,
    sell_within_6_months: bool,
) -> dict[str, float | str | list[str]]:
    owner_citizenships = [buyer.get("citizenship", "SC") for buyer in buyers if buyer.get("will_be_owner", True)]
    if not owner_citizenships:
        return {"rate": 0.0, "amount": 0.0, "tier": "1st", "notes": ["No selected owners for ABSD calculation."]}

    tier = determine_absd_tier(
        existing_property_count=max(buyer.get("existing_property_count", 0) for buyer in buyers),
        keep_existing=keep_existing,
        sell_within_6_months=sell_within_6_months,
    )
    rate = highest_absd_rate(owner_citizenships, tier)
    notes = []
    if sell_within_6_months and any(buyer.get("existing_property_count", 0) > 0 for buyer in buyers):
        notes.append("ABSD exposure may be refunded if existing property is sold within 6 months.")
    if any(cit == "Foreigner" for cit in owner_citizenships):
        notes.append("Foreign owner triggers the highest applicable ABSD rate.")
    return {"rate": rate, "amount": purchase_price * rate, "tier": tier, "notes": notes}

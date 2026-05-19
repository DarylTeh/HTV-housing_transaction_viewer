from __future__ import annotations

ABSD_RULES: dict[str, dict[str, float]] = {
    "SC": {"1st": 0.0, "2nd": 0.20, "3rd+": 0.30},
    "PR": {"1st": 0.05, "2nd": 0.30, "3rd+": 0.35},
    "Foreigner": {"1st": 0.60, "2nd": 0.60, "3rd+": 0.60},
}

SUPPORTED_CITIZENSHIPS = ["SC", "PR", "Foreigner"]
DEFAULT_ABSD_TIER = "1st"


def absd_rate(citizenship: str, property_count_tier: str) -> float:
    tier_key = property_count_tier if property_count_tier in ("1st", "2nd") else "3rd+"
    return ABSD_RULES.get(citizenship, ABSD_RULES["Foreigner"]).get(tier_key, 0.60)


def highest_absd_rate(citizenships: list[str], property_count_tier: str) -> float:
    return max(absd_rate(cit, property_count_tier) for cit in citizenships)

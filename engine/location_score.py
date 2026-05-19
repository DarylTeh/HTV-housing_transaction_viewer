from __future__ import annotations


def compute_location_score(scores: dict[str, float]) -> dict[str, float]:
    weights = {
        "transport": 1.2,
        "schools": 1.3,
        "food": 1.0,
        "shopping": 1.0,
        "nature": 0.9,
        "family_friendliness": 1.2,
    }
    total = 0.0
    weighted = {}
    for category, value in scores.items():
        weight = weights.get(category, 1.0)
        weighted_value = min(max(value, 0.0), 100.0) * weight
        weighted[category] = round(weighted_value, 1)
        total += weighted_value
    overall = round(total / sum(weights.values()), 1) if weights else 0.0
    weighted["overall"] = overall
    return weighted

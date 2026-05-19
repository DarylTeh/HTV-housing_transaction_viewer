from __future__ import annotations
import math
from rules.loan_rules import PROPERTY_RULES, AGE_LIMITS


def effective_age(buyers: list[dict], method: str) -> float:
    ages = [buyer.get("age", 0) for buyer in buyers if buyer.get("will_be_owner", True)]
    if not ages:
        return 0.0
    if method == "youngest":
        return float(min(ages))
    if method == "oldest":
        return float(max(ages))
    if method == "weighted_average":
        weights = [buyer.get("ownership_percentage", 0.0) for buyer in buyers if buyer.get("will_be_owner", True)]
        total_weight = sum(weights) or len(ages)
        return float(sum(age * (weight / total_weight if total_weight else 1.0 / len(ages)) for age, weight in zip(ages, weights)))
    return float(sum(ages) / len(ages))


def max_tenure(property_type: str, borrower_age: float, age_mode: str) -> int:
    rule = PROPERTY_RULES.get(property_type, PROPERTY_RULES["Condo"])
    cap = rule.get("max_tenure", 30)
    age_limit = AGE_LIMITS.get(age_mode, AGE_LIMITS["strict"])
    if borrower_age + cap <= age_limit:
        return int(cap)
    tenure = int(max(age_limit - borrower_age, 5))
    return max(tenure, 5)


def monthly_payment(principal: float, annual_rate: float, years: int) -> float:
    if principal <= 0 or years <= 0:
        return 0.0
    monthly_rate = annual_rate / 12.0
    periods = years * 12
    if monthly_rate <= 0:
        return principal / periods
    return principal * monthly_rate / (1 - (1 + monthly_rate) ** -periods)


def max_principal_from_monthly(monthly_capacity: float, annual_rate: float, years: int) -> float:
    if monthly_capacity <= 0 or years <= 0:
        return 0.0
    monthly_rate = annual_rate / 12.0
    periods = years * 12
    if monthly_rate <= 0:
        return monthly_capacity * periods
    return monthly_capacity * (1 - (1 + monthly_rate) ** -periods) / monthly_rate


def property_rules(property_type: str) -> dict[str, float | bool]:
    return PROPERTY_RULES.get(property_type, PROPERTY_RULES["Condo"])

from __future__ import annotations
from dataclasses import dataclass
from typing import Any

from engine.loan import effective_age, max_tenure, monthly_payment, max_principal_from_monthly, property_rules
from engine.absd import calculate_absd
from engine.cpf import calculate_cpf_usage
from engine.recommendation import generate_recommendations
from rules.hdb_rules import validate_hdb_eligibility, is_hdb_property


@dataclass
class AffordabilityResult:
    purchase_price: float
    max_affordable_price: float
    recommended_budget: float
    loan_amount: float
    monthly_installment: float
    absd_amount: float
    absd_rate: float
    bsd_amount: float
    cash_required: float
    cash_top_up: float
    cpf_used: float
    cpf_pledged: float
    cpf_shortfall: float
    remaining_cash_buffer: float
    cash_buffer_months: float
    loan_tenure_years: int
    age_warning: str | None
    hdb_eligibility_passed: bool
    hdb_eligibility_reasons: list[str]
    warnings: list[str]
    recommendations: list[str]
    summary: dict[str, Any]
    property_type: str


def calculate_bsd(price: float) -> float:
    brackets = [180_000.0, 180_000.0, 640_000.0, 960_000.0, 1_480_000.0]
    rates = [0.01, 0.02, 0.03, 0.04, 0.05, 0.06]
    remaining = price
    total = 0.0
    for amount, rate in zip(brackets, rates):
        portion = min(remaining, amount)
        total += portion * rate
        remaining -= portion
        if remaining <= 0:
            return total
    total += remaining * rates[-1]
    return total


def affordability_score(results: dict[str, Any]) -> float:
    score = 100.0
    dsr_ratio = results.get("service_ratio", 0.0)
    cash_buffer_months = results.get("cash_buffer_months", 0.0)
    if dsr_ratio > 0.55:
        score -= 30
    elif dsr_ratio > 0.45:
        score -= 15
    if cash_buffer_months < 6:
        score -= 20
    if results.get("age_warning"):
        score -= 10
    if results.get("cpf_shortfall", 0) > 0:
        score -= 10
    return max(0.0, min(100.0, score))


def calculate_affordability(
    buyers: list[dict],
    property_type: str,
    purchase_price: float,
    interest_rate: float,
    age_mode: str,
    age_method: str,
    keep_existing_property: bool,
    sell_existing_within_6_months: bool,
    available_cash: float,
    emergency_reserve: float,
    pledge_cpf: bool,
    request_pledge_amount: float,
) -> AffordabilityResult:
    rule = property_rules(property_type)
    gross_monthly_income = sum(buyer.get("monthly_income", 0.0) + buyer.get("annual_bonus", 0.0) / 12.0 for buyer in buyers if buyer.get("will_be_owner", True))
    total_monthly_debt = sum(buyer.get("other_monthly_debt", 0.0) + buyer.get("existing_home_loan", 0.0) for buyer in buyers if buyer.get("will_be_owner", True))
    effective_borrower_age = effective_age(buyers, age_method)
    tenure_years = max_tenure(property_type, effective_borrower_age, age_mode)
    monthly_service_capacity = gross_monthly_income * rule.get("tdsr", 0.55) - total_monthly_debt
    if is_hdb_property(property_type):
        monthly_service_capacity = min(monthly_service_capacity, gross_monthly_income * rule.get("msr", 0.30))
    loan_capacity = max_principal_from_monthly(max(0.0, monthly_service_capacity), interest_rate, tenure_years)
    max_price_by_loan = loan_capacity / rule.get("ltv", 0.75) if rule.get("ltv", 0.75) > 0 else 0.0
    cpf_info = calculate_cpf_usage(buyers, purchase_price, property_type, pledge_cpf, request_pledge_amount, available_cash)
    absd_info = calculate_absd(purchase_price, buyers, keep_existing_property, sell_existing_within_6_months)
    downpayment_required = purchase_price * rule.get("downpayment_pct", 0.25)
    min_cash_required = purchase_price * rule.get("min_cash_pct", 0.05)
    max_price_by_cash = 0.0
    if downpayment_required > 0:
        max_price_by_cash = (available_cash + cpf_info["cpf_available"]) / rule.get("downpayment_pct", 0.25)
    else:
        max_price_by_cash = purchase_price
    max_price_by_cash = min(max_price_by_cash, purchase_price if purchase_price > 0 else max_price_by_loan)
    max_affordable_price = min(max_price_by_loan, max_price_by_cash)
    target_price = min(purchase_price, max_affordable_price)
    loan_amount = target_price * rule.get("ltv", 0.75)
    monthly_installment = monthly_payment(loan_amount, interest_rate, tenure_years)
    cash_needed = max(0.0, downpayment_required - cpf_info["cpf_used"])
    cash_top_up = cpf_info["cash_top_up"]
    remaining_cash_buffer = available_cash - cash_needed - emergency_reserve
    cash_buffer_months = remaining_cash_buffer / max(monthly_installment, 1.0)
    age_warning = None
    if effective_borrower_age + tenure_years > 65 and age_mode == "strict":
        age_warning = "Loan tenure is capped by age under strict MAS rules."
    elif effective_borrower_age + tenure_years > 75:
        age_warning = "Loan tenure may be unsafe because the borrower age exceeds flexible MAS limits."
    hdb_passed, hdb_reasons = validate_hdb_eligibility(property_type, buyers, buyers[0].get("relationship", "Single") if buyers else "Single", any(buyer.get("existing_property_count", 0) > 0 for buyer in buyers))
    results = {
        "purchase_price": purchase_price,
        "property_type": property_type,
        "gross_monthly_income": gross_monthly_income,
        "monthly_service_capacity": monthly_service_capacity,
        "loan_capacity": loan_capacity,
        "max_price_by_loan": max_price_by_loan,
        "max_price_by_cash": max_price_by_cash,
        "max_affordable_price": max_affordable_price,
        "loan_amount": loan_amount,
        "monthly_installment": monthly_installment,
        "absd_rate": absd_info["rate"],
        "absd_amount": absd_info["amount"],
        "absd_tier": absd_info["tier"],
        "absd_notes": absd_info["notes"],
        "bsd_amount": calculate_bsd(purchase_price),
        "cash_required": cash_needed,
        "cash_top_up": cash_top_up,
        "cpf_used": cpf_info["cpf_used"],
        "cpf_pledged": cpf_info["pledged"],
        "cpf_shortfall": max(0.0, downpayment_required - cpf_info["total_oa"]),
        "remaining_cash_buffer": remaining_cash_buffer,
        "cash_buffer_months": cash_buffer_months,
        "loan_tenure_years": tenure_years,
        "age_warning": age_warning,
        "hdb_eligibility_passed": hdb_passed,
        "hdb_eligibility_reasons": hdb_reasons,
        "service_ratio": monthly_service_capacity / max(gross_monthly_income, 1.0) if gross_monthly_income > 0 else 0.0,
    }
    recommendations = generate_recommendations(results)
    warnings: list[str] = []
    if cash_top_up > 0:
        warnings.append("You need additional cash beyond your current funds to meet the down payment.")
    if absd_info["rate"] > 0:
        warnings.append("ABSD applies and may substantially raise upfront costs.")
    if cash_buffer_months < 6:
        warnings.append("Cash reserves after purchase are below 6 months.")
    if not hdb_passed:
        warnings.append("HDB eligibility requirements are not fully met.")
    if monthly_installment > gross_monthly_income * 0.55:
        warnings.append("Your monthly mortgage exceeds the standard TDSR threshold.")

    return AffordabilityResult(
        purchase_price=purchase_price,
        max_affordable_price=max_affordable_price,
        recommended_budget=max_affordable_price * 0.90,
        loan_amount=loan_amount,
        monthly_installment=monthly_installment,
        absd_amount=absd_info["amount"],
        absd_rate=absd_info["rate"],
        bsd_amount=calculate_bsd(purchase_price),
        cash_required=cash_needed,
        cash_top_up=cash_top_up,
        cpf_used=cpf_info["cpf_used"],
        cpf_pledged=cpf_info["pledged"],
        cpf_shortfall=max(0.0, downpayment_required - cpf_info["total_oa"]),
        remaining_cash_buffer=remaining_cash_buffer,
        cash_buffer_months=cash_buffer_months,
        loan_tenure_years=tenure_years,
        age_warning=age_warning,
        hdb_eligibility_passed=hdb_passed,
        hdb_eligibility_reasons=hdb_reasons,
        warnings=warnings,
        recommendations=recommendations,
        summary=results,
        property_type=property_type,
    )

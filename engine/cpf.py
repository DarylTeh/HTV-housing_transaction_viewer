from __future__ import annotations
from rules.cpf_rules import CPF_RULES
from rules.loan_rules import PROPERTY_RULES


def total_cpf_oa(buyers: list[dict]) -> float:
    return sum(buyer.get("cpf_oa", 0.0) for buyer in buyers if buyer.get("will_be_owner", True))


def calculate_cpf_usage(
    buyers: list[dict],
    purchase_price: float,
    property_type: str,
    pledge_cpf: bool,
    requested_pledge: float,
    available_cash: float,
) -> dict[str, float | bool]:
    rule = PROPERTY_RULES.get(property_type, PROPERTY_RULES["Condo"])
    total_oa = total_cpf_oa(buyers)
    loan_ltv = rule.get("ltv", 0.75)
    downpayment_pct = rule.get("downpayment_pct", 0.25)
    min_cash_pct = rule.get("min_cash_pct", 0.05)
    cash_required = purchase_price * downpayment_pct
    min_cash_required = purchase_price * min_cash_pct
    cpf_limit = purchase_price * (CPF_RULES["hdb_cpf_coverage_pct"] if rule.get("loan_type") == "hdb" else CPF_RULES["private_cpf_coverage_pct"])
    cpf_available = min(total_oa, cpf_limit)
    cpf_for_downpayment = min(cpf_available, cash_required)
    cash_after_cpf = max(0.0, cash_required - cpf_for_downpayment)
    cash_top_up = max(0.0, cash_after_cpf - available_cash)
    pledged = min(requested_pledge if pledge_cpf else 0.0, total_oa)
    remaining_oa = max(0.0, total_oa - cpf_for_downpayment - pledged)
    return {
        "total_oa": total_oa,
        "cpf_available": cpf_available,
        "cpf_used": cpf_for_downpayment,
        "pledged": pledged,
        "remaining_oa": remaining_oa,
        "cash_required": cash_required,
        "min_cash_required": min_cash_required,
        "cash_after_cpf": cash_after_cpf,
        "cash_top_up": cash_top_up,
    }

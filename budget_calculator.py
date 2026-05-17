"""
Estimate maximum purchase budget from income (IPA-style), not from a target property price.
Educational simplification — confirm figures with your bank.
"""

from __future__ import annotations

import math
from dataclasses import dataclass


@dataclass
class BudgetResult:
    housing_type: str
    assessed_income_monthly: float
    max_loan_tenure_years: int
    max_monthly_installment: float
    msr_cap: float
    tdsr_cap: float
    max_loan: float
    max_property_price: float
    safety_net_price: float
    interest_rate: float


def _loan_from_payment(monthly_payment: float, annual_rate: float, years: int) -> float:
    if monthly_payment <= 0 or years <= 0:
        return 0.0
    months = years * 12
    r = annual_rate / 12
    if r <= 0:
        return monthly_payment * months
    factor = (1 + r) ** months
    return monthly_payment * (factor - 1) / (r * factor)


def _assessed_monthly_income(
    buyer1: float,
    buyer2: float,
    pledge_monthly: float,
    unpledge_cpf: float,
) -> float:
    base = max(buyer1, 0) + max(buyer2, 0)
    # Simplified: pledge counts pledgor income; unpledge treats CPF as ~4%/yr income stream.
    unpledge_income = max(unpledge_cpf, 0) * 0.04 / 12
    return base + max(pledge_monthly, 0) + unpledge_income


def _max_tenure_years(age_youngest: int, housing_type: str) -> int:
    remaining = max(65 - age_youngest, 1)
    cap = 25 if housing_type == "HDB" else 30
    return max(1, min(cap, remaining))


def compute_budget(
    *,
    buyer1_income: float,
    buyer2_income: float = 0.0,
    age_youngest: int = 30,
    housing_type: str = "HDB",
    monthly_debts: float = 0.0,
    pledge_monthly: float = 0.0,
    unpledge_cpf: float = 0.0,
    cash_and_cpf: float = 0.0,
    downpayment_pct: float = 0.25,
    interest_rate: float = 0.035,
    safety_net_pct: float = 0.90,
) -> BudgetResult:
    assessed = _assessed_monthly_income(buyer1_income, buyer2_income, pledge_monthly, unpledge_cpf)
    tenure = _max_tenure_years(age_youngest, housing_type)

    msr_cap = assessed * 0.30
    tdsr_cap = max(assessed * 0.55 - monthly_debts, 0)

    if housing_type == "HDB":
        max_payment = min(msr_cap, tdsr_cap)
    else:
        max_payment = tdsr_cap

    max_loan = _loan_from_payment(max_payment, interest_rate, tenure)
    price_from_loan = max_loan / (1 - downpayment_pct) if downpayment_pct < 1 else max_loan
    price_with_cash = max_loan + max(cash_and_cpf, 0)
    max_price = max(price_from_loan, price_with_cash)
    safety = max_price * safety_net_pct

    return BudgetResult(
        housing_type=housing_type,
        assessed_income_monthly=assessed,
        max_loan_tenure_years=tenure,
        max_monthly_installment=max_payment,
        msr_cap=msr_cap,
        tdsr_cap=tdsr_cap,
        max_loan=max_loan,
        max_property_price=max_price,
        safety_net_price=safety,
        interest_rate=interest_rate,
    )

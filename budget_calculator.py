"""Income-based budget calculator for HDB and private property."""

from __future__ import annotations

import math
from dataclasses import dataclass


@dataclass
class BudgetResult:
    """Result from budget calculation."""
    gross_monthly_income: float
    num_buyers: int
    ages: list[int]
    cpf_pledge_pct: float
    hdb_max_budget: float
    private_max_budget: float
    recommended_budget: float
    limitations: list[str]


def max_loan_years_at_completion(age_at_completion: int, max_age: int = 65) -> bool:
    """Check if age at end of loan is acceptable (typically max 65)."""
    return age_at_completion <= max_age


def calculate_max_loan_amount(gross_monthly_income: float, debt_service_ratio: float) -> float:
    """
    Calculate max loan principal based on debt service ratio.
    
    Args:
        gross_monthly_income: Monthly gross income in SGD
        debt_service_ratio: Allowed ratio (0.30 for MSR/HDB, 0.55 for TDSR/private)
    
    Returns:
        Maximum loan amount that can be serviced
    """
    if gross_monthly_income <= 0:
        return 0.0
    
    # Assume typical 25-year HDB loan, 3.5% interest rate
    interest_rate_annual = 0.035
    monthly_rate = interest_rate_annual / 12
    months = 25 * 12
    
    max_monthly_payment = gross_monthly_income * debt_service_ratio
    
    if monthly_rate > 0:
        # Reverse mortgage formula: PV = PMT * [(1 - (1 + r)^-n) / r]
        max_loan = max_monthly_payment * (1 - (1 + monthly_rate) ** -months) / monthly_rate
    else:
        max_loan = max_monthly_payment * months
    
    return max_loan


def calculate_budget(
    gross_monthly_income: float,
    num_buyers: int = 1,
    ages: list[int] | None = None,
    cpf_pledge_pct: float = 0.0,
    max_loan_completion_age: int = 65,
) -> BudgetResult:
    """
    Calculate maximum budget for HDB and private property.
    
    Args:
        gross_monthly_income: Combined monthly gross income (all buyers)
        num_buyers: Number of buyers (1 or 2)
        ages: List of buyer ages (e.g., [35] or [35, 33])
        cpf_pledge_pct: CPF OA balance pledged as percentage (0-100)
        max_loan_completion_age: Max age at end of loan (typically 65)
    
    Returns:
        BudgetResult with HDB and private budgets
    """
    if ages is None:
        ages = [35] * num_buyers
    
    limitations = []
    
    # Validate inputs
    if num_buyers not in (1, 2):
        limitations.append("Number of buyers must be 1 or 2")
    
    if gross_monthly_income <= 0:
        limitations.append("Monthly income must be positive")
        return BudgetResult(
            gross_monthly_income=gross_monthly_income,
            num_buyers=num_buyers,
            ages=ages,
            cpf_pledge_pct=cpf_pledge_pct,
            hdb_max_budget=0.0,
            private_max_budget=0.0,
            recommended_budget=0.0,
            limitations=limitations,
        )
    
    # Check age at loan completion (25 years)
    primary_age = ages[0]
    age_at_completion = primary_age + 25
    if age_at_completion > max_loan_completion_age:
        limitations.append(
            f"Primary buyer age at loan end ({age_at_completion}) exceeds {max_loan_completion_age}. "
            f"May need shorter loan or co-buyer."
        )
    
    # HDB: MSR (Mortgage Servicing Ratio) = 30% of gross income
    hdb_max_loan = calculate_max_loan_amount(gross_monthly_income, 0.30)
    
    # Private: TDSR (Total Debt Servicing Ratio) = 55% of gross income
    # (typically lower in practice but use standard limit)
    private_max_loan = calculate_max_loan_amount(gross_monthly_income, 0.55)
    
    # Rough down payment estimation (20-25% typical)
    # For HDB: down payment is typically 10% or 5% for first-timers, then CPF can cover
    # For private: typically 25-30% cash + CPF
    
    # HDB down payment (assume 10% minimum, but CPF OA can supplement)
    hdb_down_payment_rate = 0.10
    hdb_budget = hdb_max_loan / (1 - hdb_down_payment_rate)
    
    # Private down payment (assume 25% required)
    private_down_payment_rate = 0.25
    private_budget = private_max_loan / (1 - private_down_payment_rate)
    
    # CPF pledge impact: reduces OA balance available for down payment
    # (represented as percentage loss of down payment capacity)
    if cpf_pledge_pct > 0:
        # Reduce budget slightly if pledging CPF (less capital available)
        pledge_impact = cpf_pledge_pct / 100.0 * 0.1  # 1% pledge = 0.1% budget reduction
        hdb_budget *= (1 - pledge_impact)
        private_budget *= (1 - pledge_impact)
        if cpf_pledge_pct > 50:
            limitations.append(
                f"High CPF pledge ({cpf_pledge_pct}%). Verify with CPF Board and bank; "
                "may impact down payment capacity."
            )
    
    # Recommended budget (safety net at 80% of max)
    recommended_budget = min(hdb_budget, private_budget) * 0.80
    
    return BudgetResult(
        gross_monthly_income=gross_monthly_income,
        num_buyers=num_buyers,
        ages=ages,
        cpf_pledge_pct=cpf_pledge_pct,
        hdb_max_budget=hdb_budget,
        private_max_budget=private_budget,
        recommended_budget=recommended_budget,
        limitations=limitations,
    )


def format_currency(value: float) -> str:
    """Format value as Singapore Dollar string."""
    return f"${value:,.0f}"

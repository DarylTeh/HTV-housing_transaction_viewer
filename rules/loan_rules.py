from __future__ import annotations

PROPERTY_RULES: dict[str, dict[str, float | bool]] = {
    "HDB BTO": {"max_tenure": 25, "ltv": 0.80, "tdsr": 0.30, "msr": 0.30, "downpayment_pct": 0.20, "min_cash_pct": 0.00, "cpf_allowed": True, "loan_type": "hdb"},
    "HDB resale": {"max_tenure": 25, "ltv": 0.80, "tdsr": 0.30, "msr": 0.30, "downpayment_pct": 0.20, "min_cash_pct": 0.00, "cpf_allowed": True, "loan_type": "hdb"},
    "EC new launch": {"max_tenure": 30, "ltv": 0.75, "tdsr": 0.55, "msr": 0.30, "downpayment_pct": 0.25, "min_cash_pct": 0.05, "cpf_allowed": True, "loan_type": "private"},
    "EC resale": {"max_tenure": 30, "ltv": 0.70, "tdsr": 0.55, "msr": 0.30, "downpayment_pct": 0.25, "min_cash_pct": 0.05, "cpf_allowed": True, "loan_type": "private"},
    "Condo": {"max_tenure": 30, "ltv": 0.75, "tdsr": 0.55, "msr": 0.30, "downpayment_pct": 0.25, "min_cash_pct": 0.05, "cpf_allowed": True, "loan_type": "private"},
    "Landed": {"max_tenure": 25, "ltv": 0.60, "tdsr": 0.55, "msr": 0.30, "downpayment_pct": 0.30, "min_cash_pct": 0.10, "cpf_allowed": True, "loan_type": "private"},
}

AGE_LIMITS: dict[str, int] = {
    "strict": 65,
    "flexible": 75,
}

AGE_METHODS = ["oldest", "average", "weighted_average", "youngest"]

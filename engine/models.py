from __future__ import annotations
from dataclasses import dataclass

@dataclass
class Buyer:
    name: str
    relationship: str
    age: int
    citizenship: str
    monthly_income: float
    annual_bonus: float
    cpf_oa: float
    existing_property_count: int
    existing_home_loan: float
    other_monthly_debt: float
    ownership_percentage: float
    will_be_owner: bool
    essential_occupier: bool

    def monthly_income_with_bonus(self) -> float:
        return self.monthly_income + self.annual_bonus / 12.0

    def citizenship_label(self) -> str:
        return self.citizenship

from __future__ import annotations

HDB_RULES: dict[str, dict[str, float | bool]] = {
    "HDB BTO": {"max_tenure": 25, "ltv": 0.80, "tdsr": 0.30, "msr": 0.30, "downpayment_pct": 0.20, "min_cash_pct": 0.00, "cpf_allowed": True},
    "HDB resale": {"max_tenure": 25, "ltv": 0.80, "tdsr": 0.30, "msr": 0.30, "downpayment_pct": 0.20, "min_cash_pct": 0.00, "cpf_allowed": True},
}

HDB_FAMILY_RELATIONSHIPS = [
    "Husband & Wife",
    "Father & Son",
    "Mother & Daughter",
    "Parent & Child",
    "Siblings",
    "Friends",
    "Investor Partners",
]


def is_hdb_property(property_type: str) -> bool:
    return property_type in HDB_RULES


def validate_hdb_eligibility(
    property_type: str,
    buyers: list[dict],
    relationship_type: str,
    existing_private_property: bool,
) -> tuple[bool, list[str]]:
    reasons: list[str] = []
    if not is_hdb_property(property_type):
        return True, reasons

    owners = [buyer for buyer in buyers if buyer.get("will_be_owner", True)]
    if not owners:
        reasons.append("At least one HDB owner must be selected.")
        return False, reasons

    citizenships = [buyer.get("citizenship", "SC") for buyer in owners]
    if "Foreigner" in citizenships:
        reasons.append("Foreigners cannot own HDB property.")

    has_sc = any(cit == "SC" for cit in citizenships)
    has_pr = any(cit == "PR" for cit in citizenships)
    if not has_sc:
        reasons.append("At least one Singapore Citizen owner is required for HDB eligibility.")

    if len(owners) == 1:
        age = owners[0].get("age", 0)
        if age < 35:
            reasons.append("Single buyers must be at least 35 years old to buy HDB.")

    if len(owners) > 1 and relationship_type not in HDB_FAMILY_RELATIONSHIPS:
        reasons.append("Multiple HDB owners must form a family nucleus or family-related relationship.")

    if existing_private_property:
        reasons.append("Existing private property may disqualify HDB purchase without resale.")

    return (len(reasons) == 0), reasons

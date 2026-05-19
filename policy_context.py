"""Educational context and policy explanations for new homebuyers."""

from __future__ import annotations

POLICY_EDUCATION = {
    "hdb_mop": {
        "title": "HDB Minimum Occupation Period (MOP)",
        "content": (
            "If you buy an HDB resale flat, you must live in it for at least **5 years** before you can sell or buy another property. "
            "This rule prevents speculation and keeps HDB affordable. Once MOP is over, you can upgrade to private housing, "
            "but be prepared for ABSD (stamp duty) and the requirement to sell your HDB within 6 months of buying private property."
        ),
    },
    "school_priority": {
        "title": "School Enrolment Priority Zones",
        "content": (
            "In Singapore, children seeking entry to government or government-aided schools get **priority if they live within 1 km** of the school. "
            "This is a key reason why many families look for homes near good schools. Use the 'Nearest schools' tool to check if your preferred "
            "location is within the priority zone of your chosen school."
        ),
    },
    "family_planning": {
        "title": "Planning for a Family",
        "content": (
            "If you buy HDB, you're likely planning to have children (HDB has family-friendly policies). "
            "This means proximity to **schools, supermarkets, and healthcare** becomes important for daily life. "
            "The app shows hawker centres and pharmacies nearby so you can assess convenience before committing to a location."
        ),
    },
    "cpf_usage": {
        "title": "CPF & Down Payment",
        "content": (
            "Your **CPF Ordinary Account (OA)** can be used for down payment and mortgage payments. "
            "Be cautious about pledging your CPF (using it as loan security) — it reduces your retirement savings. "
            "Most banks allow pledges, but the risk is yours. Always discuss with your bank before pledging."
        ),
    },
    "absd_explanation": {
        "title": "ABSD (Additional Buyer's Stamp Duty)",
        "content": (
            "If you're buying a second property or you're a PR/foreigner, ABSD is an extra tax on top of normal stamp duty. "
            "For **second property**: Citizens pay 20%, PRs pay 30%. For **third+**: Citizens pay 30%, PRs pay 35%. "
            "**Foreigners** pay 60% on all properties. This is why many buyers prioritize private property if they qualify."
        ),
    },
    "tdsr_msr": {
        "title": "TDSR & MSR: Loan Limits",
        "content": (
            "Banks use two ratios to check if you can afford a mortgage:\n"
            "- **MSR (Mortgage Servicing Ratio)**: For HDB loans, your monthly payment ≤ 30% of gross income.\n"
            "- **TDSR (Total Debt Servicing Ratio)**: For private property, all debt (mortgage + credit cards + car loans) ≤ 55% of gross income.\n"
            "If you exceed these, the bank won't approve the loan."
        ),
    },
}


def get_policy_tip(policy_key: str) -> dict:
    """Get educational content for a policy topic."""
    return POLICY_EDUCATION.get(policy_key, {})


def render_policy_tips() -> list[tuple[str, str]]:
    """Return list of (title, content) for all policy tips."""
    return [(v["title"], v["content"]) for v in POLICY_EDUCATION.values()]

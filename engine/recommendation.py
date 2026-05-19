from __future__ import annotations

def generate_recommendations(results: dict) -> list[str]:
    recommendations: list[str] = []
    if results.get("hdb_eligibility_passed") is False:
        recommendations.append("Review HDB eligibility and family nucleus rules before proceeding.")
    if results.get("absd_rate", 0) >= 0.6:
        recommendations.append("Consider ownership restructuring to reduce ABSD if one buyer is foreign or PR.")
    if results.get("cash_buffer_months", 999) < 6:
        recommendations.append("Your post-purchase cash buffer is below 6 months — keep more emergency reserves.")
    if results.get("age_warning"):
        recommendations.append(results["age_warning"])
    if results.get("cpf_shortfall", 0) > 0:
        recommendations.append("CPF may be insufficient for your desired purchase; additional cash top-up is required.")
    if results.get("loan_tenure_years", 0) < 25 and results.get("property_type") in ["Condo", "EC new launch", "EC resale", "Landed"]:
        recommendations.append("Loan tenure is shortened by age; consider older borrowers only if possible.")
    if results.get("max_affordable_price", 0) < results.get("purchase_price", 0):
        recommendations.append("Your current target price exceeds the calculated affordability ceiling.")
    if not recommendations:
        recommendations.append("Current scenario looks structurally sound, but confirm with a bank before committing.")
    return recommendations

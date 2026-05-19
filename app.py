import base64
import json
from typing import Any

import pandas as pd
import streamlit as st

from components.cards import show_summary_cards
from components.charts import cash_flow_sankey, payment_breakdown_pie, payment_timeline
from components.warnings import show_warning_list
from engine.affordability import AffordabilityResult, calculate_affordability
from engine.loan import monthly_payment
from rules.loan_rules import AGE_METHODS, PROPERTY_RULES


st.set_page_config(
    page_title="Singapore Property Affordability Calculator",
    page_icon="🏦",
    layout="wide",
)

BORROWER_RELATIONSHIPS = [
    "Single",
    "Husband & Wife",
    "Father & Son",
    "Mother & Daughter",
    "Parent & Child",
    "Siblings",
    "Friends",
    "Investor Partners",
]

CITIZENSHIP_OPTIONS = ["SC", "PR", "Foreigner"]
EXISTING_PROPERTY_OPTIONS = [
    "No existing property",
    "Keep existing property",
    "Sell before purchase",
    "Sell within 6 months",
]


def format_currency(value: float) -> str:
    return f"${value:,.0f}" if value is not None else "-"


def format_rate(value: float) -> str:
    return f"{value * 100:.1f}%" if value is not None else "-"


def init_session_state() -> None:
    defaults = {
        "saved_scenarios": [],
        "scenario_name": "My first scenario",
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


def buyer_inputs(index: int) -> None:
    buyer_key = f"buyer_{index}"
    if buyer_key + "_active" not in st.session_state:
        st.session_state[buyer_key + "_active"] = index < 2

    active = st.checkbox(f"Buyer {index + 1} active", value=st.session_state[buyer_key + "_active"], key=buyer_key + "_active")
    with st.expander(f"Buyer {index + 1}", expanded=active):
        if not active:
            return

        cols = st.columns([2, 1, 1])
        with cols[0]:
            st.text_input("Name", key=buyer_key + "_name", placeholder=f"Buyer {index + 1} name")
            st.selectbox("Relationship", BORROWER_RELATIONSHIPS, key=buyer_key + "_relationship")
            st.selectbox("Citizenship", CITIZENSHIP_OPTIONS, key=buyer_key + "_citizenship")
        with cols[1]:
            st.number_input("Age", min_value=18, max_value=85, value=35, step=1, key=buyer_key + "_age")
            st.number_input("Monthly income (SGD)", min_value=0.0, value=5000.0, step=100.0, key=buyer_key + "_monthly_income")
            st.number_input("Annual bonus (SGD)", min_value=0.0, value=0.0, step=500.0, key=buyer_key + "_annual_bonus")
        with cols[2]:
            st.number_input("CPF OA balance (SGD)", min_value=0.0, value=10000.0, step=500.0, key=buyer_key + "_cpf_oa")
            st.number_input("Existing property count", min_value=0, max_value=5, value=0, step=1, key=buyer_key + "_existing_property_count")
            st.number_input("Existing monthly loan payment (SGD)", min_value=0.0, value=0.0, step=100.0, key=buyer_key + "_existing_home_loan")
            st.number_input("Other monthly debt (SGD)", min_value=0.0, value=0.0, step=50.0, key=buyer_key + "_other_monthly_debt")
            st.number_input("Ownership percentage", min_value=0.0, max_value=100.0, value=25.0, step=1.0, key=buyer_key + "_ownership_percentage")
            st.checkbox("Will be owner", value=True, key=buyer_key + "_will_be_owner")
            st.checkbox("Essential occupier", value=False, key=buyer_key + "_essential_occupier")


def collect_buyers() -> list[dict[str, Any]]:
    buyers: list[dict[str, Any]] = []
    for idx in range(4):
        if not st.session_state.get(f"buyer_{idx}_active", False):
            continue
        buyer = {
            "name": st.session_state.get(f"buyer_{idx}_name", f"Buyer {idx + 1}"),
            "relationship": st.session_state.get(f"buyer_{idx}_relationship", "Single"),
            "age": st.session_state.get(f"buyer_{idx}_age", 35),
            "citizenship": st.session_state.get(f"buyer_{idx}_citizenship", "SC"),
            "monthly_income": st.session_state.get(f"buyer_{idx}_monthly_income", 0.0),
            "annual_bonus": st.session_state.get(f"buyer_{idx}_annual_bonus", 0.0),
            "cpf_oa": st.session_state.get(f"buyer_{idx}_cpf_oa", 0.0),
            "existing_property_count": st.session_state.get(f"buyer_{idx}_existing_property_count", 0),
            "existing_home_loan": st.session_state.get(f"buyer_{idx}_existing_home_loan", 0.0),
            "other_monthly_debt": st.session_state.get(f"buyer_{idx}_other_monthly_debt", 0.0),
            "ownership_percentage": st.session_state.get(f"buyer_{idx}_ownership_percentage", 0.0),
            "will_be_owner": st.session_state.get(f"buyer_{idx}_will_be_owner", True),
            "essential_occupier": st.session_state.get(f"buyer_{idx}_essential_occupier", False),
        }
        buyers.append(buyer)
    return buyers


def ownership_warning(buyers: list[dict[str, Any]]) -> list[str]:
    warnings: list[str] = []
    owner_total = sum(b.get("ownership_percentage", 0.0) for b in buyers if b.get("will_be_owner", False))
    if owner_total and abs(owner_total - 100.0) > 1.0:
        warnings.append("Ownership percentages should sum to 100% for owner buyers.")
    return warnings


def build_scenario_payload(calculation: AffordabilityResult, buyers: list[dict[str, Any]], values: dict[str, Any]) -> dict[str, Any]:
    return {
        "name": values.get("scenario_name", "Untitled scenario"),
        "buyers": buyers,
        "property_type": calculation.property_type,
        "purchase_price": calculation.purchase_price,
        "max_affordable_price": calculation.max_affordable_price,
        "monthly_installment": calculation.monthly_installment,
        "cash_required": calculation.cash_required,
        "absd_amount": calculation.absd_amount,
        "bsd_amount": calculation.bsd_amount,
        "cash_buffer_months": calculation.cash_buffer_months,
        "cpf_shortfall": calculation.cpf_shortfall,
        "warnings": calculation.warnings,
        "recommendations": calculation.recommendations,
    }


def encode_shareable_scenario(payload: dict[str, Any]) -> str:
    text = json.dumps(payload, default=str, separators=(",", ":"))
    return base64.urlsafe_b64encode(text.encode("utf-8")).decode("utf-8")


def decode_shareable_scenario(encoded: str) -> dict[str, Any] | None:
    try:
        decoded = base64.urlsafe_b64decode(encoded.encode("utf-8")).decode("utf-8")
        return json.loads(decoded)
    except Exception:
        return None


def render_profile_tab() -> None:
    st.header("1. Profile")
    st.write(
        "Add up to 4 buyers. Each person can be an owner, essential occupier, or a secondary decision-maker. "
        "The calculator learns citizenship, age, income, CPF, debt, and ownership split."
    )
    for idx in range(4):
        buyer_inputs(idx)


def render_current_property_tab() -> dict[str, Any]:
    st.header("2. Current Property")
    existing_option = st.selectbox("Existing property strategy", EXISTING_PROPERTY_OPTIONS, index=0)
    existing_count = 0
    existing_property_value = 0.0
    if existing_option != "No existing property":
        existing_count = st.number_input("Existing property count", min_value=0, max_value=10, value=1, step=1)
        existing_property_value = st.number_input("Estimated existing property value (SGD)", min_value=0.0, value=600_000.0, step=10_000.0)
        if existing_option == "Keep existing property":
            st.info("Keeping an existing property may trigger 2nd-property ABSD and lower LTV for the new loan.")
    return {
        "existing_option": existing_option,
        "existing_count": existing_count,
        "existing_property_value": existing_property_value,
        "keep_existing_property": existing_option == "Keep existing property",
        "sell_within_6_months": existing_option == "Sell within 6 months",
    }


def render_new_purchase_tab() -> dict[str, Any]:
    st.header("3. New Purchase")
    st.write("Select the property type and purchase price for the new home.")
    property_type = st.selectbox("Property type", list(PROPERTY_RULES.keys()), index=0)
    purchase_price = st.number_input("Purchase price (SGD)", min_value=100_000.0, value=600_000.0, step=10_000.0)
    scenario_name = st.text_input("Scenario name", value=st.session_state.get("scenario_name", "My first scenario"))
    st.session_state["scenario_name"] = scenario_name
    return {"property_type": property_type, "purchase_price": purchase_price, "scenario_name": scenario_name}


def render_loan_cpf_tab() -> dict[str, Any]:
    st.header("4. Loan & CPF")
    st.write("Bank rules, MAS age limits, CPF pledging and stress tests are all captured here.")
    cols = st.columns(2)
    with cols[0]:
        age_mode = st.radio("Age rule mode", ["strict", "flexible"], index=0, help="Strict mode uses age + tenure <= 65; flexible mode allows up to 75.")
        age_method = st.selectbox("Loan age method", AGE_METHODS, index=1, help="Banks may use oldest, average, weighted average or youngest borrower age.")
        interest_rate = st.number_input("Assumed interest rate (%)", min_value=1.0, max_value=8.0, value=3.5, step=0.1)
        available_cash = st.number_input("Available cash for purchase (SGD)", min_value=0.0, value=120_000.0, step=500.0)
        emergency_reserve = st.number_input("Emergency cash reserve (SGD)", min_value=0.0, value=60_000.0, step=500.0)
    with cols[1]:
        pledge_cpf = st.checkbox("Pledge CPF OA", value=True)
        pledge_amount = st.number_input("CPF pledge amount (SGD)", min_value=0.0, value=0.0, step=500.0) if pledge_cpf else 0.0
        st.markdown(
            "**Stress test**: monthly instalments are shown at 4%, 5%, and 6% on the Results page. "
            "This helps spot interest rate risk early."
        )
    return {
        "age_mode": age_mode,
        "age_method": age_method,
        "interest_rate": interest_rate / 100.0,
        "available_cash": available_cash,
        "emergency_reserve": emergency_reserve,
        "pledge_cpf": pledge_cpf,
        "pledge_amount": pledge_amount,
    }


def render_results_tab(
    buyers: list[dict[str, Any]],
    purchase_inputs: dict[str, Any],
    property_state: dict[str, Any],
    loan_inputs: dict[str, Any],
) -> None:
    st.header("5. Results")
    if not buyers:
        st.error("Please add at least one active buyer in the Profile tab.")
        return

    calc = calculate_affordability(
        buyers=buyers,
        property_type=purchase_inputs["property_type"],
        purchase_price=purchase_inputs["purchase_price"],
        interest_rate=loan_inputs["interest_rate"],
        age_mode=loan_inputs["age_mode"],
        age_method=loan_inputs["age_method"],
        keep_existing_property=property_state["keep_existing_property"],
        sell_existing_within_6_months=property_state["sell_within_6_months"],
        available_cash=loan_inputs["available_cash"],
        emergency_reserve=loan_inputs["emergency_reserve"],
        pledge_cpf=loan_inputs["pledge_cpf"],
        request_pledge_amount=loan_inputs["pledge_amount"],
    )

    metrics = [
        ("Max budget", format_currency(calc.max_affordable_price), None, "Highest purchase price supported by income, LTV and CPF allowance."),
        ("Recommended budget", format_currency(calc.recommended_budget), None, "Conservative target to preserve a buffer."),
        ("Monthly instalment", format_currency(calc.monthly_installment), None, f"Based on {calc.loan_tenure_years} years at {loan_inputs['interest_rate'] * 100:.2f}% interest."),
        ("Cash needed", format_currency(calc.cash_required), None, "Estimated additional cash required after CPF and pledge."),
        ("ABSD", format_currency(calc.absd_amount), format_rate(calc.absd_rate), "Additional Buyer's Stamp Duty based on citizenship and property count."),
        ("BSD", format_currency(calc.bsd_amount), None, "Buyer's Stamp Duty using progressive IRAS tiers."),
    ]
    show_summary_cards(metrics)

    if calc.hdb_eligibility_passed is False:
        st.error("HDB eligibility not met")
        for reason in calc.hdb_eligibility_reasons:
            st.write(f"- {reason}")

    if calc.warnings:
        show_warning_list(calc.warnings)

    with st.expander("How this is calculated"):
        st.markdown(
            f"- **Loan capacity** is based on TDSR {format_rate(PROPERTY_RULES[purchase_inputs['property_type']]['tdsr'])} and MSR {format_rate(PROPERTY_RULES[purchase_inputs['property_type']]['msr'])} where applicable."
        )
        st.markdown(
            f"- **LTV** for {purchase_inputs['property_type']} is {format_rate(PROPERTY_RULES[purchase_inputs['property_type']]['ltv'])}. "
            f"Loan amount = purchase price × LTV."
        )
        st.markdown(
            f"- **Down payment** = purchase price × {format_rate(PROPERTY_RULES[purchase_inputs['property_type']]['downpayment_pct'])}. "
            f"Minimum cash share = {format_rate(PROPERTY_RULES[purchase_inputs['property_type']]['min_cash_pct'])}."
        )
        st.markdown(
            f"- **CPF** is modelled from OA balances and pledge amount. "
            "For HDB, CPF can cover a larger share of down payment; for private property, a minimum cash portion remains."
        )

    chart_cols = st.columns(2)
    with chart_cols[0]:
        st.plotly_chart(
            payment_breakdown_pie(calc.cash_required, calc.cpf_used, calc.absd_amount, calc.bsd_amount, calc.loan_amount),
            use_container_width=True,
        )
    with chart_cols[1]:
        st.plotly_chart(cash_flow_sankey(calc.loan_amount, calc.absd_amount, calc.bsd_amount, calc.cash_required, calc.cpf_used), use_container_width=True)

    st.plotly_chart(payment_timeline(calc.purchase_price, calc.monthly_installment, calc.loan_tenure_years), use_container_width=True)

    with st.expander("Interest rate stress test"):
        stress_rates = [0.04, 0.05, 0.06]
        for rate in stress_rates:
            payment = monthly_payment(calc.loan_amount, rate, calc.loan_tenure_years)
            st.write(f"{int(rate * 100)}% interest → {format_currency(payment)} / month")

    share_payload = build_scenario_payload(calc, buyers, purchase_inputs)
    encoded = encode_shareable_scenario(share_payload)
    st.download_button(
        "Download results CSV",
        pd.DataFrame([share_payload]).to_csv(index=False).encode("utf-8"),
        file_name="property_affordability_summary.csv",
        mime="text/csv",
    )
    st.text_area("Share this scenario code", value=encoded, height=160)

    if st.button("Save this scenario"):
        st.session_state.saved_scenarios.append(share_payload)
        st.success("Scenario saved for comparison.")


def render_comparison_tab() -> None:
    st.header("6. Scenario Comparison")
    scenarios = st.session_state.saved_scenarios
    if not scenarios:
        st.info("Save one or more scenarios from the Results tab to compare them here.")
        return

    scenario_names = [scenario.get("name", f"Scenario {idx + 1}") for idx, scenario in enumerate(scenarios)]
    selections = st.multiselect("Select scenarios to compare", scenario_names, default=scenario_names[:2])
    selected = [s for s in scenarios if s.get("name") in selections]
    if len(selected) < 2:
        st.warning("Pick at least two saved scenarios to compare side by side.")
        return

    comparisons = pd.DataFrame(
        [
            {
                "Scenario": scenario.get("name", "Unnamed"),
                "Purchase price": scenario.get("purchase_price"),
                "Max affordable": scenario.get("max_affordable_price"),
                "Monthly instalment": scenario.get("monthly_installment"),
                "Cash needed": scenario.get("cash_required"),
                "ABSD": scenario.get("absd_amount"),
                "BSD": scenario.get("bsd_amount"),
                "Cash buffer months": scenario.get("cash_buffer_months"),
                "CPF shortfall": scenario.get("cpf_shortfall"),
            }
            for scenario in selected
        ]
    )
    st.dataframe(comparisons.style.format({
        "Purchase price": "${:,.0f}",
        "Max affordable": "${:,.0f}",
        "Monthly instalment": "${:,.0f}",
        "Cash needed": "${:,.0f}",
        "ABSD": "${:,.0f}",
        "BSD": "${:,.0f}",
        "Cash buffer months": "{:.1f}",
        "CPF shortfall": "${:,.0f}",
    }))

    st.download_button(
        "Download comparison CSV",
        comparisons.to_csv(index=False).encode("utf-8"),
        file_name="scenario_comparison.csv",
        mime="text/csv",
    )


def main() -> None:
    init_session_state()
    st.title("Singapore Property Affordability Calculator")
    st.markdown(
        "Use the tabs to describe buyers, current holdings, the new purchase, loan structure, and results. "
        "This tool is designed to feel like a modern banking calculator with clear metrics, warnings, and scenario comparison."
    )

    tab_profile, tab_current, tab_purchase, tab_loan, tab_results, tab_compare = st.tabs(
        ["Profile", "Current Property", "New Purchase", "Loan & CPF", "Results", "Scenario Comparison"]
    )

    with tab_profile:
        render_profile_tab()
    with tab_current:
        property_state = render_current_property_tab()
    with tab_purchase:
        purchase_inputs = render_new_purchase_tab()
    with tab_loan:
        loan_inputs = render_loan_cpf_tab()
    with tab_results:
        buyers = collect_buyers()
        extra_warnings = ownership_warning(buyers)
        if extra_warnings:
            for message in extra_warnings:
                st.warning(message)
        render_results_tab(buyers, purchase_inputs, property_state, loan_inputs)
    with tab_compare:
        render_comparison_tab()

    with st.expander("Disclaimer"):
        st.write(
            "Calculations are estimates only and not financial advice. Rules may change based on MAS, IRAS, CPF, and HDB regulations. "
            "Always confirm with your bank, lawyer and CPF Board before making a decision."
        )


if __name__ == "__main__":
    main()

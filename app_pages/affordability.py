from __future__ import annotations

import pandas as pd
import streamlit as st

from components.cards import show_summary_cards
from components.charts import cash_flow_sankey, payment_breakdown_pie, payment_timeline
from components.common import format_currency, format_rate
from engine.affordability import calculate_affordability

BUYER_TYPES = ["Primary Buyer", "Joint Buyer"]
PROPERTY_TYPES = ["HDB", "Condo", "Landed"]


def render_affordability_page(data: dict[str, pd.DataFrame], state: dict) -> None:
    st.header("Affordability")
    st.write("Estimate what you can afford today and how your budget compares to market prices.")

    with st.expander("Buyer profile", expanded=True):
        num_buyers = st.radio("Number of buyers", [1, 2], index=0, key="afford_num_buyers", horizontal=True)
        
        buyers = []
        for i in range(num_buyers):
            st.subheader(f"Buyer {i + 1}")
            citizenship = st.selectbox("Citizenship", ["SC", "PR", "Foreigner"], index=0, key=f"afford_citizenship_{i}")
            monthly_income = st.number_input("Monthly income (SGD)", min_value=0.0, value=8000.0, step=500.0, key=f"afford_monthly_income_{i}")
            existing_debt = st.number_input("Existing monthly debt (SGD)", min_value=0.0, value=300.0, step=50.0, key=f"afford_existing_debt_{i}")
            buyers.append({
                "citizenship": citizenship,
                "monthly_income": monthly_income,
                "existing_debt": existing_debt,
            })

    with st.expander("Property plan", expanded=True):
        property_type = st.selectbox("Target property type", PROPERTY_TYPES, index=1, key="afford_property_type")
        purchase_price = st.number_input("Target purchase price (SGD)", min_value=100000.0, value=900000.0, step=10000.0, key="afford_purchase_price")
        available_cash = st.number_input("Available cash for down payment (SGD)", min_value=0.0, value=150000.0, step=5000.0, key="afford_available_cash")
        interest_rate = st.number_input("Assumed home loan interest rate (%)", min_value=1.0, max_value=8.0, value=3.5, step=0.1, key="afford_interest_rate")

    if st.button("Run affordability assessment"):
        state["budget"] = purchase_price
        state["budget_calculated"] = True

    buyer_dicts = []
    for i, buyer in enumerate(buyers):
        buyer_dicts.append({
            "name": f"Buyer {i + 1}",
            "relationship": "Joint" if num_buyers == 2 else "Single",
            "age": 35,
            "citizenship": buyer["citizenship"],
            "monthly_income": buyer["monthly_income"],
            "annual_bonus": 0.0,
            "cpf_oa": 10000.0,
            "existing_property_count": 0,
            "existing_home_loan": buyer["existing_debt"],
            "other_monthly_debt": 0.0,
            "ownership_percentage": 100.0 / num_buyers,
            "will_be_owner": True,
            "essential_occupier": True,
        })
    
    result = calculate_affordability(
        buyers=buyer_dicts,
        property_type=property_type,
        purchase_price=purchase_price,
        interest_rate=interest_rate / 100.0,
        age_mode="strict",
        age_method="average",
        keep_existing_property=False,
        sell_existing_within_6_months=False,
        available_cash=available_cash,
        emergency_reserve=50000.0,
        pledge_cpf=True,
        request_pledge_amount=0.0,
    )

    if result:
        metrics = [
            ("Purchase price", format_currency(result.purchase_price), None, "Your selected home price."),
            ("Max affordable", format_currency(result.max_affordable_price), None, "Estimated maximum purchase price your income can support."),
            ("Monthly instalment", format_currency(result.monthly_installment), None, "Estimated monthly loan payment."),
            ("Cash required", format_currency(result.cash_required), None, "Cash needed after CPF and down payment."),
            ("ABSD", format_currency(result.absd_amount), format_rate(result.absd_rate), "Estimated stamp duty cost."),
        ]
        show_summary_cards(metrics)

        st.plotly_chart(
            payment_breakdown_pie(result.cash_required, result.cpf_used, result.absd_amount, result.bsd_amount, result.loan_amount),
            use_container_width=True,
        )
        st.plotly_chart(cash_flow_sankey(result.loan_amount, result.absd_amount, result.bsd_amount, result.cash_required, result.cpf_used), use_container_width=True)
        st.plotly_chart(payment_timeline(result.purchase_price, result.monthly_installment, result.loan_tenure_years), use_container_width=True)

        if st.button("Save this scenario"):
            scenario = {
                "name": f"Affordability: {num_buyers} Buyer(s)",
                "property_type": property_type,
                "purchase_price": result.purchase_price,
                "max_affordable_price": result.max_affordable_price,
                "monthly_installment": result.monthly_installment,
            }
            st.session_state.setdefault("saved_scenarios", []).append(scenario)
            st.success("Scenario saved.")

"""Streamlit UI sections for the housing journey app."""

from __future__ import annotations

import os

import pandas as pd
import plotly.express as px
import streamlit as st

from budget_calculator import compute_budget
from geo_utils import geocode_place, haversine_distance
from housing_constants import GLOSSARY, LOCATION_GUIDANCE, calculate_absd
from processed_data import (
    load_hawker_centres,
    load_pharmacies,
    load_supermarkets,
    moe_primary_near,
    nearest_places,
    ranked_schools_near,
)
from rental_model import load_rent_vs_buy_scenario, load_savings_projection
from schools import load_schools, programme_tags


def format_currency(value):
    if pd.isna(value):
        return "-"
    return f"${value:,.0f}"


def show_budget_calculator(residency: str):
    st.subheader("What can you afford? (loan budget)")
    st.caption(
        "Based on **income, age, and debts** — like a bank In-Principle Approval (IPA). "
        "The property price is an **output**, not something you enter here."
    )

    with st.form("budget_form"):
        c1, c2 = st.columns(2)
        with c1:
            num_buyers = st.radio("How many buyers on the loan?", [1, 2], horizontal=True)
            income1 = st.number_input("Buyer 1 gross monthly income (SGD)", min_value=0.0, value=5000.0, step=100.0)
            income2 = 0.0
            if num_buyers == 2:
                income2 = st.number_input("Buyer 2 gross monthly income (SGD)", min_value=0.0, value=4000.0, step=100.0)
            age1 = st.number_input("Younger buyer’s age", min_value=21, max_value=70, value=30)
        with c2:
            support = st.radio(
                "Parent support for loan assessment?",
                ["None", "Pledge income", "Unpledge CPF"],
                help="Pledge: parent’s income counted. Unpledge: parent parks CPF; bank counts a monthly amount.",
            )
            pledge_monthly = 0.0
            unpledge_cpf = 0.0
            if support == "Pledge income":
                pledge_monthly = st.number_input("Pledged monthly income (SGD)", min_value=0.0, value=0.0, step=100.0)
            elif support == "Unpledge CPF":
                unpledge_cpf = st.number_input("CPF amount unpledged (SGD)", min_value=0.0, value=0.0, step=5000.0)

            monthly_debts = st.number_input("Other monthly debt repayments (SGD)", min_value=0.0, value=0.0, step=50.0)
            cash_cpf = st.number_input("Cash + CPF you can use for down payment (SGD)", min_value=0.0, value=80000.0, step=5000.0)

        c3, c4 = st.columns(2)
        with c3:
            down_pct = st.slider("Minimum down payment assumed (%)", 5, 45, 25, 5)
            interest = st.number_input("Interest rate assumption (%)", min_value=1.0, max_value=6.0, value=3.5, step=0.1)
        with c4:
            safety_pct = st.slider("Safety-net cushion (%) of max budget", 70, 100, 90, 5) / 100.0

        run = st.form_submit_button("Estimate my budget", type="primary")

    if not run:
        return None

    results = {
        "HDB": compute_budget(
            buyer1_income=income1,
            buyer2_income=income2,
            age_youngest=int(age1),
            housing_type="HDB",
            monthly_debts=monthly_debts,
            pledge_monthly=pledge_monthly,
            unpledge_cpf=unpledge_cpf,
            cash_and_cpf=cash_cpf,
            downpayment_pct=down_pct / 100,
            interest_rate=interest / 100,
            safety_net_pct=safety_pct,
        ),
        "Private": compute_budget(
            buyer1_income=income1,
            buyer2_income=income2,
            age_youngest=int(age1),
            housing_type="Private",
            monthly_debts=monthly_debts,
            pledge_monthly=pledge_monthly,
            unpledge_cpf=unpledge_cpf,
            cash_and_cpf=cash_cpf,
            downpayment_pct=down_pct / 100,
            interest_rate=interest / 100,
            safety_net_pct=safety_pct,
        ),
    }

    st.success(f"Assessed income for loan: **{format_currency(results['HDB'].assessed_income_monthly)}** / month")

    col_h, col_p = st.columns(2)
    for col, key in ((col_h, "HDB"), (col_p, "Private")):
        r = results[key]
        with col:
            st.markdown(f"**{key}** (max loan {r.max_loan_tenure_years} yrs)")
            st.metric("Max purchase budget", format_currency(r.max_property_price))
            st.metric("With safety net", format_currency(r.safety_net_price), help=f"{safety_pct*100:.0f}% of max — room for fees & rate rises")
            st.caption(
                f"Loan ~{format_currency(r.max_loan)} · Instalment ~{format_currency(r.max_monthly_installment)}/mo "
                f"(MSR cap {format_currency(r.msr_cap)}, TDSR cap {format_currency(r.tdsr_cap)})"
            )

    st.info(
        "Compare these figures to **median prices** in the market section below. "
        "Grants, ABSD, and legal fees are not deducted — keep a buffer."
    )
    return results


def show_absd_estimator(residency: str, tier: str, suggested_price: float | None = None):
    st.caption("Only needed if you may pay Additional Buyer’s Stamp Duty — skip if this is your first SC home.")
    default_price = suggested_price if suggested_price and suggested_price > 0 else 800_000.0
    price = st.number_input("Expected purchase price for ABSD estimate (SGD)", min_value=0.0, value=float(default_price), step=50_000.0)
    tier_choice = st.selectbox(
        "Property count for ABSD",
        ["1st", "2nd", "3rd+"],
        index=["1st", "2nd", "3rd+"].index(tier if tier in ("1st", "2nd") else "3rd+"),
    )
    if price > 0:
        result = calculate_absd(price, residency, tier_choice)
        st.metric("Estimated ABSD", format_currency(result["amount"]))
        st.write(f"Rate: **{result['rate'] * 100:.0f}%** ({tier_choice} property, {residency})")


def show_location_guide():
    st.markdown(
        "Singapore families often choose location for **school priority**, **daily errands**, and **HDB rules** "
        "(5-year Minimum Occupation Period). New buyers may not know this yet — use your shortlisted address below."
    )

    for title, body in LOCATION_GUIDANCE:
        st.markdown(f"**{title}** — {body}")

    home = st.text_input("Check amenities near this address", value="Tampines Street 61", key="location_home")
    if not st.button("Check location", key="location_check"):
        return

    loc = geocode_place(home)
    if not loc:
        st.warning("Could not find that address.")
        return

    lat, lon = loc
    st.success(f"Location found. Distances are straight-line (km).")

    near_mkt = nearest_places(load_supermarkets(), lat, lon, top_n=8, name_col="name")
    if not near_mkt.empty:
        st.markdown("**Nearest supermarkets**")
        st.dataframe(near_mkt.rename(columns={"name": "Store", "distance_km": "km"}), hide_index=True, use_container_width=True)

    near_moe = moe_primary_near(lat, lon, top_n=12)
    if not near_moe.empty:
        st.markdown("**Nearest primary schools (MOE)** — check **1 km** for P1 priority")
        st.dataframe(
            near_moe.rename(columns={"school_name": "School", "distance_km": "km", "within_1km": "P1 distance"}),
            hide_index=True,
            use_container_width=True,
        )

    ranked = ranked_schools_near(lat, lon, top_n=20)
    if not ranked.empty:
        st.markdown("**Nearest top secondary schools (your ranked list)**")
        st.dataframe(
            ranked.rename(columns={"rank": "Rank", "school": "School", "score": "Score", "distance_km": "km", "within_1km": "Registration distance"}),
            hide_index=True,
            use_container_width=True,
        )

    hawker = load_hawker_centres().dropna(subset=["lat", "lon"])
    near_hawker = nearest_places(hawker, lat, lon, top_n=8, name_col="name")
    if not near_hawker.empty:
        st.markdown("**Nearest hawker centres & markets**")
        st.dataframe(near_hawker.rename(columns={"name": "Centre", "distance_km": "km"}), hide_index=True, use_container_width=True)

    pharma = load_pharmacies().dropna(subset=["lat", "lon"])
    near_ph = nearest_places(pharma, lat, lon, top_n=6, name_col="name")
    if not near_ph.empty:
        st.markdown("**Nearest pharmacies**")
        st.dataframe(near_ph.rename(columns={"name": "Pharmacy", "distance_km": "km"}), hide_index=True, use_container_width=True)


def show_savings_planner():
    df = load_savings_projection()
    if df is None or df.empty:
        st.info("Savings projection unavailable — check RentalIncome.xlsx (Savings sheet).")
        return
    st.caption("Example savings path from **RentalIncome.xlsx** (Savings sheet) — not your personal plan.")
    fig = px.line(df, x="year", y="end_balance", markers=True, title="Example: savings balance over time")
    st.plotly_chart(fig, use_container_width=True)
    st.dataframe(df, hide_index=True, use_container_width=True)


def show_rent_vs_buy_section(scenario: dict | None, filtered_df: pd.DataFrame):
    rent_or_buy = st.session_state.get("rent_or_buy", "Still deciding")
    if scenario:
        st.markdown(
            f"From **RentalIncome.xlsx** (Rental + HomeLoan sheets): condo example at "
            f"**{format_currency(scenario['purchase_price'])}**, loan **{scenario['loan_amount']:,.0f}** "
            f"at **{scenario['interest_rate']*100:.2f}%** / **{scenario['tenure_years']}** years."
        )
        c1, c2, c3 = st.columns(3)
        c1.metric("Monthly rent (yr 1)", format_currency(scenario["starting_monthly_rent"]))
        c2.metric("Monthly mortgage", format_currency(scenario["starting_monthly_instalment"]))
        c3.metric("Rent − mortgage", format_currency(scenario["starting_monthly_rent"] - scenario["starting_monthly_instalment"]))
        timeline = scenario["timeline"].head(15)
        chart_df = timeline.melt(id_vars=["year"], value_vars=["monthly_rent", "monthly_instalment"], var_name="Cost", value_name="SGD")
        chart_df["Cost"] = chart_df["Cost"].map({"monthly_rent": "Rent", "monthly_instalment": "Mortgage"})
        st.plotly_chart(px.line(chart_df, x="year", y="SGD", color="Cost", markers=True), use_container_width=True)
    if not filtered_df.empty and rent_or_buy in ("Buy", "Still deciding"):
        st.write(f"Median price in your filters: **{format_currency(filtered_df['price'].median())}** (HDB + URA transaction data).")


def show_distance_tools(google_distance_fn):
    google_key = os.environ.get("GOOGLE_MAPS_API_KEY")
    schools_df = load_schools()
    school_labels = [f"#{int(r['rank'])} {r['name']}" for _, r in schools_df.iterrows()] if not schools_df.empty else []
    label_to_name = dict(zip(school_labels, schools_df["name"].tolist())) if not schools_df.empty else {}

    t1, t2, t3 = st.tabs(["Commute", "Nearest ranked schools", "Full school list"])
    with t1:
        with st.form("distance"):
            origin = st.text_input("From (home)", value="Tampines Street 61")
            if school_labels and st.radio("To", ["Address", "School from list"], horizontal=True) == "School from list":
                picked = st.selectbox("School", school_labels)
                destination = label_to_name[picked]
            else:
                destination = st.text_input("To (work / MRT / school)", value="Tampines MRT Station")
            if st.form_submit_button("Estimate"):
                if google_key:
                    r = google_distance_fn(origin, destination, google_key)
                    if r:
                        st.success(f"{r['duration_text']} by transit, {r['distance_text']}")
                else:
                    o, d = geocode_place(origin), geocode_place(destination)
                    if o and d:
                        st.write(f"~{haversine_distance(o[0], o[1], d[0], d[1]):.1f} km straight line")
    with t2:
        home = st.text_input("Home address", value="Tampines Street 61", key="dist_schools_home")
        if st.button("Find nearest"):
            loc = geocode_place(home)
            if loc:
                near = ranked_schools_near(loc[0], loc[1], 15)
            else:
                near = pd.DataFrame()
            if not near.empty:
                near = near.copy()
                near["within_1km"] = near["distance_km"].apply(lambda d: "Yes" if d <= 1.0 else "")
                st.dataframe(near, hide_index=True, use_container_width=True)
    with t3:
        if not schools_df.empty:
            d = schools_df.copy()
            d["programmes"] = d.apply(programme_tags, axis=1)
            st.dataframe(d[["rank", "name", "score", "gender", "programmes"]], hide_index=True, height=350)


def show_glossary():
    for term, meaning in GLOSSARY.items():
        st.markdown(f"**{term}** — {meaning}")

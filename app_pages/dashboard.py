from __future__ import annotations

import pandas as pd
import streamlit as st

from components.common import format_currency
from engine.recommendation_engine import recommend_properties
from engine.trend_engine import historical_median_chart, market_trend_chart


def render_dashboard(data: dict[str, pd.DataFrame], state: dict) -> None:
    st.header("Home Dashboard")

    top_row = st.columns(5)
    medians = data.get("price_medians", pd.DataFrame())
    hdb = ec = condo = 0
    if not medians.empty:
        def latest_median_for(kind: str) -> float:
            subset = medians[medians["housing_kind"] == kind]
            if subset.empty:
                return 0
            max_year = subset["year"].max()
            vals = subset[subset["year"] == max_year]["median_price"]
            if vals.empty:
                return 0
            v = vals.mean()
            return float(v) if pd.notna(v) else 0

        hdb = latest_median_for("HDB")
        ec = latest_median_for("EC")
        condo = latest_median_for("Condo")

    top_row[0].metric("Latest HDB median", format_currency(hdb))
    top_row[1].metric("Latest EC median", format_currency(ec))
    top_row[2].metric("Latest Condo median", format_currency(condo))
    top_row[3].metric("Saved properties", len(state.get("saved_properties", [])))
    top_row[4].metric("Saved scenarios", len(state.get("saved_scenarios", [])))

    st.markdown("---")
    st.subheader("Market snapshot")
    st.markdown("Median price history for HDB, EC and Condo across the full dataset. Dataset for condo and landed only starts from 2010.")
    st.plotly_chart(historical_median_chart(data.get("transactions", pd.DataFrame())), use_container_width=True)

    # Only show budget recommendations if the user has run the affordability assessment
    if state.get("budget_calculated", False):
        budget = state.get("budget")
        recommendations = recommend_properties(data.get("transactions", pd.DataFrame()), budget)
        if recommendations:
            st.subheader("Recommended properties for your budget")
            for rec in recommendations:
                st.write(f"- {rec.get('street_name','')} in {rec.get('area_name','')} ({rec.get('housing_kind','')}) — {format_currency(rec.get('latest_price'))}")

    if saved := state.get("saved_properties", []):
        st.markdown("---")
        st.subheader("Recently saved properties")
        for item in saved[:5]:
            st.write(f"• {item}")

    if scenarios := state.get("saved_scenarios", []):
        st.markdown("---")
        st.subheader("Recent saved scenarios")
        for scenario in scenarios[-3:]:
            st.write(f"• {scenario.get('name', 'Untitled scenario')}")

from __future__ import annotations

import pandas as pd
import streamlit as st

from components.common import format_currency
from engine.recommendation_engine import recommend_properties
from engine.trend_engine import market_trend_chart


def render_dashboard(data: dict[str, pd.DataFrame], state: dict) -> None:
    st.header("Home Dashboard")

    top_row = st.columns(4)
    medians = data.get("price_medians", pd.DataFrame())
    if not medians.empty:
        latest = medians[medians["year"] == medians["year"].max()]
        hdb = latest[latest["housing_kind"] == "HDB"]["median_price"].mean()
        condo = latest[latest["housing_kind"] == "Condo"]["median_price"].mean()
    else:
        hdb = condo = 0

    top_row[0].metric("Latest HDB median", format_currency(hdb))
    top_row[1].metric("Latest Condo median", format_currency(condo))
    top_row[2].metric("Saved properties", len(state.get("saved_properties", [])))
    top_row[3].metric("Saved scenarios", len(state.get("saved_scenarios", [])))

    st.markdown("---")
    st.subheader("Quick actions")
    cards = st.columns(4)
    actions = [
        ("Calculate Budget", "Go to Affordability"),
        ("Search HDB/Condo", "Buy Property"),
        ("Find Rental", "Rent Property"),
        ("Explore Schools", "School Finder"),
    ]
    for idx, (label, value) in enumerate(actions):
        col = cards[idx]
        if col.button(label, key=f"dashboard_action_{idx}"):
            state["selected_page"] = value
            state["pending_page"] = value
        col.write(value)

    st.markdown("---")
    st.subheader("Market snapshot")
    if not medians.empty:
        st.plotly_chart(market_trend_chart(medians), use_container_width=True)

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

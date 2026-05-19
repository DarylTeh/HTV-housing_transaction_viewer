import base64
import json
from typing import Any

import pandas as pd
import streamlit as st

from pages.affordability import render_affordability_page
from pages.analytics import render_analytics_page
from pages.buy import render_buy_page
from pages.compare import render_compare_page
from pages.dashboard import render_dashboard
from pages.maps import render_map_explorer
from pages.rent import render_rent_page
from pages.saved import render_saved_page
from pages.sell import render_sell_page
from pages.schools import render_schools_page
from pages.trends import render_trends_page
from processed_data import (
    load_hawker_centres,
    load_price_medians,
    load_rent_vs_buy_timeline,
    load_schools_ranked_geocoded,
    load_supermarkets,
    load_transactions,
)

st.set_page_config(
    page_title="Singapore Property Intelligence",
    page_icon="🏠",
    layout="wide",
    initial_sidebar_state="expanded",
)

NAVIGATION = [
    "Home Dashboard",
    "Affordability",
    "Buy Property",
    "Rent Property",
    "Sell Property",
    "Project Analytics",
    "Map Explorer",
    "School Finder",
    "Rental Yield",
    "Market Trends",
    "Scenario Comparison",
    "Saved Properties",
    "Saved Scenarios",
]

INTEREST_TYPES = ["Buy", "Rent", "Sell", "Invest"]

PAGE_RENDERERS = {
    "Home Dashboard": render_dashboard,
    "Affordability": render_affordability_page,
    "Buy Property": render_buy_page,
    "Rent Property": render_rent_page,
    "Sell Property": render_sell_page,
    "Project Analytics": render_analytics_page,
    "Map Explorer": render_map_explorer,
    "School Finder": render_schools_page,
    "Rental Yield": render_rent_page,
    "Market Trends": render_trends_page,
    "Scenario Comparison": render_compare_page,
    "Saved Properties": render_saved_page,
    "Saved Scenarios": render_saved_page,
}


def init_session_state() -> None:
    defaults = {
        "saved_properties": [],
        "saved_scenarios": [],
        "nav_index": 0,
        "page_anchor": None,
        "budget": 1_100_000,
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


@st.cache_data
def load_app_data() -> dict[str, pd.DataFrame]:
    return {
        "transactions": load_transactions(),
        "price_medians": load_price_medians(),
        "schools_geocoded": load_schools_ranked_geocoded(),
        "supermarkets": load_supermarkets(),
        "hawker_centres": load_hawker_centres(),
        "rent_vs_buy": load_rent_vs_buy_timeline(),
    }


def render_global_sidebar(state: dict[str, Any]) -> str:
    st.sidebar.title("Singapore Property Intelligence")
    st.sidebar.markdown(
        "Select your user intent and jump into the experience that matters most for your next property decision."
    )

    interest = st.sidebar.radio("Interest type", INTEREST_TYPES, index=INTEREST_TYPES.index(state.get("interest_type", "Buy")))
    state["interest_type"] = interest

    page = st.sidebar.selectbox("Global navigation", NAVIGATION, index=state.get("nav_index", 0))
    state["nav_index"] = NAVIGATION.index(page)

    if st.sidebar.button("Clear saved lists"):
        state["saved_properties"] = []
        state["saved_scenarios"] = []
        st.sidebar.success("Saved properties and scenarios cleared.")

    st.sidebar.markdown("---")
    st.sidebar.write("**Need ideas?**")
    if st.sidebar.button("Search HDB" ):
        state["page_anchor"] = "Buy Property"
    if st.sidebar.button("Explore schools"):
        state["page_anchor"] = "School Finder"
    if st.sidebar.button("View market trends"):
        state["page_anchor"] = "Market Trends"

    return page


def main() -> None:
    init_session_state()
    data = load_app_data()

    page = render_global_sidebar(st.session_state)
    if st.session_state.get("page_anchor") in NAVIGATION:
        page = st.session_state.pop("page_anchor")

    st.title("Singapore Property Intelligence Platform")
    st.markdown(
        "A modern, non-linear property decision workspace built for budget, school search, rental insights, market analytics and quick comparison."
    )
    st.markdown(f"**Mode:** {st.session_state['interest_type']}")
    st.markdown("---")

    renderer = PAGE_RENDERERS.get(page)
    if renderer:
        renderer(data, st.session_state)
    else:
        st.warning("Page unavailable. Please select another experience from the sidebar.")


if __name__ == "__main__":
    main()

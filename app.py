import base64
import json
from typing import Any

import pandas as pd
import streamlit as st

from app_pages.affordability import render_affordability_page
from app_pages.analytics import render_analytics_page
from app_pages.buy import render_buy_page
from app_pages.compare import render_compare_page
from app_pages.dashboard import render_dashboard
from app_pages.maps import render_map_explorer
from app_pages.rent import render_rent_page
from app_pages.saved import render_saved_page
from app_pages.sell import render_sell_page
from app_pages.schools import render_schools_page
from app_pages.trends import render_trends_page
from processed_data import (
    load_hawker_centres,
    load_price_medians,
    load_rent_vs_buy_timeline,
    load_schools_ranked_geocoded,
    load_supermarkets,
    load_transactions,
)

st.set_page_config(
    page_title="PropHub - Your Property Guide",    
    page_icon="logo_topbottom.jpg",
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
    "Market Trends",
    "Scenario Comparison",
    "Saved Properties",
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
    "Market Trends": render_trends_page,
    "Scenario Comparison": render_compare_page,
    "Saved Properties": render_saved_page,
}


def init_session_state() -> None:
    defaults = {
        "saved_properties": [],
        "saved_scenarios": [],
        "selected_page": NAVIGATION[0],
        # `budget` is set when the user runs the Affordability assessment.
        "budget_calculated": False,
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
    render_sidebar_logo("logo_rightleft.jpg")
    st.sidebar.markdown(
        "Select your user intent and jump into the experience that matters most for your next property decision."
    )

    interest = st.sidebar.radio("Interest type", INTEREST_TYPES, index=INTEREST_TYPES.index(state.get("interest_type", "Buy")))
    state["interest_type"] = interest

    current_page = state.get("selected_page", NAVIGATION[0])
    if "nav_page_select" not in st.session_state:
        st.session_state["nav_page_select"] = current_page
    page = st.sidebar.selectbox(
        "Global navigation",
        NAVIGATION,
        index=NAVIGATION.index(current_page) if current_page in NAVIGATION else 0,
        key="nav_page_select",
    )
    if page != state.get("selected_page"):
        state["selected_page"] = page

    if st.sidebar.button("Clear saved lists", key="clear_saved_lists"):
        state["saved_properties"] = []
        state["saved_scenarios"] = []
        st.sidebar.success("Saved properties and scenarios cleared.")

    return state["selected_page"]

def render_sidebar_logo(image_path: str) -> None:
    with open(image_path, "rb") as image_file:
        encoded = base64.b64encode(image_file.read()).decode()

    st.sidebar.markdown(
        f"""
        <div style="text-align: center; padding-bottom: 1rem;">
            <img src="data:image/png;base64,{encoded}" width="220">
        </div>
        """,
        unsafe_allow_html=True,
    )

def main() -> None:
    init_session_state()
    data = load_app_data()

    page = render_global_sidebar(st.session_state)

    st.title("Property Hub")
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

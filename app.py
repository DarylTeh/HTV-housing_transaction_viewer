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
from app_pages.saved import render_saved_page
from app_pages.sell import render_sell_page
from app_pages.schools import render_schools_page
from app_pages.trends import render_trends_page
from processed_data import (
    load_hawker_centres,
    load_price_medians,
    load_rent_vs_buy_timeline,
    load_supermarkets,
    load_transactions,
    load_schools_master,
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
    "Find Properties",
    "Recent Transactions",
    "Project Analytics",
    "Map Explorer",
    "School Finder",
    "Market Trends",
    "Scenario Comparison",
    "Saved Properties",
]

PAGE_RENDERERS = {
    "Home Dashboard": render_dashboard,
    "Affordability": render_affordability_page,
    "Find Properties": render_buy_page,
    "Recent Transactions": render_sell_page,
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
        "schools_geocoded": load_schools_master(),
        "supermarkets": load_supermarkets(),
        "hawker_centres": load_hawker_centres(),
        "rent_vs_buy": load_rent_vs_buy_timeline(),
    }


def render_global_sidebar(state: dict[str, Any]) -> str:
    render_sidebar_logo("logo_rightleft.jpg")
    st.sidebar.markdown(
        """
        <style>
        section[data-testid="stSidebar"] {
            background-color: #f8f9fa !important;
        }
        section[data-testid="stSidebar"] .css-1avcm0n,
        section[data-testid="stSidebar"] .css-1d391kg,
        section[data-testid="stSidebar"] .css-1pqm26a,
        section[data-testid="stSidebar"] .css-1d0f0j4 {
            background-color: transparent !important;
        }
        .sidebar-logo-container {
            background-color: transparent !important;
            padding-bottom: 1rem;
        }
        .sidebar-logo-container img {
            background-color: transparent !important;
            display: block;
            margin: 0 auto;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )
    st.sidebar.markdown(
        "Use the global navigation menu below to access every feature of the app. "
        "Each page is designed to help you understand the market, compare properties, "
        "and manage your saved options."
    )

    current_page = state.get("selected_page", NAVIGATION[0])
    if "nav_page_select" not in st.session_state:
        st.session_state["nav_page_select"] = current_page
    page = st.sidebar.selectbox(
        "Global navigation",
        NAVIGATION,
        index=NAVIGATION.index(current_page) if current_page in NAVIGATION else 0,
        key="nav_page_select",
    )

    st.sidebar.markdown(
        """
        **Feature guide**
        - **Home Dashboard**: overview metrics, quick actions and saved items.
        - **Affordability**: calculate your budget and compare financing options.
        - **Find Properties**: search and compare HDB and condo transaction data.
        - **Recent Transactions**: review market medians and recent pricing trends.
        - **Project Analytics**: inspect project-level sales and market performance.
        - **Map Explorer**: explore property data on an interactive map.
        - **School Finder**: search schools near areas and review ranked options.
        - **Market Trends**: view pricing trends and transaction volume charts.
        - **Scenario Comparison**: compare properties and scenarios side by side.
        - **Saved Properties**: manage your saved properties and scenarios.
        """
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
        <div class="sidebar-logo-container" style="text-align: center; padding-bottom: 1rem;">
            <img src="data:image/png;base64,{encoded}" width="220" style="background: transparent;" />
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
        "A modern, non-linear property decision workspace built for budget, school search, market analytics and quick comparison."
    )
    st.markdown("---")

    renderer = PAGE_RENDERERS.get(page)
    if renderer:
        renderer(data, st.session_state)
    else:
        st.warning("Page unavailable. Please select another experience from the sidebar.")


if __name__ == "__main__":
    main()

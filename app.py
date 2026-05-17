import os

import pandas as pd
import plotly.express as px
import streamlit as st

from data_sources import DATA_SOURCE_MODE, load_all_transactions
from geo_utils import geocode_place, google_distance
from processed_data import ranked_schools_near
from property_groups import HOUSING_KINDS, default_sizes_for_kinds, size_options_for_kinds
from rental_model import load_rent_vs_buy_scenario
from schools import load_schools, programme_tags
from story import (
    BUYER_TIPS,
    absd_tier_from_story,
    apply_story_filters,
    default_kinds_from_story,
    init_story_state,
    render_journey_picker,
    render_story_step,
)
from ui_sections import (
    format_currency,
    show_absd_estimator,
    show_budget_calculator,
    show_distance_tools,
    show_glossary,
    show_location_guide,
    show_rent_vs_buy_section,
    show_savings_planner,
)

st.set_page_config(
    page_title="Singapore Housing Journey",
    page_icon="🏘️",
    layout="wide",
)

DEFAULT_YEAR_WINDOW = 5


@st.cache_data
def load_app_data():
    return load_all_transactions()


@st.cache_data
def load_school_list():
    return load_schools()


@st.cache_data
def schools_near_home(home_query: str, top_n: int = 15):
    home = geocode_place(home_query)
    if not home:
        return None, pd.DataFrame()
    return home, ranked_schools_near(home[0], home[1], top_n)


@st.cache_data
def google_distance_cached(origin: str, destination: str, api_key: str):
    return google_distance(origin, destination, api_key)


def default_year_range(year_options: list[int], window: int = DEFAULT_YEAR_WINDOW) -> tuple[int, int]:
    if not year_options:
        return 2020, 2025
    end = year_options[-1]
    return max(year_options[0], end - window + 1), end


def build_trend_chart(df, group_col: str, start_year, end_year):
    filtered = df[(df["year"] >= start_year) & (df["year"] <= end_year)].copy()
    if filtered.empty or group_col not in filtered.columns:
        return None
    target = filtered.groupby([group_col, "year"], as_index=False)["price"].median()
    return px.line(
        target,
        x="year",
        y="price",
        color=group_col,
        markers=True,
        labels={"price": "Median Price (SGD)", "year": "Year"},
        title=f"Median price trend ({start_year}–{end_year})",
    )


def calculate_percent_gain(df, group_col: str, start_year, end_year, top_n=10):
    pivot = df[df["year"].isin([start_year, end_year])].copy()
    if pivot.empty or group_col not in pivot.columns:
        return pd.DataFrame()
    medians = pivot.groupby([group_col, "year"], as_index=False)["price"].median()
    start = medians[medians["year"] == start_year].set_index(group_col)["price"]
    end = medians[medians["year"] == end_year].set_index(group_col)["price"]
    joined = pd.DataFrame({"start_price": start, "end_price": end}).dropna()
    joined["gain_pct"] = (joined["end_price"] - joined["start_price"]) / joined["start_price"] * 100
    return joined.reset_index().sort_values("gain_pct", ascending=False).head(top_n)


def render_sidebar_controls(df):
    st.sidebar.header("Your profile")
    st.session_state.residency = st.sidebar.selectbox(
        "Residency",
        ["Singapore Citizen", "Permanent Resident", "Foreigner"],
        index=["Singapore Citizen", "Permanent Resident", "Foreigner"].index(st.session_state.residency),
    )
    st.session_state.own_hdb = st.sidebar.selectbox("Own HDB?", ["No", "Yes"], index=["No", "Yes"].index(st.session_state.own_hdb))
    tip = BUYER_TIPS.get((st.session_state.residency, st.session_state.own_hdb))
    if tip:
        st.sidebar.info(tip)

    st.session_state.rent_or_buy = st.sidebar.selectbox(
        "Rent or buy?",
        ["Rent", "Buy", "Still deciding"],
        index=["Rent", "Buy", "Still deciding"].index(st.session_state.rent_or_buy),
    )
    st.session_state.first_property = st.sidebar.selectbox(
        "First property in Singapore?",
        ["Yes — first property", "No — I already own property"],
        index=0 if st.session_state.first_property.startswith("Yes") else 1,
    )

    st.sidebar.markdown("**What are you looking at?**")
    kind_options = ["Condo", "Landed"] if st.session_state.residency == "Foreigner" else HOUSING_KINDS
    default_kinds = [k for k in default_kinds_from_story() if k in kind_options]
    housing_kinds = st.sidebar.multiselect("Home type", kind_options, default=default_kinds or kind_options[:2])

    size_options = size_options_for_kinds(df, housing_kinds)
    default_sizes = [s for s in default_sizes_for_kinds(df, housing_kinds) if s in size_options]
    size_choices = st.sidebar.multiselect("Size (rooms & sqft)", size_options, default=default_sizes)

    area_labels = sorted(df["area_name"].dropna().unique()) if "area_name" in df.columns else sorted(df["town"].dropna().unique())
    selected_areas = st.sidebar.multiselect("Areas", area_labels, default=[])

    year_options = sorted(df["year"].dropna().astype(int).unique())
    yr_start, yr_end = default_year_range(year_options)
    start_year, end_year = st.sidebar.select_slider("Year range", options=year_options, value=(yr_start, yr_end))

    if st.sidebar.button("Restart guided journey"):
        st.session_state.journey_mode = None
        st.session_state.story_step = 0
        st.session_state.story_complete = False
        st.rerun()

    return housing_kinds, size_choices, selected_areas, start_year, end_year


def filter_dataframe(df, housing_kinds, size_choices, selected_areas):
    filtered = apply_story_filters(df)
    if housing_kinds:
        filtered = filtered[filtered["housing_kind"].isin(housing_kinds)]
    if size_choices:
        filtered = filtered[filtered["size_label"].isin(size_choices)]
    if selected_areas and "area_name" in filtered.columns:
        filtered = filtered[filtered["area_name"].isin(selected_areas)]
    return filtered


def main():
    init_story_state()

    st.title("🏡 Singapore Housing Journey")
    st.write(
        "A step-by-step guide for **first-time buyers**: estimate your **loan budget**, "
        "see real **HDB & private prices**, and learn what **location** means for schools and daily life."
    )
    st.caption("Data: pre-built **processed CSVs** on GitHub (fast load) · source: HDB, URA, schools, amenities")

    with st.spinner("Loading data…"):
        df = load_app_data()

    if df.empty:
        st.error("No transaction data. Add xlsx files under `data/` or run `python scripts/update_data.py`.")
        return

    if st.session_state.journey_mode is None:
        render_journey_picker()
        return

    if st.session_state.journey_mode == "guided" and not st.session_state.story_complete:
        render_story_step()
        st.divider()

    housing_kinds, size_choices, selected_areas, start_year, end_year = render_sidebar_controls(df)
    filtered = filter_dataframe(df, housing_kinds, size_choices, selected_areas)

    # --- Always visible: budget + market ---
    st.markdown("## Step 1 — Your loan budget")
    budget_results = show_budget_calculator(st.session_state.residency)
    suggested = None
    if budget_results:
        focus = housing_kinds[0] if len(housing_kinds) == 1 else "HDB"
        suggested = budget_results.get(focus, budget_results["HDB"]).safety_net_price

    st.markdown("## Step 2 — Market prices (real transactions)")
    st.write(f"**{len(filtered):,}** sales match your filters · all data **{len(df):,}** ({int(df['year'].min())}–{int(df['year'].max())})")
    m1, m2, m3 = st.columns(3)
    m1.metric("HDB sales", f"{len(df[df['dataset'] == 'HDB Resale']):,}")
    m2.metric("Private sales", f"{len(df[df['dataset'] == 'Private Property']):,}")
    m3.metric("Median (your filters)", format_currency(filtered["price"].median()) if not filtered.empty else "—")

    if filtered.empty:
        st.warning("No sales match — widen home type or area filters in the sidebar.")
    else:
        display_col = "area_name" if "area_name" in filtered.columns else "town"
        top = (
            filtered.groupby(["housing_kind", "size_label", display_col], as_index=False)["price"]
            .median()
            .sort_values("price", ascending=False)
            .head(12)
        )
        st.dataframe(
            top.rename(columns={"housing_kind": "Type", "size_label": "Size", display_col: "Area", "price": "Median"}),
            use_container_width=True,
            hide_index=True,
        )
        group_col = display_col if selected_areas else "size_label"
        chart = build_trend_chart(filtered, group_col, start_year, end_year)
        if chart:
            st.plotly_chart(chart, use_container_width=True)
        gain = calculate_percent_gain(filtered, group_col, start_year, end_year)
        if not gain.empty and start_year != end_year:
            st.dataframe(gain, use_container_width=True, hide_index=True)

    # --- Collapsible sections ---
    with st.expander("📍 Location guide — schools (1 km), supermarkets, policies", expanded=False):
        show_location_guide()

    if st.session_state.rent_or_buy in ("Rent", "Still deciding"):
        with st.expander("🏠 Rent vs buy — worked example", expanded=False):
            show_rent_vs_buy_section(load_rent_vs_buy_scenario(), filtered)

    with st.expander("💰 Savings example (from RentalIncome workbook)", expanded=False):
        show_savings_planner()

    with st.expander("📋 ABSD stamp duty estimator (optional)", expanded=False):
        tier = absd_tier_from_story() if st.session_state.first_property.startswith("Yes") else "2nd"
        if st.session_state.first_property.startswith("No"):
            tier = st.selectbox("ABSD tier", ["2nd", "3rd+"], key="absd_tier_sel") or "2nd"
        show_absd_estimator(st.session_state.residency, tier, suggested_price=suggested)

    with st.expander("🚇 Commute & school distances", expanded=False):
        show_distance_tools(google_distance_cached)

    with st.expander("📚 Glossary", expanded=False):
        show_glossary()

    with st.expander("📄 Policy notes", expanded=False):
        if os.path.exists("policy_notes.md"):
            try:
                with open("policy_notes.md", "r", encoding="utf-8") as f:
                    st.markdown(f.read())
            except UnicodeDecodeError:
                st.warning("Could not read policy_notes.md.")
        else:
            st.write("Add policy_notes.md for extra eligibility notes.")


if __name__ == "__main__":
    main()

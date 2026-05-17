import math
import os

import pandas as pd
import plotly.express as px
import requests
import streamlit as st

from data_sources import DATA_SOURCE_MODE, load_all_transactions
from housing_constants import GLOSSARY, calculate_absd, enrich_area_labels
from rental_model import load_rent_vs_buy_scenario
from story import (
    BUYER_TIPS,
    absd_tier_from_story,
    apply_story_filters,
    init_story_state,
    render_journey_picker,
    render_story_step,
    story_default_property_types,
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
def load_rental_scenario():
    return load_rent_vs_buy_scenario()


@st.cache_data
def geocode_place(query: str):
    if not query:
        return None
    url = "https://nominatim.openstreetmap.org/search"
    params = {"q": query + ", Singapore", "format": "json", "limit": 1}
    response = requests.get(url, params=params, headers={"User-Agent": "SG-Housing-Viewer/1.0"}, timeout=20)
    response.raise_for_status()
    result = response.json()
    if not result:
        return None
    return float(result[0]["lat"]), float(result[0]["lon"])


@st.cache_data
def google_distance(origin: str, destination: str, api_key: str):
    if not origin or not destination or not api_key:
        return None
    url = "https://maps.googleapis.com/maps/api/distancematrix/json"
    params = {"origins": origin, "destinations": destination, "key": api_key, "mode": "transit"}
    response = requests.get(url, params=params, timeout=20)
    response.raise_for_status()
    data = response.json()
    if data.get("status") != "OK":
        return None
    element = data["rows"][0]["elements"][0]
    if element.get("status") != "OK":
        return None
    return {"distance_text": element["distance"]["text"], "duration_text": element["duration"]["text"]}


def haversine_distance(lat1, lon1, lat2, lon2):
    rad = math.radians
    dlat = rad(lat2 - lat1)
    dlon = rad(lon2 - lon1)
    a = math.sin(dlat / 2) ** 2 + math.cos(rad(lat1)) * math.cos(rad(lat2)) * math.sin(dlon / 2) ** 2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return 6371 * c


def format_currency(value):
    if pd.isna(value):
        return "-"
    return f"${value:,.0f}"


def default_year_range(year_options: list[int], window: int = DEFAULT_YEAR_WINDOW) -> tuple[int, int]:
    if not year_options:
        return 2020, 2025
    end = year_options[-1]
    start = max(year_options[0], end - window + 1)
    return start, end


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
        labels={"price": "Median Price (SGD)", "year": "Year", group_col: "Group"},
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


def show_glossary():
    with st.expander("📚 Glossary — key terms"):
        for term, meaning in GLOSSARY.items():
            st.markdown(f"**{term}** — {meaning}")


def show_absd_estimator(residency: str, tier: str):
    st.subheader("ABSD estimator (stamp duty)")
    st.caption("Illustrative rates only — confirm with IRAS or a lawyer before buying.")
    price = st.number_input("Purchase price (SGD)", min_value=0.0, value=1_000_000.0, step=50_000.0, key="absd_price")
    tier_choice = st.selectbox(
        "Property count for ABSD",
        ["1st", "2nd", "3rd+"],
        index=["1st", "2nd", "3rd+"].index(tier if tier in ("1st", "2nd") else "3rd+"),
        key="absd_tier",
    )
    if price > 0:
        result = calculate_absd(price, residency, tier_choice)
        st.metric("Estimated ABSD", format_currency(result["amount"]))
        st.write(f"Rate applied: **{result['rate'] * 100:.0f}%** ({tier_choice} property for {residency})")


def show_rent_vs_buy_section(scenario: dict | None, filtered_df: pd.DataFrame):
    st.subheader("Rent vs buy")
    rent_or_buy = st.session_state.get("rent_or_buy", "Still deciding")

    if scenario:
        st.markdown(
            f"**Worked example** from your `RentalIncome.xlsx` workbook: "
            f"a **{scenario['property_label']}** bought at **{format_currency(scenario['purchase_price'])}** "
            f"with a **{scenario['loan_amount']:,.0f}** loan at **{scenario['interest_rate']*100:.2f}%** over "
            f"**{scenario['tenure_years']}** years."
        )
        c1, c2, c3 = st.columns(3)
        c1.metric("Example monthly rent (year 1)", format_currency(scenario["starting_monthly_rent"]))
        c2.metric("Example monthly mortgage", format_currency(scenario["starting_monthly_instalment"]))
        diff = scenario["starting_monthly_rent"] - scenario["starting_monthly_instalment"]
        c3.metric("Rent − mortgage (month 1)", format_currency(diff))

        timeline = scenario["timeline"].head(15)
        chart_df = timeline.melt(id_vars=["year"], value_vars=["monthly_rent", "monthly_instalment"], var_name="Cost", value_name="SGD")
        chart_df["Cost"] = chart_df["Cost"].map({"monthly_rent": "Rent", "monthly_instalment": "Mortgage"})
        fig = px.line(chart_df, x="year", y="SGD", color="Cost", markers=True, title="Example: rent vs mortgage over 15 years")
        st.plotly_chart(fig, use_container_width=True)
        st.caption(
            "This model includes rent growth and property appreciation assumptions from the spreadsheet. "
            "Your real costs depend on location, flat type, and loan package."
        )
    else:
        st.info("Add `data/RentalIncome.xlsx` to enable the rent-vs-buy worked example.")

    if not filtered_df.empty and rent_or_buy in ("Buy", "Still deciding"):
        med = filtered_df["price"].median()
        st.write(
            f"For your **filtered purchase data**, the median transaction price is **{format_currency(med)}**. "
            "Compare this with your savings, grants, and loan eligibility."
        )
    if rent_or_buy == "Rent":
        st.write(
            "When renting, you do not build equity, but you avoid down payment, stamp duty, and maintenance. "
            "Use the worked example above to compare monthly cash outlay."
        )


def show_affordability_calculator(default_price: float = 600_000.0):
    st.subheader("Affordability calculator")
    st.write("Rough MSR (HDB) vs TDSR (private) check — not a bank approval.")
    with st.form("affordability"):
        gross_income = st.number_input("Monthly gross income (SGD)", min_value=0.0, value=5000.0, step=100.0)
        property_price = st.number_input("Property price (SGD)", min_value=0.0, value=float(default_price), step=10000.0)
        downpayment_pct = st.slider("Down payment (%)", min_value=5, max_value=50, value=25, step=5)
        interest_rate = st.number_input("Annual loan interest rate (%)", min_value=0.0, value=3.5, step=0.1)
        loan_term_years = st.selectbox("Loan tenure (years)", [15, 20, 25, 30])
        other_monthly_debt = st.number_input("Other monthly debt payments (SGD)", min_value=0.0, value=0.0, step=50.0)
        submitted = st.form_submit_button("Calculate")

    if submitted:
        principal = property_price * (1 - downpayment_pct / 100)
        monthly_rate = interest_rate / 100 / 12
        months = loan_term_years * 12
        if monthly_rate > 0:
            monthly_payment = principal * monthly_rate / (1 - (1 + monthly_rate) ** -months)
        else:
            monthly_payment = principal / months
        msr_limit = gross_income * 0.30
        tdsr_limit = gross_income * 0.55
        remaining_tdsr = max(tdsr_limit - other_monthly_debt, 0)

        st.metric("Estimated monthly loan payment", format_currency(monthly_payment))
        st.write(f"Maximum HDB MSR allowance: {format_currency(msr_limit)} / month")
        if monthly_payment <= msr_limit:
            st.success("Within HDB MSR guideline (30%).")
        else:
            st.error("Above HDB MSR guideline (30%).")
        st.write(f"Maximum private TDSR allowance: {format_currency(remaining_tdsr)} / month after other debts")
        if monthly_payment <= remaining_tdsr:
            st.success("Within private TDSR guideline (55%).")
        else:
            st.warning("May exceed private TDSR guideline (55%).")


def show_distance_tools():
    st.subheader("Commute estimate")
    google_key = os.environ.get("GOOGLE_MAPS_API_KEY")
    with st.form("distance"):
        origin = st.text_input("Address near the home", value="Tampines Street 61")
        destination = st.text_input("Destination (work / school / MRT)", value="Tampines MRT Station")
        submitted = st.form_submit_button("Estimate")

    if submitted:
        if google_key:
            result = google_distance(origin, destination, google_key)
            if result:
                st.success(f"Transit: {result['duration_text']}, {result['distance_text']}.")
            else:
                st.warning("Google Distance Matrix returned no result.")
        else:
            st.info("No Google Maps API key — using straight-line distance (OpenStreetMap).")
            origin_loc = geocode_place(origin)
            destination_loc = geocode_place(destination)
            if origin_loc and destination_loc:
                km = haversine_distance(origin_loc[0], origin_loc[1], destination_loc[0], destination_loc[1])
                st.write(f"Approximate distance: **{km:.1f} km** (straight line).")
            else:
                st.warning("Could not geocode one of the locations.")


def render_sidebar_controls(df, property_options):
    st.sidebar.header("Your profile")
    st.session_state.residency = st.sidebar.selectbox(
        "Residency",
        ["Singapore Citizen", "Permanent Resident", "Foreigner"],
        index=["Singapore Citizen", "Permanent Resident", "Foreigner"].index(st.session_state.residency),
    )
    st.session_state.own_hdb = st.sidebar.selectbox(
        "Own HDB?",
        ["No", "Yes"],
        index=["No", "Yes"].index(st.session_state.own_hdb),
    )
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

    defaults = story_default_property_types(df, property_options)
    property_choices = st.sidebar.multiselect("Property types", property_options, default=defaults)

    area_labels = sorted(df["area_name"].dropna().unique()) if "area_name" in df.columns else sorted(df["town"].dropna().unique())
    selected_areas = st.sidebar.multiselect("Areas (towns / districts)", area_labels, default=[])

    year_options = sorted(df["year"].dropna().astype(int).unique())
    yr_start, yr_end = default_year_range(year_options)
    start_year, end_year = st.sidebar.select_slider(
        "Year range (last 5 years by default)",
        options=year_options,
        value=(yr_start, yr_end),
    )

    if st.sidebar.button("Restart guided journey"):
        st.session_state.journey_mode = None
        st.session_state.story_step = 0
        st.session_state.story_complete = False
        st.rerun()

    return property_choices, selected_areas, start_year, end_year


def filter_dataframe(df, property_choices, selected_areas):
    filtered = apply_story_filters(df)
    if property_choices:
        filtered = filtered[filtered["property_type"].isin(property_choices)]
    if selected_areas and "area_name" in filtered.columns:
        filtered = filtered[filtered["area_name"].isin(selected_areas)]
    return filtered


def main():
    init_story_state()

    st.title("🏡 Singapore Housing Journey")
    st.write(
        "Learn how HDB and private housing prices move in Singapore — then check affordability, "
        "stamp duty, and rent-vs-buy in plain language."
    )

    mode_label = "local Excel workbooks" if DATA_SOURCE_MODE == "local_xlsx" else "live government API"
    st.caption(f"Data: **{mode_label}** · Toggle via `HTV_DATA_SOURCE` in `data_sources.py`")

    with st.spinner("Loading transaction data…"):
        df = load_app_data()

    if df.empty:
        st.error("No data found. Place xlsx files in `data/` or run `python scripts/update_data.py`.")
        return

    if st.session_state.journey_mode is None:
        render_journey_picker()
        return

    if st.session_state.journey_mode == "guided" and not st.session_state.story_complete:
        render_story_step()
        st.divider()

    property_options = sorted(df["property_type"].dropna().unique())
    property_choices, selected_areas, start_year, end_year = render_sidebar_controls(df, property_options)
    filtered = filter_dataframe(df, property_choices, selected_areas)

    show_glossary()

    st.markdown("## Market snapshot")
    st.write(f"**{len(df):,}** transactions ({int(df['year'].min())}–{int(df['year'].max())}) · **{len(filtered):,}** after your filters")

    m1, m2, m3 = st.columns(3)
    m1.metric("HDB resale", f"{len(df[df['dataset'] == 'HDB Resale']):,}")
    m2.metric("Private", f"{len(df[df['dataset'] == 'Private Property']):,}")
    m3.metric("Median (filtered)", format_currency(filtered["price"].median()) if not filtered.empty else "—")

    rent_goal = st.session_state.rent_or_buy
    show_rent_tab = rent_goal in ("Rent", "Still deciding")
    tab_labels = ["Trends & prices"]
    if show_rent_tab:
        tab_labels.append("Rent vs buy")
    tab_labels.extend(["ABSD & affordability", "Commute", "Policy notes"])
    tab_objects = st.tabs(tab_labels)
    ti = 0

    with tab_objects[ti]:
        ti += 1
        if filtered.empty:
            st.warning("No records match your filters — broaden property types or areas.")
        else:
            display_col = "area_name" if "area_name" in filtered.columns else "town"
            top_summary = (
                filtered.groupby(["property_type", display_col], as_index=False)["price"]
                .median()
                .sort_values("price", ascending=False)
                .head(12)
            )
            st.subheader("Highest median prices (your selection)")
            st.dataframe(
                top_summary.rename(columns={"property_type": "Type", display_col: "Area", "price": "Median (SGD)"}),
                use_container_width=True,
            )

            group_col = display_col if selected_areas else "property_type"
            chart = build_trend_chart(filtered, group_col, start_year, end_year)
            if chart:
                st.plotly_chart(chart, use_container_width=True)

            gain_df = calculate_percent_gain(filtered, group_col, start_year, end_year)
            if not gain_df.empty and start_year != end_year:
                st.subheader(f"Price change {start_year} → {end_year}")
                st.dataframe(gain_df, use_container_width=True)

            if "region" in filtered.columns and filtered["dataset"].eq("Private Property").any():
                by_region = (
                    filtered[filtered["dataset"] == "Private Property"]
                    .groupby("region", as_index=False)["price"]
                    .median()
                    .sort_values("price", ascending=False)
                )
                st.subheader("Private property by region (CCR / RCR / OCR)")
                st.dataframe(by_region.rename(columns={"region": "Region", "price": "Median (SGD)"}), use_container_width=True)

    if show_rent_tab:
        with tab_objects[ti]:
            show_rent_vs_buy_section(load_rental_scenario(), filtered)
        ti += 1

    with tab_objects[ti]:
        tier = absd_tier_from_story() if st.session_state.first_property.startswith("Yes") else "2nd"
        if st.session_state.first_property.startswith("No"):
            tier = st.selectbox("ABSD tier", ["2nd", "3rd+"], key="story_absd_tier") or "2nd"
        show_absd_estimator(st.session_state.residency, tier)
        default_p = float(filtered["price"].median()) if not filtered.empty else 600_000.0
        show_affordability_calculator(default_price=default_p)
    ti += 1

    with tab_objects[ti]:
        show_distance_tools()
    ti += 1

    with tab_objects[ti]:
        if os.path.exists("policy_notes.md"):
            try:
                with open("policy_notes.md", "r", encoding="utf-8") as f:
                    st.markdown(f.read())
            except UnicodeDecodeError:
                st.warning("policy_notes.md could not be read (encoding).")
        else:
            st.write("Add `policy_notes.md` for eligibility notes.")

    with st.expander("Why this matters for first-time buyers"):
        st.markdown(
            "- **HDB resale** is usually cheaper than condos but has citizenship and occupancy rules.\n"
            "- **Private** homes face higher **ABSD** for PRs and foreigners.\n"
            "- Compare **several years** of prices — one hot quarter can mislead.\n"
            "- **Renting** avoids down payment and stamp duty but does not build equity."
        )


if __name__ == "__main__":
    main()

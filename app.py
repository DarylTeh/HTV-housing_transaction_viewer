import math
import os

import pandas as pd
import plotly.express as px
import pydeck as pdk
import requests
import streamlit as st

from data_sources import DATA_SOURCE_MODE, load_all_transactions
from housing_constants import GLOSSARY, calculate_absd, enrich_area_labels
from rental_model import load_rent_vs_buy_scenario
from schools import load_schools, programme_tags
from property_groups import HOUSING_KINDS, default_sizes_for_kinds, size_options_for_kinds
from story import (
    BUYER_TIPS,
    absd_tier_from_story,
    apply_story_filters,
    default_kinds_from_story,
    init_story_state,
    render_journey_picker,
    render_story_step,
)
from budget_calculator import calculate_budget, format_currency as fmt_currency
from amenity_search import load_pharmacies, load_hawker_centres, load_pois, filter_pois_by_type
from policy_context import POLICY_EDUCATION

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
    try:
        response = requests.get(url, params=params, headers={"User-Agent": "SG-Housing-Viewer/1.0"}, timeout=20)
        response.raise_for_status()
        result = response.json()
        if not result:
            return None
        return float(result[0]["lat"]), float(result[0]["lon"])
    except requests.exceptions.HTTPError as e:
        if e.response.status_code == 429:
            # Rate limited - return None and let app continue
            st.warning("Geocoding service temporarily unavailable (rate limited). Some location features may be skipped.")
            return None
        raise
    except Exception as e:
        # Silently handle other errors
        return None


@st.cache_data
def load_school_list():
    return load_schools()


@st.cache_data
def load_cached_pharmacies():
    return load_pharmacies()


@st.cache_data
def load_cached_hawker_centres():
    return load_hawker_centres()


@st.cache_data
def load_cached_pois():
    return load_pois()


@st.cache_data
def geocode_school(school_name: str):
    """Geocode a school; cached so the full list only hits the API once per school."""
    loc = geocode_place(school_name)
    if loc:
        return loc
    return geocode_place(f"{school_name} Singapore")


@st.cache_data
def schools_near_home(home_query: str, top_n: int = 15):
    home = geocode_place(home_query)
    if not home:
        return None, pd.DataFrame()

    schools_df = load_school_list()
    if schools_df.empty:
        return home, pd.DataFrame()

    rows = []
    for _, row in schools_df.iterrows():
        loc = geocode_school(row["name"])
        if not loc:
            continue
        km = haversine_distance(home[0], home[1], loc[0], loc[1])
        rows.append(
            {
                "rank": int(row["rank"]),
                "school": row["name"],
                "score": row["score"],
                "gender": row.get("gender", ""),
                "programmes": programme_tags(row),
                "distance_km": round(km, 2),
            }
        )

    if not rows:
        return home, pd.DataFrame()

    near = pd.DataFrame(rows).sort_values("distance_km").head(top_n)
    return home, near


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
    # Use min year in data to start_year (beginning of dataset)
    min_year = int(df["year"].min())
    pivot = df[df["year"].isin([min_year, end_year])].copy()
    if pivot.empty or group_col not in pivot.columns:
        return pd.DataFrame()
    medians = pivot.groupby([group_col, "year"], as_index=False)["price"].median()
    start = medians[medians["year"] == min_year].set_index(group_col)["price"]
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
            f"with a **{format_currency(scenario['loan_amount'])}** loan at **{scenario['interest_rate']*100:.2f}%** over "
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


def show_budget_calculator():
    """Show new income-based budget calculator (primary feature)."""
    st.subheader("💰 Budget Calculator — How much can I afford?")
    st.write(
        "Enter your income and details. The calculator shows max budget for HDB and private property "
        "based on bank lending limits (MSR for HDB, TDSR for private). **Property price is not needed** — "
        "the bank checks your income, not the price."
    )
    
    # Check if user is foreigner to hide CPF section
    is_foreigner = st.session_state.residency == "Foreigner"
    
    with st.form("budget_calc"):
        col1, col2 = st.columns(2)
        with col1:
            num_buyers = st.radio("Number of buyers", [1, 2], horizontal=True)
        
        with col2:
            st.caption("Enter individual buyer incomes below")
        
        st.markdown("**Buyer 1 Details**")
        income_col1, age_col1 = st.columns(2)
        with income_col1:
            income_primary = st.number_input(
                "Buyer 1 monthly gross income (SGD)", 
                min_value=0.0, 
                value=5000.0, 
                step=500.0,
                help="Gross income before CPF, tax, deductions."
            )
        with age_col1:
            age_primary = st.number_input("Buyer 1 age", min_value=18, max_value=80, value=35, step=1)
        
        if num_buyers == 2:
            st.markdown("**Buyer 2 Details**")
            income_col2, age_col2 = st.columns(2)
            with income_col2:
                income_secondary = st.number_input(
                    "Buyer 2 monthly gross income (SGD)", 
                    min_value=0.0, 
                    value=3000.0, 
                    step=500.0,
                    help="Gross income before CPF, tax, deductions."
                )
            with age_col2:
                age_secondary = st.number_input("Buyer 2 age", min_value=18, max_value=80, value=33, step=1)
            buyer_incomes = [income_primary, income_secondary]
            ages = [age_primary, age_secondary]
        else:
            buyer_incomes = [income_primary]
            ages = [age_primary]
        
        # CPF section - only show for Singapore Citizens and PRs
        if not is_foreigner:
            st.markdown("**CPF Details** (Singapore Citizens & PRs only)")
            cpf_pledge = st.number_input(
                "CPF OA balance pledged to bank (SGD)",
                min_value=0.0,
                value=0.0,
                step=1000.0,
                help="Amount of CPF Ordinary Account balance used as loan security. This will be automatically drained when buying a house."
            )
            st.caption("💡 CPF is automatically used for down payment and monthly installments. You cannot choose how much to spare.")
        else:
            cpf_pledge = 0.0
            st.info("ℹ️ CPF is not applicable for foreigners. Your budget calculation assumes full cash payment.")
        
        submitted = st.form_submit_button("Calculate My Budget", use_container_width=True, type="primary")
    
    if submitted:
        result = calculate_budget(
            gross_monthly_income=sum(buyer_incomes),  # Pass combined income for backward compatibility
            num_buyers=num_buyers,
            ages=ages,
            cpf_pledge_pct=cpf_pledge,
            buyer_incomes=buyer_incomes,  # Pass individual incomes
        )
        
        st.markdown("### Your Maximum Budget")
        
        # Display limitations if any
        if result.limitations:
            st.warning("⚠️ **Notes:**\n" + "\n".join(f"- {lim}" for lim in result.limitations))
        
        col_hdb, col_private, col_recommended = st.columns(3)
        
        with col_hdb:
            st.metric(
                "HDB Max",
                fmt_currency(result.hdb_max_budget),
                help="Based on 30% MSR (Mortgage Servicing Ratio) limit"
            )
        
        with col_private:
            st.metric(
                "Private Max",
                fmt_currency(result.private_max_budget),
                help="Based on 55% TDSR (Total Debt Servicing Ratio) limit"
            )
        
        with col_recommended:
            st.metric(
                "Recommended 🎯",
                fmt_currency(result.recommended_budget),
                help="80% of lower max as safety net"
            )
        
        st.info(
            f"**What this means:**\n\n"
            f"- **HDB**: Banks typically limit your monthly mortgage to **{fmt_currency(result.gross_monthly_income * 0.30)}** "
            f"(30% of {fmt_currency(result.gross_monthly_income)}).\n"
            f"- **Private**: Banks typically limit total debt to **{fmt_currency(result.gross_monthly_income * 0.55)}** "
            f"(55% of {fmt_currency(result.gross_monthly_income)}).\n"
            f"- **Recommended**: Stay at **{fmt_currency(result.recommended_budget)}** for breathing room.\n\n"
            f"**Next step**: Use this budget to filter properties and explore in the Market Snapshot tab below."
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
    st.subheader("Commute & nearby schools")
    google_key = os.environ.get("GOOGLE_MAPS_API_KEY")
    schools_df = load_school_list()

    home_default = "Tampines Street 61"
    school_names = schools_df["name"].tolist() if not schools_df.empty else []
    school_labels = (
        [f"#{int(r['rank'])} {r['name']}" for _, r in schools_df.iterrows()] if not schools_df.empty else []
    )
    label_to_name = dict(zip(school_labels, school_names)) if school_labels else {}

    tab_commute, tab_schools, tab_list = st.tabs(["Commute", "Nearest schools", "School rankings"])

    with tab_commute:
        with st.form("distance"):
            origin = st.text_input("Address near the home", value=home_default, key="commute_origin")
            dest_mode = st.radio("Destination", ["Custom address", "Pick from school list"], horizontal=True)
            if dest_mode == "Pick from school list" and school_labels:
                picked = st.selectbox("School", school_labels, key="commute_school_pick")
                destination = label_to_name.get(picked, picked)
            else:
                destination = st.text_input("Destination (work / school / MRT)", value="Tampines MRT Station")
            submitted = st.form_submit_button("Estimate commute")

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

    with tab_schools:
        st.caption(
            "Distances are straight-line (km) from your address to each school. "
            "School **rank** is the row order in `data/school_list.csv` (1 = top of list)."
        )
        if schools_df.empty:
            st.warning("`data/school_list.csv` not found.")
        else:
            with st.form("near_schools"):
                home = st.text_input("Your home address", value=home_default, key="schools_home")
                top_n = st.slider("Show nearest schools", min_value=5, max_value=30, value=15)
                find = st.form_submit_button("Find nearest schools")

            if find:
                with st.spinner("Locating schools (first run may take a minute while locations are cached)…"):
                    _home, near = schools_near_home(home, top_n=top_n)
                if _home is None:
                    st.warning("Could not find that address. Try block + street + Singapore.")
                elif near.empty:
                    st.warning("Could not locate schools. Check your internet connection.")
                else:
                    st.dataframe(
                        near.rename(
                            columns={
                                "rank": "Rank",
                                "school": "School",
                                "score": "Score",
                                "gender": "Gender",
                                "programmes": "Programmes",
                                "distance_km": "Distance (km)",
                            }
                        ),
                        use_container_width=True,
                        hide_index=True,
                    )
                    closest = near.iloc[0]
                    st.info(
                        f"Closest on this list: **{closest['school']}** "
                        f"(rank #{int(closest['rank'])}, ~{closest['distance_km']} km away)."
                    )

    with tab_list:
        if schools_df.empty:
            st.warning("`data/school_list.csv` not found.")
        else:
            st.caption("Full list sorted by rank (same order as the original spreadsheet).")
            display = schools_df.copy()
            display["programmes"] = display.apply(programme_tags, axis=1)
            st.dataframe(
                display[["rank", "name", "score", "gender", "programmes"]].rename(
                    columns={
                        "rank": "Rank",
                        "name": "School",
                        "score": "Score",
                        "gender": "Gender",
                        "programmes": "Programmes",
                    }
                ),
                hide_index=True,
                use_container_width=True,
                height=400,
            )


def render_sidebar_controls(df):
    st.sidebar.header("Your profile")
    
    def update_filters():
        st.rerun()
    
    st.session_state.residency = st.sidebar.selectbox(
        "Residency",
        ["Singapore Citizen", "Permanent Resident", "Foreigner"],
        index=["Singapore Citizen", "Permanent Resident", "Foreigner"].index(st.session_state.residency),
        on_change=update_filters,
        key="residency_select"
    )
    st.session_state.own_hdb = st.sidebar.selectbox(
        "Own HDB?",
        ["No", "Yes"],
        index=["No", "Yes"].index(st.session_state.own_hdb),
        on_change=update_filters,
        key="own_hdb_select"
    )
    tip = BUYER_TIPS.get((st.session_state.residency, st.session_state.own_hdb))
    if tip:
        st.sidebar.info(tip)

    st.session_state.rent_or_buy = st.sidebar.selectbox(
        "Rent or buy?",
        ["Rent", "Buy", "Still deciding"],
        index=["Rent", "Buy", "Still deciding"].index(st.session_state.rent_or_buy),
        on_change=update_filters,
        key="rent_or_buy_select"
    )
    st.session_state.first_property = st.sidebar.selectbox(
        "First property in Singapore?",
        ["Yes — first property", "No — I already own property"],
        index=0 if st.session_state.first_property.startswith("Yes") else 1,
        on_change=update_filters,
        key="first_property_select"
    )

    st.sidebar.markdown("**What are you looking at?**")
    if st.session_state.residency == "Foreigner":
        kind_options = ["Condo", "Landed"]
    else:
        kind_options = HOUSING_KINDS

    default_kinds = [k for k in default_kinds_from_story() if k in kind_options]
    housing_kinds = st.sidebar.multiselect(
        "Home type",
        kind_options,
        default=default_kinds or kind_options[:2],
        help="HDB = public flats · Condo = private apartments & EC · Landed = terrace / semi-D / bungalow",
        on_change=update_filters,
        key="housing_kinds_select"
    )

    size_options = size_options_for_kinds(df, housing_kinds)
    default_sizes = [s for s in default_sizes_for_kinds(df, housing_kinds) if s in size_options]
    size_choices = st.sidebar.multiselect(
        "Size (rooms & approx. sqft)",
        size_options,
        default=default_sizes,
        help="Sqft ranges are typical sizes from transaction data, shown in square feet.",
        on_change=update_filters,
        key="size_choices_select"
    )

    area_labels = sorted(df["area_name"].dropna().unique()) if "area_name" in df.columns else sorted(df["town"].dropna().unique())
    selected_areas = st.sidebar.multiselect("Areas (towns / districts)", area_labels, default=[], on_change=update_filters, key="selected_areas_select")

    year_options = sorted(df["year"].dropna().astype(int).unique())
    yr_start, yr_end = default_year_range(year_options)
    start_year, end_year = st.sidebar.select_slider(
        "Year range (last 5 years by default)",
        options=year_options,
        value=(yr_start, yr_end),
        on_change=update_filters,
        key="year_range_select"
    )

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

    # Header with glossary button
    col_title, col_glossary = st.columns([4, 1])
    with col_title:
        st.title("🏡 Singapore Housing Journey")
        st.write(
            "Learn how HDB and private housing prices move in Singapore — then check affordability, "
            "stamp duty, and rent-vs-buy in plain language."
        )
    
    with col_glossary:
        with st.popover("📚 Glossary", use_container_width=True):
            st.markdown("### Key Terms")
            for term, meaning in GLOSSARY.items():
                st.markdown(f"**{term}** — {meaning}")
            st.divider()
            st.caption("💡 Click outside to close")

    mode_label = "local Excel workbooks" if DATA_SOURCE_MODE == "local_xlsx" else "live government API"

    # Progress bar for data loading
    progress_bar = st.progress(0, text="Initializing...")
    status_text = st.empty()
    
    status_text.text("Loading transaction data...")
    progress_bar.progress(20)
    df = load_app_data()
    
    if df.empty:
        st.error("No data found. Place xlsx files in `data/` or run `python scripts/update_data.py`.")
        return
    
    status_text.text("Loading rental scenario...")
    progress_bar.progress(40)
    rental_scenario = load_rental_scenario()
    
    status_text.text("Loading school data...")
    progress_bar.progress(60)
    schools_df = load_school_list()
    
    status_text.text("Loading amenity data...")
    progress_bar.progress(80)
    pharmacies = load_cached_pharmacies()
    hawkers = load_cached_hawker_centres()
    pois = load_cached_pois()
    
    status_text.text("Finalizing...")
    progress_bar.progress(100)
    
    # Clear the status text and progress bar after loading
    status_text.empty()
    progress_bar.empty()

    if st.session_state.journey_mode is None:
        render_journey_picker()
        return

    if st.session_state.journey_mode == "guided" and not st.session_state.story_complete:
        render_story_step()
        st.divider()

    housing_kinds, size_choices, selected_areas, start_year, end_year = render_sidebar_controls(df)
    filtered = filter_dataframe(df, housing_kinds, size_choices, selected_areas)

    st.markdown("## Market snapshot")
    
    # Show different information based on rent/buy selection
    if st.session_state.rent_or_buy == "Rent":
        st.info("🏠 **Rental Mode**: Currently showing purchase price data for reference. Actual rental market data is not available in this dataset. Use the 'Rent vs Buy Comparison' section below to estimate monthly rental costs.")
        st.write(f"**{len(df):,}** purchase transactions ({int(df['year'].min())}–{int(df['year'].max())}) · **{len(filtered):,}** after your filters")
        
        m1, m2, m3 = st.columns(3)
        m1.metric("HDB resale (purchase)", f"{len(df[df['dataset'] == 'HDB Resale']):,}")
        m2.metric("Private (purchase)", f"{len(df[df['dataset'] == 'Private Property']):,}")
        m3.metric("Median purchase price", format_currency(filtered["price"].median()) if not filtered.empty else "—")
    else:
        st.write(f"**{len(df):,}** transactions ({int(df['year'].min())}–{int(df['year'].max())}) · **{len(filtered):,}** after your filters")

        m1, m2, m3 = st.columns(3)
        m1.metric("HDB resale", f"{len(df[df['dataset'] == 'HDB Resale']):,}")
        m2.metric("Private", f"{len(df[df['dataset'] == 'Private Property']):,}")
        m3.metric("Median (filtered)", format_currency(filtered["price"].median()) if not filtered.empty else "—")

    st.divider()
    
    # PRIMARY SECTION: Budget Calculator (Always expanded, always visible - except in rent mode)
    if st.session_state.rent_or_buy != "Rent":
        st.markdown("## 💰 Plan Your Budget")
        show_budget_calculator()
        st.divider()
    else:
        st.info("💡 Budget calculator is hidden in rental mode. Use the 'Rent vs Buy Comparison' section below to estimate rental costs.")
        st.divider()
    
    # PRIMARY SECTION: Market Trends (Always expanded)
    st.markdown("## 📊 Market Trends & Prices")
    if filtered.empty:
        st.warning("No records match your filters — try more home types, sizes, or areas.")
    else:
        display_col = "area_name" if "area_name" in filtered.columns else "town"
        top_summary = (
            filtered.groupby(["housing_kind", "size_label", display_col], as_index=False)["price"]
            .median()
            .sort_values("price", ascending=False)
            .head(12)
        )
        st.subheader("Highest median prices (your selection)")
        display_df = top_summary.rename(
            columns={
                "housing_kind": "Home type",
                "size_label": "Size",
                display_col: "Area",
                "price": "Median (SGD)",
            }
        )
        display_df["Median (SGD)"] = display_df["Median (SGD)"].apply(format_currency)
        st.dataframe(display_df, use_container_width=True, hide_index=True)

        group_col = display_col if selected_areas else "size_label"
        chart = build_trend_chart(filtered, group_col, start_year, end_year)
        if chart:
            st.plotly_chart(chart, use_container_width=True)

        gain_df = calculate_percent_gain(filtered, group_col, start_year, end_year)
        if not gain_df.empty and start_year != end_year:
            min_year = int(filtered["year"].min())
            st.subheader(f"Price change {min_year} → {end_year}")
            gain_display = gain_df.copy()
            gain_display["start_price"] = gain_display["start_price"].apply(format_currency)
            gain_display["end_price"] = gain_display["end_price"].apply(format_currency)
            gain_display["gain_pct"] = gain_display["gain_pct"].round(1).astype(str) + "%"
            st.dataframe(gain_display, use_container_width=True, hide_index=True)

        if "region" in filtered.columns and filtered["dataset"].eq("Private Property").any():
            by_region = (
                filtered[filtered["dataset"] == "Private Property"]
                .groupby("region", as_index=False)["price"]
                .median()
                .sort_values("price", ascending=False)
            )
            st.subheader("Private property by region (CCR / RCR / OCR)")
            region_display = by_region.rename(columns={"region": "Region", "price": "Median (SGD)"})
            region_display["Median (SGD)"] = region_display["Median (SGD)"].apply(format_currency)
            st.dataframe(region_display, use_container_width=True, hide_index=True)

    st.divider()
    
    # PRIMARY SECTION: Schools (Always expanded - critical for HDB families, but hidden in rent mode)
    if st.session_state.rent_or_buy != "Rent":
        st.markdown("## 🏫 Schools Near Home")
        show_distance_tools()
        st.divider()
    else:
        st.info("💡 School proximity tools are hidden in rental mode. Rental tenants typically don't need school proximity for children.")
        st.divider()
    
    # COLLAPSIBLE SECTIONS (All collapsed by default for cleaner UI)
    
    # Rent vs Buy - auto-expand when Rent is selected
    rent_goal = st.session_state.rent_or_buy
    show_rent_tab = rent_goal in ("Rent", "Still deciding")
    if show_rent_tab:
        # Auto-expand when Rent is selected, otherwise collapsed
        expand_rent = (rent_goal == "Rent")
        with st.expander("🏠 Rent vs Buy Comparison", expanded=expand_rent):
            show_rent_vs_buy_section(rental_scenario, filtered)
        st.divider()
    
    # ABSD & Advanced Affordability (collapsed by default)
    with st.expander("📋 ABSD Stamp Duty Calculator", expanded=False):
        tier = absd_tier_from_story() if st.session_state.first_property.startswith("Yes") else "2nd"
        if st.session_state.first_property.startswith("No"):
            tier = st.selectbox("ABSD tier", ["2nd", "3rd+"], key="story_absd_tier") or "2nd"
        show_absd_estimator(st.session_state.residency, tier)
        st.divider()
        st.subheader("Advanced: Check if property price fits your loan")
        default_p = float(filtered["price"].median()) if not filtered.empty else 600_000.0
        show_affordability_calculator(default_price=default_p)
    st.divider()
    
    # Policy Notes (collapsed by default)
    with st.expander("📚 Housing Policies & Rules", expanded=False):
        if os.path.exists("policy_notes.md"):
            try:
                with open("policy_notes.md", "r", encoding="utf-8") as f:
                    st.markdown(f.read())
            except UnicodeDecodeError:
                st.warning("policy_notes.md could not be read (encoding).")
        else:
            st.write("Add `policy_notes.md` for eligibility notes.")
        
        st.markdown("---")
        st.markdown("### 💡 Key Policies for First-Time Buyers")
        for title, content in [
            (POLICY_EDUCATION["hdb_mop"]["title"], POLICY_EDUCATION["hdb_mop"]["content"]),
            (POLICY_EDUCATION["school_priority"]["title"], POLICY_EDUCATION["school_priority"]["content"]),
            (POLICY_EDUCATION["family_planning"]["title"], POLICY_EDUCATION["family_planning"]["content"]),
            (POLICY_EDUCATION["cpf_usage"]["title"], POLICY_EDUCATION["cpf_usage"]["content"]),
            (POLICY_EDUCATION["absd_explanation"]["title"], POLICY_EDUCATION["absd_explanation"]["content"]),
            (POLICY_EDUCATION["tdsr_msr"]["title"], POLICY_EDUCATION["tdsr_msr"]["content"]),
        ]:
            with st.expander(title, expanded=False):
                st.write(content)
    st.divider()
    
    # Advanced Features (collapsed by default - hidden in rent mode)
    if st.session_state.rent_or_buy != "Rent":
        with st.expander("🔍 Advanced: Amenities & POI Proximity", expanded=False):
            st.subheader("Nearby Services Map")
            home_query = st.text_input("Enter home address", value="Tampines Street 61", key="amenity_search_home")
            radius_km = st.slider("Search radius (km)", min_value=0.5, max_value=5.0, value=2.0, step=0.5)
            
            if home_query:
                home_loc = geocode_place(home_query)
                if home_loc:
                    # Load data
                    pois = load_cached_pois()
                    schools_df = load_school_list()
                    
                    # Filter POIs within radius
                    nearby_pois = []
                    if not pois.empty and "lat" in pois.columns and "lon" in pois.columns:
                        for _, row in pois.iterrows():
                            try:
                                poi_lat = float(row["lat"])
                                poi_lon = float(row["lon"])
                                dist = haversine_distance(home_loc[0], home_loc[1], poi_lat, poi_lon)
                                if dist <= radius_km:
                                    nearby_pois.append({
                                        "name": row.get("name", "Unknown"),
                                        "category": row.get("category", "POI"),
                                        "lat": poi_lat,
                                        "lon": poi_lon,
                                        "distance_km": round(dist, 2)
                                    })
                            except (ValueError, TypeError):
                                continue
                    
                    # Filter schools within radius
                    nearby_schools = []
                    if not schools_df.empty:
                        for _, row in schools_df.iterrows():
                            school_name = row["name"]
                            loc = geocode_school(school_name)
                            if loc:
                                dist = haversine_distance(home_loc[0], home_loc[1], loc[0], loc[1])
                                if dist <= radius_km:
                                    nearby_schools.append({
                                        "name": school_name,
                                        "rank": int(row["rank"]),
                                        "lat": loc[0],
                                        "lon": loc[1],
                                        "distance_km": round(dist, 2)
                                    })
                    
                    # Create map data for pydeck
                    map_data = []
                    
                    # Add home location (blue marker with house icon)
                    map_data.append({
                        "lat": home_loc[0],
                        "lon": home_loc[1],
                        "name": "🏠 Target Home",
                        "type": "home",
                        "color": [0, 0, 255]  # Blue
                    })
                    
                    # Add POIs (green markers)
                    for poi in nearby_pois[:50]:  # Limit to 50 for performance
                        map_data.append({
                            "lat": poi["lat"],
                            "lon": poi["lon"],
                            "name": f"📍 {poi['name']} ({poi['category']})",
                            "type": "poi",
                            "color": [0, 255, 0]  # Green
                        })
                    
                    # Add schools (blue markers)
                    for school in nearby_schools[:20]:  # Limit to 20 for performance
                        map_data.append({
                            "lat": school["lat"],
                            "lon": school["lon"],
                            "name": f"🏫 {school['name']} (Rank #{school['rank']})",
                            "type": "school",
                            "color": [0, 0, 255]  # Blue
                        })
                    
                    if map_data:
                        map_df = pd.DataFrame(map_data)
                        
                        # Create pydeck map with colored markers
                        view_state = pdk.ViewState(
                            latitude=home_loc[0],
                            longitude=home_loc[1],
                            zoom=13,
                            pitch=0
                        )
                        
                        # Create scatterplot layer with different colors
                        layer = pdk.Layer(
                            "ScatterplotLayer",
                            data=map_df,
                            get_position="[lon, lat]",
                            get_color="color",
                            get_radius=100,
                            pickable=True
                        )
                        
                        # Create the map
                        st.pydeck_chart(pdk.Deck(
                            layers=[layer],
                            initial_view_state=view_state,
                            tooltip={
                                "html": "<b>{name}</b>",
                                "style": {
                                    "backgroundColor": "steelblue",
                                    "color": "white"
                                }
                            }
                        ))
                        
                        # Display legend
                        col1, col2, col3 = st.columns(3)
                        with col1:
                            st.markdown("🏠 **Target Home** (Blue)")
                        with col2:
                            st.markdown("📍 **POI** (Green)")
                        with col3:
                            st.markdown("🏫 **School** (Blue)")
                        
                        # Display nearby locations in tables
                        col_poi, col_school = st.columns(2)
                        
                        with col_poi:
                            st.subheader(f"Nearby POIs ({len(nearby_pois)})")
                            if nearby_pois:
                                poi_df = pd.DataFrame(nearby_pois)
                                st.dataframe(poi_df[["name", "category", "distance_km"]].head(20), use_container_width=True, hide_index=True)
                            else:
                                st.info("No POIs found within radius")
                        
                        with col_school:
                            st.subheader(f"Nearby Schools ({len(nearby_schools)})")
                            if nearby_schools:
                                school_df = pd.DataFrame(nearby_schools)
                                st.dataframe(school_df[["name", "rank", "distance_km"]].head(20), use_container_width=True, hide_index=True)
                            else:
                                st.info("No schools found within radius")
                    else:
                        st.warning("No locations found to display on map")
                    
                    # Show data availability info
                    col_pharma, col_hawker = st.columns(2)
                    with col_pharma:
                        pharmacies = load_cached_pharmacies()
                        if not pharmacies.empty:
                            st.caption(f"📍 Pharmacies data available: {len(pharmacies)} records")
                        else:
                            st.caption("Pharmacy data not available")
                    
                    with col_hawker:
                        hawkers = load_cached_hawker_centres()
                        if not hawkers.empty:
                            st.caption(f"🍜 Hawker centres data available: {len(hawkers)} records")
                        else:
                            st.caption("Hawker centre data not available")
                else:
                    st.warning("Could not locate that address. Try block + street + Singapore.")

    with st.expander("💡 Why this matters for first-time buyers", expanded=False):
        st.markdown(
            "- **HDB resale** is usually cheaper than condos but has citizenship and occupancy rules.\n"
            "- **Private** homes face higher **ABSD** for PRs and foreigners.\n"
            "- Compare **several years** of prices — one hot quarter can mislead.\n"
            "- **Renting** avoids down payment and stamp duty but does not build equity."
        )


if __name__ == "__main__":
    main()

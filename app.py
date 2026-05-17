import math
import os
from datetime import datetime

import pandas as pd
import plotly.express as px
import requests
import streamlit as st

DATA_FILES = {
    "HDB Resale": "data/latest/hdb_resale.csv",
    "Private Property": "data/latest/private_property.csv",
}

st.set_page_config(
    page_title="Singapore Housing Transaction Viewer",
    page_icon="🏘️",
    layout="wide",
)


def find_column(df, candidates, default=None):
    for candidate in candidates:
        if candidate in df.columns:
            return candidate
    return default


@st.cache_data
def load_dataframe(path):
    return pd.read_csv(path)


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
    params = {
        "origins": origin,
        "destinations": destination,
        "key": api_key,
        "mode": "transit",
    }
    response = requests.get(url, params=params, timeout=20)
    response.raise_for_status()
    data = response.json()
    if data.get("status") != "OK":
        return None
    element = data["rows"][0]["elements"][0]
    if element.get("status") != "OK":
        return None
    return {
        "distance_text": element["distance"]["text"],
        "duration_text": element["duration"]["text"],
    }


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


def normalize_hdb(df):
    df = df.copy()
    df["dataset"] = "HDB Resale"
    df["property_type"] = "HDB Resale"
    price_col = find_column(df, ["resale_price", "price", "transacted_price"], "resale_price")
    town_col = find_column(df, ["town", "planning_area", "area"], "town")
    date_col = find_column(df, ["month", "transaction_date", "sale_date"], "month")
    size_col = find_column(df, ["floor_area_sqm", "area_sqm", "area"])
    lease_col = find_column(df, ["remaining_lease", "lease_remaining", "lease"])

    df = df.rename(columns={town_col: "town", date_col: "transaction_date", price_col: "price"})
    if "town" not in df.columns:
        df["town"] = "Unknown"
    df["street_name"] = df.get("street_name", df.get("block", ""))
    df["flat_type"] = df.get("flat_type", df.get("flat_model", ""))
    df["size_sqm"] = df.get(size_col)
    df["lease_remaining"] = df.get(lease_col)
    df["transaction_date"] = pd.to_datetime(df["transaction_date"], errors="coerce")
    df["year"] = df["transaction_date"].dt.year
    df["quarter"] = df["transaction_date"].dt.to_period("Q").astype(str)
    df["price"] = pd.to_numeric(df["price"], errors="coerce")
    return df[
        ["dataset", "property_type", "town", "street_name", "transaction_date", "price", "size_sqm", "lease_remaining", "year", "quarter"]
    ]


def normalize_private(df):
    df = df.copy()
    df["dataset"] = "Private Property"
    price_col = find_column(df, ["price", "transacted_price", "resale_price"], "price")
    town_col = find_column(df, ["town", "planning_area", "location"], "town")
    date_col = find_column(df, ["transaction_date", "month", "sale_date", "completion_date"], "transaction_date")
    property_col = find_column(df, ["property_type", "type_of_area", "subtype", "property_category"], "property_type")
    size_col = find_column(df, ["floor_area_sqm", "area_sqm", "size_sqft", "floor_area"], None)
    lease_col = find_column(df, ["lease_commence_date", "tenure", "lease"], None)

    df["transaction_date"] = pd.to_datetime(df[date_col], errors="coerce")
    df["town"] = df.get(town_col, "Unknown")
    df["property_type"] = df.get(property_col, "Private")
    if pd.api.types.is_numeric_dtype(df["property_type"]):
        df["property_type"] = df["property_type"].astype(str)
    df["street_name"] = df.get("street_name", df.get("project_name", ""))
    df["size_sqm"] = df.get(size_col)
    df["lease_remaining"] = df.get(lease_col)
    df["year"] = df["transaction_date"].dt.year
    df["quarter"] = df["transaction_date"].dt.to_period("Q").astype(str)
    df["price"] = pd.to_numeric(df[price_col], errors="coerce")
    return df[
        ["dataset", "property_type", "town", "street_name", "transaction_date", "price", "size_sqm", "lease_remaining", "year", "quarter"]
    ]


def load_app_data():
    loaded = []
    for label, path in DATA_FILES.items():
        if os.path.exists(path):
            try:
                df = load_dataframe(path)
                if label == "HDB Resale":
                    loaded.append(normalize_hdb(df))
                else:
                    loaded.append(normalize_private(df))
            except Exception as exc:
                st.warning(f"Could not load {path}: {exc}")
        else:
            st.warning(f"Missing data file: {path}")
    if loaded:
        return pd.concat(loaded, ignore_index=True)
    return pd.DataFrame()


def build_trend_chart(df, group_by, start_year, end_year):
    filtered = df[(df["year"] >= start_year) & (df["year"] <= end_year)].copy()
    if filtered.empty:
        return None
    target = filtered.groupby([group_by, "year"], as_index=False)["price"].median()
    return px.line(
        target,
        x="year",
        y="price",
        color=group_by,
        markers=True,
        labels={"price": "Median Price (SGD)", "year": "Year"},
        title=f"Median price trend by {group_by.lower()} ({start_year}–{end_year})",
    )


def calculate_percent_gain(df, group_by, start_year, end_year, top_n=10):
    pivot = df[df["year"].isin([start_year, end_year])].copy()
    if pivot.empty:
        return pd.DataFrame()
    medians = pivot.groupby([group_by, "year"], as_index=False)["price"].median()
    start = medians[medians["year"] == start_year].set_index(group_by)["price"]
    end = medians[medians["year"] == end_year].set_index(group_by)["price"]
    joined = pd.DataFrame({"start_price": start, "end_price": end}).dropna()
    joined["gain_pct"] = (joined["end_price"] - joined["start_price"]) / joined["start_price"] * 100
    return joined.reset_index().sort_values("gain_pct", ascending=False).head(top_n)


def show_affordability_calculator():
    st.header("Affordability calculator")
    st.write(
        "Enter your salary and expected property price to see how HDB MSR and private TDSR compare. "
        "This calculator is a beginner guide and not a bank decision." 
    )
    with st.form("affordability"):
        gross_income = st.number_input("Monthly gross income (SGD)", min_value=0.0, value=5000.0, step=100.0)
        property_price = st.number_input("Property price (SGD)", min_value=0.0, value=600000.0, step=10000.0)
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
        st.write(f"Maximum HDB MSR allowance: {format_currency(msr_limit)} per month")
        if monthly_payment <= msr_limit:
            st.success("Your estimated payment is within the HDB MSR guideline.")
        else:
            st.error("Your estimated payment is above the HDB MSR guideline.")
        st.write(f"Maximum private-property TDSR allowance: {format_currency(remaining_tdsr)} per month after other debts")
        if monthly_payment <= remaining_tdsr:
            st.success("Your estimated payment is within the private property TDSR guideline.")
        else:
            st.warning("Your estimated payment may exceed the private property TDSR guideline.")

        st.write(
            "**Note:** MSR is usually 30% of gross salary for HDB loan decisions, while TDSR is usually 55% for private property. "
            "Actual bank assessment may vary and depends on your CPF, existing loans, and family situation."
        )


def show_distance_tools():
    st.header("Estimate distance and commute time")
    google_key = os.environ.get("GOOGLE_MAPS_API_KEY")
    with st.form("distance"):
        origin = st.text_input("Enter an address or landmark near the property", value="Tampines Street 61")
        destination = st.text_input("Enter a destination or MRT station", value="Tampines MRT Station")
        submitted = st.form_submit_button("Estimate")

    if submitted:
        if google_key:
            result = google_distance(origin, destination, google_key)
            if result:
                st.success(f"Estimated commute: {result['duration_text']} by transit, {result['distance_text']}.")
            else:
                st.warning("Google Distance Matrix returned no result. Please check the address or your API key.")
        else:
            st.info("No Google Maps API key found. Using straight-line distance estimate.")
            origin_loc = geocode_place(origin)
            destination_loc = geocode_place(destination)
            if origin_loc and destination_loc:
                km = haversine_distance(origin_loc[0], origin_loc[1], destination_loc[0], destination_loc[1])
                st.write(f"Approximate straight-line distance: {km:.1f} km.")
                if km < 1:
                    st.write("This is very close by. Travel time is likely under 15 minutes by transit or walking.")
                elif km < 5:
                    st.write("This is a short trip. Transit or driving may take 15–30 minutes depending on connections.")
                else:
                    st.write("This is a longer trip. Transit may take 30+ minutes.")
            else:
                st.warning("Could not resolve one of the locations using OpenStreetMap.")


def main():
    st.title("🏡 Singapore Housing Transaction Viewer")
    st.write(
        "A beginner-friendly dashboard for HDB resale, condos, EC, and landed property. "
        "Compare trends, see price gain, and check your affordability in simple terms."
    )

    df = load_app_data()
    if df.empty:
        st.error("No data available yet. Run the updater script or check your CSV files in data/latest/.")
        return

    st.sidebar.header("Get started")
    buyer_type = st.sidebar.selectbox(
        "Buyer profile",
        ["Singapore Citizen", "Permanent Resident", "Foreigner"],
        help="Choose the profile that matches your current status.",
    )
    own_hdb = st.sidebar.selectbox(
        "Do you currently own HDB?", ["No", "Yes"], help="Owning HDB changes the rules for buying new property." )
    property_choices = st.sidebar.multiselect(
        "Property types to explore",
        sorted(df["property_type"].dropna().unique()),
        default=sorted(df["property_type"].dropna().unique())[:3],
        help="Compare types like HDB resale, condo, executive condo, or landed property.",
    )
    selected_towns = st.sidebar.multiselect(
        "Towns or areas",
        sorted(df["town"].dropna().unique()),
        default=[df["town"].dropna().unique().tolist()[0]] if not df.empty else [],
        help="Select one or more towns for trend comparison.",
    )
    start_year, end_year = st.sidebar.select_slider(
        "Year range",
        options=sorted(df["year"].dropna().astype(int).unique()),
        value=(sorted(df["year"].dropna().astype(int).unique())[0], sorted(df["year"].dropna().astype(int).unique())[-1]),
        help="Choose the year range for price trend charts.",
    )

    filtered = df[df["property_type"].isin(property_choices)]
    if selected_towns:
        filtered = filtered[filtered["town"].isin(selected_towns)]

    st.markdown("## Data snapshot")
    st.write(f"Latest dataset contains **{len(df):,} records** from {df['year'].min():.0f} to {df['year'].max():.0f}.")
    st.write(f"Showing **{len(filtered):,} records** after filters.")

    if filtered.empty:
        st.warning("No records match your filters. Try a broader selection or reset the town/property types.")
    else:
        top_summary = (
            filtered.groupby(["property_type", "town"], as_index=False)["price"].median()
            .sort_values("price", ascending=False)
            .head(12)
        )
        st.subheader("Top median prices by property type and town")
        st.dataframe(top_summary.rename(columns={"property_type": "Type", "town": "Town", "price": "Median price (SGD)"}))

        chart = build_trend_chart(filtered, "town" if selected_towns else "property_type", start_year, end_year)
        if chart is not None:
            st.plotly_chart(chart, use_container_width=True)

        if selected_towns and len(selected_towns) > 0:
            gain_df = calculate_percent_gain(filtered, "town", start_year, end_year)
            if not gain_df.empty:
                st.subheader(f"Percent gain from {start_year} to {end_year}")
                st.dataframe(gain_df.rename(columns={"town": "Town", "start_price": "Start price", "end_price": "End price", "gain_pct": "Gain (%)"}))

        if len(property_choices) > 1:
            compare_chart = build_trend_chart(filtered, "property_type", start_year, end_year)
            if compare_chart is not None:
                st.subheader("Compare property types")
                st.plotly_chart(compare_chart, use_container_width=True)

    with st.expander("Why this matters for first-time buyers"):
        st.markdown(
            "- HDB resale flat prices are usually lower than private condos, but HDB has ownership rules."
            "\n- Private condos and landed property have higher ABSD and TDSR requirements."
            "\n- Comparing several towns over time helps you avoid short-lived price spikes."
            "\n- If you own HDB, you usually need to sell before buying private property."
        )

    left, right = st.columns([2, 1])
    with left:
        show_affordability_calculator()
    with right:
        st.header("Rules and eligibility")
        if os.path.exists("policy_notes.md"):
            with open("policy_notes.md", "r", encoding="utf-8") as f:
                st.markdown(f.read())
        else:
            st.write("Policy notes are not available. Please add policy_notes.md to the repo.")

    show_distance_tools()
    st.markdown("---")
    st.markdown("### Quick start tips")
    st.markdown(
        "1. Use the side panel to choose property type and towns.\n"
        "2. Compare median price trends over multiple years.\n"
        "3. Use the calculator for MSR vs TDSR checks.\n"
        "4. Add your Google Maps API key in Streamlit Cloud for commute estimates."
    )


if __name__ == "__main__":
    main()

from __future__ import annotations

import pandas as pd
import pydeck as pdk
import streamlit as st

from amenity_search import haversine_distance

def property_category(row):
    dataset = str(row.get("dataset", ""))
    ptype = str(row.get("property_type", ""))

    if "HDB" in dataset:
        return "HDB"

    if ptype == "Executive Condominium":
        return "EC"

    if ptype in ["Condominium", "Apartment"]:
        return "Condo"

    landed_types = {
        "Detached",
        "Detached House",
        "Semi-detached",
        "Semi-Detached",
        "Semi-Detached House",
        "Terrace",
        "Terrace House",
        "Strata Detached",
        "Strata Semi-detached",
        "Strata Terrace",
    }

    if ptype in landed_types:
        return "Landed"

    return "Other"

def search_schools(schools: pd.DataFrame, query: str) -> pd.DataFrame:
    if not query:
        return schools.sort_values("rank").head(20)
    q = query.strip()
    mask = (
        schools["name"].fillna("").str.contains(q, case=False, na=False)
        | schools["programmes"].fillna("").str.contains(q, case=False, na=False)
        | schools["gender"].fillna("").str.contains(q, case=False, na=False)
        | schools["ip"].fillna("").str.contains(q, case=False, na=False)
        | schools["ibdp"].fillna("").str.contains(q, case=False, na=False)
        | schools["sap"].fillna("").str.contains(q, case=False, na=False)
        | schools["affiliated"].fillna("").str.contains(q, case=False, na=False)
    )
    return schools[mask].sort_values("rank").head(20)


def search_schools_by_area(schools: pd.DataFrame, transactions: pd.DataFrame, query: str) -> pd.DataFrame:
    """Search schools near an area found in transactions."""
    if transactions.empty or not query:
        return pd.DataFrame()
    
    q = query.strip().lower()
    # Search for area/town/street in transactions
    mask = (
        transactions["area_name"].fillna("").str.lower().str.contains(q, na=False)
        | transactions["town"].fillna("").str.lower().str.contains(q, na=False)
        | transactions["street_name"].fillna("").str.lower().str.contains(q, na=False)
    )
    
    location_hits = transactions[mask & transactions["lat"].notna() & transactions["lon"].notna()]
    if location_hits.empty:
        return pd.DataFrame()
    
    # Use the first match as reference point
    ref = location_hits.iloc[0]
    home_lat, home_lon = float(ref["lat"]), float(ref["lon"])
    
    schools = schools.copy()
    schools["distance_km"] = schools.apply(
        lambda row: haversine_distance(home_lat, home_lon, row["lat"], row["lon"]) 
        if pd.notna(row["lat"]) and pd.notna(row["lon"]) 
        else float("inf"),
        axis=1,
    )
    schools = schools.sort_values("distance_km")

    schools = schools[
        schools["distance_km"] <= 2
    ]

    return schools.head(20)


def get_nearby_properties(
    transactions: pd.DataFrame,
    schools_df: pd.DataFrame,
    radius_km: float = 1.0,
) -> pd.DataFrame:
    """
    Return ONE row per development/project/block
    within radius of any selected school.
    """

    if transactions.empty or schools_df.empty:
        return pd.DataFrame()

    candidates = transactions[
        transactions["lat"].notna()
        & transactions["lon"].notna()
    ].copy()

    nearby_indexes = set()

    for _, school in schools_df.iterrows():

        school_lat = float(school["lat"])
        school_lon = float(school["lon"])

        distances = candidates.apply(
            lambda row: haversine_distance(
                school_lat,
                school_lon,
                float(row["lat"]),
                float(row["lon"]),
            ),
            axis=1,
        )

        matches = candidates[distances <= radius_km]

        nearby_indexes.update(matches.index)

    if not nearby_indexes:
        return pd.DataFrame()

    nearby = candidates.loc[list(nearby_indexes)].copy()

    nearby["display_type"] = nearby.apply(
        property_category,
        axis=1,
    )

    developments = []

    for _, group in nearby.groupby(
        [
            "display_type",
            "street_name",
        ],
        dropna=False,
    ):

        first = group.iloc[0]

        developments.append(
            {
                "display_type": first["display_type"],
                "name": first["street_name"],
                "lat": float(first["lat"]),
                "lon": float(first["lon"]),
                "count": len(group),
                "avg_price": group["price"].mean(),
                "median_price": group["price"].median(),
            }
        )

    return pd.DataFrame(developments)


def render_schools_page(data: dict[str, pd.DataFrame], state: dict) -> None:
    st.header("School Finder")
    st.write("Search a school or neighbourhood and view HDB, Condo, EC and Landed housing options within the 1km priority admission radius.")

    schools = data.get("schools_geocoded", pd.DataFrame())
    transactions = data.get("transactions", pd.DataFrame())
    
    if schools.empty:
        st.warning("School ranking data is unavailable.")
        return
    
    if transactions.empty:
        st.warning("Property data is unavailable.")
        return

    query = st.text_input(
        "Search school by name, programme, special status or nearby area", 
        value=state.get("school_query", ""), 
        key="school_query"
    )

    results = search_schools(schools, query)
    area_results = pd.DataFrame()
    area_search_used = False
    
    if query and results.empty:
        area_results = search_schools_by_area(schools, transactions, query)
        if not area_results.empty:
            area_search_used = True
            st.info(f"No direct school matches found. Showing schools nearest to '{query}'.")
            results = area_results

    if results.empty:
        st.info("Try another school name, programme, special status or a nearby location like 'Ang Mo Kio' or 'Bishan'.")
        return

    selected_school = state.get("selected_school")
    selected_lat = state.get("selected_school_lat")
    selected_lon = state.get("selected_school_lon")
    results = results.reset_index(drop=True)

    st.markdown(f"### {len(results)} school(s) found")
    for idx, school in results.iterrows():
        school_name = school.get("name", "Unknown")
        school_lat = school.get("lat")
        school_lon = school.get("lon")
        cols = st.columns([0.75, 0.25])
        with cols[0]:
            st.markdown(
                f"**{school_name}** — Rank {school.get('rank', '-')}, Score {school.get('score', '-')}"
            )
            st.caption(f"Programmes: {school.get('programmes', 'N/A')}")
            if pd.notna(school_lat) and pd.notna(school_lon):
                st.caption(f"📍 {school_lat:.6f}, {school_lon:.6f}")
            if selected_school == school_name:
                st.success("✓ Selected on map")
        with cols[1]:
            if pd.notna(school_lat) and pd.notna(school_lon):
                if st.button("Focus on map", key=f"focus_school_{idx}"):
                    state["selected_school"] = school_name
                    state["selected_school_lat"] = float(school_lat)
                    state["selected_school_lon"] = float(school_lon)
        st.divider()

    valid_schools = results[
        results["lat"].notna()
        & results["lon"].notna()
    ].copy()

    if valid_schools.empty:
        st.warning("No geocoded schools available.")
        return

    if (
        selected_lat is not None
        and selected_lon is not None
    ):
        center_lat = float(selected_lat)
        center_lon = float(selected_lon)
    else:
        center_lat = valid_schools["lat"].mean()
        center_lon = valid_schools["lon"].mean()

    school_markers = []

    for _, school in valid_schools.iterrows():

        school_markers.append(
            {
                "latitude": float(school["lat"]),
                "longitude": float(school["lon"]),
                "label": (
                    f"{school['name']}<br>"
                    f"Rank {school.get('rank','-')}"
                ),
                "type": "School",
                "score": school.get("score", ""),
            }
        )

    nearby_properties = get_nearby_properties(
        transactions,
        valid_schools,
        radius_km=1.0,
    )

    property_markers = []

    for _, prop in nearby_properties.iterrows():

        property_markers.append(
            {
                "latitude": float(prop["lat"]),
                "longitude": float(prop["lon"]),
                "label": (
                    f"{prop['name']}<br>"
                    f"{prop['display_type']}<br>"
                    f"{int(prop['count'])} transactions<br>"
                    f"Avg ${prop['avg_price']:,.0f}"
                ),
                "type": prop["display_type"],
            }
        )

    map_df = pd.DataFrame(
        school_markers + property_markers
    )

    circle_df = pd.DataFrame(
        [
            {
                "latitude": float(row["lat"]),
                "longitude": float(row["lon"]),
            }
            for _, row in valid_schools.iterrows()
        ]
    )

    st.metric(
        "Developments Within 1km",
        len(nearby_properties)
    )

    color_map = {
    "School": [59,130,246],

    "HDB": [34,197,94],

    "Condo": [234,179,8],

    "EC": [168,85,247],

    "Landed": [249,115,22],

    "Other": [156,163,175],
}

    map_df["color"] = map_df["type"].apply(
        lambda x: color_map.get(x, [156, 163, 175])
    )

    radius_layer = pdk.Layer(
        "ScatterplotLayer",
        data=circle_df,
        get_position="[longitude, latitude]",
        get_radius=1000,
        get_fill_color=[59,130,246,15]
        stroked=True,
        filled=True,
        line_width_min_pixels=2,
    )

    school_layer = pdk.Layer(
        "ScatterplotLayer",
        data=map_df[map_df["type"] == "School"],
        get_position="[longitude, latitude]",
        get_fill_color="color",
        get_radius=250,
        pickable=True,
    )

    property_layer = pdk.Layer(
        "ScatterplotLayer",
        data=map_df[map_df["type"] != "School"],
        get_position="[longitude, latitude]",
        get_fill_color="color",
        get_radius=100,
        pickable=True,
    )

    tooltip = {
        "html": "<b>{label}</b>",
        "style": {
            "backgroundColor": "steelblue",
            "color": "white",
        },
    }

    deck = pdk.Deck(
        layers=[
            radius_layer,
            property_layer,
            school_layer,
        ],
        initial_view_state=pdk.ViewState(
            latitude=center_lat,
            longitude=center_lon,
            zoom=13,
            pitch=0,
        ),
        tooltip=tooltip,
    )

    st.pydeck_chart(deck)

    st.caption(
        "🔵 School  •  🟢 HDB  •  🟡 Condo  •  🟣 EC  •  🟠 Landed"
    )

    if not nearby_properties.empty:

        st.markdown(
            f"### Nearby Properties within 1km"
        )

        nearby_properties = nearby_properties.copy()

        nearby_properties["display_type"] = nearby_properties.apply(
            property_category,
            axis=1,
        )

        summary = (
            nearby_properties.groupby("display_type")
            .agg(
                developments=("name", "count"),
                avg_price=("avg_price", "mean"),
            )
            .round(0)
        )

        st.dataframe(summary)
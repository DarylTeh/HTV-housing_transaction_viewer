from __future__ import annotations

import pandas as pd
import pydeck as pdk
import streamlit as st

from amenity_search import haversine_distance

PROPERTY_TYPE_KEYWORDS = {
    "HDB": ["hdb", "hub"],
    "Condo": ["condo", "residence", "apartment", "estate", "residences"],
    "Landed": ["terrace", "bungalow", "house", "semi-d", "villa", "cluster"],
}


def infer_property_type(name: str | None, category: str | None) -> str:
    text = f"{name or ''} {category or ''}".lower()
    for property_type, keywords in PROPERTY_TYPE_KEYWORDS.items():
        if any(keyword in text for keyword in keywords):
            return property_type
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


def search_schools_by_area(schools: pd.DataFrame, pois: pd.DataFrame, query: str) -> pd.DataFrame:
    if pois.empty or not query:
        return pd.DataFrame()
    q = query.strip()
    mask = (
        pois["name"].fillna("").str.contains(q, case=False, na=False)
        | pois["category"].fillna("").str.contains(q, case=False, na=False)
        | pois["address"].fillna("").str.contains(q, case=False, na=False)
    )
    location_hits = pois[mask & pois["lat"].notna() & pois["lon"].notna()]
    if location_hits.empty:
        return pd.DataFrame()
    home = location_hits.iloc[0]
    schools = schools.copy()
    schools["distance_km"] = schools.apply(
        lambda row: haversine_distance(home["lat"], home["lon"], row["lat"], row["lon"]) if pd.notna(row["lat"]) and pd.notna(row["lon"]) else float("inf"),
        axis=1,
    )
    return schools.sort_values("distance_km").head(20)


def render_schools_page(data: dict[str, pd.DataFrame], state: dict) -> None:
    st.header("School Finder")
    st.write("Search for Singapore schools and see nearby ranked institutions.")

    schools = data.get("schools_geocoded", pd.DataFrame())
    pois = data.get("pois", pd.DataFrame())
    if schools.empty:
        st.warning("School ranking data is unavailable.")
        return

    query = st.text_input("Search school by name, programme, special status or area", value=state.get("school_query", ""), key="school_query")

    results = search_schools(schools, query)
    area_results = pd.DataFrame()
    area_search_used = False
    if query and results.empty:
        area_results = search_schools_by_area(schools, pois, query)
        if not area_results.empty:
            area_search_used = True
            st.info(f"No direct school matches found. Showing schools nearest to '{query}'.")
            results = area_results

    if results.empty:
        st.info("Try another school name, programme, special status or a nearby location like Dover.")
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
        cols = st.columns([0.8, 0.2])
        with cols[0]:
            st.markdown(
                f"**{school_name}** — Rank {school.get('rank', '-')}, Score {school.get('score', '-')}, Programmes: {school.get('programmes', 'N/A')}"
            )
            if pd.notna(school_lat) and pd.notna(school_lon):
                st.write(f"Location: {school_lat:.6f}, {school_lon:.6f}")
            if selected_school == school_name:
                st.success("Selected on map")
        with cols[1]:
            if pd.notna(school_lat) and pd.notna(school_lon):
                if st.button("Focus on map", key=f"focus_school_{idx}"):
                    state["selected_school"] = school_name
                    state["selected_school_lat"] = float(school_lat)
                    state["selected_school_lon"] = float(school_lon)
                    st.experimental_rerun()
        st.markdown("---")

    if selected_school and selected_lat is not None and selected_lon is not None:
        center_lat = selected_lat
        center_lon = selected_lon
        selected_label = selected_school
    else:
        first = results.iloc[0]
        center_lat = float(first["lat"])
        center_lon = float(first["lon"])
        selected_label = first.get("name", "Selected school")

    marker_rows = []
    for _, school in results.iterrows():
        if pd.notna(school.get("lat")) and pd.notna(school.get("lon")):
            marker_rows.append(
                {
                    "latitude": float(school["lat"]),
                    "longitude": float(school["lon"]),
                    "label": school.get("name", "School"),
                    "type": "School",
                }
            )

    property_rows = []
    if not pois.empty and center_lat is not None and center_lon is not None:
        property_candidates = pois[pois["lat"].notna() & pois["lon"].notna()].copy()
        property_candidates["property_type"] = property_candidates.apply(
            lambda row: infer_property_type(row.get("name"), row.get("category")), axis=1
        )
        property_candidates["distance_km"] = property_candidates.apply(
            lambda row: haversine_distance(center_lat, center_lon, float(row["lat"]), float(row["lon"])), axis=1
        )
        nearby_properties = property_candidates[property_candidates["distance_km"] <= 1.0]
        for _, row in nearby_properties.iterrows():
            if row["property_type"] == "Other":
                continue
            property_rows.append(
                {
                    "latitude": float(row["lat"]),
                    "longitude": float(row["lon"]),
                    "label": row.get("name", row.get("category", "Property")),
                    "type": row["property_type"],
                }
            )

    map_df = pd.DataFrame(marker_rows + property_rows)
    if not map_df.empty:
        color_map = {
            "School": [59, 130, 246],
            "HDB": [34, 197, 94],
            "Condo": [234, 179, 8],
            "Landed": [249, 115, 22],
        }
        map_df["color"] = map_df["type"].map(color_map).tolist()
        layer = pdk.Layer(
            "ScatterplotLayer",
            data=map_df,
            get_position="[longitude, latitude]",
            get_fill_color="color",
            get_radius=120,
            pickable=True,
            auto_highlight=True,
        )
        view_state = pdk.ViewState(latitude=center_lat, longitude=center_lon, zoom=13, pitch=0)
        deck = pdk.Deck(layers=[layer], initial_view_state=view_state)
        st.pydeck_chart(deck)
        st.caption("School = blue, HDB = green, Condo = yellow, Landed = orange")
        if property_rows:
            st.write(f"Nearby property-like markers shown within 1 km of {selected_label}.")
    else:
        st.warning("No map points available for the selected school.")

from __future__ import annotations

import pandas as pd
import streamlit as st


def render_schools_page(data: dict[str, pd.DataFrame], state: dict) -> None:
    st.header("School Finder")
    st.write("Search for Singapore schools and see nearby ranked institutions.")

    schools = data.get("schools_geocoded", pd.DataFrame())
    if schools.empty:
        st.warning("School ranking data is unavailable.")
        return

    query = st.text_input("Search school by name, programme or special status", value=state.get("school_query", ""), key="school_query")
    mask = schools["name"].fillna("").str.contains(query, case=False, na=False) if query else pd.Series([True] * len(schools))
    results = schools[mask].sort_values("rank").head(20)

    st.markdown(f"### {len(results)} school(s) found")
    for _, school in results.iterrows():
        st.markdown(
            f"**{school.get('name', 'Unknown')}** — Rank {school.get('rank', '-')}, Score {school.get('score', '-')}, Programmes: {school.get('programmes', 'N/A')}"
        )
        if pd.notna(school.get("lat")) and pd.notna(school.get("lon")):
            st.write(f"Location: {school['lat']:.6f}, {school['lon']:.6f}")
        st.markdown("---")

    if not results.empty and pd.notna(results.iloc[0].get("lat")) and pd.notna(results.iloc[0].get("lon")):
        map_df = results.dropna(subset=["lat", "lon"]).rename(columns={"lat": "latitude", "lon": "longitude"})
        st.map(map_df[["latitude", "longitude"]])

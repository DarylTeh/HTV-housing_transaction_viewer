from __future__ import annotations

import pandas as pd
import streamlit as st


def render_map_explorer(data: dict[str, pd.DataFrame], state: dict) -> None:
    st.header("Map Explorer")
    st.write("Visualise nearby schools, supermarkets, hawker centres and other daily-life locations.")

    schools = data.get("schools_geocoded", pd.DataFrame())
    supermarkets = data.get("supermarkets", pd.DataFrame())
    hawkers = data.get("hawker_centres", pd.DataFrame())

    show_schools = st.checkbox("Show schools", value=True)
    show_supermarkets = st.checkbox("Show supermarkets", value=True)
    show_hawker = st.checkbox("Show hawker centres", value=True)

    rows: list[dict[str, float | str]] = []
    if show_schools and not schools.empty:
        rows += [
            {"lat": float(row["lat"]), "lon": float(row["lon"]), "type": "School", "name": row.get("name", "School")}
            for _, row in schools.dropna(subset=["lat", "lon"]).iterrows()
        ]
    if show_supermarkets and not supermarkets.empty:
        rows += [
            {"lat": float(row["lat"]), "lon": float(row["lon"]), "type": "Supermarket", "name": row.get("name", "Supermarket")}
            for _, row in supermarkets.dropna(subset=["lat", "lon"]).iterrows()
        ]
    if show_hawker and not hawkers.empty:
        rows += [
            {"lat": float(row["lat"]), "lon": float(row["lon"]), "type": "Hawker", "name": row.get("name", "Hawker Centre")}
            for _, row in hawkers.dropna(subset=["lat", "lon"]).iterrows()
        ]

    if not rows:
        st.warning("Enable a layer to see map points.")
        return

    map_df = pd.DataFrame(rows)
    st.map(map_df.rename(columns={"lat": "latitude", "lon": "longitude"}))
    st.markdown(f"**Points shown:** {len(map_df)}")

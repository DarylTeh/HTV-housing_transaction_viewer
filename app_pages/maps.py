from __future__ import annotations

import pandas as pd
import pydeck as pdk
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
            {"lat": float(row["lat"]), "lon": float(row["lon"]), "type": "School", "name": row.get("name", "School"), "score": row.get("score", "")}
            for _, row in schools.dropna(subset=["lat", "lon"]).iterrows()
        ]
    if show_supermarkets and not supermarkets.empty:
        rows += [
            {"lat": float(row["lat"]), "lon": float(row["lon"]), "type": "Supermarket", "name": row.get("name", "Supermarket") if pd.notna(row.get("name")) else "Supermarket", "score": ""}
            for _, row in supermarkets.dropna(subset=["lat", "lon"]).iterrows()
        ]
    if show_hawker and not hawkers.empty:
        rows += [
            {"lat": float(row["lat"]), "lon": float(row["lon"]), "type": "Hawker", "name": row.get("name", "Hawker Centre") if pd.notna(row.get("name")) else "Hawker Centre", "score": ""}
            for _, row in hawkers.dropna(subset=["lat", "lon"]).iterrows()
        ]

    if not rows:
        st.warning("Enable a layer to see map points.")
        return

    map_df = pd.DataFrame(rows)
    map_df = map_df.rename(columns={"lat": "latitude", "lon": "longitude"})
    
    color_map = {
        "School": [59, 130, 246],
        "Supermarket": [34, 197, 94],
        "Hawker": [249, 115, 22],
    }
    map_df["color"] = map_df["type"].map(color_map).tolist()
    map_df["score_info"] = map_df.apply(
        lambda row: f"T-Score: {row['score']}" if row["type"] == "School" and pd.notna(row["score"]) and row["score"] != "" else "",
        axis=1
    )
    
    layer = pdk.Layer(
        "ScatterplotLayer",
        data=map_df,
        get_position="[longitude, latitude]",
        get_fill_color="color",
        get_radius=40,
        pickable=True,
        auto_highlight=True,
    )
    
    tooltip = {
        "html": "<b>{name}</b><br/>Type: {type}<br/>{score_info}",
        "style": {
            "backgroundColor": "steelblue",
            "color": "white"
        }
    }
    
    if not map_df.empty:
        center_lat = map_df["latitude"].mean()
        center_lon = map_df["longitude"].mean()
        view_state = pdk.ViewState(latitude=center_lat, longitude=center_lon, zoom=11, pitch=0)
        deck = pdk.Deck(layers=[layer], initial_view_state=view_state, tooltip=tooltip)
        st.pydeck_chart(deck)
        st.caption("School = blue, Supermarket = green, Hawker Centre = orange")
    st.markdown(f"**Points shown:** {len(map_df)}")

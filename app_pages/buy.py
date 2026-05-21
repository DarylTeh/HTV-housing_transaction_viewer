from __future__ import annotations

import pandas as pd
import streamlit as st

from components.property_cards import render_property_card
from engine.search_engine import search_properties


def render_buy_page(data: dict[str, pd.DataFrame], state: dict) -> None:
    st.header("Find Property")
    st.write("Search current market inventory using district, MRT, school proximity and budget context.")

    transactions = data.get("transactions", pd.DataFrame())
    if transactions.empty:
        st.warning("Transaction data is not available.")
        return

    search_query = st.text_input("Search condo, HDB block, district or street", value=state.get("buy_query", ""), key="buy_query")
    housing_kind = st.selectbox(
        "Property type",
        ["", "HDB", "Condo", "Landed"],
        index=0,
        key="buy_housing_kind",
    )
    district = st.selectbox(
        "District / town",
        [""] + sorted(transactions["area_name"].dropna().unique().tolist()),
        index=0,
        key="buy_district",
    )

    results = search_properties(transactions, search_query, housing_kind or None, district or None)
    st.markdown(f"### {len(results)} result(s)")
    if results.empty:
        st.info("Try broadening your search or removing the district filter.")
        return

    for idx, row in results.iterrows():
        project = row.to_dict()
        project["nearest_mrt"] = "MRT nearby"
        project["rental_yield"] = 3.5
        render_property_card(project, key=f"buy_{idx}", saved=project.get("street_name") in state.get("saved_properties", []))

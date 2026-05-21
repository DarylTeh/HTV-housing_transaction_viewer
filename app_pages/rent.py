from __future__ import annotations

import pandas as pd
import streamlit as st

from engine.search_engine import search_properties


def render_rent_page(data: dict[str, pd.DataFrame], state: dict) -> None:
    st.header("Rent Property")
    st.write("Explore rental intelligence for expats, families, students and foreign renters.")

    rent_data = data.get("rent_vs_buy", pd.DataFrame())
    transactions = data.get("transactions", pd.DataFrame())
    if transactions.empty:
        st.warning("Transaction data is unavailable for rental analysis.")
        return

    rent_budget = st.number_input("Target monthly rent (SGD)", min_value=1000.0, value=4000.0, step=100.0, key="rent_budget")
    tenant_profile = st.selectbox("Tenant profile", ["Families", "Students", "Foreigners", "Expats"], index=0)

    st.markdown("### Rent affordability snapshot")
    if not rent_data.empty:
        st.write(rent_data.head(5))

    search_query = st.text_input("Search rental neighbourhood or project", value=state.get("rent_query", ""), key="rent_query")
    results = search_properties(transactions, search_query, top_n=12)
    if results.empty:
        st.info("Enter a rental neighbourhood or property term to see comparable rental opportunities.")
        return

    st.markdown(f"### Suggested rental zones ({len(results)})")
    for idx, row in results.iterrows():
        value = row.to_dict()
        value["nearest_mrt"] = "MRT nearby"
        value["rental_yield"] = round((rent_budget * 12) / (row.get("latest_price", 1) or 1) * 100, 1)
        st.write(f"**{value.get('street_name')}**, {value.get('area_name')} — ~{value['rental_yield']}% yield")

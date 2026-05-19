from __future__ import annotations

import pandas as pd
import streamlit as st

from engine.search_engine import search_properties
from components.common import format_dataframe_prices


def render_compare_page(data: dict[str, pd.DataFrame], state: dict) -> None:
    st.header("Scenario Comparison")
    st.write("Compare saved scenarios and shortlist properties side by side.")

    scenarios = st.session_state.get("saved_scenarios", [])
    if scenarios:
        names = [scenario.get("name", f"Scenario {i+1}") for i, scenario in enumerate(scenarios)]
        selected = st.multiselect("Pick scenarios to compare", names, default=names[:2], key="compare_scenarios")
        chosen = [scenario for scenario in scenarios if scenario.get("name") in selected]
        if len(chosen) >= 2:
            st.dataframe(
                pd.DataFrame(chosen),
                hide_index=True,
                use_container_width=True,
            )
        else:
            st.info("Save at least two scenarios from Affordability to compare them here.")
    else:
        st.info("No saved affordability scenarios yet.")

    st.markdown("---")
    st.subheader("Property comparison")
    transactions = data.get("transactions", pd.DataFrame())
    if transactions.empty:
        st.warning("Transaction data unavailable.")
        return

    query_a = st.text_input("Property A", value=state.get("compare_a", ""), key="compare_a")
    query_b = st.text_input("Property B", value=state.get("compare_b", ""), key="compare_b")
    if query_a and query_b:
        a = search_properties(transactions, query_a, top_n=1)
        b = search_properties(transactions, query_b, top_n=1)
        if not a.empty and not b.empty:
            compare_df = pd.DataFrame([a.iloc[0].to_dict(), b.iloc[0].to_dict()])
            compare_fmt = format_dataframe_prices(compare_df[["street_name", "area_name", "housing_kind", "latest_price", "median_psf"]].copy(), ["latest_price", "median_psf"])
            st.dataframe(compare_fmt, hide_index=True, use_container_width=True)
        else:
            st.warning("Enter two valid property search terms.")

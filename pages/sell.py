from __future__ import annotations

import pandas as pd
import streamlit as st


def render_sell_page(data: dict[str, pd.DataFrame], state: dict) -> None:
    st.header("Sell Property")
    st.write("Estimate resale potential by looking at recent transaction activity and neighbourhood momentum.")

    price_medians = data.get("price_medians", pd.DataFrame())
    transactions = data.get("transactions", pd.DataFrame())
    if price_medians.empty or transactions.empty:
        st.warning("Market data for sell analysis is unavailable.")
        return

    district = st.selectbox(
        "Focus on town / area",
        [""] + sorted(price_medians["area_name"].dropna().unique().tolist()),
        index=0,
        key="sell_area",
    )

    filtered = price_medians if not district else price_medians[price_medians["area_name"] == district]
    latest = filtered[filtered["year"] == filtered["year"].max()]
    st.markdown("### Latest median prices")
    st.dataframe(latest.head(10))

    if district:
        town_tx = transactions[transactions["area_name"] == district]
        st.markdown(f"### Recent transactions in {district}")
        st.dataframe(town_tx.sort_values("transaction_date", ascending=False).head(10))

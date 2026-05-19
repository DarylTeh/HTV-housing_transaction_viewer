from __future__ import annotations

import pandas as pd
import streamlit as st

from engine.trend_engine import market_trend_chart, rent_vs_buy_chart, transaction_volume_price_chart
from components.common import format_dataframe_prices


def render_trends_page(data: dict[str, pd.DataFrame], state: dict) -> None:
    st.header("Market Trends")
    st.write("View headline pricing, rent, and appreciation momentum across Singapore.")

    price_medians = data.get("price_medians", pd.DataFrame())
    rent_vs_buy = data.get("rent_vs_buy", pd.DataFrame())
    if price_medians.empty and rent_vs_buy.empty:
        st.warning("Trend data is not available.")
        return

    if not price_medians.empty:
        st.subheader("Price trend overview")
        st.plotly_chart(market_trend_chart(price_medians), use_container_width=True)

    housing_kind = st.selectbox(
        "Housing type for transaction trend",
        ["All", "HDB", "Condo", "Landed"],
        index=0,
        key="trend_housing_kind",
    )
    selected_kind = None if housing_kind == "All" else housing_kind
    st.subheader("Monthly volume and average price")
    st.plotly_chart(
        transaction_volume_price_chart(data.get("transactions", pd.DataFrame()), selected_kind),
        use_container_width=True,
    )

    if not rent_vs_buy.empty:
        st.subheader("Rent versus mortgage cost")
        st.plotly_chart(rent_vs_buy_chart(rent_vs_buy), use_container_width=True)

    if not price_medians.empty:
        latest = price_medians[price_medians["year"] == price_medians["year"].max()]
        st.metric("Latest median listings", len(latest))
        latest_fmt = format_dataframe_prices(latest.head(5), ["median_price", "price"])
        st.write(latest_fmt)

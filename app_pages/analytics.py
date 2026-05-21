from __future__ import annotations

import pandas as pd
import streamlit as st

from components.analytics_charts import line_chart
from components.common import format_dataframe_prices, format_price, format_currency
from engine.transaction_engine import project_history, project_metrics


def render_analytics_page(data: dict[str, pd.DataFrame], state: dict) -> None:
    st.header("Project Analytics")
    st.write("Inspect lifetime transaction history and market behaviour for a selected property.")

    transactions = data.get("transactions", pd.DataFrame())
    if transactions.empty:
        st.warning("Transaction history is unavailable.")
        return

    # Build typable dropdown options from transactions to help users find exact projects
    street_names = transactions["street_name"].dropna().astype(str).unique().tolist()
    area_names = transactions["area_name"].dropna().astype(str).unique().tolist()
    combo = set()
    for s in street_names:
        combo.add(s)
    for s in street_names:
        # include street + area combo where available
        area = transactions[transactions["street_name"].astype(str) == s]["area_name"].dropna().astype(str).unique()
        if len(area) > 0:
            combo.add(f"{s} — {area[0]}")
    options = [""] + sorted(combo)
    project_query = st.selectbox("Search a project or street", options, index=0, key="analytics_query")
    if not project_query:
        st.info("Select a property name, town or street to begin.")
        return
    # If user picked a combo like 'Street — Area', use the street portion for history lookup
    if " — " in project_query:
        project_query = project_query.split(" — ")[0]

    history = project_history(transactions, project_query)
    if history.empty:
        st.warning("No transactions found for that query.")
        return

    metrics = project_metrics(history)
    cols = st.columns(4)
    cols[0].metric("Transactions", metrics.get("transactions", 0))
    cols[1].metric("Latest price", format_price(metrics.get("latest_price", None)))
    cols[2].metric("Avg psf", format_price(metrics.get("average_psf", None)))
    cols[3].metric("Appreciation", f"{metrics.get('appreciation_pct', 0):.1f}%")

    monthly = (
        history.groupby(history["transaction_date"].dt.to_period("M")).agg(
            average_price=("price", "mean"), transactions=("price", "count")
        ).reset_index()
    )
    monthly["transaction_date"] = monthly["transaction_date"].dt.to_timestamp()

    st.plotly_chart(line_chart(monthly, x="transaction_date", y="average_price", title="Average transaction price over time"), use_container_width=True)
    st.plotly_chart(line_chart(monthly, x="transaction_date", y="transactions", title="Transaction count over time"), use_container_width=True)
    st.markdown("### Recent transactions")
    recent = (
        history[["transaction_date", "price", "size_sqm", "lease_remaining", "housing_kind"]]
        .sort_values("transaction_date", ascending=False)
        .head(20)
    )
    recent_fmt = format_dataframe_prices(recent, ["price"])
    st.dataframe(recent_fmt, hide_index=True, use_container_width=True)

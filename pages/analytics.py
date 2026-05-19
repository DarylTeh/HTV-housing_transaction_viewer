from __future__ import annotations

import pandas as pd
import streamlit as st

from components.analytics_charts import line_chart
from engine.transaction_engine import project_history, project_metrics


def render_analytics_page(data: dict[str, pd.DataFrame], state: dict) -> None:
    st.header("Project Analytics")
    st.write("Inspect lifetime transaction history and market behaviour for a selected property.")

    transactions = data.get("transactions", pd.DataFrame())
    if transactions.empty:
        st.warning("Transaction history is unavailable.")
        return

    project_query = st.text_input("Search a project or street", value=state.get("analytics_query", ""), key="analytics_query")
    if not project_query:
        st.info("Enter a property name, town or street to begin.")
        return

    history = project_history(transactions, project_query)
    if history.empty:
        st.warning("No transactions found for that query.")
        return

    metrics = project_metrics(history)
    cols = st.columns(4)
    cols[0].metric("Transactions", metrics.get("transactions", 0))
    cols[1].metric("Latest price", f"${metrics.get('latest_price', 0):,.0f}")
    cols[2].metric("Avg psf", f"${metrics.get('average_psf', 0):,.0f}")
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
    st.dataframe(history[["transaction_date", "price", "size_sqm", "lease_remaining", "housing_kind"]].sort_values("transaction_date", ascending=False).head(20))

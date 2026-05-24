from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from engine.transaction_engine import project_history, project_metrics
from components.common import format_price
from components.analytics_charts import line_chart


def render_compare_page(data: dict[str, pd.DataFrame], state: dict) -> None:
    st.header("Scenario Comparison")
    st.write("Compare transaction trends for multiple properties side by side.")

    transactions = data.get("transactions", pd.DataFrame())
    if transactions.empty:
        st.warning("Transaction data unavailable.")
        return

    saved_properties = st.session_state.get("saved_properties", [])
    
    st.subheader("Select Properties to Compare")
    
    # Allow selecting 2-3 properties
    num_properties = st.radio("Number of properties to compare", [2, 3], index=0, horizontal=True, key="compare_num_properties")
    
    selected_properties = []
    colors = ["#3b82f6", "#10b981", "#f59e0b"]  # Blue, Green, Orange
    
    for i in range(num_properties):
        col1, col2 = st.columns([0.7, 0.3])
        with col1:
            if saved_properties:
                selected = st.selectbox(
                    f"Property {i + 1}",
                    options=[""] + saved_properties,
                    index=0,
                    key=f"compare_property_{i}"
                )
            else:
                selected = st.text_input(f"Property {i + 1} (street name)", key=f"compare_property_text_{i}")
        
        with col2:
            st.markdown(f'<div style="background-color: {colors[i]}; width: 30px; height: 30px; border-radius: 50%; margin-top: 25px;"></div>', unsafe_allow_html=True)
        
        if selected:
            selected_properties.append(selected)
    
    # Only show comparison if we have at least 2 properties selected
    if len(selected_properties) >= 2:
        st.markdown("---")
        st.subheader("Transaction Trend Comparison")
        
        # Get transaction history for each property
        all_histories = []
        valid_properties = []
        
        for idx, prop in enumerate(selected_properties):
            history = project_history(transactions, prop)
            if not history.empty:
                all_histories.append(history)
                valid_properties.append((prop, colors[idx]))
        
        if len(valid_properties) >= 2:
            # Create a combined chart with all properties
            fig = go.Figure()
            
            for prop_name, color in valid_properties:
                history = project_history(transactions, prop_name)
                monthly = (
                    history.groupby(history["transaction_date"].dt.to_period("M")).agg(
                        average_price=("price", "mean"), transactions=("price", "count")
                    ).reset_index()
                )
                monthly["transaction_date"] = monthly["transaction_date"].dt.to_timestamp()
                
                fig.add_trace(
                    go.Scatter(
                        x=monthly["transaction_date"],
                        y=monthly["average_price"],
                        mode="lines+markers",
                        name=prop_name,
                        line=dict(color=color, width=3),
                        marker=dict(size=8),
                    )
                )
            
            fig.update_layout(
                title="Transaction Price Trends Comparison",
                xaxis_title="Date",
                yaxis_title="Average Price (SGD)",
                hovermode="x unified",
                template="plotly_white",
                legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
            )
            
            st.plotly_chart(fig, use_container_width=True)
            
            # Show metrics comparison table
            st.subheader("Metrics Comparison")
            metrics_data = []
            for prop_name, color in valid_properties:
                history = project_history(transactions, prop_name)
                metrics = project_metrics(history)
                metrics_data.append({
                    "Property": prop_name,
                    "Transactions": metrics.get("transactions", 0),
                    "Latest Price": format_price(metrics.get("latest_price", None)),
                    "Avg PSF": format_price(metrics.get("average_psf", None)),
                    "Appreciation": f"{metrics.get('appreciation_pct', 0):.1f}%",
                })
            
            metrics_df = pd.DataFrame(metrics_data)
            st.dataframe(metrics_df, hide_index=True, use_container_width=True)
            
            # Show recent transactions for each property
            st.subheader("Recent Transactions")
            for prop_name, color in valid_properties:
                st.markdown(f"### {prop_name}")
                history = project_history(transactions, prop_name)
                recent = (
                    history[["transaction_date", "price", "size_sqm", "lease_remaining", "housing_kind"]]
                    .sort_values("transaction_date", ascending=False)
                    .head(10)
                )
                st.dataframe(recent, hide_index=True, use_container_width=True)
                st.markdown("---")
        else:
            st.warning("Could not find transaction data for at least 2 of the selected properties. Try different property names.")
    else:
        st.info("Select at least 2 properties to compare their transaction trends.")

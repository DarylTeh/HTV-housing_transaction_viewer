from __future__ import annotations

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots


def market_trend_chart(price_medians: pd.DataFrame) -> px.line:
    if price_medians.empty:
        return px.line()
    latest = price_medians.sort_values(["housing_kind", "year"])
    fig = px.line(latest, x="year", y="median_price", color="housing_kind", title="Median price trend by housing type")
    fig.update_layout(hovermode="x unified", template="plotly_white")
    return fig


def historical_median_chart(transactions: pd.DataFrame) -> px.line:
    if transactions.empty:
        return px.line()

    df = transactions.copy()
    if "transaction_date" in df.columns:
        df["transaction_date"] = pd.to_datetime(df["transaction_date"], errors="coerce")
    df = df.dropna(subset=["transaction_date", "price", "housing_kind"])
    df["year"] = df["transaction_date"].dt.year
    df = df[df["year"].notna()]
    if df.empty:
        return px.line()

    summary = (
        df.groupby(["year", "housing_kind"], as_index=False)["price"]
        .median()
        .rename(columns={"price": "median_price"})
        .sort_values(["housing_kind", "year"])
    )
    fig = px.line(
        summary,
        x="year",
        y="median_price",
        color="housing_kind",
        title="Median transaction price by housing type over time",
        markers=True,
    )
    fig.update_layout(
        hovermode="x unified",
        template="plotly_white",
        xaxis_title="Year",
        yaxis_title="Median transaction price (SGD)",
    )
    return fig


def rent_vs_buy_chart(timeline: pd.DataFrame) -> px.line:
    if timeline.empty:
        return px.line()
    fig = px.line(timeline, x="year", y=["monthly_rent", "monthly_instalment"], title="Rent vs Buy monthly cashflow")
    fig.update_layout(hovermode="x unified", template="plotly_white")
    return fig


def transaction_volume_price_chart(transactions: pd.DataFrame, housing_kind: str | None = None) -> go.Figure:
    if transactions.empty:
        return go.Figure()

    df = transactions.copy()
    if "transaction_date" in df.columns:
        df["transaction_date"] = pd.to_datetime(df["transaction_date"], errors="coerce")
    if housing_kind:
        df = df[df["housing_kind"] == housing_kind]
    df = df.dropna(subset=["transaction_date"])
    if df.empty:
        return go.Figure()

    df["month"] = df["transaction_date"].dt.to_period("M").dt.to_timestamp()
    monthly = (
        df.groupby("month", dropna=False)
        .agg(volume=("price", "count"), average_price=("price", "mean"))
        .reset_index()
        .sort_values("month")
    )
    if monthly.empty:
        return go.Figure()

    fig = make_subplots(specs=[[{"secondary_y": True}]])
    fig.add_bar(
        x=monthly["month"],
        y=monthly["volume"],
        name="Transaction volume",
        marker_color="#3b82f6",
        opacity=0.75,
    )
    fig.add_trace(
        go.Scatter(
            x=monthly["month"],
            y=monthly["average_price"],
            name="Average price",
            line=dict(color="#111827", width=3),
            mode="lines+markers",
        ),
        secondary_y=True,
    )
    fig.update_layout(
        title_text="Monthly transaction volume and average price",
        hovermode="x unified",
        template="plotly_white",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
    )
    fig.update_xaxes(title_text="Month")
    fig.update_yaxes(title_text="Transactions", secondary_y=False)
    fig.update_yaxes(title_text="Average price (SGD)", secondary_y=True)
    return fig

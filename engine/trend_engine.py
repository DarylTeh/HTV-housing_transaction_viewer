from __future__ import annotations

import pandas as pd
import plotly.express as px


def market_trend_chart(price_medians: pd.DataFrame) -> px.line:
    if price_medians.empty:
        return px.line()
    latest = (
        price_medians.sort_values(["housing_kind", "year"])
        .groupby("housing_kind", group_keys=False)
        .tail(100)
    )
    fig = px.line(latest, x="year", y="median_price", color="housing_kind", title="Median price trend by housing type")
    fig.update_layout(hovermode="x unified", template="plotly_white")
    return fig


def rent_vs_buy_chart(timeline: pd.DataFrame) -> px.line:
    if timeline.empty:
        return px.line()
    fig = px.line(timeline, x="year", y=["monthly_rent", "monthly_instalment"], title="Rent vs Buy monthly cashflow")
    fig.update_layout(hovermode="x unified", template="plotly_white")
    return fig

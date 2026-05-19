from __future__ import annotations

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go


def line_chart(df: pd.DataFrame, x: str, y: str, color: str | None = None, title: str | None = None) -> go.Figure:
    if df.empty:
        return go.Figure()
    fig = px.line(df, x=x, y=y, color=color, title=title, markers=True)
    fig.update_layout(hovermode="x unified", template="plotly_white")
    return fig


def area_chart(df: pd.DataFrame, x: str, y: str, title: str | None = None) -> go.Figure:
    if df.empty:
        return go.Figure()
    fig = px.area(df, x=x, y=y, title=title)
    fig.update_traces(line=dict(color="#4f46e5"))
    fig.update_layout(hovermode="x unified", template="plotly_white")
    return fig


def bar_chart(df: pd.DataFrame, x: str, y: str, title: str | None = None) -> go.Figure:
    if df.empty:
        return go.Figure()
    fig = px.bar(df, x=x, y=y, title=title)
    fig.update_layout(template="plotly_white")
    return fig

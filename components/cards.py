from __future__ import annotations
import streamlit as st


def metric_card(label: str, value: str, delta: str | None = None, help_text: str | None = None) -> None:
    with st.expander(label if help_text else label, expanded=False):
        st.metric(label, value, delta=delta)
        if help_text:
            st.caption(help_text)


def show_summary_cards(metrics: list[tuple[str, str, str | None, str | None]]) -> None:
    cols = st.columns(min(len(metrics), 4))
    for column, metric in zip(cols, metrics):
        label, value, delta, help_text = metric
        with column:
            st.metric(label, value, delta)
            if help_text:
                st.caption(help_text)

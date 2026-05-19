from __future__ import annotations
import streamlit as st


def show_warning_list(warnings: list[str]) -> None:
    if not warnings:
        st.success("No immediate warnings detected.")
        return
    for warning in warnings:
        if "not fully met" in warning or "exceeds" in warning or "insufficient" in warning:
            st.error(warning)
        else:
            st.warning(warning)

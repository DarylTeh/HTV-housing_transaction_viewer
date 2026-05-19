from __future__ import annotations

import streamlit as st
from components.common import format_price


def render_saved_page(data: dict[str, object], state: dict) -> None:
    st.header("Saved Properties & Scenarios")
    st.write("Keep track of your shortlisted homes and planning scenarios in one place.")

    saved_properties = st.session_state.setdefault("saved_properties", [])
    saved_scenarios = st.session_state.setdefault("saved_scenarios", [])

    st.subheader("Saved properties")
    if saved_properties:
        for idx, item in enumerate(saved_properties):
            cols = st.columns([0.9, 0.1])
            cols[0].write(item)
            if cols[1].button("Remove", key=f"remove_property_{idx}"):
                saved_properties.pop(idx)
    else:
        st.info("No saved properties yet.")

    st.markdown("---")
    st.subheader("Saved scenarios")
    if saved_scenarios:
        for idx, scenario in enumerate(saved_scenarios):
            cols = st.columns([0.8, 0.2])
            cols[0].write(f"{scenario.get('name', 'Unnamed')} — {scenario.get('property_type', '')} at {format_price(scenario.get('purchase_price', None))}")
            if cols[1].button("Remove", key=f"remove_scenario_{idx}"):
                saved_scenarios.pop(idx)
    else:
        st.info("No saved scenarios yet.")

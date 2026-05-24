from __future__ import annotations

import streamlit as st


def render_property_card(project: dict, key: str, saved: bool = False) -> None:
    title = f"{project.get('street_name', 'Unknown')} — {project.get('area_name', '')}"
    housing_kind = project.get('housing_kind', '')
    # No images available in dataset — show numeric/textual details only
    cols = st.columns([0.75, 0.25])
    with cols[0]:
        st.markdown(f"### {title}")
        st.markdown(
            """
**Type:** %(housing_kind)s  
**Latest price:** %(price)s  
**Median psf:** %(psf)s  
**Latest tx date:** %(date)s  
**Nearby MRT:** %(mrt)s
            """ % {
                "housing_kind": housing_kind,
                "price": project.get("latest_price_fmt", "-"),
                "psf": project.get("median_psf_fmt", "-"),
                "date": project.get("latest_transaction_date", "-"),
                "mrt": project.get("nearest_mrt", "N/A"),
            }
        )
        if project.get("rental_yield") is not None:
            st.markdown(f"**Estimated yield:** {project['rental_yield']:.1f}%")
    with cols[1]:
        if st.button("View Analytics", key=f"analytics_{key}"):
            st.session_state["selected_property"] = title
            st.session_state["selected_page"] = "Project Analytics"
        if st.button("Save", key=f"save_{key}"):
            saved_list = st.session_state.setdefault("saved_properties", [])
            if title not in saved_list:
                saved_list.append(title)
                st.success(f"Saved {title}")
        if saved:
            st.markdown("✅ Saved")

"""Guided first-time buyer journey (optional story mode)."""

from __future__ import annotations

import streamlit as st

STORY_STEPS = [
    "welcome",
    "residency",
    "rent_or_buy",
    "property_focus",
    "summary",
]

BUYER_TIPS = {
    ("Singapore Citizen", "No"): (
        "As a citizen with no existing HDB, you can buy HDB resale or BTO subject to eligibility schemes, "
        "or private property with standard ABSD on later homes."
    ),
    ("Singapore Citizen", "Yes"): (
        "If you already own HDB, you usually must sell it before buying private property, and additional "
        "stamp duties may apply."
    ),
    ("Permanent Resident", "No"): (
        "PRs can buy resale HDB (with an eligible SC household member) or private property, but face higher "
        "ABSD than citizens."
    ),
    ("Permanent Resident", "Yes"): (
        "PRs who own HDB face the same disposal rules as citizens before upgrading to private housing."
    ),
    ("Foreigner", "No"): (
        "Foreigners generally cannot buy HDB resale flats. Private condos are possible but ABSD is much higher."
    ),
    ("Foreigner", "Yes"): (
        "Foreigners cannot own HDB. Check your existing property status with HDB or a licensed property lawyer."
    ),
}

HDB_FLAT_TYPES = ["1 ROOM", "2 ROOM", "3 ROOM", "4 ROOM", "5 ROOM", "EXECUTIVE", "MULTI-GENERATION"]
PRIVATE_TYPES = [
    "Apartment",
    "Condominium",
    "Executive Condominium",
    "Terrace House",
    "Semi-Detached House",
    "Detached House",
    "Terrace",
    "Semi-detached",
]


def init_story_state():
    defaults = {
        "journey_mode": None,
        "story_step": 0,
        "residency": "Singapore Citizen",
        "own_hdb": "No",
        "rent_or_buy": "Still deciding",
        "property_focus": "Both HDB and private",
        "first_property": "Yes — first property",
        "story_complete": False,
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


def render_journey_picker() -> str | None:
    st.subheader("How would you like to explore?")
    c1, c2 = st.columns(2)
    with c1:
        if st.button("📖 Start guided journey", use_container_width=True, type="primary"):
            st.session_state.journey_mode = "guided"
            st.session_state.story_step = 0
            st.session_state.story_complete = False
            st.rerun()
    with c2:
        if st.button("🗺️ Explore on my own", use_container_width=True):
            st.session_state.journey_mode = "explore"
            st.session_state.story_complete = True
            st.rerun()
    return st.session_state.get("journey_mode")


def render_story_step():
    step = st.session_state.story_step
    total = len(STORY_STEPS) - 1
    st.progress(min(step / total, 1.0) if total else 0.0)

    if step == 0:
        st.markdown("### Chapter 1 — Welcome")
        st.write(
            "This short journey helps you filter **real Singapore transaction data** to match your situation. "
            "You can change answers anytime from the sidebar."
        )
        st.info("Tip: Median prices are typical mid-points — half of sales were higher, half were lower.")

    elif step == 1:
        st.markdown("### Chapter 2 — Your residency & housing today")
        st.session_state.residency = st.radio(
            "What is your residency status in Singapore?",
            ["Singapore Citizen", "Permanent Resident", "Foreigner"],
        )
        st.session_state.own_hdb = st.radio("Do you currently own an HDB flat?", ["No", "Yes"])
        tip = BUYER_TIPS.get((st.session_state.residency, st.session_state.own_hdb))
        if tip:
            st.info(tip)

    elif step == 2:
        st.markdown("### Chapter 3 — Rent or buy?")
        st.session_state.rent_or_buy = st.radio(
            "What are you considering right now?",
            ["Rent", "Buy", "Still deciding"],
            help="Rent: focus on monthly cash flow. Buy: prices, loans, ABSD. Still deciding: show both.",
        )

    elif step == 3:
        st.markdown("### Chapter 4 — What housing are you curious about?")
        options = ["HDB only", "Private only", "Both HDB and private"]
        if st.session_state.residency == "Foreigner":
            options = ["Private only"]
            st.session_state.property_focus = "Private only"
            st.warning("Foreigners generally cannot purchase HDB resale flats.")
        else:
            st.session_state.property_focus = st.radio("Which market should we focus on?", options)
        st.session_state.first_property = st.radio(
            "Will this be your first property purchase in Singapore?",
            ["Yes — first property", "No — I already own property"],
        )

    elif step >= 4:
        st.markdown("### Chapter 5 — Your story so far")
        st.write(
            f"- **Status:** {st.session_state.residency} · Own HDB: **{st.session_state.own_hdb}**\n"
            f"- **Goal:** {st.session_state.rent_or_buy}\n"
            f"- **Focus:** {st.session_state.property_focus}\n"
            f"- **Purchase:** {st.session_state.first_property}"
        )
        st.success("Scroll down to see charts and tools matched to your choices.")

    nav1, nav2, nav3 = st.columns([1, 1, 2])
    with nav1:
        if step > 0 and st.button("← Back"):
            st.session_state.story_step -= 1
            st.rerun()
    with nav2:
        if step < len(STORY_STEPS) - 1 and st.button("Next →"):
            st.session_state.story_step += 1
            st.rerun()
        elif step >= len(STORY_STEPS) - 1 and st.button("Start exploring"):
            st.session_state.story_complete = True
            st.rerun()
    with nav3:
        if st.button("Skip to full dashboard"):
            st.session_state.story_complete = True
            st.session_state.journey_mode = "explore"
            st.rerun()


def story_default_property_types(df, property_options: list[str]) -> list[str]:
    focus = st.session_state.get("property_focus", "Both HDB and private")
    hdb = [p for p in property_options if p in HDB_FLAT_TYPES or p == "HDB"]
    private = [p for p in property_options if p in PRIVATE_TYPES or p == "Private Property"]
    if focus == "HDB only":
        chosen = hdb
    elif focus == "Private only":
        chosen = private
    else:
        chosen = hdb[:3] + [p for p in ["Condominium", "Apartment"] if p in property_options]
    return chosen or property_options[: min(3, len(property_options))]


def apply_story_filters(df):
    """Return dataframe filtered by story choices."""
    out = df.copy()
    if st.session_state.get("residency") == "Foreigner":
        out = out[out["dataset"] != "HDB Resale"]
    focus = st.session_state.get("property_focus", "Both HDB and private")
    if focus == "HDB only":
        out = out[out["dataset"] == "HDB Resale"]
    elif focus == "Private only":
        out = out[out["dataset"] == "Private Property"]
    return out


def absd_tier_from_story() -> str:
    if st.session_state.get("first_property", "").startswith("Yes"):
        return "1st"
    return "2nd"

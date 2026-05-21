from __future__ import annotations

import pandas as pd
import pydeck as pdk
import streamlit as st

from engine.trend_engine import market_trend_chart, rent_vs_buy_chart, transaction_volume_price_chart
from components.common import format_dataframe_prices


def get_property_details(transactions: pd.DataFrame, housing_kind: str | None = None, street_name: str | None = None) -> pd.DataFrame:
    """Get property details filtered by housing kind and/or street name."""
    filtered = transactions.copy()
    
    if housing_kind and housing_kind != "All":
        filtered = filtered[filtered["housing_kind"] == housing_kind]
    
    if street_name:
        filtered = filtered[filtered["street_name"].fillna("").str.contains(street_name, case=False, na=False)]
    
    # Get latest year data
    if not filtered.empty:
        latest_year = filtered["year"].max()
        filtered = filtered[filtered["year"] == latest_year]
    
    return filtered


def render_trends_page(data: dict[str, pd.DataFrame], state: dict) -> None:
    st.header("Market Trends")
    st.write("View headline pricing, rent, and appreciation momentum across Singapore.")

    price_medians = data.get("price_medians", pd.DataFrame())
    rent_vs_buy = data.get("rent_vs_buy", pd.DataFrame())
    transactions = data.get("transactions", pd.DataFrame())
    
    if price_medians.empty and rent_vs_buy.empty and transactions.empty:
        st.warning("Trend data is not available.")
        return

    if not price_medians.empty:
        st.subheader("Price trend overview")
        st.plotly_chart(market_trend_chart(price_medians), use_container_width=True)

    st.subheader("Transaction Analysis by Property Type")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        housing_kind = st.selectbox(
            "Housing type",
            ["All", "HDB", "Condo", "Landed"],
            index=0,
            key="trend_housing_kind",
        )
    
    selected_kind = None if housing_kind == "All" else housing_kind
    
    # Show volume and price chart
    st.subheader("Monthly volume and average price")
    st.plotly_chart(
        transaction_volume_price_chart(transactions, selected_kind),
        use_container_width=True,
    )

    # Property-level search and map
    st.subheader(f"Explore {housing_kind} Properties")
    
    col1, col2 = st.columns(2)
    with col1:
        search_street = st.text_input(
            f"Search {housing_kind} property by street/area name",
            value=state.get("trend_property_search", ""),
            key="trend_property_search",
            placeholder="e.g., Tampines, Jurong, Ang Mo Kio"
        )
    
    with col2:
        limit = st.slider("Number of properties to show on map", 10, 500, 100, key="trend_map_limit")
    
    # Get filtered properties
    if not transactions.empty:
        filtered_props = get_property_details(transactions, selected_kind, search_street if search_street else None)
        
        if not filtered_props.empty:
            # Filter to only properties with geocoding
            props_with_coords = filtered_props[filtered_props["lat"].notna() & filtered_props["lon"].notna()].copy()
            
            if not props_with_coords.empty:
                props_with_coords = props_with_coords.head(limit)
                
                # Display stats
                col1, col2, col3, col4 = st.columns(4)
                with col1:
                    st.metric("Properties Found", len(filtered_props))
                with col2:
                    st.metric("Avg Price", f"${filtered_props['price'].mean()/1e6:.1f}M")
                with col3:
                    st.metric("Median Price", f"${filtered_props['price'].median()/1e6:.1f}M")
                with col4:
                    st.metric("Avg Size", f"{filtered_props['size_sqm'].mean():.0f} sqm")
                
                # Show map
                st.markdown("**Property Map** — Click on properties to see details")
                
                map_data = props_with_coords[["lat", "lon", "street_name", "price", "size_sqm", "area_name"]].copy()
                map_data.columns = ["latitude", "longitude", "street", "price", "size_sqm", "area"]
                map_data["label"] = (
                    map_data["street"] + " • " +
                    map_data["area"] + " • $" +
                    (map_data["price"] / 1e6).round(1).astype(str) + "M"
                )
                
                if not map_data.empty and map_data["latitude"].notna().any():
                    # Color code by price range
                    min_price = filtered_props["price"].min()
                    max_price = filtered_props["price"].max()
                    price_range = max_price - min_price
                    
                    def get_price_color(price):
                        if price_range == 0:
                            return [52, 168, 224]
                        normalized = (price - min_price) / price_range
                        # Green (low price) to Red (high price)
                        r = int(255 * normalized)
                        g = int(100 * (1 - normalized))
                        b = int(100 - 50 * normalized)
                        return [r, g, b]
                    
                    map_data["color"] = map_data["price"].apply(get_price_color)
                    
                    layer = pdk.Layer(
                        "ScatterplotLayer",
                        data=map_data,
                        get_position="[longitude, latitude]",
                        get_fill_color="color",
                        get_radius=100,
                        pickable=True,
                        auto_highlight=True,
                    )
                    
                    tooltip = {
                        "html": "<b>{label}</b><br/>Size: {size_sqm} sqm<br/>Price: ${price}",
                        "style": {
                            "backgroundColor": "steelblue",
                            "color": "white",
                            "padding": "10px",
                            "borderRadius": "5px",
                        }
                    }
                    
                    center_lat = map_data["latitude"].mean()
                    center_lon = map_data["longitude"].mean()
                    
                    view_state = pdk.ViewState(latitude=center_lat, longitude=center_lon, zoom=11, pitch=0)
                    deck = pdk.Deck(layers=[layer], initial_view_state=view_state, tooltip=tooltip)
                    st.pydeck_chart(deck)
                    
                    st.caption("🟢 Lower price  •  🔴 Higher price")
                    
                    # Show detailed table
                    st.markdown("**Property Details**")
                    display_df = props_with_coords[[
                        "street_name", "area_name", "price", "size_sqm", "transaction_date"
                    ]].copy().reset_index(drop=True)
                    display_df.columns = ["Street", "Area", "Price ($)", "Size (sqm)", "Transaction Date"]
                    display_df["Price ($)"] = display_df["Price ($)"].apply(lambda x: f"${x/1e6:.2f}M" if pd.notna(x) else "N/A")
                    display_df["Size (sqm)"] = display_df["Size (sqm)"].apply(lambda x: f"{x:.0f}" if pd.notna(x) else "N/A")
                    st.dataframe(display_df, use_container_width=True)
                else:
                    st.warning(f"No geocoded properties found. Available properties: {len(filtered_props)} (not mapped)")
            else:
                st.info(f"{housing_kind} properties found: {len(filtered_props)}, but none have location data.")
        else:
            st.info(f"No {housing_kind} properties found matching '{search_street}'. Try a different search term.")
    else:
        st.warning("Transaction data not available.")

    if not rent_vs_buy.empty:
        st.subheader("Rent versus mortgage cost")
        st.plotly_chart(rent_vs_buy_chart(rent_vs_buy), use_container_width=True)

    if not price_medians.empty:
        latest = price_medians[price_medians["year"] == price_medians["year"].max()]
        st.metric("Latest median listings", len(latest))
        latest_fmt = format_dataframe_prices(latest.head(5), ["median_price", "price"])
        st.write(latest_fmt)

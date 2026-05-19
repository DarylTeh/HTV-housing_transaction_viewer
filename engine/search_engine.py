from __future__ import annotations

import pandas as pd
import re
from components.common import format_price


def _normalize(text: str | float | int | None) -> str:
    if text is None or text != text:
        return ""
    return str(text).strip().lower()


def _psf_from_sqm(price: float, sqm: float) -> float | None:
    if sqm and sqm > 0:
        return price / (sqm * 10.7639)
    return None


def build_property_catalog(transactions: pd.DataFrame) -> pd.DataFrame:
    if transactions.empty:
        return pd.DataFrame()
    df = transactions.copy()
    if "transaction_date" in df.columns:
        df["transaction_date"] = pd.to_datetime(df["transaction_date"], errors="coerce")
    group_cols = ["street_name", "area_name", "housing_kind"]
    summary = (
        df.groupby(group_cols, dropna=False)
        .agg(
            transaction_count=("price", "count"),
            latest_date=("transaction_date", "max"),
            latest_price=("price", "last"),
            average_price=("price", "mean"),
            average_size=("size_sqm", "mean"),
        )
        .reset_index()
    )
    summary["median_psf"] = summary.apply(
        lambda row: _psf_from_sqm(row["average_price"], row["average_size"]), axis=1
    )
    summary["latest_transaction_date"] = summary["latest_date"].dt.strftime("%Y-%m-%d")
    summary["latest_price_fmt"] = summary["latest_price"].apply(lambda v: format_price(v))
    summary["median_psf_fmt"] = summary["median_psf"].apply(lambda v: format_price(v))
    return summary.sort_values(["transaction_count", "latest_date"], ascending=[False, False])


def search_properties(
    transactions: pd.DataFrame,
    query: str = "",
    housing_kind: str | None = None,
    district: str | None = None,
    top_n: int = 24,
) -> pd.DataFrame:
    catalog = build_property_catalog(transactions)
    if catalog.empty:
        return catalog
    query = query.strip().lower()
    if query:
        tokens = re.split(r"\s+", query)
        mask = pd.Series(False, index=catalog.index)
        for token in tokens:
            token_mask = (
                catalog["street_name"].fillna("").str.lower().str.contains(token)
                | catalog["area_name"].fillna("").str.lower().str.contains(token)
                | catalog["housing_kind"].fillna("").str.lower().str.contains(token)
            )
            mask = mask | token_mask
        catalog = catalog[mask]
    if housing_kind:
        catalog = catalog[catalog["housing_kind"] == housing_kind]
    if district:
        catalog = catalog[catalog["area_name"] == district]
    return catalog.head(top_n)

from __future__ import annotations

import pandas as pd


def recommend_properties(transactions: pd.DataFrame, budget: float, top_n: int = 5) -> list[dict[str, object]]:
    if transactions.empty or budget <= 0:
        return []
    group = (
        transactions.groupby(["street_name", "area_name", "housing_kind"], dropna=False)
        .agg(latest_price=("price", "max"), transaction_count=("price", "count"))
        .reset_index()
    )
    candidates = group[group["latest_price"] <= budget].sort_values(["transaction_count", "latest_price"], ascending=[False, False]).head(top_n)
    return candidates.to_dict(orient="records")

from __future__ import annotations

import pandas as pd


def _ensure_date(df: pd.DataFrame) -> pd.DataFrame:
    if "transaction_date" in df.columns and not pd.api.types.is_datetime64_any_dtype(df["transaction_date"]):
        df = df.copy()
        df["transaction_date"] = pd.to_datetime(df["transaction_date"], errors="coerce")
    return df


def project_history(transactions: pd.DataFrame, project_query: str) -> pd.DataFrame:
    if transactions.empty or not project_query:
        return pd.DataFrame()
    df = _ensure_date(transactions)
    query = project_query.strip().lower()
    mask = (
        df["street_name"].fillna("").str.lower().str.contains(query)
        | df["area_name"].fillna("").str.lower().str.contains(query)
    )
    result = df[mask].copy()
    if result.empty:
        return result
    return result.sort_values("transaction_date")


def project_metrics(history: pd.DataFrame) -> dict[str, float | str]:
    if history.empty:
        return {}
    history = _ensure_date(history)
    latest = history.iloc[-1]
    prices = history["price"].dropna()
    avg_psf = (prices / (history["size_sqm"] * 10.7639)).mean()
    appreciation = 0.0
    if len(prices) > 1:
        first = prices.iloc[0]
        appreciation = ((prices.iloc[-1] - first) / first) * 100 if first else 0.0
    return {
        "transactions": len(history),
        "latest_price": latest.get("price", 0.0),
        "average_psf": avg_psf,
        "appreciation_pct": appreciation,
        "first_transaction": history["transaction_date"].min().strftime("%Y-%m-%d") if pd.notna(history["transaction_date"].min()) else "-",
        "latest_transaction": latest.get("transaction_date", "-") if latest.get("transaction_date", None) is not None else "-",
    }

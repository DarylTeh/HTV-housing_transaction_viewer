from __future__ import annotations

import pandas as pd

def format_currency(value: float | int | None) -> str:
    if value is None or (isinstance(value, (int, float)) and value != value):
        return "-"
    return f"${value:,.0f}"
def format_rate(value: float | None) -> str:
    if value is None or (isinstance(value, (int, float)) and value != value):
        return "-"
    return f"{value * 100:.1f}%"


def format_price(value: float | int | None) -> str:
    """Format a numeric price with SGD prefix and thousand separators.

    Returns a dash for missing/NaN values.
    """
    if value is None or (isinstance(value, (int, float)) and value != value):
        return "-"
    try:
        return f"${float(value):,.0f}"
    except Exception:
        return str(value)


def format_dataframe_prices(df: pd.DataFrame, price_cols: list[str]) -> pd.DataFrame:
    """Return a copy of `df` with specified price columns formatted as strings with commas.

    Non-existing columns are ignored.
    """
    out = df.copy()
    for col in price_cols:
        if col in out.columns:
            out[col] = out[col].apply(format_price)
    return out

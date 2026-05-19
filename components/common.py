from __future__ import annotations

def format_currency(value: float | int | None) -> str:
    if value is None or (isinstance(value, (int, float)) and value != value):
        return "-"
    return f"${value:,.0f}"


def format_rate(value: float | None) -> str:
    if value is None or (isinstance(value, (int, float)) and value != value):
        return "-"
    return f"{value * 100:.1f}%"

from __future__ import annotations
import plotly.graph_objects as go
import plotly.express as px
import pandas as pd


def payment_breakdown_pie(cash_needed: float, cpf_used: float, absd: float, bsd: float, loan_amount: float):
    values = [cash_needed, cpf_used, absd, bsd, loan_amount]
    labels = ["Cash & top-up", "CPF used", "ABSD", "BSD", "Loan amount"]
    fig = px.pie(names=labels, values=values, title="Payment breakdown")
    fig.update_traces(textposition="inside", textinfo="percent+label")
    return fig


def cash_flow_sankey(loan_amount: float, absd: float, bsd: float, cash_needed: float, cpf_used: float):
    nodes = ["Buyer funds", "CPF OA", "Loan", "Property price", "Stamp duties", "Cash deposit"]
    sources = [0, 1, 2, 1, 0]
    targets = [3, 3, 3, 4, 4]
    values = [cash_needed, cpf_used, loan_amount, absd, bsd]
    fig = go.Figure(
        go.Sankey(
            node={"label": nodes, "pad": 20, "thickness": 20},
            link={"source": sources, "target": targets, "value": values},
        )
    )
    fig.update_layout(title_text="Simplified cash flow into purchase", font_size=11)
    return fig


def payment_timeline(price: float, monthly_installment: float, tenure_years: int):
    years = list(range(0, tenure_years + 1, max(1, tenure_years // 10)))
    payments = [monthly_installment * 12 * year for year in years]
    df = pd.DataFrame({"Year": years, "Cumulative payments": payments})
    fig = px.line(df, x="Year", y="Cumulative payments", markers=True, title="Projected payment timeline")
    return fig

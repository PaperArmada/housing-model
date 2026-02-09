"""Plotly chart builders for the housing model dashboard."""

import plotly.graph_objects as go

from housing.model import YearSnapshot, net_worth_at_sale
from housing.output import crossover_year
from housing.params import ScenarioParams
from housing.sensitivity import SweepResult


def net_worth_chart(snapshots: list[YearSnapshot], real: bool = False) -> go.Figure:
    """Net worth over time: Buy vs Rent with crossover annotation."""
    years = [s.year for s in snapshots]
    buy_nw = [s.buy_net_worth_real if real else s.buy_net_worth for s in snapshots]
    rent_nw = [s.rent_net_worth_real if real else s.rent_net_worth for s in snapshots]
    label = "real" if real else "nominal"

    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=years,
            y=buy_nw,
            name="Buy",
            line=dict(color="#2196F3", width=2.5),
            hovertemplate="Year %{x}<br>Buy: $%{y:,.0f}<extra></extra>",
        )
    )
    fig.add_trace(
        go.Scatter(
            x=years,
            y=rent_nw,
            name="Rent",
            line=dict(color="#FF9800", width=2.5),
            hovertemplate="Year %{x}<br>Rent: $%{y:,.0f}<extra></extra>",
        )
    )

    xover = crossover_year(snapshots)
    if xover is not None:
        fig.add_vline(
            x=xover,
            line_dash="dash",
            line_color="gray",
            annotation_text=f"Crossover: Year {xover}",
            annotation_position="top left",
        )

    fig.update_layout(
        title=f"Net Worth: Buy vs Rent ({label})",
        xaxis_title="Year",
        yaxis_title="Net Worth ($)",
        yaxis_tickformat="$,.0f",
        hovermode="x unified",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        margin=dict(t=60, b=40),
    )
    return fig


def net_worth_difference_chart(
    snapshots: list[YearSnapshot], real: bool = False
) -> go.Figure:
    """Bar chart of net worth difference (buy - rent) per year."""
    years = [s.year for s in snapshots]
    diffs = [
        s.net_worth_difference_real if real else s.net_worth_difference
        for s in snapshots
    ]
    colors = ["#4CAF50" if d >= 0 else "#F44336" for d in diffs]
    labels = ["Buy wins" if d >= 0 else "Rent wins" for d in diffs]

    fig = go.Figure(
        go.Bar(
            x=years,
            y=diffs,
            marker_color=colors,
            hovertemplate="Year %{x}<br>%{text}: $%{y:,.0f}<extra></extra>",
            text=labels,
            textposition="none",
        )
    )
    fig.update_layout(
        title="Net Worth Difference (Buy - Rent)",
        xaxis_title="Year",
        yaxis_title="Difference ($)",
        yaxis_tickformat="$,.0f",
        margin=dict(t=60, b=40),
    )
    return fig


def liquidated_net_worth_chart(
    snapshots: list[YearSnapshot], params: ScenarioParams, real: bool = False
) -> go.Figure:
    """Net worth after full liquidation — selling costs, CGT, and mortgage payoff.

    This is the "walk-away-with" view: what each scenario yields if you
    sell the property / liquidate the portfolio at every year along the timeline.
    """
    years = []
    buy_vals = []
    rent_vals = []

    for s in snapshots:
        result = net_worth_at_sale(s, params)
        years.append(s.year)
        if real:
            buy_vals.append(result["buy_net_worth_after_sale_real"])
            rent_vals.append(result["rent_net_worth_after_tax_real"])
        else:
            buy_vals.append(result["buy_net_worth_after_sale"])
            rent_vals.append(result["rent_net_worth_after_tax"])

    label = "real" if real else "nominal"

    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=years,
            y=buy_vals,
            name="Buy (after sale)",
            line=dict(color="#2196F3", width=2.5),
            hovertemplate="Year %{x}<br>Buy: $%{y:,.0f}<extra></extra>",
        )
    )
    fig.add_trace(
        go.Scatter(
            x=years,
            y=rent_vals,
            name="Rent (after CGT)",
            line=dict(color="#FF9800", width=2.5),
            hovertemplate="Year %{x}<br>Rent: $%{y:,.0f}<extra></extra>",
        )
    )

    # Find liquidated crossover (first year buy overtakes rent)
    for i in range(1, len(years)):
        prev_diff = buy_vals[i - 1] - rent_vals[i - 1]
        curr_diff = buy_vals[i] - rent_vals[i]
        if prev_diff <= 0 and curr_diff > 0:
            fig.add_vline(
                x=years[i],
                line_dash="dash",
                line_color="gray",
                annotation_text=f"Crossover: Year {years[i]}",
                annotation_position="top left",
            )
            break

    fig.update_layout(
        title=f"Liquidated Net Worth: Buy vs Rent ({label})",
        xaxis_title="Year",
        yaxis_title="Net Worth ($)",
        yaxis_tickformat="$,.0f",
        hovermode="x unified",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        margin=dict(t=60, b=40),
    )
    return fig


def housing_costs_chart(snapshots: list[YearSnapshot]) -> go.Figure:
    """Grouped bar chart of annual housing costs: buy vs rent."""
    # Skip year 0 (upfront costs distort the scale)
    active = [s for s in snapshots if s.year > 0]
    years = [s.year for s in active]
    buy_costs = [s.buy_housing_costs for s in active]
    rent_costs = [s.rent_housing_costs for s in active]

    fig = go.Figure()
    fig.add_trace(
        go.Bar(
            x=years,
            y=buy_costs,
            name="Buy Costs",
            marker_color="#2196F3",
            hovertemplate="Year %{x}<br>Buy: $%{y:,.0f}<extra></extra>",
        )
    )
    fig.add_trace(
        go.Bar(
            x=years,
            y=rent_costs,
            name="Rent Costs",
            marker_color="#FF9800",
            hovertemplate="Year %{x}<br>Rent: $%{y:,.0f}<extra></extra>",
        )
    )
    fig.update_layout(
        barmode="group",
        title="Annual Housing Costs",
        xaxis_title="Year",
        yaxis_title="Annual Cost ($)",
        yaxis_tickformat="$,.0f",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        margin=dict(t=60, b=40),
    )
    return fig


def cumulative_costs_chart(snapshots: list[YearSnapshot]) -> go.Figure:
    """Line chart of cumulative housing costs over time."""
    years = [s.year for s in snapshots]
    buy_cum = [s.buy_cumulative_costs for s in snapshots]
    rent_cum = [s.rent_cumulative_costs for s in snapshots]

    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=years,
            y=buy_cum,
            name="Buy (cumulative)",
            line=dict(color="#2196F3", width=2.5),
            hovertemplate="Year %{x}<br>Buy total: $%{y:,.0f}<extra></extra>",
        )
    )
    fig.add_trace(
        go.Scatter(
            x=years,
            y=rent_cum,
            name="Rent (cumulative)",
            line=dict(color="#FF9800", width=2.5),
            hovertemplate="Year %{x}<br>Rent total: $%{y:,.0f}<extra></extra>",
        )
    )
    fig.update_layout(
        title="Cumulative Housing Costs",
        xaxis_title="Year",
        yaxis_title="Total Cost ($)",
        yaxis_tickformat="$,.0f",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        margin=dict(t=60, b=40),
    )
    return fig


def equity_buildup_chart(snapshots: list[YearSnapshot]) -> go.Figure:
    """Property value, equity, mortgage, and investment portfolios over time."""
    years = [s.year for s in snapshots]
    equity = [s.buy_equity for s in snapshots]
    prop_value = [s.property_value for s in snapshots]
    mortgage = [s.mortgage_balance for s in snapshots]
    buy_inv = [s.buy_investments for s in snapshots]
    rent_inv = [s.rent_investments for s in snapshots]

    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=years,
            y=equity,
            name="Home Equity",
            fill="tozeroy",
            line=dict(color="#4CAF50"),
            fillcolor="rgba(76,175,80,0.2)",
            hovertemplate="Year %{x}<br>Equity: $%{y:,.0f}<extra></extra>",
        )
    )
    fig.add_trace(
        go.Scatter(
            x=years,
            y=prop_value,
            name="Property Value",
            line=dict(color="#2196F3", dash="dot", width=2),
            hovertemplate="Year %{x}<br>Property: $%{y:,.0f}<extra></extra>",
        )
    )
    fig.add_trace(
        go.Scatter(
            x=years,
            y=mortgage,
            name="Mortgage Balance",
            line=dict(color="#F44336", width=2),
            hovertemplate="Year %{x}<br>Mortgage: $%{y:,.0f}<extra></extra>",
        )
    )
    fig.add_trace(
        go.Scatter(
            x=years,
            y=rent_inv,
            name="Renter Investments",
            line=dict(color="#FF9800", width=2),
            hovertemplate="Year %{x}<br>Renter inv: $%{y:,.0f}<extra></extra>",
        )
    )
    fig.add_trace(
        go.Scatter(
            x=years,
            y=buy_inv,
            name="Buyer Investments",
            line=dict(color="#9C27B0", dash="dash", width=2),
            hovertemplate="Year %{x}<br>Buyer inv: $%{y:,.0f}<extra></extra>",
        )
    )
    fig.update_layout(
        title="Equity, Debt & Investment Buildup",
        xaxis_title="Year",
        yaxis_title="Value ($)",
        yaxis_tickformat="$,.0f",
        hovermode="x unified",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        margin=dict(t=80, b=40),
    )
    return fig


def sensitivity_chart(
    results: list[SweepResult], param_name: str, is_pct: bool
) -> go.Figure:
    """Line chart of buy vs rent net worth across a parameter sweep."""
    if is_pct:
        x_values = [r.param_value * 100 for r in results]
        x_label = f"{param_name} (%)"
    else:
        x_values = [r.param_value for r in results]
        x_label = param_name

    buy_nw = [r.buy_nw_real for r in results]
    rent_nw = [r.rent_nw_real for r in results]

    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=x_values,
            y=buy_nw,
            name="Buy NW (real)",
            line=dict(color="#2196F3", width=2.5),
            hovertemplate=f"{param_name}: %{{x:.1f}}<br>Buy: $%{{y:,.0f}}<extra></extra>",
        )
    )
    fig.add_trace(
        go.Scatter(
            x=x_values,
            y=rent_nw,
            name="Rent NW (real)",
            line=dict(color="#FF9800", width=2.5),
            hovertemplate=f"{param_name}: %{{x:.1f}}<br>Rent: $%{{y:,.0f}}<extra></extra>",
        )
    )
    fig.update_layout(
        title=f"Sensitivity: {param_name}",
        xaxis_title=x_label,
        yaxis_title="Net Worth (real $)",
        yaxis_tickformat="$,.0f",
        hovermode="x unified",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        margin=dict(t=60, b=40),
    )
    return fig

"""Plotly chart builders for multi-scenario comparison."""

import plotly.graph_objects as go

from housing.model import YearSnapshot

COLOURS = ["#2196F3", "#F44336", "#4CAF50", "#FF9800", "#9C27B0", "#00BCD4"]


def comparison_difference_chart(
    scenario_data: list[tuple[str, list[YearSnapshot]]], real: bool = False
) -> go.Figure:
    """One line per scenario showing Buy-minus-Rent net worth difference over time."""
    fig = go.Figure()

    for i, (name, snapshots) in enumerate(scenario_data):
        colour = COLOURS[i % len(COLOURS)]
        years = [s.year for s in snapshots]
        diffs = [
            s.net_worth_difference_real if real else s.net_worth_difference
            for s in snapshots
        ]
        fig.add_trace(
            go.Scatter(
                x=years,
                y=diffs,
                name=name,
                line=dict(color=colour, width=2.5),
                hovertemplate=f"{name}<br>Year %{{x}}<br>Diff: $%{{y:,.0f}}<extra></extra>",
            )
        )

    fig.add_hline(y=0, line_dash="dash", line_color="gray", opacity=0.5)

    label = "real" if real else "nominal"
    fig.update_layout(
        title=f"Buy vs Rent Difference by Scenario ({label})",
        xaxis_title="Year",
        yaxis_title="Buy - Rent ($)",
        yaxis_tickformat="$,.0f",
        hovermode="x unified",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        margin=dict(t=60, b=40),
    )
    return fig


def comparison_net_worth_chart(
    scenario_data: list[tuple[str, list[YearSnapshot]]], real: bool = False
) -> go.Figure:
    """Buy (solid) and Rent (dashed) net worth lines overlaid, grouped by scenario."""
    fig = go.Figure()

    for i, (name, snapshots) in enumerate(scenario_data):
        colour = COLOURS[i % len(COLOURS)]
        years = [s.year for s in snapshots]
        buy_nw = [
            s.buy_net_worth_real if real else s.buy_net_worth for s in snapshots
        ]
        rent_nw = [
            s.rent_net_worth_real if real else s.rent_net_worth for s in snapshots
        ]

        fig.add_trace(
            go.Scatter(
                x=years,
                y=buy_nw,
                name=f"{name} — Buy",
                legendgroup=name,
                line=dict(color=colour, width=2.5),
                hovertemplate=f"{name} Buy<br>Year %{{x}}<br>${{y:,.0f}}<extra></extra>",
            )
        )
        fig.add_trace(
            go.Scatter(
                x=years,
                y=rent_nw,
                name=f"{name} — Rent",
                legendgroup=name,
                line=dict(color=colour, width=2.5, dash="dash"),
                hovertemplate=f"{name} Rent<br>Year %{{x}}<br>${{y:,.0f}}<extra></extra>",
            )
        )

    label = "real" if real else "nominal"
    fig.update_layout(
        title=f"Net Worth by Scenario ({label})",
        xaxis_title="Year",
        yaxis_title="Net Worth ($)",
        yaxis_tickformat="$,.0f",
        hovermode="x unified",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        margin=dict(t=60, b=40),
    )
    return fig

"""Plotly chart builders for Monte Carlo simulation results."""

import numpy as np
import plotly.graph_objects as go

from housing.monte_carlo import MCSummary, MCTimeSeries


def fan_chart(
    summary: MCSummary,
    metric: str = "difference",
    title: str = "Monte Carlo: Net Worth Difference (Buy - Rent)",
) -> go.Figure:
    """Fan chart with percentile bands and median line.

    Shows p10, p25, p50, p75, p90 values on hover using individual traces
    with fill="tonexty" for shaded bands.

    metric: 'buy', 'rent', or 'difference'
    """
    pctiles = {
        "buy": summary.buy_pctiles,
        "rent": summary.rent_pctiles,
        "difference": summary.diff_pctiles,
    }[metric]

    colors = {
        "buy": {
            "band_outer": "rgba(33,150,243,0.15)",
            "band_inner": "rgba(33,150,243,0.3)",
            "line": "#2196F3",
            "boundary": "rgba(33,150,243,0.4)",
        },
        "rent": {
            "band_outer": "rgba(255,152,0,0.15)",
            "band_inner": "rgba(255,152,0,0.3)",
            "line": "#FF9800",
            "boundary": "rgba(255,152,0,0.4)",
        },
        "difference": {
            "band_outer": "rgba(76,175,80,0.15)",
            "band_inner": "rgba(76,175,80,0.3)",
            "line": "#4CAF50",
            "boundary": "rgba(76,175,80,0.4)",
        },
    }[metric]

    years = summary.years
    fig = go.Figure()

    # Build traces bottom-to-top so fill="tonexty" creates correct bands:
    #   p10 → p25 (outer lower) → p75 (inner) → p90 (outer upper)
    # Then p50 median on top.

    boundary_line = dict(width=0.5, color=colors["boundary"], dash="dot")

    # p10 — bottom boundary
    if 10 in pctiles:
        fig.add_trace(go.Scatter(
            x=years,
            y=pctiles[10],
            name="p10",
            line=boundary_line,
            hovertemplate="$%{y:,.0f}",
            showlegend=False,
        ))

    # p25 — fills down to p10 (outer band)
    if 25 in pctiles:
        fig.add_trace(go.Scatter(
            x=years,
            y=pctiles[25],
            name="p25",
            line=boundary_line,
            fill="tonexty",
            fillcolor=colors["band_outer"],
            hovertemplate="$%{y:,.0f}",
            showlegend=False,
        ))

    # p75 — fills down to p25 (inner band)
    if 75 in pctiles:
        fig.add_trace(go.Scatter(
            x=years,
            y=pctiles[75],
            name="p75",
            line=boundary_line,
            fill="tonexty",
            fillcolor=colors["band_inner"],
            hovertemplate="$%{y:,.0f}",
            showlegend=False,
        ))

    # p90 — fills down to p75 (outer band)
    if 90 in pctiles:
        fig.add_trace(go.Scatter(
            x=years,
            y=pctiles[90],
            name="p90",
            line=boundary_line,
            fill="tonexty",
            fillcolor=colors["band_outer"],
            hovertemplate="$%{y:,.0f}",
            showlegend=False,
        ))

    # Median line (on top, prominent)
    if 50 in pctiles:
        fig.add_trace(go.Scatter(
            x=years,
            y=pctiles[50],
            name="Median",
            line=dict(color=colors["line"], width=2.5),
            hovertemplate="$%{y:,.0f}",
        ))

    if metric == "difference":
        fig.add_hline(y=0, line_dash="dash", line_color="gray", opacity=0.5)

    fig.update_layout(
        title=title,
        xaxis_title="Year",
        yaxis_title="Net Worth ($)",
        yaxis_tickformat="$,.0f",
        hovermode="x unified",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        margin=dict(t=60, b=40),
    )
    return fig


def prob_buy_wins_chart(summary: MCSummary) -> go.Figure:
    """Area chart of P(buy wins) over time."""
    fig = go.Figure()

    fig.add_trace(go.Scatter(
        x=summary.years,
        y=summary.prob_buy_wins * 100,
        fill="tozeroy",
        fillcolor="rgba(76,175,80,0.3)",
        line=dict(color="#4CAF50", width=2),
        hovertemplate="Year %{x}<br>P(Buy wins): %{y:.1f}%<extra></extra>",
        name="P(Buy wins)",
    ))

    fig.add_hline(y=50, line_dash="dash", line_color="gray", opacity=0.5)

    fig.update_layout(
        title="Probability that Buying Wins",
        xaxis_title="Year",
        yaxis_title="Probability (%)",
        yaxis_range=[0, 100],
        margin=dict(t=60, b=40),
    )
    return fig


def terminal_histogram(ts: MCTimeSeries, year: int) -> go.Figure:
    """Overlaid histograms of buy vs rent net worth at a given year."""
    buy_vals = ts.buy_net_worth[year]
    rent_vals = ts.rent_net_worth[year]

    fig = go.Figure()

    fig.add_trace(go.Histogram(
        x=buy_vals,
        name="Buy",
        marker_color="rgba(33,150,243,0.6)",
        nbinsx=50,
        hovertemplate="$%{x:,.0f}<br>Count: %{y}<extra>Buy</extra>",
    ))
    fig.add_trace(go.Histogram(
        x=rent_vals,
        name="Rent",
        marker_color="rgba(255,152,0,0.6)",
        nbinsx=50,
        hovertemplate="$%{x:,.0f}<br>Count: %{y}<extra>Rent</extra>",
    ))

    # Median lines — offset annotations vertically so they don't overlap
    buy_med = np.median(buy_vals)
    rent_med = np.median(rent_vals)
    fig.add_vline(x=buy_med, line_dash="dash", line_color="#2196F3",
                  annotation_text=f"Buy median: ${buy_med:,.0f}",
                  annotation_position="top right",
                  annotation_yshift=0)
    fig.add_vline(x=rent_med, line_dash="dash", line_color="#FF9800",
                  annotation_text=f"Rent median: ${rent_med:,.0f}",
                  annotation_position="top right",
                  annotation_yshift=-20)

    fig.update_layout(
        barmode="overlay",
        title=f"Net Worth Distribution at Year {year}",
        xaxis_title="Net Worth ($)",
        xaxis_tickformat="$,.0f",
        yaxis_title="Count",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        margin=dict(t=60, b=40),
    )
    return fig

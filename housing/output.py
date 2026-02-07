"""Output formatting for simulation results."""

import csv
import io

from housing.model import YearSnapshot, net_worth_at_sale
from housing.params import ScenarioParams


def fmt(value: float) -> str:
    """Format a dollar amount."""
    if abs(value) >= 1_000_000:
        return f"${value / 1_000_000:,.2f}M"
    return f"${value:,.0f}"


def summary_header(params: ScenarioParams) -> str:
    """Generate the header showing key parameters."""
    buy = params.buy
    rent = params.rent
    inv = params.investment
    stamp = buy.get_stamp_duty()

    lines = [
        "Australian Housing Model - Buy vs Rent Analysis",
        "=" * 70,
        "",
        f"  Purchase price:  {fmt(buy.purchase_price)} ({buy.state})",
        f"  Deposit:         {buy.deposit_pct:.0%} ({fmt(buy.deposit)})",
        f"  Stamp duty:      {fmt(stamp)}",
        f"  Loan amount:     {fmt(buy.loan_amount)}",
        f"  Mortgage rate:   {buy.mortgage_rate:.2%} p.a. ({buy.mortgage_term_years}yr)",
        f"  Appreciation:    {buy.property_appreciation_rate:.1%} p.a.",
        "",
        f"  Weekly rent:     ${rent.weekly_rent:,.0f} (increases {rent.rent_increase_rate:.1%}/yr)",
        f"  Savings:         {fmt(params.existing_savings)}",
        f"  Investment return: {inv.return_rate:.1%} p.a. (div yield {inv.dividend_yield:.1%})",
        f"  Inflation:       {params.inflation_rate:.1%} p.a.",
        f"  Tax bracket:     {params.tax.marginal_rate:.0%} (income {fmt(params.tax.gross_income)})",
        "",
    ]

    if buy.rate_schedule:
        schedule_str = ", ".join(
            f"yr{y}: {r:.2%}" for y, r in sorted(buy.rate_schedule)
        )
        lines.insert(8, f"  Rate schedule:   {schedule_str}")

    if buy.strata_annual > 0:
        lines.insert(9, f"  Strata:          {fmt(buy.strata_annual)}/yr")

    return "\n".join(lines)


def summary_table(
    snapshots: list[YearSnapshot],
    params: ScenarioParams,
    key_years: list[int] | None = None,
    show_real: bool = True,
) -> str:
    """Generate summary table at key year intervals."""
    if key_years is None:
        horizon = params.time_horizon_years
        key_years = [0, 5, 10, 15, 20, 25, 30]
        key_years = [y for y in key_years if y <= horizon]
        if horizon not in key_years:
            key_years.append(horizon)

    snapshot_map = {s.year: s for s in snapshots}

    if show_real:
        header = (
            f"{'Year':>4} | {'Buy NW (nom)':>14} | {'Buy NW (real)':>14} | "
            f"{'Rent NW (nom)':>14} | {'Rent NW (real)':>14} | {'Winner':>6}"
        )
    else:
        header = (
            f"{'Year':>4} | {'Buy NW':>14} | {'Rent NW':>14} | "
            f"{'Difference':>14} | {'Winner':>6}"
        )

    sep = "-" * len(header)
    lines = [header, sep]

    for year in key_years:
        s = snapshot_map.get(year)
        if s is None:
            continue
        winner = "Buy" if s.net_worth_difference > 0 else "Rent"
        if show_real:
            lines.append(
                f"{s.year:>4} | {fmt(s.buy_net_worth):>14} | {fmt(s.buy_net_worth_real):>14} | "
                f"{fmt(s.rent_net_worth):>14} | {fmt(s.rent_net_worth_real):>14} | {winner:>6}"
            )
        else:
            lines.append(
                f"{s.year:>4} | {fmt(s.buy_net_worth):>14} | {fmt(s.rent_net_worth):>14} | "
                f"{fmt(s.net_worth_difference):>14} | {winner:>6}"
            )

    return "\n".join(lines)


def crossover_year(snapshots: list[YearSnapshot]) -> int | None:
    """Find the year where buy starts winning (net_worth_difference goes positive)."""
    for i in range(1, len(snapshots)):
        prev = snapshots[i - 1]
        curr = snapshots[i]
        if prev.net_worth_difference <= 0 and curr.net_worth_difference > 0:
            return curr.year
    return None


def liquidation_summary(snapshots: list[YearSnapshot], params: ScenarioParams) -> str:
    """Show after-tax liquidation comparison at key years."""
    key_years = [5, 10, 15, 20, 25, 30]
    key_years = [y for y in key_years if y <= params.time_horizon_years]
    snapshot_map = {s.year: s for s in snapshots}

    header = (
        f"{'Year':>4} | {'Buy (after sale)':>16} | {'Rent (after CGT)':>16} | "
        f"{'Diff':>14} | {'Winner':>6}"
    )
    sep = "-" * len(header)
    lines = ["After-tax liquidation comparison:", header, sep]

    for year in key_years:
        s = snapshot_map.get(year)
        if s is None:
            continue
        result = net_worth_at_sale(s, params)
        winner = "Buy" if result["buy_wins"] else "Rent"
        lines.append(
            f"{year:>4} | {fmt(result['buy_net_worth_after_sale']):>16} | "
            f"{fmt(result['rent_net_worth_after_tax']):>16} | "
            f"{fmt(result['difference']):>14} | {winner:>6}"
        )

    return "\n".join(lines)


def detailed_table(snapshots: list[YearSnapshot]) -> str:
    """Year-by-year detailed breakdown."""
    header = (
        f"{'Yr':>3} | {'Prop Value':>12} | {'Mortgage':>12} | {'Rate':>5} | "
        f"{'Buy Costs':>10} | {'Buy NW':>12} | "
        f"{'Rent':>10} | {'Rent Inv':>12} | {'Rent NW':>12} | {'Diff':>12}"
    )
    sep = "-" * len(header)
    lines = [header, sep]

    for s in snapshots:
        lines.append(
            f"{s.year:>3} | {fmt(s.property_value):>12} | {fmt(s.mortgage_balance):>12} | "
            f"{s.mortgage_rate_used:>4.1%} | "
            f"{fmt(s.buy_housing_costs):>10} | {fmt(s.buy_net_worth):>12} | "
            f"{fmt(s.annual_rent):>10} | {fmt(s.rent_investments):>12} | "
            f"{fmt(s.rent_net_worth):>12} | {fmt(s.net_worth_difference):>12}"
        )

    return "\n".join(lines)


def to_csv(snapshots: list[YearSnapshot]) -> str:
    """Export snapshots to CSV string."""
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "year", "property_value", "mortgage_balance", "mortgage_rate",
        "buy_housing_costs", "buy_cumulative_costs", "buy_equity",
        "buy_investments", "buy_contributions", "buy_net_worth", "buy_net_worth_real",
        "annual_rent", "rent_housing_costs", "rent_cumulative_costs",
        "rent_investments", "rent_contributions", "rent_net_worth", "rent_net_worth_real",
        "net_worth_difference", "net_worth_difference_real",
    ])
    for s in snapshots:
        writer.writerow([
            s.year, f"{s.property_value:.2f}", f"{s.mortgage_balance:.2f}",
            f"{s.mortgage_rate_used:.4f}",
            f"{s.buy_housing_costs:.2f}", f"{s.buy_cumulative_costs:.2f}",
            f"{s.buy_equity:.2f}", f"{s.buy_investments:.2f}",
            f"{s.buy_contributions:.2f}", f"{s.buy_net_worth:.2f}",
            f"{s.buy_net_worth_real:.2f}",
            f"{s.annual_rent:.2f}", f"{s.rent_housing_costs:.2f}",
            f"{s.rent_cumulative_costs:.2f}", f"{s.rent_investments:.2f}",
            f"{s.rent_contributions:.2f}", f"{s.rent_net_worth:.2f}",
            f"{s.rent_net_worth_real:.2f}",
            f"{s.net_worth_difference:.2f}", f"{s.net_worth_difference_real:.2f}",
        ])
    return output.getvalue()


def full_report(snapshots: list[YearSnapshot], params: ScenarioParams) -> str:
    """Generate a complete summary report."""
    parts = [
        summary_header(params),
        summary_table(snapshots, params),
        "",
    ]

    xover = crossover_year(snapshots)
    if xover is not None:
        parts.append(f"Crossover point: Year {xover} (buying becomes better)")
    else:
        if snapshots[-1].net_worth_difference > 0:
            parts.append("Buying is better from the start.")
        else:
            parts.append("Renting is better for the entire time horizon.")

    parts.append("")
    parts.append(liquidation_summary(snapshots, params))

    return "\n".join(parts)

"""DataFrame formatters for the dashboard data tables."""

import pandas as pd

from housing.model import YearSnapshot, net_worth_at_sale
from housing.params import ScenarioParams


def snapshot_dataframe(snapshots: list[YearSnapshot]) -> pd.DataFrame:
    """Convert simulation snapshots to a display-ready DataFrame."""
    rows = []
    for s in snapshots:
        rows.append(
            {
                "Year": s.year,
                "Property Value": s.property_value,
                "Mortgage Bal.": s.mortgage_balance,
                "Rate": s.mortgage_rate_used,
                "Buy Costs": s.buy_housing_costs,
                "Buy Cumul.": s.buy_cumulative_costs,
                "Buy Equity": s.buy_equity,
                "Buy Invest.": s.buy_investments,
                "Buy NW": s.buy_net_worth,
                "Buy NW (real)": s.buy_net_worth_real,
                "Annual Rent": s.annual_rent,
                "Rent Costs": s.rent_housing_costs,
                "Rent Cumul.": s.rent_cumulative_costs,
                "Rent Invest.": s.rent_investments,
                "Rent NW": s.rent_net_worth,
                "Rent NW (real)": s.rent_net_worth_real,
                "Difference": s.net_worth_difference,
                "Diff. (real)": s.net_worth_difference_real,
            }
        )
    df = pd.DataFrame(rows)
    return df.style.format(
        {
            col: "${:,.0f}"
            for col in df.columns
            if col not in ("Year", "Rate")
        }
    ).format({"Rate": "{:.2%}"})


def sale_comparison_dataframe(
    snapshots: list[YearSnapshot], params: ScenarioParams
) -> pd.DataFrame:
    """After-tax liquidation comparison at key years."""
    key_years = [5, 10, 15, 20, 25, 30]
    key_years = [y for y in key_years if y <= params.time_horizon_years]
    if params.time_horizon_years not in key_years:
        key_years.append(params.time_horizon_years)

    snapshot_map = {s.year: s for s in snapshots}
    rows = []
    for year in key_years:
        s = snapshot_map.get(year)
        if s is None:
            continue
        result = net_worth_at_sale(s, params)
        rows.append(
            {
                "Year": year,
                "Buy (after sale)": result["buy_net_worth_after_sale"],
                "Buy (real)": result["buy_net_worth_after_sale_real"],
                "Rent (after CGT)": result["rent_net_worth_after_tax"],
                "Rent (real)": result["rent_net_worth_after_tax_real"],
                "Difference": result["difference"],
                "Diff. (real)": result["difference_real"],
                "Winner": "Buy" if result["buy_wins"] else "Rent",
            }
        )
    df = pd.DataFrame(rows)
    dollar_cols = [c for c in df.columns if c not in ("Year", "Winner")]
    return df.style.format({col: "${:,.0f}" for col in dollar_cols})

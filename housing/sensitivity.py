"""Sensitivity analysis: sweep one parameter, see how outcomes change."""

from copy import deepcopy
from dataclasses import dataclass

from housing.model import simulate, net_worth_at_sale
from housing.output import crossover_year, fmt
from housing.params import ScenarioParams


@dataclass
class SweepResult:
    param_value: float
    buy_nw_real: float
    rent_nw_real: float
    difference_real: float
    buy_wins: bool
    crossover: int | None
    # After-tax liquidation at horizon
    buy_liquidation: float
    rent_liquidation: float


def _set_nested_attr(obj: object, path: str, value: float) -> None:
    """Set a nested attribute like 'buy.mortgage_rate' on a dataclass."""
    parts = path.split(".")
    for part in parts[:-1]:
        obj = getattr(obj, part)
    setattr(obj, parts[-1], value)


def _get_nested_attr(obj: object, path: str) -> float:
    """Get a nested attribute like 'buy.mortgage_rate' from a dataclass."""
    for part in path.split("."):
        obj = getattr(obj, part)
    return obj


def sweep(
    params: ScenarioParams,
    param_path: str,
    values: list[float],
) -> list[SweepResult]:
    """Run simulation for each value of a parameter, return results."""
    results = []
    for val in values:
        p = deepcopy(params)
        _set_nested_attr(p, param_path, val)
        snapshots = simulate(p)
        final = snapshots[-1]
        xover = crossover_year(snapshots)
        liquidation = net_worth_at_sale(final, p)

        results.append(SweepResult(
            param_value=val,
            buy_nw_real=final.buy_net_worth_real,
            rent_nw_real=final.rent_net_worth_real,
            difference_real=final.net_worth_difference_real,
            buy_wins=final.net_worth_difference_real > 0,
            crossover=xover,
            buy_liquidation=liquidation["buy_net_worth_after_sale_real"],
            rent_liquidation=liquidation["rent_net_worth_after_tax_real"],
        ))

    return results


def format_sweep(
    param_path: str,
    results: list[SweepResult],
    is_percentage: bool = True,
) -> str:
    """Format sweep results as a table."""
    label = param_path.split(".")[-1]
    header = (
        f"{'':>2} {label:>12} | {'Buy NW (real)':>14} | {'Rent NW (real)':>14} | "
        f"{'Diff':>14} | {'Winner':>6} | {'Crossover':>9}"
    )
    sep = "-" * len(header)
    lines = [
        f"Sensitivity: {param_path} (at end of time horizon)",
        header,
        sep,
    ]

    for r in results:
        if is_percentage:
            val_str = f"{r.param_value:.2%}"
        else:
            val_str = f"{r.param_value:,.0f}"
        winner = "Buy" if r.buy_wins else "Rent"
        xover = f"Year {r.crossover}" if r.crossover else "N/A"
        lines.append(
            f"{'':>2} {val_str:>12} | {fmt(r.buy_nw_real):>14} | "
            f"{fmt(r.rent_nw_real):>14} | {fmt(r.difference_real):>14} | "
            f"{winner:>6} | {xover:>9}"
        )

    return "\n".join(lines)


def frange(start: float, stop: float, step: float) -> list[float]:
    """Generate a list of floats from start to stop (inclusive) by step."""
    values = []
    val = start
    while val <= stop + step / 2:  # tolerance for floating point
        values.append(round(val, 6))
        val += step
    return values

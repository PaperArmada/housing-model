"""Vectorized Monte Carlo simulation for buy-vs-rent analysis.

Runs N parallel simulations with year-by-year correlated random shocks
to property appreciation, investment returns, rent increases, inflation,
and mortgage rates. All computation uses NumPy (N,) arrays — one outer
loop over years, no inner loop over runs.
"""

from dataclasses import dataclass

import numpy as np

from housing.mc_params import CEILINGS, FLOORS, MCConfig, build_cov_matrix
from housing.model import monthly_repayment
from housing.params import ScenarioParams
from housing.tax import fhog, marginal_rate


@dataclass
class MCTimeSeries:
    """Raw Monte Carlo output. All 2-D arrays are shape (T+1, N)."""

    years: np.ndarray  # (T+1,)
    buy_net_worth: np.ndarray
    rent_net_worth: np.ndarray
    difference: np.ndarray  # buy - rent
    property_values: np.ndarray
    mortgage_balances: np.ndarray


@dataclass
class MCSummary:
    """Percentile-band statistics derived from MCTimeSeries."""

    years: np.ndarray  # (T+1,)
    percentiles: list[int]
    buy_pctiles: dict[int, np.ndarray]  # {pct: (T+1,)}
    rent_pctiles: dict[int, np.ndarray]
    diff_pctiles: dict[int, np.ndarray]
    prob_buy_wins: np.ndarray  # (T+1,)
    median_crossover: int | None


def mc_simulate(params: ScenarioParams, config: MCConfig) -> MCTimeSeries:
    """Run vectorized Monte Carlo simulation.

    Returns MCTimeSeries with arrays of shape (T+1, N) where T is the
    time horizon and N is the number of runs.
    """
    N = config.n_runs
    T = params.time_horizon_years
    buy = params.buy
    rent = params.rent
    inv = params.investment
    tax_rate = marginal_rate(params.tax.gross_income)

    # --- Random number setup ---
    rng = np.random.default_rng(config.seed)
    cov = build_cov_matrix(config)

    # Cholesky decomposition for correlated draws
    # Add tiny diagonal for numerical stability
    cov_stable = cov + np.eye(5) * 1e-10
    L = np.linalg.cholesky(cov_stable)

    # --- Initial state (year 0) — scalar, then broadcast ---
    stamp_duty = buy.get_stamp_duty()
    grant = 0.0
    if buy.first_home_buyer:
        grant = fhog(state=buy.state, new_build=buy.new_build, price=buy.purchase_price)
    upfront_buy_costs = buy.deposit + stamp_duty + buy.lmi - grant

    # Initial mortgage payment
    mortgage_bal = np.full(N, buy.loan_amount)
    current_rate = np.full(N, buy.rate_for_year(1))
    remaining_term = buy.mortgage_term_years
    initial_pmt = monthly_repayment(buy.loan_amount, buy.rate_for_year(1), remaining_term)
    monthly_pmt = np.full(N, initial_pmt)

    property_value = np.full(N, buy.purchase_price)
    buy_investments = np.full(N, max(params.existing_savings - upfront_buy_costs, 0.0))
    buy_contributions = buy_investments.copy()

    rent_investments = np.full(N, params.existing_savings)
    rent_contributions = rent_investments.copy()
    weekly_rent_arr = np.full(N, rent.weekly_rent)

    # Franking parameters (scalar)
    corp_rate = 0.30
    if tax_rate > corp_rate:
        franked_tax_rate = (tax_rate - corp_rate) / (1 - corp_rate)
    else:
        franked_tax_rate = 0.0
    effective_div_rate = (
        inv.franking_rate * franked_tax_rate
        + (1 - inv.franking_rate) * tax_rate
    )

    # --- Output arrays ---
    out_years = np.arange(T + 1)
    out_buy_nw = np.zeros((T + 1, N))
    out_rent_nw = np.zeros((T + 1, N))
    out_prop = np.zeros((T + 1, N))
    out_mort = np.zeros((T + 1, N))

    # Year 0
    buy_equity_0 = property_value - mortgage_bal
    out_buy_nw[0] = buy_equity_0 + buy_investments
    out_rent_nw[0] = rent_investments
    out_prop[0] = property_value
    out_mort[0] = mortgage_bal

    # Base means for stochastic variables
    base_means = np.array([
        buy.property_appreciation_rate,
        inv.return_rate,
        rent.rent_increase_rate,
        params.inflation_rate,
        buy.mortgage_rate,
    ])

    # Track the deterministic rate schedule year for rate changes
    prev_sched_rate = buy.rate_for_year(1)

    for year in range(1, T + 1):
        # --- Draw correlated shocks ---
        z = rng.standard_normal((N, 5))
        shocks = z @ L.T  # (N, 5) correlated

        # Realized values = base + shock, clipped to bounds
        realized = base_means[np.newaxis, :] + shocks  # (N, 5)
        realized = np.clip(realized, FLOORS, CEILINGS)

        prop_appr = realized[:, 0]
        inv_return = realized[:, 1]
        rent_inc = realized[:, 2]
        # inflation and mort_rate drawn but not all used in every calc
        inflation_yr = realized[:, 3]
        mort_rate = realized[:, 4]

        # --- Handle rate schedule (deterministic part) ---
        # If the deterministic schedule changes the rate this year,
        # shift the base mortgage rate accordingly for all runs
        sched_rate = buy.rate_for_year(year)
        if sched_rate != prev_sched_rate:
            # Shift realized mortgage rates by the schedule delta
            delta = sched_rate - prev_sched_rate
            mort_rate = np.clip(mort_rate + delta, FLOORS[4], CEILINGS[4])
            prev_sched_rate = sched_rate

        # --- Recalculate PMT where rate changed ---
        # Compare to previous rate; recalc PMT for all runs each year
        # since rates are stochastic
        rate_changed = mort_rate != current_rate
        if np.any(rate_changed) or year == 1:
            remaining_months = (buy.mortgage_term_years - (year - 1)) * 12
            if remaining_months > 0:
                rm_years = remaining_months / 12
                r_monthly = mort_rate / 12
                n_months = np.float64(remaining_months)
                # Vectorized PMT formula
                # For zero rates, PMT = balance / n_months
                zero_mask = mort_rate == 0
                factor = np.where(
                    zero_mask,
                    1.0 / n_months,
                    r_monthly * (1 + r_monthly) ** n_months
                    / ((1 + r_monthly) ** n_months - 1),
                )
                monthly_pmt = np.where(
                    mortgage_bal > 0,
                    mortgage_bal * factor,
                    0.0,
                )
            current_rate = mort_rate.copy()

        # --- Mortgage: analytical 12-payment amortization ---
        r_m = current_rate / 12  # monthly rate (N,)
        has_mortgage = mortgage_bal > 0
        # B_new = B*(1+r)^12 - PMT*((1+r)^12 - 1)/r
        # Handle zero-rate case
        compound_12 = np.where(r_m > 0, (1 + r_m) ** 12, 1.0)
        annuity_12 = np.where(
            r_m > 0,
            (compound_12 - 1) / r_m,
            12.0,
        )
        new_bal = np.where(
            has_mortgage,
            mortgage_bal * compound_12 - monthly_pmt * annuity_12,
            0.0,
        )
        new_bal = np.maximum(new_bal, 0.0)
        total_payments = np.where(has_mortgage, monthly_pmt * 12, 0.0)
        principal_paid = np.where(has_mortgage, mortgage_bal - new_bal, 0.0)
        interest_paid = np.where(has_mortgage, total_payments - principal_paid, 0.0)
        mortgage_bal = new_bal

        annual_mortgage = principal_paid + interest_paid

        # --- Property appreciates ---
        property_value = property_value * (1 + prop_appr)

        # --- Ongoing ownership costs ---
        deflator_yr = (1 + inflation_yr) ** year
        water_cost = buy.water_rates_annual * deflator_yr
        strata_cost = buy.strata_annual * deflator_yr
        ongoing = (
            property_value * buy.council_rates_pct
            + property_value * buy.insurance_pct
            + property_value * buy.maintenance_pct
            + water_cost
            + strata_cost
        )
        buy_year_costs = annual_mortgage + ongoing

        # --- Grow buy-side investments ---
        buy_gross = buy_investments * inv_return
        buy_dividends = buy_investments * inv.dividend_yield
        buy_div_tax = buy_dividends * effective_div_rate
        buy_reinvested_div = buy_dividends - buy_div_tax
        buy_investments = buy_investments + buy_gross - buy_div_tax
        buy_contributions = buy_contributions + buy_reinvested_div

        # --- Rent costs ---
        annual_rent = weekly_rent_arr * 52
        renters_ins = rent.renters_insurance_annual * deflator_yr
        rent_year_costs = annual_rent + renters_ins

        # --- Grow rent-side investments ---
        rent_gross = rent_investments * inv_return
        rent_dividends = rent_investments * inv.dividend_yield
        rent_div_tax = rent_dividends * effective_div_rate
        rent_reinvested_div = rent_dividends - rent_div_tax
        rent_investments = rent_investments + rent_gross - rent_div_tax
        rent_contributions = rent_contributions + rent_reinvested_div

        # --- Surplus investment ---
        buy_more = buy_year_costs > rent_year_costs
        rent_more = rent_year_costs > buy_year_costs
        surplus_to_rent = np.where(buy_more, buy_year_costs - rent_year_costs, 0.0)
        surplus_to_buy = np.where(rent_more, rent_year_costs - buy_year_costs, 0.0)

        rent_investments += surplus_to_rent * (1 + inv_return / 2)
        rent_contributions += surplus_to_rent
        buy_investments += surplus_to_buy * (1 + inv_return / 2)
        buy_contributions += surplus_to_buy

        # --- Net worth ---
        buy_equity = property_value - mortgage_bal
        buy_nw = buy_equity + buy_investments
        rent_nw = rent_investments

        out_buy_nw[year] = buy_nw
        out_rent_nw[year] = rent_nw
        out_prop[year] = property_value
        out_mort[year] = mortgage_bal

        # --- Increase rent for next year ---
        weekly_rent_arr = weekly_rent_arr * (1 + rent_inc)

    return MCTimeSeries(
        years=out_years,
        buy_net_worth=out_buy_nw,
        rent_net_worth=out_rent_nw,
        difference=out_buy_nw - out_rent_nw,
        property_values=out_prop,
        mortgage_balances=out_mort,
    )


def summarize(
    ts: MCTimeSeries,
    percentiles: list[int] | None = None,
) -> MCSummary:
    """Compute percentile bands and probability statistics from MC output."""
    if percentiles is None:
        percentiles = [10, 25, 50, 75, 90]

    buy_pctiles = {}
    rent_pctiles = {}
    diff_pctiles = {}

    for p in percentiles:
        buy_pctiles[p] = np.percentile(ts.buy_net_worth, p, axis=1)
        rent_pctiles[p] = np.percentile(ts.rent_net_worth, p, axis=1)
        diff_pctiles[p] = np.percentile(ts.difference, p, axis=1)

    prob_buy_wins = (ts.difference > 0).mean(axis=1)

    # Median crossover: first year where median difference > 0
    median_diff = diff_pctiles[50]
    median_crossover = None
    for i in range(1, len(median_diff)):
        if median_diff[i - 1] <= 0 and median_diff[i] > 0:
            median_crossover = int(ts.years[i])
            break

    return MCSummary(
        years=ts.years,
        percentiles=percentiles,
        buy_pctiles=buy_pctiles,
        rent_pctiles=rent_pctiles,
        diff_pctiles=diff_pctiles,
        prob_buy_wins=prob_buy_wins,
        median_crossover=median_crossover,
    )

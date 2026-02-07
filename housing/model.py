"""Core housing expense model.

Simulates year-by-year net worth for BUY vs RENT scenarios.

Buy scenario:
  - Upfront: deposit + stamp duty + LMI (reduces starting cash)
  - Monthly: mortgage repayments (P&I)
  - Annual: council rates, insurance, maintenance, water, strata
  - Asset: property appreciates; mortgage balance decreases
  - Net worth = property value - mortgage balance + remaining investments

Rent scenario:
  - Upfront: nothing (full savings go to investments)
  - Monthly: rent
  - Annual: renters insurance
  - The "saved" money (difference vs buy costs) goes to investments
  - Net worth = investment portfolio value

Both scenarios assume the same total income. Whichever scenario is
cheaper in a given year invests the surplus.
"""

from dataclasses import dataclass

from housing.params import ScenarioParams
from housing.tax import calc_cgt


@dataclass
class YearSnapshot:
    """State at end of a given year."""

    year: int

    # Buy scenario
    property_value: float
    mortgage_balance: float
    mortgage_rate_used: float  # rate in effect this year
    buy_housing_costs: float  # total housing spend this year (mortgage + ongoing)
    buy_cumulative_costs: float
    buy_equity: float  # property_value - mortgage_balance
    buy_investments: float  # any surplus invested
    buy_contributions: float  # cost base of buy investments
    buy_net_worth: float  # equity + investments
    buy_net_worth_real: float  # inflation-adjusted

    # Rent scenario
    annual_rent: float  # rent paid this year
    rent_housing_costs: float  # total housing spend this year
    rent_cumulative_costs: float
    rent_investments: float  # portfolio value
    rent_contributions: float  # cost base of rent investments
    rent_net_worth: float
    rent_net_worth_real: float  # inflation-adjusted

    # Comparison
    net_worth_difference: float  # buy - rent (positive = buy wins)
    net_worth_difference_real: float


def monthly_repayment(principal: float, annual_rate: float, years: int) -> float:
    """Calculate monthly P&I mortgage repayment."""
    if annual_rate == 0:
        return principal / (years * 12)
    r = annual_rate / 12
    n = years * 12
    return principal * (r * (1 + r) ** n) / ((1 + r) ** n - 1)


def mortgage_balance_after_year(
    balance: float, annual_rate: float, monthly_payment: float
) -> tuple[float, float, float]:
    """Simulate 12 months of mortgage payments.

    Returns (new_balance, total_principal_paid, total_interest_paid).
    """
    total_interest = 0.0
    total_principal = 0.0
    for _ in range(12):
        interest = balance * (annual_rate / 12)
        principal = monthly_payment - interest
        if principal > balance:
            principal = balance
            interest = 0
        balance -= principal
        total_interest += interest
        total_principal += principal
        if balance <= 0:
            break
    return max(balance, 0), total_principal, total_interest


def _grow_investments(
    portfolio: float, inv_return_rate: float, dividend_yield: float, marginal_rate: float
) -> float:
    """Grow an investment portfolio for one year, paying tax on dividends."""
    gross_return = portfolio * inv_return_rate
    # Dividends are taxed at marginal rate each year
    if inv_return_rate > 0:
        dividend_portion = dividend_yield / inv_return_rate
    else:
        dividend_portion = 0
    dividend_tax = gross_return * dividend_portion * marginal_rate
    return portfolio + gross_return - dividend_tax


def simulate(params: ScenarioParams) -> list[YearSnapshot]:
    """Run year-by-year simulation for both scenarios."""
    buy = params.buy
    rent = params.rent
    inv = params.investment
    tax = params.tax

    # --- Initial state (year 0) ---
    stamp_duty = buy.get_stamp_duty()
    upfront_buy_costs = buy.deposit + stamp_duty + buy.lmi

    # Calculate initial mortgage payment (may change if rates change)
    current_rate = buy.rate_for_year(1)
    mortgage_bal = buy.loan_amount
    remaining_term = buy.mortgage_term_years
    monthly_pmt = monthly_repayment(mortgage_bal, current_rate, remaining_term)

    # Buy scenario starting state
    property_value = buy.purchase_price
    buy_investments = max(params.existing_savings - upfront_buy_costs, 0)
    buy_contributions = buy_investments  # cost base
    buy_cumulative = upfront_buy_costs

    # Rent scenario starting state
    rent_investments = params.existing_savings
    rent_contributions = params.existing_savings  # cost base
    weekly_rent = rent.weekly_rent
    rent_cumulative = 0.0

    snapshots = []

    # Year 0 snapshot
    buy_nw_0 = (property_value - mortgage_bal) + buy_investments
    rent_nw_0 = rent_investments
    snapshots.append(
        YearSnapshot(
            year=0,
            property_value=property_value,
            mortgage_balance=mortgage_bal,
            mortgage_rate_used=current_rate,
            buy_housing_costs=upfront_buy_costs,
            buy_cumulative_costs=buy_cumulative,
            buy_equity=property_value - mortgage_bal,
            buy_investments=buy_investments,
            buy_contributions=buy_contributions,
            buy_net_worth=buy_nw_0,
            buy_net_worth_real=buy_nw_0,
            annual_rent=0,
            rent_housing_costs=0,
            rent_cumulative_costs=0,
            rent_investments=rent_investments,
            rent_contributions=rent_contributions,
            rent_net_worth=rent_nw_0,
            rent_net_worth_real=rent_nw_0,
            net_worth_difference=buy_nw_0 - rent_nw_0,
            net_worth_difference_real=buy_nw_0 - rent_nw_0,
        )
    )

    for year in range(1, params.time_horizon_years + 1):
        deflator = (1 + params.inflation_rate) ** year

        # --- Handle variable rates ---
        year_rate = buy.rate_for_year(year)
        if year_rate != current_rate and mortgage_bal > 0:
            current_rate = year_rate
            remaining_months = (buy.mortgage_term_years - (year - 1)) * 12
            if remaining_months > 0:
                monthly_pmt = monthly_repayment(
                    mortgage_bal, current_rate, remaining_months / 12
                )

        # --- Buy scenario ---
        if mortgage_bal > 0:
            mortgage_bal, principal_paid, interest_paid = mortgage_balance_after_year(
                mortgage_bal, current_rate, monthly_pmt
            )
            annual_mortgage = principal_paid + interest_paid
        else:
            annual_mortgage = 0
            principal_paid = 0
            interest_paid = 0

        # Property appreciates
        property_value *= 1 + buy.property_appreciation_rate

        # Ongoing ownership costs (fixed costs inflate)
        water_cost = buy.water_rates_annual * (1 + params.inflation_rate) ** year
        strata_cost = buy.strata_annual * (1 + params.inflation_rate) ** year
        ongoing = (
            property_value * buy.council_rates_pct
            + property_value * buy.insurance_pct
            + property_value * buy.maintenance_pct
            + water_cost
            + strata_cost
        )

        buy_year_costs = annual_mortgage + ongoing
        buy_cumulative += buy_year_costs

        # Grow buy-side investments
        buy_investments = _grow_investments(
            buy_investments, inv.return_rate, inv.dividend_yield, tax.marginal_rate
        )

        # --- Rent scenario ---
        annual_rent_cost = weekly_rent * 52
        renters_ins = rent.renters_insurance_annual * (1 + params.inflation_rate) ** year
        rent_year_costs = annual_rent_cost + renters_ins
        rent_cumulative += rent_year_costs

        # Grow rent-side investments
        rent_investments = _grow_investments(
            rent_investments, inv.return_rate, inv.dividend_yield, tax.marginal_rate
        )

        # --- Surplus investment (whoever pays less invests the difference) ---
        if buy_year_costs > rent_year_costs:
            surplus = buy_year_costs - rent_year_costs
            # Mid-year approximation: surplus earns ~half a year of returns
            surplus_with_growth = surplus * (1 + inv.return_rate / 2)
            rent_investments += surplus_with_growth
            rent_contributions += surplus
        elif rent_year_costs > buy_year_costs:
            surplus = rent_year_costs - buy_year_costs
            surplus_with_growth = surplus * (1 + inv.return_rate / 2)
            buy_investments += surplus_with_growth
            buy_contributions += surplus

        buy_equity = property_value - mortgage_bal
        buy_nw = buy_equity + buy_investments
        rent_nw = rent_investments

        buy_nw_real = buy_nw / deflator
        rent_nw_real = rent_nw / deflator

        # Increase rent for next year
        weekly_rent *= 1 + rent.rent_increase_rate

        snapshots.append(
            YearSnapshot(
                year=year,
                property_value=property_value,
                mortgage_balance=mortgage_bal,
                mortgage_rate_used=current_rate,
                buy_housing_costs=buy_year_costs,
                buy_cumulative_costs=buy_cumulative,
                buy_equity=buy_equity,
                buy_investments=buy_investments,
                buy_contributions=buy_contributions,
                buy_net_worth=buy_nw,
                buy_net_worth_real=buy_nw_real,
                annual_rent=annual_rent_cost,
                rent_housing_costs=rent_year_costs,
                rent_cumulative_costs=rent_cumulative,
                rent_investments=rent_investments,
                rent_contributions=rent_contributions,
                rent_net_worth=rent_nw,
                rent_net_worth_real=rent_nw_real,
                net_worth_difference=buy_nw - rent_nw,
                net_worth_difference_real=buy_nw_real - rent_nw_real,
            )
        )

    return snapshots


def net_worth_at_sale(snapshot: YearSnapshot, params: ScenarioParams) -> dict:
    """Calculate after-tax net worth if liquidating everything at a given year.

    Buy: sell property (CGT-exempt for PPOR), pay agent fees, keep investments.
    Rent: sell investments, pay CGT on capital gains (with 50% discount).
    """
    buy = params.buy
    tax = params.tax

    # Buy: sell property (PPOR = no CGT)
    sale_proceeds = snapshot.property_value * (1 - buy.selling_agent_pct) - buy.selling_legal
    buy_after_sale = max(sale_proceeds - snapshot.mortgage_balance, 0) + snapshot.buy_investments

    # Buy-side investments also have CGT if liquidated
    buy_inv_gains = max(snapshot.buy_investments - snapshot.buy_contributions, 0)
    buy_inv_cgt = calc_cgt(buy_inv_gains, tax.marginal_rate, held_over_12_months=True)
    buy_after_sale -= buy_inv_cgt

    # Rent: liquidate investments, pay CGT on actual gains
    rent_gains = max(snapshot.rent_investments - snapshot.rent_contributions, 0)
    rent_cgt = calc_cgt(rent_gains, tax.marginal_rate, held_over_12_months=True)
    rent_after_tax = snapshot.rent_investments - rent_cgt

    deflator = (1 + params.inflation_rate) ** snapshot.year

    return {
        "year": snapshot.year,
        "buy_net_worth_after_sale": buy_after_sale,
        "buy_net_worth_after_sale_real": buy_after_sale / deflator,
        "rent_net_worth_after_tax": rent_after_tax,
        "rent_net_worth_after_tax_real": rent_after_tax / deflator,
        "difference": buy_after_sale - rent_after_tax,
        "difference_real": (buy_after_sale - rent_after_tax) / deflator,
        "buy_wins": buy_after_sale > rent_after_tax,
    }

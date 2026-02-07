"""Sidebar controls for the housing model dashboard."""

from pathlib import Path

import streamlit as st

from housing.config import load_config
from housing.model import monthly_repayment
from housing.params import (
    BuyParams,
    InvestmentParams,
    RentParams,
    ScenarioParams,
    TaxParams,
)
from housing.tax import marginal_rate

CONFIGS_DIR = Path(__file__).parent.parent / "configs"

PRESETS = {
    "Custom": None,
    "Default (Sydney $800k)": "default.yaml",
    "Melbourne House": "melbourne_house.yaml",
    "Sydney Apartment": "sydney_apartment.yaml",
    "Brisbane First Home": "brisbane_first_home.yaml",
    "Rate Drop Scenario": "rate_drop_scenario.yaml",
}

# Default values for all widget keys — used for first-run initialization
# and as the baseline when no preset is loaded.
_DEFAULTS = {
    "buy_purchase_price": 800_000,
    "buy_deposit_pct": 20.0,
    "buy_state": "NSW",
    "buy_first_home": False,
    "buy_new_build": False,
    "buy_appreciation": 5.0,
    "buy_mortgage_rate": 6.2,
    "buy_mortgage_term": 30,
    "buy_lmi": 0,
    "use_rate_schedule": False,
    "buy_council": 0.3,
    "buy_insurance": 0.2,
    "buy_maintenance": 1.0,
    "buy_water": 1_200,
    "buy_strata": 0,
    "buy_agent_pct": 2.0,
    "buy_legal": 2_000,
    "rent_weekly": 650,
    "rent_increase": 4.0,
    "rent_insurance": 300,
    "inv_return": 7.0,
    "inv_dividend": 2.0,
    "inv_franking": 0.0,
    "tax_income": 180_000,
    "inflation": 3.0,
    "time_horizon": 30,
    "existing_savings": 200_000,
}


def _init_defaults():
    """Set default session state values on first run only."""
    for key, val in _DEFAULTS.items():
        if key not in st.session_state:
            st.session_state[key] = val


def _apply_preset():
    """Callback: load preset values into session state."""
    name = st.session_state.preset_selector
    filename = PRESETS.get(name)
    if filename is None:
        return
    params = load_config(CONFIGS_DIR / filename)
    b = params.buy
    r = params.rent
    inv = params.investment

    # Property
    st.session_state.buy_purchase_price = b.purchase_price
    st.session_state.buy_deposit_pct = b.deposit_pct * 100
    st.session_state.buy_state = b.state
    st.session_state.buy_first_home = b.first_home_buyer
    st.session_state.buy_new_build = b.new_build
    st.session_state.buy_appreciation = b.property_appreciation_rate * 100

    # Mortgage
    st.session_state.buy_mortgage_rate = b.mortgage_rate * 100
    st.session_state.buy_mortgage_term = b.mortgage_term_years
    st.session_state.buy_lmi = b.lmi

    # Rate schedule
    if b.rate_schedule:
        st.session_state.use_rate_schedule = True
        st.session_state.rate_schedule_entries = [
            {"year": y, "rate": rt * 100} for y, rt in b.rate_schedule
        ]
    else:
        st.session_state.use_rate_schedule = False
        st.session_state.rate_schedule_entries = []

    # Ongoing costs
    st.session_state.buy_council = b.council_rates_pct * 100
    st.session_state.buy_insurance = b.insurance_pct * 100
    st.session_state.buy_maintenance = b.maintenance_pct * 100
    st.session_state.buy_water = b.water_rates_annual
    st.session_state.buy_strata = b.strata_annual

    # Selling costs
    st.session_state.buy_agent_pct = b.selling_agent_pct * 100
    st.session_state.buy_legal = b.selling_legal

    # Rent
    st.session_state.rent_weekly = r.weekly_rent
    st.session_state.rent_increase = r.rent_increase_rate * 100
    st.session_state.rent_insurance = r.renters_insurance_annual

    # Investment
    st.session_state.inv_return = inv.return_rate * 100
    st.session_state.inv_dividend = inv.dividend_yield * 100
    st.session_state.inv_franking = inv.franking_rate * 100
    st.session_state.tax_income = params.tax.gross_income

    # Scenario
    st.session_state.inflation = params.inflation_rate * 100
    st.session_state.time_horizon = params.time_horizon_years
    st.session_state.existing_savings = params.existing_savings


def render_sidebar() -> ScenarioParams:
    """Render all sidebar controls and return constructed ScenarioParams."""
    _init_defaults()

    st.sidebar.title("Housing Model")

    st.sidebar.selectbox(
        "Load Preset",
        options=list(PRESETS.keys()),
        key="preset_selector",
        on_change=_apply_preset,
    )

    # --- Property ---
    with st.sidebar.expander("Property", expanded=True):
        purchase_price = st.number_input(
            "Purchase Price ($)",
            min_value=100_000,
            max_value=5_000_000,
            step=25_000,
            key="buy_purchase_price",
        )
        deposit_pct = st.slider(
            "Deposit (%)",
            min_value=5.0,
            max_value=50.0,
            step=1.0,
            key="buy_deposit_pct",
        )
        state = st.selectbox(
            "State", options=["NSW", "VIC", "QLD"], key="buy_state"
        )
        col1, col2 = st.columns(2)
        first_home = col1.checkbox("First Home Buyer", key="buy_first_home")
        new_build = col2.checkbox("New Build", key="buy_new_build")
        appreciation = st.slider(
            "Property Appreciation (% p.a.)",
            min_value=0.0,
            max_value=10.0,
            step=0.5,
            key="buy_appreciation",
        )

    # --- Mortgage ---
    with st.sidebar.expander("Mortgage", expanded=True):
        mortgage_rate = st.slider(
            "Mortgage Rate (% p.a.)",
            min_value=2.0,
            max_value=12.0,
            step=0.1,
            key="buy_mortgage_rate",
        )
        mortgage_term = st.select_slider(
            "Mortgage Term (years)",
            options=[15, 20, 25, 30],
            key="buy_mortgage_term",
        )
        lmi = st.number_input(
            "LMI ($)", min_value=0, max_value=50_000, step=500, key="buy_lmi"
        )

        # Variable rate schedule
        use_schedule = st.checkbox(
            "Enable variable rate schedule", key="use_rate_schedule"
        )
        rate_schedule = None
        if use_schedule:
            if "rate_schedule_entries" not in st.session_state:
                st.session_state.rate_schedule_entries = [
                    {"year": 3, "rate": 5.5},
                    {"year": 6, "rate": 5.0},
                ]
            entries = st.session_state.rate_schedule_entries
            to_remove = None
            for i, entry in enumerate(entries):
                c1, c2, c3 = st.columns([2, 2, 1])
                entries[i]["year"] = c1.number_input(
                    "From year",
                    min_value=1,
                    max_value=40,
                    value=entry["year"],
                    key=f"sched_yr_{i}",
                )
                entries[i]["rate"] = c2.number_input(
                    "Rate (%)",
                    min_value=1.0,
                    max_value=12.0,
                    value=entry["rate"],
                    step=0.1,
                    key=f"sched_rt_{i}",
                )
                if c3.button("X", key=f"sched_rm_{i}"):
                    to_remove = i
            if to_remove is not None:
                entries.pop(to_remove)
                st.rerun()
            if st.button("+ Add rate change", key="add_rate_entry"):
                next_yr = (entries[-1]["year"] + 3) if entries else 3
                entries.append({"year": next_yr, "rate": 5.0})
                st.rerun()
            rate_schedule = [(e["year"], e["rate"] / 100) for e in entries]

    # --- Ongoing Costs ---
    with st.sidebar.expander("Ongoing Costs"):
        council = st.slider(
            "Council Rates (% of value)",
            min_value=0.0,
            max_value=1.0,
            step=0.05,
            key="buy_council",
        )
        insurance = st.slider(
            "Insurance (% of value)",
            min_value=0.0,
            max_value=1.0,
            step=0.05,
            key="buy_insurance",
        )
        maintenance = st.slider(
            "Maintenance (% of value)",
            min_value=0.0,
            max_value=3.0,
            step=0.1,
            key="buy_maintenance",
        )
        water = st.number_input(
            "Water Rates ($/yr)",
            min_value=0,
            max_value=5_000,
            step=100,
            key="buy_water",
        )
        strata = st.number_input(
            "Strata ($/yr)",
            min_value=0,
            max_value=20_000,
            step=500,
            key="buy_strata",
        )

    # --- Selling Costs ---
    with st.sidebar.expander("Selling Costs"):
        agent_pct = st.slider(
            "Agent Commission (%)",
            min_value=0.0,
            max_value=5.0,
            step=0.1,
            key="buy_agent_pct",
        )
        selling_legal = st.number_input(
            "Legal Costs ($)",
            min_value=0,
            max_value=10_000,
            step=500,
            key="buy_legal",
        )

    # --- Rent ---
    with st.sidebar.expander("Rent", expanded=True):
        weekly_rent = st.number_input(
            "Weekly Rent ($)",
            min_value=100,
            max_value=3_000,
            step=25,
            key="rent_weekly",
        )
        rent_increase = st.slider(
            "Rent Increase (% p.a.)",
            min_value=0.0,
            max_value=10.0,
            step=0.5,
            key="rent_increase",
        )
        renters_ins = st.number_input(
            "Renters Insurance ($/yr)",
            min_value=0,
            max_value=2_000,
            step=50,
            key="rent_insurance",
        )

    # --- Investment & Tax ---
    with st.sidebar.expander("Investment & Tax", expanded=True):
        inv_return = st.slider(
            "Investment Return (% p.a.)",
            min_value=0.0,
            max_value=15.0,
            step=0.5,
            key="inv_return",
        )
        div_yield = st.slider(
            "Dividend Yield (% p.a.)",
            min_value=0.0,
            max_value=5.0,
            step=0.5,
            key="inv_dividend",
        )
        franking = st.slider(
            "Franking Rate (%)",
            min_value=0.0,
            max_value=100.0,
            step=10.0,
            key="inv_franking",
            help="Proportion of dividends with franking credits. "
            "~60% for Aus equity ETFs, 0% for international.",
        )
        gross_income = st.number_input(
            "Gross Income ($/yr)",
            min_value=0,
            max_value=1_000_000,
            step=5_000,
            key="tax_income",
        )
        marg = marginal_rate(gross_income)
        st.caption(f"Marginal tax rate: {marg:.0%} (incl. Medicare)")

    # --- Scenario ---
    with st.sidebar.expander("Scenario"):
        inflation = st.slider(
            "Inflation (% p.a.)",
            min_value=0.0,
            max_value=8.0,
            step=0.5,
            key="inflation",
        )
        horizon = st.slider(
            "Time Horizon (years)",
            min_value=5,
            max_value=40,
            step=1,
            key="time_horizon",
        )
        savings = st.number_input(
            "Existing Savings ($)",
            min_value=0,
            max_value=2_000_000,
            step=10_000,
            key="existing_savings",
        )

    # --- Build params ---
    buy_params = BuyParams(
        purchase_price=purchase_price,
        deposit_pct=deposit_pct / 100,
        mortgage_rate=mortgage_rate / 100,
        mortgage_term_years=mortgage_term,
        property_appreciation_rate=appreciation / 100,
        lmi=float(lmi),
        state=state,
        first_home_buyer=first_home,
        new_build=new_build,
        rate_schedule=rate_schedule,
        council_rates_pct=council / 100,
        insurance_pct=insurance / 100,
        maintenance_pct=maintenance / 100,
        water_rates_annual=float(water),
        strata_annual=float(strata),
        selling_agent_pct=agent_pct / 100,
        selling_legal=float(selling_legal),
    )

    rent_params = RentParams(
        weekly_rent=float(weekly_rent),
        rent_increase_rate=rent_increase / 100,
        renters_insurance_annual=float(renters_ins),
    )

    inv_params = InvestmentParams(
        return_rate=inv_return / 100,
        dividend_yield=div_yield / 100,
        franking_rate=franking / 100,
    )

    tax_params = TaxParams(gross_income=float(gross_income))

    params = ScenarioParams(
        buy=buy_params,
        rent=rent_params,
        investment=inv_params,
        tax=tax_params,
        inflation_rate=inflation / 100,
        time_horizon_years=horizon,
        existing_savings=float(savings),
    )

    # --- Computed values ---
    st.sidebar.markdown("---")
    st.sidebar.markdown("**Computed Values**")
    stamp = buy_params.get_stamp_duty()
    deposit_amt = buy_params.deposit
    loan = buy_params.loan_amount
    monthly = monthly_repayment(loan, buy_params.mortgage_rate, buy_params.mortgage_term_years)

    c1, c2 = st.sidebar.columns(2)
    c1.metric("Stamp Duty", f"${stamp:,.0f}")
    c2.metric("Deposit", f"${deposit_amt:,.0f}")
    c3, c4 = st.sidebar.columns(2)
    c3.metric("Loan Amount", f"${loan:,.0f}")
    c4.metric("Monthly Repmt", f"${monthly:,.0f}")

    return params

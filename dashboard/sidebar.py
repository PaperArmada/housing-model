"""Sidebar controls for the housing model dashboard."""

import streamlit as st

from configs import DIR as CONFIGS_DIR
from housing.config import load_config
from housing.lmi import estimate_lmi
from housing.model import monthly_repayment
from housing.params import (
    BuyParams,
    InvestmentParams,
    RentParams,
    ScenarioParams,
    TaxParams,
)
from housing.tax import marginal_rate

PRESETS = {
    "Default": None,
    "Sydney House": "default.yaml",
    "Sydney Apartment": "sydney_apartment.yaml",
    "Melbourne House": "melbourne_house.yaml",
    "Melbourne Apartment": "melbourne_apartment.yaml",
    "Brisbane First Home": "brisbane_first_home.yaml",
    "Rate Drop Scenario": "rate_drop_scenario.yaml",
    "Rate Rise Scenario": "rate_rise_scenario.yaml",
}

# Default values for all widget keys — used for first-run initialization
# and as the baseline when no preset is loaded.
_DEFAULTS = {
    "buy_purchase_price": 450_000,
    "buy_deposit_pct": 20.0,
    "buy_state": "NSW",
    "buy_first_home": False,
    "buy_new_build": False,
    "buy_appreciation": 4.0,
    "buy_mortgage_rate": 6.5,
    "buy_mortgage_term": 30,
    "buy_lmi": 0,
    "use_rate_schedule": False,
    "buy_council": 0.25,
    "buy_insurance": 0.15,
    "buy_maintenance": 1.0,
    "buy_water": 600,
    "buy_strata": 0,
    "buy_agent_pct": 2.5,
    "buy_legal": 3_000,
    "rent_weekly": 450,
    "rent_increase": 3.5,
    "rent_insurance": 200,
    "inv_return": 7.0,
    "inv_dividend": 2.0,
    "inv_franking": 0.0,
    "tax_income": 75_000,
    "inflation": 3.0,
    "time_horizon": 40,
    "existing_savings": 100_000,
}


def _init_defaults():
    """Set default session state values on first run only."""
    first_run = "buy_purchase_price" not in st.session_state
    for key, val in _DEFAULTS.items():
        if key not in st.session_state:
            st.session_state[key] = val
    if first_run:
        _snapshot_preset("Default")


def _snapshot_preset(name: str) -> None:
    """Save current widget values as the preset snapshot for change detection."""
    st.session_state._preset_name = name
    st.session_state._preset_snapshot = {
        k: st.session_state.get(k) for k in _DEFAULTS
    }


def _apply_preset():
    """Callback: load preset values into session state."""
    name = st.session_state.preset_selector
    filename = PRESETS.get(name)
    if filename is None:
        # "Default" — reset to defaults
        for key, val in _DEFAULTS.items():
            st.session_state[key] = val
        _snapshot_preset(name)
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
    # Auto-calculate LMI if preset has <20% deposit and no explicit LMI
    if b.lmi > 0:
        st.session_state.buy_lmi = b.lmi
    elif b.deposit_pct < 0.20:
        lvr = 1 - b.deposit_pct
        st.session_state.buy_lmi = estimate_lmi(b.loan_amount, lvr)
    else:
        st.session_state.buy_lmi = 0

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
    st.session_state.time_horizon = min(b.mortgage_term_years + 10, 40)
    st.session_state.existing_savings = params.existing_savings

    _snapshot_preset(name)


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

    # Show modification indicator (exclude buy_lmi since it's auto-derived)
    snapshot = st.session_state.get("_preset_snapshot")
    preset_name = st.session_state.get("_preset_name")
    if snapshot and preset_name:
        changed = [
            k for k in _DEFAULTS
            if k != "buy_lmi" and st.session_state.get(k) != snapshot.get(k)
        ]
        if changed:
            st.sidebar.caption(f"Modified from {preset_name} ({len(changed)} change{'s' if len(changed) != 1 else ''})")

    # --- Property ---
    with st.sidebar.expander("Property", expanded=True):
        purchase_price = st.number_input(
            "Purchase Price ($)",
            min_value=100_000,
            max_value=5_000_000,
            step=25_000,
            key="buy_purchase_price",
            help="Total purchase price of the property.",
        )
        deposit_pct = st.slider(
            "Deposit (%)",
            min_value=5.0,
            max_value=50.0,
            step=1.0,
            key="buy_deposit_pct",
            help="Percentage of purchase price paid upfront. Below 20% typically requires LMI.",
        )
        state = st.selectbox(
            "State",
            options=["NSW", "VIC", "QLD"],
            key="buy_state",
            help="Australian state \u2014 determines stamp duty rates and first home buyer concessions.",
        )
        col1, col2 = st.columns(2)
        first_home = col1.checkbox(
            "First Home Buyer",
            key="buy_first_home",
            help="Eligible for stamp duty concessions and First Home Owner Grant (FHOG) in most states.",
        )
        new_build = col2.checkbox(
            "New Build",
            key="buy_new_build",
            help="New constructions may qualify for the First Home Owner Grant.",
        )
        appreciation = st.slider(
            "Property Appreciation (% p.a.)",
            min_value=0.0,
            max_value=10.0,
            step=0.5,
            key="buy_appreciation",
            help="Expected annual growth in property value. Historical Aus average ~5-7% nominal.",
        )

    # --- Mortgage ---
    with st.sidebar.expander("Mortgage", expanded=True):
        mortgage_rate = st.slider(
            "Mortgage Rate (% p.a.)",
            min_value=2.0,
            max_value=12.0,
            step=0.1,
            key="buy_mortgage_rate",
            help="Annual interest rate on the home loan. Current Aus rates ~6-7% (2025).",
        )
        mortgage_term = st.select_slider(
            "Mortgage Term (years)",
            options=[15, 20, 25, 30],
            key="buy_mortgage_term",
            help="Loan repayment period.",
        )
        # Auto-set time horizon to mortgage term + 10
        st.session_state.time_horizon = min(mortgage_term + 10, 40)

        # Auto-estimate LMI based on deposit and purchase price
        lvr = 1 - deposit_pct / 100
        loan_for_lmi = purchase_price * lvr
        estimated_lmi = estimate_lmi(loan_for_lmi, lvr) if lvr > 0.80 else 0
        st.session_state.buy_lmi = estimated_lmi

        lmi = st.number_input(
            "LMI ($)",
            min_value=0,
            max_value=100_000,
            step=500,
            key="buy_lmi",
            help="Lenders Mortgage Insurance \u2014 auto-estimated from deposit % and loan amount. Adjust if needed.",
        )
        if lvr > 0.80:
            st.caption(
                f"Estimated LMI: ${estimated_lmi:,.0f} "
                f"(LVR {lvr:.0%}, ${loan_for_lmi:,.0f} loan)"
            )
        elif lvr <= 0.80 and lmi > 0:
            st.caption("LMI not required at 20%+ deposit.")

        # Variable rate schedule
        use_schedule = st.checkbox(
            "Enable variable rate schedule",
            key="use_rate_schedule",
            help="Model rate changes over time (e.g., rate cuts expected in future).",
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
            help="Annual council/municipal rates as a percentage of property value. Varies by LGA.",
        )
        insurance = st.slider(
            "Insurance (% of value)",
            min_value=0.0,
            max_value=1.0,
            step=0.05,
            key="buy_insurance",
            help="Annual building insurance as a percentage of property value.",
        )
        maintenance = st.slider(
            "Maintenance (% of value)",
            min_value=0.0,
            max_value=3.0,
            step=0.1,
            key="buy_maintenance",
            help="Annual maintenance budget as a percentage of property value. Rule of thumb: 1% of value.",
        )
        water = st.number_input(
            "Water Rates ($/yr)",
            min_value=0,
            max_value=5_000,
            step=100,
            key="buy_water",
            help="Annual water/sewerage charges. Fixed amount, inflates annually.",
        )
        strata = st.number_input(
            "Strata ($/yr)",
            min_value=0,
            max_value=20_000,
            step=500,
            key="buy_strata",
            help="Annual strata/body corporate levies. Zero for standalone houses, $3k-8k+ for apartments.",
        )

    # --- Selling Costs ---
    with st.sidebar.expander("Selling Costs"):
        agent_pct = st.slider(
            "Agent Commission (%)",
            min_value=0.0,
            max_value=5.0,
            step=0.1,
            key="buy_agent_pct",
            help="Real estate agent commission on eventual sale. Typical: 1.5-2.5%.",
        )
        selling_legal = st.number_input(
            "Legal Costs ($)",
            min_value=0,
            max_value=10_000,
            step=500,
            key="buy_legal",
            help="Conveyancing and legal fees for selling.",
        )

    # --- Rent ---
    with st.sidebar.expander("Rent", expanded=True):
        weekly_rent = st.number_input(
            "Weekly Rent ($)",
            min_value=100,
            max_value=3_000,
            step=25,
            key="rent_weekly",
            help="Current weekly rent for a comparable property.",
        )
        rent_increase = st.slider(
            "Rent Increase (% p.a.)",
            min_value=0.0,
            max_value=10.0,
            step=0.5,
            key="rent_increase",
            help="Expected annual rent increase. Historical Aus average ~3-5%.",
        )
        renters_ins = st.number_input(
            "Renters Insurance ($/yr)",
            min_value=0,
            max_value=2_000,
            step=50,
            key="rent_insurance",
            help="Annual contents insurance for renters.",
        )

    # --- Investment & Tax ---
    with st.sidebar.expander("Investment & Tax", expanded=True):
        inv_return = st.slider(
            "Investment Return (% p.a.)",
            min_value=0.0,
            max_value=15.0,
            step=0.5,
            key="inv_return",
            help="Expected nominal annual return on share investments. ASX long-term ~7-10%.",
        )
        div_yield = st.slider(
            "Dividend Yield (% p.a.)",
            min_value=0.0,
            max_value=5.0,
            step=0.5,
            key="inv_dividend",
            help="Portion of investment return paid as dividends (taxed annually). ASX average ~3-4%.",
        )
        franking = st.slider(
            "Franking Rate (%)",
            min_value=0.0,
            max_value=100.0,
            step=10.0,
            key="inv_franking",
            help="Proportion of dividends that carry franking credits. ~60% for Aus equity ETFs, 0% for international.",
        )
        gross_income = st.number_input(
            "Gross Income ($/yr)",
            min_value=0,
            max_value=1_000_000,
            step=5_000,
            key="tax_income",
            help="Annual gross salary \u2014 used to calculate marginal tax rate for dividend tax and CGT.",
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
            help="Expected annual CPI inflation. RBA targets 2-3%.",
        )
        horizon = st.slider(
            "Time Horizon (years)",
            min_value=5,
            max_value=40,
            step=1,
            key="time_horizon",
            help="How many years to project the comparison.",
        )
        savings = st.number_input(
            "Existing Savings ($)",
            min_value=0,
            max_value=2_000_000,
            step=10_000,
            key="existing_savings",
            help="Total savings available today \u2014 used for deposit (buy) or invested (rent).",
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

"""Streamlit dashboard for the Australian housing buy-vs-rent model."""

import streamlit as st

st.set_page_config(
    page_title="Housing Model - Buy vs Rent",
    page_icon=":house:",
    layout="wide",
)

from housing.config import dict_to_params, params_to_dict
from housing.model import simulate, net_worth_at_sale
from housing.output import crossover_year, to_csv
from housing.sensitivity import frange, sweep

from dashboard.charts import (
    cumulative_costs_chart,
    equity_buildup_chart,
    housing_costs_chart,
    net_worth_chart,
    net_worth_difference_chart,
    sensitivity_chart,
)
from dashboard.formatters import sale_comparison_dataframe, snapshot_dataframe
from dashboard.sidebar import render_sidebar


# --- Cached computation ---


@st.cache_data
def cached_simulate(params_dict: dict) -> list:
    params = dict_to_params(params_dict)
    return simulate(params)


@st.cache_data
def cached_sale(params_dict: dict, year: int) -> dict:
    params = dict_to_params(params_dict)
    snapshots = simulate(params)
    snapshot_map = {s.year: s for s in snapshots}
    return net_worth_at_sale(snapshot_map[year], params)


@st.cache_data
def cached_sweep(params_dict: dict, param_path: str, values_tuple: tuple) -> list:
    params = dict_to_params(params_dict)
    return sweep(params, param_path, list(values_tuple))


# --- Layout ---

params = render_sidebar()
params_dict = params_to_dict(params)
snapshots = cached_simulate(params_dict)
final = snapshots[-1]
sale_result = cached_sale(params_dict, final.year)

# Header
st.header("Buy vs Rent Analysis")

# Row 1: Net worth summary
m1, m2, m3, m4 = st.columns(4)
m1.metric("Buy Net Worth", f"${final.buy_net_worth:,.0f}")
m2.metric("Rent Net Worth", f"${final.rent_net_worth:,.0f}")
diff = final.net_worth_difference
winner = "Buy" if diff > 0 else "Rent"
m3.metric("Difference", f"${abs(diff):,.0f}", delta=f"{winner} wins")
xover = crossover_year(snapshots)
m4.metric("Crossover Year", f"Year {xover}" if xover else "Never")

# Row 2: After-tax liquidation
m5, m6, m7 = st.columns(3)
m5.metric(
    "Buy After Sale (real)",
    f"${sale_result['buy_net_worth_after_sale_real']:,.0f}",
)
m6.metric(
    "Rent After CGT (real)",
    f"${sale_result['rent_net_worth_after_tax_real']:,.0f}",
)
sale_diff = sale_result["difference_real"]
sale_winner = "Buy" if sale_result["buy_wins"] else "Rent"
m7.metric(
    "After-tax Diff (real)",
    f"${abs(sale_diff):,.0f}",
    delta=f"{sale_winner} wins",
)

st.divider()

# --- Tabs ---
tab_nw, tab_costs, tab_equity, tab_sens, tab_data = st.tabs(
    ["Net Worth", "Housing Costs", "Equity & Debt", "Sensitivity", "Data"]
)

with tab_nw:
    use_real = st.radio(
        "Values",
        ["Nominal", "Real (inflation-adjusted)"],
        horizontal=True,
        key="nw_real_toggle",
    ).startswith("Real")

    st.plotly_chart(
        net_worth_chart(snapshots, real=use_real), use_container_width=True
    )
    st.plotly_chart(
        net_worth_difference_chart(snapshots, real=use_real),
        use_container_width=True,
    )

with tab_costs:
    st.plotly_chart(housing_costs_chart(snapshots), use_container_width=True)
    st.plotly_chart(cumulative_costs_chart(snapshots), use_container_width=True)

with tab_equity:
    st.plotly_chart(equity_buildup_chart(snapshots), use_container_width=True)

with tab_sens:
    SWEEP_PARAMS = {
        "Mortgage Rate": ("buy.mortgage_rate", 0.03, 0.09, 0.005, True),
        "Purchase Price": ("buy.purchase_price", 500_000, 1_500_000, 50_000, False),
        "Property Appreciation": (
            "buy.property_appreciation_rate",
            0.02,
            0.08,
            0.005,
            True,
        ),
        "Weekly Rent": ("rent.weekly_rent", 300, 1200, 50, False),
        "Rent Increase Rate": ("rent.rent_increase_rate", 0.02, 0.08, 0.005, True),
        "Investment Return": ("investment.return_rate", 0.04, 0.12, 0.005, True),
        "Deposit %": ("buy.deposit_pct", 0.05, 0.40, 0.05, True),
        "Gross Income": ("tax.gross_income", 80_000, 300_000, 10_000, False),
    }

    selected = st.selectbox(
        "Parameter to sweep", list(SWEEP_PARAMS.keys()), key="sens_param"
    )
    param_path, default_min, default_max, default_step, is_pct = SWEEP_PARAMS[
        selected
    ]

    sc1, sc2, sc3 = st.columns(3)
    if is_pct:
        sweep_min = sc1.number_input(
            "Min (%)", value=default_min * 100, step=default_step * 100
        )
        sweep_max = sc2.number_input(
            "Max (%)", value=default_max * 100, step=default_step * 100
        )
        sweep_step = sc3.number_input(
            "Step (%)", value=default_step * 100, step=default_step * 100, min_value=0.1
        )
        values = frange(sweep_min / 100, sweep_max / 100, sweep_step / 100)
    else:
        sweep_min = sc1.number_input("Min", value=default_min, step=default_step)
        sweep_max = sc2.number_input("Max", value=default_max, step=default_step)
        sweep_step = sc3.number_input(
            "Step", value=default_step, step=default_step, min_value=1.0
        )
        values = frange(sweep_min, sweep_max, sweep_step)

    if values:
        results = cached_sweep(params_dict, param_path, tuple(values))
        st.plotly_chart(
            sensitivity_chart(results, selected, is_pct), use_container_width=True
        )

        crossovers = [r.crossover for r in results if r.crossover is not None]
        if crossovers:
            st.caption(
                f"Crossover year range: {min(crossovers)} - {max(crossovers)}"
            )

with tab_data:
    st.subheader("Year-by-Year Breakdown")
    st.dataframe(snapshot_dataframe(snapshots), use_container_width=True, height=400)

    st.subheader("After-Tax Liquidation at Key Years")
    st.dataframe(
        sale_comparison_dataframe(snapshots, params), use_container_width=True
    )

    csv_data = to_csv(snapshots)
    st.download_button(
        "Download Full Data (CSV)", csv_data, "housing_model.csv", "text/csv"
    )

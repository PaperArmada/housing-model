"""Streamlit dashboard for the Australian housing buy-vs-rent model."""

import streamlit as st

st.set_page_config(
    page_title="Housing Model - Buy vs Rent",
    page_icon=":house:",
    layout="wide",
)

@st.dialog("Disclaimer")
def _show_disclaimer():
    st.markdown(
        "This tool is for **educational and informational purposes only**. "
        "It is not financial advice.\n\n"
        "The model makes simplifying assumptions and uses estimated parameters "
        "that may not reflect your actual situation. Always consult a qualified "
        "financial adviser before making property or investment decisions."
    )
    if st.button("I understand", use_container_width=True):
        st.session_state.disclaimer_accepted = True
        st.rerun()


if not st.session_state.get("disclaimer_accepted", False):
    _show_disclaimer()
    st.stop()

from housing.config import dict_to_params, params_to_dict
from housing.mc_params import MCConfig
from housing.model import simulate, net_worth_at_sale
from housing.monte_carlo import mc_simulate, summarize
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
from docs import DIR as DOCS_DIR
from dashboard.compare_tab import render_compare_tab
from dashboard.formatters import sale_comparison_dataframe, snapshot_dataframe
from dashboard.mc_charts import fan_chart, prob_buy_wins_chart, terminal_histogram
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


@st.cache_data
def cached_mc(params_dict: dict, n_runs: int, seed: int | None, **vol_overrides):
    params = dict_to_params(params_dict)
    config = MCConfig(n_runs=n_runs, seed=seed, **vol_overrides)
    ts = mc_simulate(params, config)
    summary = summarize(ts)
    return ts, summary


@st.cache_data
def cached_stability(
    params_dict: dict, n_seeds: int, runs_per_seed: int, **vol_overrides
) -> dict:
    """Run MC with multiple random seeds and collect summary statistics."""
    import numpy as np

    params = dict_to_params(params_dict)
    horizon = params.time_horizon_years
    rng = np.random.default_rng(42)
    seeds = rng.integers(1, 1_000_000, size=n_seeds).tolist()

    med_diffs = []
    prob_buy_wins = []
    p10s = []
    p90s = []
    med_buy_nws = []
    med_rent_nws = []
    crossovers = []

    for s in seeds:
        config = MCConfig(n_runs=runs_per_seed, seed=s, **vol_overrides)
        ts = mc_simulate(params, config)
        summary = summarize(ts)
        med_diffs.append(summary.diff_pctiles[50][horizon])
        prob_buy_wins.append(summary.prob_buy_wins[horizon] * 100)
        p10s.append(summary.diff_pctiles[10][horizon])
        p90s.append(summary.diff_pctiles[90][horizon])
        med_buy_nws.append(summary.buy_pctiles[50][horizon])
        med_rent_nws.append(summary.rent_pctiles[50][horizon])
        crossovers.append(summary.median_crossover)

    def _stats(vals):
        a = np.array(vals, dtype=float)
        return float(np.mean(a)), float(np.std(a))

    return {
        "n_seeds": n_seeds,
        "runs_per_seed": runs_per_seed,
        "median_difference": _stats(med_diffs),
        "prob_buy_wins": _stats(prob_buy_wins),
        "p10_difference": _stats(p10s),
        "p90_difference": _stats(p90s),
        "median_buy_nw": _stats(med_buy_nws),
        "median_rent_nw": _stats(med_rent_nws),
        "crossover_years": [c for c in crossovers if c is not None],
    }


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
st.caption(
    "**Row 1** — Nominal net worth at the end of the time horizon. "
    "Buy = property value minus mortgage plus invested surplus. "
    "Rent = full investment portfolio after paying rent. "
    "Crossover is the first year where buying pulls ahead of renting."
)

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
st.caption(
    "**Row 2** — What you'd actually walk away with if you liquidated everything at the "
    "end of the horizon, after selling costs (agent commission, legal fees), capital gains "
    "tax, and adjusting for inflation. This is the most realistic comparison."
)

st.divider()

# --- Tabs ---
tab_nw, tab_costs, tab_equity, tab_mc, tab_sens, tab_compare, tab_data, tab_docs = st.tabs([
    ":material/trending_up: Net Worth",
    ":material/payments: Housing Costs",
    ":material/real_estate_agent: Equity & Debt",
    ":material/casino: Monte Carlo",
    ":material/tune: Sensitivity",
    ":material/compare_arrows: Compare",
    ":material/table_chart: Data",
    ":material/menu_book: Docs",
])

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
    st.caption(
        "Total net worth over time for each scenario. Buy net worth = property value "
        "minus remaining mortgage plus any invested surplus. Rent net worth = the full "
        "investment portfolio. Toggle between nominal and real (inflation-adjusted) values."
    )
    st.plotly_chart(
        net_worth_difference_chart(snapshots, real=use_real),
        use_container_width=True,
    )
    st.caption(
        "The gap between buy and rent net worth each year. Positive values mean buying is "
        "ahead; negative means renting is ahead. The crossover point (if any) is where "
        "the line crosses zero."
    )

with tab_costs:
    st.plotly_chart(housing_costs_chart(snapshots), use_container_width=True)
    st.caption(
        "Annual housing costs for each scenario. Buy includes mortgage repayments, "
        "council rates, insurance, maintenance, water, and strata. Rent includes "
        "weekly rent and renters insurance. Both increase with inflation over time."
    )
    st.plotly_chart(cumulative_costs_chart(snapshots), use_container_width=True)
    st.caption(
        "Total cumulative amount spent on housing from year 0 to each year. "
        "This shows the running total of all cash outlays — note that mortgage "
        "payments include principal repayment (which builds equity) as well as interest."
    )

with tab_equity:
    st.plotly_chart(equity_buildup_chart(snapshots), use_container_width=True)
    st.caption(
        "Tracks the buyer's property equity (property value minus mortgage balance), "
        "the remaining mortgage balance, and the renter's investment portfolio. "
        "The buyer's equity grows from both property appreciation and mortgage paydown. "
        "The renter's portfolio grows from investment returns on the full savings pool."
    )

with tab_mc:
    mc_enabled = st.checkbox("Enable Monte Carlo simulation", key="mc_enabled")

    if mc_enabled:
        mc_c1, mc_c2 = st.columns(2)
        n_runs = mc_c1.slider(
            "Number of runs",
            min_value=500,
            max_value=10_000,
            value=5_000,
            step=500,
            key="mc_n_runs",
        )
        seed_input = mc_c2.number_input(
            "Random seed (0 = random)",
            min_value=0,
            max_value=999_999,
            value=0,
            step=1,
            key="mc_seed",
        )
        seed = seed_input if seed_input > 0 else None

        with st.expander("Volatility settings"):
            vc1, vc2 = st.columns(2)
            std_prop = vc1.slider(
                "Property appreciation std",
                min_value=0.0, max_value=0.25, value=0.10, step=0.01,
                key="mc_std_prop",
                help="Annual standard deviation of property appreciation rate",
            )
            std_inv = vc2.slider(
                "Investment return std",
                min_value=0.0, max_value=0.30, value=0.15, step=0.01,
                key="mc_std_inv",
                help="Annual standard deviation of investment returns",
            )
            vc3, vc4 = st.columns(2)
            std_rent = vc3.slider(
                "Rent increase std",
                min_value=0.0, max_value=0.05, value=0.02, step=0.005,
                key="mc_std_rent",
            )
            std_infl = vc4.slider(
                "Inflation std",
                min_value=0.0, max_value=0.04, value=0.015, step=0.005,
                key="mc_std_infl",
            )
            std_mort = st.slider(
                "Mortgage rate std",
                min_value=0.0, max_value=0.03, value=0.01, step=0.005,
                key="mc_std_mort",
            )

        # Run MC simulation (cached)
        ts, summary = cached_mc(
            params_dict,
            n_runs=n_runs,
            seed=seed,
            std_property_appreciation=std_prop,
            std_investment_return=std_inv,
            std_rent_increase=std_rent,
            std_inflation=std_infl,
            std_mortgage_rate=std_mort,
        )

        # Summary stats
        horizon = params.time_horizon_years
        st.subheader("Summary")
        sc1, sc2, sc3, sc4 = st.columns(4)
        med_diff = summary.diff_pctiles[50][horizon]
        sc1.metric("Median Difference", f"${med_diff:,.0f}")
        prob_bw = summary.prob_buy_wins[horizon] * 100
        sc2.metric(f"P(Buy wins) at Year {horizon}", f"{prob_bw:.1f}%")
        p10 = summary.diff_pctiles[10][horizon]
        p90 = summary.diff_pctiles[90][horizon]
        sc3.metric("10th Percentile", f"${p10:,.0f}")
        sc4.metric("90th Percentile", f"${p90:,.0f}")

        if summary.median_crossover:
            st.caption(f"Median crossover year: {summary.median_crossover}")

        # Fan charts
        st.plotly_chart(
            fan_chart(summary, "difference", "Net Worth Difference (Buy - Rent)"),
            use_container_width=True,
        )
        st.caption(
            "Fan chart showing the range of buy-minus-rent outcomes across all simulations. "
            "The inner band is the 25th-75th percentile (middle 50% of outcomes), the outer "
            "band is 10th-90th. If the median stays below zero, renting is more likely to win."
        )

        fc1, fc2 = st.columns(2)
        with fc1:
            st.plotly_chart(
                fan_chart(summary, "buy", "Buy Net Worth"),
                use_container_width=True,
            )
            st.caption(
                "Distribution of buy-scenario net worth across simulations. Wider bands "
                "indicate more uncertainty, driven mainly by property appreciation volatility."
            )
        with fc2:
            st.plotly_chart(
                fan_chart(summary, "rent", "Rent Net Worth"),
                use_container_width=True,
            )
            st.caption(
                "Distribution of rent-scenario net worth. Typically wider than buy because "
                "equity market returns (15% std) are more volatile than property (10% std)."
            )

        # Probability chart
        st.plotly_chart(
            prob_buy_wins_chart(summary), use_container_width=True
        )
        st.caption(
            "The percentage of simulations where buying has a higher net worth than renting "
            "at each year. Above 50% means buying wins more often than not. This accounts "
            "for the full range of correlated economic scenarios."
        )

        # Terminal distribution
        hist_year = st.slider(
            "Distribution at year",
            min_value=1,
            max_value=horizon,
            value=horizon,
            key="mc_hist_year",
        )
        st.plotly_chart(
            terminal_histogram(ts, hist_year), use_container_width=True
        )
        st.caption(
            "Overlaid histograms of buy and rent net worth at the selected year. "
            "Where the distributions overlap, outcomes are similar. Dashed lines "
            "show the median for each scenario. Use the slider to explore different years."
        )

        # --- Stability analysis ---
        with st.expander("Stability Analysis"):
            st.caption(
                "Tests how stable the MC results are by running the simulation multiple "
                "times with different random seeds. Low standard deviations mean the "
                "results are reliable; high values suggest increasing the number of runs."
            )
            stab_c1, stab_c2 = st.columns(2)
            n_seeds = stab_c1.slider(
                "Number of seeds",
                min_value=5,
                max_value=50,
                value=20,
                step=5,
                key="stab_n_seeds",
                help="How many independent MC runs to perform.",
            )
            runs_per_seed = stab_c2.slider(
                "Runs per seed",
                min_value=500,
                max_value=10_000,
                value=1_000,
                step=500,
                key="stab_runs_per_seed",
                help="Simulations per seed. Lower is faster; higher is more precise.",
            )
            if st.button("Run stability analysis", key="run_stability"):
                vol_overrides = dict(
                    std_property_appreciation=std_prop,
                    std_investment_return=std_inv,
                    std_rent_increase=std_rent,
                    std_inflation=std_infl,
                    std_mortgage_rate=std_mort,
                )
                with st.spinner(f"Running {n_seeds} seeds x {runs_per_seed} runs..."):
                    result = cached_stability(
                        params_dict, n_seeds, runs_per_seed, **vol_overrides
                    )
                st.session_state.stability_result = result

            if "stability_result" in st.session_state:
                result = st.session_state.stability_result

                def _fmt_dollar(mean, std):
                    return f"${mean:,.0f}  (\u00b1 ${std:,.0f})"

                def _fmt_pct(mean, std):
                    return f"{mean:.1f}%  (\u00b1 {std:.1f}%)"

                st.markdown(
                    f"**{result['n_seeds']} seeds \u00d7 "
                    f"{result['runs_per_seed']:,} runs each**"
                )

                data = {
                    "Metric": [
                        "Median Difference (Buy - Rent)",
                        "P(Buy wins)",
                        "10th Percentile Difference",
                        "90th Percentile Difference",
                        "Median Buy Net Worth",
                        "Median Rent Net Worth",
                    ],
                    "Mean": [
                        f"${result['median_difference'][0]:,.0f}",
                        f"{result['prob_buy_wins'][0]:.1f}%",
                        f"${result['p10_difference'][0]:,.0f}",
                        f"${result['p90_difference'][0]:,.0f}",
                        f"${result['median_buy_nw'][0]:,.0f}",
                        f"${result['median_rent_nw'][0]:,.0f}",
                    ],
                    "Std Dev": [
                        f"${result['median_difference'][1]:,.0f}",
                        f"{result['prob_buy_wins'][1]:.1f}%",
                        f"${result['p10_difference'][1]:,.0f}",
                        f"${result['p90_difference'][1]:,.0f}",
                        f"${result['median_buy_nw'][1]:,.0f}",
                        f"${result['median_rent_nw'][1]:,.0f}",
                    ],
                }
                st.dataframe(data, use_container_width=True, hide_index=True)

                xovers = result["crossover_years"]
                if xovers:
                    st.caption(
                        f"Median crossover year appeared in {len(xovers)}/{result['n_seeds']} "
                        f"seeds (range: {min(xovers)}-{max(xovers)})."
                    )
                else:
                    st.caption("No median crossover year in any seed.")
    else:
        st.info(
            "Enable Monte Carlo simulation above to see probabilistic outcomes "
            "with fan charts showing the range of likely results."
        )

with tab_sens:
    st.caption(
        "Sweep a single parameter across a range of values while holding everything "
        "else constant. The chart shows how the final net worth difference (buy minus "
        "rent) changes as the selected parameter varies. Useful for identifying which "
        "assumptions matter most to the outcome."
    )
    SWEEP_PARAMS = {
        "Mortgage Rate": ("buy.mortgage_rate", 0.03, 0.09, 0.005, True),
        "Purchase Price": ("buy.purchase_price", 500_000.0, 1_500_000.0, 50_000.0, False),
        "Property Appreciation": (
            "buy.property_appreciation_rate",
            0.02,
            0.08,
            0.005,
            True,
        ),
        "Weekly Rent": ("rent.weekly_rent", 300.0, 1200.0, 50.0, False),
        "Rent Increase Rate": ("rent.rent_increase_rate", 0.02, 0.08, 0.005, True),
        "Investment Return": ("investment.return_rate", 0.04, 0.12, 0.005, True),
        "Deposit %": ("buy.deposit_pct", 0.05, 0.40, 0.05, True),
        "Gross Income": ("tax.gross_income", 80_000.0, 300_000.0, 10_000.0, False),
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

with tab_compare:
    render_compare_tab(params, params_dict)

with tab_data:
    st.subheader("Year-by-Year Breakdown")
    st.caption(
        "Full year-by-year simulation data for both scenarios, including property value, "
        "mortgage balance, investment portfolio, annual costs, and net worth in both "
        "nominal and real (inflation-adjusted) terms."
    )
    st.dataframe(snapshot_dataframe(snapshots), use_container_width=True, height=400)

    st.subheader("After-Tax Liquidation at Key Years")
    st.caption(
        "What you'd walk away with if you sold the property (or liquidated investments) "
        "at years 5, 10, 15, 20, 25, and 30. Accounts for selling costs, capital gains "
        "tax with the 50% discount, and inflation adjustment."
    )
    st.dataframe(
        sale_comparison_dataframe(snapshots, params), use_container_width=True
    )

    csv_data = to_csv(snapshots)
    st.download_button(
        "Download Full Data (CSV)", csv_data, "housing_model.csv", "text/csv"
    )


with tab_docs:
    docs = sorted(DOCS_DIR.glob("*.md")) if DOCS_DIR.exists() else []
    if not docs:
        st.info("No documentation files found in docs/.")
    else:
        doc_names = {d.stem.replace("_", " ").title(): d for d in docs}
        selected_doc = st.selectbox(
            "Document", list(doc_names.keys()), key="docs_selector"
        )
        st.markdown(doc_names[selected_doc].read_text())

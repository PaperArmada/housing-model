"""Compare tab — load multiple scenarios and compare buy-vs-rent outcomes."""

from pathlib import Path
import uuid

import streamlit as st

from housing.config import dict_to_params, load_config, parse_config_text, params_to_dict
from housing.model import simulate
from housing.output import crossover_year
from housing.params import ScenarioParams

from dashboard.compare_charts import comparison_difference_chart, comparison_net_worth_chart
from dashboard.sidebar import CONFIGS_DIR, PRESETS

MAX_SCENARIOS = 12


def _get_scenarios() -> list[dict]:
    if "compare_scenarios" not in st.session_state:
        st.session_state.compare_scenarios = []
    return st.session_state.compare_scenarios


def _add_scenario(name: str, params_dict: dict, source: str) -> None:
    scenarios = _get_scenarios()
    if len(scenarios) >= MAX_SCENARIOS:
        st.warning(f"Maximum {MAX_SCENARIOS} scenarios reached. Remove one first.")
        return
    scenarios.append({
        "id": str(uuid.uuid4()),
        "name": name,
        "params_dict": params_dict,
        "source": source,
    })


@st.cache_data
def _cached_simulate(params_dict: dict) -> list:
    params = dict_to_params(params_dict)
    return simulate(params)


def render_compare_tab(current_params: ScenarioParams, current_params_dict: dict) -> None:
    """Render the Compare tab UI."""
    st.subheader("Multi-Scenario Comparison")
    st.caption(
        "Load multiple scenarios and compare their buy-vs-rent outcomes side by side. "
        "Add scenarios from presets, the current sidebar configuration, or uploaded/pasted config files."
    )

    scenarios = _get_scenarios()

    # --- Scenario manager ---
    preset_names = [k for k in PRESETS if PRESETS[k] is not None]

    col_preset, col_sidebar, col_upload, col_paste = st.columns(4)

    with col_preset:
        st.markdown("**Add from Preset**")
        preset_choice = st.selectbox(
            "Preset",
            preset_names,
            key="compare_preset_select",
            label_visibility="collapsed",
        )
        if st.button("Add Preset", key="compare_add_preset"):
            filename = PRESETS[preset_choice]
            params = load_config(CONFIGS_DIR / filename)
            _add_scenario(preset_choice, params_to_dict(params), f"Preset: {preset_choice}")
            st.rerun()

    with col_sidebar:
        st.markdown("**Add Current Sidebar**")
        if st.button("Snapshot Sidebar", key="compare_add_sidebar"):
            _add_scenario("Current Sidebar", current_params_dict, "Sidebar snapshot")
            st.rerun()

    with col_upload:
        st.markdown("**Upload YAML/JSON**")
        uploaded = st.file_uploader(
            "Upload",
            type=["yaml", "yml", "json"],
            key="compare_file_upload",
            label_visibility="collapsed",
            accept_multiple_files=True,
        )
        if st.button("Add Upload", key="compare_add_upload") and uploaded:
            errors = []
            added = 0
            for f in uploaded:
                try:
                    text = f.read().decode("utf-8")
                    params = parse_config_text(text)
                    name = f.name.rsplit(".", 1)[0]
                    _add_scenario(name, params_to_dict(params), f"Upload: {f.name}")
                    added += 1
                except Exception as e:
                    errors.append(f"{f.name}: {e}")
            if errors:
                st.error("Failed to parse:\n" + "\n".join(errors))
            if added:
                st.rerun()

    with col_paste:
        st.markdown("**Paste YAML/JSON**")
        pasted = st.text_area(
            "Config text",
            height=100,
            key="compare_paste_area",
            label_visibility="collapsed",
        )
        if st.button("Add Pasted", key="compare_add_pasted") and pasted.strip():
            try:
                params = parse_config_text(pasted)
                _add_scenario("Pasted Config", params_to_dict(params), "Pasted text")
                st.rerun()
            except Exception as e:
                st.error(f"Failed to parse text: {e}")

    # --- Scenario list ---
    if scenarios:
        st.markdown("---")
        st.markdown("**Loaded Scenarios**")
        to_remove = None
        for idx, scenario in enumerate(scenarios):
            colour = ["#2196F3", "#F44336", "#4CAF50", "#FF9800", "#9C27B0", "#00BCD4"][idx % 6]
            sc1, sc2, sc3, sc4 = st.columns([0.5, 3, 2, 1])
            sc1.markdown(
                f'<div style="width:20px;height:20px;background:{colour};border-radius:4px;margin-top:8px"></div>',
                unsafe_allow_html=True,
            )
            new_name = sc2.text_input(
                "Name",
                value=scenario["name"],
                key=f"compare_name_{scenario['id']}",
                label_visibility="collapsed",
            )
            scenario["name"] = new_name
            sc3.caption(scenario["source"])
            if sc4.button("Remove", key=f"compare_rm_{scenario['id']}"):
                to_remove = idx
        if to_remove is not None:
            scenarios.pop(to_remove)
            st.rerun()

    # --- Charts ---
    if len(scenarios) >= 2:
        st.markdown("---")

        # Check for differing horizons
        horizons = set()
        scenario_data: list[tuple[str, list]] = []
        for scenario in scenarios:
            snapshots = _cached_simulate(scenario["params_dict"])
            scenario_data.append((scenario["name"], snapshots))
            horizons.add(len(snapshots) - 1)  # year count = len - 1

        if len(horizons) > 1:
            st.info(
                "Scenarios have different time horizons. Each line is plotted to its own horizon length."
            )

        use_real = st.radio(
            "Values",
            ["Nominal", "Real (inflation-adjusted)"],
            horizontal=True,
            key="compare_real_toggle",
        ).startswith("Real")

        st.plotly_chart(
            comparison_difference_chart(scenario_data, real=use_real),
            use_container_width=True,
        )
        st.caption(
            "Buy-minus-Rent net worth difference for each scenario. Lines above zero favour buying; "
            "below zero favour renting. Compare which scenario reaches positive territory first."
        )

        st.plotly_chart(
            comparison_net_worth_chart(scenario_data, real=use_real),
            use_container_width=True,
        )
        st.caption(
            "Buy (solid) and Rent (dashed) net worth lines overlaid. Same colour = same scenario. "
            "Compare absolute net worth levels across scenarios."
        )

        # --- Summary table ---
        st.markdown("---")
        st.subheader("Summary Table")

        rows = []
        for i, (name, snapshots) in enumerate(scenario_data):
            final = snapshots[-1]
            params_d = scenarios[i]["params_dict"]
            xover = crossover_year(snapshots)

            rows.append({
                "Scenario": name,
                "Purchase Price": params_d["buy"]["purchase_price"],
                "Weekly Rent": params_d["rent"]["weekly_rent"],
                "Horizon (yrs)": final.year,
                "Final Buy NW": round(final.buy_net_worth),
                "Final Rent NW": round(final.rent_net_worth),
                "Difference": round(final.net_worth_difference),
                "Winner": "Buy" if final.net_worth_difference > 0 else "Rent",
                "Crossover Year": xover if xover else None,
            })

        dollar_fmt = st.column_config.NumberColumn(format="dollar")
        st.dataframe(
            rows,
            use_container_width=True,
            hide_index=True,
            column_config={
                "Purchase Price": dollar_fmt,
                "Weekly Rent": dollar_fmt,
                "Final Buy NW": dollar_fmt,
                "Final Rent NW": dollar_fmt,
                "Difference": dollar_fmt,
                "Crossover Year": st.column_config.NumberColumn(format="Year %d"),
            },
        )
    elif len(scenarios) == 1:
        st.info("Add at least 2 scenarios to see comparison charts.")

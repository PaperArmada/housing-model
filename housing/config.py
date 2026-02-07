"""YAML config loading and validation."""

import json
from pathlib import Path

from housing.params import (
    BuyParams,
    InvestmentParams,
    RentParams,
    ScenarioParams,
    TaxParams,
)

# Use json for built-in parsing; YAML support is optional
try:
    import yaml

    HAS_YAML = True
except ImportError:
    HAS_YAML = False


def load_config(path: str | Path) -> ScenarioParams:
    """Load scenario parameters from a YAML or JSON file."""
    path = Path(path)
    text = path.read_text()

    if path.suffix in (".yaml", ".yml"):
        if not HAS_YAML:
            raise ImportError(
                "PyYAML is required to load YAML configs. "
                "Install with: pip install pyyaml"
            )
        data = yaml.safe_load(text)
    elif path.suffix == ".json":
        data = json.loads(text)
    else:
        # Try YAML first, fall back to JSON
        if HAS_YAML:
            data = yaml.safe_load(text)
        else:
            data = json.loads(text)

    return dict_to_params(data)


def dict_to_params(data: dict) -> ScenarioParams:
    """Convert a nested dict to ScenarioParams."""
    buy_data = data.get("buy", {})
    rent_data = data.get("rent", {})
    inv_data = data.get("investment", {})
    tax_data = data.get("tax", {})

    # Handle rate_schedule: convert list of dicts to list of tuples
    if "rate_schedule" in buy_data and buy_data["rate_schedule"]:
        schedule = []
        for entry in buy_data["rate_schedule"]:
            if isinstance(entry, dict):
                schedule.append((entry["year"], entry["rate"]))
            elif isinstance(entry, (list, tuple)):
                schedule.append((entry[0], entry[1]))
        buy_data["rate_schedule"] = schedule

    buy = BuyParams(**{k: v for k, v in buy_data.items() if hasattr(BuyParams, k)})
    rent_params = RentParams(**{k: v for k, v in rent_data.items() if hasattr(RentParams, k)})
    inv = InvestmentParams(**{k: v for k, v in inv_data.items() if hasattr(InvestmentParams, k)})
    tax = TaxParams(**{k: v for k, v in tax_data.items() if hasattr(TaxParams, k)})

    top_keys = {"inflation_rate", "time_horizon_years", "existing_savings"}
    top = {k: v for k, v in data.items() if k in top_keys}

    return ScenarioParams(buy=buy, rent=rent_params, investment=inv, tax=tax, **top)


def params_to_dict(params: ScenarioParams) -> dict:
    """Convert ScenarioParams to a serialisable dict."""
    from dataclasses import asdict

    d = asdict(params)
    # rate_schedule tuples -> dicts for YAML readability
    if d["buy"]["rate_schedule"]:
        d["buy"]["rate_schedule"] = [
            {"year": y, "rate": r} for y, r in d["buy"]["rate_schedule"]
        ]
    return d

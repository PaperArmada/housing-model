"""CLI entry point for the housing expense model."""

import argparse
import sys

from housing.config import load_config
from housing.model import simulate
from housing.output import full_report, detailed_table, to_csv
from housing.params import ScenarioParams
from housing.sensitivity import sweep, format_sweep, frange


def cmd_run(args: argparse.Namespace) -> None:
    """Run a simulation from a config file."""
    if args.config:
        params = load_config(args.config)
    else:
        params = ScenarioParams()

    snapshots = simulate(params)

    if args.csv:
        print(to_csv(snapshots))
    elif args.detailed:
        from housing.output import summary_header
        print(summary_header(params))
        print(detailed_table(snapshots))
    else:
        print(full_report(snapshots, params))


def cmd_sensitivity(args: argparse.Namespace) -> None:
    """Run sensitivity analysis on a parameter."""
    if args.config:
        params = load_config(args.config)
    else:
        params = ScenarioParams()

    parts = args.range.split(",")
    if len(parts) != 3:
        print("Error: --range must be start,stop,step (e.g., 0.04,0.08,0.005)", file=sys.stderr)
        sys.exit(1)

    start, stop, step = float(parts[0]), float(parts[1]), float(parts[2])
    values = frange(start, stop, step)

    is_pct = any(
        kw in args.param
        for kw in ["rate", "pct", "yield", "appreciation", "inflation"]
    )

    results = sweep(params, args.param, values)
    print(format_sweep(args.param, results, is_percentage=is_pct))


def cmd_defaults(args: argparse.Namespace) -> None:
    """Print default parameters as YAML (or JSON)."""
    params = ScenarioParams()
    from housing.config import params_to_dict
    d = params_to_dict(params)

    try:
        import yaml
        print(yaml.dump(d, default_flow_style=False, sort_keys=False))
    except ImportError:
        import json
        print(json.dumps(d, indent=2))


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Australian housing expense model for net worth optimization",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""\
Examples:
  housing run                          # Run with defaults
  housing run config.yaml              # Run with custom config
  housing run config.yaml --detailed   # Year-by-year breakdown
  housing run config.yaml --csv        # CSV output for charting
  housing sensitivity --param buy.mortgage_rate --range 0.04,0.08,0.005
  housing defaults                     # Print default config
""",
    )

    subparsers = parser.add_subparsers(dest="command")

    # run
    run_parser = subparsers.add_parser("run", help="Run buy-vs-rent simulation")
    run_parser.add_argument("config", nargs="?", help="YAML/JSON config file")
    run_parser.add_argument("--detailed", action="store_true", help="Show year-by-year breakdown")
    run_parser.add_argument("--csv", action="store_true", help="Output as CSV")

    # sensitivity
    sens_parser = subparsers.add_parser("sensitivity", help="Parameter sensitivity analysis")
    sens_parser.add_argument("--config", help="Base config file")
    sens_parser.add_argument("--param", required=True, help="Parameter path (e.g., buy.mortgage_rate)")
    sens_parser.add_argument("--range", required=True, help="start,stop,step (e.g., 0.04,0.08,0.005)")

    # defaults
    subparsers.add_parser("defaults", help="Print default parameters")

    args = parser.parse_args()

    if args.command == "run":
        cmd_run(args)
    elif args.command == "sensitivity":
        cmd_sensitivity(args)
    elif args.command == "defaults":
        cmd_defaults(args)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()

# Housing Model

Australian buy-vs-rent comparison tool with year-by-year net worth simulation,
state-specific tax calculations, Monte Carlo probabilistic analysis, and an
interactive Streamlit dashboard.

## Getting Started

### Prerequisites

- Python 3.11+
- [uv](https://docs.astral.sh/uv/) (recommended) or pip

### Install

```bash
# Clone the repo
git clone https://github.com/PaperArmada/housing-model.git
cd housing-model

# Install with all extras (dashboard + dev)
uv pip install -e ".[dev,dashboard]"

# Or with plain pip
pip install -e ".[dev,dashboard]"
```

### Run the Dashboard

```bash
streamlit run dashboard/app.py
```

Open [http://localhost:8501](http://localhost:8501) in your browser. The sidebar
has preset configurations for Sydney, Melbourne, and Brisbane scenarios — select
one to get started, or customise any parameter.

### Run from the CLI

```bash
# Run with defaults (Sydney house)
housing run

# Run a preset config
housing run configs/melbourne_apartment.yaml

# Year-by-year breakdown
housing run --detailed

# Export to CSV
housing run --csv > output.csv

# Sensitivity analysis: sweep mortgage rate from 4% to 8%
housing sensitivity --param buy.mortgage_rate --range 0.04,0.08,0.005

# Print default parameters as YAML
housing defaults
```

### Run Tests

```bash
pytest
```

### Deploy to Streamlit Cloud

The repo is deploy-ready for [Streamlit Community Cloud](https://share.streamlit.io):

1. Push to GitHub
2. Go to [share.streamlit.io](https://share.streamlit.io) and sign in with GitHub
3. Click "New app" and select this repo, branch `main`, file `dashboard/app.py`
4. Deploy — dependencies are installed automatically from `requirements.txt`

## What It Does

The model simulates two parallel financial paths over a configurable time
horizon (default 30 years):

- **Buy scenario** — Purchase a property with a mortgage. Each year: property
  appreciates, mortgage is paid down, ongoing costs (council rates, insurance,
  maintenance, strata) are incurred, and any surplus cash is invested in
  equities.
- **Rent scenario** — Rent a comparable property. The full savings pool
  (deposit + stamp duty that would have been spent) is invested in equities
  from day one. Each year: rent and renters insurance are paid, and the
  remainder grows in the share portfolio.

At each year the model tracks nominal and real (inflation-adjusted) net worth
for both scenarios, accounting for Australian tax rules including income tax,
stamp duty, capital gains tax, first home owner grants, and franking credits.

## Dashboard

The Streamlit dashboard provides seven tabs:

| Tab | Description |
|---|---|
| **Net Worth** | Buy vs rent net worth over time (nominal or real) |
| **Housing Costs** | Annual and cumulative cost comparison |
| **Equity & Debt** | Mortgage paydown, property equity, and investment portfolio |
| **Monte Carlo** | Probabilistic fan charts with correlated economic shocks |
| **Sensitivity** | Interactive parameter sweeps (mortgage rate, price, rent, etc.) |
| **Data** | Year-by-year tables and CSV export |
| **Docs** | Rendered research and methodology documentation |

### Presets

Six preset configurations are included:

| Preset | Description |
|---|---|
| Sydney House | $1.55M middle-ring house, $750/wk rent |
| Sydney Apartment | $850K inner/middle-ring 2BR, $650/wk rent |
| Melbourne House | $1.05M middle-ring house, $550/wk rent |
| Melbourne Apartment | $600K inner/middle-ring 2BR, $500/wk rent |
| Brisbane First Home | First home buyer with new build, QLD concessions |
| Rate Drop Scenario | Variable rate schedule modelling future rate cuts |

## Project Structure

```
housing-model/
├── housing/              # Core simulation engine
│   ├── cli.py            # CLI entry point (run, sensitivity, defaults)
│   ├── config.py         # YAML/JSON config loading
│   ├── mc_params.py      # Monte Carlo configuration & covariance matrix
│   ├── model.py          # Year-by-year buy-vs-rent simulation
│   ├── monte_carlo.py    # Vectorized MC engine (5,000 parallel runs)
│   ├── output.py         # Text and CSV output formatting
│   ├── params.py         # Parameter dataclasses
│   ├── sensitivity.py    # Parameter sweep analysis
│   └── tax.py            # Income tax, stamp duty, CGT, FHOG
├── dashboard/            # Streamlit web dashboard
│   ├── app.py            # Main app layout and tabs
│   ├── charts.py         # Plotly charts (net worth, costs, equity)
│   ├── formatters.py     # DataFrame formatting helpers
│   ├── mc_charts.py      # Fan charts, P(buy wins), histograms
│   └── sidebar.py        # Sidebar controls and preset loader
├── configs/              # YAML preset configurations
├── docs/                 # Research and methodology documentation
│   ├── preset_research.md
│   └── mc_distributions.md
├── tests/                # pytest test suite
│   ├── test_model.py
│   ├── test_monte_carlo.py
│   └── test_tax.py
└── pyproject.toml
```

## Tax Modelling

The model implements current Australian tax rules:

- **Income tax** — 2025-26 brackets (0 / 16 / 30 / 37 / 45%) plus 2% Medicare
  levy
- **Stamp duty** — State-specific progressive calculators for NSW, VIC, and QLD
  with first home buyer exemptions and concessions
- **Capital gains tax** — 50% CGT discount for assets held over 12 months; PPOR
  fully exempt
- **First Home Owner Grant** — State-specific grants for new builds with price
  caps ($10K NSW/VIC, $30K QLD)
- **Franking credits** — Reduces effective tax on Australian equity dividends

## Monte Carlo Simulation

The MC engine generates year-by-year correlated shocks to five economic
variables using multivariate normal draws via Cholesky decomposition:

| Variable | Default Std | Description |
|---|---|---|
| Property appreciation | 10pp | Annual growth rate volatility |
| Investment return | 15pp | Equity market return volatility |
| Rent increase | 2pp | Rental growth volatility |
| Inflation | 1.5pp | CPI volatility |
| Mortgage rate | 1pp | Interest rate volatility (random walk) |

Variables are correlated (e.g., inflation and mortgage rates at 0.65, reflecting
RBA policy). The simulation runs 5,000 parallel trajectories using vectorized
NumPy operations and produces percentile fan charts (10th–90th) with the
probability that buying wins at each year.

Full methodology and calibration rationale are documented in
[docs/mc_distributions.md](docs/mc_distributions.md).

## Documentation

Detailed documentation is available in the `docs/` directory and rendered in the
dashboard's Docs tab:

- **[Preset Research](docs/preset_research.md)** — Data sources, parameter
  justifications, and verification audit for each preset against 2024-2025
  market data
- **[MC Distributions](docs/mc_distributions.md)** — Stochastic variable
  descriptions, correlation matrix explanations, calibration rationale, and
  known limitations

## Disclaimer

This tool is for **educational and informational purposes only**. It is not
financial advice. The model makes simplifying assumptions and uses estimated
parameters that may not reflect your actual situation. Always consult a
qualified financial adviser before making property or investment decisions.

## License

This project is licensed under the [GNU General Public License v3.0](LICENSE).

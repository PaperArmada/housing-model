# Housing Model — Monte Carlo Distribution Parameters

This document describes the stochastic variables, correlation structure, and
calibration rationale used in the Monte Carlo simulation module
(`housing/monte_carlo.py`).

## Overview

The Monte Carlo simulation generates **year-by-year correlated shocks** to five
economic variables, producing thousands of possible trajectories for the buy-vs-rent
comparison. This captures the range of likely outcomes rather than a single
deterministic path.

Key design choices:
- **Year-by-year randomness** — each year draws fresh shocks rather than one draw per
  simulation run
- **Correlated variables** — shocks are jointly drawn from a multivariate normal
  distribution via Cholesky decomposition
- **Clipped to bounds** — extreme draws are capped at realistic floors and ceilings
- **Default 5,000 runs** — balances statistical reliability with computation speed

## Stochastic Variables

### 1. Property Appreciation

| Attribute | Value |
|---|---|
| Default std | 0.10 (10 percentage points) |
| Floor | -0.20 (-20%) |
| Ceiling | +0.30 (+30%) |
| Shock type | Mean-reverting (shock around base rate each year) |

**Rationale:** Australian residential property annual growth has a long-run average
of 6.4-6.8% (CoreLogic 30-year data). The standard deviation of annual price changes
is estimated at 5-10% depending on city and methodology. We use 10% as property is
measured at city level (not national), and individual property outcomes vary more than
index-level data suggests.

The floor of -20% reflects the worst historical annual declines (Perth mining
downturn, Sydney/Melbourne 2018-19 correction of ~10-15%). The ceiling of +30% allows
for boom periods like 2021 COVID-era growth.

### 2. Investment Return (Equities)

| Attribute | Value |
|---|---|
| Default std | 0.15 (15 percentage points) |
| Floor | -0.40 (-40%) |
| Ceiling | +0.50 (+50%) |
| Shock type | Mean-reverting |

**Rationale:** The ASX 200 long-run annualised standard deviation is approximately
14.9% (1984-2021 average). Our default of 15% aligns with this historical figure.

The floor of -40% captures GFC-magnitude crashes (ASX 200 fell ~50.6% peak-to-trough
in 2008-09, though the worst single calendar year was smaller). The ceiling of +50%
allows for strong recovery years.

### 3. Rent Increase

| Attribute | Value |
|---|---|
| Default std | 0.02 (2 percentage points) |
| Floor | 0.00 (0%) |
| Ceiling | 0.15 (15%) |
| Shock type | Mean-reverting |

**Rationale:** CPI rents have historically been relatively stable year-to-year,
tracking close to general inflation. Annual rent CPI growth ranged from ~1% in low
periods to 8.5% at the 2023 peak. The standard deviation of annual rent growth is
approximately 2-3 percentage points.

The floor of 0% reflects that rents rarely decline in nominal terms (even during
COVID, national rents were roughly flat while individual cities diverged). The ceiling
of 15% is above historical peaks to allow for extreme scenarios.

### 4. Inflation (CPI)

| Attribute | Value |
|---|---|
| Default std | 0.015 (1.5 percentage points) |
| Floor | 0.00 (0%) |
| Ceiling | 0.12 (12%) |
| Shock type | Mean-reverting |

**Rationale:** Australian CPI has ranged from ~1% to ~8% in the post-1990
inflation-targeting era, with a target band of 2-3%. The standard deviation of annual
CPI changes is approximately 1-2 percentage points in this era. We use 1.5% as a
moderate estimate.

The floor of 0% reflects that deflation has not occurred in Australia in the modern
era (and the RBA would act aggressively to prevent it). The ceiling of 12% allows for
extreme scenarios like the stagflation of the 1970s-80s, though this would be well
outside the post-1990 experience.

### 5. Mortgage Rate

| Attribute | Value |
|---|---|
| Default std | 0.01 (1 percentage point) |
| Floor | 0.01 (1%) |
| Ceiling | 0.15 (15%) |
| Shock type | **Random walk** (shocks add to previous year's rate) |

**Rationale:** Mortgage rates follow a **random walk** rather than mean-reverting to
the base rate. This reflects how rate changes are persistent — a rate cut doesn't
instantly revert. The 1 percentage point annual standard deviation captures the
typical range of RBA rate movements (usually 0.25-0.50% per meeting, with 4-8
meetings per year).

The floor of 1% prevents unrealistically low rates (the historical low was ~2% in
2020-21). The ceiling of 15% allows for 1980s-era rate environments while keeping
values physically meaningful.

**Important:** Because mortgage rates follow a random walk, over a 30-year horizon
they can drift substantially from the starting value. This is intentional — it
captures the structural uncertainty in long-run interest rate levels.

## Correlation Matrix

|  | Property Appreciation | Investment Return | Rent Increase | Inflation | Mortgage Rate |
|---|---|---|---|---|---|
| **Property Appreciation** | 1.00 | 0.20 | 0.30 | 0.40 | -0.25 |
| **Investment Return** | 0.20 | 1.00 | 0.05 | -0.10 | -0.15 |
| **Rent Increase** | 0.30 | 0.05 | 1.00 | 0.60 | 0.30 |
| **Inflation** | 0.40 | -0.10 | 0.60 | 1.00 | 0.65 |
| **Mortgage Rate** | -0.25 | -0.15 | 0.30 | 0.65 | 1.00 |

### Correlation Explanations

**Strong correlations (|r| >= 0.5):**

- **Inflation <-> Mortgage Rate (0.65):** The RBA explicitly targets inflation by
  adjusting the cash rate. Higher inflation leads to rate hikes; lower inflation to
  cuts. This is the strongest structural relationship in the matrix, confirmed by
  decades of RBA policy. The correlation isn't higher because rate changes lag
  inflation and the RBA considers other factors (employment, financial stability).

- **Inflation <-> Rent Increase (0.60):** Rents are a major component of CPI
  (~6% weight) and are driven by similar demand-side forces. Landlords adjust rents
  partly in response to their own rising costs (which track CPI). The ABS notes that
  advertised rent changes lead CPI rent changes by approximately 3 quarters.

**Moderate correlations (0.2 <= |r| < 0.5):**

- **Property Appreciation <-> Inflation (0.40):** Property is widely considered an
  inflation hedge. Higher inflation erodes cash savings and pushes investors toward
  real assets. However, the relationship is dampened because high inflation also
  triggers rate hikes which depress property demand.

- **Property Appreciation <-> Rent Increase (0.30):** Both are driven by housing
  demand fundamentals (population growth, supply constraints). However, they can
  diverge — property prices are more sensitive to credit conditions while rents
  respond more to vacancy rates.

- **Rent Increase <-> Mortgage Rate (0.30):** Higher rates push would-be buyers into
  the rental market, increasing rental demand and rents. This is a demand-switching
  effect documented in Australian housing research.

- **Property Appreciation <-> Mortgage Rate (-0.25):** Higher rates reduce borrowing
  capacity and dampen property demand, depressing prices. This is one of the key
  transmission mechanisms of monetary policy. The magnitude is moderate because other
  factors (supply, immigration, sentiment) also drive prices.

- **Property Appreciation <-> Investment Return (0.20):** Broad economic correlation —
  both benefit from economic growth and suffer in recessions. However, property and
  equities are distinct asset classes with different drivers.

**Weak correlations (|r| < 0.2):**

- **Investment Return <-> Mortgage Rate (-0.15):** Higher rates increase discount
  rates for equities and raise the attractiveness of cash/bonds, putting downward
  pressure on equity valuations. The relationship is weak because equity earnings
  also respond to the economic conditions that prompt rate changes.

- **Investment Return <-> Inflation (-0.10):** Surprise inflation tends to hurt
  equities (via compressed margins and rising discount rates), but mild inflation
  can coexist with strong earnings. Near zero.

- **Investment Return <-> Rent Increase (0.05):** Essentially uncorrelated. Rents
  are driven by housing-specific factors, equities by corporate earnings and global
  capital flows.

## Methodology

### Cholesky Decomposition

The covariance matrix is constructed as:

```
Cov = Corr * outer(stds, stds)
```

where `stds` is the vector of standard deviations `[0.10, 0.15, 0.02, 0.015, 0.01]`
and `Corr` is the correlation matrix above.

The Cholesky decomposition `L = cholesky(Cov)` produces a lower-triangular matrix
such that `L @ L.T = Cov`. Correlated draws are then generated as:

```python
z = rng.standard_normal((N, 5))   # independent standard normals
shocks = z @ L.T                   # correlated shocks with correct covariance
```

### Clipping

After adding shocks to base rates, values are clipped to `[floor, ceiling]` bounds.
This prevents physically impossible values (negative inflation, negative mortgage
rates) and extreme outliers that would distort the simulation.

Clipping does slightly bias the distribution (truncating tails), but the bounds are
set wide enough that clipping occurs in less than ~1% of draws under normal
conditions.

### Vectorization

The simulation operates on `(N,)` arrays for all N runs simultaneously. The year loop
iterates T times (one per year), but within each year all N runs are computed in
parallel using NumPy vector operations.

Mortgage amortization uses the analytical 12-payment formula:

```
B_new = B * (1+r)^12 - PMT * ((1+r)^12 - 1) / r
```

rather than an inner loop over 12 months, since the monthly rate is constant within
each year.

## Calibration Rationale

### Where the Numbers Come From

| Parameter | Calibration Source | Confidence |
|---|---|---|
| Investment return std (15%) | ASX 200 historical std 14.9% (1984-2021) | **High** — directly observable from market data |
| Property appreciation std (10%) | Estimated from CoreLogic annual city-level price changes; academic studies cite 5-10% for Australian housing | **Medium** — depends on granularity (city vs suburb vs individual property) |
| Inflation std (1.5%) | RBA CPI data post-1990; range ~1-8%, std ~1-2pp | **Medium-High** — stable institutional environment |
| Rent increase std (2%) | ABS CPI rents component; range ~0-8.5%, std ~2-3pp | **Medium** — limited academic literature on this specific measure |
| Mortgage rate std (1%) | RBA cash rate changes; typical annual rate movement ~0.5-2pp | **Medium** — random walk assumption adds uncertainty |
| Inflation-mortgage correlation (0.65) | RBA's explicit inflation-targeting mandate since 1993 | **High** — structurally enforced by policy |
| Inflation-rent correlation (0.60) | Rents are CPI component; empirical co-movement well documented | **High** |
| Property-inflation correlation (0.40) | General inflation-hedge property; academic literature | **Medium** — varies by time period |
| Other correlations | Directional reasoning + approximate magnitudes from financial literature | **Low-Medium** — informed estimates, not regression outputs |

### What We Don't Have

- Precise regression-derived correlations from Australian data for all 10 pairs
- Formal time-varying correlation analysis (correlations change in crises)
- Sub-city-level volatility data (suburb-level would be higher than city-level)

## Known Limitations

1. **Normality assumption:** Real financial returns are fat-tailed (leptokurtic).
   Extreme events (GFC, COVID) are more likely than a normal distribution predicts.
   The clipping bounds partially address this but don't fully capture tail risk.

2. **Constant correlation:** The correlation matrix is fixed over the entire
   simulation. In reality, correlations tend to increase during crises ("correlation
   breakdown") — property and equities become more correlated when both are falling.

3. **No regime switching:** The model doesn't distinguish between expansion/recession
   regimes, which have different volatility and correlation structures.

4. **Mortgage rate random walk:** Over 30 years, a random walk with std=1% can produce
   rates that drift far from starting values. This may overstate long-run rate
   uncertainty — in practice, rates are somewhat mean-reverting toward a neutral rate.
   However, the neutral rate itself is uncertain (as demonstrated by the shift from
   ~7% in the 2000s to ~2% in the 2010s to ~4% in the 2020s).

5. **No autocorrelation in non-mortgage variables:** Property prices, equity returns,
   and rents show some momentum (positive autocorrelation) over 1-3 year horizons.
   The model treats each year as independent (conditional on the base rate). This may
   understate the probability of multi-year booms/busts.

6. **Single property vs index:** The model simulates property appreciation at an
   index level. Individual property outcomes have higher volatility than the city
   index due to property-specific factors.

7. **No negative rent growth:** The 0% floor on rent growth means the model doesn't
   allow nominal rent decreases, which can occur in specific markets (e.g., Perth
   2015-17, Melbourne inner-city during COVID).

---

## Verification Audit (February 2026)

Key calibration points checked against available sources:

| Parameter | Model Value | Market Evidence | Assessment |
|---|---|---|---|
| Investment return std | 15% | ASX 200 long-run std ~14.9% (1984-2021); decade avg ~14.3% | **Accurate** — directly matches historical data |
| Property appreciation std | 10% | Estimated 5-10% for city-level annual changes; academic literature cites similar range | **Reasonable** — at upper end of range, appropriate for individual-property-level modelling |
| Inflation std | 1.5% | Post-1990 CPI range ~1-8%; implied std ~1.5-2% | **Reasonable** |
| Rent increase std | 2% | CPI rents range ~0-8.5% (post-2020); longer-term range narrower | **Reasonable** — may be slightly low given recent volatility |
| Mortgage rate std | 1% | Typical annual rate movement 0.5-2pp (RBA moves in 0.25% increments, multiple times per year) | **Reasonable** |
| Inflation-mortgage correlation | 0.65 | Strong structural relationship via RBA inflation targeting; confirmed by historical co-movement | **Well-supported** |
| Inflation-rent correlation | 0.60 | Rents are CPI component; ABS documents strong linkage | **Well-supported** |
| Other correlations | Various | Directionally correct; magnitudes are informed estimates | **Reasonable but unverified** — would benefit from formal regression analysis |

### Recommendations

1. **Consider adding autocorrelation** for property appreciation (momentum effect) in
   a future version. A simple AR(1) model with coefficient ~0.3 would capture the
   tendency for property markets to trend over 2-3 year periods.

2. **Rent growth std** may be slightly low given the 2020-2025 experience. Consider
   increasing to 0.025 (2.5pp) to better capture the range of outcomes.

3. **Formal calibration**: The correlation matrix would benefit from being estimated
   directly from historical Australian data (ABS CPI, CoreLogic indices, RBA rates,
   ASX returns) rather than set from qualitative reasoning. This could be a future
   enhancement.

### Sources

- [Trading Economics — Australia Stock Price Volatility](https://tradingeconomics.com/australia/stock-price-volatility-wb-data.html)
- [FRED — Residential Property Prices for Australia](https://fred.stlouisfed.org/series/QAUN368BIS)
- [RBA — Historical Interest Rate Data](https://www.rba.gov.au/statistics/historical-data.html)
- [RBA — Measures of Consumer Price Inflation](https://www.rba.gov.au/inflation/measures-cpi.html)
- [ABS — Private Rent Inflation](https://www.abs.gov.au/articles/private-rent-inflation-capital-cities-vs-regions)
- [ABS — Consumer Price Index](https://www.abs.gov.au/statistics/economy/price-indexes-and-inflation/consumer-price-index-australia/latest-release)
- [Challenger — Inflation and Interest Rate Relationship](https://www.challenger.com.au/individual/learn/articles/Is-the-link-between-inflation-and-interest-rates-as-straightforward-as-it-seems)
- [RBA — Long-run Trends in Housing Price Growth (Bulletin 2015)](https://www.rba.gov.au/publications/bulletin/2015/sep/3.html)
- [Russell/ASX Long-Term Investing Report 2018](https://russellinvestments.com/-/media/files/au/insights/2018-russell-investmentsasx-long-term-investing-report.pdf)
- [DPN — Australian House Price Growth Over 30 Years](https://www.dpn.com.au/articles/house-price-growth-australia-over-30-years)

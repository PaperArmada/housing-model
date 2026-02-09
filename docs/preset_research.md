# Housing Model — Preset Parameter Research

This document records the rationale behind each preset configuration in the housing
model, the data sources consulted, and a verification audit against 2024-2025 market
data.

## Data Sources

| Source | Used For |
|---|---|
| CoreLogic / Cotality dwelling value indices | Median house & unit prices by city |
| Domain Rental Report (quarterly) | Median weekly rents by city & dwelling type |
| RBA Lenders' Interest Rates tables | Average mortgage rates |
| ABS Consumer Price Index | Inflation & rent CPI |
| ATO 2025-26 tax brackets | Income tax rates |
| CoreLogic long-run price indices | Historical appreciation rates |
| Vanguard / Russell-ASX Long-Term Investing Report | Equity return assumptions |
| DFFH Victoria Rental Report | Melbourne-specific rental data |

## Common Assumptions

These parameters are held constant across presets so the comparison is
apples-to-apples:

| Parameter | Value | Rationale |
|---|---|---|
| Mortgage rate | 6.2% | Avg advertised variable rate late 2024; actual new-loan rates ~5.5% by late 2025 after RBA cuts, but 6.2% reflects a blended/conservative figure |
| Mortgage term | 30 years | Standard Australian home loan term |
| Investment return | 7.0% nominal | ASX long-term total return ~9-10% less fees/drag; conservative |
| Dividend yield | 2.0% | Below ASX avg (~3-4%) to reflect modern index ETF mix with some international allocation |
| Inflation | 3.0% | RBA target band 2-3%; using top of band |
| Time horizon | 30 years | Full mortgage term |
| Selling agent commission | 2.0% | Mid-range for Australian metro markets (typical 1.5-2.5%) |
| Legal costs (selling) | $2,000 | Standard conveyancing estimate |

---

## Sydney House

**Config file:** `configs/default.yaml`

**Location proxy:** Middle-ring Sydney house (e.g., Epping, Ryde, Hurstville,
Canterbury-Bankstown).

### Property

| Parameter | Value | Rationale |
|---|---|---|
| Purchase price | $1,550,000 | Greater Sydney median house ~$1.49M (June 2025) to ~$1.60M (late 2025). $1.55M sits in the middle of this range. |
| Deposit | 20% ($310,000) | Standard to avoid LMI |
| State | NSW | |
| First home buyer | No | Typical scenario |
| New build | No | Existing dwelling |
| Appreciation | 5.0% p.a. | CoreLogic 30-yr national avg ~6.4-6.8%; Sydney historically outperforms but 5% is conservative for forward-looking estimate |

### Ongoing Costs

| Parameter | Value | Rationale |
|---|---|---|
| Council rates | 0.25% of value | Sydney councils typically $1,500-$4,000/yr on a ~$1.5M property; 0.25% ≈ $3,875 |
| Insurance | 0.15% of value | Building insurance ~$2,000-$3,000/yr for a house |
| Maintenance | 1.0% of value | Standard rule of thumb for houses |
| Water rates | $1,200/yr | Sydney Water typical residential bill |
| Strata | $0 | Freestanding house, no strata |

### Rent

| Parameter | Value | Rationale |
|---|---|---|
| Weekly rent | $750 | Domain Sept 2025: Sydney median house rent $780/wk. $750 is slightly below for a comparable middle-ring property. |
| Rent increase | 4.0% p.a. | Above CPI but below recent peaks (8.5% in 2023). Long-run ~3-5%. |
| Renters insurance | $300/yr | Standard contents policy |

### Financial Profile

| Parameter | Value | Rationale |
|---|---|---|
| Gross income | $180,000 | Above-average income needed to service a $1.24M loan (~$9.3k/month at 6.2%) |
| Existing savings | $350,000 | Covers 20% deposit ($310k) + stamp duty (~$67k) — tight but feasible |

---

## Sydney Apartment

**Config file:** `configs/sydney_apartment.yaml`

**Location proxy:** Inner/middle-ring 2BR apartment (e.g., Surry Hills, Marrickville,
Bondi Junction, Parramatta).

### Property

| Parameter | Value | Rationale |
|---|---|---|
| Purchase price | $850,000 | Sydney median unit price in the $850K-$950K range (2025). $850K targets middle-ring 2BR. |
| Deposit | 20% ($170,000) | |
| State | NSW | |
| Appreciation | 3.5% p.a. | Apartments historically appreciate slower than houses in Sydney |

### Ongoing Costs

| Parameter | Value | Rationale |
|---|---|---|
| Council rates | 0.2% of value | Lower assessed value means lower rates |
| Insurance | 0.1% of value | Building covered by strata; this is unit-specific top-up |
| Maintenance | 0.5% of value | Lower for apartments (exterior maintained by strata) |
| Water rates | $800/yr | Lower usage for apartment |
| Strata | $5,500/yr | Typical for mid-rise apartment in Sydney inner/middle ring |

### Rent

| Parameter | Value | Rationale |
|---|---|---|
| Weekly rent | $650 | Sydney 2BR apartment rents broadly $550-$750 depending on area |
| Rent increase | 4.0% p.a. | Same as house scenario |
| Renters insurance | $300/yr | |

### Financial Profile

| Parameter | Value | Rationale |
|---|---|---|
| Gross income | $160,000 | Lower loan amount ($680k) means lower income requirement |
| Existing savings | $220,000 | Covers deposit ($170k) + stamp duty (~$33k) |

---

## Melbourne House

**Config file:** `configs/melbourne_house.yaml`

**Location proxy:** Middle-ring Melbourne house (e.g., Reservoir, Coburg, Box Hill,
Preston, Bentleigh).

### Property

| Parameter | Value | Rationale |
|---|---|---|
| Purchase price | $1,050,000 | Greater Melbourne median house $974K-$989K (Oct 2025). $1.05M for middle-ring with good transport. |
| Deposit | 20% ($210,000) | |
| State | VIC | |
| Appreciation | 4.5% p.a. | Melbourne has underperformed Sydney recently (14.9% over 5 years vs 35%); 4.5% is a moderate forward estimate |

### Ongoing Costs

| Parameter | Value | Rationale |
|---|---|---|
| Council rates | 0.25% of value | Similar to Sydney; VIC councils comparable |
| Insurance | 0.15% of value | |
| Maintenance | 1.0% of value | Standard for houses |
| Water rates | $1,100/yr | Melbourne Water typical bill |
| Strata | $0 | Freestanding house |

### Rent

| Parameter | Value | Rationale |
|---|---|---|
| Weekly rent | $550 | DFFH Vic: Melbourne median house rent $570-$580 (2025); Domain: $580. $550 for a comparable middle-ring property. |
| Rent increase | 4.0% p.a. | Melbourne rent growth slowed to ~2% in early 2025 but historically higher; 4% is forward-looking |
| Renters insurance | $300/yr | |

### Financial Profile

| Parameter | Value | Rationale |
|---|---|---|
| Gross income | $160,000 | Lower loan ($840k) than Sydney house |
| Existing savings | $250,000 | Covers deposit ($210k) + VIC stamp duty (~$55k) — tight |

---

## Melbourne Apartment

**Config file:** `configs/melbourne_apartment.yaml`

**Location proxy:** Inner/middle-ring 2BR apartment (e.g., Richmond, Brunswick,
Footscray, South Yarra).

### Property

| Parameter | Value | Rationale |
|---|---|---|
| Purchase price | $600,000 | Melbourne median unit $636K-$639K (Oct 2025). $600K targets accessible end of inner/middle ring. |
| Deposit | 20% ($120,000) | |
| State | VIC | |
| Appreciation | 3.0% p.a. | Melbourne apartments have seen the weakest growth among major metro segments |

### Ongoing Costs

| Parameter | Value | Rationale |
|---|---|---|
| Council rates | 0.2% of value | |
| Insurance | 0.1% of value | |
| Maintenance | 0.5% of value | Strata covers common areas |
| Water rates | $750/yr | |
| Strata | $4,500/yr | Slightly lower than Sydney equivalent |

### Rent

| Parameter | Value | Rationale |
|---|---|---|
| Weekly rent | $500 | Melbourne 2BR unit rents ~$450-$550 |
| Rent increase | 4.5% p.a. | Melbourne unit rents growing faster than house rents (1.7% units vs 0.7% houses in 2025); mean-reversion expected |
| Renters insurance | $300/yr | |

### Financial Profile

| Parameter | Value | Rationale |
|---|---|---|
| Gross income | $140,000 | Lower entry point |
| Existing savings | $160,000 | Covers deposit ($120k) + VIC stamp duty (~$22k) |

---

## Brisbane First Home

**Config file:** `configs/brisbane_first_home.yaml`

**Location proxy:** Brisbane house suitable for a first home buyer (e.g., outer suburbs,
Ipswich corridor, Moreton Bay).

### Property

| Parameter | Value | Rationale |
|---|---|---|
| Purchase price | $600,000 | Below the $700,000 QLD first home buyer stamp duty exemption cap for existing properties |
| Deposit | 10% ($60,000) | Common for FHBs — lower deposit to get into market sooner |
| State | QLD | |
| First home buyer | Yes | Enables QLD stamp duty exemption |
| New build | No | Existing dwelling |
| Appreciation | 5.0% p.a. | Brisbane has outperformed recently; 5% is moderate for forward-looking |
| LMI | $8,000 | ~1.3% of $540k loan at 90% LVR — typical for 10% deposit |

### Ongoing Costs

Uses model defaults (council 0.3%, insurance 0.2%, maintenance 1.0%, water $1,200, no strata).

### Rent

| Parameter | Value | Rationale |
|---|---|---|
| Weekly rent | $500 | Brisbane median house rent ~$550-600 (2025); $500 targets affordable outer-ring |
| Rent increase | 4.0% p.a. | Consistent with other presets |
| Renters insurance | $300/yr | Default |

### Financial Profile

| Parameter | Value | Rationale |
|---|---|---|
| Gross income | $120,000 | Moderate income — serviceable for $540k loan (~$3.9k/month at 6.2%) |
| Existing savings | $100,000 | Covers deposit ($60k) + LMI ($8k), with ~$32k buffer for stamp duty (exempt as FHB) and costs |

### Notes

This preset demonstrates the QLD first home buyer stamp duty exemption (fully exempt
below $700k for existing properties). LMI is explicitly set at $8,000 rather than
relying on auto-calculation, matching typical quotes for 90% LVR at this price point.

---

## Rate Drop Scenario

**Config file:** `configs/rate_drop_scenario.yaml`

**Purpose:** Models a falling interest rate environment — rates start at 6.5% and
progressively drop to 4.8% over 8 years. Useful for stress-testing how rate cuts
affect the buy-vs-rent outcome.

### Rate Schedule

| Period | Rate | Rationale |
|---|---|---|
| Years 1-2 | 6.5% | Starting rate — current market level |
| Years 3-4 | 5.8% | First easing cycle — 70bp cut |
| Years 5-7 | 5.2% | Continued easing |
| Year 8+ | 4.8% | Terminal rate — close to estimated neutral |

### Other Parameters

Base Sydney scenario ($800k purchase, 20% deposit, $650/wk rent, $180k income, $200k
savings). All non-rate parameters match the standard assumptions so the rate schedule
effect can be isolated.

### Notes

Compare this directly with the Rate Rise Scenario and a flat-rate Sydney scenario to
see how rate trajectory affects the crossover year and terminal net worth difference.

---

## Rate Rise Scenario

**Config file:** `configs/rate_rise_scenario.yaml`

**Purpose:** Models a rising interest rate environment — rates start at 5.5% and
progressively rise to 7.5% over 8 years. The mirror image of the Rate Drop Scenario.

### Rate Schedule

| Period | Rate | Rationale |
|---|---|---|
| Years 1-2 | 5.5% | Starting rate — slightly below current market |
| Years 3-4 | 6.2% | First tightening cycle — 70bp increase |
| Years 5-7 | 7.0% | Continued tightening |
| Year 8+ | 7.5% | Terminal rate — elevated rate environment |

### Other Parameters

Identical base scenario to the Rate Drop preset ($800k purchase, 20% deposit, $650/wk
rent, $180k income, $200k savings) so the two are directly comparable.

### Notes

Rising rates increase mortgage costs and typically suppress property appreciation, but
the model holds appreciation constant. In the Monte Carlo simulation, the negative
correlation between mortgage rates and property appreciation (-0.25) captures this
relationship stochastically.

---

## Default Preset

The Default preset is not a YAML config file — it is the set of initial widget values
shown when no preset is loaded. These are defined in `dashboard/sidebar.py:_DEFAULTS`.

**Purpose:** Provide a reasonable starting point for an average American budget, since
the model's tax calculations and stamp duty are Australian-specific but the financial
concepts are universal.

| Parameter | Value | Rationale |
|---|---|---|
| Purchase price | $450,000 | US median home price ~$420k (2025), rounded up |
| Deposit | 20% | Standard to avoid PMI (US equivalent of LMI) |
| State | NSW | Model uses Australian tax/stamp duty calculations |
| Appreciation | 4.0% p.a. | US long-term average ~3-5% |
| Mortgage rate | 6.5% | US 30-year fixed rates ~6-7% (2025) |
| Mortgage term | 30 years | Standard US mortgage |
| Council rates | 0.25% | Proxy for US property tax (actual US rates 1-2% but model calculates differently) |
| Insurance | 0.15% | |
| Maintenance | 1.0% | Standard rule of thumb |
| Water | $600/yr | US average ~$500-700/yr |
| Agent commission | 2.5% | US typical 2.5-3% |
| Legal costs | $3,000 | US closing costs higher than Australian |
| Weekly rent | $450 | ~$1,950/month, US median ~$1,800-2,000 |
| Rent increase | 3.5% p.a. | US average ~3-4% |
| Renters insurance | $200/yr | US renters insurance ~$150-250 |
| Investment return | 7.0% | S&P 500 long-term similar to ASX |
| Dividend yield | 2.0% | |
| Franking | 0.0% | No franking credits in US tax system |
| Gross income | $75,000 | US median household income |
| Inflation | 3.0% | |
| Time horizon | 40 years | Auto-set to mortgage term + 10 |
| Existing savings | $100,000 | Reasonable US savings for first home |

---

## Cross-Preset Consistency

All presets share the same:
- **Mortgage rate** (6.2%) — so differences in outcomes reflect property fundamentals,
  not financing assumptions
- **Investment return** (7%) and **dividend yield** (2%) — same opportunity cost of
  capital
- **Inflation** (3%) — same real-value baseline
- **Time horizon** (30 years) — full mortgage lifecycle

What varies between presets:
- **Purchase price** and **weekly rent** — reflect actual market prices in each segment
- **Appreciation rate** — reflects historical performance differences (houses > apartments, Sydney > Melbourne)
- **Ongoing costs** — houses have higher maintenance but no strata; apartments have lower maintenance but significant strata
- **Financial profile** — income and savings scaled to what's required to service each loan

## Known Limitations

1. **LMI auto-estimated, not quoted** — the dashboard auto-calculates LMI from a
   published rate table when deposit < 20%. Actual premiums vary by insurer and lender.
   See the [LMI Estimation](lmi_estimation.md) doc for details.
2. **Single-rate mortgage** — actual rates vary by lender, LVR, and loan features.
   The Rate Drop and Rate Rise presets demonstrate variable rate schedules.
3. **Location averaging** — prices represent a broad middle-ring proxy, not any
   specific suburb.
4. **Static rent/appreciation** — in reality these vary year-to-year (captured by MC
   simulation).
5. **No renovation/improvement costs** for houses.
6. **Franking rate set to 0%** — conservative; actual ASX dividend franking ~60%.

---

## Verification Audit (February 2026)

Key data points checked against current sources:

| Parameter | Preset Value | Market Data (Source) | Assessment |
|---|---|---|---|
| Sydney median house price | $1,550,000 | $1.49M (June 2025) – $1.60M (late 2025), CoreLogic | **OK** — within range |
| Melbourne median house price | $1,050,000 | $974K–$989K (Oct 2025), CoreLogic | **Slightly high** — preset targets middle-ring suburbs above median |
| Sydney median unit price | $850,000 | ~$900K+ (Cotality combined), varies by source | **OK** — conservative end |
| Melbourne median unit price | $600,000 | $636K–$639K (Oct 2025), CoreLogic | **OK** — slightly below median |
| Mortgage rate | 6.2% | Avg new OO variable rate 5.49-5.51% (Sept 2025); RBA rate hike Feb 2026 to 3.85% | **High** — actual new-loan rates ~5.5%. Consider reducing to 5.8% or adding note. |
| Sydney median house rent | $750/wk | $780/wk (Domain Sept 2025); $750-$775 (March 2025) | **OK** — slightly below latest but reasonable |
| Melbourne median house rent | $550/wk | $570-$580/wk (DFFH/Domain 2025) | **OK** — slightly below but reasonable for middle-ring |
| Investment return | 7.0% | ASX 10-yr total return ~9-10%; after fees/international dilution ~7% reasonable | **OK** |
| Property appreciation (Sydney) | 5.0% | 30-yr national avg 6.4-6.8%; Sydney higher historically | **OK** — conservative |
| Property appreciation (Melbourne) | 4.5% | Melbourne 5-yr growth 14.9% (~2.8% p.a.) but longer-term higher | **OK** — optimistic vs recent but reasonable long-run |

### Recommendations

1. **Mortgage rate**: Consider reducing from 6.2% to ~5.8% given actual new-loan
   rates are ~5.5% (though the Feb 2026 RBA hike may push these up again). The rate
   drop scenario preset already models future cuts.
2. **Melbourne apartment appreciation (3.0%)**: This is realistic given recent
   underperformance but may be pessimistic over a 30-year horizon.
3. **Franking rate**: The 0% default understates the tax benefit of Australian equity
   dividends. Consider 50-60% as default for presets with ASX-heavy portfolios.

### Sources

- [CoreLogic / PropertyUpdate — Latest Median Property Prices](https://propertyupdate.com.au/the-latest-median-property-prices-in-australias-major-cities/)
- [Domain September 2025 Rental Report](https://www.timeout.com/sydney/news/revealed-how-much-it-costs-to-rent-in-sydney-in-2025-103025)
- [DFFH Victoria Rental Report](https://www.dffh.vic.gov.au/publications/rental-report)
- [RBA Lenders' Interest Rates](https://www.rba.gov.au/statistics/interest-rates/)
- [Mozo Home Loan Statistics](https://mozo.com.au/home-loan-statistics)
- [Your Mortgage — Median Prices February 2026](https://www.yourmortgage.com.au/compare-home-loans/median-house-prices-around-australia)
- [OpenAgent — Sydney Property Market](https://www.openagent.com.au/suburb-profiles/sydney-property-market)
- [OpenAgent — Melbourne Property Market](https://www.openagent.com.au/suburb-profiles/melbourne-property-market)

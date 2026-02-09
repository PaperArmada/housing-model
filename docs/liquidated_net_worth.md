# Housing Model — Liquidated Net Worth Calculations

This document explains the "Liquidated" view in the Net Worth tab — what you'd
actually walk away with if you sold the property or liquidated the investment portfolio
at any point during the simulation.

## Paper vs Liquidated Net Worth

The model tracks two different measures of net worth:

### Paper Net Worth (default view)

```
Buy NW  = Property Value - Mortgage Balance + Invested Surplus
Rent NW = Investment Portfolio Value
```

This is the "mark-to-market" value — what your assets are worth on paper. It does not
account for the costs of actually converting those assets to cash.

### Liquidated Net Worth

```
Buy NW  = Sale Proceeds - Mortgage Payoff + Investments - Investment CGT
Rent NW = Investments - Investment CGT
```

This is the "walk-away-with" value — what you'd have in your bank account after selling
everything, paying all fees, and settling all tax obligations.

## Buy Scenario — Liquidation Steps

### 1. Sell the Property

```
Sale Proceeds = Property Value × (1 - Agent Commission %) - Legal Costs
```

- **Agent commission**: A percentage of the sale price (default 2%), deducted at
  settlement
- **Legal costs**: Conveyancing and settlement fees, **inflated with CPI** to the sale
  year. A $2,000 cost at year 0 becomes ~$4,850 at year 30 with 3% inflation. This
  matches how other fixed costs (water rates, strata, renters insurance) are treated
  in the simulation.

### 2. Pay Off the Mortgage (Full Recourse)

```
Property Equity After Sale = Sale Proceeds - Mortgage Balance
```

In Australia, mortgages are **full recourse** — if the property sells for less than
the outstanding mortgage, the borrower still owes the difference. The model does not
clip negative equity to zero. If the property is underwater, the shortfall is deducted
from the buyer's investments.

This matters in scenarios with:
- Small deposits (5-10%)
- Negative property appreciation
- Early liquidation (before significant principal paydown)

### 3. Liquidate Invested Surplus

The buyer may have surplus savings invested (e.g., if rent scenario costs exceed buy
scenario costs in some years, or if initial savings exceeded upfront purchase costs).

```
Capital Gains = max(Investment Value - Cost Base, 0)
CGT = Capital Gains × 50% × Marginal Tax Rate
Buy Investments After Tax = Investment Value - CGT
```

The 50% CGT discount applies because investments are assumed held for more than
12 months.

### 4. Total Liquidated Buy Net Worth

```
Buy Liquidated NW = Property Equity After Sale + Buy Investments After Tax
```

### PPOR CGT Exemption

The property itself is **CGT-exempt** as a Principal Place of Residence (PPOR). No
capital gains tax is payable on the property sale, regardless of how much it has
appreciated. This is one of the most significant tax advantages of owner-occupied
property in Australia.

## Rent Scenario — Liquidation Steps

### 1. Liquidate Investment Portfolio

```
Capital Gains = max(Investment Value - Cost Base, 0)
CGT = Capital Gains × 50% × Marginal Tax Rate
Rent Liquidated NW = Investment Value - CGT
```

The cost base tracks:
- Initial savings invested at year 0
- Annual surplus contributions (when rent costs are less than buy costs)
- After-tax reinvested dividends (to avoid double taxation)

The 50% CGT discount applies for assets held over 12 months.

## Cost Base Tracking

Both scenarios track investment cost bases to calculate accurate capital gains:

- **Initial contributions**: Savings invested at year 0
- **Surplus contributions**: When one scenario is cheaper than the other, the
  difference is invested. These contributions are added to the cost base at face value.
- **Reinvested dividends**: Dividends are taxed annually. The after-tax amount is
  reinvested and added to the cost base (since the dividend income has already been
  taxed, it should not be taxed again at liquidation).

```
Cost Base += Annual Surplus Contribution + After-Tax Reinvested Dividends
```

## Real (Inflation-Adjusted) Values

Both paper and liquidated net worth can be viewed in real terms:

```
Real Value = Nominal Value / (1 + Inflation Rate) ^ Year
```

This answers: "What is this amount worth in today's purchasing power?"

## Crossover Year

The paper and liquidated views may show **different crossover years** (the year where
buying overtakes renting). The liquidated crossover is typically later because:

1. **Selling costs** are a fixed drag on the buy scenario (2-3% of property value)
2. **CGT on investments** affects both scenarios, but the rent scenario typically has
   larger investment gains (larger portfolio) so the drag is proportionally similar
3. In early years, selling costs dominate the difference

## Dashboard Integration

The Net Worth tab provides two toggles:

- **View**: Paper / Liquidated — switches between the two net worth measures
- **Values**: Nominal / Real — switches between nominal and inflation-adjusted

Both the main comparison chart and the difference bar chart update based on these
selections. The top-of-page summary metrics always show both views (Row 1 = paper,
Row 2 = liquidated real values).

## Known Limitations

1. **No mortgage break costs**: Breaking a fixed-rate mortgage early can incur
   significant fees. The model uses variable rates, so this is less relevant, but
   some fixed-rate scenarios (via rate schedules) would realistically include break
   costs.

2. **Single marginal tax rate**: CGT is calculated at the user's current marginal
   rate, which may not reflect their actual rate at the time of liquidation (income
   may change over 30 years).

3. **No transaction timing**: The model assumes instantaneous liquidation at year-end.
   In practice, property sales take weeks to months, and market conditions at the
   exact point of sale matter.

4. **50% CGT discount always applied**: The model assumes all investments qualify for
   the 12-month holding period discount. In reality, surplus contributions made during
   the current year would not yet qualify. The error is small since gains on
   current-year contributions are minimal.

5. **No stamp duty on reinvestment**: If the buyer sells and buys another property,
   they would incur stamp duty again. The model assumes a clean exit to cash.

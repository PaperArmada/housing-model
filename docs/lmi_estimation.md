# Housing Model — LMI Estimation

This document describes the Lenders Mortgage Insurance (LMI) auto-estimation feature,
including the rate table, calculation method, and limitations.

## What is LMI?

Lenders Mortgage Insurance protects the **lender** (not the borrower) against the risk
of the borrower defaulting on a home loan when the deposit is less than 20% of the
property value. Despite protecting the lender, the borrower pays the premium.

LMI is typically required when the Loan-to-Value Ratio (LVR) exceeds 80%.

## How the Model Estimates LMI

The dashboard auto-populates the LMI field whenever the deposit drops below 20%.
The estimate is based on a published rate table that varies by two factors:

1. **LVR band** — 1% increments from 80% to 95%
2. **Loan amount tier** — four tiers based on the loan size

### Formula

```
LVR = 1 - (Deposit % / 100)
Loan Amount = Purchase Price × LVR
LMI = Loan Amount × Rate(LVR, Loan Tier)
```

### Loan Amount Tiers

| Tier | Loan Amount | Typical Scenario |
|---|---|---|
| 0 | Up to $300,000 | Regional/affordable property |
| 1 | $300,001 - $500,000 | Entry-level metro apartment |
| 2 | $500,001 - $1,000,000 | Mid-range metro house/apartment |
| 3 | Over $1,000,000 | Premium metro property |

Higher loan amounts attract higher LMI rates (not just higher absolute premiums).

### Rate Table

The full rate table used in the model (`housing/lmi.py`):

| LVR Band | Tier 0 (<=300k) | Tier 1 (300-500k) | Tier 2 (500k-1M) | Tier 3 (>1M) |
|---|---|---|---|---|
| 80-81% | 0.50% | 0.64% | 0.90% | 0.99% |
| 81-82% | 0.50% | 0.67% | 0.94% | 1.04% |
| 82-83% | 0.55% | 0.71% | 0.99% | 1.10% |
| 83-84% | 0.73% | 0.90% | 1.26% | 1.40% |
| 84-85% | 0.78% | 0.98% | 1.37% | 1.52% |
| 85-86% | 0.92% | 1.21% | 1.69% | 1.88% |
| 86-87% | 0.98% | 1.27% | 1.78% | 1.97% |
| 87-88% | 1.12% | 1.36% | 1.90% | 2.11% |
| 88-89% | 1.18% | 1.42% | 1.99% | 2.20% |
| 89-90% | 1.27% | 1.68% | 2.35% | 2.60% |
| 90-91% | 1.97% | 2.58% | 3.61% | 4.00% |
| 91-92% | 1.97% | 2.58% | 3.61% | 4.00% |
| 92-93% | 2.21% | 2.92% | 4.09% | 4.53% |
| 93-94% | 2.21% | 2.92% | 4.09% | 4.53% |
| 94-95% | 2.43% | 3.21% | 4.49% | 4.98% |

**Source:** Perth Mortgage Specialist / Helia-style published schedules.

### Key Observations

- **Sharp jump at 90% LVR**: Rates roughly double when crossing from 89-90% to 90-91%.
  This reflects the significantly higher risk above 90% LVR.
- **Loan size matters**: A $900k loan at 90% LVR attracts a 2.35% rate ($21,150),
  while a $400k loan at the same LVR attracts 1.68% ($6,720).
- **LVR below 80% = $0**: No LMI is required when deposit is 20% or more.

### Example Calculations

| Purchase Price | Deposit | LVR | Loan Amount | LMI Rate | LMI Premium |
|---|---|---|---|---|---|
| $600,000 | 10% ($60k) | 90% | $540,000 | 2.35% | $12,690 |
| $800,000 | 15% ($120k) | 85% | $680,000 | 1.37% | $9,316 |
| $1,200,000 | 12% ($144k) | 88% | $1,056,000 | 2.11% | $22,282 |
| $450,000 | 5% ($22.5k) | 95% | $427,500 | 3.21% | $13,723 |

## Dashboard Behaviour

### Auto-Population

The LMI field in the Mortgage section of the sidebar auto-updates whenever:
- The **deposit percentage** changes (via the slider)
- The **purchase price** changes

When deposit >= 20%, LMI is automatically set to $0.
When deposit < 20%, LMI is populated with the estimate from the rate table.

A caption below the LMI field shows the estimate details:
> Estimated LMI: $12,690 (LVR 90%, $540,000 loan)

### Manual Override

The LMI field remains editable. Users can enter a specific quote from their lender.
However, the auto-estimate will overwrite any manual value when the deposit or purchase
price changes.

### Preset Loading

When loading a preset:
- If the preset has an explicit LMI value > 0, that value is used
- If the preset has deposit < 20% and LMI = 0, LMI is auto-calculated
- If deposit >= 20%, LMI is set to 0

## LMI in the Simulation

LMI is treated as an **upfront cost** added to the deposit and stamp duty:

```
Upfront Buy Costs = Deposit + Stamp Duty + LMI - FHOG
Starting Buy Investments = max(Existing Savings - Upfront Buy Costs, 0)
```

LMI increases the cash required to purchase and reduces the buyer's starting
investment pool. It does not affect the loan amount or mortgage repayments (LMI is
a one-off premium, not added to the loan in this model).

## Known Limitations

1. **Approximate rates**: Actual LMI premiums vary by insurer (Helia, QBE LMI),
   lender, property type, and borrower profile. The table provides a reasonable
   estimate but should not replace an actual quote.

2. **No LMI capitalisation**: In practice, many borrowers add LMI to the loan
   (capitalise it), which increases the loan amount and ongoing repayments. The model
   treats LMI as a cash payment from savings.

3. **No LMI waivers**: Some professions (doctors, lawyers, accountants) qualify for
   LMI waivers at certain lenders even with deposits below 20%. The model does not
   account for this.

4. **Stamp duty on LMI**: In some states, stamp duty is also payable on the LMI
   premium itself. The model does not include this additional cost.

5. **Fixed table**: The rate table is a point-in-time snapshot. LMI rates change
   periodically as insurers adjust their risk pricing.

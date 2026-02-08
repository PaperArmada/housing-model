"""Lenders Mortgage Insurance (LMI) estimation.

Based on published Australian LMI rate tables. Rates are approximate —
actual premiums vary by insurer (Helia, QBE) and lender.
"""

# Full rate table: LVR band (upper bound) → loan tier → rate as fraction of loan amount.
# Source: Perth Mortgage Specialist / Helia-style published schedules.
# Loan tiers: 0 = ≤$300k, 1 = $300k–$500k, 2 = $500k–$1M, 3 = >$1M.
_RATE_TABLE: list[tuple[float, tuple[float, float, float, float]]] = [
    (0.81, (0.0050, 0.0064, 0.00896, 0.00992)),
    (0.82, (0.0050, 0.0067, 0.00938, 0.01039)),
    (0.83, (0.0055, 0.0071, 0.00994, 0.01101)),
    (0.84, (0.0073, 0.0090, 0.01260, 0.01395)),
    (0.85, (0.0078, 0.0098, 0.01372, 0.01519)),
    (0.86, (0.0092, 0.0121, 0.01694, 0.01876)),
    (0.87, (0.0098, 0.0127, 0.01778, 0.01969)),
    (0.88, (0.0112, 0.0136, 0.01904, 0.02108)),
    (0.89, (0.0118, 0.0142, 0.01988, 0.02201)),
    (0.90, (0.0127, 0.0168, 0.02352, 0.02604)),
    (0.91, (0.0197, 0.0258, 0.03612, 0.03999)),
    (0.92, (0.0197, 0.0258, 0.03612, 0.03999)),
    (0.93, (0.0221, 0.0292, 0.04088, 0.04526)),
    (0.94, (0.0221, 0.0292, 0.04088, 0.04526)),
    (0.95, (0.0243, 0.0321, 0.04494, 0.04976)),
]


def _loan_tier(loan_amount: float) -> int:
    """Return the loan amount tier index (0–3)."""
    if loan_amount <= 300_000:
        return 0
    if loan_amount <= 500_000:
        return 1
    if loan_amount <= 1_000_000:
        return 2
    return 3


def estimate_lmi(loan_amount: float, lvr: float) -> float:
    """Estimate LMI premium in dollars.

    Parameters
    ----------
    loan_amount : float
        The loan amount in dollars.
    lvr : float
        Loan-to-Value Ratio as a fraction (e.g. 0.90 for 90%).

    Returns
    -------
    float
        Estimated LMI premium in dollars, rounded to nearest dollar.
        Returns 0 if LVR ≤ 80%.
    """
    if lvr <= 0.80:
        return 0.0

    tier = _loan_tier(loan_amount)

    # Find the matching LVR band
    for upper_bound, rates in _RATE_TABLE:
        if lvr <= upper_bound:
            return round(loan_amount * rates[tier])

    # Above 95% — use the highest band
    _, rates = _RATE_TABLE[-1]
    return round(loan_amount * rates[tier])

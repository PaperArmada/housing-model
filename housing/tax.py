"""Australian tax calculations: stamp duty, income tax, CGT."""


# ---------------------------------------------------------------------------
# Income tax brackets (2025-26)
# ---------------------------------------------------------------------------

INCOME_BRACKETS_2025 = [
    (18_200, 0.00),
    (45_000, 0.16),
    (135_000, 0.30),
    (190_000, 0.37),
    (float("inf"), 0.45),
]

MEDICARE_LEVY = 0.02


def income_tax(gross_income: float) -> float:
    """Calculate total income tax (excluding Medicare levy)."""
    tax = 0.0
    prev_threshold = 0
    for threshold, rate in INCOME_BRACKETS_2025:
        taxable_in_band = min(gross_income, threshold) - prev_threshold
        if taxable_in_band <= 0:
            break
        tax += taxable_in_band * rate
        prev_threshold = threshold
    return tax


def marginal_rate(gross_income: float) -> float:
    """Return the marginal tax rate (inc. Medicare levy) for a given income."""
    prev_threshold = 0
    rate = 0.0
    for threshold, r in INCOME_BRACKETS_2025:
        if gross_income <= threshold:
            rate = r
            break
        prev_threshold = threshold
        rate = r
    return rate + MEDICARE_LEVY


# ---------------------------------------------------------------------------
# Stamp duty calculators by state
# ---------------------------------------------------------------------------


def calc_nsw_stamp_duty(
    price: float, first_home_buyer: bool = False, new_build: bool = False
) -> float:
    """NSW stamp duty (transfer duty).

    First home buyers:
      - Existing property: exempt up to $800k, concessional $800k-$1M
      - New build: exempt up to $800k, concessional $800k-$1M
    """
    if first_home_buyer and price <= 800_000:
        return 0.0

    # Standard progressive brackets
    brackets = [
        (17_000, 0.0125),
        (36_000, 0.015),
        (97_000, 0.0175),
        (364_000, 0.035),
        (1_212_000, 0.045),
        (3_636_000, 0.055),
        (float("inf"), 0.065),
    ]
    duty = _progressive_duty(price, brackets)

    if first_home_buyer and price <= 1_000_000:
        # Concessional: linear phase-out between $800k and $1M
        discount = 1.0 - (price - 800_000) / 200_000
        duty *= 1 - discount

    return duty


def calc_vic_stamp_duty(
    price: float, first_home_buyer: bool = False, new_build: bool = False
) -> float:
    """VIC stamp duty (land transfer duty).

    First home buyers:
      - Exempt up to $600k
      - Concessional $600k-$750k
    """
    if first_home_buyer and price <= 600_000:
        return 0.0

    # VIC owner-occupier (PPR) rates
    brackets = [
        (25_000, 0.014),
        (130_000, 0.024),
        (440_000, 0.05),
        (960_000, 0.06),
    ]
    # VIC uses progressive below $960k, flat 5.5% of total above $960k
    if price <= 960_000:
        duty = _progressive_duty(price, brackets)
    else:
        duty = price * 0.055

    if first_home_buyer and price <= 750_000:
        discount = 1.0 - (price - 600_000) / 150_000
        duty *= 1 - discount

    return duty


def calc_qld_stamp_duty(
    price: float, first_home_buyer: bool = False, new_build: bool = False
) -> float:
    """QLD stamp duty (transfer duty).

    Owner-occupier (home concession) rates used by default.
    First home buyers:
      - Existing: exempt up to $700k, concessional $700k-$800k
      - New build: exempt up to $800k (no cap beyond that for FHB on new builds)
    """
    if first_home_buyer:
        exempt_cap = 800_000 if new_build else 700_000
        if price <= exempt_cap:
            return 0.0
        concession_cap = exempt_cap + 100_000
        if price <= concession_cap:
            full_duty = _qld_home_concession_duty(price)
            discount = 1.0 - (price - exempt_cap) / 100_000
            return full_duty * (1 - discount)

    return _qld_home_concession_duty(price)


def _qld_home_concession_duty(price: float) -> float:
    """QLD home concession (owner-occupier) rates."""
    brackets = [
        (75_000, 0.015),
        (540_000, 0.035),
        (1_000_000, 0.045),
        (float("inf"), 0.0575),
    ]
    return _progressive_duty(price, brackets)


def _progressive_duty(price: float, brackets: list[tuple[float, float]]) -> float:
    """Calculate duty using progressive (marginal) brackets."""
    duty = 0.0
    prev = 0.0
    for threshold, rate in brackets:
        band = min(price, threshold) - prev
        if band <= 0:
            break
        duty += band * rate
        prev = threshold
    return duty


# ---------------------------------------------------------------------------
# Stamp duty dispatcher
# ---------------------------------------------------------------------------

STAMP_DUTY_CALCULATORS = {
    "NSW": calc_nsw_stamp_duty,
    "VIC": calc_vic_stamp_duty,
    "QLD": calc_qld_stamp_duty,
}


def calc_stamp_duty(
    price: float,
    state: str = "NSW",
    first_home_buyer: bool = False,
    new_build: bool = False,
) -> float:
    """Calculate stamp duty for a given state."""
    calc = STAMP_DUTY_CALCULATORS.get(state.upper())
    if calc is None:
        raise ValueError(
            f"Unknown state '{state}'. Supported: {list(STAMP_DUTY_CALCULATORS.keys())}"
        )
    return calc(price, first_home_buyer=first_home_buyer, new_build=new_build)


# ---------------------------------------------------------------------------
# Capital gains tax
# ---------------------------------------------------------------------------


def calc_cgt(
    gains: float,
    marginal_tax_rate: float,
    held_over_12_months: bool = True,
    is_ppor: bool = False,
) -> float:
    """Calculate CGT payable.

    PPOR (primary place of residence) is fully exempt.
    50% discount applies for assets held >12 months.
    """
    if is_ppor or gains <= 0:
        return 0.0
    taxable = gains
    if held_over_12_months:
        taxable *= 0.50  # 50% CGT discount
    return taxable * marginal_tax_rate


# ---------------------------------------------------------------------------
# First Home Owner Grant
# ---------------------------------------------------------------------------

FHOG_AMOUNTS = {
    "NSW": 10_000,  # new homes only
    "VIC": 10_000,  # new homes only
    "QLD": 30_000,  # new homes only, up to $750k
}


def fhog(state: str = "NSW", new_build: bool = False, price: float = 0) -> float:
    """First Home Owner Grant amount (new builds only)."""
    if not new_build:
        return 0.0
    amount = FHOG_AMOUNTS.get(state.upper(), 0)
    # QLD has a price cap
    if state.upper() == "QLD" and price > 750_000:
        return 0.0
    return amount

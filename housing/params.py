"""Parameters for housing expense modeling."""

from dataclasses import dataclass, field

from housing.tax import calc_stamp_duty, marginal_rate


@dataclass
class BuyParams:
    """Parameters for buying a property."""

    purchase_price: float = 800_000
    deposit_pct: float = 0.20  # 20% deposit
    mortgage_rate: float = 0.062  # 6.2% p.a.
    mortgage_term_years: int = 30
    property_appreciation_rate: float = 0.05  # 5% p.a.
    stamp_duty_override: float | None = None  # set to skip calculation
    lmi: float = 0.0  # lenders mortgage insurance (if deposit < 20%)
    state: str = "NSW"
    first_home_buyer: bool = False
    new_build: bool = False

    # Variable rate schedule: list of (from_year, rate) tuples.
    # e.g. [(1, 0.062), (4, 0.055)] = 6.2% years 1-3, 5.5% from year 4.
    # If None, mortgage_rate is used for entire term.
    rate_schedule: list[tuple[int, float]] | None = None

    # Ongoing costs (annual, as % of property value)
    council_rates_pct: float = 0.003  # ~0.3% of value
    insurance_pct: float = 0.002  # ~0.2% of value
    maintenance_pct: float = 0.01  # ~1% of value
    water_rates_annual: float = 1_200
    strata_annual: float = 0  # 0 for houses, ~$3k-8k for apartments

    # Transaction costs for eventual sale
    selling_agent_pct: float = 0.02  # 2% agent commission
    selling_legal: float = 2_000

    @property
    def deposit(self) -> float:
        return self.purchase_price * self.deposit_pct

    @property
    def loan_amount(self) -> float:
        return self.purchase_price - self.deposit

    def get_stamp_duty(self) -> float:
        if self.stamp_duty_override is not None:
            return self.stamp_duty_override
        return calc_stamp_duty(
            self.purchase_price,
            state=self.state,
            first_home_buyer=self.first_home_buyer,
            new_build=self.new_build,
        )

    def rate_for_year(self, year: int) -> float:
        """Get the mortgage rate applicable for a given year."""
        if not self.rate_schedule:
            return self.mortgage_rate
        # Find the most recent rate change at or before this year
        applicable_rate = self.mortgage_rate
        for from_year, rate in sorted(self.rate_schedule):
            if from_year <= year:
                applicable_rate = rate
            else:
                break
        return applicable_rate


@dataclass
class RentParams:
    """Parameters for renting."""

    weekly_rent: float = 650  # $/week
    rent_increase_rate: float = 0.04  # 4% p.a.
    renters_insurance_annual: float = 300


@dataclass
class InvestmentParams:
    """Parameters for investing savings (the rent-vs-buy difference)."""

    return_rate: float = 0.07  # 7% p.a. nominal (equities index)
    dividend_yield: float = 0.02  # portion of return that's dividends (taxed annually)
    franking_rate: float = 0.0  # proportion of dividends that are franked (0-1)


@dataclass
class TaxParams:
    """Australian tax parameters."""

    gross_income: float = 180_000  # annual gross income

    @property
    def marginal_rate(self) -> float:
        return marginal_rate(self.gross_income)


@dataclass
class ScenarioParams:
    """Complete scenario parameters."""

    buy: BuyParams = field(default_factory=BuyParams)
    rent: RentParams = field(default_factory=RentParams)
    investment: InvestmentParams = field(default_factory=InvestmentParams)
    tax: TaxParams = field(default_factory=TaxParams)
    inflation_rate: float = 0.03  # for real vs nominal comparison
    time_horizon_years: int = 30
    existing_savings: float = 200_000  # total savings available upfront

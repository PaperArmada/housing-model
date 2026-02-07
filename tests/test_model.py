"""Tests for the core simulation model."""

import pytest
from housing.model import (
    monthly_repayment,
    mortgage_balance_after_year,
    simulate,
    net_worth_at_sale,
)
from housing.params import BuyParams, RentParams, ScenarioParams, TaxParams, InvestmentParams


class TestMonthlyRepayment:
    def test_known_value(self):
        # $640,000 loan at 6.2% over 30 years
        # Expected ~$3,920/month
        pmt = monthly_repayment(640_000, 0.062, 30)
        assert 3_800 < pmt < 4_100

    def test_zero_rate(self):
        pmt = monthly_repayment(360_000, 0.0, 30)
        assert pmt == pytest.approx(1_000, rel=1e-2)

    def test_higher_rate_means_higher_payment(self):
        low = monthly_repayment(500_000, 0.04, 30)
        high = monthly_repayment(500_000, 0.08, 30)
        assert high > low

    def test_shorter_term_means_higher_payment(self):
        long = monthly_repayment(500_000, 0.06, 30)
        short = monthly_repayment(500_000, 0.06, 15)
        assert short > long


class TestMortgageAmortization:
    def test_principal_plus_interest_equals_payments(self):
        balance = 640_000
        rate = 0.062
        pmt = monthly_repayment(balance, rate, 30)
        new_bal, principal, interest = mortgage_balance_after_year(balance, rate, pmt)
        assert principal + interest == pytest.approx(pmt * 12, rel=1e-4)
        assert new_bal == pytest.approx(balance - principal, rel=1e-4)

    def test_balance_decreases(self):
        balance = 640_000
        rate = 0.062
        pmt = monthly_repayment(balance, rate, 30)
        new_bal, _, _ = mortgage_balance_after_year(balance, rate, pmt)
        assert new_bal < balance

    def test_full_amortization(self):
        """After 30 years of payments, balance should be ~$0."""
        balance = 640_000
        rate = 0.062
        pmt = monthly_repayment(balance, rate, 30)
        for _ in range(30):
            balance, _, _ = mortgage_balance_after_year(balance, rate, pmt)
        assert balance == pytest.approx(0, abs=1.0)


class TestSimulation:
    def test_year_zero_snapshot(self):
        params = ScenarioParams()
        snapshots = simulate(params)
        s0 = snapshots[0]
        assert s0.year == 0
        assert s0.property_value == params.buy.purchase_price
        assert s0.mortgage_balance == params.buy.loan_amount

    def test_correct_number_of_snapshots(self):
        params = ScenarioParams(time_horizon_years=10)
        snapshots = simulate(params)
        assert len(snapshots) == 11  # year 0 through year 10

    def test_property_appreciates(self):
        params = ScenarioParams(time_horizon_years=5)
        snapshots = simulate(params)
        assert snapshots[-1].property_value > params.buy.purchase_price

    def test_mortgage_decreases(self):
        params = ScenarioParams(time_horizon_years=5)
        snapshots = simulate(params)
        assert snapshots[-1].mortgage_balance < params.buy.loan_amount

    def test_rent_investments_grow(self):
        params = ScenarioParams(time_horizon_years=5)
        snapshots = simulate(params)
        assert snapshots[-1].rent_investments > params.existing_savings

    def test_real_values_less_than_nominal(self):
        params = ScenarioParams(time_horizon_years=10)
        snapshots = simulate(params)
        s10 = snapshots[10]
        assert s10.buy_net_worth_real < s10.buy_net_worth
        assert s10.rent_net_worth_real < s10.rent_net_worth

    def test_cost_base_tracked(self):
        """Cost base should grow as surplus and reinvested dividends accumulate."""
        params = ScenarioParams(time_horizon_years=10)
        snapshots = simulate(params)
        # Rent contributions should be >= initial savings (surplus + reinvested dividends)
        assert snapshots[-1].rent_contributions >= params.existing_savings

    def test_cost_base_includes_reinvested_dividends(self):
        """Cost base must include reinvested after-tax dividends to avoid double-taxation."""
        params = ScenarioParams(time_horizon_years=10)
        snapshots = simulate(params)
        # With dividends being reinvested, contributions should grow beyond
        # just the initial savings + surplus (dividends add to cost base each year)
        # Using zero dividend yield as baseline: no reinvested dividends
        no_div = ScenarioParams(
            time_horizon_years=10,
            investment=InvestmentParams(return_rate=0.07, dividend_yield=0.0),
        )
        no_div_snaps = simulate(no_div)
        # With dividends, cost base should be higher (reinvested dividends tracked)
        assert snapshots[-1].rent_contributions > no_div_snaps[-1].rent_contributions

    def test_buy_cheaper_than_rent_initially(self):
        """With default params, rent scenario starts richer (no deposit spent)."""
        params = ScenarioParams()
        snapshots = simulate(params)
        assert snapshots[0].rent_net_worth > snapshots[0].buy_net_worth

    def test_variable_rates(self):
        """Rate schedule should affect mortgage payments."""
        fixed = ScenarioParams(
            buy=BuyParams(mortgage_rate=0.06),
            time_horizon_years=10,
        )
        variable = ScenarioParams(
            buy=BuyParams(
                mortgage_rate=0.06,
                rate_schedule=[(1, 0.06), (5, 0.04)],
            ),
            time_horizon_years=10,
        )
        fixed_snaps = simulate(fixed)
        var_snaps = simulate(variable)
        # With rates dropping at year 5, buyer should end up better off
        assert var_snaps[-1].buy_net_worth > fixed_snaps[-1].buy_net_worth

    def test_fhog_applied_for_new_build_fhb(self):
        """First home buyers purchasing new builds should receive the FHOG."""
        no_grant = ScenarioParams(
            buy=BuyParams(
                state="QLD", first_home_buyer=True, new_build=False,
                purchase_price=600_000,
            ),
            time_horizon_years=5,
        )
        with_grant = ScenarioParams(
            buy=BuyParams(
                state="QLD", first_home_buyer=True, new_build=True,
                purchase_price=600_000,
            ),
            time_horizon_years=5,
        )
        no_grant_snaps = simulate(no_grant)
        with_grant_snaps = simulate(with_grant)
        # QLD FHOG is $30k for new builds — buyer starts with more investments
        assert with_grant_snaps[0].buy_investments > no_grant_snaps[0].buy_investments

    def test_fhog_not_applied_for_non_fhb(self):
        """Non-first-home-buyers should not receive FHOG even for new builds."""
        params = ScenarioParams(
            buy=BuyParams(
                state="QLD", first_home_buyer=False, new_build=True,
                purchase_price=600_000,
            ),
            time_horizon_years=5,
        )
        fhb_params = ScenarioParams(
            buy=BuyParams(
                state="QLD", first_home_buyer=True, new_build=True,
                purchase_price=600_000,
            ),
            time_horizon_years=5,
        )
        non_fhb = simulate(params)
        fhb = simulate(fhb_params)
        # FHB gets stamp duty exemption + FHOG, so much better starting position
        assert fhb[0].buy_investments > non_fhb[0].buy_investments

    def test_franking_credits_boost_investments(self):
        """Franking credits should reduce dividend tax and boost portfolio growth."""
        no_franking = ScenarioParams(
            time_horizon_years=10,
            investment=InvestmentParams(franking_rate=0.0),
        )
        with_franking = ScenarioParams(
            time_horizon_years=10,
            investment=InvestmentParams(franking_rate=1.0),
        )
        no_frank_snaps = simulate(no_franking)
        frank_snaps = simulate(with_franking)
        # With franking, investments grow faster (lower tax drag)
        assert frank_snaps[-1].rent_investments > no_frank_snaps[-1].rent_investments


class TestNetWorthAtSale:
    def test_buy_ppor_no_cgt(self):
        params = ScenarioParams(time_horizon_years=10)
        snapshots = simulate(params)
        result = net_worth_at_sale(snapshots[-1], params)
        # Buy net worth should be positive
        assert result["buy_net_worth_after_sale"] > 0

    def test_rent_pays_cgt(self):
        params = ScenarioParams(time_horizon_years=10)
        snapshots = simulate(params)
        result = net_worth_at_sale(snapshots[-1], params)
        # After-tax should be less than pre-tax
        assert result["rent_net_worth_after_tax"] < snapshots[-1].rent_investments

    def test_real_values_included(self):
        params = ScenarioParams(time_horizon_years=10)
        snapshots = simulate(params)
        result = net_worth_at_sale(snapshots[-1], params)
        assert result["buy_net_worth_after_sale_real"] < result["buy_net_worth_after_sale"]

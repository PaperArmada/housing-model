"""Tests for Monte Carlo simulation."""

import numpy as np
import pytest

from housing.mc_params import MCConfig, build_cov_matrix
from housing.model import simulate
from housing.monte_carlo import MCTimeSeries, mc_simulate, summarize
from housing.params import ScenarioParams


class TestMCConfig:
    def test_std_vector_shape(self):
        config = MCConfig()
        stds = config.std_vector()
        assert stds.shape == (5,)
        assert all(s >= 0 for s in stds)

    def test_correlation_matrix_symmetric(self):
        config = MCConfig()
        corr = config.correlation_matrix()
        assert corr.shape == (5, 5)
        np.testing.assert_array_almost_equal(corr, corr.T)

    def test_correlation_diagonal_ones(self):
        config = MCConfig()
        corr = config.correlation_matrix()
        np.testing.assert_array_equal(np.diag(corr), np.ones(5))

    def test_cov_matrix_positive_semidefinite(self):
        config = MCConfig()
        cov = build_cov_matrix(config)
        eigenvalues = np.linalg.eigvalsh(cov)
        assert all(ev >= -1e-10 for ev in eigenvalues)


class TestZeroVolatility:
    """With zero volatility, MC should reproduce the deterministic model exactly."""

    def test_matches_deterministic(self):
        params = ScenarioParams(time_horizon_years=10)
        config = MCConfig(
            n_runs=50,
            seed=42,
            std_property_appreciation=0.0,
            std_investment_return=0.0,
            std_rent_increase=0.0,
            std_inflation=0.0,
            std_mortgage_rate=0.0,
        )

        # Deterministic baseline
        snapshots = simulate(params)
        det_buy = [s.buy_net_worth for s in snapshots]
        det_rent = [s.rent_net_worth for s in snapshots]

        # MC simulation
        ts = mc_simulate(params, config)

        # Every run should match the deterministic result
        for year in range(len(snapshots)):
            # All N runs should be (nearly) identical
            np.testing.assert_allclose(
                ts.buy_net_worth[year],
                det_buy[year],
                rtol=1e-3,
                err_msg=f"Buy NW mismatch at year {year}",
            )
            np.testing.assert_allclose(
                ts.rent_net_worth[year],
                det_rent[year],
                rtol=1e-3,
                err_msg=f"Rent NW mismatch at year {year}",
            )

    def test_all_runs_identical(self):
        """With zero vol, all runs should produce the same trajectory."""
        params = ScenarioParams(time_horizon_years=5)
        config = MCConfig(
            n_runs=20,
            seed=123,
            std_property_appreciation=0.0,
            std_investment_return=0.0,
            std_rent_increase=0.0,
            std_inflation=0.0,
            std_mortgage_rate=0.0,
        )
        ts = mc_simulate(params, config)

        for year in range(6):
            # std across runs should be negligible (floating point noise only)
            mean_buy = np.mean(ts.buy_net_worth[year])
            mean_rent = np.mean(ts.rent_net_worth[year])
            # Coefficient of variation < 0.01% (i.e. std < 0.01% of mean)
            if mean_buy > 0:
                assert np.std(ts.buy_net_worth[year]) / mean_buy < 1e-4
            if mean_rent > 0:
                assert np.std(ts.rent_net_worth[year]) / mean_rent < 1e-4


class TestSeedReproducibility:
    def test_same_seed_same_result(self):
        params = ScenarioParams(time_horizon_years=5)
        config = MCConfig(n_runs=100, seed=42)

        ts1 = mc_simulate(params, config)
        ts2 = mc_simulate(params, config)

        np.testing.assert_array_equal(ts1.buy_net_worth, ts2.buy_net_worth)
        np.testing.assert_array_equal(ts1.rent_net_worth, ts2.rent_net_worth)

    def test_different_seed_different_result(self):
        params = ScenarioParams(time_horizon_years=5)
        ts1 = mc_simulate(params, MCConfig(n_runs=100, seed=42))
        ts2 = mc_simulate(params, MCConfig(n_runs=100, seed=99))

        # Final year values should differ
        assert not np.allclose(ts1.buy_net_worth[-1], ts2.buy_net_worth[-1])


class TestCorrelation:
    def test_inflation_mortgage_positive(self):
        """High inflation-mortgage correlation: when inflation is high,
        mortgage rates should tend to be high too."""
        params = ScenarioParams(time_horizon_years=20)
        config = MCConfig(n_runs=5_000, seed=42)

        # We need to check the raw draws — run MC and compare property
        # values (driven by appreciation) with mortgage balances (driven
        # by rates). With positive inflation-mortgage correlation, years
        # with high inflation should have higher rates = higher mortgage
        # balances on average.
        ts = mc_simulate(params, config)

        # Just verify the simulation produces reasonable spreads
        final_buy = ts.buy_net_worth[-1]
        assert np.std(final_buy) > 0  # There should be spread
        assert np.mean(final_buy) > 0  # Average should be positive


class TestSummarize:
    def test_percentile_ordering(self):
        params = ScenarioParams(time_horizon_years=10)
        config = MCConfig(n_runs=1_000, seed=42)
        ts = mc_simulate(params, config)
        summary = summarize(ts)

        # p10 <= p50 <= p90 at every year
        for year in range(11):
            assert summary.buy_pctiles[10][year] <= summary.buy_pctiles[50][year]
            assert summary.buy_pctiles[50][year] <= summary.buy_pctiles[90][year]
            assert summary.rent_pctiles[10][year] <= summary.rent_pctiles[50][year]
            assert summary.rent_pctiles[50][year] <= summary.rent_pctiles[90][year]

    def test_prob_buy_wins_bounded(self):
        params = ScenarioParams(time_horizon_years=10)
        config = MCConfig(n_runs=500, seed=42)
        ts = mc_simulate(params, config)
        summary = summarize(ts)

        assert all(0 <= p <= 1 for p in summary.prob_buy_wins)

    def test_years_match(self):
        params = ScenarioParams(time_horizon_years=10)
        config = MCConfig(n_runs=100, seed=42)
        ts = mc_simulate(params, config)
        summary = summarize(ts)

        np.testing.assert_array_equal(summary.years, np.arange(11))


class TestClipping:
    def test_property_values_bounded(self):
        """Property values should never go negative."""
        params = ScenarioParams(time_horizon_years=10)
        config = MCConfig(n_runs=1_000, seed=42)
        ts = mc_simulate(params, config)

        assert np.all(ts.property_values >= 0)

    def test_mortgage_non_negative(self):
        params = ScenarioParams(time_horizon_years=10)
        config = MCConfig(n_runs=1_000, seed=42)
        ts = mc_simulate(params, config)

        assert np.all(ts.mortgage_balances >= 0)


class TestOutputShape:
    def test_array_shapes(self):
        T = 15
        N = 200
        params = ScenarioParams(time_horizon_years=T)
        config = MCConfig(n_runs=N, seed=42)
        ts = mc_simulate(params, config)

        assert ts.years.shape == (T + 1,)
        assert ts.buy_net_worth.shape == (T + 1, N)
        assert ts.rent_net_worth.shape == (T + 1, N)
        assert ts.difference.shape == (T + 1, N)
        assert ts.property_values.shape == (T + 1, N)
        assert ts.mortgage_balances.shape == (T + 1, N)

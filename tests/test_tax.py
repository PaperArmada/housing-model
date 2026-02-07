"""Tests for Australian tax calculations."""

import pytest
from housing.tax import (
    calc_cgt,
    calc_nsw_stamp_duty,
    calc_qld_stamp_duty,
    calc_stamp_duty,
    calc_vic_stamp_duty,
    fhog,
    income_tax,
    marginal_rate,
)


class TestIncomeTax:
    def test_below_tax_free_threshold(self):
        assert income_tax(18_200) == 0.0

    def test_second_bracket(self):
        # $45,000: tax on $26,800 at 16%
        tax = income_tax(45_000)
        assert tax == pytest.approx(26_800 * 0.16, rel=1e-2)

    def test_top_bracket(self):
        # $250,000: should hit the 45% bracket
        tax = income_tax(250_000)
        assert tax > 0
        # Verify it's more than someone at $190k
        assert tax > income_tax(190_000)

    def test_zero_income(self):
        assert income_tax(0) == 0.0


class TestMarginalRate:
    def test_below_threshold(self):
        assert marginal_rate(15_000) == 0.0 + 0.02  # 0% + Medicare

    def test_common_salary(self):
        # $180,000 is in the 37% bracket ($135,001-$190,000)
        assert marginal_rate(180_000) == 0.37 + 0.02

    def test_high_income(self):
        assert marginal_rate(250_000) == 0.45 + 0.02


class TestNSWStampDuty:
    def test_800k_non_fhb(self):
        duty = calc_nsw_stamp_duty(800_000)
        # Should be around $31,490
        assert 30_000 < duty < 33_000

    def test_fhb_exempt(self):
        assert calc_nsw_stamp_duty(700_000, first_home_buyer=True) == 0.0
        assert calc_nsw_stamp_duty(800_000, first_home_buyer=True) == 0.0

    def test_fhb_concessional(self):
        # $900k: between $800k and $1M, should get partial discount
        duty_full = calc_nsw_stamp_duty(900_000)
        duty_fhb = calc_nsw_stamp_duty(900_000, first_home_buyer=True)
        assert duty_fhb < duty_full
        assert duty_fhb > 0

    def test_fhb_above_concession(self):
        # Above $1M: no FHB benefit
        duty_full = calc_nsw_stamp_duty(1_100_000)
        duty_fhb = calc_nsw_stamp_duty(1_100_000, first_home_buyer=True)
        assert duty_fhb == duty_full

    def test_low_price(self):
        duty = calc_nsw_stamp_duty(15_000)
        assert duty == pytest.approx(15_000 * 0.0125, rel=1e-2)


class TestVICStampDuty:
    def test_fhb_exempt(self):
        assert calc_vic_stamp_duty(500_000, first_home_buyer=True) == 0.0

    def test_above_960k_flat_rate(self):
        # Above $960k: flat 5.5%
        duty = calc_vic_stamp_duty(1_200_000)
        assert duty == pytest.approx(1_200_000 * 0.055, rel=1e-2)

    def test_ppr_brackets(self):
        # $300k: 25k*1.4% + 105k*2.4% + 170k*5% = 350 + 2520 + 8500 = $11,370
        assert calc_vic_stamp_duty(300_000) == pytest.approx(11_370, rel=1e-2)

    def test_above_440k_bracket(self):
        # $750k: 25k*1.4% + 105k*2.4% + 310k*5% + 310k*6%
        # = 350 + 2520 + 15500 + 18600 = $36,970
        assert calc_vic_stamp_duty(750_000) == pytest.approx(36_970, rel=1e-2)


class TestQLDStampDuty:
    def test_fhb_existing_exempt(self):
        assert calc_qld_stamp_duty(600_000, first_home_buyer=True) == 0.0
        assert calc_qld_stamp_duty(700_000, first_home_buyer=True) == 0.0

    def test_fhb_new_build_exempt(self):
        assert calc_qld_stamp_duty(750_000, first_home_buyer=True, new_build=True) == 0.0

    def test_non_fhb(self):
        duty = calc_qld_stamp_duty(600_000)
        assert duty > 0


class TestStampDutyDispatcher:
    def test_nsw(self):
        assert calc_stamp_duty(800_000, state="NSW") == calc_nsw_stamp_duty(800_000)

    def test_vic(self):
        assert calc_stamp_duty(800_000, state="VIC") == calc_vic_stamp_duty(800_000)

    def test_qld(self):
        assert calc_stamp_duty(800_000, state="QLD") == calc_qld_stamp_duty(800_000)

    def test_unknown_state(self):
        with pytest.raises(ValueError, match="Unknown state"):
            calc_stamp_duty(800_000, state="WA")

    def test_case_insensitive(self):
        assert calc_stamp_duty(800_000, state="nsw") == calc_nsw_stamp_duty(800_000)


class TestCGT:
    def test_ppor_exempt(self):
        assert calc_cgt(100_000, 0.39, is_ppor=True) == 0.0

    def test_no_gains(self):
        assert calc_cgt(0, 0.39) == 0.0
        assert calc_cgt(-50_000, 0.39) == 0.0

    def test_with_50pct_discount(self):
        # $100k gain, 39% marginal rate, held >12 months
        cgt = calc_cgt(100_000, 0.39, held_over_12_months=True)
        assert cgt == pytest.approx(100_000 * 0.50 * 0.39)

    def test_without_discount(self):
        cgt = calc_cgt(100_000, 0.39, held_over_12_months=False)
        assert cgt == pytest.approx(100_000 * 0.39)


class TestFHOG:
    def test_no_grant_for_existing(self):
        assert fhog("NSW", new_build=False) == 0

    def test_nsw_new_build(self):
        assert fhog("NSW", new_build=True) == 10_000

    def test_qld_new_build(self):
        assert fhog("QLD", new_build=True, price=600_000) == 30_000

    def test_qld_over_cap(self):
        assert fhog("QLD", new_build=True, price=800_000) == 0

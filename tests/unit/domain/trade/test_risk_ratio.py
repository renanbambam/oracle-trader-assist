"""Unit tests for RiskRatio value object."""

import pytest
from pydantic import ValidationError

from oracle.domain.trade.value_objects import RiskRatio


class TestFromLevels:
    def test_long_1r_2r(self):
        rr = RiskRatio.from_levels(entry=20.0, stop=19.0, target=22.0)
        assert rr.risk_points == 1.0
        assert rr.reward_points == 2.0
        assert rr.rr == 2.0

    def test_short_symmetric(self):
        rr = RiskRatio.from_levels(entry=20.0, stop=22.0, target=16.0)
        assert rr.risk_points == 2.0
        assert rr.reward_points == 4.0
        assert rr.rr == 2.0

    def test_rr_is_rounded_to_2_decimals(self):
        # risk=3, reward=7 → 7/3 = 2.333... → 2.33
        rr = RiskRatio.from_levels(entry=10.0, stop=7.0, target=17.0)
        assert rr.rr == 2.33

    def test_exact_2_5r(self):
        rr = RiskRatio.from_levels(entry=10.0, stop=9.0, target=12.5)
        assert rr.rr == 2.5

    def test_uses_abs_for_short_levels(self):
        # stop above entry for SHORT — abs handles direction
        rr = RiskRatio.from_levels(entry=50.0, stop=52.0, target=44.0)
        assert rr.risk_points == 2.0
        assert rr.reward_points == 6.0
        assert rr.rr == 3.0


class TestAcceptability:
    def test_exactly_2r_is_acceptable(self):
        rr = RiskRatio.from_levels(entry=20.0, stop=19.0, target=22.0)
        assert rr.is_acceptable is True

    def test_above_2r_is_acceptable(self):
        rr = RiskRatio.from_levels(entry=20.0, stop=19.0, target=23.0)
        assert rr.is_acceptable is True

    def test_below_2r_is_not_acceptable(self):
        # reward=1.5, risk=1.0 → rr=1.5
        rr = RiskRatio.from_levels(entry=20.0, stop=19.0, target=21.5)
        assert rr.is_acceptable is False

    def test_exactly_1r_is_not_acceptable(self):
        rr = RiskRatio.from_levels(entry=20.0, stop=19.0, target=21.0)
        assert rr.is_acceptable is False


class TestImmutability:
    def test_risk_ratio_is_frozen(self):
        rr = RiskRatio.from_levels(entry=20.0, stop=19.0, target=22.0)
        with pytest.raises(Exception):
            rr.risk_points = 99.0  # type: ignore

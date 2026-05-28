"""Unit tests for ExpectedValue value object."""

import pytest
from pydantic import ValidationError

from oracle.domain.analytics.value_objects import ExpectedValue


class TestEvCalculation:
    def test_positive_ev(self):
        # EV = 0.6 * 2.0 - 0.4 * 1.0 = 1.2 - 0.4 = 0.8
        ev = ExpectedValue(average_win_r=2.0, average_loss_r=1.0, win_rate_pct=60.0)
        assert ev.ev_r == 0.8

    def test_negative_ev(self):
        # EV = 0.3 * 2.0 - 0.7 * 1.0 = 0.6 - 0.7 = -0.1
        ev = ExpectedValue(average_win_r=2.0, average_loss_r=1.0, win_rate_pct=30.0)
        assert ev.ev_r == -0.1

    def test_breakeven_ev(self):
        # EV = 0.5 * 1.0 - 0.5 * 1.0 = 0.0
        ev = ExpectedValue(average_win_r=1.0, average_loss_r=1.0, win_rate_pct=50.0)
        assert ev.ev_r == 0.0

    def test_ev_rounded_to_3_decimals(self):
        # EV = 0.33 * 3.0 - 0.67 * 1.0 = 0.99 - 0.67 = 0.32
        ev = ExpectedValue(average_win_r=3.0, average_loss_r=1.0, win_rate_pct=33.0)
        assert ev.ev_r == 0.32

    def test_high_win_rate_high_rr(self):
        # EV = 0.7 * 3.0 - 0.3 * 1.0 = 2.1 - 0.3 = 1.8
        ev = ExpectedValue(average_win_r=3.0, average_loss_r=1.0, win_rate_pct=70.0)
        assert ev.ev_r == 1.8


class TestPositivity:
    def test_positive_ev_is_positive(self):
        ev = ExpectedValue(average_win_r=2.0, average_loss_r=1.0, win_rate_pct=60.0)
        assert ev.is_positive is True

    def test_negative_ev_is_not_positive(self):
        ev = ExpectedValue(average_win_r=1.0, average_loss_r=2.0, win_rate_pct=40.0)
        assert ev.is_positive is False

    def test_zero_ev_is_not_positive(self):
        ev = ExpectedValue(average_win_r=1.0, average_loss_r=1.0, win_rate_pct=50.0)
        assert ev.is_positive is False


class TestValidation:
    def test_negative_avg_win_raises(self):
        with pytest.raises(ValidationError):
            ExpectedValue(average_win_r=-0.1, average_loss_r=1.0, win_rate_pct=50.0)

    def test_negative_avg_loss_raises(self):
        with pytest.raises(ValidationError):
            ExpectedValue(average_win_r=2.0, average_loss_r=-0.1, win_rate_pct=50.0)

    def test_win_rate_above_100_raises(self):
        with pytest.raises(ValidationError):
            ExpectedValue(average_win_r=2.0, average_loss_r=1.0, win_rate_pct=100.1)

    def test_win_rate_below_0_raises(self):
        with pytest.raises(ValidationError):
            ExpectedValue(average_win_r=2.0, average_loss_r=1.0, win_rate_pct=-1.0)

"""Unit tests for DrawdownMetric value object."""

import pytest
from pydantic import ValidationError

from oracle.domain.analytics.value_objects import DrawdownMetric


def _metric(**overrides) -> DrawdownMetric:
    defaults = dict(
        max_drawdown_r=5.0,
        current_drawdown_r=0.0,
        max_consecutive_losses=4,
        current_consecutive_losses=0,
    )
    return DrawdownMetric(**{**defaults, **overrides})


class TestDrawdownState:
    def test_zero_current_is_not_in_drawdown(self):
        assert _metric(current_drawdown_r=0.0).is_in_drawdown is False

    def test_positive_current_is_in_drawdown(self):
        assert _metric(current_drawdown_r=1.5).is_in_drawdown is True

    def test_small_current_is_in_drawdown(self):
        assert _metric(current_drawdown_r=0.1).is_in_drawdown is True


class TestCriticalThreshold:
    def test_exactly_3r_is_critical(self):
        assert _metric(current_drawdown_r=3.0).is_critical is True

    def test_above_3r_is_critical(self):
        assert _metric(current_drawdown_r=4.5).is_critical is True

    def test_just_below_3r_is_not_critical(self):
        assert _metric(current_drawdown_r=2.99).is_critical is False

    def test_zero_is_not_critical(self):
        assert _metric(current_drawdown_r=0.0).is_critical is False


class TestValidation:
    def test_negative_max_drawdown_raises(self):
        with pytest.raises(ValidationError):
            _metric(max_drawdown_r=-1.0)

    def test_negative_current_drawdown_raises(self):
        with pytest.raises(ValidationError):
            _metric(current_drawdown_r=-0.1)

    def test_negative_max_consecutive_losses_raises(self):
        with pytest.raises(ValidationError):
            _metric(max_consecutive_losses=-1)

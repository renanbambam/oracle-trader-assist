"""Unit tests for ConfidenceFactors weighted average calculation."""

import pytest
from pydantic import ValidationError

from oracle.domain.analysis.value_objects import ConfidenceFactors


def _factors(**overrides) -> ConfidenceFactors:
    defaults = dict(
        trend_alignment=0.5,
        setup_quality=0.5,
        historical_match=0.5,
        macro_context=0.5,
        market_quality=0.5,
        emotional_state=0.5,
    )
    return ConfidenceFactors(**{**defaults, **overrides})


class TestWeightedAverage:
    def test_all_ones_returns_100(self):
        f = _factors(
            trend_alignment=1.0, setup_quality=1.0, historical_match=1.0,
            macro_context=1.0, market_quality=1.0, emotional_state=1.0,
        )
        assert f.weighted_average == 100.0

    def test_all_zeros_returns_0(self):
        f = _factors(
            trend_alignment=0.0, setup_quality=0.0, historical_match=0.0,
            macro_context=0.0, market_quality=0.0, emotional_state=0.0,
        )
        assert f.weighted_average == 0.0

    def test_trend_alignment_weight_is_25_percent(self):
        # Only trend_alignment=1.0 → 0.25 * 100 = 25.0
        f = _factors(
            trend_alignment=1.0, setup_quality=0.0, historical_match=0.0,
            macro_context=0.0, market_quality=0.0, emotional_state=0.0,
        )
        assert f.weighted_average == 25.0

    def test_setup_quality_weight_is_25_percent(self):
        f = _factors(
            trend_alignment=0.0, setup_quality=1.0, historical_match=0.0,
            macro_context=0.0, market_quality=0.0, emotional_state=0.0,
        )
        assert f.weighted_average == 25.0

    def test_emotional_state_weight_is_5_percent(self):
        f = _factors(
            trend_alignment=0.0, setup_quality=0.0, historical_match=0.0,
            macro_context=0.0, market_quality=0.0, emotional_state=1.0,
        )
        assert f.weighted_average == 5.0

    def test_market_quality_weight_is_10_percent(self):
        f = _factors(
            trend_alignment=0.0, setup_quality=0.0, historical_match=0.0,
            macro_context=0.0, market_quality=1.0, emotional_state=0.0,
        )
        assert f.weighted_average == 10.0

    def test_all_halves_returns_50(self):
        f = _factors()  # all defaults = 0.5
        assert f.weighted_average == 50.0


class TestValidation:
    def test_factor_above_1_raises(self):
        with pytest.raises(ValidationError):
            _factors(trend_alignment=1.1)

    def test_factor_below_0_raises(self):
        with pytest.raises(ValidationError):
            _factors(setup_quality=-0.01)

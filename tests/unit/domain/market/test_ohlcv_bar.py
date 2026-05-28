"""Unit tests for OHLCVBar value object — OHLC consistency and computed properties."""

from datetime import datetime, timezone

import pytest
from pydantic import ValidationError

from oracle.domain.market.enums import Timeframe
from oracle.domain.market.value_objects import OHLCVBar

_TS = datetime(2024, 1, 15, 9, 0, 0, tzinfo=timezone.utc)


def _bar(**overrides) -> OHLCVBar:
    defaults = dict(
        symbol="PETR4",
        timeframe=Timeframe.M5,
        timestamp=_TS,
        open=10.0,
        high=12.0,
        low=9.0,
        close=11.0,
        volume=1000.0,
    )
    return OHLCVBar(**{**defaults, **overrides})


# ── OHLC consistency ───────────────────────────────────────────────────────────

class TestOHLCConsistency:
    def test_valid_bullish_bar(self):
        bar = _bar(open=10.0, high=12.0, low=9.0, close=11.0)
        assert bar.open == 10.0

    def test_valid_bearish_bar(self):
        bar = _bar(open=11.0, high=12.0, low=9.0, close=10.0)
        assert bar.close == 10.0

    def test_doji_bar_open_equals_close(self):
        bar = _bar(open=10.0, high=12.0, low=8.0, close=10.0)
        assert bar.open == bar.close

    def test_high_below_close_raises(self):
        # high=10.5 < close=11.0
        with pytest.raises(ValidationError, match="high must be"):
            _bar(open=10.0, high=10.5, low=9.0, close=11.0)

    def test_high_below_open_raises(self):
        # high=11.0 < open=12.0
        with pytest.raises(ValidationError, match="high must be"):
            _bar(open=12.0, high=11.0, low=9.0, close=10.0)

    def test_low_above_close_raises(self):
        # low=10.5 > close=9.0
        with pytest.raises(ValidationError, match="low must be"):
            _bar(open=10.0, high=12.0, low=10.5, close=9.0)

    def test_low_above_open_raises(self):
        # low=10.0 > open=9.0
        with pytest.raises(ValidationError, match="low must be"):
            _bar(open=9.0, high=12.0, low=10.0, close=11.0)

    def test_negative_volume_raises(self):
        with pytest.raises(ValidationError):
            _bar(volume=-1.0)

    def test_zero_volume_is_valid(self):
        bar = _bar(volume=0.0)
        assert bar.volume == 0.0


# ── Directional properties ─────────────────────────────────────────────────────

class TestDirectionalProperties:
    def test_close_above_open_is_bullish(self):
        assert _bar(open=10.0, close=11.0).is_bullish is True

    def test_close_below_open_is_not_bullish(self):
        assert _bar(open=11.0, high=12.0, low=9.0, close=10.0).is_bullish is False

    def test_doji_close_equals_open_is_bullish(self):
        # close >= open: equal counts as bullish
        assert _bar(open=10.0, high=12.0, low=8.0, close=10.0).is_bullish is True


# ── Body calculations ──────────────────────────────────────────────────────────

class TestBodyCalculations:
    def test_body_size_bullish(self):
        assert _bar(open=10.0, close=11.0).body_size == 1.0

    def test_body_size_bearish_same_magnitude(self):
        assert _bar(open=11.0, high=12.0, low=9.0, close=10.0).body_size == 1.0

    def test_body_size_doji_is_zero(self):
        assert _bar(open=10.0, high=12.0, low=8.0, close=10.0).body_size == 0.0

    def test_body_pct(self):
        # body=1.0, open=10.0 → 10.0%
        assert _bar(open=10.0, close=11.0).body_pct == 10.0


# ── Wick calculations ──────────────────────────────────────────────────────────

class TestWickCalculations:
    def test_upper_wick_bullish(self):
        # high=12, max(open=10, close=11)=11 → wick=1.0
        assert _bar(open=10.0, high=12.0, low=9.0, close=11.0).upper_wick == 1.0

    def test_lower_wick_bullish(self):
        # min(open=10, close=11)=10, low=9 → wick=1.0
        assert _bar(open=10.0, high=12.0, low=9.0, close=11.0).lower_wick == 1.0

    def test_pin_bar_large_upper_wick(self):
        bar = _bar(open=10.0, high=15.0, low=9.5, close=10.5)
        assert bar.upper_wick == 4.5   # 15.0 - 10.5
        assert bar.lower_wick == 0.5   # 10.0 - 9.5

    def test_full_body_bar_has_no_wicks(self):
        # high == close, low == open (marubozu bullish)
        bar = _bar(open=10.0, high=11.0, low=10.0, close=11.0)
        assert bar.upper_wick == 0.0
        assert bar.lower_wick == 0.0

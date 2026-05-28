"""Unit tests for WinRate value object."""

import pytest
from pydantic import ValidationError

from oracle.domain.analytics.value_objects import WinRate


class TestPct:
    def test_70_percent(self):
        assert WinRate(wins=7, losses=3).pct == 70.0

    def test_100_percent(self):
        assert WinRate(wins=10, losses=0).pct == 100.0

    def test_0_percent(self):
        assert WinRate(wins=0, losses=10).pct == 0.0

    def test_zero_trades_returns_0_without_error(self):
        assert WinRate(wins=0, losses=0).pct == 0.0

    def test_breakevens_included_in_total(self):
        # wins=5, total=10 (5 losses + 0 be... wait) wins=5, losses=3, be=2 → total=10, pct=50
        wr = WinRate(wins=5, losses=3, breakevens=2)
        assert wr.total == 10
        assert wr.pct == 50.0

    def test_pct_rounded_to_1_decimal(self):
        # 1/3 * 100 = 33.333... → 33.3
        assert WinRate(wins=1, losses=2).pct == 33.3

    def test_total_without_breakevens(self):
        wr = WinRate(wins=3, losses=7)
        assert wr.total == 10


class TestProfitability:
    def test_above_50_is_profitable(self):
        assert WinRate(wins=6, losses=4).is_profitable is True

    def test_exactly_50_is_not_profitable(self):
        assert WinRate(wins=5, losses=5).is_profitable is False

    def test_below_50_is_not_profitable(self):
        assert WinRate(wins=3, losses=7).is_profitable is False


class TestValidation:
    def test_negative_wins_raises(self):
        with pytest.raises(ValidationError):
            WinRate(wins=-1, losses=5)

    def test_negative_losses_raises(self):
        with pytest.raises(ValidationError):
            WinRate(wins=5, losses=-1)

    def test_negative_breakevens_raises(self):
        with pytest.raises(ValidationError):
            WinRate(wins=5, losses=3, breakevens=-1)

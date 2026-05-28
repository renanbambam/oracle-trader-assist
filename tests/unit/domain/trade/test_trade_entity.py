"""Unit tests for Trade entity — LONG/SHORT geometry and business properties."""

from datetime import datetime, timezone

import pytest
from pydantic import ValidationError

from oracle.domain.market.enums import Timeframe
from oracle.domain.trade.entities import Trade
from oracle.domain.trade.enums import Direction, EmotionalState, TradeStatus


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _long(**overrides) -> Trade:
    defaults = dict(
        asset="PETR4",
        direction=Direction.LONG,
        timeframe=Timeframe.M5,
        entry=20.0,
        stop=19.0,
        target=22.0,
        setup="breakout",
        emotional_state=EmotionalState.CALMO,
        opened_at=_utcnow(),
    )
    return Trade(**{**defaults, **overrides})


def _short(**overrides) -> Trade:
    defaults = dict(
        asset="PETR4",
        direction=Direction.SHORT,
        timeframe=Timeframe.M5,
        entry=20.0,
        stop=21.0,
        target=18.0,
        setup="reversal",
        emotional_state=EmotionalState.CALMO,
        opened_at=_utcnow(),
    )
    return Trade(**{**defaults, **overrides})


# ── LONG geometry ──────────────────────────────────────────────────────────────

class TestLongGeometry:
    def test_valid_long_is_created(self):
        trade = _long()
        assert trade.direction == Direction.LONG
        assert trade.entry == 20.0
        assert trade.stop == 19.0
        assert trade.target == 22.0

    def test_long_stop_equal_to_entry_raises(self):
        with pytest.raises(ValidationError, match="stop must be below entry"):
            _long(stop=20.0)

    def test_long_stop_above_entry_raises(self):
        with pytest.raises(ValidationError, match="stop must be below entry"):
            _long(stop=21.0)

    def test_long_target_equal_to_entry_raises(self):
        with pytest.raises(ValidationError, match="target must be above entry"):
            _long(target=20.0)

    def test_long_target_below_entry_raises(self):
        with pytest.raises(ValidationError, match="target must be above entry"):
            _long(target=18.0)


# ── SHORT geometry ─────────────────────────────────────────────────────────────

class TestShortGeometry:
    def test_valid_short_is_created(self):
        trade = _short()
        assert trade.direction == Direction.SHORT
        assert trade.entry == 20.0
        assert trade.stop == 21.0
        assert trade.target == 18.0

    def test_short_stop_equal_to_entry_raises(self):
        with pytest.raises(ValidationError, match="stop must be above entry"):
            _short(stop=20.0)

    def test_short_stop_below_entry_raises(self):
        with pytest.raises(ValidationError, match="stop must be above entry"):
            _short(stop=19.0)

    def test_short_target_equal_to_entry_raises(self):
        with pytest.raises(ValidationError, match="target must be below entry"):
            _short(target=20.0)

    def test_short_target_above_entry_raises(self):
        with pytest.raises(ValidationError, match="target must be below entry"):
            _short(target=21.0)


# ── Status ─────────────────────────────────────────────────────────────────────

class TestTradeStatus:
    def test_new_trade_defaults_to_open(self):
        trade = _long()
        assert trade.is_open is True

    def test_cancelled_trade_is_not_open(self):
        trade = _long(status=TradeStatus.CANCELLED)
        assert trade.is_open is False

    def test_closed_trade_is_not_open(self):
        trade = _long(status=TradeStatus.CLOSED)
        assert trade.is_open is False


# ── Emotional state ────────────────────────────────────────────────────────────

class TestEmotionalCompromise:
    def test_fomo_is_compromised(self):
        assert _long(emotional_state=EmotionalState.FOMO).is_emotionally_compromised is True

    def test_revanche_is_compromised(self):
        assert _long(emotional_state=EmotionalState.REVANCHE).is_emotionally_compromised is True

    def test_calmo_is_not_compromised(self):
        assert _long(emotional_state=EmotionalState.CALMO).is_emotionally_compromised is False

    def test_ansioso_is_not_compromised(self):
        assert _long(emotional_state=EmotionalState.ANSIOSO).is_emotionally_compromised is False

    def test_confiante_is_not_compromised(self):
        assert _long(emotional_state=EmotionalState.CONFIANTE).is_emotionally_compromised is False


# ── Risk ratio delegation ──────────────────────────────────────────────────────

class TestRiskRatioDelegation:
    def test_long_risk_ratio_computed_correctly(self):
        # entry=20, stop=19, target=22 → risk=1, reward=2, rr=2.0
        rr = _long(entry=20.0, stop=19.0, target=22.0).risk_ratio
        assert rr.risk_points == 1.0
        assert rr.reward_points == 2.0
        assert rr.rr == 2.0

    def test_short_risk_ratio_computed_correctly(self):
        # entry=20, stop=22, target=16 → risk=2, reward=4, rr=2.0
        rr = _short(entry=20.0, stop=22.0, target=16.0).risk_ratio
        assert rr.risk_points == 2.0
        assert rr.reward_points == 4.0
        assert rr.rr == 2.0

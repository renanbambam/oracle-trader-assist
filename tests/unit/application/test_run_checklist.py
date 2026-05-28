"""Unit tests for RunChecklistUseCase — pure domain logic, zero I/O."""

from datetime import datetime

import pytest

from oracle.application.trade.dtos import ChecklistInput
from oracle.application.trade.run_checklist import RunChecklistUseCase
from oracle.domain.market.enums import Timeframe
from oracle.domain.trade.enums import Direction, EmotionalState

_safe_time = datetime(2026, 1, 2, 10, 30)  # 10:30 — not a blocked window
_risky_time = datetime(2026, 1, 2, 14, 15)  # 14:15 — US open window
_b3_open_time = datetime(2026, 1, 2, 9, 5)  # B3 opening auction


def _input(**overrides):
    defaults = dict(
        asset="PETR4",
        direction=Direction.LONG,
        timeframe=Timeframe.M15,
        setup="breakout",
        emotional_state=EmotionalState.CALMO,
        rr_ratio=2.0,
        today_losses=0,
    )
    return ChecklistInput(**{**defaults, **overrides})


def test_all_rules_pass_returns_operar():
    result = RunChecklistUseCase().execute(_input(), check_time=_safe_time)
    assert result.verdict == "OPERAR"
    assert result.passed_count == result.total_count


def test_fomo_emotional_state_blocks_operation():
    result = RunChecklistUseCase().execute(_input(emotional_state=EmotionalState.FOMO), check_time=_safe_time)
    assert result.verdict == "NAO_OPERAR"
    blocked = [i for i in result.items if i.rule == "Estado emocional"]
    assert blocked[0].passed is False
    assert blocked[0].blocking is True


def test_low_rr_ratio_blocks_operation():
    result = RunChecklistUseCase().execute(_input(rr_ratio=1.0), check_time=_safe_time)
    assert result.verdict == "NAO_OPERAR"


def test_two_daily_losses_blocks_operation():
    result = RunChecklistUseCase().execute(_input(today_losses=2), check_time=_safe_time)
    assert result.verdict == "NAO_OPERAR"


def test_empty_setup_blocks_operation():
    result = RunChecklistUseCase().execute(_input(setup=""), check_time=_safe_time)
    assert result.verdict == "NAO_OPERAR"


def test_risky_time_gives_atencao_not_blocking():
    result = RunChecklistUseCase().execute(_input(), check_time=_risky_time)
    assert result.verdict == "ATENÇÃO"
    time_item = next(i for i in result.items if i.rule == "Janela de horário")
    assert time_item.passed is False
    assert time_item.blocking is False


def test_b3_open_time_non_blocking():
    result = RunChecklistUseCase().execute(_input(), check_time=_b3_open_time)
    assert result.verdict == "ATENÇÃO"
    time_item = next(i for i in result.items if i.rule == "Janela de horário")
    assert time_item.passed is False
    assert time_item.blocking is False


def test_revanche_also_blocks():
    result = RunChecklistUseCase().execute(_input(emotional_state=EmotionalState.REVANCHE), check_time=_safe_time)
    assert result.verdict == "NAO_OPERAR"


def test_one_loss_confiante_passes():
    result = RunChecklistUseCase().execute(
        _input(emotional_state=EmotionalState.CONFIANTE, today_losses=1),
        check_time=_safe_time,
    )
    assert result.verdict == "OPERAR"

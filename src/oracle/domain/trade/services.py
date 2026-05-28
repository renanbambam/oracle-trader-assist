"""Trade domain services — pure business logic, zero I/O.

ChecklistValidator enforces anti-FOMO and risk management rules.
All results are plain NamedTuples so the domain stays dependency-free.
"""

from datetime import datetime
from typing import NamedTuple

from oracle.domain.trade.enums import EmotionalState

_MIN_RR = 1.5
_MAX_DAILY_LOSSES = 2
# 14:00–14:59 BRT (US market open volatility spike); 9:00–9:14 BRT (B3 opening auction)
_BLOCKED_HOURS = frozenset([14])


class ChecklistItem(NamedTuple):
    rule: str
    passed: bool
    blocking: bool
    message: str


class ChecklistResult(NamedTuple):
    items: list[ChecklistItem]
    passed_count: int
    total_count: int
    verdict: str  # "OPERAR" | "ATENÇÃO" | "NAO_OPERAR"


class ChecklistValidator:
    """Validates a trade intent against anti-FOMO and risk management rules."""

    def validate(
        self,
        emotional_state: str,
        rr_ratio: float,
        today_losses: int,
        setup: str,
        check_time: datetime | None = None,
    ) -> ChecklistResult:
        now = check_time or datetime.now()
        items = [
            self._check_emotional_state(emotional_state),
            self._check_rr_ratio(rr_ratio),
            self._check_time_window(now),
            self._check_daily_losses(today_losses),
            self._check_setup_named(setup),
        ]

        passed = sum(1 for i in items if i.passed)
        blocking_failed = any(not i.passed and i.blocking for i in items)

        if blocking_failed:
            verdict = "NAO_OPERAR"
        elif passed < len(items):
            verdict = "ATENÇÃO"
        else:
            verdict = "OPERAR"

        return ChecklistResult(
            items=items,
            passed_count=passed,
            total_count=len(items),
            verdict=verdict,
        )

    @staticmethod
    def _check_emotional_state(state: str) -> ChecklistItem:
        allowed = {EmotionalState.CALMO.value, EmotionalState.CONFIANTE.value}
        passed = str(state) in allowed
        return ChecklistItem(
            rule="Estado emocional",
            passed=passed,
            blocking=True,
            message="OK" if passed else f"'{state}' aumenta risco — aguardar ou não operar",
        )

    @staticmethod
    def _check_rr_ratio(rr: float) -> ChecklistItem:
        passed = rr >= _MIN_RR
        return ChecklistItem(
            rule="Relação Risco:Retorno",
            passed=passed,
            blocking=True,
            message=f"R:R {rr:.1f} ≥ {_MIN_RR}" if passed else f"R:R {rr:.1f} < mínimo {_MIN_RR}",
        )

    @staticmethod
    def _check_time_window(now: datetime) -> ChecklistItem:
        h, m = now.hour, now.minute
        in_b3_open = h == 9 and m < 15
        in_us_open = h in _BLOCKED_HOURS
        passed = not in_b3_open and not in_us_open
        msg = "Horário favorável" if passed else "Janela de risco (abertura B3 ou EUA) — aguardar"
        return ChecklistItem(rule="Janela de horário", passed=passed, blocking=False, message=msg)

    @staticmethod
    def _check_daily_losses(losses: int) -> ChecklistItem:
        passed = losses < _MAX_DAILY_LOSSES
        return ChecklistItem(
            rule="Limite de perdas diárias",
            passed=passed,
            blocking=True,
            message=f"{losses}/{_MAX_DAILY_LOSSES} perdas" if passed
            else f"{losses} perdas — limite atingido, encerrar operações",
        )

    @staticmethod
    def _check_setup_named(setup: str) -> ChecklistItem:
        passed = bool(setup and setup.strip())
        return ChecklistItem(
            rule="Setup identificado",
            passed=passed,
            blocking=True,
            message="Setup definido" if passed else "Operar sem setup é especulação — identificar padrão primeiro",
        )

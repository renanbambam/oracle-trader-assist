"""GetPerformanceUseCase — computes performance metrics from closed trades."""

from datetime import datetime, timedelta, timezone

from oracle.application.analytics.dtos import PerformanceOutput, PerformanceQuery
from oracle.domain.analytics.enums import MetricPeriod, PerformanceGrade
from oracle.domain.analytics.value_objects import DrawdownMetric, ExpectedValue, WinRate
from oracle.domain.trade.enums import TradeResult, TradeStatus


class GetPerformanceUseCase:
    def __init__(self, trade_repository, analytics_repository) -> None:
        self._trade_repo = trade_repository
        self._analytics_repo = analytics_repository

    async def execute(self, query: PerformanceQuery) -> PerformanceOutput:
        period_start, period_end = _period_range(query.period)
        closed = await self._trade_repo.get_by_status(TradeStatus.CLOSED)

        if query.asset:
            closed = [t for t in closed if t.asset == query.asset]

        if query.period != MetricPeriod.ALL_TIME:
            closed = [
                t for t in closed
                if t.closed_at and period_start <= t.closed_at <= period_end
            ]

        report = _compute(closed, query.period, period_start, period_end)
        await self._analytics_repo.save(report, asset=query.asset)
        return report

    async def get_summary(self) -> PerformanceOutput:
        return await self.execute(PerformanceQuery(period=MetricPeriod.ALL_TIME))


def _period_range(period: MetricPeriod) -> tuple[datetime, datetime]:
    end = datetime.now(timezone.utc)
    deltas = {
        MetricPeriod.DAILY: timedelta(days=1),
        MetricPeriod.WEEKLY: timedelta(weeks=1),
        MetricPeriod.MONTHLY: timedelta(days=30),
        MetricPeriod.QUARTERLY: timedelta(days=90),
    }
    delta = deltas.get(period)
    start = (end - delta) if delta else datetime(2000, 1, 1, tzinfo=timezone.utc)
    return start, end


def _compute(
    trades: list,
    period: MetricPeriod,
    period_start: datetime,
    period_end: datetime,
) -> PerformanceOutput:
    now = datetime.now(timezone.utc)

    if not trades:
        return PerformanceOutput(
            period=period,
            period_start=period_start,
            period_end=period_end,
            win_rate_pct=0.0,
            total_trades=0,
            total_r=0.0,
            average_r=0.0,
            expected_value_r=0.0,
            max_drawdown_r=0.0,
            grade=PerformanceGrade.F,
            generated_at=now,
        )

    wins = [t for t in trades if t.result == TradeResult.WIN]
    losses = [t for t in trades if t.result == TradeResult.LOSS]
    breakevens = [t for t in trades if t.result == TradeResult.BREAKEVEN]

    win_rate = WinRate(wins=len(wins), losses=len(losses), breakevens=len(breakevens))

    win_rs = [t.r_realized or 0.0 for t in wins]
    loss_rs = [abs(t.r_realized or 0.0) for t in losses]
    avg_win_r = round(sum(win_rs) / len(win_rs), 3) if win_rs else 0.0
    avg_loss_r = round(sum(loss_rs) / len(loss_rs), 3) if loss_rs else 0.0

    ev = ExpectedValue(
        average_win_r=avg_win_r,
        average_loss_r=avg_loss_r,
        win_rate_pct=win_rate.pct,
    )

    r_series = [t.r_realized or 0.0 for t in trades]
    total_r = round(sum(r_series), 2)
    average_r = round(total_r / len(trades), 2)

    dd = _compute_drawdown(r_series)
    grade = _grade(win_rate.pct, ev.ev_r)

    return PerformanceOutput(
        period=period,
        period_start=period_start,
        period_end=period_end,
        win_rate_pct=win_rate.pct,
        total_trades=len(trades),
        total_r=total_r,
        average_r=average_r,
        expected_value_r=ev.ev_r,
        max_drawdown_r=dd.max_drawdown_r,
        grade=grade,
        generated_at=now,
    )


def _compute_drawdown(r_series: list[float]) -> DrawdownMetric:
    peak = 0.0
    running = 0.0
    max_dd = 0.0
    consecutive = 0
    max_consecutive = 0

    for r in r_series:
        running += r
        peak = max(peak, running)
        dd = peak - running
        max_dd = max(max_dd, dd)
        if r < 0:
            consecutive += 1
            max_consecutive = max(max_consecutive, consecutive)
        else:
            consecutive = 0

    current_dd = max(0.0, peak - running)
    return DrawdownMetric(
        max_drawdown_r=round(max_dd, 2),
        current_drawdown_r=round(current_dd, 2),
        max_consecutive_losses=max_consecutive,
        current_consecutive_losses=consecutive,
    )


def _grade(win_rate_pct: float, ev_r: float) -> PerformanceGrade:
    if ev_r >= 0.3 and win_rate_pct >= 55:
        return PerformanceGrade.A
    if ev_r >= 0.1 and win_rate_pct >= 50:
        return PerformanceGrade.B
    if ev_r >= 0.0 and win_rate_pct >= 45:
        return PerformanceGrade.C
    if ev_r >= -0.2:
        return PerformanceGrade.D
    return PerformanceGrade.F

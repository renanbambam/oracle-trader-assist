"""PostgreSQL implementation of analytics report persistence."""

from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from oracle.application.analytics.dtos import PerformanceOutput
from oracle.domain.analytics.enums import MetricPeriod
from oracle.infrastructure.database.models.analytics_model import PerformanceReportOrm


def _to_orm(report: PerformanceOutput, asset: str | None) -> PerformanceReportOrm:
    now = datetime.now(timezone.utc)
    return PerformanceReportOrm(
        created_at=now,
        updated_at=now,
        period=str(report.period),
        period_start=report.period_start,
        period_end=report.period_end,
        asset=asset,
        win_rate_pct=report.win_rate_pct,
        total_trades=report.total_trades,
        total_r=report.total_r,
        average_r=report.average_r,
        expected_value_r=report.expected_value_r,
        max_drawdown_r=report.max_drawdown_r,
        grade=str(report.grade),
        generated_at=report.generated_at,
    )


def _to_dto(row: PerformanceReportOrm) -> PerformanceOutput:
    from oracle.domain.analytics.enums import PerformanceGrade
    return PerformanceOutput(
        period=MetricPeriod(row.period),
        period_start=row.period_start,
        period_end=row.period_end,
        win_rate_pct=row.win_rate_pct,
        total_trades=row.total_trades,
        total_r=row.total_r,
        average_r=row.average_r,
        expected_value_r=row.expected_value_r,
        max_drawdown_r=row.max_drawdown_r,
        grade=PerformanceGrade(row.grade),
        generated_at=row.generated_at,
    )


class PostgresAnalyticsRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def save(self, report: PerformanceOutput, asset: str | None = None) -> None:
        self._session.add(_to_orm(report, asset))
        await self._session.flush()

    async def get_latest(
        self,
        period: MetricPeriod,
        asset: str | None = None,
    ) -> PerformanceOutput | None:
        stmt = (
            select(PerformanceReportOrm)
            .where(PerformanceReportOrm.period == str(period))
            .where(PerformanceReportOrm.asset == asset)
            .order_by(PerformanceReportOrm.generated_at.desc())
            .limit(1)
        )
        row = (await self._session.execute(stmt)).scalars().first()
        return _to_dto(row) if row else None

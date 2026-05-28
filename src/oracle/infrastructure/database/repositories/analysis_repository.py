"""PostgreSQL implementation of AnalysisRepository."""

import json
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from oracle.domain.analysis.entities import ChartAnalysis
from oracle.domain.analysis.enums import AnalysisStatus, ConfidenceLabel, Suggestion, TrendDirection, TrendStrength
from oracle.domain.analysis.value_objects import ConfidenceScore
from oracle.domain.market.enums import Timeframe
from oracle.infrastructure.database.models.analysis_model import ChartAnalysisOrm


def _to_orm(a: ChartAnalysis) -> ChartAnalysisOrm:
    return ChartAnalysisOrm(
        id=a.id,
        created_at=a.created_at,
        updated_at=a.updated_at,
        session_id=a.session_id,
        asset=a.asset,
        timeframe=str(a.timeframe),
        status=str(a.status),
        suggestion=str(a.suggestion) if a.suggestion else None,
        confidence_score=a.confidence.score if a.confidence else None,
        confidence_label=str(a.confidence.label) if a.confidence else None,
        confidence_justification=a.confidence.justification if a.confidence else None,
        trend_direction=str(a.trend_direction) if a.trend_direction else None,
        trend_strength=str(a.trend_strength) if a.trend_strength else None,
        support_level=a.support_level,
        resistance_level=a.resistance_level,
        setup_description=a.setup_description,
        reasoning=a.reasoning,
        risks_json=json.dumps(a.risks) if a.risks else None,
        bull_scenario=a.bull_scenario,
        bear_scenario=a.bear_scenario,
        raw_response=a.raw_response,
        screenshot_path=a.screenshot_path,
    )


def _to_domain(row: ChartAnalysisOrm) -> ChartAnalysis:
    confidence = None
    if row.confidence_score is not None and row.confidence_label and row.confidence_justification:
        confidence = ConfidenceScore(
            score=row.confidence_score,
            label=ConfidenceLabel(row.confidence_label),
            justification=row.confidence_justification,
        )
    return ChartAnalysis(
        id=row.id,
        created_at=row.created_at,
        updated_at=row.updated_at,
        session_id=row.session_id,
        asset=row.asset,
        timeframe=Timeframe(row.timeframe),
        status=AnalysisStatus(row.status),
        suggestion=Suggestion(row.suggestion) if row.suggestion else None,
        confidence=confidence,
        trend_direction=TrendDirection(row.trend_direction) if row.trend_direction else None,
        trend_strength=TrendStrength(row.trend_strength) if row.trend_strength else None,
        support_level=row.support_level,
        resistance_level=row.resistance_level,
        setup_description=row.setup_description,
        reasoning=row.reasoning,
        risks=json.loads(row.risks_json) if row.risks_json else [],
        bull_scenario=row.bull_scenario,
        bear_scenario=row.bear_scenario,
        raw_response=row.raw_response,
        screenshot_path=row.screenshot_path,
    )


class PostgresAnalysisRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def save(self, analysis: ChartAnalysis) -> ChartAnalysis:
        self._session.add(_to_orm(analysis))
        await self._session.flush()
        return analysis

    async def get_by_id(self, analysis_id: UUID) -> ChartAnalysis | None:
        row = await self._session.get(ChartAnalysisOrm, analysis_id)
        return _to_domain(row) if row else None

    async def update(self, analysis: ChartAnalysis) -> ChartAnalysis:
        await self._session.merge(_to_orm(analysis))
        await self._session.flush()
        return analysis

    async def get_by_session(self, session_id: UUID, limit: int = 10) -> list[ChartAnalysis]:
        stmt = (
            select(ChartAnalysisOrm)
            .where(ChartAnalysisOrm.session_id == session_id)
            .order_by(ChartAnalysisOrm.created_at.desc())
            .limit(limit)
        )
        rows = (await self._session.execute(stmt)).scalars().all()
        return [_to_domain(r) for r in rows]

    async def get_by_asset(self, asset: str, limit: int = 20) -> list[ChartAnalysis]:
        stmt = (
            select(ChartAnalysisOrm)
            .where(ChartAnalysisOrm.asset == asset)
            .order_by(ChartAnalysisOrm.created_at.desc())
            .limit(limit)
        )
        rows = (await self._session.execute(stmt)).scalars().all()
        return [_to_domain(r) for r in rows]

    async def get_recent(self, limit: int = 20) -> list[ChartAnalysis]:
        stmt = (
            select(ChartAnalysisOrm)
            .order_by(ChartAnalysisOrm.created_at.desc())
            .limit(limit)
        )
        rows = (await self._session.execute(stmt)).scalars().all()
        return [_to_domain(r) for r in rows]

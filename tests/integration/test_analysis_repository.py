"""Integration tests for PostgresAnalysisRepository — real PostgreSQL."""

from uuid import uuid4

import pytest

from oracle.domain.analysis.entities import ChartAnalysis
from oracle.domain.analysis.enums import AnalysisStatus, ConfidenceLabel, Suggestion, TrendDirection, TrendStrength
from oracle.domain.analysis.value_objects import ConfidenceScore
from oracle.domain.market.enums import Timeframe
from oracle.infrastructure.database.repositories.analysis_repository import PostgresAnalysisRepository
from tests.integration.conftest import requires_docker

pytestmark = requires_docker


def _analysis(**overrides) -> ChartAnalysis:
    defaults = dict(
        session_id=uuid4(),
        asset="PETR4",
        timeframe=Timeframe.M5,
        status=AnalysisStatus.PENDING,
    )
    return ChartAnalysis(**{**defaults, **overrides})


def _completed_analysis(**overrides) -> ChartAnalysis:
    a = _analysis(status=AnalysisStatus.COMPLETED, **overrides)
    a.suggestion = Suggestion.OPERAR
    a.confidence = ConfidenceScore(
        score=75.0,
        label=ConfidenceLabel.ALTA,
        justification="confluência técnica forte",
    )
    a.trend_direction = TrendDirection.BULLISH
    a.trend_strength = TrendStrength.FORTE
    a.reasoning = "Preço rompeu resistência com volume acima da média."
    a.risks = ["Reversão no suporte", "Notícia macro adversa"]
    a.bull_scenario = "Testa 31.00"
    a.bear_scenario = "Retorna ao suporte em 28.50"
    return a


async def test_save_and_get_by_id(session):
    repo = PostgresAnalysisRepository(session)
    analysis = _analysis()

    await repo.save(analysis)
    found = await repo.get_by_id(analysis.id)

    assert found is not None
    assert found.id == analysis.id
    assert found.asset == "PETR4"
    assert found.timeframe == Timeframe.M5
    assert found.status == AnalysisStatus.PENDING


async def test_get_by_id_not_found_returns_none(session):
    repo = PostgresAnalysisRepository(session)
    assert await repo.get_by_id(uuid4()) is None


async def test_save_and_update_to_completed(session):
    repo = PostgresAnalysisRepository(session)
    analysis = _analysis()
    await repo.save(analysis)

    analysis.status = AnalysisStatus.COMPLETED
    analysis.suggestion = Suggestion.AGUARDAR
    analysis.reasoning = "Setup indefinido, aguardar confirmação."
    await repo.update(analysis)

    found = await repo.get_by_id(analysis.id)
    assert found.status == AnalysisStatus.COMPLETED
    assert found.suggestion == Suggestion.AGUARDAR
    assert found.reasoning == "Setup indefinido, aguardar confirmação."


async def test_confidence_score_roundtrip(session):
    repo = PostgresAnalysisRepository(session)
    analysis = _completed_analysis()
    await repo.save(analysis)

    found = await repo.get_by_id(analysis.id)

    assert found.confidence is not None
    assert found.confidence.score == 75.0
    assert found.confidence.label == ConfidenceLabel.ALTA
    assert found.confidence.justification == "confluência técnica forte"


async def test_risks_list_roundtrip(session):
    repo = PostgresAnalysisRepository(session)
    analysis = _completed_analysis()
    await repo.save(analysis)

    found = await repo.get_by_id(analysis.id)
    assert found.risks == ["Reversão no suporte", "Notícia macro adversa"]


async def test_get_by_session(session):
    repo = PostgresAnalysisRepository(session)
    session_id = uuid4()
    a1 = _analysis(session_id=session_id)
    a2 = _analysis(session_id=session_id)
    other = _analysis()

    for a in [a1, a2, other]:
        await repo.save(a)

    results = await repo.get_by_session(session_id)
    ids = {r.id for r in results}
    assert a1.id in ids
    assert a2.id in ids
    assert other.id not in ids


async def test_get_by_asset(session):
    repo = PostgresAnalysisRepository(session)
    petr = _analysis(asset="PETR4")
    win = _analysis(asset="WINFUT")
    await repo.save(petr)
    await repo.save(win)

    results = await repo.get_by_asset("PETR4")
    assert all(r.asset == "PETR4" for r in results)
    assert any(r.id == petr.id for r in results)

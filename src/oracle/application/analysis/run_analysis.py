"""RunAnalysisUseCase — orchestrates the AI chart analysis flow.

Flow: create PENDING entity → build prompt → call Claude → parse response
      → update entity to COMPLETED → persist → publish event → return DTO.
"""

import traceback
from uuid import uuid4

from loguru import logger

from oracle.application.analysis.dtos import RunAnalysisInput, RunAnalysisOutput
from oracle.core.ports import EventBus
from oracle.domain.analysis.entities import ChartAnalysis
from oracle.domain.analysis.enums import AnalysisStatus
from oracle.domain.analysis.events import AnalysisCompleted
from prompts.analysis.chart_analysis import build_prompt
from prompts.analysis.response_parser import parse_analysis_response
from prompts.system.oracle_system_v1 import TEMPLATE as SYSTEM_PROMPT


class RunAnalysisUseCase:
    def __init__(
        self,
        repository,
        ai_provider,
        event_bus: EventBus,
        load_context_uc=None,   # LoadContextUseCase — optional context injection
        save_context_uc=None,   # SaveContextUseCase — optional context persistence
        news_provider=None,
        calendar_provider=None,
    ) -> None:
        self._repo = repository
        self._ai = ai_provider
        self._event_bus = event_bus
        self._load_ctx = load_context_uc
        self._save_ctx = save_context_uc
        self._news = news_provider
        self._calendar = calendar_provider

    async def execute(self, data: RunAnalysisInput) -> RunAnalysisOutput:
        session_id = data.session_id or uuid4()

        analysis = ChartAnalysis(
            session_id=session_id,
            asset=data.asset,
            timeframe=data.timeframe,
            status=AnalysisStatus.PENDING,
        )
        await self._repo.save(analysis)

        history: str | None = None
        similar_history: str | None = None
        if self._load_ctx is not None:
            history = await self._load_ctx.get_history_for_prompt(data.asset)
            similar_history = await self._load_ctx.get_recent_records_for_prompt(data.asset)

        news_context: str | None = None
        if self._news is not None:
            try:
                items = await self._news.get_news(data.asset, max_results=3)
                if items:
                    lines = [f"NOTÍCIAS RECENTES ({data.asset}):"]
                    for item in items:
                        lines.append(f"- {item.title} [{item.source}]")
                        if item.summary:
                            lines.append(f"  {item.summary[:120]}")
                    news_context = "\n".join(lines)
            except Exception as exc:
                logger.warning(f"News fetch failed: {exc}")

        calendar_context: str | None = None
        if self._calendar is not None:
            try:
                events = await self._calendar.get_today_events()
                high_impact = [e for e in events if e.impact == "HIGH"]
                if high_impact:
                    lines = ["EVENTOS MACRO HOJE (HIGH IMPACT):"]
                    for ev in high_impact[:5]:
                        lines.append(f"- {ev.time} | {ev.country} | {ev.title}")
                    calendar_context = "\n".join(lines)
            except Exception as exc:
                logger.warning(f"Calendar fetch failed: {exc}")

        prompt = build_prompt(
            asset=data.asset,
            timeframe=str(data.timeframe),
            has_screenshot=data.screenshot_b64 is not None,
            notes=data.notes,
            history=history or None,
            similar_history=similar_history or None,
            news_context=news_context,
            calendar_context=calendar_context,
        )

        try:
            raw = await self._ai.complete(
                prompt=prompt,
                system=SYSTEM_PROMPT,
                image_b64=data.screenshot_b64,
            )
        except Exception as exc:
            logger.error(f"Analysis failed:\n{traceback.format_exc()}")
            analysis.status = AnalysisStatus.FAILED
            await self._repo.update(analysis)
            raise RuntimeError(f"AI provider failed: {exc}") from exc

        parsed = parse_analysis_response(raw)

        analysis.status = AnalysisStatus.COMPLETED
        analysis.raw_response = raw
        analysis.suggestion = parsed.suggestion
        analysis.confidence = parsed.confidence
        analysis.trend_direction = parsed.trend_direction
        analysis.trend_strength = parsed.trend_strength
        analysis.support_level = parsed.support_level
        analysis.resistance_level = parsed.resistance_level
        analysis.setup_description = parsed.setup_description
        analysis.reasoning = parsed.reasoning
        analysis.risks = parsed.risks
        analysis.bull_scenario = parsed.bull_scenario
        analysis.bear_scenario = parsed.bear_scenario

        await self._repo.update(analysis)

        if self._load_ctx is not None and self._save_ctx is not None and parsed.reasoning:
            from oracle.application.memory.dtos import AppendMessageInput, LoadContextInput
            from oracle.domain.memory.enums import MessageRole
            ctx = await self._load_ctx.execute(LoadContextInput(asset=data.asset))
            await self._save_ctx.execute(
                AppendMessageInput(
                    session_id=ctx.session_id,
                    role=MessageRole.ASSISTANT,
                    content=f"{parsed.suggestion} | {parsed.reasoning or ''}",
                )
            )

        await self._event_bus.publish(
            channel="analysis",
            event="analysis.completed",
            payload=AnalysisCompleted(
                session_id=session_id,
                analysis_id=analysis.id,
                asset=analysis.asset,
                timeframe=analysis.timeframe,
                suggestion=parsed.suggestion,
                confidence_score=parsed.confidence.score,
                confidence_label=parsed.confidence.label,
                trend_direction=parsed.trend_direction,
            ).model_dump(mode="json"),
        )

        return _to_output(analysis)

    async def get(self, analysis_id) -> RunAnalysisOutput | None:
        analysis = await self._repo.get_by_id(analysis_id)
        if analysis is None:
            return None
        return _to_output(analysis)

    async def list_recent(self, asset: str | None = None, limit: int = 20) -> list[RunAnalysisOutput]:
        if asset:
            analyses = await self._repo.get_by_asset(asset.upper(), limit=limit)
        else:
            analyses = await self._repo.get_recent(limit=limit)
        return [_to_output(a) for a in analyses]


def _to_output(analysis: ChartAnalysis) -> RunAnalysisOutput:
    confidence = analysis.confidence
    return RunAnalysisOutput(
        analysis_id=analysis.id,
        asset=analysis.asset,
        timeframe=analysis.timeframe,
        suggestion=analysis.suggestion or "REVISAR_CONTEXTO",
        confidence_score=confidence.score if confidence else 0.0,
        confidence_label=confidence.label if confidence else "MUITO_BAIXA",
        trend_direction=analysis.trend_direction or "LATERAL",
        reasoning=analysis.reasoning or "",
        risks=analysis.risks or [],
        bull_scenario=analysis.bull_scenario or "",
        bear_scenario=analysis.bear_scenario or "",
        created_at=analysis.created_at,
    )

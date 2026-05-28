"""morning_briefing_job — scheduled generation of the morning briefing.

Runs every weekday at 07:00 (America/Sao_Paulo). Calls BriefingService,
publishes result to EventBus, and optionally notifies via Telegram.
"""

from datetime import datetime, timezone

from loguru import logger


async def run_morning_briefing(
    *,
    engine,
    settings,
    event_bus,
) -> None:
    """Entry point called by OracleScheduler."""
    started_at = datetime.now(timezone.utc)
    logger.info(f"MorningBriefingJob: starting at {started_at.isoformat()}")

    try:
        result = await _generate_briefing(engine=engine, settings=settings)
    except Exception as exc:
        logger.error(f"MorningBriefingJob: briefing generation failed — {exc}")
        return

    await event_bus.publish(
        channel="system",
        event="briefing.generated",
        payload={
            "content": result.content[:500],  # truncated for WS payload
            "assets": result.assets_covered,
            "generated_at": result.generated_at.isoformat(),
        },
    )

    await _notify_telegram(content=result.content, settings=settings)

    elapsed = (datetime.now(timezone.utc) - started_at).total_seconds()
    logger.info(f"MorningBriefingJob: completed in {elapsed:.1f}s")


async def _generate_briefing(*, engine, settings):
    from oracle.application.briefing.dtos import GenerateBriefingInput
    from oracle.application.briefing.generate_briefing import GenerateBriefingUseCase
    from oracle.infrastructure.ai.claude_adapter import ClaudeAdapter
    from oracle.infrastructure.database.connection import build_session_factory
    from oracle.infrastructure.database.repositories.trade_repository import PostgresTradeRepository

    session_factory = build_session_factory(engine)
    async with session_factory() as session:
        trade_repo = PostgresTradeRepository(session)
        ai_provider = ClaudeAdapter(settings)
        use_case = GenerateBriefingUseCase(trade_repository=trade_repo, ai_provider=ai_provider)
        return await use_case.execute(
            GenerateBriefingInput(assets=settings.BRIEFING_ASSETS)
        )


async def _notify_telegram(*, content: str, settings) -> None:
    if not (settings.TELEGRAM_BOT_TOKEN and settings.TELEGRAM_CHAT_ID):
        return
    try:
        from oracle.infrastructure.messaging.telegram_adapter import TelegramAdapter
        adapter = TelegramAdapter(
            bot_token=settings.TELEGRAM_BOT_TOKEN,
            chat_id=settings.TELEGRAM_CHAT_ID,
        )
        summary = f"📊 *Briefing Matinal Oracle*\n\n{content[:1000]}"
        await adapter.send_message(summary)
    except Exception as exc:
        logger.warning(f"MorningBriefingJob: Telegram notification failed — {exc}")

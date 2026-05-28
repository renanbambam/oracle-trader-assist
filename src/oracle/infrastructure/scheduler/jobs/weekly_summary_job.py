"""weekly_summary_job — automated weekly performance summary.

Runs every Monday at 08:00 (America/Sao_Paulo). Queries analytics for the
previous week, publishes to EventBus and optionally notifies via Telegram.
"""

from datetime import datetime, timedelta, timezone

from loguru import logger


async def run_weekly_summary(
    *,
    engine,
    settings,
    event_bus,
) -> None:
    """Entry point called by OracleScheduler."""
    started_at = datetime.now(timezone.utc)
    logger.info(f"WeeklySummaryJob: starting at {started_at.isoformat()}")

    try:
        summary = await _build_weekly_summary(engine=engine, started_at=started_at)
    except Exception as exc:
        logger.error(f"WeeklySummaryJob: summary generation failed — {exc}")
        return

    await event_bus.publish(
        channel="system",
        event="weekly_summary.generated",
        payload=summary,
    )

    await _notify_telegram(summary=summary, settings=settings)

    elapsed = (datetime.now(timezone.utc) - started_at).total_seconds()
    logger.info(f"WeeklySummaryJob: completed in {elapsed:.1f}s — {summary['trade_count']} trades processed")


async def _build_weekly_summary(*, engine, started_at: datetime) -> dict:
    from oracle.domain.trade.enums import TradeResult, TradeStatus
    from oracle.infrastructure.database.connection import build_session_factory
    from oracle.infrastructure.database.repositories.trade_repository import PostgresTradeRepository

    week_start = (started_at - timedelta(days=7)).replace(
        hour=0, minute=0, second=0, microsecond=0
    )

    session_factory = build_session_factory(engine)
    async with session_factory() as session:
        repo = PostgresTradeRepository(session)
        closed = await repo.get_by_status(TradeStatus.CLOSED)

    week_trades = [
        t for t in closed
        if t.closed_at and t.closed_at >= week_start
    ]

    if not week_trades:
        return {
            "period_start": week_start.isoformat(),
            "period_end": started_at.isoformat(),
            "trade_count": 0,
            "win_count": 0,
            "loss_count": 0,
            "win_rate": 0.0,
            "total_r": 0.0,
            "best_trade": None,
            "worst_trade": None,
        }

    wins = [t for t in week_trades if t.result == TradeResult.WIN]
    losses = [t for t in week_trades if t.result == TradeResult.LOSS]
    total_r = sum(t.r_realized or 0.0 for t in week_trades)
    win_rate = len(wins) / len(week_trades) if week_trades else 0.0

    r_values = [(t.r_realized or 0.0, t.asset, str(t.setup)) for t in week_trades]
    best = max(r_values, key=lambda x: x[0])
    worst = min(r_values, key=lambda x: x[0])

    return {
        "period_start": week_start.isoformat(),
        "period_end": started_at.isoformat(),
        "trade_count": len(week_trades),
        "win_count": len(wins),
        "loss_count": len(losses),
        "win_rate": round(win_rate, 4),
        "total_r": round(total_r, 2),
        "best_trade": {"r": best[0], "asset": best[1], "setup": best[2]},
        "worst_trade": {"r": worst[0], "asset": worst[1], "setup": worst[2]},
    }


async def _notify_telegram(*, summary: dict, settings) -> None:
    if not (settings.TELEGRAM_BOT_TOKEN and settings.TELEGRAM_CHAT_ID):
        return
    try:
        from oracle.infrastructure.messaging.telegram_adapter import TelegramAdapter

        tc = summary["trade_count"]
        wr = summary["win_rate"] * 100
        tr = summary["total_r"]
        msg = (
            f"📈 *Resumo Semanal Oracle*\n\n"
            f"Trades: {tc} | Win rate: {wr:.1f}% | Total R: {tr:+.2f}R\n"
            f"Período: {summary['period_start'][:10]} → {summary['period_end'][:10]}"
        )
        adapter = TelegramAdapter(
            bot_token=settings.TELEGRAM_BOT_TOKEN,
            chat_id=settings.TELEGRAM_CHAT_ID,
        )
        await adapter.send_message(msg)
    except Exception as exc:
        logger.warning(f"WeeklySummaryJob: Telegram notification failed — {exc}")

"""GenerateBriefingUseCase — generates morning briefing via Claude."""

import re
from datetime import datetime, timezone

from oracle.application.briefing.dtos import BriefingOutput, GenerateBriefingInput
from oracle.domain.trade.enums import TradeStatus
from prompts.briefing.morning_briefing import build_prompt
from prompts.system.oracle_system_v1 import TEMPLATE as SYSTEM_PROMPT


class GenerateBriefingUseCase:
    def __init__(
        self,
        trade_repository,
        ai_provider,
        load_context_uc=None,  # LoadContextUseCase — optional history injection
    ) -> None:
        self._trade_repo = trade_repository
        self._ai = ai_provider
        self._load_ctx = load_context_uc

    async def execute(self, data: GenerateBriefingInput) -> BriefingOutput:
        assets = data.assets[: data.max_assets]
        now = datetime.now(timezone.utc)
        date_str = now.strftime("%d/%m/%Y")

        trades_summary = ""
        if data.include_recent_trades:
            trades_summary = await self._build_trades_summary(assets, now)

        memory_context = ""
        if self._load_ctx is not None:
            parts = []
            for asset in assets:
                hist = await self._load_ctx.get_history_for_prompt(asset, max_turns=5)
                if hist:
                    parts.append(hist)
            memory_context = "\n\n".join(parts)

        prompt = build_prompt(
            assets=assets,
            trades_summary=trades_summary,
            memory_context=memory_context,
            date=date_str,
        )

        try:
            content = await self._ai.complete(prompt=prompt, system=SYSTEM_PROMPT)
        except Exception as exc:
            raise RuntimeError(f"AI provider failed: {exc}") from exc

        return BriefingOutput(
            content=content,
            assets_covered=assets,
            key_levels=_extract_key_levels(content, assets),
            upcoming_events=[],
            recent_trade_context=trades_summary,
            generated_at=now,
        )

    async def _build_trades_summary(self, assets: list[str], now: datetime) -> str:
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        closed = await self._trade_repo.get_by_status(TradeStatus.CLOSED)

        today_trades = [
            t for t in closed
            if t.closed_at and t.closed_at >= today_start
            and (not assets or t.asset in assets)
        ]

        if not today_trades:
            return "Nenhum trade fechado hoje."

        lines = []
        for t in today_trades[:10]:
            r_str = f"{t.r_realized:+.2f}R" if t.r_realized is not None else "?"
            result = str(t.result) if t.result else "?"
            lines.append(f"  {t.asset} {t.direction} {t.setup} → {result} {r_str}")

        return "\n".join(lines)


def _extract_key_levels(content: str, assets: list[str]) -> dict[str, dict[str, float]]:
    """Parse Claude's briefing text to extract support/resistance per asset."""
    result: dict[str, dict[str, float]] = {}
    num_pat = r"([\d]{1,7}[.,][\d]{2,4})"

    for sym in assets:
        escaped = re.escape(sym)
        # Find the section of text that mentions this asset (up to 800 chars ahead)
        section_re = re.compile(
            rf"(?:^|\n)[^\n]*{escaped}[\s\S]{{0,800}}?(?=\n[A-Z]{{3,6}}[\d]?\b|\Z)",
            re.IGNORECASE | re.MULTILINE,
        )
        match = section_re.search(content)
        section = match.group(0) if match else content

        sup_match = re.search(rf"[Ss]uporte[^\d]{{0,30}}{num_pat}", section)
        res_match = re.search(rf"[Rr]esist[êe]ncia[^\d]{{0,30}}{num_pat}", section)

        sup = float(sup_match.group(1).replace(",", ".")) if sup_match else None
        res = float(res_match.group(1).replace(",", ".")) if res_match else None

        if sup is not None or res is not None:
            result[sym] = {}
            if sup is not None:
                result[sym]["support"] = sup
            if res is not None:
                result[sym]["resistance"] = res

    return result

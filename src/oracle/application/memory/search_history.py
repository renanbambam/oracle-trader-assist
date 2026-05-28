"""SearchHistoryUseCase — retrieves similar memory records for prompt enrichment."""

from oracle.application.memory.dtos import (
    SearchHistoryInput,
    SearchHistoryOutput,
    SearchHistoryRecord,
)
from oracle.domain.memory.contracts import MemoryStore


class SearchHistoryUseCase:
    """Queries past MemoryRecords by asset + setup type for context injection."""

    def __init__(self, memory_store: MemoryStore) -> None:
        self._store = memory_store

    async def execute(self, data: SearchHistoryInput) -> SearchHistoryOutput:
        records = await self._store.search_similar(
            asset=data.asset,
            setup_type=data.setup_type,
            limit=data.limit,
        )

        output_records = [
            SearchHistoryRecord(
                id=r.id,
                asset=r.asset,
                setup_type=r.setup_type,
                content=r.content,
                relevance_score=r.relevance_score,
                created_at=r.created_at,
            )
            for r in records
        ]

        prompt_context = _format_for_prompt(output_records, data.asset, data.setup_type)
        return SearchHistoryOutput(records=output_records, prompt_context=prompt_context)


def _format_for_prompt(
    records: list[SearchHistoryRecord],
    asset: str,
    setup_type: str,
) -> str:
    if not records:
        return ""
    lines = [f"HISTÓRICO SIMILAR — {asset} / {setup_type}:"]
    for r in records:
        snippet = r.content[:200] + "..." if len(r.content) > 200 else r.content
        lines.append(f"- {snippet}")
    return "\n".join(lines)

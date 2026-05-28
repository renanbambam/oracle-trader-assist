"""Analysis domain — contracts (protocols/interfaces).

AIProvider abstracts Claude (and any future LLM).
AnalysisRepository abstracts the persistence layer.
"""

from collections.abc import AsyncGenerator
from typing import Protocol, runtime_checkable
from uuid import UUID

from oracle.domain.analysis.entities import ChartAnalysis


@runtime_checkable
class AIProvider(Protocol):
    """Port for LLM inference.

    Implemented by ClaudeAdapter in infrastructure/ai/.
    The prompt caching strategy is the adapter's responsibility,
    not the application layer's.
    """

    async def complete(
        self,
        prompt: str,
        system: str,
        image_b64: str | None = None,
    ) -> str: ...

    def stream(
        self,
        messages: list[dict],
        system: str,
    ) -> AsyncGenerator[str, None]: ...

    def stream_message(
        self,
        message: str,
        system: str,
    ) -> AsyncGenerator[str, None]: ...

    async def count_tokens(self, text: str) -> int: ...


@runtime_checkable
class AnalysisRepository(Protocol):
    """Port for persisting and querying analysis records."""

    async def save(self, analysis: ChartAnalysis) -> ChartAnalysis: ...

    async def get_by_id(self, analysis_id: UUID) -> ChartAnalysis | None: ...

    async def get_by_session(
        self,
        session_id: UUID,
        limit: int = 10,
    ) -> list[ChartAnalysis]: ...

    async def get_by_asset(
        self,
        asset: str,
        limit: int = 20,
    ) -> list[ChartAnalysis]: ...

"""Memory domain — value objects."""

from pydantic import Field

from oracle.domain.shared.base import ValueObject


class TokenBudget(ValueObject):
    """Allocation policy for Claude context window tokens.

    These defaults are calibrated for Claude Sonnet (200k context).
    Adjust for Haiku/Opus as needed via Settings injection.
    """

    max_total: int = Field(default=150_000, gt=0)
    system_reserve: int = Field(default=5_000, gt=0)
    context_reserve: int = Field(default=10_000, gt=0)
    history_budget: int = Field(default=80_000, gt=0)
    current_analysis_budget: int = Field(default=55_000, gt=0)

    @property
    def available_for_history(self) -> int:
        return self.history_budget

    @property
    def total_overhead(self) -> int:
        """Tokens permanently reserved (system + response reserve)."""
        return self.system_reserve + self.context_reserve


class ContextWindow(ValueObject):
    """Current state of a context session's token usage."""

    total_budget: int = Field(gt=0)
    used_tokens: int = Field(ge=0)
    turns_count: int = Field(ge=0)
    was_trimmed: bool = False
    trim_count: int = Field(default=0, ge=0)

    @property
    def remaining_tokens(self) -> int:
        return max(0, self.total_budget - self.used_tokens)

    @property
    def usage_pct(self) -> float:
        if self.total_budget == 0:
            return 0.0
        return round(self.used_tokens / self.total_budget * 100, 1)

    @property
    def is_near_limit(self) -> bool:
        """True when usage exceeds 80% — triggers proactive trimming."""
        return self.usage_pct >= 80.0

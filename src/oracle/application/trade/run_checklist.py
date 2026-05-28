"""RunChecklistUseCase — validates a pending trade against anti-FOMO rules."""

from datetime import datetime

from oracle.application.trade.dtos import (
    ChecklistInput,
    ChecklistItemOutput,
    ChecklistOutput,
)
from oracle.domain.trade.services import ChecklistValidator


class RunChecklistUseCase:
    """Pure validation — no DB, no AI. Delegates to ChecklistValidator domain service."""

    _validator = ChecklistValidator()

    def execute(
        self,
        data: ChecklistInput,
        check_time: datetime | None = None,
    ) -> ChecklistOutput:
        result = self._validator.validate(
            emotional_state=str(data.emotional_state),
            rr_ratio=data.rr_ratio,
            today_losses=data.today_losses,
            setup=data.setup,
            check_time=check_time,
        )

        return ChecklistOutput(
            items=[
                ChecklistItemOutput(
                    rule=item.rule,
                    passed=item.passed,
                    blocking=item.blocking,
                    message=item.message,
                )
                for item in result.items
            ],
            passed_count=result.passed_count,
            total_count=result.total_count,
            verdict=result.verdict,
        )

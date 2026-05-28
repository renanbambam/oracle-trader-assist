"""SendMessageUseCase — streams Claude responses token-by-token via EventBus."""

from oracle.core.ports import EventBus
from prompts.system.oracle_system_v1 import TEMPLATE as SYSTEM_PROMPT


class SendMessageUseCase:
    def __init__(self, ai_provider, event_bus: EventBus) -> None:
        self._ai = ai_provider
        self._event_bus = event_bus

    async def execute(self, message: str) -> None:
        """Stream a response to `message`, publishing each token as ai.token on ai_stream."""
        try:
            async for token in self._ai.stream_message(message, SYSTEM_PROMPT):
                await self._event_bus.publish(
                    channel="ai_stream",
                    event="ai.token",
                    payload={"token": token},
                )
        finally:
            await self._event_bus.publish(
                channel="ai_stream",
                event="ai.stream_end",
                payload={},
            )

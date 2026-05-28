"""Cross-cutting port definitions — abstract interfaces for infrastructure adapters.

Domain and Application layers import these Protocols.
Infrastructure provides the concrete implementations.

This is the "ports" side of Ports & Adapters (Hexagonal Architecture).

Domain-specific ports live in their bounded context's contracts.py:
  - domain/market/contracts.py       → MarketDataProvider
  - domain/analysis/contracts.py     → AIProvider, AnalysisRepository
  - domain/trade/contracts.py        → TradeRepository
  - domain/memory/contracts.py       → MemoryStore
  - domain/replay/contracts.py       → ReplayRepository
"""

from typing import Any, AsyncGenerator, Protocol, runtime_checkable


@runtime_checkable
class EventBus(Protocol):
    """Port for the pub/sub event bus.

    Implemented by RedisEventBus in infrastructure/redis/event_bus.py.
    Application layer uses this interface — never the concrete class.

    channel: logical WebSocket channel name ("analysis", "trading", etc.)
    event:   event type string ("analysis.completed", "trade.opened", etc.)
    payload: serialisable dict with event data — must be JSON-safe.
    """

    async def publish(
        self,
        channel: str,
        event: str,
        payload: dict[str, Any],
    ) -> None: ...

    def subscribe(
        self,
        channels: list[str],
    ) -> AsyncGenerator[dict[str, Any], None]: ...


@runtime_checkable
class NotificationProvider(Protocol):
    """Port for push notifications to the trader.

    Implemented by TelegramAdapter and TTSAdapter in infrastructure/messaging/.
    Both are Phase 2 features — this port exists to keep the application layer
    decoupled from the delivery mechanism.
    """

    async def send(self, message: str, priority: str = "normal") -> None: ...

    async def send_alert(self, title: str, body: str) -> None: ...

    @property
    def is_available(self) -> bool: ...

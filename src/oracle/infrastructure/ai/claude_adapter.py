"""ClaudeAdapter — implements AIProvider using the Anthropic SDK.

Prompt caching strategy:
  System prompt is marked cache_control: ephemeral (5-min TTL in Anthropic API).
  This reduces billing on repeated analysis calls with the same system prompt.

Streaming:
  stream() yields raw text tokens as they arrive from the API.
  Callers publish AIStreamToken events to the WebSocket channel.
"""

from collections.abc import AsyncGenerator

import anthropic
from loguru import logger

from oracle.config.settings import Settings


class ClaudeAdapter:
    """Anthropic Claude implementation of AIProvider."""

    def __init__(self, settings: Settings) -> None:
        self._client = anthropic.AsyncAnthropic(api_key=settings.ANTHROPIC_API_KEY)
        self._model = settings.CLAUDE_MODEL
        self._max_tokens = settings.CLAUDE_MAX_TOKENS

    async def complete(
        self,
        prompt: str,
        system: str,
        image_b64: str | None = None,
    ) -> str:
        messages = _build_messages(prompt, image_b64)
        system_blocks = _system_with_cache(system)

        response = await self._client.messages.create(
            model=self._model,
            max_tokens=self._max_tokens,
            system=system_blocks,
            messages=messages,
        )
        content = response.content[0].text
        _log_usage(response.usage, self._model)
        return content

    async def stream(
        self,
        messages: list[dict],
        system: str,
    ) -> AsyncGenerator[str, None]:
        system_blocks = _system_with_cache(system)

        async with self._client.messages.stream(
            model=self._model,
            max_tokens=self._max_tokens,
            system=system_blocks,
            messages=messages,
        ) as stream:
            async for text in stream.text_stream:
                yield text

    async def stream_message(
        self,
        message: str,
        system: str,
    ) -> AsyncGenerator[str, None]:
        async for token in self.stream([{"role": "user", "content": message}], system):
            yield token

    async def count_tokens(self, text: str) -> int:
        response = await self._client.messages.count_tokens(
            model=self._model,
            messages=[{"role": "user", "content": text}],
        )
        return response.input_tokens


def _build_messages(prompt: str, image_b64: str | None) -> list[dict]:
    if image_b64 is None:
        return [{"role": "user", "content": prompt}]

    return [
        {
            "role": "user",
            "content": [
                {
                    "type": "image",
                    "source": {
                        "type": "base64",
                        "media_type": "image/png",
                        "data": image_b64,
                    },
                },
                {"type": "text", "text": prompt},
            ],
        }
    ]


def _system_with_cache(system: str) -> list[dict]:
    return [
        {
            "type": "text",
            "text": system,
            "cache_control": {"type": "ephemeral"},
        }
    ]


def _log_usage(usage: object, model: str) -> None:
    try:
        logger.debug(
            f"Claude usage — model={model} "
            f"input={usage.input_tokens} "  # type: ignore[attr-defined]
            f"output={usage.output_tokens} "  # type: ignore[attr-defined]
            f"cached={getattr(usage, 'cache_read_input_tokens', 0)}"
        )
    except Exception:
        pass

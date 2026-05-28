"""TelegramAdapter — sends notifications via Telegram Bot API.

Uses httpx (already in the stack) — no additional library required.
Silently skips if bot_token or chat_id are not configured.

Bot API reference: https://core.telegram.org/bots/api#sendmessage
"""

import httpx
from loguru import logger

_TELEGRAM_API = "https://api.telegram.org/bot{token}/sendMessage"
_MAX_MESSAGE_LENGTH = 4096


class TelegramAdapter:
    """Sends text messages to a Telegram chat via the Bot API."""

    def __init__(self, bot_token: str, chat_id: str) -> None:
        self._bot_token = bot_token
        self._chat_id = chat_id

    async def send_message(self, text: str, parse_mode: str = "Markdown") -> bool:
        """Send a text message.

        Returns True on success, False if not configured or on error.
        Never raises — failures are logged as warnings.
        """
        if not self._bot_token or not self._chat_id:
            logger.debug("TelegramAdapter: not configured — skipping notification")
            return False

        truncated = text[:_MAX_MESSAGE_LENGTH]
        url = _TELEGRAM_API.format(token=self._bot_token)
        payload = {
            "chat_id": self._chat_id,
            "text": truncated,
            "parse_mode": parse_mode,
            "disable_web_page_preview": True,
        }

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.post(url, json=payload)
                resp.raise_for_status()
                data = resp.json()

            if data.get("ok"):
                logger.debug(f"TelegramAdapter: message sent (chat_id={self._chat_id})")
                return True

            logger.warning(f"TelegramAdapter: API returned ok=false — {data}")
            return False

        except Exception as exc:
            logger.warning(f"TelegramAdapter: send failed — {exc}")
            return False

    async def send_alert(self, title: str, body: str) -> bool:
        """Convenience wrapper that formats a titled alert message."""
        text = f"*{title}*\n\n{body}"
        return await self.send_message(text)

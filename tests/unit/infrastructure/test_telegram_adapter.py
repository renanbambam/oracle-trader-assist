"""Unit tests for TelegramAdapter — mocked HTTP, no real API calls."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from oracle.infrastructure.messaging.telegram_adapter import TelegramAdapter


def _patch_httpx(json_data: dict, status_code: int = 200):
    mock_resp = MagicMock()
    mock_resp.status_code = status_code
    mock_resp.json.return_value = json_data
    mock_resp.raise_for_status = MagicMock()
    mock_client = AsyncMock()
    mock_client.post = AsyncMock(return_value=mock_resp)
    mock_ctx = MagicMock()
    mock_ctx.__aenter__ = AsyncMock(return_value=mock_client)
    mock_ctx.__aexit__ = AsyncMock(return_value=False)
    return patch("httpx.AsyncClient", return_value=mock_ctx)


async def test_send_message_returns_true_on_success():
    adapter = TelegramAdapter(bot_token="bot:TOKEN", chat_id="123")
    with _patch_httpx({"ok": True, "result": {"message_id": 1}}):
        result = await adapter.send_message("Hello from Oracle")
    assert result is True


async def test_send_message_returns_false_when_unconfigured():
    adapter = TelegramAdapter(bot_token="", chat_id="")
    result = await adapter.send_message("test")
    assert result is False


async def test_send_message_returns_false_on_api_error():
    adapter = TelegramAdapter(bot_token="bot:TOKEN", chat_id="123")
    with _patch_httpx({"ok": False, "description": "Unauthorized"}):
        result = await adapter.send_message("test")
    assert result is False


async def test_send_message_truncates_long_text():
    adapter = TelegramAdapter(bot_token="bot:TOKEN", chat_id="123")
    long_text = "X" * 5000

    captured_payload: dict = {}

    async def _fake_post(url, json=None, **kwargs):
        captured_payload.update(json or {})
        resp = MagicMock()
        resp.json.return_value = {"ok": True}
        resp.raise_for_status = MagicMock()
        return resp

    mock_client = AsyncMock()
    mock_client.post = AsyncMock(side_effect=_fake_post)
    mock_ctx = MagicMock()
    mock_ctx.__aenter__ = AsyncMock(return_value=mock_client)
    mock_ctx.__aexit__ = AsyncMock(return_value=False)

    with patch("httpx.AsyncClient", return_value=mock_ctx):
        await adapter.send_message(long_text)

    assert len(captured_payload.get("text", "")) <= 4096


async def test_send_message_handles_http_exception():
    adapter = TelegramAdapter(bot_token="bot:TOKEN", chat_id="123")
    mock_client = AsyncMock()
    mock_client.post = AsyncMock(side_effect=Exception("connection refused"))
    mock_ctx = MagicMock()
    mock_ctx.__aenter__ = AsyncMock(return_value=mock_client)
    mock_ctx.__aexit__ = AsyncMock(return_value=False)

    with patch("httpx.AsyncClient", return_value=mock_ctx):
        result = await adapter.send_message("test")

    assert result is False


async def test_send_alert_formats_title_and_body():
    adapter = TelegramAdapter(bot_token="bot:TOKEN", chat_id="123")
    captured: dict = {}

    async def _send(text, **kw):
        captured["text"] = text
        return True

    adapter.send_message = _send  # type: ignore[method-assign]
    await adapter.send_alert("Título", "Corpo da mensagem")

    assert "Título" in captured["text"]
    assert "Corpo da mensagem" in captured["text"]

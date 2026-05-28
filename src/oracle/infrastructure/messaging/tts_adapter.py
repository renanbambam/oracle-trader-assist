"""TTSAdapter — text-to-speech notifications.

Strategy:
  1. Windows: use SAPI via PowerShell (no extra library needed)
  2. Fallback: log the text at INFO level (silent mode)

The adapter is fire-and-forget — it never raises. Failures are logged
and the calling code continues normally.
"""

import asyncio
import platform
import subprocess

from loguru import logger


class TTSAdapter:
    """Speaks text aloud using the platform's native TTS engine."""

    def __init__(self, enabled: bool = True, rate: int = 180) -> None:
        self._enabled = enabled
        self._rate = rate  # words per minute for SAPI
        self._is_windows = platform.system() == "Windows"

    async def speak(self, text: str) -> None:
        """Speak text asynchronously.

        Runs in a thread executor so the event loop is not blocked.
        """
        if not self._enabled:
            return
        await asyncio.get_running_loop().run_in_executor(None, self._speak_sync, text)

    def _speak_sync(self, text: str) -> None:
        if self._is_windows:
            self._speak_windows(text)
        else:
            logger.info(f"TTS (no engine): {text}")

    def _speak_windows(self, text: str) -> None:
        safe_text = text.replace('"', "'").replace("\n", " ").replace("*", "")
        script = (
            f'Add-Type -AssemblyName System.Speech; '
            f'$s = New-Object System.Speech.Synthesis.SpeechSynthesizer; '
            f'$s.Rate = {self._rate - 100}; '
            f'$s.Speak("{safe_text}")'
        )
        try:
            subprocess.run(
                ["powershell", "-NonInteractive", "-Command", script],
                timeout=30,
                capture_output=True,
                check=False,
            )
        except Exception as exc:
            logger.warning(f"TTSAdapter: Windows SAPI failed — {exc}")
            logger.info(f"TTS (fallback): {text}")

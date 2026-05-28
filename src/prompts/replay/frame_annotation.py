"""Replay frame annotation prompt — Claude comments on a single OHLCV bar."""

PROMPT_NAME = "frame_annotation"
PROMPT_VERSION = "1.0.0"

TEMPLATE = """Analise este candle de replay histórico e forneça um comentário educativo objetivo:

ATIVO: {asset} | TIMEFRAME: {timeframe}
FRAME #{frame_index} — {timestamp}

OHLCV:
  Abertura:  {open}
  Máxima:    {high}
  Mínima:    {low}
  Fechamento: {close}
  Volume:    {volume}
  Contexto de volume: {volume_context}

{annotations_section}

Responda em 2-3 linhas diretas:
- O que este candle indica sobre a dinâmica do mercado neste momento?
- Há algum padrão ou sinal técnico relevante?
- Qual seria a ação recomendada (observar / considerar long / considerar short / aguardar confirmação)?
""".strip()


def build_prompt(
    asset: str,
    timeframe: str,
    frame_index: int,
    timestamp: str,
    open: float,
    high: float,
    low: float,
    close: float,
    volume: float,
    volume_context: str = "at_avg",
    annotations: list[str] | None = None,
) -> str:
    ann_lines = "\n".join(f"- {a}" for a in (annotations or []))
    annotations_section = f"ANOTAÇÕES:\n{ann_lines}" if ann_lines else ""
    return TEMPLATE.format(
        asset=asset,
        timeframe=timeframe,
        frame_index=frame_index,
        timestamp=timestamp,
        open=open,
        high=high,
        low=low,
        close=close,
        volume=volume,
        volume_context=volume_context,
        annotations_section=annotations_section,
    )

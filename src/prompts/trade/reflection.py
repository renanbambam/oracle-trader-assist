"""Post-trade reflection prompt — Claude analyzes a completed trade.

Triggered after a trade is closed. Produces a structured reflection that
is stored in MemoryRecord for future context injection.
"""

PROMPT_NAME = "trade_reflection"
PROMPT_VERSION = "1.0.0"

TEMPLATE = """Analise este trade concluído e forneça uma reflexão objetiva:

TRADE:
Ativo: {asset} | Direção: {direction} | Timeframe: {timeframe}
Setup: {setup}
Entrada: {entry} | Stop: {stop} | Alvo: {target}
Saída: {exit_price} | Resultado: {result} | R realizado: {r_realized:+.2f}R
Estado emocional: {emotional_state}
{notes_section}

Responda EXATAMENTE neste formato:

## O QUE FUNCIONOU
[1-2 linhas sobre o que estava correto na análise]

## O QUE FALHOU
[1-2 linhas sobre o que não funcionou ou poderia ter sido melhor]

## LIÇÃO PRINCIPAL
[1 linha — a lição mais importante deste trade]

## PADRÃO IDENTIFICADO
Setup: [categoria do setup — breakout/reversal/trend_continuation/range/custom]
Contexto: [condição de mercado que favoreceu ou prejudicou]

## SCORE DE EXECUÇÃO
[0-10] — [justificativa em 1 linha comparando planejamento vs execução]
""".strip()


def build_prompt(
    asset: str,
    direction: str,
    timeframe: str,
    setup: str,
    entry: float,
    stop: float,
    target: float,
    exit_price: float,
    result: str,
    r_realized: float,
    emotional_state: str,
    notes: str | None = None,
) -> str:
    notes_section = f"Notas: {notes}" if notes else ""
    return TEMPLATE.format(
        asset=asset,
        direction=direction,
        timeframe=timeframe,
        setup=setup,
        entry=entry,
        stop=stop,
        target=target,
        exit_price=exit_price,
        result=result,
        r_realized=r_realized,
        emotional_state=emotional_state,
        notes_section=notes_section,
    )

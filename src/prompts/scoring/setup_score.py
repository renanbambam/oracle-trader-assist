"""Setup scoring prompt — qualitative validation of a numerical confidence score.

The numerical score is computed deterministically from factor weights.
This prompt asks Claude to validate the score and provide qualitative context
that the formula cannot capture (narrative coherence, hidden risks, etc.).
"""

PROMPT_NAME = "setup_score"
PROMPT_VERSION = "1.0.0"

WEIGHTS: dict[str, float] = {
    "trend_alignment": 0.25,
    "setup_quality": 0.25,
    "historical_match": 0.20,
    "macro_context": 0.15,
    "market_quality": 0.10,
    "emotional_state": 0.05,
}

TEMPLATE = """Avalie o setup de trading com os seguintes scores (0.0 = mínimo, 1.0 = máximo):

Alinhamento de tendência: {trend_alignment:.0%} (peso 25%)
Qualidade do setup: {setup_quality:.0%} (peso 25%)
Match histórico: {historical_match:.0%} (peso 20%)
Contexto macro: {macro_context:.0%} (peso 15%)
Qualidade do mercado: {market_quality:.0%} (peso 10%)
Estado emocional: {emotional_state:.0%} (peso 5%)

Score ponderado calculado: {weighted_score:.0f}/100

Responda APENAS:
VALIDADO: [Sim/Não] — [justificativa em 1 linha]
AJUSTE: [+X / -X / 0] — [motivo se houver ajuste ao score numérico]
ALERTA: [risco qualitativo não capturado pelo score, ou "Nenhum"]
""".strip()


def build_prompt(
    trend_alignment: float,
    setup_quality: float,
    historical_match: float,
    macro_context: float,
    market_quality: float,
    emotional_state: float,
) -> str:
    factors = dict(
        trend_alignment=trend_alignment,
        setup_quality=setup_quality,
        historical_match=historical_match,
        macro_context=macro_context,
        market_quality=market_quality,
        emotional_state=emotional_state,
    )
    weighted_score = sum(factors[k] * WEIGHTS[k] for k in WEIGHTS) * 100

    return TEMPLATE.format(**factors, weighted_score=weighted_score)


def compute_weighted_score(
    trend_alignment: float,
    setup_quality: float,
    historical_match: float,
    macro_context: float,
    market_quality: float,
    emotional_state: float,
) -> float:
    factors = dict(
        trend_alignment=trend_alignment,
        setup_quality=setup_quality,
        historical_match=historical_match,
        macro_context=macro_context,
        market_quality=market_quality,
        emotional_state=emotional_state,
    )
    return round(sum(factors[k] * WEIGHTS[k] for k in WEIGHTS) * 100, 1)

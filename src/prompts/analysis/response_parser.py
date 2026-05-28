"""Parse Claude's structured analysis response into domain primitives.

The parser is intentionally lenient — if a section is missing or
malformed it returns a safe default rather than crashing.
"""

import re

from oracle.domain.analysis.enums import (
    AnalysisStatus,
    ConfidenceLabel,
    Suggestion,
    TrendDirection,
    TrendStrength,
)
from oracle.domain.analysis.value_objects import ConfidenceScore


class ParsedAnalysis:
    """Intermediate result from parsing Claude's raw text response."""

    __slots__ = (
        "suggestion", "confidence", "trend_direction", "trend_strength",
        "support_level", "resistance_level", "setup_description",
        "reasoning", "risks", "bull_scenario", "bear_scenario",
    )

    def __init__(self) -> None:
        self.suggestion: Suggestion = Suggestion.REVISAR_CONTEXTO
        self.confidence: ConfidenceScore = ConfidenceScore.from_value(0.0, "parse error")
        self.trend_direction: TrendDirection = TrendDirection.LATERAL
        self.trend_strength: TrendStrength = TrendStrength.FRACA
        self.support_level: float | None = None
        self.resistance_level: float | None = None
        self.setup_description: str | None = None
        self.reasoning: str | None = None
        self.risks: list[str] = []
        self.bull_scenario: str | None = None
        self.bear_scenario: str | None = None


def parse_analysis_response(raw: str) -> ParsedAnalysis:
    result = ParsedAnalysis()
    sections = _split_sections(raw)

    result.trend_direction, result.trend_strength = _parse_trend(sections.get("TENDÊNCIA", ""))
    result.support_level, result.resistance_level = _parse_levels(sections.get("ESTRUTURA DE MERCADO", ""))
    result.setup_description = _clean(sections.get("SETUP IDENTIFICADO", "")) or None
    result.reasoning = _clean(sections.get("RACIOCÍNIO", "")) or None
    result.suggestion = _parse_suggestion(sections.get("SUGESTÃO", ""))
    result.confidence = _parse_confidence(sections.get("CONFIDENCE SCORE", ""))
    result.risks = _parse_risks(sections.get("RISCOS E INVALIDADORES", ""))
    result.bull_scenario, result.bear_scenario = _parse_scenarios(sections.get("CENÁRIOS ALTERNATIVOS", ""))

    return result


# ── Section splitting ──────────────────────────────────────────────────────────

def _split_sections(text: str) -> dict[str, str]:
    pattern = r"##\s+([A-ZÁÉÍÓÚÃÕÇ &]+)"
    parts = re.split(pattern, text)
    sections: dict[str, str] = {}
    for i in range(1, len(parts) - 1, 2):
        title = parts[i].strip()
        body = parts[i + 1].strip() if i + 1 < len(parts) else ""
        sections[title] = body
    return sections


# ── Individual section parsers ─────────────────────────────────────────────────

def _parse_trend(text: str) -> tuple[TrendDirection, TrendStrength]:
    direction = TrendDirection.LATERAL
    strength = TrendStrength.FRACA

    upper = text.upper()
    if "BULLISH" in upper:
        direction = TrendDirection.BULLISH
    elif "BEARISH" in upper:
        direction = TrendDirection.BEARISH

    if "FORTE" in upper:
        strength = TrendStrength.FORTE
    elif "MODERADA" in upper:
        strength = TrendStrength.MODERADA

    return direction, strength


def _parse_levels(text: str) -> tuple[float | None, float | None]:
    support = _extract_price(r"[Ss]uporte[:\s]+([0-9]+[.,][0-9]+)", text)
    resistance = _extract_price(r"[Rr]esist[êe]ncia[:\s]+([0-9]+[.,][0-9]+)", text)
    return support, resistance


def _parse_suggestion(text: str) -> Suggestion:
    upper = text.upper()
    if "NÃO OPERAR" in upper or "NAO OPERAR" in upper:
        return Suggestion.NAO_OPERAR
    if "OPERAR" in upper:
        return Suggestion.OPERAR
    if "AGUARDAR" in upper:
        return Suggestion.AGUARDAR
    return Suggestion.REVISAR_CONTEXTO


def _parse_confidence(text: str) -> ConfidenceScore:
    match = re.search(r"(\d{1,3})%?\s*[—–-]\s*(.+)", text)
    if match:
        try:
            score = float(match.group(1))
            justification = match.group(2).strip()
            return ConfidenceScore.from_value(min(score, 100.0), justification)
        except (ValueError, Exception):
            pass
    num = re.search(r"(\d{1,3})", text)
    if num:
        try:
            return ConfidenceScore.from_value(float(num.group(1)), text[:120])
        except Exception:
            pass
    return ConfidenceScore.from_value(0.0, "não foi possível extrair confidence score")


def _parse_risks(text: str) -> list[str]:
    items = re.findall(r"[-•]\s*(.+)", text)
    return [item.strip() for item in items if item.strip()][:5]


def _parse_scenarios(text: str) -> tuple[str | None, str | None]:
    bull = re.search(r"[Bb]ull[:\s]+(.+)", text)
    bear = re.search(r"[Bb]ear[:\s]+(.+)", text)
    return (
        bull.group(1).strip() if bull else None,
        bear.group(1).strip() if bear else None,
    )


# ── Helpers ────────────────────────────────────────────────────────────────────

def _extract_price(pattern: str, text: str) -> float | None:
    m = re.search(pattern, text)
    if m:
        try:
            return float(m.group(1).replace(",", "."))
        except ValueError:
            pass
    return None


def _clean(text: str) -> str:
    return text.strip()

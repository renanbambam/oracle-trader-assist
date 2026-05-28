"""Analysis domain — enumerations."""

from enum import StrEnum


class Suggestion(StrEnum):
    """AI trade suggestion — the primary decision output."""
    OPERAR = "OPERAR"
    AGUARDAR = "AGUARDAR"
    NAO_OPERAR = "NAO_OPERAR"
    REVISAR_CONTEXTO = "REVISAR_CONTEXTO"


class ConfidenceLabel(StrEnum):
    MUITO_BAIXA = "MUITO_BAIXA"
    BAIXA = "BAIXA"
    MODERADA = "MODERADA"
    ALTA = "ALTA"
    MUITO_ALTA = "MUITO_ALTA"


class TrendDirection(StrEnum):
    BULLISH = "BULLISH"
    BEARISH = "BEARISH"
    LATERAL = "LATERAL"


class TrendStrength(StrEnum):
    FRACA = "FRACA"
    MODERADA = "MODERADA"
    FORTE = "FORTE"


class AnalysisStatus(StrEnum):
    PENDING = "pending"
    COMPLETED = "completed"
    FAILED = "failed"

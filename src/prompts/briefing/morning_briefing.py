"""Morning briefing prompt — aggregates day context for Claude."""

PROMPT_NAME = "morning_briefing"
PROMPT_VERSION = "1.0.0"

TEMPLATE = """BRIEFING MATINAL — {date}
ATIVOS MONITORADOS: {assets_str}

TRADES REALIZADOS HOJE:
{trades_summary}

CONTEXTO DA SESSÃO:
{memory_context}

Gere um briefing matinal em português (máximo 400 palavras) com:
1. Avaliação dos trades já realizados (se houver) — resultados, R realizado, padrões
2. Principais níveis técnicos a monitorar para cada ativo
3. Alertas de risco e pontos de atenção para a sessão
4. Recomendação geral para o restante do dia

Seja direto e objetivo. Não repita dados já fornecidos, apenas analise e conclua.
""".strip()


def build_prompt(
    assets: list[str],
    trades_summary: str,
    memory_context: str,
    date: str,
) -> str:
    assets_str = ", ".join(assets) if assets else "nenhum especificado"
    return TEMPLATE.format(
        date=date,
        assets_str=assets_str,
        trades_summary=trades_summary or "Nenhum trade realizado ainda hoje.",
        memory_context=memory_context or "Sem histórico de sessão disponível.",
    )

"""Prompt for full chart analysis — technical + contextual."""

PROMPT_NAME = "chart_analysis"
PROMPT_VERSION = "1.0.0"

TEMPLATE = """Analise o gráfico do ativo {asset} no timeframe {timeframe}.

{screenshot_instruction}

DADOS ADICIONAIS:
{context_block}

Responda EXATAMENTE neste formato (sem texto fora dele):

## TENDÊNCIA
[BULLISH/BEARISH/LATERAL] — força: [FRACA/MODERADA/FORTE]

## ESTRUTURA DE MERCADO
Suporte: [nível ou N/A] | Resistência: [nível ou N/A]

## SETUP IDENTIFICADO
[Descrição técnica objetiva em 1-3 linhas]

## RACIOCÍNIO
[3-5 linhas cruzando gráfico + contexto + histórico disponível]

## SUGESTÃO
[OPERAR / AGUARDAR / NÃO OPERAR / REVISAR CONTEXTO]
Motivo: [1-2 linhas diretas]

## CONFIDENCE SCORE
[número 0-100]% — [justificativa em 1 linha]

## RISCOS E INVALIDADORES
- [risco 1]
- [risco 2]

## CENÁRIOS ALTERNATIVOS
Bull: [cenário se preço subir]
Bear: [cenário se preço cair]
""".strip()


def build_prompt(
    asset: str,
    timeframe: str,
    has_screenshot: bool,
    notes: str | None = None,
    history: str | None = None,
    similar_history: str | None = None,
    news_context: str | None = None,
    calendar_context: str | None = None,
) -> str:
    screenshot_instruction = (
        "Analise o gráfico enviado com atenção à estrutura de preço, tendência e padrões."
        if has_screenshot
        else "Sem screenshot disponível. Baseie a análise nos dados fornecidos."
    )
    context_lines = []
    if similar_history:
        context_lines.append(similar_history)
    if history:
        context_lines.append(history)
    if news_context:
        context_lines.append(news_context)
    if calendar_context:
        context_lines.append(calendar_context)
    if notes:
        context_lines.append(f"Notas do trader: {notes}")
    if not context_lines:
        context_lines.append("Nenhum contexto adicional fornecido.")

    return TEMPLATE.format(
        asset=asset,
        timeframe=timeframe,
        screenshot_instruction=screenshot_instruction,
        context_block="\n".join(context_lines),
    )

# Oracle Trader Assist — Avaliação Técnica do Sistema

> Gerado em 2026-05-27. Avaliação honesta do estado atual: o que funciona, o que está quebrado, o que falta, e sugestões priorizadas.

---

## 1. Visão Geral do Sistema

Oracle Trader Assist é uma plataforma de assistência a day traders com:
- Backend Python/FastAPI com Clean Architecture
- Frontend SPA vanilla JS servido pelo próprio FastAPI
- Claude (Anthropic) como engine de IA para análise e chat
- PostgreSQL para persistência, Redis para eventos em tempo real
- APScheduler para jobs agendados
- Integração MT5 via bridge script (Windows)

**Versão atual:** 0.1.0 (fase MVP)  
**Testes:** 206 unit/API passando | 43 integration (requerem Docker)

---

## 2. Arquitetura — Estado Atual

### O que está bem feito

```
src/oracle/
├── domain/           ← Entidades, enums, value objects, eventos, contratos
│   ├── analysis/     ✅ Completo
│   ├── trade/        ✅ Completo
│   ├── memory/       ✅ Completo
│   ├── replay/       ✅ Completo
│   ├── analytics/    ✅ Completo
│   └── market/       ✅ Completo
├── application/      ← Use cases (um por arquivo)
│   ├── analysis/     ✅ RunAnalysisUseCase, SendMessageUseCase
│   ├── trade/        ✅ RecordTrade, CloseTrade, ReflectOnTrade, RunChecklist
│   ├── memory/       ✅ LoadContext, SaveContext, SearchHistory
│   ├── replay/       ✅ CreateReplay, ControlReplay, AnnotateFrame
│   ├── analytics/    ✅ GetPerformanceUseCase
│   └── briefing/     ✅ GenerateBriefingUseCase
├── infrastructure/   ← Adapters (PostgreSQL, Redis, Claude, MT5, News)
└── interface/        ← FastAPI routers, WebSocket gateway, dependencies
```

**Strengths:**
- Clean Architecture corretamente implementada — sem vazamento de camadas
- Um use case por arquivo (project-rules respeitado)
- DTOs separados de entidades de domínio
- Testes unitários do domínio são puros (sem I/O)
- API tests usam TestClient com mocks de infraestrutura
- Alembic para migrations (5 tabelas: trades, analyses, memory, performance_reports, replay_sessions)
- Loguru + logging interception para tracebacks completos
- Prompt caching (cache_control: ephemeral) economiza tokens Claude

---

## 3. Bugs Corrigidos Nesta Sessão

| Bug | Causa Raiz | Fix Aplicado |
|-----|-----------|-------------|
| HTTP 500 ao fechar trade | `Entity` usa `use_enum_values=True` → `trade.direction` é `str`, não enum. `str.value` não existe. | `close_trade.py:31`: `trade.direction.value == "LONG"` → `trade.direction == "LONG"` |
| Briefing "Ativos" sem Sup/Res | `GenerateBriefingUseCase` retorna `key_levels={}` hard-coded | Frontend: `_parseLevelsFromBriefing()` extrai via regex do texto + fallback ±1.5% do preço atual |
| Replay sem feedback visual | `replayNext()` aguardava WS silenciosamente | Spinner imediato + timeout 3s com display de status via REST |
| POST /trades retorna 422 | Frontend enviava `direction: 'long'` (lowercase), enum espera `'LONG'` | `dir.toUpperCase()` no payload |
| Widget MERCADO sempre vazio | WS `market.ticker_updated` só dispara com MT5 bridge ativo | `loadQuotes()` popula widget via REST mock |
| Servidor caía silenciosamente | APScheduler Redis jobstore tentava pickling do engine SQLAlchemy | `MemoryJobStore` + `_InterceptHandler` para logging |

---

## 4. O Que Funciona (em produção, agora)

### Backend ✅
- `POST /api/v1/trades` — registrar trade com validação geométrica (LONG/SHORT)
- `GET /api/v1/trades` — listar trades com limit
- `PUT /api/v1/trades/{id}/close` — fechar trade + calcular R realizado (**bug corrigido**)
- `POST /api/v1/analyses` — análise técnica via Claude (com ou sem screenshot)
- `GET /api/v1/analyses/{id}` — buscar análise por ID
- `GET /api/v1/market/quotes` — 8 símbolos via MockMarketAdapter
- `GET /api/v1/market/quotes/{sym}/timeframes` — MTF trend grid
- `GET /api/v1/analytics/performance` — métricas calculadas dos trades fechados
- `GET /api/v1/analytics/summary` — resumo all-time
- `GET /api/v1/briefing/morning` — briefing via Claude
- `GET /api/v1/health` — health check API + DB
- `POST /api/v1/replay` — criar sessão de replay (dados sintéticos)
- `PUT /api/v1/replay/{id}/next` — avançar frame
- `POST /api/v1/replay/{id}/annotate` — anotar frame com IA
- `GET /api/v1/memory/context` — carregar contexto de sessão por ativo
- `GET /api/v1/memory/search` — buscar histórico de setups
- WebSocket `/ws` — eventos em tempo real (análise, trades, replay, AI stream, mercado)

### Frontend ✅
- Análise técnica com circular score, sugestão, trend, scenarios
- Chat (streaming via WS + fallback REST)
- Histórico de trades com stats (total, open, win, loss, WR%)
- Fechar trade com modal (bug corrigido)
- Mercado com 8 símbolos, grid MTF, calendário macro
- Widget MERCADO no sidebar com polling 3s
- Ticker strip com polling 3s
- Performance com gauge, EV, drawdown, P&L diário
- Briefing matinal com parsing de níveis (novo)
- Checklist pré-trade com score e veredicto
- Calculadora de risco (pip value, lot size, R:R)
- Replay com controles e anotação por IA
- Polling automático por página (trades 5s, perf 10s, análise 5s)

---

## 5. O Que Está Quebrado ou Com Funcionamento Inadequado

### 5.1 Dados de Mercado — Crítico

**Problema:** `MockMarketAdapter` gera preços com `random.gauss()` a cada request. Os preços mudam aleatoriamente a cada 3 segundos (polling). O ticker strip e o widget MERCADO mostram variações falsas e sem sentido.

**Impacto:** Análise técnica real é impossível. Suporte/resistência do briefing usam valores calculados sobre dados aleatórios.

**Fix necessário:** 
- Opção A: MT5 bridge funcionando via ActivTrades demo (Windows, ver `scripts/mt5_bridge.py`)
- Opção B: Integração com Yahoo Finance ou Alpha Vantage para dados reais via REST

### 5.2 Briefing — key_levels sempre vazio (backend)

**Problema:** `GenerateBriefingUseCase.execute()` retorna `key_levels={}` hard-coded. Níveis de suporte/resistência não são extraídos do texto do Claude.

**Fix atual (frontend):** Regex sobre o texto + fallback ±1.5% do preço. É workaround — funciona apenas se o Claude mencionar os valores com formatação consistente.

**Fix correto (backend):** Parsear a resposta do Claude com regex estruturado e popular `key_levels` antes de retornar `BriefingOutput`. Exemplo:
```python
key_levels = _extract_levels_from_content(content, assets)
```
Isso garante que a API retorne dados reais e qualquer cliente (mobile, etc.) se beneficie.

### 5.3 Replay — Dados Sintéticos

**Problema:** `_generate_frames()` usa gaussian random walk, não dados históricos reais. O replay não representa o que aconteceu no mercado.

**Fix necessário:** Integrar um provedor de dados históricos OHLCV (Yahoo Finance, Investing.com, MT5 historical) e substituir `_generate_frames()` por fetch real de barras.

### 5.4 APScheduler — Jobs Não Persistem Entre Restarts

**Problema:** Jobs usam `MemoryJobStore` (necessário porque SQLAlchemy engine não é picklable). Se o servidor reiniciar, os jobs continuam agendados mas o estado em memória é perdido — sem problema funcional, mas execuções perdidas durante downtime não são recuperadas.

**Fix:** Sem workaround simples com esta arquitetura. Para jobs críticos (morning briefing), avaliar uso de celery + beat com Redis backend, ou separar o engine do scheduler dos kwargs do job.

### 5.5 Análise — Endpoint sem Listagem

**Problema:** Existe `GET /api/v1/analyses/{id}` mas não `GET /api/v1/analyses`. O poller da página de análise (`pollLatestAnalysis`) só consegue refazer fetch de uma análise já conhecida por ID — não descobre análises novas sem WS.

**Fix:** Adicionar `GET /api/v1/analyses?asset=&limit=` que retorna análises recentes. O use case `RunAnalysisUseCase.get()` já existe — é só adicionar `list()` e o endpoint.

### 5.6 Sem Autenticação

**Problema:** Qualquer pessoa com acesso à URL pode ver trades, análises, briefings e acionar IA.

**Fix:** Para uso pessoal (localhost), aceitável. Para produção: Bearer token simples via `fastapi-security` ou API key em header.

### 5.7 Documentação OpenAPI Desabilitada em Produção

**Problema:** `docs_url`, `redoc_url` e `openapi_url` são `None` quando `DEBUG=False`. Impossível explorar a API em produção sem editar settings.

**Fix:** Proteger `/docs` com API key em vez de desabilitar completamente.

---

## 6. O Que Está Documentado Mas Não Implementado

| Feature | Documentado em | Status |
|---------|---------------|--------|
| ML integration / embeddings | roadmap.md | ❌ Não iniciado |
| Pattern recognition | roadmap.md, feature-backlog.md | ❌ Não iniciado |
| Trade classification automática | roadmap.md | ❌ Não iniciado |
| `score_setup.py` use case | project-rules.md (análise) | ❌ Scoring está embutido no RunAnalysisUseCase |
| Dados históricos reais para replay | architecture.md | ❌ Ainda random walk |
| Notificações push browser | implied by event bus | ❌ Não implementado |
| Multi-ativo no replay | architecture.md | ❌ Só 5 ativos hard-coded com preços base |

---

## 7. Sugestões de Melhoria — Priorizadas

### Alta Prioridade (impacto imediato)

**1. Integrar Yahoo Finance para dados reais (1-2 dias)**
```python
# pip install yfinance
import yfinance as yf
snap = yf.download("PETR4.SA", period="1d", interval="5m")
```
Substituiria MockMarketAdapter com dados reais sem dependência do MT5.

**2. Populator de key_levels no backend (2h)**
Parsear texto do Claude antes de retornar `BriefingOutput`. Regex como o do frontend, mas no Python/backend, para que qualquer client se beneficie.

**3. Endpoint `GET /api/v1/analyses` para listagem (2h)**
Sem isso, o poller da página de análise é cego a novas análises disparadas por outros clientes.

**4. Rate limiting das chamadas Claude (1h)**
```python
from slowapi import Limiter
@router.post("", dependencies=[Depends(limiter.limit("10/minute"))])
```
Sem rate limiting, um click duplo no botão "Analisar" dispara duas chamadas Claude simultâneas.

### Média Prioridade (qualidade de vida)

**5. Chart de velas no Replay (3-5 dias)**
O replay atual mostra apenas OHLCV em texto. Um gráfico de velas com Chart.js ou Lightweight Charts tornaria o replay funcional para estudo real.

**6. Histórico de análises na página Análise (1 dia)**
Lista das últimas N análises por ativo, com timestamp, score e sugestão. Permite comparar evolução do raciocínio.

**7. Modo escuro/claro toggleável (4h)**
O CSS já usa variáveis CSS. Adicionar toggle e persistir em `localStorage`.

**8. Export de trades para CSV/Excel (2h)**
```javascript
function exportTrades() {
  const csv = state.trades.map(t => [t.asset, t.direction, ...].join(',')).join('\n');
  const blob = new Blob([csv], {type:'text/csv'});
  ...
}
```

**9. Paginação na lista de trades (2h)**
Atualmente `limit=100` fixo. Com muitos trades, a tabela fica pesada. Implementar cursor-based pagination ou `offset/limit` com controles na UI.

**10. Reflection na UI (2h)**
`POST /api/v1/trades/{id}/reflect` existe e retorna análise reflexiva do Claude sobre o trade. Não há botão na UI de trades para disparar isso.

### Baixa Prioridade (futura)

**11. Autenticação por API key (quando sair do localhost)**
Simples header `X-API-Key` verificado em middleware.

**12. Prometheus metrics endpoint (devops)**
`pip install prometheus-fastapi-instrumentator` — expõe `/metrics` para Grafana.

**13. Replay com dados históricos reais (semanas)**
Requer integração com MT5 histórico ou provedor externo, storage de OHLCV e re-arquitetura do `_generate_frames()`.

**14. Embeddings para busca semântica de setups**
O `SearchHistoryUseCase` faz busca por campos exatos. Embeddings permitiriam "setups similares a este" mesmo com nomes diferentes.

---

## 8. Cobertura de Testes — Avaliação

| Camada | Cobertura | Qualidade |
|--------|-----------|-----------|
| Domain entities/value objects | ✅ Alta (unit tests puros) | Excelente |
| Application use cases | ⚠️ Parcial — apenas checklist tem unit test | Insuficiente |
| Infrastructure repositories | ✅ Boa (integration tests, precisa Docker) | Boa |
| API routers | ✅ Boa (TestClient com FakeAI) | Boa |
| Frontend | ❌ Zero testes | Ausente |

**Lacunas principais:**
- `RunAnalysisUseCase` — sem unit test que verifique o prompt construído
- `GenerateBriefingUseCase` — sem unit test do content parsing
- `CloseTradeUseCase` — sem unit test (o bug de `.value` teria sido pego aqui)
- `GetPerformanceUseCase` — sem unit test de cálculo de métricas

**Recomendação:** Adicionar unit tests para os use cases de aplicação usando `FakeRepository` e `FakeAIProvider` (o padrão já existe nos integration tests).

---

## 9. Dependências Externas — Estado

| Serviço | Necessário para | Estado |
|---------|----------------|--------|
| PostgreSQL | Persistência de todos os dados | ✅ Funcionando (Docker) |
| Redis | WebSocket event bus, cache | ✅ Funcionando (Docker) |
| Anthropic API | Análise, chat, briefing, reflection, annotate | ✅ Funcionando (requer ANTHROPIC_API_KEY) |
| MetaTrader 5 | Dados de mercado em tempo real | ⚠️ Instável (ActivTrades auth error -6) |
| NewsAPI | Contexto de notícias na análise | ⚠️ Requer NEWS_API_KEY |
| Finnhub | Calendário econômico | ⚠️ Requer FINNHUB_API_KEY |
| Telegram | Notificações do morning briefing | ⚠️ Requer TELEGRAM_BOT_TOKEN |

---

## 10. Próximas Ações Recomendadas (em ordem)

1. **[Hoje]** Resolver dados de mercado reais — Yahoo Finance para cotações  
2. **[Hoje]** Adicionar `GET /api/v1/analyses?limit=` para listagem  
3. **[Amanhã]** Implementar key_levels no backend do briefing  
4. **[Esta semana]** Unit tests para CloseTradeUseCase, RunAnalysisUseCase  
5. **[Esta semana]** Botão "Refletir" na UI de trades → `POST /{id}/reflect`  
6. **[Próxima semana]** Chart de velas no replay (Lightweight Charts)  
7. **[Próxima semana]** Export CSV de trades  
8. **[Futuro]** Dados históricos reais para replay  

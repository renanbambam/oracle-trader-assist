# Oracle Trader Assist — Architecture

> Fonte de verdade arquitetural: `docs/oracle_architecture_final.md`
> Este arquivo é o sumário executivo. Para detalhes completos, consulte o documento acima.

---

## Naming

- Project: **Oracle Trader Assist**
- Codename: `oracle`
- Service prefix: `oracle_*`
- Class prefix: `Oracle*`
- **Prohibited:** ~~Jarvis~~, ~~jarvis~~, ~~JARVIS~~

---

## Stack

### Backend
- Python 3.12+
- FastAPI — API HTTP + WebSocket gateway
- PostgreSQL 16+ — persistência principal
- SQLAlchemy 2.0 (async) — ORM
- Alembic — migrações de schema
- Redis 7+ — pub/sub, cache, session state
- Pydantic v2 — validação e schemas

### AI
- Claude API (Sonnet padrão, Opus pontual)
- Anthropic prompt caching (obrigatório)
- future: embeddings, ML scoring

### Market Data
- MetaTrader5 (Windows, via MarketDataProvider interface)
- NewsAPI — notícias
- Finnhub — calendário econômico

### Infrastructure
- Docker + Docker Compose
- GitHub Actions CI/CD
- pytest + testcontainers
- Ruff + Black

---

## Architecture Principles

- Clean Architecture (domain → application → infrastructure → interface)
- SOLID em todo código de domínio
- Event-driven via Redis pub/sub
- Repository Pattern com interfaces no domínio
- Dependency Injection via FastAPI Depends
- Backend-first — sem frontend antes do core estar sólido
- Sem overengineering — abstrações quando há necessidade real, não antecipada

---

## Modularidade e Complexidade

**Filosofia:** modular-first · maintainability-first · testability-first · readability-first

### Limites de complexidade

- Alvo médio: até ~200 linhas por arquivo
- Limite: arquivos acima de ~300 linhas devem ser divididos
- Sem god objects, sem services monolíticos, sem routers com lógica de negócio

### Decomposição por camada

| Camada | Padrão de decomposição |
|---|---|
| `domain/<ctx>/` | `entities.py` · `value_objects.py` · `enums.py` · `events.py` · `contracts.py` · `services.py` |
| `application/<ctx>/` | `dtos.py` · um arquivo por use case |
| `infrastructure/<ctx>/` | um arquivo por model, repository e adapter |
| `interface/api/routers/<ctx>/` | `router.py` · `requests.py` · `responses.py` |

### Regras

- Preferir composição ao invés de centralização
- Alta coesão dentro de módulos; baixo acoplamento entre módulos
- Módulos comunicam intenção pelo nome — sem `utils.py` ou `helpers.py` genéricos
- Bounded contexts se comunicam via EventBus, nunca por importação direta entre contextos

> Detalhes completos e anti-patterns proibidos: `project-rules.md`

---

## Bounded Contexts

1. **Market** — OHLCV, ticker, news, calendar
2. **Analysis** — AI chat, vision, confidence scoring
3. **Memory** — context sessions, persistent state, conversation history
4. **Trade** — journal, reflection, risk check, anti-FOMO
5. **Replay** — timeline, playback control, AI annotations
6. **Analytics** — performance, win rate, behavioral patterns

---

## Clean Architecture Layers

```
interface/        ← HTTP routers, WebSocket gateway, request/response schemas
application/      ← Use cases, command/query handlers
domain/           ← Entities, value objects, services, repository interfaces
infrastructure/   ← PostgreSQL, Redis, Claude API, MT5, NewsAPI
```

**Regra:** dependências apontam para dentro. `domain` não importa nada de `infrastructure`.

---

## Main Modules

- `Context Persistence Engine` — sessões de contexto com trimming automático
- `Trade Journal` — registro, validação, reflexão pós-trade
- `Replay Engine` — playback histórico com análise de IA por frame
- `Confidence Scoring` — score 0-100 com pesos e justificativas
- `AI Assistant Layer` — Claude com prompt caching e streaming
- `WebSocket Gateway` — broadcast de eventos via Redis pub/sub
- `Analytics Engine` — win rate, expectativa, métricas comportamentais

---

## Roadmap

### MVP
- FastAPI core + PostgreSQL + Alembic
- WebSocket gateway + Redis EventBus
- Trade journal (record, close, reflect)
- Replay engine
- Claude integration (analysis + chat + streaming)
- Confidence scoring engine

### Phase 2
- Analytics dashboard endpoints
- Morning briefing scheduler
- Notifications (Telegram, TTS)
- Advanced scoring metrics

### Future ML
- Embeddings + RAG sobre histórico
- Trade classification model
- Pattern recognition
- Predictive scoring

---

## Key Decisions

| Decision | Choice |
|---|---|
| Database | PostgreSQL (not SQLite) |
| Event bus | Redis pub/sub |
| No frontend in MVP | Backend-first, API-first |
| Prompt caching | Mandatory from day 1 |
| MT5 abstraction | MarketDataProvider Protocol |
| Obsidian | Optional integration, not core dependency |
| Migrations | Alembic from first schema |
| Replay Engine | In MVP scope |

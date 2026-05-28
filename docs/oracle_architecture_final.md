# Oracle Trader Assist — Arquitetura Final

> Documento vivo. Fonte oficial de verdade arquitetural.
> Stack, módulos, fluxos, contratos e estratégias definitivas.

---

## 0. Nomenclatura Oficial

| Contexto | Nome |
|---|---|
| Produto | Oracle Trader Assist |
| Codename interno | oracle |
| Prefixo de serviços | `oracle_*` |
| Prefixo de classes | `Oracle*` |
| Nome proibido | ~~Jarvis~~, ~~jarvis~~, ~~JARVIS~~ |

Referências visuais em `docs/ui-references/` são legado de design — válidas para direção visual, inválidas como fonte de nomenclatura ou arquitetura.

---

## 1. Visão e Filosofia

Oracle Trader Assist é uma plataforma enterprise de suporte à decisão para day trading. Não é um bot de execução. É um copiloto analítico que cruza dados de mercado, histórico pessoal, contexto macro e inteligência artificial para elevar a qualidade da tomada de decisão do trader.

**Princípios inegociáveis:**
- Backend-first. Nenhum frontend antes do core estar sólido.
- Clean Architecture obrigatória em todos os módulos.
- SOLID em todo código de domínio.
- Event-driven para comunicação entre módulos e clientes.
- Repository Pattern para toda persistência.
- Dependency Injection em todos os serviços.
- Testes obrigatórios no domínio e nos use cases.
- Sem overengineering. Abstrações quando há necessidade real, não antecipada.

### Filosofia de Modularidade

O código do Oracle segue **modularidade extrema** como princípio de design. A justificativa é pragmática: o projeto é desenvolvido de forma iterativa e assistida por IA — código modular é mais fácil de navegar, testar, alterar e comunicar.

**Limites de complexidade obrigatórios:**
- Alvo médio: até ~200 linhas por arquivo
- Limite: arquivos acima de ~300 linhas devem ser divididos
- Sem god objects, sem services monolíticos, sem routers com lógica de negócio embutida

**Decomposição por tipo de conceito (por bounded context):**

| Arquivo | Conteúdo |
|---|---|
| `entities.py` | Entidades com identidade e ciclo de vida |
| `value_objects.py` | Objetos imutáveis, sem identidade |
| `enums.py` | Enumerações do domínio |
| `events.py` | Eventos de domínio emitidos por este contexto |
| `contracts.py` | Interfaces / Protocols (repositórios, providers) |
| `services.py` | Domain services — lógica pura, sem IO |
| `dtos.py` | Transferência de dados entre camadas |
| `requests.py` / `responses.py` | Schemas de API separados por direção |

**Objetivo:** qualquer desenvolvedor ou IA deve encontrar qualquer responsabilidade em ≤ 10 segundos pelo nome do arquivo, sem ler o projeto inteiro.

---

## 2. Stack Oficial

### Backend
| Tecnologia | Versão mínima | Função |
|---|---|---|
| Python | 3.12+ | Runtime principal |
| FastAPI | 0.111+ | API HTTP + WebSocket gateway |
| PostgreSQL | 16+ | Persistência principal |
| SQLAlchemy | 2.0+ | ORM async |
| Alembic | 1.13+ | Migrações de schema |
| Redis | 7+ | Pub/Sub, cache, session state |
| Pydantic | 2.7+ | Validação e schemas |
| httpx | 0.27+ | HTTP async para integrações externas |
| loguru | 0.7+ | Logging estruturado |
| pytest | 8+ | Framework de testes |
| Ruff | 0.4+ | Linter |
| Black | 24+ | Formatter |

### AI
| Tecnologia | Função |
|---|---|
| Claude API (Sonnet padrão) | Análise multimodal, chat, reflexão |
| Claude API (Opus pontual) | Análise crítica de alta convicção |
| Anthropic prompt caching | Redução de custo e latência |
| future: sentence-transformers | Embeddings para RAG |
| future: scikit-learn / XGBoost | Scoring ML |

### Dados de Mercado
| Tecnologia | Função |
|---|---|
| MetaTrader5 (Windows) | Provider padrão — OHLCV, preço, posições |
| NewsAPI | Notícias relevantes por ativo |
| Finnhub | Calendário econômico |

> **Importante:** MT5 é Windows-only. Toda integração com mercado passa por `MarketDataProvider` (Protocol). MT5 é uma implementação, não uma dependência direta do domínio.

### Infraestrutura
| Tecnologia | Função |
|---|---|
| Docker + Docker Compose | Ambiente de desenvolvimento |
| GitHub Actions | CI/CD |
| python-dotenv | Variáveis de ambiente |
| APScheduler | Jobs agendados (briefing, limpeza) |

---

## 3. Bounded Contexts

O sistema é organizado em 6 contextos de domínio. Cada contexto tem autonomia sobre seus dados, regras e modelos.

```
┌─────────────────────────────────────────────────────────────────┐
│                     Oracle Trader Assist                        │
│                                                                 │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────────┐  │
│  │   MARKET     │  │  ANALYSIS    │  │       MEMORY         │  │
│  │  CONTEXT     │  │  CONTEXT     │  │      CONTEXT         │  │
│  │              │  │              │  │                      │  │
│  │ • OHLCV      │  │ • AI chat    │  │ • Context sessions   │  │
│  │ • Ticker     │  │ • Vision     │  │ • Trade history      │  │
│  │ • News       │  │ • Confidence │  │ • Persistent state   │  │
│  │ • Calendar   │  │ • Scoring    │  │ • Embeddings (future)│  │
│  └──────────────┘  └──────────────┘  └──────────────────────┘  │
│                                                                 │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────────┐  │
│  │    TRADE     │  │    REPLAY    │  │     ANALYTICS        │  │
│  │   CONTEXT    │  │   CONTEXT    │  │      CONTEXT         │  │
│  │              │  │              │  │                      │  │
│  │ • Journal    │  │ • Timeline   │  │ • Win rate           │  │
│  │ • Reflection │  │ • Playback   │  │ • Performance        │  │
│  │ • Risk check │  │ • AI markers │  │ • Behavioral         │  │
│  │ • Anti-FOMO  │  │ • Control    │  │ • Heatmaps           │  │
│  └──────────────┘  └──────────────┘  └──────────────────────┘  │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### Regras de comunicação entre contextos
- Contextos se comunicam via **eventos** (EventBus/Redis), nunca por importação direta de modelos internos.
- Cada contexto expõe uma **API pública** (application services + DTOs).
- Um contexto nunca acessa o repositório de outro contexto diretamente.

---

## 4. Arquitetura em Camadas (Clean Architecture)

```
interface/api/          ← HTTP routers, WebSocket gateway, request/response schemas
     │
     ▼
application/            ← Use cases, application services, command/query handlers
     │
     ▼
domain/                 ← Entities, value objects, domain services, repository interfaces
     │
     ▼
infrastructure/         ← PostgreSQL, Redis, Claude API, MT5, NewsAPI, file system
```

### Regras rígidas
1. **Dependências apontam para dentro.** `domain` não importa nada de `infrastructure`.
2. **Domain não conhece FastAPI, SQLAlchemy, nem Redis.** Apenas interfaces puras (Protocol).
3. **Infrastructure implementa interfaces do domínio.** Ex.: `PostgresTradeRepository` implementa `TradeRepository`.
4. **Use cases orquestram.** Não contêm lógica de negócio — delegam para domain services.
5. **Schemas da API são distintos dos modelos de domínio.** `TradeCreateRequest` ≠ `Trade`.

---

## 5. Árvore Final do Projeto

> Segue a filosofia de modularidade extrema: cada arquivo tem responsabilidade única.
> Padrão de decomposição por contexto: `entities` · `value_objects` · `enums` · `events` · `contracts` · `services`

```
oracle-trader-assist/
│
├── src/
│   └── oracle/
│       │
│       ├── domain/                          # Regras de negócio puras — zero dependências externas
│       │   ├── market/
│       │   │   ├── entities.py              # MarketSnapshot, OHLCVBar, Ticker
│       │   │   ├── value_objects.py         # Symbol, Timeframe, Price
│       │   │   ├── enums.py                 # TimeframeEnum, AssetClass
│       │   │   ├── events.py                # MarketTickerUpdated, CandleClosed
│       │   │   └── contracts.py             # MarketDataProvider (Protocol)
│       │   │
│       │   ├── analysis/
│       │   │   ├── entities.py              # AnalysisSession, ChartAnalysis
│       │   │   ├── value_objects.py         # ConfidenceScore, TrendDirection
│       │   │   ├── enums.py                 # Suggestion, ConfidenceLabel, TrendStrength
│       │   │   ├── events.py                # AnalysisCompleted, ConfidenceUpdated
│       │   │   ├── contracts.py             # AnalysisRepository (Protocol)
│       │   │   └── services.py              # ConfidenceEngine, MultiTimeframeAligner
│       │   │
│       │   ├── trade/
│       │   │   ├── entities.py              # Trade, TradeResult
│       │   │   ├── value_objects.py         # RiskRatio, EntryPoint
│       │   │   ├── enums.py                 # Direction, TradeResult, EmotionalState
│       │   │   ├── events.py                # TradeRecorded, TradeClosed
│       │   │   ├── contracts.py             # TradeRepository (Protocol)
│       │   │   └── services.py              # RiskCalculator, AntiFOMOFilter, ChecklistValidator
│       │   │
│       │   ├── memory/
│       │   │   ├── entities.py              # ContextSession, ConversationTurn
│       │   │   ├── value_objects.py         # TokenBudget, ContextWindow
│       │   │   ├── enums.py                 # TrimStrategy, SessionStatus
│       │   │   ├── events.py                # ContextTrimmed, SessionExpired
│       │   │   ├── contracts.py             # MemoryRepository (Protocol)
│       │   │   └── services.py              # ContextWindowManager, ContextTrimmer
│       │   │
│       │   ├── replay/
│       │   │   ├── entities.py              # ReplaySession, ReplayFrame, ReplayTimeline
│       │   │   ├── value_objects.py         # TimeRange, FrameAnnotation
│       │   │   ├── enums.py                 # ReplayState, PlaybackSpeed
│       │   │   ├── events.py                # ReplayFrameAdvanced, ReplayCompleted
│       │   │   ├── contracts.py             # ReplayRepository (Protocol)
│       │   │   └── services.py              # ReplayEngine, FrameAdvancer
│       │   │
│       │   └── analytics/
│       │       ├── entities.py              # PerformanceReport, SetupStats, TraderProfile
│       │       ├── value_objects.py         # WinRate, ExpectedValue, DrawdownMetric
│       │       ├── enums.py                 # MetricPeriod, SetupCategory
│       │       ├── events.py                # ReportGenerated
│       │       └── services.py              # PerformanceCalculator, BehavioralAnalyzer
│       │
│       ├── application/                     # Use cases — um arquivo por operação
│       │   ├── analysis/
│       │   │   ├── dtos.py                  # AnalysisRequest, AnalysisResult DTOs
│       │   │   ├── run_analysis.py          # UseCase: análise completa de setup
│       │   │   ├── send_message.py          # UseCase: chat com IA (streaming)
│       │   │   └── score_setup.py           # UseCase: calcular confidence score
│       │   │
│       │   ├── trade/
│       │   │   ├── dtos.py                  # TradeInput, TradeOutput, CloseInput DTOs
│       │   │   ├── record_trade.py          # UseCase: registrar operação
│       │   │   ├── close_trade.py           # UseCase: fechar com resultado
│       │   │   ├── reflect_on_trade.py      # UseCase: reflexão pós-trade via IA
│       │   │   └── run_checklist.py         # UseCase: checklist pré-operação
│       │   │
│       │   ├── memory/
│       │   │   ├── dtos.py                  # ContextLoadRequest, ContextSaveInput DTOs
│       │   │   ├── load_context.py          # UseCase: carregar contexto para análise
│       │   │   ├── save_context.py          # UseCase: persistir sessão de contexto
│       │   │   └── search_history.py        # UseCase: buscar histórico similar
│       │   │
│       │   ├── replay/
│       │   │   ├── dtos.py                  # CreateReplayInput, ControlInput DTOs
│       │   │   ├── create_replay.py         # UseCase: iniciar sessão de replay
│       │   │   ├── control_replay.py        # UseCase: play/pause/seek/step
│       │   │   └── annotate_frame.py        # UseCase: anotar frame com IA
│       │   │
│       │   ├── analytics/
│       │   │   ├── dtos.py                  # PerformanceQuery, SetupStatsQuery DTOs
│       │   │   ├── get_performance.py       # UseCase: relatório de performance
│       │   │   └── get_setup_stats.py       # UseCase: estatísticas por setup
│       │   │
│       │   └── briefing/
│       │       ├── dtos.py                  # BriefingRequest, BriefingResult DTOs
│       │       └── generate_briefing.py     # UseCase: briefing matinal
│       │
│       ├── infrastructure/                  # Implementações concretas — um arquivo por adapter
│       │   ├── database/
│       │   │   ├── base.py                  # DeclarativeBase compartilhada
│       │   │   ├── connection.py            # Engine + session factory builders
│       │   │   ├── models/                  # ORM models — separados das domain entities
│       │   │   │   ├── trade_model.py       # TradeORM
│       │   │   │   ├── analysis_model.py    # AnalysisORM
│       │   │   │   ├── context_session_model.py   # ContextSessionORM
│       │   │   │   ├── replay_session_model.py    # ReplaySessionORM
│       │   │   │   └── analysis_feature_model.py  # AnalysisFeatureORM (feature store ML)
│       │   │   └── repositories/
│       │   │       ├── trade_repository.py  # PostgresTradeRepository
│       │   │       ├── analysis_repository.py
│       │   │       ├── memory_repository.py
│       │   │       └── replay_repository.py
│       │   │
│       │   ├── redis/
│       │   │   ├── client.py                # Redis async client builder
│       │   │   ├── event_bus.py             # RedisEventBus — implementa EventBus Protocol
│       │   │   └── session_store.py         # Cache de estado ativo (replay, context)
│       │   │
│       │   ├── ai/
│       │   │   ├── claude_client.py         # Wrapper Claude API: retry, caching, streaming
│       │   │   ├── prompt_engine.py         # Seleciona e renderiza template de prompt
│       │   │   ├── response_parser.py       # Parseia resposta estruturada da IA
│       │   │   └── vision_adapter.py        # Análise de screenshots via Vision API
│       │   │
│       │   ├── market_data/
│       │   │   ├── contracts.py             # MarketDataProvider Protocol (espelho do domínio)
│       │   │   ├── mt5_adapter.py           # Implementação MT5 — Windows only
│       │   │   └── mock_adapter.py          # Implementação mock — testes e não-Windows
│       │   │
│       │   ├── news/
│       │   │   ├── news_adapter.py          # NewsAPI adapter
│       │   │   └── calendar_adapter.py      # Finnhub economic calendar adapter
│       │   │
│       │   ├── messaging/
│       │   │   ├── telegram_adapter.py      # Notificações Telegram (Fase 2)
│       │   │   └── tts_adapter.py           # Text-to-Speech adapter (Fase 2)
│       │   │
│       │   └── scheduler/
│       │       ├── scheduler.py             # APScheduler com jobstore Redis
│       │       └── jobs/
│       │           ├── morning_briefing_job.py
│       │           ├── weekly_summary_job.py
│       │           └── news_refresh_job.py
│       │
│       └── interface/
│           ├── api/
│           │   ├── app.py                   # create_app() factory com lifespan
│           │   ├── dependencies.py          # FastAPI Depends() providers
│           │   ├── middleware.py            # CorrelationId + RequestLogging
│           │   └── routers/                 # Cada contexto: router + requests + responses
│           │       ├── analysis/
│           │       │   ├── router.py        # POST /api/v1/analysis — routing apenas
│           │       │   ├── requests.py      # AnalysisRequest, ChatRequest schemas
│           │       │   └── responses.py     # AnalysisResponse, ChatChunk schemas
│           │       ├── trades/
│           │       │   ├── router.py        # GET/POST/PATCH /api/v1/trades
│           │       │   ├── requests.py      # TradeCreateRequest, TradeCloseRequest
│           │       │   └── responses.py     # TradeResponse, TradeListResponse
│           │       ├── memory/
│           │       │   ├── router.py        # GET/POST /api/v1/memory
│           │       │   ├── requests.py      # ContextLoadRequest
│           │       │   └── responses.py     # ContextResponse, SessionResponse
│           │       ├── replay/
│           │       │   ├── router.py        # /api/v1/replay
│           │       │   ├── requests.py      # CreateReplayRequest, ControlRequest
│           │       │   └── responses.py     # ReplayResponse, FrameResponse
│           │       ├── analytics/
│           │       │   ├── router.py        # GET /api/v1/analytics
│           │       │   ├── requests.py      # PerformanceQuery
│           │       │   └── responses.py     # PerformanceResponse, SetupStatsResponse
│           │       └── health/
│           │           └── router.py        # /health, /health/live, /health/ready
│           │
│           └── websocket/
│               ├── gateway.py               # WebSocketGateway — connection manager
│               ├── handler.py               # Mensagens inbound do cliente
│               └── broadcaster.py           # Subscreve EventBus e faz broadcast
│
├── prompts/                                 # TODOS os prompts centralizados
│   ├── __init__.py
│   ├── versions.py                          # PROMPT_REGISTRY — manifest central
│   ├── system/
│   │   ├── oracle_system_v1.py             # System prompt principal (cached)
│   │   └── oracle_quick_v1.py              # System prompt para respostas curtas
│   ├── analysis/
│   │   ├── chart_analysis_v1.py            # Análise de gráfico com contexto multimodal
│   │   └── ohlcv_context_v1.py             # Contextualização de dados OHLCV
│   ├── trade/
│   │   └── reflection_v1.py                # Reflexão pós-trade
│   ├── briefing/
│   │   └── morning_briefing_v1.py          # Briefing matinal
│   └── scoring/
│       └── confidence_scoring_v1.py        # Prompt de scoring de setup
│
├── migrations/
│   ├── env.py                               # Async Alembic env (asyncpg)
│   ├── script.py.mako                       # Template de migration
│   └── versions/
│
├── tests/
│   ├── conftest.py                          # Fixtures globais: settings, app, client
│   ├── unit/
│   │   ├── domain/
│   │   │   ├── test_confidence_engine.py
│   │   │   ├── test_anti_fomo_filter.py
│   │   │   ├── test_replay_engine.py
│   │   │   └── test_context_window_manager.py
│   │   └── application/
│   │       ├── test_run_analysis.py
│   │       ├── test_record_trade.py
│   │       └── test_control_replay.py
│   ├── integration/
│   │   ├── test_trade_repository.py         # Testcontainers + PostgreSQL real
│   │   ├── test_analysis_repository.py
│   │   └── test_redis_event_bus.py
│   └── api/
│       ├── test_health.py
│       ├── test_analysis_router.py
│       ├── test_trades_router.py
│       └── test_websocket_gateway.py
│
├── docs/
│   ├── oracle_architecture_final.md         # Este documento (fonte de verdade)
│   ├── ui-references/
│   │   ├── architecture.md                  # Direção de UX e eventos UI
│   │   └── jarvis_hud_v4_final.html         # Visual reference (branding legado, conteúdo válido)
│   └── jarvis_dss_arquitetura_v3_completa.html
│
├── docker/
│   └── Dockerfile                           # Multi-stage: base → deps → dev/production
├── docker-compose.yml                       # PostgreSQL + Redis + app (dev)
├── docker-compose.test.yml                  # Stack isolada para testes
├── .github/workflows/ci.yml                 # Lint + test jobs
├── alembic.ini
├── pyproject.toml                           # Ruff, Black, pytest, coverage
├── requirements.txt
├── requirements-dev.txt
├── Makefile
└── .env.example
```

---

## 6. Responsabilidades por Módulo

### Domain Layer

| Módulo | Responsabilidade única |
|---|---|
| `domain/market` | Representar dados de mercado; definir o contrato do provider |
| `domain/analysis` | Calcular confidence score; determinar alinhamento multi-timeframe; modelar resultados de análise |
| `domain/trade` | Validar operações; calcular risco/retorno; filtrar entradas emocionais; modelar estados do trade |
| `domain/memory` | Gerenciar janela de contexto; decidir o que persiste e o que descarta |
| `domain/replay` | Controlar timeline de replay; avançar frames; modelar estado do playback |
| `domain/analytics` | Calcular win rate, expectativa, drawdown, métricas comportamentais |

### Application Layer

| Use Case | Orquestra |
|---|---|
| `run_analysis` | market_data → context_loader → prompt_engine → claude_client → confidence_engine → persist |
| `send_message` | context_loader → claude_client (stream) → context_saver → broadcast |
| `record_trade` | validate → trade_repo.save → context_repo.update → event_bus.emit |
| `reflect_on_trade` | trade_repo.get → prompt_engine → claude_client → trade_repo.update_reflection |
| `create_replay` | market_data → build_timeline → replay_repo.save → event_bus.emit |
| `control_replay` | replay_repo.get → replay_engine.control → session_store.update → event_bus.emit |
| `generate_briefing` | news + calendar + trade_history → prompt_engine → claude_client → persist |

### Infrastructure Layer

| Módulo | Responsabilidade |
|---|---|
| `database/repositories` | CRUD em PostgreSQL via SQLAlchemy async |
| `redis/event_bus` | Publish/subscribe de eventos de domínio |
| `redis/session_store` | Estado de sessão ativa (replay state, context session) |
| `ai/claude_client` | Chamadas à API Anthropic com retry, streaming, prompt caching |
| `ai/prompt_engine` | Seleciona e renderiza template de prompt com contexto injetado |
| `market_data/mt5_provider` | Implementa `MarketDataProvider` via biblioteca MT5 |
| `scheduler` | APScheduler com jobstore Redis para jobs persistentes |

### Interface Layer

| Módulo | Responsabilidade |
|---|---|
| `api/routers` | Parse de request, validação de schema, chamada ao use case, formatação de response |
| `api/dependencies` | Injeção de repositórios e serviços via FastAPI Depends |
| `websocket/gateway` | Gerenciar conexões WebSocket, canais, heartbeat |
| `websocket/broadcaster` | Subscrever EventBus e fazer broadcast para clientes conectados |

---

## 7. Fluxo Completo de Dados

### Fluxo 1 — Análise de Setup (principal)

```
Cliente (HTTP POST /api/v1/analysis)
  │
  ▼
[Interface] analysis_router.py
  │ valida AnalysisRequest schema
  ▼
[Application] RunAnalysisUseCase
  │
  ├── [Infra] MarketDataProvider.get_snapshot(asset, timeframe)
  │     └── MT5Provider → OHLCV atual + preço + volume
  │
  ├── [Infra] NewsClient.get_recent(asset, hours=24)
  │
  ├── [Infra] CalendarClient.get_today_events()
  │
  ├── [Infra] MemoryRepository.get_similar_trades(asset, setup)
  │     └── PostgreSQL → últimas análises similares
  │
  ├── [Domain] ContextWindowManager.build(market + news + history)
  │     └── Respeita TOKEN_BUDGET; aplica trimming se necessário
  │
  ├── [Infra] PromptEngine.render("chart_analysis", context)
  │
  ├── [Infra] ClaudeClient.analyze(image, prompt, system_prompt_cached)
  │     └── stream_response ou full_response
  │
  ├── [Infra] ResponseParser.parse(raw) → ChartAnalysis entity
  │
  ├── [Domain] ConfidenceEngine.calculate(analysis_factors)
  │     └── Score 0–100 com breakdown e justificativas
  │
  ├── [Infra] AnalysisRepository.save(analysis)
  │     └── PostgreSQL
  │
  └── [Infra] EventBus.publish("analysis.completed", analysis)
        └── Redis pub/sub → Broadcaster → WebSocket clients

[Interface] response 200 → AnalysisResponse schema
```

### Fluxo 2 — Chat com IA (streaming)

```
Cliente (POST /api/v1/analysis/chat)
  │
  ▼
[Application] SendMessageUseCase
  │
  ├── [Infra] MemoryRepository.get_session(session_id)
  ├── [Domain] ContextWindowManager.append(new_message)
  │     └── Aplica trimming se budget excedido
  ├── [Infra] ClaudeClient.stream_message(messages, system_cached)
  │     └── AsyncGenerator[str] por token
  │
  └── Cada token → EventBus.publish("ai.token", token)
        └── Redis → Broadcaster → WebSocket ("ai_stream" channel)

[Interface] SSE stream ou WebSocket
```

### Fluxo 3 — Registro de Trade

```
Cliente (POST /api/v1/trades)
  │
  ▼
[Application] RecordTradeUseCase
  │
  ├── [Domain] Trade.validate() via Pydantic
  ├── [Domain] RiskCalculator.compute(trade) → RR, risk_pct
  ├── [Domain] AntiFOMOFilter.check(timestamp, context) → FOMOAlert
  ├── [Infra] TradeRepository.save(trade) → PostgreSQL
  ├── [Infra] MemoryRepository.update_session(trade_context)
  └── [Infra] EventBus.publish("trade.recorded", trade)
```

### Fluxo 4 — Replay

```
Cliente (POST /api/v1/replay)
  │
  ▼
[Application] CreateReplayUseCase
  │
  ├── [Infra] MarketDataProvider.get_historical(asset, range)
  ├── [Domain] ReplayEngine.build_timeline(candles, events)
  ├── [Infra] ReplayRepository.save(session) → PostgreSQL
  └── [Infra] SessionStore.set_replay_state(session_id, state) → Redis

Cliente (POST /api/v1/replay/{id}/control)
  │
  ▼
[Application] ControlReplayUseCase
  │
  ├── [Infra] SessionStore.get_replay_state(session_id)
  ├── [Domain] ReplayEngine.apply_control(action, state)
  │     └── play | pause | step | seek | set_speed
  ├── [Infra] SessionStore.update_replay_state(new_state)
  └── [Infra] EventBus.publish("replay.frame_advanced", frame)
        └── Redis → WebSocket ("replay" channel)
```

---

## 8. Fluxo de Eventos Realtime (WebSocket)

### Arquitetura do Gateway

```
Oracle Core
  │
  └── EventBus (Redis pub/sub)
        │
        └── Broadcaster (subscreve todos os canais)
              │
              └── WebSocket Gateway (FastAPI)
                    │
                    ├── cliente_1 (subscrito em: market, analysis)
                    ├── cliente_2 (subscrito em: market, replay, ai_stream)
                    └── cliente_3 (subscrito em: analysis, trading)
```

### Protocolo de Mensagem

```json
{
  "event": "analysis.completed",
  "channel": "analysis",
  "session_id": "uuid-v4",
  "timestamp": "2026-05-25T09:30:00.000Z",
  "payload": {
    "asset": "PETR4",
    "timeframe": "M15",
    "suggestion": "AGUARDAR",
    "confidence_score": 72,
    "confidence_label": "ALTA",
    "reasoning": "...",
    "risks": ["...", "..."]
  }
}
```

### Canais e Eventos

| Canal | Evento | Gatilho | Frequência |
|---|---|---|---|
| `market` | `market.ticker_updated` | MT5 polling | ~1s configurável |
| `market` | `market.candle_closed` | Fechamento de candle | Por timeframe |
| `analysis` | `analysis.completed` | Análise finalizada | On demand |
| `analysis` | `analysis.context_updated` | Contexto de sessão mudou | On demand |
| `ai_stream` | `ai.token` | Token gerado pelo Claude | Streaming |
| `ai_stream` | `ai.stream_end` | Resposta completa | On demand |
| `trading` | `trade.recorded` | Trade registrado | On demand |
| `trading` | `trade.closed` | Trade fechado | On demand |
| `trading` | `confidence.updated` | Score atualizado | On demand |
| `replay` | `replay.started` | Sessão de replay criada | On demand |
| `replay` | `replay.frame_advanced` | Frame avançou | Controlado |
| `replay` | `replay.paused` | Replay pausado | On demand |
| `system` | `system.connected` | Cliente conectou | Connection |
| `system` | `system.error` | Erro de processamento | On demand |

### Reconnect e Cold Start

```
1. Cliente conecta via ws://host/ws?token=...&channels=market,analysis
2. Servidor envia snapshot do estado atual de cada canal solicitado
3. Heartbeat a cada 30s (ping/pong)
4. Desconexão → cliente faz reconnect exponencial (1s, 2s, 4s, max 30s)
5. Ao reconectar → novo snapshot + continuação do stream
6. Eventos perdidos → consultáveis via REST (não via WebSocket)
```

---

## 9. Estratégia de Persistência

### PostgreSQL — Entidades Principais

```sql
-- Análises de setup
analyses (
  id uuid PK,
  session_id uuid,
  asset varchar(12),
  timeframe varchar(5),
  suggestion analysis_suggestion_enum,
  confidence_score float,
  confidence_label varchar(20),
  trend varchar(20),
  reasoning text,
  risks jsonb,
  raw_response text,
  screenshot_path varchar,
  created_at timestamptz
)

-- Operações registradas
trades (
  id uuid PK,
  asset varchar(12),
  direction trade_direction_enum,
  timeframe varchar(5),
  entry float,
  stop float,
  target float,
  exit float,
  result trade_result_enum,
  r_realized float,
  setup varchar(100),
  emotional_state emotional_state_enum,
  confidence_score float,
  analysis_id uuid FK analyses,
  created_at timestamptz,
  closed_at timestamptz
)

-- Sessões de contexto (memória persistente)
context_sessions (
  id uuid PK,
  asset varchar(12),
  started_at timestamptz,
  last_active_at timestamptz,
  token_count int,
  turns jsonb,               -- lista de ConversationTurn
  metadata jsonb
)

-- Sessões de replay
replay_sessions (
  id uuid PK,
  asset varchar(12),
  timeframe varchar(5),
  range_start timestamptz,
  range_end timestamptz,
  total_frames int,
  current_frame int,
  state replay_state_enum,
  annotations jsonb,
  created_at timestamptz
)

-- Logs de análise para ML (feature store)
analysis_features (
  id uuid PK,
  trade_id uuid FK trades,
  trend_alignment float,
  setup_quality float,
  historical_match float,
  macro_context float,
  market_quality float,
  emotional_state float,
  final_score float,
  label varchar(20),
  created_at timestamptz
)
```

### Redis — Dados Efêmeros e Mensagens

| Key pattern | Tipo | TTL | Conteúdo |
|---|---|---|---|
| `oracle:session:{id}` | Hash | 4h | Estado da sessão de análise ativa |
| `oracle:replay:{id}:state` | Hash | 2h | Posição e estado atual do replay |
| `oracle:market:{asset}:snapshot` | Hash | 30s | Último snapshot de mercado |
| `oracle:ws:clients` | Set | — | IDs de clientes conectados |
| `oracle:events:{channel}` | Pub/Sub | — | Stream de eventos por canal |
| `oracle:rate:{client_id}` | Counter | 60s | Rate limiting por cliente |

### Migrações (Alembic)

- Cada alteração de schema = nova migration com `alembic revision --autogenerate`
- Migration nunca destrói dados existentes — apenas evolui o schema
- Down migrations obrigatórias para todos os `upgrade()`
- Executadas automaticamente no startup em produção

---

## 10. Replay Engine — Arquitetura

### Conceito

O Replay Engine permite ao trader rever qualquer período histórico frame a frame, com análise de IA injetada em momentos específicos da timeline. Funciona como um "modo de treinamento" onde o trader pratica tomada de decisão em dados reais passados.

### Entidades de Domínio

```python
# domain/replay/entities.py

class ReplayTimeline:
    session_id: UUID
    asset: str
    timeframe: str
    frames: list[ReplayFrame]
    current_index: int
    state: ReplayState

class ReplayFrame:
    index: int
    timestamp: datetime
    ohlcv: OHLCVBar
    volume_context: str             # "above_avg" | "below_avg" | "at_avg"
    annotations: list[FrameAnnotation]
    ai_commentary: str | None       # Gerado on demand

class FrameAnnotation:
    type: str                       # "trade_opened" | "ai_marker" | "news_event"
    label: str
    color: str
    metadata: dict

class ReplayState(Enum):
    IDLE = "idle"
    PLAYING = "playing"
    PAUSED = "paused"
    COMPLETED = "completed"
```

### Controles disponíveis

| Ação | Comportamento |
|---|---|
| `play` | Avança frames automaticamente na velocidade configurada |
| `pause` | Pausa no frame atual |
| `step` | Avança exatamente 1 frame |
| `step_back` | Recua exatamente 1 frame |
| `seek(index)` | Vai para frame específico |
| `set_speed(1x\|2x\|5x\|10x)` | Define velocidade de playback |
| `annotate_ai` | Solicita análise de IA no frame atual |

### Fluxo de Estado (no Redis)

```
IDLE → CREATE → PAUSED (frame 0)
PAUSED → PLAY → PLAYING
PLAYING → PAUSE → PAUSED
PLAYING → END_OF_TIMELINE → COMPLETED
PAUSED → STEP → PAUSED (frame + 1)
ANY_STATE → SEEK(n) → PAUSED (frame n)
```

### Persistência de Replay

- **PostgreSQL**: Sessão criada, configuração, anotações e frames visitados
- **Redis**: Estado atual de playback (posição, velocidade, estado) — TTL 2h
- **Frames**: Calculados on-the-fly a partir dos dados históricos do PostgreSQL, não armazenados individualmente

---

## 11. Gerenciamento de Context Window

### Estratégia

O Claude tem uma janela de contexto finita. A estratégia garante que nunca seja excedida sem aviso, com degradação controlada (trimming) ao invés de erro.

### Definições

```python
# domain/memory/value_objects.py

class TokenBudget:
    MAX_TOTAL_TOKENS: int = 150_000       # Limite do modelo
    SYSTEM_PROMPT_RESERVE: int = 5_000    # Reservado para system prompt (cached)
    CONTEXT_RESERVE: int = 10_000         # Reservado para resposta
    HISTORY_BUDGET: int = 80_000          # Disponível para histórico
    CURRENT_ANALYSIS_BUDGET: int = 55_000 # Disponível para contexto da análise atual
```

### Algoritmo de Trimming

```
1. Sistema calcula tokens de cada segmento:
   - system_prompt → sempre preservado (prompt caching)
   - current_analysis_context → sempre preservado (prioridade máxima)
   - recent_history (N turns) → reduzido se necessário
   - older_history → primeiro a ser removido

2. Se total > HISTORY_BUDGET:
   - Remove turns mais antigas primeiro (FIFO)
   - Preserva sempre os últimos 5 turns
   - Loga aviso: "Context trimmed: removed N oldest turns"

3. Se após trimming ainda > budget:
   - Lança ContextWindowExceededError
   - API retorna 422 com instrução para iniciar nova sessão
```

### Segmentos de Contexto

| Segmento | Cached? | Prioridade | Política |
|---|---|---|---|
| System prompt | Sim (Anthropic cache) | Máxima | Nunca removido |
| Contexto de análise atual | Não | Alta | Nunca removido nesta análise |
| Últimos 5 turns | Não | Alta | Nunca removidos |
| Histórico de sessão (>5 turns) | Não | Média | Removidos oldest-first |
| Contexto de trades similares | Não | Baixa | Removidos se necessário |

---

## 12. Estratégia de Prompt Versioning

### Princípios

- Cada prompt é um módulo Python com constantes nomeadas e versionadas.
- O sistema nunca hardcoda strings de prompt em serviços ou use cases.
- O `PromptEngine` é o único ponto que conhece e seleciona prompts.
- Mudanças em prompts são rastreadas via git como qualquer outro código.

### Estrutura de Arquivo de Prompt

```python
# prompts/analysis/chart_analysis_v1.py

PROMPT_NAME = "chart_analysis"
PROMPT_VERSION = "1.0.0"
PROMPT_DESCRIPTION = "Análise completa de setup com contexto multimodal"

TEMPLATE = """
Analise o screenshot do gráfico fornecido.

═══ DADOS DO ATIVO ═══
Ativo:       {asset}
Timeframe:   {timeframe}
Preço atual: {current_price}
Volume:      {volume_context}

═══ CONTEXTO MACRO ═══
{macro_context}

═══ HISTÓRICO SIMILAR ═══
{similar_history}

{format_instructions}
"""

FORMAT_INSTRUCTIONS = """
Responda seguindo exatamente este formato:

## TENDÊNCIA
[BULLISH/BEARISH/LATERAL] — força: [FRACA/MODERADA/FORTE]

## ESTRUTURA
Suporte: [nível] | Resistência: [nível]

## SETUP
[descrição objetiva]

## RACIOCÍNIO
[3-5 linhas cruzando gráfico + contexto + histórico]

## SUGESTÃO
[OPERAR / AGUARDAR / NÃO OPERAR / REVISAR CONTEXTO]
Motivo: [1-2 linhas diretas]

## CONFIDENCE SCORE
[0-100]% — [justificativa 1 linha]

## RISCOS
- [invalidador 1]
- [invalidador 2]

## CENÁRIOS
Bull: [cenário se subir]
Bear: [cenário se cair]
"""
```

### Registro de Versões

```python
# prompts/versions.py

PROMPT_REGISTRY = {
    "oracle_system": "prompts.system.oracle_system_v1",
    "chart_analysis": "prompts.analysis.chart_analysis_v1",
    "ohlcv_context": "prompts.analysis.ohlcv_context_v1",
    "reflection": "prompts.trade.reflection_v1",
    "morning_briefing": "prompts.briefing.morning_briefing_v1",
    "confidence_scoring": "prompts.scoring.confidence_scoring_v1",
}

# Para usar versão alternativa em A/B testing:
# PROMPT_REGISTRY["chart_analysis"] = "prompts.analysis.chart_analysis_v2"
```

### Política de Versionamento

- `v1.0.0` → prompt inicial
- `v1.1.0` → mudança no formato/instrução (mesma semântica)
- `v2.0.0` → mudança na estrutura ou identidade do Oracle
- Versões antigas não são deletadas — ficam no repositório como histórico
- O `ResponseParser` é versionado junto com o prompt que ele parseia

---

## 13. Estrutura Oficial dos Prompts

### System Prompt do Oracle

```python
# prompts/system/oracle_system_v1.py

ORACLE_SYSTEM_PROMPT = """
Você é Oracle — sistema de apoio à decisão para day trading de alta performance.

IDENTIDADE:
- Direto, claro e acionável
- Trabalha com probabilidades, nunca certezas
- Explica o raciocínio completo em toda sugestão
- Nunca promete que o trade vai funcionar
- Cruza múltiplas fontes antes de sugerir
- Age como parceiro analítico sênior, não como assistente passivo
- Nunca afirma que um trade vai funcionar — afirma que as condições favorecem ou desfavorecem

COMPORTAMENTO OBRIGATÓRIO:
- Toda sugestão termina com: OPERAR / AGUARDAR / NÃO OPERAR / REVISAR CONTEXTO
- Todo confidence score tem justificativa em formato: X% — [razão em 1 linha]
- Toda análise identifica pelo menos 2 cenários alternativos (bull e bear)
- Qualquer dado ausente é declarado, não inventado

RESTRIÇÕES:
- Não executa ordens
- Não prevê preços com certeza
- Não substitui a gestão de risco humana
- Não ignora contexto macro em análises técnicas
"""
```

### Hierarquia de Prompts

```
oracle_system (base, sempre cached)
    │
    ├── chart_analysis    (análise completa com imagem + contexto)
    ├── ohlcv_context     (contextualização de dados numéricos)
    ├── reflection        (reflexão pós-trade)
    ├── morning_briefing  (briefing matinal automático)
    └── confidence_scoring (scoring sem imagem, apenas dados)
```

---

## 14. Logs e Observabilidade

### Configuração de Logging

```python
# Loguru — configuração por ambiente

# Desenvolvimento
logger.add(sys.stderr, level="DEBUG", format="{time} | {level} | {name}:{line} | {message}")

# Produção
logger.add(
    "logs/oracle_{time:YYYY-MM-DD}.log",
    level="INFO",
    format="{time:ISO} | {level} | {extra[correlation_id]} | {name} | {message}",
    rotation="1 day",
    retention="30 days",
    serialize=True  # JSON estruturado
)
```

### Correlation IDs

Toda requisição HTTP recebe um `X-Correlation-ID` (UUID v4) no middleware. Esse ID é propagado para:
- Todos os logs gerados durante a requisição
- Chamadas para Claude API (via header customizado)
- Eventos emitidos no EventBus durante a requisição

```python
# interface/api/middleware.py
async def correlation_id_middleware(request: Request, call_next):
    correlation_id = request.headers.get("X-Correlation-ID", str(uuid4()))
    with logger.contextualize(correlation_id=correlation_id):
        response = await call_next(request)
        response.headers["X-Correlation-ID"] = correlation_id
        return response
```

### Níveis de Log por Contexto

| Contexto | Level | O que logar |
|---|---|---|
| Requisição HTTP | INFO | método, path, status, duration_ms, correlation_id |
| Claude API call | INFO | model, prompt_tokens, completion_tokens, cached_tokens, latency_ms |
| Database query | DEBUG | query (sem dados sensíveis), duration_ms |
| EventBus publish | DEBUG | channel, event, session_id |
| Context trimming | WARN | tokens_removed, turns_removed, session_id |
| Erro de domínio | ERROR | exception class, message, correlation_id |
| Erro externo (MT5, NewsAPI) | ERROR | provider, status_code, retry_count |

### Métricas (futuro — Fase 2)

- `oracle_analysis_duration_seconds` — latência de análise completa
- `oracle_claude_tokens_total` — tokens consumidos por tipo
- `oracle_claude_cache_hit_ratio` — taxa de cache hit nos prompts
- `oracle_websocket_connections_active` — conexões ativas
- `oracle_replay_sessions_active` — sessões de replay ativas

---

## 15. Estratégia de Testes

### Pirâmide de Testes

```
         ┌──────────┐
         │   API    │  ← Poucos (TestClient, contrato HTTP)
        ┌┴──────────┴┐
        │Integration │  ← Médio (Testcontainers, real PostgreSQL + Redis)
       ┌┴────────────┴┐
       │     Unit     │  ← Muitos (puro Python, sem IO)
       └──────────────┘
```

### Testes Unitários (domain + application)

**Regras:**
- Zero I/O. Sem PostgreSQL, sem Redis, sem HTTP.
- Dependências externas = mocks via `unittest.mock` ou fixtures Pydantic.
- Um arquivo de teste por use case ou domain service.
- Nomenclatura: `test_<entidade>_<cenario>_<resultado_esperado>`.

```python
# tests/unit/domain/test_confidence_engine.py
def test_confidence_engine_high_alignment_returns_alta():
    engine = ConfidenceEngine()
    factors = {
        "trend_alignment": 0.9,
        "setup_quality": 0.8,
        "historical_match": 0.7,
        "macro_context": 0.8,
        "market_quality": 0.7,
        "emotional_state": 1.0,
    }
    result = engine.calculate(factors)
    assert result.score >= 80
    assert result.label == "MUITO ALTA"

def test_confidence_engine_low_alignment_returns_baixa():
    ...

def test_confidence_engine_missing_factors_uses_neutral_default():
    ...
```

### Testes de Integração

**Ferramentas:** `pytest-asyncio` + `testcontainers-python` para PostgreSQL e Redis reais.

```python
# tests/integration/test_trade_repository.py
@pytest.fixture
async def trade_repo(pg_container):
    engine = create_async_engine(pg_container.get_connection_url())
    return PostgresTradeRepository(engine)

async def test_save_and_retrieve_trade(trade_repo):
    trade = Trade(asset="PETR4", direction=Direction.LONG, ...)
    saved = await trade_repo.save(trade)
    retrieved = await trade_repo.get_by_id(saved.id)
    assert retrieved.asset == "PETR4"
```

### Testes de API

**Ferramentas:** `fastapi.testclient.TestClient` com repositórios mockados via override de dependency.

```python
# tests/api/test_analysis_router.py
def test_post_analysis_returns_result(client, mock_analysis_use_case):
    mock_analysis_use_case.execute.return_value = AnalysisResult(...)
    response = client.post("/api/v1/analysis", json={"asset": "PETR4", "timeframe": "M15"})
    assert response.status_code == 200
    assert "confidence_score" in response.json()
```

### Cobertura Mínima

| Camada | Cobertura mínima |
|---|---|
| `domain/` | 90% |
| `application/` | 80% |
| `infrastructure/` | 60% (foco em repos e clients) |
| `interface/api/` | 70% |

### CI (GitHub Actions)

```yaml
# .github/workflows/ci.yml
steps:
  - Ruff (lint)
  - Black (format check)
  - pytest unit (sem containers)
  - pytest integration (com testcontainers)
  - pytest api (TestClient)
  - coverage report (falha se < thresholds)
```

---

## 16. Decisões Arquiteturais Registradas (ADRs)

| # | Decisão | Justificativa |
|---|---|---|
| ADR-01 | PostgreSQL em vez de SQLite | Escalabilidade, tipagem nativa, suporte async, índices avançados para ML feature store |
| ADR-02 | Redis para EventBus | Pub/sub nativo, TTL nativo, compatível com WebSocket broadcast, suporta jobstore do APScheduler |
| ADR-03 | Sem frontend no MVP | Backend-first elimina retrabalho de API design; React pode ser adicionado sem mudar o backend |
| ADR-04 | Prompt caching obrigatório | System prompt é estático e grande — cache Anthropic reduz custo em ~80% em sessões longas |
| ADR-05 | MT5 atrás de Protocol | Windows-only; abstrair permite testes em qualquer OS e troca de provider no futuro |
| ADR-06 | Obsidian como integração opcional | Dependência de app desktop terceiro é risco de runtime; PostgreSQL é o source of truth |
| ADR-07 | Prompts como módulos versionados | Auditabilidade via git; sem surpresas quando o modelo muda; facilita A/B testing |
| ADR-08 | Replay Engine no MVP | Feature diferenciada que requer dados históricos — estruturar desde o início evita migração |
| ADR-09 | Alembic desde o primeiro schema | Dados de trades têm valor crescente com o tempo; migration-first evita perda de histórico |
| ADR-10 | Correlation IDs em todas as requests | Rastreabilidade end-to-end entre HTTP, EventBus, Claude API e logs |
| ADR-11 | Limite de ~200 linhas por arquivo | Arquivos pequenos são mais fáceis de testar, revisar e para IA navegar; evita acúmulo silencioso de responsabilidades |
| ADR-12 | `enums.py` e `events.py` separados das entities | Enums e eventos crescem independentemente das entidades; separar evita arquivo gigante e facilita import seletivo |
| ADR-13 | `contracts.py` em vez de `repositories.py` | Nome "contracts" comunica que é abstração/Protocol — não implementação; evita confusão com os repositories da infra |
| ADR-14 | `requests.py` / `responses.py` separados por contexto | Request schemas e response schemas têm ciclos de vida distintos; separar facilita versioning e testes de contrato |

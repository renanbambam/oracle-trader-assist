# Oracle Trader Assist

AI-powered trading assistant with real-time market analysis, context-aware memory, and structured decision support.

**Stack:** Python 3.12 · FastAPI · PostgreSQL 16 · Redis 7 · SQLAlchemy 2.0 async · Alembic · Pydantic v2

---

## Quick Start

### Prerequisites

- Docker + Docker Compose
- Python 3.12+
- `make` (optional but recommended)

### 1. Configure environment

```bash
cp .env.example .env
# Edit .env — set ANTHROPIC_API_KEY and POSTGRES_PASSWORD at minimum
```

### 2. Start infrastructure

```bash
make up          # starts PostgreSQL + Redis
# or
docker compose up postgres redis -d
```

### 3. Install dependencies and run locally

```bash
make dev         # pip install -r requirements*.txt + pre-commit install
uvicorn oracle.main:app --reload
```

### 4. Run with Docker (full stack)

```bash
docker compose up --build
```

### 5. Apply migrations

```bash
make migrate     # alembic upgrade head
```

### 6. Run tests

```bash
make test        # pytest with coverage
make test-unit   # unit tests only (no Docker needed)
```

---

## Project Structure

```
oracle-trader-assist/
├── src/
│   ├── oracle/
│   │   ├── config/
│   │   │   └── settings.py          # Pydantic BaseSettings — all env vars
│   │   ├── core/
│   │   │   ├── logging.py           # Loguru setup + correlation ID context var
│   │   │   └── ports.py             # Protocol interfaces (EventBus)
│   │   ├── domain/                  # Pure business logic — no framework imports
│   │   │   ├── market/
│   │   │   ├── analysis/
│   │   │   ├── trade/
│   │   │   ├── memory/
│   │   │   ├── replay/
│   │   │   └── analytics/
│   │   ├── application/             # Use cases — orchestrate domain + ports
│   │   │   ├── analysis/
│   │   │   ├── trade/
│   │   │   ├── memory/
│   │   │   ├── replay/
│   │   │   ├── analytics/
│   │   │   └── briefing/
│   │   ├── infrastructure/          # Framework/IO implementations
│   │   │   ├── database/
│   │   │   │   ├── base.py          # SQLAlchemy DeclarativeBase
│   │   │   │   └── connection.py    # Engine + session factory builders
│   │   │   └── redis/
│   │   │       ├── client.py        # aioredis client builder
│   │   │       └── event_bus.py     # RedisEventBus (implements EventBus port)
│   │   └── interface/
│   │       ├── api/
│   │       │   ├── app.py           # create_app() factory with lifespan
│   │       │   ├── dependencies.py  # FastAPI Depends() providers
│   │       │   ├── middleware.py    # CorrelationId + RequestLogging
│   │       │   └── routers/
│   │       │       └── health.py    # /health, /health/live, /health/ready
│   │       └── websocket/
│   │           ├── gateway.py       # WebSocketGateway — connection manager
│   │           └── broadcaster.py   # EventBroadcaster — Redis → WebSocket fan-out
│   └── prompts/
│       ├── versions.py              # PROMPT_REGISTRY — central prompt manifest
│       └── system/
│           └── oracle_system_v1.py  # Oracle identity + analysis format
├── tests/
│   ├── conftest.py                  # Fixtures: test_settings, app, async client
│   ├── api/
│   │   └── test_health.py
│   ├── unit/
│   └── integration/
├── migrations/
│   ├── env.py                       # Async Alembic env (asyncpg)
│   ├── script.py.mako
│   └── versions/
├── docker/
│   └── Dockerfile                   # Multi-stage: base → deps → dev/production
├── .github/
│   └── workflows/
│       └── ci.yml                   # Lint + test jobs with service containers
├── docker-compose.yml               # Dev stack: postgres + redis + app
├── docker-compose.test.yml          # Isolated test infrastructure
├── alembic.ini
├── pyproject.toml                   # Ruff, Black, pytest, coverage config
├── requirements.txt
├── requirements-dev.txt
├── Makefile
└── .env.example
```

---

## Architecture

The project follows **Clean Architecture** with strict one-way dependencies:

```
domain ← application ← infrastructure
                    ↑
              interface/api
```

- **domain/** — entities, value objects, repository protocols. Zero external dependencies.
- **application/** — use cases. Depend only on domain protocols.
- **infrastructure/** — SQLAlchemy models, Redis client, Alembic migrations.
- **interface/** — FastAPI routes, WebSocket gateway, middleware.

**Bounded Contexts:** Market · Analysis · Trade · Memory · Replay · Analytics

**Event Flow:** `RedisEventBus.publish()` → Redis pub/sub → `EventBroadcaster.run()` → `WebSocketGateway.broadcast_to_channel()` → connected clients

---

## Available Commands

```bash
make help            # list all targets
make dev             # install all deps + pre-commit hooks
make up              # start postgres + redis
make down            # stop and remove containers
make logs            # tail docker compose logs
make migrate         # alembic upgrade head
make migrate-down    # alembic downgrade -1
make migrate-gen m='describe change'  # generate new migration
make test            # pytest --cov
make test-unit       # tests/unit/ only
make test-integration  # tests/integration/ only
make lint            # ruff check
make format          # black + ruff --fix
make check           # CI mode: lint + format check
make clean           # remove __pycache__, .coverage, dist
```

---

## Environment Variables

See `.env.example` for all variables with descriptions. Required at minimum:

| Variable | Description |
|---|---|
| `ANTHROPIC_API_KEY` | Claude API key |
| `POSTGRES_PASSWORD` | PostgreSQL password |
| `ENVIRONMENT` | `development` / `staging` / `production` / `test` |

---

## API

Base URL: `http://localhost:8000`

| Method | Path | Description |
|---|---|---|
| GET | `/api/v1/health` | Service status |
| GET | `/api/v1/health/live` | Liveness probe |
| GET | `/api/v1/health/ready` | Readiness probe (checks DB + Redis) |
| WS | `/ws` | WebSocket gateway |

**Correlation IDs:** Every request accepts `X-Correlation-ID` header and echoes it back. If absent, a UUID is generated and returned.

---

## WebSocket Channels

Connect to `ws://localhost:8000/ws` and send:

```json
{"type": "subscribe", "channels": ["market", "analysis", "ai_stream"]}
```

Available channels: `market` · `analysis` · `ai_stream` · `trading` · `replay` · `system`

---

## Development Notes

- **Pre-commit hooks** enforce Ruff + Black on every commit.
- **Correlation IDs** propagate through all log lines via `contextvars.ContextVar`.
- **Migrations** run async via `asyncio.run()` in `migrations/env.py` — safe with asyncpg.
- **Test client** uses `httpx.AsyncClient` + `ASGITransport` (no real server needed for API tests).
- **Settings** are singletons via `@lru_cache` — override in tests by passing a `Settings` instance to `create_app()`.

.PHONY: help install dev up down logs migrate migrate-down test test-unit test-integration lint format check clean

# ─────────────────────────────────────────────────────────────────────────────
# Help
# ─────────────────────────────────────────────────────────────────────────────
help:
	@echo ""
	@echo "Oracle Trader Assist — Development Commands"
	@echo "─────────────────────────────────────────────"
	@echo "  make install          Install production dependencies"
	@echo "  make dev              Install all dependencies + pre-commit"
	@echo ""
	@echo "  make up               Start Docker services (postgres + redis)"
	@echo "  make down             Stop Docker services"
	@echo "  make logs             Tail application logs"
	@echo ""
	@echo "  make migrate          Run pending Alembic migrations"
	@echo "  make migrate-down     Rollback last migration"
	@echo "  make migrate-gen m='' Generate migration: make migrate-gen m='add_trades_table'"
	@echo ""
	@echo "  make test             Run all tests with coverage"
	@echo "  make test-unit        Run unit tests only (fast, no Docker needed)"
	@echo "  make test-integration Run integration tests (requires Docker)"
	@echo ""
	@echo "  make lint             Run Ruff linter"
	@echo "  make format           Format code with Black + Ruff"
	@echo "  make check            Run lint + format check (CI mode)"
	@echo ""
	@echo "  make clean            Remove caches and build artifacts"
	@echo ""

# ─────────────────────────────────────────────────────────────────────────────
# Dependencies
# ─────────────────────────────────────────────────────────────────────────────
install:
	pip install -r requirements.txt

dev:
	pip install -r requirements.txt -r requirements-dev.txt
	pre-commit install
	@echo "Dev environment ready."

# ─────────────────────────────────────────────────────────────────────────────
# Docker
# ─────────────────────────────────────────────────────────────────────────────
up:
	docker-compose up -d postgres redis
	@echo "Waiting for services to be healthy..."
	@sleep 2

down:
	docker-compose down

logs:
	docker-compose logs -f app

# ─────────────────────────────────────────────────────────────────────────────
# Database migrations
# ─────────────────────────────────────────────────────────────────────────────
migrate:
	PYTHONPATH=src alembic upgrade head

migrate-down:
	PYTHONPATH=src alembic downgrade -1

migrate-gen:
	PYTHONPATH=src alembic revision --autogenerate -m "$(m)"

# ─────────────────────────────────────────────────────────────────────────────
# Tests
# ─────────────────────────────────────────────────────────────────────────────
test:
	PYTHONPATH=src pytest tests/ --cov=oracle --cov-report=term-missing --cov-report=xml

test-unit:
	PYTHONPATH=src pytest tests/unit/ -v

test-integration:
	PYTHONPATH=src pytest tests/integration/ -v

# ─────────────────────────────────────────────────────────────────────────────
# Code Quality
# ─────────────────────────────────────────────────────────────────────────────
lint:
	ruff check src tests

format:
	black src tests
	ruff check --fix src tests

check:
	ruff check src tests
	black --check src tests

# ─────────────────────────────────────────────────────────────────────────────
# Clean
# ─────────────────────────────────────────────────────────────────────────────
clean:
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .pytest_cache -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .ruff_cache -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .mypy_cache -exec rm -rf {} + 2>/dev/null || true
	find . -name "*.pyc" -delete 2>/dev/null || true
	rm -f coverage.xml .coverage
	@echo "Clean complete."

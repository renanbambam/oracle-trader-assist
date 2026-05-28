# ─────────────────────────────────────────────────────────────────────────────
# Oracle Trader Assist — Multi-stage Dockerfile
#
# Stages:
#   base         → Python runtime with shared env vars
#   dependencies → Production dependencies installed
#   dev          → Dev dependencies added (for local development)
#   production   → Minimal production image
# ─────────────────────────────────────────────────────────────────────────────

# ── Base ──────────────────────────────────────────────────────────────────────
FROM python:3.12-slim AS base

WORKDIR /app

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PYTHONPATH=/app/src

# ── Dependencies ──────────────────────────────────────────────────────────────
FROM base AS dependencies

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# ── Development ───────────────────────────────────────────────────────────────
FROM dependencies AS dev

COPY requirements-dev.txt .
RUN pip install --no-cache-dir -r requirements-dev.txt

# Copy source (mounted as volume in docker-compose for hot reload)
COPY . .

CMD ["uvicorn", "oracle.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]

# ── Production ────────────────────────────────────────────────────────────────
FROM dependencies AS production

# Copy only what's needed to run
COPY src/ src/
COPY migrations/ migrations/
COPY alembic.ini .

# Non-root user for security
RUN groupadd -r oracle && useradd -r -g oracle oracle
USER oracle

EXPOSE 8000

CMD ["uvicorn", "oracle.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "2"]

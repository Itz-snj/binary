# syntax=docker/dockerfile:1.7

# ── Stage 1: build the React dashboard ─────────────────────────────────
FROM oven/bun:1.2-alpine AS web-builder

WORKDIR /web
COPY web/package.json web/bun.lock ./
RUN bun install --frozen-lockfile

COPY web/ ./
RUN bun run build


# ── Stage 2: Python runtime ────────────────────────────────────────────
FROM python:3.13-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# git is needed by some PyGithub paths; libpq is needed by psycopg.
RUN apt-get update \
    && apt-get install -y --no-install-recommends git libpq5 curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt ./
RUN pip install -r requirements.txt

# Copy the engine source. .dockerignore keeps venv/node_modules/db files out.
COPY . ./

# Drop the built React app into the place main.py serves from.
COPY --from=web-builder /web/dist ./web/dist

EXPOSE 8000

# Run Alembic migrations on container start, then launch the server.
CMD ["sh", "-c", "alembic upgrade head && uvicorn main:app --host 0.0.0.0 --port 8000"]

# Stage 1: Build React 19 + TypeScript Frontend with Bun
FROM oven/bun:1.2-alpine AS frontend-builder
WORKDIR /app/frontend
COPY frontend/package.json frontend/bun.lock* ./
RUN bun install
COPY frontend/ ./
RUN bun run build

# Stage 2: Python 3.12 FastAPI Runtime managed by uv
FROM python:3.12-slim
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    GOOGLE_API_USE_CLIENT_CERTIFICATE=false \
    GOOGLE_CLOUD_PROJECT=adhish-base-project-1 \
    PORT=8080

WORKDIR /app

# Copy specifications and agent skills
COPY 0-spec ./0-spec
COPY .agents ./.agents
COPY .mcp.json ./.mcp.json

# Install backend dependencies via uv
WORKDIR /app/backend
COPY backend/pyproject.toml backend/uv.lock ./
RUN uv sync --frozen --no-dev

# Copy backend source and tests
COPY backend/app ./app
COPY backend/tests ./tests

# Copy built frontend static bundle into /app/frontend/dist
COPY --from=frontend-builder /app/frontend/dist /app/frontend/dist

EXPOSE 8080

CMD ["sh", "-c", "uv run uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8080}"]

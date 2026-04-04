# syntax=docker/dockerfile:1.7

FROM python:3.12-slim AS deps
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/
WORKDIR /app
ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy
COPY pyproject.toml uv.lock README.md ./
RUN uv sync --extra frontend --no-dev --no-install-project

FROM deps AS build
COPY src ./src
RUN uv sync --extra frontend --no-dev

FROM python:3.12-slim AS runtime
WORKDIR /app
COPY --from=build /app/.venv /app/.venv
COPY --from=build /app/src /app/src
ENV PATH="/app/.venv/bin:$PATH"
EXPOSE 7777
CMD ["gunicorn", "livetrivia._wsgi_app:server", "--bind", "0.0.0.0:7777", "--workers", "2"]

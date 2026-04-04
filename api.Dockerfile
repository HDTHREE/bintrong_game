# syntax=docker/dockerfile:1.7

FROM python:3.12-slim AS deps
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/
WORKDIR /app
ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy
COPY pyproject.toml uv.lock README.md ./
RUN uv sync --extra backend --no-dev --no-install-project

FROM deps AS build
COPY src ./src
RUN uv sync --extra backend --no-dev

FROM python:3.12-slim AS runtime
WORKDIR /app
COPY --from=build /app/.venv /app/.venv
COPY --from=build /app/src /app/src
ENV PATH="/app/.venv/bin:$PATH"
EXPOSE 8000
CMD ["python", "-m", "uvicorn", "livetrivia._api:api", "--host", "0.0.0.0", "--port", "8000"]

FROM python:3.12-slim-bookworm AS builder

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy

WORKDIR /app

RUN python -m pip install --no-cache-dir uv==0.12.17

COPY pyproject.toml uv.lock ./
RUN uv sync --locked --no-dev --no-install-project

COPY app ./app
RUN uv sync --locked --no-dev

FROM python:3.12-slim-bookworm AS runtime

ENV PATH="/app/.venv/bin:$PATH" \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

RUN groupadd --system watchai \
    && useradd --system --gid watchai --home-dir /app watchai \
    && mkdir -p /app/private-media /app/private-renders \
    && chown watchai:watchai /app/private-media /app/private-renders

COPY --from=builder --chown=watchai:watchai /app/.venv /app/.venv
COPY --chown=watchai:watchai app ./app
COPY --chown=watchai:watchai alembic ./alembic
COPY --chown=watchai:watchai alembic.ini ./alembic.ini

USER watchai
EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]

# syntax=docker/dockerfile:1
FROM ghcr.io/astral-sh/uv:0.9.7@sha256:ba4857bf2a068e9bc0e64eed8563b065908a4cd6bfb66b531a9c424c8e25e142 AS uv
FROM python:3.14.0-slim-bookworm@sha256:d13fa0424035d290decef3d575cea23d1b7d5952cdf429df8f5542c71e961576 AS dependencies

COPY --from=uv /uv /usr/local/bin/uv
ENV UV_PYTHON_DOWNLOADS=never UV_LINK_MODE=copy
WORKDIR /app
COPY pyproject.toml uv.lock .python-version README.md ./
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --locked --no-dev --no-install-project --python /usr/local/bin/python

FROM dependencies AS test-dependencies
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --locked --no-install-project --python /usr/local/bin/python

FROM python:3.14.0-slim-bookworm@sha256:d13fa0424035d290decef3d575cea23d1b7d5952cdf429df8f5542c71e961576 AS runtime
ENV PATH="/app/.venv/bin:$PATH" \
    PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PYDANTIC_AI_NO_BANNER=1
WORKDIR /app
RUN useradd --create-home --uid 10001 app \
    && mkdir /reports && chown app:app /app /reports
COPY --from=dependencies /app/.venv /app/.venv
COPY app ./app
COPY data ./data
COPY eval/__init__.py eval/run.py eval/checks.py eval/cases.json eval/holdout_cases.json ./eval/
COPY pyproject.toml uv.lock README.md ./
USER app
ENTRYPOINT ["python", "-m", "app.main"]
CMD ["--help"]

FROM runtime AS tests
COPY --from=test-dependencies /app/.venv /app/.venv
COPY tests ./tests
ENTRYPOINT ["python", "-m", "pytest"]
CMD ["-q"]

FROM runtime AS app

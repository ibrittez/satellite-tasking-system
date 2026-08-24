FROM python:3.12-slim AS base

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

RUN useradd --create-home app

WORKDIR /app

COPY pyproject.toml ./
COPY src ./src
RUN pip install --no-cache-dir .

COPY data ./data

# =======================================
# test: `docker build --target test`
# =======================================

FROM base AS test

RUN pip install --no-cache-dir ".[dev]"
COPY tests ./tests

ENTRYPOINT ["pytest"]
CMD []

# =======================================
# runtime: default target
# =======================================

FROM base AS runtime

USER app

ENTRYPOINT ["sat-task-system", "--tasks", "/app/data/spec_tasks.json"]
CMD []

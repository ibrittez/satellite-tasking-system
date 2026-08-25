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
# web: `docker build --target web`
# =======================================

FROM base AS web

RUN pip install --no-cache-dir ".[web]"

USER app

EXPOSE 5000

# 0.0.0.0, or the port publish reaches a server bound to the container's loopback.
ENTRYPOINT ["sat-task-system", "--web", "--host", "0.0.0.0", \
            "--tasks", "/app/data/spec_tasks.json"]
CMD []

# =======================================
# runtime: default target, so it stays last
# =======================================

FROM base AS runtime

USER app

ENTRYPOINT ["sat-task-system", "--tasks", "/app/data/spec_tasks.json"]
CMD []

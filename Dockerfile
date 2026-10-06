ARG PYTHON_IMAGE=python:3.12-slim-bookworm@sha256:782412e85d0f0984994c290652577d4018aff08145c85b262bb63dc0c7522254
FROM ${PYTHON_IMAGE} AS builder
COPY --from=ghcr.io/astral-sh/uv:0.11.8@sha256:3b7b60a81d3c57ef471703e5c83fd4aaa33abcd403596fb22ab07db85ae91347 /uv /usr/local/bin/uv
ENV UV_PYTHON_DOWNLOADS=never UV_LINK_MODE=copy
WORKDIR /app
COPY pyproject.toml uv.lock ./
COPY src ./src
RUN --mount=type=secret,id=proxy_ca \
    if [ -f /run/secrets/proxy_ca ]; then \
      SSL_CERT_FILE=/run/secrets/proxy_ca uv sync --locked --no-dev --no-editable; \
    else uv sync --locked --no-dev --no-editable; fi

FROM ${PYTHON_IMAGE} AS runtime
ENV PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1 PATH="/app/.venv/bin:$PATH"
WORKDIR /app
RUN groupadd --gid 10001 radar \
    && useradd --no-log-init --create-home --uid 10001 --gid 10001 radar \
    && mkdir -p /app/data \
    && chown radar:radar /app/data
COPY --chown=10001:10001 --from=builder /app/.venv /app/.venv
COPY --chown=10001:10001 config ./config
COPY --chown=10001:10001 tests/fixtures/jobs.json ./tests/fixtures/jobs.json
COPY --chown=10001:10001 scripts/smoke_container.py ./scripts/smoke_container.py
COPY --chown=10001:10001 scripts/cloud_runtime.py ./scripts/cloud_runtime.py
USER 10001:10001
HEALTHCHECK --interval=5m --timeout=30s --start-period=10m --retries=3 \
    CMD ["trading-radar", "health"]
ENTRYPOINT ["trading-radar"]
CMD ["watch"]

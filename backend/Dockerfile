FROM python:3.12-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# ── deps ──────────────────────────────────────────────────────────────────────
FROM base AS builder
WORKDIR /app
COPY pyproject.toml ./
RUN pip install --upgrade pip && pip install -e .

# ── runner ────────────────────────────────────────────────────────────────────
FROM base AS runner
WORKDIR /app

RUN addgroup --system --gid 1001 appgroup && \
    adduser  --system --uid 1001 --ingroup appgroup appuser

COPY --from=builder /usr/local/lib/python3.12/site-packages /usr/local/lib/python3.12/site-packages
COPY --from=builder /usr/local/bin/uvicorn                  /usr/local/bin/uvicorn
COPY app ./app
COPY migrations ./migrations
COPY alembic.ini ./

RUN chown -R appuser:appgroup /app
USER appuser

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "2"]

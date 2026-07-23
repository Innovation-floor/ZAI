# syntax=docker/dockerfile:1.7
# ---- builder -------------------------------------------------------------
FROM python:3.12-slim AS builder
ENV PIP_NO_CACHE_DIR=1 PIP_DISABLE_PIP_VERSION_CHECK=1
WORKDIR /build
COPY requirements.txt .
RUN python -m venv /opt/venv && /opt/venv/bin/pip install -r requirements.txt

# ---- runtime -------------------------------------------------------------
FROM python:3.12-slim AS runtime
ENV PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1 PATH="/opt/venv/bin:$PATH"
RUN apt-get update && apt-get install -y --no-install-recommends curl \
    && rm -rf /var/lib/apt/lists/* \
    && groupadd --system --gid 10001 zai \
    && useradd --system --uid 10001 --gid zai --home /app zai
COPY --from=builder /opt/venv /opt/venv
WORKDIR /app
COPY --chown=zai:zai app ./app
USER zai
EXPOSE 8000
HEALTHCHECK --interval=20s --timeout=4s --start-period=15s --retries=3 \
  CMD curl -fsS http://localhost:8000/api/health/live || exit 1
# Single worker is REQUIRED: sessions and uploaded documents live in process
# memory (app/core/engine.py SessionStore). With two workers an upload lands in
# one process and the follow-up question in the other, producing a 404.
# Move SessionStore to Redis before raising this.
CMD ["uvicorn","app.main:app","--host","0.0.0.0","--port","8000","--workers","1","--proxy-headers"]
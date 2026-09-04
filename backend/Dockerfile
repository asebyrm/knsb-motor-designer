# syntax=docker/dockerfile:1
FROM python:3.11-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# system deps for psycopg / reportlab; fonts-dejavu-core gives the PDF report a
# Unicode font so Turkish letters (ı, ğ, ş, İ, Ğ, Ş) render (see core/export/fonts.py)
RUN apt-get update && apt-get install -y --no-install-recommends \
        build-essential libpq5 curl fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/*

COPY backend/ ./backend/
COPY locales/ ./locales/
RUN pip install --upgrade pip && pip install -e "./backend[api]"

WORKDIR /app/backend
ENV LOCALES_DIR=/app/locales \
    OUTPUTS_DIR=/app/outputs \
    API_WORKERS=4
RUN mkdir -p /app/outputs

EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s --retries=3 \
    CMD curl -fsS http://localhost:8000/api/health || exit 1

# Gunicorn manages N Uvicorn workers (Section 12.2 - never a single worker in prod)
CMD ["sh", "-c", "gunicorn api.main:app -k uvicorn.workers.UvicornWorker \
     -w ${API_WORKERS:-4} -b 0.0.0.0:8000 --timeout 120 --graceful-timeout 30 \
     || uvicorn api.main:app --host 0.0.0.0 --port 8000 --workers ${API_WORKERS:-4}"]

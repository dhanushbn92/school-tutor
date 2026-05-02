# Cloud Run image for the FastAPI backend.
#
# Build (from repo root):
#   docker build -t school-tuter-api .
# Run locally:
#   docker run --rm -p 8080:8080 -e PORT=8080 \
#     -e DATABASE_URL=... -e ALLOWED_ORIGINS=http://localhost:5173 \
#     school-tuter-api
#
# Cloud Run injects $PORT (default 8080) and expects the container to listen
# on 0.0.0.0:$PORT. Containers are stateless — artifacts must live in GCS.

FROM python:3.12-slim AS base

# Avoid .pyc clutter, force unbuffered logs (Cloud Run captures stdout line-by-line).
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# System deps:
#  - libpq for psycopg (binary wheel still needs the runtime lib in slim)
#  - curl for the optional Cloud Run startup probe
#  - tini as PID 1 so signals propagate cleanly to gunicorn
RUN apt-get update \
 && apt-get install -y --no-install-recommends \
        libpq5 \
        curl \
        tini \
 && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python deps first so the layer caches across code changes.
COPY requirements.txt ./
RUN pip install -r requirements.txt

# App source. Tests / data / db are excluded via .dockerignore.
COPY app ./app
COPY migrations ./migrations
COPY alembic.ini ./alembic.ini

# Drop privileges. Cloud Run already runs the container in a sandbox, but
# defence-in-depth is cheap.
RUN useradd --system --uid 1001 --gid 0 appuser \
 && chown -R appuser:0 /app
USER appuser

# Cloud Run sets $PORT; default to 8080 for local runs.
ENV PORT=8080
EXPOSE 8080

# tini → gunicorn → uvicorn workers. Workers=2 is a sane default for the
# 1-vCPU / 512MB Cloud Run shape; bump via WEB_CONCURRENCY env var.
ENTRYPOINT ["/usr/bin/tini", "--"]
CMD exec gunicorn app.main:app \
    --bind 0.0.0.0:${PORT} \
    --workers ${WEB_CONCURRENCY:-2} \
    --worker-class uvicorn.workers.UvicornWorker \
    --timeout 120 \
    --access-logfile - \
    --error-logfile -

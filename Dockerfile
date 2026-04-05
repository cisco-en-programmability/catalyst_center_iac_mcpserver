FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    RUNNER_ARTIFACT_ROOT=/var/lib/catalyst-center-iac-mcp/artifacts \
    REDIS_URL=redis://redis:6379/0 \
    CATALYSTCENTER_VERSION=2.3.7.9

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    git \
    openssh-client \
    && rm -rf /var/lib/apt/lists/*

RUN useradd --create-home --home-dir /home/appuser --shell /usr/sbin/nologin appuser \
    && mkdir -p /app "${RUNNER_ARTIFACT_ROOT}" \
    && chown -R appuser:appuser /app "${RUNNER_ARTIFACT_ROOT}"

WORKDIR /app

COPY pyproject.toml README.md ./
RUN pip install --upgrade pip setuptools wheel \
    && pip install . \
    && ansible-galaxy collection install cisco.catalystcenter

COPY server.py runner_engine.py transformers.py redis_store.py settings.py models.py ./

USER appuser
EXPOSE 8000

CMD ["uvicorn", "server:app", "--host", "0.0.0.0", "--port", "8000"]

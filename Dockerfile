FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    SERVER_HOST=0.0.0.0 \
    SERVER_PORT=8000 \
    SERVER_WORKERS=1 \
    RUNNER_ARTIFACT_ROOT=/var/lib/catalyst-center-iac-mcp/artifacts \
    REDIS_URL=redis://redis:6379/0 \
    CATALYSTCENTER_VERSION=2.3.7.9

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    ca-certificates \
    curl \
    git \
    openssh-client \
    && rm -rf /var/lib/apt/lists/*

RUN useradd --create-home --home-dir /home/appuser --shell /usr/sbin/nologin appuser \
    && mkdir -p /app "${RUNNER_ARTIFACT_ROOT}" \
    && chown -R appuser:appuser /app "${RUNNER_ARTIFACT_ROOT}"

WORKDIR /app

COPY pyproject.toml README.md LICENSE requirements.yml tool_catalog.yaml catalyst_center_clusters.yaml ./
COPY server.py runner_engine.py transformers.py redis_store.py settings.py models.py cluster_registry.py tool_registry.py ./
RUN pip install --upgrade pip setuptools wheel \
    && pip install "ansible-core>=2.16,<2.19" \
    && pip install . \
    && ansible-galaxy collection install -r requirements.yml

USER appuser
EXPOSE 8000

CMD ["catalyst-center-iac-mcp"]

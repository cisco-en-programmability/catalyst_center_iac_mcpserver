from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = "catalyst_center_iac_mcp"
    app_version: str = "0.1.0"
    server_host: str = "0.0.0.0"
    server_port: int = 8000
    server_workers: int = 1
    proxy_headers: bool = True
    forwarded_allow_ips: str = "*"
    tls_certfile: str | None = None
    tls_keyfile: str | None = None
    tls_ca_certs: str | None = None
    mcp_path: str = "/mcp"
    mcp_transport: Literal["http", "sse"] = "http"
    redis_url: str = "redis://127.0.0.1:6379/0"
    runner_artifact_root: Path = Field(
        default_factory=lambda: Path("/tmp/catalyst_center_iac_mcp/artifacts")
    )
    runner_timeout_seconds: int = 3600
    runner_status_poll_seconds: float = 1.0
    task_ttl_seconds: int = 86400
    task_poll_interval_ms: int = 2000
    ansible_collection_namespace: str = "cisco.catalystcenter"
    catalystcenter_host: str | None = None
    catalystcenter_username: str | None = None
    catalystcenter_password: str | None = None
    catalystcenter_verify_ssl: bool = True
    catalystcenter_port: int = 443
    catalystcenter_version: str = "2.3.7.9"
    oauth_enabled: bool = False
    oauth_issuer: str | None = None
    oauth_audience: str | None = None
    oauth_jwks_url: str | None = None
    allow_anonymous_healthcheck: bool = True

    def tenant_env_name(self, tenant_id: str, field_name: str) -> str:
        tenant = tenant_id.strip().upper().replace("-", "_")
        return f"CATALYSTCENTER_{tenant}_{field_name}"


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    settings = Settings()
    settings.runner_artifact_root.mkdir(parents=True, exist_ok=True)
    return settings

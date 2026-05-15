from __future__ import annotations

from pathlib import Path

import yaml
from pydantic import BaseModel, ConfigDict, Field, model_validator


def _normalize_selector(value: str) -> str:
    return "".join(ch.lower() for ch in value if ch.isalnum())


class CatalystCenterCluster(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str
    label: str | None = None
    host: str
    version: str
    location: str | None = None
    enabled: bool = True
    default: bool = False
    port: int = 443
    verify_ssl: bool = True
    credential_key: str | None = None

    @property
    def slug(self) -> str:
        base = self.credential_key or self.label or self.name
        return _normalize_selector(base)

    def matches(self, selector: str) -> bool:
        normalized_selector = _normalize_selector(selector)
        candidates = [self.name, self.host, self.slug]
        if self.label:
            candidates.append(self.label)
        if self.location:
            candidates.append(self.location)
        return any(_normalize_selector(candidate) == normalized_selector for candidate in candidates)


class CatalystCenterClusterCatalog(BaseModel):
    model_config = ConfigDict(extra="forbid")

    catalyst_centers: list[CatalystCenterCluster] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_unique_selectors(self) -> "CatalystCenterClusterCatalog":
        seen: dict[str, str] = {}
        for cluster in self.catalyst_centers:
            selectors = {cluster.slug, _normalize_selector(cluster.name), _normalize_selector(cluster.host)}
            if cluster.label:
                selectors.add(_normalize_selector(cluster.label))
            if cluster.location:
                selectors.add(_normalize_selector(cluster.location))
            for selector in selectors:
                previous = seen.get(selector)
                if previous and previous != cluster.name:
                    raise ValueError(
                        f"duplicate Catalyst Center selector `{selector}` for `{previous}` and `{cluster.name}`"
                    )
                seen[selector] = cluster.name
        default_clusters = [cluster.name for cluster in self.catalyst_centers if cluster.default]
        if len(default_clusters) > 1:
            raise ValueError(
                f"multiple default Catalyst Center clusters configured: {', '.join(default_clusters)}"
            )
        if default_clusters:
            default_cluster = next(cluster for cluster in self.catalyst_centers if cluster.default)
            if not default_cluster.enabled:
                raise ValueError(
                    f"default Catalyst Center cluster `{default_cluster.name}` must be enabled"
                )
        return self

    def enabled_clusters(self) -> list[CatalystCenterCluster]:
        return [cluster for cluster in self.catalyst_centers if cluster.enabled]

    def default_cluster(self) -> CatalystCenterCluster | None:
        for cluster in self.enabled_clusters():
            if cluster.default:
                return cluster
        enabled = self.enabled_clusters()
        if len(enabled) == 1:
            return enabled[0]
        return None

    def resolve(self, selector: str | None) -> CatalystCenterCluster | None:
        if not selector:
            return self.default_cluster()
        for cluster in self.enabled_clusters():
            if cluster.matches(selector):
                return cluster
        raise ValueError(
            f"No enabled Catalyst Center cluster matched selector `{selector}`"
        )


def load_cluster_catalog(path: Path) -> CatalystCenterClusterCatalog:
    if not path.exists():
        return CatalystCenterClusterCatalog()
    raw = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    if not isinstance(raw, dict):
        raise ValueError(f"cluster catalog must decode to a dictionary: {path}")
    return CatalystCenterClusterCatalog.model_validate(raw)

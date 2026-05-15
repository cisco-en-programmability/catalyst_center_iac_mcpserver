from pathlib import Path

import pytest

from cluster_registry import load_cluster_catalog


def test_cluster_catalog_loads_and_filters_enabled_clusters():
    catalog = load_cluster_catalog(Path(__file__).resolve().parents[1] / "catalyst_center_clusters.yaml")

    enabled_names = [cluster.name for cluster in catalog.enabled_clusters()]

    assert enabled_names == ["Portland"]


def test_cluster_catalog_resolves_by_name_label_and_location():
    catalog = load_cluster_catalog(Path(__file__).resolve().parents[1] / "catalyst_center_clusters.yaml")

    assert catalog.resolve("Portland").name == "Portland"
    assert catalog.resolve("dev").name == "Portland"
    assert catalog.resolve("10.195.243.38").name == "Portland"


def test_cluster_catalog_uses_default_when_selector_is_omitted():
    catalog = load_cluster_catalog(Path(__file__).resolve().parents[1] / "catalyst_center_clusters.yaml")

    assert catalog.resolve(None).name == "Portland"


def test_cluster_catalog_rejects_multiple_default_clusters(tmp_path: Path):
    cluster_file = tmp_path / "clusters.yaml"
    cluster_file.write_text(
        """catalyst_centers:
  - name: "Portland"
    label: "DEV"
    host: "portland.example.com"
    version: "2.3.7.9"
    enabled: true
    default: true
  - name: "San Jose"
    label: "SAN"
    host: "san.example.com"
    version: "2.3.7.9"
    enabled: true
    default: true
""",
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="multiple default Catalyst Center clusters configured"):
        load_cluster_catalog(cluster_file)

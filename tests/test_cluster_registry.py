from pathlib import Path

from cluster_registry import load_cluster_catalog


def test_cluster_catalog_loads_and_filters_enabled_clusters():
    catalog = load_cluster_catalog(Path(__file__).resolve().parents[1] / "catalyst_center_clusters.yaml")

    enabled_names = [cluster.name for cluster in catalog.enabled_clusters()]

    assert enabled_names == ["Portland"]


def test_cluster_catalog_resolves_by_name_label_and_location():
    catalog = load_cluster_catalog(Path(__file__).resolve().parents[1] / "catalyst_center_clusters.yaml")

    assert catalog.resolve("Portland").name == "Portland"
    assert catalog.resolve("dev").name == "Portland"
    assert catalog.resolve("Portland-center.domain.com").name == "Portland"

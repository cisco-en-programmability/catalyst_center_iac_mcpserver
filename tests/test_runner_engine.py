from pathlib import Path

import pytest

import runner_engine
from redis_store import InMemoryTaskStore
from runner_engine import RunnerEngine
from settings import Settings


@pytest.mark.asyncio
async def test_submit_workflow_creates_submitted_task(tmp_path: Path):
    settings = Settings(
        runner_artifact_root=tmp_path,
        catalystcenter_host="https://catc.example.com",
        catalystcenter_username="svc",
        catalystcenter_password="secret",
    )
    engine = RunnerEngine(settings, store=InMemoryTaskStore())

    submission = await engine.submit_workflow(
        tool_name="provision_site",
        module_name="site_workflow_manager",
        tenant_id="default",
        state="merged",
        config=[{"type": "area", "site": {"area": {"name": "USA", "parent_name": "Global"}}}],
    )

    record = await engine.get_task(submission.task_id)

    assert submission.status == "submitted"
    assert record is not None
    assert record.status.value in {"submitted", "running"}
    assert record.module_name == "site_workflow_manager"


@pytest.mark.asyncio
async def test_runner_files_use_cisco_catalystcenter_only(tmp_path: Path):
    settings = Settings(
        runner_artifact_root=tmp_path,
        catalystcenter_host="https://catc.example.com",
        catalystcenter_username="svc",
        catalystcenter_password="secret",
    )
    engine = RunnerEngine(settings, store=InMemoryTaskStore())

    await engine.submit_workflow(
        tool_name="provision_site",
        module_name="site_workflow_manager",
        tenant_id="default",
        state="merged",
        config=[{"type": "area", "site": {"area": {"name": "USA", "parent_name": "Global"}}}],
    )

    playbook = next(tmp_path.glob("*/project/playbook.yml")).read_text(encoding="utf-8")
    envvars = next(tmp_path.glob("*/env/envvars")).read_text(encoding="utf-8")
    sitecustomize = next(tmp_path.glob("*/env/sitecustomize.py")).read_text(encoding="utf-8")

    assert "cisco.catalystcenter.site_workflow_manager" in playbook
    assert "cisco.dnac" not in playbook
    assert "PYTHONPATH" in envvars
    assert "ANSIBLE_STDOUT_CALLBACK" not in envvars
    assert "CatalystCenterAPI" in sitecustomize
    assert "state: merged" in playbook
    assert "config_verify: true" in playbook


@pytest.mark.asyncio
async def test_submit_module_supports_playbook_config_generator_args(tmp_path: Path):
    settings = Settings(
        runner_artifact_root=tmp_path,
        catalystcenter_host="https://catc.example.com",
        catalystcenter_username="svc",
        catalystcenter_password="secret",
    )
    engine = RunnerEngine(settings, store=InMemoryTaskStore())

    submission = await engine.submit_module(
        tool_name="generate_site_config",
        module_name="site_playbook_config_generator",
        tenant_id="default",
        module_args={
            "state": "gathered",
            "file_mode": "overwrite",
            "config": {
                "component_specific_filters": {
                    "site": [
                        {"parent_name_hierarchy": "Global/USA/SAN JOSE", "site_type": ["building", "floor"]}
                    ]
                }
            },
        },
    )

    record = await engine.get_task(submission.task_id)
    playbook = next(tmp_path.glob("*/project/playbook.yml")).read_text(encoding="utf-8")

    assert submission.status == "submitted"
    assert record is not None
    assert record.module_name == "site_playbook_config_generator"
    assert record.module_args["state"] == "gathered"
    assert "cisco.catalystcenter.site_playbook_config_generator" in playbook
    assert "state: gathered" in playbook
    assert "file_mode: overwrite" in playbook
    assert "Global/USA/SAN JOSE" in playbook


@pytest.mark.asyncio
async def test_submit_module_sets_default_catalystcenter_log_path(tmp_path: Path):
    settings = Settings(
        runner_artifact_root=tmp_path,
        catalystcenter_host="https://catc.example.com",
        catalystcenter_username="svc",
        catalystcenter_password="secret",
    )
    engine = RunnerEngine(settings, store=InMemoryTaskStore())

    submission = await engine.submit_module(
        tool_name="inventory",
        module_name="inventory_workflow_manager",
        tenant_id="default",
        module_args={
            "state": "merged",
            "config_verify": True,
            "config": [{"inventory": [{"device_ips": ["10.10.10.1"]}]}],
        },
    )

    record = await engine.get_task(submission.task_id)
    playbook = next(tmp_path.glob("*/project/playbook.yml")).read_text(encoding="utf-8")
    expected_log_path = tmp_path / submission.task_id / "catalystcenter.log"

    assert record is not None
    assert record.module_args["catalystcenter_log"] is True
    assert record.module_args["catalystcenter_log_append"] is False
    assert record.module_args["catalystcenter_log_file_path"] == str(expected_log_path)
    assert str(expected_log_path) in playbook


@pytest.mark.asyncio
async def test_submit_module_passes_verbosity_and_log_level(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    settings = Settings(
        runner_artifact_root=tmp_path,
        catalystcenter_host="https://catc.example.com",
        catalystcenter_username="svc",
        catalystcenter_password="secret",
    )
    engine = RunnerEngine(settings, store=InMemoryTaskStore())
    captured: dict[str, object] = {}

    def fake_run_async(**kwargs):
        captured.update(kwargs)
        return object(), object()

    def fake_create_task(coro):
        coro.close()
        return None

    monkeypatch.setattr(runner_engine.ansible_runner, "run_async", fake_run_async)
    monkeypatch.setattr(runner_engine.asyncio, "create_task", fake_create_task)

    submission = await engine.submit_module(
        tool_name="inventory",
        module_name="inventory_workflow_manager",
        tenant_id="default",
        module_args={
            "state": "merged",
            "config_verify": True,
            "config": [{"inventory": [{"device_ips": ["10.10.10.1"]}]}],
        },
        verbosity=3,
        catalystcenter_log_level="INFO",
    )

    record = await engine.get_task(submission.task_id)

    assert captured["verbosity"] == 3
    assert record is not None
    assert record.module_args["catalystcenter_log_level"] == "INFO"


def test_resolve_credentials_uses_cluster_catalog_selection(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    cluster_catalog = tmp_path / "clusters.yaml"
    cluster_catalog.write_text(
        """catalyst_centers:
  - name: "Portland"
    label: "DEV"
    host: "Portland-center.domain.com"
    version: "3.1.3.0"
    location: "Portland"
    enabled: true
""",
        encoding="utf-8",
    )
    settings = Settings(
        runner_artifact_root=tmp_path,
        catalyst_center_clusters_file=cluster_catalog,
    )
    monkeypatch.setenv("CC_DEV_USERNAME", "cluster-user")
    monkeypatch.setenv("CC_DEV_PASSWORD", "cluster-pass")
    engine = RunnerEngine(settings, store=InMemoryTaskStore())

    credentials, cluster_name = engine.resolve_credentials("default", catalyst_center="Portland")

    assert cluster_name == "Portland"
    assert credentials.host == "Portland-center.domain.com"
    assert credentials.username == "cluster-user"
    assert credentials.password == "cluster-pass"
    assert credentials.version == "3.1.3.0"


def test_attach_generated_file_outputs_reads_direct_result_file(tmp_path: Path):
    generated = tmp_path / "site.yml"
    generated.write_text("config:\n  - type: floor\n", encoding="utf-8")

    settings = Settings(
        runner_artifact_root=tmp_path,
        catalystcenter_host="https://catc.example.com",
        catalystcenter_username="svc",
        catalystcenter_password="secret",
    )
    engine = RunnerEngine(settings, store=InMemoryTaskStore())

    enriched = engine._attach_generated_file_outputs(
        {
            "status": "success",
            "response": {
                "file_path": str(generated),
                "message": "generated",
            },
        }
    )

    assert "generatedFiles" in enriched
    assert len(enriched["generatedFiles"]) == 1
    assert enriched["generatedFiles"][0]["path"] == str(generated)
    assert enriched["generatedFiles"][0]["content"] == "config:\n  - type: floor\n"
    assert enriched["generatedFiles"][0]["truncated"] is False


def test_attach_generated_file_outputs_reads_nested_result_file_once(tmp_path: Path):
    generated = tmp_path / "provision.yml"
    generated.write_text("config:\n  - management_ip_address: 10.1.1.1\n", encoding="utf-8")

    settings = Settings(
        runner_artifact_root=tmp_path,
        catalystcenter_host="https://catc.example.com",
        catalystcenter_username="svc",
        catalystcenter_password="secret",
    )
    engine = RunnerEngine(settings, store=InMemoryTaskStore())

    enriched = engine._attach_generated_file_outputs(
        {
            "status": "success",
            "msg": {
                "YAML config generation Task succeeded for module 'provision_workflow_manager'.": {
                    "file_path": str(generated),
                    "devices_count": 6,
                }
            },
            "response": {
                "file_path": str(generated),
                "status": "success",
            },
        }
    )

    assert "generatedFiles" in enriched
    assert len(enriched["generatedFiles"]) == 1
    assert enriched["generatedFiles"][0]["path"] == str(generated)
    assert "management_ip_address" in enriched["generatedFiles"][0]["content"]


def test_attach_generated_file_outputs_resolves_relative_path_from_artifact_project(tmp_path: Path):
    artifact_dir = tmp_path / "artifact"
    generated = artifact_dir / "project" / "provision.yml"
    generated.parent.mkdir(parents=True, exist_ok=True)
    generated.write_text("config:\n  - management_ip_address: 10.1.1.2\n", encoding="utf-8")

    settings = Settings(
        runner_artifact_root=tmp_path,
        catalystcenter_host="https://catc.example.com",
        catalystcenter_username="svc",
        catalystcenter_password="secret",
    )
    engine = RunnerEngine(settings, store=InMemoryTaskStore())

    enriched = engine._attach_generated_file_outputs(
        {
            "status": "success",
            "msg": {
                "YAML config generation Task succeeded for module 'provision_workflow_manager'.": {
                    "file_path": "provision.yml",
                    "devices_count": 6,
                }
            },
        },
        artifact_dir=artifact_dir,
    )

    assert "generatedFiles" in enriched
    assert len(enriched["generatedFiles"]) == 1
    assert enriched["generatedFiles"][0]["path"] == str(generated)
    assert "management_ip_address" in enriched["generatedFiles"][0]["content"]

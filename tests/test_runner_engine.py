from pathlib import Path

import pytest

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
    assert "CatalystCenterAPI" in sitecustomize


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

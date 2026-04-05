from pathlib import Path

import pytest

from redis_store import InMemoryTaskStore
from runner_engine import RunnerEngine
from settings import Settings


@pytest.mark.asyncio
async def test_submit_workflow_creates_submitted_task(tmp_path: Path):
    settings = Settings(
        runner_artifact_root=tmp_path,
        dnac_host="https://catc.example.com",
        dnac_username="svc",
        dnac_password="secret",
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


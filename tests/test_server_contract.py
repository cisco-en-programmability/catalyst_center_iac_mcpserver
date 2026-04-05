from models import TaskLifecycleStatus, TaskRecord
from redis_store import InMemoryTaskStore
from runner_engine import RunnerEngine
from settings import Settings


def test_task_record_status_payload_shape():
    record = TaskRecord(
        task_id="task-1",
        tenant_id="default",
        tool_name="delete_site",
        module_name="site_workflow_manager",
        status=TaskLifecycleStatus.SUBMITTED,
        status_message="Task submitted",
        artifact_dir="/tmp/task-1",
        runner_ident="task-1",
        module_args={"state": "deleted"},
        destructive=True,
    )

    payload = record.to_status_payload()

    assert payload["taskId"] == "task-1"
    assert payload["status"] == "submitted"
    assert payload["destructive"] is True

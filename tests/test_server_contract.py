import asyncio

import server
from models import TaskLifecycleStatus, TaskRecord


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


def test_all_workflow_manager_tools_are_registered():
    async def _list_names():
        tools = await server.mcp.list_tools()
        return {tool.name for tool in tools}

    names = asyncio.run(_list_names())

    assert "provision_site" in names
    assert "run_site_workflow_manager" in names
    assert "run_template_workflow_manager" in names
    assert "run_inventory_workflow_manager" in names
    assert "run_wireless_design_workflow_manager" in names

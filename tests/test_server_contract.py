import asyncio
from types import SimpleNamespace

from fastapi.testclient import TestClient

import server
from models import TaskLifecycleStatus, TaskRecord


def test_task_record_status_payload_shape():
    record = TaskRecord(
        task_id="task-1",
        tenant_id="default",
        catalyst_center="Portland",
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

    assert payload["iacTaskId"] == "task-1"
    assert payload["iacStatus"] == "submitted"
    assert payload["iacStatusMessage"] == "Task submitted"
    assert payload["destructive"] is True
    assert payload["catalystCenter"] == "Portland"


def test_all_workflow_manager_tools_are_registered():
    async def _list_names():
        tools = await server.mcp.list_tools()
        return {tool.name for tool in tools}

    names = asyncio.run(_list_names())

    assert "provision_site" in names
    assert "site" in names
    assert "template" in names
    assert "inventory" in names
    assert "wireless_design" in names
    assert "swim" in names


def test_playbook_config_generator_tools_are_registered_when_available():
    async def _list_names():
        tools = await server.mcp.list_tools()
        return {tool.name for tool in tools}

    names = asyncio.run(_list_names())

    if server.GENERIC_PLAYBOOK_GENERATOR_MODULES:
        assert "site_config" in names
        assert "inventory_config" in names
        assert "template_config" in names


def test_catalog_metadata_is_attached_to_registered_tools():
    async def _list_tools():
        return await server.mcp.list_tools()

    tools = asyncio.run(_list_tools())
    by_name = {tool.name: tool for tool in tools}

    assert by_name["provision_site"].meta["catalog"]["topCategory"] == "direct_tools"
    assert by_name["provision_site"].meta["catalog"]["subcategory"] == "site_management"
    assert by_name["site"].meta["catalog"]["workflowCategory"] == "configuration_creation"
    assert by_name["inventory"].parameters["properties"]["state"]["enum"] == [
        "merged",
        "deleted",
    ]
    assert by_name["network_devices_info"].parameters["properties"]["state"] == {
        "const": "gathered",
        "default": "gathered",
        "type": "string",
    }
    assert by_name["fabric_devices_info"].parameters["properties"]["state"] == {
        "const": "gathered",
        "default": "gathered",
        "type": "string",
    }
    assert by_name["network_compliance"].parameters["properties"]["state"] == {
        "const": "merged",
        "default": "merged",
        "type": "string",
    }
    assert by_name["network_devices_info"].annotations.readOnlyHint is True
    assert by_name["inventory"].annotations.readOnlyHint is False


def test_cluster_listing_tool_is_registered():
    async def _list_names():
        tools = await server.mcp.list_tools()
        return {tool.name for tool in tools}

    names = asyncio.run(_list_names())

    assert "list_catalyst_centers" in names
    assert "get_task_stdout" in names
    assert "get_task_log" in names


def test_submit_accepts_string_state_for_gathered_tools(monkeypatch):
    captured: dict[str, object] = {}

    class DummyEngine:
        async def submit_workflow(self, **kwargs):
            captured.update(kwargs)
            return SimpleNamespace(task_id="task-123")

    class DummyContext:
        request_context = None

        async def report_progress(self, progress, total, message):
            return None

    monkeypatch.setattr(server, "engine", DummyEngine())

    response = asyncio.run(
        server._submit(
            ctx=DummyContext(),
            tool_name="network_devices_info",
            module_name="network_devices_info_workflow_manager",
            tenant_id="default",
            catalyst_center="PORT",
            state="gathered",
            config=[],
        )
    )

    assert response.iacTaskId == "task-123"
    assert captured["state"] == "gathered"


def test_inventory_config_tool_returns_iac_task_id(monkeypatch):
    captured: dict[str, object] = {}

    class DummyEngine:
        async def submit_module(self, **kwargs):
            captured.update(kwargs)
            return SimpleNamespace(task_id="iac-task-456")

    monkeypatch.setattr(server, "engine", DummyEngine())

    async def _call_tool():
        return await server.mcp.call_tool(
            "inventory_config",
            {
                "catalyst_center": "PORT",
                "module_args_json": "{\"file_path\":\"/tmp/inventory.yml\"}",
            },
        )

    result = asyncio.run(_call_tool())

    assert result.structured_content["iacTaskId"] == "iac-task-456"
    assert result.structured_content["iacStatus"] == "submitted"
    assert captured["tool_name"] == "inventory_config"
    assert captured["catalyst_center"] == "PORT"
    assert captured["module_args"] == {
        "file_path": "/tmp/inventory.yml",
        "state": "gathered",
    }


def test_iactasks_status_endpoint_returns_iac_payload(monkeypatch):
    record = TaskRecord(
        task_id="iac-task-123",
        tenant_id="default",
        catalyst_center="Portland",
        tool_name="inventory_config",
        module_name="inventory_playbook_config_generator",
        status=TaskLifecycleStatus.COMPLETED,
        status_message="Task completed successfully",
        artifact_dir="/tmp/iac-task-123",
        runner_ident="iac-task-123",
        module_args={"state": "gathered"},
        result={"devices": []},
    )

    class DummyEngine:
        async def connect(self):
            return None

        async def close(self):
            return None

        async def get_task(self, task_id):
            assert task_id == "iac-task-123"
            return record

    async def _allow_anonymous():
        return {"tenant_id": "default", "subject": "anonymous"}

    monkeypatch.setattr(server, "engine", DummyEngine())
    server.app.dependency_overrides[server.get_identity_context] = _allow_anonymous

    try:
        with TestClient(server.app) as client:
            response = client.get("/iactasks/get/iac-task-123")
    finally:
        server.app.dependency_overrides.pop(server.get_identity_context, None)

    assert response.status_code == 200
    assert response.json()["iacTaskId"] == "iac-task-123"
    assert response.json()["iacStatus"] == "completed"


def test_get_task_stdout_tool_returns_tail(monkeypatch, tmp_path):
    artifact_dir = tmp_path / "iac-task-123"
    stdout_dir = artifact_dir / "artifacts" / "iac-task-123"
    stdout_dir.mkdir(parents=True)
    stdout_file = stdout_dir / "stdout"
    stdout_file.write_text("line-1\nline-2\nline-3\n", encoding="utf-8")

    record = TaskRecord(
        task_id="iac-task-123",
        tenant_id="default",
        catalyst_center="Portland",
        tool_name="inventory",
        module_name="inventory_workflow_manager",
        status=TaskLifecycleStatus.COMPLETED,
        status_message="Task completed successfully",
        artifact_dir=str(artifact_dir),
        runner_ident="iac-task-123",
        module_args={"state": "merged"},
    )

    class DummyEngine:
        async def get_task(self, task_id):
            assert task_id == "iac-task-123"
            return record

    monkeypatch.setattr(server, "engine", DummyEngine())

    async def _call_tool():
        return await server.mcp.call_tool(
            "get_task_stdout",
            {
                "iac_task_id": "iac-task-123",
                "tail_lines": 2,
            },
        )

    result = asyncio.run(_call_tool())

    assert result.structured_content["iacTaskId"] == "iac-task-123"
    assert result.structured_content["stdoutPath"] == str(stdout_file)
    assert result.structured_content["mode"] == "tail"
    assert result.structured_content["lineCount"] == 2
    assert result.structured_content["stdout"] == "line-2\nline-3\n"


def test_get_task_log_tool_returns_default_dnac_log(monkeypatch, tmp_path):
    artifact_dir = tmp_path / "iac-task-789"
    project_dir = artifact_dir / "project"
    project_dir.mkdir(parents=True)
    sdk_log = project_dir / "dnac.log"
    sdk_log.write_text("sdk-1\nsdk-2\nsdk-3\n", encoding="utf-8")

    record = TaskRecord(
        task_id="iac-task-789",
        tenant_id="default",
        catalyst_center="Portland",
        tool_name="inventory",
        module_name="inventory_workflow_manager",
        status=TaskLifecycleStatus.COMPLETED,
        status_message="Task completed successfully",
        artifact_dir=str(artifact_dir),
        runner_ident="iac-task-789",
        module_args={"state": "merged"},
    )

    class DummyEngine:
        async def get_task(self, task_id):
            assert task_id == "iac-task-789"
            return record

    monkeypatch.setattr(server, "engine", DummyEngine())

    async def _call_tool():
        return await server.mcp.call_tool(
            "get_task_log",
            {
                "iac_task_id": "iac-task-789",
                "log_type": "catalystcenter",
                "head_lines": 2,
                "tail_lines": None,
            },
        )

    result = asyncio.run(_call_tool())

    assert result.structured_content["iacTaskId"] == "iac-task-789"
    assert result.structured_content["logType"] == "catalystcenter"
    assert result.structured_content["logPath"] == str(sdk_log)
    assert result.structured_content["mode"] == "head"
    assert result.structured_content["lineCount"] == 2
    assert result.structured_content["content"] == "sdk-1\nsdk-2\n"

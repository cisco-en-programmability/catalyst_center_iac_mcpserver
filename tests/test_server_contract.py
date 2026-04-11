import asyncio

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

    assert payload["taskId"] == "task-1"
    assert payload["status"] == "submitted"
    assert payload["destructive"] is True
    assert payload["catalystCenter"] == "Portland"


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
    assert "run_swim_workflow_manager" in names


def test_playbook_config_generator_tools_are_registered_when_available():
    async def _list_names():
        tools = await server.mcp.list_tools()
        return {tool.name for tool in tools}

    names = asyncio.run(_list_names())

    if server.GENERIC_PLAYBOOK_GENERATOR_MODULES:
        assert "generate_site_config" in names
        assert "generate_inventory_config" in names
        assert "generate_template_config" in names


def test_catalog_metadata_is_attached_to_registered_tools():
    async def _list_tools():
        return await server.mcp.list_tools()

    tools = asyncio.run(_list_tools())
    by_name = {tool.name: tool for tool in tools}

    assert by_name["provision_site"].meta["catalog"]["topCategory"] == "direct_tools"
    assert by_name["provision_site"].meta["catalog"]["subcategory"] == "site_management"
    assert by_name["run_site_workflow_manager"].meta["catalog"]["workflowCategory"] == "configuration_creation"


def test_cluster_listing_tool_is_registered():
    async def _list_names():
        tools = await server.mcp.list_tools()
        return {tool.name for tool in tools}

    names = asyncio.run(_list_names())

    assert "list_catalyst_centers" in names

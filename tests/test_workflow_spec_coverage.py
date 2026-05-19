import asyncio

import server


def _assert_normalized_schema_node(node: dict, *, path: str) -> None:
    assert isinstance(node, dict), f"{path} must be a dict"

    allowed_keys = {
        "type",
        "elements",
        "required",
        "default",
        "choices",
        "description",
        "suboptions",
    }
    unexpected = set(node) - allowed_keys
    assert not unexpected, f"{path} has unexpected keys: {sorted(unexpected)}"

    if "suboptions" in node:
        suboptions = node["suboptions"]
        assert isinstance(suboptions, dict), f"{path}.suboptions must be a dict"
        for child_name, child_node in suboptions.items():
            assert isinstance(child_name, str) and child_name, f"{path} contains blank child key"
            _assert_normalized_schema_node(child_node, path=f"{path}.{child_name}")


def test_all_registered_tools_expose_authoritative_workflow_specs():
    async def _list_tools():
        return await server.mcp.list_tools()

    tools = asyncio.run(_list_tools())
    by_name = {tool.name: tool for tool in tools}

    expected_tool_names: set[str] = set()

    for definition in server.DIRECT_TOOL_DEFINITIONS:
        expected_tool_names.add(definition.tool_name)

    for definition in server.TOOL_CATALOG.iter_workflow_tools("configuration_creation"):
        if definition.module_name in set(server.GENERIC_WORKFLOW_MODULES):
            expected_tool_names.add(definition.tool_name)

    for definition in server.TOOL_CATALOG.iter_workflow_tools("configuration_generation"):
        if definition.module_name in set(server.GENERIC_PLAYBOOK_GENERATOR_MODULES):
            expected_tool_names.add(definition.tool_name)

    missing = expected_tool_names - set(by_name)
    assert not missing, f"Registered MCP tools missing from tools/list: {sorted(missing)}"

    for tool_name in sorted(expected_tool_names):
        tool = by_name[tool_name]
        assert "workflowSpec" in tool.meta, f"{tool_name} missing meta.workflowSpec"
        assert "meta.workflowSpec" in tool.description, f"{tool_name} missing workflowSpec description guidance"

        workflow_spec = tool.meta["workflowSpec"]
        assert workflow_spec["moduleName"], f"{tool_name} missing workflowSpec.moduleName"
        assert workflow_spec["modulePath"], f"{tool_name} missing workflowSpec.modulePath"

        options = workflow_spec.get("options")
        assert isinstance(options, dict) and options, f"{tool_name} has empty workflowSpec.options"

        for option_name, option_schema in options.items():
            _assert_normalized_schema_node(option_schema, path=f"{tool_name}.workflowSpec.options.{option_name}")


def test_all_workflow_modules_have_parseable_documentation_specs():
    modules_to_check = set()
    modules_to_check.update(definition.module_name for definition in server.DIRECT_TOOL_DEFINITIONS)
    modules_to_check.update(
        definition.module_name
        for definition in server.TOOL_CATALOG.iter_workflow_tools("configuration_creation")
        if definition.module_name in set(server.GENERIC_WORKFLOW_MODULES)
    )
    modules_to_check.update(
        definition.module_name
        for definition in server.TOOL_CATALOG.iter_workflow_tools("configuration_generation")
        if definition.module_name in set(server.GENERIC_PLAYBOOK_GENERATOR_MODULES)
    )

    missing_specs = []
    for module_name in sorted(modules_to_check):
        spec = server._workflow_manager_tool_spec(module_name)
        if spec is None:
            missing_specs.append(module_name)
            continue
        assert spec["moduleName"] == module_name
        assert isinstance(spec.get("options"), dict) and spec["options"], (
            f"{module_name} returned no normalized options"
        )

    assert not missing_specs, (
        "Modules missing parseable authoritative documentation specs: "
        + ", ".join(missing_specs)
    )

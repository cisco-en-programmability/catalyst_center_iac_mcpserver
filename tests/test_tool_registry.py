from pathlib import Path

from tool_registry import load_tool_catalog


def test_tool_catalog_loads_with_expected_top_categories():
    catalog = load_tool_catalog(Path(__file__).resolve().parents[1] / "tool_catalog.yaml")

    workflow_creation_categories = set(catalog.workflow_tools.configuration_creation)
    workflow_generation_categories = set(catalog.workflow_tools.configuration_generation)

    assert "site_management" in catalog.direct_tools
    assert "provision" in workflow_creation_categories
    assert "sd_access_fabric" in workflow_creation_categories
    assert "inventory" in workflow_generation_categories
    assert "wired_campus" in workflow_generation_categories
    assert "rma" in workflow_generation_categories


def test_tool_catalog_derives_expected_tool_names():
    catalog = load_tool_catalog(Path(__file__).resolve().parents[1] / "tool_catalog.yaml")

    workflow_tool_names = {
        definition.tool_name
        for definition in catalog.iter_workflow_tools("configuration_creation")
    }
    generator_tool_names = {
        definition.tool_name
        for definition in catalog.iter_workflow_tools("configuration_generation")
    }

    assert "run_site_workflow_manager" in workflow_tool_names
    assert "run_provision_workflow_manager" in workflow_tool_names
    assert "run_reports_workflow_manager" in workflow_tool_names
    assert "run_swim_workflow_manager" in workflow_tool_names
    assert "run_lan_automation_workflow_manager" in workflow_tool_names
    assert "run_wired_campus_automation_workflow_manager" in workflow_tool_names
    assert "run_rma_workflow_manager" in workflow_tool_names
    assert "generate_site_config" in generator_tool_names
    assert "generate_inventory_config" in generator_tool_names
    assert "generate_rma_config" in generator_tool_names

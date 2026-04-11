from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import yaml
from pydantic import BaseModel, ConfigDict, RootModel, model_validator


class DirectToolDefinition(BaseModel):
    model_config = ConfigDict(extra="forbid")

    handler: str
    module_name: str
    description: str
    destructive: bool = False


class WorkflowToolDefinition(BaseModel):
    model_config = ConfigDict(extra="forbid")

    module_name: str
    description: str | None = None
    destructive: bool = False


class CategoryToolMap(RootModel[dict[str, list[DirectToolDefinition | WorkflowToolDefinition]]]):
    pass


class WorkflowToolsSection(BaseModel):
    model_config = ConfigDict(extra="forbid")

    configuration_creation: dict[str, list[WorkflowToolDefinition]]
    configuration_generation: dict[str, list[WorkflowToolDefinition]]


class ToolCatalog(BaseModel):
    model_config = ConfigDict(extra="forbid")

    version: int = 1
    direct_tools: dict[str, list[DirectToolDefinition]]
    workflow_tools: WorkflowToolsSection

    @model_validator(mode="after")
    def validate_uniqueness(self) -> "ToolCatalog":
        seen_tool_names: set[str] = set()
        for definition in self.iter_direct_tools():
            if definition.tool_name in seen_tool_names:
                raise ValueError(f"duplicate tool name in catalog: {definition.tool_name}")
            seen_tool_names.add(definition.tool_name)
        for definition in self.iter_workflow_tools("configuration_creation"):
            if definition.tool_name in seen_tool_names:
                raise ValueError(f"duplicate tool name in catalog: {definition.tool_name}")
            seen_tool_names.add(definition.tool_name)
        for definition in self.iter_workflow_tools("configuration_generation"):
            if definition.tool_name in seen_tool_names:
                raise ValueError(f"duplicate tool name in catalog: {definition.tool_name}")
            seen_tool_names.add(definition.tool_name)
        return self

    def iter_direct_tools(self) -> list["ResolvedToolDefinition"]:
        definitions: list[ResolvedToolDefinition] = []
        for subcategory, entries in self.direct_tools.items():
            for entry in entries:
                definitions.append(
                    ResolvedToolDefinition(
                        top_category="direct_tools",
                        workflow_category=None,
                        subcategory=subcategory,
                        tool_name=entry.handler,
                        module_name=entry.module_name,
                        description=entry.description,
                        destructive=entry.destructive,
                        read_only=False,
                        handler_name=entry.handler,
                    )
                )
        return definitions

    def iter_workflow_tools(
        self,
        workflow_category: str,
    ) -> list["ResolvedToolDefinition"]:
        definitions: list[ResolvedToolDefinition] = []
        category_map = getattr(self.workflow_tools, workflow_category)
        for subcategory, entries in category_map.items():
            for entry in entries:
                tool_name = _derive_workflow_tool_name(workflow_category, entry.module_name)
                definitions.append(
                    ResolvedToolDefinition(
                        top_category="workflow_tools",
                        workflow_category=workflow_category,
                        subcategory=subcategory,
                        tool_name=tool_name,
                        module_name=entry.module_name,
                        description=entry.description
                        or _derive_workflow_description(workflow_category, entry.module_name),
                        destructive=entry.destructive,
                        read_only=workflow_category == "configuration_generation",
                        handler_name=None,
                    )
                )
        return definitions


@dataclass(frozen=True, slots=True)
class ResolvedToolDefinition:
    top_category: str
    workflow_category: str | None
    subcategory: str
    tool_name: str
    module_name: str
    description: str
    destructive: bool
    read_only: bool
    handler_name: str | None


def _derive_workflow_tool_name(workflow_category: str, module_name: str) -> str:
    if workflow_category == "configuration_creation":
        return f"run_{module_name}"
    base_name = module_name.removesuffix("_playbook_config_generator")
    return f"generate_{base_name}_config"


def _derive_workflow_description(workflow_category: str, module_name: str) -> str:
    if workflow_category == "configuration_creation":
        return (
            f"Generic wrapper for `{module_name}`. Pass the module `config` payload as a JSON string."
        )
    return (
        f"Read-only wrapper for `{module_name}`. Pass the module arguments as a JSON "
        "object string. If `state` is omitted, it defaults to `gathered`."
    )


def load_tool_catalog(path: Path) -> ToolCatalog:
    raw = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    if not isinstance(raw, dict):
        raise ValueError(f"tool catalog must decode to a dictionary: {path}")
    return ToolCatalog.model_validate(raw)

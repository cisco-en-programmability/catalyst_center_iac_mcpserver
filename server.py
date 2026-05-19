from __future__ import annotations

from contextlib import asynccontextmanager
from collections import deque
from enum import Enum
from difflib import get_close_matches
from functools import lru_cache
import json
import os
from pathlib import Path
import re
from typing import Any, Literal

import jwt
import uvicorn
from fastapi import Depends, FastAPI, Header, HTTPException, Request
from fastapi.responses import JSONResponse
from fastmcp import Context, FastMCP
from mcp.types import ToolAnnotations
from starlette.middleware.base import BaseHTTPMiddleware
import yaml

from models import (
    AssuranceIssuePriority,
    AssuranceIssueProcessType,
    AssuranceIssueRequest,
    AssuranceIssueStatus,
    DiscoveryRequest,
    DiscoveryType,
    FabricDeviceRequest,
    FabricDeviceRole,
    InventoryDeviceRequest,
    NetworkSettingsRequest,
    SiteProvisionRequest,
    SiteType,
    TaskRecord,
    TaskSubmissionResponse,
    TemplateDeployRequest,
    TemplateFailurePolicy,
    WorkflowMutationState,
    WorkflowState,
)
from runner_engine import RunnerEngine, get_runner_engine
from settings import Settings, get_settings
from tool_registry import ResolvedToolDefinition, load_tool_catalog
from cluster_registry import load_cluster_catalog
from transformers import (
    build_assurance_issue_workflow_config,
    build_discovery_workflow_config,
    build_fabric_devices_workflow_config,
    build_inventory_workflow_config,
    build_network_settings_workflow_config,
    build_site_workflow_config,
    build_template_workflow_config,
)

DEFAULT_WORKFLOW_MODULES: tuple[str, ...] = (
    "accesspoint_location_workflow_manager",
    "accesspoint_workflow_manager",
    "application_policy_workflow_manager",
    "assurance_device_health_score_settings_workflow_manager",
    "assurance_icap_settings_workflow_manager",
    "assurance_issue_workflow_manager",
    "backup_and_restore_workflow_manager",
    "device_configs_backup_workflow_manager",
    "device_credential_workflow_manager",
    "discovery_workflow_manager",
    "events_and_notifications_workflow_manager",
    "fabric_devices_info_workflow_manager",
    "inventory_workflow_manager",
    "ise_radius_integration_workflow_manager",
    "lan_automation_workflow_manager",
    "network_compliance_workflow_manager",
    "network_devices_info_workflow_manager",
    "network_profile_switching_workflow_manager",
    "network_profile_wireless_workflow_manager",
    "network_settings_workflow_manager",
    "path_trace_workflow_manager",
    "pnp_workflow_manager",
    "provision_workflow_manager",
    "reports_workflow_manager",
    "rma_workflow_manager",
    "sda_extranet_policies_workflow_manager",
    "sda_fabric_devices_workflow_manager",
    "sda_fabric_multicast_workflow_manager",
    "sda_fabric_sites_zones_workflow_manager",
    "sda_fabric_transits_workflow_manager",
    "sda_fabric_virtual_networks_workflow_manager",
    "sda_host_port_onboarding_workflow_manager",
    "site_workflow_manager",
    "swim_workflow_manager",
    "tags_workflow_manager",
    "template_workflow_manager",
    "user_role_workflow_manager",
    "wired_campus_automation_workflow_manager",
    "wireless_design_workflow_manager",
)


def _collection_module_dirs(collection_namespace: str) -> tuple[Path, ...]:
    parts = collection_namespace.split(".")
    if len(parts) != 2:
        return ()

    vendor, collection = parts
    raw_roots: list[str] = []
    for env_name in ("ANSIBLE_COLLECTIONS_PATH", "ANSIBLE_COLLECTIONS_PATHS"):
        value = os.getenv(env_name)
        if value:
            raw_roots.extend(path for path in value.split(os.pathsep) if path)

    raw_roots.extend(
        [
            str(Path.home() / ".ansible" / "collections"),
            "/usr/share/ansible/collections",
        ]
    )

    discovered: list[Path] = []
    seen: set[Path] = set()
    for raw_root in raw_roots:
        root = Path(raw_root).expanduser()
        candidates = (
            root / "ansible_collections" / vendor / collection / "plugins" / "modules",
            root / vendor / collection / "plugins" / "modules",
        )
        for candidate in candidates:
            if candidate.exists() and candidate not in seen:
                discovered.append(candidate)
                seen.add(candidate)
    return tuple(discovered)


def _discover_collection_modules(collection_namespace: str, suffix: str) -> tuple[str, ...]:
    modules: set[str] = set()
    for modules_dir in _collection_module_dirs(collection_namespace):
        modules.update(path.stem for path in modules_dir.glob(f"*{suffix}.py"))
    return tuple(sorted(modules))


GENERIC_WORKFLOW_MODULES: tuple[str, ...] = (
    _discover_collection_modules("cisco.catalystcenter", "_workflow_manager")
    or DEFAULT_WORKFLOW_MODULES
)
GENERIC_PLAYBOOK_GENERATOR_MODULES: tuple[str, ...] = _discover_collection_modules(
    "cisco.catalystcenter", "_playbook_config_generator"
)

_DOCUMENTATION_BLOCK_RE = re.compile(
    r"DOCUMENTATION\s*=\s*r?([\"']{3})(?P<body>.*?)(?:\1)",
    re.DOTALL,
)

WORKFLOW_STATE_OVERRIDES: dict[str, tuple[str, ...]] = {
    "network_devices_info_workflow_manager": ("gathered",),
    "fabric_devices_info_workflow_manager": ("gathered",),
    "network_compliance_workflow_manager": ("merged",),
}


def _find_collection_module_path(module_name: str) -> Path | None:
    for modules_dir in _collection_module_dirs("cisco.catalystcenter"):
        candidate = modules_dir / f"{module_name}.py"
        if candidate.exists():
            return candidate
    return None


@lru_cache(maxsize=None)
def _load_workflow_manager_documentation(module_name: str) -> dict[str, Any] | None:
    module_path = _find_collection_module_path(module_name)
    if module_path is None:
        return None

    text = module_path.read_text(encoding="utf-8", errors="ignore")
    match = _DOCUMENTATION_BLOCK_RE.search(text)
    if match is None:
        return None

    parsed = yaml.safe_load(match.group("body"))
    if not isinstance(parsed, dict):
        return None
    return parsed


def _normalize_workflow_option_schema(option_schema: dict[str, Any]) -> dict[str, Any]:
    normalized: dict[str, Any] = {}
    for field_name in (
        "type",
        "elements",
        "required",
        "default",
        "choices",
        "description",
    ):
        if field_name in option_schema:
            normalized[field_name] = option_schema[field_name]

    suboptions = option_schema.get("suboptions")
    if isinstance(suboptions, dict):
        normalized["suboptions"] = {
            name: _normalize_workflow_option_schema(subschema)
            for name, subschema in suboptions.items()
            if isinstance(subschema, dict)
        }
    return normalized


@lru_cache(maxsize=None)
def _workflow_manager_tool_spec(module_name: str) -> dict[str, Any] | None:
    documentation = _load_workflow_manager_documentation(module_name)
    if documentation is None:
        return None

    options = documentation.get("options")
    if not isinstance(options, dict):
        return None

    normalized_options = {
        name: _normalize_workflow_option_schema(schema)
        for name, schema in options.items()
        if isinstance(schema, dict)
    }
    module_path = _find_collection_module_path(module_name)
    return {
        "moduleName": module_name,
        "modulePath": str(module_path) if module_path is not None else None,
        "shortDescription": documentation.get("short_description"),
        "options": normalized_options,
    }


def _format_spec_line(name: str, schema: dict[str, Any], indent: int = 0) -> list[str]:
    fragments: list[str] = []
    if "type" in schema:
        fragments.append(f"type={schema['type']}")
    if "elements" in schema:
        fragments.append(f"elements={schema['elements']}")
    if schema.get("required") is True:
        fragments.append("required=true")
    if "default" in schema:
        fragments.append(f"default={schema['default']!r}")
    if "choices" in schema:
        fragments.append(f"choices={schema['choices']}")
    line = f"{'  ' * indent}- `{name}`"
    if fragments:
        line = f"{line}: {', '.join(fragments)}"
    lines = [line]
    suboptions = schema.get("suboptions")
    if isinstance(suboptions, dict):
        for child_name, child_schema in suboptions.items():
            if isinstance(child_schema, dict):
                lines.extend(_format_spec_line(child_name, child_schema, indent + 1))
    return lines


def _module_spec_excerpt(module_name: str) -> str | None:
    spec = _workflow_manager_tool_spec(module_name)
    if spec is None:
        return None

    options = spec.get("options")
    if not isinstance(options, dict):
        return None

    lines = [
        "Authoritative module spec (derived from the installed Ansible module):",
        "Use the exact keys below. Do not invent aliases or inferred field names.",
    ]
    for option_name in ("state", "config_verify", "config"):
        option_schema = options.get(option_name)
        if isinstance(option_schema, dict):
            lines.extend(_format_spec_line(option_name, option_schema))
    return "\n".join(lines)

class NoBufferingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        response.headers["X-Accel-Buffering"] = "no"
        response.headers.setdefault("Cache-Control", "no-cache")
        return response


class McpPathCanonicalizationMiddleware:
    def __init__(self, app: Any, mcp_path: str):
        self.app = app
        self.bare_path = mcp_path.rstrip("/") or "/"
        self.canonical_path = self.bare_path if self.bare_path == "/" else f"{self.bare_path}/"

    async def __call__(self, scope: dict[str, Any], receive: Any, send: Any) -> None:
        if (
            scope["type"] == "http"
            and self.bare_path != self.canonical_path
            and scope.get("path") == self.bare_path
        ):
            scope = dict(scope)
            scope["path"] = self.canonical_path
            scope["raw_path"] = self.canonical_path.encode("utf-8")
        await self.app(scope, receive, send)


def get_identity_context(
    request: Request,
    authorization: str | None = Header(default=None),
    settings: Settings = Depends(get_settings),
) -> dict[str, Any]:
    if (
        request.url.path == "/healthz"
        and settings.allow_anonymous_healthcheck
        and not settings.oauth_enabled
    ):
        return {"subject": "anonymous", "tenant_id": "default"}
    if not settings.oauth_enabled:
        return {"subject": "anonymous", "tenant_id": "default"}
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing bearer token")
    if not settings.oauth_jwks_url:
        raise HTTPException(status_code=500, detail="oauth_jwks_url must be configured when OAuth is enabled")
    token = authorization.split(" ", 1)[1]
    try:
        signing_key = jwt.PyJWKClient(settings.oauth_jwks_url).get_signing_key_from_jwt(token)
        claims = jwt.decode(
            token,
            signing_key.key,
            algorithms=["RS256", "RS384", "RS512", "ES256", "ES384", "ES512"],
            audience=settings.oauth_audience,
            issuer=settings.oauth_issuer,
        )
    except jwt.PyJWTError as exc:
        raise HTTPException(status_code=401, detail=f"Invalid bearer token: {exc}") from exc
    return {
        "subject": claims.get("sub", "unknown"),
        "tenant_id": claims.get("tenant_id") or claims.get("tid") or "default",
    }


settings = get_settings()
engine = get_runner_engine()
TOOL_CATALOG = load_tool_catalog(Path(__file__).with_name("tool_catalog.yaml"))
CLUSTER_CATALOG = load_cluster_catalog(settings.catalyst_center_clusters_file)


def _cluster_summary_text() -> str:
    enabled_clusters = CLUSTER_CATALOG.enabled_clusters()
    if not enabled_clusters:
        return "No enabled Catalyst Center clusters are configured; tools use tenant or default environment credentials."
    lines = [
        "Enabled Catalyst Center clusters can be selected with the `catalyst_center` argument."
    ]
    for cluster in enabled_clusters:
        label = f", label={cluster.label}" if cluster.label else ""
        location = f", location={cluster.location}" if cluster.location else ""
        lines.append(
            f"- {cluster.name} (host={cluster.host}, version={cluster.version}{label}{location})"
        )
    return " ".join(lines)


mcp = FastMCP(
    name=settings.app_name,
    version=settings.app_version,
    instructions=(
        "Cisco Catalyst Center IaC MCP server. Tools expose flat arguments and submit "
        "workflow-manager and playbook-config-generator operations as long-running tasks "
        "backed by ansible-runner. "
        f"{_cluster_summary_text()}"
    ),
    strict_input_validation=True,
)


def _tool_annotations(*, destructive: bool = False, read_only: bool = False) -> ToolAnnotations:
    return ToolAnnotations(
        readOnlyHint=read_only,
        destructiveHint=destructive,
        idempotentHint=not destructive,
        openWorldHint=True,
    )


async def _submit(
    *,
    ctx: Context,
    tool_name: str,
    module_name: str,
    tenant_id: str,
    catalyst_center: str | None,
    state: WorkflowState | WorkflowMutationState | str,
    config: list[dict[str, Any]],
    destructive: bool = False,
    verbosity: int | None = None,
    catalystcenter_log_level: str | None = None,
) -> TaskSubmissionResponse:
    async def notify(progress: float, total: float, message: str) -> None:
        await ctx.report_progress(progress, total, message)

    state_value = state.value if isinstance(state, Enum) else state

    submission = await engine.submit_workflow(
        tool_name=tool_name,
        module_name=module_name,
        tenant_id=tenant_id,
        catalyst_center=catalyst_center,
        state=state_value,
        config=config,
        progress_callback=notify,
        destructive=destructive,
        verbosity=verbosity,
        catalystcenter_log_level=catalystcenter_log_level,
        progress_token=(
            ctx.request_context.meta.progressToken
            if ctx.request_context and ctx.request_context.meta
            else None
        ),
    )
    return TaskSubmissionResponse(iacTaskId=submission.task_id)


async def _submit_module(
    *,
    ctx: Context,
    tool_name: str,
    module_name: str,
    tenant_id: str,
    catalyst_center: str | None,
    module_args: dict[str, Any],
    destructive: bool = False,
    verbosity: int | None = None,
    catalystcenter_log_level: str | None = None,
) -> TaskSubmissionResponse:
    async def notify(progress: float, total: float, message: str) -> None:
        await ctx.report_progress(progress, total, message)

    submission = await engine.submit_module(
        tool_name=tool_name,
        module_name=module_name,
        tenant_id=tenant_id,
        catalyst_center=catalyst_center,
        module_args=module_args,
        progress_callback=notify,
        destructive=destructive,
        verbosity=verbosity,
        catalystcenter_log_level=catalystcenter_log_level,
        progress_token=(
            ctx.request_context.meta.progressToken
            if ctx.request_context and ctx.request_context.meta
            else None
        ),
    )
    return TaskSubmissionResponse(iacTaskId=submission.task_id)


def _parse_config_json(config_json: str) -> list[dict[str, Any]]:
    try:
        parsed = json.loads(config_json)
    except json.JSONDecodeError as exc:
        raise HTTPException(status_code=400, detail=f"config_json is not valid JSON: {exc}") from exc
    if isinstance(parsed, dict):
        parsed = [parsed]
    if not isinstance(parsed, list):
        raise HTTPException(
            status_code=400,
            detail=(
                "config_json must decode to a workflow config object or a list of workflow config objects. "
                "If you provide a single object, the server can wrap it automatically; scalars and arrays of non-objects are invalid."
            ),
        )
    if not all(isinstance(item, dict) for item in parsed):
        raise HTTPException(status_code=400, detail="config_json must decode to a list of dictionaries")
    return parsed


def _parse_module_args_json(module_args_json: str) -> dict[str, Any]:
    try:
        parsed = json.loads(module_args_json)
    except json.JSONDecodeError as exc:
        raise HTTPException(status_code=400, detail=f"module_args_json is not valid JSON: {exc}") from exc
    if not isinstance(parsed, dict):
        raise HTTPException(status_code=400, detail="module_args_json must decode to a dictionary")
    return parsed


def _validated_verbosity(verbosity: int | None) -> int | None:
    if verbosity is None:
        return None
    if verbosity < 0:
        raise HTTPException(status_code=400, detail="verbosity must be greater than or equal to 0")
    return verbosity


def _schema_type_matches(value: Any, expected_type: str) -> bool:
    if expected_type == "str":
        return isinstance(value, str)
    if expected_type == "bool":
        return isinstance(value, bool)
    if expected_type == "int":
        return isinstance(value, int) and not isinstance(value, bool)
    if expected_type == "float":
        return isinstance(value, (int, float)) and not isinstance(value, bool)
    if expected_type == "list":
        return isinstance(value, list)
    if expected_type == "dict":
        return isinstance(value, dict)
    return True


def _unknown_field_error(path: str, invalid_key: str, allowed_keys: list[str]) -> HTTPException:
    detail = f"Unknown field `{invalid_key}` at `{path}`."
    suggestion = get_close_matches(invalid_key, allowed_keys, n=1, cutoff=0.6)
    if suggestion:
        detail = f"{detail} Did you mean `{suggestion[0]}`?"
    if allowed_keys:
        detail = f"{detail} Allowed keys: {', '.join(f'`{key}`' for key in allowed_keys)}."
    return HTTPException(status_code=400, detail=detail)


def _validate_schema_value(path: str, value: Any, schema: dict[str, Any]) -> None:
    expected_type = schema.get("type")
    if isinstance(expected_type, str) and not _schema_type_matches(value, expected_type):
        raise HTTPException(
            status_code=400,
            detail=(
                f"Field `{path}` must be of type `{expected_type}`; "
                f"received `{type(value).__name__}`."
            ),
        )

    choices = schema.get("choices")
    if isinstance(choices, list):
        if expected_type == "list" and isinstance(value, list) and schema.get("elements") != "dict":
            invalid_items = [item for item in value if item not in choices]
            if invalid_items:
                raise HTTPException(
                    status_code=400,
                    detail=(
                        f"Field `{path}` contains invalid value(s) {invalid_items!r}. "
                        f"Allowed values: {choices!r}."
                    ),
                )
        elif expected_type != "list" and value not in choices:
            raise HTTPException(
                status_code=400,
                detail=(
                    f"Field `{path}` has invalid value `{value}`. "
                    f"Allowed values: {choices!r}."
                ),
            )

    suboptions = schema.get("suboptions")
    if expected_type == "dict" and isinstance(value, dict) and isinstance(suboptions, dict):
        allowed_keys = list(suboptions.keys())
        for key, nested_value in value.items():
            nested_schema = suboptions.get(key)
            if not isinstance(nested_schema, dict):
                raise _unknown_field_error(path, key, allowed_keys)
            _validate_schema_value(f"{path}.{key}", nested_value, nested_schema)
        missing_required = [
            key
            for key, nested_schema in suboptions.items()
            if isinstance(nested_schema, dict) and nested_schema.get("required") is True and key not in value
        ]
        if missing_required:
            raise HTTPException(
                status_code=400,
                detail=(
                    f"Field `{path}` is missing required key(s): "
                    f"{', '.join(f'`{key}`' for key in missing_required)}."
                ),
            )

    if expected_type == "list" and isinstance(value, list):
        elements_type = schema.get("elements")
        if elements_type == "dict":
            item_schema = {"type": "dict", "suboptions": suboptions or {}}
            for index, item in enumerate(value):
                _validate_schema_value(f"{path}[{index}]", item, item_schema)
        elif isinstance(elements_type, str):
            item_schema = {"type": elements_type}
            if isinstance(choices, list):
                item_schema["choices"] = choices
            for index, item in enumerate(value):
                _validate_schema_value(f"{path}[{index}]", item, item_schema)


def _validate_workflow_schema_config(module_name: str, config: list[dict[str, Any]]) -> None:
    spec = _workflow_manager_tool_spec(module_name)
    if spec is None:
        return
    options = spec.get("options")
    if not isinstance(options, dict):
        return
    config_schema = options.get("config")
    if isinstance(config_schema, dict):
        _validate_schema_value("config", config, config_schema)


def _validate_module_args(module_name: str, module_args: dict[str, Any]) -> None:
    spec = _workflow_manager_tool_spec(module_name)
    if spec is None:
        return
    options = spec.get("options")
    if not isinstance(options, dict):
        return

    allowed_keys = list(options.keys())
    for key, value in module_args.items():
        option_schema = options.get(key)
        if not isinstance(option_schema, dict):
            raise _unknown_field_error("module_args", key, allowed_keys)
        _validate_schema_value(f"module_args.{key}", value, option_schema)


def _validate_reports_config(config: list[dict[str, Any]]) -> None:
    for config_index, config_item in enumerate(config):
        generate_report = config_item.get("generate_report")
        if generate_report is None:
            continue
        if not isinstance(generate_report, list) or not generate_report:
            raise HTTPException(
                status_code=400,
                detail=(
                    "The `reports` tool requires `generate_report` to be a non-empty list. "
                    "Each `generate_report` item must include a non-empty `view` field."
                ),
            )
        for report_index, report_item in enumerate(generate_report):
            if not isinstance(report_item, dict):
                raise HTTPException(
                    status_code=400,
                    detail=(
                        "The `reports` tool requires each `generate_report` item to be an object "
                        "with a non-empty `view` field."
                    ),
                )
            view = report_item.get("view")
            if not isinstance(view, str) or not view.strip():
                raise HTTPException(
                    status_code=400,
                    detail=(
                        "The `reports` tool requires `generate_report[].view`. "
                        f"Missing or empty `view` at config_json[{config_index}].generate_report[{report_index}]. "
                        "Confirm the intended report view with the user before execution."
                    ),
                )


def _validate_workflow_config(tool_name: str, module_name: str, config: list[dict[str, Any]]) -> None:
    if tool_name == "reports" or module_name == "reports_workflow_manager":
        _validate_reports_config(config)
    _validate_workflow_schema_config(module_name, config)


async def provision_site(
    site_type: SiteType,
    name: str,
    parent_path: str,
    latitude: float | None = None,
    longitude: float | None = None,
    rf_model: str | None = None,
    verbosity: int | None = None,
    catalystcenter_log_level: str | None = None,
    tenant_id: str = "default",
    catalyst_center: str | None = None,
    ctx: Context | None = None,
) -> dict[str, Any]:
    assert ctx is not None
    request = SiteProvisionRequest(
        site_type=site_type,
        name=name,
        parent_path=parent_path,
        latitude=latitude,
        longitude=longitude,
        rf_model=rf_model,
        state=WorkflowState.MERGED,
    )
    return (await _submit(
        ctx=ctx,
        tool_name="provision_site",
        module_name="site_workflow_manager",
        tenant_id=tenant_id,
        catalyst_center=catalyst_center,
        state=WorkflowState.MERGED,
        config=build_site_workflow_config(request),
        verbosity=_validated_verbosity(verbosity),
        catalystcenter_log_level=catalystcenter_log_level,
    )).model_dump()


async def delete_site(
    site_type: SiteType,
    name: str,
    parent_path: str,
    verbosity: int | None = None,
    catalystcenter_log_level: str | None = None,
    tenant_id: str = "default",
    catalyst_center: str | None = None,
    ctx: Context | None = None,
) -> dict[str, Any]:
    assert ctx is not None
    request = SiteProvisionRequest(
        site_type=site_type,
        name=name,
        parent_path=parent_path,
        state=WorkflowState.DELETED,
    )
    return (await _submit(
        ctx=ctx,
        tool_name="delete_site",
        module_name="site_workflow_manager",
        tenant_id=tenant_id,
        catalyst_center=catalyst_center,
        state=WorkflowState.DELETED,
        config=build_site_workflow_config(request),
        destructive=True,
        verbosity=_validated_verbosity(verbosity),
        catalystcenter_log_level=catalystcenter_log_level,
    )).model_dump()


async def deploy_template(
    project_name: str,
    template_name: str,
    target_id: str,
    target_type: str = "MANAGED_DEVICE_UUID",
    force_push: bool = False,
    template_params: dict[str, str] | None = None,
    failure_policy: TemplateFailurePolicy = TemplateFailurePolicy.ABORT_TARGET_ON_ERROR,
    tenant_id: str = "default",
    catalyst_center: str | None = None,
    ctx: Context | None = None,
) -> dict[str, Any]:
    assert ctx is not None
    request = TemplateDeployRequest(
        project_name=project_name,
        template_name=template_name,
        target_id=target_id,
        target_type=target_type,
        force_push=force_push,
        template_params=template_params or {},
        failure_policy=failure_policy,
    )
    return (await _submit(
        ctx=ctx,
        tool_name="deploy_template",
        module_name="template_workflow_manager",
        tenant_id=tenant_id,
        catalyst_center=catalyst_center,
        state=WorkflowState.MERGED,
        config=build_template_workflow_config(request),
    )).model_dump()


async def onboard_fabric_devices(
    fabric_name: str,
    device_ip: str,
    device_roles: list[FabricDeviceRole],
    tenant_id: str = "default",
    catalyst_center: str | None = None,
    ctx: Context | None = None,
) -> dict[str, Any]:
    assert ctx is not None
    request = FabricDeviceRequest(
        fabric_name=fabric_name,
        device_ip=device_ip,
        device_roles=device_roles,
        state=WorkflowState.MERGED,
    )
    return (await _submit(
        ctx=ctx,
        tool_name="onboard_fabric_devices",
        module_name="sda_fabric_devices_workflow_manager",
        tenant_id=tenant_id,
        catalyst_center=catalyst_center,
        state=WorkflowState.MERGED,
        config=build_fabric_devices_workflow_config(request),
    )).model_dump()


async def reprovision_fabric_device(
    fabric_name: str,
    device_ip: str,
    device_roles: list[FabricDeviceRole],
    tenant_id: str = "default",
    catalyst_center: str | None = None,
    ctx: Context | None = None,
) -> dict[str, Any]:
    assert ctx is not None
    request = FabricDeviceRequest(
        fabric_name=fabric_name,
        device_ip=device_ip,
        device_roles=device_roles,
        state=WorkflowState.MERGED,
    )
    return (await _submit(
        ctx=ctx,
        tool_name="reprovision_fabric_device",
        module_name="sda_fabric_devices_workflow_manager",
        tenant_id=tenant_id,
        catalyst_center=catalyst_center,
        state=WorkflowState.MERGED,
        config=build_fabric_devices_workflow_config(request),
        destructive=True,
    )).model_dump()


async def manage_assurance_issues(
    issue_name: str,
    issue_process_type: AssuranceIssueProcessType,
    issue_status: AssuranceIssueStatus | None = None,
    device_name: str | None = None,
    network_device_ip_address: str | None = None,
    site_hierarchy: str | None = None,
    priority: AssuranceIssuePriority | None = None,
    start_datetime: str | None = None,
    end_datetime: str | None = None,
    ignore_duration: str | None = None,
    tenant_id: str = "default",
    catalyst_center: str | None = None,
    ctx: Context | None = None,
) -> dict[str, Any]:
    assert ctx is not None
    request = AssuranceIssueRequest(
        issue_name=issue_name,
        issue_process_type=issue_process_type,
        issue_status=issue_status,
        device_name=device_name,
        network_device_ip_address=network_device_ip_address,
        site_hierarchy=site_hierarchy,
        priority=priority,
        start_datetime=start_datetime,
        end_datetime=end_datetime,
        ignore_duration=ignore_duration,
    )
    return (await _submit(
        ctx=ctx,
        tool_name="manage_assurance_issues",
        module_name="assurance_issue_workflow_manager",
        tenant_id=tenant_id,
        catalyst_center=catalyst_center,
        state=WorkflowState.MERGED,
        config=build_assurance_issue_workflow_config(request),
    )).model_dump()


async def discover_devices(
    discovery_name: str,
    discovery_type: DiscoveryType,
    ip_address_list: list[str],
    protocol_order: str = "ssh,telnet",
    retry: int = 3,
    timeout: int = 5,
    enable_password_list: list[str] | None = None,
    global_credential_id_list: list[str] | None = None,
    preferred_mgmt_ip_method: str | None = None,
    tenant_id: str = "default",
    catalyst_center: str | None = None,
    ctx: Context | None = None,
) -> dict[str, Any]:
    assert ctx is not None
    request = DiscoveryRequest(
        discovery_name=discovery_name,
        discovery_type=discovery_type,
        ip_address_list=ip_address_list,
        protocol_order=protocol_order,
        retry=retry,
        timeout=timeout,
        enable_password_list=enable_password_list,
        global_credential_id_list=global_credential_id_list,
        preferred_mgmt_ip_method=preferred_mgmt_ip_method,
    )
    return (await _submit(
        ctx=ctx,
        tool_name="discover_devices",
        module_name="discovery_workflow_manager",
        tenant_id=tenant_id,
        catalyst_center=catalyst_center,
        state=WorkflowState.MERGED,
        config=build_discovery_workflow_config(request),
    )).model_dump()


async def manage_inventory(
    device_ips: list[str] | None = None,
    device_uuids: list[str] | None = None,
    site_name: str | None = None,
    device_family: str | None = None,
    role: str | None = None,
    update_mgmt_ip: bool = False,
    export_device_list: bool = False,
    tenant_id: str = "default",
    catalyst_center: str | None = None,
    ctx: Context | None = None,
) -> dict[str, Any]:
    assert ctx is not None
    request = InventoryDeviceRequest(
        device_ips=device_ips,
        device_uuids=device_uuids,
        site_name=site_name,
        device_family=device_family,
        role=role,
        update_mgmt_ip=update_mgmt_ip,
        export_device_list=export_device_list,
    )
    return (await _submit(
        ctx=ctx,
        tool_name="manage_inventory",
        module_name="inventory_workflow_manager",
        tenant_id=tenant_id,
        catalyst_center=catalyst_center,
        state=WorkflowState.MERGED,
        config=build_inventory_workflow_config(request),
    )).model_dump()


async def configure_network_settings(
    site_name: str,
    dhcp_servers: list[str] | None = None,
    dns_servers: list[str] | None = None,
    ntp_servers: list[str] | None = None,
    timezone: str | None = None,
    message_of_the_day: str | None = None,
    netflow_collector_ip: str | None = None,
    netflow_collector_port: int | None = None,
    snmp_servers: list[str] | None = None,
    syslog_servers: list[str] | None = None,
    verbosity: int | None = None,
    catalystcenter_log_level: str | None = None,
    tenant_id: str = "default",
    catalyst_center: str | None = None,
    ctx: Context | None = None,
) -> dict[str, Any]:
    assert ctx is not None
    request = NetworkSettingsRequest(
        site_name=site_name,
        dhcp_servers=dhcp_servers,
        dns_servers=dns_servers,
        ntp_servers=ntp_servers,
        timezone=timezone,
        message_of_the_day=message_of_the_day,
        netflow_collector_ip=netflow_collector_ip,
        netflow_collector_port=netflow_collector_port,
        snmp_servers=snmp_servers,
        syslog_servers=syslog_servers,
    )
    return (await _submit(
        ctx=ctx,
        tool_name="configure_network_settings",
        module_name="network_settings_workflow_manager",
        tenant_id=tenant_id,
        catalyst_center=catalyst_center,
        state=WorkflowState.MERGED,
        config=build_network_settings_workflow_config(request),
        verbosity=_validated_verbosity(verbosity),
        catalystcenter_log_level=catalystcenter_log_level,
    )).model_dump()


@mcp.tool(
    name="list_catalyst_centers",
    description="List enabled Catalyst Center clusters defined in catalyst_center_clusters.yaml.",
    annotations=_tool_annotations(read_only=True),
)
async def list_catalyst_centers() -> dict[str, Any]:
    return {
        "catalystCenters": [
            {
                "name": cluster.name,
                "label": cluster.label,
                "host": cluster.host,
                "version": cluster.version,
                "location": cluster.location,
                "enabled": cluster.enabled,
                "credentialEnvPrefix": settings.cluster_env_name(cluster.slug, ""),
            }
            for cluster in CLUSTER_CATALOG.enabled_clusters()
        ]
    }


@mcp.tool(
    name="list_configured_catalyst_centers",
    description="List all Catalyst Center clusters defined in catalyst_center_clusters.yaml, including disabled entries.",
    annotations=_tool_annotations(read_only=True),
)
async def list_configured_catalyst_centers() -> dict[str, Any]:
    return {
        "catalystCenters": [
            {
                "name": cluster.name,
                "label": cluster.label,
                "host": cluster.host,
                "version": cluster.version,
                "location": cluster.location,
                "enabled": cluster.enabled,
                "credentialEnvPrefix": settings.cluster_env_name(cluster.slug, ""),
            }
            for cluster in CLUSTER_CATALOG.catalyst_centers
        ]
    }


async def _get_task_record_for_tenant(iac_task_id: str, tenant_id: str) -> TaskRecord:
    record = await engine.get_task(iac_task_id)
    if record is None:
        raise HTTPException(
            status_code=404,
            detail=(
                "iacTaskId not found. Confirm you are polling the exact task ID returned at submission time. "
                "If the ID is correct, likely causes are task expiry from the Redis store, polling with the wrong tenant, "
                "or submitting and polling against MCP servers that do not share the same Redis/app_name configuration."
            ),
        )
    if record.tenant_id != tenant_id:
        raise HTTPException(status_code=403, detail="iacTaskId does not belong to this tenant")
    return record


@mcp.tool(
    name="get_iac_task",
    description="Return a compact summary for an IaC task by iacTaskId.",
    annotations=_tool_annotations(read_only=True),
)
async def get_iac_task(
    iac_task_id: str,
    tenant_id: str = "default",
) -> dict[str, Any]:
    record = await _get_task_record_for_tenant(iac_task_id, tenant_id)
    return {
        "iacTaskId": record.task_id,
        "iacStatus": record.status.value,
        "iacStatusMessage": record.status_message,
        "toolName": record.tool_name,
        "moduleName": record.module_name,
        "catalystCenter": record.catalyst_center,
        "iacCreatedAt": record.created_at.isoformat(),
        "iacLastUpdatedAt": record.updated_at.isoformat(),
        "iacProgress": record.progress,
        "iacTotal": record.total,
        "destructive": record.destructive,
    }


@mcp.tool(
    name="get_iac_taskdetail",
    description="Return the full stored task status payload for an IaC task by iacTaskId.",
    annotations=_tool_annotations(read_only=True),
)
async def get_iac_taskdetail(
    iac_task_id: str,
    tenant_id: str = "default",
) -> dict[str, Any]:
    record = await _get_task_record_for_tenant(iac_task_id, tenant_id)
    return record.to_status_payload()


def _task_stdout_path_candidates(record: TaskRecord) -> tuple[Path, ...]:
    candidates: list[Path] = []

    artifact_dir = Path(record.artifact_dir)
    candidates.append(artifact_dir / "artifacts" / record.runner_ident / "stdout")

    if stdout_path := (record.result or {}).get("stdout"):
        candidates.append(Path(stdout_path))

    candidates.append(
        settings.runner_artifact_root / record.task_id / "artifacts" / record.runner_ident / "stdout"
    )

    deduped: list[Path] = []
    seen: set[Path] = set()
    for candidate in candidates:
        if candidate not in seen:
            deduped.append(candidate)
            seen.add(candidate)
    return tuple(deduped)


def _resolve_task_stdout_path(record: TaskRecord) -> Path | None:
    for candidate in _task_stdout_path_candidates(record):
        if candidate.exists():
            return candidate
    return None


def _task_sdk_log_path_candidates(record: TaskRecord) -> tuple[Path, ...]:
    artifact_dir = Path(record.artifact_dir)
    configured_path = (
        record.module_args.get("catalystcenter_log_file_path")
        or record.module_args.get("catalyst_center_log_file_path")
        or record.module_args.get("dnac_log_file_path")
        or "dnac.log"
    )

    raw_candidates = [Path(str(configured_path))]
    if str(configured_path) != "catalystcenter.log":
        raw_candidates.append(Path("catalystcenter.log"))
    if str(configured_path) != "dnac.log":
        raw_candidates.append(Path("dnac.log"))

    candidates: list[Path] = []
    for raw_candidate in raw_candidates:
        if raw_candidate.is_absolute():
            candidates.append(raw_candidate)
            continue
        candidates.extend(
            [
                artifact_dir / "project" / raw_candidate,
                artifact_dir / raw_candidate,
                settings.runner_artifact_root / record.task_id / "project" / raw_candidate,
                settings.runner_artifact_root / record.task_id / raw_candidate,
            ]
        )

    deduped: list[Path] = []
    seen: set[Path] = set()
    for candidate in candidates:
        if candidate not in seen:
            deduped.append(candidate)
            seen.add(candidate)
    return tuple(deduped)


def _resolve_task_sdk_log_path(record: TaskRecord) -> Path | None:
    for candidate in _task_sdk_log_path_candidates(record):
        if candidate.exists():
            return candidate
    return None


def _read_head_lines(path: Path, line_count: int) -> str:
    lines: list[str] = []
    with path.open("r", encoding="utf-8", errors="replace") as handle:
        for _, line in zip(range(line_count), handle):
            lines.append(line)
    return "".join(lines)


def _read_tail_lines(path: Path, line_count: int) -> str:
    with path.open("r", encoding="utf-8", errors="replace") as handle:
        return "".join(deque(handle, maxlen=line_count))


DEFAULT_TASK_LOG_TAIL_LINES = 100


def _resolve_line_window(
    *,
    head_lines: int | None,
    tail_lines: int | None,
) -> tuple[str, int]:
    if head_lines is not None and tail_lines is not None:
        raise HTTPException(status_code=400, detail="Specify either head_lines or tail_lines, not both")

    if head_lines is not None:
        line_count = head_lines
        mode = "head"
    else:
        line_count = tail_lines if tail_lines is not None else DEFAULT_TASK_LOG_TAIL_LINES
        mode = "tail"

    if line_count < 1:
        raise HTTPException(status_code=400, detail="Requested line count must be at least 1")

    return mode, line_count


@mcp.tool(
    name="get_task_stdout",
    description=(
        "Return ansible-runner stdout for an IaC task by resolving the artifact path from the task record. "
        "Supports either a head-style slice or a tail-style slice. "
        "If neither head_lines nor tail_lines is provided, the server returns the last 100 lines."
    ),
    annotations=_tool_annotations(read_only=True),
)
async def get_task_stdout(
    iac_task_id: str,
    tail_lines: int | None = None,
    head_lines: int | None = None,
    tenant_id: str = "default",
) -> dict[str, Any]:
    mode, line_count = _resolve_line_window(head_lines=head_lines, tail_lines=tail_lines)

    record = await engine.get_task(iac_task_id)
    if record is None:
        raise HTTPException(status_code=404, detail="iacTaskId not found")
    if record.tenant_id != tenant_id:
        raise HTTPException(status_code=403, detail="iacTaskId does not belong to this tenant")

    stdout_path = _resolve_task_stdout_path(record)
    if stdout_path is None:
        raise HTTPException(
            status_code=404,
            detail="stdout artifact not found for iacTaskId",
        )

    if mode == "head":
        stdout = _read_head_lines(stdout_path, line_count)
        command = f"sed -n '1,{line_count}p' {stdout_path}"
    else:
        stdout = _read_tail_lines(stdout_path, line_count)
        command = f"tail -{line_count} {stdout_path}"

    return {
        "iacTaskId": record.task_id,
        "iacStatus": record.status.value,
        "toolName": record.tool_name,
        "moduleName": record.module_name,
        "iacArtifactDir": record.artifact_dir,
        "stdoutPath": str(stdout_path),
        "mode": mode,
        "lineCount": line_count,
        "commandEquivalent": command,
        "stdout": stdout,
    }


@mcp.tool(
    name="get_task_log",
    description=(
        "Return a text log artifact for an IaC task. Supports ansible-runner stdout and the Catalyst Center SDK log "
        "(typically dnac.log unless an explicit log path was provided to the module). "
        "If neither head_lines nor tail_lines is provided, the server returns the last 100 lines."
    ),
    annotations=_tool_annotations(read_only=True),
)
async def get_task_log(
    iac_task_id: str,
    log_type: Literal["stdout", "catalystcenter"] = "stdout",
    tail_lines: int | None = None,
    head_lines: int | None = None,
    tenant_id: str = "default",
) -> dict[str, Any]:
    mode, line_count = _resolve_line_window(head_lines=head_lines, tail_lines=tail_lines)

    record = await engine.get_task(iac_task_id)
    if record is None:
        raise HTTPException(status_code=404, detail="iacTaskId not found")
    if record.tenant_id != tenant_id:
        raise HTTPException(status_code=403, detail="iacTaskId does not belong to this tenant")

    if log_type == "stdout":
        log_path = _resolve_task_stdout_path(record)
    else:
        log_path = _resolve_task_sdk_log_path(record)

    if log_path is None:
        raise HTTPException(
            status_code=404,
            detail=f"{log_type} log artifact not found for iacTaskId",
        )

    if mode == "head":
        content = _read_head_lines(log_path, line_count)
        command = f"sed -n '1,{line_count}p' {log_path}"
    else:
        content = _read_tail_lines(log_path, line_count)
        command = f"tail -{line_count} {log_path}"

    return {
        "iacTaskId": record.task_id,
        "iacStatus": record.status.value,
        "toolName": record.tool_name,
        "moduleName": record.module_name,
        "iacArtifactDir": record.artifact_dir,
        "logType": log_type,
        "logPath": str(log_path),
        "mode": mode,
        "lineCount": line_count,
        "commandEquivalent": command,
        "content": content,
    }


DIRECT_TOOL_HANDLERS: dict[str, Any] = {
    "provision_site": provision_site,
    "delete_site": delete_site,
    "configure_network_settings": configure_network_settings,
    "deploy_template": deploy_template,
}

# Direct tool definitions are now loaded from tool_catalog.yaml
# This ensures all tool metadata is centralized and schema-driven
DIRECT_TOOL_DEFINITIONS: tuple[ResolvedToolDefinition, ...] = tuple(
    TOOL_CATALOG.iter_direct_tools()
)

CONFIRMATION_GUIDANCE = (
    "Before executing this tool, first propose the planned run details to the user and obtain "
    "explicit confirmation."
)

REPORTS_VIEW_GUIDANCE = (
    "For the `reports` tool, each `generate_report` item must include a non-empty `view` field. "
    "If the report view is unknown, stop and ask the user to choose the view instead of guessing."
)


def _catalog_meta(definition: ResolvedToolDefinition) -> dict[str, Any]:
    meta: dict[str, Any] = {
        "catalog": {
            "topCategory": definition.top_category,
            "subcategory": definition.subcategory,
        }
    }
    if definition.workflow_category is not None:
        meta["catalog"]["workflowCategory"] = definition.workflow_category
    workflow_spec = _workflow_manager_tool_spec(definition.module_name)
    if workflow_spec is not None:
        meta["workflowSpec"] = workflow_spec
    if definition.destructive:
        meta["humanInTheLoop"] = {"required": True}
    return meta


def _tool_description_with_guidance(description: str, *, require_confirmation: bool) -> str:
    if not require_confirmation:
        return description
    if CONFIRMATION_GUIDANCE in description:
        return description
    return f"{description.rstrip()}\n\n{CONFIRMATION_GUIDANCE}"


def _append_module_spec_guidance(
    description: str,
    *,
    module_name: str,
    parameter_guidance: str,
) -> str:
    module_spec_excerpt = _module_spec_excerpt(module_name)
    if not module_spec_excerpt:
        return description
    if "meta.workflowSpec" in description:
        return description
    return (
        f"{description.rstrip()}\n\n"
        "The full normalized module spec is attached in tool metadata as "
        "`meta.workflowSpec`.\n"
        f"{parameter_guidance}\n\n"
        f"{module_spec_excerpt}"
    )


def _workflow_tool_description(
    description: str,
    *,
    require_confirmation: bool,
    tool_name: str,
    module_name: str,
) -> str:
    description = _tool_description_with_guidance(
        description,
        require_confirmation=require_confirmation,
    )
    if tool_name == "reports" and REPORTS_VIEW_GUIDANCE not in description:
        description = f"{description.rstrip()}\n\n{REPORTS_VIEW_GUIDANCE}"
    return _append_module_spec_guidance(
        description,
        module_name=module_name,
        parameter_guidance=(
            "This wrapper still accepts the module `config` payload as JSON input, so "
            "build that payload from `meta.workflowSpec` instead of assuming field names."
        ),
    )


def _register_direct_tools() -> None:
    available_workflow_modules = set(GENERIC_WORKFLOW_MODULES)
    for definition in DIRECT_TOOL_DEFINITIONS:
        if definition.module_name not in available_workflow_modules:
            raise RuntimeError(
                f"Direct tool `{definition.tool_name}` references unknown module "
                f"`{definition.module_name}` in tool_catalog.yaml"
            )
        handler = DIRECT_TOOL_HANDLERS.get(definition.handler_name or "")
        if handler is None:
            raise RuntimeError(
                f"Direct tool `{definition.tool_name}` references unknown handler "
                f"`{definition.handler_name}` in tool_catalog.yaml"
            )
        mcp.tool(
            handler,
            name=definition.tool_name,
            description=_append_module_spec_guidance(
                _tool_description_with_guidance(
                    definition.description,
                    require_confirmation=True,
                ),
                module_name=definition.module_name,
                parameter_guidance=(
                    "This direct MCP tool exposes a simplified argument surface. "
                    "When there is any ambiguity, prefer the exact MCP parameters first, "
                    "then consult `meta.workflowSpec` for the underlying workflow-manager shape."
                ),
            ),
            annotations=_tool_annotations(destructive=definition.destructive),
            meta=_catalog_meta(definition),
        )


def _register_generic_workflow_tools() -> None:
    available_workflow_modules = set(GENERIC_WORKFLOW_MODULES)
    for definition in TOOL_CATALOG.iter_workflow_tools("configuration_creation"):
        if definition.module_name not in available_workflow_modules:
            raise RuntimeError(
                f"Workflow tool `{definition.tool_name}` references unknown module "
                f"`{definition.module_name}` in tool_catalog.yaml"
            )

        def _make_generic_tool(
            module_name: str,
            tool_name: str,
            destructive: bool,
        ):
            state_options = WORKFLOW_STATE_OVERRIDES.get(module_name, ("merged", "deleted"))

            if state_options == ("gathered",):
                async def _generic_tool(
                    config_json: str,
                    state: Literal["gathered"] = "gathered",
                    verbosity: int | None = None,
                    catalystcenter_log_level: str | None = None,
                    tenant_id: str = "default",
                    catalyst_center: str | None = None,
                    ctx: Context | None = None,
                ) -> dict[str, Any]:
                    assert ctx is not None
                    config = _parse_config_json(config_json)
                    _validate_workflow_config(tool_name, module_name, config)
                    return (
                        await _submit(
                            ctx=ctx,
                            tool_name=tool_name,
                            module_name=module_name,
                            tenant_id=tenant_id,
                            catalyst_center=catalyst_center,
                            state=state,
                            config=config,
                            destructive=destructive,
                            verbosity=_validated_verbosity(verbosity),
                            catalystcenter_log_level=catalystcenter_log_level,
                        )
                    ).model_dump()

                return _generic_tool

            if state_options == ("merged",):
                async def _generic_tool(
                    config_json: str,
                    state: Literal["merged"] = "merged",
                    verbosity: int | None = None,
                    catalystcenter_log_level: str | None = None,
                    tenant_id: str = "default",
                    catalyst_center: str | None = None,
                    ctx: Context | None = None,
                ) -> dict[str, Any]:
                    assert ctx is not None
                    config = _parse_config_json(config_json)
                    _validate_workflow_config(tool_name, module_name, config)
                    return (
                        await _submit(
                            ctx=ctx,
                            tool_name=tool_name,
                            module_name=module_name,
                            tenant_id=tenant_id,
                            catalyst_center=catalyst_center,
                            state=state,
                            config=config,
                            destructive=destructive,
                            verbosity=_validated_verbosity(verbosity),
                            catalystcenter_log_level=catalystcenter_log_level,
                        )
                    ).model_dump()

                return _generic_tool

            async def _generic_tool(
                config_json: str,
                state: WorkflowMutationState = WorkflowMutationState.MERGED,
                verbosity: int | None = None,
                catalystcenter_log_level: str | None = None,
                tenant_id: str = "default",
                catalyst_center: str | None = None,
                ctx: Context | None = None,
            ) -> dict[str, Any]:
                assert ctx is not None
                config = _parse_config_json(config_json)
                _validate_workflow_config(tool_name, module_name, config)
                return (
                    await _submit(
                        ctx=ctx,
                        tool_name=tool_name,
                        module_name=module_name,
                        tenant_id=tenant_id,
                        catalyst_center=catalyst_center,
                        state=state,
                        config=config,
                        destructive=destructive,
                        verbosity=_validated_verbosity(verbosity),
                        catalystcenter_log_level=catalystcenter_log_level,
                    )
                ).model_dump()

            return _generic_tool

        generic_tool = _make_generic_tool(
            definition.module_name,
            definition.tool_name,
            definition.destructive,
        )
        is_read_only = (
            definition.module_name in WORKFLOW_STATE_OVERRIDES
            and WORKFLOW_STATE_OVERRIDES[definition.module_name] == ("gathered",)
        )
        mcp.tool(
            generic_tool,
            name=definition.tool_name,
            description=_workflow_tool_description(
                definition.description,
                require_confirmation=not is_read_only,
                tool_name=definition.tool_name,
                module_name=definition.module_name,
            ),
            annotations=_tool_annotations(
                destructive=definition.destructive,
                read_only=is_read_only,
            ),
            meta=_catalog_meta(definition),
        )


def _register_generic_playbook_generator_tools() -> None:
    available_generator_modules = set(GENERIC_PLAYBOOK_GENERATOR_MODULES)
    for definition in TOOL_CATALOG.iter_workflow_tools("configuration_generation"):
        if definition.module_name not in available_generator_modules:
            continue

        def _make_generator_tool(module_name: str, tool_name: str):
            async def _generator_tool(
                module_args_json: str | None = None,
                verbosity: int | None = None,
                catalystcenter_log_level: str | None = None,
                tenant_id: str = "default",
                catalyst_center: str | None = None,
                ctx: Context | None = None,
            ) -> dict[str, Any]:
                assert ctx is not None
                module_args = (
                    _parse_module_args_json(module_args_json)
                    if module_args_json is not None
                    else {}
                )
                module_args.setdefault("state", WorkflowState.GATHERED.value)
                _validate_module_args(module_name, module_args)
                return (
                    await _submit_module(
                        ctx=ctx,
                        tool_name=tool_name,
                        module_name=module_name,
                        tenant_id=tenant_id,
                        catalyst_center=catalyst_center,
                        module_args=module_args,
                        verbosity=_validated_verbosity(verbosity),
                        catalystcenter_log_level=catalystcenter_log_level,
                    )
                ).model_dump()

            return _generator_tool

        generator_tool = _make_generator_tool(definition.module_name, definition.tool_name)
        mcp.tool(
            generator_tool,
            name=definition.tool_name,
            description=_append_module_spec_guidance(
                definition.description,
                module_name=definition.module_name,
                parameter_guidance=(
                    "This generator wrapper accepts module arguments as JSON input, so "
                    "build those arguments from `meta.workflowSpec` instead of assuming key names."
                ),
            ),
            annotations=_tool_annotations(read_only=True),
            meta=_catalog_meta(definition),
        )


_register_direct_tools()
_register_generic_workflow_tools()
_register_generic_playbook_generator_tools()


@asynccontextmanager
async def lifespan(_: FastAPI):
    await engine.connect()
    try:
        yield
    finally:
        await engine.close()


def create_app() -> FastAPI:
    mcp_app = mcp.http_app(
        path="/",
        transport=settings.mcp_transport,
        stateless_http=settings.mcp_stateless_http,
        json_response=True,
    )

    @asynccontextmanager
    async def combined_lifespan(app: FastAPI):
        async with lifespan(app):
            async with mcp_app.lifespan(app):
                yield

    app = FastAPI(title=settings.app_name, version=settings.app_version, lifespan=combined_lifespan)
    app.add_middleware(McpPathCanonicalizationMiddleware, mcp_path=settings.mcp_path)
    app.add_middleware(NoBufferingMiddleware)

    @app.get("/healthz")
    async def healthcheck(identity: dict[str, Any] = Depends(get_identity_context)):
        return {"status": "ok", "subject": identity["subject"]}

    @app.get("/iactasks/get/{task_id}")
    @app.get("/tasks/get/{task_id}")
    async def get_task_status(
        task_id: str,
        identity: dict[str, Any] = Depends(get_identity_context),
    ):
        task = await engine.get_task(task_id)
        if task is None:
            raise HTTPException(status_code=404, detail="iacTaskId not found")
        if task.tenant_id != identity["tenant_id"] and identity["subject"] != "anonymous":
            raise HTTPException(status_code=403, detail="iacTaskId does not belong to this tenant")
        return JSONResponse(task.to_status_payload())

    @app.get("/iactasks/get/{task_id}/logs")
    @app.get("/tasks/get/{task_id}/logs")
    async def get_task_logs(
        task_id: str,
        identity: dict[str, Any] = Depends(get_identity_context),
    ):
        """
        Retrieve detailed logs for a failed IAC task including:
        - Ansible stdout/stderr
        - Catalyst Center API logs
        - Job events
        - Playbook execution details
        """
        task = await engine.get_task(task_id)
        if task is None:
            raise HTTPException(status_code=404, detail="iacTaskId not found")
        if task.tenant_id != identity["tenant_id"] and identity["subject"] != "anonymous":
            raise HTTPException(status_code=403, detail="iacTaskId does not belong to this tenant")
        
        logs = await engine.get_task_logs(task_id)
        return JSONResponse(logs)

    app.mount(settings.mcp_path, mcp_app)
    return app


app = create_app()


def _build_uvicorn_kwargs() -> dict[str, Any]:
    certfile = settings.tls_certfile
    keyfile = settings.tls_keyfile

    if bool(certfile) != bool(keyfile):
        raise ValueError("TLS_CERTFILE and TLS_KEYFILE must be set together")
    if settings.https_only and not (certfile and keyfile):
        raise ValueError(
            "HTTPS_ONLY is enabled but TLS_CERTFILE/TLS_KEYFILE are not configured"
        )
    if (
        settings.mcp_transport == "http"
        and not settings.mcp_stateless_http
        and settings.server_workers != 1
    ):
        raise ValueError(
            "Session-backed MCP HTTP requires SERVER_WORKERS=1. "
            "Use MCP_STATELESS_HTTP=true or reduce SERVER_WORKERS to 1."
        )

    return {
        "host": settings.server_host,
        "port": settings.server_port,
        "workers": settings.server_workers,
        "proxy_headers": settings.proxy_headers,
        "forwarded_allow_ips": settings.forwarded_allow_ips,
        "ssl_certfile": certfile,
        "ssl_keyfile": keyfile,
        "ssl_ca_certs": settings.tls_ca_certs,
    }


def main() -> None:
    uvicorn.run(
        "server:app",
        **_build_uvicorn_kwargs(),
    )


if __name__ == "__main__":
    main()

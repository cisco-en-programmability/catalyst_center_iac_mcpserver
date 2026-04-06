from __future__ import annotations

from contextlib import asynccontextmanager
import json
import os
from pathlib import Path
from typing import Any

import jwt
import uvicorn
from fastapi import Depends, FastAPI, Header, HTTPException, Request
from fastapi.responses import JSONResponse
from fastmcp import Context, FastMCP
from mcp.types import ToolAnnotations
from starlette.middleware.base import BaseHTTPMiddleware

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
    TaskSubmissionResponse,
    TemplateDeployRequest,
    TemplateFailurePolicy,
    WorkflowState,
)
from runner_engine import RunnerEngine, get_runner_engine
from settings import Settings, get_settings
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

class NoBufferingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        response.headers["X-Accel-Buffering"] = "no"
        response.headers.setdefault("Cache-Control", "no-cache")
        return response


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
mcp = FastMCP(
    name=settings.app_name,
    version=settings.app_version,
    instructions=(
        "Cisco Catalyst Center IaC MCP server. Tools expose flat arguments and submit "
        "workflow-manager and playbook-config-generator operations as long-running tasks "
        "backed by ansible-runner."
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
    state: WorkflowState,
    config: list[dict[str, Any]],
    destructive: bool = False,
) -> TaskSubmissionResponse:
    async def notify(progress: float, total: float, message: str) -> None:
        await ctx.report_progress(progress, total, message)

    submission = await engine.submit_workflow(
        tool_name=tool_name,
        module_name=module_name,
        tenant_id=tenant_id,
        state=state.value,
        config=config,
        progress_callback=notify,
        destructive=destructive,
        progress_token=(
            ctx.request_context.meta.progressToken
            if ctx.request_context and ctx.request_context.meta
            else None
        ),
    )
    return TaskSubmissionResponse(taskId=submission.task_id)


async def _submit_module(
    *,
    ctx: Context,
    tool_name: str,
    module_name: str,
    tenant_id: str,
    module_args: dict[str, Any],
    destructive: bool = False,
) -> TaskSubmissionResponse:
    async def notify(progress: float, total: float, message: str) -> None:
        await ctx.report_progress(progress, total, message)

    submission = await engine.submit_module(
        tool_name=tool_name,
        module_name=module_name,
        tenant_id=tenant_id,
        module_args=module_args,
        progress_callback=notify,
        destructive=destructive,
        progress_token=(
            ctx.request_context.meta.progressToken
            if ctx.request_context and ctx.request_context.meta
            else None
        ),
    )
    return TaskSubmissionResponse(taskId=submission.task_id)


def _parse_config_json(config_json: str) -> list[dict[str, Any]]:
    try:
        parsed = json.loads(config_json)
    except json.JSONDecodeError as exc:
        raise HTTPException(status_code=400, detail=f"config_json is not valid JSON: {exc}") from exc
    if not isinstance(parsed, list):
        raise HTTPException(status_code=400, detail="config_json must decode to a list of workflow config objects")
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


@mcp.tool(
    name="provision_site",
    description="Create or update an area, building, or floor in Catalyst Center using flat site arguments.",
    annotations=_tool_annotations(),
)
async def provision_site(
    site_type: SiteType,
    name: str,
    parent_path: str,
    latitude: float | None = None,
    longitude: float | None = None,
    rf_model: str | None = None,
    tenant_id: str = "default",
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
        state=WorkflowState.MERGED,
        config=build_site_workflow_config(request),
    )).model_dump()


@mcp.tool(
    name="delete_site",
    description="Delete a site hierarchy object in Catalyst Center. Client confirmation is required.",
    annotations=_tool_annotations(destructive=True),
    meta={"humanInTheLoop": {"required": True}},
)
async def delete_site(
    site_type: SiteType,
    name: str,
    parent_path: str,
    tenant_id: str = "default",
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
        state=WorkflowState.DELETED,
        config=build_site_workflow_config(request),
        destructive=True,
    )).model_dump()


@mcp.tool(
    name="deploy_template",
    description="Deploy a Catalyst Center template to one target using a flat key-value template parameter map.",
    annotations=_tool_annotations(),
)
async def deploy_template(
    project_name: str,
    template_name: str,
    target_id: str,
    target_type: str = "MANAGED_DEVICE_UUID",
    template_params: dict[str, str] | None = None,
    failure_policy: TemplateFailurePolicy = TemplateFailurePolicy.ABORT_TARGET_ON_ERROR,
    tenant_id: str = "default",
    ctx: Context | None = None,
) -> dict[str, Any]:
    assert ctx is not None
    request = TemplateDeployRequest(
        project_name=project_name,
        template_name=template_name,
        target_id=target_id,
        target_type=target_type,
        template_params=template_params or {},
        failure_policy=failure_policy,
    )
    return (await _submit(
        ctx=ctx,
        tool_name="deploy_template",
        module_name="template_workflow_manager",
        tenant_id=tenant_id,
        state=WorkflowState.MERGED,
        config=build_template_workflow_config(request),
    )).model_dump()


@mcp.tool(
    name="onboard_fabric_devices",
    description="Onboard one fabric device with explicit SD-Access roles.",
    annotations=_tool_annotations(),
)
async def onboard_fabric_devices(
    fabric_name: str,
    device_ip: str,
    device_roles: list[FabricDeviceRole],
    tenant_id: str = "default",
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
        state=WorkflowState.MERGED,
        config=build_fabric_devices_workflow_config(request),
    )).model_dump()


@mcp.tool(
    name="reprovision_fabric_device",
    description="Re-apply provisioning for a fabric device. Client confirmation is required.",
    annotations=_tool_annotations(destructive=True),
    meta={"humanInTheLoop": {"required": True}},
)
async def reprovision_fabric_device(
    fabric_name: str,
    device_ip: str,
    device_roles: list[FabricDeviceRole],
    tenant_id: str = "default",
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
        state=WorkflowState.MERGED,
        config=build_fabric_devices_workflow_config(request),
        destructive=True,
    )).model_dump()


@mcp.tool(
    name="manage_assurance_issues",
    description="Resolve, ignore, or act on an assurance issue using flat issue filters.",
    annotations=_tool_annotations(),
)
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
        state=WorkflowState.MERGED,
        config=build_assurance_issue_workflow_config(request),
    )).model_dump()


@mcp.tool(
    name="discover_devices",
    description="Initiate network device discovery using IP addresses, ranges, or CDP/LLDP.",
    annotations=_tool_annotations(),
)
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
        state=WorkflowState.MERGED,
        config=build_discovery_workflow_config(request),
    )).model_dump()


@mcp.tool(
    name="manage_inventory",
    description="Manage device inventory - update management IPs, assign to sites, or export device lists.",
    annotations=_tool_annotations(),
)
async def manage_inventory(
    device_ips: list[str] | None = None,
    device_uuids: list[str] | None = None,
    site_name: str | None = None,
    device_family: str | None = None,
    role: str | None = None,
    update_mgmt_ip: bool = False,
    export_device_list: bool = False,
    tenant_id: str = "default",
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
        state=WorkflowState.MERGED,
        config=build_inventory_workflow_config(request),
    )).model_dump()


@mcp.tool(
    name="configure_network_settings",
    description="Configure network settings for a site including DHCP, DNS, NTP, SNMP, and Syslog servers.",
    annotations=_tool_annotations(),
)
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
    tenant_id: str = "default",
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
        state=WorkflowState.MERGED,
        config=build_network_settings_workflow_config(request),
    )).model_dump()


def _register_generic_workflow_tools() -> None:
    destructive_module_hints = {"backup_and_restore_workflow_manager", "rma_workflow_manager"}

    for module_name in GENERIC_WORKFLOW_MODULES:
        tool_name = f"run_{module_name}"
        destructive = module_name in destructive_module_hints

        def _make_generic_tool(
            module_name: str,
            tool_name: str,
            destructive: bool,
        ):
            async def _generic_tool(
                config_json: str,
                state: WorkflowState = WorkflowState.MERGED,
                tenant_id: str = "default",
                ctx: Context | None = None,
            ) -> dict[str, Any]:
                assert ctx is not None
                config = _parse_config_json(config_json)
                return (
                    await _submit(
                        ctx=ctx,
                        tool_name=tool_name,
                        module_name=module_name,
                        tenant_id=tenant_id,
                        state=state,
                        config=config,
                        destructive=destructive,
                    )
                ).model_dump()

            return _generic_tool

        generic_tool = _make_generic_tool(module_name, tool_name, destructive)

        description = (
            f"Generic wrapper for `{module_name}`. Pass the module `config` payload as a JSON string."
        )
        meta = {"humanInTheLoop": {"required": True}} if destructive else None
        mcp.tool(
            generic_tool,
            name=tool_name,
            description=description,
            annotations=_tool_annotations(destructive=destructive),
            meta=meta,
        )


def _register_generic_playbook_generator_tools() -> None:
    for module_name in GENERIC_PLAYBOOK_GENERATOR_MODULES:
        base_name = module_name.removesuffix("_playbook_config_generator")
        tool_name = f"generate_{base_name}_config"

        def _make_generator_tool(module_name: str, tool_name: str):
            async def _generator_tool(
                module_args_json: str | None = None,
                tenant_id: str = "default",
                ctx: Context | None = None,
            ) -> dict[str, Any]:
                assert ctx is not None
                module_args = (
                    _parse_module_args_json(module_args_json)
                    if module_args_json is not None
                    else {}
                )
                module_args.setdefault("state", WorkflowState.GATHERED.value)
                return (
                    await _submit_module(
                        ctx=ctx,
                        tool_name=tool_name,
                        module_name=module_name,
                        tenant_id=tenant_id,
                        module_args=module_args,
                    )
                ).model_dump()

            return _generator_tool

        generator_tool = _make_generator_tool(module_name, tool_name)
        description = (
            f"Read-only wrapper for `{module_name}`. Pass the module arguments as a JSON "
            "object string. If `state` is omitted, it defaults to `gathered`."
        )
        mcp.tool(
            generator_tool,
            name=tool_name,
            description=description,
            annotations=_tool_annotations(read_only=True),
        )


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
    app = FastAPI(title=settings.app_name, version=settings.app_version, lifespan=lifespan)
    app.add_middleware(NoBufferingMiddleware)

    @app.get("/healthz")
    async def healthcheck(identity: dict[str, Any] = Depends(get_identity_context)):
        return {"status": "ok", "subject": identity["subject"]}

    @app.get("/tasks/get/{task_id}")
    async def get_task_status(
        task_id: str,
        identity: dict[str, Any] = Depends(get_identity_context),
    ):
        task = await engine.get_task(task_id)
        if task is None:
            raise HTTPException(status_code=404, detail="taskId not found")
        if task.tenant_id != identity["tenant_id"] and identity["subject"] != "anonymous":
            raise HTTPException(status_code=403, detail="taskId does not belong to this tenant")
        return JSONResponse(task.to_status_payload())

    app.mount(
        settings.mcp_path,
        mcp.http_app(path="/", transport=settings.mcp_transport, stateless_http=True),
    )
    return app


app = create_app()


def main() -> None:
    uvicorn.run(
        "server:app",
        host=settings.server_host,
        port=settings.server_port,
        workers=settings.server_workers,
        proxy_headers=settings.proxy_headers,
        forwarded_allow_ips=settings.forwarded_allow_ips,
        ssl_certfile=settings.tls_certfile,
        ssl_keyfile=settings.tls_keyfile,
        ssl_ca_certs=settings.tls_ca_certs,
    )


if __name__ == "__main__":
    main()

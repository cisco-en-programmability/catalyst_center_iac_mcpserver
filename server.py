from __future__ import annotations

from contextlib import asynccontextmanager
from typing import Any

import jwt
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
    FabricDeviceRequest,
    FabricDeviceRole,
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
    build_fabric_devices_workflow_config,
    build_site_workflow_config,
    build_template_workflow_config,
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
        "workflow-manager operations as long-running tasks backed by ansible-runner."
    ),
    strict_input_validation=True,
)


def _tool_annotations(*, destructive: bool = False) -> ToolAnnotations:
    return ToolAnnotations(
        readOnlyHint=False,
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

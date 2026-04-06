from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class TaskLifecycleStatus(str, Enum):
    SUBMITTED = "submitted"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class SiteType(str, Enum):
    AREA = "area"
    BUILDING = "building"
    FLOOR = "floor"


class WorkflowState(str, Enum):
    MERGED = "merged"
    DELETED = "deleted"
    GATHERED = "gathered"


class FabricDeviceRole(str, Enum):
    BORDER_NODE = "BORDER_NODE"
    EDGE_NODE = "EDGE_NODE"
    CONTROL_PLANE_NODE = "CONTROL_PLANE_NODE"
    WIRELESS_CONTROLLER_NODE = "WIRELESS_CONTROLLER_NODE"


class AssuranceIssueProcessType(str, Enum):
    RESOLUTION = "resolution"
    IGNORE = "ignore"
    COMMAND_EXECUTION = "command_execution"


class AssuranceIssueStatus(str, Enum):
    ACTIVE = "ACTIVE"
    RESOLVED = "RESOLVED"
    IGNORED = "IGNORED"


class AssuranceIssuePriority(str, Enum):
    P1 = "P1"
    P2 = "P2"
    P3 = "P3"
    P4 = "P4"


class TemplateFailurePolicy(str, Enum):
    ABORT_TARGET_ON_ERROR = "ABORT_TARGET_ON_ERROR"
    CONTINUE_ON_ERROR = "CONTINUE_ON_ERROR"


class TenantCredentials(BaseModel):
    host: str
    username: str
    password: str
    verify_ssl: bool = True
    port: int = 443
    version: str = "2.3.7.9"


class SiteProvisionRequest(BaseModel):
    site_type: SiteType
    name: str
    parent_path: str
    latitude: float | None = None
    longitude: float | None = None
    rf_model: str | None = None
    state: WorkflowState = WorkflowState.MERGED

    @field_validator("parent_path")
    @classmethod
    def validate_parent_path(cls, value: str) -> str:
        trimmed = value.strip().strip("/")
        if not trimmed:
            raise ValueError("parent_path must be a non-empty site hierarchy")
        return trimmed


class TemplateDeployRequest(BaseModel):
    project_name: str
    template_name: str
    target_id: str
    target_type: Literal["MANAGED_DEVICE_UUID", "MANAGED_DEVICE_IP", "HOSTNAME"] = (
        "MANAGED_DEVICE_UUID"
    )
    template_params: dict[str, str] = Field(default_factory=dict)
    failure_policy: TemplateFailurePolicy = TemplateFailurePolicy.ABORT_TARGET_ON_ERROR


class FabricDeviceRequest(BaseModel):
    fabric_name: str
    device_ip: str
    device_roles: list[FabricDeviceRole]
    state: WorkflowState = WorkflowState.MERGED


class AssuranceIssueRequest(BaseModel):
    issue_name: str
    issue_process_type: AssuranceIssueProcessType
    issue_status: AssuranceIssueStatus | None = None
    device_name: str | None = None
    network_device_ip_address: str | None = None
    site_hierarchy: str | None = None
    priority: AssuranceIssuePriority | None = None
    start_datetime: str | None = None
    end_datetime: str | None = None
    ignore_duration: str | None = None


class DiscoveryType(str, Enum):
    SINGLE = "SINGLE"
    RANGE = "RANGE"
    MULTI_RANGE = "MULTI_RANGE"
    CDP = "CDP"
    LLDP = "LLDP"
    CIDR = "CIDR"


class DiscoveryRequest(BaseModel):
    discovery_name: str
    discovery_type: DiscoveryType
    ip_address_list: list[str]
    protocol_order: str = "ssh,telnet"
    retry: int = 3
    timeout: int = 5
    enable_password_list: list[str] | None = None
    global_credential_id_list: list[str] | None = None
    preferred_mgmt_ip_method: str | None = None


class InventoryDeviceRequest(BaseModel):
    device_ips: list[str] | None = None
    device_uuids: list[str] | None = None
    site_name: str | None = None
    device_family: str | None = None
    role: str | None = None
    update_mgmt_ip: bool = False
    export_device_list: bool = False


class NetworkSettingsRequest(BaseModel):
    site_name: str
    dhcp_servers: list[str] | None = None
    dns_servers: list[str] | None = None
    ntp_servers: list[str] | None = None
    timezone: str | None = None
    message_of_the_day: str | None = None
    netflow_collector_ip: str | None = None
    netflow_collector_port: int | None = None
    snmp_servers: list[str] | None = None
    syslog_servers: list[str] | None = None


class TaskSubmissionResponse(BaseModel):
    taskId: str
    status: Literal["submitted"] = "submitted"


class TaskRecord(BaseModel):
    task_id: str
    tenant_id: str
    tool_name: str
    module_name: str
    status: TaskLifecycleStatus
    status_message: str
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)
    progress: float = 0.0
    total: float = 100.0
    artifact_dir: str
    runner_ident: str
    module_args: dict[str, Any]
    result: dict[str, Any] | None = None
    events: list[dict[str, Any]] = Field(default_factory=list)
    destructive: bool = False
    progress_token: str | int | None = None

    def to_status_payload(self) -> dict[str, Any]:
        return {
            "taskId": self.task_id,
            "status": self.status.value,
            "statusMessage": self.status_message,
            "createdAt": self.created_at.isoformat(),
            "lastUpdatedAt": self.updated_at.isoformat(),
            "progress": self.progress,
            "total": self.total,
            "artifactDir": self.artifact_dir,
            "runnerIdent": self.runner_ident,
            "toolName": self.tool_name,
            "moduleName": self.module_name,
            "result": self.result,
            "events": self.events,
            "destructive": self.destructive,
        }

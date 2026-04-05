from __future__ import annotations

from typing import Any

from models import (
    AssuranceIssueRequest,
    FabricDeviceRequest,
    SiteProvisionRequest,
    SiteType,
    TemplateDeployRequest,
)


def _compact(data: dict[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in data.items() if value is not None}


def build_site_workflow_config(request: SiteProvisionRequest) -> list[dict[str, Any]]:
    site_payload = {
        "name": request.name,
        "parent_name": request.parent_path,
    }
    if request.site_type == SiteType.BUILDING:
        site_payload.update(
            {
                "latitude": request.latitude,
                "longitude": request.longitude,
            }
        )
    elif request.site_type == SiteType.FLOOR:
        site_payload.update({"rf_model": request.rf_model})

    return [
        {
            "type": request.site_type.value,
            "site": {
                request.site_type.value: _compact(site_payload),
            },
        }
    ]


def build_template_workflow_config(request: TemplateDeployRequest) -> list[dict[str, Any]]:
    template_params = [
        {"key": key, "value": value}
        for key, value in sorted(request.template_params.items())
    ]
    return [
        {
            "template_deploy": {
                "project_name": request.project_name,
                "template_name": request.template_name,
                "target_info": [
                    {
                        "id": request.target_id,
                        "type": request.target_type,
                    }
                ],
                "template_params": template_params,
                "failure_policy": request.failure_policy.value,
            }
        }
    ]


def build_fabric_devices_workflow_config(
    request: FabricDeviceRequest,
) -> list[dict[str, Any]]:
    return [
        {
            "fabric_devices": [
                {
                    "fabric_name": request.fabric_name,
                    "device_ip": request.device_ip,
                    "device_roles": [role.value for role in request.device_roles],
                }
            ]
        }
    ]


def build_assurance_issue_workflow_config(
    request: AssuranceIssueRequest,
) -> list[dict[str, Any]]:
    assurance_issue = _compact(
        {
            "issue_name": request.issue_name,
            "issue_process_type": request.issue_process_type.value,
            "issue_status": request.issue_status.value if request.issue_status else None,
            "device_name": request.device_name,
            "network_device_ip_address": request.network_device_ip_address,
            "site_hierarchy": request.site_hierarchy,
            "priority": request.priority.value if request.priority else None,
            "start_datetime": request.start_datetime,
            "end_datetime": request.end_datetime,
            "ignore_duration": request.ignore_duration,
        }
    )
    return [{"assurance_issue": [assurance_issue]}]


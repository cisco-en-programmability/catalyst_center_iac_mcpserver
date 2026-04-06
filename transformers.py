from __future__ import annotations

from typing import Any

from models import (
    AssuranceIssueRequest,
    DiscoveryRequest,
    FabricDeviceRequest,
    InventoryDeviceRequest,
    NetworkSettingsRequest,
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


def build_discovery_workflow_config(
    request: DiscoveryRequest,
) -> list[dict[str, Any]]:
    discovery_config = _compact(
        {
            "discovery_name": request.discovery_name,
            "discovery_type": request.discovery_type.value,
            "ip_address_list": request.ip_address_list,
            "protocol_order": request.protocol_order,
            "retry": request.retry,
            "timeout": request.timeout,
            "enable_password_list": request.enable_password_list,
            "global_credential_id_list": request.global_credential_id_list,
            "preferred_mgmt_ip_method": request.preferred_mgmt_ip_method,
        }
    )
    return [{"discovery": [discovery_config]}]


def build_inventory_workflow_config(
    request: InventoryDeviceRequest,
) -> list[dict[str, Any]]:
    inventory_config = _compact(
        {
            "device_ips": request.device_ips,
            "device_uuids": request.device_uuids,
            "site_name": request.site_name,
            "device_family": request.device_family,
            "role": request.role,
            "update_mgmt_ip": True if request.update_mgmt_ip else None,
            "export_device_list": True if request.export_device_list else None,
        }
    )
    return [{"inventory": [inventory_config]}]


def build_network_settings_workflow_config(
    request: NetworkSettingsRequest,
) -> list[dict[str, Any]]:
    network_settings = _compact(
        {
            "site_name": request.site_name,
            "dhcp_servers": request.dhcp_servers,
            "dns_servers": request.dns_servers,
            "ntp_servers": request.ntp_servers,
            "timezone": request.timezone,
            "message_of_the_day": request.message_of_the_day,
            "netflow_collector_ip": request.netflow_collector_ip,
            "netflow_collector_port": request.netflow_collector_port,
            "snmp_servers": request.snmp_servers,
            "syslog_servers": request.syslog_servers,
        }
    )
    return [{"network_settings": [network_settings]}]

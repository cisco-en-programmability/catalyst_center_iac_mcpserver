from models import (
    AssuranceIssuePriority,
    AssuranceIssueProcessType,
    AssuranceIssueRequest,
    FabricDeviceRequest,
    FabricDeviceRole,
    SiteProvisionRequest,
    SiteType,
    TemplateDeployRequest,
    TemplateFailurePolicy,
)
from transformers import (
    build_assurance_issue_workflow_config,
    build_fabric_devices_workflow_config,
    build_site_workflow_config,
    build_template_workflow_config,
)


def test_build_site_workflow_config_for_floor():
    request = SiteProvisionRequest(
        site_type=SiteType.FLOOR,
        name="floor-3",
        parent_path="Global/USA/SJC/HQ",
        rf_model="Outdoor Open Space",
    )

    config = build_site_workflow_config(request)

    assert config == [
        {
            "type": "floor",
            "site": {
                "floor": {
                    "name": "floor-3",
                    "parent_name": "Global/USA/SJC/HQ",
                    "rf_model": "Outdoor Open Space",
                }
            },
        }
    ]


def test_build_template_workflow_config_expands_flat_params():
    request = TemplateDeployRequest(
        project_name="Campus",
        template_name="Day0",
        target_id="device-123",
        template_params={"hostname": "edge-1", "loopback": "10.0.0.1"},
        failure_policy=TemplateFailurePolicy.ABORT_TARGET_ON_ERROR,
    )

    config = build_template_workflow_config(request)

    assert config[0]["template_deploy"]["template_params"] == [
        {"key": "hostname", "value": "edge-1"},
        {"key": "loopback", "value": "10.0.0.1"},
    ]


def test_build_fabric_devices_workflow_config_normalizes_roles():
    request = FabricDeviceRequest(
        fabric_name="HQ-Fabric",
        device_ip="10.10.10.10",
        device_roles=[FabricDeviceRole.BORDER_NODE, FabricDeviceRole.EDGE_NODE],
    )

    config = build_fabric_devices_workflow_config(request)

    assert config == [
        {
            "fabric_devices": [
                {
                    "fabric_name": "HQ-Fabric",
                    "device_ip": "10.10.10.10",
                    "device_roles": ["BORDER_NODE", "EDGE_NODE"],
                }
            ]
        }
    ]


def test_build_assurance_issue_workflow_config_compacts_filters():
    request = AssuranceIssueRequest(
        issue_name="AP Down",
        issue_process_type=AssuranceIssueProcessType.IGNORE,
        priority=AssuranceIssuePriority.P2,
        ignore_duration="24h",
    )

    config = build_assurance_issue_workflow_config(request)

    assert config == [
        {
            "assurance_issue": [
                {
                    "issue_name": "AP Down",
                    "issue_process_type": "ignore",
                    "priority": "P2",
                    "ignore_duration": "24h",
                }
            ]
        }
    ]


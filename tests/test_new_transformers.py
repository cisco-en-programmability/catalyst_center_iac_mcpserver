from models import (
    DiscoveryRequest,
    DiscoveryType,
    InventoryDeviceRequest,
    NetworkSettingsRequest,
)
from transformers import (
    build_discovery_workflow_config,
    build_inventory_workflow_config,
    build_network_settings_workflow_config,
)


def test_build_discovery_workflow_config_with_cidr():
    request = DiscoveryRequest(
        discovery_name="Campus-Discovery",
        discovery_type=DiscoveryType.CIDR,
        ip_address_list=["10.10.10.0/24", "192.168.1.0/24"],
        protocol_order="ssh,telnet",
        retry=3,
        timeout=5,
    )

    config = build_discovery_workflow_config(request)

    assert config == [
        {
            "discovery": [
                {
                    "discovery_name": "Campus-Discovery",
                    "discovery_type": "CIDR",
                    "ip_address_list": ["10.10.10.0/24", "192.168.1.0/24"],
                    "protocol_order": "ssh,telnet",
                    "retry": 3,
                    "timeout": 5,
                }
            ]
        }
    ]


def test_build_discovery_workflow_config_with_credentials():
    request = DiscoveryRequest(
        discovery_name="Secure-Discovery",
        discovery_type=DiscoveryType.RANGE,
        ip_address_list=["10.10.10.1-10.10.10.50"],
        global_credential_id_list=["cred-1", "cred-2"],
        enable_password_list=["enable123"],
        preferred_mgmt_ip_method="UseLoopBack",
    )

    config = build_discovery_workflow_config(request)

    assert config[0]["discovery"][0]["global_credential_id_list"] == ["cred-1", "cred-2"]
    assert config[0]["discovery"][0]["enable_password_list"] == ["enable123"]
    assert config[0]["discovery"][0]["preferred_mgmt_ip_method"] == "UseLoopBack"


def test_build_inventory_workflow_config_with_device_ips():
    request = InventoryDeviceRequest(
        device_ips=["10.10.10.1", "10.10.10.2"],
        site_name="Global/USA/SJC",
        update_mgmt_ip=True,
    )

    config = build_inventory_workflow_config(request)

    assert config == [
        {
            "inventory": [
                {
                    "device_ips": ["10.10.10.1", "10.10.10.2"],
                    "site_name": "Global/USA/SJC",
                    "update_mgmt_ip": True,
                }
            ]
        }
    ]


def test_build_inventory_workflow_config_with_filters():
    request = InventoryDeviceRequest(
        device_family="Switches and Hubs",
        role="ACCESS",
        export_device_list=True,
    )

    config = build_inventory_workflow_config(request)

    assert config[0]["inventory"][0]["device_family"] == "Switches and Hubs"
    assert config[0]["inventory"][0]["role"] == "ACCESS"
    assert config[0]["inventory"][0]["export_device_list"] is True


def test_build_network_settings_workflow_config_complete():
    request = NetworkSettingsRequest(
        site_name="Global/USA/San Jose HQ",
        dhcp_servers=["10.10.10.10", "10.10.10.11"],
        dns_servers=["8.8.8.8", "8.8.4.4"],
        ntp_servers=["time.nist.gov"],
        timezone="America/Los_Angeles",
        message_of_the_day="Welcome to HQ",
        netflow_collector_ip="10.10.10.100",
        netflow_collector_port=9995,
        snmp_servers=["10.10.10.101"],
        syslog_servers=["10.10.10.102"],
    )

    config = build_network_settings_workflow_config(request)

    network_settings = config[0]["network_settings"][0]
    assert network_settings["site_name"] == "Global/USA/San Jose HQ"
    assert network_settings["dhcp_servers"] == ["10.10.10.10", "10.10.10.11"]
    assert network_settings["dns_servers"] == ["8.8.8.8", "8.8.4.4"]
    assert network_settings["ntp_servers"] == ["time.nist.gov"]
    assert network_settings["timezone"] == "America/Los_Angeles"
    assert network_settings["message_of_the_day"] == "Welcome to HQ"
    assert network_settings["netflow_collector_ip"] == "10.10.10.100"
    assert network_settings["netflow_collector_port"] == 9995


def test_build_network_settings_workflow_config_minimal():
    request = NetworkSettingsRequest(
        site_name="Global/USA/Branch",
        dns_servers=["8.8.8.8"],
    )

    config = build_network_settings_workflow_config(request)

    network_settings = config[0]["network_settings"][0]
    assert network_settings["site_name"] == "Global/USA/Branch"
    assert network_settings["dns_servers"] == ["8.8.8.8"]
    assert "dhcp_servers" not in network_settings
    assert "ntp_servers" not in network_settings

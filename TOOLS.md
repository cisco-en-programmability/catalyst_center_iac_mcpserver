# Catalyst Center MCP Tool Inventory

This file lists the tools exposed by the Catalyst Center MCP server.

## Direct Tools

| Tool | Category | Notes |
| --- | --- | --- |
| `provision_site` | `site_management` | Typed direct tool |
| `delete_site` | `site_management` | Typed direct tool, destructive |
| `configure_network_settings` | `site_management` | Typed direct tool |
| `deploy_template` | `cli_templates` | Typed direct tool |
| `discover_devices` | `discovery` | Typed direct tool |
| `manage_inventory` | `inventory` | Typed direct tool |
| `onboard_fabric_devices` | `sd_access_fabric` | Typed direct tool |
| `reprovision_fabric_device` | `sd_access_fabric` | Typed direct tool, destructive |
| `manage_assurance_issues` | `assurance` | Typed direct tool |
| `list_catalyst_centers` | `platform` | Read-only helper tool |

## Workflow Manager Tools

These are registered as `run_<module_name>`.

| Category | Tools |
| --- | --- |
| `site_management` | `run_site_workflow_manager`, `run_network_settings_workflow_manager`, `run_tags_workflow_manager` |
| `ise_and_aaa` | `run_user_role_workflow_manager`, `run_ise_radius_integration_workflow_manager` |
| `cli_templates` | `run_template_workflow_manager` |
| `pnp` | `run_pnp_workflow_manager` |
| `wireless` | `run_wireless_design_workflow_manager` |
| `network_profiles` | `run_network_profile_switching_workflow_manager`, `run_network_profile_wireless_workflow_manager` |
| `assurance` | `run_assurance_issue_workflow_manager`, `run_assurance_icap_settings_workflow_manager`, `run_assurance_device_health_score_settings_workflow_manager` |
| `application_policy` | `run_application_policy_workflow_manager` |
| `events_and_notifications` | `run_events_and_notifications_workflow_manager` |
| `config_backups` | `run_device_configs_backup_workflow_manager`, `run_backup_and_restore_workflow_manager` |
| `access_points_configuration` | `run_accesspoint_workflow_manager`, `run_accesspoint_location_workflow_manager` |
| `discovery` | `run_discovery_workflow_manager`, `run_device_credential_workflow_manager` |
| `inventory` | `run_inventory_workflow_manager`, `run_network_devices_info_workflow_manager`, `run_network_compliance_workflow_manager` |
| `provision` | `run_provision_workflow_manager` |
| `reports` | `run_reports_workflow_manager` |
| `path_trace` | `run_path_trace_workflow_manager` |
| `sd_access_fabric` | `run_sda_fabric_devices_workflow_manager`, `run_sda_fabric_multicast_workflow_manager`, `run_sda_fabric_sites_zones_workflow_manager`, `run_sda_fabric_transits_workflow_manager`, `run_sda_fabric_virtual_networks_workflow_manager`, `run_sda_extranet_policies_workflow_manager`, `run_fabric_devices_info_workflow_manager`, `run_sda_host_port_onboarding_workflow_manager` |
| `lan_automation` | `run_lan_automation_workflow_manager` |
| `wired_campus` | `run_wired_campus_automation_workflow_manager` |
| `software_upgrade_swim` | `run_swim_workflow_manager` |
| `rma` | `run_rma_workflow_manager` |

## Config Generator Tools

These are registered as `generate_<domain>_config`.

| Category | Tools |
| --- | --- |
| `site_management` | `generate_site_config`, `generate_network_settings_config`, `generate_tags_config` |
| `ise_and_aaa` | `generate_user_role_config`, `generate_ise_radius_integration_config` |
| `cli_templates` | `generate_template_config` |
| `pnp` | `generate_pnp_config` |
| `wireless` | `generate_wireless_design_config` |
| `network_profiles` | `generate_network_profile_switching_config`, `generate_network_profile_wireless_config` |
| `assurance` | `generate_assurance_issue_config`, `generate_assurance_icap_settings_config`, `generate_assurance_device_health_score_settings_config` |
| `application_policy` | `generate_application_policy_config` |
| `events_and_notifications` | `generate_events_and_notifications_config` |
| `config_backups` | `generate_device_configs_backup_config`, `generate_backup_and_restore_config` |
| `access_points_configuration` | `generate_accesspoint_config`, `generate_accesspoint_location_config` |
| `discovery` | `generate_discovery_config`, `generate_device_credential_config` |
| `inventory` | `generate_inventory_config`, `generate_network_devices_info_config`, `generate_network_compliance_config` |
| `provision` | `generate_provision_config` |
| `reports` | `generate_reports_config` |
| `path_trace` | `generate_path_trace_config` |
| `sd_access_fabric` | `generate_sda_fabric_devices_config`, `generate_sda_fabric_multicast_config`, `generate_sda_fabric_sites_zones_config`, `generate_sda_fabric_transits_config`, `generate_sda_fabric_virtual_networks_config`, `generate_sda_extranet_policies_config`, `generate_fabric_devices_info_config`, `generate_sda_host_port_onboarding_config` |
| `lan_automation` | `generate_lan_automation_config` |
| `wired_campus` | `generate_wired_campus_automation_config` |
| `software_upgrade_swim` | `generate_swim_config` |
| `rma` | `generate_rma_config` |

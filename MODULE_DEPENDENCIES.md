# Module Dependencies and Prerequisites Guide

This guide documents the **mandatory requirements** and **prerequisite data** needed for each Catalyst Center workflow module. Use this to understand what information you must gather before calling each tool.

---

## 📋 Table of Contents

- [Understanding Dependencies](#understanding-dependencies)
- [Site Management](#site-management)
- [Network Settings](#network-settings)
- [Discovery](#discovery)
- [Inventory Management](#inventory-management)
- [Compliance](#compliance)
- [SD-Access Fabric](#sd-access-fabric)
- [Templates](#templates)
- [User & Role Management](#user--role-management)
- [Common Data Gathering Tools](#common-data-gathering-tools)

---

## Understanding Dependencies

### Dependency Types

1. **Hierarchical Dependencies** - Parent objects must exist first
   - Example: Site → Building → Floor
   - Example: Fabric Site → Fabric Devices

2. **Reference Dependencies** - Referenced objects must exist
   - Example: Template deployment needs template name + project name
   - Example: Device assignment needs device IP + site name

3. **Discovery Dependencies** - Objects must be discovered/visible
   - Example: Compliance needs device IP (device must be in inventory)
   - Example: Fabric onboarding needs device IP (device must be provisioned)

4. **Configuration Dependencies** - Settings must be configured
   - Example: Device provisioning needs network settings configured
   - Example: Fabric devices need fabric site created

---

## Site Management

### `site_workflow_manager`

**Purpose:** Create/update/delete site hierarchy (areas, buildings, floors)

#### Mandatory Requirements

| Operation | Required Fields | Prerequisites |
|-----------|----------------|---------------|
| Create Area | `name`, `parent_path` | Parent site must exist |
| Create Building | `name`, `parent_path`, `latitude`, `longitude` | Parent area must exist |
| Create Floor | `name`, `parent_path`, `rf_model`, `width`, `length`, `height` | Parent building must exist |
| Delete Site | `name` OR `site_name_hierarchy` | No child sites, no assigned devices |

#### How to Get Required Information

**1. Get existing site hierarchy:**
```python
# Use site_playbook_config_generator to export current sites
result = await generate_site_config(
    module_args_json='{"state": "gathered"}'
)
# Returns all sites with their paths
```

**2. Verify parent exists:**
```python
# Check if "Global/USA" exists before creating "Global/USA/California"
sites = result["config"]
parent_exists = any(s["site"]["area"]["parent_name_hierarchy"] == "Global/USA" for s in sites)
```

**3. Get geographic coordinates (for buildings):**
```bash
# Use geocoding service or manual lookup
# Example: San Jose, CA = 37.3382° N, 121.8863° W
```

#### Example Workflow

```python
# Step 1: Create area
await provision_site(
    site_type="area",
    name="USA",
    parent_path="Global"
)

# Step 2: Create building (requires area from step 1)
await provision_site(
    site_type="building", 
    name="San-Jose-HQ",
    parent_path="Global/USA",
    latitude=37.3382,
    longitude=-121.8863
)

# Step 3: Create floor (requires building from step 2)
await provision_site(
    site_type="floor",
    name="Floor-1",
    parent_path="Global/USA/San-Jose-HQ",
    rf_model="Cubes And Walled Offices",
    width=100.0,
    length=100.0,
    height=10.0
)
```

---

## Network Settings

### `network_settings_workflow_manager`

**Purpose:** Configure DHCP, DNS, NTP, SNMP, Syslog for a site

#### Mandatory Requirements

| Field | Required | Type | Notes |
|-------|----------|------|-------|
| `site_name` | ✅ Yes | string | Must be existing site hierarchy path |
| `dhcp_servers` | ❌ No | list[string] | IP addresses |
| `dns_servers` | ❌ No | list[string] | IP addresses |
| `ntp_servers` | ❌ No | list[string] | IP addresses or hostnames |
| `timezone` | ❌ No | string | IANA timezone (e.g., "America/Los_Angeles") |

#### How to Get Required Information

**1. Get site name hierarchy:**
```python
# List all sites
sites = await generate_site_config()
site_paths = [s["site"]["area"]["parent_name_hierarchy"] + "/" + s["site"]["area"]["name"] 
              for s in sites["config"]]
# Example: "Global/USA/San-Jose-HQ"
```

**2. Get current network settings:**
```python
# Export current settings
settings = await generate_network_settings_config(
    module_args_json='{"site_name": "Global/USA/San-Jose-HQ"}'
)
```

**3. Verify server reachability:**
```bash
# Test DHCP server
ping 10.10.10.1

# Test DNS server  
nslookup google.com 8.8.8.8

# Test NTP server
ntpdate -q time.cisco.com
```

#### Example Workflow

```python
# Step 1: Ensure site exists
await provision_site(site_type="building", name="HQ", parent_path="Global")

# Step 2: Configure network settings
await configure_network_settings(
    site_name="Global/HQ",
    dhcp_servers=["10.10.10.1"],
    dns_servers=["8.8.8.8", "8.8.4.4"],
    ntp_servers=["time.cisco.com"],
    timezone="America/Los_Angeles"
)
```

---

## Discovery

### `discovery_workflow_manager`

**Purpose:** Discover network devices using IP ranges, CDP, or LLDP

#### Mandatory Requirements

| Field | Required | Type | Notes |
|-------|----------|------|-------|
| `discovery_name` | ✅ Yes | string | Unique name for this discovery |
| `discovery_type` | ✅ Yes | enum | "SINGLE", "RANGE", "MULTI RANGE", "CDP", "LLDP" |
| `ip_address_list` | ✅ Yes | list[string] | IPs, ranges, or seed IPs for CDP/LLDP |
| `protocol_order` | ❌ No | string | Default: "ssh,telnet" |
| `global_credential_id_list` | ⚠️ Conditional | list[string] | Required for SSH/SNMP discovery |

#### How to Get Required Information

**1. Get available credentials:**
```python
# Use device_credential_playbook_config_generator
creds = await generate_device_credential_config()
cli_creds = [c for c in creds["config"] if c.get("cli_credential")]
snmp_creds = [c for c in creds["config"] if c.get("snmp_v2c_read")]
```

**2. Plan IP ranges:**
```bash
# Scan network to find active devices
nmap -sn 10.10.20.0/24

# Or use specific IPs
# 10.10.20.1, 10.10.20.2, 10.10.20.3
```

**3. Verify network connectivity:**
```bash
# Test SSH access
ssh admin@10.10.20.1

# Test SNMP
snmpwalk -v2c -c public 10.10.20.1 system
```

#### Example Workflow

```python
# Step 1: Get credential IDs
creds = await generate_device_credential_config()
cli_cred_id = creds["config"][0]["cli_credential"][0]["id"]
snmp_cred_id = creds["config"][0]["snmp_v2c_read"][0]["id"]

# Step 2: Discover devices
result = await discover_devices(
    discovery_name="Branch-Discovery-2026",
    discovery_type="RANGE",
    ip_address_list=["10.10.20.1-10.10.20.50"],
    protocol_order="ssh,telnet",
    global_credential_id_list=[cli_cred_id, snmp_cred_id]
)

# Step 3: Wait for discovery to complete
final = await wait_iac_task(iac_task_id=result["iacTaskId"])
```

---

## Inventory Management

### `inventory_workflow_manager`

**Purpose:** Assign devices to sites, update management IPs, export inventory

#### Mandatory Requirements

| Operation | Required Fields | Prerequisites |
|-----------|----------------|---------------|
| Assign to Site | `device_ip`, `site_name` | Device discovered, site exists |
| Update Mgmt IP | `device_ip`, `new_mgmt_ip` | Device in inventory |
| Export Inventory | `site_name` OR none | Sites exist |

#### How to Get Required Information

**1. Get discovered devices:**
```python
# Export current inventory
inventory = await generate_inventory_config()
devices = inventory["config"]

# Get device IPs
device_ips = [d["management_ip_address"] for d in devices]
```

**2. Get site names:**
```python
# Export sites
sites = await generate_site_config()
site_names = [s["site"]["area"]["parent_name_hierarchy"] + "/" + s["site"]["area"]["name"]
              for s in sites["config"]]
```

**3. Verify device is discovered:**
```python
# Check if device exists in inventory
device_exists = any(d["management_ip_address"] == "10.10.20.1" for d in devices)
```

#### Example Workflow

```python
# Step 1: Discover devices (if not already done)
await discover_devices(...)

# Step 2: Get device IP from discovery
inventory = await generate_inventory_config()
device_ip = inventory["config"][0]["management_ip_address"]

# Step 3: Assign device to site
await manage_inventory(
    device_ip=device_ip,
    site_name="Global/USA/Branch-1"
)
```

---

## Compliance

### `compliance_workflow_manager`

**Purpose:** Run compliance checks on devices

#### Mandatory Requirements

| Field | Required | Type | Notes |
|-------|----------|------|-------|
| `device_ip` OR `site_id` | ✅ Yes | string | Must specify one |
| `run_compliance` | ✅ Yes | boolean | Set to true to trigger check |
| `compliance_type` | ❌ No | string | Default: "RUNNING_CONFIG" |

#### How to Get Required Information

**1. Get device IPs:**
```python
# Export inventory
inventory = await generate_inventory_config()

# Filter by site or device type
branch_devices = [
    d["management_ip_address"] 
    for d in inventory["config"]
    if "Branch" in d.get("site_name", "")
]
```

**2. Get site IDs:**
```python
# Export sites
sites = await generate_site_config()

# Get site ID by name
site_id = next(
    s["site"]["area"]["id"]
    for s in sites["config"]
    if s["site"]["area"]["name"] == "Branch-1"
)
```

**3. Verify device is reachable:**
```python
# Check device status in inventory
device = next(d for d in inventory["config"] if d["management_ip_address"] == "10.10.20.1")
is_reachable = device.get("reachability_status") == "Reachable"
```

#### Example Workflow

```python
# Option 1: Run compliance by device IP
await run_compliance_workflow_manager(
    config_json=json.dumps([{
        "device_ip": "10.10.20.1",
        "run_compliance": True
    }])
)

# Option 2: Run compliance for all devices in a site
sites = await generate_site_config()
site_id = sites["config"][0]["site"]["area"]["id"]

await run_compliance_workflow_manager(
    config_json=json.dumps([{
        "site_id": site_id,
        "run_compliance": True
    }])
)
```

---

## SD-Access Fabric

### `sda_fabric_sites_workflow_manager`

**Purpose:** Create fabric sites

#### Mandatory Requirements

| Field | Required | Type | Notes |
|-------|----------|------|-------|
| `site_name_hierarchy` | ✅ Yes | string | Must be existing site |
| `fabric_type` | ✅ Yes | enum | "FABRIC_SITE", "FABRIC_ZONE" |
| `authentication_profile` | ⚠️ Conditional | string | Required for FABRIC_SITE |

#### How to Get Required Information

**1. Get site hierarchy:**
```python
sites = await generate_site_config()
site_paths = [s["site"]["area"]["parent_name_hierarchy"] + "/" + s["site"]["area"]["name"]
              for s in sites["config"]]
```

**2. Get authentication profiles:**
```python
# List available auth profiles from Catalyst Center
# (This requires direct API call or UI lookup)
# Common values: "No Authentication", "Closed Authentication"
```

### `sda_fabric_devices_workflow_manager`

**Purpose:** Onboard devices to fabric

#### Mandatory Requirements

| Field | Required | Type | Notes |
|-------|----------|------|-------|
| `fabric_name` | ✅ Yes | string | Must be existing fabric site |
| `device_ip` | ✅ Yes | string | Must be provisioned device |
| `device_roles` | ✅ Yes | list[enum] | "CONTROL_PLANE", "EDGE_NODE", "BORDER_NODE" |

#### How to Get Required Information

**1. Get fabric sites:**
```python
fabrics = await generate_sda_fabric_sites_config()
fabric_names = [f["site_name_hierarchy"] for f in fabrics["config"]]
```

**2. Get provisioned devices:**
```python
inventory = await generate_inventory_config()
provisioned = [
    d["management_ip_address"]
    for d in inventory["config"]
    if d.get("provisioning_state") == "Provisioned"
]
```

**3. Determine device roles:**
- **CONTROL_PLANE** - Fabric control plane node (typically core switches)
- **EDGE_NODE** - Access layer switches
- **BORDER_NODE** - Connects fabric to external networks

#### Example Workflow

```python
# Step 1: Create site
await provision_site(site_type="building", name="Fabric-Site-1", parent_path="Global")

# Step 2: Configure network settings
await configure_network_settings(site_name="Global/Fabric-Site-1", ...)

# Step 3: Discover and provision devices
await discover_devices(...)
await manage_inventory(device_ip="10.10.30.1", site_name="Global/Fabric-Site-1")

# Step 4: Create fabric site
await run_sda_fabric_sites_workflow_manager(
    config_json=json.dumps([{
        "site_name_hierarchy": "Global/Fabric-Site-1",
        "fabric_type": "FABRIC_SITE",
        "authentication_profile": "No Authentication"
    }])
)

# Step 5: Onboard fabric devices
await onboard_fabric_devices(
    fabric_name="Global/Fabric-Site-1",
    device_ip="10.10.30.1",
    device_roles=["CONTROL_PLANE", "BORDER_NODE"]
)
```

---

## Templates

### `template_workflow_manager`

**Purpose:** Deploy CLI templates to devices

#### Mandatory Requirements

| Field | Required | Type | Notes |
|-------|----------|------|-------|
| `project_name` | ✅ Yes | string | Must exist in Catalyst Center |
| `template_name` | ✅ Yes | string | Must exist in project |
| `target_id` | ✅ Yes | string | Device UUID or hostname |
| `target_type` | ✅ Yes | enum | "MANAGED_DEVICE_UUID", "MANAGED_DEVICE_HOSTNAME" |
| `template_params` | ⚠️ Conditional | dict | Required if template has variables |

#### How to Get Required Information

**1. Get projects and templates:**
```python
# Export template configuration
templates = await generate_template_config()

# List projects
projects = list(set(t["project_name"] for t in templates["config"]))

# List templates in project
project_templates = [
    t["template_name"]
    for t in templates["config"]
    if t["project_name"] == "Onboarding Configuration"
]
```

**2. Get device UUID:**
```python
inventory = await generate_inventory_config()
device = next(d for d in inventory["config"] if d["management_ip_address"] == "10.10.20.1")
device_uuid = device["id"]
```

**3. Get template parameters:**
```python
# Check template definition for required variables
template = next(
    t for t in templates["config"]
    if t["template_name"] == "Interface-Config"
)
# Variables might be: interface_name, vlan_id, ip_address, etc.
```

#### Example Workflow

```python
# Step 1: Get device UUID
inventory = await generate_inventory_config()
device_uuid = inventory["config"][0]["id"]

# Step 2: Deploy template
await deploy_template(
    project_name="Onboarding Configuration",
    template_name="Interface-Config",
    target_id=device_uuid,
    target_type="MANAGED_DEVICE_UUID",
    template_params={
        "interface_name": "GigabitEthernet1/0/1",
        "vlan_id": "100",
        "ip_address": "192.168.100.1"
    },
    failure_policy="ABORT_ON_ERROR"
)
```

---

## User & Role Management

### `user_role_workflow_manager`

**Purpose:** Create/update/delete users, roles, and access groups

#### Mandatory Requirements

**For Users:**
| Field | Required | Type | Notes |
|-------|----------|------|-------|
| `username` | ✅ Yes | string | Unique username |
| `email` | ✅ Yes | string | Valid email address |
| `first_name` | ✅ Yes | string | User's first name |
| `last_name` | ✅ Yes | string | User's last name |
| `role_list` | ✅ Yes | list[string] | Must be existing role names |

**For Roles:**
| Field | Required | Type | Notes |
|-------|----------|------|-------|
| `role_name` | ✅ Yes | string | Unique role name |
| `description` | ❌ No | string | Role description |
| `assurance` | ❌ No | list[dict] | Assurance permissions |
| `network_provision` | ❌ No | list[dict] | Network provision permissions |

**For Access Groups:**
| Field | Required | Type | Notes |
|-------|----------|------|-------|
| `name` | ✅ Yes | string | Unique access group name |
| `site_hierarchy` | ✅ Yes | string | Must be existing site |
| `role_name` | ✅ Yes | string | Must be existing role |

#### How to Get Required Information

**1. Get existing roles:**
```python
# Export current roles
user_roles = await generate_user_role_config()
role_names = [r["role_name"] for r in user_roles["config"].get("role_details", [])]
# Example: ["NETWORK-ADMIN-ROLE", "OBSERVER-ROLE"]
```

**2. Get site hierarchy for access groups:**
```python
sites = await generate_site_config()
site_paths = [s["site"]["area"]["parent_name_hierarchy"] + "/" + s["site"]["area"]["name"]
              for s in sites["config"]]
```

#### Example Workflow

```python
# Step 1: Create custom role
await run_user_role_workflow_manager(
    config_json=json.dumps({
        "role_details": [{
            "role_name": "Branch-Admin",
            "description": "Admin for branch sites",
            "assurance": [{"overall": "write"}],
            "network_provision": [{"overall": "write"}]
        }]
    })
)

# Step 2: Create user with role
await run_user_role_workflow_manager(
    config_json=json.dumps({
        "user_details": [{
            "username": "john.doe",
            "email": "john.doe@example.com",
            "first_name": "John",
            "last_name": "Doe",
            "role_list": ["Branch-Admin"]
        }]
    })
)

# Step 3: Create access group
await run_user_role_workflow_manager(
    config_json=json.dumps({
        "access_group_details": [{
            "name": "Branch-Access",
            "description": "Access to branch sites",
            "site_hierarchy": "Global/USA/Branch-1",
            "role_name": "Branch-Admin"
        }]
    })
)
```

---

## Common Data Gathering Tools

### Use Config Generators to Export Current State

All `*_playbook_config_generator` modules can export current configuration:

```python
# Export sites
sites = await generate_site_config()

# Export network settings
network = await generate_network_settings_config()

# Export inventory
inventory = await generate_inventory_config()

# Export templates
templates = await generate_template_config()

# Export fabric sites
fabrics = await generate_sda_fabric_sites_config()

# Export users and roles
users = await generate_user_role_config()
```

### Common Patterns

**Pattern 1: Check if object exists before creating**
```python
# Get current state
current = await generate_site_config()

# Check existence
exists = any(s["site"]["area"]["name"] == "New-Site" for s in current["config"])

if not exists:
    await provision_site(...)
```

**Pattern 2: Get ID from name**
```python
# Get all sites
sites = await generate_site_config()

# Find site by name and get ID
site = next(s for s in sites["config"] if s["site"]["area"]["name"] == "HQ")
site_id = site["site"]["area"]["id"]
```

**Pattern 3: Validate prerequisites**
```python
# Before creating floor, verify building exists
sites = await generate_site_config()
building_exists = any(
    s["site"]["building"]["name"] == "HQ" and 
    s["site"]["building"]["parent_name_hierarchy"] == "Global/USA"
    for s in sites["config"]
)

if not building_exists:
    raise ValueError("Building must exist before creating floor")
```

---

## Dependency Graph Examples

### Complete Site Provisioning Flow

```
1. Create Area (Global/USA)
   ↓
2. Create Building (Global/USA/HQ)
   ├─ Requires: latitude, longitude
   ↓
3. Configure Network Settings (Global/USA/HQ)
   ├─ Requires: DHCP, DNS, NTP server IPs
   ↓
4. Discover Devices
   ├─ Requires: IP ranges, credentials
   ↓
5. Assign Devices to Site (Global/USA/HQ)
   ├─ Requires: device IPs from step 4
   ↓
6. Run Compliance
   ├─ Requires: device IPs OR site ID
```

### Fabric Deployment Flow

```
1. Create Site Hierarchy
   ↓
2. Configure Network Settings
   ↓
3. Discover Devices
   ↓
4. Provision Devices
   ↓
5. Create Fabric Site
   ├─ Requires: site hierarchy, auth profile
   ↓
6. Onboard Fabric Devices
   ├─ Requires: fabric name, device IPs, roles
```

### Template Deployment Flow

```
1. Create/Import Template (via UI or API)
   ↓
2. Discover Devices
   ↓
3. Get Device UUID
   ├─ Use: generate_inventory_config()
   ↓
4. Deploy Template
   ├─ Requires: project name, template name, device UUID, parameters
```

---

## Quick Reference: Required Fields by Module

| Module | Always Required | Conditionally Required | How to Get |
|--------|----------------|----------------------|------------|
| `site_workflow_manager` | `name`, `parent_path` | `latitude`, `longitude` (buildings) | `generate_site_config()` |
| `network_settings_workflow_manager` | `site_name` | At least one setting (DHCP/DNS/NTP) | `generate_site_config()` |
| `discovery_workflow_manager` | `discovery_name`, `ip_address_list` | `global_credential_id_list` | `generate_device_credential_config()` |
| `inventory_workflow_manager` | `device_ip` OR `site_name` | - | `generate_inventory_config()` |
| `compliance_workflow_manager` | `device_ip` OR `site_id` | - | `generate_inventory_config()`, `generate_site_config()` |
| `sda_fabric_sites_workflow_manager` | `site_name_hierarchy`, `fabric_type` | `authentication_profile` | `generate_site_config()` |
| `sda_fabric_devices_workflow_manager` | `fabric_name`, `device_ip`, `device_roles` | - | `generate_sda_fabric_sites_config()`, `generate_inventory_config()` |
| `template_workflow_manager` | `project_name`, `template_name`, `target_id` | `template_params` | `generate_template_config()`, `generate_inventory_config()` |
| `user_role_workflow_manager` | Varies by operation | `role_list` (users), `site_hierarchy` (access groups) | `generate_user_role_config()`, `generate_site_config()` |

---

## Best Practices

### 1. Always Export Before Modify
```python
# Get current state first
current = await generate_site_config()

# Then make changes
await provision_site(...)
```

### 2. Validate Prerequisites
```python
# Check parent exists
sites = await generate_site_config()
parent_exists = any(s["site"]["area"]["name"] == "USA" for s in sites["config"])

if not parent_exists:
    raise ValueError("Parent site 'USA' must exist")
```

### 3. Use wait_iac_task for Verification
```python
# Submit task
result = await provision_site(...)

# Wait and verify
final = await wait_iac_task(iac_task_id=result["iacTaskId"])

if final["iacStatus"] == "completed":
    print(f"✅ Success: {final['ansibleRecap']}")
else:
    print(f"❌ Failed: {final['iacStatusMessage']}")
```

### 4. Handle Dependencies in Order
```python
# Wrong: Create floor before building
await provision_site(site_type="floor", ...)  # ❌ Will fail

# Right: Create in hierarchy order
await provision_site(site_type="area", name="USA", parent_path="Global")
await provision_site(site_type="building", name="HQ", parent_path="Global/USA")
await provision_site(site_type="floor", name="Floor-1", parent_path="Global/USA/HQ")
```

---

## Troubleshooting

### "Parent site not found"
**Solution:** Create parent sites first in hierarchy order (area → building → floor)

### "Device not found"
**Solution:** Run discovery first, verify device is in inventory using `generate_inventory_config()`

### "Site not found"
**Solution:** Verify site exists using `generate_site_config()`, check exact hierarchy path

### "Credential not found"
**Solution:** Get credential IDs using `generate_device_credential_config()`

### "Template not found"
**Solution:** Verify project and template exist using `generate_template_config()`

### "Role not found"
**Solution:** Get existing roles using `generate_user_role_config()`

---

## Additional Resources

- [README.md](README.md) - Installation and configuration
- [Examples](examples/) - Working code examples
- [Tool Catalog](tool_catalog.yaml) - All available modules
- [Ansible Collection Docs](https://galaxy.ansible.com/ui/repo/published/cisco/catalystcenter/) - Module specifications

---

**Last Updated:** 2026-05-28  
**Version:** 1.0.0

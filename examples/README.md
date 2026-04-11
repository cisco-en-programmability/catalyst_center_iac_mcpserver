# Catalyst Center IAC MCP Examples

This directory contains practical examples demonstrating how to use the Catalyst Center IAC MCP server for various network automation workflows.

## Prerequisites

1. MCP server running on `http://localhost:8000`
2. Catalyst Center instance configured with credentials
3. Python 3.11+ with `httpx` installed:
   ```bash
   pip install httpx
   ```

## Examples

### 1. Site Provisioning (`provision_site_example.py`)

Demonstrates creating a hierarchical site structure:
- Area (USA)
- Building (San Jose HQ) with GPS coordinates
- Floor (Floor 1) with RF model

**Run:**
```bash
python examples/provision_site_example.py
```

### 2. Device Discovery (`discovery_example.py`)

Shows how to discover network devices using:
- CIDR notation (10.10.10.0/24)
- IP ranges
- CDP/LLDP protocols

**Run:**
```bash
python examples/discovery_example.py
```

### 3. Network Settings (`network_settings_example.py`)

Configures comprehensive network settings for a site:
- DHCP servers
- DNS servers
- NTP servers
- Timezone
- SNMP/Syslog servers
- Message of the day

**Run:**
```bash
python examples/network_settings_example.py
```

### 4. SD-Access Fabric Workflow (`fabric_workflow_example.py`)

Complete SD-Access fabric setup:
1. Create fabric site
2. Onboard border and control plane nodes
3. Configure virtual networks with VLANs

**Run:**
```bash
python examples/fabric_workflow_example.py
```

## MCP Protocol Usage

All examples use the MCP JSON-RPC 2.0 protocol:

```python
{
    "jsonrpc": "2.0",
    "id": 1,
    "method": "tools/call",
    "params": {
        "name": "tool_name",
        "arguments": {
            # Tool-specific arguments
        }
    }
}
```

## Task Polling

Long-running operations return a task ID. Poll for status:

```bash
curl http://localhost:8000/tasks/get/{task_id}
```

Response includes:
- `status`: submitted, running, completed, failed
- `progress`: Current progress value
- `total`: Total progress value (usually 100)
- `statusMessage`: Human-readable status
- `result`: Final result when completed

### 5. Version Fallback (`version_fallback_example.py`)

**NEW**: Demonstrates automatic version normalization for Catalyst Center compatibility:

The MCP server automatically normalizes Catalyst Center versions to ensure compatibility:

- **2.3.7.10** or **2.3.7** automatically falls back to **2.3.7.9**
- **3.1.3.1** or **3.1.3.7** automatically falls back to **3.1.3.6**
- Unsupported versions remain unchanged

This ensures that any version within the same major.minor.patch family works with the nearest supported version.

**Configuration Example:**
```bash
# These will all be normalized to 2.3.7.9
CATALYSTCENTER_VERSION=2.3.7.10
CATALYSTCENTER_VERSION=2.3.7

# These will all be normalized to 3.1.3.6
CATALYSTCENTER_VERSION=3.1.3.1
CATALYSTCENTER_VERSION=3.1.3.7
CATALYSTCENTER_VERSION=3.1.3
```

**Run:**
```bash
python examples/version_fallback_example.py
```

## Multi-Tenant Usage

To target a specific Catalyst Center instance:

```python
"arguments": {
    # ... other arguments
    "tenant_id": "acme"  # Uses CATALYSTCENTER_ACME_* env vars
}
```

## Generic Workflow Tools

For advanced use cases, use generic workflow managers directly:

```python
import json

config = [
    {
        "run_compliance": True,
        "device_uuids": ["device-1", "device-2"]
    }
]

response = await client.post(
    f"{base_url}/mcp",
    json={
        "jsonrpc": "2.0",
        "id": 1,
        "method": "tools/call",
        "params": {
            "name": "run_network_compliance_workflow_manager",
            "arguments": {
                "config_json": json.dumps(config),
                "state": "merged"
            }
        }
    }
)
```

## Error Handling

Always check the response structure:

```python
result = response.json()

if "error" in result:
    print(f"Error: {result['error']['message']}")
elif "result" in result:
    # Success - extract task ID or result
    pass
```

## Additional Resources

- [MCP Protocol Specification](https://modelcontextprotocol.io/)
- [Cisco Catalyst Center Ansible Collection](https://github.com/cisco-en-programmability/catalystcenter-ansible)
- [Main README](../README.md)

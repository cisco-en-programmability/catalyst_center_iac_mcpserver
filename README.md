# Catalyst Center IAC MCP Server

A FastMCP server that exposes Cisco Catalyst Center automation as MCP tools for AI agents.

## What It Does

- **78+ MCP tools** for Catalyst Center workflows
- **Specialized tools**: `provision_site`, `deploy_template`, `discover_devices`
- **Generic workflow tools**: All `*_workflow_manager` modules
- **Read-only config tools**: All `*_playbook_config_generator` modules
- **Async task execution** with Redis persistence
- **Multi-tenant support** for multiple Catalyst Center instances

## Quick Start

### 1. Prerequisites

```bash
# Python 3.11+
python --version

# Redis 6.0+
redis-cli ping  # Should return "PONG"

# Ansible Collection
ansible-galaxy collection install cisco.catalystcenter:==2.6.0
```

### 2. Install

```bash
# Clone and install
git clone https://github.com/cisco-en-programmability/catalyst_center_iac_mcpserver.git
cd catalyst_center_iac_mcpserver
python3.11 -m venv .venv
source .venv/bin/activate
pip install .
```

### 3. Configure

Create environment file:
```bash
mkdir -p ~/.config/catalyst-center-iac-mcp
cat > ~/.config/catalyst-center-iac-mcp/env << 'EOF'
REDIS_URL=redis://127.0.0.1:6379/0
RUNNER_ARTIFACT_ROOT=$HOME/.local/share/catalyst-center-iac-mcp/artifacts

CATALYSTCENTER_HOST=your-catalyst-center.example.com
CATALYSTCENTER_USERNAME=admin
CATALYSTCENTER_PASSWORD=your-password
CATALYSTCENTER_VERIFY_SSL=false
CATALYSTCENTER_PORT=443
CATALYSTCENTER_VERSION=2.6.0

SERVER_HOST=127.0.0.1
SERVER_PORT=8000
EOF
```

### 4. Run

```bash
# Load environment and start
export $(grep -v '^#' ~/.config/catalyst-center-iac-mcp/env | xargs)
catalyst-center-iac-mcp
```

Server runs at: `http://127.0.0.1:8000`

## Usage

### With Claude Desktop

Add to `claude_desktop_config.json`:
```json
{
  "mcpServers": {
    "catalyst-center": {
      "url": "http://127.0.0.1:8000/mcp",
      "transport": "http"
    }
  }
}
```

### Key Tools

**Site Management:**
```python
# Create site hierarchy
provision_site(site_type="building", name="HQ", parent_path="Global/USA")
```

**Device Discovery:**
```python
# Discover devices
discover_devices(discovery_type="CIDR", ip_address_list=["10.10.10.0/24"])
```

**Template Deployment:**
```python
# Deploy configuration template
deploy_template(template_name="Switch-Config", devices=["switch1", "switch2"])
```

### Task Polling

Long operations return task IDs:
```bash
# Check task status
curl http://127.0.0.1:8000/tasks/get/{task_id}
```

## Multi-Tenant Support

Add tenant-specific credentials:
```bash
CATALYSTCENTER_ACME_HOST=acme-catalyst.example.com
CATALYSTCENTER_ACME_USERNAME=acme-admin
CATALYSTCENTER_ACME_PASSWORD=acme-secret
```

Use with `tenant_id="acme"` in tool calls.

## Version Fallback

The MCP server automatically normalizes Catalyst Center versions for compatibility:

- **2.3.7.10** or **2.3.7** automatically falls back to **2.3.7.9**
- **3.1.3.1** or **3.1.3.7** automatically falls back to **3.1.3.6**
- Unsupported versions remain unchanged

This ensures any version within the same major.minor.patch family works with the nearest supported version.

```bash
# These all normalize to 2.3.7.9
CATALYSTCENTER_VERSION=2.3.7.10
CATALYSTCENTER_VERSION=2.3.7

# These all normalize to 3.1.3.6  
CATALYSTCENTER_VERSION=3.1.3.1
CATALYSTCENTER_VERSION=3.1.3.7
CATALYSTCENTER_VERSION=3.1.3
```

## Examples

See `examples/` directory for complete workflows:
- Site provisioning
- Device discovery  
- Network settings
- SD-Access fabric
- **Multi-tenant operations** (2 Catalyst Center instances)
- **Version fallback** (automatic version normalization)

## Production Deployment

For production, use:
- Docker Compose stack (included)
- Systemd service with NGINX reverse proxy
- HTTPS with OAuth authentication

See `deploy/` directory for production configurations.

## Endpoints

- `GET /healthz` - Health check
- `POST /mcp` - MCP protocol endpoint  
- `GET /tasks/get/{task_id}` - Task status

## Troubleshooting

**Missing tools:** Reinstall Ansible collection
```bash
ansible-galaxy collection install cisco.catalystcenter:==2.6.0 --force
```

**Connection issues:** Verify Catalyst Center reachability and credentials

**Redis errors:** Ensure Redis is running and accessible

## License

Cisco Sample Code License


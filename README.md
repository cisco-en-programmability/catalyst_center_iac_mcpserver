# Catalyst Center IAC MCP Server

A FastMCP server that exposes Cisco Catalyst Center automation as MCP tools for AI agents.

## What It Does

- **78+ MCP tools** for Catalyst Center workflows
- **Specialized tools**: `provision_site`, `deploy_template`, `discover_devices`
- **Generic workflow tools**: All `*_workflow_manager` modules
- **Read-only config tools**: All `*_playbook_config_generator` modules
- **Async task execution** with Redis persistence
- **Multi-tenant support** for multiple Catalyst Center instances
- **Cluster support** through YAML catalog configuration
- **Version fallback** for automatic Catalyst Center compatibility

## Quick Start

### 1. Prerequisites

### Specialized Tools

- `provision_site`
- `delete_site`
- `deploy_template`
- `onboard_fabric_devices`
- `reprovision_fabric_device`
- `manage_assurance_issues`
- `discover_devices`
- `manage_inventory`
- `configure_network_settings`

These are the preferred tools for common workflows because they keep the LLM-facing interface flat and typed.

### Generic Workflow Tools

Generic workflow tools are registered as:

- `run_<module_name>`

Example:

- `run_site_workflow_manager`
- `run_inventory_workflow_manager`
- `run_sda_fabric_devices_workflow_manager`

These tools accept `config_json` as a JSON string representing the module `config` payload.

### Generic Config Generator Tools

Read-only config generator tools are registered as:

- `generate_<domain>_config`

Example:

- `generate_site_config`
- `generate_inventory_config`
- `generate_template_config`
- `generate_network_settings_config`

These tools accept `module_args_json` as a JSON object string. If `state` is omitted, the server sets it to `gathered`.

### Cluster Selection

Most tools also accept:

- `tenant_id`: routes through the existing tenant-scoped environment variables
- `catalyst_center`: selects an enabled cluster from [`catalyst_center_clusters.yaml`](/Users/pawansi/.codex/worktrees/c252/catalyst_center_iac_mcp/catalyst_center_clusters.yaml) by `name`, `label`, `location`, or `host`

If `catalyst_center` is provided, cluster selection takes precedence over `tenant_id`.

## Architecture

- `FastMCP`: MCP tool registration and request handling
- `FastAPI`: HTTP app for `/mcp`, `/healthz`, and `/tasks/get/{task_id}`
- `ansible-runner`: the only execution path for Catalyst Center operations
- `Redis`: task state, progress, results, and artifact indexing
- `transformers.py`: flat tool input to nested workflow payload translation
- `runner_engine.py`: module submission, ansible-runner lifecycle, artifact persistence

The server is stateless by design. Redis and runner artifacts hold the operational state, which makes multi-instance deployment practical.

## Multiple Catalyst Centers

Use [`catalyst_center_clusters.yaml`](/Users/pawansi/.codex/worktrees/c252/catalyst_center_iac_mcp/catalyst_center_clusters.yaml) to define multiple Catalyst Center clusters that the MCP server can target by `name`, `label`, `location`, or `host`.

Example:

```yaml
catalyst_centers:
  - name: "Portland"
    label: "dev"
    host: "Portland-center.domain.com"
    version: "3.1.3.0"
    location: "Portland"
    enabled: true
  - name: "San Jose"
    label: "produsion"
    host: "SanJose-catalyst.domain.com"
    version: "2.3.7.9"
    location: "San Jose"
    enabled: false
```

Cluster credentials stay in environment variables, not in YAML. For a cluster with label `dev`, set:

```bash
CC_DEV_USERNAME=automation
CC_DEV_PASSWORD=change-me
CC_DEV_VERIFY_SSL=false
CC_DEV_PORT=443
CC_DEV_VERSION=3.1.3.0
```

Then pass `catalyst_center="Portland"` or `catalyst_center="dev"` in any tool call. If `catalyst_center` is omitted, the server falls back to the existing `tenant_id` and default `CATALYSTCENTER_*` environment variables. The older `CATALYSTCENTER_CLUSTER_*` names are still accepted for backward compatibility.

## Requirements

- **Operating System**: macOS, Linux (Ubuntu/Debian/RHEL/CentOS), or Windows WSL2
- **Python**: 3.11 or higher
- **Redis**: 6.0 or higher
- **Ansible Collection**: `cisco.catalystcenter` 2.6.0+
- **Network**: Reachability to Cisco Catalyst Center instance

## Installation

Choose your platform and deployment mode:

### macOS Installation

#### Prerequisites
>>>>>>> c215d6036b2dcf7d1cd4558c49a01e1b7391fe86

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

Server will be available at: `http://127.0.0.1:8000`

---

### Ubuntu/Debian Installation

#### Prerequisites

```bash
# Update package list
sudo apt-get update

# Install dependencies
sudo apt-get install -y \
    python3.11 \
    python3.11-venv \
    python3-pip \
    build-essential \
    ca-certificates \
    redis-server \
    git

# Start Redis
sudo systemctl enable redis-server
sudo systemctl start redis-server
```

#### Install MCP Server (Production)

```bash
# Create system user
sudo useradd --system --create-home \
    --home-dir /opt/catalyst-center-iac-mcp \
    --shell /usr/sbin/nologin \
    catalystmcp

# Create directories
sudo mkdir -p /opt/catalyst-center-iac-mcp \
    /var/lib/catalyst-center-iac-mcp/artifacts \
    /etc/catalyst-center-iac-mcp

sudo chown -R catalystmcp:catalystmcp \
    /opt/catalyst-center-iac-mcp \
    /var/lib/catalyst-center-iac-mcp \
    /etc/catalyst-center-iac-mcp

# Clone repository
cd /tmp
git clone https://github.com/cisco-en-programmability/catalyst_center_iac_mcpserver.git
sudo cp -r catalyst_center_iac_mcpserver/* /opt/catalyst-center-iac-mcp/
sudo chown -R catalystmcp:catalystmcp /opt/catalyst-center-iac-mcp

# Install as catalystmcp user
sudo -u catalystmcp bash << 'EOSU'
cd /opt/catalyst-center-iac-mcp
python3.11 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip setuptools wheel
pip install .
ansible-galaxy collection install cisco.catalystcenter:==2.6.0
EOSU
```

#### Configure Environment (Ubuntu/Debian)

```bash
# Create environment file
sudo tee /etc/catalyst-center-iac-mcp/catalyst-center-iac-mcp.env > /dev/null << 'EOF'
# Redis Configuration
REDIS_URL=redis://127.0.0.1:6379/0

# Artifact Storage
RUNNER_ARTIFACT_ROOT=/var/lib/catalyst-center-iac-mcp/artifacts

# Catalyst Center Credentials
CATALYSTCENTER_HOST=your-catalyst-center.example.com
CATALYSTCENTER_USERNAME=admin
CATALYSTCENTER_PASSWORD=your-password
CATALYSTCENTER_VERIFY_SSL=false
CATALYSTCENTER_PORT=443
CATALYSTCENTER_VERSION=2.6.0

# Server Configuration
SERVER_HOST=127.0.0.1
SERVER_PORT=8000
SERVER_WORKERS=4
EOF

# Edit with your credentials
sudo nano /etc/catalyst-center-iac-mcp/catalyst-center-iac-mcp.env

# Secure the file
sudo chmod 600 /etc/catalyst-center-iac-mcp/catalyst-center-iac-mcp.env
sudo chown catalystmcp:catalystmcp /etc/catalyst-center-iac-mcp/catalyst-center-iac-mcp.env
```

#### Run Server (Ubuntu/Debian - Local HTTP Mode)

```bash
# Manual start
sudo -u catalystmcp bash << 'EOSU'
cd /opt/catalyst-center-iac-mcp
source .venv/bin/activate
export $(grep -v '^#' /etc/catalyst-center-iac-mcp/catalyst-center-iac-mcp.env | xargs)
catalyst-center-iac-mcp
EOSU
```

---

### RHEL/CentOS/Rocky Linux Installation

#### Prerequisites

```bash
# Install EPEL repository
sudo dnf install -y epel-release

# Install dependencies
sudo dnf install -y \
    python3.11 \
    python3.11-devel \
    python3-pip \
    gcc \
    git \
    redis

# Start Redis
sudo systemctl enable redis
sudo systemctl start redis
```

Follow the same installation steps as Ubuntu/Debian above, adjusting paths as needed.

---

### Windows WSL2 Installation

#### Prerequisites

1. Install WSL2 with Ubuntu 22.04:
```powershell
wsl --install -d Ubuntu-22.04
```

2. Open Ubuntu terminal and follow the Ubuntu installation instructions above.

---

### Development Installation (All Platforms)

For development on any platform:

```bash
# Clone repository
git clone https://github.com/cisco-en-programmability/catalyst_center_iac_mcpserver.git
cd catalyst_center_iac_mcpserver

# Create virtual environment
python3.11 -m venv .venv
source .venv/bin/activate  # On Windows WSL2: source .venv/bin/activate

# Install in development mode
pip install --upgrade pip setuptools wheel
pip install -e ".[dev]"

# Install Ansible collection
ansible-galaxy collection install cisco.catalystcenter:==2.6.0

# Run tests
python -m pytest -q

# Create local config
mkdir -p ~/.config/catalyst-center-iac-mcp
cp deploy/env/catalyst-center-iac-mcp.env.example ~/.config/catalyst-center-iac-mcp/env
nano ~/.config/catalyst-center-iac-mcp/env  # Edit with your settings
```

## Configuration

### Required Environment Variables

```bash
REDIS_URL=redis://127.0.0.1:6379/0
RUNNER_ARTIFACT_ROOT=/var/lib/catalyst-center-iac-mcp/artifacts

CATALYSTCENTER_HOST=catalyst-center.example.com
CATALYSTCENTER_USERNAME=automation
CATALYSTCENTER_PASSWORD=change-me
CATALYSTCENTER_VERIFY_SSL=false
CATALYSTCENTER_PORT=443
CATALYSTCENTER_VERSION=2.6.0
```

### Server Environment Variables

```bash
APP_NAME=catalyst_center_iac_mcp
APP_VERSION=0.1.0
SERVER_HOST=127.0.0.1
SERVER_PORT=8000
SERVER_WORKERS=2
PROXY_HEADERS=true
FORWARDED_ALLOW_IPS=127.0.0.1

MCP_PATH=/mcp
MCP_TRANSPORT=http
RUNNER_TIMEOUT_SECONDS=3600
TASK_TTL_SECONDS=86400
TASK_POLL_INTERVAL_MS=2000
CATALYST_CENTER_CLUSTERS_FILE=./catalyst_center_clusters.yaml
```

### Direct TLS Environment Variables

If you want the app itself to terminate HTTPS:

```bash
TLS_CERTFILE=/etc/ssl/certs/catalyst-center-iac-mcp/fullchain.pem
TLS_KEYFILE=/etc/ssl/private/catalyst-center-iac-mcp/privkey.pem
TLS_CA_CERTS=/etc/ssl/certs/ca-certificates.crt
SERVER_PORT=8443
```

### OAuth Environment Variables

```bash
OAUTH_ENABLED=true
OAUTH_ISSUER=https://auth.example.com
OAUTH_AUDIENCE=catalyst-center-mcp
OAUTH_JWKS_URL=https://auth.example.com/.well-known/jwks.json
ALLOW_ANONYMOUS_HEALTHCHECK=true
```

### Multi-Tenant Credentials

```bash
CATALYSTCENTER_ACME_HOST=acme-catc.example.com
CATALYSTCENTER_ACME_USERNAME=svc-acme
CATALYSTCENTER_ACME_PASSWORD=acme-secret
CATALYSTCENTER_ACME_VERIFY_SSL=true
CATALYSTCENTER_ACME_VERSION=2.6.0
```

When invoking a tool, pass `tenant_id="acme"` to target that Catalyst Center instance.

### Multi-Cluster Credentials

Define the cluster inventory in [`catalyst_center_clusters.yaml`](/Users/pawansi/.codex/worktrees/c252/catalyst_center_iac_mcp/catalyst_center_clusters.yaml), then provide credentials by cluster label or slug:

```bash
CC_DEV_USERNAME=svc-dev
CC_DEV_PASSWORD=dev-secret
CC_DEV_VERIFY_SSL=false
CC_DEV_PORT=443
CC_DEV_VERSION=3.1.3.0
```

The older `CATALYSTCENTER_CLUSTER_*` variable names are still accepted for backward compatibility.

### Routing Rules

- Use `catalyst_center` when you want the model or caller to pick from a named Catalyst Center cluster inventory.
- Use `tenant_id` when you want the legacy tenant-scoped environment variable routing.
- If both are provided, `catalyst_center` takes precedence.
- Use `list_catalyst_centers` to inspect enabled cluster names, labels, locations, and hosts before selecting one.

An example environment file is included at [catalyst-center-iac-mcp.env.example](/Users/pawansi/workspace/catalyst_center_iac_mcp/deploy/env/catalyst-center-iac-mcp.env.example).

## Running the Server

### Linux CLI

```bash
. /opt/catalyst-center-iac-mcp/.venv/bin/activate
export $(grep -v '^#' /etc/catalyst-center-iac-mcp/catalyst-center-iac-mcp.env | xargs)
catalyst-center-iac-mcp
```

### Direct HTTPS

This is acceptable for labs or small deployments:

```bash
export SERVER_HOST=0.0.0.0
export SERVER_PORT=8443
export TLS_CERTFILE=/etc/letsencrypt/live/mcp.example.com/fullchain.pem
export TLS_KEYFILE=/etc/letsencrypt/live/mcp.example.com/privkey.pem

catalyst-center-iac-mcp
```

Then access:

- `https://mcp.example.com:8443/healthz`
- `https://mcp.example.com:8443/mcp`

### Recommended HTTPS Deployment

For production Linux deployments, use:

- the app on `127.0.0.1:8000`
- NGINX or another reverse proxy for HTTPS
- systemd for process supervision

This is the better pattern because it gives you:

- TLS termination and certificate rotation
- reverse-proxy buffering control for MCP and SSE
- cleaner operational boundaries
- easier log and service management

Provided deployment examples:

- systemd unit: [catalyst-center-iac-mcp.service](/Users/pawansi/workspace/catalyst_center_iac_mcp/deploy/systemd/catalyst-center-iac-mcp.service)
- NGINX config: [catalyst-center-iac-mcp.conf](/Users/pawansi/workspace/catalyst_center_iac_mcp/deploy/nginx/catalyst-center-iac-mcp.conf)

### systemd Deployment

1. Copy the example environment file:

```bash
sudo cp /opt/catalyst-center-iac-mcp/deploy/env/catalyst-center-iac-mcp.env.example /etc/catalyst-center-iac-mcp/catalyst-center-iac-mcp.env
sudo vi /etc/catalyst-center-iac-mcp/catalyst-center-iac-mcp.env
```

2. Copy the service file:

```bash
sudo cp /opt/catalyst-center-iac-mcp/deploy/systemd/catalyst-center-iac-mcp.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now catalyst-center-iac-mcp
```

3. Verify:

```bash
sudo systemctl status catalyst-center-iac-mcp
curl http://127.0.0.1:8000/healthz
```

### NGINX HTTPS Deployment

1. Install NGINX and obtain a certificate.
2. Copy the example config:

```bash
sudo cp /opt/catalyst-center-iac-mcp/deploy/nginx/catalyst-center-iac-mcp.conf /etc/nginx/conf.d/
sudo nginx -t
sudo systemctl reload nginx
```

3. Verify over HTTPS:

```bash
curl https://mcp.example.com/healthz
```

Important for MCP and SSE:

- reverse proxy buffering must stay disabled on `/mcp/`
- `proxy_read_timeout` should be large enough for long-running jobs
- `X-Forwarded-Proto` should be passed through

## Docker

Build:

```bash
docker build -t catalyst-center-iac-mcp .
```

Run:

```bash
docker run -d \
  --name catalyst-center-iac-mcp \
  -p 8000:8000 \
  -e SERVER_HOST=0.0.0.0 \
  -e SERVER_PORT=8000 \
  -e REDIS_URL=redis://redis:6379/0 \
  -e CATALYSTCENTER_HOST=catalyst-center.example.com \
  -e CATALYSTCENTER_USERNAME=automation \
  -e CATALYSTCENTER_PASSWORD=change-me \
  -e CATALYSTCENTER_VERSION=2.6.0 \
  -v /var/lib/catalyst-center-iac-mcp:/var/lib/catalyst-center-iac-mcp \
  catalyst-center-iac-mcp
```

For production HTTPS, put the container behind NGINX, Caddy, HAProxy, or a Kubernetes ingress.

## Docker Compose HTTPS Stack

For a single-host Linux deployment with Redis, the MCP app, and NGINX HTTPS termination, use the included [compose.yaml](/Users/pawansi/workspace/catalyst_center_iac_mcp/compose.yaml).

This stack includes:

- `redis`
- `app`
- `nginx`

It expects:

- an app environment file at `deploy/env/catalyst-center-iac-mcp.env`
- TLS certificates at:
  - `deploy/certs/fullchain.pem`
  - `deploy/certs/privkey.pem`

The Docker-specific NGINX config is [catalyst-center-iac-mcp-docker.conf](/Users/pawansi/workspace/catalyst_center_iac_mcp/deploy/nginx/catalyst-center-iac-mcp-docker.conf).

### Bring Up the Stack

1. Copy and edit the environment file:

```bash
cp deploy/env/catalyst-center-iac-mcp.env.example deploy/env/catalyst-center-iac-mcp.env
vi deploy/env/catalyst-center-iac-mcp.env
```

2. Place your TLS certificate and private key here:

```bash
deploy/certs/fullchain.pem
deploy/certs/privkey.pem
```

3. Start the full stack:

```bash
docker compose up -d --build
```

4. Verify:

```bash
docker compose ps
curl https://your-hostname/healthz
```

### Compose Notes

- The MCP app listens on the internal Docker network at `app:8000`
- NGINX exposes `80` and `443`
- Redis persists data in the `redis-data` volume
- ansible-runner artifacts persist in the `app-artifacts` volume
- NGINX disables proxy buffering for `/mcp/` so HTTP/SSE transport remains usable

### One-Command Linux Example

After the env file and TLS files are in place:

```bash
docker compose up -d --build
```

Then register the MCP server in your client as:

```json
{
  "mcpServers": {
    "catalyst-center": {
      "url": "https://your-hostname/mcp",
      "transport": "http"
    }
  }
}
```

## How to Use

This section provides step-by-step instructions for common user workflows.

### Quick Start: First-Time Setup

**Step 1: Verify Installation**

```bash
# Check server is installed
catalyst-center-iac-mcp --help

# Check Redis is running
redis-cli ping  # Should return "PONG"
```

**Step 2: Configure Credentials**

Edit your environment file with your Catalyst Center details:

```bash
# macOS
nano ~/.config/catalyst-center-iac-mcp/env

# Linux
sudo nano /etc/catalyst-center-iac-mcp/catalyst-center-iac-mcp.env
```

Update these values:
```bash
CATALYSTCENTER_HOST=your-actual-catalyst-center.example.com
CATALYSTCENTER_USERNAME=your-username
CATALYSTCENTER_PASSWORD=your-password
```

**Step 3: Start the Server**

```bash
# macOS
cd ~/workspace/catalyst_center_iac_mcpserver
source .venv/bin/activate
>>>>>>> c215d6036b2dcf7d1cd4558c49a01e1b7391fe86
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

**Step 2: Extract Task ID from Response**

Response will look like:
```json
{
  "jsonrpc": "2.0",
  "id": 1,
  "result": {
    "content": [
      {
        "type": "text",
        "text": "{\"taskId\":\"abc-123-def-456\",\"status\":\"submitted\"}"
      }
    ]
  }
}
```

Extract the `taskId`: `abc-123-def-456`

**Step 3: Poll Task Status**

```bash
curl http://127.0.0.1:8000/tasks/get/abc-123-def-456
```

**Step 4: Wait for Completion**

Poll every 5-10 seconds until `status` is `completed` or `failed`:

```bash
# Automated polling script
TASK_ID="abc-123-def-456"
while true; do
  STATUS=$(curl -s http://127.0.0.1:8000/tasks/get/$TASK_ID | jq -r '.status')
  echo "Status: $STATUS"
  if [ "$STATUS" = "completed" ] || [ "$STATUS" = "failed" ]; then
    break
  fi
  sleep 5
done

# Get final result
curl http://127.0.0.1:8000/tasks/get/$TASK_ID | jq .
```

---

### Common Workflows

#### Workflow 1: Create Site Hierarchy

**User Actions:**

1. **Create Area**
```bash
curl -X POST http://127.0.0.1:8000/mcp \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "id": 1,
    "method": "tools/call",
    "params": {
      "name": "provision_site",
      "arguments": {
        "site_type": "area",
        "name": "USA",
        "parent_path": "Global"
      }
    }
  }'
```

2. **Create Building**
```bash
curl -X POST http://127.0.0.1:8000/mcp \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "id": 2,
    "method": "tools/call",
    "params": {
      "name": "provision_site",
      "arguments": {
        "site_type": "building",
        "name": "San Jose HQ",
        "parent_path": "Global/USA",
        "latitude": 37.3382,
        "longitude": -121.8863
      }
    }
  }'
```

3. **Create Floor**
```bash
curl -X POST http://127.0.0.1:8000/mcp \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "id": 3,
    "method": "tools/call",
    "params": {
      "name": "provision_site",
      "arguments": {
        "site_type": "floor",
        "name": "Floor 1",
        "parent_path": "Global/USA/San Jose HQ",
        "rf_model": "Outdoor Open Space"
      }
    }
  }'
```

#### Workflow 2: Discover and Inventory Devices

**User Actions:**

1. **Start Device Discovery**
```bash
curl -X POST http://127.0.0.1:8000/mcp \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "id": 1,
    "method": "tools/call",
    "params": {
      "name": "discover_devices",
      "arguments": {
        "discovery_name": "Campus-Discovery-2024",
        "discovery_type": "CIDR",
        "ip_address_list": ["10.10.10.0/24"],
        "protocol_order": "ssh,telnet",
        "retry": 3,
        "timeout": 5
      }
    }
  }'
```

2. **Poll Discovery Task** (wait for completion)

3. **Update Device Inventory**
```bash
curl -X POST http://127.0.0.1:8000/mcp \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "id": 2,
    "method": "tools/call",
    "params": {
      "name": "manage_inventory",
      "arguments": {
        "device_ips": ["10.10.10.1", "10.10.10.2"],
        "site_name": "Global/USA/San Jose HQ",
        "update_mgmt_ip": true
      }
    }
  }'
```

#### Workflow 3: Configure Network Settings

**User Actions:**

```bash
curl -X POST http://127.0.0.1:8000/mcp \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "id": 1,
    "method": "tools/call",
    "params": {
      "name": "configure_network_settings",
      "arguments": {
        "site_name": "Global/USA/San Jose HQ",
        "dhcp_servers": ["10.10.10.10", "10.10.10.11"],
        "dns_servers": ["8.8.8.8", "8.8.4.4"],
        "ntp_servers": ["time.nist.gov", "time.google.com"],
        "timezone": "America/Los_Angeles",
        "snmp_servers": ["10.10.10.100"],
        "syslog_servers": ["10.10.10.101"]
      }
    }
  }'
```

#### Workflow 4: Read Current Configuration (Read-Only)

**User Actions:**

```bash
curl -X POST http://127.0.0.1:8000/mcp \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "id": 1,
    "method": "tools/call",
    "params": {
      "name": "generate_site_config",
      "arguments": {
        "module_args_json": "{\"config\":{\"component_specific_filters\":{\"site\":[{\"parent_name_hierarchy\":\"Global/USA\",\"site_type\":[\"building\",\"floor\"]}]}}}"
      }
    }
  }'
```

This returns current site configuration without making any changes.

---

### Multi-Tenant Usage

This path is still supported for legacy tenant-scoped routing.

**User Actions:**

1. **Configure Second Tenant**

Add to your environment file:
>>>>>>> c215d6036b2dcf7d1cd4558c49a01e1b7391fe86
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
    "method": "tools/call",
    "params": {
      "name": "provision_site",
      "arguments": {
        "site_type": "building",
        "name": "PDX-HQ",
        "parent_path": "Global",
        "catalyst_center": "Portland"
      }
    }
  }'
```

You can also inspect configured clusters first with `list_catalyst_centers`.

Example:

```bash
curl -X POST http://127.0.0.1:8000/mcp \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "id": 1,
    "method": "tools/call",
    "params": {
      "name": "list_catalyst_centers",
      "arguments": {}
    }
  }'
```

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


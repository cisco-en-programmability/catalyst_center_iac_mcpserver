# Catalyst Center IAC MCP Server

A FastMCP server that exposes Cisco Catalyst Center automation as MCP tools for AI agents.

## What It Does

- **70 MCP tools** for Catalyst Center workflows
- **3 Direct tools**: Simplified interfaces for common operations
- **38 Workflow tools**: Full control over Catalyst Center configuration
- **29 Config generators**: Read-only tools for querying current state
- **Async task execution** with Redis persistence
- **Multi-tenant support** for multiple Catalyst Center instances
- **Cluster support** through YAML catalog configuration
- **Version fallback** for automatic Catalyst Center compatibility
- **Schema-driven** tool registry for easy maintenance

## Quick Start

For production deployments, start with the Docker or Docker Compose workflows in the [Installation](#installation) section. The local Python quick start below is intended for development and lab environments.

### 1. Prerequisites

```bash
# Python 3.11+
python3 --version

# Redis 6.0+
redis-cli ping  # Should return "PONG"

# Python package and Ansible collection manifests
ls pyproject.toml requirements.yml
```

### 2. Install

```bash
# Clone repository
git clone https://github.com/cisco-en-programmability/catalyst_center_iac_mcpserver.git
cd catalyst_center_iac_mcpserver

# Create virtual environment
python3 -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install Python package and Ansible runtime separately
pip install --upgrade pip setuptools wheel
pip install "ansible-core>=2.16,<2.19"
pip install .

# Install Ansible collection
ansible-galaxy collection install -r requirements.yml
```

### 3. Configure

```bash
# Create config directory
mkdir -p ~/.config/catalyst-center-iac-mcp

# Create environment file
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

# Edit with your credentials
nano ~/.config/catalyst-center-iac-mcp/env
```

### 4. Run

```bash
# Load environment and start
export $(grep -v '^#' ~/.config/catalyst-center-iac-mcp/env | xargs)
catalyst-center-iac-mcp
```

Server will be available at: `http://127.0.0.1:8000`

### 5. Test

#### Option A: With API Key Authentication (Recommended)

**Step 1: Generate a secure API key**
```bash
# Generate a random 32-character API key
API_KEY=$(python3 -c "import secrets; print(secrets.token_urlsafe(32))")
echo "Generated API Key: $API_KEY"

# Or use a custom key
API_KEY="my-secure-key-12345"
```

**Step 2: Configure the server**
```bash
# Add to your .env file or export
export API_KEY_ENABLED=true
export API_KEYS="$API_KEY"

# Restart server to apply changes
catalyst-center-iac-mcp
```

**Step 3: Test with API key**
```bash
# Health check with API key
curl -k https://127.0.0.1:8000/healthz \
  -H "X-API-Key: $API_KEY"

# Expected response:
# {"status": "ok", "subject": "apikey:my-secur..."}

# List available tools with API key
curl -k -X POST https://127.0.0.1:8000/mcp \
  -H "Content-Type: application/json" \
  -H "X-API-Key: $API_KEY" \
  -d '{"jsonrpc":"2.0","id":1,"method":"tools/list","params":{}}'

# Call a tool with API key
curl -k -X POST https://127.0.0.1:8000/mcp \
  -H "Content-Type: application/json" \
  -H "X-API-Key: $API_KEY" \
  -d '{
    "jsonrpc": "2.0",
    "id": 2,
    "method": "tools/call",
    "params": {
      "name": "list_catalyst_centers",
      "arguments": {}
    }
  }'

# Check task status with API key
TASK_ID="your-task-id-here"
curl -k https://127.0.0.1:8000/iactasks/get/$TASK_ID \
  -H "X-API-Key: $API_KEY"

# Get task logs with API key
curl -k https://127.0.0.1:8000/iactasks/get/$TASK_ID/logs \
  -H "X-API-Key: $API_KEY"
```

**Multiple API Keys (for different clients):**
```bash
# Generate multiple keys
KEY_CI_CD=$(python3 -c "import secrets; print(secrets.token_urlsafe(32))")
KEY_MONITORING=$(python3 -c "import secrets; print(secrets.token_urlsafe(32))")
KEY_BACKUP=$(python3 -c "import secrets; print(secrets.token_urlsafe(32))")

# Configure server with multiple keys
export API_KEYS="$KEY_CI_CD,$KEY_MONITORING,$KEY_BACKUP"

# Each client uses their own key
curl -H "X-API-Key: $KEY_CI_CD" https://127.0.0.1:8000/mcp ...
curl -H "X-API-Key: $KEY_MONITORING" https://127.0.0.1:8000/mcp ...
```

**Custom Header Name:**
```bash
# Use a custom header instead of X-API-Key
export API_KEY_HEADER="X-Custom-Auth"

# Restart server, then use custom header
curl -H "X-Custom-Auth: $API_KEY" https://127.0.0.1:8000/healthz
```

#### Option B: With Session ID (Stateful)

```bash
# Health check
curl -k https://127.0.0.1:8000/healthz

# Initialize MCP session and capture the session ID
SESSION_ID=$(curl -k -s -D - https://127.0.0.1:8000/mcp \
  -H "Content-Type: application/json" \
  -H "Accept: application/json, text/event-stream" \
  -d '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2025-03-26","capabilities":{},"clientInfo":{"name":"curl","version":"1.0"}}}' \
  | awk 'BEGIN{IGNORECASE=1} /^mcp-session-id:/{print $2}' | tr -d '\r')

echo "Session ID: $SESSION_ID"

# List available tools with the returned session ID
curl -k -X POST https://127.0.0.1:8000/mcp \
  -H "Content-Type: application/json" \
  -H "Accept: application/json, text/event-stream" \
  -H "mcp-session-id: ${SESSION_ID}" \
  -d '{"jsonrpc":"2.0","id":2,"method":"tools/list","params":{}}'
```

#### Option C: Without Authentication (Development Only)

```bash
# Disable authentication
export API_KEY_ENABLED=false
export OAUTH_ENABLED=false

# Restart server, then test without headers
curl -k https://127.0.0.1:8000/healthz
curl -k -X POST https://127.0.0.1:8000/mcp \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","id":1,"method":"tools/list"}'
```

**⚠️ Security Note:** Always use API keys or OAuth in production. Anonymous access should only be used for local development.

## Tool Categories

### Direct Tools (3)

Simplified interfaces for common operations:

- **`provision_site`** - Create/update sites with flat parameters
- **`delete_site`** - Delete sites (destructive)
- **`configure_network_settings`** - Configure DHCP, DNS, NTP, SNMP, Syslog

### Workflow Tools (38)

Full control over configuration (pattern: `<module>` without the `_workflow_manager` suffix):

- Site management, ISE/AAA, templates, PnP, wireless
- Network profiles, assurance, application policy
- Discovery, inventory, provisioning, reports
- **SD-Access fabric** (8 tools), LAN automation, RMA

### Config Generators (29)

Read-only tools for querying state (pattern: `<domain>_config`):

- Query current configuration without making changes
- Default to `state: gathered` for safe operations
- Same categories as workflow tools

See [tool_catalog.yaml](https://github.com/cisco-en-programmability/catalyst_center_iac_mcpserver/blob/main/tool_catalog.yaml) and the MCP `tools/list` response for the complete tool inventory.

### Cluster Selection

Most tools accept:

- **`tenant_id`**: Routes through tenant-scoped environment variables
- **`catalyst_center`**: Selects cluster from `catalyst_center_clusters.yaml` by name, label, location, or host

If both provided, `catalyst_center` takes precedence.

## Architecture

- `FastMCP`: MCP tool registration and request handling
- `FastAPI`: HTTP app for `/mcp`, `/healthz`, and `/iactasks/get/{task_id}`
- `ansible-runner`: the only execution path for Catalyst Center operations
- `Redis`: task state, progress, results, and artifact indexing
- `transformers.py`: flat tool input to nested workflow payload translation
- `runner_engine.py`: module submission, ansible-runner lifecycle, artifact persistence

The server is stateless by design. Redis and runner artifacts hold the operational state, which makes multi-instance deployment practical.

## Multiple Catalyst Centers

Use [`catalyst_center_clusters.yaml`](https://github.com/cisco-en-programmability/catalyst_center_iac_mcpserver/blob/main/catalyst_center_clusters.yaml) to define multiple Catalyst Center clusters that the MCP server can target by `name`, `label`, `location`, or `host`. You can also mark exactly one enabled cluster with `default: true` so calls that omit `catalyst_center` use that cluster automatically.

Example:

```yaml
catalyst_centers:
  - name: "Portland"
    label: "dev"
    host: "Portland-center.domain.com"
    version: "3.1.3.0"
    location: "Portland"
    enabled: true
    default: true
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

Recommended production paths:

- Docker for single-node deployments
- Docker Compose HTTPS stack for Redis, NGINX, and the MCP server

Use the local Python installation steps below for development and lab environments.

Choose your platform and deployment mode:

### macOS Local Python Installation

#### Prerequisites

```bash
# Install Homebrew (if not already installed)
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

# Install Python 3.11+
brew install python@3.11

# Install Redis
brew install redis
brew services start redis

# Verify installations
python3 --version  # Should be 3.11+
redis-cli ping     # Should return "PONG"
```

#### Install MCP Server

```bash
# Clone repository
git clone https://github.com/cisco-en-programmability/catalyst_center_iac_mcpserver.git
cd catalyst_center_iac_mcpserver

# Create virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install Python package and Ansible runtime separately
pip install --upgrade pip setuptools wheel
pip install "ansible-core>=2.16,<2.19"
pip install .

# Install Ansible collection
ansible-galaxy collection install -r requirements.yml
```

#### Configure

```bash
# Create config directory
mkdir -p ~/.config/catalyst-center-iac-mcp

# Create environment file
cat > ~/.config/catalyst-center-iac-mcp/env << 'EOF'
# Redis Configuration
REDIS_URL=redis://127.0.0.1:6379/0

# Artifact Storage
RUNNER_ARTIFACT_ROOT=$HOME/.local/share/catalyst-center-iac-mcp/artifacts

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
EOF

# Edit with your actual credentials
nano ~/.config/catalyst-center-iac-mcp/env
```

#### Run

```bash
# Activate virtual environment
cd ~/path/to/catalyst_center_iac_mcpserver
source .venv/bin/activate

# Load environment variables
export $(grep -v '^#' ~/.config/catalyst-center-iac-mcp/env | xargs)

# Start server
catalyst-center-iac-mcp
```

Server will be available at: `http://127.0.0.1:8000`

---

### Ubuntu/Debian Local Python Installation

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

#### Install MCP Server (Local Python)

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
pip install "ansible-core>=2.16,<2.19"
pip install .
ansible-galaxy collection install -r requirements.yml
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

### RHEL/CentOS/Rocky Linux Local Python Installation

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

### Windows WSL2 Local Python Installation

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

# Install Python package and Ansible runtime separately
pip install --upgrade pip setuptools wheel
pip install "ansible-core>=2.16,<2.19"
pip install -e ".[dev]"

# Install Ansible collection
ansible-galaxy collection install -r requirements.yml

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
HTTPS_ONLY=true

MCP_PATH=/mcp
MCP_TRANSPORT=http
MCP_STATELESS_HTTP=true
RUNNER_TIMEOUT_SECONDS=3600
TASK_TTL_SECONDS=86400
TASK_POLL_INTERVAL_MS=2000
CATALYST_CENTER_CLUSTERS_FILE=./catalyst_center_clusters.yaml
```

`MCP_STATELESS_HTTP=true` is the default and is the correct mode for app-level MCP server registrations, including Codex app-level MCP servers. Set it to `false` only if you explicitly want session-backed HTTP behavior and your client supports user-specific MCP sessions.

If you run the server with `MCP_STATELESS_HTTP=false` and register it as an app-level MCP server, some clients may fail with errors like:

```text
Trying to create user-specific connection for app-level server
```

That happens because session-backed MCP HTTP requires a per-user session, while app-level registrations are shared and stateless by design.

For the `reports` workflow tool, each `generate_report` entry must include a non-empty `view` field. If the report view is not known, ask the user to choose the view before executing the tool instead of guessing.

`HTTPS_ONLY=true` is the default. The server will refuse to start unless `TLS_CERTFILE` and `TLS_KEYFILE` are configured. Set `HTTPS_ONLY=false` only for local development or when HTTP is intentionally used behind another TLS terminator.

### Direct TLS Environment Variables

If you want the app itself to terminate HTTPS:

```bash
TLS_CERTFILE=/etc/ssl/certs/catalyst-center-iac-mcp/fullchain.pem
TLS_KEYFILE=/etc/ssl/private/catalyst-center-iac-mcp/privkey.pem
TLS_CA_CERTS=/etc/ssl/certs/ca-certificates.crt
SERVER_PORT=8443
```

### API Key Authentication (Recommended for Services)

```bash
# Enable API key authentication
API_KEY_ENABLED=true

# Comma-separated list of valid API keys
API_KEYS=your-secret-key-12345,another-key-67890

# Optional: Custom header name (default: X-API-Key)
API_KEY_HEADER=X-API-Key
```

**Usage:**
```bash
curl -H "X-API-Key: your-secret-key-12345" \
  http://localhost:8000/mcp \
  -d '{"jsonrpc":"2.0","id":1,"method":"tools/list"}'
```

**Generate secure keys:**
```bash
python3 -c "import secrets; print(secrets.token_urlsafe(32))"
```

See **[docs/API_KEY_AUTHENTICATION.md](https://github.com/cisco-en-programmability/catalyst_center_iac_mcpserver/blob/main/docs/API_KEY_AUTHENTICATION.md)** for the complete guide.

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

Define the cluster inventory in [`catalyst_center_clusters.yaml`](https://github.com/cisco-en-programmability/catalyst_center_iac_mcpserver/blob/main/catalyst_center_clusters.yaml), then provide credentials by cluster label or slug:

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
- If `catalyst_center` is omitted, the enabled cluster marked with `default: true` is used automatically.
- If no default is configured and there is exactly one enabled cluster, that single enabled cluster is used automatically.
- Use `list_catalyst_centers` to inspect enabled cluster names, labels, locations, and hosts before selecting one.

An example environment file is included at [catalyst-center-iac-mcp.env.example](https://github.com/cisco-en-programmability/catalyst_center_iac_mcpserver/blob/main/deploy/env/catalyst-center-iac-mcp.env.example).

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

- systemd unit: [catalyst-center-iac-mcp.service](https://github.com/cisco-en-programmability/catalyst_center_iac_mcpserver/blob/main/deploy/systemd/catalyst-center-iac-mcp.service)
- NGINX config: [catalyst-center-iac-mcp.conf](https://github.com/cisco-en-programmability/catalyst_center_iac_mcpserver/blob/main/deploy/nginx/catalyst-center-iac-mcp.conf)

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

For a single-host Linux deployment with Redis, the MCP app, and NGINX HTTPS termination, use the included [compose.yaml](https://github.com/cisco-en-programmability/catalyst_center_iac_mcpserver/blob/main/compose.yaml).

This stack includes:

- `redis`
- `app`
- `nginx`

It expects:

- an app environment file at `deploy/env/catalyst-center-iac-mcp.env`
- TLS certificates at:
  - `deploy/certs/fullchain.pem`
  - `deploy/certs/privkey.pem`

The Docker-specific NGINX config is [catalyst-center-iac-mcp-docker.conf](https://github.com/cisco-en-programmability/catalyst_center_iac_mcpserver/blob/main/deploy/nginx/catalyst-center-iac-mcp-docker.conf).

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
cd ~/path/to/catalyst_center_iac_mcpserver
source .venv/bin/activate
export $(grep -v '^#' ~/.config/catalyst-center-iac-mcp/env | xargs)
catalyst-center-iac-mcp

# Linux
sudo systemctl start catalyst-center-iac-mcp
```

Server runs at: `http://127.0.0.1:8000`

**Step 4: Verify Server is Running**

```bash
# Health check
curl http://127.0.0.1:8000/healthz

# Should return: {"status":"healthy"}
```

## Usage

### With Claude Desktop

Add to `claude_desktop_config.json`:

**Local HTTP:**
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

**Production HTTPS:**
```json
{
  "mcpServers": {
    "catalyst-center": {
      "url": "https://mcp.example.com/mcp",
      "transport": "http"
    }
  }
}
```

### Example Tool Calls

#### 1. Create Site Hierarchy

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
        "site_type": "building",
        "name": "San Jose HQ",
        "parent_path": "Global/USA",
        "latitude": 37.3382,
        "longitude": -121.8863
      }
    }
  }'
```

#### 2. Configure Network Settings

```bash
curl -X POST http://127.0.0.1:8000/mcp \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "id": 2,
    "method": "tools/call",
    "params": {
      "name": "configure_network_settings",
      "arguments": {
        "site_name": "Global/USA/San Jose HQ",
        "dhcp_servers": ["10.10.10.10"],
        "dns_servers": ["8.8.8.8", "8.8.4.4"],
        "ntp_servers": ["time.nist.gov"],
        "timezone": "America/Los_Angeles"
      }
    }
  }'
```

#### 3. Query Current Configuration (Read-Only)

```bash
curl -X POST http://127.0.0.1:8000/mcp \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "id": 3,
    "method": "tools/call",
    "params": {
      "name": "generate_site_config",
      "arguments": {
        "module_args_json": "{\"config\":{\"component_specific_filters\":{\"site\":[{\"parent_name_hierarchy\":\"Global/USA\",\"site_type\":[\"building\"]}]}}}"
      }
    }
  }'
```

### Task Polling

Long operations return IaC task IDs. Poll for completion:

```bash
# Extract IaC task ID from response
IAC_TASK_ID="abc-123-def-456"

# Poll task status
curl http://127.0.0.1:8000/iactasks/get/$IAC_TASK_ID

# Response includes status, progress, and results
{
  "iacTaskId": "abc-123-def-456",
  "iacStatus": "completed",
  "iacProgress": 100,
  "iacTotal": 100,
  "iacStatusMessage": "Task completed successfully",
  "result": {...}
}
```

### Task Logs

Use the MCP tools `get_task_stdout` and `get_task_log` to read task artifacts.

- Pass `head_lines` or `tail_lines`, not both.
- You do not need to send `tail_lines: null` when using `head_lines`.
- If neither is provided, the server defaults internally to the last `100` lines.

Examples:

```json
{
  "iac_task_id": "abc-123-def-456",
  "head_lines": 200
}
```

```json
{
  "iac_task_id": "abc-123-def-456",
  "log_type": "catalystcenter",
  "tail_lines": 500
}
```

Use `get_iac_task` for a compact task summary and `get_iac_taskdetail` for the full stored task payload, including `result`, `iacEvents`, artifact paths, and progress fields.

### Python Examples

See the [examples directory](https://github.com/cisco-en-programmability/catalyst_center_iac_mcpserver/tree/main/examples) for complete Python examples:

- **`provision_site_example.py`** - Site hierarchy creation
- **`discovery_example.py`** - Device discovery with polling
- **`fabric_workflow_example.py`** - SD-Access fabric setup
- **`network_settings_example.py`** - Network settings configuration
- **`version_fallback_example.py`** - Version normalization behavior

All examples support HTTPS with SSL verification and OAuth authentication.

## Multi-Tenant & Multi-Cluster Support

### Multi-Tenant (Legacy)

Add tenant-specific credentials to environment:

### Multi-Tenant Usage

This path is still supported for legacy tenant-scoped routing.

Add to your environment file:
```bash
CATALYSTCENTER_ACME_HOST=acme-catalyst.example.com
CATALYSTCENTER_ACME_USERNAME=acme-admin
CATALYSTCENTER_ACME_PASSWORD=acme-secret
```

Use with `tenant_id="acme"` in tool calls.

For multi-cluster routing, use the `catalyst_center` argument with selectors defined in [`catalyst_center_clusters.yaml`](https://github.com/cisco-en-programmability/catalyst_center_iac_mcpserver/blob/main/catalyst_center_clusters.yaml). Inspect configured clusters first with `list_catalyst_centers`.

For end-to-end request examples, see the [examples directory](https://github.com/cisco-en-programmability/catalyst_center_iac_mcpserver/tree/main/examples) and the [module dependency guide](https://github.com/cisco-en-programmability/catalyst_center_iac_mcpserver/blob/main/MODULE_DEPENDENCIES.md).

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

See the [examples directory](https://github.com/cisco-en-programmability/catalyst_center_iac_mcpserver/tree/main/examples) for complete workflows:
- Site provisioning
- Device discovery  
- Network settings
- SD-Access fabric
- **Multi-tenant operations** (2 Catalyst Center instances)
- **Version fallback** (automatic version normalization)

## Production Deployment

For production, prefer:
- Docker Compose HTTPS stack for Redis, the MCP app, and NGINX
- Docker behind an external reverse proxy for simpler single-node deployments
- systemd with NGINX only when you intentionally manage a host-based Python install

See [compose.yaml](https://github.com/cisco-en-programmability/catalyst_center_iac_mcpserver/blob/main/compose.yaml) and the files under [`deploy/`](https://github.com/cisco-en-programmability/catalyst_center_iac_mcpserver/tree/main/deploy) for production configurations.

## Endpoints

- `GET /healthz` - Health check
- `POST /mcp` - MCP protocol endpoint  
- `GET /iactasks/get/{task_id}` - Task status
- `GET /iactasks/get/{task_id}/logs` - Task logs and artifacts

## Documentation

### Module Dependencies Guide
See **[MODULE_DEPENDENCIES.md](https://github.com/cisco-en-programmability/catalyst_center_iac_mcpserver/blob/main/MODULE_DEPENDENCIES.md)** for comprehensive documentation on:
- **Mandatory requirements** for each workflow module
- **How to get required information** (device IPs, site IDs, etc.)
- **Prerequisite data gathering** using config generators
- **Complete workflow examples** with dependency chains
- **Troubleshooting** common prerequisite errors

**Example:** For compliance checks, you need either:
- Device IP (get from `generate_inventory_config()`)
- Site ID (get from `generate_site_config()`)

### Additional Resources
- [Examples](https://github.com/cisco-en-programmability/catalyst_center_iac_mcpserver/tree/main/examples) - Working code samples
- [Tool Catalog](https://github.com/cisco-en-programmability/catalyst_center_iac_mcpserver/blob/main/tool_catalog.yaml) - All available modules
- [Schema Architecture](https://github.com/cisco-en-programmability/catalyst_center_iac_mcpserver/blob/main/SCHEMA_DRIVEN_ARCHITECTURE.md) - Tool registry design
- [Contributing](https://github.com/cisco-en-programmability/catalyst_center_iac_mcpserver/blob/main/CONTRIBUTING.md) - Development guide

## Release Notes

See [CHANGELOG.md](https://github.com/cisco-en-programmability/catalyst_center_iac_mcpserver/blob/main/CHANGELOG.md) for version history, release notes, and upgrade guidance.

## Troubleshooting

**Missing tools:** Reinstall Ansible collection
```bash
ansible-galaxy collection install cisco.catalystcenter:==2.6.0 --force
```

**Connection issues:** Verify Catalyst Center reachability and credentials

**Redis errors:** Ensure Redis is running and accessible

## Support

For the certified `cisco.catalystcenter` collection on Red Hat Automation Hub, use the `Create issue` action from the collection page instead of opening GitHub issues for collection certification support.

For this MCP server repository, open issues in [GitHub Issues](https://github.com/cisco-en-programmability/catalyst_center_iac_mcpserver/issues). For broader Catalyst Center platform guidance, see [Cisco DevNet](https://developer.cisco.com/catalyst-center/).

## License

This repository is provided under the [Cisco Sample Code License, Version 1.1](https://github.com/cisco-en-programmability/catalyst_center_iac_mcpserver/blob/main/LICENSE).

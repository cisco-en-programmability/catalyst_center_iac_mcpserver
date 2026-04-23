# HTTPS Examples Setup Guide

All examples have been updated to use HTTPS with proper SSL verification and optional OAuth authentication.

## Quick Start

### 1. Set Environment Variables

```bash
# Required: MCP Server URL (HTTPS)
export MCP_SERVER_URL="https://mcp.example.com"

# Optional: SSL Verification (set to "false" for self-signed certs)
export VERIFY_SSL="true"

# Optional: OAuth/JWT Authentication Token
export MCP_AUTH_TOKEN="your-oauth-jwt-token-here"
```

### 2. Run Examples

```bash
# Site provisioning
python3 provision_site_example.py

# Device discovery
python3 discovery_example.py

# SD-Access fabric workflow
python3 fabric_workflow_example.py

# Network settings configuration
python3 network_settings_example.py

# Version fallback demonstration
python3 version_fallback_example.py
```

---

## Configuration Options

### Production HTTPS (Recommended)

Use a properly configured HTTPS server with valid SSL certificate:

```bash
export MCP_SERVER_URL="https://mcp.example.com"
export VERIFY_SSL="true"
export MCP_AUTH_TOKEN="eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9..."
```

### Development with Self-Signed Certificate

For testing with self-signed certificates:

```bash
export MCP_SERVER_URL="https://localhost:8443"
export VERIFY_SSL="false"  # Disable SSL verification
```

**⚠️ Warning**: Only use `VERIFY_SSL=false` in development environments!

### Local HTTP (Not Recommended)

For local development only:

```bash
export MCP_SERVER_URL="http://localhost:8000"
export VERIFY_SSL="true"  # Ignored for HTTP
```

---

## HTTPS Deployment Options

### Option 1: NGINX Reverse Proxy (Recommended)

Run the MCP server on localhost and use NGINX for HTTPS termination:

```nginx
# /etc/nginx/conf.d/mcp.conf
server {
    listen 443 ssl http2;
    server_name mcp.example.com;

    ssl_certificate /etc/letsencrypt/live/mcp.example.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/mcp.example.com/privkey.pem;

    location /mcp {
        proxy_pass http://127.0.0.1:8000;
        proxy_buffering off;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    location /tasks {
        proxy_pass http://127.0.0.1:8000;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
    }

    location /healthz {
        proxy_pass http://127.0.0.1:8000;
    }
}
```

Start the MCP server:
```bash
export SERVER_HOST=127.0.0.1
export SERVER_PORT=8000
catalyst-center-iac-mcp
```

### Option 2: Direct TLS (Simple Deployment)

Configure the MCP server to handle HTTPS directly:

```bash
export SERVER_HOST=0.0.0.0
export SERVER_PORT=8443
export TLS_CERTFILE=/etc/letsencrypt/live/mcp.example.com/fullchain.pem
export TLS_KEYFILE=/etc/letsencrypt/live/mcp.example.com/privkey.pem

catalyst-center-iac-mcp
```

### Option 3: Docker Compose with NGINX

Use the provided Docker Compose stack:

```bash
# Edit environment file
cp deploy/env/catalyst-center-iac-mcp.env.example deploy/env/catalyst-center-iac-mcp.env
nano deploy/env/catalyst-center-iac-mcp.env

# Place SSL certificates
cp fullchain.pem deploy/certs/
cp privkey.pem deploy/certs/

# Start stack
docker compose up -d --build
```

---

## OAuth/JWT Authentication

### Obtaining an Access Token

If your MCP server requires OAuth authentication:

```bash
# Example: Get token from OAuth provider
curl -X POST https://auth.example.com/oauth/token \
  -H "Content-Type: application/json" \
  -d '{
    "grant_type": "client_credentials",
    "client_id": "your-client-id",
    "client_secret": "your-client-secret",
    "audience": "catalyst-center-mcp"
  }'
```

Response:
```json
{
  "access_token": "eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "Bearer",
  "expires_in": 3600
}
```

### Using the Token

```bash
export MCP_AUTH_TOKEN="eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9..."
python3 provision_site_example.py
```

The examples automatically add the `Authorization: Bearer <token>` header when `MCP_AUTH_TOKEN` is set.

---

## SSL Certificate Setup

### Let's Encrypt (Free, Automated)

```bash
# Install certbot
sudo apt-get install certbot

# Get certificate
sudo certbot certonly --standalone -d mcp.example.com

# Certificates will be at:
# /etc/letsencrypt/live/mcp.example.com/fullchain.pem
# /etc/letsencrypt/live/mcp.example.com/privkey.pem

# Auto-renewal (add to crontab)
0 0 * * * certbot renew --quiet
```

### Self-Signed Certificate (Development Only)

```bash
# Generate self-signed certificate
openssl req -x509 -newkey rsa:4096 -nodes \
  -keyout privkey.pem \
  -out fullchain.pem \
  -days 365 \
  -subj "/CN=localhost"

# Use with VERIFY_SSL=false
export MCP_SERVER_URL="https://localhost:8443"
export VERIFY_SSL="false"
```

---

## Example Workflows

### Complete HTTPS Setup Example

```bash
# 1. Set up environment
export MCP_SERVER_URL="https://mcp.example.com"
export VERIFY_SSL="true"
export MCP_AUTH_TOKEN="$(curl -s -X POST https://auth.example.com/oauth/token \
  -H "Content-Type: application/json" \
  -d '{
    "grant_type": "client_credentials",
    "client_id": "'"$CLIENT_ID"'",
    "client_secret": "'"$CLIENT_SECRET"'",
    "audience": "catalyst-center-mcp"
  }' | jq -r '.access_token')"

# 2. Verify connection
curl -H "Authorization: Bearer $MCP_AUTH_TOKEN" \
  https://mcp.example.com/healthz

# 3. Run examples
python3 provision_site_example.py
python3 discovery_example.py
python3 fabric_workflow_example.py
```

### Development with Self-Signed Cert

```bash
# 1. Generate certificate
openssl req -x509 -newkey rsa:4096 -nodes \
  -keyout privkey.pem -out fullchain.pem -days 365 \
  -subj "/CN=localhost"

# 2. Start server with TLS
export SERVER_HOST=0.0.0.0
export SERVER_PORT=8443
export TLS_CERTFILE=./fullchain.pem
export TLS_KEYFILE=./privkey.pem
catalyst-center-iac-mcp &

# 3. Run examples (disable SSL verification)
export MCP_SERVER_URL="https://localhost:8443"
export VERIFY_SSL="false"
python3 provision_site_example.py
```

---

## Troubleshooting

### SSL Certificate Verification Failed

**Error**: `SSL: CERTIFICATE_VERIFY_FAILED`

**Solutions**:
1. **Production**: Ensure valid SSL certificate is installed
2. **Development**: Set `VERIFY_SSL=false` (not recommended for production)
3. **Self-signed**: Add certificate to system trust store

### Connection Refused

**Error**: `Connection refused`

**Solutions**:
1. Verify server is running: `curl https://mcp.example.com/healthz`
2. Check firewall rules: `sudo ufw status`
3. Verify NGINX is running: `sudo systemctl status nginx`
4. Check server logs: `journalctl -u catalyst-center-iac-mcp -f`

### Authentication Failed

**Error**: `401 Unauthorized`

**Solutions**:
1. Verify token is valid: `echo $MCP_AUTH_TOKEN`
2. Check token expiration
3. Ensure OAuth is configured: `OAUTH_ENABLED=true`
4. Verify JWKS URL is accessible

### Invalid Token Format

**Error**: `Invalid authorization header`

**Solutions**:
1. Token should be JWT format: `eyJhbGciOi...`
2. Don't include "Bearer" prefix in `MCP_AUTH_TOKEN`
3. Ensure no extra whitespace or newlines

---

## Security Best Practices

### ✅ Production Checklist

- [x] Use HTTPS with valid SSL certificate
- [x] Enable SSL verification (`VERIFY_SSL=true`)
- [x] Use OAuth/JWT authentication
- [x] Rotate tokens regularly
- [x] Use NGINX reverse proxy
- [x] Enable rate limiting
- [x] Monitor access logs
- [x] Use firewall rules
- [x] Keep certificates up to date

### ❌ Don't Do This in Production

- ❌ Use HTTP instead of HTTPS
- ❌ Disable SSL verification
- ❌ Use self-signed certificates
- ❌ Hardcode authentication tokens
- ❌ Expose server directly without reverse proxy
- ❌ Use default credentials
- ❌ Skip certificate validation

---

## Additional Resources

- **Main README**: [../README.md](../README.md)
- **Deployment Guide**: [../deploy/README.md](../deploy/README.md)
- **NGINX Config**: [../deploy/nginx/catalyst-center-iac-mcp.conf](../deploy/nginx/catalyst-center-iac-mcp.conf)
- **Docker Compose**: [../compose.yaml](../compose.yaml)
- **MCP Specification**: https://spec.modelcontextprotocol.io/

---

**Last Updated**: April 22, 2026  
**Examples Version**: 1.0 (HTTPS)

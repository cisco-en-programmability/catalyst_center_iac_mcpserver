# API Key Authentication

This guide explains how to configure and use API key-based authentication for the Catalyst Center IAC MCP Server.

## Overview

The MCP server supports three authentication modes:

1. **API Key Authentication** - Simple key-based auth using `X-API-Key` header
2. **OAuth Authentication** - JWT bearer token validation
3. **Anonymous** - No authentication (development only)

API key authentication is ideal for:
- Service-to-service communication
- CI/CD pipelines
- Automated workflows
- Development and testing

## Configuration

### Environment Variables

```bash
# Enable API key authentication
API_KEY_ENABLED=true

# Comma-separated list of valid API keys
API_KEYS=key1_abc123def456,key2_xyz789ghi012,key3_mno345pqr678

# Optional: Custom header name (default: X-API-Key)
API_KEY_HEADER=X-API-Key
```

### Example .env File

```bash
# Server configuration
SERVER_HOST=0.0.0.0
SERVER_PORT=8000
REDIS_URL=redis://127.0.0.1:6379/0

# API Key Authentication
API_KEY_ENABLED=true
API_KEYS=my-secret-key-12345,another-key-67890

# Disable OAuth (if not needed)
OAUTH_ENABLED=false

# Allow healthcheck without auth
ALLOW_ANONYMOUS_HEALTHCHECK=true
```

## Generating API Keys

### Secure Random Keys

```bash
# Generate a secure 32-character API key
python3 -c "import secrets; print(secrets.token_urlsafe(32))"
# Example output: kJ8vN2mP9qR4sT6uV8wX0yZ1aB3cD5eF7gH9iJ

# Generate multiple keys
for i in {1..3}; do
  python3 -c "import secrets; print(secrets.token_urlsafe(32))"
done
```

### UUID-based Keys

```bash
# Generate UUID-based key
python3 -c "import uuid; print(f'iac-mcp-{uuid.uuid4()}')"
# Example output: iac-mcp-f47ac10b-58cc-4372-a567-0e02b2c3d479
```

### Best Practices

1. **Use long, random keys** - At least 32 characters
2. **Rotate keys regularly** - Update keys every 90 days
3. **One key per client** - Easier to revoke if compromised
4. **Store securely** - Use secrets management (Vault, AWS Secrets Manager)
5. **Never commit to git** - Use .env files (in .gitignore)

## Usage

### HTTP Requests

```bash
# Using curl
curl -X POST http://localhost:8000/mcp \
  -H "Content-Type: application/json" \
  -H "X-API-Key: your-api-key-here" \
  -d '{
    "jsonrpc": "2.0",
    "id": 1,
    "method": "tools/list"
  }'
```

### Python Client

```python
import httpx
import json

API_KEY = "your-api-key-here"
BASE_URL = "http://localhost:8000"

headers = {
    "Content-Type": "application/json",
    "X-API-Key": API_KEY
}

# List available tools
response = httpx.post(
    f"{BASE_URL}/mcp",
    headers=headers,
    json={
        "jsonrpc": "2.0",
        "id": 1,
        "method": "tools/list"
    }
)

print(response.json())

# Call a tool
response = httpx.post(
    f"{BASE_URL}/mcp",
    headers=headers,
    json={
        "jsonrpc": "2.0",
        "id": 2,
        "method": "tools/call",
        "params": {
            "name": "provision_site",
            "arguments": {
                "site_type": "building",
                "name": "HQ",
                "parent_path": "Global"
            }
        }
    }
)

result = response.json()
print(result)
```

### JavaScript/TypeScript Client

```typescript
const API_KEY = "your-api-key-here";
const BASE_URL = "http://localhost:8000";

const headers = {
  "Content-Type": "application/json",
  "X-API-Key": API_KEY
};

// List tools
const response = await fetch(`${BASE_URL}/mcp`, {
  method: "POST",
  headers,
  body: JSON.stringify({
    jsonrpc: "2.0",
    id: 1,
    method: "tools/list"
  })
});

const data = await response.json();
console.log(data);
```

### Task Status Endpoints

```bash
# Get task status
curl -H "X-API-Key: your-api-key-here" \
  http://localhost:8000/iactasks/get/abc-123-def-456

# Get task logs
curl -H "X-API-Key: your-api-key-here" \
  http://localhost:8000/iactasks/get/abc-123-def-456/logs
```

## Authentication Flow

```
Client Request
    ↓
[X-API-Key header present?]
    ↓ Yes
[API_KEY_ENABLED=true?]
    ↓ Yes
[Key in API_KEYS list?]
    ↓ Yes
✅ Authenticated
    ↓
[subject: "apikey:abc12345..."]
[tenant_id: "default"]
```

## Error Responses

### Missing API Key

```json
{
  "detail": "Missing API key in X-API-Key header"
}
```

**HTTP Status:** 401 Unauthorized  
**WWW-Authenticate:** ApiKey

### Invalid API Key

```json
{
  "detail": "Invalid API key"
}
```

**HTTP Status:** 401 Unauthorized  
**WWW-Authenticate:** ApiKey

### Configuration Error

```json
{
  "detail": "API_KEYS must be configured when API key authentication is enabled"
}
```

**HTTP Status:** 500 Internal Server Error

## Security Considerations

### Transport Security

**Always use HTTPS in production:**

```bash
# Enable HTTPS
HTTPS_ONLY=true
TLS_CERTFILE=/path/to/cert.pem
TLS_KEYFILE=/path/to/key.pem
```

**Why:** API keys sent over HTTP can be intercepted.

### Key Management

**DO:**
- ✅ Use environment variables
- ✅ Use secrets management systems
- ✅ Rotate keys regularly
- ✅ Use different keys per environment (dev/staging/prod)
- ✅ Revoke compromised keys immediately

**DON'T:**
- ❌ Hardcode keys in source code
- ❌ Commit keys to version control
- ❌ Share keys via email/chat
- ❌ Reuse keys across environments
- ❌ Use weak or predictable keys

### Rate Limiting

Consider adding rate limiting for API key requests:

```python
# Example with slowapi (not included)
from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)

@app.post("/mcp")
@limiter.limit("100/minute")
async def mcp_endpoint(...):
    ...
```

### Logging

API keys are partially logged for audit purposes:

```
subject: "apikey:kJ8vN2mP..."
```

Only the first 8 characters are logged to prevent key exposure in logs.

## Multi-Tenant Support

Currently, API key authentication uses a default tenant. For multi-tenant scenarios:

### Option 1: Different Keys Per Tenant

```bash
# .env
API_KEYS=tenant1-key-abc123,tenant2-key-def456,tenant3-key-ghi789
```

Map keys to tenants in your application logic.

### Option 2: Use OAuth with Tenant Claims

For true multi-tenant isolation, use OAuth with tenant claims:

```bash
OAUTH_ENABLED=true
OAUTH_JWKS_URL=https://your-idp.com/.well-known/jwks.json
```

JWT claims should include `tenant_id` or `tid`.

## Combining with OAuth

You can enable both authentication methods:

```bash
# Enable both
API_KEY_ENABLED=true
OAUTH_ENABLED=true

# API keys for services
API_KEYS=service-key-123,ci-cd-key-456

# OAuth for user access
OAUTH_JWKS_URL=https://idp.example.com/.well-known/jwks.json
```

**Priority:** API key is checked first, then OAuth.

## Testing

### Test API Key Authentication

```bash
# Start server with API key auth
export API_KEY_ENABLED=true
export API_KEYS=test-key-12345
python -m uvicorn server:app --reload

# Test with valid key
curl -H "X-API-Key: test-key-12345" \
  http://localhost:8000/healthz

# Expected: {"status": "ok", "subject": "apikey:test-key..."}

# Test with invalid key
curl -H "X-API-Key: wrong-key" \
  http://localhost:8000/healthz

# Expected: 401 Unauthorized
```

### Test Without Authentication

```bash
# Disable all auth
export API_KEY_ENABLED=false
export OAUTH_ENABLED=false

# Should work without headers
curl http://localhost:8000/healthz

# Expected: {"status": "ok", "subject": "anonymous"}
```

## Production Deployment

### Docker Compose

```yaml
version: '3.8'

services:
  iac-mcp:
    image: catalyst-center-iac-mcp:latest
    environment:
      - API_KEY_ENABLED=true
      - API_KEYS=${API_KEYS}  # From .env file
      - HTTPS_ONLY=true
      - TLS_CERTFILE=/certs/server.crt
      - TLS_KEYFILE=/certs/server.key
    volumes:
      - ./certs:/certs:ro
      - ./secrets:/secrets:ro
    ports:
      - "8000:8000"
    secrets:
      - api_keys

secrets:
  api_keys:
    file: ./secrets/api_keys.txt
```

### Kubernetes Secret

```yaml
apiVersion: v1
kind: Secret
metadata:
  name: iac-mcp-api-keys
type: Opaque
stringData:
  api-keys: "key1,key2,key3"
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: iac-mcp
spec:
  template:
    spec:
      containers:
      - name: iac-mcp
        image: catalyst-center-iac-mcp:latest
        env:
        - name: API_KEY_ENABLED
          value: "true"
        - name: API_KEYS
          valueFrom:
            secretKeyRef:
              name: iac-mcp-api-keys
              key: api-keys
```

### NGINX Reverse Proxy

```nginx
server {
    listen 443 ssl http2;
    server_name iac-mcp.example.com;

    ssl_certificate /etc/nginx/certs/server.crt;
    ssl_certificate_key /etc/nginx/certs/server.key;

    location / {
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # Pass through API key header
        proxy_set_header X-API-Key $http_x_api_key;
    }
}
```

## Troubleshooting

### "Missing API key" Error

**Cause:** `X-API-Key` header not sent

**Solution:**
```bash
# Ensure header is included
curl -H "X-API-Key: your-key" ...
```

### "Invalid API key" Error

**Cause:** Key not in `API_KEYS` list

**Solution:**
1. Check `.env` file has correct keys
2. Restart server after updating `.env`
3. Verify no extra spaces in `API_KEYS`

```bash
# Correct
API_KEYS=key1,key2,key3

# Wrong (spaces)
API_KEYS=key1, key2, key3
```

### Authentication Not Working

**Cause:** `API_KEY_ENABLED` not set to `true`

**Solution:**
```bash
# Check current setting
echo $API_KEY_ENABLED

# Enable it
export API_KEY_ENABLED=true
```

### Keys Not Loading

**Cause:** `.env` file not loaded

**Solution:**
```bash
# Load .env manually
export $(cat .env | xargs)

# Or use python-dotenv
pip install python-dotenv
```

## Migration Guide

### From Anonymous to API Key Auth

1. **Generate keys:**
   ```bash
   python3 -c "import secrets; print(secrets.token_urlsafe(32))"
   ```

2. **Update .env:**
   ```bash
   API_KEY_ENABLED=true
   API_KEYS=your-generated-key
   ```

3. **Restart server:**
   ```bash
   systemctl restart catalyst-center-iac-mcp
   ```

4. **Update clients:**
   ```python
   headers = {"X-API-Key": "your-generated-key"}
   ```

### From OAuth to API Key Auth

```bash
# Disable OAuth
OAUTH_ENABLED=false

# Enable API keys
API_KEY_ENABLED=true
API_KEYS=key1,key2,key3
```

Clients change from:
```python
headers = {"Authorization": "Bearer <token>"}
```

To:
```python
headers = {"X-API-Key": "key1"}
```

## Additional Resources

- [README.md](../README.md) - Main documentation
- [MODULE_DEPENDENCIES.md](../MODULE_DEPENDENCIES.md) - Module prerequisites
- [CONTRIBUTING.md](../CONTRIBUTING.md) - Development guide

---

**Last Updated:** 2026-05-31  
**Version:** 1.0.0

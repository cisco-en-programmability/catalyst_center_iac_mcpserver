#!/usr/bin/env bash
#
# Secure quick demo for the Catalyst Center IAC MCP Server.
#
# Performs an authenticated health check and lists the configured Catalyst
# Centers over HTTPS. Intended as a first "does it work?" smoke test after
# following the golden path in README.md.
#
# Usage:
#   export MCP_URL="https://127.0.0.1:8443"     # server base URL
#   export API_KEY="your-generated-api-key"     # a key present in API_KEYS
#   ./scripts/demo.sh
#
# Notes:
#   - Set INSECURE_TLS=false to enforce certificate verification. It defaults to
#     true so a self-signed lab certificate works out of the box.
#   - Requires: curl. Uses python3 for pretty JSON if available.

set -euo pipefail

MCP_URL="${MCP_URL:-https://127.0.0.1:8443}"
API_KEY="${API_KEY:-}"
API_KEY_HEADER="${API_KEY_HEADER:-X-API-Key}"
INSECURE_TLS="${INSECURE_TLS:-true}"

if [[ -z "${API_KEY}" ]]; then
  echo "ERROR: API_KEY is not set. Export the API key you configured in API_KEYS." >&2
  echo "       export API_KEY=\"your-generated-api-key\"" >&2
  exit 1
fi

curl_opts=(--silent --show-error --fail-with-body)
if [[ "${INSECURE_TLS}" == "true" ]]; then
  curl_opts+=(--insecure)
fi

pretty() {
  if command -v python3 >/dev/null 2>&1; then
    python3 -m json.tool 2>/dev/null || cat
  else
    cat
  fi
}

echo "==> Health check: ${MCP_URL}/healthz"
curl "${curl_opts[@]}" "${MCP_URL}/healthz" \
  -H "${API_KEY_HEADER}: ${API_KEY}" | pretty
echo

echo "==> Tool call: list_catalyst_centers"
curl "${curl_opts[@]}" -X POST "${MCP_URL}/mcp" \
  -H "Content-Type: application/json" \
  -H "${API_KEY_HEADER}: ${API_KEY}" \
  -d '{
    "jsonrpc": "2.0",
    "id": 1,
    "method": "tools/call",
    "params": { "name": "list_catalyst_centers", "arguments": {} }
  }' | pretty
echo

echo "==> Demo complete."

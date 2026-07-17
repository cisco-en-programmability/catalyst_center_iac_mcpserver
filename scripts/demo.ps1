#!/usr/bin/env pwsh
#
# Secure quick demo for the Catalyst Center IAC MCP Server (Windows PowerShell 5.1
# or PowerShell 7+). Mirrors scripts/demo.sh: an authenticated health check plus a
# list_catalyst_centers tool call over HTTPS. Intended as a first "does it work?"
# smoke test after following the golden path in README.md.
#
# Usage:
#   $env:MCP_URL = "https://127.0.0.1:8443"     # server base URL
#   $env:API_KEY = "your-generated-api-key"     # a key present in API_KEYS
#   ./scripts/demo.ps1
#
# Notes:
#   - Set $env:INSECURE_TLS = "false" to enforce certificate verification. It
#     defaults to "true" so a self-signed lab certificate works out of the box.

[CmdletBinding()]
param()

$ErrorActionPreference = 'Stop'

$McpUrl       = if ($env:MCP_URL)        { $env:MCP_URL }        else { 'https://127.0.0.1:8443' }
$ApiKey       = $env:API_KEY
$ApiKeyHeader = if ($env:API_KEY_HEADER) { $env:API_KEY_HEADER } else { 'X-API-Key' }
$InsecureTls  = if ($env:INSECURE_TLS)   { $env:INSECURE_TLS }   else { 'true' }

if ([string]::IsNullOrWhiteSpace($ApiKey)) {
    Write-Error "API_KEY is not set. Set the key you configured in API_KEYS, e.g. `$env:API_KEY = 'your-generated-api-key'"
    exit 1
}

$headers = @{ $ApiKeyHeader = $ApiKey }

# Common Invoke-RestMethod parameters; handle TLS skip per PowerShell edition.
$common = @{ Headers = $headers }
if ($InsecureTls -eq 'true') {
    if ($PSVersionTable.PSVersion.Major -ge 6) {
        # PowerShell 7+ supports this switch natively.
        $common['SkipCertificateCheck'] = $true
    } else {
        # Windows PowerShell 5.1: accept self-signed certs and force TLS 1.2.
        [System.Net.ServicePointManager]::ServerCertificateValidationCallback = { $true }
        [System.Net.ServicePointManager]::SecurityProtocol = [System.Net.SecurityProtocolType]::Tls12
    }
}

Write-Host "==> Health check: $McpUrl/healthz"
$health = Invoke-RestMethod @common -Method Get -Uri "$McpUrl/healthz"
$health | ConvertTo-Json -Depth 10

Write-Host ""
Write-Host "==> Tool call: list_catalyst_centers"
$body = @{
    jsonrpc = '2.0'
    id      = 1
    method  = 'tools/call'
    params  = @{ name = 'list_catalyst_centers'; arguments = @{} }
} | ConvertTo-Json -Depth 10

$result = Invoke-RestMethod @common -Method Post -Uri "$McpUrl/mcp" `
    -ContentType 'application/json' -Body $body
$result | ConvertTo-Json -Depth 10

Write-Host ""
Write-Host "==> Demo complete."

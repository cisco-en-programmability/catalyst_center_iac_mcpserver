# catalyst_center_iac_mcp

`catalyst_center_iac_mcp` is a stateless FastMCP server that turns flat, LLM-safe tool invocations into Cisco Catalyst Center workflow-manager playbook runs executed by `ansible-runner`.

## Design

- FastMCP exposes the MCP tools.
- FastAPI provides the HTTP entrypoint, health checks, and `/tasks/get/{task_id}` polling endpoint.
- `ansible-runner.run_async()` is the only execution path for network actions.
- Redis stores task state, progress, result summaries, and runner artifact locations.
- Runner artifacts are written to disk and indexed in Redis by `taskId`.
- Tool inputs remain flat; `transformers.py` re-expands them into the nested `config` payloads expected by workflow-manager modules.
- The runtime targets the `cisco.catalystcenter` Ansible collection only.

## Transport

- Default MCP transport: Streamable HTTP (`/mcp`)
- Optional SSE mode: set `MCP_TRANSPORT=sse`
- Reverse proxies should disable buffering for MCP and progress streams.

Recommended NGINX settings:

```nginx
location /mcp/ {
    proxy_pass http://app;
    proxy_buffering off;
    proxy_cache off;
    proxy_set_header X-Accel-Buffering no;
}
```

## Environment

```bash
export REDIS_URL=redis://redis:6379/0
export CATALYSTCENTER_HOST=catalyst-center.example.com
export CATALYSTCENTER_USERNAME=automation
export CATALYSTCENTER_PASSWORD=secret
export CATALYSTCENTER_VERIFY_SSL=false
export CATALYSTCENTER_VERSION=2.3.7.9
export RUNNER_ARTIFACT_ROOT=/var/lib/catalyst-center-iac-mcp/artifacts
```

Multi-tenant credentials can be injected with tenant-scoped variables:

```bash
export CATALYSTCENTER_ACME_HOST=acme-catc.example.com
export CATALYSTCENTER_ACME_USERNAME=svc-acme
export CATALYSTCENTER_ACME_PASSWORD=secret
```

Then invoke the tools with `tenant_id="acme"`.

The runner writes a local `sitecustomize.py` shim into each Ansible private data directory.
That shim aliases `catalystcentersdk.api.CatalystCenterAPI` to `DNACenterAPI` when needed,
which keeps the current `cisco.catalystcenter` collection working without falling back to
the sunset `cisco.dnac` collection.

## Run

```bash
uvicorn server:app --host 0.0.0.0 --port 8000
```

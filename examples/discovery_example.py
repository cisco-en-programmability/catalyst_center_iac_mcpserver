#!/usr/bin/env python3
"""
Example: Discover network devices using the MCP server

This example demonstrates device discovery using IP ranges and CIDR notation.

Requirements:
- MCP server running with HTTPS
- Valid SSL certificate or set VERIFY_SSL=False for self-signed certs
- Optional: OAuth token for authentication
"""

import asyncio
import os
import httpx
import json


async def discover_network_devices():
    """Initiate device discovery for a network segment."""
    
    # Configuration
    base_url = os.getenv("MCP_SERVER_URL", "https://mcp.example.com")
    verify_ssl = os.getenv("VERIFY_SSL", "true").lower() == "true"
    auth_token = os.getenv("MCP_AUTH_TOKEN")
    
    # Setup headers
    headers = {"Content-Type": "application/json"}
    if auth_token:
        headers["Authorization"] = f"Bearer {auth_token}"
    
    async with httpx.AsyncClient(
        verify=verify_ssl,
        timeout=60.0,  # Longer timeout for discovery
        headers=headers
    ) as client:
        # Discover devices using IP range
        print("Initiating device discovery for 10.10.10.0/24...")
        
        response = await client.post(
            f"{base_url}/mcp",
            json={
                "jsonrpc": "2.0",
                "id": 1,
                "method": "tools/call",
                "params": {
                    "name": "discover_devices",
                    "arguments": {
                        "discovery_name": "Campus-Discovery-Jan-2024",
                        "discovery_type": "CIDR",
                        "ip_address_list": ["10.10.10.0/24"],
                        "protocol_order": "ssh,telnet",
                        "retry": 3,
                        "timeout": 5,
                        "tenant_id": "default"
                    }
                }
            }
        )
        
        result = response.json()
        print(f"Discovery initiated: {json.dumps(result, indent=2)}")
        
        # Extract and poll task
        if "result" in result and "content" in result["result"]:
            task_text = result["result"]["content"][0]["text"]
            task_data = json.loads(task_text)
            task_id = task_data.get("taskId")
            
            if task_id:
                print(f"\nPolling discovery task: {task_id}")
                
                # Poll until complete
                for i in range(30):
                    await asyncio.sleep(10)
                    status_response = await client.get(
                        f"{base_url}/tasks/get/{task_id}",
                        headers=headers
                    )
                    status = status_response.json()
                    
                    print(f"Progress: {status.get('progress')}/{status.get('total')} - {status.get('statusMessage')}")
                    
                    if status.get("status") in ["completed", "failed"]:
                        print(f"\nFinal status: {json.dumps(status, indent=2)}")
                        break


if __name__ == "__main__":
    print("MCP Server HTTPS Example - Device Discovery")
    print(f"Server: {os.getenv('MCP_SERVER_URL', 'https://mcp.example.com')}")
    print(f"SSL Verification: {os.getenv('VERIFY_SSL', 'true')}")
    print(f"Authentication: {'Enabled' if os.getenv('MCP_AUTH_TOKEN') else 'Disabled'}")
    print("-" * 60)
    
    asyncio.run(discover_network_devices())

#!/usr/bin/env python3
"""
Example: Provision a complete site hierarchy in Catalyst Center

This example demonstrates how to use the provision_site tool to create
a hierarchical site structure: Area -> Building -> Floor

Requirements:
- MCP server running with HTTPS (via NGINX or direct TLS)
- Valid SSL certificate or set VERIFY_SSL=False for self-signed certs
- Optional: OAuth token for authentication
"""

import asyncio
import os
import httpx


async def provision_site_hierarchy():
    """Create a complete site hierarchy using the MCP server."""
    
    # Configuration - update these for your environment
    base_url = os.getenv("MCP_SERVER_URL", "https://mcp.example.com")
    verify_ssl = os.getenv("VERIFY_SSL", "true").lower() == "true"
    auth_token = os.getenv("MCP_AUTH_TOKEN")  # Optional OAuth token
    
    # Setup headers
    headers = {"Content-Type": "application/json"}
    if auth_token:
        headers["Authorization"] = f"Bearer {auth_token}"
    
    # Create HTTPS client with SSL verification
    async with httpx.AsyncClient(
        verify=verify_ssl,
        timeout=30.0,
        headers=headers
    ) as client:
        # Step 1: Create an Area
        print("Creating area: USA...")
        area_response = await client.post(
            f"{base_url}/mcp",
            json={
                "jsonrpc": "2.0",
                "id": 1,
                "method": "tools/call",
                "params": {
                    "name": "provision_site",
                    "arguments": {
                        "site_type": "area",
                        "name": "USA",
                        "parent_path": "Global",
                        "tenant_id": "default"
                    }
                }
            }
        )
        area_result = area_response.json()
        print(f"Area task: {area_result}")
        
        # Step 2: Create a Building
        print("\nCreating building: San Jose HQ...")
        building_response = await client.post(
            f"{base_url}/mcp",
            json={
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
                        "longitude": -121.8863,
                        "tenant_id": "default"
                    }
                }
            }
        )
        building_result = building_response.json()
        print(f"Building task: {building_result}")
        
        # Step 3: Create a Floor
        print("\nCreating floor: Floor 1...")
        floor_response = await client.post(
            f"{base_url}/mcp",
            json={
                "jsonrpc": "2.0",
                "id": 3,
                "method": "tools/call",
                "params": {
                    "name": "provision_site",
                    "arguments": {
                        "site_type": "floor",
                        "name": "Floor 1",
                        "parent_path": "Global/USA/San Jose HQ",
                        "rf_model": "Outdoor Open Space",
                        "tenant_id": "default"
                    }
                }
            }
        )
        floor_result = floor_response.json()
        print(f"Floor task: {floor_result}")
        
        # Poll task status
        if "result" in floor_result and "content" in floor_result["result"]:
            task_id = floor_result["result"]["content"][0]["text"]
            # Extract taskId from response
            import json
            task_data = json.loads(task_id)
            task_id = task_data.get("taskId")
            
            if task_id:
                print(f"\nPolling task status for: {task_id}")
                status_response = await client.get(
                    f"{base_url}/tasks/get/{task_id}",
                    headers=headers
                )
                print(f"Task status: {status_response.json()}")


if __name__ == "__main__":
    # Example environment variables:
    # export MCP_SERVER_URL="https://mcp.example.com"
    # export VERIFY_SSL="true"  # Set to "false" for self-signed certs
    # export MCP_AUTH_TOKEN="your-oauth-token"  # Optional
    
    print("MCP Server HTTPS Example - Site Provisioning")
    print(f"Server: {os.getenv('MCP_SERVER_URL', 'https://mcp.example.com')}")
    print(f"SSL Verification: {os.getenv('VERIFY_SSL', 'true')}")
    print(f"Authentication: {'Enabled' if os.getenv('MCP_AUTH_TOKEN') else 'Disabled'}")
    print("-" * 60)
    
    asyncio.run(provision_site_hierarchy())

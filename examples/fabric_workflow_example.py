#!/usr/bin/env python3
"""
Example: Complete SD-Access fabric workflow

This example demonstrates a complete SD-Access fabric setup workflow:
1. Create fabric site
2. Onboard fabric devices
3. Configure virtual networks

Requirements:
- MCP server running with HTTPS
- Valid SSL certificate or set VERIFY_SSL=False for self-signed certs
- Optional: OAuth token for authentication
"""

import asyncio
import os
import httpx
import json


async def setup_sda_fabric():
    """Complete SD-Access fabric setup workflow."""
    
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
        timeout=60.0,
        headers=headers
    ) as client:
        # Step 1: Create fabric site using generic tool
        print("Step 1: Creating fabric site...")
        
        fabric_site_config = [
            {
                "site_name": "Global/USA/San Jose HQ",
                "fabric_type": "FABRIC_SITE",
                "authentication_profile": "No Authentication"
            }
        ]
        
        site_response = await client.post(
            f"{base_url}/mcp",
            json={
                "jsonrpc": "2.0",
                "id": 1,
                "method": "tools/call",
                "params": {
                    "name": "run_sda_fabric_sites_zones_workflow_manager",
                    "arguments": {
                        "config_json": json.dumps(fabric_site_config),
                        "state": "merged",
                        "tenant_id": "default"
                    }
                }
            }
        )
        print(f"Fabric site created: {site_response.json()}")
        
        # Step 2: Onboard border and edge nodes
        print("\nStep 2: Onboarding fabric devices...")
        
        device_response = await client.post(
            f"{base_url}/mcp",
            json={
                "jsonrpc": "2.0",
                "id": 2,
                "method": "tools/call",
                "params": {
                    "name": "run_sda_fabric_devices_workflow_manager",
                    "arguments": {
                        "config_json": json.dumps([{
                            "fabric_site_name_hierarchy": "Global/USA/San Jose HQ",
                            "device_ip": "10.10.10.50",
                            "device_roles": ["BORDER_NODE", "CONTROL_PLANE_NODE"]
                        }]),
                        "state": "merged",
                        "tenant_id": "default"
                    }
                }
            }
        )
        print(f"Device onboarded: {device_response.json()}")
        
        # Step 3: Configure virtual network
        print("\nStep 3: Configuring virtual network...")
        
        vn_config = [
            {
                "virtual_network_name": "GUEST_VN",
                "vlan_name": "Guest_VLAN",
                "vlan_id": 100,
                "traffic_type": "DATA",
                "fabric_sites": ["Global/USA/San Jose HQ"]
            }
        ]
        
        vn_response = await client.post(
            f"{base_url}/mcp",
            json={
                "jsonrpc": "2.0",
                "id": 3,
                "method": "tools/call",
                "params": {
                    "name": "run_sda_fabric_virtual_networks_workflow_manager",
                    "arguments": {
                        "config_json": json.dumps(vn_config),
                        "state": "merged",
                        "tenant_id": "default"
                    }
                }
            }
        )
        print(f"Virtual network configured: {vn_response.json()}")


if __name__ == "__main__":
    print("MCP Server HTTPS Example - SD-Access Fabric Workflow")
    print(f"Server: {os.getenv('MCP_SERVER_URL', 'https://mcp.example.com')}")
    print(f"SSL Verification: {os.getenv('VERIFY_SSL', 'true')}")
    print(f"Authentication: {'Enabled' if os.getenv('MCP_AUTH_TOKEN') else 'Disabled'}")
    print("-" * 60)
    
    asyncio.run(setup_sda_fabric())

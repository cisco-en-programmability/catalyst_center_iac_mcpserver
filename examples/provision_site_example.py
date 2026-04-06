#!/usr/bin/env python3
"""
Example: Provision a complete site hierarchy in Catalyst Center

This example demonstrates how to use the provision_site tool to create
a hierarchical site structure: Area -> Building -> Floor
"""

import asyncio
import httpx


async def provision_site_hierarchy():
    """Create a complete site hierarchy using the MCP server."""
    
    base_url = "http://localhost:8000"
    
    async with httpx.AsyncClient() as client:
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
                status_response = await client.get(f"{base_url}/tasks/get/{task_id}")
                print(f"Task status: {status_response.json()}")


if __name__ == "__main__":
    asyncio.run(provision_site_hierarchy())

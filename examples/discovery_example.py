#!/usr/bin/env python3
"""
Example: Discover network devices using the MCP server

This example demonstrates device discovery using IP ranges and CIDR notation.
"""

import asyncio
import httpx
import json


async def discover_network_devices():
    """Initiate device discovery for a network segment."""
    
    base_url = "http://localhost:8000"
    
    async with httpx.AsyncClient() as client:
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
                    status_response = await client.get(f"{base_url}/tasks/get/{task_id}")
                    status = status_response.json()
                    
                    print(f"Progress: {status.get('progress')}/{status.get('total')} - {status.get('statusMessage')}")
                    
                    if status.get("status") in ["completed", "failed"]:
                        print(f"\nFinal status: {json.dumps(status, indent=2)}")
                        break


if __name__ == "__main__":
    asyncio.run(discover_network_devices())

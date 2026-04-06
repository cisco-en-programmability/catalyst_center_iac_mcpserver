#!/usr/bin/env python3
"""
Example: Configure network settings for a site

This example demonstrates configuring DNS, NTP, DHCP, and other network
settings for a specific site in the hierarchy.
"""

import asyncio
import httpx
import json


async def configure_site_network_settings():
    """Configure comprehensive network settings for a site."""
    
    base_url = "http://localhost:8000"
    
    async with httpx.AsyncClient() as client:
        print("Configuring network settings for Global/USA/San Jose HQ...")
        
        response = await client.post(
            f"{base_url}/mcp",
            json={
                "jsonrpc": "2.0",
                "id": 1,
                "method": "tools/call",
                "params": {
                    "name": "configure_network_settings",
                    "arguments": {
                        "site_name": "Global/USA/San Jose HQ",
                        "dhcp_servers": ["10.10.10.10", "10.10.10.11"],
                        "dns_servers": ["8.8.8.8", "8.8.4.4"],
                        "ntp_servers": ["time.nist.gov", "time.google.com"],
                        "timezone": "America/Los_Angeles",
                        "message_of_the_day": "Welcome to San Jose HQ Network",
                        "snmp_servers": ["10.10.10.100"],
                        "syslog_servers": ["10.10.10.101"],
                        "tenant_id": "default"
                    }
                }
            }
        )
        
        result = response.json()
        print(f"Network settings configuration: {json.dumps(result, indent=2)}")
        
        # Poll task status
        if "result" in result and "content" in result["result"]:
            task_text = result["result"]["content"][0]["text"]
            task_data = json.loads(task_text)
            task_id = task_data.get("taskId")
            
            if task_id:
                print(f"\nPolling task: {task_id}")
                await asyncio.sleep(5)
                
                status_response = await client.get(f"{base_url}/tasks/get/{task_id}")
                status = status_response.json()
                print(f"Task status: {json.dumps(status, indent=2)}")


if __name__ == "__main__":
    asyncio.run(configure_site_network_settings())

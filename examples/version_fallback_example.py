#!/usr/bin/env python3
"""
Example: Demonstrating Catalyst Center version fallback functionality

This example shows how the MCP server automatically normalizes Catalyst Center
versions to the nearest supported version for compatibility.

Requirements:
- MCP server running with HTTPS
- Valid SSL certificate or set VERIFY_SSL=False for self-signed certs
- Optional: OAuth token for authentication
"""

import asyncio
import os
import httpx
import json


async def demonstrate_version_fallback():
    """Demonstrate version fallback with different Catalyst Center versions."""
    
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
        timeout=30.0,
        headers=headers
    ) as client:
        print("=== Catalyst Center Version Fallback Example ===\n")
        
        # Test case 1: Version 2.3.7.10 should fallback to 2.3.7.9
        print("1. Testing version 2.3.7.10 (should fallback to 2.3.7.9)...")
        
        response = await client.post(
            f"{base_url}/mcp",
            json={
                "jsonrpc": "2.0",
                "id": 1,
                "method": "tools/call",
                "params": {
                    "name": "generate_site_config",
                    "arguments": {
                        "module_args_json": json.dumps({
                            "config": {
                                "component_specific_filters": {
                                    "site": [{
                                        "parent_name_hierarchy": "Global/USA",
                                        "site_type": ["building"]
                                    }]
                                }
                            }
                        }),
                        "tenant_id": "default"
                    }
                }
            }
        )
        
        result = response.json()
        print(f"Response: {json.dumps(result, indent=2)}")
        
        # Test case 2: Version 3.1.3.7 should fallback to 3.1.3.6
        print("\n2. Testing version 3.1.3.7 (should fallback to 3.1.3.6)...")
        
        # Note: Set up a tenant with version 3.1.3.7 in your environment
        # os.environ["CATALYSTCENTER_TEST_HOST"] = "test-catalyst.example.com"
        # os.environ["CATALYSTCENTER_TEST_USERNAME"] = "test-admin"
        # os.environ["CATALYSTCENTER_TEST_PASSWORD"] = "test-password"
        # os.environ["CATALYSTCENTER_TEST_VERSION"] = "3.1.3.7"
        
        response = await client.post(
            f"{base_url}/mcp",
            json={
                "jsonrpc": "2.0",
                "id": 2,
                "method": "tools/call",
                "params": {
                    "name": "generate_site_config",
                    "arguments": {
                        "module_args_json": json.dumps({
                            "config": {
                                "component_specific_filters": {
                                    "site": [{
                                        "parent_name_hierarchy": "Global/USA",
                                        "site_type": ["building"]
                                    }]
                                }
                            }
                        }),
                        "tenant_id": "test"
                    }
                }
            }
        )
        
        result = response.json()
        print(f"Response: {json.dumps(result, indent=2)}")
        
        # Test case 3: Show supported versions
        print("\n3. Version fallback mapping:")
        print("   2.3.7.x -> 2.3.7.9")
        print("   3.1.3.x -> 3.1.6.0")
        print("   Other versions -> unchanged")
        
        print("\n=== Version Fallback Demo Complete ===")


async def test_version_normalization_directly():
    """Test the version normalization function directly."""
    print("\n=== Direct Version Normalization Test ===")
    
    # Import the settings to test the function
    import sys
    import os
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    
    try:
        from settings import Settings
        settings = Settings()
        
        test_versions = [
            "2.3.7.9",
            "2.3.7", 
            "3.1.3.1",
            "3.1.3.7",
            "3.1.3.0",
            "3.1.6.0",
            "invalid"
        ]
        
        print("Testing version normalization:")
        for version in test_versions:
            normalized = settings.normalize_catalystcenter_version(version)
            print(f"  {version:<12} -> {normalized}")
            
    except ImportError as e:
        print(f"Could not import settings module: {e}")
        print("This is expected if dependencies are not installed.")


if __name__ == "__main__":
    print("MCP Server HTTPS Example - Version Fallback")
    print(f"Server: {os.getenv('MCP_SERVER_URL', 'https://mcp.example.com')}")
    print(f"SSL Verification: {os.getenv('VERIFY_SSL', 'true')}")
    print(f"Authentication: {'Enabled' if os.getenv('MCP_AUTH_TOKEN') else 'Disabled'}")
    print("-" * 60)
    
    asyncio.run(demonstrate_version_fallback())
    asyncio.run(test_version_normalization_directly())

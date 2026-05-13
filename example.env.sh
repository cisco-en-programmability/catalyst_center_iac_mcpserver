#!/usr/bin/env bash

# Source this file before starting the IaC MCP server:
#   source /Users/pawansi/workspace/catalyst_center_iac_mcp/env.sh

# Portland
export CC_PORT_USERNAME="change-me"
export CC_PORT_PASSWORD="change-me"
export CC_PORT_VERIFY_SSL="false"
export CC_PORT_PORT="443"
export CC_PORT_VERSION="2.3.7.9"

# San Jose
export CC_SAN_USERNAME="change-me"
export CC_SAN_PASSWORD="change-me"
export CC_SAN_VERIFY_SSL="false"
export CC_SAN_PORT="443"
export CC_SAN_VERSION="2.3.7.9"

# Solutions
export CC_SOL_USERNAME="admin"
export CC_SOL_PASSWORD="change-me"
export CC_SOL_VERIFY_SSL="false"
export CC_SOL_PORT="443"
export CC_SOL_VERSION="3.1.6.0"

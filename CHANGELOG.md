# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Comprehensive README.md with architecture, features, and usage examples
- SLIDES.md presentation guide with 24 detailed slides
- CONTRIBUTING.md with development guidelines
- Four new specialized tools:
  - `discover_devices` - Network device discovery
  - `manage_inventory` - Device inventory management
  - `configure_network_settings` - Site network settings configuration
  - `manage_assurance_issues` - Assurance issue management (existing, now documented)
- New models: `DiscoveryRequest`, `InventoryDeviceRequest`, `NetworkSettingsRequest`
- New transformers for discovery, inventory, and network settings workflows
- Comprehensive examples directory with 5 working examples:
  - `provision_site_example.py`
  - `discovery_example.py`
  - `network_settings_example.py`
  - `fabric_workflow_example.py`
  - `examples/README.md`
- Test coverage for new transformers in `test_new_transformers.py`
- Complete documentation of all 39 generic workflow manager tools

### Changed
- Enhanced README with detailed architecture diagrams
- Improved documentation structure and organization
- Updated tool descriptions for better clarity

### Fixed
- Documentation inconsistencies
- Missing examples for specialized tools

## [0.1.0] - 2024-01-01

### Added
- Initial release of Catalyst Center IAC MCP Server
- FastMCP server implementation with MCP protocol support
- FastAPI HTTP/SSE transport layer
- ansible-runner integration for async task execution
- Redis-backed task state management
- Multi-tenant credential support
- OAuth/JWT authentication support
- 6 specialized tools:
  - `provision_site` - Create/update site hierarchy
  - `delete_site` - Delete site objects
  - `deploy_template` - Deploy configuration templates
  - `onboard_fabric_devices` - SD-Access fabric device onboarding
  - `reprovision_fabric_device` - Re-apply fabric provisioning
  - `manage_assurance_issues` - Assurance issue management
- 39 generic workflow manager tools covering complete cisco.catalystcenter collection:
  - Access point management
  - Application policy management
  - Assurance and health monitoring
  - Backup and restore
  - Device credentials and discovery
  - Events and notifications
  - Inventory management
  - ISE RADIUS integration
  - LAN automation
  - Network compliance
  - Network profiles (switching and wireless)
  - Network settings
  - Path trace
  - PnP workflows
  - Provisioning
  - Reports
  - RMA workflows
  - SD-Access (SDA) fabric management
  - SWIM (software image management)
  - Tags management
  - Templates
  - User roles
  - Wired campus automation
  - Wireless design
- Core transformers for site, template, fabric device, and assurance workflows
- Comprehensive models with Pydantic validation
- Task lifecycle management with progress tracking
- Health check endpoint (`/healthz`)
- Task status polling endpoint (`/tasks/get/{task_id}`)
- Docker deployment support
- SDK compatibility shim for DNACenterAPI → CatalystCenterAPI migration
- Unit tests for transformers and server contracts
- Basic documentation

### Security
- OAuth/JWT authentication with JWKS validation
- Tenant-scoped credential isolation
- Destructive operation confirmation requirements
- Human-in-the-loop for sensitive operations

## Release Notes

### Version 0.1.0 - Initial Release

This is the first production-ready release of the Catalyst Center IAC MCP Server. It provides a complete bridge between AI agents and Cisco Catalyst Center network automation through the Model Context Protocol (MCP).

**Key Highlights:**
- **Complete Coverage**: All 39 workflow managers from cisco.catalystcenter Ansible collection
- **AI-Friendly**: Flat tool interfaces that transform to complex nested configurations
- **Production Ready**: Multi-tenant, OAuth-enabled, Redis-backed state management
- **Async by Design**: Non-blocking task execution with real-time progress tracking
- **Comprehensive**: 45 total tools (6 specialized + 39 generic workflow managers)

**Supported Catalyst Center Versions:**
- 2.3.7.6
- 2.3.7.9
- 3.1.3.0
- 3.1.6.0

**Requirements:**
- Python >= 3.11
- Redis server
- ansible-core >= 2.16
- catalystcentersdk >= 3.1.6.0.0
- cisco.catalystcenter Ansible collection

**Known Limitations:**
- Task artifacts stored on disk (implement cleanup policy for production)
- Redis single-instance (use Redis Cluster for HA)
- No built-in workflow composition (use external orchestration)

**Migration Notes:**
- This is the initial release, no migration required
- Compatible with cisco.catalystcenter collection versions 6.x

---

## Upgrade Guide

### From Development to 0.1.0

No upgrade required - this is the initial release.

### Future Upgrades

When upgrading between versions:

1. **Backup Redis data**:
   ```bash
   redis-cli SAVE
   cp /var/lib/redis/dump.rdb /backup/
   ```

2. **Review CHANGELOG** for breaking changes

3. **Update dependencies**:
   ```bash
   pip install -e . --upgrade
   ansible-galaxy collection install cisco.catalystcenter --upgrade
   ```

4. **Update environment variables** if new settings added

5. **Run tests**:
   ```bash
   pytest
   ```

6. **Restart server**:
   ```bash
   # Graceful restart with zero downtime
   systemctl reload catalyst-mcp
   ```

---

## Support

For issues, questions, or contributions:
- GitHub Issues: https://github.com/cisco-en-programmability/catalyst_center_iac_mcp/issues
- Cisco DevNet: https://developer.cisco.com/catalyst-center/

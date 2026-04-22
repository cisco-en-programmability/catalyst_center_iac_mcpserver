# YAML-Based Tool Registry System

## Overview

The Catalyst Center IAC MCP Server now uses a **declarative YAML-based configuration system** for managing all MCP tools. This makes it easy to add, modify, or remove tools without changing the core server code.

## ✅ What's Implemented

The YAML tool registry system is **fully implemented** and includes:

### 1. Core Infrastructure
- ✅ **`tool_registry.py`** - Pydantic-based YAML loader and validator
- ✅ **`tool_catalog.yaml`** - Master tool catalog with all 78+ tools
- ✅ **Server integration** - `server.py` loads and registers tools from YAML

### 2. Tool Categories

The catalog supports three types of tools:

#### **Direct Tools** (Specialized)
- Custom handlers with simplified parameter schemas
- Transformer functions for complex config generation
- Examples: `provision_site`, `delete_site`, `deploy_template`, `discover_devices`

#### **Workflow Creation Tools** (Generic)
- Auto-registered from `*_workflow_manager` modules
- Accept raw JSON configuration
- Tool naming: `run_<module_name>`
- Examples: `run_site_workflow_manager`, `run_inventory_workflow_manager`

#### **Configuration Generation Tools** (Read-Only)
- Auto-registered from `*_playbook_config_generator` modules
- Read-only operations (state defaults to `gathered`)
- Tool naming: `generate_<base_name>_config`
- Examples: `generate_site_config`, `generate_inventory_config`

### 3. Documentation

- ✅ **`config/TOOL_CATALOG_GUIDE.md`** - Comprehensive guide for managing the tool catalog
- ✅ **`config/schemas/tool_catalog.schema.yaml`** - JSON Schema for validation
- ✅ **`scripts/manage_tool_catalog.py`** - CLI tool for catalog management

### 4. Features

- **Declarative Configuration** - All tools defined in YAML
- **Schema Validation** - Pydantic models ensure correctness
- **Uniqueness Checking** - Prevents duplicate tool names
- **Module Discovery** - Auto-discovers available Ansible modules
- **Category Organization** - Logical grouping of related tools
- **Destructive Marking** - Flags dangerous operations

## 📁 File Structure

```
catalyst_center_iac_mcp/
├── tool_catalog.yaml                    # Master tool catalog
├── tool_registry.py                     # YAML loader and validator
├── server.py                            # Uses YAML catalog for registration
├── config/
│   ├── README.md                        # This file
│   ├── TOOL_CATALOG_GUIDE.md           # Comprehensive usage guide
│   ├── tools/                           # Future: split catalog by category
│   │   ├── specialized/
│   │   └── generic/
│   └── schemas/
│       └── tool_catalog.schema.yaml    # JSON Schema for validation
└── scripts/
    └── manage_tool_catalog.py          # CLI management tool
```

## 🚀 Quick Start

### View All Tools

```bash
python3 scripts/manage_tool_catalog.py list
```

### Validate Catalog

```bash
python3 scripts/manage_tool_catalog.py validate
```

### Check Module Availability

```bash
python3 scripts/manage_tool_catalog.py check
```

### Generate Documentation

```bash
python3 scripts/manage_tool_catalog.py docs --output TOOLS.md
```

## 📝 Adding a New Tool

### Option 1: Add a Direct Tool (Specialized)

1. **Create handler function** in `server.py`:

```python
DIRECT_TOOL_HANDLERS = {
    "your_new_tool": _your_new_tool_handler,
}

async def _your_new_tool_handler(
    param1: str,
    param2: int,
    state: WorkflowState = WorkflowState.MERGED,
    tenant_id: str = "default",
    ctx: Context | None = None,
) -> dict[str, Any]:
    config = build_your_config(param1, param2)
    return (await _submit(...)).model_dump()
```

2. **Create transformer** in `transformers.py`:

```python
def build_your_config(param1: str, param2: int) -> list[dict[str, Any]]:
    config = _compact({"param1": param1, "param2": param2})
    return [{"your_config_key": [config]}]
```

3. **Add to catalog** (`tool_catalog.yaml`):

```yaml
direct_tools:
  your_category:
    - handler: your_new_tool
      module_name: your_workflow_manager
      description: |
        What your tool does.
      destructive: false
```

4. **Restart server** - tool is automatically registered!

### Option 2: Add a Workflow Tool (Generic)

Simply add to `tool_catalog.yaml`:

```yaml
workflow_tools:
  configuration_creation:
    your_category:
      - module_name: your_new_workflow_manager
        description: "Optional custom description"
        destructive: false
```

The tool will be auto-registered as `run_your_new_workflow_manager`.

### Option 3: Add a Config Generator (Read-Only)

```yaml
workflow_tools:
  configuration_generation:
    your_category:
      - module_name: your_new_playbook_config_generator
```

The tool will be auto-registered as `generate_your_new_config`.

## 🎯 Current Tool Count

As of the latest update:

- **9 Direct Tools** (specialized)
- **39 Workflow Creation Tools** (generic)
- **30 Configuration Generation Tools** (read-only)
- **78+ Total Tools**

## 🔍 Tool Discovery

The server automatically discovers available modules from the installed `cisco.catalystcenter` collection:

```python
GENERIC_WORKFLOW_MODULES = _discover_collection_modules(
    "cisco.catalystcenter", 
    "_workflow_manager"
)

GENERIC_PLAYBOOK_GENERATOR_MODULES = _discover_collection_modules(
    "cisco.catalystcenter", 
    "_playbook_config_generator"
)
```

If a module listed in the catalog is not found:
- **Workflow tools**: Server raises an error at startup
- **Config generators**: Tool is silently skipped

## 📚 Documentation

### For Users
- **`README.md`** - Main project documentation
- **`TOOLS.md`** - Auto-generated tool reference (run `manage_tool_catalog.py docs`)

### For Developers
- **`config/TOOL_CATALOG_GUIDE.md`** - Complete guide to managing the catalog
- **`config/schemas/tool_catalog.schema.yaml`** - Schema reference
- **`CONTRIBUTING.md`** - Development guidelines

## 🛠️ CLI Tool Reference

### `manage_tool_catalog.py`

```bash
# Validate catalog syntax and schema
python3 scripts/manage_tool_catalog.py validate

# List all tools
python3 scripts/manage_tool_catalog.py list

# List only direct tools
python3 scripts/manage_tool_catalog.py list --category direct

# Check if all modules are installed
python3 scripts/manage_tool_catalog.py check

# Generate markdown documentation
python3 scripts/manage_tool_catalog.py docs --output TOOLS.md
```

## 🔄 Migration Status

### ✅ Completed
- YAML catalog structure designed and implemented
- All workflow managers migrated to YAML
- All config generators migrated to YAML
- All specialized tools migrated to YAML
- Validation and documentation tools created

### 🚧 Future Enhancements
- [ ] Hot reload (update tools without server restart)
- [ ] Parameter schemas in YAML (define param types/validation)
- [ ] Conditional tool registration (feature flags)
- [ ] Version compatibility tracking (min/max collection versions)
- [ ] Tool dependencies (define relationships between tools)
- [ ] Split catalog into multiple files (one per category)

## 📖 Examples

### Example 1: Current tool_catalog.yaml Structure

```yaml
version: 1

direct_tools:
  site_management:
    - handler: provision_site
      module_name: site_workflow_manager
      description: "Create or update sites"
      destructive: false

workflow_tools:
  configuration_creation:
    site_management:
      - module_name: site_workflow_manager
      - module_name: network_settings_workflow_manager
      
  configuration_generation:
    site_management:
      - module_name: site_playbook_config_generator
```

### Example 2: Adding a Compliance Tool

```yaml
direct_tools:
  compliance:
    - handler: run_compliance_check
      module_name: network_compliance_workflow_manager
      description: |
        Run compliance checks on devices.
        Validates device configuration against intent.
      destructive: false
```

## 🎓 Best Practices

1. **Use Direct Tools for Common Workflows** - Better UX for AI agents
2. **Use Workflow Tools for Advanced Use Cases** - Full control over parameters
3. **Provide Clear Descriptions** - Help AI agents understand tool purpose
4. **Mark Destructive Operations** - Triggers approval workflows
5. **Group Related Tools** - Keep categories logical and organized
6. **Validate Before Committing** - Run `manage_tool_catalog.py validate`

## 🐛 Troubleshooting

### Tool Not Showing Up

1. Check YAML syntax: `python3 scripts/manage_tool_catalog.py validate`
2. Check module exists: `ansible-doc cisco.catalystcenter.<module_name>`
3. Check server logs for errors

### Module Not Found

```bash
# Reinstall collection
ansible-galaxy collection install cisco.catalystcenter:==2.6.0 --force
```

### Duplicate Tool Name

Tool names must be unique across all categories. Rename one of the conflicting tools in `tool_catalog.yaml`.

## 📞 Support

For questions or issues:
1. Check `config/TOOL_CATALOG_GUIDE.md` for detailed documentation
2. Run `python3 scripts/manage_tool_catalog.py --help`
3. Review examples in `tool_catalog.yaml`
4. See `CONTRIBUTING.md` for development guidelines

---

**The YAML-based tool registry system is production-ready and actively used by the MCP server!** 🎉

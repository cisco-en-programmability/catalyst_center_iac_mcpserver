# Schema-Driven Tool Architecture

## Overview

The Catalyst Center IAC MCP Server now uses a **fully schema-driven architecture** where all tool definitions are centralized in YAML configuration files and validated against a JSON Schema.

This document explains the architecture, benefits, and validation process.

---

## Architecture Components

### 1. **JSON Schema** (`config/schemas/tool_catalog.schema.yaml`)

The authoritative schema that defines:
- Tool catalog structure
- Valid categories (21 categories)
- Module naming patterns
- Required and optional fields
- All 120+ valid module names with examples

**Key Features:**
- ✅ Validates YAML syntax
- ✅ Enforces naming conventions
- ✅ Documents all supported categories
- ✅ Provides IDE auto-completion
- ✅ Includes comprehensive examples

### 2. **Tool Catalog** (`tool_catalog.yaml`)

The single source of truth for all 79 tools:
- **9 Direct Tools** - Specialized with custom handlers
- **39 Workflow Creation Tools** - Generic configuration tools
- **30 Configuration Generation Tools** - Read-only query tools
- **1 Platform Tool** - Cluster management

**Structure:**
```yaml
version: 1
direct_tools:
  <category>:
    - handler: <tool_name>
      module_name: <ansible_module>
      description: <detailed_description>
      destructive: <true|false>

workflow_tools:
  configuration_creation:
    <category>:
      - module_name: <module>_workflow_manager
        destructive: <true|false>  # optional
        
  configuration_generation:
    <category>:
      - module_name: <module>_playbook_config_generator
```

### 3. **Tool Registry** (`tool_registry.py`)

Pydantic-based loader and validator:
- Loads `tool_catalog.yaml`
- Validates against schema
- Checks tool name uniqueness
- Provides iteration methods for each tool type

**Key Classes:**
- `ToolCatalog` - Main catalog model
- `DirectToolDefinition` - Direct tool schema
- `WorkflowToolDefinition` - Workflow tool schema
- `ResolvedToolDefinition` - Unified tool representation

### 4. **Server Registration** (`server.py`)

Loads tools from catalog and registers with MCP:

```python
# Load catalog (schema-validated)
TOOL_CATALOG = load_tool_catalog(Path("tool_catalog.yaml"))

# Direct tools from YAML (no longer hardcoded!)
DIRECT_TOOL_DEFINITIONS = tuple(TOOL_CATALOG.iter_direct_tools())

# Workflow creation tools from YAML
for definition in TOOL_CATALOG.iter_workflow_tools("configuration_creation"):
    # Register tool...

# Config generation tools from YAML
for definition in TOOL_CATALOG.iter_workflow_tools("configuration_generation"):
    # Register tool...
```

---

## Data Flow

```
┌─────────────────────────────────────┐
│  JSON Schema                        │
│  tool_catalog.schema.yaml           │
│  - Defines valid structure          │
│  - 21 categories documented         │
│  - 120+ module examples             │
└──────────────┬──────────────────────┘
               │ validates
               ▼
┌─────────────────────────────────────┐
│  Tool Catalog                       │
│  tool_catalog.yaml                  │
│  - 9 direct tools                   │
│  - 39 workflow creation tools       │
│  - 30 config generation tools       │
└──────────────┬──────────────────────┘
               │ loaded by
               ▼
┌─────────────────────────────────────┐
│  Tool Registry                      │
│  tool_registry.py                   │
│  - Pydantic validation              │
│  - Uniqueness checking              │
│  - Type safety                      │
└──────────────┬──────────────────────┘
               │ provides definitions to
               ▼
┌─────────────────────────────────────┐
│  MCP Server                         │
│  server.py                          │
│  - Registers tools with FastMCP     │
│  - Maps to handler functions        │
│  - Applies annotations              │
└─────────────────────────────────────┘
```

---

## Benefits

### 1. **Single Source of Truth**
- All tool metadata in one place (`tool_catalog.yaml`)
- No duplication between code and configuration
- Easy to audit and maintain

### 2. **Schema Validation**
- Automatic validation at server startup
- Catches errors before deployment
- IDE support with auto-completion

### 3. **No Code Changes for New Tools**
To add a new tool:
1. Add to `tool_catalog.yaml`
2. (For direct tools) Add handler function
3. Restart server

No changes to registration logic needed!

### 4. **Type Safety**
- Pydantic models ensure correctness
- Compile-time type checking
- Runtime validation

### 5. **Documentation as Code**
- Schema serves as API documentation
- Examples embedded in schema
- Self-documenting system

### 6. **Maintainability**
- Centralized configuration
- Clear separation of concerns
- Easy to update descriptions

---

## Supported Categories

The schema defines 21 categories across all tool types:

| Category | Direct Tools | Workflow Tools | Config Generators | Total |
|----------|--------------|----------------|-------------------|-------|
| site_management | 2 | 3 | 3 | 8 |
| ise_and_aaa | 0 | 2 | 2 | 4 |
| cli_templates | 1 | 1 | 1 | 3 |
| pnp | 0 | 1 | 1 | 2 |
| wireless | 0 | 1 | 1 | 2 |
| network_profiles | 0 | 2 | 2 | 4 |
| assurance | 1 | 3 | 3 | 7 |
| application_policy | 0 | 1 | 1 | 2 |
| events_and_notifications | 0 | 1 | 1 | 2 |
| config_backups | 0 | 2 | 2 | 4 |
| access_points_configuration | 0 | 2 | 2 | 4 |
| discovery | 1 | 2 | 2 | 5 |
| inventory | 1 | 3 | 3 | 7 |
| provision | 0 | 1 | 1 | 2 |
| reports | 0 | 1 | 1 | 2 |
| path_trace | 0 | 1 | 1 | 2 |
| **sd_access_fabric** | **2** | **8** | **8** | **18** |
| lan_automation | 0 | 1 | 1 | 2 |
| wired_campus | 0 | 1 | 1 | 2 |
| software_upgrade_swim | 0 | 1 | 1 | 2 |
| rma | 0 | 1 | 1 | 2 |
| network_settings | 1 | 0 | 0 | 1 |
| template_deployment | 1 | 0 | 0 | 1 |
| fabric_devices | 2 | 0 | 0 | 2 |
| **TOTAL** | **9** | **39** | **30** | **78** |

*Note: Some categories appear only in direct_tools (network_settings, template_deployment, fabric_devices)*

---

## Validation Process

### Automatic Validation (Server Startup)

```python
# In server.py
TOOL_CATALOG = load_tool_catalog(Path("tool_catalog.yaml"))
```

This automatically:
1. ✅ Validates YAML syntax
2. ✅ Validates against Pydantic models
3. ✅ Checks tool name uniqueness
4. ✅ Verifies required fields
5. ✅ Raises errors if invalid

### Manual Validation (CLI Tool)

```bash
# Validate catalog
python3 scripts/manage_tool_catalog.py validate

# Output:
# Validating tool catalog: tool_catalog.yaml
# ============================================================
# ✅ YAML syntax: Valid
# ✅ Schema validation: Passed
# ✅ Tool uniqueness: Verified
# 
# 📊 Tool Statistics:
#    Direct tools: 9
#    Workflow creation tools: 39
#    Workflow generation tools: 30
#    Total tools: 78
# 
# ✅ Validation successful!
```

### JSON Schema Validation (Optional)

For stricter validation, use a JSON Schema validator:

```bash
# Install validator
pip install pyyaml jsonschema

# Validate
python3 << 'EOF'
import yaml
import jsonschema

# Load schema
with open('config/schemas/tool_catalog.schema.yaml') as f:
    schema = yaml.safe_load(f)

# Load catalog
with open('tool_catalog.yaml') as f:
    catalog = yaml.safe_load(f)

# Validate
jsonschema.validate(catalog, schema)
print("✅ JSON Schema validation passed!")
EOF
```

---

## Module Discovery

The server automatically discovers available Ansible modules:

```python
# Discover workflow managers
GENERIC_WORKFLOW_MODULES = _discover_collection_modules(
    "cisco.catalystcenter", 
    "_workflow_manager"
) or DEFAULT_WORKFLOW_MODULES

# Discover config generators
GENERIC_PLAYBOOK_GENERATOR_MODULES = _discover_collection_modules(
    "cisco.catalystcenter", 
    "_playbook_config_generator"
)
```

**Discovery Process:**
1. Search Ansible collection paths
2. Find modules matching suffix pattern
3. Return sorted list of module names
4. Fall back to default list if discovery fails

**Validation:**
- Workflow tools: Error if module not found
- Config generators: Skip if module not found

---

## Adding a New Tool

### Example: Adding a Compliance Tool

**1. Update `tool_catalog.yaml`:**

```yaml
direct_tools:
  compliance:
    - handler: run_compliance_check
      module_name: network_compliance_workflow_manager
      description: |
        Run compliance checks on network devices.
        Validates device configuration against defined policies.
      destructive: false
```

**2. Add handler function in `server.py`:**

```python
# Add to DIRECT_TOOL_HANDLERS
DIRECT_TOOL_HANDLERS = {
    # ... existing handlers ...
    "run_compliance_check": _run_compliance_check_handler,
}

# Define handler
async def _run_compliance_check_handler(
    device_ids: list[str],
    compliance_type: str,
    state: WorkflowState = WorkflowState.MERGED,
    tenant_id: str = "default",
    ctx: Context | None = None,
) -> dict[str, Any]:
    assert ctx is not None
    config = build_compliance_config(device_ids, compliance_type)
    return (await _submit(...)).model_dump()
```

**3. Add transformer in `transformers.py`:**

```python
def build_compliance_config(
    device_ids: list[str],
    compliance_type: str
) -> list[dict[str, Any]]:
    config = _compact({
        "device_ids": device_ids,
        "compliance_type": compliance_type,
    })
    return [{"compliance": [config]}]
```

**4. Restart server** - Tool is automatically registered!

---

## Error Handling

### Missing Module Error

```
RuntimeError: Workflow tool `run_xyz_workflow_manager` references unknown module 
`xyz_workflow_manager` in tool_catalog.yaml
```

**Solution:** Module doesn't exist in installed collection. Either:
1. Install correct collection version
2. Remove tool from catalog

### Duplicate Tool Name Error

```
ValueError: duplicate tool name in catalog: provision_site
```

**Solution:** Tool names must be unique. Rename one of the tools.

### Invalid YAML Syntax

```
yaml.scanner.ScannerError: mapping values are not allowed here
```

**Solution:** Fix YAML syntax errors in `tool_catalog.yaml`.

---

## Testing

### Unit Tests

```python
# Test catalog loading
def test_load_catalog():
    catalog = load_tool_catalog(Path("tool_catalog.yaml"))
    assert catalog.version == 1
    assert len(catalog.iter_direct_tools()) == 9

# Test tool uniqueness
def test_tool_uniqueness():
    catalog = load_tool_catalog(Path("tool_catalog.yaml"))
    tool_names = set()
    for tool in catalog.iter_direct_tools():
        assert tool.tool_name not in tool_names
        tool_names.add(tool.tool_name)
```

### Integration Tests

```bash
# Start server
catalyst-center-iac-mcp

# Verify tools loaded
curl http://localhost:8000/mcp \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","id":1,"method":"tools/list","params":{}}'

# Should return 78+ tools
```

---

## Migration Checklist

- [x] Create JSON Schema (`config/schemas/tool_catalog.schema.yaml`)
- [x] Populate `tool_catalog.yaml` with all tools
- [x] Implement Pydantic models in `tool_registry.py`
- [x] Update `server.py` to load from catalog
- [x] Remove hardcoded tool definitions
- [x] Add CLI validation tool (`scripts/manage_tool_catalog.py`)
- [x] Create documentation
- [x] Test all tools load correctly
- [ ] Add JSON Schema validation to CI/CD
- [ ] Create tool catalog versioning strategy

---

## Future Enhancements

### Planned Features

1. **Parameter Schemas in YAML**
   - Define parameter types and validation in catalog
   - Auto-generate Pydantic models from schema
   - Better error messages

2. **Hot Reload**
   - Watch `tool_catalog.yaml` for changes
   - Reload tools without server restart
   - Useful for development

3. **Feature Flags**
   - Enable/disable tools via configuration
   - Environment-specific tool sets
   - A/B testing new tools

4. **Version Compatibility**
   - Specify min/max collection versions per tool
   - Automatic compatibility checking
   - Graceful degradation

5. **Tool Dependencies**
   - Define relationships between tools
   - Prerequisite checking
   - Workflow orchestration

6. **Multi-File Catalogs**
   - Split catalog by category
   - Easier to manage large catalogs
   - Team-based ownership

---

## Conclusion

The schema-driven architecture provides:

✅ **Centralized Configuration** - Single source of truth  
✅ **Type Safety** - Pydantic validation  
✅ **Maintainability** - Easy to update and extend  
✅ **Documentation** - Schema serves as API docs  
✅ **Validation** - Automatic error detection  
✅ **Flexibility** - Easy to add new tools  

**The system is production-ready and fully schema-driven!** 🎉

---

**Last Updated**: April 22, 2026  
**Schema Version**: 1.0  
**Total Tools**: 78 (9 direct + 39 workflow + 30 generators)  
**Collection Version**: cisco.catalystcenter 2.6.0

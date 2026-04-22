#!/usr/bin/env python3
"""
Tool Catalog Management CLI

This script provides utilities for managing the tool_catalog.yaml file:
- Validate YAML syntax and schema
- List all registered tools
- Check for missing modules
- Generate tool documentation
- Add new tools interactively
"""

import sys
from pathlib import Path
from typing import Any

import yaml

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from tool_registry import load_tool_catalog, ResolvedToolDefinition


def validate_catalog(catalog_path: Path) -> bool:
    """Validate the tool catalog YAML file."""
    print(f"Validating tool catalog: {catalog_path}")
    print("=" * 60)
    
    try:
        # Load and validate
        catalog = load_tool_catalog(catalog_path)
        
        # Count tools
        direct_tools = catalog.iter_direct_tools()
        creation_tools = catalog.iter_workflow_tools("configuration_creation")
        generation_tools = catalog.iter_workflow_tools("configuration_generation")
        
        print(f"✅ YAML syntax: Valid")
        print(f"✅ Schema validation: Passed")
        print(f"✅ Tool uniqueness: Verified")
        print()
        print(f"📊 Tool Statistics:")
        print(f"   Direct tools: {len(direct_tools)}")
        print(f"   Workflow creation tools: {len(creation_tools)}")
        print(f"   Workflow generation tools: {len(generation_tools)}")
        print(f"   Total tools: {len(direct_tools) + len(creation_tools) + len(generation_tools)}")
        print()
        print("✅ Validation successful!")
        return True
        
    except yaml.YAMLError as e:
        print(f"❌ YAML syntax error: {e}")
        return False
    except ValueError as e:
        print(f"❌ Validation error: {e}")
        return False
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return False


def list_tools(catalog_path: Path, category: str | None = None) -> None:
    """List all tools in the catalog."""
    catalog = load_tool_catalog(catalog_path)
    
    print("Tool Catalog Listing")
    print("=" * 80)
    
    # Direct tools
    direct_tools = catalog.iter_direct_tools()
    if not category or category == "direct":
        print("\n📌 DIRECT TOOLS (Specialized)")
        print("-" * 80)
        
        by_subcategory: dict[str, list[ResolvedToolDefinition]] = {}
        for tool in direct_tools:
            by_subcategory.setdefault(tool.subcategory, []).append(tool)
            
        for subcategory, tools in sorted(by_subcategory.items()):
            print(f"\n  {subcategory}:")
            for tool in tools:
                destructive_marker = " 🔴 DESTRUCTIVE" if tool.destructive else ""
                print(f"    • {tool.tool_name}{destructive_marker}")
                print(f"      Module: {tool.module_name}")
                if tool.description:
                    desc_lines = tool.description.strip().split('\n')
                    print(f"      Description: {desc_lines[0][:60]}...")
    
    # Workflow creation tools
    creation_tools = catalog.iter_workflow_tools("configuration_creation")
    if not category or category == "creation":
        print("\n\n🔧 WORKFLOW TOOLS (Configuration Creation)")
        print("-" * 80)
        
        by_subcategory = {}
        for tool in creation_tools:
            by_subcategory.setdefault(tool.subcategory, []).append(tool)
            
        for subcategory, tools in sorted(by_subcategory.items()):
            print(f"\n  {subcategory}:")
            for tool in tools:
                destructive_marker = " 🔴 DESTRUCTIVE" if tool.destructive else ""
                print(f"    • {tool.tool_name}{destructive_marker}")
                print(f"      Module: {tool.module_name}")
    
    # Workflow generation tools
    generation_tools = catalog.iter_workflow_tools("configuration_generation")
    if not category or category == "generation":
        print("\n\n📖 WORKFLOW TOOLS (Configuration Generation - Read-Only)")
        print("-" * 80)
        
        by_subcategory = {}
        for tool in generation_tools:
            by_subcategory.setdefault(tool.subcategory, []).append(tool)
            
        for subcategory, tools in sorted(by_subcategory.items()):
            print(f"\n  {subcategory}:")
            for tool in tools:
                print(f"    • {tool.tool_name}")
                print(f"      Module: {tool.module_name}")
    
    print("\n" + "=" * 80)
    print(f"Total: {len(direct_tools)} direct + {len(creation_tools)} creation + {len(generation_tools)} generation")


def check_modules(catalog_path: Path) -> None:
    """Check if all referenced modules exist in the installed collection."""
    import subprocess
    
    print("Checking module availability...")
    print("=" * 60)
    
    catalog = load_tool_catalog(catalog_path)
    
    # Get all module names
    all_tools = (
        catalog.iter_direct_tools() +
        catalog.iter_workflow_tools("configuration_creation") +
        catalog.iter_workflow_tools("configuration_generation")
    )
    
    modules = {tool.module_name for tool in all_tools}
    
    print(f"Checking {len(modules)} unique modules...\n")
    
    missing = []
    found = []
    
    for module in sorted(modules):
        full_name = f"cisco.catalystcenter.{module}"
        try:
            result = subprocess.run(
                ["ansible-doc", full_name],
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode == 0:
                found.append(module)
                print(f"  ✅ {module}")
            else:
                missing.append(module)
                print(f"  ❌ {module} - NOT FOUND")
        except Exception as e:
            missing.append(module)
            print(f"  ❌ {module} - ERROR: {e}")
    
    print()
    print("=" * 60)
    print(f"Found: {len(found)}/{len(modules)}")
    
    if missing:
        print(f"\n⚠️  Missing modules ({len(missing)}):")
        for module in missing:
            print(f"  - {module}")
        print("\nTo install the collection:")
        print("  ansible-galaxy collection install cisco.catalystcenter:==2.6.0 --force")
    else:
        print("✅ All modules are available!")


def generate_docs(catalog_path: Path, output_path: Path) -> None:
    """Generate markdown documentation for all tools."""
    catalog = load_tool_catalog(catalog_path)
    
    with open(output_path, 'w') as f:
        f.write("# Catalyst Center IAC MCP Tools\n\n")
        f.write("Auto-generated tool documentation from tool_catalog.yaml\n\n")
        f.write("---\n\n")
        
        # Direct tools
        f.write("## Direct Tools (Specialized)\n\n")
        f.write("These tools provide simplified interfaces for common workflows.\n\n")
        
        direct_tools = catalog.iter_direct_tools()
        by_subcategory: dict[str, list[ResolvedToolDefinition]] = {}
        for tool in direct_tools:
            by_subcategory.setdefault(tool.subcategory, []).append(tool)
            
        for subcategory, tools in sorted(by_subcategory.items()):
            f.write(f"### {subcategory.replace('_', ' ').title()}\n\n")
            for tool in tools:
                f.write(f"#### `{tool.tool_name}`\n\n")
                if tool.description:
                    f.write(f"{tool.description.strip()}\n\n")
                f.write(f"- **Module**: `{tool.module_name}`\n")
                f.write(f"- **Destructive**: {'Yes ⚠️' if tool.destructive else 'No'}\n")
                f.write(f"- **Read-Only**: {'Yes' if tool.read_only else 'No'}\n\n")
        
        # Workflow creation tools
        f.write("\n---\n\n")
        f.write("## Workflow Tools (Configuration Creation)\n\n")
        f.write("These tools accept raw JSON configuration and create/modify Catalyst Center settings.\n\n")
        
        creation_tools = catalog.iter_workflow_tools("configuration_creation")
        by_subcategory = {}
        for tool in creation_tools:
            by_subcategory.setdefault(tool.subcategory, []).append(tool)
            
        for subcategory, tools in sorted(by_subcategory.items()):
            f.write(f"### {subcategory.replace('_', ' ').title()}\n\n")
            for tool in tools:
                f.write(f"- **`{tool.tool_name}`**\n")
                f.write(f"  - Module: `{tool.module_name}`\n")
                if tool.destructive:
                    f.write(f"  - ⚠️ **Destructive operation**\n")
                f.write("\n")
        
        # Workflow generation tools
        f.write("\n---\n\n")
        f.write("## Workflow Tools (Configuration Generation)\n\n")
        f.write("These are read-only tools that query current configuration without making changes.\n\n")
        
        generation_tools = catalog.iter_workflow_tools("configuration_generation")
        by_subcategory = {}
        for tool in generation_tools:
            by_subcategory.setdefault(tool.subcategory, []).append(tool)
            
        for subcategory, tools in sorted(by_subcategory.items()):
            f.write(f"### {subcategory.replace('_', ' ').title()}\n\n")
            for tool in tools:
                f.write(f"- **`{tool.tool_name}`** - `{tool.module_name}`\n")
        
        f.write("\n---\n\n")
        f.write(f"**Total Tools**: {len(direct_tools)} direct + {len(creation_tools)} creation + {len(generation_tools)} generation\n")
    
    print(f"✅ Documentation generated: {output_path}")


def main():
    """Main CLI entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Manage the Catalyst Center IAC MCP tool catalog"
    )
    parser.add_argument(
        "--catalog",
        type=Path,
        default=Path(__file__).parent.parent / "tool_catalog.yaml",
        help="Path to tool_catalog.yaml"
    )
    
    subparsers = parser.add_subparsers(dest="command", help="Command to run")
    
    # Validate command
    subparsers.add_parser("validate", help="Validate the tool catalog")
    
    # List command
    list_parser = subparsers.add_parser("list", help="List all tools")
    list_parser.add_argument(
        "--category",
        choices=["direct", "creation", "generation"],
        help="Filter by category"
    )
    
    # Check command
    subparsers.add_parser("check", help="Check module availability")
    
    # Docs command
    docs_parser = subparsers.add_parser("docs", help="Generate documentation")
    docs_parser.add_argument(
        "--output",
        type=Path,
        default=Path("TOOLS.md"),
        help="Output file path"
    )
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
    
    if not args.catalog.exists():
        print(f"❌ Tool catalog not found: {args.catalog}")
        sys.exit(1)
    
    if args.command == "validate":
        success = validate_catalog(args.catalog)
        sys.exit(0 if success else 1)
        
    elif args.command == "list":
        list_tools(args.catalog, args.category)
        
    elif args.command == "check":
        check_modules(args.catalog)
        
    elif args.command == "docs":
        generate_docs(args.catalog, args.output)


if __name__ == "__main__":
    main()

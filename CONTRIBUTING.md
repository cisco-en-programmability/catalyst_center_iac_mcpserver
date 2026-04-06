# Contributing to Catalyst Center IAC MCP Server

Thank you for your interest in contributing! This document provides guidelines and instructions for contributing to the project.

## Table of Contents

- [Code of Conduct](#code-of-conduct)
- [Getting Started](#getting-started)
- [Development Setup](#development-setup)
- [Making Changes](#making-changes)
- [Testing](#testing)
- [Submitting Changes](#submitting-changes)
- [Adding New Tools](#adding-new-tools)
- [Code Style](#code-style)

## Code of Conduct

This project follows the Ansible project's [Code of Conduct](https://docs.ansible.com/ansible/devel/community/code_of_conduct.html). By participating, you are expected to uphold this code.

## Getting Started

1. **Fork the repository** on GitHub
2. **Clone your fork** locally:
   ```bash
   git clone https://github.com/YOUR_USERNAME/catalyst_center_iac_mcp.git
   cd catalyst_center_iac_mcp
   ```
3. **Add upstream remote**:
   ```bash
   git remote add upstream https://github.com/cisco-en-programmability/catalyst_center_iac_mcp.git
   ```

## Development Setup

### Prerequisites

- Python 3.11 or higher
- Redis server (for testing)
- Ansible collection: `cisco.catalystcenter`

### Install Dependencies

```bash
# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install package with dev dependencies
pip install -e ".[dev]"

# Install Ansible collection
ansible-galaxy collection install cisco.catalystcenter
```

### Environment Configuration

Create a `.env` file for local development:

```bash
REDIS_URL=redis://localhost:6379/0
CATALYSTCENTER_HOST=your-test-instance.example.com
CATALYSTCENTER_USERNAME=test-user
CATALYSTCENTER_PASSWORD=test-password
CATALYSTCENTER_VERIFY_SSL=false
RUNNER_ARTIFACT_ROOT=/tmp/catalyst-mcp-artifacts
```

## Making Changes

### Branch Naming

Use descriptive branch names:
- `feature/add-wireless-tool` - New features
- `fix/template-deployment-bug` - Bug fixes
- `docs/update-readme` - Documentation updates
- `test/add-discovery-tests` - Test additions

### Commit Messages

Follow conventional commit format:

```
type(scope): brief description

Detailed explanation of the change (optional)

Fixes #123
```

Types:
- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation changes
- `test`: Test additions or modifications
- `refactor`: Code refactoring
- `chore`: Maintenance tasks

Examples:
```
feat(tools): add wireless controller configuration tool

Add specialized tool for configuring wireless controllers with
simplified parameter interface.

Fixes #45
```

## Testing

### Run All Tests

```bash
pytest
```

### Run Specific Test File

```bash
pytest tests/test_transformers.py
```

### Run with Coverage

```bash
pytest --cov=. --cov-report=html
open htmlcov/index.html
```

### Test Requirements

- All new features must include tests
- Maintain or improve code coverage
- Tests should be isolated and repeatable
- Use fixtures for common test data

## Submitting Changes

### Before Submitting

1. **Update from upstream**:
   ```bash
   git fetch upstream
   git rebase upstream/main
   ```

2. **Run tests**:
   ```bash
   pytest
   ```

3. **Check code style**:
   ```bash
   # Format with black (if available)
   black .
   
   # Check types with mypy (if available)
   mypy .
   ```

### Pull Request Process

1. **Push to your fork**:
   ```bash
   git push origin feature/your-feature-name
   ```

2. **Create Pull Request** on GitHub with:
   - Clear title describing the change
   - Detailed description of what and why
   - Reference to related issues
   - Screenshots/examples if applicable

3. **PR Checklist**:
   - [ ] Tests added/updated
   - [ ] Documentation updated
   - [ ] CHANGELOG.md updated (if applicable)
   - [ ] All tests passing
   - [ ] No merge conflicts

4. **Review Process**:
   - Maintainers will review your PR
   - Address feedback and update PR
   - Once approved, maintainers will merge

## Adding New Tools

### Adding a Specialized Tool

1. **Define Model** in `models.py`:
   ```python
   class NewFeatureRequest(BaseModel):
       param1: str
       param2: int
       optional_param: str | None = None
   ```

2. **Create Transformer** in `transformers.py`:
   ```python
   def build_new_feature_workflow_config(
       request: NewFeatureRequest,
   ) -> list[dict[str, Any]]:
       config = _compact({
           "param1": request.param1,
           "param2": request.param2,
           "optional_param": request.optional_param,
       })
       return [{"new_feature": [config]}]
   ```

3. **Add Tool** in `server.py`:
   ```python
   @mcp.tool(
       name="new_feature_tool",
       description="Description of what this tool does",
       annotations=_tool_annotations(),
   )
   async def new_feature_tool(
       param1: str,
       param2: int,
       optional_param: str | None = None,
       tenant_id: str = "default",
       ctx: Context | None = None,
   ) -> dict[str, Any]:
       assert ctx is not None
       request = NewFeatureRequest(
           param1=param1,
           param2=param2,
           optional_param=optional_param,
       )
       return (await _submit(
           ctx=ctx,
           tool_name="new_feature_tool",
           module_name="new_feature_workflow_manager",
           tenant_id=tenant_id,
           state=WorkflowState.MERGED,
           config=build_new_feature_workflow_config(request),
       )).model_dump()
   ```

4. **Add Tests** in `tests/test_transformers.py`:
   ```python
   def test_build_new_feature_workflow_config():
       request = NewFeatureRequest(
           param1="value1",
           param2=42,
       )
       config = build_new_feature_workflow_config(request)
       assert config == [{"new_feature": [{"param1": "value1", "param2": 42}]}]
   ```

5. **Add Example** in `examples/`:
   ```python
   # examples/new_feature_example.py
   # Complete working example
   ```

6. **Update Documentation**:
   - Add to README.md specialized tools list
   - Update SLIDES.md if significant
   - Add usage example

### Adding a Generic Workflow Manager

If a new workflow manager is added to `cisco.catalystcenter` collection:

1. Prefer automatic discovery from the installed `cisco.catalystcenter` collection.
   If the module family is not discoverable in your environment, update the fallback
   module tuples in `server.py`.
2. Add to README.md generic tools list
3. If destructive, add to `destructive_module_hints` set

## Code Style

### Python Style

- Follow PEP 8
- Use type hints for all functions
- Maximum line length: 100 characters
- Use `black` for formatting (if available)
- Use `isort` for import sorting (if available)

### Documentation Style

- Use docstrings for all public functions/classes
- Follow Google docstring format
- Include examples in docstrings where helpful

Example:
```python
def build_config(request: Request) -> list[dict[str, Any]]:
    """Build workflow configuration from request.
    
    Args:
        request: The request object containing parameters
        
    Returns:
        List of configuration dictionaries for the workflow manager
        
    Example:
        >>> request = Request(name="test", value=42)
        >>> config = build_config(request)
        >>> print(config)
        [{"name": "test", "value": 42}]
    """
    return [{"name": request.name, "value": request.value}]
```

### File Organization

```
catalyst_center_iac_mcp/
├── server.py           # FastMCP/FastAPI server and tool definitions
├── models.py           # Pydantic models and enums
├── transformers.py     # Config transformation functions
├── runner_engine.py    # ansible-runner integration
├── redis_store.py      # Redis persistence layer
├── settings.py         # Configuration and settings
├── tests/              # Test files
│   ├── test_server_contract.py
│   ├── test_transformers.py
│   └── test_runner_engine.py
├── examples/           # Usage examples
└── docs/              # Additional documentation
```

## Documentation

### README Updates

When adding features, update:
- Features list
- Available Tools section
- Configuration section (if new env vars)
- Usage Examples (if applicable)

### Example Updates

- Keep examples working and tested
- Use realistic scenarios
- Include error handling
- Add comments explaining key steps

## Questions?

- Open an issue for questions
- Join Cisco DevNet community
- Check existing issues and PRs

## License

By contributing, you agree that your contributions will be licensed under the Cisco Sample Code License.

# Contributing to macOS-MCP

We appreciate your interest in contributing to macOS-MCP! This guide provides standards and procedures for contributing to the project.

## Prerequisites

Before contributing, please ensure you have:

- **macOS**: macOS 12 (Monterey) or later
- **Python**: Python 3.11 or later
- **UV Package Manager**: Install with `curl -LsSf https://astral.sh/uv/install.sh | sh` or `pip install uv`
- **Git**: For version control
- **GitHub Account**: For submitting pull requests

## Development Standards

### Code Style

We use **Ruff** for code formatting and linting to maintain consistency.

**Formatting Rules:**
- **Line length**: 100 characters maximum
- **String quotes**: Use double quotes for strings
- **Naming conventions**:
  - Functions: `snake_case`
  - Classes: `PascalCase`
  - Constants: `UPPER_CASE`
  - Private methods/attributes: Leading underscore (`_method_name`)

### Documentation Requirements

All public functions and classes must include **Google-style docstrings** with proper type hints.

**Example:**
```python
def click(self, x: int, y: int, button: str = "left") -> bool:
    """Click at the specified coordinates.
    
    Args:
        x: X coordinate of the click position
        y: Y coordinate of the click position
        button: Mouse button to click ("left", "right", or "center")
    
    Returns:
        True if click was successful, False otherwise
    
    Raises:
        ValueError: If button type is not recognized
    """
```

## Contribution Workflow

### 1. Fork and Branch

1. Fork the repository on GitHub
2. Clone your fork: `git clone https://github.com/<your-username>/macos-mcp.git`
3. Create a feature branch with a descriptive name:
   - `feature/` for new features
   - `fix/` for bug fixes
   - `docs/` for documentation
   - `refactor/` for code refactoring

   Example: `git checkout -b feature/add-audio-control`

### 2. Make Changes

- Keep changes focused and atomic
- Ensure code follows the style guidelines
- Add or update docstrings for modified functions
- Update tests for new or modified functionality

### 3. Testing

Before submitting a pull request, verify that:

- ✓ All tests pass: `pytest`
- ✓ Code follows style guidelines: `ruff check .`
- ✓ Code is properly formatted: `ruff format .`
- ✓ New features have unit and integration tests
- ✓ Edge cases are covered

### 4. Commit Messages

Write clear and informative commit messages:

- Use present tense: "Add feature" not "Added feature"
- Be specific: "Fix AXValue error in tree traversal" not "Fix bug"
- Reference issues: "Fix #123: ..." when applicable

### 5. Create a Pull Request

1. Push your branch to your fork
2. Create a pull request to the main branch
3. Provide a clear description of changes
4. Reference any related issues
5. Ensure all CI checks pass

## Quality Assurance Checklist

Before submitting your PR, verify:

- [ ] Code follows project style guidelines (Ruff)
- [ ] All tests pass locally
- [ ] New features include corresponding tests
- [ ] Docstrings are added/updated for public APIs
- [ ] No breaking changes (or clearly documented if necessary)
- [ ] Commit messages are clear and informative
- [ ] Changes are focused and atomic

## Testing

### Running Tests

```bash
# Run all tests
pytest

# Run specific test file
pytest tests/test_desktop.py

# Run with coverage
pytest --cov=src/macos_mcp tests/
```

### Writing Tests

- Use descriptive test function names: `test_click_success_valid_coordinates`
- Test both success and failure cases
- Use fixtures for common setup
- Mock external dependencies appropriately
- Include docstrings explaining test purpose

## Code Review Process

All pull requests go through review:

1. At least one maintainer review required
2. All CI checks must pass
3. Discussions are constructive and focused on code quality
4. Once approved, maintainers will merge the PR

## Support and Questions

For questions or discussions:

- **GitHub Discussions**: Use for general questions and ideas
- **GitHub Issues**: Report bugs or request features
- **Email**: jeogeoalukka@gmail.com for non-public matters

## Recognition

Contributors are recognized in:
- Release notes for significant contributions
- GitHub contributors page
- Project acknowledgements

## License

All contributions are submitted under the MIT License. By submitting a pull request, you agree that your work will be licensed under the MIT License.

## Code of Conduct

We are committed to providing a welcoming and inclusive environment. Please be respectful of other contributors and maintain professional communication in all interactions.

---

Thank you for contributing to macOS-MCP! 🎉

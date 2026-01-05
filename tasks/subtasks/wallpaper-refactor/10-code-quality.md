# 10. Code Quality

meta:
  id: wallpaper-refactor-10
  feature: wallpaper-refactor
  priority: P3
  depends_on: [all previous]
  tags: [linting, formatting]

objective:
- Configure automated code quality tools (ruff for linting, black for formatting) to maintain code consistency and catch common issues.

deliverables:
- pyproject.toml configuration for ruff and black
- .pre-commit-config.yaml (optional)
- Zero linting errors
- Consistent code formatting

steps:
1. Add code quality tools to pyproject.toml:
   ```toml
   [project.optional-dependencies]
   dev = [
       "black>=23.0.0",
       "ruff>=0.1.0",
   ]
   ```

2. Configure black in pyproject.toml:
   ```toml
   [tool.black]
   line-length = 100
   target-version = ["py311", "py312"]
   include = '\.pyi?$'
   exclude = '''
   /(
       \.git
     | \.venv
     | \.mypy_cache
     | build
     | dist
   )/
   '''
   ```

3. Configure ruff in pyproject.toml:
   ```toml
   [tool.ruff]
   target-version = "py311"
   line-length = 100
   select = [
       "E",   # pycodestyle errors
       "W",   # pycodestyle warnings
       "F",   # Pyflakes
       "I",   # isort
       "B",   # flake8-bugbear
       "C4",  # flake8-comprehensions
       "UP",  # pyupgrade
       "ARG", # flake8-unused-arguments
       "SIM", # flake8-simplify
   ]
   ignore = [
       "E501",  # Line too long (handled by black)
       "B008",  # Do not perform function calls in argument defaults
       "C901",  # Too complex
   ]

   [tool.ruff.per-file-ignores]
   "__init__.py" = ["F401"]  # Unused imports

   [tool.ruff.isort]
   known-first-party = ["wallpicker"]
   ```

4. Format code with black:
   ```bash
   # Install black
   pip install black

   # Format all code
   black src/ tests/

   # Check if formatting needed (CI-friendly)
   black --check src/ tests/

   # Format specific file
   black src/services/wallhaven_service.py
   ```

5. Run ruff for linting:
   ```bash
   # Install ruff
   pip install ruff

   # Check for issues
   ruff check src/ tests/

   # Auto-fix issues
   ruff check --fix src/ tests/

   # Explain a rule
   ruff rule B950
   ```

6. Add pre-commit configuration (optional):
   ```yaml
   # .pre-commit-config.yaml
   repos:
     - repo: https://github.com/psf/black
       rev: 23.12.0
       hooks:
         - id: black
           language_version: python3.11

     - repo: https://github.com/astral-sh/ruff-pre-commit
       rev: v0.1.8
       hooks:
         - id: ruff
           args: [--fix, --exit-non-zero-on-fix]
   ```

7. Fix common issues:
   ```bash
   # Run ruff and see issues
   ruff check src/ tests/

   # Fix auto-fixable issues
   ruff check --fix src/ tests/

   # Common issues to fix manually:
   # - F401: Remove unused imports
   # - F841: Remove unused variables
   # - ARG001: Remove unused arguments
   # - B006: Don't use mutable default arguments
   ```

8. Format existing code:
   ```python
   # Before:
   def __init__(self,api_key=None):
       self.api_key=api_key

   # After (black formatted):
   def __init__(self, api_key=None):
       self.api_key = api_key

   # Before:
   x=1;y=2;z=3

   # After:
   x = 1
   y = 2
   z = 3
   ```

9. Add formatting checks to CI (if applicable):
   ```yaml
   # .github/workflows/ci.yml
   - name: Check formatting
     run: |
       black --check src/ tests/
       ruff check src/ tests/
   ```

10. Document code style conventions:
    ```markdown
    # CODE STYLE

    ## Formatting
    - Use black for formatting (line length: 100)
    - Target Python version: 3.11+

    ## Linting
    - Use ruff for linting
    - Fix all auto-fixable issues
    - Manual fixes for: unused imports, unused variables, mutable defaults

    ## Imports
    - Group imports: stdlib, third-party, local
    - Use isort (via ruff)
    - Known first-party: wallpicker

    ## Type Hints
    - All functions must have type hints
    - Use Optional[T] for nullable values
    - Use TypeAlias for complex types
    ```

tests:
- Unit: Code formatting check
- Unit: Linting check
- Integration: Pre-commit hooks work

acceptance_criteria:
- black configured in pyproject.toml
- ruff configured in pyproject.toml
- All code formatted with black
- ruff reports 0 errors
- No unused imports or variables
- Consistent code style across project
- Pre-commit hooks configured (optional)

validation:
- Commands to verify:
  ```bash
  black --check src/ tests/  # Should pass
  ruff check src/ tests/  # Should pass
  black --version
  ruff --version
  ```
- Run: black --diff src/ to see formatting changes
- Run: ruff check src/ tests/ --statistics

notes:
- black: opinionated formatter (enforces style)
- ruff: fast linter (10x faster than flake8)
- Use ruff instead of flake8, isort, pyupgrade
- Line length: 100 (reasonable balance)
- Black is strict: accept its style
- Ruff has auto-fix for many issues
- Pre-commit hooks: enforce code quality before commit
- CI: check formatting/linting in CI/CD
- VS Code extension: ruff, black formatter

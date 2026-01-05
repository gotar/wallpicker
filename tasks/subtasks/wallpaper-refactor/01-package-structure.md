# 01. Package Structure

meta:
  id: wallpaper-refactor-01
  feature: wallpaper-refactor
  priority: P0
  depends_on: []
  tags: [packaging, foundation]

objective:
- Establish modern Python packaging with pyproject.toml while preserving flat src/ structure and dual installation support.

deliverables:
- pyproject.toml with build system, dependencies, and project metadata
- Update PKGBUILD to use pyproject.toml for dependencies
- Update requirements.txt (keep for backward compatibility with install.sh)
- src/__init__.py (minimal, to support proper imports)
- Launcher script updates to work with new structure

steps:
1. Create pyproject.toml with:
   - Build system: setuptools with pyproject.toml backend
   - Project metadata (name, version, description)
   - Python version requirement (3.11+)
   - Dependencies: requests, Pillow, PyGObject, send2trash, aiohttp, rapidfuzz
   - Optional dev dependencies: pytest, pytest-asyncio, pytest-mock, pytest-cov, mypy, ruff, black, structlog
   - Entry points: wallpicker = src.ui.main_window:main

2. Create minimal src/__init__.py:
   ```python
   """Wallpicker - Modern wallpaper picker application."""
   __version__ = "0.1.0"
   ```
   - This enables proper Python package imports while keeping flat structure
   - Services remain at src.services.* (services/__init__.py optional)

3. Update PKGBUILD:
   - Remove dependency list (now in pyproject.toml)
   - Use `python -m build` to build from pyproject.toml
   - Keep makedepends: python-build, python-installer, python-wheel

4. Update requirements.txt:
   - Keep as reference for install.sh
   - Sync with pyproject.toml dependencies

5. Verify installation:
   - Test: `python -m pip install -e .` (development install)
   - Test: `python -m build` (package build)
   - Test: `wallpicker --version` (command works)

tests:
- Unit: Test imports work correctly from installed package
- Integration: Test that wallpicker command launches from installation
- E2E: Test install.sh and PKGBUILD both produce working installation

acceptance_criteria:
- pyproject.toml exists with complete metadata and dependencies
- `python -m pip install -e .` succeeds
- `wallpicker` command launches application
- Existing install.sh still works
- PKGBUILD builds and installs successfully
- All imports work: `from wallpicker.services.wallhaven_service import WallhavenService`
- Flat src/ structure preserved (no nested src/wallpicker package)

validation:
- Commands to verify:
  ```bash
  python -m pip install -e .
  python -c "from wallpicker.services.wallhaven_service import WallhavenService; print('OK')"
  python -m build
  ```
- Check: install.sh completes without errors
- Check: makepkg -si (on Arch) completes without errors

notes:
- Preserve anti-pattern: Do NOT create nested src/wallpicker/ package
- Keep sys.path manipulation in entry points (launcher.py, main.py) until later refactor
- pyproject.toml is the single source of truth for dependencies
- requirements.txt remains for backward compatibility with install.sh

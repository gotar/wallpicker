# 08. Type Safety

meta:
  id: wallpaper-refactor-08
  feature: wallpaper-refactor
  priority: P2
  depends_on: [01, 02, 03, 04]
  tags: [type-hints, mypy]

objective:
- Add comprehensive type hints to the codebase and enable mypy for static type checking, catching type errors before runtime.

deliverables:
- Type hints on all functions and methods
- Type stub files for third-party libraries if needed
- mypy.ini configuration
- Zero type errors reported by mypy

steps:
1. Add mypy to pyproject.toml:
   ```toml
   [project.optional-dependencies]
   dev = [
       "mypy>=1.5.0",
       "types-aiofiles",
       "types-requests",
   ]
   ```

2. Create mypy.ini:
   ```ini
   [mypy]
   python_version = 3.11
   warn_return_any = True
   warn_unused_configs = True
   disallow_untyped_defs = True
   disallow_incomplete_defs = True
   check_untyped_defs = True
   no_implicit_optional = True
   warn_redundant_casts = True
   warn_unused_ignores = True
   warn_no_return = True
   strict_equality = True

   # Per-module settings
   [mypy-gi.*]
   ignore_missing_imports = True

   [mypy-aiohttp.*]
   ignore_missing_imports = True

   [mypy-rapidfuzz.*]
   ignore_missing_imports = True

   [mypy-send2trash.*]
   ignore_missing_imports = True
   ```

3. Add type hints to domain models:
   ```python
   # src/domain/wallpaper.py
   from dataclasses import dataclass
   from typing import List, Dict, Any, Optional
   from enum import Enum

   class WallpaperSource(Enum):
       WALLHAVEN = "wallhaven"
       LOCAL = "local"
       FAVORITE = "favorite"

   @dataclass
   class Wallpaper:
       id: str
       url: str
       path: str
       resolution: Resolution
       source: WallpaperSource
       category: str
       purity: WallpaperPurity
       colors: List[str]
       file_size: int
       thumbs_large: str
       thumbs_small: str

       def matches_query(self, query: str) -> bool:
           ...

       def to_dict(self) -> Dict[str, Any]:
           ...
   ```

4. Add type hints to services:
   ```python
   # src/services/wallhaven_service.py
   from typing import List, Optional, Dict, Any
   from aiohttp import ClientSession
   from domain.wallpaper import Wallpaper

   class WallhavenService(BaseService):
       BASE_URL: str = "https://wallhaven.cc/api/v1"
       RATE_LIMIT: int = 45

       def __init__(self, api_key: Optional[str] = None) -> None:
           super().__init__()
           self.api_key = api_key
           self._session: Optional[ClientSession] = None
           self._last_request_time: float = 0.0

       async def search(
           self,
           q: str = "",
           categories: str = "111",
           purity: str = "100",
           sorting: str = "date_added",
           order: str = "desc",
           atleast: str = "1920x1080",
           page: int = 1,
       ) -> Dict[str, Any]:
           """Search wallpapers"""
           ...

       async def download(self, url: str, dest: Path) -> bool:
           """Download wallpaper"""
           ...

       def parse_wallpapers(self, data: List[Dict[str, Any]]) -> List[Wallpaper]:
           """Parse API response"""
           ...

       async def close(self) -> None:
           """Close session"""
           ...
   ```

5. Add type hints to ViewModels:
   ```python
   # src/ui/view_models/base.py
   from gi.repository import GObject
   from typing import Optional, Callable, Any

   class BaseViewModel(GObject.Object):
       def __init__(self) -> None:
           super().__init__()
           self._is_busy: bool = False
           self._error_message: Optional[str] = None

   # src/ui/view_models/wallhaven_view_model.py
   class WallhavenViewModel(BaseViewModel):
       def __init__(self, service: WallhavenService) -> None:
           super().__init__()
           self._service = service
           self._wallpapers: Gio.ListStore = Gio.ListStore()
           self._current_page: int = 1
           self._total_pages: int = 1

       @GObject.Property(type=Gio.ListStore)
       def wallpapers(self) -> Gio.ListStore:
           return self._wallpapers

       async def search(self, query: str, **filters: Any) -> None:
           """Search wallpapers"""
           ...
   ```

6. Add type hints to UI views:
   ```python
   # src/ui/views/wallhaven_view.py
   class WallhavenView(Gtk.Box):
       def __init__(self, viewmodel: WallhavenViewModel) -> None:
           super().__init__(orientation=Gtk.Orientation.VERTICAL)
           self.viewmodel = viewmodel
           self._setup_ui()
           self._bind_viewmodel()

       def _setup_ui(self) -> None:
           """Setup UI widgets"""
           ...

       def _bind_viewmodel(self) -> None:
           """Bind ViewModel properties"""
           ...

       def _on_search_clicked(self, button: Gtk.Button) -> None:
           """Handle search button click"""
           ...
   ```

7. Fix type errors iteratively:
   ```bash
   # Run mypy and see errors
   mypy src/

   # Fix errors one by one:
   # - Add type hints to functions
   # - Fix type mismatches
   # - Add type: ignore comments for external libraries
   ```

8. Add pre-commit type check:
   ```bash
   # In .pre-commit-config.yaml (if using pre-commit)
   repos:
     - repo: https://github.com/pre-commit/mirrors-mypy
       rev: v1.5.0
       hooks:
         - id: mypy
           additional_dependencies:
             - types-aiofiles
             - types-requests
   ```

tests:
- Unit: Type checking with mypy
- Integration: Type checking in tests
- Verify no type errors in production code

acceptance_criteria:
- Type hints on all functions and methods
- mypy.ini configured
- mypy reports 0 type errors in src/
- mypy reports minimal errors in tests/
- Type hints use modern syntax (e.g., List[str], Optional[str])
- No any types in production code (except where necessary)
- Complex types use TypeAlias for clarity

validation:
- Commands to verify:
  ```bash
  mypy --version
  mypy src/
  mypy src/ --strict  # Try for strict mode
  ```
- Check output: "Success: no issues found in X source files"

notes:
- Use Optional[T] for nullable values
- Use Union[T1, T2] for multiple types
- Use TypeAlias for complex types: `WallpaperList = List[Wallpaper]`
- Ignore external libraries: gi.*, aiohttp (missing stubs)
- Use type: ignore sparingly (only when truly necessary)
- mypy catches errors before runtime
- Consider pyright as alternative (better async support)
- Type hints improve IDE autocomplete

# WALLPICKER

**Refactored:** 2026-01-05 (Updated: 2026-01-16 with v2.1 AI upscaling and resolution sorting)
**Type:** Python GTK4 + Libadwaita Desktop App (MVVM Architecture)

## OVERVIEW
Wallpaper picker with multi-source support (Wallhaven API + local files). Features a modern MVVM architecture, async operations, dependency injection, and comprehensive testing.

**Phase 2 Complete:** AI upscaling with waifu2x, concurrent queue processing, resolution sorting, and single-card refresh.

## STRUCTURE
```
./
├── src/
│   ├── core/         # Core infrastructure (DI container, logging)
│   ├── domain/       # Domain entities and value objects
│   ├── services/     # Business logic services (Async)
│   └── ui/           # UI Layer (MVVM)
│       ├── components/    # Reusable UI components
│       ├── view_models/  # Presentation logic
│       └── views/        # GTK Widgets
├── tests/            # Pytest test suite
└── data/             # Assets
```

## KEY COMPONENTS

| Component | Location | Description |
|-----------|----------|-------------|
| **Entry Point** | `src/ui/main_window.py` | Orchestrates DI container and ViewModels with Adw.ToolbarView |
| **DI Container** | `src/core/container.py` | Manages service lifecycles and dependencies |
| **Domain Models** | `src/domain/` | Rich entities (Wallpaper, Config) |
| **Wallhaven** | `src/services/wallhaven_service.py` | Async API client (aiohttp) |
| **Local Files** | `src/services/local_service.py` | Local file management |
| **ViewModels** | `src/ui/view_models/` | Observable state for UI binding |
| **Toast Service** | `src/services/toast_service.py` | Native Adw.ToastOverlay for notifications |
| **Status Page** | `src/ui/components/status_page.py` | Reusable loading/empty/error states |
| **Views** | `src/ui/views/` | GTK widgets that bind to ViewModels |
| **AI Upscaler** | `src/ui/view_models/local_view_model.py` | waifu2x-ncnn-vulkan integration with queue |

## ARCHITECTURE CONVENTIONS

### MVVM Pattern
- **Models**: Domain entities (`src/domain`) and Services (`src/services`)
- **ViewModels**: Expose observable properties (`GObject.Property`) and command methods. No GTK widget references.
- **Views**: GTK widgets that bind to ViewModels. No business logic.
- **Components**: Reusable UI elements (`src/ui/components/`).

### Modern UI Layout (Phase 1)
- **Adw.ToolbarView**: Proper header/content separation with flat styling
- **Adw.HeaderBar**: Window title, refresh button, menu button
- **Adw.ViewSwitcherBar**: Tab navigation at bottom
- **Adw.ToastOverlay**: Window-level native notifications (replaces inline errors)
- **Adw.StatusPage**: Empty/loading/error states with Adw.Stack

### AI Upscaling (v2.1)
- Config option `upscaler_enabled` in `~/.config/wallpicker/config.json`
- Uses waifu2x-ncnn-vulkan with CPU mode (avoids RADV driver bugs)
- Queue system with 2 concurrent operations
- Visual feedback: blocking overlay with spinner, flash animation on complete
- Auto-refresh of thumbnail and metadata (resolution/size)
- Image verification before replacement, backup on failure

### Async Operations
- Network and file I/O use `async`/`await`.
- UI invokes async methods via `GLib` integration or `asyncio`.
- No `threading.Thread` for IO-bound tasks (replaced by asyncio).

### Testing
- **Framework**: `pytest`
- **Coverage**: >95%
- **Fixtures**: `tests/conftest.py` handles mock services and async loops.
- **Structure**: Tests mirror source directory structure.

## CONFIGURATION
- **Config**: `~/.config/wallpicker/config.json`
- **Cache**: `~/.cache/wallpicker/` (Thumbnails, Logs)
- **Wallpaper Setting**: Symlink at `~/.cache/current_wallpaper` + `awww`

## COMMANDS
```bash
# Run Application
./launcher.sh

# Run Tests
python -m pytest tests/

# Code Quality
ruff check .
black .
mypy src/
```

## DEPENDENCIES
- **Runtime**: `PyGObject`, `aiohttp`, `requests`, `Pillow`, `rapidfuzz`, `send2trash`
- **Dev**: `pytest`, `pytest-asyncio`, `pytest-cov`, `ruff`, `black`, `mypy`
- **Optional**: `awww` (animated transitions), `waifu2x-ncnn-vulkan` (AI upscaling)

# WALLPICKER

**Generated:** 2026-01-05
**Type:** Python GTK4 + Libadwaita Desktop App

## OVERVIEW
Wallpaper picker with multi-source support (Wallhaven API + local files). Async HTTP requests, thumbnail caching, favorites management.

## STRUCTURE
```
./
├── src/
│   ├── services/     # All business logic (wallpaper fetching, caching, DB)
│   └── ui/           # GTK/Libadwaita UI layer
├── tests/
└── data/             # Assets (icons)
```

## WHERE TO LOOK
| Task | Location |
|------|----------|
| Wallpaper API integration | src/services/wallhaven_service.py |
| Local file browsing | src/services/local_service.py |
| UI entry point | src/ui/main_window.py |
| Config management | src/services/config_service.py |
| Thumbnail caching | src/services/thumbnail_cache.py |
| Setting wallpapers | src/services/wallpaper_setter.py |
| Favorites DB | src/services/favorites_service.py |

## CONVENTIONS (NON-STANDARD)

### Module Loading
All entry points (`main.py`, `launcher.py`) manually add `src/` to `sys.path`:
```python
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))
```
No `__init__.py` in `src/` directories.

### Installation
Two paths:
- `./install.sh` → User-space to `~/.local/`
- `PKGBUILD` (Arch) → System-wide to `/usr/`

Both create executable `wallpicker` that calls `launcher.py`.

### Testing
Custom `run_tests.py` using `unittest` with extensive mocking (no pytest).

### Build
- Dev: `mise run dev` (Python 3.13 from mise.toml)
- Package: PKGBUILD for Arch Linux
- Dependencies: Listed in `requirements.txt`

## ANTI-PATTERNS (THIS PROJECT)
- Do NOT add `__init__.py` to `src/` dirs (intentional flat structure)
- Do NOT use pytest (unittest + mocks only)
- Do NOT modify install.sh after cloning (contains hardcoded paths)
- Do NOT import from src/ without sys.path manipulation in entry points

## CONFIG LOCATIONS
- Config: `~/.config/wallpicker/config.json`
- Thumbnails: `~/.cache/wallpicker/thumbnails/` (7-day expiry, 500MB limit)

## DEPENDENCIES
- requests, Pillow, PyGObject, send2trash, aiohttp, rapidfuzz
- Python 3.13+

## COMMANDS
```bash
mise run dev          # Dev mode
./install.sh          # Install to ~/.local/
python tests/run_tests.py  # Run tests
```

## NOTES
- Async/await for HTTP requests (wallhaven_service.py)
- GTK4 + Libadwaita for UI (modern GNOME styling)
- All services importable from anywhere (flat src/ structure)
- Wallpaper transitions via `awww` command

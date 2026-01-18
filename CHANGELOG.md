# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [2.3.0] - 2026-01-18

### Fixed
- **System freeze on startup**: Fixed critical threading bug where `Gdk.Texture` was being created in worker threads
  - GTK4 objects must be created in the main thread - violating this caused display server corruption
  - Now loads image bytes in worker thread, creates texture in main thread via `GLib.idle_add()`
- **Nested event loops**: Fixed `asyncio.run()` calls that created conflicting event loops
  - `wallpaper_setter.py`, `thumbnail_cache.py`, `favorites_view_model.py` now use global event loop
  - Added timeouts to prevent blocking forever

### Changed
- **Massive performance improvement**: Added infinite scroll pagination to local tab
  - Initial load: 50 wallpapers (was 600+)
  - Loads more as user scrolls near bottom
  - Memory limit: max 300 items visible, oldest cleared automatically
  - Startup time: <1 second (was 5-15 seconds)
  - Memory usage: ~50-100 MB (was 500-1000 MB)

### Added
- **PIL-based thumbnail generation**: Local wallpapers now use proper cached thumbnails
  - Generates 200x160 thumbnails (was loading full resolution images)
  - Thumbnails cached to `~/.cache/wallpicker/thumbnails/`
  - In-memory LRU cache for fast repeated access
  - Automatic regeneration when source image is newer

## [2.2.3] - 2026-01-18

### Fixed
- **Sorting not working**: Sort changes now trigger full grid rebuild instead of incremental update
  - Previously, changing sort order had no visible effect

### Added
- **Local tab filters**: Added resolution and aspect ratio filters for local wallpapers
  - Minimum resolution filter: All, 1920x1080, 2560x1440, 3840x2160 (4K)
  - Aspect ratio filter: All, 16:9, 16:10, 21:9, 9:16, 1:1

## [2.2.2] - 2026-01-17

### Fixed
- **UI jump on startup**: Removed deferred grid update that caused visible layout shift

## [2.2.1] - 2026-01-17

### Fixed
- **Critical startup performance**: Removed synchronous image resolution reading during wallpaper scan
  - Resolution now lazy-loaded only when displayed
  - 626 wallpapers load in ~0.01s vs seconds before
- **UI responsiveness**: Incremental grid updates instead of full rebuild on refresh
- **Thumbnail loading**: Increased parallel workers from 4 to 8

### Changed
- About dialog now reads version from package metadata (importlib.metadata)
- License format updated to SPDX standard in pyproject.toml

## [2.2.0] - 2026-01-16

### Added
- About dialog with dynamic version display
- Version management connected to pyproject.toml

## [2.1.0] - 2026-01-16

### Added
- **AI Upscaling**: New feature to upscale local wallpapers 2x using waifu2x-ncnn-vulkan
  - Config option `upscaler_enabled` (default: false)
  - Upscale button appears on wallpaper cards when enabled
  - Blocking overlay with spinner during processing
  - Automatic verification of upscaled images
  - Queue system with concurrent processing (2 at a time)
  - Visual feedback with flash animation on completion
  - Metadata (resolution/size) auto-refreshes after upscaling

- **Resolution Sorting**: New sort option for local wallpapers
  - Sort by resolution (largest first)
  - Available in Local and Favorites tabs

### Changed
- Improved wallpaper card refresh mechanism
- Single card refresh instead of full grid reload
- Fixed scroll position stability when adding overlays
- Using `Gtk.Overlay` for upscaling indicator (no layout disruption)

### Fixed
- Resolution sorting handles string format correctly
- Fixed AttributeError when refreshing wallpaper cards with Overlay container
- CSS cleanup: removed unsupported `gap` and `backdrop-filter` properties

## [2.0.0] - 2025-12-24

### Added
- **MVVM Architecture Refactoring**: Complete architectural overhaul
  - ViewModels with GObject properties for observable state
  - Clean separation of concerns (Models, Views, ViewModels, Services)
  - Dependency injection container
  - BaseViewModel with common functionality

- **Modern UI**: Phase 1 UI/UX improvements
  - Adw.ToolbarView layout with proper header/content separation
  - Native Toast notifications via Adw.ToastOverlay
  - Reusable Status Page components (loading/empty/error states)
  - Adw.ViewSwitcherBar for tab navigation at bottom

- **Smart Thumbnail Caching**: Improved thumbnail handling
  - Persistent disk-based caching
  - Automatic cleanup of old thumbnails
  - Faster subsequent loads

- **Keyboard Navigation**: Full keyboard support
  - Arrow keys to navigate wallpapers
  - Enter to set wallpaper
  - Delete to remove
  - F for favorites, R for refresh

### Changed
- Refactored all views to use GTK4/Libadwaita patterns
- Async operations use asyncio throughout
- Toast service replaced inline error messages

## [1.5.0] - 2025-11-15

### Added
- Favorites system with persistent storage
- Quick access to favorite wallpapers
- Auto-download remote wallpapers to favorites

### Changed
- Improved wallpaper deletion (moves to trash)
- Better error handling for network operations

## [1.4.0] - 2025-10-20

### Added
- Wallhaven API integration
- Search, filter, and browse wallpapers
- Support for categories (General, Anime, People)
- Purity filtering (SFW, Sketchy, NSFW)
- Multiple sorting options

## [1.3.0] - 2025-09-10

### Added
- Local wallpaper management
- Custom directory selection
- Thumbnail previews
- File metadata display (resolution, size)

## [1.2.0] - 2025-08-15

### Added
- Smooth animated wallpaper transitions using `awww`
- Wallpaper setting via symlink mechanism
- Support for multiple desktop environments

## [1.1.0] - 2025-07-01

### Added
- Initial release
- Basic wallpaper browsing and setting
- Python GTK4 interface

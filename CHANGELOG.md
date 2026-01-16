# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

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

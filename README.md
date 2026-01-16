# WallPicker

A modern GTK4/Libadwaita wallpaper picker application. Browse and discover wallpapers from Wallhaven.cc, manage your local wallpaper collection, and set your desktop background with smooth animated transitions.

![WallPreview](https://img.shields.io/badge/Status-Stable-brightgreen)
![Python](https://img.shields.io/badge/python-3.11+-blue.svg)
![License](https://img.shields.io/badge/license-MIT-purple.svg)

## Features

- **Wallhaven Integration**: Search, filter, and browse thousands of wallpapers from Wallhaven.cc with support for categories, purity levels, and sorting options. Shows total wallpaper count for searches.
  - **Local Wallpaper Management**: Browse and manage wallpapers from your `~/Pictures` directory (or custom directory) with thumbnail previews. Auto-refreshes when downloading from Wallhaven.
- **Favorites System**: Save your favorite wallpapers for quick access across sessions. Supports both local and remote wallpapers with automatic downloading.
- **Smart Thumbnail Caching**: Persistent disk-based caching for instant thumbnail loading with automatic cleanup
- **Smooth Transitions**: Animated wallpaper changes using `awww` utility
- **AI Upscaling**: Upscale local wallpapers 2x using Real-ESRGAN (requires `realesrgan-ncnn-vulkan`)
- **Modern UI**: Native GTK4/Libadwaita interface with Adw.ToolbarView, Adw.ToastOverlay, Adw.StatusPage, and responsive grid layouts
- **MVVM Architecture**: Clean separation of concerns with proper ViewModels, Views, and Services
- **Async Operations**: All I/O operations use async/await for non-blocking UI
- **Dependency Injection**: Service container for flexible dependency management

## Screenshots

![WallPicker Screenshot](data/screenshot.png)

## Requirements

### System Dependencies

- **Python**: 3.11 or higher
- **GTK4**: 4.0 or higher
- **Libadwaita**: 1.0 or higher
- **awww**: Animated wallpaper setter (optional but recommended for transitions)
- **realesrgan-ncnn-vulkan**: AI upscaler for local wallpapers (optional, enables upscaler feature)

### Python Packages

 - PyGObject
 - requests
 - send2trash
 - aiohttp
 - Pillow
 - rapidfuzz

## Installation

### From Git Repository (Recommended)

1. Clone the repository:
```bash
git clone https://github.com/gotar/wallpicker.git
cd wallpicker
```

2. Run the installation script:
```bash
./install.sh
```

The installation script will:
- Install system dependencies (GTK4, Libadwaita, Python bindings)
- Install Python dependencies from requirements.txt
- Copy application files to `~/.local/share/wallpicker`
- Create a symlink in `~/.local/bin/wallpicker`
- Install desktop entry and icon

3. Make sure `~/.local/bin` is in your PATH (add to `~/.bashrc` or `~/.zshrc`):
```bash
export PATH="$HOME/.local/bin:$PATH"
```

4. Run the application:
```bash
wallpicker
```

**Note**: You may need to log out and log back in for the desktop entry to appear in your application menu.

### Arch Linux / Arch-based Distributions

WallPicker is available in the Arch User Repository (AUR).

#### Install from AUR (Recommended)

Using yay:
```bash
yay -S wallpicker
```

Using paru:
```bash
paru -S wallpicker
```

Manual AUR installation:
```bash
git clone https://aur.archlinux.org/wallpicker.git
cd wallpicker
makepkg -si
```

#### Build from PKGBUILD

If you prefer to build from the repository:
```bash
git clone https://github.com/gotar/wallpicker.git
cd wallpicker
makepkg -si
```

For animated transitions (optional but recommended):
```bash
yay -S awww
```

## Usage

Launch the application:
```bash
wallpicker
```

### Application Overview

WallPicker provides three main tabs:

#### Wallhaven Tab

Browse wallpapers from Wallhaven.cc directly within the application.

- **Search**: Enter keywords to find specific wallpapers
- **Filters**: Configure categories (General, Anime, People), purity (SFW, Sketchy, NSFW), and sorting options
- **Download**: Save wallpapers to your local collection
- **Set Wallpaper**: Apply a wallpaper directly with smooth transitions

#### Local Tab

Manage your existing wallpaper collection from your local directory.

- **Browse**: View thumbnails of your local wallpapers
- **Custom Directory**: Click the folder icon in the toolbar to select a custom wallpapers directory (defaults to `~/Pictures`)
- **Set Wallpaper**: Apply any image as your desktop background
- **Add to Favorites**: Save wallpapers to your favorites collection
- **Delete**: Remove unwanted wallpapers (moves to trash)
- **Upscale**: Upscale wallpapers 2x using AI (requires `realesrgan-ncnn-vulkan` and `upscaler_enabled: true` in config)
- **Notifications**: Get system notifications for successful actions

#### Favorites Tab

Quick access to your saved favorite wallpapers.

- **Add to Favorites**: Save any wallpaper from Wallhaven or Local tabs
- **Quick Access**: Instantly browse and set your favorites
- **Persistent Storage**: Favorites persist across application restarts
- **Auto-refresh**: Automatically reloads when switching to the tab

## Configuration

WallPicker uses a configuration file at `~/.config/wallpicker/config.json` for customization. The configuration file is automatically created on first launch with default values.

### Configuration Options

```json
{
    "local_wallpapers_dir": null,
    "wallhaven_api_key": null,
    "notifications_enabled": true,
    "upscaler_enabled": false
}
```

 - **local_wallpapers_dir**: Custom path to your wallpapers directory (default: `~/Pictures`)
 - **wallhaven_api_key**: Wallhaven API key for extended access (optional)
 - **notifications_enabled**: Enable/disable system notifications for actions (default: true)
 - **upscaler_enabled**: Enable AI upscaler button for local wallpapers (default: false, requires `realesrgan-ncnn-vulkan`)

 ### Setting Custom Wallpaper Directory

You can change the wallpaper directory in two ways:

**Via UI (Recommended)**:
1. Open WallPicker and navigate to the Local tab
2. Click the folder icon in the toolbar
3. Select your desired wallpapers directory
4. The setting will be saved automatically

**Via Configuration File**:
1. Create configuration directory:
```bash
mkdir -p ~/.config/wallpicker
```

2. Set your custom directory:
```bash
echo '{"local_wallpapers_dir": "/path/to/your/wallpapers"}' > ~/.config/wallpicker/config.json
```

3. Restart WallPicker

**Note**: Use the absolute path (e.g., `/home/username/Papers`) to your wallpaper directory.

### Wallhaven API Key (Optional)

For full access to Wallhaven features (including NSFW content if your account is verified):

1. Create a Wallhaven account and obtain your API key from [wallhaven.cc/settings/account](https://wallhaven.cc/settings/account)
2. Add your API key to the config:
```bash
echo '{"wallhaven_api_key": "your_api_key_here"}' > ~/.config/wallpicker/config.json
```

Or combine both settings:
```bash
echo '{"local_wallpapers_dir": "/path/to/wallpapers", "wallhaven_api_key": "your_api_key"}' > ~/.config/wallpicker/config.json
```
3. Add your API key:
```bash
echo '{"wallhaven_api_key": "your_api_key_here"}' > ~/.config/wallpicker/config.json
```

### AI Upscaler (Optional)

WallPicker can upscale local wallpapers 2x using Real-ESRGAN AI upscaling.

**Requirements:**
- Install `realesrgan-ncnn-vulkan` from AUR:
```bash
yay -S realesrgan-ncnn-vulkan
```

**Enable in config:**
```bash
echo '"upscaler_enabled": true' > ~/.config/wallpicker/config.json
```

Or combine with other settings:
```bash
echo '{"local_wallpapers_dir": "/path/to/wallpapers", "upscaler_enabled": true}' > ~/.config/wallpicker/config.json
```

Once enabled, an "Upscale 2x (AI)" button will appear on local wallpaper cards. The upscaled image replaces the original file.

### Cache Management

WallPicker automatically manages thumbnail caching:

- **Location**: `~/.cache/wallpicker/thumbnails/`
- **Expiry**: Cached thumbnails expire after 7 days
- **Size Limit**: Maximum 500 MB with automatic cleanup of oldest files

## Wallpaper Setting Mechanism

WallPicker sets wallpapers using a symlink-based approach:

1. Creates a symbolic link at `~/.cache/current_wallpaper` pointing to the selected wallpaper
2. Invokes `awww` for animated transitions (or a fallback command)

Example transition command:
```bash
awww ~/.cache/current_wallpaper --transition-type outer --transition-duration 1
```

## Project Structure

```
wallpicker/
 ├── wallpicker                    # Application entry point
 ├── launcher.py                   # Development launcher
 ├── install.sh                    # Installation script
 ├── src/
 │   ├── services/
 │   │   ├── wallhaven_service.py   # Wallhaven API integration
 │   │   ├── local_service.py       # Local wallpaper browsing
 │   │   ├── wallpaper_setter.py   # Wallpaper application logic
 │   │   ├── favorites_service.py   # Favorites management
 │   │   ├── config_service.py      # Configuration management
 │   │   └── thumbnail_cache.py    # Image caching system
 │   └── ui/
 │       └── main_window.py        # GTK4/Libadwaita UI
 ├── tests/
 │   └── run_tests.py              # Test suite
 ├── requirements.txt              # Python dependencies
 ├── README.md                     # This file
 └── .gitignore
```

## Development

### Running Tests

```bash
python -m pytest tests/
```

Run specific test files:
```bash
python -m pytest tests/ui/test_favorites_view_model.py
```

### Contributing

Contributions are welcome! Please feel free to submit pull requests or open issues for bugs and feature requests.

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Acknowledgments

- Wallhaven.cc for providing an excellent wallpaper API
- The GTK and Libadwaita projects for the fantastic UI framework
- `awww` for animated wallpaper transitions

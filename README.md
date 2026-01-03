# WallPicker

A modern GTK4/Libadwaita wallpaper picker application. Browse and discover wallpapers from Wallhaven.cc, manage your local wallpaper collection, and set your desktop background with smooth animated transitions.

![WallPreview](https://img.shields.io/badge/Status-Stable-brightgreen)
![Python](https://img.shields.io/badge/python-3.11+-blue.svg)
![License](https://img.shields.io/badge/license-MIT-purple.svg)

## Features

- **Wallhaven Integration**: Search, filter, and browse thousands of wallpapers from Wallhaven.cc with support for categories, purity levels, and sorting options
- **Local Wallpaper Management**: Browse and manage wallpapers from your `~/Pictures` directory with thumbnail previews
- **Favorites System**: Save your favorite wallpapers for quick access across sessions
- **Smart Thumbnail Caching**: Persistent disk-based caching for instant thumbnail loading with automatic cleanup
- **Smooth Transitions**: Animated wallpaper changes using the `awww` utility
- **Modern UI**: Native GTK4/Libadwaita interface that integrates seamlessly with your desktop environment

## Screenshots

![WallPicker Screenshot](data/screenshot.png)

## Requirements

### System Dependencies

- **Python**: 3.11 or higher
- **GTK4**: 4.0 or higher
- **Libadwaita**: 1.0 or higher
- **awww**: Animated wallpaper setter (optional but recommended for transitions)

### Python Packages

- PyGObject
- requests
- send2trash
- fuzzywuzzy

## Installation

### From Git Repository

1. Clone the repository:
```bash
git clone https://github.com/gotar/wallpicker.git
cd wallpicker
```

2. Install Python dependencies:
```bash
pip install -r requirements.txt
```

3. Run the application:
```bash
./wallpicker
```

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
./wallpicker
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

Manage your existing wallpaper collection from `~/Pictures`.

- **Browse**: View thumbnails of your local wallpapers
- **Set Wallpaper**: Apply any image as your desktop background
- **Delete**: Remove unwanted wallpapers (moves to trash)

#### Favorites Tab

Quick access to your saved favorite wallpapers.

- **Add to Favorites**: Save any wallpaper from Wallhaven or Local tabs
- **Quick Access**: Instantly browse and set your favorites
- **Persistent Storage**: Favorites persist across application restarts

## Configuration

WallPicker uses a configuration file at `~/.config/wallpicker/config.json` for customization. The configuration file is automatically created on first launch with default values.

### Configuration Options

```json
{
    "local_wallpapers_dir": null,
    "wallhaven_api_key": null
}
```

- **local_wallpapers_dir**: Custom path to your wallpapers directory (default: `~/Pictures/Upscaled_Wallpapers` or `~/Pictures`)
- **wallhaven_api_key**: Wallhaven API key for extended access (optional)

### Setting Custom Wallpaper Directory

To use a custom directory for local wallpapers:

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
python tests/run_tests.py
```

### Contributing

Contributions are welcome! Please feel free to submit pull requests or open issues for bugs and feature requests.

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Acknowledgments

- Wallhaven.cc for providing an excellent wallpaper API
- The GTK and Libadwaita projects for the fantastic UI framework
- `awww` for animated wallpaper transitions

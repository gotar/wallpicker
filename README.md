# WallPicker

A GTK4/Libadwaita wallpaper picker for Hyprland. Browse Wallhaven.cc, manage local wallpapers, and set them with smooth transitions.

## Features

- **Wallhaven Integration** - Search, filter, and download wallpapers from Wallhaven.cc
- **Local Management** - Browse ~/Pictures, set or delete wallpapers
- **Favorites** - Save favorite wallpapers for quick access
- **Smooth Transitions** - Uses `awww` for animated wallpaper changes

## Requirements

- Hyprland
- Python 3.11+
- GTK4 + Libadwaita
- `awww` (for setting wallpapers with transitions)

### Arch Linux

```bash
sudo pacman -S python python-gobject gtk4 libadwaita python-requests python-send2trash
```

## Installation

```bash
git clone https://github.com/pgotar/wallpicker.git
cd wallpicker
pip install -r requirements.txt
./wallpicker
```

## Usage

```bash
./wallpicker
```

### Tabs

- **Wallhaven** - Search online wallpapers, download or set directly
- **Local** - Browse ~/Pictures, set or delete wallpapers  
- **Favorites** - Quick access to saved favorites

### Wallhaven API Key (Optional)

For NSFW content access:

```bash
mkdir -p ~/.config/wallpicker
echo '{"wallhaven_api_key": "your_key"}' > ~/.config/wallpicker/config.json
```

## Project Structure

```
wallpicker/
├── wallpicker              # Entry point
├── src/
│   ├── services/
│   │   ├── wallhaven_service.py
│   │   ├── local_service.py
│   │   ├── wallpaper_setter.py
│   │   └── favorites_service.py
│   └── ui/
│       └── main_window.py
└── requirements.txt
```

## How Wallpaper Setting Works

Uses the same logic as `~/.local/bin/random_wallpaper.sh`:
1. Creates symlink at `~/.cache/current_wallpaper`
2. Calls `awww` with smooth transition (`--transition-type outer --transition-duration 1`)

## License

MIT

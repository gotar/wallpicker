"""Domain models for Wallpicker application."""

from .wallpaper import Wallpaper, WallpaperSource, WallpaperPurity, Resolution
from .config import Config, ConfigError
from .favorite import Favorite
from .exceptions import WallpickerError, WallpaperError, ServiceError

__all__ = [
    "Wallpaper",
    "WallpaperSource",
    "WallpaperPurity",
    "Resolution",
    "Config",
    "ConfigError",
    "Favorite",
    "WallpickerError",
    "WallpaperError",
    "ServiceError",
]

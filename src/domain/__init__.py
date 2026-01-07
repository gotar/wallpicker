"""Domain models for Wallpicker application."""

from .config import Config, ConfigError
from .exceptions import ServiceError, WallpaperError, WallpickerError
from .favorite import Favorite
from .wallpaper import Resolution, Wallpaper, WallpaperPurity, WallpaperSource

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

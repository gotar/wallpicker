"""Domain models for Wallpicker application."""

from .wallpaper import Resolution, Wallpaper, WallpaperPurity, WallpaperSource
from .config import Config, ConfigError
from .exceptions import ServiceError, WallpaperError, WallpickerError
from .favorite import Favorite

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

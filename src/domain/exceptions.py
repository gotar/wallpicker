"""Custom exceptions for Wallpicker domain."""


class WallpickerError(Exception):
    """Base exception for Wallpicker domain errors."""

    pass


class ConfigError(WallpickerError):
    """Configuration-related errors."""

    pass


class WallpaperError(WallpickerError):
    """Wallpaper-related errors."""

    pass


class ServiceError(WallpickerError):
    """Service layer errors."""

    pass

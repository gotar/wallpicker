"""Wallpicker - Modern wallpaper picker application."""

try:
    from importlib.metadata import version

    __version__ = version("wallpicker")
except Exception:
    __version__ = "2.5.1"

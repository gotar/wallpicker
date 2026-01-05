"""Tests for domain exceptions."""

import pytest

from domain.exceptions import ConfigError, ServiceError, WallpaperError, WallpickerError


def test_wallpicker_error():
    """Test base WallpickerError."""
    with pytest.raises(WallpickerError):
        raise WallpickerError("Test error")


def test_config_error_is_wallpicker_error():
    """Test ConfigError is subclass of WallpickerError."""
    with pytest.raises(WallpickerError):
        raise ConfigError("Config error")


def test_wallpaper_error_is_wallpicker_error():
    """Test WallpaperError is subclass of WallpickerError."""
    with pytest.raises(WallpickerError):
        raise WallpaperError("Wallpaper error")


def test_service_error_is_wallpicker_error():
    """Test ServiceError is subclass of WallpickerError."""
    with pytest.raises(ServiceError):
        raise ServiceError("Service error")


def test_config_error_message():
    """Test ConfigError with message."""
    error = ConfigError("Directory not found")
    assert str(error) == "Directory not found"
    with pytest.raises(ConfigError, match="Directory not found"):
        raise error


def test_wallpaper_error_message():
    """Test WallpaperError with message."""
    error = WallpaperError("Invalid resolution")
    assert str(error) == "Invalid resolution"
    with pytest.raises(WallpaperError, match="Invalid resolution"):
        raise error


def test_service_error_message():
    """Test ServiceError with message."""
    error = ServiceError("API request failed")
    assert str(error) == "API request failed"
    with pytest.raises(ServiceError, match="API request failed"):
        raise error

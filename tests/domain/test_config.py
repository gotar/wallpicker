"""Tests for Config domain model."""

from pathlib import Path

import pytest

from domain.config import Config, ConfigError


def test_config_default_values():
    """Test Config with default values."""
    config = Config()
    assert config.local_wallpapers_dir is None
    assert config.wallhaven_api_key is None


def test_config_with_values():
    """Test Config with values."""
    config = Config(
        local_wallpapers_dir=Path("/test/path"), wallhaven_api_key="test-key"
    )
    assert config.local_wallpapers_dir == Path("/test/path")
    assert config.wallhaven_api_key == "test-key"


def test_config_validation_valid():
    """Test Config validation with valid data."""
    temp_dir = Path("/tmp/wallpicker_config_test")
    temp_dir.mkdir(parents=True, exist_ok=True)

    config = Config(local_wallpapers_dir=temp_dir)
    config.validate()  # Should not raise

    # Cleanup
    temp_dir.rmdir()


def test_config_validation_invalid_dir():
    """Test Config validation with non-existent directory."""
    config = Config(local_wallpapers_dir=Path("/nonexistent/path"))
    with pytest.raises(ConfigError):
        config.validate()


def test_config_validation_file_instead_of_dir():
    """Test Config validation when path is a file."""
    import tempfile

    with tempfile.NamedTemporaryFile(delete=False) as f:
        temp_file = Path(f.name)

    try:
        config = Config(local_wallpapers_dir=temp_file)
        with pytest.raises(ConfigError):
            config.validate()
    finally:
        temp_file.unlink()


def test_config_pictures_dir():
    """Test pictures_dir property."""
    custom_dir = Path("/custom/path")
    config = Config(local_wallpapers_dir=custom_dir)
    assert config.pictures_dir == custom_dir

    config2 = Config()
    assert config2.pictures_dir == Path.home() / "Pictures"


def test_config_serialization():
    """Test Config to_dict and from_dict."""
    config = Config(
        local_wallpapers_dir=Path("/test/path"), wallhaven_api_key="test-key"
    )

    data = config.to_dict()
    assert data["local_wallpapers_dir"] == "/test/path"
    assert data["wallhaven_api_key"] == "test-key"


def test_config_from_dict():
    """Test Config.from_dict."""
    data = {
        "local_wallpapers_dir": "/test/path",
        "wallhaven_api_key": "test-key",
    }

    config = Config.from_dict(data)
    assert config.local_wallpapers_dir == Path("/test/path")
    assert config.wallhaven_api_key == "test-key"


def test_config_from_dict_with_none():
    """Test Config.from_dict with None values."""
    data = {
        "local_wallpapers_dir": None,
        "wallhaven_api_key": None,
    }

    config = Config.from_dict(data)
    assert config.local_wallpapers_dir is None
    assert config.wallhaven_api_key is None

"""Tests for ConfigService."""

import json
from pathlib import Path

import pytest

from domain.config import Config
from domain.exceptions import ServiceError
from services.config_service import ConfigService


@pytest.fixture
def config_service(temp_dir: Path) -> ConfigService:
    """Create ConfigService with temporary config file."""
    config_file = temp_dir / "config.json"
    return ConfigService(config_file=config_file)


def test_config_service_init(config_service: ConfigService):
    """Test ConfigService initialization."""
    # Config file is created on first load/save, not init
    assert config_service.config_dir == config_service.config_file.parent


def test_load_default_config(config_service: ConfigService):
    """Test loading default configuration."""
    # Don't create any config file - it should create defaults
    # The fixture creates a ConfigService but doesn't call _ensure_config_exists
    # So load_config should create the file with defaults
    config = config_service.load_config()
    assert config is not None
    assert config.local_wallpapers_dir is None
    assert config.wallhaven_api_key is None
    # File should be created after load
    assert config_service.config_file.exists()


def test_load_existing_config(config_service: ConfigService, temp_dir: Path):
    """Test loading existing configuration."""
    # Create wallpapers directory first
    wallpapers_dir = temp_dir / "wallpapers"
    wallpapers_dir.mkdir(parents=True, exist_ok=True)

    # Write custom config directly to file
    test_config = {
        "local_wallpapers_dir": str(wallpapers_dir),
        "wallhaven_api_key": "test-key",
    }

    with open(config_service.config_file, "w") as f:
        json.dump(test_config, f)

    # Reload from file
    config_service._config = None
    config = config_service.load_config()
    assert config is not None
    assert config.local_wallpapers_dir == wallpapers_dir
    assert config.wallhaven_api_key == "test-key"


def test_save_config(config_service: ConfigService, temp_dir: Path):
    """Test saving configuration."""
    # Create wallpapers directory first
    wallpapers_dir = temp_dir / "wallpapers"
    wallpapers_dir.mkdir(parents=True, exist_ok=True)

    config = Config(
        local_wallpapers_dir=wallpapers_dir,
        wallhaven_api_key="test-key",
    )

    config_service.save_config(config)

    # Verify file was written
    with open(config_service.config_file) as f:
        saved_data = json.load(f)

    assert saved_data["local_wallpapers_dir"] == str(wallpapers_dir)
    assert saved_data["wallhaven_api_key"] == "test-key"


def test_save_config_validation(config_service: ConfigService, temp_dir: Path):
    """Test saving config with invalid data."""
    # Create directory
    temp_dir.mkdir(parents=True, exist_ok=True)

    # Try to save with non-existent directory
    # Note: Config validation requires directory to exist
    config = Config(
        local_wallpapers_dir=Path("/nonexistent/path"),
        wallhaven_api_key="test-key",
    )

    with pytest.raises(ServiceError, match="Failed to save configuration"):
        config_service.save_config(config)


def test_legacy_get_method(config_service: ConfigService, temp_dir: Path):
    """Test legacy get method for compatibility."""
    # Create directories first
    test_dir = temp_dir / "test"
    test_dir.mkdir(parents=True, exist_ok=True)

    config_service.save_config(
        Config(
            local_wallpapers_dir=test_dir,
            wallhaven_api_key="key",
        )
    )

    assert config_service.get("local_wallpapers_dir") == test_dir
    assert config_service.get("wallhaven_api_key") == "key"
    assert config_service.get("nonexistent", "default") == "default"


def test_legacy_set_method(config_service: ConfigService, temp_dir: Path):
    """Test legacy set method for compatibility."""
    # Create directory first
    custom_dir = temp_dir / "custom"
    custom_dir.mkdir(parents=True, exist_ok=True)

    config_service.set("local_wallpapers_dir", custom_dir)
    config_service.set("wallhaven_api_key", "custom-key")

    config = config_service.get_config()
    assert config.local_wallpapers_dir == custom_dir
    assert config.wallhaven_api_key == "custom-key"


def test_legacy_save_method(config_service: ConfigService, temp_dir: Path):
    """Test legacy save method for compatibility."""
    temp_dir.mkdir(parents=True, exist_ok=True)

    # Create a valid subdirectory that exists
    legacy_dir = temp_dir / "legacy"
    legacy_dir.mkdir(exist_ok=True)

    config_dict = {
        "local_wallpapers_dir": str(legacy_dir),
        "wallhaven_api_key": "legacy-key",
    }

    config_service.save(config_dict)

    with open(config_service.config_file) as f:
        saved = json.load(f)

    assert saved["local_wallpapers_dir"] == str(legacy_dir)
    assert saved["wallhaven_api_key"] == "legacy-key"

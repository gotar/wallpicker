"""Configuration Service using domain models."""

import json
from pathlib import Path

from domain.config import Config, ConfigError
from domain.exceptions import ServiceError
from services.base import BaseService


class ConfigService(BaseService):
    """Service for managing application configuration using domain models."""

    DEFAULT_CONFIG = {
        "local_wallpapers_dir": None,
        "wallhaven_api_key": None,
    }

    def __init__(self, config_file: Path | None = None) -> None:
        """Initialize configuration service.

        Args:
            config_file: Path to config file (defaults to ~/.config/wallpicker/config.json)
        """
        super().__init__()
        self.config_file = (
            config_file or Path.home() / ".config" / "wallpicker" / "config.json"
        )
        self.config_dir = self.config_file.parent
        self._config: Config | None = None

    def _ensure_config_exists(self) -> None:
        """Create config directory and default config if they don't exist."""
        self.config_dir.mkdir(parents=True, exist_ok=True)

        if not self.config_file.exists():
            self.log_info(f"Creating default config at {self.config_file}")
            with open(self.config_file, "w") as f:
                json.dump(self.DEFAULT_CONFIG, f, indent=4)

    def load_config(self) -> Config:
        """Load configuration from file and return domain model.

        Returns:
            Config domain model with validated state

        Raises:
            ServiceError: If config file cannot be read
        """
        try:
            if self._config is None:
                self._ensure_config_exists()

            if self.config_file.exists():
                with open(self.config_file) as f:
                    config_data = json.load(f)
                self._config = Config.from_dict(config_data)
                self.log_debug(f"Loaded config from {self.config_file}")
            else:
                self._config = Config.from_dict(self.DEFAULT_CONFIG)
                self.log_debug("Using default config")
            return self._config
        except (json.JSONDecodeError, OSError) as e:
            self.log_error(
                f"Failed to load config from {self.config_file}: {e}", exc_info=True
            )
            raise ServiceError(f"Failed to load configuration: {e}") from e

    def save_config(self, config: Config) -> None:
        """Save configuration domain model to file.

        Args:
            config: Config domain model to save

        Raises:
            ServiceError: If config file cannot be written
        """
        try:
            config.validate()  # Validate before saving
            config_dict = config.to_dict()

            self.config_dir.mkdir(parents=True, exist_ok=True)
            with open(self.config_file, "w") as f:
                json.dump(config_dict, f, indent=4)

            self._config = config
            self.log_info(f"Saved config to {self.config_file}")
        except (ConfigError, OSError) as e:
            self.log_error(
                f"Failed to save config to {self.config_file}: {e}", exc_info=True
            )
            raise ServiceError(f"Failed to save configuration: {e}") from e

    def get_config(self) -> Config | None:
        """Get current configuration, loading if necessary.

        Returns:
            Config domain model or None if not loaded
        """
        if self._config is None:
            self.load_config()
        return self._config

    def get(self, key: str, default=None):
        """Get configuration value (legacy method for compatibility).

        Args:
            key: Configuration key to retrieve
            default: Default value if key not found

        Returns:
            Configuration value or default
        """
        config = self.get_config()
        return getattr(config, key, default)

    def set(self, key: str, value) -> None:
        """Set configuration value and save (legacy method for compatibility).

        Args:
            key: Configuration key to set
            value: Value to set
        """
        config = self.get_config()
        setattr(config, key, value)
        self.save_config(config)

    def save(self, config: dict) -> None:
        """Save entire configuration (legacy method for compatibility).

        Args:
            config: Configuration dictionary
        """
        config_model = Config.from_dict(config)
        self.save_config(config_model)

    def set_pictures_dir(self, path: Path) -> None:
        config = self.get_config()
        if config:
            config.local_wallpapers_dir = path
            self.save_config(config)

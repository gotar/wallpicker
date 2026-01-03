"""
Configuration Service
Handles reading and writing application configuration
"""

import json
from pathlib import Path
from typing import Dict, Optional

DEFAULT_CONFIG = {
    "local_wallpapers_dir": None,
    "wallhaven_api_key": None,
}


class ConfigService:
    """Service for managing application configuration"""

    def __init__(self, config_file: Optional[Path] = None):
        self.config_file = (
            config_file or Path.home() / ".config" / "wallpicker" / "config.json"
        )
        self.config_dir = self.config_file.parent
        self._config: Dict = DEFAULT_CONFIG.copy()

    def _ensure_config_exists(self):
        """Create config directory and default config if they don't exist"""
        self.config_dir.mkdir(parents=True, exist_ok=True)

        if not self.config_file.exists():
            with open(self.config_file, "w") as f:
                json.dump(DEFAULT_CONFIG, f, indent=4)

    def load(self) -> Dict:
        """Load configuration from file"""
        if self._config is not None and not self.config_file.exists():
            self._ensure_config_exists()

        if self.config_file.exists():
            with open(self.config_file, "r") as f:
                self._config = json.load(f)

        return self._config

    def get(self, key: str, default=None):
        """Get configuration value"""
        config = self.load()
        return config.get(key, default)

    def set(self, key: str, value):
        """Set configuration value and save to file"""
        config = self.load()
        config[key] = value

        with open(self.config_file, "w") as f:
            json.dump(config, f, indent=4)

        self._config = config

    def save(self, config: Dict):
        """Save entire configuration"""
        self.config_dir.mkdir(parents=True, exist_ok=True)

        with open(self.config_file, "w") as f:
            json.dump(config, f, indent=4)

        self._config = config

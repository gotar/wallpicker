"""Config domain model with validation."""

from dataclasses import dataclass
from pathlib import Path

from .exceptions import ConfigError

# Constants
DEFAULT_RESOLUTION = "1920x1080"
FILTER_RESOLUTIONS = ["", "1920x1080", "2560x1440", "3840x2160"]


@dataclass
class Config:
    """Application configuration domain model."""

    local_wallpapers_dir: Path | None = None
    wallhaven_api_key: str | None = None
    notifications_enabled: bool = True
    upscaler_enabled: bool = False

    def validate(self) -> None:
        """Validate configuration state."""
        if self.local_wallpapers_dir:
            if not isinstance(self.local_wallpapers_dir, Path):
                raise ConfigError("local_wallpapers_dir must be a Path object")
            if not self.local_wallpapers_dir.exists():
                raise ConfigError(f"Directory does not exist: {self.local_wallpapers_dir}")
            if not self.local_wallpapers_dir.is_dir():
                raise ConfigError(f"Path is not a directory: {self.local_wallpapers_dir}")

    @property
    def pictures_dir(self) -> Path:
        """Get pictures directory, fallback to user Pictures."""
        return self.local_wallpapers_dir or Path.home() / "Pictures"

    def to_dict(self) -> dict:
        """Convert to dict for JSON serialization."""
        return {
            "local_wallpapers_dir": (
                str(self.local_wallpapers_dir) if self.local_wallpapers_dir else None
            ),
            "wallhaven_api_key": self.wallhaven_api_key,
            "notifications_enabled": self.notifications_enabled,
            "upscaler_enabled": self.upscaler_enabled,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Config":
        """Create from dict for JSON deserialization."""
        local_dir_value = data.get("local_wallpapers_dir")
        api_key_value = data.get("wallhaven_api_key")
        notifications_value = data.get("notifications_enabled", True)
        upscaler_value = data.get("upscaler_enabled", False)

        local_dir = (
            Path(local_dir_value)
            if local_dir_value and isinstance(local_dir_value, (str, Path))
            else None
        )
        api_key = api_key_value if isinstance(api_key_value, str) else None
        notifications = notifications_value if isinstance(notifications_value, bool) else True
        upscaler = upscaler_value if isinstance(upscaler_value, bool) else False

        return cls(
            local_wallpapers_dir=local_dir,
            wallhaven_api_key=api_key,
            notifications_enabled=notifications,
            upscaler_enabled=upscaler,
        )
        api_key = api_key_value if isinstance(api_key_value, str) else None
        notifications = notifications_value if isinstance(notifications_value, bool) else True

        return cls(
            local_wallpapers_dir=local_dir,
            wallhaven_api_key=api_key,
            notifications_enabled=notifications,
        )

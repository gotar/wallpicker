"""Config domain model with validation."""

from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from .exceptions import ConfigError


@dataclass
class Config:
    """Application configuration domain model."""

    local_wallpapers_dir: Optional[Path] = None
    wallhaven_api_key: Optional[str] = None

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
            "local_wallpapers_dir": str(self.local_wallpapers_dir)
            if self.local_wallpapers_dir
            else None,
            "wallhaven_api_key": self.wallhaven_api_key,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Config":
        """Create from dict for JSON deserialization."""
        local_dir = data.get("local_wallpapers_dir")
        return cls(
            local_wallpapers_dir=Path(local_dir) if local_dir else None,
            wallhaven_api_key=data.get("wallhaven_api_key"),
        )

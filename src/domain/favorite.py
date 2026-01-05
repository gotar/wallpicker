"""Favorite domain model."""

from dataclasses import dataclass
from datetime import datetime
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .wallpaper import Wallpaper


@dataclass
class Favorite:
    """Favorite wallpaper domain entity."""

    wallpaper: "Wallpaper"
    added_at: datetime

    @property
    def days_since_added(self) -> int:
        """Calculate days since wallpaper was added to favorites."""
        return (datetime.now() - self.added_at).days

    @property
    def wallpaper_id(self) -> str:
        """Get wallpaper ID for serialization."""
        return self.wallpaper.id

    def to_dict(self) -> dict:
        """Convert to dict for JSON serialization."""
        return {
            "wallpaper": self.wallpaper.to_dict(),
            "added_at": self.added_at.isoformat(),
        }

    @classmethod
    def from_dict(cls, data: dict, wallpaper_class: type) -> "Favorite":
        """Create from dict for JSON deserialization."""
        from .wallpaper import Wallpaper

        wallpaper = Wallpaper.from_dict(data["wallpaper"])
        added_at = datetime.fromisoformat(data["added_at"])
        return cls(wallpaper=wallpaper, added_at=added_at)

"""Service interfaces for abstraction and testing."""

from abc import ABC, abstractmethod
from pathlib import Path

from domain.config import Config
from domain.wallpaper import Wallpaper


class IWallpaperService(ABC):
    """Interface for wallpaper search and retrieval."""

    @abstractmethod
    def search(
        self,
        query: str = "",
        page: int = 1,
        **kwargs,
    ) -> list[Wallpaper]:
        """Search for wallpapers.

        Args:
            query: Search query string
            page: Page number for pagination
            **kwargs: Additional search parameters

        Returns:
            List of Wallpaper objects
        """
        pass

    @abstractmethod
    def download(self, wallpaper: Wallpaper, dest: Path) -> bool:
        """Download wallpaper to destination.

        Args:
            wallpaper: Wallpaper object to download
            dest: Destination path

        Returns:
            True if successful, False otherwise
        """
        pass


class IFavoritesService(ABC):
    """Interface for favorites management."""

    @abstractmethod
    def add_favorite(self, wallpaper: Wallpaper) -> None:
        """Add wallpaper to favorites."""
        pass

    @abstractmethod
    def remove_favorite(self, wallpaper_id: str) -> None:
        """Remove wallpaper from favorites."""
        pass

    @abstractmethod
    def is_favorite(self, wallpaper_id: str) -> bool:
        """Check if wallpaper is in favorites."""
        pass

    @abstractmethod
    def get_favorites(self) -> list[Wallpaper]:
        """Get all favorite wallpapers."""
        pass

    @abstractmethod
    def search_favorites(self, query: str) -> list[Wallpaper]:
        """Search favorites by query."""
        pass


class IConfigService(ABC):
    """Interface for configuration management."""

    @abstractmethod
    def load_config(self) -> Config:
        """Load configuration from file."""
        pass

    @abstractmethod
    def save_config(self, config: Config) -> None:
        """Save configuration to file."""
        pass


class IThumbnailCache(ABC):
    """Interface for thumbnail caching."""

    @abstractmethod
    def get_thumbnail(self, url: str, size: str = "small") -> Path | None:
        """Get cached thumbnail or None if not cached."""
        pass

    @abstractmethod
    def cache_thumbnail(self, url: str, image_data: bytes, size: str = "small") -> Path:
        """Cache thumbnail image."""
        pass

    @abstractmethod
    def cleanup(self) -> int:
        """Clean up old thumbnails. Returns number of files removed."""
        pass


class IWallpaperSetter(ABC):
    """Interface for setting wallpapers."""

    @abstractmethod
    def set_wallpaper(self, path: Path) -> bool:
        """Set wallpaper to given path."""
        pass

    @abstractmethod
    def get_current_wallpaper(self) -> Path | None:
        """Get currently set wallpaper path."""
        pass

"""Favorites Service using domain models."""

import json
from datetime import datetime
from pathlib import Path

from rapidfuzz import process

from domain.exceptions import ServiceError
from domain.favorite import Favorite
from domain.wallpaper import Wallpaper
from services.base import BaseService


class FavoritesService(BaseService):
    """Service for managing favorite wallpapers using domain models."""

    def __init__(self, favorites_file: Path | None = None) -> None:
        """Initialize favorites service.

        Args:
            favorites_file: Path to favorites file (defaults to ~/.config/wallpicker/favorites.json)
        """
        super().__init__()
        self.favorites_file = (
            favorites_file or Path.home() / ".config" / "wallpicker" / "favorites.json"
        )
        self.favorites_dir = self.favorites_file.parent
        self._favorites: list[Favorite] = []

    def _ensure_favorites_file_exists(self) -> None:
        """Create favorites directory and file if they don't exist."""
        self.favorites_dir.mkdir(parents=True, exist_ok=True)

        if not self.favorites_file.exists():
            self.log_info(f"Creating empty favorites file at {self.favorites_file}")
            with open(self.favorites_file, "w") as f:
                json.dump([], f)

    def _load_favorites(self) -> list[Favorite]:
        """Load favorites from file.

        Returns:
            List of Favorite domain models
        """
        try:
            self._ensure_favorites_file_exists()

            if self.favorites_file.exists():
                with open(self.favorites_file) as f:
                    favorites_data = json.load(f)
                self._favorites = self._parse_favorites_data(favorites_data)
                self.log_debug(f"Loaded {len(self._favorites)} favorites")
            else:
                self._favorites = []
        except (json.JSONDecodeError, OSError) as e:
            self.log_error(
                f"Failed to load favorites from {self.favorites_file}: {e}",
                exc_info=True,
            )
            raise ServiceError(f"Failed to load favorites: {e}") from e

        return self._favorites

    def _parse_favorites_data(self, data) -> list[Favorite]:
        from domain.wallpaper import (
            Resolution,
            Wallpaper,
            WallpaperPurity,
            WallpaperSource,
        )

        if isinstance(data, list):
            return [Favorite.from_dict(item, Wallpaper) for item in data]

        if isinstance(data, dict):
            favorites = []
            for wallpaper_id, wallpaper_data in data.items():
                try:
                    resolution_str = wallpaper_data.get("resolution", "1920x1080")
                    if isinstance(resolution_str, str) and "x" in resolution_str:
                        w, h = resolution_str.split("x")
                        resolution = Resolution(width=int(w), height=int(h))
                    else:
                        resolution = Resolution(width=1920, height=1080)

                    source_str = wallpaper_data.get("source", "wallhaven")
                    if source_str == "local":
                        source = WallpaperSource.LOCAL
                    elif source_str == "favorite":
                        source = WallpaperSource.FAVORITE
                    else:
                        source = WallpaperSource.WALLHAVEN

                    purity_str = wallpaper_data.get("purity", "sfw").lower()
                    if purity_str == "sketchy":
                        purity = WallpaperPurity.SKETCHY
                    elif purity_str == "nsfw":
                        purity = WallpaperPurity.NSFW
                    else:
                        purity = WallpaperPurity.SFW

                    wallpaper = Wallpaper(
                        id=wallpaper_data.get("id", wallpaper_id),
                        url=wallpaper_data.get("url", ""),
                        path=wallpaper_data.get(
                            "path", wallpaper_data.get("thumbs_large", "")
                        ),
                        thumbs_large=wallpaper_data.get(
                            "thumbs_large", wallpaper_data.get("thumbs_small", "")
                        ),
                        thumbs_small=wallpaper_data.get("thumbs_small", ""),
                        resolution=resolution,
                        source=source,
                        category=wallpaper_data.get("category", "general"),
                        purity=purity,
                    )
                    favorite = Favorite(wallpaper=wallpaper, added_at=datetime.now())
                    favorites.append(favorite)
                except Exception as e:
                    self.log_warning(f"Failed to parse favorite {wallpaper_id}: {e}")
                    continue
            if favorites:
                self._save_favorites(favorites)
                self.log_info(f"Migrated {len(favorites)} favorites from old format")
            return favorites

        return []

    def add_favorite(self, wallpaper: Wallpaper) -> None:
        """Add wallpaper to favorites.

        Args:
            wallpaper: Wallpaper domain model to add
        """
        favorites = self._load_favorites()

        if self.is_favorite(wallpaper.id):
            self.log_debug(f"Wallpaper {wallpaper.id} already in favorites")
            return

        favorite = Favorite(wallpaper=wallpaper, added_at=datetime.now())
        favorites.append(favorite)
        self._save_favorites(favorites)
        self.log_info(f"Added wallpaper {wallpaper.id} to favorites")

    def remove_favorite(self, wallpaper_id: str) -> bool:
        """Remove wallpaper from favorites by ID.

        Args:
            wallpaper_id: ID of wallpaper to remove

        Returns:
            True if wallpaper was removed, False if not found
        """
        favorites = self._load_favorites()

        original_count = len(favorites)
        favorites = [f for f in favorites if f.wallpaper_id != wallpaper_id]

        if len(favorites) == original_count:
            self.log_warning(f"Wallpaper {wallpaper_id} not found in favorites")
            return False

        self._save_favorites(favorites)
        self.log_info(f"Removed wallpaper {wallpaper_id} from favorites")
        return True

    def is_favorite(self, wallpaper_id: str) -> bool:
        """Check if wallpaper is in favorites.

        Args:
            wallpaper_id: ID of wallpaper to check

        Returns:
            True if wallpaper is in favorites, False otherwise
        """
        favorites = self._load_favorites()
        return any(f.wallpaper_id == wallpaper_id for f in favorites)

    def get_favorites(self) -> list[Favorite]:
        """Get all favorite wallpapers.

        Returns:
            List of Favorite domain models
        """
        favorites = self._load_favorites()
        return favorites

    def search_favorites(self, query: str) -> list[Wallpaper]:
        """Search favorites by query using fuzzy matching.

        Args:
            query: Search query string

        Returns:
            List of matching Wallpaper domain models
        """
        favorites = self.get_favorites()

        if not query:
            return favorites

        # Build searchable strings from wallpaper data
        search_strings = [
            f"{w.wallpaper.id} {w.wallpaper.category} {w.wallpaper.url}"
            for w in favorites
        ]

        # Use rapidfuzz for fuzzy matching
        results = process.extract(query, search_strings, limit=len(favorites))
        matched_indices = [result[2] for result in results if result[1] >= 60]

        return [favorites[i].wallpaper for i in matched_indices]

    def _save_favorites(self, favorites: list[Favorite]) -> None:
        """Save favorites to file.

        Args:
            favorites: List of Favorite domain models

        Raises:
            ServiceError: If file cannot be written
        """
        try:
            favorites_data = [f.to_dict() for f in favorites]
            with open(self.favorites_file, "w") as f:
                json.dump(favorites_data, f, indent=4)
            self._favorites = favorites
            self.log_debug(f"Saved {len(favorites)} favorites to {self.favorites_file}")
        except OSError as e:
            self.log_error(
                f"Failed to save favorites to {self.favorites_file}: {e}", exc_info=True
            )
            raise ServiceError(f"Failed to save favorites: {e}") from e

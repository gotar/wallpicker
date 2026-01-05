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
                self._favorites = [
                    Favorite.from_dict(data, Wallpaper) for data in favorites_data
                ]
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

    def remove_favorite(self, wallpaper_id: str) -> None:
        """Remove wallpaper from favorites by ID.

        Args:
            wallpaper_id: ID of wallpaper to remove

        Raises:
            ServiceError: If wallpaper not found in favorites
        """
        favorites = self._load_favorites()

        favorites = [f for f in favorites if f.wallpaper_id != wallpaper_id]

        if len(favorites) == len(self._favorites):
            self.log_warning(f"Wallpaper {wallpaper_id} not found in favorites")
            return

        self._save_favorites(favorites)
        self.log_info(f"Removed wallpaper {wallpaper_id} from favorites")

    def is_favorite(self, wallpaper_id: str) -> bool:
        """Check if wallpaper is in favorites.

        Args:
            wallpaper_id: ID of wallpaper to check

        Returns:
            True if wallpaper is in favorites, False otherwise
        """
        favorites = self._load_favorites()
        return any(f.wallpaper_id == wallpaper_id for f in favorites)

    def get_favorites(self) -> list[Wallpaper]:
        """Get all favorite wallpapers.

        Returns:
            List of Wallpaper domain models
        """
        favorites = self._load_favorites()
        return [f.wallpaper for f in favorites]

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
        search_strings = [f"{w.id} {w.category} {w.url}" for w in favorites]

        # Use rapidfuzz for fuzzy matching
        results = process.extract(query, search_strings, limit=len(favorites))
        matched_indices = [result[2] for result in results if result[1] >= 60]

        return [favorites[i] for i in matched_indices]

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

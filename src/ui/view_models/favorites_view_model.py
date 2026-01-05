"""
ViewModel for favorites management
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from domain.favorite import Favorite
from domain.wallpaper import Wallpaper
from gi.repository import GObject
from services.favorites_service import FavoritesService
from services.wallpaper_setter import WallpaperSetter
from ui.view_models.base import BaseViewModel


class FavoritesViewModel(BaseViewModel):
    """ViewModel for favorites management"""

    def __init__(
        self,
        favorites_service: FavoritesService,
        wallpaper_setter: WallpaperSetter,
    ) -> None:
        super().__init__()
        self.favorites_service = favorites_service
        self.wallpaper_setter = wallpaper_setter

        # Observable state
        self._favorites: list[Wallpaper] = []
        self.search_query = ""

    @GObject.Property(type=object)
    def favorites(self) -> list[Wallpaper]:
        """Favorites list property"""
        return self._favorites

    @favorites.setter
    def favorites(self, value: list[Wallpaper]) -> None:
        self._favorites = value

    def load_favorites(self) -> None:
        """Load all favorites"""
        try:
            self.is_busy = True
            self.error_message = None

            favorites = self.favorites_service.get_favorites()
            self.favorites = favorites

        except Exception as e:
            self.error_message = f"Failed to load favorites: {e}"
            self.favorites = []
        finally:
            self.is_busy = False

    def search_favorites(self, query: str = "") -> None:
        """Search favorites"""
        try:
            self.is_busy = True
            self.error_message = None
            self.search_query = query

            if not query or query.strip() == "":
                # Load all favorites if query is empty
                self.load_favorites()
            else:
                results = self.favorites_service.search_wallpapers(query)
                self.favorites = results

        except Exception as e:
            self.error_message = f"Failed to search favorites: {e}"
            self.favorites = []
        finally:
            self.is_busy = False

    def add_favorite(
        self,
        wallpaper_id: str,
        full_url: str,
        path: str,
        source: str,
        tags: str,
    ) -> bool:
        """Add wallpaper to favorites"""
        try:
            self.is_busy = True
            self.error_message = None

            # Create wallpaper object for service
            from domain.wallpaper import Wallpaper

            wallpaper = Wallpaper(
                id=wallpaper_id,
                url=full_url,
                short_url=full_url,
                thumbs=None,
                path=path,
                purity="sfw",
                category="general",
                resolution=None,
                colors=None,
                tags=tags.split(",") if tags else [],
                file_size=0,
                file_type=0,
                created_at=None,
                views=0,
                favorites=0,
                source=source,
            )

            favorite = self.favorites_service.add_favorite(wallpaper)

            # Add to list if addition succeeded
            if favorite:
                self.favorites.append(favorite)

            return favorite is not None

        except Exception as e:
            self.error_message = f"Failed to add favorite: {e}"
            return False
        finally:
            self.is_busy = False

    def remove_favorite(self, favorite: Favorite) -> bool:
        """Remove wallpaper from favorites"""
        try:
            self.is_busy = True
            self.error_message = None

            result = self.favorites_service.remove_favorite(favorite.wallpaper_id)

            if result:
                # Remove from list if deletion succeeded
                if favorite in self.favorites:
                    self.favorites.remove(favorite)

            return result

        except Exception as e:
            self.error_message = f"Failed to remove favorite: {e}"
            return False
        finally:
            self.is_busy = False

    async def set_wallpaper(self, favorite: Favorite) -> bool:
        """Set wallpaper as desktop background"""
        try:
            self.is_busy = True
            self.error_message = None

            result = self.wallpaper_setter.set_wallpaper(favorite.path)

            return result

        except Exception as e:
            self.error_message = f"Failed to set wallpaper: {e}"
            return False
        finally:
            self.is_busy = False

    def is_favorite(self, wallpaper_id: str) -> bool:
        """Check if wallpaper is in favorites"""
        result = self.favorites_service.is_favorite(wallpaper_id)
        return result if result is not None else False

    def get_favorite(self, wallpaper_id: str) -> Favorite:
        """Get favorite by wallpaper ID"""
        favorite = self.favorites_service.is_favorite(wallpaper_id)
        if not favorite:
            raise ValueError(f"Wallpaper {wallpaper_id} not in favorites")
        # Find favorite in favorites list
        for fav in self.favorites:
            if fav.wallpaper_id == wallpaper_id:
                return fav
        raise ValueError(f"Wallpaper {wallpaper_id} not in favorites list")

    def refresh_favorites(self) -> None:
        """Refresh favorites list"""
        self.search_query = ""
        self.load_favorites()

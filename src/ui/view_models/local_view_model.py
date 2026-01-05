"""
ViewModel for local wallpaper browsing
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from datetime import datetime
from pathlib import Path

import sys

from gi.repository import GObject

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from domain.wallpaper import Wallpaper
from services.favorites_service import FavoritesService
from services.local_service import LocalWallpaper, LocalWallpaperService
from services.wallpaper_setter import WallpaperSetter
from ui.view_models.base import BaseViewModel


class LocalViewModel(BaseViewModel):
    """ViewModel for local wallpaper browsing"""

    def __init__(
        self,
        local_service: LocalWallpaperService,
        wallpaper_setter: WallpaperSetter,
        pictures_dir: Path | None = None,
    ) -> None:
        super().__init__()
        self.local_service = local_service
        self.wallpaper_setter = wallpaper_setter
        self.pictures_dir = pictures_dir
        self.favorites_service: FavoritesService | None = None

        self._wallpapers: list[LocalWallpaper] = []
        self.search_query = ""

    @GObject.Property(type=object)
    def wallpapers(self) -> list[LocalWallpaper]:
        """Wallpapers list property"""
        return self._wallpapers

    @wallpapers.setter
    def wallpapers(self, value: list[LocalWallpaper]) -> None:
        self._wallpapers = value

    def load_wallpapers(self, recursive: bool = True) -> None:
        """Load wallpapers from local directory"""
        try:
            self.is_busy = True
            self.error_message = None

            if self.pictures_dir:
                self.local_service.pictures_dir = self.pictures_dir

            wallpapers = self.local_service.get_wallpapers(recursive=recursive)
            self.wallpapers = wallpapers

        except Exception as e:
            self.error_message = f"Failed to load wallpapers: {e}"
            self.wallpapers = []
        finally:
            self.is_busy = False

    def search_wallpapers(self, query: str = "") -> None:
        """Search wallpapers"""
        try:
            self.is_busy = True
            self.error_message = None
            self.search_query = query

            if not query or query.strip() == "":
                # Load all wallpapers if query is empty
                self.load_wallpapers()
            else:
                results = self.local_service.search_wallpapers(query, self.wallpapers)
                self.wallpapers = results

        except Exception as e:
            self.error_message = f"Failed to search wallpapers: {e}"
            self.wallpapers = []
        finally:
            self.is_busy = False

    async def set_wallpaper(self, wallpaper: LocalWallpaper) -> bool:
        """Set wallpaper as desktop background"""
        try:
            self.is_busy = True
            self.error_message = None

            result = self.wallpaper_setter.set_wallpaper(str(wallpaper.path))

            return result

        except Exception as e:
            self.error_message = f"Failed to set wallpaper: {e}"
            return False
        finally:
            self.is_busy = False

    def delete_wallpaper(self, wallpaper: LocalWallpaper) -> bool:
        """Delete wallpaper from disk"""
        try:
            self.is_busy = True
            self.error_message = None

            result = self.local_service.delete_wallpaper(wallpaper.path)

            if result:
                # Remove from list if deletion succeeded
                if wallpaper in self.wallpapers:
                    self.wallpapers.remove(wallpaper)

            return result

        except Exception as e:
            self.error_message = f"Failed to delete wallpaper: {e}"
            return False
        finally:
            self.is_busy = False

    def refresh_wallpapers(self) -> None:
        """Refresh wallpaper list from disk"""
        self.search_query = ""
        self.load_wallpapers()

    async def add_to_favorites(self, wallpaper: LocalWallpaper) -> bool:
        if not self.favorites_service:
            self.error_message = "Favorites service not available"
            return False

        try:
            self.is_busy = True
            self.error_message = None

            self.favorites_service.add_favorite(wallpaper)

            return True

        except Exception as e:
            self.error_message = f"Failed to add to favorites: {e}"
            return False
        finally:
            self.is_busy = False

"""
ViewModel for local wallpaper browsing
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import sys
from pathlib import Path

from gi.repository import GObject  # noqa: E402

from domain.wallpaper import WallpaperPurity
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
        favorites_service: FavoritesService | None = None,
        config_service=None,
        thumbnail_cache=None,
    ) -> None:
        super().__init__(thumbnail_cache=thumbnail_cache)
        self.local_service = local_service
        self.wallpaper_setter = wallpaper_setter
        self.pictures_dir = pictures_dir
        self.favorites_service = favorites_service
        self.config_service = config_service
        self.notification_service = None

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

            if result:
                self.emit("wallpaper-set", wallpaper.filename)

            return result

        except Exception as e:
            self.error_message = f"Failed to set wallpaper: {e}"
            return False
        finally:
            self.is_busy = False

    def delete_wallpaper(self, wallpaper: LocalWallpaper) -> bool:
        try:
            self.is_busy = True
            self.error_message = None

            result = self.local_service.delete_wallpaper(wallpaper.path)

            if result:
                if wallpaper in self._wallpapers:
                    self._wallpapers.remove(wallpaper)
                    self.notify("wallpapers")
                if self.notification_service:
                    self.notification_service.notify_success(f"Deleted '{wallpaper.filename}'")

            return result

        except Exception as e:
            self.error_message = f"Failed to delete wallpaper: {e}"
            if self.notification_service:
                self.notification_service.notify_error(f"Failed to delete: {e}")
            return False
        finally:
            self.is_busy = False

    def refresh_wallpapers(self) -> None:
        """Refresh wallpaper list from disk"""
        self.search_query = ""
        self.load_wallpapers()

    def sort_by_name(self) -> None:
        """Sort wallpapers by filename (A-Z)"""
        self._wallpapers.sort(key=lambda w: w.filename.lower())
        self.notify("wallpapers")

    def sort_by_date(self) -> None:
        """Sort wallpapers by modification date (newest first)"""
        self._wallpapers.sort(key=lambda w: w.modified_time, reverse=True)
        self.notify("wallpapers")

    def set_pictures_dir(self, path: Path) -> None:
        self.pictures_dir = path
        self.local_service.pictures_dir = path
        if self.config_service:
            self.config_service.set_pictures_dir(path)
        self.load_wallpapers()

    def select_all(self) -> None:
        """Select all wallpapers."""
        self._selected_wallpapers_list = self.wallpapers.copy()
        self._update_selection_state()

    def add_to_favorites(self, wallpaper: LocalWallpaper) -> bool:
        if not self.favorites_service:
            self.error_message = "Favorites service not available"
            return False

        try:
            self.is_busy = True
            self.error_message = None

            wallpaper_id = f"local_{hash(wallpaper.path)}"
            if self.favorites_service.is_favorite(wallpaper_id):
                if self.notification_service:
                    self.notification_service.notify_warning("Already in favorites")
                return False

            from PIL import Image

            from domain.wallpaper import Resolution, Wallpaper, WallpaperSource

            width, height = 1920, 1080
            try:
                with Image.open(wallpaper.path) as img:
                    width, height = img.size
            except Exception:
                pass

            wallpaper_domain = Wallpaper(
                id=wallpaper_id,
                url=str(wallpaper.path),
                path=str(wallpaper.path),
                resolution=Resolution(width=width, height=height),
                source=WallpaperSource.LOCAL,
                category="general",
                purity=WallpaperPurity.SFW,
            )

            self.favorites_service.add_favorite(wallpaper_domain)

            if self.notification_service:
                self.notification_service.notify_success(
                    f"Added '{wallpaper.filename}' to favorites"
                )

            return True

        except Exception as e:
            self.error_message = f"Failed to add to favorites: {e}"
            if self.notification_service:
                self.notification_service.notify_error(f"Failed to add to favorites: {e}")
            return False
        finally:
            self.is_busy = False

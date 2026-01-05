"""Local ViewModel for managing local wallpaper browsing."""

import asyncio
from pathlib import Path
from typing import Optional

from gi.repository import Gio

from .base import BaseViewModel
from ..services.local_service_refactored import LocalService
from ..services.thumbnail_cache_refactored import ThumbnailCache
from ..services.favorites_service_refactored import FavoritesService
from ..services.wallpaper_setter_refactored import WallpaperSetter
from ..domain.wallpaper import Wallpaper


class LocalViewModel(BaseViewModel):
    """ViewModel for local wallpaper browsing."""

    __gtype_name__ = "LocalViewModel"

    def __init__(
        self,
        local_service: LocalService,
        thumbnail_cache: ThumbnailCache,
        favorites_service: FavoritesService,
        wallpaper_setter: WallpaperSetter,
    ) -> None:
        """Initialize Local ViewModel.

        Args:
            local_service: Local file browsing service
            thumbnail_cache: Thumbnail caching service
            favorites_service: Favorites management service
            wallpaper_setter: Wallpaper setting service
        """
        super().__init__()
        self._local_service = local_service
        self._thumbnail_cache = thumbnail_cache
        self._favorites_service = favorites_service
        self._wallpaper_setter = wallpaper_setter

        # Observable state
        self._wallpapers: Gio.ListStore = Gio.ListStore.new(Wallpaper.__gtype__)
        self._selected_wallpaper: Optional[Wallpaper] = None
        self._current_directory: Optional[Path] = None

    @GObject.Property(type=Gio.ListStore)
    def wallpapers(self) -> Gio.ListStore:
        """Get list of local wallpapers."""
        return self._wallpapers

    @GObject.Property(type=Wallpaper)
    def selected_wallpaper(self) -> Optional[Wallpaper]:
        """Get currently selected wallpaper."""
        return self._selected_wallpaper

    @selected_wallpaper.setter
    def selected_wallpaper(self, value: Optional[Wallpaper]) -> None:
        """Set selected wallpaper."""
        self._selected_wallpaper = value

    @GObject.Property(type=str)
    def current_directory(self) -> str:
        """Get current directory path."""
        return str(self._current_directory) if self._current_directory else ""

    async def load_wallpapers(self, directory: Path) -> None:
        """Load wallpapers from directory.

        Args:
            directory: Directory path to load wallpapers from
        """
        self.set_busy(True)
        self._current_directory = directory

        try:
            wallpapers = await self._local_service.search(directory=str(directory))

            self._wallpapers.remove_all()
            for wallpaper in wallpapers:
                self._wallpapers.append(wallpaper)

            self.notify("wallpapers")
            self.notify("current_directory")
        except Exception as e:
            self.error_message = str(e)
        finally:
            self.set_busy(False)

    async def delete_wallpaper(self) -> None:
        """Delete selected wallpaper (moves to trash)."""
        if not self._selected_wallpaper:
            return

        self.set_busy(True)

        try:
            await self._local_service.delete(self._selected_wallpaper.path)
            await self.load_wallpapers(self._current_directory)
        except Exception as e:
            self.error_message = str(e)
        finally:
            self.set_busy(False)

    async def set_wallpaper(self) -> None:
        """Set selected wallpaper as current wallpaper."""
        if not self._selected_wallpaper:
            return

        self.set_busy(True)

        try:
            path = Path(self._selected_wallpaper.path)
            await self._wallpaper_setter.set_wallpaper(path)
        except Exception as e:
            self.error_message = str(e)
        finally:
            self.set_busy(False)

    async def add_to_favorites(self) -> None:
        """Add selected wallpaper to favorites."""
        if not self._selected_wallpaper:
            return

        self.set_busy(True)

        try:
            self._favorites_service.add_favorite(self._selected_wallpaper)
        except Exception as e:
            self.error_message = str(e)
        finally:
            self.set_busy(False)

"""Favorites ViewModel for managing favorite wallpapers."""

import asyncio
from typing import Optional

from gi.repository import Gio

from .base import BaseViewModel
from ..services.favorites_service_refactored import FavoritesService
from ..services.wallpaper_setter_refactored import WallpaperSetter
from ..domain.wallpaper import Wallpaper


class FavoritesViewModel(BaseViewModel):
    """ViewModel for favorites management."""

    __gtype_name__ = "FavoritesViewModel"

    def __init__(
        self,
        favorites_service: FavoritesService,
        wallpaper_setter: WallpaperSetter,
    ) -> None:
        """Initialize Favorites ViewModel.

        Args:
            favorites_service: Favorites management service
            wallpaper_setter: Wallpaper setting service
        """
        super().__init__()
        self._favorites_service = favorites_service
        self._wallpaper_setter = wallpaper_setter

        # Observable state
        self._favorites: Gio.ListStore = Gio.ListStore.new(Wallpaper.__gtype__)
        self._selected_wallpaper: Optional[Wallpaper] = None
        self._search_query: str = ""

    @GObject.Property(type=Gio.ListStore)
    def favorites(self) -> Gio.ListStore:
        """Get list of favorite wallpapers."""
        return self._favorites

    @GObject.Property(type=Wallpaper)
    def selected_wallpaper(self) -> Optional[Wallpaper]:
        """Get currently selected wallpaper."""
        return self._selected_wallpaper

    @selected_wallpaper.setter
    def selected_wallpaper(self, value: Optional[Wallpaper]) -> None:
        """Set selected wallpaper."""
        self._selected_wallpaper = value

    @GObject.Property(type=str)
    def search_query(self) -> str:
        """Get current search query."""
        return self._search_query

    @search_query.setter
    def search_query(self, value: str) -> None:
        """Set search query and trigger search."""
        self._search_query = value
        asyncio.create_task(self.search_favorites(value))

    async def load_favorites(self) -> None:
        """Load all favorite wallpapers."""
        self.set_busy(True)

        try:
            favorites = self._favorites_service.get_favorites()

            self._favorites.remove_all()
            for wallpaper in favorites:
                self._favorites.append(wallpaper)

            self.notify("favorites")
        except Exception as e:
            self.error_message = str(e)
        finally:
            self.set_busy(False)

    async def search_favorites(self, query: str = "") -> None:
        """Search favorites by query.

        Args:
            query: Search query string
        """
        self.set_busy(True)
        self._search_query = query

        try:
            results = self._favorites_service.search_favorites(query)

            self._favorites.remove_all()
            for wallpaper in results:
                self._favorites.append(wallpaper)

            self.notify("favorites")
        except Exception as e:
            self.error_message = str(e)
        finally:
            self.set_busy(False)

    async def remove_from_favorites(self) -> None:
        """Remove selected wallpaper from favorites."""
        if not self._selected_wallpaper:
            return

        self.set_busy(True)

        try:
            self._favorites_service.remove_favorite(self._selected_wallpaper.id)
            await self.load_favorites()
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

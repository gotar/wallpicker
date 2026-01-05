"""Wallhaven ViewModel for managing Wallhaven API interactions."""

import asyncio
from typing import Optional

from gi.repository import Gio, GLib

from .base import BaseViewModel
from ..services.wallhaven_service_refactored import WallhavenService
from ..services.thumbnail_cache_refactored import ThumbnailCache
from ..services.favorites_service_refactored import FavoritesService
from ..domain.wallpaper import Wallpaper


class WallhavenViewModel(BaseViewModel):
    """ViewModel for Wallhaven wallpaper browsing."""

    __gtype_name__ = "WallhavenViewModel"

    def __init__(
        self,
        wallhaven_service: WallhavenService,
        thumbnail_cache: ThumbnailCache,
        favorites_service: FavoritesService,
    ) -> None:
        """Initialize Wallhaven ViewModel.

        Args:
            wallhaven_service: Wallhaven API service
            thumbnail_cache: Thumbnail caching service
            favorites_service: Favorites management service
        """
        super().__init__()
        self._wallhaven_service = wallhaven_service
        self._thumbnail_cache = thumbnail_cache
        self._favorites_service = favorites_service

        # Observable state
        self._wallpapers: Gio.ListStore = Gio.ListStore.new(Wallpaper.__gtype__)
        self._current_page: int = 1
        self._total_pages: int = 1
        self._query: str = ""
        self._selected_wallpaper: Optional[Wallpaper] = None

    @GObject.Property(type=Gio.ListStore)
    def wallpapers(self) -> Gio.ListStore:
        """Get list of wallpapers."""
        return self._wallpapers

    @GObject.Property(type=int)
    def current_page(self) -> int:
        """Get current page number."""
        return self._current_page

    @GObject.Property(type=int)
    def total_pages(self) -> int:
        """Get total pages."""
        return self._total_pages

    @GObject.Property(type=str)
    def query(self) -> str:
        """Get current search query."""
        return self._query

    @GObject.Property(type=Wallpaper)
    def selected_wallpaper(self) -> Optional[Wallpaper]:
        """Get currently selected wallpaper."""
        return self._selected_wallpaper

    @selected_wallpaper.setter
    def selected_wallpaper(self, value: Optional[Wallpaper]) -> None:
        """Set selected wallpaper."""
        self._selected_wallpaper = value

    async def search(self, query: str = "", page: int = 1) -> None:
        """Search for wallpapers.

        Args:
            query: Search query string
            page: Page number
        """
        self.set_busy(True)
        self._query = query
        self._current_page = page

        try:
            results = await self._wallhaven_service.search(
                query=query,
                page=page,
                categories="111",
                purity="sfw",
            )

            # Update wallpaper list
            self._wallpapers.remove_all()
            for wallpaper in results:
                self._wallpapers.append(wallpaper)

            self.notify("wallpapers")
        except Exception as e:
            self.error_message = str(e)
        finally:
            self.set_busy(False)

    async def next_page(self) -> None:
        """Load next page of results."""
        if self._current_page < self._total_pages:
            await self.search(query=self._query, page=self._current_page + 1)

    async def prev_page(self) -> None:
        """Load previous page of results."""
        if self._current_page > 1:
            await self.search(query=self._query, page=self._current_page - 1)

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

    async def set_wallpaper(self) -> None:
        """Set selected wallpaper as current wallpaper."""
        # This would need WallpaperSetterService
        pass

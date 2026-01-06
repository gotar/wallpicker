"""ViewModel for Wallhaven wallpaper browsing"""

import sys
from pathlib import Path

import gi

gi.require_version("Gtk", "4.0")
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from gi.repository import GObject

from domain.wallpaper import Wallpaper
from services.favorites_service import FavoritesService
from services.thumbnail_cache import ThumbnailCache
from services.wallhaven_service import WallhavenService
from ui.view_models.base import BaseViewModel


class WallhavenViewModel(BaseViewModel):
    """ViewModel for Wallhaven wallpaper browsing"""

    def __init__(
        self,
        wallhaven_service: WallhavenService,
        thumbnail_cache: ThumbnailCache,
        wallpaper_setter,
        config_service,
    ) -> None:
        super().__init__()
        self.wallhaven_service = wallhaven_service
        self.thumbnail_cache = thumbnail_cache
        self.wallpaper_setter = wallpaper_setter
        self.config_service = config_service
        self.favorites_service: FavoritesService | None = None

        self._wallpapers: list[Wallpaper] = []
        self._current_page = 1
        self._total_pages = 1
        self._search_query = ""
        self._category = "111"
        self._purity = "100"
        self._sorting = "toplist"
        self._order = "desc"
        self._resolution = ""

    @GObject.Property(type=object)
    def wallpapers(self) -> list[Wallpaper]:
        """Wallpapers list property"""
        return self._wallpapers

    @wallpapers.setter
    def wallpapers(self, value: list[Wallpaper]) -> None:
        self._wallpapers = value

    @GObject.Property(type=int, default=1)
    def current_page(self) -> int:
        """Current page property"""
        return self._current_page

    @current_page.setter
    def current_page(self, value: int) -> None:
        self._current_page = value

    @GObject.Property(type=int, default=1)
    def total_pages(self) -> int:
        """Total pages property"""
        return self._total_pages

    @total_pages.setter
    def total_pages(self, value: int) -> None:
        self._total_pages = value

    @GObject.Property(type=str, default="")
    def search_query(self) -> str:
        """Search query property"""
        return self._search_query

    @search_query.setter
    def search_query(self, value: str) -> None:
        self._search_query = value

    @GObject.Property(type=str, default="111")
    def category(self) -> str:
        """Category property"""
        return self._category

    @category.setter
    def category(self, value: str) -> None:
        self._category = value

    @GObject.Property(type=str, default="100")
    def purity(self) -> str:
        """Purity property"""
        return self._purity

    @purity.setter
    def purity(self, value: str) -> None:
        self._purity = value

    @GObject.Property(type=str, default="toplist")
    def sorting(self) -> str:
        """Sorting property"""
        return self._sorting

    @sorting.setter
    def sorting(self, value: str) -> None:
        self._sorting = value

    @GObject.Property(type=str, default="desc")
    def order(self) -> str:
        """Order property"""
        return self._order

    @order.setter
    def order(self, value: str) -> None:
        self._order = value

    @GObject.Property(type=str, default="")
    def resolution(self) -> str:
        """Resolution property"""
        return self._resolution

    @resolution.setter
    def resolution(self, value: str) -> None:
        self._resolution = value

    async def load_initial_wallpapers(self) -> None:
        """Load initial wallpapers with current parameters"""
        await self.search_wallpapers(
            query=self.search_query,
            page=1,
            category=self.category,
            purity="100",
            sorting=self.sorting,
            order="desc",
            resolution="",
        )

    async def search_wallpapers(
        self,
        query: str = "",
        page: int = 1,
        category: str = "111",
        purity: str = "100",
        sorting: str = "toplist",
        order: str = "desc",
        resolution: str = "",
    ) -> None:
        """Search wallpapers on Wallhaven"""
        try:
            self.is_busy = True
            self.error_message = None
            self.search_query = query
            self.category = category
            self.purity = purity
            self.sorting = sorting
            self.order = order
            self.resolution = resolution

            wallpapers, meta = await self.wallhaven_service.search(
                query=query,
                page=page,
                categories=category,
                purity=purity,
                sorting=sorting,
                order=order,
                atleast=resolution,
            )

            self.wallpapers = wallpapers
            self.current_page = meta.get("current_page", page)
            self.total_pages = meta.get("last_page", page + 1)

        except Exception as e:
            self.error_message = f"Failed to search wallpapers: {e}"
            self.wallpapers = []
        finally:
            self.is_busy = False

    async def load_next_page(self) -> None:
        """Load next page of wallpapers"""
        if self.current_page < self.total_pages:
            await self.search_wallpapers(
                query=self.search_query,
                page=self.current_page + 1,
                category=self.category,
                purity=self.purity,
                sorting=self.sorting,
                order=self.order,
                resolution=self.resolution,
            )

    async def load_prev_page(self) -> None:
        """Load previous page of wallpapers"""
        if self.current_page > 1:
            await self.search_wallpapers(
                query=self.search_query,
                page=self.current_page - 1,
                category=self.category,
                purity=self.purity,
                sorting=self.sorting,
                order=self.order,
                resolution=self.resolution,
            )

    def has_next_page(self) -> bool:
        """Check if there's a next page"""
        return self.current_page < self.total_pages

    def has_prev_page(self) -> bool:
        """Check if there's a previous page"""
        return self.current_page > 1

    def can_load_next_page(self) -> bool:
        """Check if there's a next page available"""
        return self.current_page < self.total_pages

    def can_load_prev_page(self) -> bool:
        """Check if there's a previous page available"""
        return self.current_page > 1

    def can_navigate(self) -> bool:
        """Check if pagination navigation is available"""
        return self.has_next_page() or self.has_prev_page()

    async def set_wallpaper(self, wallpaper: Wallpaper) -> bool:
        """Set wallpaper as desktop background."""
        try:
            self.is_busy = True
            self.error_message = None

            if not wallpaper.path:
                await self.download_wallpaper(wallpaper)

            if wallpaper.path:
                result = self.wallpaper_setter.set_wallpaper(wallpaper.path)
                if result:
                    filename = Path(wallpaper.path).name if wallpaper.path else wallpaper.id
                    self.emit("wallpaper-set", filename)
                return result

            return False

        except Exception as e:
            self.error_message = f"Failed to set wallpaper: {e}"
            return False
        finally:
            self.is_busy = False

    async def add_to_favorites(self, wallpaper: Wallpaper) -> bool:
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

    async def download_wallpaper(self, wallpaper: Wallpaper) -> None:
        config = self.config_service.get_config()

        if not wallpaper.url:
            return

        try:
            self.is_busy = True

            filename = f"{wallpaper.id}.{wallpaper.url.rsplit('.', 1)[-1]}"
            dest_path = config.local_wallpapers_dir / filename

            session = await self.wallhaven_service._get_session()

            async with session.get(wallpaper.url) as response:
                if response.status != 200:
                    raise Exception(f"Download failed: {response.status}")

                content = await response.read()

            dest_path.parent.mkdir(parents=True, exist_ok=True)

            with open(dest_path, "wb") as f:
                f.write(content)

            wallpaper.path = str(dest_path)
            self.wallpapers = self.wallpapers.copy()
            index = self.wallpapers.index(wallpaper)
            self.wallpapers[index] = wallpaper
            self.notify("wallpapers")

        except Exception as e:
            print(f"Download error: {e}")
            import traceback

            traceback.print_exc()
        finally:
            self.is_busy = False

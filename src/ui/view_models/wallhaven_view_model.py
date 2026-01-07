"""ViewModel for Wallhaven wallpaper browsing"""

import sys
from pathlib import Path

import gi

gi.require_version("Gtk", "4.0")
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from gi.repository import GObject  # noqa: E402

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
        super().__init__(thumbnail_cache=thumbnail_cache)
        self.wallhaven_service = wallhaven_service
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
        self._top_range = ""
        self._ratios = ""
        self._colors = ""
        self._resolutions = ""
        self._seed = ""

    @GObject.Property(type=object)
    def wallpapers(self) -> list[Wallpaper]:
        return self._wallpapers

    @wallpapers.setter
    def wallpapers(self, value: list[Wallpaper]) -> None:
        self._wallpapers = value

    @GObject.Property(type=int, default=1)
    def current_page(self) -> int:
        return self._current_page

    @current_page.setter
    def current_page(self, value: int) -> None:
        self._current_page = value

    @GObject.Property(type=int, default=1)
    def total_pages(self) -> int:
        return self._total_pages

    @total_pages.setter
    def total_pages(self, value: int) -> None:
        self._total_pages = value

    @GObject.Property(type=str, default="")
    def search_query(self) -> str:
        return self._search_query

    @search_query.setter
    def search_query(self, value: str) -> None:
        self._search_query = value

    @GObject.Property(type=str, default="111")
    def category(self) -> str:
        return self._category

    @category.setter
    def category(self, value: str) -> None:
        self._category = value

    @GObject.Property(type=str, default="100")
    def purity(self) -> str:
        return self._purity

    @purity.setter
    def purity(self, value: str) -> None:
        self._purity = value

    @GObject.Property(type=str, default="toplist")
    def sorting(self) -> str:
        return self._sorting

    @sorting.setter
    def sorting(self, value: str) -> None:
        self._sorting = value

    @GObject.Property(type=str, default="desc")
    def order(self) -> str:
        return self._order

    @order.setter
    def order(self, value: str) -> None:
        self._order = value

    @GObject.Property(type=str, default="")
    def resolution(self) -> str:
        return self._resolution

    @resolution.setter
    def resolution(self, value: str) -> None:
        self._resolution = value

    @GObject.Property(type=str, default="")
    def top_range(self) -> str:
        return self._top_range

    @top_range.setter
    def top_range(self, value: str) -> None:
        self._top_range = value

    @GObject.Property(type=str, default="")
    def ratios(self) -> str:
        return self._ratios

    @ratios.setter
    def ratios(self, value: str) -> None:
        self._ratios = value

    @GObject.Property(type=str, default="")
    def colors(self) -> str:
        return self._colors

    @colors.setter
    def colors(self, value: str) -> None:
        self._colors = value

    @GObject.Property(type=str, default="")
    def resolutions(self) -> str:
        return self._resolutions

    @resolutions.setter
    def resolutions(self, value: str) -> None:
        self._resolutions = value

    @GObject.Property(type=str, default="")
    def seed(self) -> str:
        return self._seed

    @seed.setter
    def seed(self, value: str) -> None:
        self._seed = value

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
            top_range=self.top_range,
            ratios=self.ratios,
            colors=self.colors,
            resolutions=self.resolutions,
            seed=self.seed,
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
        top_range: str = "",
        ratios: str = "",
        colors: str = "",
        resolutions: str = "",
        seed: str = "",
        append_results: bool = False,
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
            self.top_range = top_range
            self.ratios = ratios
            self.colors = colors
            self.resolutions = resolutions
            self.seed = seed

            wallpapers, meta = await self.wallhaven_service.search(
                query=query,
                page=page,
                categories=category,
                purity=purity,
                sorting=sorting,
                order=order,
                atleast=resolution,
                top_range=top_range,
                ratios=ratios,
                colors=colors,
                resolutions=resolutions,
                seed=seed,
            )

            if append_results and self.wallpapers:
                self.wallpapers = self.wallpapers + wallpapers
            else:
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
                top_range=self.top_range,
                ratios=self.ratios,
                colors=self.colors,
                resolutions=self.resolutions,
                seed=self.seed,
                append_results=True,
            )

    async def load_prev_page(self) -> None:
        """Load previous page of wallpapers"""
        target_page = self.current_page - 1
        if target_page >= 1:
            await self.search_wallpapers(
                query=self.search_query,
                page=target_page,
                category=self.category,
                purity=self.purity,
                sorting=self.sorting,
                order=self.order,
                resolution=self.resolution,
                top_range=self.top_range,
                ratios=self.ratios,
                colors=self.colors,
                resolutions=self.resolutions,
                seed=self.seed,
                append_results=True,
            )

    def has_next_page(self) -> bool:
        """Check if there's a next page"""
        return self.current_page < self.total_pages

    def has_prev_page(self) -> bool:
        """Check if there's a previous page"""
        return self.current_page > 1

    def select_all(self) -> None:
        """Select all wallpapers."""
        self._selected_wallpapers_list = self.wallpapers.copy()
        self._update_selection_state()

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

            local_path = None

            if wallpaper.path and Path(wallpaper.path).exists():
                local_path = wallpaper.path
            else:
                local_path = await self.download_wallpaper(wallpaper)

            if local_path:
                result = self.wallpaper_setter.set_wallpaper(local_path)
                if result:
                    filename = Path(local_path).name
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

            if self.favorites_service.is_favorite(wallpaper.id):
                return False

            self.favorites_service.add_favorite(wallpaper)

            if self.notification_service:
                self.notification_service.notify_success("Added to favorites")

            return True

        except Exception as e:
            self.error_message = f"Failed to add to favorites: {e}"
            if self.notification_service:
                self.notification_service.notify_error(f"Failed to add to favorites: {e}")
            return False
        finally:
            self.is_busy = False

    async def download_wallpaper(self, wallpaper: Wallpaper) -> str | None:
        """Download wallpaper and return the local path, or None on failure."""
        config = self.config_service.get_config()

        if not wallpaper.url:
            return None

        try:
            self.is_busy = True

            filename = f"{wallpaper.id}.{wallpaper.url.rsplit('.', 1)[-1]}"
            dest_path = config.local_wallpapers_dir / filename

            success = await self.wallhaven_service.download(wallpaper, dest_path)

            if success:
                wallpaper.path = str(dest_path)
                self.wallpapers = self.wallpapers.copy()
                index = self.wallpapers.index(wallpaper)
                self.wallpapers[index] = wallpaper
                self.notify("wallpapers")
                return str(dest_path)
            else:
                self.error_message = f"Failed to download wallpaper {wallpaper.id}"
                return None

        except Exception as e:
            print(f"Download error: {e}")
            import traceback

            traceback.print_exc()
            self.error_message = f"Download error: {e}"
            return None
        finally:
            self.is_busy = False

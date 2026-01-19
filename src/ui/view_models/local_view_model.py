"""
ViewModel for local wallpaper browsing
"""

import asyncio
import hashlib
import shutil
import sys
from collections import deque
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from gi.repository import GLib, GObject  # noqa: E402

from core.asyncio_integration import schedule_async  # noqa: E402
from domain.wallpaper import WallpaperPurity  # noqa: E402
from services.favorites_service import FavoritesService  # noqa: E402
from services.local_service import LocalWallpaper, LocalWallpaperService  # noqa: E402
from services.wallpaper_setter import WallpaperSetter  # noqa: E402
from ui.view_models.base import BaseViewModel  # noqa: E402


class LocalViewModel(BaseViewModel):
    """ViewModel for local wallpaper browsing"""

    __gsignals__ = {
        "upscaling-complete": (GObject.SignalFlags.RUN_FIRST, None, (bool, str, str)),
        "upscaling-queue-changed": (GObject.SignalFlags.RUN_FIRST, None, (int, int)),
    }

    # Max concurrent upscaling operations
    MAX_CONCURRENT_UPSCALING = 2

    def __init__(
        self,
        local_service: LocalWallpaperService,
        wallpaper_setter: WallpaperSetter,
        pictures_dir: Path | None = None,
        favorites_service: FavoritesService | None = None,
        config_service=None,
    ) -> None:
        super().__init__()
        self.local_service = local_service
        self.wallpaper_setter = wallpaper_setter
        self.pictures_dir = pictures_dir
        self.favorites_service = favorites_service
        self.config_service = config_service
        self._wallpapers: list[LocalWallpaper] = []
        self.search_query = ""
        self._current_wallpaper_path: str | None = None

        # Upscaling queue system
        self._upscale_queue: deque = deque()
        self._active_count = 0
        self._completed_count = 0
        self._failed_count = 0

    @GObject.Property(type=object)
    def wallpapers(self) -> list[LocalWallpaper]:
        """Wallpapers list property"""
        return self._wallpapers

    @wallpapers.setter
    def wallpapers(self, value: list[LocalWallpaper]) -> None:
        self._wallpapers = value

    def _set_wallpapers(self, wallpapers: list[LocalWallpaper]) -> bool:
        self._wallpapers = wallpapers
        self.notify("wallpapers")
        return False

    @GObject.Property(type=int)
    def upscaling_queue_size(self) -> int:
        """Number of items waiting in upscaling queue"""
        return len(self._upscale_queue)

    @GObject.Property(type=int)
    def upscaling_active_count(self) -> int:
        """Number of currently active upscaling operations"""
        return self._active_count

    @GObject.Property(type=int)
    def upscaling_total_count(self) -> int:
        """Total items being processed (queue + active)"""
        return len(self._upscale_queue) + self._active_count

    @GObject.Property(type=str)
    def current_wallpaper_path(self) -> str | None:
        """Path of currently set wallpaper (resolved from symlink)."""
        return self._current_wallpaper_path

    def refresh_current_wallpaper(self):
        """Refresh current wallpaper from symlink."""
        self._current_wallpaper_path = self.wallpaper_setter.get_current_wallpaper()
        self.notify("current-wallpaper-path")

    def _emit_queue_changed(self):
        """Emit signal when queue status changes."""
        self.notify("upscaling-queue-size")
        self.notify("upscaling-active-count")
        self.notify("upscaling-total-count")
        self.emit(
            "upscaling-queue-changed",
            len(self._upscale_queue),
            self._active_count,
        )

    async def load_wallpapers(self, recursive: bool = True) -> None:
        try:
            self.is_busy = True
            self.error_message = None

            if self.pictures_dir:
                self.local_service.pictures_dir = self.pictures_dir

            wallpapers = await self.local_service.get_wallpapers_async(
                recursive=recursive
            )
            self.search_query = ""
            GLib.idle_add(self._set_wallpapers, wallpapers)

        except Exception as e:
            self.error_message = f"Failed to load wallpapers: {e}"
            GLib.idle_add(self._set_wallpapers, [])
        finally:
            self.is_busy = False

    async def search_wallpapers(self, query: str = "") -> None:
        try:
            self.is_busy = True
            self.error_message = None
            self.search_query = query

            if not query or query.strip() == "":
                await self.load_wallpapers()
            else:
                results = await self.local_service.search_wallpapers_async(
                    query, self.wallpapers
                )
                GLib.idle_add(self._set_wallpapers, results)

        except Exception as e:
            self.error_message = f"Failed to search wallpapers: {e}"
            GLib.idle_add(self._set_wallpapers, [])
        finally:
            self.is_busy = False

    async def set_wallpaper(self, wallpaper: LocalWallpaper) -> tuple[bool, str]:
        try:
            self.is_busy = True
            self.error_message = None
            result = await self.wallpaper_setter.set_wallpaper_async(
                str(wallpaper.path)
            )
            if result:
                return True, "Wallpaper set successfully"
            return False, "Failed to set wallpaper"
        except Exception as e:
            self.error_message = str(e)
            return False, str(e)
        finally:
            self.is_busy = False

    async def delete_wallpaper(self, wallpaper: LocalWallpaper) -> tuple[bool, str]:
        try:
            self.is_busy = True
            self.error_message = None

            result = await self.local_service.delete_wallpaper_async(wallpaper.path)

            if result:
                if wallpaper in self._wallpapers:
                    self._wallpapers.remove(wallpaper)
                    self.notify("wallpapers")
                return True, f"Deleted '{wallpaper.filename}'"

            return False, "Failed to delete"

        except Exception as e:
            self.error_message = f"Failed to delete wallpaper: {e}"
            return False, str(e)
        finally:
            self.is_busy = False

    async def refresh_wallpapers(self) -> None:
        self.search_query = ""
        await self.load_wallpapers()

    def sort_by_name(self) -> None:
        """Sort wallpapers by filename (A-Z)"""
        self._wallpapers.sort(key=lambda w: w.filename.lower())
        self.notify("wallpapers")

    def sort_by_date(self) -> None:
        """Sort wallpapers by modification date (newest first)"""
        self._wallpapers.sort(key=lambda w: w.modified_time, reverse=True)
        self.notify("wallpapers")

    def sort_by_resolution(self) -> None:
        """Sort wallpapers by resolution (largest first)"""

        def get_resolution_pixels(wp):
            if wp.resolution and isinstance(wp.resolution, str):
                parts = wp.resolution.split("x")
                if len(parts) == 2:
                    try:
                        return int(parts[0]) * int(parts[1])
                    except ValueError:
                        return 0
            return 0

        self._wallpapers.sort(key=get_resolution_pixels, reverse=True)
        self.notify("wallpapers")

    def filter_wallpapers(self, filters: dict) -> None:
        schedule_async(self._apply_filters_async(filters))

    async def _apply_filters_async(self, filters: dict) -> None:
        try:
            self.is_busy = True

            all_wallpapers = await self.local_service.get_wallpapers_async(
                recursive=True
            )

            if self.search_query:
                all_wallpapers = await self.local_service.search_wallpapers_async(
                    self.search_query, all_wallpapers
                )

            filtered = self._apply_resolution_filter(all_wallpapers, filters)
            filtered = self._apply_aspect_filter(filtered, filters)

            GLib.idle_add(self._set_wallpapers, filtered)
        except Exception as e:
            self.error_message = f"Failed to filter: {e}"
        finally:
            self.is_busy = False

    def _apply_resolution_filter(
        self, wallpapers: list[LocalWallpaper], filters: dict
    ) -> list[LocalWallpaper]:
        min_resolution = filters.get("resolution")
        if not min_resolution:
            return wallpapers

        try:
            min_w, min_h = map(int, min_resolution.split("x"))
        except ValueError:
            return wallpapers

        result = []
        for wp in wallpapers:
            if not wp.resolution:
                continue
            try:
                parts = wp.resolution.split("x")
                if len(parts) == 2:
                    w, h = int(parts[0]), int(parts[1])
                    if w >= min_w and h >= min_h:
                        result.append(wp)
            except ValueError:
                continue
        return result

    def _apply_aspect_filter(
        self, wallpapers: list[LocalWallpaper], filters: dict
    ) -> list[LocalWallpaper]:
        ratio_filter = filters.get("ratios")
        if not ratio_filter:
            return wallpapers

        ratio_map = {
            "16x9": (16, 9),
            "16x10": (16, 10),
            "21x9": (21, 9),
            "9x16": (9, 16),
            "1x1": (1, 1),
        }

        target = ratio_map.get(ratio_filter)
        if not target:
            return wallpapers

        target_ratio = target[0] / target[1]
        tolerance = 0.1

        result = []
        for wp in wallpapers:
            if not wp.resolution:
                continue
            try:
                parts = wp.resolution.split("x")
                if len(parts) == 2:
                    w, h = int(parts[0]), int(parts[1])
                    if h == 0:
                        continue
                    wp_ratio = w / h
                    if abs(wp_ratio - target_ratio) <= tolerance:
                        result.append(wp)
            except ValueError:
                continue
        return result

    async def set_pictures_dir(self, path: Path) -> None:
        self.pictures_dir = path
        self.local_service.pictures_dir = path
        if self.config_service:
            await asyncio.to_thread(self.config_service.set_pictures_dir, path)
        await self.load_wallpapers()

    def select_all(self) -> None:
        """Select all wallpapers."""
        self._selected_wallpapers_list = self.wallpapers.copy()
        self._update_selection_state()

    async def add_to_favorites(self, wallpaper: LocalWallpaper) -> tuple[bool, str]:
        if self.is_busy:
            return False, "Operation in progress"

        if not self.favorites_service:
            self.error_message = "Favorites service not available"
            return False, "Favorites service not available"

        try:
            self.is_busy = True
            self.error_message = None

            path_hash = hashlib.sha256(str(wallpaper.path).encode()).hexdigest()[:16]
            wallpaper_id = f"local_{path_hash}"
            if await asyncio.to_thread(
                self.favorites_service.is_favorite, wallpaper_id
            ):
                return False, "Already in favorites"

            from domain.wallpaper import Resolution, Wallpaper, WallpaperSource

            width, height = await asyncio.to_thread(
                self._get_image_size, wallpaper.path
            )

            wallpaper_domain = Wallpaper(
                id=wallpaper_id,
                url=str(wallpaper.path),
                path=str(wallpaper.path),
                resolution=Resolution(width=width, height=height),
                source=WallpaperSource.LOCAL,
                category="general",
                purity=WallpaperPurity.SFW,
            )

            await asyncio.to_thread(
                self.favorites_service.add_favorite, wallpaper_domain
            )
            return True, f"Added '{wallpaper.filename}' to favorites"

        except Exception as e:
            self.error_message = f"Failed to add to favorites: {e}"
            return False, str(e)
        finally:
            self.is_busy = False

    def _get_image_size(self, path: Path) -> tuple[int, int]:
        width, height = 1920, 1080
        try:
            from PIL import Image

            with Image.open(path) as img:
                width, height = img.size
        except (OSError, ValueError):
            pass
        return width, height

    def queue_upscale(self, wallpaper: LocalWallpaper) -> tuple[bool, str]:
        """Queue a wallpaper for upscaling. Non-blocking, supports concurrent operations.

        Args:
            wallpaper: The wallpaper to upscale

        Returns:
            Tuple of (queued, message)
        """
        # Add to queue
        self._upscale_queue.append(wallpaper)

        # Get queue size BEFORE processing (item is still in queue)
        queue_size = len(self._upscale_queue)

        # Emit queue changed (show toast will use this)
        self._emit_queue_changed()

        # Try to start processing if we have capacity
        self._process_upscale_queue()

        if queue_size == 1:
            return True, "Upscaling started..."
        else:
            return True, f"Added to queue ({queue_size - self._active_count} waiting)"

    def _process_upscale_queue(self):
        """Process items from the upscaling queue."""
        while (
            self._upscale_queue and self._active_count < self.MAX_CONCURRENT_UPSCALING
        ):
            wallpaper = self._upscale_queue.popleft()
            self._active_count += 1
            self._emit_queue_changed()

            # Start async upscaling
            schedule_async(self._run_upscale_async(wallpaper))

    async def _run_upscale_async(self, wallpaper: LocalWallpaper) -> tuple[bool, str]:
        """Run the actual upscaling process asynchronously.

        Args:
            wallpaper: The wallpaper to upscale

        Returns:
            Tuple of (success, message)
        """
        try:
            # Check if waifu2x is available
            if not shutil.which("waifu2x-ncnn-vulkan"):
                result = False, "waifu2x-ncnn-vulkan not found in PATH"
                self._finish_upscale(wallpaper, *result)
                return result

            # realesrgan-ncnn-vulkan models directory
            # model_path = Path.home() / ".local/lib/realesrgan-ncnn-vulkan/models"

            # Create temp file for upscaled image
            temp_path = (
                wallpaper.path.parent
                / f"{wallpaper.path.stem}_upscaled{wallpaper.path.suffix}"
            )

            try:
                # Use waifu2x (no RADV driver bugs) with CPU mode
                process = await asyncio.create_subprocess_exec(
                    "waifu2x-ncnn-vulkan",
                    "-i",
                    str(wallpaper.path),
                    "-o",
                    str(temp_path),
                    "-s",
                    "2",
                    "-n",
                    "1",
                    "-g",
                    "-1",  # CPU mode
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                )
                stdout, stderr = await process.communicate()

                if process.returncode != 0:
                    stderr_text = stderr.decode("utf-8", errors="replace").strip()
                    result = (
                        False,
                        f"Upscaling failed: {stderr_text or 'Unknown error'}",
                    )
                    self._finish_upscale(wallpaper, *result)
                    return result

                # Check if output was created
                if not temp_path.exists():
                    result = False, "Upscaling produced no output"
                    self._finish_upscale(wallpaper, *result)
                    return result

                # Get original file size
                original_size = wallpaper.path.stat().st_size

                # Replace original with upscaled version
                backup_path = (
                    wallpaper.path.parent
                    / f"{wallpaper.path.stem}_backup{wallpaper.path.suffix}"
                )

                try:
                    # Verify upscaled image is valid before replacing
                    from PIL import Image

                    try:
                        with Image.open(temp_path) as img:
                            width, height = img.size
                            if width < 100 or height < 100:
                                raise ValueError(
                                    f"Invalid dimensions: {width}x{height}"
                                )
                    except Exception as verify_error:
                        if temp_path.exists():
                            temp_path.unlink()
                        result = False, f"Upscaled image is invalid: {verify_error}"
                        self._finish_upscale(wallpaper, *result)
                        return result

                    # Move original to backup
                    wallpaper.path.rename(backup_path)
                    # Move upscaled to original location
                    temp_path.rename(wallpaper.path)
                    # Remove backup
                    backup_path.unlink()
                except OSError as e:
                    if temp_path.exists():
                        temp_path.unlink()
                    result = False, f"Failed to replace file: {e}"
                    self._finish_upscale(wallpaper, *result)
                    return result

                new_size = wallpaper.path.stat().st_size
                size_improvement = f"({original_size / 1024 / 1024:.1f} MB → {new_size / 1024 / 1024:.1f} MB)"
                result = True, f"Upscaled 2x {size_improvement}"
                self._finish_upscale(wallpaper, *result)
                return result

            except asyncio.CancelledError:
                if temp_path.exists():
                    temp_path.unlink()
                result = False, "Upscaling cancelled"
                self._finish_upscale(wallpaper, *result)
                raise
            except Exception as e:
                if temp_path.exists():
                    temp_path.unlink()
                result = False, str(e)
                self._finish_upscale(wallpaper, *result)
                raise

        finally:
            # This will be called by _finish_upscale
            pass

    def _finish_upscale(self, wallpaper: LocalWallpaper, success: bool, message: str):
        """Handle completion of an upscaling operation."""
        self._active_count -= 1
        if success:
            self._completed_count += 1
        else:
            self._failed_count += 1

        self._emit_queue_changed()
        self.emit("upscaling-complete", success, message, str(wallpaper.path))

        # Process next item in queue
        self._process_upscale_queue()

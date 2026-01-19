"""
Local Wallpaper Service
Handles browsing, searching, and deleting local wallpapers
"""

import asyncio
import logging
from pathlib import Path

from gi.repository import GObject
from rapidfuzz import fuzz, process
from send2trash import send2trash


class LocalWallpaper(GObject.Object):
    __gtype_name__ = "LocalWallpaper"

    def __init__(
        self,
        path: Path,
        filename: str,
        size: int,
        modified_time: float,
        resolution=None,
    ):
        super().__init__()
        self.path = path
        self.filename = filename
        self.size = size
        self.modified_time = modified_time
        self._resolution = resolution

    @property
    def resolution(self):
        if self._resolution is None:
            self._load_resolution()
        return self._resolution

    @resolution.setter
    def resolution(self, value):
        self._resolution = value

    def _load_resolution(self):
        try:
            from PIL import Image

            with Image.open(self.path) as img:
                width, height = img.size
                self._resolution = f"{width}x{height}"
        except Exception:
            self._resolution = ""


class LocalWallpaperService:
    """Service for managing local wallpapers"""

    SUPPORTED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".bmp", ".gif"}

    def __init__(self, pictures_dir: Path | None = None):
        self.pictures_dir = pictures_dir or Path.home() / "Pictures"
        if not self.pictures_dir.exists():
            self.pictures_dir = Path.home() / "Pictures"

    def get_wallpapers(self, recursive: bool = True) -> list[LocalWallpaper]:
        return self._get_wallpapers_sync(recursive=recursive)

    async def get_wallpapers_async(
        self, recursive: bool = True
    ) -> list[LocalWallpaper]:
        return await asyncio.to_thread(self._get_wallpapers_sync, recursive)

    def _get_wallpapers_sync(self, recursive: bool = True) -> list[LocalWallpaper]:
        """
        Get list of wallpapers from Pictures directory

        Args:
            recursive: Search subdirectories recursively

        Returns:
            List of LocalWallpaper objects
        """
        wallpapers = []

        try:
            if recursive:
                pattern = "**/*"
            else:
                pattern = "*"

            for file_path in self.pictures_dir.glob(pattern):
                if (
                    file_path.is_file()
                    and file_path.suffix.lower() in self.SUPPORTED_EXTENSIONS
                ):
                    stat = file_path.stat()

                    # Defer resolution reading - too expensive at scan time
                    wallpapers.append(
                        LocalWallpaper(
                            path=file_path,
                            filename=file_path.name,
                            size=stat.st_size,
                            modified_time=stat.st_mtime,
                            resolution=None,
                        )
                    )

            # Sort by modification time (newest first)
            wallpapers.sort(key=lambda w: w.modified_time, reverse=True)
        except Exception as e:
            logging.error(f"Error scanning directory: {e}")

        return wallpapers

    def delete_wallpaper(self, wallpaper_path: Path) -> bool:
        try:
            if wallpaper_path.exists():
                send2trash(str(wallpaper_path))
                return True
            return False
        except Exception as e:
            logging.error(f"Error deleting wallpaper: {e}")
            return False

    async def delete_wallpaper_async(self, wallpaper_path: Path) -> bool:
        return await asyncio.to_thread(self.delete_wallpaper, wallpaper_path)

    def get_pictures_dir(self) -> Path:
        """Get Pictures directory path"""
        return self.pictures_dir

    def search_wallpapers(
        self, query: str, wallpapers: list[LocalWallpaper] | None = None
    ) -> list[LocalWallpaper]:
        if not query or query.strip() == "":
            return self.get_wallpapers() if wallpapers is None else wallpapers

        wallpapers_list = self.get_wallpapers() if wallpapers is None else wallpapers
        if not wallpapers_list:
            return []

        filenames = [w.filename for w in wallpapers_list]

        results = process.extract(
            query, filenames, scorer=fuzz.partial_ratio, limit=len(wallpapers_list)
        )

        scored_wallpapers = []
        for _filename, score, index in results:
            if score >= 50:
                scored_wallpapers.append((wallpapers_list[index], score))

        scored_wallpapers.sort(key=lambda x: x[1], reverse=True)
        return [wp for wp, _ in scored_wallpapers]

    async def search_wallpapers_async(
        self, query: str, wallpapers: list[LocalWallpaper] | None = None
    ) -> list[LocalWallpaper]:
        return await asyncio.to_thread(self.search_wallpapers, query, wallpapers)

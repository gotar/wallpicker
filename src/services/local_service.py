"""
Local Wallpaper Service
Handles browsing, searching, and deleting local wallpapers
"""

import os
from pathlib import Path
from typing import List, Optional
from send2trash import send2trash
from gi.repository import GObject
from rapidfuzz import process, fuzz


class LocalWallpaper(GObject.Object):
    __gtype_name__ = "LocalWallpaper"

    def __init__(self, path: Path, filename: str, size: int, modified_time: float):
        super().__init__()
        self.path = path
        self.filename = filename
        self.size = size
        self.modified_time = modified_time


class LocalWallpaperService:
    """Service for managing local wallpapers"""

    SUPPORTED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".bmp", ".gif"}

    def __init__(self, pictures_dir: Optional[Path] = None):
        self.pictures_dir = pictures_dir or Path.home() / "Pictures"
        if not self.pictures_dir.exists():
            self.pictures_dir = Path.home() / "Pictures"

    def get_wallpapers(self, recursive: bool = True) -> List[LocalWallpaper]:
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
                    wallpapers.append(
                        LocalWallpaper(
                            path=file_path,
                            filename=file_path.name,
                            size=stat.st_size,
                            modified_time=stat.st_mtime,
                        )
                    )

            # Sort by modification time (newest first)
            wallpapers.sort(key=lambda w: w.modified_time, reverse=True)
        except Exception as e:
            print(f"Error scanning directory: {e}")

        return wallpapers

    def delete_wallpaper(self, wallpaper_path: Path) -> bool:
        """
        Move wallpaper to trash (safe delete)

        Args:
            wallpaper_path: Path to wallpaper file

        Returns:
            True if successful, False otherwise
        """
        try:
            if wallpaper_path.exists():
                send2trash(str(wallpaper_path))
                return True
            return False
        except Exception as e:
            print(f"Error deleting wallpaper: {e}")
            return False

    def get_pictures_dir(self) -> Path:
        """Get Pictures directory path"""
        return self.pictures_dir

    def search_wallpapers(
        self, query: str, wallpapers: Optional[List[LocalWallpaper]] = None
    ) -> List[LocalWallpaper]:
        """
        Search wallpapers using fuzzy matching

        Args:
            query: Search query string
            wallpapers: List to search (if None, gets all wallpapers)

        Returns:
            List of LocalWallpaper objects sorted by relevance
        """
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
        for filename, score, index in results:
            if score >= 50:
                scored_wallpapers.append((wallpapers_list[index], score))

        scored_wallpapers.sort(key=lambda x: x[1], reverse=True)
        return [wp for wp, _ in scored_wallpapers]

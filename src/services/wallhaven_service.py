"""
Wallhaven API Service
Handles searching, downloading wallpapers from wallhaven.cc
"""

import os
import requests
import time
from pathlib import Path
from typing import Dict, List, Optional
from gi.repository import GObject


class Wallpaper(GObject.Object):
    __gtype_name__ = "Wallpaper"

    def __init__(
        self,
        id: str,
        url: str,
        path: str,
        thumbs_large: str,
        thumbs_small: str,
        resolution: str,
        category: str,
        purity: str,
        colors: List[str],
        file_size: int,
    ):
        super().__init__()
        self.id = id
        self.url = url
        self.path = path  # Direct download URL
        self.thumbs_large = thumbs_large
        self.thumbs_small = thumbs_small
        self.resolution = resolution
        self.category = category
        self.purity = purity
        self.colors = colors
        self.file_size = file_size


class WallhavenService:
    """Service for interacting with Wallhaven API"""

    BASE_URL = "https://wallhaven.cc/api/v1"
    RATE_LIMIT = 45  # requests per minute
    RATE_LIMIT_DELAY = 60.0 / RATE_LIMIT  # seconds between requests

    PRESETS = {
        "General Landscape": {
            "categories": "100",
            "purity": "100",
            "q": "landscape dark",
        },
        "Anime Scenery": {"categories": "010", "purity": "100", "q": "scenery dark"},
        "Nature": {"categories": "100", "purity": "100", "q": "nature"},
        "Architecture": {"categories": "100", "purity": "100", "q": "architecture"},
        "Cyberpunk": {"categories": "100", "purity": "100", "q": "cyberpunk"},
        "Space": {"categories": "100", "purity": "100", "q": "space"},
        "Forest": {"categories": "100", "purity": "100", "q": "forest"},
        "Mountain": {"categories": "100", "purity": "100", "q": "mountain"},
    }

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key
        self.session = requests.Session()
        self.last_request_time = 0

    def _rate_limit(self):
        """Enforce rate limiting"""
        current_time = time.time()
        time_since_last = current_time - self.last_request_time
        if time_since_last < self.RATE_LIMIT_DELAY:
            time.sleep(self.RATE_LIMIT_DELAY - time_since_last)
        self.last_request_time = time.time()

    def _get_headers(self) -> Dict[str, str]:
        """Get request headers with optional API key"""
        headers = {"User-Agent": "wallpicker/1.0"}
        if self.api_key:
            headers["X-API-Key"] = self.api_key
        return headers

    def search(
        self,
        q: str = "",
        categories: str = "111",  # General/Anime/People
        purity: str = "100",  # SFW only
        sorting: str = "date_added",
        order: str = "desc",
        atleast: str = "1920x1080",
        page: int = 1,
    ) -> Dict:
        """
        Search wallpapers on Wallhaven

        Args:
            q: Search query (tags, keywords)
            categories: 3-character string (e.g., "111" = all)
            purity: 3-character string (e.g., "100" = SFW only)
            sorting: Sort method (date_added, relevance, random, etc.)
            order: Sort order (desc, asc)
            atleast: Minimum resolution
            page: Page number

        Returns:
            Dict with 'data' (list of wallpapers) and 'meta' (pagination info)
        """
        self._rate_limit()

        params = {
            "q": q,
            "categories": categories,
            "purity": purity,
            "sorting": sorting,
            "order": order,
            "atleast": atleast,
            "page": page,
        }

        try:
            response = self.session.get(
                f"{self.BASE_URL}/search", headers=self._get_headers(), params=params
            )
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            return {"error": str(e), "data": []}

    def parse_wallpapers(self, data: List[Dict]) -> List[Wallpaper]:
        """Parse API response into Wallpaper objects"""
        wallpapers = []
        for item in data:
            wp = Wallpaper(
                id=item["id"],
                url=item["url"],
                path=item["path"],
                thumbs_large=item["thumbs"]["large"],
                thumbs_small=item["thumbs"]["small"],
                resolution=item["resolution"],
                category=item["category"],
                purity=item["purity"],
                colors=item["colors"],
                file_size=item["file_size"],
            )
            wallpapers.append(wp)
        return wallpapers

    def search_preset(self, preset_name: str, page: int = 1) -> Dict:
        """
        Search using predefined preset from scripts

        Args:
            preset_name: Name of preset (e.g., 'General Landscape')
            page: Page number

        Returns:
            Dict with 'data' and 'meta'
        """
        if preset_name not in self.PRESETS:
            return {"error": f"Unknown preset: {preset_name}", "data": []}

        preset = self.PRESETS[preset_name]
        return self.search(
            q=preset["q"],
            categories=preset["categories"],
            purity=preset["purity"],
            sorting="random",
            page=page,
        )

    def get_presets(self) -> List[str]:
        """Get list of available preset names"""
        return list(self.PRESETS.keys())

    def download(
        self, url: str, dest_path: Path, progress_callback: Optional[callable] = None
    ) -> bool:
        """
        Download wallpaper with progress callback

        Args:
            url: Direct download URL
            dest_path: Destination file path
            progress_callback: Function called with (bytes_downloaded, total_bytes)

        Returns:
            True if successful, False otherwise
        """
        try:
            response = self.session.get(url, stream=True)
            response.raise_for_status()
            total_size = int(response.headers.get("content-length", 0))

            dest_path.parent.mkdir(parents=True, exist_ok=True)

            with open(dest_path, "wb") as f:
                downloaded = 0
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
                        downloaded += len(chunk)
                        if progress_callback and total_size > 0:
                            progress_callback(downloaded, total_size)

            return True
        except Exception as e:
            print(f"Download error: {e}")
            return False

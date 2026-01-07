"""Wallhaven Service using async patterns and domain models."""

import asyncio
from collections.abc import Callable
from pathlib import Path
from typing import Any

import aiohttp

from domain.exceptions import ServiceError
from domain.wallpaper import Resolution, Wallpaper, WallpaperPurity, WallpaperSource
from services.base import BaseService


class WallhavenService(BaseService):
    """Async service for searching and downloading wallpapers from Wallhaven API."""

    BASE_URL = "https://wallhaven.cc/api/v1"
    RATE_LIMIT = 45  # requests per minute
    REQUEST_INTERVAL = 60 / RATE_LIMIT  # seconds between requests

    PRESETS = {
        "Anime": {"purity": "sfw", "categories": "010"},
        "People": {"purity": "sfw", "categories": "001"},
        "General": {"purity": "sfw", "categories": "100"},
        "Anime NSFW": {"purity": "nsfw", "categories": "010"},
        "People NSFW": {"purity": "nsfw", "categories": "001"},
        "General NSFW": {"purity": "nsfw", "categories": "100"},
    }

    def __init__(self, api_key: str | None = None) -> None:
        """Initialize Wallhaven service.

        Args:
            api_key: Wallhaven API key (optional but recommended for higher rate limits)
        """
        super().__init__()
        self.api_key = api_key
        self._last_request_time = 0.0
        self._session: aiohttp.ClientSession | None = None

    async def _get_session(self) -> aiohttp.ClientSession:
        """Get or create aiohttp session."""
        if self._session is None or self._session.closed:
            headers = {}
            if self.api_key:
                headers["X-API-Key"] = self.api_key

            self._session = aiohttp.ClientSession(headers=headers)

        return self._session

    async def _rate_limit(self) -> None:
        """Enforce rate limiting between requests."""
        now = asyncio.get_event_loop().time()
        time_since_last = now - self._last_request_time

        if time_since_last < self.REQUEST_INTERVAL:
            await asyncio.sleep(self.REQUEST_INTERVAL - time_since_last)

        self._last_request_time = asyncio.get_event_loop().time()

    async def search(
        self,
        query: str = "",
        categories: str = "111",
        purity: str = "100",
        sorting: str = "date_added",
        order: str = "desc",
        atleast: str = "",
        page: int = 1,
        top_range: str = "",
        ratios: str = "",
        colors: str = "",
        resolutions: str = "",
        seed: str = "",
    ) -> tuple[list[Wallpaper], dict]:
        """Search wallpapers with given parameters.

        Args:
            query: Search query with tag support (e.g., "nature", "+mountains -anime")
            categories: 3-digit binary string [general][anime][people] (e.g., "111" = all)
            purity: 3-digit binary string [sfw][sketchy][nsfw] (e.g., "100" = SFW only)
            sorting: Sort method (date_added, relevance, random, views, favorites, toplist, hot)
            order: Sort order (asc, desc)
            atleast: Minimum resolution (e.g., "1920x1080")
            page: Page number (1-indexed)
            top_range: Time range for toplist sorting (1d, 3d, 1w, 1M, 3M, 6M, 1y)
            ratios: Aspect ratios comma-separated (e.g., "16x9,16x10,21x9")
            colors: Hex color code (e.g., "0066cc" for blue)
            resolutions: Exact resolutions comma-separated (e.g., "1920x1080,2560x1440")
            seed: Random seed for consistent random results (6 alphanumeric chars)

        Returns:
            Tuple of (wallpapers list, metadata dict)
        """
        await self._rate_limit()

        params = {
            "q": query,
            "categories": categories,
            "purity": purity,
            "sorting": sorting,
            "order": order,
            "atleast": atleast,
            "page": page,
        }

        if top_range:
            params["topRange"] = top_range
        if ratios:
            params["ratios"] = ratios
        if colors:
            params["colors"] = colors
        if resolutions:
            params["resolutions"] = resolutions
        if seed:
            params["seed"] = seed

        try:
            session = await self._get_session()
            url = f"{self.BASE_URL}/search"
            async with session.get(url, params=params) as response:
                if response.status != 200:
                    response.raise_for_status()

                data = await response.json()

            wallpapers: list[Wallpaper] = []
            for item in data.get("data", []):
                try:
                    wallpaper = self._wallpaper_from_dict(item)
                    wallpapers.append(wallpaper)
                except (KeyError, ValueError) as e:
                    self.log_warning(f"Failed to parse wallpaper: {e}")

            self.log_debug(f"Found {len(wallpapers)} wallpapers")
            return wallpapers, data.get("meta", {})
        except (aiohttp.ClientError, KeyError) as e:
            self.log_error(f"Wallhaven search failed: {e}", exc_info=True)
            raise ServiceError(f"Failed to search Wallhaven: {e}") from e

    def _wallpaper_from_dict(self, data: dict[str, Any]) -> Wallpaper:
        """Convert Wallhaven API response to Wallpaper domain model.

        Args:
            data: Dictionary from Wallhaven API

        Returns:
            Wallpaper domain model
        """
        resolution = Resolution(
            width=data.get("dimension_x", 0),
            height=data.get("dimension_y", 0),
        )

        purity_map = {
            "sfw": WallpaperPurity.SFW,
            "sketchy": WallpaperPurity.SKETCHY,
            "nsfw": WallpaperPurity.NSFW,
        }

        return Wallpaper(
            id=data["id"],
            url=data["url"],
            path=data.get("path", data.get("full_url", "")),
            resolution=resolution,
            source=WallpaperSource.WALLHAVEN,
            category=data.get("category", "general"),
            purity=purity_map.get(data.get("purity", "sfw"), WallpaperPurity.SFW),
            colors=data.get("colors", []),
            file_size=data.get("file_size", 0),
            thumbs_large=data.get("thumbs", {}).get("large", ""),
            thumbs_small=data.get("thumbs", {}).get("small", ""),
        )

    async def download(
        self,
        wallpaper: Wallpaper,
        dest: Path,
        progress_callback: "Callable[[int, int], None] | None" = None,
    ) -> bool:
        """Download wallpaper to destination.

        Args:
            wallpaper: Wallpaper domain model to download
            dest: Destination path
            progress_callback: Optional callback for progress updates

        Returns:
            True if successful, False otherwise
        """
        await self._rate_limit()

        session = await self._get_session()

        try:
            self.log_info(f"Downloading wallpaper {wallpaper.id}")

            dest.parent.mkdir(parents=True, exist_ok=True)

            async with session.get(wallpaper.path) as response:
                response.raise_for_status()
                total_size = int(response.headers.get("content-length", 0))
                downloaded = 0

                with open(dest, "wb") as f:
                    async for chunk in response.content.iter_chunked(8192):
                        f.write(chunk)
                        downloaded += len(chunk)

                        if progress_callback and total_size > 0:
                            progress_callback(downloaded, total_size)

            self.log_debug(f"Downloaded wallpaper to {dest}")
            return True
        except (aiohttp.ClientError, OSError) as e:
            self.log_error(
                f"Failed to download wallpaper {wallpaper.id}: {e}", exc_info=True
            )
            return False

    async def close(self) -> None:
        """Close aiohttp session."""
        if self._session and not self._session.closed:
            await self._session.close()
            self.log_debug("Closed aiohttp session")

    def __del__(self) -> None:
        """Cleanup on deletion."""
        if self._session and not self._session.closed:
            try:
                loop = asyncio.get_event_loop()
                loop.create_task(self.close())
            except RuntimeError:
                pass

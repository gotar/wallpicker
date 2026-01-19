"""Thumbnail Cache Service using async patterns."""

import asyncio
import hashlib
import time
from pathlib import Path

import aiohttp

from core.asyncio_integration import get_event_loop
from domain.exceptions import ServiceError
from services.base import BaseService


class ThumbnailCache(BaseService):
    """Async service for caching thumbnail images to disk."""

    CACHE_DIR = Path.home() / ".cache" / "wallpicker" / "thumbnails"
    CACHE_EXPIRY_DAYS = 7  # Cache expires after 7 days
    MAX_CACHE_SIZE_MB = 500  # Maximum cache size in MB

    def __init__(self, cache_dir: Path | None = None) -> None:
        """Initialize thumbnail cache.

        Args:
            cache_dir: Custom cache directory (defaults to ~/.cache/wallpicker/thumbnails)
        """
        super().__init__()
        self.cache_dir = cache_dir or self.CACHE_DIR
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    def _get_cache_path(self, url: str) -> Path:
        """Generate cache file path from URL using hash."""
        url_hash = hashlib.md5(url.encode()).hexdigest()
        ext = url.split(".")[-1].split("?")[0][:4]  # Get extension, max 4 chars
        if len(ext) > 4 or not ext.isalpha():
            ext = "jpg"
        return self.cache_dir / f"{url_hash}.{ext}"

    def _is_expired(self, cache_path: Path) -> bool:
        """Check if cache entry has expired."""
        if not cache_path.exists():
            return True
        file_age = time.time() - cache_path.stat().st_mtime
        return file_age > (self.CACHE_EXPIRY_DAYS * 24 * 60 * 60)

    def cleanup(self) -> int:
        """Clean up old cache entries if cache is too large.

        Returns:
            Number of files removed
        """
        removed_count = 0
        total_size = sum(f.stat().st_size for f in self.cache_dir.glob("*"))
        max_size_bytes = self.MAX_CACHE_SIZE_MB * 1024 * 1024

        # Remove expired files
        if total_size > max_size_bytes:
            for cache_file in list(self.cache_dir.glob("*")):
                if self._is_expired(cache_file):
                    try:
                        cache_file.unlink()
                        removed_count += 1
                    except OSError:
                        self.log_warning(
                            f"Failed to delete expired cache: {cache_file}"
                        )

        # Remove oldest files if still over limit
        files = sorted(self.cache_dir.glob("*"), key=lambda f: f.stat().st_mtime)
        total_size = sum(f.stat().st_size for f in files)

        while total_size > max_size_bytes * 0.9 and files:
            oldest = files.pop(0)
            total_size -= oldest.stat().st_size
            try:
                oldest.unlink()
                removed_count += 1
            except OSError:
                self.log_warning(f"Failed to delete old cache: {oldest}")

        if removed_count > 0:
            self.log_info(f"Cleaned up {removed_count} cache files")

        return removed_count

    def get_thumbnail(self, url: str) -> Path | None:
        """Get cached thumbnail path if available and not expired.

        Args:
            url: Thumbnail URL

        Returns:
            Path to cached file or None if not cached/expired
        """
        cache_path = self._get_cache_path(url)

        if self._is_expired(cache_path):
            return None

        self.log_debug(f"Cache hit: {url[:50]}...")
        return cache_path

    async def download_and_cache(
        self, url: str, session: aiohttp.ClientSession
    ) -> Path:
        """Download thumbnail from URL and cache it.

        Args:
            url: Thumbnail URL to download
            session: aiohttp session for async download

        Returns:
            Path to cached file

        Raises:
            ServiceError: If download fails
        """
        cache_path = self._get_cache_path(url)

        try:
            self.cleanup()
            self.log_info(f"Downloading thumbnail: {url[:50]}...")

            async with session.get(url) as response:
                response.raise_for_status()
                image_data = await response.read()

            with open(cache_path, "wb") as f:
                f.write(image_data)

            self.log_debug(f"Cached thumbnail: {cache_path.name}")
            return cache_path
        except (aiohttp.ClientError, OSError) as e:
            self.log_error(
                f"Failed to download thumbnail from {url}: {e}", exc_info=True
            )
            raise ServiceError(f"Failed to download thumbnail: {e}") from e

    async def get_or_download(self, url: str, session: aiohttp.ClientSession) -> Path:
        """Get thumbnail from cache or download if not available.

        Args:
            url: Thumbnail URL or local file path
            session: aiohttp session for async download

        Returns:
            Path to file (cached thumbnail for URLs, original path for local files)
        """
        path = Path(url)
        if path.exists() and path.is_file():
            return path

        cached = self.get_thumbnail(url)
        if cached:
            return cached

        return await self.download_and_cache(url, session)

    def get_or_download_sync(self, url: str) -> Path:
        """Synchronous version for use in thread pools.

        Args:
            url: Thumbnail URL or local file path

        Returns:
            Path to file (cached thumbnail for URLs, original path for local files)

        Raises:
            ServiceError: If download fails
        """
        # Check if it's a local file - return directly
        path = Path(url)
        if path.exists() and path.is_file():
            return path

        # Check cache first
        cached = self.get_thumbnail(url)
        if cached:
            return cached

        # Need to download - use global event loop
        try:
            loop = get_event_loop()
            future = asyncio.run_coroutine_threadsafe(
                self._download_with_session(url), loop
            )
            return future.result(timeout=60)
        except RuntimeError:
            # Event loop not set up, run synchronously (last resort)
            return asyncio.run(self._download_with_session(url))
        except Exception as e:
            raise ServiceError(f"Failed to download thumbnail: {e}") from e

    async def _download_with_session(self, url: str) -> Path:
        """Download thumbnail with aiohttp session."""
        async with aiohttp.ClientSession() as session:
            return await self.download_and_cache(url, session)

    async def get_or_download_async(self, url: str) -> Path:
        path = Path(url)
        if path.exists() and path.is_file():
            return path

        cached = self.get_thumbnail(url)
        if cached:
            return cached

        async with aiohttp.ClientSession() as session:
            return await self.download_and_cache(url, session)

"""Thumbnail loading service for async thumbnail operations.

This service handles the GTK-specific thumbnail loading logic that was
previously in BaseViewModel, properly separating concerns.
"""

import logging
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import gi

gi.require_version("Gdk", "4.0")
gi.require_version("GLib", "2.0")

from gi.repository import Gdk, GLib  # noqa: E402

logger = logging.getLogger(__name__)


class ThumbnailLoader:
    """Service for loading thumbnails asynchronously."""

    def __init__(self, thumbnail_cache=None, max_workers: int = 8):
        """Initialize thumbnail loader.

        Args:
            thumbnail_cache: ThumbnailCache instance for caching remote thumbnails
            max_workers: Maximum number of worker threads
        """
        self._thumbnail_cache = thumbnail_cache
        self._executor = ThreadPoolExecutor(max_workers=max_workers)

    def load_thumbnail_async(
        self, path_or_url: str, callback: Callable[[Gdk.Texture | None], None]
    ) -> None:
        """Load thumbnail asynchronously and invoke callback on main thread.

        Args:
            path_or_url: Local file path or remote URL
            callback: Function to call with Gdk.Texture or None on failure
        """

        def _load_thumbnail():
            try:
                # Handle remote URLs with caching
                if path_or_url.startswith(("http://", "https://")) and self._thumbnail_cache:
                    logger.info(f"Loading thumbnail from URL: {path_or_url[:60]}...")
                    thumbnail_path = self._thumbnail_cache.get_or_download_sync(path_or_url)
                    if thumbnail_path and thumbnail_path.exists():
                        texture = Gdk.Texture.new_from_filename(str(thumbnail_path))
                        logger.debug(f"Thumbnail loaded successfully: {thumbnail_path.name}")
                        GLib.idle_add(lambda: callback(texture))
                        return

                # Handle local files
                path = Path(path_or_url)
                if path.exists():
                    texture = Gdk.Texture.new_from_filename(str(path))
                    logger.debug(f"Local thumbnail loaded: {path.name}")
                    GLib.idle_add(lambda: callback(texture))
                    return
            except (OSError, Exception) as e:
                logger.error(f"Failed to load thumbnail from {path_or_url}: {e}", exc_info=True)

            # Invoke callback with None if loading failed
            GLib.idle_add(lambda: callback(None))

        self._executor.submit(_load_thumbnail)

    def shutdown(self) -> None:
        """Shutdown the executor."""
        self._executor.shutdown(wait=False)

    def __del__(self) -> None:
        """Cleanup on destruction."""
        if hasattr(self, "_executor"):
            self._executor.shutdown(wait=False)

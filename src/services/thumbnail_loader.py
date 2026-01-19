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

# Thumbnail cache directory
_THUMBNAIL_CACHE_DIR = Path.home() / ".cache" / "wallpicker" / "thumbnails"
_THUMBNAIL_SIZE = (200, 160)


class ThumbnailLoader:
    """Service for loading thumbnails asynchronously."""

    def __init__(self, thumbnail_cache=None, max_workers: int = 4):
        """Initialize thumbnail loader.

        Args:
            thumbnail_cache: ThumbnailCache instance for caching remote thumbnails
            max_workers: Maximum number of worker threads
        """
        self._thumbnail_cache = thumbnail_cache
        self._executor = ThreadPoolExecutor(max_workers=max_workers)
        self._local_thumbnail_cache = {}  # In-memory cache for local thumbnails
        self._ensure_cache_dir()

    def _ensure_cache_dir(self):
        """Ensure thumbnail cache directory exists."""
        try:
            _THUMBNAIL_CACHE_DIR.mkdir(parents=True, exist_ok=True)
        except Exception as e:
            logger.warning(f"Could not create thumbnail cache directory: {e}")

    def _get_local_thumbnail_path(self, file_path: str) -> Path:
        """Get the path for a local thumbnail file."""
        # Use file path hash for cache key
        path = Path(file_path)
        cache_key = f"{path.stat().st_mtime}_{path.stat().st_size}"
        return (
            _THUMBNAIL_CACHE_DIR
            / f"local_{hash(file_path) & 0xFFFFFFFF:08x}_{cache_key}.jpg"
        )

    def _generate_thumbnail(self, file_path: str) -> bytes | None:
        """Generate a thumbnail for a local image file.

        Returns:
            JPEG bytes of the thumbnail, or None on failure.
        """
        try:
            from PIL import Image

            path = Path(file_path)
            if not path.exists():
                return None

            # Check if thumbnail already exists and is up to date
            thumb_path = self._get_local_thumbnail_path(file_path)
            if thumb_path.exists():
                # Check if source is older than thumbnail
                if path.stat().st_mtime <= thumb_path.stat().st_mtime:
                    return thumb_path.read_bytes()

            # Generate thumbnail
            with Image.open(path) as img:
                # Convert to RGB if necessary (for PNG with transparency)
                if img.mode in ("RGBA", "P"):
                    img = img.convert("RGB")
                img.thumbnail(_THUMBNAIL_SIZE, Image.Resampling.LANCZOS)

                # Save to cache
                thumb_path.parent.mkdir(parents=True, exist_ok=True)
                img.save(thumb_path, "JPEG", quality=80, optimize=True)

                # Return bytes
                import io

                buffer = io.BytesIO()
                img.save(buffer, "JPEG", quality=80, optimize=True)
                return buffer.getvalue()

        except ImportError:
            logger.warning("PIL not available, falling back to direct loading")
        except Exception as e:
            logger.error(
                f"Failed to generate thumbnail for {file_path}: {e}", exc_info=True
            )

        return None

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
                if path_or_url.startswith(("http://", "https://")):
                    if self._thumbnail_cache:
                        logger.debug(f"Loading remote thumbnail: {path_or_url[:60]}...")
                        thumbnail_path = self._thumbnail_cache.get_or_download_sync(
                            path_or_url
                        )
                        if thumbnail_path and thumbnail_path.exists():
                            # Read file bytes in worker thread
                            try:
                                data = thumbnail_path.read_bytes()

                                # Schedule texture creation in main thread
                                def create_remote_texture():
                                    try:
                                        texture = Gdk.Texture.new_from_bytes(
                                            GLib.Bytes.new(data)
                                        )
                                        callback(texture)
                                    except Exception:
                                        callback(None)

                                GLib.idle_add(create_remote_texture)
                                return
                            except Exception:
                                pass

                    GLib.idle_add(lambda: callback(None))
                    return

                # Handle local files - use thumbnail generation
                path = Path(path_or_url)
                if path.exists():
                    # Check in-memory cache first
                    if path_or_url in self._local_thumbnail_cache:
                        data = self._local_thumbnail_cache[path_or_url]
                        if data:

                            def create_cached_texture():
                                try:
                                    texture = Gdk.Texture.new_from_bytes(
                                        GLib.Bytes.new(data)
                                    )
                                    callback(texture)
                                except Exception:
                                    callback(None)

                            GLib.idle_add(create_cached_texture)
                            return

                    # Generate or load thumbnail in worker thread
                    thumbnail_data = self._generate_thumbnail(path_or_url)

                    if thumbnail_data:
                        # Cache in memory
                        self._local_thumbnail_cache[path_or_url] = thumbnail_data

                        # Create texture in main thread
                        def create_local_texture():
                            try:
                                texture = Gdk.Texture.new_from_bytes(
                                    GLib.Bytes.new(thumbnail_data)
                                )
                                callback(texture)
                            except Exception:
                                callback(None)

                        GLib.idle_add(create_local_texture)
                        return

            except (OSError, Exception) as e:
                logger.error(
                    f"Failed to load thumbnail from {path_or_url}: {e}", exc_info=True
                )

            # Invoke callback with None if loading failed
            GLib.idle_add(lambda: callback(None))

        self._executor.submit(_load_thumbnail)

    def shutdown(self) -> None:
        """Shutdown the executor."""
        self._executor.shutdown(wait=False)

    def clear_memory_cache(self) -> None:
        """Clear the in-memory thumbnail cache."""
        self._local_thumbnail_cache.clear()

    def __del__(self) -> None:
        """Cleanup on destruction."""
        if hasattr(self, "_executor"):
            self._executor.shutdown(wait=False)

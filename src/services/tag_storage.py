"""Tag Storage Service for persisting AI-generated tags."""

import hashlib
import json
import logging
from pathlib import Path

from services.base import BaseService


class TagStorageService(BaseService):
    """Service for storing and retrieving AI-generated wallpaper tags."""

    def __init__(self, cache_dir: Path | None = None):
        """Initialize tag storage service.

        Args:
            cache_dir: Directory for tag cache (defaults to ~/.cache/wallpicker/tags)
        """
        super().__init__()
        self.cache_dir = cache_dir or Path.home() / ".cache" / "wallpicker" / "tags"
        self._ensure_cache_dir()

    def _ensure_cache_dir(self) -> None:
        """Create cache directory if it doesn't exist."""
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    def _get_tag_file_path(self, image_path: Path) -> Path:
        """Get the tag file path for an image.

        Args:
            image_path: Path to the image file

        Returns:
            Path to the tag JSON file
        """
        # Use hash of absolute path for filename (handles moved files)
        path_hash = hashlib.md5(str(image_path.resolve()).encode()).hexdigest()
        return self.cache_dir / f"{path_hash}.json"

    def get_tags(self, image_path: Path) -> list[str]:
        """Get cached tags for an image.

        Args:
            image_path: Path to the image file

        Returns:
            List of tags, empty list if not found
        """
        tag_file = self._get_tag_file_path(image_path)

        if not tag_file.exists():
            return []

        try:
            with open(tag_file, "r") as f:
                data = json.load(f)
            return data.get("tags", [])
        except (json.JSONDecodeError, OSError) as e:
            self.log_warning(f"Failed to load tags for {image_path}: {e}")
            return []

    def save_tags(self, image_path: Path, tags: list[str], confidence: dict | None = None) -> bool:
        """Save tags for an image.

        Args:
            image_path: Path to the image file
            tags: List of tags to save
            confidence: Optional dict mapping tag to confidence score

        Returns:
            True if successful, False otherwise
        """
        tag_file = self._get_tag_file_path(image_path)

        try:
            data = {
                "path": str(image_path),
                "tags": tags,
                "confidence": confidence or {},
            }
            with open(tag_file, "w") as f:
                json.dump(data, f, indent=2)
            return True
        except OSError as e:
            self.log_error(f"Failed to save tags for {image_path}: {e}")
            return False

    def get_tags_with_confidence(self, image_path: Path) -> tuple[list[str], dict]:
        """Get tags and their confidence scores for an image.

        Args:
            image_path: Path to the image file

        Returns:
            Tuple of (tags list, confidence dict)
        """
        tag_file = self._get_tag_file_path(image_path)

        if not tag_file.exists():
            return [], {}

        try:
            with open(tag_file, "r") as f:
                data = json.load(f)
            return data.get("tags", []), data.get("confidence", {})
        except (json.JSONDecodeError, OSError) as e:
            self.log_warning(f"Failed to load tags for {image_path}: {e}")
            return [], {}

    def delete_tags(self, image_path: Path) -> bool:
        """Delete cached tags for an image.

        Args:
            image_path: Path to the image file

        Returns:
            True if deleted or didn't exist, False on error
        """
        tag_file = self._get_tag_file_path(image_path)

        if not tag_file.exists():
            return True

        try:
            tag_file.unlink()
            return True
        except OSError as e:
            self.log_error(f"Failed to delete tags for {image_path}: {e}")
            return False

    def has_tags(self, image_path: Path) -> bool:
        """Check if tags exist for an image.

        Args:
            image_path: Path to the image file

        Returns:
            True if tags exist, False otherwise
        """
        tag_file = self._get_tag_file_path(image_path)
        return tag_file.exists()

    def get_untagged_images(self, image_paths: list[Path]) -> list[Path]:
        """Filter a list of images to find those without tags.

        Args:
            image_paths: List of image paths to check

        Returns:
            List of image paths that don't have cached tags
        """
        return [p for p in image_paths if not self.has_tags(p)]

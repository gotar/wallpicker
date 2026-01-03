import unittest
import json
import os
import shutil
from pathlib import Path
from unittest.mock import MagicMock, patch

# Add src to path
import sys

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../src")))

from services.wallhaven_service import WallhavenService, Wallpaper
from services.local_service import LocalWallpaperService
from services.favorites_service import FavoritesService
from services.wallpaper_setter import WallpaperSetter


class TestWallhavenService(unittest.TestCase):
    def setUp(self):
        self.service = WallhavenService()

    @patch("requests.Session.get")
    def test_search_parsing(self, mock_get):
        # Mock API response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "data": [
                {
                    "id": "test1",
                    "resolution": "1920x1080",
                    "category": "anime",
                    "purity": "sfw",
                    "path": "http://example.com/full.jpg",
                    "thumbs": {
                        "large": "http://example.com/thumb.jpg",
                        "small": "http://example.com/small.jpg",
                    },
                    "colors": ["#000000"],
                    "file_size": 1024,
                    "url": "http://example.com/view/1",
                }
            ],
            "meta": {"total": 1},
        }
        mock_get.return_value = mock_response

        # Test search
        result = self.service.search(q="test")
        wallpapers = self.service.parse_wallpapers(result["data"])

        self.assertEqual(len(wallpapers), 1)
        self.assertEqual(wallpapers[0].id, "test1")
        self.assertEqual(wallpapers[0].resolution, "1920x1080")


class TestFavoritesService(unittest.TestCase):
    def setUp(self):
        self.test_dir = Path("/tmp/wallpicker_test")
        self.test_dir.mkdir(parents=True, exist_ok=True)
        # Patch the config dir
        self.patcher = patch(
            "services.favorites_service.Path.home", return_value=self.test_dir
        )
        self.patcher.start()
        self.service = FavoritesService()

    def tearDown(self):
        self.patcher.stop()
        if self.test_dir.exists():
            shutil.rmtree(self.test_dir)

    def test_add_remove_favorite(self):
        wp = Wallpaper(
            id="fav1",
            url="http://example.com/1.jpg",
            path="http://example.com/full.jpg",
            thumbs_large="http://example.com/t1.jpg",
            thumbs_small="http://example.com/t1_small.jpg",
            resolution="1920x1080",
            category="general",
            purity="sfw",
            colors=["#ffffff"],
            file_size=1024,
        )

        # Add
        self.service.add_favorite(wp)
        self.assertTrue(self.service.is_favorite("fav1"))

        # Check persistence
        new_service = FavoritesService()
        self.assertTrue(new_service.is_favorite("fav1"))

        # Remove
        self.service.remove_favorite("fav1")
        self.assertFalse(self.service.is_favorite("fav1"))


class TestWallpaperSetter(unittest.TestCase):
    def setUp(self):
        self.setter = WallpaperSetter()

    @patch.dict(os.environ, {"XDG_CURRENT_DESKTOP": "GNOME"})
    def test_detect_gnome(self):
        self.assertEqual(self.setter._detect_desktop_environment(), "gnome")

    @patch.dict(os.environ, {"XDG_CURRENT_DESKTOP": "KDE"})
    def test_detect_kde(self):
        self.assertEqual(self.setter._detect_desktop_environment(), "kde")


if __name__ == "__main__":
    unittest.main()

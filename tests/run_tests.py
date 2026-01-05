import os
import shutil

# Add src to path
import sys
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../src")))

from services.config_service import ConfigService
from services.favorites_service import FavoritesService
from services.local_service import LocalWallpaperService
from services.thumbnail_cache import ThumbnailCache
from services.wallhaven_service import WallhavenService, Wallpaper
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

    @patch("subprocess.run")
    @patch("pathlib.Path.exists", return_value=True)
    @patch("pathlib.Path.is_symlink", return_value=False)
    def test_set_wallpaper(self, mock_symlink, mock_exists, mock_run):
        self.setter.set_wallpaper("/test/image.jpg")
        self.assertGreater(mock_run.call_count, 0)


class TestLocalWallpaperService(unittest.TestCase):
    def setUp(self):
        self.test_dir = Path("/tmp/wallpicker_local_test")
        self.test_dir.mkdir(parents=True, exist_ok=True)
        self.service = LocalWallpaperService(pictures_dir=self.test_dir)

        # Create test wallpapers
        (self.test_dir / "test1.jpg").touch()
        (self.test_dir / "test2.png").touch()
        (self.test_dir / "test3.webp").touch()
        (self.test_dir / "not_image.txt").touch()

    def tearDown(self):
        if self.test_dir.exists():
            shutil.rmtree(self.test_dir)

    def test_get_wallpapers(self):
        wallpapers = self.service.get_wallpapers()
        self.assertEqual(len(wallpapers), 3)
        self.assertTrue(
            all(w.path.suffix in (".jpg", ".png", ".webp") for w in wallpapers)
        )

    def test_search_wallpapers_empty_query(self):
        wallpapers = self.service.search_wallpapers("")
        self.assertEqual(len(wallpapers), 3)

    def test_search_wallpapers_fuzzy(self):
        wallpapers = self.service.search_wallpapers("test1")
        self.assertGreater(len(wallpapers), 0)
        self.assertTrue(any("test1" in w.filename for w in wallpapers))

    def test_search_wallpapers_partial(self):
        wallpapers = self.service.search_wallpapers("test")
        self.assertEqual(len(wallpapers), 3)

    def test_search_wallpapers_no_results(self):
        wallpapers = self.service.search_wallpapers("nonexistent")
        self.assertEqual(len(wallpapers), 0)


class TestThumbnailCache(unittest.TestCase):
    def setUp(self):
        self.cache = ThumbnailCache()

    def tearDown(self):
        pass

    def test_get_cache_path(self):
        url = "http://example.com/image.jpg"
        cache_path = self.cache._get_cache_path(url)
        self.assertTrue(cache_path.parent.exists())
        self.assertTrue(cache_path.suffix in (".jpg", ".png", ".webp"))


class TestConfigService(unittest.TestCase):
    def setUp(self):
        self.test_dir = Path("/tmp/wallpicker_config_test")
        self.test_dir.mkdir(parents=True, exist_ok=True)
        config_dir = self.test_dir / ".config" / "wallpicker"
        config_dir.mkdir(parents=True, exist_ok=True)
        (config_dir / "config.json").write_text("{}")
        self.patcher = patch(
            "services.config_service.Path.home", return_value=self.test_dir
        )
        self.patcher.start()
        self.service = ConfigService()

    def tearDown(self):
        self.patcher.stop()
        if self.test_dir.exists():
            shutil.rmtree(self.test_dir)

    def test_save_and_load_config(self):
        self.service.set("local_wallpapers_dir", "/test/path")
        config = self.service.load()
        self.service.save(config)

        new_service = ConfigService()
        self.assertEqual(new_service.get("local_wallpapers_dir"), "/test/path")

    def test_get_default_value(self):
        value = self.service.get("nonexistent_key", "default")
        self.assertEqual(value, "default")

    def test_set_and_get(self):
        self.service.set("test_key", "test_value")
        self.assertEqual(self.service.get("test_key"), "test_value")


if __name__ == "__main__":
    unittest.main()

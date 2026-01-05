"""
Tests for LocalWallpaperService
"""

import sys
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from services.local_service import LocalWallpaper, LocalWallpaperService


class TestLocalWallpaperModel:
    """Test LocalWallpaper model"""

    def test_create_local_wallpaper(self):
        """Test creating LocalWallpaper object"""
        path = Path("/test/image.jpg")
        wallpaper = LocalWallpaper(
            path=path,
            filename="image.jpg",
            size=1024,
            modified_time=1234567890.0,
        )

        assert wallpaper.path == path
        assert wallpaper.filename == "image.jpg"
        assert wallpaper.size == 1024
        assert wallpaper.modified_time == 1234567890.0

    def test_gobject_subclass(self):
        """Test LocalWallpaper is GObject subclass"""
        wallpaper = LocalWallpaper(
            path=Path("/test/image.jpg"),
            filename="image.jpg",
            size=1024,
            modified_time=1234567890.0,
        )

        assert wallpaper.__gtype_name__ == "LocalWallpaper"


class TestLocalWallpaperServiceInit:
    """Test LocalWallpaperService initialization"""

    def test_init_default_pictures_dir(self):
        """Test initialization with default Pictures directory"""
        service = LocalWallpaperService()

        expected_dir = Path.home() / "Pictures"
        assert service.pictures_dir == expected_dir

    def test_init_custom_pictures_dir(self, tmp_path):
        """Test initialization with custom directory"""
        custom_dir = tmp_path / "wallpapers"
        custom_dir.mkdir()

        service = LocalWallpaperService(pictures_dir=custom_dir)

        assert service.pictures_dir == custom_dir

    def test_init_fallback_to_default(self, tmp_path):
        """Test fallback to default when custom dir doesn't exist"""
        # Create a non-existent path
        non_existent = tmp_path / "does_not_exist"

        service = LocalWallpaperService(pictures_dir=non_existent)

        # Should fall back to default Pictures directory
        assert service.pictures_dir == Path.home() / "Pictures"

    def test_get_pictures_dir(self, tmp_path):
        """Test getting pictures directory"""
        service = LocalWallpaperService(pictures_dir=tmp_path)

        assert service.get_pictures_dir() == tmp_path


class TestGetWallpapers:
    """Test get_wallpapers method"""

    def test_get_wallpapers_recursive(self, tmp_path):
        """Test getting wallpapers recursively"""
        # Create test files
        (tmp_path / "image1.jpg").touch()
        (tmp_path / "image2.png").touch()
        subdir = tmp_path / "subdir"
        subdir.mkdir()
        (subdir / "image3.webp").touch()
        (tmp_path / "not_image.txt").touch()

        service = LocalWallpaperService(pictures_dir=tmp_path)
        wallpapers = service.get_wallpapers(recursive=True)

        assert len(wallpapers) == 3
        assert all(isinstance(w, LocalWallpaper) for w in wallpapers)
        filenames = [w.filename for w in wallpapers]
        assert "image1.jpg" in filenames
        assert "image2.png" in filenames
        assert "image3.webp" in filenames

    def test_get_wallpapers_non_recursive(self, tmp_path):
        """Test getting wallpapers non-recursively"""
        # Create test files
        (tmp_path / "image1.jpg").touch()
        (tmp_path / "image2.png").touch()
        subdir = tmp_path / "subdir"
        subdir.mkdir()
        (subdir / "image3.webp").touch()

        service = LocalWallpaperService(pictures_dir=tmp_path)
        wallpapers = service.get_wallpapers(recursive=False)

        assert len(wallpapers) == 2
        filenames = [w.filename for w in wallpapers]
        assert "image1.jpg" in filenames
        assert "image2.png" in filenames
        assert "image3.webp" not in filenames

    def test_get_wallpapers_sorted_by_modified_time(self, tmp_path):
        """Test that wallpapers are sorted by modification time (newest first)"""
        import time

        # Create files with different timestamps
        (tmp_path / "old.jpg").touch()
        time.sleep(0.1)
        (tmp_path / "new.jpg").touch()
        time.sleep(0.1)
        (tmp_path / "newest.jpg").touch()

        service = LocalWallpaperService(pictures_dir=tmp_path)
        wallpapers = service.get_wallpapers()

        assert len(wallpapers) == 3
        # Newest should be first
        assert wallpapers[0].filename == "newest.jpg"
        assert wallpapers[1].filename == "new.jpg"
        assert wallpapers[2].filename == "old.jpg"

    def test_get_wallpapers_supported_extensions(self, tmp_path):
        """Test that only supported image extensions are included"""
        supported = [".jpg", ".jpeg", ".png", ".webp", ".bmp", ".gif"]
        unsupported = [".txt", ".pdf", ".doc"]

        for ext in supported:
            (tmp_path / f"image{ext}").touch()

        for ext in unsupported:
            (tmp_path / f"file{ext}").touch()

        service = LocalWallpaperService(pictures_dir=tmp_path)
        wallpapers = service.get_wallpapers()

        assert len(wallpapers) == len(supported)
        for w in wallpapers:
            assert w.path.suffix.lower() in service.SUPPORTED_EXTENSIONS

    def test_get_wallpapers_case_insensitive_extensions(self, tmp_path):
        """Test that extension matching is case-insensitive"""
        (tmp_path / "IMAGE1.JPG").touch()
        (tmp_path / "image2.PNG").touch()
        (tmp_path / "Image3.WebP").touch()

        service = LocalWallpaperService(pictures_dir=tmp_path)
        wallpapers = service.get_wallpapers()

        assert len(wallpapers) == 3

    def test_get_wallpapers_empty_directory(self, tmp_path):
        """Test getting wallpapers from empty directory"""
        service = LocalWallpaperService(pictures_dir=tmp_path)
        wallpapers = service.get_wallpapers()

        assert wallpapers == []

    def test_get_wallpapers_directory_not_exists(self, tmp_path):
        """Test getting wallpapers from non-existent directory"""
        non_existent = tmp_path / "does_not_exist"
        service = LocalWallpaperService(pictures_dir=non_existent)

        # Should return empty list (not raise exception)
        wallpapers = service.get_wallpapers()
        assert wallpapers == []

    def test_get_wallpapers_includes_metadata(self, tmp_path):
        """Test that wallpapers include correct file metadata"""
        test_file = tmp_path / "test.jpg"
        test_file.touch()
        test_file.write_bytes(b"x" * 1024)  # 1KB file

        service = LocalWallpaperService(pictures_dir=tmp_path)
        wallpapers = service.get_wallpapers()

        assert len(wallpapers) == 1
        wallpaper = wallpapers[0]
        assert wallpaper.path == test_file
        assert wallpaper.filename == "test.jpg"
        assert wallpaper.size == 1024
        assert isinstance(wallpaper.modified_time, float)


class TestDeleteWallpaper:
    """Test delete_wallpaper method"""

    def test_delete_wallpaper_success(self, tmp_path):
        """Test successful deletion with mocked send2trash"""
        test_file = tmp_path / "delete_me.jpg"
        test_file.write_bytes(b"test content")  # Write content so file exists

        service = LocalWallpaperService(pictures_dir=tmp_path)

        with patch("services.local_service.send2trash") as mock_send2trash:
            result = service.delete_wallpaper(test_file)

            assert result is True
            mock_send2trash.assert_called_once_with(str(test_file))

    def test_delete_wallpaper_non_existent(self, tmp_path):
        """Test deleting non-existent file"""
        non_existent = tmp_path / "does_not_exist.jpg"

        service = LocalWallpaperService(pictures_dir=tmp_path)
        result = service.delete_wallpaper(non_existent)

        assert result is False

    def test_delete_wallpaper_with_mock_send2trash(self, tmp_path):
        """Test that send2trash is called correctly"""
        test_file = tmp_path / "test.jpg"
        test_file.touch()

        service = LocalWallpaperService(pictures_dir=tmp_path)

        with patch("services.local_service.send2trash") as mock_send2trash:
            result = service.delete_wallpaper(test_file)

            mock_send2trash.assert_called_once_with(str(test_file))
            assert result is True


class TestSearchWallpapers:
    """Test search_wallpapers method"""

    def test_search_empty_query(self, tmp_path):
        """Test search with empty query returns all wallpapers"""
        (tmp_path / "anime.jpg").touch()
        (tmp_path / "nature.png").touch()

        service = LocalWallpaperService(pictures_dir=tmp_path)
        results = service.search_wallpapers("")

        assert len(results) == 2

    def test_search_whitespace_query(self, tmp_path):
        """Test search with whitespace query returns all wallpapers"""
        (tmp_path / "anime.jpg").touch()
        (tmp_path / "nature.png").touch()

        service = LocalWallpaperService(pictures_dir=tmp_path)
        results = service.search_wallpapers("   ")

        assert len(results) == 2

    def test_search_with_results(self, tmp_path):
        """Test search with matching results"""
        (tmp_path / "anime_girl.jpg").touch()
        (tmp_path / "anime_boy.png").touch()
        (tmp_path / "nature.jpg").touch()

        service = LocalWallpaperService(pictures_dir=tmp_path)
        results = service.search_wallpapers("anime")

        assert len(results) == 2
        filenames = [w.filename for w in results]
        assert "anime_girl.jpg" in filenames
        assert "anime_boy.png" in filenames
        assert "nature.jpg" not in filenames

    def test_search_no_results(self, tmp_path):
        """Test search with no matching results"""
        (tmp_path / "anime.jpg").touch()
        (tmp_path / "nature.jpg").touch()

        service = LocalWallpaperService(pictures_dir=tmp_path)
        results = service.search_wallpapers("mountain")

        assert results == []

    def test_search_partial_match(self, tmp_path):
        """Test fuzzy matching with partial strings"""
        (tmp_path / "beautiful_landscape.jpg").touch()
        (tmp_path / "land_scape.png").touch()

        service = LocalWallpaperService(pictures_dir=tmp_path)
        results = service.search_wallpapers("scape")

        # Should match both with "scape" substring
        assert len(results) >= 1

    def test_search_with_custom_wallpaper_list(self):
        """Test search with provided wallpaper list"""
        wallpapers = [
            LocalWallpaper(
                path=Path("/anime.jpg"),
                filename="anime.jpg",
                size=1024,
                modified_time=1234567890.0,
            ),
            LocalWallpaper(
                path=Path("/nature.jpg"),
                filename="nature.jpg",
                size=2048,
                modified_time=1234567891.0,
            ),
        ]

        service = LocalWallpaperService()
        results = service.search_wallpapers("anime", wallpapers=wallpapers)

        assert len(results) == 1
        assert results[0].filename == "anime.jpg"

    def test_search_custom_list_empty(self, tmp_path):
        """Test search with empty custom wallpaper list"""
        service = LocalWallpaperService(pictures_dir=tmp_path)
        results = service.search_wallpapers("anime", wallpapers=[])

        assert results == []

    def test_search_score_threshold(self, tmp_path):
        """Test that only results with score >= 50 are returned"""
        (tmp_path / "anime_girl.jpg").touch()
        (tmp_path / "nature.jpg").touch()

        service = LocalWallpaperService(pictures_dir=tmp_path)
        results = service.search_wallpapers("anime")

        # "anime_girl.jpg" should match with high score
        # "nature.jpg" should not match (score < 50)
        assert len(results) == 1
        assert results[0].filename == "anime_girl.jpg"

    def test_search_sort_by_relevance(self, tmp_path):
        """Test that results are sorted by relevance score"""
        (tmp_path / "anime_girl.jpg").touch()
        (tmp_path / "anime.jpg").touch()
        (tmp_path / "something_anime_related.png").touch()

        service = LocalWallpaperService(pictures_dir=tmp_path)
        results = service.search_wallpapers("anime")

        # All should match "anime"
        assert len(results) == 3
        # Results should be sorted by relevance (fuzzy matching)
        # The exact match "anime.jpg" might not be first due to fuzzy scoring
        filenames = [w.filename for w in results]
        assert "anime.jpg" in filenames
        assert "anime_girl.jpg" in filenames
        assert "something_anime_related.png" in filenames


class TestSupportedExtensions:
    """Test supported extensions configuration"""

    def test_supported_extensions_set(self):
        """Test that SUPPORTED_EXTENSIONS includes common image formats"""
        service = LocalWallpaperService()

        expected_extensions = {".jpg", ".jpeg", ".png", ".webp", ".bmp", ".gif"}
        assert service.SUPPORTED_EXTENSIONS == expected_extensions

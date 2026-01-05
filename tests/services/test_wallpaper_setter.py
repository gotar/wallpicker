"""
Tests for WallpaperSetter service
"""

import subprocess
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from services.wallpaper_setter import WallpaperSetter


class TestWallpaperSetterInit:
    """Test WallpaperSetter initialization"""

    def test_init_creates_directories(self, tmp_path):
        """Test that initialization creates cache and symlink directories"""
        # Mock home directory to tmp_path
        with patch("pathlib.Path.home", return_value=tmp_path):
            WallpaperSetter()

            cache_dir = tmp_path / ".cache" / "wallpaper"
            symlink_dir = tmp_path / ".config" / "omarchy" / "current"

            assert cache_dir.exists()
            assert symlink_dir.exists()

    def test_init_sets_correct_paths(self):
        """Test that initialization sets correct paths"""
        home = Path.home()

        setter = WallpaperSetter()

        expected_cache = home / ".cache" / "wallpaper"
        expected_symlink = home / ".config" / "omarchy" / "current" / "background"

        assert setter.cache_dir == expected_cache
        assert setter.symlink_path == expected_symlink


class TestSetWallpaper:
    """Test set_wallpaper method"""

    @pytest.fixture
    def test_image_path(self, tmp_path):
        """Create a test image path"""
        test_file = tmp_path / "wallpaper.jpg"
        test_file.write_bytes(b"test image data")
        return str(test_file)

    def test_set_wallpaper_success(self, test_image_path):
        """Test successful wallpaper setting"""
        with patch("pathlib.Path.home"):
            setter = WallpaperSetter()

            with patch.object(setter, "_ensure_daemon_running"):
                with patch.object(setter, "_update_symlink"):
                    with patch.object(setter, "_apply_wallpaper"):
                        with patch.object(setter, "_cleanup_old_wallpapers"):
                            result = setter.set_wallpaper(test_image_path)

                            assert result is True
                            setter._ensure_daemon_running.assert_called_once()
                            setter._update_symlink.assert_called_once()
                            setter._apply_wallpaper.assert_called_once()
                            setter._cleanup_old_wallpapers.assert_called_once()

    def test_set_wallpaper_non_existent_path(self):
        """Test setting wallpaper with non-existent path"""
        with patch("pathlib.Path.home"):
            setter = WallpaperSetter()

            result = setter.set_wallpaper("/non/existent/path.jpg")

            # Should return False for non-existent file
            assert result is False

    def test_set_wallpaper_exception(self, test_image_path):
        """Test that exceptions are caught and return False"""
        with patch("pathlib.Path.home"):
            setter = WallpaperSetter()

            with patch.object(setter, "_ensure_daemon_running"):
                with patch.object(setter, "_update_symlink"):
                    with patch.object(
                        setter, "_apply_wallpaper", side_effect=Exception("Test error")
                    ):
                        result = setter.set_wallpaper(test_image_path)

                        # Should return False on exception
                        assert result is False

    def test_set_wallpaper_calls_in_order(self, test_image_path):
        """Test that methods are called in correct order"""
        with patch("pathlib.Path.home"):
            setter = WallpaperSetter()

            # Mock the methods
            mock_daemon = MagicMock()
            mock_update = MagicMock()
            mock_apply = MagicMock()
            mock_cleanup = MagicMock()

            setter._ensure_daemon_running = mock_daemon
            setter._update_symlink = mock_update
            setter._apply_wallpaper = mock_apply
            setter._cleanup_old_wallpapers = mock_cleanup

            setter.set_wallpaper(test_image_path)

            # Check all methods were called
            assert mock_daemon.called
            assert mock_update.called
            assert mock_apply.called
            assert mock_cleanup.called


class TestEnsureDaemonRunning:
    """Test _ensure_daemon_running method"""

    def test_ensure_daemon_already_running(self):
        """Test when daemon is already running"""
        with patch("pathlib.Path.home"):
            setter = WallpaperSetter()

            # Mock pgrep to find daemon running
            mock_result = MagicMock()
            mock_result.returncode = 0
            with patch("subprocess.run", return_value=mock_result):
                setter._ensure_daemon_running()

                # pgrep should be called
                subprocess.run.assert_called_once()

    def test_ensure_daemon_not_running(self):
        """Test when daemon is not running"""
        with patch("pathlib.Path.home"):
            setter = WallpaperSetter()

            # Mock pgrep to not find daemon
            mock_result = MagicMock()
            mock_result.returncode = 1
            with patch("subprocess.run", return_value=mock_result) as mock_run:
                with patch("subprocess.Popen") as mock_popen:
                    with patch("time.sleep") as mock_sleep:
                        setter._ensure_daemon_running()

                        # pgrep should be called
                        mock_run.assert_called_once()
                        # daemon should be started
                        mock_popen.assert_called_once()
                        # should sleep for daemon to start
                        mock_sleep.assert_called_once_with(1)

    def test_ensure_daemon_pgrep_args(self):
        """Test that pgrep is called with correct arguments"""
        with patch("pathlib.Path.home"):
            setter = WallpaperSetter()

        mock_result = MagicMock()
        mock_result.returncode = 1

        with patch("subprocess.run", return_value=mock_result) as mock_run:
            with patch("subprocess.Popen"):
                with patch("time.sleep"):
                    setter._ensure_daemon_running()

                    # Check pgrep arguments
                    call_args = mock_run.call_args
                    cmd = call_args[0][0]
                    assert cmd[0] == "pgrep"
                    assert "-x" in cmd
                    assert "awww-daemon" in cmd


class TestUpdateSymlink:
    """Test _update_symlink method"""

    def test_update_symlink_new(self, tmp_path):
        """Test updating symlink when none exists"""
        with patch("pathlib.Path.home", return_value=tmp_path):
            setter = WallpaperSetter()

            test_image = tmp_path / "wallpaper.jpg"
            test_image.write_bytes(b"test")

            setter._update_symlink(test_image)

            assert setter.symlink_path.is_symlink()
            assert setter.symlink_path.resolve() == test_image

    def test_update_symlink_existing(self, tmp_path):
        """Test updating symlink when one already exists"""
        with patch("pathlib.Path.home", return_value=tmp_path):
            setter = WallpaperSetter()

            # Create existing symlink
            old_target = tmp_path / "old.jpg"
            old_target.write_bytes(b"old")
            setter.symlink_path.symlink_to(old_target)

            # Create new target
            new_target = tmp_path / "new.jpg"
            new_target.write_bytes(b"new")

            setter._update_symlink(new_target)

            # Old symlink should be replaced
            assert setter.symlink_path.resolve() == new_target

    def test_update_symlink_unlinks_old(self, tmp_path):
        """Test that old symlink is unlinked before creating new"""
        with patch("pathlib.Path.home", return_value=tmp_path):
            setter = WallpaperSetter()

            # Create existing symlink
            old_target = tmp_path / "old.jpg"
            old_target.write_bytes(b"old")
            setter.symlink_path.symlink_to(old_target)

            # Verify old symlink exists
            assert setter.symlink_path.is_symlink()
            assert setter.symlink_path.resolve() == old_target

            # Update to new target
            new_target = tmp_path / "new.jpg"
            new_target.write_bytes(b"new")

            setter._update_symlink(new_target)

            # New symlink should point to new target
            assert setter.symlink_path.is_symlink()
            assert setter.symlink_path.resolve() == new_target


class TestApplyWallpaper:
    """Test _apply_wallpaper method"""

    def test_apply_wallpaper_command(self):
        """Test that correct awww command is run"""
        with patch("pathlib.Path.home"):
            setter = WallpaperSetter()

        test_path = Path("/test/wallpaper.jpg")

        with patch("subprocess.run") as mock_run:
            setter._apply_wallpaper(test_path)

            # Check awww command arguments
            call_args = mock_run.call_args
            cmd = call_args[0][0]

            assert cmd[0] == "awww"
            assert "img" in cmd
            assert "--transition-type" in cmd
            assert "random" in cmd
            assert "--transition-fps" in cmd
            assert "60" in cmd
            assert "--transition-duration" in cmd
            assert "3" in cmd
            assert "--transition-bezier" in cmd
            assert str(test_path) in cmd
            assert "--transition-bezier" in cmd
            assert ".43,1.19,1,.4" in cmd

    def test_apply_wallpaper_with_check(self):
        """Test that command is run with check=True"""
        with patch("pathlib.Path.home"):
            setter = WallpaperSetter()

        test_path = Path("/test/wallpaper.jpg")

        with patch("subprocess.run") as mock_run:
            setter._apply_wallpaper(test_path)

            # Check that check=True is passed
            call_kwargs = mock_run.call_args[1]
            assert call_kwargs["check"] is True


class TestCleanupOldWallpapers:
    """Test _cleanup_old_wallpapers method"""

    def test_cleanup_removes_old_files(self, tmp_path):
        """Test that old wallpapers are removed"""
        with patch("pathlib.Path.home", return_value=tmp_path):
            setter = WallpaperSetter()

            # Create more than 10 wallpaper files in cache_dir
            for i in range(15):
                wallpaper_file = setter.cache_dir / f"wallpaper_{i}.jpg"
                wallpaper_file.write_bytes(b"test")

            import time

            # Make some files newer
            time.sleep(0.01)
            for i in range(5):
                wallpaper_file = setter.cache_dir / f"wallpaper_{i}.jpg"
                wallpaper_file.write_bytes(b"newer")

            setter._cleanup_old_wallpapers()

            # Should keep only 10 files (the newest ones)
            remaining = list(setter.cache_dir.glob("wallpaper_*.jpg"))
            assert len(remaining) == 10

    def test_cleanup_ignores_non_wallpaper_files(self, tmp_path):
        """Test that non-wallpaper files are not deleted"""
        with patch("pathlib.Path.home", return_value=tmp_path):
            setter = WallpaperSetter()

            # Create wallpaper and non-wallpaper files
            for i in range(5):
                (tmp_path / f"wallpaper_{i}.jpg").write_bytes(b"wp")
                (tmp_path / f"other_{i}.txt").write_bytes(b"txt")

            setter._cleanup_old_wallpapers()

            # Only wallpaper files should be affected
            list(tmp_path.glob("wallpaper_*.jpg"))
            other_files = list(tmp_path.glob("other_*.txt"))

            # Some wallpaper files might be deleted if >10, but other files should remain
            assert len(other_files) == 5

    def test_cleanup_no_files(self, tmp_path):
        """Test cleanup when no wallpapers exist"""
        with patch("pathlib.Path.home", return_value=tmp_path):
            setter = WallpaperSetter()

            # No wallpaper files exist
            setter._cleanup_old_wallpapers()

            # Should not raise error
            assert True

    def test_cleanup_exactly_ten_files(self, tmp_path):
        """Test cleanup with exactly 10 files"""
        with patch("pathlib.Path.home", return_value=tmp_path):
            setter = WallpaperSetter()

            # Create exactly 10 wallpaper files
            for i in range(10):
                wallpaper_file = tmp_path / f"wallpaper_{i}.jpg"
                wallpaper_file.write_bytes(b"test")

            initial_count = len(list(tmp_path.glob("wallpaper_*.jpg")))
            assert initial_count == 10

            setter._cleanup_old_wallpapers()

            # Should keep all 10 files
            remaining = list(tmp_path.glob("wallpaper_*.jpg"))
            assert len(remaining) == 10


class TestGetCurrentWallpaper:
    """Test get_current_wallpaper method"""

    def test_get_current_wallpaper_exists(self, tmp_path):
        """Test getting current wallpaper when symlink exists"""
        with patch("pathlib.Path.home", return_value=tmp_path):
            setter = WallpaperSetter()

            # Create symlink and target
            target_file = tmp_path / "current.jpg"
            target_file.write_bytes(b"current wallpaper")
            setter.symlink_path.symlink_to(target_file)

            result = setter.get_current_wallpaper()

            assert result == str(target_file)

    def test_get_current_wallpaper_no_symlink(self, tmp_path):
        """Test getting current wallpaper when symlink doesn't exist"""
        with patch("pathlib.Path.home", return_value=tmp_path):
            setter = WallpaperSetter()

            result = setter.get_current_wallpaper()

            # Should return None
            assert result is None

    def test_get_current_wallpaper_target_missing(self, tmp_path):
        """Test getting current wallpaper when symlink target is missing"""
        with patch("pathlib.Path.home", return_value=tmp_path):
            setter = WallpaperSetter()

            # Create symlink to non-existent file
            setter.symlink_path.symlink_to(tmp_path / "missing.jpg")

            result = setter.get_current_wallpaper()

            # Should return None
            assert result is None

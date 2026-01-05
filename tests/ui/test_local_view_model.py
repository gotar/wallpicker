"""Tests for LocalViewModel."""

import pytest


class TestLocalViewModelInit:
    """Test LocalViewModel initialization."""

    def test_init_with_services(self, local_view_model):
        """Test that ViewModel initializes with required services."""
        assert local_view_model.local_service is not None
        assert local_view_model.wallpaper_setter is not None

    def test_init_default_state(self, local_view_model):
        """Test initial state values."""
        assert local_view_model.wallpapers == []
        assert local_view_model.search_query == ""
        assert local_view_model.is_busy is False
        assert not local_view_model.error_message  # Empty or None


class TestLocalViewModelLoadWallpapers:
    """Test load_wallpapers method."""

    def test_load_wallpapers_success(self, local_view_model, mock_local_service):
        """Test successful wallpaper loading."""
        local_view_model.load_wallpapers()

        mock_local_service.get_wallpapers.assert_called_once_with(recursive=True)
        assert len(local_view_model.wallpapers) == 3
        assert local_view_model.is_busy is False

    def test_load_wallpapers_sets_busy(self, local_view_model, mock_local_service):
        """Test that is_busy is managed during loading."""
        # After completion, is_busy should be False
        local_view_model.load_wallpapers()
        assert local_view_model.is_busy is False

    def test_load_wallpapers_error_handling(self, local_view_model, mock_local_service):
        """Test error handling during load."""
        mock_local_service.get_wallpapers.side_effect = Exception("Test error")

        local_view_model.load_wallpapers()

        assert local_view_model.error_message is not None
        assert "Failed to load" in local_view_model.error_message
        assert local_view_model.wallpapers == []

    def test_load_wallpapers_non_recursive(self, local_view_model, mock_local_service):
        """Test non-recursive loading."""
        local_view_model.load_wallpapers(recursive=False)

        mock_local_service.get_wallpapers.assert_called_once_with(recursive=False)


class TestLocalViewModelSearchWallpapers:
    """Test search_wallpapers method."""

    def test_search_empty_query_loads_all(self, local_view_model, mock_local_service):
        """Test that empty search loads all wallpapers."""
        local_view_model.search_wallpapers("")

        mock_local_service.get_wallpapers.assert_called()

    def test_search_with_query(self, local_view_model, mock_local_service):
        """Test search with actual query."""
        # First load some wallpapers
        local_view_model.load_wallpapers()

        local_view_model.search_wallpapers("test")

        mock_local_service.search_wallpapers.assert_called_once()
        assert local_view_model.search_query == "test"

    def test_search_updates_wallpapers(self, local_view_model, mock_local_service):
        """Test that search results update wallpapers list."""
        local_view_model.load_wallpapers()
        local_view_model.search_wallpapers("test")

        # Should have filtered results
        assert len(local_view_model.wallpapers) == 1


class TestLocalViewModelDeleteWallpaper:
    """Test delete_wallpaper method."""

    def test_delete_wallpaper_success(self, local_view_model, mock_local_service):
        """Test successful wallpaper deletion."""
        local_view_model.load_wallpapers()
        wallpaper = local_view_model.wallpapers[0]

        result = local_view_model.delete_wallpaper(wallpaper)

        assert result is True
        mock_local_service.delete_wallpaper.assert_called_once_with(wallpaper.path)

    def test_delete_removes_from_list(self, local_view_model, mock_local_service):
        """Test that deleted wallpaper is removed from list."""
        local_view_model.load_wallpapers()
        initial_count = len(local_view_model.wallpapers)
        wallpaper = local_view_model.wallpapers[0]

        local_view_model.delete_wallpaper(wallpaper)

        assert len(local_view_model.wallpapers) == initial_count - 1

    def test_delete_failure_keeps_in_list(self, local_view_model, mock_local_service):
        """Test that failed deletion keeps wallpaper in list."""
        mock_local_service.delete_wallpaper.return_value = False

        local_view_model.load_wallpapers()
        initial_count = len(local_view_model.wallpapers)
        wallpaper = local_view_model.wallpapers[0]

        local_view_model.delete_wallpaper(wallpaper)

        assert len(local_view_model.wallpapers) == initial_count


class TestLocalViewModelRefresh:
    """Test refresh_wallpapers method."""

    def test_refresh_clears_search(self, local_view_model):
        """Test that refresh clears search query."""
        local_view_model.search_query = "test"

        local_view_model.refresh_wallpapers()

        assert local_view_model.search_query == ""

    def test_refresh_reloads_wallpapers(self, local_view_model, mock_local_service):
        """Test that refresh reloads wallpapers."""
        local_view_model.refresh_wallpapers()

        mock_local_service.get_wallpapers.assert_called()

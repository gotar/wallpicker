"""Tests for WallhavenViewModel."""

import pytest


class TestWallhavenViewModelInit:
    """Test WallhavenViewModel initialization."""

    def test_init_with_services(self, wallhaven_view_model):
        """Test that ViewModel initializes with required services."""
        assert wallhaven_view_model.wallhaven_service is not None
        assert wallhaven_view_model.thumbnail_cache is not None

    def test_init_default_state(self, wallhaven_view_model):
        """Test initial state values."""
        assert wallhaven_view_model.wallpapers == []
        assert wallhaven_view_model.current_page == 1
        assert wallhaven_view_model.total_pages == 1
        assert wallhaven_view_model.search_query == ""
        assert wallhaven_view_model.category == "111"
        assert wallhaven_view_model.purity == "100"
        assert wallhaven_view_model.sorting == "toplist"
        assert wallhaven_view_model.order == "desc"
        assert wallhaven_view_model.resolution == ""


class TestWallhavenViewModelSearchWallpapers:
    """Test search_wallpapers method."""

    @pytest.mark.asyncio
    async def test_search_wallpapers_success(
        self, wallhaven_view_model, mock_wallhaven_service
    ):
        """Test successful wallpaper search."""
        await wallhaven_view_model.search_wallpapers(query="nature")

        mock_wallhaven_service.search.assert_called_once()
        assert len(wallhaven_view_model.wallpapers) == 3
        assert wallhaven_view_model.search_query == "nature"
        assert wallhaven_view_model.is_busy is False

    @pytest.mark.asyncio
    async def test_search_with_filters(
        self, wallhaven_view_model, mock_wallhaven_service
    ):
        """Test search with category and purity filters."""
        await wallhaven_view_model.search_wallpapers(
            query="test",
            category="100",
            purity="110",
            sorting="random",
        )

        assert wallhaven_view_model.category == "100"
        assert wallhaven_view_model.purity == "110"
        assert wallhaven_view_model.sorting == "random"

    @pytest.mark.asyncio
    async def test_search_error_handling(
        self, wallhaven_view_model, mock_wallhaven_service
    ):
        """Test error handling during search."""
        mock_wallhaven_service.search.side_effect = Exception("API Error")

        await wallhaven_view_model.search_wallpapers(query="test")

        assert wallhaven_view_model.error_message is not None
        assert "Failed to search" in wallhaven_view_model.error_message
        assert wallhaven_view_model.wallpapers == []


class TestWallhavenViewModelPagination:
    """Test pagination methods."""

    @pytest.mark.asyncio
    async def test_load_next_page(self, wallhaven_view_model, mock_wallhaven_service):
        """Test loading next page."""
        # First search
        await wallhaven_view_model.search_wallpapers(query="test")

        # Simulate having more pages
        wallhaven_view_model.total_pages = 5
        initial_page = wallhaven_view_model.current_page

        await wallhaven_view_model.load_next_page()

        assert wallhaven_view_model.current_page == initial_page + 1

    @pytest.mark.asyncio
    async def test_load_prev_page(self, wallhaven_view_model, mock_wallhaven_service):
        """Test loading previous page."""
        # First search at page 2
        await wallhaven_view_model.search_wallpapers(query="test", page=2)

        await wallhaven_view_model.load_prev_page()

        assert wallhaven_view_model.current_page == 1

    @pytest.mark.asyncio
    async def test_load_prev_page_at_first(
        self, wallhaven_view_model, mock_wallhaven_service
    ):
        """Test that prev page does nothing at first page."""
        await wallhaven_view_model.search_wallpapers(query="test", page=1)

        await wallhaven_view_model.load_prev_page()

        # Should still be at page 1
        assert wallhaven_view_model.current_page == 1

    def test_has_next_page(self, wallhaven_view_model):
        """Test has_next_page property."""
        wallhaven_view_model._current_page = 1
        wallhaven_view_model._total_pages = 5

        assert wallhaven_view_model.has_next_page() is True

        wallhaven_view_model._current_page = 5
        assert wallhaven_view_model.has_next_page() is False

    def test_has_prev_page(self, wallhaven_view_model):
        """Test has_prev_page property."""
        wallhaven_view_model._current_page = 1

        assert wallhaven_view_model.has_prev_page() is False

        wallhaven_view_model._current_page = 3
        assert wallhaven_view_model.has_prev_page() is True

    def test_can_navigate(self, wallhaven_view_model):
        """Test can_navigate property."""
        wallhaven_view_model._current_page = 1
        wallhaven_view_model._total_pages = 1

        assert wallhaven_view_model.can_navigate() is False

        wallhaven_view_model._total_pages = 5
        assert wallhaven_view_model.can_navigate() is True


class TestWallhavenViewModelProperties:
    """Test observable properties."""

    def test_category_property(self, wallhaven_view_model):
        """Test category property get/set."""
        wallhaven_view_model.category = "010"
        assert wallhaven_view_model.category == "010"

    def test_purity_property(self, wallhaven_view_model):
        """Test purity property get/set."""
        wallhaven_view_model.purity = "111"
        assert wallhaven_view_model.purity == "111"

    def test_sorting_property(self, wallhaven_view_model):
        """Test sorting property get/set."""
        wallhaven_view_model.sorting = "random"
        assert wallhaven_view_model.sorting == "random"

    def test_resolution_property(self, wallhaven_view_model):
        """Test resolution property get/set."""
        wallhaven_view_model.resolution = "1920x1080"
        assert wallhaven_view_model.resolution == "1920x1080"

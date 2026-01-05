"""Tests for FavoritesViewModel."""

import pytest


class TestFavoritesViewModelInit:
    """Test FavoritesViewModel initialization."""

    def test_init_with_services(self, favorites_view_model):
        """Test that ViewModel initializes with required services."""
        assert favorites_view_model.favorites_service is not None
        assert favorites_view_model.wallpaper_setter is not None

    def test_init_default_state(self, favorites_view_model):
        """Test initial state values."""
        assert favorites_view_model.favorites == []
        assert favorites_view_model.search_query == ""
        assert favorites_view_model.is_busy is False
        assert not favorites_view_model.error_message  # Empty or None


class TestFavoritesViewModelLoadFavorites:
    """Test load_favorites method."""

    def test_load_favorites_success(self, favorites_view_model, mock_favorites_service):
        """Test successful favorites loading."""
        favorites_view_model.load_favorites()

        mock_favorites_service.get_favorites.assert_called_once()
        assert len(favorites_view_model.favorites) == 2
        assert favorites_view_model.is_busy is False

    def test_load_favorites_error_handling(self, favorites_view_model, mock_favorites_service):
        """Test error handling during load."""
        mock_favorites_service.get_favorites.side_effect = Exception("Test error")

        favorites_view_model.load_favorites()

        assert favorites_view_model.error_message is not None
        assert "Failed to load" in favorites_view_model.error_message
        assert favorites_view_model.favorites == []


class TestFavoritesViewModelSearchFavorites:
    """Test search_favorites method."""

    def test_search_empty_query_loads_all(self, favorites_view_model, mock_favorites_service):
        """Test that empty search loads all favorites."""
        favorites_view_model.search_favorites("")

        mock_favorites_service.get_favorites.assert_called()

    def test_search_with_query(self, favorites_view_model, mock_favorites_service):
        favorites_view_model.search_favorites("test")

        mock_favorites_service.search_favorites.assert_called_once_with("test")
        assert favorites_view_model.search_query == "test"

    def test_search_updates_favorites(self, favorites_view_model, mock_favorites_service):
        favorites_view_model.search_favorites("test")

        assert len(favorites_view_model.favorites) == 1


class TestFavoritesViewModelAddFavorite:
    """Test add_favorite method."""

    def test_add_favorite_success(self, favorites_view_model, mock_favorites_service):
        result = favorites_view_model.add_favorite(
            wallpaper_id="new_id",
            full_url="https://example.com/new.jpg",
            path="/path/to/new.jpg",
            source="local",
            tags="tag1,tag2",
        )

        assert result is True
        mock_favorites_service.add_favorite.assert_called_once()

    def test_add_favorite_failure(self, favorites_view_model, mock_favorites_service):
        mock_favorites_service.add_favorite.side_effect = Exception("Test error")

        result = favorites_view_model.add_favorite(
            wallpaper_id="new_id",
            full_url="https://example.com/new.jpg",
            path="/path/to/new.jpg",
            source="local",
            tags="",
        )

        assert result is False
        assert "Failed to add favorite" in favorites_view_model.error_message


class TestFavoritesViewModelRemoveFavorite:
    """Test remove_favorite method."""

    def test_remove_favorite_success(self, favorites_view_model, mock_favorites_service):
        """Test successful favorite removal."""
        favorites_view_model.load_favorites()
        favorite = favorites_view_model.favorites[0]

        result = favorites_view_model.remove_favorite(favorite)

        assert result is True
        mock_favorites_service.remove_favorite.assert_called_once()

    def test_remove_updates_list(self, favorites_view_model, mock_favorites_service):
        """Test that removed favorite is removed from list."""
        favorites_view_model.load_favorites()
        initial_count = len(favorites_view_model.favorites)
        favorite = favorites_view_model.favorites[0]

        favorites_view_model.remove_favorite(favorite)

        assert len(favorites_view_model.favorites) == initial_count - 1


class TestFavoritesViewModelIsFavorite:
    """Test is_favorite method."""

    def test_is_favorite_true(self, favorites_view_model, mock_favorites_service):
        """Test checking if wallpaper is in favorites."""
        mock_favorites_service.is_favorite.return_value = True

        result = favorites_view_model.is_favorite("test_id")

        assert result is True
        mock_favorites_service.is_favorite.assert_called_once_with("test_id")

    def test_is_favorite_false(self, favorites_view_model, mock_favorites_service):
        """Test checking if wallpaper is not in favorites."""
        mock_favorites_service.is_favorite.return_value = False

        result = favorites_view_model.is_favorite("test_id")

        assert result is False


class TestFavoritesViewModelRefresh:
    """Test refresh_favorites method."""

    def test_refresh_clears_search(self, favorites_view_model):
        """Test that refresh clears search query."""
        favorites_view_model.search_query = "test"

        favorites_view_model.refresh_favorites()

        assert favorites_view_model.search_query == ""

    def test_refresh_reloads_favorites(self, favorites_view_model, mock_favorites_service):
        """Test that refresh reloads favorites."""
        favorites_view_model.refresh_favorites()

        mock_favorites_service.get_favorites.assert_called()

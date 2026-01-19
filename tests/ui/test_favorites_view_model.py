"""Tests for FavoritesViewModel."""

from datetime import datetime

import pytest

from domain.favorite import Favorite
from domain.wallpaper import Resolution, Wallpaper, WallpaperPurity, WallpaperSource


@pytest.fixture
def favorites_view_model(mocker):
    """Create FavoritesViewModel with mocked dependencies."""
    from ui.view_models.favorites_view_model import FavoritesViewModel

    mock_service = mocker.MagicMock()
    mock_setter = mocker.MagicMock()

    # Create Favorite objects for testing
    favorites = [
        Favorite(
            wallpaper=Wallpaper(
                id=f"wallpaper_{i}",
                url=f"https://example.com/wallpaper_{i}.jpg",
                path=f"/path/to/wallpaper_{i}.jpg",
                source=WallpaperSource.WALLHAVEN,
                category="anime",
                purity=WallpaperPurity.SFW,
                resolution=Resolution(1920, 1080),
            ),
            added_at=datetime.now(),
        )
        for i in range(2)
    ]

    # Mock asyncio.to_thread to return a coroutine that resolves to the result
    def to_thread_mock(func, *args, **kwargs):
        async def wrapper():
            return func(*args, **kwargs)

        return wrapper()

    mocker.patch(
        "ui.view_models.favorites_view_model.asyncio.to_thread",
        side_effect=to_thread_mock,
    )

    # Mock GLib.idle_add to execute callback immediately and handle coroutines
    import asyncio
    import inspect

    def idle_add_handler(func, *args):
        # Try to call the function and check if it returns a coroutine
        try:
            result = func(*args)
            if inspect.iscoroutine(result):
                # It's a coroutine, run it with a new event loop
                asyncio.run(result)
            else:
                # It's a regular return value, nothing to do
                pass
        except Exception:
            # If calling fails, just pass
            pass

    mocker.patch(
        "ui.view_models.favorites_view_model.GLib.idle_add",
        side_effect=idle_add_handler,
    )

    # Configure service methods - use regular return_value for methods called via asyncio.to_thread
    mock_service.get_favorites.return_value = favorites
    mock_service.search_favorites.return_value = [favorites[0]]
    mock_service.is_favorite.return_value = (
        False  # Return False directly (called via asyncio.to_thread)
    )
    mock_service.add_favorite.return_value = True
    mock_service.remove_favorite.return_value = True

    return FavoritesViewModel(
        favorites_service=mock_service,
        wallpaper_setter=mock_setter,
    )


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
        assert not favorites_view_model.error_message


class TestFavoritesViewModelLoadFavorites:
    """Test load_favorites method."""

    @pytest.mark.asyncio
    async def test_load_favorites_success(self, favorites_view_model, mocker):
        """Test successful favorites loading."""
        await favorites_view_model.load_favorites()

        assert len(favorites_view_model.favorites) == 2
        assert favorites_view_model.is_busy is False


class TestFavoritesViewModelSearchFavorites:
    """Test search_favorites method."""

    @pytest.mark.asyncio
    async def test_search_empty_query_loads_all(self, favorites_view_model):
        """Test that empty search loads all favorites."""
        await favorites_view_model.search_favorites("")

        assert len(favorites_view_model.favorites) == 2

    @pytest.mark.asyncio
    async def test_search_with_query(self, favorites_view_model):
        """Test search with actual query."""
        await favorites_view_model.search_favorites("test")

        assert favorites_view_model.search_query == "test"

    @pytest.mark.asyncio
    async def test_search_updates_favorites(self, favorites_view_model):
        """Test that search results update favorites list."""
        await favorites_view_model.search_favorites("test")

        assert len(favorites_view_model.favorites) == 1


class TestFavoritesViewModelAddFavorite:
    """Test add_favorite method."""

    @pytest.mark.asyncio
    async def test_add_favorite_success(self, favorites_view_model, mocker):
        """Test successful favorite addition."""
        result = await favorites_view_model.add_favorite(
            wallpaper_id="new_id",
            full_url="https://example.com/new.jpg",
            path="/path/to/new.jpg",
            source="local",
            tags="tag1,tag2",
        )

        assert result is True


class TestFavoritesViewModelRemoveFavorite:
    """Test remove_favorite method."""

    @pytest.mark.asyncio
    async def test_remove_favorite_success(self, favorites_view_model):
        """Test successful favorite removal."""
        await favorites_view_model.load_favorites()
        favorite = favorites_view_model.favorites[0]

        result = await favorites_view_model.remove_favorite(favorite)

        assert result is True

    @pytest.mark.asyncio
    async def test_remove_updates_list(self, favorites_view_model):
        """Test that removed favorite is removed from list."""
        await favorites_view_model.load_favorites()
        initial_count = len(favorites_view_model.favorites)
        favorite = favorites_view_model.favorites[0]

        await favorites_view_model.remove_favorite(favorite)

        assert len(favorites_view_model.favorites) == initial_count - 1


class TestFavoritesViewModelIsFavorite:
    """Test is_favorite method."""

    @pytest.mark.asyncio
    async def test_is_favorite_true(self, favorites_view_model, mocker):
        """Test checking if wallpaper is in favorites."""
        favorites_view_model.favorites_service.is_favorite.return_value = True

        result = await favorites_view_model.is_favorite("test_id")

        assert result is True

    @pytest.mark.asyncio
    async def test_is_favorite_false(self, favorites_view_model):
        """Test checking if wallpaper is not in favorites."""
        result = await favorites_view_model.is_favorite("test_id")

        assert result is False


class TestFavoritesViewModelRefresh:
    """Test refresh_favorites method."""

    @pytest.mark.asyncio
    async def test_refresh_clears_search(self, favorites_view_model):
        """Test that refresh clears search query."""
        favorites_view_model.search_query = "test"

        await favorites_view_model.refresh_favorites()

        assert favorites_view_model.search_query == ""

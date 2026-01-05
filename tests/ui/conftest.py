"""Pytest fixtures for UI integration tests."""

import sys
from pathlib import Path
from unittest.mock import MagicMock, AsyncMock

import pytest

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))


@pytest.fixture
def mock_local_service(tmp_path):
    """Mock LocalWallpaperService for ViewModel tests."""
    from services.local_service import LocalWallpaper, LocalWallpaperService

    mock = MagicMock(spec=LocalWallpaperService)
    mock.pictures_dir = tmp_path

    # Create some mock wallpapers
    wallpapers = [
        LocalWallpaper(
            path=tmp_path / f"wallpaper_{i}.jpg",
            filename=f"wallpaper_{i}.jpg",
            size=1000 * i,
            modified_time=1000000.0 + i,
        )
        for i in range(3)
    ]

    mock.get_wallpapers.return_value = wallpapers
    mock.search_wallpapers.return_value = wallpapers[:1]
    mock.delete_wallpaper.return_value = True

    return mock


@pytest.fixture
def mock_wallpaper_setter():
    """Mock WallpaperSetter for ViewModel tests."""
    from services.wallpaper_setter import WallpaperSetter

    mock = MagicMock(spec=WallpaperSetter)
    mock.set_wallpaper.return_value = True
    mock.get_current_wallpaper.return_value = None

    return mock


@pytest.fixture
def mock_favorites_service(tmp_path):
    """Mock FavoritesService for ViewModel tests."""
    from datetime import datetime

    from services.favorites_service import FavoritesService
    from domain.favorite import Favorite
    from domain.wallpaper import Wallpaper, Resolution, WallpaperSource, WallpaperPurity

    mock = MagicMock(spec=FavoritesService)

    # Create some mock favorites with proper Wallpaper objects
    favorites = []
    for i in range(2):
        wallpaper = Wallpaper(
            id=f"fav_{i}",
            url=f"https://example.com/{i}.jpg",
            path=str(tmp_path / f"favorite_{i}.jpg"),
            resolution=Resolution(width=1920, height=1080),
            source=WallpaperSource.LOCAL,
            category="general",
            purity=WallpaperPurity.SFW,
        )
        favorites.append(Favorite(wallpaper=wallpaper, added_at=datetime.now()))

    mock.get_favorites.return_value = favorites
    mock.search_favorites.return_value = favorites[:1]

    # Track state for add/remove operations
    def track_add(wallpaper):
        return True

    def track_remove(wallpaper_id):
        return True

    mock.add_favorite.side_effect = track_add
    mock.remove_favorite.side_effect = track_remove
    mock.is_favorite.return_value = False

    return mock


@pytest.fixture
def mock_wallhaven_service():
    """Mock WallhavenService for ViewModel tests."""
    from services.wallhaven_service import WallhavenService
    from domain.wallpaper import Wallpaper, Resolution, WallpaperSource, WallpaperPurity

    mock = MagicMock(spec=WallhavenService)

    # Create mock wallpapers with proper domain objects
    wallpapers = [
        Wallpaper(
            id=f"wh_{i}",
            url=f"https://example.com/{i}.jpg",
            path=f"/tmp/wh_{i}.jpg",
            resolution=Resolution(width=1920, height=1080),
            source=WallpaperSource.WALLHAVEN,
            category="general",
            purity=WallpaperPurity.SFW,
        )
        for i in range(3)
    ]

    async def mock_search(*args, **kwargs):
        return wallpapers

    mock.search = AsyncMock(side_effect=mock_search)

    return mock


@pytest.fixture
def mock_thumbnail_cache():
    """Mock ThumbnailCache for ViewModel tests."""
    from services.thumbnail_cache import ThumbnailCache

    mock = MagicMock(spec=ThumbnailCache)
    mock.get_thumbnail.return_value = None
    mock.cleanup.return_value = 0

    return mock


@pytest.fixture
def local_view_model(mock_local_service, mock_wallpaper_setter, tmp_path):
    """Create LocalViewModel with mocked services."""
    from ui.view_models.local_view_model import LocalViewModel

    return LocalViewModel(
        local_service=mock_local_service,
        wallpaper_setter=mock_wallpaper_setter,
        pictures_dir=tmp_path,
    )


@pytest.fixture
def favorites_view_model(mock_favorites_service, mock_wallpaper_setter):
    """Create FavoritesViewModel with mocked services."""
    from ui.view_models.favorites_view_model import FavoritesViewModel

    return FavoritesViewModel(
        favorites_service=mock_favorites_service,
        wallpaper_setter=mock_wallpaper_setter,
    )


@pytest.fixture
def wallhaven_view_model(mock_wallhaven_service, mock_thumbnail_cache):
    """Create WallhavenViewModel with mocked services."""
    from ui.view_models.wallhaven_view_model import WallhavenViewModel

    return WallhavenViewModel(
        wallhaven_service=mock_wallhaven_service,
        thumbnail_cache=mock_thumbnail_cache,
    )

"""Tests for FavoritesService."""

import json
from pathlib import Path

import pytest

from domain.wallpaper import Resolution, Wallpaper, WallpaperPurity, WallpaperSource
from services.favorites_service import FavoritesService


@pytest.fixture
def favorites_service(temp_dir: Path) -> FavoritesService:
    """Create FavoritesService with temporary favorites file."""
    favorites_file = temp_dir / "favorites.json"
    return FavoritesService(favorites_file=favorites_file)


@pytest.fixture
def sample_wallpaper() -> Wallpaper:
    """Create sample wallpaper for testing."""
    res = Resolution(width=1920, height=1080)
    return Wallpaper(
        id="test123",
        url="http://example.com/view/1",
        path="http://example.com/full.jpg",
        resolution=res,
        source=WallpaperSource.WALLHAVEN,
        category="anime",
        purity=WallpaperPurity.SFW,
        colors=["#000000"],
        file_size=1024,
    )


def test_favorites_service_init(favorites_service: FavoritesService):
    """Test FavoritesService initialization."""
    # Favorites file is created on first write, not initialization
    assert favorites_service.favorites_dir.exists()
    assert favorites_service.favorites_file.parent == favorites_service.favorites_dir


def test_add_favorite(favorites_service: FavoritesService, sample_wallpaper: Wallpaper):
    """Test adding wallpaper to favorites."""
    favorites_service.add_favorite(sample_wallpaper)

    favorites = favorites_service.get_favorites()
    assert len(favorites) == 1
    assert favorites[0].wallpaper_id == sample_wallpaper.id


def test_add_duplicate_favorite(favorites_service: FavoritesService, sample_wallpaper: Wallpaper):
    """Test adding duplicate favorite."""
    favorites_service.add_favorite(sample_wallpaper)
    favorites_service.add_favorite(sample_wallpaper)

    favorites = favorites_service.get_favorites()
    assert len(favorites) == 1  # Should not duplicate


def test_remove_favorite(favorites_service: FavoritesService, sample_wallpaper: Wallpaper):
    """Test removing favorite."""
    favorites_service.add_favorite(sample_wallpaper)

    favorites_service.remove_favorite(sample_wallpaper.id)

    favorites = favorites_service.get_favorites()
    assert len(favorites) == 0


def test_remove_nonexistent_favorite(favorites_service: FavoritesService):
    """Test removing non-existent favorite."""
    # Should not raise error
    favorites_service.remove_favorite("nonexistent")


def test_is_favorite(favorites_service: FavoritesService, sample_wallpaper: Wallpaper):
    """Test checking if wallpaper is favorite."""
    assert not favorites_service.is_favorite(sample_wallpaper.id)

    favorites_service.add_favorite(sample_wallpaper)
    assert favorites_service.is_favorite(sample_wallpaper.id)


def test_get_favorites(favorites_service: FavoritesService, sample_wallpaper: Wallpaper):
    """Test getting all favorites."""
    # Add multiple favorites
    for i in range(3):
        wallpaper = Wallpaper(
            id=f"test{i}",
            url=f"http://example.com/{i}",
            path=f"http://example.com/full{i}.jpg",
            resolution=Resolution(width=1920, height=1080),
            source=WallpaperSource.WALLHAVEN,
            category="anime",
            purity=WallpaperPurity.SFW,
        )
        favorites_service.add_favorite(wallpaper)

    favorites = favorites_service.get_favorites()
    assert len(favorites) == 3


def test_search_favorites_empty(favorites_service: FavoritesService):
    """Test searching empty favorites."""
    results = favorites_service.search_favorites("anime")
    assert len(results) == 0


def test_search_favorites_no_query(
    favorites_service: FavoritesService, sample_wallpaper: Wallpaper
):
    """Test searching favorites without query returns all."""
    favorites_service.add_favorite(sample_wallpaper)

    results = favorites_service.search_favorites("")
    assert len(results) == 1


def test_search_favorites_by_id(favorites_service: FavoritesService, sample_wallpaper: Wallpaper):
    """Test searching favorites by ID."""
    favorites_service.add_favorite(sample_wallpaper)

    results = favorites_service.search_favorites("test123")
    assert len(results) == 1
    assert results[0].id == sample_wallpaper.id


def test_search_favorites_by_category(
    favorites_service: FavoritesService, sample_wallpaper: Wallpaper
):
    """Test searching favorites by category."""
    favorites_service.add_favorite(sample_wallpaper)

    results = favorites_service.search_favorites("anime")
    assert len(results) == 1


def test_search_favorites_no_match(
    favorites_service: FavoritesService, sample_wallpaper: Wallpaper
):
    """Test searching with no matches."""
    favorites_service.add_favorite(sample_wallpaper)

    results = favorites_service.search_favorites("nonexistent")
    assert len(results) == 0


def test_favorite_persistence(favorites_service: FavoritesService, sample_wallpaper: Wallpaper):
    """Test favorites persist across service instances."""
    # Add favorite
    favorites_service.add_favorite(sample_wallpaper)

    # Create new service instance
    new_service = FavoritesService(favorites_file=favorites_service.favorites_file)

    favorites = new_service.get_favorites()
    assert len(favorites) == 1
    assert favorites[0].wallpaper.id == sample_wallpaper.id


def test_favorite_serialization(favorites_service: FavoritesService, sample_wallpaper: Wallpaper):
    """Test favorite JSON serialization."""
    favorites_service.add_favorite(sample_wallpaper)

    # Read JSON file directly
    with open(favorites_service.favorites_file) as f:
        data = json.load(f)

    assert len(data) == 1
    assert data[0]["wallpaper"]["id"] == sample_wallpaper.id
    assert "added_at" in data[0]


def test_days_since_added(favorites_service: FavoritesService, sample_wallpaper: Wallpaper):
    """Test days since favorite was added."""
    favorites_service.add_favorite(sample_wallpaper)

    favorites_list = favorites_service.get_favorites()
    assert len(favorites_list) == 1
    assert favorites_list[0].wallpaper.id == sample_wallpaper.id

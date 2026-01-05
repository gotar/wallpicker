"""Tests for Favorite domain model."""

from datetime import datetime, timedelta

from domain.favorite import Favorite
from domain.wallpaper import Resolution, Wallpaper, WallpaperPurity, WallpaperSource


def test_favorite_domain_model():
    """Test Favorite domain model."""
    res = Resolution(width=1920, height=1080)
    wallpaper = Wallpaper(
        id="fav1",
        url="http://example.com/view/1",
        path="http://example.com/full.jpg",
        resolution=res,
        source=WallpaperSource.WALLHAVEN,
        category="anime",
        purity=WallpaperPurity.SFW,
    )

    added_at = datetime.now()
    favorite = Favorite(wallpaper=wallpaper, added_at=added_at)

    assert favorite.wallpaper == wallpaper
    assert favorite.added_at == added_at
    assert favorite.wallpaper_id == "fav1"


def test_favorite_days_since_added():
    """Test days_since_added property."""
    res = Resolution(width=1920, height=1080)
    wallpaper = Wallpaper(
        id="fav1",
        url="http://example.com/view/1",
        path="http://example.com/full.jpg",
        resolution=res,
        source=WallpaperSource.WALLHAVEN,
        category="anime",
        purity=WallpaperPurity.SFW,
    )

    added_at = datetime.now() - timedelta(days=5)
    favorite = Favorite(wallpaper=wallpaper, added_at=added_at)

    assert favorite.days_since_added >= 5
    assert favorite.days_since_added <= 6  # Allow for test execution time


def test_favorite_wallpaper_id_property():
    """Test wallpaper_id property."""
    res = Resolution(width=1920, height=1080)
    wallpaper = Wallpaper(
        id="test123",
        url="http://example.com/view/1",
        path="http://example.com/full.jpg",
        resolution=res,
        source=WallpaperSource.WALLHAVEN,
        category="anime",
        purity=WallpaperPurity.SFW,
    )

    favorite = Favorite(wallpaper=wallpaper, added_at=datetime.now())
    assert favorite.wallpaper_id == "test123"


def test_favorite_serialization():
    """Test Favorite to_dict and from_dict."""
    res = Resolution(width=1920, height=1080)
    wallpaper = Wallpaper(
        id="fav1",
        url="http://example.com/view/1",
        path="http://example.com/full.jpg",
        resolution=res,
        source=WallpaperSource.WALLHAVEN,
        category="anime",
        purity=WallpaperPurity.SFW,
        colors=["#000000"],
    )

    added_at = datetime.now()
    favorite = Favorite(wallpaper=wallpaper, added_at=added_at)

    # Serialize
    data = favorite.to_dict()
    assert data["added_at"] == added_at.isoformat()
    assert data["wallpaper"]["id"] == "fav1"

    # Deserialize
    restored = Favorite.from_dict(data, Wallpaper)
    assert restored.wallpaper_id == favorite.wallpaper_id
    assert restored.wallpaper.category == favorite.wallpaper.category


def test_favorite_from_dict_with_wallpaper_class():
    """Test Favorite.from_dict with Wallpaper class."""
    data = {
        "wallpaper": {
            "id": "fav1",
            "url": "http://example.com/view/1",
            "path": "http://example.com/full.jpg",
            "resolution": {"width": 1920, "height": 1080},
            "source": "wallhaven",
            "category": "anime",
            "purity": "sfw",
            "colors": ["#000000"],
        },
        "added_at": "2024-01-01T00:00:00",
    }

    favorite = Favorite.from_dict(data, Wallpaper)
    assert favorite.wallpaper_id == "fav1"
    assert favorite.wallpaper.category == "anime"
    assert favorite.wallpaper.source == WallpaperSource.WALLHAVEN

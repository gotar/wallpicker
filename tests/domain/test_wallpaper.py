"""Tests for Wallpaper domain model."""

import pytest

from domain.wallpaper import Resolution, Wallpaper, WallpaperPurity, WallpaperSource


def test_resolution_value_object():
    """Test Resolution value object."""
    res = Resolution(width=1920, height=1080)
    assert res.width == 1920
    assert res.height == 1080
    assert res.aspect_ratio == 1920 / 1080
    assert str(res) == "1920x1080"


def test_resolution_to_dict():
    """Test Resolution serialization."""
    res = Resolution(width=1920, height=1080)
    data = res.to_dict()
    assert data == {"width": 1920, "height": 1080}


def test_resolution_immutability():
    """Test Resolution is immutable."""
    res = Resolution(width=1920, height=1080)
    # dataclass(frozen=True) makes it immutable
    with pytest.raises(AttributeError):
        res.width = 3840


def test_wallpaper_domain_model():
    """Test Wallpaper domain model."""
    res = Resolution(width=1920, height=1080)
    wallpaper = Wallpaper(
        id="test1",
        url="http://example.com/view/1",
        path="http://example.com/full.jpg",
        resolution=res,
        source=WallpaperSource.WALLHAVEN,
        category="anime",
        purity=WallpaperPurity.SFW,
        colors=["#000000"],
        file_size=1024,
        thumbs_large="http://example.com/thumb.jpg",
        thumbs_small="http://example.com/small.jpg",
    )

    assert wallpaper.id == "test1"
    assert wallpaper.is_landscape
    assert not wallpaper.is_portrait
    assert wallpaper.size_mb == 1024 / (1024 * 1024)


def test_wallpaper_matches_query():
    """Test wallpaper query matching."""
    res = Resolution(width=1920, height=1080)
    wallpaper = Wallpaper(
        id="test123",
        url="http://example.com/anime/1.jpg",
        path="http://example.com/full.jpg",
        resolution=res,
        source=WallpaperSource.WALLHAVEN,
        category="anime",
        purity=WallpaperPurity.SFW,
    )

    assert wallpaper.matches_query("test")
    assert wallpaper.matches_query("anime")
    assert wallpaper.matches_query("example")
    assert not wallpaper.matches_query("nonexistent")


def test_wallpaper_serialization():
    """Test Wallpaper to_dict and from_dict."""
    res = Resolution(width=1920, height=1080)
    wallpaper = Wallpaper(
        id="test1",
        url="http://example.com/view/1",
        path="http://example.com/full.jpg",
        resolution=res,
        source=WallpaperSource.WALLHAVEN,
        category="anime",
        purity=WallpaperPurity.SFW,
        colors=["#000000"],
        file_size=1024,
    )

    # Serialize
    data = wallpaper.to_dict()
    assert data["id"] == "test1"
    assert data["source"] == "wallhaven"
    assert data["purity"] == "sfw"

    # Deserialize
    restored = Wallpaper.from_dict(data)
    assert restored.id == wallpaper.id
    assert restored.source == wallpaper.source
    assert restored.purity == wallpaper.purity


def test_wallpaper_from_dict_defaults():
    """Test Wallpaper.from_dict with missing fields."""
    data = {
        "id": "test1",
        "url": "http://example.com/view/1",
        "path": "http://example.com/full.jpg",
        "resolution": {"width": 1920, "height": 1080},
        "source": "wallhaven",
        "category": "general",
        "purity": "sfw",
    }

    wallpaper = Wallpaper.from_dict(data)
    assert wallpaper.id == "test1"
    assert wallpaper.colors == []
    assert wallpaper.file_size == 0
    assert wallpaper.thumbs_large == ""

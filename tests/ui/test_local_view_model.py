"""Tests for LocalViewModel."""

import pytest

from services.local_service import LocalWallpaper


@pytest.fixture
def local_view_model(mocker, tmp_path):
    """Create LocalViewModel with mocked dependencies."""
    from ui.view_models.local_view_model import LocalViewModel

    mock_service = mocker.MagicMock()
    mock_setter = mocker.MagicMock()

    wallpapers = [
        LocalWallpaper(
            path=tmp_path / f"wallpaper_{i}.jpg",
            filename=f"wallpaper_{i}.jpg",
            size=1000 * i,
            modified_time=1000000.0 + i,
            tags=[],
        )
        for i in range(3)
    ]
    mock_service.get_wallpapers_async = mocker.AsyncMock(return_value=wallpapers)
    mock_service.search_wallpapers_async = mocker.AsyncMock(return_value=wallpapers[:1])
    mock_service.delete_wallpaper_async = mocker.AsyncMock(return_value=True)

    mocker.patch(
        "ui.view_models.local_view_model.GLib.idle_add",
        side_effect=lambda func, *args: func(*args),
    )

    return LocalViewModel(
        local_service=mock_service,
        wallpaper_setter=mock_setter,
        toast_service=None,
    )


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
        assert not local_view_model.error_message


class TestLocalViewModelLoadWallpapers:
    """Test load_wallpapers method."""

    @pytest.mark.asyncio
    async def test_load_wallpapers_success(self, local_view_model, mocker):
        """Test successful wallpaper loading."""
        await local_view_model.load_wallpapers()

        assert len(local_view_model.wallpapers) == 3
        assert local_view_model.is_busy is False

    @pytest.mark.asyncio
    async def test_load_wallpapers_sets_busy(self, local_view_model):
        """Test that is_busy is managed during loading."""
        await local_view_model.load_wallpapers()
        assert local_view_model.is_busy is False


class TestLocalViewModelSearchWallpapers:
    """Test search_wallpapers method."""

    @pytest.mark.asyncio
    async def test_search_empty_query_loads_all(self, local_view_model):
        """Test that empty search loads all wallpapers."""
        await local_view_model.search_wallpapers("")

        assert len(local_view_model.wallpapers) == 3

    @pytest.mark.asyncio
    async def test_search_with_query(self, local_view_model):
        """Test search with actual query."""
        await local_view_model.search_wallpapers("test")

        assert local_view_model.search_query == "test"

    @pytest.mark.asyncio
    async def test_search_updates_wallpapers(self, local_view_model):
        """Test that search results update wallpapers list."""
        await local_view_model.search_wallpapers("test")

        assert len(local_view_model.wallpapers) == 1


class TestLocalViewModelDeleteWallpaper:
    """Test delete_wallpaper method."""

    @pytest.mark.asyncio
    async def test_delete_wallpaper_success(self, local_view_model):
        """Test successful wallpaper deletion."""
        await local_view_model.load_wallpapers()
        wallpaper = local_view_model.wallpapers[0]

        success, message = await local_view_model.delete_wallpaper(wallpaper)

        assert success is True
        assert "Deleted" in message

    @pytest.mark.asyncio
    async def test_delete_removes_from_list(self, local_view_model):
        """Test that deleted wallpaper is removed from list."""
        await local_view_model.load_wallpapers()
        initial_count = len(local_view_model.wallpapers)
        wallpaper = local_view_model.wallpapers[0]

        await local_view_model.delete_wallpaper(wallpaper)

        assert len(local_view_model.wallpapers) == initial_count - 1


class TestLocalViewModelRefresh:
    """Test refresh_wallpapers method."""

    @pytest.mark.asyncio
    async def test_refresh_clears_search(self, local_view_model):
        """Test that refresh clears search query."""
        local_view_model.search_query = "test"

        await local_view_model.refresh_wallpapers()

        assert local_view_model.search_query == ""


class TestLocalViewModelSorting:
    """Test sorting methods."""

    def test_sort_by_name(self, local_view_model, tmp_path):
        """Test sorting wallpapers by name."""
        local_view_model._wallpapers = [
            LocalWallpaper(
                path=tmp_path / "zebra.jpg",
                filename="zebra.jpg",
                size=100,
                modified_time=1.0,
            ),
            LocalWallpaper(
                path=tmp_path / "alpha.jpg",
                filename="alpha.jpg",
                size=100,
                modified_time=2.0,
            ),
            LocalWallpaper(
                path=tmp_path / "beta.jpg",
                filename="beta.jpg",
                size=100,
                modified_time=3.0,
            ),
        ]

        local_view_model.sort_by_name()

        filenames = [w.filename for w in local_view_model.wallpapers]
        assert filenames == ["alpha.jpg", "beta.jpg", "zebra.jpg"]

    def test_sort_by_date(self, local_view_model, tmp_path):
        """Test sorting wallpapers by date (newest first)."""
        local_view_model._wallpapers = [
            LocalWallpaper(
                path=tmp_path / "old.jpg",
                filename="old.jpg",
                size=100,
                modified_time=1000.0,
            ),
            LocalWallpaper(
                path=tmp_path / "new.jpg",
                filename="new.jpg",
                size=100,
                modified_time=3000.0,
            ),
            LocalWallpaper(
                path=tmp_path / "mid.jpg",
                filename="mid.jpg",
                size=100,
                modified_time=2000.0,
            ),
        ]

        local_view_model.sort_by_date()

        filenames = [w.filename for w in local_view_model.wallpapers]
        assert filenames == ["new.jpg", "mid.jpg", "old.jpg"]

    def test_sort_by_resolution(self, local_view_model, tmp_path):
        """Test sorting wallpapers by resolution (largest first)."""
        wp1 = LocalWallpaper(
            path=tmp_path / "small.jpg",
            filename="small.jpg",
            size=100,
            modified_time=1.0,
        )
        wp1._resolution = "1920x1080"
        wp2 = LocalWallpaper(
            path=tmp_path / "large.jpg",
            filename="large.jpg",
            size=100,
            modified_time=2.0,
        )
        wp2._resolution = "3840x2160"
        wp3 = LocalWallpaper(
            path=tmp_path / "medium.jpg",
            filename="medium.jpg",
            size=100,
            modified_time=3.0,
        )
        wp3._resolution = "2560x1440"

        local_view_model._wallpapers = [wp1, wp2, wp3]

        local_view_model.sort_by_resolution()

        filenames = [w.filename for w in local_view_model.wallpapers]
        assert filenames == ["large.jpg", "medium.jpg", "small.jpg"]


class TestLocalViewModelFiltering:
    """Test filter methods."""

    def test_apply_resolution_filter_all(self, local_view_model, tmp_path):
        """Test resolution filter with 'All' returns everything."""
        wp1 = LocalWallpaper(
            path=tmp_path / "small.jpg",
            filename="small.jpg",
            size=100,
            modified_time=1.0,
        )
        wp1._resolution = "1280x720"
        wp2 = LocalWallpaper(
            path=tmp_path / "large.jpg",
            filename="large.jpg",
            size=100,
            modified_time=2.0,
        )
        wp2._resolution = "3840x2160"

        result = local_view_model._apply_resolution_filter([wp1, wp2], {})

        assert len(result) == 2

    def test_apply_resolution_filter_minimum(self, local_view_model, tmp_path):
        """Test resolution filter with minimum resolution."""
        wp1 = LocalWallpaper(
            path=tmp_path / "small.jpg",
            filename="small.jpg",
            size=100,
            modified_time=1.0,
        )
        wp1._resolution = "1280x720"
        wp2 = LocalWallpaper(
            path=tmp_path / "hd.jpg", filename="hd.jpg", size=100, modified_time=2.0
        )
        wp2._resolution = "1920x1080"
        wp3 = LocalWallpaper(
            path=tmp_path / "4k.jpg", filename="4k.jpg", size=100, modified_time=3.0
        )
        wp3._resolution = "3840x2160"

        result = local_view_model._apply_resolution_filter(
            [wp1, wp2, wp3], {"resolution": "1920x1080"}
        )

        filenames = [w.filename for w in result]
        assert "small.jpg" not in filenames
        assert "hd.jpg" in filenames
        assert "4k.jpg" in filenames

    def test_apply_aspect_filter_16x9(self, local_view_model, tmp_path):
        """Test aspect ratio filter for 16:9."""
        wp1 = LocalWallpaper(
            path=tmp_path / "wide.jpg", filename="wide.jpg", size=100, modified_time=1.0
        )
        wp1._resolution = "1920x1080"
        wp2 = LocalWallpaper(
            path=tmp_path / "square.jpg",
            filename="square.jpg",
            size=100,
            modified_time=2.0,
        )
        wp2._resolution = "1000x1000"
        wp3 = LocalWallpaper(
            path=tmp_path / "ultrawide.jpg",
            filename="ultrawide.jpg",
            size=100,
            modified_time=3.0,
        )
        wp3._resolution = "2560x1080"

        result = local_view_model._apply_aspect_filter([wp1, wp2, wp3], {"ratios": "16x9"})

        filenames = [w.filename for w in result]
        assert "wide.jpg" in filenames
        assert "square.jpg" not in filenames
        assert "ultrawide.jpg" not in filenames

    def test_apply_aspect_filter_square(self, local_view_model, tmp_path):
        """Test aspect ratio filter for 1:1 (square)."""
        wp1 = LocalWallpaper(
            path=tmp_path / "wide.jpg", filename="wide.jpg", size=100, modified_time=1.0
        )
        wp1._resolution = "1920x1080"
        wp2 = LocalWallpaper(
            path=tmp_path / "square.jpg",
            filename="square.jpg",
            size=100,
            modified_time=2.0,
        )
        wp2._resolution = "1000x1000"

        result = local_view_model._apply_aspect_filter([wp1, wp2], {"ratios": "1x1"})

        filenames = [w.filename for w in result]
        assert "square.jpg" in filenames
        assert "wide.jpg" not in filenames

    def test_apply_aspect_filter_all(self, local_view_model, tmp_path):
        """Test aspect ratio filter with 'All' returns everything."""
        wp1 = LocalWallpaper(
            path=tmp_path / "wide.jpg", filename="wide.jpg", size=100, modified_time=1.0
        )
        wp1._resolution = "1920x1080"
        wp2 = LocalWallpaper(
            path=tmp_path / "square.jpg",
            filename="square.jpg",
            size=100,
            modified_time=2.0,
        )
        wp2._resolution = "1000x1000"

        result = local_view_model._apply_aspect_filter([wp1, wp2], {})

        assert len(result) == 2

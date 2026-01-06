"""Tests for WallhavenService refactored implementation."""

from unittest.mock import AsyncMock, MagicMock, patch

import aiohttp
import pytest

from domain.exceptions import ServiceError
from domain.wallpaper import (
    Resolution,
    Wallpaper,
    WallpaperPurity,
    WallpaperSource,
)
from services.wallhaven_service import WallhavenService


class MockAsyncContextManager:
    """Helper for mocking async context managers."""

    def __init__(self, return_value):
        self.return_value = return_value

    async def __aenter__(self):
        return self.return_value

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        pass


class TestWallhavenServiceInit:
    """Tests for WallhavenService initialization."""

    def test_init_with_api_key(self):
        """Test initialization with API key."""
        service = WallhavenService(api_key="test_key")
        assert service.api_key == "test_key"
        assert service.BASE_URL == "https://wallhaven.cc/api/v1"

    def test_init_without_api_key(self):
        """Test initialization without API key."""
        service = WallhavenService()
        assert service.api_key is None

    def test_rate_limit_config(self):
        """Test rate limiting configuration."""
        service = WallhavenService()
        assert service.RATE_LIMIT == 45
        assert service.REQUEST_INTERVAL == 60 / 45

    def test_presets_config(self):
        """Test presets configuration."""
        service = WallhavenService()
        assert "Anime" in service.PRESETS
        assert service.PRESETS["Anime"] == {"purity": "sfw", "categories": "010"}


class TestGetSession:
    """Tests for _get_session method."""

    @pytest.mark.asyncio
    async def test_create_session_with_api_key(self):
        """Test creating session with API key."""
        service = WallhavenService(api_key="test_key")

        with patch("aiohttp.ClientSession") as mock_session_cls:
            await service._get_session()

            mock_session_cls.assert_called_once_with(headers={"X-API-Key": "test_key"})

    @pytest.mark.asyncio
    async def test_create_session_without_api_key(self):
        """Test creating session without API key."""
        service = WallhavenService()

        with patch("aiohttp.ClientSession") as mock_session_cls:
            await service._get_session()

            # Even without API key, headers={} is passed
            mock_session_cls.assert_called_once_with(headers={})

    @pytest.mark.asyncio
    async def test_reuse_existing_session(self):
        """Test reusing existing session."""
        service = WallhavenService()
        service._session = AsyncMock()

        session = await service._get_session()

        assert session is service._session

    @pytest.mark.asyncio
    async def test_create_new_session_after_close(self):
        """Test creating new session after closing previous one."""
        service = WallhavenService()
        service._session = None

        with patch("aiohttp.ClientSession") as mock_session_cls:
            await service._get_session()

            # Even without API key, headers={} is passed
            mock_session_cls.assert_called_once_with(headers={})


class TestRateLimit:
    """Tests for _rate_limit method."""

    @pytest.mark.asyncio
    async def test_rate_limit_no_delay(self):
        """Test rate limiting when enough time has passed."""
        service = WallhavenService()
        service._last_request_time = 0.0

        with patch("asyncio.sleep") as mock_sleep:
            await service._rate_limit()

            mock_sleep.assert_not_called()

    @pytest.mark.asyncio
    async def test_rate_limit_with_delay(self):
        """Test rate limiting when not enough time has passed."""
        service = WallhavenService()

        # Set last request to recent past (will trigger sleep)
        import asyncio

        service._last_request_time = asyncio.get_event_loop().time()

        with patch("asyncio.sleep") as mock_sleep:
            await service._rate_limit()

            # Should have called sleep since not enough time passed
            assert mock_sleep.called
            # Sleep time should be positive
            sleep_args = mock_sleep.call_args[0]
            assert sleep_args[0] > 0


class TestSearch:
    """Tests for search method."""

    @pytest.fixture
    def sample_wallpaper_response(self):
        """Sample Wallhaven API response."""
        return {
            "data": [
                {
                    "id": "abc123",
                    "url": "https://wallhaven.cc/w/abc123",
                    "path": "https://w.wallhaven.cc/full/abc123.jpg",
                    "dimension_x": 1920,
                    "dimension_y": 1080,
                    "category": "general",
                    "purity": "sfw",
                    "colors": ["#ff0000", "#00ff00"],
                },
                {
                    "id": "def456",
                    "url": "https://wallhaven.cc/w/def456",
                    "path": "https://w.wallhaven.cc/full/def456.jpg",
                    "dimension_x": 2560,
                    "dimension_y": 1440,
                    "category": "anime",
                    "purity": "sfw",
                    "colors": ["#0000ff"],
                },
            ],
            "meta": {
                "current_page": 1,
                "last_page": 5,
                "per_page": 24,
                "total": 120,
                "query": "",
            },
        }

    @pytest.fixture
    def wallhaven_service(self):
        """Create WallhavenService instance."""
        return WallhavenService()

    @pytest.mark.asyncio
    async def test_search_success(self, wallhaven_service, sample_wallpaper_response):
        """Test successful search."""
        with patch.object(wallhaven_service, "_get_session") as mock_get_session:
            with patch.object(wallhaven_service, "_rate_limit") as mock_rate_limit:
                mock_session = AsyncMock()
                mock_response = MagicMock()
                mock_response.status = 200
                mock_response.raise_for_status = MagicMock()
                mock_response.json = AsyncMock(return_value=sample_wallpaper_response)

                # Mock async context manager for session.get()
                mock_context = MockAsyncContextManager(mock_response)
                mock_session.get = MagicMock(return_value=mock_context)
                mock_get_session.return_value = mock_session

                wallpapers, meta = await wallhaven_service.search(query="test")

                assert len(wallpapers) == 2
                assert all(isinstance(w, Wallpaper) for w in wallpapers)
                assert wallpapers[0].id == "abc123"
                assert wallpapers[1].id == "def456"
                assert meta["current_page"] == 1
                assert meta["last_page"] == 5
                mock_rate_limit.assert_called_once()

    @pytest.mark.asyncio
    async def test_search_with_params(self, wallhaven_service):
        """Test search with custom parameters."""
        with patch.object(wallhaven_service, "_get_session") as mock_get_session:
            with patch.object(wallhaven_service, "_rate_limit"):
                mock_session = AsyncMock()
                mock_response = MagicMock()
                mock_response.status = 200
                mock_response.raise_for_status = MagicMock()
                mock_response.json = AsyncMock(return_value={"data": []})

                # Mock async context manager
                mock_context = MockAsyncContextManager(mock_response)
                mock_session.get = MagicMock(return_value=mock_context)
                mock_get_session.return_value = mock_session

                await wallhaven_service.search(
                    query="anime",
                    page=2,
                    categories="010",
                    purity="sfw",
                    sorting="views",
                    order="asc",
                    atleast="1920x1080",
                    top_range="1w",
                    ratios="16x9,16x10",
                    colors="0066cc",
                    resolutions="1920x1080,2560x1440",
                    seed="abc123",
                )

                # Verify params were passed correctly
                call_args = mock_session.get.call_args
                params = call_args[1]["params"]
                assert params["q"] == "anime"
                assert params["page"] == 2
                assert params["categories"] == "010"
                assert params["purity"] == "sfw"
                assert params["topRange"] == "1w"
                assert params["ratios"] == "16x9,16x10"
                assert params["colors"] == "0066cc"
                assert params["resolutions"] == "1920x1080,2560x1440"
                assert params["seed"] == "abc123"
                assert params["sorting"] == "views"
                assert params["order"] == "asc"
                assert params["atleast"] == "1920x1080"

    @pytest.mark.asyncio
    async def test_search_http_error(self, wallhaven_service):
        """Test search with HTTP error."""
        with patch.object(wallhaven_service, "_get_session") as mock_get_session:
            with patch.object(wallhaven_service, "_rate_limit"):
                mock_session = AsyncMock()
                mock_response = MagicMock()
                mock_response.status = 500
                mock_response.raise_for_status = MagicMock(
                    side_effect=aiohttp.ClientResponseError(MagicMock(), MagicMock(), status=500)
                )

                # Mock async context manager
                mock_context = MockAsyncContextManager(mock_response)
                mock_session.get = MagicMock(return_value=mock_context)
                mock_get_session.return_value = mock_session

                with pytest.raises(ServiceError, match="Failed to search Wallhaven"):
                    await wallhaven_service.search()

    @pytest.mark.asyncio
    async def test_search_malformed_wallpaper(self, wallhaven_service, sample_wallpaper_response):
        """Test search with malformed wallpaper data."""
        sample_wallpaper_response["data"].append({"invalid": "data"})

        with patch.object(wallhaven_service, "_get_session") as mock_get_session:
            with patch.object(wallhaven_service, "_rate_limit"):
                mock_session = AsyncMock()
                mock_response = MagicMock()
                mock_response.status = 200
                mock_response.raise_for_status = MagicMock()
                mock_response.json = AsyncMock(return_value=sample_wallpaper_response)

                # Mock async context manager
                mock_context = MockAsyncContextManager(mock_response)
                mock_session.get = MagicMock(return_value=mock_context)
                mock_get_session.return_value = mock_session

                # Should skip invalid wallpapers
                wallpapers = await wallhaven_service.search()

                assert len(wallpapers) == 2  # Only valid ones

    @pytest.mark.asyncio
    async def test_search_empty_results(self, wallhaven_service):
        """Test search with no results."""
        with patch.object(wallhaven_service, "_get_session") as mock_get_session:
            with patch.object(wallhaven_service, "_rate_limit"):
                mock_session = AsyncMock()
                mock_response = MagicMock()
                mock_response.status = 200
                mock_response.raise_for_status = MagicMock()
                mock_response.json = AsyncMock(return_value={"data": []})

                # Mock async context manager
                mock_context = MockAsyncContextManager(mock_response)
                mock_session.get = MagicMock(return_value=mock_context)
                mock_get_session.return_value = mock_session

                wallpapers, meta = await wallhaven_service.search()

                assert len(wallpapers) == 0
                assert meta == {}
                assert meta == {}


class TestWallpaperFromDict:
    """Tests for _wallpaper_from_dict method."""

    @pytest.fixture
    def wallhaven_service(self):
        """Create WallhavenService instance."""
        return WallhavenService()

    def test_wallpaper_from_dict_complete(self, wallhaven_service):
        """Test creating Wallpaper from complete dict."""
        data = {
            "id": "abc123",
            "url": "https://wallhaven.cc/w/abc123",
            "path": "https://w.wallhaven.cc/full/abc123.jpg",
            "dimension_x": 1920,
            "dimension_y": 1080,
            "category": "general",
            "purity": "sfw",
            "colors": ["#ff0000", "#00ff00"],
        }

        wallpaper = wallhaven_service._wallpaper_from_dict(data)

        assert wallpaper.id == "abc123"
        assert wallpaper.url == "https://wallhaven.cc/w/abc123"
        assert wallpaper.path == "https://w.wallhaven.cc/full/abc123.jpg"
        assert wallpaper.resolution == Resolution(1920, 1080)
        assert wallpaper.source == WallpaperSource.WALLHAVEN
        assert wallpaper.category == "general"
        assert wallpaper.purity == WallpaperPurity.SFW
        assert wallpaper.colors == ["#ff0000", "#00ff00"]

    def test_wallpaper_from_dict_missing_fields(self, wallhaven_service):
        """Test creating Wallpaper with missing fields."""
        data = {
            "id": "abc123",
            "url": "https://wallhaven.cc/w/abc123",
            "path": "https://w.wallhaven.cc/full/abc123.jpg",
            "dimension_x": 1920,
            "dimension_y": 1080,
            "category": "general",
            "purity": "sfw",
        }

        wallpaper = wallhaven_service._wallpaper_from_dict(data)

        assert wallpaper.id == "abc123"
        assert wallpaper.colors == []

    def test_wallpaper_from_dict_purity_mapping(self, wallhaven_service):
        """Test purity string to enum mapping."""
        for purity_str, expected_enum in [
            ("sfw", WallpaperPurity.SFW),
            ("sketchy", WallpaperPurity.SKETCHY),
            ("nsfw", WallpaperPurity.NSFW),
        ]:
            data = {
                "id": "abc123",
                "url": "https://wallhaven.cc/w/abc123",
                "path": "https://w.wallhaven.cc/full/abc123.jpg",
                "dimension_x": 1920,
                "dimension_y": 1080,
                "category": "general",
                "purity": purity_str,
            }

            wallpaper = wallhaven_service._wallpaper_from_dict(data)

            assert wallpaper.purity == expected_enum


class TestDownload:
    """Tests for download method."""

    @pytest.fixture
    def wallhaven_service(self):
        """Create WallhavenService instance."""
        return WallhavenService()

    @pytest.mark.asyncio
    async def test_download_success(self, wallhaven_service, tmp_path):
        """Test successful download."""
        wallpaper = Wallpaper(
            id="abc123",
            url="https://wallhaven.cc/w/abc123",
            path="https://w.wallhaven.cc/full/abc123.jpg",
            resolution=Resolution(1920, 1080),
            source=WallpaperSource.WALLHAVEN,
            category="general",
            purity=WallpaperPurity.SFW,
        )

        dest = tmp_path / "wallpapers" / "abc123.jpg"

        with patch.object(wallhaven_service, "_get_session") as mock_get_session:
            with patch.object(wallhaven_service, "_rate_limit"):
                mock_session = AsyncMock()

                # Mock response
                mock_response = MagicMock()
                mock_response.status = 200
                mock_response.headers = {"content-length": "100"}
                mock_response.raise_for_status = MagicMock()

                # Mock async content iteration
                chunk_data = b"test data" * 10

                async def iter_chunked(n):
                    """Mock async chunked iteration."""
                    for i in range(0, len(chunk_data), n):
                        yield chunk_data[i : i + n]

                mock_response.content.iter_chunked = iter_chunked

                # Mock async context manager
                mock_context = MockAsyncContextManager(mock_response)
                mock_session.get = MagicMock(return_value=mock_context)
                mock_get_session.return_value = mock_session

                result = await wallhaven_service.download(wallpaper, dest)

                assert result is True
                assert dest.exists()
                assert dest.read_bytes() == chunk_data

    @pytest.mark.asyncio
    async def test_download_with_progress_callback(self, wallhaven_service, tmp_path):
        """Test download with progress callback."""
        wallpaper = Wallpaper(
            id="abc123",
            url="https://wallhaven.cc/w/abc123",
            path="https://w.wallhaven.cc/full/abc123.jpg",
            resolution=Resolution(1920, 1080),
            source=WallpaperSource.WALLHAVEN,
            category="general",
            purity=WallpaperPurity.SFW,
        )

        dest = tmp_path / "wallpapers" / "abc123.jpg"
        progress_updates = []

        def progress_callback(downloaded, total):
            progress_updates.append((downloaded, total))

        with patch.object(wallhaven_service, "_get_session") as mock_get_session:
            with patch.object(wallhaven_service, "_rate_limit"):
                mock_session = AsyncMock()

                # Mock response
                chunk_data = b"testdatatestdatatestdata123"
                mock_response = MagicMock()
                mock_response.status = 200
                mock_response.headers = {"content-length": str(len(chunk_data))}
                mock_response.raise_for_status = MagicMock()

                async def iter_chunked(n):
                    for i in range(0, len(chunk_data), n):
                        yield chunk_data[i : i + n]

                mock_response.content.iter_chunked = iter_chunked

                # Mock async context manager
                mock_context = MockAsyncContextManager(mock_response)
                mock_session.get = MagicMock(return_value=mock_context)
                mock_get_session.return_value = mock_session

                await wallhaven_service.download(wallpaper, dest, progress_callback)

                assert len(progress_updates) > 0
                assert all(downloaded <= len(chunk_data) for downloaded, _ in progress_updates)

    @pytest.mark.asyncio
    async def test_download_http_error(self, wallhaven_service, tmp_path):
        """Test download with HTTP error."""
        wallpaper = Wallpaper(
            id="abc123",
            url="https://wallhaven.cc/w/abc123",
            path="https://w.wallhaven.cc/full/abc123.jpg",
            resolution=Resolution(1920, 1080),
            source=WallpaperSource.WALLHAVEN,
            category="general",
            purity=WallpaperPurity.SFW,
        )

        dest = tmp_path / "wallpapers" / "abc123.jpg"

        with patch.object(wallhaven_service, "_get_session") as mock_get_session:
            with patch.object(wallhaven_service, "_rate_limit"):
                mock_session = AsyncMock()
                mock_response = MagicMock()
                mock_response.status = 404
                mock_response.raise_for_status = MagicMock(
                    side_effect=aiohttp.ClientResponseError(MagicMock(), MagicMock(), status=404)
                )

                # Mock async context manager
                mock_context = MockAsyncContextManager(mock_response)
                mock_session.get = MagicMock(return_value=mock_context)
                mock_get_session.return_value = mock_session

                result = await wallhaven_service.download(wallpaper, dest)

                assert result is False
                assert not dest.exists()


class TestClose:
    """Tests for close method."""

    @pytest.mark.asyncio
    async def test_close_session(self):
        """Test closing session."""
        service = WallhavenService()
        service._session = AsyncMock()
        service._session.closed = False

        await service.close()

        service._session.close.assert_called_once()
        # The close() method doesn't set _session to None, it just closes it
        # The _session remains but is now closed
        assert service._session is not None

    @pytest.mark.asyncio
    async def test_close_already_closed(self):
        """Test closing already closed session."""
        service = WallhavenService()
        service._session = None

        await service.close()

        # Should not raise any error

    @pytest.mark.asyncio
    async def test_close_without_session(self):
        """Test closing when session was never created."""
        service = WallhavenService()
        service._session = None

        await service.close()

        # Should not raise any error

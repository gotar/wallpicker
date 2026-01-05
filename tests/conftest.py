"""Pytest configuration and fixtures."""

import asyncio
import sys
from collections.abc import AsyncGenerator
from pathlib import Path

import pytest
from pytest_mock import MockerFixture

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))


# Pytest-asyncio configuration
def pytest_configure(config):
    """Configure pytest with async support."""
    config.addinivalue_line(
        "markers", "slow: marks tests as slow (deselect with '-m \"not slow\"')"
    )
    config.addinivalue_line("markers", "integration: marks tests as integration tests")


@pytest.fixture
def event_loop() -> asyncio.AbstractEventLoop:
    """Create event loop for async tests."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
async def aiohttp_session(mocker: MockerFixture) -> AsyncGenerator:
    """Create aiohttp session mock for async tests."""
    from aiohttp import ClientResponse, ClientSession

    mocker.patch("aiohttp.ClientSession", autospec=True)

    async def mock_request(*args, **kwargs):
        response = mocker.Mock(spec=ClientResponse)
        response.status = 200
        response.headers = {"content-length": "1000"}
        return response

    mock_instance = mocker.Mock(spec=ClientSession)
    mock_instance.get.return_value = mock_request
    mock_instance.get.side_effect = lambda *args, **kwargs: asyncio.create_task(
        mock_request(*args, **kwargs)
    )

    yield mock_instance


@pytest.fixture
def temp_dir(tmp_path: Path) -> Path:
    """Create temporary directory for tests."""
    test_dir = tmp_path / "wallpicker_test"
    test_dir.mkdir(parents=True, exist_ok=True)
    yield test_dir


@pytest.fixture
def service_config(temp_dir: Path) -> object:
    """ConfigService fixture for tests."""
    from core.container import ServiceConfig

    return ServiceConfig(
        local_wallpapers_dir=temp_dir,
        cache_dir=temp_dir / "cache",
        config_file=temp_dir / "config.json",
    )


@pytest.fixture
def config_service(temp_dir: Path) -> object:
    """ConfigService fixture for tests."""
    from services.config_service import ConfigService

    config_file = temp_dir / "config.json"
    return ConfigService(config_file=config_file)

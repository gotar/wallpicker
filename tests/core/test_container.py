"""Tests for DI container."""

import pytest

from core.container import ServiceConfig, ServiceContainer


def test_container_init():
    """Test container initialization."""
    config = ServiceConfig()
    container = ServiceContainer(config)
    assert container._config == config
    assert len(container._services) == 0


def test_container_register_and_get():
    """Test service registration and retrieval."""

    class TestService:
        def __init__(self):
            self.value = 42

    config = ServiceConfig()
    container = ServiceContainer(config)
    container.register(TestService, TestService)

    service = container.get(TestService)
    assert service.value == 42

    # Should return same instance (singleton)
    service2 = container.get(TestService)
    assert service is service2


def test_container_register_instance():
    """Test registering pre-created instance."""

    class TestService:
        def __init__(self, value: int):
            self.value = value

    config = ServiceConfig()
    container = ServiceContainer(config)
    instance = TestService(99)
    container.register_instance(TestService, instance)

    service = container.get(TestService)
    assert service.value == 99

    # Should return same instance
    service2 = container.get(TestService)
    assert service is service2


def test_container_get_missing_service():
    """Test getting unregistered service."""
    config = ServiceConfig()
    container = ServiceContainer(config)

    class TestService:
        pass

    with pytest.raises(KeyError, match="No factory registered"):
        container.get(TestService)


def test_container_reset():
    """Test container reset."""

    class TestService:
        def __init__(self):
            self.value = 1

    config = ServiceConfig()
    container = ServiceContainer(config)
    container.register(TestService, TestService)

    # Get service (creates instance)
    service = container.get(TestService)
    assert service.value == 1

    # Reset
    container.reset()
    assert len(container._services) == 0

    # Get service again (creates new instance)
    service2 = container.get(TestService)
    assert service2 is not service


def test_service_config_defaults():
    """Test ServiceConfig defaults."""
    config = ServiceConfig()
    assert config.wallhaven_api_key is None
    assert config.local_wallpapers_dir is None
    assert config.cache_dir is None
    assert config.config_file is None


def test_service_config_with_values():
    """Test ServiceConfig with values."""
    from pathlib import Path

    config = ServiceConfig(
        wallhaven_api_key="test-key",
        local_wallpapers_dir=Path("/test/path"),
        cache_dir=Path("/test/cache"),
        config_file=Path("/test/config.json"),
    )

    assert config.wallhaven_api_key == "test-key"
    assert config.local_wallpapers_dir == Path("/test/path")
    assert config.cache_dir == Path("/test/cache")
    assert config.config_file == Path("/test/config.json")


def test_global_container():
    """Test global container instance."""
    from core.container import container as global_container

    # Initially None
    assert global_container is None

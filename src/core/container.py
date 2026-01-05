"""Dependency injection container for service management."""

from collections.abc import Callable
from dataclasses import dataclass
from logging import getLogger
from pathlib import Path
from typing import Any, TypeVar

T = TypeVar("T")


@dataclass
class ServiceConfig:
    """Configuration for service instantiation."""

    wallhaven_api_key: str | None = None
    local_wallpapers_dir: Path | None = None
    cache_dir: Path | None = None
    config_file: Path | None = None


class ServiceContainer:
    """Dependency injection container for managing service lifecycles."""

    def __init__(self, config: ServiceConfig) -> None:
        """Initialize container with configuration."""
        self._config = config
        self._services: dict[type, object] = {}
        self._factories: dict[type, Callable[[], Any]] = {}
        self._logger = getLogger(__name__)

    def register(self, service_class: type[T], factory: Callable[[], T]) -> None:
        """Register a service factory for lazy instantiation."""
        self._factories[service_class] = factory
        self._logger.debug(f"Registered factory for {service_class.__name__}")

    def register_instance(self, service_class: type[T], instance: T) -> None:
        """Register a pre-instantiated service instance."""
        self._services[service_class] = instance
        self._logger.debug(f"Registered instance of {service_class.__name__}")

    def get(self, service_class: type[T]) -> T:
        """Get or create service instance."""
        if service_class not in self._services:
            self._create_service(service_class)
        return self._services[service_class]

    def _create_service(self, service_class: type[T]) -> T:
        """Create service instance using registered factory."""
        if service_class not in self._factories:
            raise KeyError(f"No factory registered for {service_class.__name__}")

        factory = self._factories[service_class]
        instance = factory()
        self._services[service_class] = instance
        self._logger.debug(f"Created instance of {service_class.__name__}")
        return instance

    def reset(self) -> None:
        """Clear all registered services (for testing)."""
        self._services.clear()
        self._logger.debug("Container reset")


# Global container instance (for GTK app)
container: ServiceContainer | None = None

"""Dependency injection container for service management."""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, Type, TypeVar, Optional, Callable, Any
from logging import getLogger

T = TypeVar("T")


@dataclass
class ServiceConfig:
    """Configuration for service instantiation."""

    wallhaven_api_key: Optional[str] = None
    local_wallpapers_dir: Optional[Path] = None
    cache_dir: Optional[Path] = None
    config_file: Optional[Path] = None


class ServiceContainer:
    """Dependency injection container for managing service lifecycles."""

    def __init__(self, config: ServiceConfig) -> None:
        """Initialize container with configuration."""
        self._config = config
        self._services: Dict[Type, object] = {}
        self._factories: Dict[Type, Callable[[], Any]] = {}
        self._logger = getLogger(__name__)

    def register(self, service_class: Type[T], factory: Callable[[], T]) -> None:
        """Register a service factory for lazy instantiation."""
        self._factories[service_class] = factory
        self._logger.debug(f"Registered factory for {service_class.__name__}")

    def register_instance(self, service_class: Type[T], instance: T) -> None:
        """Register a pre-instantiated service instance."""
        self._services[service_class] = instance
        self._logger.debug(f"Registered instance of {service_class.__name__}")

    def get(self, service_class: Type[T]) -> T:
        """Get or create service instance."""
        if service_class not in self._services:
            self._create_service(service_class)
        return self._services[service_class]

    def _create_service(self, service_class: Type[T]) -> T:
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
container: Optional[ServiceContainer] = None

# 03. Service Layer

meta:
  id: wallpaper-refactor-03
  feature: wallpaper-refactor
  priority: P1
  depends_on: [02]
  tags: [services, dependency-injection]

objective:
- Refactor service layer with dependency injection, removing hard-coded service instantiation and making services testable.

deliverables:
- src/core/container.py: DI container for service instantiation
- src/services/base.py: Base service class with common functionality
- Refactored services (wallhaven, local, favorites, config, thumbnail_cache, wallpaper_setter)
- Update main_window.py to use DI container
- Service interfaces for mocking

steps:
1. Create src/core/container.py (DI container):
   ```python
   from typing import Dict, Type, TypeVar, Optional
   from dataclasses import dataclass

   T = TypeVar('T')

   @dataclass
   class ServiceConfig:
       """Configuration for service instantiation"""
       wallhaven_api_key: Optional[str] = None
       local_wallpapers_dir: Optional[str] = None
       cache_dir: Optional[str] = None
       config_file: Optional[str] = None

   class ServiceContainer:
       """Dependency injection container"""

       def __init__(self, config: ServiceConfig):
           self._config = config
           self._services: Dict[Type, object] = {}

       def register(self, service_class: Type[T], instance: T) -> None:
           self._services[service_class] = instance

       def get(self, service_class: Type[T]) -> T:
           if service_class not in self._services:
               self._create_service(service_class)
           return self._services[service_class]

       def _create_service(self, service_class: Type[T]) -> T:
           """Lazy service creation with dependency resolution"""
           # Implementation handles service instantiation
           ...

   # Global container instance (for GTK app)
   container: Optional[ServiceContainer] = None
   ```

2. Create src/services/base.py:
   ```python
   from abc import ABC, abstractmethod
   from typing import Optional
   from logging import getLogger

   class BaseService(ABC):
       """Base class for all services"""

       def __init__(self):
           self._logger = getLogger(self.__class__.__name__)

       def log_debug(self, message: str) -> None:
           self._logger.debug(message)

       def log_error(self, message: str, exc_info: bool = False) -> None:
           self._logger.error(message, exc_info=exc_info)
   ```

3. Define service interfaces (src/services/interfaces.py):
   ```python
   from abc import ABC, abstractmethod
   from typing import List, Optional
   from pathlib import Path
   from domain.wallpaper import Wallpaper, WallpaperSource

   class IWallpaperService(ABC):
       @abstractmethod
       def search(self, query: str, **kwargs) -> List[Wallpaper]:
           pass

       @abstractmethod
       def download(self, wallpaper: Wallpaper, dest: Path) -> bool:
           pass

   class IFavoritesService(ABC):
       @abstractmethod
       def add_favorite(self, wallpaper: Wallpaper) -> None:
           pass

       @abstractmethod
       def remove_favorite(self, wallpaper_id: str) -> None:
           pass

       @abstractmethod
       def is_favorite(self, wallpaper_id: str) -> bool:
           pass

       @abstractmethod
       def get_favorites(self) -> List[Wallpaper]:
           pass
   ```

4. Refactor existing services:
   - Add type hints to all service methods
   - Make services inherit from BaseService
   - Implement interfaces where appropriate
   - Update constructors to accept dependencies (not create them)
   - Replace print statements with logging

5. Update main_window.py to use DI container:
   ```python
   def do_activate(self):
       if not self.window:
           # Create container with config
           config = ServiceConfig.from_file(...)
           container = ServiceContainer(config)

           # Initialize services via container
           self.wallhaven_service = container.get(WallhavenService)
           self.local_service = container.get(LocalWallpaperService)
           # ... other services

           self.window = WallPickerWindow(self)
       self.window.present()
   ```

6. Update launcher.py and main.py to initialize container

tests:
- Unit: Test ServiceContainer registration and retrieval
- Unit: Test lazy service creation
- Integration: Test all services can be instantiated via container
- Integration: Test services work with domain models
- Mock: Test services using interfaces

acceptance_criteria:
- DI container implemented and working
- All services use BaseService for logging
- Service interfaces defined for key services
- main_window.py uses container for all services
- No hard-coded service instantiation in main_window.py
- Services accept dependencies via constructor
- All print statements replaced with logging
- Type hints on all service methods

validation:
- Commands to verify:
  ```bash
  python -c "from wallpicker.core.container import ServiceContainer; print('OK')"
  python -m pytest tests/services/ -v
  ```
- Run main_window.py and verify all services load correctly

notes:
- Lazy loading: Services created only when first needed
- Singleton pattern: Each service type instantiated once
- Interfaces enable easy mocking for tests
- Container manages service lifecycle
- Logging configured in BaseService (actual config in later task)

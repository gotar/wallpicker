# 02. Domain Models

meta:
  id: wallpaper-refactor-02
  feature: wallpaper-refactor
  priority: P1
  depends_on: [01]
  tags: [domain-model, models]

objective:
- Create rich domain models that encapsulate business logic, replacing basic data classes with value objects and domain entities.

deliverables:
- src/domain/wallpaper.py: Wallpaper entity with behavior
- src/domain/value_objects.py: Resolution, Color, WallpaperId value objects
- src/domain/config.py: Config entity with validation
- src/domain/favorite.py: Favorite entity
- Update existing services to use new domain models

steps:
1. Create src/domain/ directory with __init__.py

2. Implement Wallpaper entity (src/domain/wallpaper.py):
   ```python
   from dataclasses import dataclass
   from typing import List
   from enum import Enum

   class WallpaperSource(Enum):
       WALLHAVEN = "wallhaven"
       LOCAL = "local"
       FAVORITE = "favorite"

   class WallpaperPurity(Enum):
       SFW = "sfw"
       SKETCHY = "sketchy"
       NSFW = "nsfw"

   @dataclass
   class Resolution:
       width: int
       height: int

       @property
       def aspect_ratio(self) -> float:
           return self.width / self.height

       def __str__(self) -> str:
           return f"{self.width}x{self.height}"

   @dataclass
   class Wallpaper:
       id: str
       url: str
       path: str  # Local file path or download URL
       resolution: Resolution
       source: WallpaperSource
       category: str
       purity: WallpaperPurity
       colors: List[str]
       file_size: int
       thumbs_large: str
       thumbs_small: str

       # Domain behavior
       @property
       def is_landscape(self) -> bool:
           return self.resolution.aspect_ratio >= 1

       @property
       def is_portrait(self) -> bool:
           return self.resolution.aspect_ratio < 1

       @property
       def size_mb(self) -> float:
           return self.file_size / (1024 * 1024)

       def matches_query(self, query: str) -> bool:
           query_lower = query.lower()
           return (
               query_lower in self.id.lower()
               or query_lower in self.category.lower()
               or query_lower in self.url.lower()
           )

       def to_dict(self) -> dict:
           # For JSON serialization
           ...
   ```

3. Implement Config entity (src/domain/config.py):
   ```python
   from dataclasses import dataclass
   from pathlib import Path
   from typing import Optional

   @dataclass
   class Config:
       local_wallpapers_dir: Optional[Path] = None
       wallhaven_api_key: Optional[str] = None

       def validate(self) -> None:
           if self.local_wallpapers_dir:
               if not self.local_wallpapers_dir.exists():
                   raise ConfigError(f"Directory does not exist: {self.local_wallpapers_dir}")

       @property
       def pictures_dir(self) -> Path:
           return self.local_wallpapers_dir or Path.home() / "Pictures"
   ```

4. Implement Favorite entity (src/domain/favorite.py):
   ```python
   from dataclasses import dataclass
   from datetime import datetime

   @dataclass
   class Favorite:
       wallpaper: Wallpaper
       added_at: datetime

       @property
       def days_since_added(self) -> int:
           return (datetime.now() - self.added_at).days
   ```

5. Update services to use domain models:
   - wallhaven_service.py: Parse API responses to create Wallpaper entities
   - local_service.py: Convert LocalWallpaper to Wallpaper entity
   - favorites_service.py: Use Favorite entity

6. Create custom exception base (domain/exceptions.py):
   ```python
   class WallpickerError(Exception):
       """Base exception for wallpicker domain errors"""
       pass

   class ConfigError(WallpickerError):
       """Configuration-related errors"""
       pass

   class WallpaperError(WallpickerError):
       """Wallpaper-related errors"""
       pass

   class ServiceError(WallpickerError):
       """Service layer errors"""
       pass
   ```

tests:
- Unit: Test Resolution aspect_ratio calculations
- Unit: Test Wallpaper.is_landscape / is_portrait properties
- Unit: Test Wallpaper.matches_query logic
- Unit: Test Config validation
- Integration: Test wallhaven_service parsing to domain models
- Integration: Test local_service conversion to domain models

acceptance_criteria:
- All domain models created with proper type hints
- Wallpaper entity encapsulates business logic (not just data)
- Resolution, Color, WallpaperId as value objects (immutable)
- Config entity with validation logic
- Custom exception hierarchy created
- All services updated to use domain models
- No dict-based wallpaper objects remain (except JSON serialization)
- Unit tests for domain model behavior

validation:
- Commands to verify:
  ```bash
  python -c "from wallpicker.domain.wallpaper import Wallpaper, WallpaperSource; print('OK')"
  python -m pytest tests/domain/ -v
  ```
- Run tests for services to ensure domain model integration works

notes:
- Domain models should be independent of infrastructure (GTK, files)
- Follow DDD: Entities have identity, Value Objects don't
- Business logic goes in domain models, not services (Rich Domain Model)
- Config entity validates its own state (encapsulation)

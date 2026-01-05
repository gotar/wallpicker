# 07. Testing Refactor

meta:
  id: wallpaper-refactor-07
  feature: wallpaper-refactor
  priority: P2
  depends_on: [01, 02, 03]
  tags: [testing, pytest]

objective:
- Migrate from unittest to pytest with fixtures, improving test coverage and maintainability.

deliverables:
- pytest.ini configuration
- tests/conftest.py with fixtures
- Refactored test files to use pytest
- New tests for domain models and ViewModels
- Test coverage report (pytest-cov)

steps:
1. Add pytest dependencies to pyproject.toml:
   ```toml
   [project.optional-dependencies]
   dev = [
       "pytest>=7.4.0",
       "pytest-asyncio>=0.21.0",
       "pytest-mock>=3.11.0",
       "pytest-cov>=4.1.0",
   ]
   ```

2. Create pytest.ini:
   ```ini
   [pytest]
   testpaths = tests
   python_files = test_*.py
   python_classes = Test*
   python_functions = test_*
   addopts =
       --verbose
       --tb=short
       --strict-markers
       --cov=src
       --cov-report=html
       --cov-report=term-missing
   markers =
       slow: marks tests as slow (deselect with '-m "not slow"')
       network: marks tests that require network access
       ui: marks UI-related tests
   ```

3. Create tests/conftest.py with fixtures:
   ```python
   import pytest
   import asyncio
   from pathlib import Path
   from unittest.mock import MagicMock
   from services.wallhaven_service import WallhavenService
   from services.local_service import LocalWallpaperService
   from services.favorites_service import FavoritesService
   from domain.wallpaper import Wallpaper, WallpaperSource, WallpaperPurity

   # Fixtures for test data
   @pytest.fixture
   def sample_wallpaper():
       return Wallpaper(
           id="test123",
           url="https://wallhaven.cc/w/test123",
           path="https://w.wallhaven.cc/full/test123.jpg",
           thumbs_large="https://th.wallhaven.cc/small/test123.jpg",
           thumbs_small="https://th.wallhaven.cc/small/test123.jpg",
           resolution="1920x1080",
           source=WallpaperSource.WALLHAVEN,
           category="general",
           purity=WallpaperPurity.SFW,
           colors=["#000000"],
           file_size=1024*1024,
       )

   @pytest.fixture
   def temp_dir(tmp_path):
       """Temporary directory for file operations"""
       test_dir = tmp_path / "wallpaper_test"
       test_dir.mkdir()
       return test_dir

   # Async fixtures
   @pytest.fixture(scope="session")
   def event_loop():
       """Create event loop for async tests"""
       loop = asyncio.get_event_loop_policy().new_event_loop()
       yield loop
       loop.close()

   # Service fixtures
   @pytest.fixture
   def wallhaven_service():
       """Mock wallhaven service"""
       service = WallhavenService(api_key=None)
       yield service

   @pytest.fixture
   def local_service(temp_dir):
       """Local service with temp directory"""
       service = LocalWallpaperService(pictures_dir=temp_dir)
       yield service

   @pytest.fixture
   def mock_aiohttp():
       """Mock aiohttp for network tests"""
       with pytest.mock.patch("aiohttp.ClientSession") as mock:
           yield mock

   # Config fixtures
   @pytest.fixture
   def mock_config(tmp_path):
       """Mock config file"""
       config_dir = tmp_path / ".config" / "wallpicker"
       config_dir.mkdir(parents=True)
       config_file = config_dir / "config.json"
       config_file.write_text('{"test": true}')

       with pytest.mock.patch("domain.config.Path.home", return_value=tmp_path):
           yield config_file
   ```

4. Migrate existing tests to pytest:
   ```python
   # tests/services/test_wallhaven_service.py
   import pytest
   from unittest.mock import AsyncMock, MagicMock
   from services.wallhaven_service import WallhavenService

   class TestWallhavenService:
       @pytest.fixture
       def service(self):
           return WallhavenService(api_key="test_key")

       @pytest.mark.asyncio
       async def test_search_success(self, service, mock_aiohttp):
           """Test successful search"""
           mock_response = AsyncMock()
           mock_response.status = 200
           mock_response.json = AsyncMock(return_value={
               "data": [...],
               "meta": {"total": 1}
           })
           mock_response.raise_for_status = MagicMock()

           mock_aiohttp.return_value.__aenter__.return_value = mock_response

           result = await service.search(q="test")
           assert "data" in result
           assert result["data"] is not None

       @pytest.mark.asyncio
       async def test_search_network_error(self, service, mock_aiohttp):
           """Test network error handling"""
           mock_aiohttp.side_effect = aiohttp.ClientError("Network error")

           with pytest.raises(NetworkError):
               await service.search(q="test")

       @pytest.mark.asyncio
       async def test_rate_limiting(self, service):
           """Test rate limiting"""
           import time
           start = time.time()

           for _ in range(3):
               # This should take at least 2 * (60/45) seconds
               await service.search(q="test")

           elapsed = time.time() - start
           assert elapsed >= 2.5  # Approximate rate limit

   # tests/domain/test_wallpaper.py
   class TestWallpaper:
       def test_is_landscape(self, sample_wallpaper):
           assert sample_wallpaper.is_landscape is True

       def test_matches_query(self, sample_wallpaper):
           assert sample_wallpaper.matches_query("test") is True
           assert sample_wallpaper.matches_query("nature") is False

       def test_size_mb(self, sample_wallpaper):
           assert sample_wallpaper.size_mb == 1.0
   ```

5. Create tests for ViewModels:
   ```python
   # tests/ui/test_wallhaven_viewmodel.py
   import pytest
   from unittest.mock import AsyncMock
   from ui.view_models.wallhaven_view_model import WallhavenViewModel

   class TestWallhavenViewModel:
       @pytest.fixture
       def viewmodel(self, wallhaven_service):
           return WallhavenViewModel(wallhaven_service)

       @pytest.mark.asyncio
       async def test_search_sets_busy(self, viewmodel):
           """Test that search sets is_busy property"""
           viewmodel._service.search = AsyncMock(return_value={
               "data": [], "meta": {"total": 0}
           })

           assert viewmodel.is_busy is False

           search_task = asyncio.create_task(viewmodel.search("test"))
           await asyncio.sleep(0.01)  # Let it start

           assert viewmodel.is_busy is True
           await search_task
           assert viewmodel.is_busy is False

       @pytest.mark.asyncio
       async def test_search_error_handling(self, viewmodel):
           """Test error handling in search"""
           viewmodel._service.search = AsyncMock(
               side_effect=NetworkError("Test error")
           )

           await viewmodel.search("test")

           assert viewmodel.error_message == "Network error: Test error"
           assert viewmodel.is_busy is False
   ```

6. Create tests for DI container:
   ```python
   # tests/core/test_container.py
   class TestServiceContainer:
       def test_service_registration(self):
           """Test service registration"""
           container = ServiceContainer(ServiceConfig())
           mock_service = MagicMock()

           container.register(MockService, mock_service)
           retrieved = container.get(MockService)

           assert retrieved is mock_service

       def test_lazy_service_creation(self):
           """Test services are created lazily"""
           container = ServiceContainer(ServiceConfig())

           assert MockService not in container._services
           container.get(MockService)
           assert MockService in container._services
   ```

7. Add pytest-asyncio configuration for async tests:
   ```python
   # In conftest.py
   pytest_plugins = ("pytest_asyncio",)
   ```

tests:
- Unit: All service tests
- Unit: Domain model tests
- Unit: ViewModel tests
- Integration: DI container tests
- Coverage: Ensure >80% coverage

acceptance_criteria:
- All tests migrated to pytest
- fixtures in conftest.py for common test data
- Async tests use pytest-asyncio
- Tests for all domain models
- Tests for ViewModels
- Tests for DI container
- pytest-cov generates coverage report
- Coverage >80%
- No unittest imports remain
- Tests run with: pytest

validation:
- Commands to verify:
  ```bash
  pytest --version
  pytest -v
  pytest --cov=src --cov-report=html
  grep -r "import unittest" tests/  # Should return nothing
  grep -r "unittest.TestCase" tests/  # Should return nothing
  ```
- Check coverage report: open htmlcov/index.html
- Run: pytest -m "not slow" for quick test run

notes:
- Use fixtures for common test data (sample_wallpaper, temp_dir)
- pytest-asyncio for async tests
- pytest-mock for mocking (better than unittest.mock)
- pytest-cov for coverage reports
- Mark slow tests with @pytest.mark.slow
- Keep run_tests.py for backward compatibility? (deprecated)
- Test naming: test_<method>_<scenario>
- Use descriptive assertion messages

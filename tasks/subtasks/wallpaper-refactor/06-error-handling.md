# 06. Error Handling

meta:
  id: wallpaper-refactor-06
  feature: wallpaper-refactor
  priority: P2
  depends_on: [02]
  tags: [error-handling, exceptions]

objective:
- Implement custom exception hierarchy and consistent error handling throughout the application, replacing generic exception catches.

deliverables:
- src/domain/exceptions.py: Complete exception hierarchy
- Error handling middleware in services
- User-friendly error messages in UI
- Error recovery strategies where applicable

steps:
1. Complete exception hierarchy (src/domain/exceptions.py):
   ```python
   class WallpickerError(Exception):
       """Base exception for all wallpicker errors"""
       def __init__(self, message: str, details: Optional[dict] = None):
           super().__init__(message)
           self.message = message
           self.details = details or {}

   # Domain errors
   class ConfigError(WallpickerError):
       """Configuration-related errors"""
       pass

   class WallpaperError(WallpickerError):
       """Wallpaper entity errors"""
       pass

   class FileNotFoundError(WallpaperError):
       """File not found errors"""
       pass

   class ValidationError(WallpickerError):
       """Input validation errors"""
       pass

   # Service errors
   class ServiceError(WallpickerError):
       """Base service error"""
       pass

   class NetworkError(ServiceError):
       """Network-related errors"""
       pass

   class APIError(ServiceError):
       """API-related errors (Wallhaven, etc.)"""
       pass

   class CacheError(ServiceError):
       """Cache-related errors"""
       pass

   class StorageError(ServiceError):
       """Storage/file system errors"""
       pass

   # UI errors
   class UIError(WallpickerError):
       """UI-related errors"""
       pass

   class UserError(UIError):
       """User-triggered errors (cancel, invalid input)"""
       pass
   ```

2. Update services to raise specific exceptions:
   ```python
   # In wallhaven_service.py
   class WallhavenService(BaseService):
       async def search(self, q: str, **kwargs) -> dict:
           try:
               result = await self._make_request(...)
               return result
           except aiohttp.ClientConnectionError as e:
               raise NetworkError(
                   "Failed to connect to Wallhaven",
                   details={"query": q, "original_error": str(e)}
               )
           except aiohttp.ClientResponseError as e:
               if e.status == 401:
                   raise APIError(
                       "Invalid API key",
                       details={"status_code": e.status}
                   )
               elif e.status == 429:
                   raise APIError(
                       "Rate limit exceeded",
                       details={"status_code": e.status}
                   )
               else:
                   raise APIError(
                       f"API error: {e.status}",
                       details={"status_code": e.status}
                   )

       async def download(self, url: str, dest: Path) -> bool:
           try:
               await self._download_to_file(url, dest)
               return True
           except PermissionError:
               raise StorageError(
                   "Permission denied",
                   details={"path": str(dest)}
               )
           except OSError as e:
               raise StorageError(
                   f"Failed to save file: {e}",
                   details={"path": str(dest)}
               )
   ```

3. Add error handling in services:
   ```python
   class BaseService(ABC):
       def handle_error(self, error: Exception, context: str = "") -> None:
           """Centralized error handling"""
           if isinstance(error, WallpickerError):
               self.log_error(f"[{context}] {error.message}")
               # UI-friendly message already in error.message
           else:
               self.log_error(f"[{context}] Unexpected error: {error}", exc_info=True)
               # Wrap in generic error
               raise ServiceError(
                   "An unexpected error occurred",
                   details={"original_error": str(error)}
               )
   ```

4. Update ViewModels to handle errors:
   ```python
   class WallhavenViewModel(BaseViewModel):
       async def search(self, query: str, **filters) -> None:
           self.is_busy = True
           self.error_message = None

           try:
               result = await self._service.search(query, **filters)
               # Process result
               ...

           except NetworkError as e:
               self.error_message = f"Network error: {e.message}"

           except APIError as e:
               self.error_message = f"API error: {e.message}"

           except ServiceError as e:
               self.error_message = f"Service error: {e.message}"

           except Exception as e:
               self.log_error(f"Unexpected error: {e}", exc_info=True)
               self.error_message = "An unexpected error occurred"

           finally:
               self.is_busy = False
   ```

5. Update UI to display errors:
   ```python
   # In view classes, observe error_message property
   def _bind_viewmodel(self, viewmodel):
       viewmodel.connect("notify::error-message", self._on_error_changed)

   def _on_error_changed(self, vm, pspec):
       error_msg = vm.error_message
       if error_msg:
           self._show_error_toast(error_msg)
           # Optionally log detailed error
           self.log_debug(f"User error: {error_msg}")
   ```

6. Add error recovery strategies:
   ```python
   class WallpaperService(BaseService):
       async def download_with_retry(self, url: str, dest: Path, retries: int = 3) -> bool:
           """Download with automatic retry"""
           last_error = None

           for attempt in range(retries):
               try:
                   return await self.download(url, dest)
               except NetworkError as e:
                   last_error = e
                   if attempt < retries - 1:
                       delay = 2 ** attempt  # Exponential backoff
                       self.log_debug(f"Retry {attempt + 1}/{retries} in {delay}s")
                       await asyncio.sleep(delay)

           raise NetworkError(
               f"Failed after {retries} attempts: {last_error.message}",
               details={"url": url, "retries": retries}
           )
   ```

tests:
- Unit: Test custom exceptions are raised correctly
- Unit: Test error message formatting
- Integration: Test error handling in services
- UI: Test error messages display correctly
- Unit: Test retry logic

acceptance_criteria:
- Custom exception hierarchy implemented
- Services raise specific exceptions (not generic Exception)
- No bare except blocks in services
- User-friendly error messages in UI
- Error recovery strategies implemented (retry, fallback)
- All exceptions logged with context
- Error handling follows consistent pattern

validation:
- Commands to verify:
  ```bash
  grep -r "except Exception:" src/services/  # Should be minimal/none
  grep -r "raise.*Exception" src/ | grep -v "WallpickerError"  # Should return nothing
  python -m pytest tests/ -k error -v
  ```
- Test error scenarios: network failure, invalid API key, file permission error

notes:
- Custom exceptions carry user-friendly messages
- Detailed info in exception.details for logging
- UI shows user-friendly message, logs details
- Centralized error handling in BaseService
- Retry strategies for transient failures (network)
- Don't catch and suppress errors (always re-raise or handle)

# 05. Async Refactor

meta:
  id: wallpaper-refactor-05
  feature: wallpaper-refactor
  priority: P2
  depends_on: [03]
  tags: [async, performance]

objective:
- Standardize async/await patterns throughout the application, replacing threading with consistent async operations.

deliverables:
- Refactored wallhaven_service.py to use aiohttp (async)
- Refactored thumbnail_cache.py with async operations
- Async wrapper for file operations
- Updated ViewModels to use async/await
- Removed all threading.Thread usage

steps:
1. Refactor wallhaven_service.py to be fully async:
   ```python
   import aiohttp
   import asyncio

   class WallhavenService(BaseService):
       BASE_URL = "https://wallhaven.cc/api/v1"
       RATE_LIMIT = 45  # requests per minute

       def __init__(self, api_key: Optional[str] = None):
           super().__init__()
           self.api_key = api_key
           self._session: Optional[aiohttp.ClientSession] = None
           self._last_request_time = 0

       async def _get_session(self) -> aiohttp.ClientSession:
           if self._session is None or self._session.closed:
               self._session = aiohttp.ClientSession()
           return self._session

       async def _rate_limit(self):
           """Enforce rate limiting"""
           current_time = asyncio.get_event_loop().time()
           time_since_last = current_time - self._last_request_time
           if time_since_last < (60.0 / self.RATE_LIMIT):
               await asyncio.sleep((60.0 / self.RATE_LIMIT) - time_since_last)
           self._last_request_time = asyncio.get_event_loop().time()

       async def search(self, q: str = "", **kwargs) -> dict:
           """Async search wallpapers"""
           await self._rate_limit()

           session = await self._get_session()
           params = {"q": q, **kwargs}

           try:
               async with session.get(
                   f"{self.BASE_URL}/search",
                   headers=self._get_headers(),
                   params=params
               ) as response:
                   response.raise_for_status()
                   return await response.json()
           except aiohttp.ClientError as e:
               self.log_error(f"Search error: {e}")
                   return {"error": str(e), "data": []}

       async def download(self, url: str, dest: Path) -> bool:
           """Async download"""
           session = await self._get_session()

           try:
               async with session.get(url) as response:
                   response.raise_for_status()
                   dest.parent.mkdir(parents=True, exist_ok=True)

                   with open(dest, "wb") as f:
                       async for chunk in response.content.iter_chunked(8192):
                           f.write(chunk)
               return True
           except Exception as e:
               self.log_error(f"Download error: {e}")
               return False

       async def close(self):
           """Close session"""
           if self._session:
               await self._session.close()
   ```

2. Create async file operations wrapper (src/core/async_file_ops.py):
   ```python
   import aiofiles
   from pathlib import Path

   async def read_file(path: Path) -> str:
       async with aiofiles.open(path, mode='r') as f:
           return await f.read()

   async def write_file(path: Path, content: str):
       async with aiofiles.open(path, mode='w') as f:
           await f.write(content)

   async def delete_file(path: Path):
       # send2trash is sync, run in executor
       loop = asyncio.get_event_loop()
       await loop.run_in_executor(None, send2trash, str(path))
   ```

3. Refactor thumbnail_cache.py with async operations:
   ```python
   class ThumbnailCache(BaseService):
       async def load_thumbnail_async(self, url: str, image_widget) -> None:
           """Load thumbnail asynchronously"""
           cache_path = self._get_cache_path(url)

           if await self._is_cached(cache_path):
               await self._load_from_cache(cache_path, image_widget)
           else:
               await self._download_and_cache(url, cache_path, image_widget)

       async def _download_and_cache(self, url, cache_path, image_widget):
           """Download and cache thumbnail"""
           async with aiohttp.ClientSession() as session:
               async with session.get(url) as response:
                   response.raise_for_status()
                   data = await response.read()

               cache_path.parent.mkdir(parents=True, exist_ok=True)
               async with aiofiles.open(cache_path, "wb") as f:
                   await f.write(data)

           await self._load_from_cache(cache_path, image_widget)
   ```

4. Update ViewModels to use async methods:
   ```python
   class WallhavenViewModel(BaseViewModel):
       async def search(self, query: str, **filters) -> None:
           self.is_busy = True
           try:
               result = await self._service.search(query, **filters)
               wallpapers = self._service.parse_wallpapers(result.get("data", []))
               self._wallpapers.remove_all()
               for wp in wallpapers:
                   self._wallpapers.append(wp)
           except Exception as e:
               self.error_message = str(e)
           finally:
               self.is_busy = False

       async def download_wallpaper(self, wallpaper: Wallpaper, dest: Path) -> None:
           success = await self._service.download(wallpaper.path, dest)
           # Update UI state
   ```

5. Update UI to run async methods:
   ```python
   # In view classes, use GLib asyncio integration
   from gi.repository import GLib
   import asyncio

   async def _async_wrapper(coro):
       try:
           await coro
       except Exception as e:
           self.log_error(f"Async error: {e}")

   def _on_search_clicked(self, button):
       # Run async search
       asyncio.run_coroutine_threadsafe(
           self.viewmodel.search(self.query),
           asyncio.get_event_loop()
       )
   ```

6. Remove all threading.Thread usage:
   - Replace threading.Thread with asyncio
   - Remove threading imports
   - Remove GLib.idle_add (use asyncio event loop)

tests:
- Unit: Test async service methods
- Integration: Test async search and download
- Unit: Test async file operations
- UI: Test async operations don't block UI

acceptance_criteria:
- All network I/O uses async/await (aiohttp)
- All file I/O uses async (aiofiles) where possible
- No threading.Thread usage remaining
- wallhaven_service is fully async
- thumbnail_cache is fully async
- ViewModels use async methods
- UI doesn't freeze during async operations
- Tests cover async operations

validation:
- Commands to verify:
  ```bash
  grep -r "threading.Thread" src/  # Should return nothing
  grep -r "GLib.idle_add" src/ui/  # Should return nothing
  python -m pytest tests/ -v -k async
  ```
- Run application and verify UI is responsive during searches

notes:
- aiohttp for async HTTP requests
- aiofiles for async file I/O
- send2trash is sync, use run_in_executor
- GTK event loop integration: asyncio.run_coroutine_threadsafe()
- Remove GLib.idle_add, use asyncio event loop
- Services need close() method for cleanup

# 09. Structured Logging

meta:
  id: wallpaper-refactor-09
  feature: wallpaper-refactor
  priority: P2
  depends_on: [01, 02, 03]
  tags: [logging, observability]

objective:
- Replace print statements with structured logging, providing better debugging, monitoring, and error tracking.

deliverables:
- Logging configuration in core
- Structured logging in all services
- Log levels appropriate for severity
- Log files for persistent logging

steps:
1. Add logging dependencies to pyproject.toml:
   ```toml
   [project.dependencies]
   structlog = ">=23.0.0"
   colorlog = ">=6.7.0"  # For colored console output
   ```

2. Create logging configuration (src/core/logging_config.py):
   ```python
   import logging
   import structlog
   import sys
   from pathlib import Path

   def configure_logging(
       level: int = logging.INFO,
       log_file: Optional[Path] = None,
       json_output: bool = False,
   ) -> None:
       """Configure structured logging"""

       # Standard library logging configuration
       logging.basicConfig(
           format="%(message)s",
           level=level,
       )

       # Console handler (colored, human-readable)
       console_handler = logging.StreamHandler(sys.stdout)
       console_handler.setFormatter(
           colorlog.ColoredFormatter(
               "%(log_color)s%(asctime)s %(levelname)s %(name)s %(message)s",
               datefmt="%Y-%m-%d %H:%M:%S",
               log_colors={
                   "DEBUG": "cyan",
                   "INFO": "green",
                   "WARNING": "yellow",
                   "ERROR": "red",
                   "CRITICAL": "red,bg_white",
               }
           )
       )

       # File handler (persistent, structured)
       handlers = [console_handler]
       if log_file:
           log_file.parent.mkdir(parents=True, exist_ok=True)
           file_handler = logging.FileHandler(log_file)
           file_handler.setFormatter(logging.Formatter("%(message)s"))
           handlers.append(file_handler)

       root_logger = logging.getLogger()
       root_logger.handlers = handlers

       # Configure structlog
       if json_output:
           # JSON output for log aggregation
           structlog.configure(
               processors=[
                   structlog.stdlib.filter_by_level,
                   structlog.stdlib.add_logger_name,
                   structlog.stdlib.add_log_level,
                   structlog.processors.TimeStamper(fmt="iso"),
                   structlog.processors.StackInfoRenderer(),
                   structlog.processors.format_exc_info,
                   structlog.processors.JSONRenderer(),
               ],
               context_class=dict,
               logger_factory=structlog.stdlib.LoggerFactory(),
               wrapper_class=structlog.stdlib.BoundLogger,
               cache_logger_on_first_use=True,
           )
       else:
           # Human-readable output for development
           structlog.configure(
               processors=[
                   structlog.stdlib.filter_by_level,
                   structlog.stdlib.add_logger_name,
                   structlog.stdlib.add_log_level,
                   structlog.processors.TimeStamper(fmt="%Y-%m-%d %H:%M:%S"),
                   structlog.dev.ConsoleRenderer(colors=True),
               ],
               context_class=dict,
               logger_factory=structlog.stdlib.LoggerFactory(),
               wrapper_class=structlog.stdlib.BoundLogger,
               cache_logger_on_first_use=True,
           )

       return structlog.get_logger()
   ```

3. Add logging to BaseService:
   ```python
   import structlog

   class BaseService(ABC):
       def __init__(self):
           self._logger = structlog.get_logger(self.__class__.__name__)

       def log_debug(self, message: str, **kwargs) -> None:
           self._logger.debug(message, **kwargs)

       def log_info(self, message: str, **kwargs) -> None:
           self._logger.info(message, **kwargs)

       def log_warning(self, message: str, **kwargs) -> None:
           self._logger.warning(message, **kwargs)

       def log_error(self, message: str, exc_info: bool = False, **kwargs) -> None:
           self._logger.error(message, exc_info=exc_info, **kwargs)

       def log_critical(self, message: str, exc_info: bool = True, **kwargs) -> None:
           self._logger.critical(message, exc_info=exc_info, **kwargs)
   ```

4. Replace print statements in services:
   ```python
   # Before (wallhaven_service.py)
   print(f"Download error: {e}")

   # After
   class WallhavenService(BaseService):
       async def download(self, url: str, dest: Path) -> bool:
           try:
               await self._download_to_file(url, dest)
               return True
           except Exception as e:
               self.log_error(
                   "Download failed",
                   url=url,
                   dest=str(dest),
                   error=str(e)
               )
               return False

   # Before (local_service.py)
   print(f"Error scanning directory: {e}")

   # After
   class LocalWallpaperService(BaseService):
       def get_wallpapers(self, recursive: bool = True) -> List[LocalWallpaper]:
           try:
               # ... scanning logic
           except Exception as e:
               self.log_error(
                   "Failed to scan directory",
                   directory=str(self.pictures_dir),
                   error=str(e)
               )
               return []
   ```

5. Add context to logs:
   ```python
   # Add context to each log entry
   self.log_info(
       "Searching wallpapers",
       query=query,
       categories=categories,
       page=page
   )

   # Structured output:
   # 2025-01-05 10:30:15 INFO WallhavenService Searching wallpapers query="landscape" categories="111" page=1
   ```

6. Configure logging in main entry point:
   ```python
   # main.py or launcher.py
   import sys
   from pathlib import Path

   def main():
       # Configure logging
       log_dir = Path.home() / ".cache" / "wallpicker" / "logs"
       configure_logging(
           level=logging.DEBUG if "--debug" in sys.argv else logging.INFO,
           log_file=log_dir / "wallpicker.log",
           json_output="--json-logs" in sys.argv,
       )

       logger = structlog.get_logger(__name__)
       logger.info("Starting Wallpicker")

       # Start application
       ...
   ```

7. Add logging to ViewModels:
   ```python
   class WallhavenViewModel(BaseViewModel):
       async def search(self, query: str, **filters) -> None:
           self.log_info("Search started", query=query, filters=filters)

           try:
               result = await self._service.search(query, **filters)
               self.log_info(
                   "Search completed",
                   query=query,
                   count=len(result.get("data", []))
               )
           except Exception as e:
               self.log_error(
                   "Search failed",
                   query=query,
                   error=str(e),
                   exc_info=True
               )
               raise
   ```

8. Remove all print statements:
   ```bash
   # Find all print statements
   grep -rn "print(" src/

   # Replace with logging
   ```

tests:
- Unit: Test logging configuration
- Unit: Test log levels
- Integration: Test logs are written to file
- UI: Test debug logs don't appear in release mode

acceptance_criteria:
- Logging configured with structlog
- All print statements replaced with logging
- Services use structured logging with context
- Log file written to ~/.cache/wallpicker/logs/
- Colored console output for development
- JSON output option for production
- Log levels: DEBUG, INFO, WARNING, ERROR, CRITICAL
- Logs include context (query, url, etc.)

validation:
- Commands to verify:
  ```bash
  grep -rn "print(" src/  # Should return nothing
  python -m pytest tests/ -v  # Check test logs
  ```
- Run application and check console output (colored, formatted)
- Check log file: ~/.cache/wallpicker/logs/wallpicker.log

notes:
- Structured logging: key-value pairs in logs
- Context-aware: logs include relevant data (query, url, etc.)
- Log levels: DEBUG for dev, INFO for production
- Colorized output for console
- JSON output for log aggregation (ELK, Splunk, etc.)
- Log rotation: configure in logging dictConfig
- Don't log sensitive data (API keys, passwords)
- Log errors with exc_info=True for stack traces

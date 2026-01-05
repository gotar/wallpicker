"""Base service class with common functionality."""

from abc import ABC
from logging import getLogger, Logger


class BaseService(ABC):
    """Base class for all services with logging support."""

    def __init__(self) -> None:
        """Initialize base service with logger."""
        self._logger: Logger = getLogger(self.__class__.__name__)

    @property
    def logger(self) -> Logger:
        """Get logger instance."""
        return self._logger

    def log_debug(self, message: str) -> None:
        """Log debug message."""
        self._logger.debug(message)

    def log_info(self, message: str) -> None:
        """Log info message."""
        self._logger.info(message)

    def log_warning(self, message: str) -> None:
        """Log warning message."""
        self._logger.warning(message)

    def log_error(self, message: str, exc_info: bool = False) -> None:
        """Log error message."""
        self._logger.error(message, exc_info=exc_info)

    def log_critical(self, message: str, exc_info: bool = False) -> None:
        """Log critical message."""
        self._logger.critical(message, exc_info=exc_info)

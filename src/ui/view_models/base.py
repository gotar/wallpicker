"""Base ViewModel with observable state management."""

from gi.repository import GObject
from typing import Optional, Any


class BaseViewModel(GObject.Object):
    """Base ViewModel with observable state for MVVM pattern."""

    __gtype_name__ = "BaseViewModel"

    def __init__(self) -> None:
        """Initialize base ViewModel."""
        super().__init__()
        self._is_busy: bool = False
        self._error_message: Optional[str] = None

    @GObject.Property(type=bool, default=False)
    def is_busy(self) -> bool:
        """Get busy state."""
        return self._is_busy

    @is_busy.setter
    def is_busy(self, value: bool) -> None:
        """Set busy state and notify observers."""
        self._is_busy = value

    @GObject.Property(type=str, default=None)
    def error_message(self) -> Optional[str]:
        """Get error message."""
        return self._error_message

    @error_message.setter
    def error_message(self, value: Optional[str]) -> None:
        """Set error message and notify observers."""
        self._error_message = value
        if value:
            self.is_busy = False

    def clear_error(self) -> None:
        """Clear error message."""
        self.error_message = None

    def set_busy(self, busy: bool) -> None:
        """Set busy state."""
        self.is_busy = busy
        if not busy:
            self.clear_error()

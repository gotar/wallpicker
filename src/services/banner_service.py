"""Banner Service for managing Adw.Banner notifications."""

from collections.abc import Callable
from enum import IntEnum, auto

from gi.repository import Adw, GLib, GObject


class BannerPriority(IntEnum):
    """Priority levels for banner queue management."""

    LOW = auto()  # Info banners
    MEDIUM = auto()  # API warnings, selection banners
    HIGH = auto()  # Storage warnings


class BannerType(str):
    """Banner type identifiers."""

    SELECTION = "selection"
    STORAGE = "storage"
    API = "api"
    INFO = "info"


class BannerService(GObject.Object):
    """Service for managing Adw.Banner notifications.

    Supports priority-based banner queue management with automatic
    dismissal and integration with Adw.ToolbarView layout.
    """

    # GObject properties
    current_banner_type = GObject.Property(type=str, default="")
    is_visible = GObject.Property(type=bool, default=False)

    def __init__(self, window: Adw.ApplicationWindow):
        """Initialize BannerService with window reference.

        Args:
            window: The main application window for banner attachment
        """
        super().__init__()
        self.window = window

        # Banner container (will be inserted into ToolbarView)
        self.banner_container = Adw.Banner()
        self.banner_container.set_revealed(False)
        self.banner_container.set_button_label(None)
        self._current_callback = None
        self._current_banner = None
        self.current_banner_type = ""
        self.is_visible = False

        # Banner queue for priority-based management
        self._banner_queue = []
        self._dismiss_timeout = None

        # Connect button-clicked signal to handle callbacks
        self.banner_container.connect("button-clicked", self._on_button_clicked)

    def _on_button_clicked(self, banner) -> None:
        """Handle button click on banner."""
        if self._current_callback:
            self._current_callback()

    def _apply_css_class(self, css_class: str | None) -> None:
        """Apply CSS class to banner.

        Args:
            css_class: CSS class name or None
        """
        # Clear existing custom classes
        context = self.banner_container.get_style_context()
        context.remove_class("warning-banner")
        context.remove_class("info-banner")
        context.remove_class("selection-banner")

        # Apply new class
        if css_class:
            context.add_class(css_class)

    def _schedule_auto_dismiss(self, seconds: int) -> None:
        """Schedule automatic banner dismissal.

        Args:
            seconds: Seconds before dismissal
        """
        self._dismiss_timeout = GLib.timeout_add_seconds(
            seconds, self._on_auto_dismiss_timeout
        )

    def _cancel_auto_dismiss(self) -> None:
        """Cancel scheduled auto-dismiss."""
        if self._dismiss_timeout:
            GLib.source_remove(self._dismiss_timeout)
            self._dismiss_timeout = None

    def _on_auto_dismiss_timeout(self) -> bool:
        """Handle auto-dismiss timeout.

        Returns:
            False to indicate timeout should not repeat
        """
        self.clear_banner()
        return False

    def show_selection_banner(self, count: int, on_set_all: Callable) -> None:
        """Show multi-selection banner.

        Args:
            count: Number of selected wallpapers
            on_set_all: Callback for "Set All" button
        """
        if count <= 0:
            self.hide_selection_banner()
            return

        title = f"{count} wallpaper{'s' if count > 1 else ''} selected"

        self._show_banner(
            title=title,
            button_text="Set All",
            callback=on_set_all,
            priority=BannerPriority.MEDIUM,
            banner_type=BannerType.SELECTION,
            css_class="selection-banner",
        )

    def show_storage_warning(
        self, used_mb: int, limit_mb: int, on_clear_cache: Callable
    ) -> None:
        """Show storage warning banner.

        Args:
            used_mb: Current cache usage in MB
            limit_mb: Cache limit in MB (typically 500)
            on_clear_cache: Callback for "Clear Cache" button
        """
        title = f"Storage space low ({used_mb} MB / {limit_mb} MB)"

        self._show_banner(
            title=title,
            button_text="Clear Cache",
            callback=on_clear_cache,
            priority=BannerPriority.HIGH,
            banner_type=BannerType.STORAGE,
            css_class="warning-banner",
        )

    def show_api_warning(
        self,
        message: str,
        button_text: str | None = None,
        on_button_click: Callable | None = None,
    ) -> None:
        """Show API quota warning.

        Args:
            message: Warning message
            button_text: Optional button label
            on_button_click: Optional button callback
        """
        self._show_banner(
            title=message,
            button_text=button_text,
            callback=on_button_click,
            priority=BannerPriority.MEDIUM,
            banner_type=BannerType.API,
            css_class="warning-banner",
        )

    def show_info_banner(
        self,
        message: str,
        button_text: str | None = None,
        on_button_click: Callable | None = None,
    ) -> None:
        """Show informational banner.

        Args:
            message: Informational message
            button_text: Optional button label
            on_button_click: Optional button callback
        """
        self._show_banner(
            title=message,
            button_text=button_text,
            callback=on_button_click,
            priority=BannerPriority.LOW,
            banner_type=BannerType.INFO,
            css_class="info-banner",
            auto_dismiss_seconds=10,
        )

    def clear_banner(self) -> None:
        """Hide/dismiss current banner."""
        if not self.is_visible:
            return

        self._clear_current_banner()
        self._process_next_banner()

    def hide_selection_banner(self) -> None:
        """Hide multi-selection banner specifically."""
        self._remove_from_queue_by_type(BannerType.SELECTION)

        if self.current_banner_type == BannerType.SELECTION:
            self.clear_banner()

    def get_banner_widget(self) -> Adw.Banner:
        """Get the Adw.Banner widget for window layout integration.

        Returns:
            The Adw.Banner widget to be inserted into ToolbarView
        """
        return self.banner_container

    def cleanup(self) -> None:
        """Clean up banner resources on window close."""
        self._cancel_auto_dismiss()
        self._clear_current_banner()
        self._banner_queue.clear()

    def _show_banner(
        self,
        title: str,
        button_text: str | None = None,
        callback: Callable | None = None,
        priority: BannerPriority = BannerPriority.LOW,
        banner_type: str = BannerType.INFO,
        css_class: str | None = None,
        auto_dismiss_seconds: int | None = None,
    ) -> None:
        """Show a banner with priority queue management.

        Args:
            title: Banner title/message
            button_text: Optional button label
            callback: Optional button callback
            priority: Banner priority for queue ordering
            banner_type: Type identifier for banner
            css_class: CSS class to apply
            auto_dismiss_seconds: Optional auto-dismiss timeout
        """
        entry = {
            "title": title,
            "button_text": button_text,
            "callback": callback,
            "priority": priority,
            "type": banner_type,
            "css_class": css_class,
            "auto_dismiss_seconds": auto_dismiss_seconds,
        }
        self._add_to_queue(entry)
        self._process_next_banner()

    def _add_to_queue(self, entry: dict) -> None:
        """Add banner to priority queue, replacing same-type banners.

        Args:
            entry: Banner entry dictionary
        """
        self._remove_from_queue_by_type(entry["type"])
        self._banner_queue.append(entry)
        self._banner_queue.sort(key=lambda x: x["priority"], reverse=True)

    def _remove_from_queue_by_type(self, banner_type: str) -> None:
        """Remove banners of specified type from queue.

        Args:
            banner_type: Banner type to remove
        """
        self._banner_queue = [
            banner for banner in self._banner_queue if banner["type"] != banner_type
        ]

    def _display_banner_entry(self, entry: dict) -> None:
        """Display a banner entry from the queue.

        Args:
            entry: Banner entry dictionary
        """
        self._apply_css_class(entry.get("css_class"))

        self.banner_container.set_title(entry["title"])

        if entry["button_text"]:
            self.banner_container.set_button_label(entry["button_text"])
        else:
            self.banner_container.set_button_label(None)

        self._current_callback = entry.get("callback")

        self.banner_container.set_revealed(True)
        self.current_banner_type = entry["type"]
        self.is_visible = True

        if entry.get("auto_dismiss_seconds"):
            self._schedule_auto_dismiss(entry["auto_dismiss_seconds"])
        elif entry["type"] == BannerType.INFO:
            self._schedule_auto_dismiss(10)

    def _process_next_banner(self) -> None:
        """Process next banner from the queue."""
        # Clear current banner
        self._clear_current_banner()

        # Display next banner if queue not empty
        if self._banner_queue:
            next_banner = self._banner_queue.pop(0)
            self._display_banner_entry(next_banner)

    def _clear_current_banner(self) -> None:
        """Clear the currently displayed banner."""
        if not self.is_visible:
            return

        # Cancel any pending auto-dismiss
        self._cancel_auto_dismiss()

        # Hide banner
        self.banner_container.set_revealed(False)
        self.current_banner_type = None
        self.is_visible = False
        self._current_callback = None

        # Clear CSS classes
        self._apply_css_class(None)

    @property
    def logger(self):
        """Get logger instance (compatibility with BaseService)."""
        import logging

        return logging.getLogger(self.__class__.__name__)

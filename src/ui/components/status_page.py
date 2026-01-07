"""Reusable Status Page component for loading, empty, and error states."""

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")

from gi.repository import Adw, Gtk  # noqa: E402


class WallpaperStatusPage(Adw.Bin):
    """Reusable status page for different states."""

    def __init__(self):
        super().__init__()

        self.stack = Adw.Stack()
        self.stack.set_transition_type(Gtk.StackTransitionType.CROSSFADE)
        self.stack.set_transition_duration(300)
        self.stack.set_hexpand(True)
        self.stack.set_vexpand(True)

        # Loading state
        self.loading_page = Adw.StatusPage()
        self.loading_page.set_icon_name("image-loading-symbolic")
        self.loading_page.set_title("Loading wallpapers...")
        self.loading_page.set_description("Fetching from server")
        self.stack.add_named(self.loading_page, "loading")

        # Empty state
        self.empty_page = Adw.StatusPage()
        self.empty_page.set_icon_name("image-missing-symbolic")
        self.empty_page.set_title("No wallpapers found")
        self.empty_page.set_description(
            "Add wallpapers to your collection or adjust your search filters"
        )
        self.empty_page.add_css_class("compact")
        self.stack.add_named(self.empty_page, "empty")

        # Error state
        self.error_page = Adw.StatusPage()
        self.error_page.set_icon_name("network-offline-symbolic")
        self.error_page.set_title("Failed to load")
        self.error_page.set_description("Check your connection and try again")

        # Retry button for error page
        self.retry_btn = Gtk.Button(label="Retry")
        self.retry_btn.add_css_class("suggested-action")
        self.error_page.set_child(self.retry_btn)
        self.stack.add_named(self.error_page, "error")

        # Content state (placeholder for actual content)
        self.content_page = Adw.Bin()
        self.content_page.set_hexpand(True)
        self.content_page.set_vexpand(True)
        self.stack.add_named(self.content_page, "content")

        self.set_child(self.stack)

        # Callback storage
        self._retry_callback = None
        self._empty_action_callback = None

        # Connect retry button
        self.retry_btn.connect("clicked", self._on_retry_clicked)

    def set_state(
        self, state: str, title: str = None, description: str = None, callback=None
    ):
        """Set the visible state.

        Args:
            state: One of 'loading', 'empty', 'error', 'content'
            title: Optional title to override default
            description: Optional description to override default
            callback: Optional callback function for retry/action buttons
        """
        self.stack.set_visible_child_name(state)

        if state == "error":
            if title:
                self.error_page.set_title(title)
            if description:
                self.error_page.set_description(description)
            self._retry_callback = callback
            self.retry_btn.set_visible(callback is not None)

        elif state == "empty":
            if title:
                self.empty_page.set_title(title)
            if description:
                self.empty_page.set_description(description)
            self._empty_action_callback = callback

    def set_content(self, widget):
        """Set the content widget for 'content' state."""
        self.content_page.set_child(widget)

    def _on_retry_clicked(self, button):
        """Handle retry button click."""
        if self._retry_callback:
            self._retry_callback()

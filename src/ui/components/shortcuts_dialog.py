"""Keyboard shortcuts dialog component."""

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")

from gi.repository import Adw, Gtk  # noqa: E402


class ShortcutsDialog(Adw.Dialog):
    """Dialog displaying all keyboard shortcuts."""

    def __init__(self, parent_window):
        """Initialize shortcuts dialog.

        Args:
            parent_window: Parent window for dialog
        """
        super().__init__()
        self.set_title("Keyboard Shortcuts")
        self.set_content_width(600)
        self.set_content_height(700)
        self.add_css_class("shortcuts-dialog")

        # Create main content
        self._create_ui()

    def _create_ui(self):
        """Create dialog UI with shortcut groups."""
        # Main scroll area
        scroll = Gtk.ScrolledWindow()
        scroll.set_vexpand(True)
        scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)

        # Content box
        content = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=16)
        content.set_margin_top(24)
        content.set_margin_bottom(24)
        content.set_margin_start(24)
        content.set_margin_end(24)

        # Tab navigation section
        tab_group = self._create_shortcut_group(
            "Tab Navigation",
            [
                ("Ctrl/Cmd + 1", "Go to Local tab"),
                ("Ctrl/Cmd + 2", "Go to Wallhaven tab"),
                ("Ctrl/Cmd + 3", "Go to Favorites tab"),
                ("Alt + 1/2/3", "Alternative tab selection"),
                ("Ctrl/Cmd + Tab", "Next tab"),
                ("Ctrl/Cmd + Shift + Tab", "Previous tab"),
                ("Ctrl/Cmd + [", "Previous tab"),
                ("Ctrl/Cmd + ]", "Next tab"),
            ],
        )
        content.append(tab_group)

        # Search section
        search_group = self._create_shortcut_group(
            "Search",
            [
                ("Ctrl/Cmd + F", "Focus search entry"),
                ("Ctrl/Cmd + N", "New search (clears search)"),
                ("Escape", "Clear search and lose focus"),
            ],
        )
        content.append(search_group)

        # Grid navigation section
        grid_group = self._create_shortcut_group(
            "Grid Navigation",
            [
                ("↑ / ↓ / ← / →", "Navigate between cards"),
                ("Enter / Return", "Set wallpaper (open preview)"),
                ("Space", "Toggle favorite"),
                ("Ctrl/Cmd + A", "Select all wallpapers"),
                ("Escape", "Deselect all wallpapers"),
            ],
        )
        content.append(grid_group)

        # Actions section
        actions_group = self._create_shortcut_group(
            "Actions",
            [
                ("Ctrl/Cmd + R", "Refresh current view"),
                ("Ctrl/Cmd + D", "Delete selected wallpapers"),
                ("Double-click", "Set wallpaper directly"),
            ],
        )
        content.append(actions_group)

        # Preview dialog section
        preview_group = self._create_shortcut_group(
            "Preview Dialog",
            [
                ("Escape", "Close dialog"),
                ("Ctrl/Cmd + W", "Close dialog"),
                ("Enter / Return", "Set wallpaper"),
                ("Space", "Toggle favorite"),
                ("Double-click", "Close dialog"),
            ],
        )
        content.append(preview_group)

        # Selection section
        selection_group = self._create_shortcut_group(
            "Multi-Selection",
            [
                ("Ctrl/Cmd + Click", "Toggle selection"),
                ("Shift + Click", "Range selection"),
                ("Ctrl/Cmd + A", "Select all"),
                ("Escape", "Deselect all"),
            ],
        )
        content.append(selection_group)

        # Tips section
        tips_group = self._create_info_group(
            "Tips",
            [
                "• Use arrow keys to navigate the grid quickly",
                "• Press Enter to preview wallpaper or set it directly",
                "• Use Ctrl+A to select multiple wallpapers",
                "• Keyboard shortcuts work seamlessly with mouse/touch",
                "• Press Ctrl+? or Ctrl+/ to show this dialog (coming soon)",
            ],
        )
        content.append(tips_group)

        scroll.set_child(content)
        self.set_child(scroll)

    def _create_shortcut_group(
        self, title: str, shortcuts: list[tuple[str, str]]
    ) -> Adw.PreferencesGroup:
        """Create a shortcut group with title and shortcuts.

        Args:
            title: Group title
            shortcuts: List of (shortcut, description) tuples

        Returns:
            Adw.PreferencesGroup with shortcuts
        """
        group = Adw.PreferencesGroup()
        group.set_title(title)
        group.set_margin_top(12)

        for shortcut, description in shortcuts:
            row = Adw.ActionRow()
            row.set_title(shortcut)
            row.set_subtitle(description)

            group.add(row)

        return group

    def _create_info_group(self, title: str, tips: list[str]) -> Adw.PreferencesGroup:
        """Create an info group with tips.

        Args:
            title: Group title
            tips: List of tip strings

        Returns:
            Adw.PreferencesGroup with tips
        """
        group = Adw.PreferencesGroup()
        group.set_title(title)
        group.set_margin_top(12)

        for tip in tips:
            row = Adw.ActionRow()
            row.set_title(tip)
            row.set_activatable(False)

            group.add(row)

        return group

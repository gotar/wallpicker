"""Main Window - Refactored with Adw.ToolbarView and MVVM pattern."""

# ruff: noqa: E402  # gi.repository imports must follow gi.require_version()

import logging
import sys
from pathlib import Path

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")

from gi.repository import Adw, Gdk, Gio, Gtk  # noqa: E402

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from core.asyncio_integration import schedule_async  # noqa: E402
from services.banner_service import BannerService
from services.config_service import ConfigService
from services.favorites_service import FavoritesService
from services.local_service import LocalWallpaperService
from services.notification_service import NotificationService
from services.thumbnail_cache import ThumbnailCache
from services.thumbnail_loader import ThumbnailLoader
from services.toast_service import ToastService
from services.wallhaven_service import WallhavenService
from services.wallpaper_setter import WallpaperSetter
from ui.components.shortcuts_dialog import ShortcutsDialog
from ui.view_models.favorites_view_model import FavoritesViewModel
from ui.view_models.local_view_model import LocalViewModel
from ui.view_models.wallhaven_view_model import WallhavenViewModel
from ui.views.favorites_view import FavoritesView
from ui.views.local_view import LocalView
from ui.views.wallhaven_view import WallhavenView


class MainWindow(Adw.Application):
    """Main application entry point."""

    def __init__(self, debug=False):
        super().__init__(application_id="com.gotar.Wallpicker")
        self.debug = debug
        self.window = None
        self.config = None
        self.config_service = None
        self.wallpaper_setter = None
        self.local_service = None
        self.favorites_service = None
        self.wallhaven_service = None
        self.thumbnail_cache = None
        self.notification_service = None
        self.local_view_model = None
        self.favorites_view_model = None
        self.wallhaven_view_model = None

    def do_activate(self):
        if not self.window:
            # Load CSS before creating window
            self._load_css()

            self.config_service = ConfigService()
            self.config = self.config_service.get_config()

            self.wallpaper_setter = WallpaperSetter()
            self.notification_service = NotificationService(
                enabled=self.config.notifications_enabled if self.config else True
            )

            self.local_service = LocalWallpaperService(
                pictures_dir=self.config.pictures_dir if self.config else None
            )
            self.favorites_service = FavoritesService()
            self.wallhaven_service = WallhavenService()
            self.thumbnail_cache = ThumbnailCache()
            self.thumbnail_loader = ThumbnailLoader(thumbnail_cache=self.thumbnail_cache)
            self.banner_service = BannerService(self)

        self.wallhaven_view_model = WallhavenViewModel(
            wallhaven_service=self.wallhaven_service,
            wallpaper_setter=self.wallpaper_setter,
            config_service=self.config_service,
        )
        self.wallhaven_view_model.favorites_service = self.favorites_service

        self.local_view_model = LocalViewModel(
            local_service=self.local_service,
            wallpaper_setter=self.wallpaper_setter,
            pictures_dir=self.config.pictures_dir if self.config else None,
            config_service=self.config_service,
        )
        self.local_view_model.favorites_service = self.favorites_service

        self.favorites_view_model = FavoritesViewModel(
            favorites_service=self.favorites_service,
            wallpaper_setter=self.wallpaper_setter,
            config_service=self.config_service,
            wallhaven_service=self.wallhaven_service,
        )

        self.window = WallPickerWindow(
            application=self,
            local_view_model=self.local_view_model,
            favorites_view_model=self.favorites_view_model,
            wallhaven_view_model=self.wallhaven_view_model,
            wallpaper_setter=self.wallpaper_setter,
            banner_service=self.banner_service,
            thumbnail_loader=self.thumbnail_loader,
            config_service=self.config_service,
        )

        # Add responsive breakpoints
        breakpoint = Adw.Breakpoint(condition=Adw.BreakpointCondition.parse("max-width: 600px"))
        self.window.add_breakpoint(breakpoint)

        self.window.present()

    def _load_css(self):
        """Load CSS stylesheet for the application."""
        css_paths = [
            Path(__file__).parent.parent.parent / "data" / "style.css",
            Path("/usr/share/wallpicker/style.css"),
            Path.home() / ".local/share/wallpicker/style.css",
        ]

        css_path = None
        for path in css_paths:
            if path.exists():
                css_path = path
                break

        if not css_path:
            logging.warning(f"CSS file not found in any of: {css_paths}")
            return

        css_provider = Gtk.CssProvider()

        try:
            css_provider.load_from_path(str(css_path))

            display = Gdk.Display.get_default()
            if display:
                Gtk.StyleContext.add_provider_for_display(
                    display,
                    css_provider,
                    Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION,
                )
            else:
                logging.warning("Could not get default display for CSS loading")
        except Exception as e:
            logging.error(f"Error loading CSS: {e}")


class WallPickerWindow(Adw.ApplicationWindow):
    """Main application window with Adw.ToolbarView and MVVM architecture."""

    def __init__(
        self,
        application,
        local_view_model,
        favorites_view_model,
        wallhaven_view_model,
        wallpaper_setter,
        banner_service,
        thumbnail_loader,
        config_service=None,
    ):
        super().__init__(application=application)
        self.set_title("WallPicker")
        self.set_default_size(1200, 800)
        self.set_size_request(600, 400)

        self.local_view_model = local_view_model
        self.favorites_view_model = favorites_view_model
        self.wallhaven_view_model = wallhaven_view_model
        self.wallpaper_setter = wallpaper_setter
        self.banner_service = banner_service
        self.thumbnail_loader = thumbnail_loader
        self.config_service = config_service

        self.wallhaven_view_model.connect("wallpaper-downloaded", self._on_wallpaper_downloaded)

        self._create_ui()
        self._setup_menu()
        self._setup_keyboard_navigation()
        self._setup_focus_chain()

    def _on_set_wallpaper(self, wallpaper):
        """Set wallpaper from any view."""
        self.wallpaper_setter.set_wallpaper(wallpaper.path)
        self.toast_service.show_info("Wallpaper set")

    def _on_delete_wallpaper(self, wallpaper):
        """Delete wallpaper from local view."""

        # Use the view model to delete (it has the service)
        self.local_view_model.delete_wallpaper(wallpaper)
        self.toast_service.show_info("Wallpaper deleted")

    def _on_remove_favorite(self, favorite):
        """Remove favorite from favorites view."""
        # Use the view model to remove (it has the service)
        self.favorites_view_model.remove_favorite(favorite)
        self.toast_service.show_info("Removed from favorites")

    def _on_wallpaper_downloaded(self, view_model, download_path):
        """Refresh local view when wallpaper is downloaded from Wallhaven."""
        self.local_view_model.load_wallpapers()

    def _create_ui(self):
        """Create main UI with Adw.ToolbarView layout."""
        self.toast_service = ToastService(self)

        self.toolbar_view = Adw.ToolbarView()

        # Header
        self.header = Adw.HeaderBar()
        self.toolbar_view.add_top_bar(self.header)

        # Refresh button
        self.refresh_btn = Gtk.Button()
        self.refresh_btn.set_icon_name("view-refresh-symbolic")
        self.refresh_btn.add_css_class("flat")
        self.refresh_btn.set_tooltip_text("Refresh")
        self.refresh_btn.connect("clicked", self._on_refresh_button_clicked)
        self.header.pack_start(self.refresh_btn)

        # Menu button
        self.menu_btn = Gtk.MenuButton()
        self.menu_btn.set_icon_name("open-menu-symbolic")
        self.menu_btn.add_css_class("flat")
        self.header.pack_end(self.menu_btn)

        # Tab switcher bar (placed below header at top of content area)
        self.switcher_bar = Adw.ViewSwitcherBar()
        self.switcher_bar.set_reveal(True)
        self.toolbar_view.add_top_bar(self.switcher_bar)

        # View stack for tabs
        self.stack = Adw.ViewStack()
        self.stack.set_hexpand(True)
        self.stack.set_vexpand(True)

        # Track tab names for keyboard navigation
        self.tabs = ["local", "wallhaven", "favorites"]

        # Create views (add_titled() auto-creates ViewSwitcherBar at bottom)
        self.local_view = LocalView(
            self.local_view_model,
            self.banner_service,
            self.toast_service,
            self.thumbnail_loader,
            on_set_wallpaper=self._on_set_wallpaper,
            on_delete=self._on_delete_wallpaper,
            config_service=self.config_service,
        )
        local_page = self.stack.add_titled(self.local_view, "local", "Local")
        local_page.set_icon_name("folder-symbolic")

        self.wallhaven_view = WallhavenView(
            self.wallhaven_view_model,
            self.banner_service,
            self.toast_service,
            self.thumbnail_loader,
        )
        wallhaven_page = self.stack.add_titled(self.wallhaven_view, "wallhaven", "Wallhaven")
        wallhaven_page.set_icon_name("globe-symbolic")

        self.favorites_view = FavoritesView(
            self.favorites_view_model,
            self.banner_service,
            self.toast_service,
            self.thumbnail_loader,
        )
        favorites_page = self.stack.add_titled(self.favorites_view, "favorites", "Favorites")
        favorites_page.set_icon_name("starred-symbolic")

        # Connect ViewSwitcherBar to ViewStack
        self.switcher_bar.set_stack(self.stack)

        # Set stack as content (no Clamp - use full window width)
        self.toolbar_view.set_content(self.stack)

        # Banner at bottom
        self.toolbar_view.add_bottom_bar(self.banner_service.get_banner_widget())

        # Wrap toolbar view in toast overlay
        self.toast_service.overlay.set_child(self.toolbar_view)

        # Connect stack change signal
        self.stack.connect("notify::visible-child", self._on_tab_changed)

        # Load initial data
        try:
            self.local_view_model.load_wallpapers()
            self.favorites_view_model.load_favorites()
        except Exception as e:
            self.toast_service.show_error(f"Failed to load: {e}")

        # Setup gesture controllers
        self._setup_gestures()

    def _on_tab_changed(self, stack, pspec):
        """Handle tab change."""
        visible_child = stack.get_visible_child()
        logger = logging.getLogger(__name__)

        if visible_child == self.favorites_view:
            logger.info("Switching to Favorites tab")
            self.favorites_view_model.load_favorites()
        elif visible_child == self.wallhaven_view:
            # Only load Wallhaven wallpapers if not already loaded
            logger.info(
                f"Switching to Wallhaven tab (wallpapers count: {len(self.wallhaven_view_model.wallpapers)})"
            )
            if not self.wallhaven_view_model.wallpapers:
                logger.info("Loading Wallhaven wallpapers for the first time")
                schedule_async(self.wallhaven_view_model.load_initial_wallpapers())

    def _on_refresh_button_clicked(self, button):
        """Handle refresh button click."""
        visible_child = self.stack.get_visible_child()
        if visible_child == self.local_view:
            self.local_view_model.load_wallpapers()
            self.toast_service.show_info("Local wallpapers refreshed")
        elif visible_child == self.favorites_view:
            self.favorites_view_model.load_favorites()
            self.toast_service.show_info("Favorites refreshed")
        elif visible_child == self.wallhaven_view:
            schedule_async(self.wallhaven_view_model.load_initial_wallpapers())
            self.toast_service.show_info("Wallhaven wallpapers refreshed")

    def _setup_gestures(self):
        """Setup touch gestures for the application"""
        self._setup_swipe_gestures()
        self._setup_keyboard_navigation()

    def _setup_swipe_gestures(self):
        """Setup swipe gesture for tab switching."""

        # Create swipe controller
        swipe = Gtk.GestureSwipe()
        swipe.set_propagation_phase(Gtk.PropagationPhase.BUBBLE)
        swipe.connect("swipe", self._on_swipe)
        self.stack.add_controller(swipe)

    def _on_swipe(self, gesture, dx, dy):
        """Handle swipe gesture for tab switching."""
        # Get current visible tab
        current = self.stack.get_visible_child_name()
        if current not in self.tabs:
            return

        current_idx = self.tabs.index(current)

        # Determine direction (left/right swipe on horizontal axis)
        # Swipe right (dx > 0) → Previous tab
        # Swipe left (dx < 0) → Next tab
        if dx > 100:  # Swipe right with minimum threshold
            new_idx = max(0, current_idx - 1)
        elif dx < -100:  # Swipe left with minimum threshold
            new_idx = min(len(self.tabs) - 1, current_idx + 1)
        else:
            return  # Swipe not long enough

        # Only switch if we're actually changing tabs
        if new_idx != current_idx:
            new_tab = self.tabs[new_idx]
            self.stack.set_visible_child_name(new_tab)

    def _setup_keyboard_navigation(self):
        """Setup keyboard shortcuts for global navigation."""
        key_controller = Gtk.EventControllerKey()
        key_controller.connect("key-pressed", self._on_key_pressed)
        self.add_controller(key_controller)

    def _setup_menu(self):
        """Setup menu button with keyboard shortcuts option."""
        # Create popover menu
        popover = Gtk.PopoverMenu()
        self.menu_btn.set_popover(popover)

        # Create menu model
        menu = Gio.Menu()

        # Add shortcuts menu item
        shortcuts_item = Gio.MenuItem()
        shortcuts_item.set_label("Keyboard Shortcuts")
        shortcuts_item.set_detailed_action("win.shortcuts")
        menu.append_item(shortcuts_item)

        # Add about menu item
        about_item = Gio.MenuItem()
        about_item.set_label("About Wallpicker")
        about_item.set_detailed_action("win.about")
        menu.append_item(about_item)

        popover.set_menu_model(menu)

        # Setup action for shortcuts
        shortcuts_action = Gio.SimpleAction.new("shortcuts", None)
        shortcuts_action.connect("activate", self._show_shortcuts_dialog)
        self.add_action(shortcuts_action)

        # Setup action for about
        about_action = Gio.SimpleAction.new("about", None)
        about_action.connect("activate", self._show_about_dialog)
        self.add_action(about_action)

        # Add tooltip
        self.menu_btn.set_tooltip_text("Menu")

    def _show_shortcuts_dialog(self, action, parameter):
        """Show keyboard shortcuts dialog."""
        dialog = ShortcutsDialog(self)
        dialog.present()

    def _show_about_dialog(self, action, parameter):
        """Show about dialog."""
        about = Adw.AboutDialog()
        about.set_application_name("Wallpicker")
        about.set_version("1.0.0")
        about.set_developer_name("Wallpicker Contributors")
        about.set_license_type(Gtk.License.MIT_X11)
        about.set_website("https://github.com/gotar/wallpicker")
        about.set_issue_url("https://github.com/gotar/wallpicker/issues")
        about.add_credit_section("Contributors", ["gotar"])
        about.present(self)

    def _on_key_pressed(self, controller, keyval, keycode, state):
        """Handle keyboard shortcuts."""
        # Ctrl/Cmd + 1/2/3 : Direct tab selection
        if state & (Gdk.ModifierType.CONTROL_MASK | Gdk.ModifierType.SUPER_MASK):
            if keyval == Gdk.KEY_1:
                self.stack.set_visible_child_name("local")
                return True
            elif keyval == Gdk.KEY_2:
                self.stack.set_visible_child_name("wallhaven")
                return True
            elif keyval == Gdk.KEY_3:
                self.stack.set_visible_child_name("favorites")
                return True
            elif keyval == Gdk.KEY_Tab:  # Ctrl+Tab: Next tab
                self._next_tab()
                return True
            elif keyval == Gdk.KEY_f:  # Ctrl+F: Focus search
                self._focus_search_entry()
                return True
            elif keyval == Gdk.KEY_r:  # Ctrl+R: Refresh
                self._on_refresh_button_clicked(None)
                return True
            elif keyval == Gdk.KEY_n:  # Ctrl+N: New search
                self._focus_search_entry(clear=True)
                return True

        # Ctrl/Cmd + Shift + Tab: Previous tab
        elif (
            state
            & (
                Gdk.ModifierType.CONTROL_MASK
                | Gdk.ModifierType.SUPER_MASK
                | Gdk.ModifierType.SHIFT_MASK
            )
            and keyval == Gdk.KEY_Tab
        ):
            self._prev_tab()
            return True

        # Alt + 1/2/3 : Alternative direct tab selection
        elif state & Gdk.ModifierType.ALT_MASK:
            if keyval == Gdk.KEY_1:
                self.stack.set_visible_child_name("local")
                return True
            elif keyval == Gdk.KEY_2:
                self.stack.set_visible_child_name("wallhaven")
                return True
            elif keyval == Gdk.KEY_3:
                self.stack.set_visible_child_name("favorites")
                return True

        # Ctrl/Cmd + [ / ] : Previous/Next tab (alternative)
        elif state & (Gdk.ModifierType.CONTROL_MASK | Gdk.ModifierType.SUPER_MASK):
            if keyval == Gdk.KEY_bracketright:  # ] → Next tab
                self._next_tab()
                return True
            elif keyval == Gdk.KEY_bracketleft:  # [ → Previous tab
                self._prev_tab()
                return True

        return False

    def _focus_search_entry(self, clear=False):
        """Focus search entry in current view."""
        visible_child = self.stack.get_visible_child()
        if visible_child == self.wallhaven_view and hasattr(self.wallhaven_view, "search_entry"):
            if clear:
                self.wallhaven_view.search_entry.set_text("")
            self.wallhaven_view.search_entry.grab_focus()
        elif visible_child == self.favorites_view and hasattr(self.favorites_view, "search_entry"):
            if clear:
                self.favorites_view.search_entry.set_text("")
            self.favorites_view.search_entry.grab_focus()

    def _setup_focus_chain(self):
        """Setup initial focus when tab changes."""
        self.stack.connect("notify::visible-child", self._on_tab_focus_changed)

    def _on_tab_focus_changed(self, stack, pspec):
        """Handle focus change when tab changes."""
        visible_child = stack.get_visible_child()
        # Focus search entry if available
        if visible_child == self.wallhaven_view and hasattr(self.wallhaven_view, "search_entry"):
            # Don't auto-focus search on wallhaven, user can use Ctrl+F
            pass
        elif visible_child == self.local_view:
            # Focus grid on local view
            if hasattr(self.local_view, "wallpaper_grid"):
                first_child = self.local_view.wallpaper_grid.get_first_child()
                if first_child:
                    first_child.grab_focus()
        elif visible_child == self.favorites_view:
            # Focus grid on favorites view
            if hasattr(self.favorites_view, "wallpapers_grid"):
                first_child = self.favorites_view.wallpapers_grid.get_first_child()
                if first_child:
                    first_child.grab_focus()

    def _next_tab(self):
        """Switch to next tab."""
        current = self.stack.get_visible_child_name()
        if current not in self.tabs:
            return

        current_idx = self.tabs.index(current)
        new_idx = (current_idx + 1) % len(self.tabs)
        self.stack.set_visible_child_name(self.tabs[new_idx])

    def _prev_tab(self):
        """Switch to previous tab."""
        current = self.stack.get_visible_child_name()
        if current not in self.tabs:
            return

        current_idx = self.tabs.index(current)
        new_idx = (current_idx - 1) % len(self.tabs)
        self.stack.set_visible_child_name(self.tabs[new_idx])


def main():
    """Entry point for the wallpicker application."""
    import sys

    from core.asyncio_integration import setup_event_loop

    setup_event_loop()

    debug = "--debug" in sys.argv
    if debug:
        sys.argv.remove("--debug")

    app = MainWindow(debug=debug)
    app.run()

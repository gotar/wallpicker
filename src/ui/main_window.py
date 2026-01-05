"""Main Window - Refactored with MVVM pattern and simplified service access."""

import sys
from pathlib import Path

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from gi.repository import Adw, Gtk

from services.config_service import ConfigService
from services.favorites_service import FavoritesService
from services.local_service import LocalWallpaperService
from services.thumbnail_cache import ThumbnailCache
from services.wallhaven_service import WallhavenService
from services.wallpaper_setter import WallpaperSetter
from ui.view_models.favorites_view_model import FavoritesViewModel
from ui.view_models.local_view_model import LocalViewModel
from ui.view_models.wallhaven_view_model import WallhavenViewModel
from ui.views.favorites_view import FavoritesView
from ui.views.local_view import LocalView
from ui.views.wallhaven_view import WallhavenView


class MainWindow(Adw.Application):
    """Main application entry point."""

    def __init__(self, debug=False):
        super().__init__(application_id="com.example.Wallpicker")
        self.debug = debug
        self.window = None
        self.config_service = None
        self.wallpaper_setter = None
        self.local_view_model = None
        self.favorites_view_model = None
        self.wallhaven_view_model = None

    def do_activate(self):
        if not self.window:
            self.config_service = ConfigService()
            config = self.config_service.get_config()
            pictures_dir = config.pictures_dir

            self.wallpaper_setter = WallpaperSetter()
            local_service = LocalWallpaperService(pictures_dir=pictures_dir)
            favorites_service = FavoritesService()
            wallhaven_service = WallhavenService()
            thumbnail_cache = ThumbnailCache()

            self.wallhaven_view_model = WallhavenViewModel(
                wallhaven_service=wallhaven_service,
                thumbnail_cache=thumbnail_cache,
            )
            self.wallhaven_view_model.favorites_service = favorites_service
            self.local_view_model = LocalViewModel(
                local_service=local_service,
                wallpaper_setter=self.wallpaper_setter,
                pictures_dir=pictures_dir,
            )
            self.local_view_model.favorites_service = favorites_service
            self.favorites_view_model = FavoritesViewModel(
                favorites_service=favorites_service,
                wallpaper_setter=self.wallpaper_setter,
            )

        self.window = WallPickerWindow(
            application=self,
            local_view_model=self.local_view_model,
            favorites_view_model=self.favorites_view_model,
            wallhaven_view_model=self.wallhaven_view_model,
        )
        self.window.present()
        print("DEBUG: Window presented")


class WallPickerWindow(Adw.ApplicationWindow):
    """Main application window with MVVM architecture."""

    def __init__(
        self,
        application,
        local_view_model,
        favorites_view_model,
        wallhaven_view_model,
    ):
        super().__init__(application=application, title="Wallpicker")
        self.set_default_size(1200, 800)

        self.local_view_model = local_view_model
        self.favorites_view_model = favorites_view_model
        self.wallhaven_view_model = wallhaven_view_model

        self._create_ui()

    def _create_ui(self):
        """Create main UI with tabs."""
        main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        self.set_content(main_box)

        # Header with current wallpaper
        header = Adw.HeaderBar()
        header.set_show_end_title_buttons(False)

        self.current_wallpaper_label = Gtk.Label(label="Current: None")
        header.pack_start(self.current_wallpaper_label)
        main_box.append(header)

        # Tab stack for switching between views
        self.stack = Adw.ViewStack()
        self.stack.set_hexpand(True)
        self.stack.set_vexpand(True)

        # Switcher for tabs
        self.switcher = Adw.ViewSwitcher()
        self.switcher.set_stack(self.stack)

        # Create views
        self.local_view = LocalView(self.local_view_model)
        self.stack.add_titled_with_icon(
            self.local_view,
            name="local",
            title="Local",
            icon_name="folder-symbolic",
        )

        self.wallhaven_view = WallhavenView(self.wallhaven_view_model)
        self.stack.add_titled_with_icon(
            self.wallhaven_view,
            name="wallhaven",
            title="Wallhaven",
            icon_name="globe-symbolic",
        )

        self.favorites_view = FavoritesView(self.favorites_view_model)
        self.stack.add_titled_with_icon(
            self.favorites_view,
            name="favorites",
            title="Favorites",
            icon_name="starred-symbolic",
        )

        main_box.append(self.switcher)
        main_box.append(self.stack)

        # Load initial data
        try:
            self.local_view_model.load_wallpapers()
            self.favorites_view_model.load_favorites()
        except Exception as e:
            print(f"Error loading initial data: {e}")

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
gi.require_version("GdkPixbuf", "2.0")

from gi.repository import Gtk, Adw, GLib, Gdk, Gio, GdkPixbuf
from pathlib import Path
import requests
import threading

from services.wallhaven_service import WallhavenService, Wallpaper
from services.local_service import LocalWallpaperService, LocalWallpaper
from services.wallpaper_setter import WallpaperSetter
from services.favorites_service import FavoritesService


class MainWindow(Adw.Application):
    """Main application window"""

    def __init__(self):
        super().__init__(application_id="com.github.wallpicker")
        self.window = None
        self.wallhaven_service = WallhavenService()
        self.local_service = LocalWallpaperService()
        self.wallpaper_setter = WallpaperSetter()
        self.favorites_service = FavoritesService()

    def do_activate(self):
        if not self.window:
            self.window = WallPickerWindow(self)
        self.window.present()


class WallPickerWindow(Adw.ApplicationWindow):
    """Main window with wallpaper picker UI"""

    def __init__(self, app):
        super().__init__(application=app, title="Wallpaper Picker")
        self.set_default_size(1200, 800)

        # Main box
        main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        self.set_content(main_box)

        # Create header bar with search
        self._create_header_bar(main_box)

        # Create tabbed view
        self._create_tabbed_view(main_box)

        # Load initial data
        GLib.idle_add(self._load_local_wallpapers)

    def _create_header_bar(self, parent):
        """Create header bar with search and refresh button"""
        header = Adw.HeaderBar()

        # Search entry
        self.search_entry = Gtk.SearchEntry(placeholder_text="Search wallpapers...")
        self.search_entry.set_hexpand(True)
        header.pack_start(self.search_entry)

        # Refresh button
        refresh_btn = Gtk.Button(icon_name="view-refresh-symbolic")
        refresh_btn.connect("clicked", self._on_refresh_clicked)
        header.pack_end(refresh_btn)

        parent.append(header)

    def _create_tabbed_view(self, parent):
        """Create tabbed view for Wallhaven and local wallpapers"""
        self.stack = Gtk.Stack()
        self.stack.set_vexpand(True)

        # Wallhaven tab
        self.wallhaven_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        self._create_wallhaven_ui(self.wallhaven_box)

        # Local wallpapers tab
        self.local_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        self._create_local_ui(self.local_box)

        # Favorites tab
        self.favorites_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        self._create_favorites_ui(self.favorites_box)

        # Stack switcher
        switcher = Gtk.StackSwitcher(stack=self.stack, halign=Gtk.Align.CENTER)

        # Add to stack
        self.stack.add_titled(self.wallhaven_box, "wallhaven", "Wallhaven")
        self.stack.add_titled(self.local_box, "local", "Local")
        self.stack.add_titled(self.favorites_box, "favorites", "Favorites")

        parent.append(switcher)
        parent.append(self.stack)

    def _create_wallhaven_ui(self, parent):
        """Create Wallhaven-specific UI"""
        # Filter box
        filter_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)

        # Categories dropdown
        self.categories_combo = Gtk.ComboBoxText()
        self.categories_combo.append_text("All (111)")
        self.categories_combo.append_text("General (100)")
        self.categories_combo.append_text("Anime (010)")
        self.categories_combo.append_text("People (001)")
        self.categories_combo.set_active(0)
        filter_box.append(Gtk.Label(label="Categories:"))
        filter_box.append(self.categories_combo)

        # Sorting dropdown
        self.sorting_combo = Gtk.ComboBoxText()
        for sort in ["date_added", "relevance", "random", "views", "favorites"]:
            self.sorting_combo.append_text(sort)
        self.sorting_combo.set_active(0)
        filter_box.append(Gtk.Label(label="Sort:"))
        filter_box.append(self.sorting_combo)

        # Search button
        search_btn = Gtk.Button(label="Search")
        search_btn.connect("clicked", self._on_wallhaven_search)
        filter_box.append(search_btn)

        parent.append(filter_box)

        # Scroll window for grid
        scroll = Gtk.ScrolledWindow()
        scroll.set_vexpand(True)

        # Grid view
        self.wallhaven_grid = Gtk.GridView()
        self.wallhaven_selection = Gtk.SingleSelection()
        self.wallhaven_selection.set_autoselect(False)

        # Grid flow
        self.wallhaven_grid.set_min_columns(2)
        self.wallhaven_grid.set_max_columns(6)
        self.wallhaven_grid.set_model(self.wallhaven_selection)

        # Factory for wallpaper cards
        factory = Gtk.SignalListItemFactory()
        factory.connect("setup", self._on_wallhaven_item_setup)
        factory.connect("bind", self._on_wallhaven_item_bind)
        factory.connect("unbind", self._on_wallhaven_item_unbind)
        self.wallhaven_grid.set_factory(factory)

        scroll.set_child(self.wallhaven_grid)
        parent.append(scroll)

        # Status bar
        self.wallhaven_status = Gtk.Label(label="Click Search to load wallpapers")
        parent.append(self.wallhaven_status)

    def _create_local_ui(self, parent):
        """Create local wallpapers UI"""
        # Toolbar
        toolbar = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)

        refresh_btn = Gtk.Button(label="Refresh")
        refresh_btn.connect("clicked", self._on_local_refresh)
        toolbar.append(refresh_btn)

        delete_btn = Gtk.Button(icon_name="user-trash-symbolic")
        delete_btn.connect("clicked", self._on_delete_selected)
        toolbar.append(delete_btn)

        parent.append(toolbar)

        # Scroll window
        scroll = Gtk.ScrolledWindow()
        scroll.set_vexpand(True)

        # Grid view
        self.local_grid = Gtk.GridView()
        self.local_selection = Gtk.SingleSelection()
        self.local_selection.set_autoselect(False)

        self.local_grid.set_min_columns(2)
        self.local_grid.set_max_columns(6)
        self.local_grid.set_model(self.local_selection)

        # Factory for local wallpaper cards
        factory = Gtk.SignalListItemFactory()
        factory.connect("setup", self._on_local_item_setup)
        factory.connect("bind", self._on_local_item_bind)
        factory.connect("unbind", self._on_local_item_unbind)
        self.local_grid.set_factory(factory)

        scroll.set_child(self.local_grid)
        parent.append(scroll)

        # Status bar
        self.local_status = Gtk.Label(label="Loading local wallpapers...")
        parent.append(self.local_status)

    def _on_wallhaven_item_setup(self, factory, list_item):
        """Setup widget for wallhaven wallpaper item"""
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        box.set_margin_start(10)
        box.set_margin_end(10)
        box.set_margin_top(10)
        box.set_margin_bottom(10)

        # Image placeholder
        image = Gtk.Image(pixel_size=200)
        image.set_size_request(280, 160)
        image.set_icon_name("image-missing-symbolic")
        box.append(image)

        # Info labels
        resolution = Gtk.Label(label="")
        resolution.set_halign(Gtk.Align.START)
        box.append(resolution)

        category = Gtk.Label(label="")
        category.set_halign(Gtk.Align.START)
        box.append(category)

        # Set as wallpaper button
        set_btn = Gtk.Button(label="Set Wallpaper")
        box.append(set_btn)

        # Download button
        download_btn = Gtk.Button(label="Download")
        box.append(download_btn)

        # Favorite button
        fav_btn = Gtk.Button(icon_name="emblem-favorite-symbolic")
        box.append(fav_btn)

        list_item.set_child(box)

        # Store widgets for bind
        list_item.image = image
        list_item.resolution = resolution
        list_item.category = category
        list_item.set_btn = set_btn
        list_item.download_btn = download_btn
        list_item.fav_btn = fav_btn

    def _on_wallhaven_item_bind(self, factory, list_item):
        """Bind wallhaven wallpaper data to widget"""
        wallpaper = list_item.get_item()
        if not wallpaper:
            return

        item = list_item
        app = Gtk.Application.get_default()

        self._load_thumbnail(item.image, wallpaper.thumbs_large)

        # Set labels
        item.resolution.set_text(f"Resolution: {wallpaper.resolution}")
        item.category.set_text(f"Category: {wallpaper.category}")

        # Connect buttons
        # Disconnect old signals if needed (not easily possible with Gtk.SignalListItemFactory in this simple way,
        # normally we'd subclass or use a controller, but for this demo we'll just reconnect and rely on GC or careful management.
        # However, connecting multiple times is bad. A better way in Python for this simple binding
        # is to check if we already connected or just assume the factory creates fresh widgets per item usually.
        # Actually, reusing list items means we MUST disconnect.
        # For simplicity in this generated code, we assume clean bind/unbind or fresh widgets.
        # Let's use a helper to safe connect if possible, or just standard connect.

        # Check favorite status
        is_fav = app.favorites_service.is_favorite(wallpaper.id)
        if is_fav:
            item.fav_btn.add_css_class("suggested-action")
        else:
            item.fav_btn.remove_css_class("suggested-action")

        item.set_btn.connect("clicked", self._on_set_wallhaven_wallpaper, wallpaper)
        item.download_btn.connect("clicked", self._on_download_wallpaper, wallpaper)
        item.fav_btn.connect(
            "clicked", self._on_toggle_favorite, wallpaper, item.fav_btn
        )

    def _on_wallhaven_item_unbind(self, factory, list_item):
        """Cleanup when item is unbound"""
        pass

    def _create_favorites_ui(self, parent):
        """Create Favorites UI"""
        # Toolbar
        toolbar = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)

        refresh_btn = Gtk.Button(label="Refresh")
        refresh_btn.connect("clicked", self._on_favorites_refresh)
        toolbar.append(refresh_btn)

        parent.append(toolbar)

        # Scroll window
        scroll = Gtk.ScrolledWindow()
        scroll.set_vexpand(True)

        # Grid view
        self.favorites_grid = Gtk.GridView()
        self.favorites_selection = Gtk.SingleSelection()
        self.favorites_selection.set_autoselect(False)

        self.favorites_grid.set_min_columns(2)
        self.favorites_grid.set_max_columns(6)
        self.favorites_grid.set_model(self.favorites_selection)

        # Use same factory setup as wallhaven but without favorite toggle (or with 'remove' button)
        factory = Gtk.SignalListItemFactory()
        factory.connect("setup", self._on_favorite_item_setup)
        factory.connect("bind", self._on_favorite_item_bind)
        self.favorites_grid.set_factory(factory)

        scroll.set_child(self.favorites_grid)
        parent.append(scroll)

        self.favorites_status = Gtk.Label(label="Loading favorites...")
        parent.append(self.favorites_status)

    def _on_favorite_item_setup(self, factory, list_item):
        """Setup widget for favorite item"""
        # Reuse similar layout to wallhaven
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        box.set_margin_start(10)
        box.set_margin_end(10)
        box.set_margin_top(10)
        box.set_margin_bottom(10)

        image = Gtk.Image(pixel_size=200)
        image.set_size_request(280, 160)
        image.set_icon_name("image-missing-symbolic")
        box.append(image)

        info_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        resolution = Gtk.Label(halign=Gtk.Align.START)
        category = Gtk.Label(halign=Gtk.Align.START)
        info_box.append(resolution)
        info_box.append(category)
        box.append(info_box)

        # Actions
        btn_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        set_btn = Gtk.Button(label="Set")
        download_btn = Gtk.Button(label="Download")
        remove_btn = Gtk.Button(icon_name="user-trash-symbolic")

        btn_box.append(set_btn)
        btn_box.append(download_btn)
        btn_box.append(remove_btn)
        box.append(btn_box)

        list_item.set_child(box)

        list_item.image = image
        list_item.resolution = resolution
        list_item.category = category
        list_item.set_btn = set_btn
        list_item.download_btn = download_btn
        list_item.remove_btn = remove_btn

    def _on_favorite_item_bind(self, factory, list_item):
        """Bind favorite data"""
        wallpaper = list_item.get_item()
        if not wallpaper:
            return

        item = list_item
        GLib.idle_add(self._load_thumbnail, item.image, wallpaper.thumbs_large)
        item.resolution.set_text(f"Res: {wallpaper.resolution}")
        item.category.set_text(f"Cat: {wallpaper.category}")

        item.set_btn.connect("clicked", self._on_set_wallhaven_wallpaper, wallpaper)
        item.download_btn.connect("clicked", self._on_download_wallpaper, wallpaper)
        item.remove_btn.connect("clicked", self._on_remove_favorite, wallpaper)

    def _on_toggle_favorite(self, button, wallpaper, btn_widget):
        """Toggle favorite status"""
        app = Gtk.Application.get_default()
        if app.favorites_service.is_favorite(wallpaper.id):
            app.favorites_service.remove_favorite(wallpaper.id)
            btn_widget.remove_css_class("suggested-action")
        else:
            app.favorites_service.add_favorite(wallpaper)
            btn_widget.add_css_class("suggested-action")

    def _on_remove_favorite(self, button, wallpaper):
        """Remove from favorites list"""
        app = Gtk.Application.get_default()
        app.favorites_service.remove_favorite(wallpaper.id)
        self._load_favorites()

    def _on_favorites_refresh(self, button):
        self._load_favorites()

    def _load_favorites(self):
        app = Gtk.Application.get_default()
        wallpapers = app.favorites_service.get_favorites()

        list_store = Gio.ListStore()
        for wp in wallpapers:
            list_store.append(wp)

        self.favorites_selection.set_model(list_store)
        self.favorites_status.set_text(
            f"Favorites: {len(wallpapers)}" if wallpapers else "No favorites yet"
        )

    def _on_refresh_clicked(self, button):
        """Refresh current view"""
        current_page = self.stack.get_visible_child_name()
        if current_page == "wallhaven":
            self._on_wallhaven_search(button)
        elif current_page == "local":
            self._on_local_refresh(button)
        elif current_page == "favorites":
            self._load_favorites()

    def _on_wallhaven_search(self, button):
        query = self.search_entry.get_text()
        categories_map = {
            0: "111",
            1: "100",
            2: "010",
            3: "001",
        }
        categories = categories_map[self.categories_combo.get_active()]
        sorting = self.sorting_combo.get_active_text()

        self.wallhaven_status.set_text("Searching...")
        app = Gtk.Application.get_default()

        def do_search():
            result = app.wallhaven_service.search(
                q=query,
                categories=categories,
                purity="100",
                sorting=sorting,
            )
            GLib.idle_add(on_search_done, result)

        def on_search_done(result):
            if "error" in result:
                self.wallhaven_status.set_text(f"Error: {result['error']}")
                return

            wallpapers = app.wallhaven_service.parse_wallpapers(result.get("data", []))

            list_store = Gio.ListStore()
            for wp in wallpapers:
                list_store.append(wp)

            self.wallhaven_selection.set_model(list_store)
            self.wallhaven_status.set_text(f"Found {len(wallpapers)} wallpapers")

        threading.Thread(target=do_search, daemon=True).start()

    def _load_thumbnail(self, image_widget, url):
        def do_load():
            try:
                response = requests.get(url, timeout=10)
                if response.status_code == 200:
                    GLib.idle_add(set_image, response.content)
            except Exception as e:
                print(f"Error loading thumbnail: {e}")

        def set_image(data):
            try:
                texture = Gdk.Texture.new_from_bytes(GLib.Bytes.new(data))
                image_widget.set_from_paintable(texture)
            except Exception:
                pass

        threading.Thread(target=do_load, daemon=True).start()

    def _on_set_wallhaven_wallpaper(self, button, wallpaper):
        app = Gtk.Application.get_default()

        cache_dir = Path.home() / ".cache" / "wallpaper"
        cache_dir.mkdir(parents=True, exist_ok=True)
        ext = wallpaper.path.split(".")[-1]
        dest_path = cache_dir / f"{wallpaper.id}.{ext}"

        self.wallhaven_status.set_text(f"Downloading {wallpaper.id}...")

        def do_download():
            success = app.wallhaven_service.download(wallpaper.path, dest_path, None)
            GLib.idle_add(on_download_done, success)

        def on_download_done(success):
            if success:
                if app.wallpaper_setter.set_wallpaper(dest_path):
                    self.wallhaven_status.set_text(
                        f"Wallpaper set: {wallpaper.resolution}"
                    )
                else:
                    self.wallhaven_status.set_text("Failed to set wallpaper")
            else:
                self.wallhaven_status.set_text("Download failed")

        threading.Thread(target=do_download, daemon=True).start()

    def _on_download_wallpaper(self, button, wallpaper):
        app = Gtk.Application.get_default()

        wallpapers_dir = Path.home() / ".local/share/wallpicker/wallpapers"
        wallpapers_dir.mkdir(parents=True, exist_ok=True)
        ext = wallpaper.path.split(".")[-1]
        dest_path = wallpapers_dir / f"{wallpaper.id}.{ext}"

        self.wallhaven_status.set_text(f"Downloading {wallpaper.id}...")

        def do_download():
            success = app.wallhaven_service.download(wallpaper.path, dest_path, None)
            GLib.idle_add(on_download_done, success)

        def on_download_done(success):
            if success:
                self.wallhaven_status.set_text(f"Saved to {dest_path}")
            else:
                self.wallhaven_status.set_text("Download failed")

        threading.Thread(target=do_download, daemon=True).start()

    def _load_local_wallpapers(self):
        """Load local wallpapers into grid"""
        app = Gtk.Application.get_default()
        wallpapers = app.local_service.get_wallpapers()

        list_store = Gio.ListStore()
        for wp in wallpapers:
            list_store.append(wp)

        self.local_selection.set_model(list_store)
        self.local_status.set_text(f"{len(wallpapers)} local wallpapers")

    def _on_local_refresh(self, button):
        """Refresh local wallpapers list"""
        self._load_local_wallpapers()

    def _on_delete_selected(self, button):
        """Delete selected local wallpaper"""
        selected = self.local_selection.get_selected_item()
        if not selected:
            return

        app = Gtk.Application.get_default()
        if app.local_service.delete_wallpaper(selected.path):
            self._load_local_wallpapers()
            self.local_status.set_text("Wallpaper deleted")
        else:
            self.local_status.set_text("Failed to delete wallpaper")

    def _on_local_item_setup(self, factory, list_item):
        """Setup widget for local wallpaper item"""
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        box.set_margin_start(10)
        box.set_margin_end(10)
        box.set_margin_top(10)
        box.set_margin_bottom(10)

        # Image
        image = Gtk.Image(pixel_size=200)
        image.set_size_request(280, 160)
        image.set_from_icon_name("image-missing-symbolic")
        box.append(image)

        # Info labels
        filename = Gtk.Label(label="")
        filename.set_halign(Gtk.Align.START)
        box.append(filename)

        size = Gtk.Label(label="")
        size.set_halign(Gtk.Align.START)
        box.append(size)

        # Set wallpaper button
        set_btn = Gtk.Button(label="Set Wallpaper")
        box.append(set_btn)

        list_item.set_child(box)

        # Store widgets for bind
        list_item.image = image
        list_item.filename = filename
        list_item.size = size
        list_item.set_btn = set_btn

    def _on_local_item_bind(self, factory, list_item):
        wallpaper = list_item.get_item()
        if not wallpaper:
            return

        item = list_item
        self._load_local_thumbnail(item.image, wallpaper.path)

        item.filename.set_text(wallpaper.filename)
        size_mb = wallpaper.size / (1024 * 1024)
        item.size.set_text(f"Size: {size_mb:.2f} MB")

        item.set_btn.connect("clicked", self._on_set_local_wallpaper, wallpaper)

    def _on_local_item_unbind(self, factory, list_item):
        pass

    def _load_local_thumbnail(self, image_widget, path):
        def do_load():
            try:
                pixbuf = GdkPixbuf.Pixbuf.new_from_file_at_scale(
                    str(path), 280, 160, True
                )
                GLib.idle_add(set_image, pixbuf)
            except Exception:
                pass

        def set_image(pixbuf):
            try:
                texture = Gdk.Texture.new_for_pixbuf(pixbuf)
                image_widget.set_from_paintable(texture)
            except Exception:
                pass

        threading.Thread(target=do_load, daemon=True).start()

    def _on_set_local_wallpaper(self, button, wallpaper):
        """Set local wallpaper"""
        app = Gtk.Application.get_default()

        if app.wallpaper_setter.set_wallpaper(wallpaper.path):
            self.local_status.set_text(f"Wallpaper set: {wallpaper.filename}")
        else:
            self.local_status.set_text("Failed to set wallpaper")

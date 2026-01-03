import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
gi.require_version("GdkPixbuf", "2.0")

from gi.repository import Gtk, Adw, GLib, Gdk, Gio, GdkPixbuf
from pathlib import Path
import requests
import threading
import os

from services.wallhaven_service import WallhavenService, Wallpaper
from services.local_service import LocalWallpaperService, LocalWallpaper
from services.wallpaper_setter import WallpaperSetter
from services.favorites_service import FavoritesService


class MainWindow(Adw.Application):
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
    def __init__(self, app):
        super().__init__(application=app, title="Wallpicker")
        self.set_default_size(1200, 800)
        self.current_wallpaper_path = self._get_current_wallpaper()

        main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        self.set_content(main_box)

        self._setup_css()
        self._create_header_bar(main_box)
        self._create_tabbed_view(main_box)

        GLib.idle_add(self._load_local_wallpapers)
        GLib.idle_add(self._load_favorites)

    def _get_current_wallpaper(self):
        symlink = Path.home() / ".cache" / "current_wallpaper"
        if symlink.exists() and symlink.is_symlink():
            return str(symlink.resolve())
        return None

    def _setup_css(self):
        css = b"""
        .wallpaper-card {
            background: @card_bg_color;
            border-radius: 12px;
            padding: 8px;
            transition: all 200ms ease;
        }
        .wallpaper-card:hover {
            background: @card_shade_color;
            box-shadow: 0 4px 12px rgba(0,0,0,0.15);
        }
        .wallpaper-image {
            border-radius: 8px;
            background: @window_bg_color;
        }
        .current-wallpaper {
            border: 3px solid @accent_bg_color;
            box-shadow: 0 0 12px @accent_bg_color;
        }
        .action-button {
            border-radius: 8px;
            padding: 6px 12px;
        }
        .destructive-action {
            background: @error_bg_color;
            color: @error_fg_color;
        }
        .suggested-action {
            background: @accent_bg_color;
            color: @accent_fg_color;
        }
        .status-bar {
            padding: 8px 16px;
            background: @headerbar_bg_color;
            border-top: 1px solid @borders;
        }
        .filter-bar {
            padding: 12px;
            background: @headerbar_bg_color;
            border-bottom: 1px solid @borders;
        }
        .tab-toolbar {
            padding: 8px 12px;
            background: alpha(@card_bg_color, 0.5);
        }
        """
        provider = Gtk.CssProvider()
        provider.load_from_data(css)
        Gtk.StyleContext.add_provider_for_display(
            Gdk.Display.get_default(), provider, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
        )

    def _create_header_bar(self, parent):
        header = Adw.HeaderBar()
        header.set_title_widget(Gtk.Label(label="Wallpicker", css_classes=["title"]))

        self.search_entry = Gtk.SearchEntry(placeholder_text="Search Wallhaven...")
        self.search_entry.set_hexpand(True)
        self.search_entry.set_max_width_chars(40)
        header.pack_start(self.search_entry)

        refresh_btn = Gtk.Button(
            icon_name="view-refresh-symbolic", tooltip_text="Refresh"
        )
        refresh_btn.connect("clicked", self._on_refresh_clicked)
        header.pack_end(refresh_btn)

        parent.append(header)

    def _create_tabbed_view(self, parent):
        self.stack = Gtk.Stack()
        self.stack.set_vexpand(True)
        self.stack.set_transition_type(Gtk.StackTransitionType.SLIDE_LEFT_RIGHT)
        self.stack.set_transition_duration(200)

        self.local_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        self._create_local_ui(self.local_box)

        self.wallhaven_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        self._create_wallhaven_ui(self.wallhaven_box)

        self.favorites_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        self._create_favorites_ui(self.favorites_box)

        self.stack.add_titled(self.local_box, "local", "Local")
        self.stack.add_titled(self.wallhaven_box, "wallhaven", "Wallhaven")
        self.stack.add_titled(self.favorites_box, "favorites", "Favorites")

        switcher = Gtk.StackSwitcher(stack=self.stack, halign=Gtk.Align.CENTER)
        switcher.set_margin_top(8)
        switcher.set_margin_bottom(8)

        parent.append(switcher)
        parent.append(self.stack)

    def _create_wallhaven_ui(self, parent):
        filter_box = Gtk.Box(
            orientation=Gtk.Orientation.HORIZONTAL,
            spacing=12,
            css_classes=["filter-bar"],
        )

        cat_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        cat_box.append(Gtk.Label(label="Category:"))
        self.categories_combo = Gtk.ComboBoxText()
        for cat in ["All", "General", "Anime", "People"]:
            self.categories_combo.append_text(cat)
        self.categories_combo.set_active(0)
        cat_box.append(self.categories_combo)
        filter_box.append(cat_box)

        sort_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        sort_box.append(Gtk.Label(label="Sort:"))
        self.sorting_combo = Gtk.ComboBoxText()
        for sort in [
            "date_added",
            "relevance",
            "random",
            "views",
            "favorites",
            "toplist",
        ]:
            self.sorting_combo.append_text(sort)
        self.sorting_combo.set_active(0)
        sort_box.append(self.sorting_combo)
        filter_box.append(sort_box)

        search_btn = Gtk.Button(label="Search", css_classes=["suggested-action"])
        search_btn.connect("clicked", self._on_wallhaven_search)
        filter_box.append(search_btn)

        parent.append(filter_box)

        scroll = Gtk.ScrolledWindow()
        scroll.set_vexpand(True)

        self.wallhaven_grid = Gtk.GridView()
        self.wallhaven_grid.set_min_columns(2)
        self.wallhaven_grid.set_max_columns(5)
        self.wallhaven_selection = Gtk.SingleSelection()
        self.wallhaven_selection.set_autoselect(False)
        self.wallhaven_grid.set_model(self.wallhaven_selection)

        factory = Gtk.SignalListItemFactory()
        factory.connect("setup", self._on_wallhaven_item_setup)
        factory.connect("bind", self._on_wallhaven_item_bind)
        self.wallhaven_grid.set_factory(factory)

        scroll.set_child(self.wallhaven_grid)
        parent.append(scroll)

        self.wallhaven_status = Gtk.Label(
            label="Enter search terms and click Search", css_classes=["status-bar"]
        )
        parent.append(self.wallhaven_status)

    def _create_local_ui(self, parent):
        toolbar = Gtk.Box(
            orientation=Gtk.Orientation.HORIZONTAL,
            spacing=8,
            css_classes=["tab-toolbar"],
        )

        refresh_btn = Gtk.Button(
            icon_name="view-refresh-symbolic", tooltip_text="Refresh"
        )
        refresh_btn.connect("clicked", self._on_local_refresh)
        toolbar.append(refresh_btn)

        toolbar.append(Gtk.Separator(orientation=Gtk.Orientation.VERTICAL))

        fav_btn = Gtk.Button(
            icon_name="emblem-favorite-symbolic", tooltip_text="Add to Favorites"
        )
        fav_btn.connect("clicked", self._on_add_local_to_favorites)
        toolbar.append(fav_btn)

        toolbar.append(Gtk.Separator(orientation=Gtk.Orientation.VERTICAL))

        trash_btn = Gtk.Button(
            icon_name="user-trash-symbolic", tooltip_text="Move to Trash"
        )
        trash_btn.connect("clicked", self._on_delete_selected)
        toolbar.append(trash_btn)

        delete_btn = Gtk.Button(
            label="Delete Forever",
            css_classes=["destructive-action"],
            tooltip_text="Permanently delete",
        )
        delete_btn.connect("clicked", self._on_delete_permanently)
        toolbar.append(delete_btn)

        parent.append(toolbar)

        scroll = Gtk.ScrolledWindow()
        scroll.set_vexpand(True)

        self.local_grid = Gtk.GridView()
        self.local_grid.set_min_columns(2)
        self.local_grid.set_max_columns(5)
        self.local_selection = Gtk.SingleSelection()
        self.local_selection.set_autoselect(False)
        self.local_grid.set_model(self.local_selection)

        factory = Gtk.SignalListItemFactory()
        factory.connect("setup", self._on_local_item_setup)
        factory.connect("bind", self._on_local_item_bind)
        self.local_grid.set_factory(factory)

        scroll.set_child(self.local_grid)
        parent.append(scroll)

        self.local_status = Gtk.Label(label="Loading...", css_classes=["status-bar"])
        parent.append(self.local_status)

    def _create_favorites_ui(self, parent):
        toolbar = Gtk.Box(
            orientation=Gtk.Orientation.HORIZONTAL,
            spacing=8,
            css_classes=["tab-toolbar"],
        )

        refresh_btn = Gtk.Button(
            icon_name="view-refresh-symbolic", tooltip_text="Refresh"
        )
        refresh_btn.connect("clicked", self._on_favorites_refresh)
        toolbar.append(refresh_btn)

        parent.append(toolbar)

        scroll = Gtk.ScrolledWindow()
        scroll.set_vexpand(True)

        self.favorites_grid = Gtk.GridView()
        self.favorites_grid.set_min_columns(2)
        self.favorites_grid.set_max_columns(5)
        self.favorites_selection = Gtk.SingleSelection()
        self.favorites_selection.set_autoselect(False)
        self.favorites_grid.set_model(self.favorites_selection)

        factory = Gtk.SignalListItemFactory()
        factory.connect("setup", self._on_favorite_item_setup)
        factory.connect("bind", self._on_favorite_item_bind)
        self.favorites_grid.set_factory(factory)

        scroll.set_child(self.favorites_grid)
        parent.append(scroll)

        self.favorites_status = Gtk.Label(
            label="Loading...", css_classes=["status-bar"]
        )
        parent.append(self.favorites_status)

    def _on_wallhaven_item_setup(self, factory, list_item):
        card = Gtk.Box(
            orientation=Gtk.Orientation.VERTICAL,
            spacing=8,
            css_classes=["wallpaper-card"],
        )
        card.set_margin_start(8)
        card.set_margin_end(8)
        card.set_margin_top(8)
        card.set_margin_bottom(8)

        image = Gtk.Image()
        image.set_size_request(300, 180)
        image.add_css_class("wallpaper-image")
        card.append(image)

        info = Gtk.Label(label="", halign=Gtk.Align.START, css_classes=["dim-label"])
        card.append(info)

        btn_box = Gtk.Box(
            orientation=Gtk.Orientation.HORIZONTAL, spacing=6, homogeneous=True
        )

        set_btn = Gtk.Button(
            label="Set", css_classes=["action-button", "suggested-action"]
        )
        download_btn = Gtk.Button(label="Save", css_classes=["action-button"])
        fav_btn = Gtk.Button(
            icon_name="emblem-favorite-symbolic", css_classes=["action-button"]
        )

        btn_box.append(set_btn)
        btn_box.append(download_btn)
        btn_box.append(fav_btn)
        card.append(btn_box)

        list_item.set_child(card)
        list_item.image = image
        list_item.info = info
        list_item.set_btn = set_btn
        list_item.download_btn = download_btn
        list_item.fav_btn = fav_btn

    def _on_wallhaven_item_bind(self, factory, list_item):
        wallpaper = list_item.get_item()
        if not wallpaper:
            return

        self._load_thumbnail(list_item.image, wallpaper.thumbs_large)
        list_item.info.set_text(f"{wallpaper.resolution} • {wallpaper.category}")

        app = Gtk.Application.get_default()
        is_fav = app.favorites_service.is_favorite(wallpaper.id)
        if is_fav:
            list_item.fav_btn.add_css_class("suggested-action")
        else:
            list_item.fav_btn.remove_css_class("suggested-action")

        list_item.set_btn.connect(
            "clicked", self._on_set_wallhaven_wallpaper, wallpaper
        )
        list_item.download_btn.connect(
            "clicked", self._on_download_wallpaper, wallpaper
        )
        list_item.fav_btn.connect(
            "clicked", self._on_toggle_favorite, wallpaper, list_item.fav_btn
        )

    def _on_favorite_item_setup(self, factory, list_item):
        card = Gtk.Box(
            orientation=Gtk.Orientation.VERTICAL,
            spacing=8,
            css_classes=["wallpaper-card"],
        )
        card.set_margin_start(8)
        card.set_margin_end(8)
        card.set_margin_top(8)
        card.set_margin_bottom(8)

        image = Gtk.Image()
        image.set_size_request(300, 180)
        image.add_css_class("wallpaper-image")
        card.append(image)

        info = Gtk.Label(label="", halign=Gtk.Align.START, css_classes=["dim-label"])
        card.append(info)

        btn_box = Gtk.Box(
            orientation=Gtk.Orientation.HORIZONTAL, spacing=6, homogeneous=True
        )

        set_btn = Gtk.Button(
            label="Set", css_classes=["action-button", "suggested-action"]
        )
        download_btn = Gtk.Button(label="Save", css_classes=["action-button"])
        remove_btn = Gtk.Button(
            icon_name="user-trash-symbolic",
            css_classes=["action-button", "destructive-action"],
        )

        btn_box.append(set_btn)
        btn_box.append(download_btn)
        btn_box.append(remove_btn)
        card.append(btn_box)

        list_item.set_child(card)
        list_item.image = image
        list_item.info = info
        list_item.set_btn = set_btn
        list_item.download_btn = download_btn
        list_item.remove_btn = remove_btn

    def _on_favorite_item_bind(self, factory, list_item):
        wallpaper = list_item.get_item()
        if not wallpaper:
            return

        self._load_thumbnail(list_item.image, wallpaper.thumbs_large)
        list_item.info.set_text(f"{wallpaper.resolution} • {wallpaper.category}")

        list_item.set_btn.connect(
            "clicked", self._on_set_wallhaven_wallpaper, wallpaper
        )
        list_item.download_btn.connect(
            "clicked", self._on_download_wallpaper, wallpaper
        )
        list_item.remove_btn.connect("clicked", self._on_remove_favorite, wallpaper)

    def _on_toggle_favorite(self, button, wallpaper, btn_widget):
        app = Gtk.Application.get_default()
        if app.favorites_service.is_favorite(wallpaper.id):
            app.favorites_service.remove_favorite(wallpaper.id)
            btn_widget.remove_css_class("suggested-action")
        else:
            app.favorites_service.add_favorite(wallpaper)
            btn_widget.add_css_class("suggested-action")

    def _on_remove_favorite(self, button, wallpaper):
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
            f"{len(wallpapers)} favorites" if wallpapers else "No favorites yet"
        )

    def _on_refresh_clicked(self, button):
        current_page = self.stack.get_visible_child_name()
        if current_page == "wallhaven":
            self._on_wallhaven_search(button)
        elif current_page == "local":
            self._on_local_refresh(button)
        elif current_page == "favorites":
            self._load_favorites()

    def _on_wallhaven_search(self, button):
        query = self.search_entry.get_text()
        categories_map = {0: "111", 1: "100", 2: "010", 3: "001"}
        categories = categories_map[self.categories_combo.get_active()]
        sorting = self.sorting_combo.get_active_text()

        self.wallhaven_status.set_text("Searching...")
        app = Gtk.Application.get_default()

        def do_search():
            result = app.wallhaven_service.search(
                q=query, categories=categories, purity="100", sorting=sorting
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
            except Exception:
                pass

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

        self.wallhaven_status.set_text(f"Downloading...")

        def do_download():
            success = app.wallhaven_service.download(wallpaper.path, dest_path, None)
            GLib.idle_add(on_download_done, success)

        def on_download_done(success):
            if success and app.wallpaper_setter.set_wallpaper(dest_path):
                self.current_wallpaper_path = str(dest_path)
                self.wallhaven_status.set_text(f"Wallpaper set!")
            else:
                self.wallhaven_status.set_text("Failed to set wallpaper")

        threading.Thread(target=do_download, daemon=True).start()

    def _on_download_wallpaper(self, button, wallpaper):
        app = Gtk.Application.get_default()
        wallpapers_dir = app.local_service.wallpapers_dir
        wallpapers_dir.mkdir(parents=True, exist_ok=True)
        ext = wallpaper.path.split(".")[-1]
        dest_path = wallpapers_dir / f"{wallpaper.id}.{ext}"

        self.wallhaven_status.set_text(f"Downloading to library...")

        def do_download():
            success = app.wallhaven_service.download(wallpaper.path, dest_path, None)
            GLib.idle_add(on_download_done, success)

        def on_download_done(success):
            if success:
                self.wallhaven_status.set_text(f"Saved to {dest_path.name}")
                self._load_local_wallpapers()
            else:
                self.wallhaven_status.set_text("Download failed")

        threading.Thread(target=do_download, daemon=True).start()

    def _load_local_wallpapers(self):
        app = Gtk.Application.get_default()
        wallpapers = app.local_service.get_wallpapers()

        list_store = Gio.ListStore()
        selected_idx = None

        for i, wp in enumerate(wallpapers):
            list_store.append(wp)
            if (
                self.current_wallpaper_path
                and str(wp.path) == self.current_wallpaper_path
            ):
                selected_idx = i

        self.local_selection.set_model(list_store)

        if selected_idx is not None:
            self.local_selection.set_selected(selected_idx)

        self.local_status.set_text(f"{len(wallpapers)} wallpapers")

    def _on_local_refresh(self, button):
        self.current_wallpaper_path = self._get_current_wallpaper()
        self._load_local_wallpapers()

    def _on_add_local_to_favorites(self, button):
        selected = self.local_selection.get_selected_item()
        if not selected:
            self.local_status.set_text("Select a wallpaper first")
            return

        app = Gtk.Application.get_default()
        local_wp = Wallpaper(
            id=f"local_{selected.filename}",
            url=f"file://{selected.path}",
            path=str(selected.path),
            thumbs_large=f"file://{selected.path}",
            thumbs_small=f"file://{selected.path}",
            resolution=f"{selected.size} bytes",
            category="local",
            purity="sfw",
            colors=[],
            file_size=selected.size,
        )
        app.favorites_service.add_favorite(local_wp)
        self.local_status.set_text(f"Added {selected.filename} to favorites")

    def _on_delete_selected(self, button):
        selected = self.local_selection.get_selected_item()
        if not selected:
            self.local_status.set_text("Select a wallpaper first")
            return

        app = Gtk.Application.get_default()
        if app.local_service.delete_wallpaper(selected.path):
            self._load_local_wallpapers()
            self.local_status.set_text("Moved to trash")
        else:
            self.local_status.set_text("Failed to delete")

    def _on_delete_permanently(self, button):
        selected = self.local_selection.get_selected_item()
        if not selected:
            self.local_status.set_text("Select a wallpaper first")
            return

        try:
            os.remove(selected.path)
            self._load_local_wallpapers()
            self.local_status.set_text("Permanently deleted")
        except Exception as e:
            self.local_status.set_text(f"Failed: {e}")

    def _on_local_item_setup(self, factory, list_item):
        card = Gtk.Box(
            orientation=Gtk.Orientation.VERTICAL,
            spacing=8,
            css_classes=["wallpaper-card"],
        )
        card.set_margin_start(8)
        card.set_margin_end(8)
        card.set_margin_top(8)
        card.set_margin_bottom(8)

        overlay = Gtk.Overlay()
        image = Gtk.Image()
        image.set_size_request(300, 180)
        image.add_css_class("wallpaper-image")
        overlay.set_child(image)

        current_badge = Gtk.Label(
            label="CURRENT", halign=Gtk.Align.END, valign=Gtk.Align.START
        )
        current_badge.add_css_class("suggested-action")
        current_badge.set_margin_top(8)
        current_badge.set_margin_end(8)
        current_badge.set_visible(False)
        overlay.add_overlay(current_badge)

        card.append(overlay)

        info = Gtk.Label(
            label="", halign=Gtk.Align.START, ellipsize=3, max_width_chars=30
        )
        card.append(info)

        size_label = Gtk.Label(
            label="", halign=Gtk.Align.START, css_classes=["dim-label"]
        )
        card.append(size_label)

        set_btn = Gtk.Button(
            label="Set Wallpaper", css_classes=["action-button", "suggested-action"]
        )
        card.append(set_btn)

        list_item.set_child(card)
        list_item.image = image
        list_item.info = info
        list_item.size_label = size_label
        list_item.set_btn = set_btn
        list_item.current_badge = current_badge
        list_item.card = card

    def _on_local_item_bind(self, factory, list_item):
        wallpaper = list_item.get_item()
        if not wallpaper:
            return

        self._load_local_thumbnail(list_item.image, wallpaper.path)
        list_item.info.set_text(wallpaper.filename)
        size_mb = wallpaper.size / (1024 * 1024)
        list_item.size_label.set_text(f"{size_mb:.1f} MB")

        is_current = (
            self.current_wallpaper_path
            and str(wallpaper.path) == self.current_wallpaper_path
        )
        list_item.current_badge.set_visible(is_current)
        if is_current:
            list_item.image.add_css_class("current-wallpaper")
        else:
            list_item.image.remove_css_class("current-wallpaper")

        list_item.set_btn.connect("clicked", self._on_set_local_wallpaper, wallpaper)

    def _load_local_thumbnail(self, image_widget, path):
        def do_load():
            try:
                pixbuf = GdkPixbuf.Pixbuf.new_from_file_at_scale(
                    str(path), 300, 180, True
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
        app = Gtk.Application.get_default()
        if app.wallpaper_setter.set_wallpaper(wallpaper.path):
            self.current_wallpaper_path = str(wallpaper.path)
            self.local_status.set_text(f"Set: {wallpaper.filename}")
            self._load_local_wallpapers()
        else:
            self.local_status.set_text("Failed to set wallpaper")

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
from services.thumbnail_cache import ThumbnailCache
from services.config_service import ConfigService


class MainWindow(Adw.Application):
    def __init__(self):
        super().__init__(application_id="com.github.wallpicker")
        self.window = None
        self.config = ConfigService()

        api_key = self.config.get("wallhaven_api_key")
        self.wallhaven_service = WallhavenService(api_key=api_key)

        local_dir = self.config.get("local_wallpapers_dir")
        if local_dir:
            local_dir = Path(local_dir)
        self.local_service = LocalWallpaperService(pictures_dir=local_dir)

        self.wallpaper_setter = WallpaperSetter()
        self.favorites_service = FavoritesService()
        self.thumbnail_cache = ThumbnailCache()

    def do_activate(self):
        if not self.window:
            self.window = WallPickerWindow(self)
        self.window.present()


class WallPickerWindow(Adw.ApplicationWindow):
    def __init__(self, app):
        super().__init__(application=app, title="Wallpicker")
        self.set_default_size(1200, 800)
        self.current_wallpaper_path = self._get_current_wallpaper()
        self.search_changed_timer = None
        self.wallhaven_current_page = 1
        self.wallhaven_total_pages = 1
        self.wallhaven_last_search_params = None
        self.wallhaven_current_page = 1
        self.wallhaven_total_pages = 1
        self.wallhaven_last_search_params = None

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
            padding: 6px;
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
            border-radius: 6px;
            min-height: 32px;
            min-width: 32px;
        }
        .destructive-action {
            background: @error_bg_color;
            color: @error_fg_color;
        }
        .suggested-action {
            background: @accent_bg_color;
            color: @accent_fg_color;
        }
        .favorite-icon {
            color: #ffd700;
        }
        .download-icon {
            color: #4caf50;
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
        .current-badge {
            background: @accent_bg_color;
            color: @accent_fg_color;
            border-radius: 4px;
            padding: 2px 8px;
            font-size: 10px;
            font-weight: bold;
        }
        .action-button:hover {
            background: shade(@card_bg_color, 1.1);
            transform: scale(1.02);
        }
        .action-button:active {
            background: shade(@card_bg_color, 0.9);
            transform: scale(0.98);
        }
        .suggested-action:hover {
            background: shade(@accent_bg_color, 1.1);
            transform: scale(1.02);
        }
        .suggested-action:active {
            background: shade(@accent_bg_color, 0.9);
            transform: scale(0.98);
        }
        .destructive-action:hover {
            background: shade(@error_bg_color, 1.1);
            transform: scale(1.02);
        }
        .destructive-action:active {
            background: shade(@error_bg_color, 0.9);
            transform: scale(0.98);
        }
        .favorite-icon {
            color: #FFD700;
        }
        .download-icon {
            color: #4CAF50;
        }
        """
        provider = Gtk.CssProvider()
        provider.load_from_data(css)
        Gtk.StyleContext.add_provider_for_display(
            Gdk.Display.get_default(), provider, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
        )

    def _send_notification(self, title, body):
        notification = Gio.Notification.new(title)
        notification.set_body(body)
        self.get_application().send_notification(None, notification)

    def _create_header_bar(self, parent):
        header = Adw.HeaderBar()
        header.set_title_widget(Gtk.Label(label="Wallpicker", css_classes=["title"]))

        self.search_entry = Gtk.SearchEntry(
            placeholder_text="Search local wallpapers..."
        )
        self.search_entry.set_hexpand(True)
        self.search_entry.set_max_width_chars(40)
        self.search_entry.connect("search-changed", self._on_search_changed)
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

        self.stack.connect("notify::visible-child", self._on_tab_changed)

    def _on_tab_changed(self, stack, pspec):
        visible_child = stack.get_visible_child()
        if visible_child == self.wallhaven_box:
            self.search_entry.set_placeholder_text("Search Wallhaven...")
            self.sorting_combo.set_active(5)
            self.categories_combo.set_active(1)
            self._on_wallhaven_search(None)
        elif visible_child == self.local_box:
            self.search_entry.set_placeholder_text("Search local images...")
        elif visible_child == self.favorites_box:
            self.search_entry.set_placeholder_text("Search favorites...")
            self._load_favorites()

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

        search_btn = Gtk.Button(
            icon_name="system-search-symbolic", css_classes=["suggested-action"]
        )
        search_btn.connect("clicked", self._on_wallhaven_search)
        filter_box.append(search_btn)

        spacer = Gtk.Label()
        spacer.set_hexpand(True)
        filter_box.append(spacer)

        prev_btn = Gtk.Button(
            icon_name="go-previous-symbolic", tooltip_text="Previous page"
        )
        prev_btn.connect("clicked", self._on_wallhaven_prev_page)
        prev_btn.set_sensitive(False)
        self.wallhaven_prev_btn = prev_btn

        next_btn = Gtk.Button(icon_name="go-next-symbolic", tooltip_text="Next page")
        next_btn.connect("clicked", self._on_wallhaven_next_page)
        next_btn.set_sensitive(False)
        self.wallhaven_next_btn = next_btn

        filter_box.append(prev_btn)
        filter_box.append(next_btn)

        parent.append(filter_box)

        scroll = Gtk.ScrolledWindow()
        scroll.set_vexpand(True)

        self.wallhaven_grid = Gtk.GridView()
        self.wallhaven_grid.set_min_columns(2)
        self.wallhaven_grid.set_max_columns(4)
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
        scroll = Gtk.ScrolledWindow()
        scroll.set_vexpand(True)

        self.local_grid = Gtk.GridView()
        self.local_grid.set_min_columns(2)
        self.local_grid.set_max_columns(4)
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
        scroll = Gtk.ScrolledWindow()
        scroll.set_vexpand(True)

        self.favorites_grid = Gtk.GridView()
        self.favorites_grid.set_min_columns(2)
        self.favorites_grid.set_max_columns(4)
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
            spacing=6,
            css_classes=["wallpaper-card"],
        )
        card.set_margin_start(6)
        card.set_margin_end(6)
        card.set_margin_top(6)
        card.set_margin_bottom(6)

        overlay = Gtk.Overlay()
        image = Gtk.Picture()
        image.set_size_request(-1, 220)
        image.set_content_fit(Gtk.ContentFit.COVER)
        image.add_css_class("wallpaper-image")
        overlay.set_child(image)

        click_gesture = Gtk.GestureClick()
        click_gesture.set_button(1)
        click_gesture.set_propagation_phase(Gtk.PropagationPhase.CAPTURE)
        click_gesture.connect("pressed", self._on_wallhaven_image_click, list_item)
        image.add_controller(click_gesture)
        card.append(overlay)

        info = Gtk.Label(label="", halign=Gtk.Align.START, css_classes=["dim-label"])
        info.set_ellipsize(3)
        card.append(info)

        btn_box = Gtk.Box(
            orientation=Gtk.Orientation.HORIZONTAL, spacing=6, homogeneous=True
        )

        set_btn = Gtk.Button(
            icon_name="emblem-ok-symbolic",
            tooltip_text="Set as Wallpaper",
            css_classes=["action-button", "suggested-action"],
        )
        download_btn = Gtk.Button(
            icon_name="folder-download-symbolic",
            tooltip_text="Save to Library",
            css_classes=["action-button", "download-icon"],
        )
        fav_btn = Gtk.Button(
            icon_name="starred-symbolic",
            tooltip_text="Add to Favorites",
            css_classes=["action-button", "favorite-icon"],
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
            list_item.fav_btn.set_icon_name("starred-symbolic")
        else:
            list_item.fav_btn.set_icon_name("non-starred-symbolic")

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
            spacing=6,
            css_classes=["wallpaper-card"],
        )
        card.set_margin_start(6)
        card.set_margin_end(6)
        card.set_margin_top(6)
        card.set_margin_bottom(6)

        overlay = Gtk.Overlay()
        image = Gtk.Picture()
        image.set_size_request(-1, 220)
        image.set_content_fit(Gtk.ContentFit.COVER)
        image.add_css_class("wallpaper-image")
        overlay.set_child(image)

        click_gesture = Gtk.GestureClick()
        click_gesture.set_button(1)
        click_gesture.set_propagation_phase(Gtk.PropagationPhase.CAPTURE)
        click_gesture.connect("pressed", self._on_favorite_image_click, list_item)
        image.add_controller(click_gesture)
        card.append(overlay)

        info = Gtk.Label(label="", halign=Gtk.Align.START, css_classes=["dim-label"])
        info.set_ellipsize(3)
        card.append(info)

        btn_box = Gtk.Box(
            orientation=Gtk.Orientation.HORIZONTAL, spacing=6, homogeneous=True
        )

        set_btn = Gtk.Button(
            icon_name="emblem-ok-symbolic",
            tooltip_text="Set as Wallpaper",
            css_classes=["action-button", "suggested-action"],
        )
        remove_btn = Gtk.Button(
            icon_name="user-trash-symbolic",
            tooltip_text="Remove from Favorites",
            css_classes=["action-button", "destructive-action"],
        )

        btn_box.append(set_btn)
        btn_box.append(remove_btn)
        card.append(btn_box)

        list_item.set_child(card)
        list_item.image = image
        list_item.info = info
        list_item.set_btn = set_btn
        list_item.remove_btn = remove_btn

    def _on_favorite_item_bind(self, factory, list_item):
        wallpaper = list_item.get_item()
        if not wallpaper:
            return

        if wallpaper.thumbs_large.startswith("file://"):
            self._load_local_thumbnail(list_item.image, wallpaper.thumbs_large[7:])
        else:
            self._load_thumbnail(list_item.image, wallpaper.thumbs_large)
        list_item.info.set_text(f"{wallpaper.resolution} • {wallpaper.category}")

        list_item.set_btn.connect(
            "clicked", self._on_set_wallhaven_wallpaper, wallpaper
        )
        list_item.remove_btn.connect("clicked", self._on_remove_favorite, wallpaper)

    def _on_toggle_favorite(self, button, wallpaper, btn_widget):
        app = Gtk.Application.get_default()
        if app.favorites_service.is_favorite(wallpaper.id):
            app.favorites_service.remove_favorite(wallpaper.id)
            btn_widget.set_icon_name("non-starred-symbolic")
            self._send_notification(
                "Removed from Favorites",
                f"Wallpaper {wallpaper.id} removed from favorites.",
            )
        else:
            app.favorites_service.add_favorite(wallpaper)
            btn_widget.set_icon_name("starred-symbolic")
            self._send_notification(
                "Added to Favorites", f"Wallpaper {wallpaper.id} added to favorites."
            )

    def _on_remove_favorite(self, button, wallpaper):
        app = Gtk.Application.get_default()
        app.favorites_service.remove_favorite(wallpaper.id)
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

    def _on_search_changed(self, entry):
        if self.search_changed_timer:
            GLib.source_remove(self.search_changed_timer)

        def trigger_search():
            self.search_changed_timer = None
            self._on_search_wallpapers()

        self.search_changed_timer = GLib.timeout_add(500, trigger_search)

    def _on_wallhaven_search(self, button):
        query = self.search_entry.get_text()
        categories_map = {0: "111", 1: "100", 2: "010", 3: "001"}
        categories = categories_map[self.categories_combo.get_active()]
        sorting = self.sorting_combo.get_active_text()

        if button is not None:
            self.wallhaven_current_page = 1

        self.wallhaven_last_search_params = {
            "q": query,
            "categories": categories,
            "sorting": sorting,
        }

        self._perform_wallhaven_search()

    def _perform_wallhaven_search(self):
        if not self.wallhaven_last_search_params:
            return

        params = self.wallhaven_last_search_params
        self.wallhaven_status.set_text("Searching...")
        app = Gtk.Application.get_default()

        def do_search():
            result = app.wallhaven_service.search(
                q=params["q"],
                categories=params["categories"],
                purity="100",
                sorting=params["sorting"],
                page=self.wallhaven_current_page,
            )
            GLib.idle_add(on_search_done, result)

        def on_search_done(result):
            if "error" in result:
                self.wallhaven_status.set_text(f"Error: {result['error']}")
                return

            meta = result.get("meta", {})
            self.wallhaven_total_pages = meta.get("last_page", 1)
            total_results = meta.get("total", 0)

            wallpapers = app.wallhaven_service.parse_wallpapers(result.get("data", []))
            list_store = Gio.ListStore()
            for wp in wallpapers:
                list_store.append(wp)

            self.wallhaven_selection.set_model(list_store)
            self.wallhaven_status.set_text(
                f"Page {self.wallhaven_current_page}/{self.wallhaven_total_pages} • {len(wallpapers)} wallpapers from {total_results}"
            )

            self.wallhaven_prev_btn.set_sensitive(self.wallhaven_current_page > 1)
            self.wallhaven_next_btn.set_sensitive(
                self.wallhaven_current_page < self.wallhaven_total_pages
            )

        threading.Thread(target=do_search, daemon=True).start()

    def _on_wallhaven_prev_page(self, button):
        if self.wallhaven_current_page > 1:
            self.wallhaven_current_page -= 1
            self._perform_wallhaven_search()

    def _on_wallhaven_next_page(self, button):
        if self.wallhaven_current_page < self.wallhaven_total_pages:
            self.wallhaven_current_page += 1
            self._perform_wallhaven_search()

    def _on_search_wallpapers(self):
        visible_child = self.stack.get_visible_child()

        if visible_child == self.local_box:
            self._on_local_search()
        elif visible_child == self.wallhaven_box:
            self._on_wallhaven_search(None)
        elif visible_child == self.favorites_box:
            self._on_favorites_search()

    def _on_favorites_search(self):
        query = self.search_entry.get_text()
        app = Gtk.Application.get_default()

        wallpapers = app.favorites_service.search_wallpapers(query)
        list_store = Gio.ListStore()
        for wp in wallpapers:
            list_store.append(wp)

        self.favorites_selection.set_model(list_store)
        self.favorites_status.set_text(f"Found {len(wallpapers)} wallpapers")

    def _on_local_search(self):
        query = self.search_entry.get_text()
        app = Gtk.Application.get_default()

        wallpapers = app.local_service.search_wallpapers(query)
        list_store = Gio.ListStore()
        for wp in wallpapers:
            list_store.append(wp)

        self.local_selection.set_model(list_store)
        self.local_status.set_text(f"Found {len(wallpapers)} wallpapers")

    def _load_thumbnail(self, image_widget, url):
        app = Gtk.Application.get_default()
        app.thumbnail_cache.load_thumbnail_with_cache(url, image_widget)

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
                self._send_notification(
                    "Wallpaper Set",
                    f"Wallpaper {wallpaper.id} has been set successfully.",
                )
            else:
                self.wallhaven_status.set_text("Failed to set wallpaper")
                self._send_notification(
                    "Failed to Set Wallpaper",
                    "There was an error setting the wallpaper.",
                )

        threading.Thread(target=do_download, daemon=True).start()

    def _on_wallhaven_image_click(self, gesture, n_press, x, y, list_item):
        if n_press == 2:
            wallpaper = list_item.get_item()
            self._on_set_wallhaven_wallpaper(None, wallpaper)

    def _on_local_image_click(self, gesture, n_press, x, y, list_item):
        if n_press == 2:
            wallpaper = list_item.get_item()
            self._on_set_local_wallpaper(None, wallpaper)

    def _on_favorite_image_click(self, gesture, n_press, x, y, list_item):
        if n_press == 2:
            wallpaper = list_item.get_item()
            self._on_set_favorite_wallpaper(None, wallpaper)

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
                self._send_notification(
                    "Wallpaper Downloaded",
                    f"Wallpaper {wallpaper.id} saved to library.",
                )
            else:
                self.wallhaven_status.set_text("Download failed")
                self._send_notification(
                    "Download Failed", "Failed to download the wallpaper."
                )

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

    def _on_local_refresh(self, button=None):
        self.current_wallpaper_path = self._get_current_wallpaper()
        self._load_local_wallpapers()

    def _on_local_item_setup(self, factory, list_item):
        card = Gtk.Box(
            orientation=Gtk.Orientation.VERTICAL,
            spacing=6,
            css_classes=["wallpaper-card"],
        )
        card.set_margin_start(6)
        card.set_margin_end(6)
        card.set_margin_top(6)
        card.set_margin_bottom(6)

        overlay = Gtk.Overlay()
        image = Gtk.Picture()
        image.set_size_request(-1, 220)
        image.set_content_fit(Gtk.ContentFit.COVER)
        image.add_css_class("wallpaper-image")
        overlay.set_child(image)

        click_gesture = Gtk.GestureClick()
        click_gesture.set_button(1)
        click_gesture.set_propagation_phase(Gtk.PropagationPhase.CAPTURE)
        click_gesture.connect("pressed", self._on_local_image_click, list_item)
        image.add_controller(click_gesture)

        current_badge = Gtk.Label(
            label="CURRENT", halign=Gtk.Align.END, valign=Gtk.Align.START
        )
        current_badge.add_css_class("current-badge")
        current_badge.set_margin_top(8)
        current_badge.set_margin_end(8)
        current_badge.set_visible(False)
        overlay.add_overlay(current_badge)

        card.append(overlay)

        info = Gtk.Label(label="", halign=Gtk.Align.START, css_classes=["dim-label"])
        info.set_ellipsize(3)
        info.set_max_width_chars(35)
        card.append(info)

        btn_box = Gtk.Box(
            orientation=Gtk.Orientation.HORIZONTAL, spacing=6, homogeneous=True
        )

        set_btn = Gtk.Button(
            icon_name="emblem-ok-symbolic",
            tooltip_text="Set as Wallpaper",
            css_classes=["action-button", "suggested-action"],
        )
        fav_btn = Gtk.Button(
            icon_name="starred-symbolic",
            tooltip_text="Add to Favorites",
            css_classes=["action-button", "favorite-icon"],
        )
        trash_btn = Gtk.Button(
            icon_name="user-trash-symbolic",
            tooltip_text="Move to Trash",
            css_classes=["action-button", "destructive-action"],
        )

        btn_box.append(set_btn)
        btn_box.append(fav_btn)
        btn_box.append(trash_btn)
        card.append(btn_box)

        list_item.set_child(card)
        list_item.image = image
        list_item.info = info
        list_item.set_btn = set_btn
        list_item.fav_btn = fav_btn
        list_item.trash_btn = trash_btn
        list_item.current_badge = current_badge

    def _on_local_item_bind(self, factory, list_item):
        wallpaper = list_item.get_item()
        if not wallpaper:
            return

        self._load_local_thumbnail(list_item.image, wallpaper.path)
        size_mb = wallpaper.size / (1024 * 1024)
        list_item.info.set_text(f"{wallpaper.filename} • {size_mb:.1f} MB")

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
        list_item.fav_btn.connect(
            "clicked", self._on_add_local_to_favorites_btn, wallpaper
        )
        list_item.trash_btn.connect(
            "clicked", self._on_delete_local_wallpaper, wallpaper
        )

    def _load_local_thumbnail(self, image_widget, path):
        MAX_FILE_SIZE = 20 * 1024 * 1024

        def do_load():
            try:
                file_size = path.stat().st_size
                if file_size > MAX_FILE_SIZE:
                    raise MemoryError(
                        f"File too large ({file_size / 1024 / 1024:.1f}MB)"
                    )

                pixbuf = GdkPixbuf.Pixbuf.new_from_file_at_scale(
                    str(path), 400, 280, True
                )
                GLib.idle_add(set_image, pixbuf, None)
            except MemoryError as e:
                print(f"Memory error loading {path}: {e}")
                GLib.idle_add(set_image, None, f"File too large")
            except GLib.GError as e:
                print(f"Gdk error loading {path}: {e}")
                GLib.idle_add(set_image, None, str(e))
            except Exception as e:
                print(f"Error loading thumbnail for {path}: {e}")
                GLib.idle_add(set_image, None, str(e))

        def set_image(pixbuf, error):
            if pixbuf:
                try:
                    texture = Gdk.Texture.new_for_pixbuf(pixbuf)
                    image_widget.set_paintable(texture)
                except Exception as e:
                    print(f"Error setting texture: {e}")

        threading.Thread(target=do_load, daemon=True).start()

    def _on_set_local_wallpaper(self, button, wallpaper):
        app = Gtk.Application.get_default()
        if app.wallpaper_setter.set_wallpaper(wallpaper.path):
            self.current_wallpaper_path = str(wallpaper.path)
            self.local_status.set_text(f"Set: {wallpaper.filename}")
            self._send_notification(
                "Wallpaper Set",
                f"Local wallpaper {wallpaper.filename} has been set successfully.",
            )
        else:
            self.local_status.set_text("Failed to set wallpaper")
            self._send_notification(
                "Failed to Set Wallpaper",
                "There was an error setting the local wallpaper.",
            )

    def _on_add_local_to_favorites_btn(self, button, wallpaper):
        app = Gtk.Application.get_default()
        local_wp = Wallpaper(
            id=f"local_{wallpaper.filename}",
            url=f"file://{wallpaper.path}",
            path=str(wallpaper.path),
            thumbs_large=f"file://{wallpaper.path}",
            thumbs_small=f"file://{wallpaper.path}",
            resolution=f"{wallpaper.size} bytes",
            category="local",
            purity="sfw",
            colors=[],
            file_size=wallpaper.size,
        )
        app.favorites_service.add_favorite(local_wp)
        self.local_status.set_text(f"Added {wallpaper.filename} to favorites")
        self._send_notification(
            "Added to Favorites",
            f"Local wallpaper {wallpaper.filename} added to favorites.",
        )

    def _on_delete_local_wallpaper(self, button, wallpaper):
        app = Gtk.Application.get_default()
        if app.local_service.delete_wallpaper(wallpaper.path):
            self._load_local_wallpapers()
            self.local_status.set_text("Moved to trash")
            self._send_notification(
                "Wallpaper Deleted",
                f"Local wallpaper {wallpaper.filename} moved to trash.",
            )
        else:
            self.local_status.set_text("Failed to delete")
            self._send_notification(
                "Failed to Delete Wallpaper",
                "There was an error deleting the local wallpaper.",
            )

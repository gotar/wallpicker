"""View for Wallhaven wallpaper browsing."""

import asyncio
import concurrent.futures
import sys
import threading
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import gi

gi.require_version("Gtk", "4.0")

from gi.repository import GObject, Gtk

from ui.view_models.wallhaven_view_model import WallhavenViewModel


class WallhavenView(Gtk.Box):
    """View for Wallhaven wallpaper browsing"""

    def __init__(self, view_model: WallhavenViewModel):
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        self.view_model = view_model

        self._event_loop = asyncio.new_event_loop()

        def run_loop():
            asyncio.set_event_loop(self._event_loop)
            self._event_loop.run_forever()

        self._loop_thread = threading.Thread(target=run_loop, daemon=True)
        self._loop_thread.start()

        self._create_filter_bar()
        self._create_wallpaper_grid()
        self._create_pagination_controls()

        self._bind_to_view_model()

    def __del__(self):
        if hasattr(self, "_event_loop") and self._event_loop.is_running():
            self._event_loop.call_soon_threadsafe(self._event_loop.stop)

    def _run_async(self, coro):
        future = asyncio.run_coroutine_threadsafe(coro, self._event_loop)
        try:
            future.result(timeout=30)
        except concurrent.futures.TimeoutError:
            print("Timeout waiting for async operation")

    def _create_filter_bar(self):
        """Create filter and search controls"""
        filter_box = Gtk.Box(
            orientation=Gtk.Orientation.HORIZONTAL,
            spacing=12,
        )
        filter_box.add_css_class("filter-bar")

        # Category dropdown
        cat_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        cat_box.append(Gtk.Label(label="Category:"))
        self.categories_combo = Gtk.ComboBoxText()
        for cat in ["All", "General", "Anime", "People"]:
            self.categories_combo.append_text(cat)
        self.categories_combo.set_active(0)
        cat_box.append(self.categories_combo)
        filter_box.append(cat_box)

        # Sorting dropdown
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

        # Search entry
        self.search_entry = Gtk.Entry(placeholder_text="Search wallpapers...")
        self.search_entry.set_hexpand(True)
        filter_box.append(self.search_entry)

        # Search button
        search_btn = Gtk.Button(icon_name="system-search-symbolic", tooltip_text="Search")
        search_btn.add_css_class("suggested-action")
        search_btn.connect("clicked", self._on_search_clicked)
        filter_box.append(search_btn)

        # Loading spinner
        self.loading_spinner = Gtk.Spinner(spinning=False)
        filter_box.append(self.loading_spinner)

        # Error label
        self.error_label = Gtk.Label(wrap=True)
        self.error_label.add_css_class("error")
        self.error_label.set_visible(False)
        filter_box.append(self.error_label)

        # Spacer
        spacer = Gtk.Label()
        spacer.set_hexpand(True)
        filter_box.append(spacer)

        # Pagination buttons
        self.prev_btn = Gtk.Button(icon_name="go-previous-symbolic", tooltip_text="Previous page")
        self.prev_btn.set_sensitive(False)
        self.prev_btn.connect("clicked", self._on_prev_page_clicked)
        filter_box.append(self.prev_btn)

        self.next_btn = Gtk.Button(icon_name="go-next-symbolic", tooltip_text="Next page")
        self.next_btn.set_sensitive(False)
        self.next_btn.connect("clicked", self._on_next_page_clicked)
        filter_box.append(self.next_btn)

        self.append(filter_box)

    def _create_wallpaper_grid(self):
        """Create wallpaper grid display"""
        self.scroll = Gtk.ScrolledWindow()
        self.scroll.set_vexpand(True)

        # Create flow box for wallpaper grid
        self.wallpaper_grid = Gtk.FlowBox()
        self.wallpaper_grid.set_homogeneous(True)
        self.wallpaper_grid.set_min_children_per_line(2)
        self.wallpaper_grid.set_max_children_per_line(6)
        self.wallpaper_grid.set_column_spacing(12)
        self.wallpaper_grid.set_row_spacing(12)
        self.wallpaper_grid.set_selection_mode(Gtk.SelectionMode.NONE)
        self.scroll.set_child(self.wallpaper_grid)

        self.append(self.scroll)

    def _create_pagination_controls(self):
        """Create pagination status display"""
        status_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        status_box.add_css_class("status-bar")

        self.page_label = Gtk.Label(label="Page 1")
        status_box.append(self.page_label)

        self.append(status_box)

    def _bind_to_view_model(self):
        GObject.Object.bind_property(
            self.view_model,
            "is-busy",
            self.loading_spinner,
            "spinning",
            GObject.BindingFlags.DEFAULT,
        )
        self.view_model.connect("notify::wallpapers", self._on_wallpapers_changed)
        self.view_model.connect("notify::current-page", self._on_page_changed)
        self.view_model.connect("notify::total-pages", self._on_page_changed)

    def _on_search_clicked(self, button):
        category = self._get_category()
        sorting = self._get_sorting()
        query = self.search_entry.get_text()

        self.view_model.category = category
        self.view_model.sorting = sorting

        self._run_async(
            self.view_model.search_wallpapers(
                query=query,
                category=category,
                sorting=sorting,
            )
        )

    def _on_prev_page_clicked(self, button):
        self._run_async(self.view_model.load_prev_page())

    def _on_next_page_clicked(self, button):
        self._run_async(self.view_model.load_next_page())

    def _on_wallpapers_changed(self, obj, pspec):
        """Handle wallpapers property change"""
        self.update_wallpaper_grid(self.view_model.wallpapers)

    def _on_page_changed(self, obj, pspec):
        """Handle page property change"""
        self.update_pagination(
            self.view_model.current_page,
            self.view_model.total_pages,
        )

    def update_wallpaper_grid(self, wallpapers):
        """Update wallpaper grid with new wallpapers"""
        while child := self.wallpaper_grid.get_first_child():
            self.wallpaper_grid.remove(child)

        for wallpaper in wallpapers:
            card = self._create_wallpaper_card(wallpaper)
            self.wallpaper_grid.append(card)

    def _create_wallpaper_card(self, wallpaper):
        card = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        card.set_hexpand(True)
        card.set_size_request(220, 200)
        card.add_css_class("wallpaper-card")

        image = Gtk.Picture()
        image.set_size_request(200, 160)
        image.set_content_fit(Gtk.ContentFit.COVER)
        image.add_css_class("wallpaper-thumb")

        def on_thumbnail_loaded(texture):
            if texture:
                image.set_paintable(texture)

        thumb_url = wallpaper.thumbs_large or wallpaper.thumbs_small or ""
        if thumb_url:
            self.view_model.load_thumbnail_async(thumb_url, on_thumbnail_loaded)

        overlay = Gtk.Overlay()
        overlay.set_child(image)
        card.append(overlay)

        click = Gtk.GestureClick()
        click.set_button(1)
        click.connect("pressed", self._on_card_double_clicked, wallpaper)
        card.add_controller(click)

        actions_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        actions_box.set_halign(Gtk.Align.CENTER)
        actions_box.set_homogeneous(True)

        download_btn = Gtk.Button(
            icon_name="folder-download-symbolic", tooltip_text="Download wallpaper"
        )
        download_btn.add_css_class("action-button")
        download_btn.connect("clicked", self._on_download_wallpaper, wallpaper)
        actions_box.append(download_btn)

        set_btn = Gtk.Button(icon_name="image-x-generic-symbolic", tooltip_text="Set as wallpaper")
        set_btn.add_css_class("action-button")
        set_btn.connect("clicked", self._on_set_wallpaper, wallpaper)
        actions_box.append(set_btn)

        fav_btn = Gtk.Button(icon_name="starred-symbolic", tooltip_text="Add to favorites")
        fav_btn.add_css_class("action-button")
        fav_btn.connect("clicked", self._on_add_to_favorites, wallpaper)
        actions_box.append(fav_btn)

        card.append(actions_box)
        return card

    def _on_set_wallpaper(self, button, wallpaper):
        async def set_with_download():
            if not wallpaper.path:
                downloaded = await self.view_model.download_wallpaper(wallpaper)
                if downloaded and downloaded.path:
                    if self.view_model.notification_service:
                        self.view_model.notification_service.notify_success(
                            "Wallpaper set successfully"
                        )
                    self.view_model.wallpaper_setter.set_wallpaper(downloaded.path)
                    self.update_wallpaper_grid(self.view_model.wallpapers)
                elif self.view_model.error_message:
                    if self.view_model.notification_service:
                        self.view_model.notification_service.notify_error(
                            self.view_model.error_message
                        )
            else:
                if self.view_model.notification_service:
                    self.view_model.notification_service.notify_success(
                        "Wallpaper set successfully"
                    )
                self.view_model.wallpaper_setter.set_wallpaper(wallpaper.path)

        self._run_async(set_with_download())

    def _on_card_double_clicked(self, gesture, n_press, x, y, wallpaper):
        self._on_set_wallpaper(None, wallpaper)

    def _on_download_wallpaper(self, button, wallpaper):
        async def download_only():
            downloaded = await self.view_model.download_wallpaper(wallpaper)
            if downloaded and downloaded.path:
                if self.view_model.notification_service:
                    self.view_model.notification_service.notify_success(
                        f"Wallpaper downloaded to: {downloaded.path}"
                    )
                self.update_wallpaper_grid(self.view_model.wallpapers)
            elif self.view_model.error_message:
                if self.view_model.notification_service:
                    self.view_model.notification_service.notify_error(self.view_model.error_message)

        self._run_async(download_only())

    def _on_add_to_favorites(self, button, wallpaper):
        async def add_to_favs():
            result = await self.view_model.add_to_favorites(wallpaper)
            if result and self.view_model.notification_service:
                self.view_model.notification_service.notify_success("Added to favorites")
            elif not result and self.view_model.notification_service:
                self.view_model.notification_service.notify_error("Failed to add to favorites")

        self._run_async(add_to_favs())

    def _get_category(self) -> str:
        """Get selected category code"""
        active = self.categories_combo.get_active()
        categories = {"All": "111", "General": "100", "Anime": "010", "People": "001"}
        return list(categories.values())[active]

    def _get_sorting(self) -> str:
        """Get selected sorting option"""
        active = self.sorting_combo.get_active()
        sortings = [
            "date_added",
            "relevance",
            "random",
            "views",
            "favorites",
            "toplist",
        ]
        return sortings[active]

    def update_pagination(self, current_page: int, total_pages: int):
        """Update pagination controls"""
        self.page_label.set_text(f"Page {current_page}")
        self.prev_btn.set_sensitive(current_page > 1)
        self.next_btn.set_sensitive(current_page < total_pages)

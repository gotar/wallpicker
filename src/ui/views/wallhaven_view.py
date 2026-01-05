"""View for Wallhaven wallpaper browsing."""

import sys
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

        # Create UI components
        self._create_filter_bar()
        self._create_wallpaper_grid()
        self._create_pagination_controls()

        # Bind to ViewModel state
        self._bind_to_view_model()

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
        """Bind View to ViewModel state changes"""
        GObject.Object.bind_property(
            self.view_model,
            "is-busy",
            self.loading_spinner,
            "spinning",
            GObject.BindingFlags.DEFAULT,
        )
        GObject.Object.bind_property(
            self.view_model,
            "error-message",
            self.error_label,
            "label",
            GObject.BindingFlags.DEFAULT,
        )
        GObject.Object.bind_property(
            self.view_model,
            "error-message",
            self.error_label,
            "visible",
            GObject.BindingFlags.SYNC_CREATE,
        )
        self.view_model.connect("notify::wallpapers", self._on_wallpapers_changed)
        self.view_model.connect("notify::current-page", self._on_page_changed)
        self.view_model.connect("notify::total-pages", self._on_page_changed)

    def _on_search_clicked(self, button):
        """Handle search button click"""
        category = self._get_category()
        sorting = self._get_sorting()
        query = self.search_entry.get_text()

        self.view_model.category = category
        self.view_model.sorting = sorting

        import threading
        import asyncio

        def run_search():
            asyncio.run(
                self.view_model.search_wallpapers(
                    query=query,
                    category=category,
                    sorting=sorting,
                )
            )

        threading.Thread(target=run_search, daemon=True).start()

    def _on_prev_page_clicked(self, button):
        """Handle previous page button click"""
        import threading
        import asyncio

        def run_prev():
            asyncio.run(self.view_model.load_prev_page())

        threading.Thread(target=run_prev, daemon=True).start()

    def _on_next_page_clicked(self, button):
        """Handle next page button click"""
        import threading
        import asyncio

        def run_next():
            asyncio.run(self.view_model.load_next_page())

        threading.Thread(target=run_next, daemon=True).start()

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
        """Create wallpaper card with image and actions"""
        card = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        card.set_hexpand(True)
        card.set_size_request(220, 180)

        # Use Picture for better scaling
        image = Gtk.Picture()
        image.set_size_request(220, 160)
        image.set_content_fit(Gtk.ContentFit.COVER)
        image.add_css_class("wallpaper-thumb")

        def on_thumbnail_loaded(texture):
            if texture:
                image.set_paintable(texture)

        # Use thumbnail URL
        thumb_url = wallpaper.thumbs_large or wallpaper.thumbs_small or ""
        if thumb_url:
            self.view_model.load_thumbnail_async(thumb_url, on_thumbnail_loaded)

        overlay = Gtk.Overlay()
        overlay.set_child(image)
        card.append(overlay)

        actions_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=4)

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
        """Handle set wallpaper button click"""
        pass

    def _on_add_to_favorites(self, button, wallpaper):
        """Handle add to favorites button click"""
        pass

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

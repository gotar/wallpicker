"""View for Wallhaven wallpaper browsing."""

import asyncio
import concurrent.futures
import sys
import threading
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")

from gi.repository import Adw, Gdk, GLib, GObject, Gtk

from ui.view_models.wallhaven_view_model import WallhavenViewModel


class WallhavenView(Adw.Bin):
    """View for Wallhaven wallpaper browsing with adaptive layout"""

    def __init__(self, view_model: WallhavenViewModel, banner_service=None):
        super().__init__()
        self.view_model = view_model
        self.banner_service = banner_service
        self._last_selected_wallpaper = None

        self._event_loop = asyncio.new_event_loop()

        def run_loop():
            asyncio.set_event_loop(self._event_loop)
            self._event_loop.run_forever()

        self._loop_thread = threading.Thread(target=run_loop, daemon=True)
        self._loop_thread.start()

        self._create_ui()

        self._setup_keyboard_shortcuts()
        self._setup_pull_to_refresh()
        self._setup_scroll_snap()
        self._bind_to_view_model()

    def _create_ui(self):
        """Create main UI structure"""
        self.main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        self.set_child(self.main_box)

        self._create_filter_bar()
        self._create_wallpaper_grid()
        self._create_pagination_controls()

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

        self.main_box.append(filter_box)

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

        self.main_box.append(self.scroll)

    def _create_pagination_controls(self):
        status_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        status_box.add_css_class("status-bar")
        status_box.set_halign(Gtk.Align.CENTER)

        self.prev_btn = Gtk.Button(icon_name="go-previous-symbolic", tooltip_text="Previous page")
        self.prev_btn.set_sensitive(False)
        self.prev_btn.connect("clicked", self._on_prev_page_clicked)
        status_box.append(self.prev_btn)

        self.page_label = Gtk.Label(label="Page 1 / 1 - 0 wallpapers")
        status_box.append(self.page_label)

        self.next_btn = Gtk.Button(icon_name="go-next-symbolic", tooltip_text="Next page")
        self.next_btn.set_sensitive(False)
        self.next_btn.connect("clicked", self._on_next_page_clicked)
        status_box.append(self.next_btn)

        self.main_box.append(status_box)

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
        self.view_model.connect("notify::selected-count", self._on_selection_changed)

    def _setup_keyboard_shortcuts(self):
        key_controller = Gtk.EventControllerKey()
        key_controller.connect("key-pressed", self._on_key_pressed)
        self.add_controller(key_controller)

        # Setup grid navigation
        self._setup_grid_navigation()

    def _setup_grid_navigation(self):
        """Setup keyboard navigation for wallpaper grid."""
        # Add key controller to flow box for arrow key navigation
        grid_key_controller = Gtk.EventControllerKey()
        grid_key_controller.connect("key-pressed", self._on_grid_key_pressed)
        self.wallpaper_grid.add_controller(grid_key_controller)

        # Track card->wallpaper mapping for keyboard activation
        self.card_wallpaper_map = {}

    def _on_key_pressed(self, controller, keyval, keycode, state):
        """Handle keyboard shortcuts at view level."""
        if state & Gdk.ModifierType.CONTROL_MASK and keyval == Gdk.KEY_a:
            self.view_model.select_all()
            return True
        elif keyval == Gdk.KEY_Escape:
            self.view_model.clear_selection()
            return True
        return False

    def _on_grid_key_pressed(self, controller, keyval, keycode, state):
        """Handle keyboard navigation within grid."""
        # Arrow keys: Navigate between cards
        if keyval == Gdk.KEY_Down:
            self._focus_next_card()
            return True
        elif keyval == Gdk.KEY_Up:
            self._focus_prev_card()
            return True
        elif keyval == Gdk.KEY_Right:
            self._focus_next_card()
            return True
        elif keyval == Gdk.KEY_Left:
            self._focus_prev_card()
            return True
        # Enter/Return: Set wallpaper
        elif keyval in (Gdk.KEY_Return, Gdk.KEY_KP_Enter):
            focused = self.wallpaper_grid.get_focus_child()
            if focused and focused in self.card_wallpaper_map:
                wallpaper = self.card_wallpaper_map[focused]
                self._on_set_wallpaper(None, wallpaper)
            return True
        # Space: Toggle favorite
        elif keyval == Gdk.KEY_space:
            focused = self.wallpaper_grid.get_focus_child()
            if focused and focused in self.card_wallpaper_map:
                wallpaper = self.card_wallpaper_map[focused]
                self._on_add_to_favorites(None, wallpaper)
            return True
        # Escape: Clear selection and remove focus
        elif keyval == Gdk.KEY_Escape:
            self.view_model.clear_selection()
            focused = self.wallpaper_grid.get_focus_child()
            if focused:
                focused.grab_remove()
            return True
        return False

    def _focus_next_card(self):
        """Focus next card in grid."""
        current = self.wallpaper_grid.get_focus_child()
        if not current:
            # Focus first card if none focused
            first = self.wallpaper_grid.get_first_child()
            if first:
                first.grab_focus()
            return

        # Get all children
        children = []
        child = self.wallpaper_grid.get_first_child()
        while child:
            children.append(child)
            child = child.get_next_sibling()

        if not children:
            return

        current_idx = children.index(current)
        next_idx = (current_idx + 1) % len(children)
        children[next_idx].grab_focus()

    def _focus_prev_card(self):
        """Focus previous card in grid."""
        current = self.wallpaper_grid.get_focus_child()
        if not current:
            # Focus last card if none focused
            last = self.wallpaper_grid.get_first_child()
            while last and last.get_next_sibling():
                last = last.get_next_sibling()
            if last:
                last.grab_focus()
            return

        # Get all children
        children = []
        child = self.wallpaper_grid.get_first_child()
        while child:
            children.append(child)
            child = child.get_next_sibling()

        if not children:
            return

        current_idx = children.index(current)
        prev_idx = (current_idx - 1) % len(children)
        children[prev_idx].grab_focus()

    def _setup_pull_to_refresh(self):
        """Setup pull-to-refresh gesture on scrolled window."""
        self.is_refreshing = False

        # Swipe controller for pull gesture
        swipe = Gtk.GestureSwipe()
        swipe.set_propagation_phase(Gtk.PropagationPhase.BUBBLE)
        swipe.connect("swipe", self._on_pull_swipe)
        self.scroll.add_controller(swipe)

    def _setup_scroll_snap(self):
        """Setup scroll snap for pagination at bottom."""
        scroll_controller = Gtk.EventControllerScroll()
        scroll_controller.connect("scroll", self._on_scroll)
        self.scroll.add_controller(scroll_controller)

    def _on_pull_swipe(self, gesture, dx, dy):
        """Handle pull-down gesture for refresh."""
        # Only trigger on vertical pull (dy < 0) and near top of scroll
        vadj = self.scroll.get_vadjustment()
        current_value = vadj.get_value()

        # Check if we're at the top of scroll and pulling down
        if dy < -100 and current_value < 50 and not self.is_refreshing:
            self.is_refreshing = True
            self._refresh_current_search()

            # Reset flag after a delay
            GLib.timeout_add(1000, self._reset_refresh_flag)

    def _on_scroll(self, controller, dx, dy):
        """Handle scroll snap for pagination."""
        vadj = self.scroll.get_vadjustment()
        page_size = vadj.get_page_size()
        value = vadj.get_value()
        upper = vadj.get_upper()

        # At bottom of scroll - load next page
        if (
            value + page_size >= upper - 10
            and self.view_model.current_page < self.view_model.total_pages
        ):
            self._run_async(self.view_model.load_next_page())

    def _refresh_current_search(self):
        """Refresh current Wallhaven search."""

        async def refresh():
            category = self._get_category()
            sorting = self._get_sorting()
            query = self.search_entry.get_text()

            self.view_model.category = category
            self.view_model.sorting = sorting

            await self.view_model.search_wallpapers(
                query=query,
                category=category,
                sorting=sorting,
            )

        self._run_async(refresh())

    def _reset_refresh_flag(self):
        """Reset refreshing flag."""
        self.is_refreshing = False
        return False

    def _on_key_pressed(self, controller, keyval, keycode, state):
        if state & Gdk.ModifierType.CONTROL_MASK and keyval == Gdk.KEY_a:
            self.view_model.select_all()
            return True
        elif keyval == Gdk.KEY_Escape:
            self.view_model.clear_selection()
            return True
        return False

    def _on_selection_changed(self, obj, pspec):
        count = self.view_model.selected_count
        if count > 0 and self.banner_service:
            self.banner_service.show_selection_banner(
                count=count, on_set_all=self._on_set_all_selected
            )
        elif count == 0 and self.banner_service:
            self.banner_service.hide_selection_banner()

    def _on_set_all_selected(self):
        selected = self.view_model.get_selected_wallpapers()
        for wallpaper in selected:
            if wallpaper.path:
                self.view_model.wallpaper_setter.set_wallpaper(wallpaper.path)
                break
        self.view_model.clear_selection()

    def _on_search_clicked(self, button):
        category = self._get_category()
        sorting = self._get_sorting()
        query = self.search_entry.get_text()
        advanced = self.search_filter_bar.get_advanced_filters()

        self.view_model.category = category
        self.view_model.sorting = sorting

        self.view_model.top_range = advanced.get("top_range", "")
        self.view_model.ratios = advanced.get("ratios", "")
        self.view_model.colors = advanced.get("colors", "")
        self.view_model.resolutions = advanced.get("resolutions", "")

        self._run_async(
            self.view_model.search_wallpapers(
                query=query,
                page=1,
                category=category,
                purity="100",
                sorting=sorting,
                order="desc",
                resolution="",
                top_range=self.view_model.top_range,
                ratios=self.view_model.ratios,
                colors=self.view_model.colors,
                resolutions=self.view_model.resolutions,
            )
        )

    def _on_prev_page_clicked(self, button):
        self._run_async(self.view_model.load_prev_page())

    def _on_next_page_clicked(self, button):
        self._run_async(self.view_model.load_next_page())

    def _on_wallpapers_changed(self, obj, pspec):
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

        is_selected = wallpaper in self.view_model.get_selected_wallpapers()
        if is_selected:
            card.add_css_class("selected")
        if self.view_model.selection_mode:
            card.add_css_class("selection-mode")

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

        checkbox = Gtk.CheckButton()
        checkbox.add_css_class("selection-checkbox")
        checkbox.set_halign(Gtk.Align.START)
        checkbox.set_valign(Gtk.Align.START)
        checkbox.set_margin_start(8)
        checkbox.set_margin_top(8)
        checkbox.set_active(is_selected)
        if self.view_model.selection_mode:
            checkbox.set_visible(True)
        else:
            checkbox.set_visible(False)
        checkbox.connect(
            "toggled", lambda cb: self._on_selection_toggled(wallpaper, cb.get_active())
        )
        overlay.add_overlay(checkbox)

        card.append(overlay)

        click = Gtk.GestureClick()
        click.set_button(1)
        click.connect("pressed", self._on_card_clicked, wallpaper, card, checkbox)
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

    def _on_card_clicked(self, gesture, n_press, x, y, wallpaper, card, checkbox):
        if self.view_model.selection_mode and n_press == 1:
            checkbox.set_active(not checkbox.get_active())
        elif n_press == 2:
            self._on_set_wallpaper(None, wallpaper)
            if self.view_model.selection_mode:
                checkbox.set_active(not checkbox.get_active())

    def _on_selection_toggled(self, wallpaper, is_selected):
        self.view_model.toggle_selection(wallpaper)

    def _on_set_wallpaper(self, button, wallpaper):
        async def set_with_download():
            result = await self.view_model.set_wallpaper(wallpaper)
            if result:
                if self.view_model.notification_service:
                    self.view_model.notification_service.notify_success(
                        "Wallpaper set successfully"
                    )
                self.update_wallpaper_grid(self.view_model.wallpapers)
            elif self.view_model.error_message:
                if self.view_model.notification_service:
                    self.view_model.notification_service.notify_error(self.view_model.error_message)

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
        wallpaper_count = len(self.view_model.wallpapers)
        self.page_label.set_text(
            f"Page {current_page} / {total_pages} - {wallpaper_count} wallpapers"
        )
        self.prev_btn.set_sensitive(current_page > 1)
        self.next_btn.set_sensitive(current_page < total_pages)

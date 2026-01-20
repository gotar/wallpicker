"""View for local wallpaper browsing with pagination support."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")

from gi.repository import Adw, Gdk, GLib, GObject, Gtk, Pango  # noqa: E402

from core.asyncio_integration import schedule_async  # noqa: E402
from ui.components.search_filter_bar import SearchFilterBar  # noqa: E402
from ui.view_models.local_view_model import LocalViewModel  # noqa: E402

# Pagination settings for lazy loading
INITIAL_PAGE_SIZE = 50
PAGE_SIZE = 50
LOAD_MORE_THRESHOLD = 300
MAX_VISIBLE_ITEMS = 1000


class LocalView(Adw.BreakpointBin):
    """View for local wallpaper browsing with adaptive layout and pagination"""

    def __init__(
        self,
        view_model: LocalViewModel,
        banner_service=None,
        toast_service=None,
        thumbnail_loader=None,
        on_set_wallpaper=None,
        on_delete=None,
        config_service=None,
    ):
        super().__init__()
        self.view_model = view_model
        self.banner_service = banner_service
        self.toast_service = toast_service
        self.thumbnail_loader = thumbnail_loader
        self.on_set_wallpaper = on_set_wallpaper
        self.on_delete = on_delete
        self.config_service = config_service
        self._last_selected_wallpaper = None
        self._search_debounce_timer = None
        self._wallpaper_card_map = {}  # Reverse mapping: wallpaper -> card
        self._path_card_map = {}  # Mapping by path string: path -> card
        self._upscale_overlays = {}
        self._tag_overlays = {}
        self._metadata_labels = {}
        self._tags_labels = {}
        self._needs_full_rebuild = False

        # Pagination state
        self._all_wallpapers = []  # Current view (may be filtered)
        self._full_wallpapers = []  # Always contains all wallpapers
        self._visible_wallpapers = []
        self._current_page = 0
        self._is_loading_more = False
        self._has_more_items = True

        self._create_ui()

        self._setup_keyboard_shortcuts()
        self._bind_to_view_model()
        self._bind_upscale_signal()
        self._bind_tagging_signal()
        self._setup_scroll_detection()

    def _bind_tagging_signal(self):
        """Connect to tagging signals."""
        self.view_model.connect("tagging-complete", self._on_tagging_complete)
        self.view_model.connect("tagging-queue-changed", self._on_tagging_queue_changed)

    def _bind_upscale_signal(self):
        """Connect to upscaling signals."""
        self.view_model.connect("upscaling-complete", self._on_upscale_complete)
        self.view_model.connect("upscaling-queue-changed", self._on_queue_changed)

    def _setup_scroll_detection(self):
        """Setup scroll detection for lazy loading."""
        self._is_loading_more = False
        self._has_more_items = True
        vadj = self.scroll.get_vadjustment()
        vadj.connect("value-changed", self._on_scroll_changed)

    def _on_scroll_changed(self, adjustment):
        """Handle scroll position changes for lazy loading."""
        if self._is_loading_more or not self._has_more_items:
            return
        value = adjustment.get_value()
        page_size = adjustment.get_page_size()
        upper = adjustment.get_upper()
        remaining = upper - (value + page_size)
        if remaining <= LOAD_MORE_THRESHOLD:
            self._load_more_items()

    def _load_more_items(self):
        """Load more items for lazy loading."""
        if self._is_loading_more or not self._has_more_items:
            return

        self._is_loading_more = True
        current_count = len(self._visible_wallpapers)
        next_count = current_count + PAGE_SIZE

        if next_count >= len(self._all_wallpapers):
            next_count = len(self._all_wallpapers)
            self._has_more_items = False

        new_wallpapers = self._all_wallpapers[current_count:next_count]

        if not new_wallpapers:
            self._is_loading_more = False
            return

        for wallpaper in new_wallpapers:
            card = self._create_wallpaper_card(wallpaper)
            self.wallpaper_grid.append(card)

        self._visible_wallpapers = self._all_wallpapers[:next_count]
        self._current_page += 1
        self._is_loading_more = False
        self.update_status(len(self._all_wallpapers))

        self._clear_old_items()

    def _clear_old_items(self):
        """Clear oldest items when exceeding max visible to manage memory."""
        if len(self._visible_wallpapers) <= MAX_VISIBLE_ITEMS:
            return

        items_to_remove = len(self._visible_wallpapers) - MAX_VISIBLE_ITEMS
        keep_from = items_to_remove

        child = self.wallpaper_grid.get_first_child()
        for _ in range(items_to_remove):
            if child:
                next_child = child.get_next_sibling()
                self._remove_card_mappings(child)
                self.wallpaper_grid.remove(child)
                child = next_child

        self._visible_wallpapers = self._visible_wallpapers[keep_from:]

    def _remove_card_mappings(self, card):
        """Remove all mappings for a card."""
        if card in self.card_wallpaper_map:
            wp = self.card_wallpaper_map.pop(card)
            self._wallpaper_card_map.pop(wp, None)
            self._path_card_map.pop(str(wp.path), None)
        for path, existing_card in list(self._path_card_map.items()):
            if existing_card == card:
                self._path_card_map.pop(path, None)
                self._metadata_labels.pop(path, None)
                break

    def _create_ui(self):
        """Create main UI structure"""
        self.main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        self.set_child(self.main_box)

        self._create_filter_bar()
        self._create_wallpaper_grid()
        self._create_status_bar()

    def _create_filter_bar(self):
        """Create unified filter bar for local wallpapers"""
        toolbar_wrapper = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        toolbar_wrapper.add_css_class("toolbar-wrapper")
        self.main_box.append(toolbar_wrapper)

        folder_btn = Gtk.Button(icon_name="folder-symbolic", tooltip_text="Choose folder")
        folder_btn.connect("clicked", self._on_folder_clicked)
        toolbar_wrapper.append(folder_btn)

        self.search_filter_bar = SearchFilterBar(
            tab_type="local",
            on_search_changed=self._on_search_changed,
            on_sort_changed=self._on_sort_changed,
            on_filter_changed=self._on_filter_changed,
        )
        toolbar_wrapper.append(self.search_filter_bar)

        self.loading_spinner = Gtk.Spinner(spinning=False)
        toolbar_wrapper.append(self.loading_spinner)

    def _on_search_changed(self, text: str):
        if self._search_debounce_timer:
            GLib.source_remove(self._search_debounce_timer)

        self._search_debounce_timer = GLib.timeout_add(300, self._trigger_search, text)

    def _trigger_search(self, text: str) -> bool:
        if self._search_debounce_timer:
            self._search_debounce_timer = None

        schedule_async(self.view_model.search_wallpapers(text))
        return False

    def _on_sort_changed(self, sorting: str):
        self._needs_full_rebuild = True
        if sorting == "name":
            self.view_model.sort_by_name()
        elif sorting == "date":
            self.view_model.sort_by_date()
        elif sorting == "resolution":
            self.view_model.sort_by_resolution()

    def _on_filter_changed(self, filters: dict):
        self._needs_full_rebuild = True
        self.view_model.filter_wallpapers(filters)

    def update_status(self, count: int):
        self.status_label.set_text(f"{count} wallpapers")

    def _create_wallpaper_grid(self):
        """Create wallpaper grid display"""
        self.scroll = Gtk.ScrolledWindow()
        self.scroll.set_vexpand(True)

        # Create flow box for wallpaper grid
        self.wallpaper_grid = Gtk.FlowBox()
        self.wallpaper_grid.set_homogeneous(True)
        self.wallpaper_grid.set_min_children_per_line(4)
        self.wallpaper_grid.set_max_children_per_line(12)
        self.wallpaper_grid.set_column_spacing(12)
        self.wallpaper_grid.set_row_spacing(12)
        self.wallpaper_grid.set_selection_mode(Gtk.SelectionMode.NONE)
        self.scroll.set_child(self.wallpaper_grid)

        self.main_box.append(self.scroll)

    def _create_status_bar(self):
        status_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        status_box.add_css_class("status-bar")
        status_box.set_halign(Gtk.Align.CENTER)
        self.status_label = Gtk.Label(label="")
        status_box.append(self.status_label)
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
        self.view_model.connect("notify::selected-count", self._on_selection_changed)
        self.view_model.connect(
            "notify::current-wallpaper-path", self._on_current_wallpaper_changed
        )

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
        elif keyval == Gdk.KEY_Escape:
            self.view_model.clear_selection()
            return True
        # Home: Scroll to current wallpaper
        elif keyval == Gdk.KEY_Home:
            self.scroll_to_current_wallpaper()
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

    def _on_pull_swipe(self, gesture, dx, dy):
        """Handle pull-down gesture for refresh."""
        # Only trigger on vertical pull (dy < 0) and near top of scroll
        vadj = self.scroll.get_vadjustment()
        current_value = vadj.get_value()

        # Check if we're at the top of the scroll and pulling down
        if dy < -100 and current_value < 50 and not self.is_refreshing:
            self.is_refreshing = True
            schedule_async(self.view_model.refresh_wallpapers())

            GLib.timeout_add(1000, self._reset_refresh_flag)

    def _on_key_pressed(self, controller, keyval, keycode, state):
        if state & Gdk.ModifierType.CONTROL_MASK and keyval == Gdk.KEY_a:
            self.view_model.select_all()
            return True
        elif keyval == Gdk.KEY_Escape:
            self.view_model.clear_selection()
            return True
        elif keyval == Gdk.KEY_Home:
            self.scroll_to_current_wallpaper()
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

    def _on_current_wallpaper_changed(self, obj, pspec):
        """Handle current wallpaper path change - update card highlights."""
        self._update_current_wallpaper_highlight()

    def _update_current_wallpaper_highlight(self):
        """Update CSS classes to highlight the currently set wallpaper."""
        current_path = self.view_model.current_wallpaper_path
        if not current_path:
            return

        # Remove current-wallpaper class from all cards
        for _wallpaper, card in self._wallpaper_card_map.items():
            card.remove_css_class("current-wallpaper")

        # Add current-wallpaper class to matching card
        card = self._path_card_map.get(current_path)
        if card:
            card.add_css_class("current-wallpaper")

    def scroll_to_current_wallpaper(self):
        """Scroll the scrolled window to show the currently set wallpaper."""
        # Always refresh from symlink first to catch external changes
        self.view_model.refresh_current_wallpaper()

        current_path = self.view_model.current_wallpaper_path
        if not current_path:
            if self.toast_service:
                self.toast_service.show_info("No current wallpaper set")
            return

        target_path = current_path
        card = self._path_card_map.get(target_path)

        if not card:
            # Try matching by filename first
            current_filename = Path(current_path).name
            matched_path = self._find_path_by_filename(current_filename)
            if matched_path:
                target_path = matched_path
                card = self._path_card_map.get(target_path)

        if not card:
            # Try matching by content hash (handles awww cache copies)
            matched_path = self.view_model.find_wallpaper_by_hash(current_path)
            if matched_path:
                target_path = matched_path
                card = self._path_card_map.get(target_path)

        if not card:
            if not self._load_until_path_found(target_path):
                # Try hash match after loading more
                matched_path = self.view_model.find_wallpaper_by_hash(current_path)
                if matched_path:
                    target_path = matched_path

        card = self._path_card_map.get(target_path)
        if card:
            self._scroll_to_card(card)
        elif self.toast_service:
            self.toast_service.show_info("Current wallpaper not in list")

    def _find_path_by_filename(self, filename: str) -> str | None:
        """Find a wallpaper path by matching filename."""
        for wp in self._full_wallpapers:
            if wp.path.name == filename:
                return str(wp.path)
        return None

    def _load_until_path_found(self, target_path: str) -> bool:
        """Load more items until the target path is in the visible cards.

        Returns True if the path was found, False otherwise.
        """
        target_filename = Path(target_path).name

        has_match = any(str(wp.path) == target_path for wp in self._full_wallpapers)
        has_filename_match = any(wp.path.name == target_filename for wp in self._full_wallpapers)

        if not has_match and not has_filename_match:
            return False

        max_iterations = len(self._full_wallpapers) // PAGE_SIZE + 5
        for _ in range(max_iterations):
            if target_path in self._path_card_map:
                return True
            matched = self._find_path_by_filename(target_filename)
            if matched and matched in self._path_card_map:
                return True
            if not self._has_more_items:
                break
            self._load_more_items()

        return target_path in self._path_card_map or bool(
            self._find_path_by_filename(target_filename)
        )

    def _scroll_to_card(self, card):
        """Scroll the scrolled window to make the given card visible."""
        vadj = self.scroll.get_vadjustment()

        # Use translate_coordinates to get card position relative to scroll window
        result = card.translate_coordinates(self.scroll, 0, 0)
        if result is None:
            # Fallback: try to get allocation
            allocation = card.get_allocation()
            card_y = allocation.y
        else:
            card_x, card_y = result

        card_height = card.get_allocated_height()
        scroll_height = vadj.get_page_size()
        scroll_upper = vadj.get_upper()

        # Calculate scroll position to center the card
        new_y = card_y - (scroll_height - card_height) // 2

        # Clamp to valid range
        new_y = max(0, min(new_y, scroll_upper - scroll_height))

        # Set the scroll position
        vadj.set_value(new_y)

    def _on_set_all_selected(self):
        selected = self.view_model.get_selected_wallpapers()
        if not selected:
            return

        async def set_first():
            success, message = await self.view_model.set_wallpaper(selected[0])
            if success and self.toast_service:
                self.toast_service.show_success(message)
            elif self.toast_service:
                self.toast_service.show_error(message)

        schedule_async(set_first())
        self.view_model.clear_selection()

    def _on_folder_clicked(self, button):
        window = self.get_root()
        dialog = Gtk.FileDialog()
        dialog.set_title("Choose wallpapers folder")

        def on_folder_selected(dialog, result):
            try:
                folder = dialog.select_folder_finish(result)
                if folder:
                    path = Path(folder.get_path())

                    async def set_dir():
                        await self.view_model.set_pictures_dir(path)

                    schedule_async(set_dir())
            except (RuntimeError, TypeError) as e:
                import logging

                logger = logging.getLogger(__name__)
                logger.debug(f"Could not get folder path from dialog: {e}")

        dialog.select_folder(window, None, on_folder_selected)

    def _on_wallpapers_changed(self, obj, pspec):
        """Handle wallpapers property change with pagination."""
        wallpapers = self.view_model.wallpapers
        self._all_wallpapers = wallpapers
        self._full_wallpapers = wallpapers  # Keep full list for scroll-to-current
        self._visible_wallpapers = []
        self._current_page = 0
        self._has_more_items = len(wallpapers) > INITIAL_PAGE_SIZE

        # Clear existing grid
        self._clear_grid()

        # Load initial batch
        initial_batch = wallpapers[:INITIAL_PAGE_SIZE]
        for wallpaper in initial_batch:
            card = self._create_wallpaper_card(wallpaper)
            self.wallpaper_grid.append(card)

        self._visible_wallpapers = initial_batch
        self.update_status(len(wallpapers))

        # Refresh and highlight current wallpaper
        self.view_model.refresh_current_wallpaper()
        self._update_current_wallpaper_highlight()

    def update_wallpaper_grid(self, wallpapers):
        # With pagination, full rebuild handles everything
        self._on_wallpapers_changed(None, None)

    def _clear_grid(self):
        """Clear all cards from the grid."""
        child = self.wallpaper_grid.get_first_child()
        while child:
            next_child = child.get_next_sibling()
            self.wallpaper_grid.remove(child)
            self._remove_card_mappings(child)
            child = next_child
        self.card_wallpaper_map.clear()
        self._wallpaper_card_map.clear()
        self._path_card_map.clear()
        self._metadata_labels.clear()
        self._upscale_overlays.clear()

    def _rebuild_wallpaper_grid(self, wallpapers):
        child = self.wallpaper_grid.get_first_child()
        while child:
            next_child = child.get_next_sibling()
            self.wallpaper_grid.remove(child)
            child = next_child

        self.card_wallpaper_map.clear()
        self._wallpaper_card_map.clear()
        self._path_card_map.clear()
        self._metadata_labels.clear()
        self._upscale_overlays.clear()

        for wallpaper in wallpapers:
            card = self._create_wallpaper_card(wallpaper)
            self.wallpaper_grid.append(card)

    def _create_wallpaper_card(self, wallpaper):
        card = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        card.set_hexpand(True)
        card.add_css_class("wallpaper-card")

        # Make card focusable
        card.set_can_focus(True)
        card.set_focusable(True)

        # Store mapping for keyboard activation
        self.card_wallpaper_map[card] = wallpaper
        self._wallpaper_card_map[wallpaper] = card
        self._path_card_map[str(wallpaper.path)] = card

        gesture = Gtk.GestureClick()
        gesture.set_button(1)
        gesture.connect("pressed", self._on_card_clicked, wallpaper)
        card.add_controller(gesture)

        is_selected = wallpaper in self.view_model.get_selected_wallpapers()
        if is_selected:
            card.add_css_class("selected")
        if self.view_model.selection_mode:
            card.add_css_class("selection-mode")

        # Highlight current wallpaper
        current_path = self.view_model.current_wallpaper_path
        if current_path and str(wallpaper.path) == current_path:
            card.add_css_class("current-wallpaper")

        image = Gtk.Picture()
        image.set_size_request(200, 160)
        image.set_content_fit(Gtk.ContentFit.CONTAIN)
        image.add_css_class("wallpaper-thumb")

        # Create overlay container for image + spinner
        image_overlay = Gtk.Overlay()
        image_overlay.set_child(image)

        def on_thumbnail_loaded(texture):
            if texture:
                image.set_paintable(texture)

        thumb_path = str(wallpaper.path)
        if self.thumbnail_loader:
            self.thumbnail_loader.load_thumbnail_async(thumb_path, on_thumbnail_loaded)

        card.append(image_overlay)

        # Info box with filename and metadata
        info_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
        info_box.add_css_class("card-info-box")

        # Filename
        filename_label = Gtk.Label()
        filename_label.set_ellipsize(Pango.EllipsizeMode.END)
        filename_label.set_lines(1)
        filename_label.set_max_width_chars(35)
        filename_label.set_halign(Gtk.Align.CENTER)
        filename_label.set_text(wallpaper.filename)
        filename_label.add_css_class("filename-label")
        info_box.append(filename_label)

        # Metadata (resolution • size • aspect ratio)
        metadata_label = Gtk.Label()
        metadata_parts = []

        if wallpaper.resolution:
            metadata_parts.append(wallpaper.resolution)

        if wallpaper.size:
            size = wallpaper.size
            if size >= 1024 * 1024:
                size_str = f"{size / (1024 * 1024):.1f} MB"
            elif size >= 1024:
                size_str = f"{size / 1024:.1f} KB"
            else:
                size_str = f"{size} B"
            metadata_parts.append(size_str)

        metadata_label.set_text(" • ".join(metadata_parts) if metadata_parts else "")
        metadata_label.add_css_class("metadata-label")
        info_box.append(metadata_label)

        # Tags display
        tags_label = Gtk.Label()
        tags_label.add_css_class("tags-label")
        if wallpaper.tags:
            # Show first 5 tags, truncate if too many
            display_tags = wallpaper.tags[:5]
            tags_text = " ".join(f"#{tag}" for tag in display_tags)
            if len(wallpaper.tags) > 5:
                tags_text += f" +{len(wallpaper.tags) - 5}"
            tags_label.set_text(tags_text)
            tags_label.set_tooltip_text(" • ".join(wallpaper.tags))
        else:
            tags_label.set_text("No tags")
            tags_label.add_css_class("dim-label")
        info_box.append(tags_label)

        path_str = str(wallpaper.path)
        self._metadata_labels[path_str] = metadata_label
        self._tags_labels[path_str] = tags_label

        card.append(info_box)

        # Actions box
        actions_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        actions_box.add_css_class("card-actions-box")
        actions_box.set_halign(Gtk.Align.CENTER)

        set_btn = Gtk.Button(icon_name="image-x-generic-symbolic", tooltip_text="Set as wallpaper")
        set_btn.add_css_class("action-button")
        set_btn.add_css_class("suggested-action")
        set_btn.set_cursor_from_name("pointer")
        set_btn.connect("clicked", self._on_set_wallpaper, wallpaper)
        actions_box.append(set_btn)

        fav_btn = Gtk.Button(icon_name="starred-symbolic", tooltip_text="Add to favorites")
        fav_btn.add_css_class("action-button")
        fav_btn.add_css_class("favorite-action")
        fav_btn.set_cursor_from_name("pointer")
        fav_btn.connect("clicked", self._on_add_to_favorites, wallpaper)
        actions_box.append(fav_btn)

        delete_btn = Gtk.Button(icon_name="user-trash-symbolic", tooltip_text="Delete")
        delete_btn.add_css_class("action-button")
        delete_btn.add_css_class("destructive-action")
        delete_btn.set_cursor_from_name("pointer")
        delete_btn.connect("clicked", self._on_delete_wallpaper, wallpaper)
        actions_box.append(delete_btn)

        # Show upscale button only if enabled in config
        if self._is_upscaler_enabled():
            upscale_btn = Gtk.Button(icon_name="zoom-in-symbolic", tooltip_text="Upscale 2x (AI)")
            upscale_btn.add_css_class("action-button")
            upscale_btn.set_cursor_from_name("pointer")
            upscale_btn.connect("clicked", self._on_upscale_wallpaper, wallpaper)
            actions_box.append(upscale_btn)

        # Show tag button
        tag_btn = Gtk.Button(icon_name="tag-symbolic", tooltip_text="Generate AI tags")
        tag_btn.add_css_class("action-button")
        tag_btn.set_cursor_from_name("pointer")
        tag_btn.connect("clicked", self._on_generate_tags, wallpaper)
        actions_box.append(tag_btn)

        card.append(actions_box)
        return card

    def _is_upscaler_enabled(self) -> bool:
        """Returns True if upscaler is enabled in config."""
        if not self.config_service:
            return False
        config = self.config_service.get_config()
        return config.upscaler_enabled if config else False

    def _on_card_clicked(self, gesture, n_press, x, y, wallpaper):
        if n_press == 2:
            self._on_set_wallpaper(None, wallpaper)

    def _on_selection_toggled(self, wallpaper, is_selected):
        self.view_model.toggle_selection(wallpaper)

    def _on_set_wallpaper(self, button, wallpaper):
        async def set_wallpaper():
            success, message = await self.view_model.set_wallpaper(wallpaper)
            if success:
                if self.toast_service:
                    self.toast_service.show_success(message)
            else:
                if self.toast_service:
                    self.toast_service.show_error(message)

        schedule_async(set_wallpaper())

    def _on_add_to_favorites(self, button, wallpaper):
        async def add_to_favorites():
            success, message = await self.view_model.add_to_favorites(wallpaper)
            if success:
                if self.toast_service:
                    self.toast_service.show_success(message)
            else:
                if self.toast_service:
                    self.toast_service.show_error(message)

        schedule_async(add_to_favorites())

    def _on_delete_wallpaper(self, button, wallpaper):
        window = self.get_root()

        dialog = Adw.MessageDialog(
            transient_for=window,
            heading="Delete wallpaper?",
            body=f"Are you sure you want to delete '{wallpaper.filename}'?\nThis action cannot be undone.",
        )
        dialog.add_response("cancel", "Cancel")
        dialog.add_response("delete", "Delete")
        dialog.set_response_appearance("delete", Adw.ResponseAppearance.DESTRUCTIVE)
        dialog.set_default_response("cancel")
        dialog.set_close_response("cancel")

        def on_response(dialog, response):
            if response == "delete":

                async def delete_wallpaper():
                    success, message = await self.view_model.delete_wallpaper(wallpaper)
                    if success:
                        if self.toast_service:
                            self.toast_service.show_success(message)
                        self.update_status(len(self.view_model.wallpapers))
                    else:
                        if self.toast_service:
                            self.toast_service.show_error(message)

                schedule_async(delete_wallpaper())

        dialog.connect("response", on_response)
        dialog.present()

    def _on_upscale_wallpaper(self, button, wallpaper):
        success, message = self.view_model.queue_upscale(wallpaper)
        if success:
            card = self._wallpaper_card_map.get(wallpaper)
            if card:
                self._show_upscale_overlay(card)
            if self.toast_service:
                self.toast_service.show_info(message)
        else:
            if self.toast_service:
                self.toast_service.show_error(message)

    def _on_generate_tags(self, button, wallpaper):
        success, message = self.view_model.queue_generate_tags(wallpaper)
        if success:
            card = self._wallpaper_card_map.get(wallpaper)
            if card:
                self._show_tag_overlay(card)
            if self.toast_service:
                self.toast_service.show_info(message)
        else:
            if self.toast_service:
                self.toast_service.show_error(message)

    def _show_tag_overlay(self, card):
        """Show blocking overlay with spinner on the card's image."""
        if card in self._tag_overlays:
            return

        image_overlay = None
        child = card.get_first_child()
        while child:
            if isinstance(child, Gtk.Overlay):
                image_overlay = child
                break
            child = child.get_next_sibling()

        if not image_overlay:
            return

        overlay = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        overlay.add_css_class("upscale-overlay-small")
        overlay.set_halign(Gtk.Align.CENTER)
        overlay.set_valign(Gtk.Align.CENTER)

        spinner = Gtk.Spinner(spinning=True)
        spinner.set_size_request(24, 24)
        overlay.append(spinner)

        image_overlay.add_overlay(overlay)
        self._tag_overlays[card] = overlay

    def _hide_tag_overlay(self, card):
        """Hide blocking overlay from the card."""
        if card not in self._tag_overlays:
            return

        overlay = self._tag_overlays.pop(card)

        image_overlay = None
        child = card.get_first_child()
        while child:
            if isinstance(child, Gtk.Overlay):
                image_overlay = child
                break
            child = child.get_next_sibling()

        if image_overlay:
            image_overlay.remove_overlay(overlay)

    def _on_tagging_complete(self, view_model, success: bool, message: str, wallpaper_path: str):
        """Handle tagging completion."""
        if success:
            if self.toast_service:
                self.toast_service.show_success(message)
            card = self._path_card_map.get(wallpaper_path)
            if card:
                self._hide_tag_overlay(card)
                self._refresh_wallpaper_card_by_path(wallpaper_path)
            else:
                for wp in self.view_model.wallpapers:
                    if wp in self._wallpaper_card_map:
                        card = self._wallpaper_card_map[wp]
                        self._hide_tag_overlay(card)
                        self._refresh_wallpaper_card(wp)
                        break
        else:
            if self.toast_service:
                self.toast_service.show_error(message)
            card = self._path_card_map.get(wallpaper_path)
            if card:
                self._hide_tag_overlay(card)

    def _on_tagging_queue_changed(self, view_model, queue_size: int, active_count: int):
        """Handle tagging queue changes."""
        if queue_size == 0 and active_count == 0:
            if self.toast_service:
                self.toast_service.show_info("All tags generated")

    def _show_upscale_overlay(self, card):
        """Show blocking overlay with spinner on the card's image."""
        if card in self._upscale_overlays:
            return

        # Find the image_overlay in the card
        image_overlay = None
        child = card.get_first_child()
        while child:
            if isinstance(child, Gtk.Overlay):
                image_overlay = child
                break
            child = child.get_next_sibling()

        if not image_overlay:
            return

        # Create overlay widget
        overlay = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        overlay.add_css_class("upscale-overlay-small")
        overlay.set_halign(Gtk.Align.CENTER)
        overlay.set_valign(Gtk.Align.CENTER)

        # Spinner
        spinner = Gtk.Spinner(spinning=True)
        spinner.set_size_request(24, 24)
        overlay.append(spinner)

        # Add to image overlay (stacked on top, no layout impact)
        image_overlay.add_overlay(overlay)
        self._upscale_overlays[card] = overlay

    def _hide_upscale_overlay(self, card):
        """Hide blocking overlay from the card."""
        if card not in self._upscale_overlays:
            return

        overlay = self._upscale_overlays.pop(card)

        # Find the image_overlay
        image_overlay = None
        child = card.get_first_child()
        while child:
            if isinstance(child, Gtk.Overlay):
                image_overlay = child
                break
            child = child.get_next_sibling()

        if image_overlay:
            image_overlay.remove_overlay(overlay)

    def _on_upscale_complete(self, view_model, success: bool, message: str, wallpaper_path: str):
        """Handle upscaling completion."""
        if success:
            if self.toast_service:
                self.toast_service.show_success(message)
            # Find and refresh the card by path
            card = self._path_card_map.get(wallpaper_path)
            if card:
                self._hide_upscale_overlay(card)
                self._refresh_wallpaper_card_by_path(wallpaper_path)
            else:
                # Fallback: search in wallpaper map
                for wp in self.view_model.wallpapers:
                    if wp in self._wallpaper_card_map:
                        card = self._wallpaper_card_map[wp]
                        self._hide_upscale_overlay(card)
                        self._refresh_wallpaper_card(wp)
                        break
        else:
            if self.toast_service:
                self.toast_service.show_error(message)
            # Hide overlay even on failure
            for wp in self.view_model.wallpapers:
                if wp in self._wallpaper_card_map:
                    card = self._wallpaper_card_map[wp]
                    if card in self._upscale_overlays:
                        self._hide_upscale_overlay(card)
                    break

    def _on_queue_changed(self, view_model, queue_size: int, active_count: int):
        """Handle queue status changes."""
        if queue_size == 0 and active_count == 0:
            if self.toast_service:
                self.toast_service.show_info("All upscaling complete")
        elif active_count > 0:
            if self.toast_service:
                if queue_size > 0:
                    self.toast_service.show_info(
                        f"Upscaling {active_count} item(s), {queue_size} in queue..."
                    )
                else:
                    self.toast_service.show_info(f"Upscaling {active_count} item(s)...")

    def _refresh_wallpaper_card(self, wallpaper):
        """Refresh a single wallpaper card with visual flash effect."""
        card = self._wallpaper_card_map.get(wallpaper)
        if not card:
            return

        # Get the image widget (first child after any overlays)
        image = card.get_first_child()
        if not image:
            return

        # Load new thumbnail
        def on_thumbnail_loaded(texture):
            if texture:
                image.set_paintable(texture)

        if self.thumbnail_loader:
            self.thumbnail_loader.load_thumbnail_async(str(wallpaper.path), on_thumbnail_loaded)

        # Add flash effect
        card.add_css_class("flash-animation")
        GLib.timeout_add(100, lambda: card.remove_css_class("flash-animation"))
        GLib.timeout_add(200, lambda: card.add_css_class("flash-animation"))
        GLib.timeout_add(300, lambda: card.remove_css_class("flash-animation"))

    def _refresh_wallpaper_card_by_path(self, path: str):
        """Refresh a wallpaper card by path string."""
        card = self._path_card_map.get(path)
        if not card:
            return

        wallpaper = None
        for wp in self.view_model.wallpapers:
            if str(wp.path) == path:
                wallpaper = wp
                break

        metadata_label = self._metadata_labels.get(path)
        if metadata_label:
            try:
                import os

                from PIL import Image

                file_path = path
                file_stat = os.stat(file_path)

                resolution_text = ""
                try:
                    with Image.open(file_path) as img:
                        width, height = img.size
                        resolution_text = f"{width}x{height}"
                except Exception:
                    pass

                size = file_stat.st_size
                if size >= 1024 * 1024:
                    size_str = f"{size / (1024 * 1024):.1f} MB"
                elif size >= 1024:
                    size_str = f"{size / 1024:.1f} KB"
                else:
                    size_str = f"{size} B"

                parts = []
                if resolution_text:
                    parts.append(resolution_text)
                parts.append(size_str)
                metadata_label.set_text(" • ".join(parts) if parts else "")
            except Exception:
                pass

        tags_label = self._tags_labels.get(path)
        if tags_label and wallpaper:
            if wallpaper.tags:
                display_tags = wallpaper.tags[:5]
                tags_text = " ".join(f"#{tag}" for tag in display_tags)
                if len(wallpaper.tags) > 5:
                    tags_text += f" +{len(wallpaper.tags) - 5}"
                tags_label.set_text(tags_text)
                tags_label.set_tooltip_text(" • ".join(wallpaper.tags))
                tags_label.remove_css_class("dim-label")
            else:
                tags_label.set_text("No tags")
                tags_label.add_css_class("dim-label")

        card.add_css_class("flash-animation")
        GLib.timeout_add(100, lambda: card.remove_css_class("flash-animation"))
        GLib.timeout_add(200, lambda: card.add_css_class("flash-animation"))
        GLib.timeout_add(300, lambda: card.remove_css_class("flash-animation"))

    def _reset_refresh_flag(self):
        """Reset refreshing flag."""
        self.is_refreshing = False
        return False

"""View for favorites management."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")

from gi.repository import Adw, Gdk, GLib, Gtk, Pango  # noqa: E402

from ui.components.search_filter_bar import SearchFilterBar
from ui.view_models.favorites_view_model import FavoritesViewModel


class FavoritesView(Adw.Bin):
    """View for favorites wallpaper browsing with adaptive layout"""

    def __init__(
        self,
        view_model: FavoritesViewModel,
        banner_service=None,
        on_set_wallpaper=None,
        on_remove_favorite=None,
    ):
        super().__init__()
        self.view_model = view_model
        self.banner_service = banner_service
        self.on_set_wallpaper = on_set_wallpaper
        self.on_remove_favorite = on_remove_favorite
        self.card_wallpaper_map = {}
        self._last_selected_wallpaper = None

        self._create_ui()

        self._setup_keyboard_shortcuts()
        self._bind_to_view_model()

    def _create_ui(self):
        """Create main UI structure"""
        self.main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        self.set_child(self.main_box)

        self._create_toolbar()
        self._create_wallpapers_grid()
        self._create_status_bar()

    def _create_toolbar(self):
        toolbar_wrapper = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        toolbar_wrapper.add_css_class("toolbar-wrapper")
        self.main_box.append(toolbar_wrapper)

        self.search_filter_bar = SearchFilterBar(
            tab_type="favorites",
            on_search_changed=self._on_search_changed,
        )
        toolbar_wrapper.append(self.search_filter_bar)

        self.loading_spinner = Gtk.Spinner(spinning=False)
        toolbar_wrapper.append(self.loading_spinner)

    def _on_search_changed(self, search_text):
        """Handle search text changes."""
        self.view_model.search_query = search_text

    def _create_wallpapers_grid(self):
        """Create wallpapers grid display"""
        self.scroll = Gtk.ScrolledWindow()
        self.scroll.set_vexpand(True)

        # Create flow box for wallpapers grid
        self.wallpapers_grid = Gtk.FlowBox()
        self.wallpapers_grid.set_homogeneous(True)
        self.wallpapers_grid.set_min_children_per_line(2)
        self.wallpapers_grid.set_max_children_per_line(12)
        self.wallpapers_grid.set_column_spacing(12)
        self.wallpapers_grid.set_row_spacing(12)
        self.wallpapers_grid.set_selection_mode(Gtk.SelectionMode.NONE)
        self.scroll.set_child(self.wallpapers_grid)

        self.main_box.append(self.scroll)

    def _create_status_bar(self):
        status_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        status_box.add_css_class("status-bar")
        status_box.set_halign(Gtk.Align.CENTER)
        self.status_label = Gtk.Label(label="")
        status_box.append(self.status_label)
        self.main_box.append(status_box)

    def _bind_to_view_model(self):
        """Bind to ViewModel state changes"""
        self.view_model.connect("notify::favorites", self._on_favorites_changed)
        self.view_model.connect("notify::is-busy", self._on_busy_changed)
        self.view_model.connect("notify::error-message", self._on_error_changed)
        self.view_model.connect("notify::selected-count", self._on_selection_changed)

        self._on_favorites_changed()

    def _setup_keyboard_shortcuts(self):
        key_controller = Gtk.EventControllerKey()
        key_controller.connect("key-pressed", self._on_key_pressed)
        self.add_controller(key_controller)

        # Setup grid navigation
        self._setup_grid_navigation()

    def _setup_grid_navigation(self):
        """Setup keyboard navigation for wallpapers grid."""
        # Add key controller to flow box for arrow key navigation
        grid_key_controller = Gtk.EventControllerKey()
        grid_key_controller.connect("key-pressed", self._on_grid_key_pressed)
        self.wallpapers_grid.add_controller(grid_key_controller)

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
            focused = self.wallpapers_grid.get_focus_child()
            if focused and focused in self.card_wallpaper_map:
                wallpaper = self.card_wallpaper_map[focused]
                self.view_model.set_wallpaper(wallpaper)
            return True
        # Space: Toggle favorite (remove from favorites)
        elif keyval == Gdk.KEY_space:
            focused = self.wallpapers_grid.get_focus_child()
            if focused and focused in self.card_wallpaper_map:
                wallpaper = self.card_wallpaper_map[focused]
                self.view_model.remove_favorite(wallpaper)
            return True
        # Escape: Clear selection and remove focus
        elif keyval == Gdk.KEY_Escape:
            self.view_model.clear_selection()
            return True
        return False

    def _focus_next_card(self):
        """Focus next card in grid."""
        current = self.wallpapers_grid.get_focus_child()
        if not current:
            # Focus first card if none focused
            first = self.wallpapers_grid.get_first_child()
            if first:
                first.grab_focus()
            return

        # Get all children
        children = []
        child = self.wallpapers_grid.get_first_child()
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
        current = self.wallpapers_grid.get_focus_child()
        if not current:
            # Focus last card if none focused
            last = self.wallpapers_grid.get_first_child()
            while last and last.get_next_sibling():
                last = last.get_next_sibling()
            if last:
                last.grab_focus()
            return

        # Get all children
        children = []
        child = self.wallpapers_grid.get_first_child()
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

        # Check if we're at the top of scroll and pulling down
        if dy < -100 and current_value < 50 and not self.is_refreshing:
            self.is_refreshing = True
            self.view_model.load_favorites()

            # Reset flag after a delay
            GLib.timeout_add(1000, self._reset_refresh_flag)

    def _reset_refresh_flag(self):
        """Reset refreshing flag."""
        self.is_refreshing = False
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
        for favorite in selected:
            self.view_model.set_wallpaper(favorite)
            break
        self.view_model.clear_selection()

    def _on_favorites_changed(self, *args):
        """Handle favorites list changes"""
        self.update_wallpapers_grid()
        self.update_status()

    def _on_busy_changed(self, *args):
        """Handle busy state changes"""
        self.loading_spinner.set_spinning(self.view_model.is_busy)

    def _on_error_changed(self, *args):
        """Handle error message changes"""
        # Error handling can be added here if needed

    def update_wallpapers_grid(self):
        """Update wallpapers grid display"""
        # Clear existing cards
        while self.wallpapers_grid.get_first_child():
            self.wallpapers_grid.remove(self.wallpapers_grid.get_first_child())

        # Clear card->wallpaper mapping
        self.card_wallpaper_map.clear()

        # Add new cards
        for favorite in self.view_model.favorites:
            card = self._create_wallpaper_card(favorite)
            self.wallpapers_grid.append(card)

    def update_status(self):
        """Update status bar"""
        count = len(self.view_model.favorites)
        self.status_label.set_text(f"{count} favorites")

    def _create_wallpaper_card(self, favorite):
        """Create wallpaper card with image and actions"""
        card = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        card.set_hexpand(True)
        card.add_css_class("wallpaper-card")

        # Make card focusable
        card.set_can_focus(True)
        card.set_focusable(True)

        # Store mapping for keyboard activation
        self.card_wallpaper_map[card] = favorite.wallpaper

        wallpaper = favorite.wallpaper
        is_selected = wallpaper in self.view_model.get_selected_wallpapers()
        if is_selected:
            card.add_css_class("selected")
        if self.view_model.selection_mode:
            card.add_css_class("selection-mode")

        gesture = Gtk.GestureClick()
        gesture.set_button(1)
        gesture.connect("pressed", self._on_card_clicked, favorite, card)
        card.add_controller(gesture)

        image = Gtk.Picture()
        image.set_size_request(200, 160)
        image.set_content_fit(Gtk.ContentFit.CONTAIN)
        image.add_css_class("wallpaper-thumb")
        image.set_tooltip_text(
            Path(wallpaper.path).name if hasattr(wallpaper, "path") else "Favorite"
        )

        def on_thumbnail_loaded(texture):
            if texture:
                image.set_paintable(texture)

        self.view_model.load_thumbnail_async(str(wallpaper.path), on_thumbnail_loaded)

        card.append(image)

        # Info box with filename and metadata
        info_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
        info_box.add_css_class("card-info-box")

        # Filename
        filename_label = Gtk.Label()
        filename_label.set_ellipsize(Pango.EllipsizeMode.END)
        filename_label.set_lines(1)
        filename_label.set_max_width_chars(20)
        filename_label.set_xalign(0)
        filename_label.set_text(
            Path(wallpaper.path).name if hasattr(wallpaper, "path") else wallpaper.filename
        )
        filename_label.add_css_class("filename-label")
        info_box.append(filename_label)

        metadata_label = Gtk.Label()
        metadata_parts = []

        if hasattr(wallpaper, "resolution") and wallpaper.resolution:
            metadata_parts.append(str(wallpaper.resolution))

        if hasattr(wallpaper, "file_size") and wallpaper.file_size:
            size = wallpaper.file_size
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

        card.append(info_box)

        # Actions box
        actions_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        actions_box.add_css_class("card-actions-box")
        actions_box.set_halign(Gtk.Align.CENTER)

        set_btn = Gtk.Button(icon_name="image-x-generic-symbolic", tooltip_text="Set as wallpaper")
        set_btn.add_css_class("action-button")
        set_btn.add_css_class("suggested-action")
        set_btn.set_cursor_from_name("pointer")
        set_btn.connect("clicked", self._on_set_wallpaper, favorite)
        actions_box.append(set_btn)

        remove_btn = Gtk.Button(icon_name="user-trash-symbolic", tooltip_text="Remove")
        remove_btn.add_css_class("action-button")
        remove_btn.add_css_class("destructive-action")
        remove_btn.set_cursor_from_name("pointer")
        remove_btn.connect("clicked", self._on_remove_favorite, favorite)
        actions_box.append(remove_btn)

        card.append(actions_box)
        return card

    def _on_card_clicked(self, gesture, n_press, x, y, favorite, card):
        if self.view_model.selection_mode and n_press == 1:
            wallpaper = favorite.wallpaper
            self.view_model.toggle_selection(wallpaper)
            self.update_wallpapers_grid()
        elif n_press == 2:
            self._on_set_wallpaper(None, favorite)
            if self.view_model.selection_mode:
                self.update_wallpapers_grid()

    def _on_selection_toggled(self, wallpaper, is_selected):
        self.view_model.toggle_selection(wallpaper)

    def _on_set_wallpaper(self, button, favorite):
        """Handle set wallpaper button click"""
        self.view_model.set_wallpaper(favorite)

    def _on_search_changed(self, search_text):
        """Handle search text changes."""
        self.view_model.search_query = search_text

    def _on_remove_favorite(self, button, favorite):
        window = self.get_root()

        dialog = Adw.MessageDialog(
            transient_for=window,
            modal=True,
            heading="Remove favorite?",
            body=f"Are you sure you want to remove '{favorite.wallpaper.id}' from favorites?",
        )
        dialog.add_response("cancel", "Cancel")
        dialog.add_response("remove", "Remove")
        dialog.set_response_appearance("remove", Adw.ResponseAppearance.DESTRUCTIVE)
        dialog.set_default_response("cancel")
        dialog.set_close_response("cancel")

        def on_response(dialog, response):
            if response == "remove":
                self.view_model.remove_favorite(favorite.wallpaper_id)
            dialog.destroy()

        dialog.connect("response", on_response)
        dialog.present()

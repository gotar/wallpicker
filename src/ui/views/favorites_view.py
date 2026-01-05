"""View for favorites management."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import gi

gi.require_version("Gtk", "4.0")

from gi.repository import GObject, Gtk

from ui.view_models.favorites_view_model import FavoritesViewModel


class FavoritesView(Gtk.Box):
    """View for favorites management"""

    def __init__(self, view_model: FavoritesViewModel):
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        self.view_model = view_model

        # Create UI components
        self._create_toolbar()
        self._create_favorites_list()

        # Bind to ViewModel state
        self._bind_to_view_model()

    def _create_toolbar(self):
        """Create toolbar with actions"""
        toolbar = Gtk.Box(
            orientation=Gtk.Orientation.HORIZONTAL,
            spacing=12,
        )
        toolbar.add_css_class("filter-bar")

        # Refresh button
        refresh_btn = Gtk.Button(icon_name="view-refresh-symbolic", tooltip_text="Refresh")
        refresh_btn.connect("clicked", self._on_refresh_clicked)
        toolbar.append(refresh_btn)

        # Loading spinner
        self.loading_spinner = Gtk.Spinner(spinning=False)
        toolbar.append(self.loading_spinner)

        # Spacer
        spacer = Gtk.Label()
        spacer.set_hexpand(True)
        toolbar.append(spacer)

        # Search entry
        self.search_entry = Gtk.SearchEntry(placeholder_text="Search favorites...")
        self.search_entry.connect("search-changed", self._on_search_changed)
        toolbar.append(self.search_entry)

        # Status label
        self.status_label = Gtk.Label(label="")
        toolbar.append(self.status_label)

        # Error label
        self.error_label = Gtk.Label(wrap=True)
        self.error_label.add_css_class("error")
        self.error_label.set_visible(False)
        toolbar.append(self.error_label)

        # Search debounce timer
        self._search_timer = None

        self.append(toolbar)

    def _create_favorites_list(self):
        """Create favorites list/grid display"""
        self.scroll = Gtk.ScrolledWindow()
        self.scroll.set_vexpand(True)

        # Create flow box for favorites grid
        self.favorites_grid = Gtk.FlowBox()
        self.favorites_grid.set_homogeneous(True)
        self.favorites_grid.set_max_children_per_line(4)
        self.favorites_grid.set_selection_mode(Gtk.SelectionMode.NONE)
        self.scroll.set_child(self.favorites_grid)

        self.append(self.scroll)

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
        self.view_model.connect("notify::favorites", self._on_favorites_changed)

    def _on_refresh_clicked(self, button):
        """Handle refresh button click"""
        self.view_model.refresh_favorites()

    def _on_search_changed(self, entry):
        """Handle search entry change with debounce"""
        if self._search_timer:
            GObject.source_remove(self._search_timer)

        query = entry.get_text()
        self._search_timer = GObject.timeout_add(500, self._do_search, query)

    def _do_search(self, query):
        """Execute search after debounce"""
        self._search_timer = None
        self.view_model.search_favorites(query)
        return False

    def _on_favorites_changed(self, obj, pspec):
        """Handle favorites property change"""
        self.update_favorites_grid(self.view_model.favorites)
        self.update_status(len(self.view_model.favorites))

    def update_favorites_grid(self, favorites):
        """Update favorites grid with new favorites"""
        while child := self.favorites_grid.get_first_child():
            self.favorites_grid.remove(child)

        for wallpaper in favorites:
            card = self._create_favorite_card(wallpaper)
            self.favorites_grid.append(card)

    def _create_favorite_card(self, wallpaper):
        """Create favorite card with image and actions"""
        card = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        card.set_size_request(180, 180)

        image = Gtk.Image()
        image.set_size_request(180, 180)
        image.add_css_class("wallpaper-thumb")

        def on_thumbnail_loaded(texture):
            if texture:
                image.set_paintable(texture)

        self.view_model.load_thumbnail_async(str(wallpaper.path), on_thumbnail_loaded)

        overlay = Gtk.Overlay()
        overlay.set_child(image)
        card.append(overlay)

        actions_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=4)

        set_btn = Gtk.Button(icon_name="wallpaper-symbolic", tooltip_text="Set as wallpaper")
        set_btn.add_css_class("action-button")
        set_btn.connect("clicked", self._on_set_wallpaper, wallpaper)
        actions_box.append(set_btn)

        remove_btn = Gtk.Button(icon_name="user-trash-symbolic", tooltip_text="Remove")
        remove_btn.add_css_class("destructive-action")
        remove_btn.connect("clicked", self._on_remove_favorite, wallpaper)
        actions_box.append(remove_btn)

        card.append(actions_box)
        return card

    def _on_set_wallpaper(self, button, wallpaper):
        """Handle set wallpaper button click"""
        import threading

        threading.Thread(
            target=lambda: self.view_model.set_wallpaper(wallpaper), daemon=True
        ).start()

    def _on_remove_favorite(self, button, wallpaper):
        """Handle remove button click"""
        dialog = Gtk.MessageDialog(
            transient_for=self,
            modal=True,
            message_type=Gtk.MessageType.QUESTION,
            buttons=Gtk.ButtonsType.YES_NO,
            text="Remove from favorites?",
            secondary_text=f"Are you sure you want to remove '{Path(wallpaper.path).name}' from favorites?",
        )

        def on_response(dialog, response):
            dialog.destroy()
            if response == Gtk.ResponseType.YES:
                self.view_model.remove_favorite(wallpaper.id)

        dialog.connect("response", on_response)
        dialog.present()

    def update_status(self, count: int):
        """Update status label"""
        self.status_label.set_text(f"{count} favorites")

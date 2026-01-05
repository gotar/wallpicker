"""View for local wallpaper browsing."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import gi

gi.require_version("Gtk", "4.0")

from gi.repository import Adw, GObject, Gtk

from ui.view_models.local_view_model import LocalViewModel


class LocalView(Gtk.Box):
    """View for local wallpaper browsing"""

    def __init__(self, view_model: LocalViewModel):
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        self.view_model = view_model

        # Create UI components
        self._create_toolbar()
        self._create_wallpaper_grid()

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

        # Status label
        self.status_label = Gtk.Label(label="")
        toolbar.append(self.status_label)

        # Error label
        self.error_label = Gtk.Label(wrap=True)
        self.error_label.add_css_class("error")
        self.error_label.set_visible(False)
        toolbar.append(self.error_label)

        self.append(toolbar)

    def update_status(self, count: int):
        """Update status label with wallpaper count"""
        self.status_label.set_label(f"{count} wallpapers")

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

    def _on_refresh_clicked(self, button):
        """Handle refresh button click"""
        self.view_model.refresh_wallpapers()

    def _on_wallpapers_changed(self, obj, pspec):
        """Handle wallpapers property change"""
        self.update_wallpaper_grid(self.view_model.wallpapers)
        self.update_status(len(self.view_model.wallpapers))

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

        # Use Picture for better scaling with aspect ratio
        image = Gtk.Picture()
        image.set_size_request(220, 160)
        image.set_content_fit(Gtk.ContentFit.CONTAIN)  # Keep aspect ratio
        image.add_css_class("wallpaper-thumb")

        def on_thumbnail_loaded(texture):
            if texture:
                image.set_paintable(texture)

        self.view_model.load_thumbnail_async(str(wallpaper.path), on_thumbnail_loaded)

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

        delete_btn = Gtk.Button(icon_name="user-trash-symbolic", tooltip_text="Delete")
        delete_btn.add_css_class("destructive-action")
        delete_btn.connect("clicked", self._on_delete_wallpaper, wallpaper)
        actions_box.append(delete_btn)

        card.append(actions_box)
        return card

    def _on_set_wallpaper(self, button, wallpaper):
        """Handle set wallpaper button click"""
        # Run synchronously since WallpaperSetter.set_wallpaper is sync
        result = self.view_model.wallpaper_setter.set_wallpaper(str(wallpaper.path))
        if not result:
            print(f"Failed to set wallpaper: {wallpaper.path}")

    def _on_add_to_favorites(self, button, wallpaper):
        """Handle add to favorites button click"""
        # TODO: Connect to FavoritesService when available
        print(f"Added to favorites: {wallpaper.filename}")

    def _on_delete_wallpaper(self, button, wallpaper):
        """Handle delete button click"""
        # Get the top-level window
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
                result = self.view_model.delete_wallpaper(wallpaper)
                if result:
                    self.update_status(len(self.view_model.wallpapers))

        dialog.connect("response", on_response)
        dialog.present()

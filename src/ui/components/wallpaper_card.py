"""Modern Wallpaper Card Component with hover animations and selection states."""

from fractions import Fraction
from pathlib import Path

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
gi.require_version("Gdk", "4.0")
gi.require_version("Pango", "1.0")

from gi.repository import Gdk, Gtk, Pango  # noqa: E402


class WallpaperCard(Gtk.Box):
    """Modern wallpaper card with hover animations and selection states."""

    __gtype_name__ = "WallpaperCard"

    def __init__(
        self,
        wallpaper,
        on_set_wallpaper=None,
        on_add_to_favorites=None,
        on_download=None,
        on_delete=None,
        on_info=None,
        is_favorite=False,
        is_current=False,
        is_selected=False,
        selection_mode=False,
    ):
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=0)

        self.wallpaper = wallpaper
        self.on_set_wallpaper = on_set_wallpaper
        self.on_add_to_favorites = on_add_to_favorites
        self.on_download = on_download
        self.on_delete = on_delete
        self.on_info = on_info

        self.is_favorite = is_favorite
        self.is_current = is_current
        self.is_selected = is_selected
        self.selection_mode = selection_mode

        self.checkbox = None

        self.add_css_class("wallpaper-card")
        self.set_size_request(280, 200)

        # Accessibility: Set accessible role and name for card
        self.set_accessible_role(Gtk.AccessibleRole.GROUP)
        self.set_accessible_name(self._get_accessible_name())
        self.set_accessible_description(self._get_accessible_description())

        self._create_gestures()

        self._create_image()
        self._create_info_row()
        self._create_actions_bar()

        self._update_card_state()

    def _create_gestures(self):
        click = Gtk.GestureClick()
        click.set_button(1)
        click.connect("pressed", self._on_card_pressed)
        self.add_controller(click)

        long_press = Gtk.GestureLongPress()
        long_press.set_propagation_phase(Gtk.PropagationPhase.BUBBLE)
        long_press.set_touch_only(True)
        long_press.connect("pressed", self._on_long_press)
        self.add_controller(long_press)

        self.add_css_class("touch-feedback")

    def _on_card_pressed(self, gesture, n_press, x, y):
        if self.selection_mode and n_press == 1 and self.checkbox and not self.checkbox.has_focus():
            self.checkbox.set_active(not self.checkbox.get_active())
        elif n_press == 2:
            if self.on_set_wallpaper:
                self.on_set_wallpaper()
                if self.selection_mode and self.checkbox:
                    self.checkbox.set_active(not self.checkbox.get_active())

    def _on_long_press(self, gesture, x, y):
        if self.on_info:
            self.on_info()

    def _create_image(self):
        overlay = Gtk.Overlay()
        overlay.set_vexpand(True)

        self.image = Gtk.Picture()
        self.image.set_size_request(260, 140)
        self.image.set_content_fit(Gtk.ContentFit.COVER)
        self.image.add_css_class("wallpaper-thumb")
        self.image.set_halign(Gtk.Align.CENTER)
        self.image.set_valign(Gtk.Align.CENTER)

        # Accessibility: Alt text for image
        filename = self._get_filename()
        self.image.set_accessible_name(f"Wallpaper thumbnail: {filename}")
        self.image.set_accessible_role(Gtk.AccessibleRole.IMG)

        if hasattr(self.wallpaper, "thumbnail_url") and self.wallpaper.thumbnail_url:
            self._load_thumbnail_async(self.wallpaper.thumbnail_url)
        elif hasattr(self.wallpaper, "path") and self.wallpaper.path:
            self._load_thumbnail_async(str(self.wallpaper.path))

        overlay.set_child(self.image)

        self.checkbox = Gtk.CheckButton()
        self.checkbox.add_css_class("selection-checkbox")
        self.checkbox.set_halign(Gtk.Align.START)
        self.checkbox.set_valign(Gtk.Align.START)
        self.checkbox.set_margin_start(8)
        self.checkbox.set_margin_top(8)
        self.checkbox.set_active(self.is_selected)
        self.checkbox.connect("toggled", self._on_checkbox_toggled)

        # Accessibility: Checkbox labels
        self.checkbox.set_accessible_name(f"Select {filename}")
        self.checkbox.set_accessible_role(Gtk.AccessibleRole.CHECK_BOX)
        overlay.add_overlay(self.checkbox)
        self._update_checkbox_visibility()

        self.append(overlay)

    def _on_checkbox_toggled(self, checkbox):
        if hasattr(self, "on_selection_toggled"):
            self.is_selected = checkbox.get_active()
            self.on_selection_toggled(self.wallpaper, self.is_selected)
            self._update_card_state()

    def _update_checkbox_visibility(self):
        if self.checkbox:
            if self.selection_mode:
                self.checkbox.set_visible(True)
                self.checkbox.set_opacity(1)
            else:
                self.checkbox.set_visible(False)
                self.checkbox.set_opacity(0)

    def _load_thumbnail_async(self, path_or_url):
        """Load thumbnail asynchronously."""
        # This will be called by the view with view_model.load_thumbnail_async
        # Set a callback property for the view to use
        self._thumbnail_loader = lambda thumbnail_path: self._on_thumbnail_loaded(thumbnail_path)

    def _on_thumbnail_loaded(self, texture):
        """Handle thumbnail load completion."""
        if texture:
            self.image.set_paintable(texture)

    def _create_info_row(self):
        """Create information row with filename and metadata (resolution, aspect ratio, size)."""
        info_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        info_box.add_css_class("card-info-box")

        # Filename (truncated)
        filename = self._get_filename()
        self.filename_label = Gtk.Label(label=filename)
        self.filename_label.add_css_class("filename-label")
        self.filename_label.set_xalign(0)
        self.filename_label.set_lines(1)
        self.filename_label.set_max_width_chars(25)
        self.filename_label.set_ellipsize(Pango.EllipsizeMode.END)
        info_box.append(self.filename_label)

        # Resolution/metadata
        metadata = self._get_metadata()
        if metadata:
            metadata_label = Gtk.Label(label=metadata)
            metadata_label.add_css_class("caption")
            metadata_label.add_css_class("dim-label")
            info_box.append(metadata_label)

        self.append(info_box)

    def _get_filename(self) -> str:
        """Get filename (truncation handled by GTK ellipsis)."""
        if hasattr(self.wallpaper, "filename"):
            filename = self.wallpaper.filename
        elif hasattr(self.wallpaper, "path"):
            filename = Path(self.wallpaper.path).name
        else:
            filename = "wallpaper"
        return filename

    def _get_accessible_name(self) -> str:
        """Get accessible name for screen readers."""
        filename = self._get_filename()
        return f"Wallpaper: {filename}"

    def _get_accessible_description(self) -> str:
        """Get accessible description with metadata."""
        parts = []
        if hasattr(self.wallpaper, "resolution") and self.wallpaper.resolution:
            parts.append(f"Resolution: {self.wallpaper.resolution}")
        if hasattr(self.wallpaper, "file_size") and self.wallpaper.file_size:
            parts.append(f"Size: {self.wallpaper.file_size}")
        if self.is_current:
            parts.append("Currently set as wallpaper")
        if self.is_favorite:
            parts.append("In favorites")
        return ". ".join(parts) if parts else "Wallpaper image"

    def _format_aspect_ratio(self) -> str:
        """Format aspect ratio as simplified fraction (e.g., '16:9')."""
        res = self._get_resolution_string()
        if res:
            try:
                width, height = res.split("x")
                width = int(width)
                height = int(height)
                if height == 0:
                    return ""
                frac = Fraction(width, height).limit_denominator(100)
                return f"{frac.numerator}:{frac.denominator}"
            except (ValueError, ZeroDivisionError, AttributeError):
                pass
        return ""

    def _get_metadata(self) -> str:
        """Get metadata string (resolution, size, aspect ratio)."""
        parts = []

        resolution = self._get_resolution_string()
        if resolution:
            parts.append(resolution)

        aspect_ratio = self._format_aspect_ratio()
        if aspect_ratio:
            parts.append(aspect_ratio)

        size = self._get_file_size_string()
        if size:
            parts.append(size)

        return " • ".join(parts) if parts else ""

    def _get_resolution_string(self) -> str:
        """Get resolution string from wallpaper."""
        if hasattr(self.wallpaper, "resolution"):
            res = self.wallpaper.resolution
            if res:
                return str(res)
        return ""

    def _get_file_size_string(self) -> str:
        """Get formatted file size string."""
        size = None
        if hasattr(self.wallpaper, "file_size") and self.wallpaper.file_size:
            size = self.wallpaper.file_size
        elif hasattr(self.wallpaper, "size") and self.wallpaper.size:
            size = self.wallpaper.size

        if size:
            if size >= 1024 * 1024:
                return f"{size / (1024 * 1024):.1f} MB"
            elif size >= 1024:
                return f"{size / 1024:.1f} KB"
            else:
                return f"{size} B"
        return ""

    def _create_actions_bar(self):
        """Create action buttons at bottom of card."""
        actions_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        actions_box.set_halign(Gtk.Align.CENTER)
        actions_box.set_homogeneous(True)
        actions_box.add_css_class("card-actions-box")

        # Set wallpaper button (always present)
        set_btn = Gtk.Button()
        set_btn.set_icon_name("image-x-generic-symbolic")
        set_btn.set_tooltip_text("Set as wallpaper")
        set_btn.add_css_class("action-button")
        set_btn.add_css_class("suggested-action")
        # Accessibility
        set_btn.set_accessible_name("Set wallpaper")
        set_btn.set_accessible_description("Set this image as desktop background")
        set_btn.set_accessible_role(Gtk.AccessibleRole.BUTTON)
        set_btn.connect("clicked", self._on_set_wallpaper_clicked)
        actions_box.append(set_btn)

        # Favorite button (toggle state)
        self.fav_btn = Gtk.Button()
        if self.is_favorite:
            self.fav_btn.set_icon_name("starred-symbolic")
        else:
            self.fav_btn.set_icon_name("non-starred-symbolic")
        self.fav_btn.set_tooltip_text(
            "Add to favorites" if not self.is_favorite else "Remove from favorites"
        )
        self.fav_btn.add_css_class("action-button")
        self.fav_btn.add_css_class("favorite-action")
        fav_label = "Remove from favorites" if self.is_favorite else "Add to favorites"
        self.fav_btn.set_accessible_name(fav_label)
        self.fav_btn.set_accessible_role(Gtk.AccessibleRole.TOGGLE_BUTTON)
        self.fav_btn.connect("clicked", self._on_favorite_clicked)
        actions_box.append(self.fav_btn)

        # Download button (Wallhaven only)
        if self.on_download:
            download_btn = Gtk.Button()
            download_btn.set_icon_name("folder-download-symbolic")
            download_btn.set_tooltip_text("Download wallpaper")
            download_btn.add_css_class("action-button")
            download_btn.add_css_class("download-action")
            download_btn.set_accessible_name("Download wallpaper")
            download_btn.set_accessible_description("Save this wallpaper to your local collection")
            download_btn.set_accessible_role(Gtk.AccessibleRole.BUTTON)
            download_btn.connect("clicked", self.on_download)
            actions_box.append(download_btn)

        # Info/menu button
        if self.on_info:
            info_btn = Gtk.Button()
            info_btn.set_icon_name("info-symbolic")
            info_btn.set_tooltip_text("More options")
            info_btn.add_css_class("action-button")
            info_btn.add_css_class("info-action")
            info_btn.set_accessible_name("More options")
            info_btn.set_accessible_description("View wallpaper details and additional options")
            info_btn.set_accessible_role(Gtk.AccessibleRole.BUTTON)
            info_btn.connect("clicked", self.on_info)
            actions_box.append(info_btn)

        # Delete button (Local only)
        if self.on_delete:
            delete_btn = Gtk.Button()
            delete_btn.set_icon_name("user-trash-symbolic")
            delete_btn.set_tooltip_text("Delete")
            delete_btn.add_css_class("destructive-action")
            delete_btn.add_css_class("action-button")
            delete_btn.set_accessible_name("Delete wallpaper")
            delete_btn.set_accessible_description("Move this wallpaper to trash")
            delete_btn.set_accessible_role(Gtk.AccessibleRole.BUTTON)
            delete_btn.connect("clicked", self.on_delete)
            actions_box.append(delete_btn)

        self.append(actions_box)

    def _on_set_wallpaper_clicked(self, button):
        """Handle set wallpaper button click."""
        if self.on_set_wallpaper:
            self.on_set_wallpaper()

    def _on_favorite_clicked(self, button):
        """Handle favorite button click."""
        if self.on_add_to_favorites:
            self.on_add_to_favorites()

    def _update_card_state(self):
        self.remove_css_class("current")
        self.remove_css_class("selected")

        if self.is_current:
            self.add_css_class("current")

        if self.is_selected:
            self.add_css_class("selected")

        if self.fav_btn:
            if self.is_favorite:
                self.fav_btn.set_icon_name("starred-symbolic")
            else:
                self.fav_btn.set_icon_name("non-starred-symbolic")

    def set_favorite_state(self, is_favorite: bool):
        if self.is_favorite != is_favorite:
            self.is_favorite = is_favorite
            self._update_card_state()

    def set_current_state(self, is_current: bool):
        if self.is_current != is_current:
            self.is_current = is_current
            self._update_card_state()

    def set_selected_state(self, is_selected: bool):
        if self.is_selected != is_selected:
            self.is_selected = is_selected
            if self.checkbox:
                self.checkbox.handler_block_by_func(self._on_checkbox_toggled)
                self.checkbox.set_active(is_selected)
                self.checkbox.handler_unblock_by_func(self._on_checkbox_toggled)
            self._update_card_state()

    def set_selection_mode(self, selection_mode: bool):
        if self.selection_mode != selection_mode:
            self.selection_mode = selection_mode
            self._update_checkbox_visibility()

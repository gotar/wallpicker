"""Modern Preview Dialog component for wallpaper inspection."""

import threading
from pathlib import Path

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
gi.require_version("Gdk", "4.0")
gi.require_version("GdkPixbuf", "2.0")

from gi.repository import Adw, Gdk, GdkPixbuf, GLib, Gtk  # noqa: E402


class PreviewDialog(Adw.Dialog):
    """Modern wallpaper preview dialog with metadata sidebar."""

    __gtype_name__ = "PreviewDialog"

    def __init__(
        self,
        window: Adw.ApplicationWindow,
        wallpaper,
        on_set_wallpaper=None,
        on_toggle_favorite=None,
        on_open_externally=None,
        on_delete=None,
        on_copy_path=None,
        is_favorite=False,
        thumbnail_cache=None,
    ):
        """Initialize preview dialog.

        Args:
            window: Parent window for dialog
            wallpaper: Wallpaper object to display
            on_set_wallpaper: Callback for "Set Wallpaper" button
            on_toggle_favorite: Callback for favorite toggle (receives bool)
            on_open_externally: Callback for "Open Externally" button
            on_delete: Callback for "Delete" button (Local only)
            on_copy_path: Callback for "Copy Path" button
            is_favorite: Initial favorite state
            thumbnail_cache: ThumbnailCache service for loading images
        """
        super().__init__()

        self.window = window
        self.wallpaper = wallpaper
        self.on_set_wallpaper = on_set_wallpaper
        self.on_toggle_favorite = on_toggle_favorite
        self.on_open_externally = on_open_externally
        self.on_delete = on_delete
        self.on_copy_path = on_copy_path
        self.is_favorite = is_favorite
        self.thumbnail_cache = thumbnail_cache

        # Dialog properties
        self.set_title("Wallpaper Preview")
        self.set_content_width(900)
        self.set_content_height(700)
        self.add_css_class("preview-dialog")
        self.set_transition_type(Adw.DialogTransitionType.COVER)

        # Create UI
        self._create_ui()
        self._setup_shortcuts()
        self._load_image()

    def _create_ui(self):
        """Create dialog UI with split-view layout."""
        # Main content box
        main_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=0)
        main_box.set_hexpand(True)
        main_box.set_vexpand(True)

        # Left side: Image preview
        self.image_container = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self.image_container.set_hexpand(True)
        self.image_container.set_vexpand(True)
        self.image_container.add_css_class("preview-image-container")

        # Create picture widget
        self.image = Gtk.Picture()
        self.image.set_content_fit(Gtk.ContentFit.CONTAIN)
        self.image.set_halign(Gtk.Align.CENTER)
        self.image.set_valign(Gtk.Align.CENTER)
        self.image.set_hexpand(True)
        self.image.set_vexpand(True)
        self.image.add_css_class("preview-image")
        self.image_container.append(self.image)

        # Loading spinner
        self.loading_spinner = Gtk.Spinner()
        self.loading_spinner.set_hexpand(True)
        self.loading_spinner.set_vexpand(True)
        self.loading_spinner.start()
        self.image_container.append(self.loading_spinner)

        # Double-click gesture for fullscreen toggle
        click = Gtk.GestureClick()
        click.set_button(1)
        click.connect("pressed", self._on_image_double_click)
        self.image.add_controller(click)

        zoom = Gtk.GestureZoom()
        zoom.connect("scale-changed", self._on_zoom_changed)
        self.image.add_controller(zoom)

        self.current_scale = 1.0

        main_box.append(self.image_container)

        # Right side: Metadata sidebar
        self.sidebar = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self.sidebar.set_width_request(320)
        self.sidebar.add_css_class("preview-sidebar")

        # Create sidebar content
        self._create_metadata_section()
        self._create_actions_section()

        main_box.append(self.sidebar)

        # Wrap in clamp for responsive behavior
        clamp = Adw.Clamp()
        clamp.set_maximum_size(1400)
        clamp.set_child(main_box)

        # Set as dialog content
        self.set_child(clamp)

    def _create_metadata_section(self):
        """Create metadata display section."""
        # Metadata group
        metadata_group = Adw.PreferencesGroup()
        metadata_group.set_title("Information")
        self.sidebar.append(metadata_group)

        # Filename row
        filename_row = Adw.ActionRow()
        filename_row.set_title("File")
        filename = self._get_filename()
        filename_row.set_subtitle(filename)
        filename_row.add_suffix(Gtk.Image(icon_name="document-symbolic"))
        filename_row.set_activatable(True)
        filename_row.connect("activated", self._on_copy_path)
        metadata_group.add(filename_row)

        # Resolution row
        resolution_row = Adw.ActionRow()
        resolution_row.set_title("Resolution")
        resolution = (
            f"{self.wallpaper.resolution.width}×{self.wallpaper.resolution.height}"
        )
        resolution_row.set_subtitle(resolution)
        resolution_row.add_suffix(Gtk.Image(icon_name="display-symbolic"))
        metadata_group.add(resolution_row)

        # File size row
        size_row = Adw.ActionRow()
        size_row.set_title("Size")
        size_mb = self.wallpaper.file_size / (1024 * 1024)
        size_str = f"{size_mb:.2f} MB" if size_mb > 0 else "Unknown"
        size_row.set_subtitle(size_str)
        size_row.add_suffix(Gtk.Image(icon_name="drive-harddisk-symbolic"))
        metadata_group.add(size_row)

        # Source row
        source_row = Adw.ActionRow()
        source_row.set_title("Source")
        source_str = self._get_source_display()
        source_row.set_subtitle(source_str)
        source_row.add_suffix(self._get_source_icon())
        metadata_group.add(source_row)

        # Category row (if available)
        if hasattr(self.wallpaper, "category") and self.wallpaper.category:
            category_row = Adw.ActionRow()
            category_row.set_title("Category")
            category_row.set_subtitle(self.wallpaper.category)
            category_row.add_suffix(Gtk.Image(icon_name="tag-symbolic"))
            metadata_group.add(category_row)

    def _create_actions_section(self):
        """Create action buttons section."""
        # Actions group
        actions_group = Adw.PreferencesGroup()
        actions_group.set_title("Actions")
        self.sidebar.append(actions_group)

        # Primary action: Set wallpaper
        self.set_wallpaper_btn = Gtk.Button()
        self.set_wallpaper_btn.set_label("Set Wallpaper")
        self.set_wallpaper_btn.add_css_class("suggested-action")
        self.set_wallpaper_btn.add_css_class("pill")
        self.set_wallpaper_btn.set_hexpand(True)
        self.set_wallpaper_btn.set_size_request(-1, 48)
        self.set_wallpaper_btn.connect("clicked", self._on_set_wallpaper)
        actions_group.add(self.set_wallpaper_btn)

        # Favorite toggle button
        self.favorite_btn = Gtk.ToggleButton()
        self.favorite_btn.set_hexpand(True)
        self.favorite_btn.set_size_request(-1, 42)
        self._update_favorite_button()
        self.favorite_btn.connect("toggled", self._on_favorite_toggled)
        actions_group.add(self.favorite_btn)

        # Secondary actions box
        secondary_actions_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        secondary_actions_box.set_margin_top(12)
        actions_group.add(secondary_actions_box)

        # Open externally button
        if self.on_open_externally:
            open_btn = Gtk.Button()
            open_btn.set_label("Open Externally")
            open_btn.add_css_class("flat")
            open_btn.set_hexpand(True)
            open_btn.set_icon_name("external-link-symbolic")
            open_btn.connect("clicked", self._on_open_externally)
            secondary_actions_box.append(open_btn)

        # Copy path button
        if self.on_copy_path:
            copy_btn = Gtk.Button()
            copy_btn.set_label("Copy Path")
            copy_btn.add_css_class("flat")
            copy_btn.set_hexpand(True)
            copy_btn.set_icon_name("edit-copy-symbolic")
            copy_btn.connect("clicked", self._on_copy_path)
            secondary_actions_box.append(copy_btn)

        # Delete button (Local only)
        if self.on_delete:
            self.delete_btn = Gtk.Button()
            self.delete_btn.set_label("Delete")
            self.delete_btn.add_css_class("destructive-action")
            self.delete_btn.set_hexpand(True)
            self.delete_btn.set_size_request(-1, 42)
            self.delete_btn.set_icon_name("user-trash-symbolic")
            self.delete_btn.set_visible(
                self.wallpaper.source.value in ("local", "favorite")
            )
            self.delete_btn.connect("clicked", self._on_delete)
            actions_group.add(self.delete_btn)

    def _setup_shortcuts(self):
        """Setup keyboard shortcuts."""
        key_controller = Gtk.EventControllerKey()
        key_controller.connect("key-pressed", self._on_key_pressed)
        self.add_controller(key_controller)

    def _on_key_pressed(self, controller, keyval, keycode, state):
        """Handle keyboard shortcuts."""
        # Escape: Close dialog
        if keyval == Gdk.KEY_Escape:
            self.close()
            return True
        # Ctrl/Cmd + W: Close dialog
        elif (
            state & (Gdk.ModifierType.CONTROL_MASK | Gdk.ModifierType.SUPER_MASK)
            and keyval == Gdk.KEY_w
        ):
            self.close()
            return True
        # Return: Set wallpaper
        elif keyval == Gdk.KEY_Return:
            self._on_set_wallpaper(None)
            return True
        # Space: Toggle favorite
        elif keyval == Gdk.KEY_space:
            self._toggle_favorite()
            return True
        return False

    def _get_filename(self) -> str:
        """Get display filename."""
        if hasattr(self.wallpaper, "filename"):
            return self.wallpaper.filename
        elif hasattr(self.wallpaper, "path") and self.wallpaper.path:
            return Path(self.wallpaper.path).name
        return "wallpaper"

    def _get_source_display(self) -> str:
        """Get human-readable source name."""
        source_map = {
            "wallhaven": "Wallhaven.cc",
            "local": "Local",
            "favorite": "Favorite",
        }
        return source_map.get(self.wallpaper.source.value, "Unknown")

    def _get_source_icon(self) -> Gtk.Image:
        """Get source icon."""
        icon_map = {
            "wallhaven": "globe-symbolic",
            "local": "folder-symbolic",
            "favorite": "starred-symbolic",
        }
        icon_name = icon_map.get(
            self.wallpaper.source.value, "image-x-generic-symbolic"
        )
        return Gtk.Image(icon_name=icon_name)

    def _update_favorite_button(self):
        """Update favorite button state."""
        if self.is_favorite:
            self.favorite_btn.set_label("Remove from Favorites")
            self.favorite_btn.set_icon_name("starred-symbolic")
        else:
            self.favorite_btn.set_label("Add to Favorites")
            self.favorite_btn.set_icon_name("non-starred-symbolic")

    def _load_image(self):
        """Load wallpaper image asynchronously."""
        # Determine image source
        image_source = None
        if self.wallpaper.source.value == "wallhaven":
            # Use large thumbnail or full URL
            image_source = self.wallpaper.thumbs_large or self.wallpaper.url
        else:
            # Use local path
            image_source = self.wallpaper.path

        if not image_source:
            self._on_image_load_failed("No image source available")
            return

        # Load image in background thread
        def load_in_thread():
            try:
                if self.thumbnail_cache and self.wallpaper.source.value == "wallhaven":
                    # Use thumbnail cache for remote images
                    import asyncio

                    async def fetch_image():
                        session = (
                            self.thumbnail_cache._get_session()
                            if hasattr(self.thumbnail_cache, "_get_session")
                            else None
                        )
                        if not session:
                            # Fallback to synchronous load
                            return self._load_image_sync(image_source)

                        # Try cache first
                        cached = self.thumbnail_cache.get_thumbnail(image_source)
                        if cached:
                            return str(cached)

                        # Download and cache
                        return str(
                            await self.thumbnail_cache.download_and_cache(
                                image_source, session
                            )
                        )

                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                    path = loop.run_until_complete(fetch_image())
                    loop.close()
                    image_path = path
                else:
                    # Load local file directly
                    image_path = image_source

                # Load as Gdk.Texture
                from gi.repository import GdkPixbuf

                pixbuf = GdkPixbuf.Pixbuf.new_from_file(str(image_path))
                texture = Gdk.Texture.new_for_pixbuf(pixbuf)
                return texture
            except Exception as e:
                print(f"Error loading image: {e}")
                return None

        def on_loaded(result):
            self.loading_spinner.stop()
            self.loading_spinner.set_visible(False)

            if result:
                self.image.set_paintable(result)
            else:
                self._on_image_load_failed("Failed to load image")

        # Execute in thread

        thread = threading.Thread(
            target=lambda: GLib.idle_add(on_loaded, load_in_thread())
        )
        thread.start()

    def _load_image_sync(self, image_source):
        """Fallback synchronous image loader."""

        pixbuf = GdkPixbuf.Pixbuf.new_from_file(image_source)
        texture = Gdk.Texture.new_for_pixbuf(pixbuf)
        return texture

    def _on_image_load_failed(self, error_message):
        """Handle image load failure."""
        self.loading_spinner.stop()
        self.loading_spinner.set_visible(False)

        # Show error icon
        error_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        error_box.set_valign(Gtk.Align.CENTER)
        error_box.set_halign(Gtk.Align.CENTER)

        error_icon = Gtk.Image()
        error_icon.set_from_icon_name("image-missing-symbolic")
        error_icon.set_pixel_size(64)
        error_icon.add_css_class("dim-label")

        error_label = Gtk.Label(label=error_message)
        error_label.add_css_class("dim-label")

        error_box.append(error_icon)
        error_box.append(error_label)

        self.image_container.append(error_box)

    def _on_image_double_click(self, gesture, n_press, x, y):
        """Handle double-click on image."""
        if n_press == 2:
            self.close()

    def _on_zoom_changed(self, gesture, scale):
        """Handle pinch zoom gesture."""
        self.current_scale = max(1.0, min(5.0, scale))

        zoom_levels = [100, 125, 150, 175, 200, 250, 300, 400, 500]
        zoom_value = int(self.current_scale * 100)
        closest = min(zoom_levels, key=lambda x: abs(x - zoom_value))

        for level in zoom_levels:
            self.image.remove_css_class(f"zoom-{level}")

        self.image.add_css_class(f"zoom-{closest}")

    def _on_set_wallpaper(self, button):
        """Handle set wallpaper button click."""
        if self.on_set_wallpaper:
            self.on_set_wallpaper()
            self.close()

    def _on_favorite_toggled(self, button):
        """Handle favorite button toggle."""
        self._toggle_favorite()

    def _toggle_favorite(self):
        """Toggle favorite state."""
        if self.on_toggle_favorite:
            self.is_favorite = not self.is_favorite
            self.on_toggle_favorite(self.is_favorite)
            self._update_favorite_button()

    def _on_open_externally(self, button):
        """Handle open externally button click."""
        if self.on_open_externally:
            self.on_open_externally()
            self.close()

    def _on_copy_path(self, row_or_button):
        """Handle copy path action."""
        if self.on_copy_path:
            self.on_copy_path()

    def _on_delete(self, button):
        """Handle delete button click."""
        if self.on_delete:
            self.on_delete()
            self.close()

    def _copy_path_to_clipboard(self):
        """Copy wallpaper path to system clipboard."""
        clipboard = Gdk.Display.get_default().get_clipboard()
        path = self.wallpaper.path if self.wallpaper.path else self.wallpaper.url
        clipboard.set_text(path)

    def update_favorite_state(self, is_favorite: bool):
        """Update favorite state from external source."""
        if self.is_favorite != is_favorite:
            self.is_favorite = is_favorite
            self._update_favorite_button()

    def set_delete_visible(self, visible: bool):
        """Show/hide delete button (Local wallpapers only)."""
        if hasattr(self, "delete_btn"):
            self.delete_btn.set_visible(visible)

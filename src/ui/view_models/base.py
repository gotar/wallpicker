"""Base ViewModel for UI state management."""

from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor

from gi.repository import Gdk, GdkPixbuf, GObject, GLib


class BaseViewModel(GObject.Object):
    """Base ViewModel with observable state"""

    __gtype_name__ = "BaseViewModel"

    is_busy = GObject.Property(type=bool, default=False)
    error_message = GObject.Property(type=str, default=None)

    def __init__(self) -> None:
        super().__init__()
        self._is_busy = False
        self._error_message: str | None = None
        self._executor = ThreadPoolExecutor(max_workers=4)

    def bind_property(
        self,
        prop_name: str,
        widget,
        widget_prop: str,
        flags=GObject.BindingFlags.DEFAULT,
    ) -> GObject.Binding:
        """Bind ViewModel property to widget property.

        Args:
            prop_name: ViewModel property name
            widget: Target widget
            widget_prop: Widget property name
            flags: GObject binding flags

        Returns:
            GObject.Binding object
        """
        return GObject.Object.bind_property(self, prop_name, widget, widget_prop, flags)

    def emit_property_changed(self, prop_name: str) -> None:
        """Emit notify signal for property.

        Args:
            prop_name: Property name to emit notification for
        """
        self.notify(prop_name)

    def load_thumbnail_async(
        self, path_or_url: str, callback: Callable[[Gdk.Texture | None], None]
    ) -> None:
        """Load thumbnail asynchronously and invoke callback on main thread.

        Args:
            path_or_url: Local file path or remote URL
            callback: Function to call with Gdk.Texture or None on failure
        """

        def _load_thumbnail():
            try:
                # Check if it's a URL
                if path_or_url.startswith(("http://", "https://")):
                    import requests
                    from io import BytesIO

                    response = requests.get(path_or_url, timeout=10)
                    response.raise_for_status()

                    loader = GdkPixbuf.PixbufLoader()
                    loader.write(response.content)
                    loader.close()
                    pixbuf = loader.get_pixbuf()

                    # Scale the pixbuf
                    if pixbuf:
                        pixbuf = pixbuf.scale_simple(
                            220, 160, GdkPixbuf.InterpType.BILINEAR
                        )
                else:
                    # Local file
                    pixbuf = GdkPixbuf.Pixbuf.new_from_file_at_scale(
                        str(path_or_url), 220, 160, True
                    )

                if pixbuf:
                    texture = Gdk.Texture.new_for_pixbuf(pixbuf)
                    GLib.idle_add(lambda: callback(texture) or False)
                else:
                    GLib.idle_add(lambda: callback(None) or False)
            except Exception as e:
                print(f"Failed to load thumbnail for {path_or_url}: {e}")
                GLib.idle_add(lambda: callback(None) or False)

        self._executor.submit(_load_thumbnail)

    def clear_error(self) -> None:
        """Clear error message"""
        self.error_message = None

    def __del__(self) -> None:
        """Cleanup executor on deletion."""
        if hasattr(self, "_executor"):
            self._executor.shutdown(wait=False)

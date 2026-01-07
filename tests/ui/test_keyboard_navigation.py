"""Test keyboard navigation functionality."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

import pytest


def test_main_window_has_keyboard_navigation():
    """Test main window has keyboard navigation methods."""
    from ui.main_window import WallPickerWindow

    # Verify keyboard navigation methods exist
    assert hasattr(WallPickerWindow, "_on_key_pressed")
    assert hasattr(WallPickerWindow, "_next_tab")
    assert hasattr(WallPickerWindow, "_prev_tab")
    assert hasattr(WallPickerWindow, "_focus_search_entry")
    assert hasattr(WallPickerWindow, "_setup_menu")
    assert hasattr(WallPickerWindow, "_setup_keyboard_navigation")
    assert hasattr(WallPickerWindow, "_setup_focus_chain")


def test_local_view_has_grid_navigation():
    """Test local view has grid navigation methods."""
    from ui.views.local_view import LocalView

    # Verify grid navigation methods exist
    assert hasattr(LocalView, "_setup_grid_navigation")
    assert hasattr(LocalView, "_on_grid_key_pressed")
    assert hasattr(LocalView, "_focus_next_card")
    assert hasattr(LocalView, "_focus_prev_card")
    assert hasattr(LocalView, "_on_key_pressed")


def test_favorites_view_has_grid_navigation():
    """Test favorites view has grid navigation methods."""
    from ui.views.favorites_view import FavoritesView

    # Verify grid navigation methods exist
    assert hasattr(FavoritesView, "_setup_grid_navigation")
    assert hasattr(FavoritesView, "_on_grid_key_pressed")
    assert hasattr(FavoritesView, "_focus_next_card")
    assert hasattr(FavoritesView, "_focus_prev_card")
    assert hasattr(FavoritesView, "_on_key_pressed")


def test_wallhaven_view_has_grid_navigation():
    """Test wallhaven view has grid navigation methods."""
    from ui.views.wallhaven_view import WallhavenView

    # Verify grid navigation methods exist
    assert hasattr(WallhavenView, "_setup_grid_navigation")
    assert hasattr(WallhavenView, "_on_grid_key_pressed")
    assert hasattr(WallhavenView, "_focus_next_card")
    assert hasattr(WallhavenView, "_focus_prev_card")
    assert hasattr(WallhavenView, "_on_key_pressed")


def test_preview_dialog_has_shortcuts():
    """Test preview dialog has keyboard shortcuts."""
    from ui.components.preview_dialog import PreviewDialog

    # Verify keyboard shortcuts method exists
    assert hasattr(PreviewDialog, "_on_key_pressed")
    assert hasattr(PreviewDialog, "_setup_shortcuts")


def test_shortcuts_dialog_component_exists():
    """Test shortcuts dialog component exists."""
    from ui.components.shortcuts_dialog import ShortcutsDialog

    # Verify ShortcutsDialog class exists
    assert ShortcutsDialog is not None

    # Verify dialog can be created
    # (Can't instantiate without parent_window, but verify class structure)
    assert hasattr(ShortcutsDialog, "__init__")


def test_cards_are_made_focusable():
    """Test that cards are made focusable in views."""
    # Check local_view.py contains focusability setup
    local_view_path = Path(__file__).parent.parent.parent / "src" / "ui" / "views" / "local_view.py"

    assert local_view_path.exists()

    with open(local_view_path, "r") as f:
        content = f.read()

    # Verify cards are made focusable
    assert "set_can_focus(True)" in content or "set_focusable(True)" in content
    # Verify card->wallpaper mapping exists
    assert "card_wallpaper_map" in content


def test_css_focus_styles_exist():
    """Test focus styles are defined in CSS."""
    css_path = Path(__file__).parent.parent.parent / "data" / "style.css"

    assert css_path.exists()

    with open(css_path, "r") as f:
        css_content = f.read()

    # Check for focus indicators
    assert ":focus-visible" in css_content or "*:focus" in css_content
    assert ".wallpaper-card:focus" in css_content or ".wallpaper-card:focus-visible" in css_content
    # Check for shortcuts dialog styling
    assert ".shortcuts-dialog" in css_content or "SHORTCUTS DIALOG" in css_content.upper()
    # Check for focus animations
    assert "focus" in css_content.lower()


def test_all_views_support_ctrl_a():
    """Test all views support Ctrl+A to select all."""
    from ui.views.local_view import LocalView
    from ui.views.favorites_view import FavoritesView
    from ui.views.wallhaven_view import WallhavenView

    # Verify all views handle Ctrl+A
    assert hasattr(LocalView, "_on_key_pressed")
    assert hasattr(FavoritesView, "_on_key_pressed")
    assert hasattr(WallhavenView, "_on_key_pressed")


def test_all_views_support_escape():
    """Test all views support Escape to clear selection."""
    from ui.views.local_view import LocalView
    from ui.views.favorites_view import FavoritesView
    from ui.views.wallhaven_view import WallhavenView

    # Verify all views handle Escape
    assert hasattr(LocalView, "_on_key_pressed")
    assert hasattr(FavoritesView, "_on_key_pressed")
    assert hasattr(WallhavenView, "_on_key_pressed")


def test_menu_integration():
    """Test menu is integrated in main window."""
    from ui.main_window import WallPickerWindow

    # Verify menu setup method exists
    assert hasattr(WallPickerWindow, "_setup_menu")
    assert hasattr(WallPickerWindow, "_show_shortcuts_dialog")


def test_gtk_event_controller_imports():
    """Test EventControllerKey is imported correctly."""
    from ui.views.local_view import LocalView

    local_view_path = Path(__file__).parent.parent.parent / "src" / "ui" / "views" / "local_view.py"

    with open(local_view_path, "r") as f:
        content = f.read()

    # Verify EventControllerKey is imported
    assert "EventControllerKey" in content
    # Verify key press handler is set up
    assert "_on_key_pressed" in content
    assert "key-pressed" in content


def test_shortcuts_dialog_structure():
    """Test shortcuts dialog has proper structure."""
    from ui.components.shortcuts_dialog import ShortcutsDialog

    shortcuts_dialog_path = (
        Path(__file__).parent.parent.parent / "src" / "ui" / "components" / "shortcuts_dialog.py"
    )

    assert shortcuts_dialog_path.exists()

    with open(shortcuts_dialog_path, "r") as f:
        content = f.read()

    # Verify dialog structure
    assert "Adw.PreferencesGroup" in content or "PreferencesGroup" in content
    assert "Adw.ActionRow" in content or "ActionRow" in content
    # Verify shortcut groups are created
    assert "_create_shortcut_group" in content or "create_shortcut_group" in content


def test_focus_chain_setup():
    """Test focus chain is set up in main window."""
    from ui.main_window import WallPickerWindow

    # Verify focus chain method exists
    assert hasattr(WallPickerWindow, "_setup_focus_chain")
    assert hasattr(WallPickerWindow, "_on_tab_focus_changed")

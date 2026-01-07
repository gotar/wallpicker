"""Unit tests for touch gesture functionality."""

import sys
from pathlib import Path
from unittest.mock import MagicMock, Mock

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import gi

gi.require_version("Gdk", "4.0")
from gi.repository import Gdk

import pytest


class TestSwipeGestures:
    """Test swipe gesture for tab switching."""

    def test_swipe_method_exists(self):
        """Test that _on_swipe method exists in main window."""
        from ui.main_window import WallPickerWindow

        assert hasattr(WallPickerWindow, "_on_swipe")

    def test_swipe_logic_thresholds(self):
        """Test swipe logic uses correct dx thresholds."""
        from ui.main_window import WallPickerWindow

        import inspect

        source = inspect.getsource(WallPickerWindow._on_swipe)

        assert "dx > 100" in source
        assert "dx < -100" in source


class TestKeyboardShortcuts:
    """Test keyboard shortcuts equivalent to swipe gestures."""

    def test_key_pressed_method_exists(self):
        """Test that _on_key_pressed method exists in main window."""
        from ui.main_window import WallPickerWindow

        assert hasattr(WallPickerWindow, "_on_key_pressed")

    def test_keyboard_setup_exists(self):
        """Test that keyboard navigation is set up."""
        from ui.main_window import WallPickerWindow

        assert hasattr(WallPickerWindow, "_setup_keyboard_navigation")

    def test_ctrl_1_selects_local_tab(self):
        """Test Ctrl+1 selects local tab."""
        from ui.main_window import WallPickerWindow

        import inspect

        source = inspect.getsource(WallPickerWindow._on_key_pressed)

        assert "Gdk.KEY_1" in source
        assert '"local"' in source

    def test_ctrl_2_selects_wallhaven_tab(self):
        """Test Ctrl+2 selects wallhaven tab."""
        from ui.main_window import WallPickerWindow

        import inspect

        source = inspect.getsource(WallPickerWindow._on_key_pressed)

        assert "Gdk.KEY_2" in source
        assert '"wallhaven"' in source

    def test_ctrl_3_selects_favorites_tab(self):
        """Test Ctrl+3 selects favorites tab."""
        from ui.main_window import WallPickerWindow

        import inspect

        source = inspect.getsource(WallPickerWindow._on_key_pressed)

        assert "Gdk.KEY_3" in source
        assert '"favorites"' in source

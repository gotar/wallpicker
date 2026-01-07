"""Adaptive layout mixin for GTK4 views with Adw.Breakpoint support."""

import gi

gi.require_version("Adw", "1")

from gi.repository import Adw, Gtk  # noqa: E402


class AdaptiveLayoutMixin:
    """Mixin for adding adaptive layout support with Adw.Breakpoint.

    Provides responsive grid column count and filter bar orientation
    based on window width breakpoints.
    """

    def _setup_adaptive_layout(self, flow_box: Gtk.FlowBox):
        """Setup adaptive layout with breakpoints for flow box.

        Args:
            flow_box: The FlowBox widget to adapt
        """
        self.flow_box = flow_box
        self.flow_box.set_min_children_per_line(2)
        self.flow_box.set_selection_mode(Gtk.SelectionMode.NONE)
        self.flow_box.set_max_children_per_line(6)
        self._setup_breakpoints()

    def _setup_breakpoints(self):
        """Setup adaptive breakpoints for different window sizes.

        Breakpoints:
        - Narrow (< 600px): 2 columns, stacked filters
        - Medium (600-900px): 3 columns
        - Wide (900-1200px): 4 columns
        - Ultra-wide (1200-1400px): 5 columns
        - Full (> 1400px): 6 columns (max)
        """
        # Breakpoint: Narrow (< 600px) - 2 columns, stacked filters
        narrow_bp = Adw.Breakpoint.new(
            Adw.BreakpointCondition.parse("max-width: 600px")
        )

        def apply_narrow(*args):
            self.flow_box.set_max_children_per_line(2)
            if hasattr(self, "filter_bar"):
                self.filter_bar.set_orientation(Gtk.Orientation.VERTICAL)

        def unapply_narrow(*args):
            self.flow_box.set_max_children_per_line(3)
            self.flow_box.set_homogeneous(False)
            if hasattr(self, "filter_bar"):
                self.filter_bar.set_orientation(Gtk.Orientation.HORIZONTAL)

        narrow_bp.connect("apply", apply_narrow)
        narrow_bp.connect("unapply", unapply_narrow)
        self.add_breakpoint(narrow_bp)

        # Breakpoint: Medium (600-900px) - 3 columns
        medium_bp = Adw.Breakpoint.new(
            Adw.BreakpointCondition.parse("min-width: 600px")
        )
        medium_bp.set_condition(Adw.BreakpointCondition.parse("max-width: 900px"))

        def apply_medium(*args):
            self.flow_box.set_max_children_per_line(3)

        medium_bp.connect("apply", apply_medium)
        self.add_breakpoint(medium_bp)

        # Breakpoint: Wide (900-1200px) - 4 columns
        wide_bp = Adw.Breakpoint.new(Adw.BreakpointCondition.parse("min-width: 900px"))
        wide_bp.set_condition(Adw.BreakpointCondition.parse("max-width: 1200px"))

        def apply_wide(*args):
            self.flow_box.set_max_children_per_line(4)

        wide_bp.connect("apply", apply_wide)
        self.add_breakpoint(wide_bp)

        # Breakpoint: Ultra-wide (1200-1400px) - 5 columns
        ultra_bp = Adw.Breakpoint.new(
            Adw.BreakpointCondition.parse("min-width: 1200px")
        )
        ultra_bp.set_condition(Adw.BreakpointCondition.parse("max-width: 1400px"))

        def apply_ultra(*args):
            self.flow_box.set_max_children_per_line(5)

        ultra_bp.connect("apply", apply_ultra)
        self.add_breakpoint(ultra_bp)

        # Breakpoint: Full (> 1400px) - 6 columns (max)
        full_bp = Adw.Breakpoint.new(Adw.BreakpointCondition.parse("min-width: 1400px"))

        def apply_full(*args):
            self.flow_box.set_max_children_per_line(6)

        full_bp.connect("apply", apply_full)
        self.add_breakpoint(full_bp)

    def _setup_filter_adaptation(self, filter_bar: Gtk.Box):
        """Setup filter bar orientation adaptation.

        Args:
            filter_bar: The filter bar widget to adapt
        """
        self.filter_bar = filter_bar

        # Narrow screens: Filters stacked vertically below search
        # Wide screens: Filters horizontal
        narrow_bp = Adw.Breakpoint.new(
            Adw.BreakpointCondition.parse("max-width: 900px")
        )

        def apply_narrow_filters(*args):
            if hasattr(self, "filter_bar"):
                self.filter_bar.set_orientation(Gtk.Orientation.VERTICAL)
                self.filter_bar.set_halign(Gtk.Align.FILL)
                self.filter_bar.add_css_class("vertical")

        def unapply_narrow_filters(*args):
            if hasattr(self, "filter_bar"):
                self.filter_bar.set_orientation(Gtk.Orientation.HORIZONTAL)
                self.filter_bar.set_halign(Gtk.Align.CENTER)
                self.filter_bar.remove_css_class("vertical")

        narrow_bp.connect("apply", apply_narrow_filters)
        narrow_bp.connect("unapply", unapply_narrow_filters)
        self.add_breakpoint(narrow_bp)

#!/usr/bin/python3
# CinTile — AppearanceWidget.py
# Tactile-style appearance controls with color-lock feature.
# Uses Cinnamon's JSONSettingsHandler API for live updates to extension.js.
# License: GPL-3.0

from gi.repository import Gtk, Gdk
from JsonSettingsWidgets import SettingsWidget

DEFAULTS = {
    "text-color":       "rgba(255, 255, 255, 0.9)",
    "text-size":        48,
    "border-color":     "rgba(74, 144, 217, 0.8)",
    "border-size":      2,
    "grid-color":       "rgba(74, 144, 217, 0.3)",
    "highlight-color":  "rgba(255, 200, 0, 0.6)",
    "window-gap":       0,
    "grid-opacity":     80,
    "link-colors":      True,
    "theme-color":      "rgba(74, 144, 217, 1.0)",
}


class AppearanceWidget(SettingsWidget):
    """Tactile-style appearance controls with linked/unlinked color modes."""

    def __init__(self, info, key, settings):
        SettingsWidget.__init__(self)
        self.key = key
        self.settings = settings
        self.info = info

        # Widget references for external-change refresh
        self._color_buttons = {}  # key -> Gtk.ColorButton
        self._spin_buttons = {}   # key -> Gtk.SpinButton

        # --- Outer centering box ---
        outer = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        outer.set_halign(Gtk.Align.CENTER)

        # --- Main container ---
        root = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        root.set_margin_start(12)
        root.set_margin_end(12)
        root.set_margin_top(8)
        root.set_margin_bottom(8)

        # --- Link toggle row ---
        link_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        link_row.set_halign(Gtk.Align.CENTER)

        self.link_switch = Gtk.Switch()
        self.link_switch.set_active(self._get("link-colors", True))
        self.link_switch.connect("notify::active", self._on_link_toggled)

        link_label = Gtk.Label(label="Link colors")
        link_row.pack_start(link_label, False, False, 0)
        link_row.pack_start(self.link_switch, False, False, 0)

        hl_sep = Gtk.Separator(orientation=Gtk.Orientation.VERTICAL)
        link_row.pack_start(hl_sep, False, False, 12)

        self.hl_switch = Gtk.Switch()
        self.hl_switch.set_active(self._get("show-highlight", True))
        self.hl_switch.connect("notify::active", self._on_highlight_toggled)

        hl_label = Gtk.Label(label="Show selection highlight")
        link_row.pack_start(hl_label, False, False, 0)
        link_row.pack_start(self.hl_switch, False, False, 0)

        root.pack_start(link_row, False, False, 0)

        # --- Linked mode: theme color + highlight ---
        self.linked_grid = Gtk.Grid()
        self.linked_grid.set_column_spacing(12)
        self.linked_grid.set_row_spacing(8)
        self.linked_grid.set_halign(Gtk.Align.CENTER)

        # Row 0: Theme color | Highlight color
        self.linked_grid.attach(
            Gtk.Label(label="Theme color", halign=Gtk.Align.END), 0, 0, 1, 1
        )
        self.theme_btn = self._make_color_button("theme-color", alpha=False)
        self.linked_grid.attach(self.theme_btn, 1, 0, 1, 1)

        self.linked_grid.attach(
            Gtk.Label(label="Highlight color", halign=Gtk.Align.END), 2, 0, 1, 1
        )
        self.linked_hl_btn = self._make_color_button("highlight-color", alpha=True)
        self.linked_grid.attach(self.linked_hl_btn, 3, 0, 1, 1)

        # Row 1: Text color (independent even when linked)
        self.linked_grid.attach(
            Gtk.Label(label="Text color", halign=Gtk.Align.END), 0, 1, 1, 1
        )
        self.linked_text_btn = self._make_color_button("text-color", alpha=True)
        self.linked_grid.attach(self.linked_text_btn, 1, 1, 1, 1)

        root.pack_start(self.linked_grid, False, False, 0)

        # --- Unlinked mode: full individual controls ---
        self.unlinked_grid = Gtk.Grid()
        self.unlinked_grid.set_column_spacing(12)
        self.unlinked_grid.set_row_spacing(8)
        self.unlinked_grid.set_halign(Gtk.Align.CENTER)

        self._grid_color_row(self.unlinked_grid, 0,
                             "Text color", "text-color",
                             "Border color", "border-color")
        self._grid_color_row(self.unlinked_grid, 1,
                             "Background color", "grid-color",
                             "Highlight color", "highlight-color")

        # Realize children now, then lock visibility against parent show_all()
        self.linked_grid.show_all()
        self.unlinked_grid.show_all()
        self.linked_grid.set_no_show_all(True)
        self.unlinked_grid.set_no_show_all(True)

        root.pack_start(self.unlinked_grid, False, False, 0)

        # --- Shared numeric controls (always visible) ---
        num_grid = Gtk.Grid()
        num_grid.set_column_spacing(12)
        num_grid.set_row_spacing(8)
        num_grid.set_halign(Gtk.Align.CENTER)

        self._grid_spin_row(num_grid, 0,
                            "Text size", "text-size", 12, 96, 2,
                            "Border size", "border-size", 0, 10, 1)
        self._grid_spin_row(num_grid, 1,
                            "Gap size", "window-gap", 0, 50, 2,
                            "Overlay opacity", "grid-opacity", 20, 100, 5)

        root.pack_start(num_grid, False, False, 0)

        outer.pack_start(root, False, False, 0)
        self.pack_start(outer, True, True, 0)

        # --- Show/hide based on link state ---
        self._update_mode_visibility()

    # =========================================================================
    # Settings API wrappers
    # =========================================================================

    def _get(self, key, default=0):
        """Read a value via Cinnamon's settings handler."""
        try:
            val = self.settings.get_value(key)
            return val if val is not None else default
        except Exception:
            return default

    def _put(self, key, value):
        """Write a value via Cinnamon's settings handler (triggers JS callbacks)."""
        try:
            self.settings.set_value(key, value)
        except Exception as e:
            print("[CinTile AppearanceWidget] set_value error for '%s': %s" % (key, e))

    # =========================================================================
    # Grid row builders
    # =========================================================================

    def _grid_color_row(self, grid, row, lbl1, key1, lbl2, key2):
        grid.attach(Gtk.Label(label=lbl1, halign=Gtk.Align.END), 0, row, 1, 1)
        btn1 = self._make_color_button(key1, alpha=True)
        grid.attach(btn1, 1, row, 1, 1)
        grid.attach(Gtk.Label(label=lbl2, halign=Gtk.Align.END), 2, row, 1, 1)
        btn2 = self._make_color_button(key2, alpha=True)
        grid.attach(btn2, 3, row, 1, 1)

    def _grid_spin_row(self, grid, row, lbl1, key1, lo1, hi1, step1,
                       lbl2, key2, lo2, hi2, step2):
        grid.attach(Gtk.Label(label=lbl1, halign=Gtk.Align.END), 0, row, 1, 1)
        grid.attach(self._make_spin(key1, lo1, hi1, step1), 1, row, 1, 1)
        grid.attach(Gtk.Label(label=lbl2, halign=Gtk.Align.END), 2, row, 1, 1)
        grid.attach(self._make_spin(key2, lo2, hi2, step2), 3, row, 1, 1)

    # =========================================================================
    # Widget factories
    # =========================================================================

    def _make_color_button(self, key, alpha=True):
        btn = Gtk.ColorButton()
        btn.set_use_alpha(alpha)
        rgba = Gdk.RGBA()
        color_str = str(self._get(key, DEFAULTS.get(key, "rgba(255,255,255,1)")))
        if not rgba.parse(color_str):
            rgba.parse(str(DEFAULTS.get(key, "rgba(255,255,255,1)")))
        btn.set_rgba(rgba)
        btn.connect("color-set", self._on_color_set, key)
        self._color_buttons[key] = btn
        return btn

    def _make_spin(self, key, lo, hi, step):
        val = self._get(key, DEFAULTS.get(key, 0))
        adj = Gtk.Adjustment(value=val, lower=lo, upper=hi, step_increment=step)
        spin = Gtk.SpinButton(adjustment=adj)
        spin.set_numeric(True)
        spin.set_width_chars(4)
        spin.connect("value-changed", self._on_spin_changed, key)
        self._spin_buttons[key] = spin
        return spin

    # =========================================================================
    # Link toggle
    # =========================================================================

    def _on_link_toggled(self, switch, _pspec):
        linked = switch.get_active()
        self._put("link-colors", linked)

        if linked:
            self._apply_theme_color()

        self._update_mode_visibility()

    def _on_highlight_toggled(self, switch, _pspec):
        self._put("show-highlight", switch.get_active())

    def _update_mode_visibility(self):
        linked = self._get("link-colors", True)
        if linked:
            self.linked_grid.show()
            self.unlinked_grid.hide()
        else:
            self.linked_grid.hide()
            self.unlinked_grid.show()

    # =========================================================================
    # Color derivation (linked mode)
    # =========================================================================

    def _apply_theme_color(self):
        """Derive grid-color, border-color, text-color from the theme color."""
        rgba = Gdk.RGBA()
        theme_str = str(self._get("theme-color", DEFAULTS["theme-color"]))
        if not rgba.parse(theme_str):
            rgba.parse(DEFAULTS["theme-color"])

        r = int(round(rgba.red * 255))
        g = int(round(rgba.green * 255))
        b = int(round(rgba.blue * 255))

        # Background: theme color at 30% opacity
        grid_color = "rgba(%d, %d, %d, 0.30)" % (r, g, b)
        self._put("grid-color", grid_color)
        # Border: theme color at 80% opacity
        border_color = "rgba(%d, %d, %d, 0.80)" % (r, g, b)
        self._put("border-color", border_color)

        # Update any visible color buttons to reflect derived values
        for key, color_str in [("grid-color", grid_color),
                                ("border-color", border_color)]:
            if key in self._color_buttons:
                derived = Gdk.RGBA()
                derived.parse(color_str)
                self._color_buttons[key].set_rgba(derived)

    # =========================================================================
    # Change handlers
    # =========================================================================

    def _on_color_set(self, btn, key):
        rgba = btn.get_rgba()
        value = "rgba(%d, %d, %d, %.2f)" % (
            int(round(rgba.red * 255)),
            int(round(rgba.green * 255)),
            int(round(rgba.blue * 255)),
            round(rgba.alpha, 2)
        )
        self._put(key, value)

        # If linked and this is the theme color, derive the others
        if key == "theme-color" and self._get("link-colors", True):
            self._apply_theme_color()

    def _on_spin_changed(self, spin, key):
        self._put(key, int(spin.get_value()))
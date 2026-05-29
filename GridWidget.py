#!/usr/bin/python3
# CinTile — GridWidget.py
# Visual grid editor for the CinTile settings panel.
# Uses Cinnamon's JSONSettingsHandler API for live updates to extension.js.
# License: GPL-3.0

import json
import math

from gi.repository import Gtk, Gdk, Pango, PangoCairo
from JsonSettingsWidgets import SettingsWidget

# Default key labels — used when no custom binding exists
DEFAULT_LABELS = [
    ['Q', 'W', 'E', 'R', 'T', 'Y', 'U'],
    ['A', 'S', 'D', 'F', 'G', 'H', 'J'],
    ['Z', 'X', 'C', 'V', 'B', 'N', 'M']
]

# Default key codes matching DEFAULT_LABELS (GDK keysyms = Clutter keysyms)
DEFAULT_CODES = [
    [Gdk.KEY_q, Gdk.KEY_w, Gdk.KEY_e, Gdk.KEY_r, Gdk.KEY_t, Gdk.KEY_y, Gdk.KEY_u],
    [Gdk.KEY_a, Gdk.KEY_s, Gdk.KEY_d, Gdk.KEY_f, Gdk.KEY_g, Gdk.KEY_h, Gdk.KEY_j],
    [Gdk.KEY_z, Gdk.KEY_x, Gdk.KEY_c, Gdk.KEY_v, Gdk.KEY_b, Gdk.KEY_n, Gdk.KEY_m]
]

# Limits matching settings-schema.json
MIN_ROWS, MAX_ROWS = 2, 3
MIN_COLS, MAX_COLS = 2, 7
MIN_WEIGHT, MAX_WEIGHT = 0, 10


class GridWidget(SettingsWidget):
    """Custom settings widget: visual grid editor with +/- weight controls
    and click-to-assign key binding."""

    def __init__(self, info, key, settings):
        SettingsWidget.__init__(self)
        self.key = key
        self.settings = settings
        self.info = info
        self._selected_cell = None  # (row, col) or None
        self._cell_rects = {}       # {(row, col): (x, y, w, h)} for hit testing

        # --- Outer centering wrapper ---
        outer = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        outer.set_halign(Gtk.Align.CENTER)

        # --- Build UI ---
        root = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        root.set_margin_start(4)
        root.set_margin_end(4)
        root.set_margin_top(8)
        root.set_margin_bottom(8)

        # Row 1: dimension controls (centered)
        dim_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        dim_box.set_halign(Gtk.Align.CENTER)

        dim_box.pack_start(Gtk.Label(label="Rows"), False, False, 0)
        dim_box.pack_start(self._btn("−", self._on_rows, -1), False, False, 0)
        self.rows_lbl = Gtk.Label()
        self.rows_lbl.set_width_chars(2)
        dim_box.pack_start(self.rows_lbl, False, False, 0)
        dim_box.pack_start(self._btn("+", self._on_rows, 1), False, False, 0)

        dim_box.pack_start(
            Gtk.Separator(orientation=Gtk.Orientation.VERTICAL), False, False, 8
        )

        dim_box.pack_start(Gtk.Label(label="Columns"), False, False, 0)
        dim_box.pack_start(self._btn("−", self._on_cols, -1), False, False, 0)
        self.cols_lbl = Gtk.Label()
        self.cols_lbl.set_width_chars(2)
        dim_box.pack_start(self.cols_lbl, False, False, 0)
        dim_box.pack_start(self._btn("+", self._on_cols, 1), False, False, 0)

        root.pack_start(dim_box, False, False, 0)

        # Row 2: [row-weight controls | col-weight header + grid preview]
        grid_area = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=4)

        # Left: row weight +/- controls (vertically stacked)
        self.rw_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
        self.rw_box.set_valign(Gtk.Align.END)
        grid_area.pack_start(self.rw_box, False, False, 0)

        # Right: col weights on top, grid preview below
        right = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)

        self.cw_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=2)
        self.cw_box.set_halign(Gtk.Align.FILL)
        right.pack_start(self.cw_box, False, False, 0)

        self.canvas = Gtk.DrawingArea()
        self.canvas.set_size_request(380, 200)
        self.canvas.set_can_focus(True)
        self.canvas.add_events(
            Gdk.EventMask.BUTTON_PRESS_MASK | Gdk.EventMask.KEY_PRESS_MASK
        )
        self.canvas.connect("draw", self._on_draw)
        self.canvas.connect("button-press-event", self._on_cell_click)
        self.canvas.connect("key-press-event", self._on_key_assign)
        right.pack_start(self.canvas, True, True, 0)

        grid_area.pack_start(right, True, True, 0)
        root.pack_start(grid_area, True, True, 0)

        # Row 3: hint label + reset button
        bottom_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        bottom_box.set_halign(Gtk.Align.CENTER)

        self.hint_lbl = Gtk.Label(label="Click a cell to assign a key")
        self.hint_lbl.set_opacity(0.6)
        bottom_box.pack_start(self.hint_lbl, False, False, 0)

        reset_btn = Gtk.Button(label="Reset Keys")
        reset_btn.connect("clicked", self._on_reset_all)
        bottom_box.pack_start(reset_btn, False, False, 0)

        root.pack_start(bottom_box, False, False, 0)

        # Pack root into outer, outer into SettingsWidget
        outer.pack_start(root, True, True, 0)
        self.pack_start(outer, True, True, 0)

        # --- Initial render ---
        self._rebuild_controls()
        self._refresh_display()

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
            print("[CinTile GridWidget] set_value error for '%s': %s" % (key, e))

    # No _nudge_js needed — key-bindings stored as JSON string,
    # which bindProperty handles reliably as a primitive type.

    # =========================================================================
    # Key binding helpers
    # =========================================================================

    def _get_bindings(self):
        """Read custom key bindings dict from settings (stored as JSON string)."""
        raw = self._get("key-bindings", "{}")
        if isinstance(raw, dict):
            return raw
        try:
            parsed = json.loads(raw)
            return parsed if isinstance(parsed, dict) else {}
        except (json.JSONDecodeError, TypeError):
            return {}

    def _put_binding(self, row, col, code, label):
        """Store a custom key binding for a cell."""
        bindings = self._get_bindings()
        bindings["%d-%d" % (row, col)] = {"code": code, "label": label}
        self._put("key-bindings", json.dumps(bindings))

    def _clear_binding(self, row, col):
        """Remove a custom key binding for a cell (revert to default)."""
        bindings = self._get_bindings()
        key = "%d-%d" % (row, col)
        if key in bindings:
            del bindings[key]
            self._put("key-bindings", json.dumps(bindings))

    def _get_label(self, row, col):
        """Get display label for a cell — custom binding or default."""
        bindings = self._get_bindings()
        key = "%d-%d" % (row, col)
        if key in bindings and bindings[key].get("label"):
            return bindings[key]["label"]
        if row < len(DEFAULT_LABELS) and col < len(DEFAULT_LABELS[row]):
            return DEFAULT_LABELS[row][col]
        return ""

    # =========================================================================
    # Helpers
    # =========================================================================

    def _btn(self, label, cb, delta):
        b = Gtk.Button(label=label)
        b.set_size_request(28, 28)
        b.connect("clicked", cb, delta)
        return b

    def _rows(self):
        return max(MIN_ROWS, min(MAX_ROWS, self._get("grid-rows", 2)))

    def _cols(self):
        return max(MIN_COLS, min(MAX_COLS, self._get("grid-cols", 4)))

    def _cw(self, i):
        return max(MIN_WEIGHT, min(MAX_WEIGHT, self._get("col-%d-weight" % i, 1)))

    def _rw(self, i):
        return max(MIN_WEIGHT, min(MAX_WEIGHT, self._get("row-%d-weight" % i, 1)))

    # =========================================================================
    # Dimension change handlers
    # =========================================================================

    def _on_rows(self, _btn, delta):
        cur = self._rows()
        nv = max(MIN_ROWS, min(MAX_ROWS, cur + delta))
        if nv == cur:
            return
        self._put("grid-rows", nv)
        for i in range(nv):
            if self._rw(i) == 0:
                self._put("row-%d-weight" % i, 1)
        self._selected_cell = None
        self._rebuild_controls()
        self._refresh_display()

    def _on_cols(self, _btn, delta):
        cur = self._cols()
        nv = max(MIN_COLS, min(MAX_COLS, cur + delta))
        if nv == cur:
            return
        self._put("grid-cols", nv)
        for i in range(nv):
            if self._cw(i) == 0:
                self._put("col-%d-weight" % i, 1)
        self._selected_cell = None
        self._rebuild_controls()
        self._refresh_display()

    # =========================================================================
    # Weight change handlers
    # =========================================================================

    def _on_cw_change(self, _btn, data):
        i, delta = data
        nv = max(MIN_WEIGHT, min(MAX_WEIGHT, self._cw(i) + delta))
        self._put("col-%d-weight" % i, nv)
        self._rebuild_controls()
        self._refresh_display()

    def _on_rw_change(self, _btn, data):
        i, delta = data
        nv = max(MIN_WEIGHT, min(MAX_WEIGHT, self._rw(i) + delta))
        self._put("row-%d-weight" % i, nv)
        self._rebuild_controls()
        self._refresh_display()

    # =========================================================================
    # Click-to-assign handlers
    # =========================================================================

    def _on_cell_click(self, widget, event):
        """Handle click on canvas — select cell for key assignment."""
        # Right-click on selected cell clears its binding
        if event.button == 3 and self._selected_cell:
            row, col = self._selected_cell
            self._clear_binding(row, col)
            self._selected_cell = None
            self.hint_lbl.set_text("Binding cleared — using default")
            self._refresh_display()
            return True

        # Left-click — find which cell was hit
        for (row, col), (cx, cy, cw, ch) in self._cell_rects.items():
            if cx <= event.x <= cx + cw and cy <= event.y <= cy + ch:
                self._selected_cell = (row, col)
                label = self._get_label(row, col)
                self.hint_lbl.set_text("Press a key for cell [%s]" % label)
                self.canvas.grab_focus()
                self._refresh_display()
                return True

        # Clicked outside any cell — deselect
        self._selected_cell = None
        self.hint_lbl.set_text("Click a cell to assign a key")
        self._refresh_display()
        return True

    def _on_key_assign(self, widget, event):
        """Handle key press — assign to selected cell."""
        if not self._selected_cell:
            return False

        keyval = event.keyval
        row, col = self._selected_cell

        # Escape cancels selection
        if keyval == Gdk.KEY_Escape:
            self._selected_cell = None
            self.hint_lbl.set_text("Click a cell to assign a key")
            self._refresh_display()
            return True

        # Delete/Backspace clears binding
        if keyval in (Gdk.KEY_Delete, Gdk.KEY_BackSpace):
            self._clear_binding(row, col)
            self._selected_cell = None
            self.hint_lbl.set_text("Binding cleared — using default")
            self._refresh_display()
            return True

        # Ignore modifier-only keys
        if keyval in (Gdk.KEY_Shift_L, Gdk.KEY_Shift_R,
                      Gdk.KEY_Control_L, Gdk.KEY_Control_R,
                      Gdk.KEY_Alt_L, Gdk.KEY_Alt_R,
                      Gdk.KEY_Super_L, Gdk.KEY_Super_R):
            return True

        # Check for duplicate — is this key already assigned to another cell?
        bindings = self._get_bindings()
        for cell_key, binding in bindings.items():
            if binding.get("code") == keyval and cell_key != "%d-%d" % (row, col):
                r, c = cell_key.split("-")
                self.hint_lbl.set_text("Key already assigned to row %s, col %s" % (r, c))
                return True

        # Also check against defaults for other cells
        for dr in range(self._rows()):
            for dc in range(self._cols()):
                if dr == row and dc == col:
                    continue
                cell_key = "%d-%d" % (dr, dc)
                if cell_key in bindings:
                    # This cell has a custom binding, already checked above
                    continue
                if dr < len(DEFAULT_CODES) and dc < len(DEFAULT_CODES[dr]):
                    if DEFAULT_CODES[dr][dc] == keyval:
                        self.hint_lbl.set_text("Key already used by default cell [%s]" % DEFAULT_LABELS[dr][dc])
                        return True

        # Get display label for the key
        char = chr(Gdk.keyval_to_unicode(keyval)) if Gdk.keyval_to_unicode(keyval) else ""
        if char and char.strip():
            label = char.upper()
        else:
            label = Gdk.keyval_name(keyval) or "?"

        self._put_binding(row, col, keyval, label)
        self._selected_cell = None
        self.hint_lbl.set_text("Assigned [%s] to row %d, col %d" % (label, row, col))
        self._refresh_display()
        return True

    def _on_reset_all(self, _btn):
        """Clear all custom key bindings."""
        self._put("key-bindings", json.dumps({}))
        self._selected_cell = None
        self.hint_lbl.set_text("All key bindings reset to defaults")
        self._refresh_display()

    # =========================================================================
    # UI rebuild
    # =========================================================================

    def _rebuild_controls(self):
        """Destroy and recreate weight +/- controls for active rows/cols."""
        for ch in self.cw_box.get_children():
            ch.destroy()
        for ch in self.rw_box.get_children():
            ch.destroy()

        cols = self._cols()
        rows = self._rows()

        # Column weight controls (horizontal, one per column)
        for i in range(cols):
            w = self._cw(i)
            box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=1)
            m = Gtk.Button(label="−")
            m.set_size_request(22, 22)
            m.connect("clicked", self._on_cw_change, (i, -1))
            lbl = Gtk.Label(label=str(w))
            lbl.set_width_chars(2)
            p = Gtk.Button(label="+")
            p.set_size_request(22, 22)
            p.connect("clicked", self._on_cw_change, (i, 1))
            box.pack_start(m, False, False, 0)
            box.pack_start(lbl, False, False, 0)
            box.pack_start(p, False, False, 0)
            self.cw_box.pack_start(box, True, False, 0)

        # Spacer above row weights to align with col-weight header height
        spacer = Gtk.Box()
        spacer.set_size_request(-1, 26)
        self.rw_box.pack_start(spacer, False, False, 0)

        # Row weight controls (vertical, one per row)
        for i in range(rows):
            w = self._rw(i)
            box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=1)
            m = Gtk.Button(label="−")
            m.set_size_request(22, 22)
            m.connect("clicked", self._on_rw_change, (i, -1))
            lbl = Gtk.Label(label=str(w))
            lbl.set_width_chars(2)
            p = Gtk.Button(label="+")
            p.set_size_request(22, 22)
            p.connect("clicked", self._on_rw_change, (i, 1))
            box.pack_start(m, False, False, 0)
            box.pack_start(lbl, False, False, 0)
            box.pack_start(p, False, False, 0)
            self.rw_box.pack_start(box, True, False, 0)

        self.cw_box.show_all()
        self.rw_box.show_all()

    def _refresh_display(self):
        self.rows_lbl.set_text(str(self._rows()))
        self.cols_lbl.set_text(str(self._cols()))
        self.canvas.queue_draw()

    # =========================================================================
    # Cairo drawing — proportional grid preview
    # =========================================================================

    @staticmethod
    def _parse_rgba(color_str, fallback=(0.29, 0.56, 0.85, 0.3)):
        """Parse 'rgba(r, g, b, a)' string into (r, g, b, a) floats 0–1."""
        rgba = Gdk.RGBA()
        if rgba.parse(str(color_str)):
            return (rgba.red, rgba.green, rgba.blue, rgba.alpha)
        return fallback

    def _on_draw(self, widget, cr):
        alloc = widget.get_allocation()
        w, h = alloc.width, alloc.height

        cols = self._cols()
        rows = self._rows()
        cws = [self._cw(i) for i in range(cols)]
        rws = [self._rw(i) for i in range(rows)]
        total_cw = sum(cws) or 1
        total_rw = sum(rws) or 1

        # Read colors from settings (matches the live overlay)
        fill_c = self._parse_rgba(
            self._get("grid-color", "rgba(74, 144, 217, 0.3)"))
        border_c = self._parse_rgba(
            self._get("border-color", "rgba(74, 144, 217, 0.8)"))
        text_c = self._parse_rgba(
            self._get("text-color", "rgba(255, 255, 255, 0.9)"))
        highlight_c = self._parse_rgba(
            self._get("highlight-color", "rgba(255, 200, 0, 0.6)"))
        border_size = max(1, self._get("border-size", 2))

        gap = 3
        self._cell_rects = {}

        for row in range(rows):
            for col in range(cols):
                if cws[col] < 1 or rws[row] < 1:
                    continue

                # Proportional cell bounds (Tactile algorithm)
                x1 = w * sum(cws[:col]) / total_cw
                x2 = w * sum(cws[:col + 1]) / total_cw
                y1 = h * sum(rws[:row]) / total_rw
                y2 = h * sum(rws[:row + 1]) / total_rw

                cx = x1 + gap
                cy = y1 + gap
                cw = (x2 - x1) - gap * 2
                ch = (y2 - y1) - gap * 2

                if cw < 2 or ch < 2:
                    continue

                # Store rect for hit testing
                self._cell_rects[(row, col)] = (cx, cy, cw, ch)

                # Determine if this cell is selected
                is_selected = (self._selected_cell == (row, col))

                # Check if cell has custom binding
                bindings = self._get_bindings()
                has_custom = "%d-%d" % (row, col) in bindings

                # Cell fill — highlight if selected
                if is_selected:
                    cr.set_source_rgba(*highlight_c)
                else:
                    cr.set_source_rgba(*fill_c)
                self._rounded_rect(cr, cx, cy, cw, ch, 4)
                cr.fill()

                # Cell border — brighter if selected or custom
                if is_selected:
                    cr.set_source_rgba(1.0, 0.78, 0.0, 1.0)
                    cr.set_line_width(border_size + 1)
                elif has_custom:
                    cr.set_source_rgba(0.4, 0.8, 0.4, 0.9)
                    cr.set_line_width(border_size + 1)
                else:
                    cr.set_source_rgba(*border_c)
                    cr.set_line_width(border_size)
                self._rounded_rect(cr, cx, cy, cw, ch, 4)
                cr.stroke()

                # Key label
                label = self._get_label(row, col)
                if label:
                    cr.set_source_rgba(*text_c)
                    layout = PangoCairo.create_layout(cr)
                    font = Pango.FontDescription("Sans Bold 18")
                    layout.set_font_description(font)
                    layout.set_text(label, -1)
                    _ink, logical = layout.get_pixel_extents()
                    tx = cx + (cw - logical.width) / 2
                    ty = cy + (ch - logical.height) / 2
                    cr.move_to(tx, ty)
                    PangoCairo.show_layout(cr, layout)

        return True

    @staticmethod
    def _rounded_rect(cr, x, y, w, h, r):
        """Draw a rounded rectangle path."""
        cr.new_sub_path()
        cr.arc(x + w - r, y + r, r, -math.pi / 2, 0)
        cr.arc(x + w - r, y + h - r, r, 0, math.pi / 2)
        cr.arc(x + r, y + h - r, r, math.pi / 2, math.pi)
        cr.arc(x + r, y + r, r, math.pi, 3 * math.pi / 2)
        cr.close_path()
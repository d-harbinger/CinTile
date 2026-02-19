#!/usr/bin/python3
# CinTile — GridWidget.py
# Visual grid editor for the CinTile settings panel.
# Uses Cinnamon's JSONSettingsHandler API for live updates to extension.js.
# License: GPL-3.0

import json
import os

from gi.repository import Gtk, Gdk, GLib, Gio, Pango, PangoCairo
from JsonSettingsWidgets import SettingsWidget

UUID = "cintile@forgetting.me"

# Must match extension.js KEY_LABELS exactly
KEY_LABELS = [
    ['Q', 'W', 'E', 'R', 'T', 'Y', 'U'],
    ['A', 'S', 'D', 'F', 'G', 'H', 'J'],
    ['Z', 'X', 'C', 'V', 'B', 'N', 'M'],
    ['I', 'O', 'P', '[', ']', '\\', ''],
    ['K', 'L', ';', "'", '', '', '']
]

# Limits matching settings-schema.json
MIN_ROWS, MAX_ROWS = 2, 5
MIN_COLS, MAX_COLS = 2, 7
MIN_WEIGHT, MAX_WEIGHT = 0, 10


class GridWidget(SettingsWidget):
    """Custom settings widget: visual grid editor with +/- weight controls."""

    def __init__(self, info, key, settings):
        SettingsWidget.__init__(self)
        self.key = key
        self.settings = settings
        self.info = info

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
        self.canvas.connect("draw", self._on_draw)
        right.pack_start(self.canvas, True, True, 0)

        grid_area.pack_start(right, True, True, 0)
        root.pack_start(grid_area, True, True, 0)

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
        # Give newly visible rows a weight of 1 if currently 0
        for i in range(nv):
            if self._rw(i) == 0:
                self._put("row-%d-weight" % i, 1)
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

    def _on_draw(self, widget, cr):
        alloc = widget.get_allocation()
        w, h = alloc.width, alloc.height

        cols = self._cols()
        rows = self._rows()
        cws = [self._cw(i) for i in range(cols)]
        rws = [self._rw(i) for i in range(rows)]
        total_cw = sum(cws) or 1
        total_rw = sum(rws) or 1

        gap = 3

        key_idx = 0
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
                    key_idx += 1
                    continue

                # Cell fill
                cr.set_source_rgba(0.29, 0.56, 0.85, 0.3)
                self._rounded_rect(cr, cx, cy, cw, ch, 4)
                cr.fill()

                # Cell border
                cr.set_source_rgba(0.29, 0.56, 0.85, 0.8)
                cr.set_line_width(2)
                self._rounded_rect(cr, cx, cy, cw, ch, 4)
                cr.stroke()

                # Key label
                if row < len(KEY_LABELS) and col < len(KEY_LABELS[row]):
                    label = KEY_LABELS[row][col]
                    if label:
                        cr.set_source_rgba(1.0, 1.0, 1.0, 0.9)
                        layout = PangoCairo.create_layout(cr)
                        font = Pango.FontDescription("Sans Bold 18")
                        layout.set_font_description(font)
                        layout.set_text(label, -1)
                        _ink, logical = layout.get_pixel_extents()
                        tx = cx + (cw - logical.width) / 2
                        ty = cy + (ch - logical.height) / 2
                        cr.move_to(tx, ty)
                        PangoCairo.show_layout(cr, layout)

                key_idx += 1

        return True

    @staticmethod
    def _rounded_rect(cr, x, y, w, h, r):
        """Draw a rounded rectangle path."""
        import math
        cr.new_sub_path()
        cr.arc(x + w - r, y + r, r, -math.pi / 2, 0)
        cr.arc(x + w - r, y + h - r, r, 0, math.pi / 2)
        cr.arc(x + r, y + h - r, r, math.pi / 2, math.pi)
        cr.arc(x + r, y + r, r, math.pi, 3 * math.pi / 2)
        cr.close_path()
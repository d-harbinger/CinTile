// CinTile — Keyboard-driven window tiling for Cinnamon
// A port of Tactile (GNOME) with weighted grid support
// UUID: cintile@d-harbinger
// License: GPL-3.0
// https://github.com/d-harbinger/CinTile

const St = imports.gi.St;
const Clutter = imports.gi.Clutter;
const Main = imports.ui.main;
const Meta = imports.gi.Meta;
const GLib = imports.gi.GLib;
const Settings = imports.ui.settings;

const ExtensionSystem = imports.ui.extensionSystem;
const Common = ExtensionSystem.extensions['cintile@d-harbinger'].common;

// Extension state
let config = null;
let settings = null;
let gridOverlay = null;
let firstTile = null;
let gridCells = [];
let KEY_MAP = {};
let currentMonitorIndex = 0;
let focusedWindow = null;

// Key codes for grid cell assignment (left-to-right, top-to-bottom)
const AVAILABLE_KEYS = [
    [Clutter.KEY_q, Clutter.KEY_w, Clutter.KEY_e, Clutter.KEY_r, Clutter.KEY_t, Clutter.KEY_y, Clutter.KEY_u],
    [Clutter.KEY_a, Clutter.KEY_s, Clutter.KEY_d, Clutter.KEY_f, Clutter.KEY_g, Clutter.KEY_h, Clutter.KEY_j],
    [Clutter.KEY_z, Clutter.KEY_x, Clutter.KEY_c, Clutter.KEY_v, Clutter.KEY_b, Clutter.KEY_n, Clutter.KEY_m],
    [Clutter.KEY_i, Clutter.KEY_o, Clutter.KEY_p, Clutter.KEY_bracketleft, Clutter.KEY_bracketright, Clutter.KEY_backslash],
    [Clutter.KEY_k, Clutter.KEY_l, Clutter.KEY_semicolon, Clutter.KEY_apostrophe]
];

// Display labels matching AVAILABLE_KEYS (row-major order, max 7 cols × 5 rows)
const KEY_LABELS = [
    ['Q', 'W', 'E', 'R', 'T', 'Y', 'U'],
    ['A', 'S', 'D', 'F', 'G', 'H', 'J'],
    ['Z', 'X', 'C', 'V', 'B', 'N', 'M'],
    ['I', 'O', 'P', '[', ']', '\\', ''],
    ['K', 'L', ';', "'", '', '', '']
];

// =============================================================================
// Key map — maps Clutter key codes to {row, col} grid positions
// =============================================================================

function buildKeyMap() {
    KEY_MAP = {};
    let weights = Common.getActiveWeights(config);

    for (let row = 0; row < config.gridRows && row < AVAILABLE_KEYS.length; row++) {
        if (weights.rowWeights[row] < 1) continue;
        for (let col = 0; col < config.gridCols && col < AVAILABLE_KEYS[row].length; col++) {
            if (weights.colWeights[col] < 1) continue;
            KEY_MAP[AVAILABLE_KEYS[row][col]] = { row: row, col: col };
        }
    }
}

// =============================================================================
// Settings callback
// =============================================================================

function onSettingsChanged() {
    buildKeyMap();
    if (gridOverlay) {
        hideGrid();
        showGrid();
    }
}

// =============================================================================
// Extension lifecycle: init → enable → disable
// =============================================================================

function init(metadata) {
    config = {};
    settings = new Settings.ExtensionSettings(config, metadata.uuid);

    // Grid dimensions
    settings.bindProperty(Settings.BindingDirection.IN, "grid-rows", "gridRows", onSettingsChanged, null);
    settings.bindProperty(Settings.BindingDirection.IN, "grid-cols", "gridCols", onSettingsChanged, null);

    // Column weights (0–6)
    for (let i = 0; i < 7; i++) {
        settings.bindProperty(Settings.BindingDirection.IN, "col-" + i + "-weight", "col" + i + "Weight", onSettingsChanged, null);
    }

    // Row weights (0–4)
    for (let i = 0; i < 5; i++) {
        settings.bindProperty(Settings.BindingDirection.IN, "row-" + i + "-weight", "row" + i + "Weight", onSettingsChanged, null);
    }

    // Appearance
    settings.bindProperty(Settings.BindingDirection.IN, "window-gap", "windowGap", onSettingsChanged, null);
    settings.bindProperty(Settings.BindingDirection.IN, "grid-opacity", "gridOpacity", onSettingsChanged, null);
    settings.bindProperty(Settings.BindingDirection.IN, "grid-color", "gridColor", onSettingsChanged, null);
    settings.bindProperty(Settings.BindingDirection.IN, "highlight-color", "highlightColor", onSettingsChanged, null);
    settings.bindProperty(Settings.BindingDirection.IN, "keybinding", "keybinding", null, null);
    settings.bindProperty(Settings.BindingDirection.IN, "text-color", "textColor", onSettingsChanged, null);
    settings.bindProperty(Settings.BindingDirection.IN, "text-size", "textSize", onSettingsChanged, null);
    settings.bindProperty(Settings.BindingDirection.IN, "border-color", "borderColor", onSettingsChanged, null);
    settings.bindProperty(Settings.BindingDirection.IN, "border-size", "borderSize", onSettingsChanged, null);
    settings.bindProperty(Settings.BindingDirection.IN, "show-highlight", "showHighlight", onSettingsChanged, null);

    buildKeyMap();
}

function enable() {
    Main.keybindingManager.addHotKey(
        "cintile-show-grid",
        config.keybinding,
        showGrid
    );
}

function disable() {
    Main.keybindingManager.removeHotKey("cintile-show-grid");
    if (gridOverlay) {
        hideGrid();
    }
}

// =============================================================================
// Grid overlay display
// =============================================================================

function showGrid() {
    if (gridOverlay) {
        hideGrid();
        return;
    }

    // Capture the focused window before modal grabs it
    focusedWindow = global.display.focus_window;

    // Determine which monitor the focused window is on
    if (focusedWindow) {
        let rect = focusedWindow.get_frame_rect();
        let monitors = Main.layoutManager.monitors;
        let cx = rect.x + rect.width / 2;
        let cy = rect.y + rect.height / 2;

        for (let i = 0; i < monitors.length; i++) {
            let m = monitors[i];
            if (cx >= m.x && cx < m.x + m.width && cy >= m.y && cy < m.y + m.height) {
                currentMonitorIndex = i;
                break;
            }
        }
    } else {
        currentMonitorIndex = Main.layoutManager.primaryIndex;
    }

    displayGridOnMonitor(currentMonitorIndex);
}

function displayGridOnMonitor(monitorIndex) {
    let monitors = Main.layoutManager.monitors;

    if (monitorIndex < 0 || monitorIndex >= monitors.length) {
        global.logError("[CinTile] Invalid monitor index: " + monitorIndex);
        return;
    }

    let monitor = monitors[monitorIndex];
    let weights = Common.getActiveWeights(config);

    // Safe defaults for appearance properties
    let textColor = config.textColor || 'rgba(255, 255, 255, 0.9)';
    let textSize = config.textSize || 48;
    let borderColor = config.borderColor || 'rgba(74, 144, 217, 0.8)';
    let borderSize = config.borderSize != null ? config.borderSize : 2;
    let gridColor = config.gridColor || 'rgba(74, 144, 217, 0.3)';
    let highlightColor = config.highlightColor || 'rgba(255, 200, 0, 0.6)';
    let gridOpacity = config.gridOpacity || 80;

    gridOverlay = new St.Widget({
        name: 'cintileGrid',
        reactive: true,
        can_focus: true,
        track_hover: true,
        x: monitor.x,
        y: monitor.y,
        width: monitor.width,
        height: monitor.height
    });

    let bgOpacity = gridOpacity / 100;
    gridOverlay.set_style('background-color: rgba(0, 0, 0, ' + (bgOpacity * 0.5) + ');');

    gridCells = [];

    // Work area relative to overlay origin (0, 0)
    let relativeWorkArea = { x: 0, y: 0, width: monitor.width, height: monitor.height };
    let gap = config.windowGap || 0;

    for (let row = 0; row < config.gridRows; row++) {
        gridCells[row] = [];

        for (let col = 0; col < config.gridCols; col++) {
            if (weights.colWeights[col] < 1 || weights.rowWeights[row] < 1) {
                gridCells[row][col] = null;
                continue;
            }

            let geom = Common.calculateCellGeometry(relativeWorkArea, weights.colWeights, weights.rowWeights, col, row);
            geom.x += gap;
            geom.y += gap;
            geom.width -= (gap * 2);
            geom.height -= (gap * 2);

            let cell = new St.Bin({
                style: 'background-color: ' + gridColor + '; ' +
                       'border: ' + borderSize + 'px solid ' + borderColor + '; ' +
                       'border-radius: 4px;'
            });
            cell.set_position(geom.x, geom.y);
            cell.set_size(geom.width, geom.height);

            if (KEY_LABELS[row] && KEY_LABELS[row][col]) {
                let label = new St.Label({
                    text: KEY_LABELS[row][col],
                    style: 'font-size: ' + textSize + 'px; color: ' + textColor + '; font-weight: bold;'
                });
                label.set_x_align(Clutter.ActorAlign.CENTER);
                label.set_y_align(Clutter.ActorAlign.CENTER);
                cell.set_child(label);
            }

            gridOverlay.add_child(cell);
            gridCells[row][col] = cell;
        }
    }

    Main.layoutManager.addChrome(gridOverlay, { affectsInputRegion: true });
    gridOverlay.connect('key-press-event', onKeyPress);

    if (!Main.pushModal(gridOverlay)) {
        global.logError("[CinTile] Failed to acquire modal grab");
        hideGrid();
        return;
    }

    firstTile = null;
}

// =============================================================================
// Monitor cycling
// =============================================================================

function cycleToNextMonitor() {
    let monitors = Main.layoutManager.monitors;

    if (gridOverlay) {
        Main.popModal(gridOverlay);
        Main.layoutManager.removeChrome(gridOverlay);
        gridOverlay.destroy();
        gridOverlay = null;
        gridCells = [];
        firstTile = null;
    }

    currentMonitorIndex = (currentMonitorIndex + 1) % monitors.length;
    displayGridOnMonitor(currentMonitorIndex);
}

// =============================================================================
// Grid teardown
// =============================================================================

function hideGrid() {
    if (gridOverlay) {
        Main.popModal(gridOverlay);
        Main.layoutManager.removeChrome(gridOverlay);
        gridOverlay.destroy();
        gridOverlay = null;
        gridCells = [];
        firstTile = null;
    }
    focusedWindow = null;
}

// =============================================================================
// Keyboard handling
// =============================================================================

function onKeyPress(actor, event) {
    let symbol = event.get_key_symbol();

    if (symbol === Clutter.KEY_Escape) {
        hideGrid();
        return true;
    }

    if (symbol === Clutter.KEY_space) {
        cycleToNextMonitor();
        return true;
    }

    if (!KEY_MAP[symbol]) {
        return false;
    }

    let tile = KEY_MAP[symbol];

    if (!firstTile) {
        firstTile = tile;
        if (config.showHighlight) {
            highlightCell(tile.row, tile.col, true);
        }
        return true;
    } else {
        tileWindow(firstTile, tile);
        hideGrid();
        return true;
    }
}

function highlightCell(row, col, highlight) {
    if (!gridCells[row] || !gridCells[row][col]) return;

    let borderColor = config.borderColor || 'rgba(74, 144, 217, 0.8)';
    let borderSize = config.borderSize != null ? config.borderSize : 2;
    let gridColor = config.gridColor || 'rgba(74, 144, 217, 0.3)';
    let highlightColor = config.highlightColor || 'rgba(255, 200, 0, 0.6)';

    if (highlight) {
        gridCells[row][col].set_style(
            'background-color: ' + highlightColor + '; ' +
            'border: ' + (borderSize + 1) + 'px solid rgba(255, 200, 0, 1); ' +
            'border-radius: 4px;'
        );
    } else {
        gridCells[row][col].set_style(
            'background-color: ' + gridColor + '; ' +
            'border: ' + borderSize + 'px solid ' + borderColor + '; ' +
            'border-radius: 4px;'
        );
    }
}

// =============================================================================
// Window tiling
// =============================================================================

function tileWindow(tile1, tile2) {
    let window = focusedWindow;

    if (!window || window.get_window_type() !== Meta.WindowType.NORMAL) {
        return;
    }

    let workspace = global.screen.get_active_workspace();
    let workArea = workspace.get_work_area_for_monitor(currentMonitorIndex);
    let weights = Common.getActiveWeights(config);

    // Span from top-left to bottom-right of the two selected tiles
    let minRow = Math.min(tile1.row, tile2.row);
    let maxRow = Math.max(tile1.row, tile2.row);
    let minCol = Math.min(tile1.col, tile2.col);
    let maxCol = Math.max(tile1.col, tile2.col);

    let startGeom = Common.calculateCellGeometry(workArea, weights.colWeights, weights.rowWeights, minCol, minRow);
    let endGeom = Common.calculateCellGeometry(workArea, weights.colWeights, weights.rowWeights, maxCol, maxRow);

    let gap = config.windowGap || 0;
    let x = startGeom.x + gap;
    let y = startGeom.y + gap;
    let width = (endGeom.x + endGeom.width) - startGeom.x - (gap * 2);
    let height = (endGeom.y + endGeom.height) - startGeom.y - (gap * 2);

    if (window.maximized_horizontally || window.maximized_vertically) {
        window.unmaximize(Meta.MaximizeFlags.BOTH);
    }

    GLib.idle_add(GLib.PRIORITY_DEFAULT, function() {
        window.move_frame(true, Math.floor(x), Math.floor(y));
        window.move_resize_frame(true, Math.floor(x), Math.floor(y), Math.floor(width), Math.floor(height));
        return false;
    });
}
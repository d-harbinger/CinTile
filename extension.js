const St = imports.gi.St;
const Clutter = imports.gi.Clutter;
const Main = imports.ui.main;
const Meta = imports.gi.Meta;
const Lang = imports.lang;
const GLib = imports.gi.GLib;
const Settings = imports.ui.settings;

// Import our common utilities
const ExtensionSystem = imports.ui.extensionSystem;
const Common = ExtensionSystem.extensions['cintile@forgetting.me'].common;

// Settings container
let config = null;
let settings = null;

// State
let gridOverlay = null;
let firstTile = null;
let gridCells = [];
let KEY_MAP = {};
let currentMonitorIndex = 0;
let focusedWindow = null;

// Available keys for mapping
const AVAILABLE_KEYS = [
    Clutter.KEY_q, Clutter.KEY_w, Clutter.KEY_e, Clutter.KEY_r,
    Clutter.KEY_a, Clutter.KEY_s, Clutter.KEY_d, Clutter.KEY_f,
    Clutter.KEY_z, Clutter.KEY_x, Clutter.KEY_c, Clutter.KEY_v,
    Clutter.KEY_t, Clutter.KEY_y, Clutter.KEY_g, Clutter.KEY_h,
    Clutter.KEY_u, Clutter.KEY_i, Clutter.KEY_j, Clutter.KEY_k,
    Clutter.KEY_b, Clutter.KEY_n, Clutter.KEY_o, Clutter.KEY_p
];

const KEY_LABELS = [
    ['Q', 'W', 'E', 'R', 'T', 'Y', 'U'],
    ['A', 'S', 'D', 'F', 'G', 'H', 'J'],
    ['Z', 'X', 'C', 'V', 'B', 'N', 'M'],
    ['I', 'O', 'P', '[', ']', '\\', ''],
    ['K', 'L', ';', "'", '', '', '']
];

function buildKeyMap() {
    KEY_MAP = {};
    let keyIndex = 0;
    
    let weights = Common.getActiveWeights(config);
    
    global.log("[CinTile] Building key map");
    global.log("[CinTile] Col weights: [" + weights.colWeights + "]");
    global.log("[CinTile] Row weights: [" + weights.rowWeights + "]");
    
    // Only map keys for cells with non-zero weights
    for (let row = 0; row < config.gridRows && keyIndex < AVAILABLE_KEYS.length; row++) {
        for (let col = 0; col < config.gridCols && keyIndex < AVAILABLE_KEYS.length; col++) {
            // Skip cells with zero weight (hidden)
            if (weights.colWeights[col] < 1 || weights.rowWeights[row] < 1) {
                continue;
            }
            
            KEY_MAP[AVAILABLE_KEYS[keyIndex]] = {row: row, col: col};
            keyIndex++;
        }
    }
    
    global.log("[CinTile] Mapped " + keyIndex + " keys");
}

function onSettingsChanged() {
    global.log("[CinTile] Settings changed");
    buildKeyMap();
    
    if (gridOverlay) {
        hideGrid();
        showGrid();
    }
}

function init(metadata) {
    global.log("[CinTile] Initializing extension");
    
    config = {};
    settings = new Settings.ExtensionSettings(config, metadata.uuid);
    
    // Bind grid dimensions
    settings.bindProperty(Settings.BindingDirection.IN, "grid-rows", "gridRows", onSettingsChanged, null);
    settings.bindProperty(Settings.BindingDirection.IN, "grid-cols", "gridCols", onSettingsChanged, null);
    
    // Bind column weights
    for (let i = 0; i < 7; i++) {
        settings.bindProperty(Settings.BindingDirection.IN, "col-" + i + "-weight", "col" + i + "Weight", onSettingsChanged, null);
    }
    
    // Bind row weights
    for (let i = 0; i < 5; i++) {
        settings.bindProperty(Settings.BindingDirection.IN, "row-" + i + "-weight", "row" + i + "Weight", onSettingsChanged, null);
    }
    
    // Bind appearance settings
    settings.bindProperty(Settings.BindingDirection.IN, "window-gap", "windowGap", onSettingsChanged, null);
    settings.bindProperty(Settings.BindingDirection.IN, "grid-opacity", "gridOpacity", onSettingsChanged, null);
    settings.bindProperty(Settings.BindingDirection.IN, "grid-color", "gridColor", onSettingsChanged, null);
    settings.bindProperty(Settings.BindingDirection.IN, "highlight-color", "highlightColor", onSettingsChanged, null);
    settings.bindProperty(Settings.BindingDirection.IN, "keybinding", "keybinding", null, null);
    
    buildKeyMap();
}

function enable() {
    global.log("[CinTile] Extension enabled!");
    
    Main.keybindingManager.addHotKey(
        "cintile-show-grid",
        config.keybinding,
        Lang.bind(this, showGrid)
    );
}

function disable() {
    global.log("[CinTile] Extension disabled!");
    Main.keybindingManager.removeHotKey("cintile-show-grid");
    
    if (gridOverlay) {
        hideGrid();
    }
}

function showGrid() {
    global.log("[CinTile] Showing grid!");
    
    if (gridOverlay) {
        hideGrid();
        return;
    }
    
    // Capture the focused window NOW
    focusedWindow = global.display.focus_window;
    
    // Find which monitor the focused window is on
    if (focusedWindow) {
        let rect = focusedWindow.get_frame_rect();
        let monitors = Main.layoutManager.monitors;
        
        let windowCenterX = rect.x + rect.width / 2;
        let windowCenterY = rect.y + rect.height / 2;
        
        for (let i = 0; i < monitors.length; i++) {
            let mon = monitors[i];
            if (windowCenterX >= mon.x && windowCenterX < mon.x + mon.width &&
                windowCenterY >= mon.y && windowCenterY < mon.y + mon.height) {
                currentMonitorIndex = i;
                global.log("[CinTile] Window is on monitor " + i);
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
        global.log("[CinTile] Invalid monitor index: " + monitorIndex);
        return;
    }
    
    let monitor = monitors[monitorIndex];
    let weights = Common.getActiveWeights(config);
    
    global.log("[CinTile] Displaying weighted grid on monitor " + monitorIndex);
    
    // Overlay positioned at monitor location
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
    
    let bgOpacity = config.gridOpacity / 100;
    gridOverlay.set_style('background-color: rgba(0, 0, 0, ' + (bgOpacity * 0.5) + ');');
    
    gridCells = [];
    
    // Create a RELATIVE work area (0,0 based) for cell calculations
    let relativeWorkArea = {
        x: 0,
        y: 0,
        width: monitor.width,
        height: monitor.height
    };
    
    // Create cells using weighted layout
    for (let row = 0; row < config.gridRows; row++) {
        gridCells[row] = [];
        
        for (let col = 0; col < config.gridCols; col++) {
            // Skip cells with zero weight
            if (weights.colWeights[col] < 1 || weights.rowWeights[row] < 1) {
                gridCells[row][col] = null;
                continue;
            }
            
            // Calculate geometry RELATIVE to overlay (0,0)
            let geom = Common.calculateCellGeometry(relativeWorkArea, weights.colWeights, weights.rowWeights, col, row);
            
            // Apply gap shrink
            let gap = config.windowGap;
            geom.x += gap;
            geom.y += gap;
            geom.width -= (gap * 2);
            geom.height -= (gap * 2);
            
            let cell = new St.Bin({
                style: 'background-color: ' + config.gridColor + '; ' +
                       'border: 2px solid rgba(74, 144, 217, 0.8); ' +
                       'border-radius: 4px;'
            });
            
            // Position RELATIVE to gridOverlay
            cell.set_position(geom.x, geom.y);
            cell.set_size(geom.width, geom.height);
            
            if (KEY_LABELS[row] && KEY_LABELS[row][col]) {
                let label = new St.Label({
                    text: KEY_LABELS[row][col],
                    style: 'font-size: 72px; color: white; font-weight: bold;'
                });
                label.set_x_align(Clutter.ActorAlign.CENTER);
                label.set_y_align(Clutter.ActorAlign.CENTER);
                cell.set_child(label);
            }
            
            gridOverlay.add_child(cell);
            gridCells[row][col] = cell;
        }
    }
    
    Main.layoutManager.addChrome(gridOverlay, {
        affectsInputRegion: true
    });
    
    gridOverlay.connect('key-press-event', onKeyPress);
    
    if (Main.pushModal(gridOverlay)) {
        global.log("[CinTile] Modal grabbed on monitor " + monitorIndex);
    }
    
    firstTile = null;
}

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
    
    global.log("[CinTile] Cycling to monitor " + currentMonitorIndex);
    
    displayGridOnMonitor(currentMonitorIndex);
}

function hideGrid() {
    global.log("[CinTile] Hiding grid!");
    
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

function onKeyPress(actor, event) {
    let symbol = event.get_key_symbol();
    
    if (symbol === Clutter.KEY_Escape) {
        hideGrid();
        return true;
    }
    
    if (symbol === Clutter.KEY_space) {
        global.log("[CinTile] Spacebar - cycling monitors");
        cycleToNextMonitor();
        return true;
    }
    
    if (!KEY_MAP[symbol]) {
        global.log("[CinTile] Invalid key");
        return false;
    }
    
    let tile = KEY_MAP[symbol];
    
    if (!firstTile) {
        firstTile = tile;
        global.log("[CinTile] First tile: " + tile.row + "," + tile.col);
        highlightCell(tile.row, tile.col, true);
        return true;
    } else {
        global.log("[CinTile] Second tile: " + tile.row + "," + tile.col);
        tileWindow(firstTile, tile);
        hideGrid();
        return true;
    }
}

function highlightCell(row, col, highlight) {
    if (gridCells[row] && gridCells[row][col]) {
        if (highlight) {
            gridCells[row][col].set_style(
                'background-color: ' + config.highlightColor + '; ' +
                'border: 3px solid rgba(255, 200, 0, 1); ' +
                'border-radius: 4px;'
            );
        } else {
            gridCells[row][col].set_style(
                'background-color: ' + config.gridColor + '; ' +
                'border: 2px solid rgba(74, 144, 217, 0.8); ' +
                'border-radius: 4px;'
            );
        }
    }
}

function tileWindow(tile1, tile2) {
    let window = focusedWindow;
    
    if (!window || window.get_window_type() !== Meta.WindowType.NORMAL) {
        Main.notify("CinTile", "No window to tile!");
        return;
    }
    
    global.log("[CinTile] Tiling window to monitor " + currentMonitorIndex);
    
    let workspace = global.screen.get_active_workspace();
    let workArea = workspace.get_work_area_for_monitor(currentMonitorIndex);
    
    let weights = Common.getActiveWeights(config);
    
    // Calculate combined area from two tiles
    let minRow = Math.min(tile1.row, tile2.row);
    let maxRow = Math.max(tile1.row, tile2.row);
    let minCol = Math.min(tile1.col, tile2.col);
    let maxCol = Math.max(tile1.col, tile2.col);
    
    // Get geometry for top-left cell
    let startGeom = Common.calculateCellGeometry(workArea, weights.colWeights, weights.rowWeights, minCol, minRow);
    // Get geometry for bottom-right cell
    let endGeom = Common.calculateCellGeometry(workArea, weights.colWeights, weights.rowWeights, maxCol, maxRow);
    
    // Combined area
    let x = startGeom.x;
    let y = startGeom.y;
    let width = (endGeom.x + endGeom.width) - startGeom.x;
    let height = (endGeom.y + endGeom.height) - startGeom.y;
    
    // Apply gap
    let gap = config.windowGap;
    x += gap;
    y += gap;
    width -= (gap * 2);
    height -= (gap * 2);
    
    if (window.maximized_horizontally || window.maximized_vertically) {
        window.unmaximize(Meta.MaximizeFlags.BOTH);
    }
    
    GLib.idle_add(GLib.PRIORITY_DEFAULT, function() {
        window.move_frame(true, Math.floor(x), Math.floor(y));
        window.move_resize_frame(
            true,
            Math.floor(x),
            Math.floor(y),
            Math.floor(width),
            Math.floor(height)
        );
        return false;
    });
    
    Main.notify("CinTile", "Window tiled!");
}
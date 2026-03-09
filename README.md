# CinTile

Keyboard-driven window tiling for the Cinnamon desktop environment. A port of [Tactile](https://gitlab.com/lundal/tactile) (GNOME) with weighted grid support.

## Features

- **Two-key tiling**: Press `Super+T` to show grid, press two keys to tile the focused window between those cells
- **Weighted grid**: Up to 7×5 grid with per-column and per-row weight control for non-uniform layouts
- **Multi-monitor**: Spacebar cycles the grid overlay between monitors
- **Visual grid editor**: Proportional cell preview with rows/columns and per-axis weight adjustment
- **Appearance controls**: Color theming (linked and unlinked modes), text size, border size, gap size, overlay opacity
- **Custom key bindings**: Click any grid cell and press a key to assign it — fully remappable layout
- **Configurable keybinding**: Default `Super+T`, changeable via Cinnamon Settings

## Install

### Using Make (recommended)

```bash
git clone https://github.com/d-harbinger/CinTile.git ~/Projects/CinTile
cd ~/Projects/CinTile
make deploy-restart
```

### Manual Install

```bash
git clone https://github.com/d-harbinger/CinTile.git ~/Projects/CinTile
mkdir -p ~/.local/share/cinnamon/extensions/cintile@d-harbinger/
cp ~/Projects/CinTile/{extension.js,common.js,metadata.json,settings-schema.json,icon.png,GridWidget.py,AppearanceWidget.py} \
  ~/.local/share/cinnamon/extensions/cintile@d-harbinger/
nohup cinnamon --replace &>/dev/null &
```

Then enable in **Cinnamon Settings → Extensions → CinTile**.

### Updating

```bash
cd ~/Projects/CinTile
git pull
make deploy-restart
```

### Verify

```bash
journalctl /usr/bin/cinnamon -f --no-pager | grep -i cintile
```

## Usage

| Key | Action |
|---|---|
| `Super+T` | Toggle grid overlay |
| `Q W E R T ...` | Select first tile, then second tile |
| `Spacebar` | Cycle grid to next monitor |
| `Escape` | Cancel / hide grid |

Press the same key twice (e.g. `Q Q`) to tile to a single cell. Press two different keys (e.g. `Q F`) to tile across the spanning area between those cells.

### Key Layout

Default keys map directly to the physical keyboard layout, scaling with grid size:

```
Row 0:  Q  W  E  R  T  Y  U
Row 1:  A  S  D  F  G  H  J
Row 2:  Z  X  C  V  B  N  M
```

A 2×4 grid uses Q W E R / A S D F. A 3×5 grid uses Q W E R T / A S D F G / Z X C V B. And so on.

To customize, click any cell in the Grid Layout settings widget and press a key to assign it. Right-click or press Delete to revert a cell to its default. Use the "Reset All" button to clear all custom bindings.

## File Structure

| File | Purpose |
|---|---|
| `extension.js` | Main logic — overlay, keyboard capture, tiling |
| `common.js` | Pure utility functions — weighted grid math |
| `metadata.json` | Extension identity and version compatibility |
| `settings-schema.json` | Configuration UI definition |
| `GridWidget.py` | Custom Python GTK3 widget for visual grid editor |
| `AppearanceWidget.py` | Custom Python GTK3 widget for appearance controls |
| `icon.png` | 64×64 extension icon |
| `cintile-icon.svg` | SVG source for icon |
| `Makefile` | deploy / restart / logs targets |

## Makefile Targets

| Target | Action |
|---|---|
| `make deploy` | Copy extension files to Cinnamon extensions directory |
| `make restart` | Restart Cinnamon |
| `make deploy-restart` | Deploy then restart |
| `make logs` | Tail Cinnamon journal filtered to CinTile |
| `make clean` | Remove extension from Cinnamon extensions directory |

## Technical Notes

- Settings use Cinnamon's `Settings.ExtensionSettings` with `bindProperty` for real-time JS updates
- Custom Python widgets write directly to the settings JSON file as a workaround for [Cinnamon Issue #9336](https://github.com/linuxmint/cinnamon/issues/9336) (custom widgets can't bind to JavaScript)
- Window positioning uses `GLib.idle_add()` for reliability
- Grid math uses Tactile's cumulative-weight algorithm via `common.js`

## Roadmap

- Cinnamon Spices store submission (requires `UUID/files/UUID/` restructure, `info.json`, `screenshot.png`)
- Localization support

## License

GPL-3.0 — same as Cinnamon and Tactile.
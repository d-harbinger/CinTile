# CinTile

Keyboard-driven window tiling for the Cinnamon desktop environment. A port of [Tactile](https://gitlab.com/lundal/tactile) (GNOME) with weighted grid support.

## Features

- **Two-key tiling**: Press `Super+T` to show grid, press two keys to tile the focused window between those cells
- **Weighted grid**: Up to 7×5 grid with per-column and per-row weight control
- **Multi-monitor**: Spacebar cycles the grid overlay between monitors
- **Configurable**: Grid colors, opacity, window gaps, and keybinding via Cinnamon Settings

## Install

```bash
# Clone
git clone d-harbinger ~/Projects/CinTile
cd ~/Projects/CinTile

# Deploy to Cinnamon
make deploy

# Enable in Cinnamon Settings → Extensions → CinTile
# Or restart Cinnamon: make restart
```

## Usage

| Key | Action |
|---|---|
| `Super+T` | Toggle grid overlay |
| `Q W E R ...` | Select first tile, then second tile |
| `Spacebar` | Cycle grid to next monitor |
| `Escape` | Cancel / hide grid |

Press the same key twice (e.g. `Q Q`) to tile to a single cell.


## File Structure

| File | Purpose |
|---|---|
| `extension.js` | Main logic — overlay, keyboard capture, tiling |
| `common.js` | Pure utility functions — weighted grid math |
| `metadata.json` | Extension identity and version compatibility |
| `settings-schema.json` | Configuration UI definition |
| `stylesheet.css` | Reserved for CSS-based theming |

## Known Issues / TODO

- Settings UI uses spinbuttons for weight config — planned: visual grid editor widget
- Cinnamon Issue [#9336](https://github.com/linuxmint/cinnamon/issues/9336) prevents custom widgets from binding to JS code

## License

GPL-3.0 — same as Cinnamon and Tactile.
# CinTile

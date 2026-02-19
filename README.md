# CinTile

Keyboard-driven window tiling for the Cinnamon desktop environment. A port of [Tactile](https://gitlab.com/lundal/tactile) (GNOME) with weighted grid support.

## Features

- **Two-key tiling**: Press `Super+T` to show grid, press two keys to tile the focused window between those cells
- **Weighted grid**: Up to 7×5 grid with per-column and per-row weight control
- **Multi-monitor**: Spacebar cycles the grid overlay between monitors
- **Configurable**: Grid colors, opacity, window gaps, and keybinding via Cinnamon Settings

## Install

### Using Make (recommended)

```bash
# Clone
git clone https://github.com/d-harbinger/CinTile.git ~/Projects/CinTile
cd ~/Projects/CinTile

# Deploy to Cinnamon
make deploy

# Restart Cinnamon
make restart
```

### Manual Install

```bash
# Clone
git clone https://github.com/d-harbinger/CinTile.git ~/Projects/CinTile

# Deploy to Cinnamon extension directory
mkdir -p ~/.local/share/cinnamon/extensions/cintile@forgetting.me/
cp ~/Projects/CinTile/{extension.js,common.js,metadata.json,settings-schema.json,stylesheet.css} \
  ~/.local/share/cinnamon/extensions/cintile@forgetting.me/

# Restart Cinnamon
nohup cinnamon --replace &>/dev/null &
```

Then enable in **Cinnamon Settings → Extensions → CinTile**.

### Verify

```bash
journalctl /usr/bin/cinnamon -f --no-pager | grep -i cintile
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
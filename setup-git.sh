#!/usr/bin/env bash
# =============================================================================
# CinTile Git Init — Run from ~/Projects/CinTile (or wherever your source is)
# Creates git support files alongside your existing source, initializes repo
# =============================================================================
set -euo pipefail

UUID="cintile@forgetting.me"
EXT_DIR="$HOME/.local/share/cinnamon/extensions/${UUID}"

echo "╔══════════════════════════════════════════╗"
echo "║         CinTile — Git Init               ║"
echo "╚══════════════════════════════════════════╝"
echo ""

# --- Sanity check: are we in the right directory? ---
if [ ! -f "extension.js" ] || [ ! -f "common.js" ]; then
    echo "[ERROR] extension.js and/or common.js not found in $(pwd)"
    echo "        Run this script from your CinTile source directory."
    exit 1
fi

echo "[OK] Source files found in $(pwd)"

# =============================================================================
# .gitignore
# =============================================================================
echo "[WRITE] .gitignore"
cat > .gitignore << 'EOF'
*.pyc
__pycache__/
*.swp
*.swo
*~
.vscode/
*.bak
EOF

# =============================================================================
# Makefile
# =============================================================================
echo "[WRITE] Makefile"
cat > Makefile << 'EOF'
UUID = cintile@forgetting.me
EXT_DIR = $(HOME)/.local/share/cinnamon/extensions/$(UUID)
SRC_FILES = extension.js common.js metadata.json settings-schema.json

.PHONY: deploy restart logs clean

deploy:
	@mkdir -p $(EXT_DIR)
	@cp -v $(SRC_FILES) $(EXT_DIR)/
	@echo "✓ Deployed to $(EXT_DIR)"

restart:
	@echo "Restarting Cinnamon..."
	@nohup cinnamon --replace &>/dev/null &
	@echo "✓ Cinnamon restarting"

deploy-restart: deploy restart

logs:
	@journalctl /usr/bin/cinnamon -f --no-pager | grep -i cintile

clean:
	@rm -rf $(EXT_DIR)
	@echo "✓ Removed $(EXT_DIR)"
EOF

# =============================================================================
# README.md
# =============================================================================
echo "[WRITE] README.md"
cat > README.md << 'EOF'
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
git clone <your-repo-url> ~/Projects/CinTile
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

## Development

```bash
make deploy          # Copy files to extension directory
make restart         # Restart Cinnamon (X11)
make deploy-restart  # Both
make logs            # Tail Cinnamon logs filtered for CinTile
make clean           # Remove from extension directory
```

Debug via Looking Glass: `Alt+F2` → `lg`

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
EOF

# =============================================================================
# LICENSE (GPL-3.0 header)
# =============================================================================
echo "[WRITE] LICENSE"
cat > LICENSE << 'EOF'
GNU GENERAL PUBLIC LICENSE
Version 3, 29 June 2007

Copyright (C) 2007 Free Software Foundation, Inc. <https://fsf.org/>

Everyone is permitted to copy and distribute verbatim copies of this
license document, but changing it is not allowed.

See https://www.gnu.org/licenses/gpl-3.0.txt for the full license text.
EOF

# =============================================================================
# Initialize git repo + first commit
# =============================================================================
echo ""
if [ -d ".git" ]; then
    echo "[SKIP] Git repo already exists"
else
    echo "[GIT]  Initializing repository"
    git init
fi

echo "[GIT]  Staging all files"
git add -A

echo "[GIT]  Creating initial commit"
git commit -m "Initial commit — CinTile v0.2.0

Keyboard-driven window tiling for Cinnamon (Tactile port)
- Weighted grid system (up to 7x5)
- Two-key tile selection
- Multi-monitor support with spacebar cycling
- Configurable via Cinnamon Settings"

echo ""
echo "╔══════════════════════════════════════════════════════════════╗"
echo "║  Done! Repository initialized.                              ║"
echo "║                                                              ║"
echo "║  Next steps:                                                 ║"
echo "║    1. Create repo on GitHub/GitLab                           ║"
echo "║    2. git remote add origin <your-repo-url>                  ║"
echo "║    3. git push -u origin main                                ║"
echo "║                                                              ║"
echo "║  Deploy:  make deploy                                        ║"
echo "║  Test:    Super+T                                            ║"
echo "╚══════════════════════════════════════════════════════════════╝"
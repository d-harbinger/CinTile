# CLAUDE.md — CinTile

Keyboard-driven window tiling for the Cinnamon desktop: press `Super+T` for a
grid overlay, then two keys to tile the focused window between those cells.
A port of GNOME's [Tactile](https://gitlab.com/lundal/tactile) with weighted
rows and columns. GPL-3.0, matching Cinnamon and Tactile.

## Project at a glance

- **Two runtimes, one extension.** This is the single most important fact
  about the repo. `extension.js` and `common.js` run as **GJS** — Cinnamon's
  SpiderMonkey JavaScript. `GridWidget.py` and `AppearanceWidget.py` are
  **PyGObject/GTK3** widgets embedded in the Cinnamon settings window. Logic
  that looks duplicated across the two is usually a real language boundary,
  not laziness; check which side a file runs on before "deduplicating".
- **No build step, no package manager, no test suite.** The source files
  *are* the deployed artifact. `common.js` holds the pure weighted-grid math;
  `settings-schema.json` defines the configuration UI.
- **Identity**: UUID `cintile@d-harbinger`, version `0.3.0`,
  `cinnamon-version: ["6.6"]` — all in `metadata.json`. Bump the version
  there when shipping, and widen `cinnamon-version` only after testing on
  that release.

## Install and iterate

| Task | Command |
|---|---|
| Deploy + restart Cinnamon | `make deploy-restart` |
| Deploy only | `make deploy` |
| Watch the logs | `make logs` |
| Remove the installed copy | `make clean` |

`make deploy` copies into
`~/.local/share/cinnamon/extensions/cintile@d-harbinger/`. Enable it once in
**Cinnamon Settings → Extensions → CinTile**. `make restart` runs
`cinnamon --replace`, which restarts the running desktop session.

**The `SRC_FILES` list in the `Makefile` is the deploy manifest.** A new
runtime file that is not added there is silently never deployed, and the
extension keeps running the old code — a confusing failure that looks like a
caching problem. Add the file to `SRC_FILES` in the same change.

## Verification boundary

CinTile can only be verified inside a running Cinnamon session, which this
environment does not have. Nothing about tiling behaviour, the overlay, key
capture, or the settings widgets can be claimed as working from here — deploy
and observe is the owner's step. `make logs` is the diagnostic channel.

## Gotchas

- **The Python widgets write the settings JSON file directly.** That is a
  deliberate workaround for [Cinnamon issue #9336](https://github.com/linuxmint/cinnamon/issues/9336)
  — custom settings widgets cannot bind to JavaScript. The JS side picks the
  values up through `Settings.ExtensionSettings` with `bindProperty`. Do not
  "fix" the direct write without checking that the binding path actually
  works on the target Cinnamon release.
- **Window positioning goes through `GLib.idle_add()`** for reliability;
  moving it back onto the synchronous path reintroduces placement races.
- **Store submission is not just a tag.** The Cinnamon Spices listing needs a
  `UUID/files/UUID/` restructure plus `info.json` and `screenshot.png` — a
  packaging change, tracked in the README roadmap alongside localization.
- Untracked files exist at the repo root (an editor workspace file, a
  `nohup.out` from a Cinnamon restart). They are not source; leave them out
  of any commit.

## Where things are documented

`README.md` covers install, key layout, the Makefile targets, and the
technical notes. The audit and decision record — including why the two
runtimes make a naive duplication count wrong, and why no security pass
applies (no network surface, no subprocess, no secrets; the only input is
the logged-in user's own settings) — lives at
`~/Projects/claude-settings/workspace/audits/CinTile/TEACHING.md`.
Do not create a `TEACHING.md` at this repo's root.

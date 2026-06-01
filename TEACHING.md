# TEACHING.md — CinTile

Per-project AI-codegen slop audit for the workspace library cleanup. Two jobs at once:
(1) find this project's slop, taught with **the repo's own code** as the examples; (2) record
*what Claude did and why*, so a later learning pass (via the `bionic` tool) can read the reasoning,
not just the result.

CinTile is a Cinnamon desktop extension: a keyboard-driven window tiler (a port of GNOME's
[Tactile](https://gitlab.com/lundal/tactile)) with a weighted grid. The runtime is **GJS**
(`extension.js` + `common.js`, Cinnamon's SpiderMonkey JavaScript) and the settings UI is
**PyGObject/GTK3** (`GridWidget.py`, `AppearanceWidget.py`). That two-runtime split is the
single most important fact for reading the findings below — half the "duplication" is a real
language boundary, not laziness, and the audit has to tell the two apart.

---

## Re-audit — 2026-06-01 (shape pass, no source changes)

Re-ran the classification and re-read every file. **Verdict unchanged: shape pass, security n/a.**

**Why no security pass.** CinTile has no remote attack surface. There is no HTTP server, no SSR,
no API routes, no network client, no database, no subprocess spawned from input, no authentication,
and no secret handling. The only "input" is the logged-in user configuring their own desktop
through Cinnamon's settings UI. The one place external data crosses into a sink is settings color
and size strings flowing into Clutter/St `set_style()` CSS (`extension.js` lines 195, 219–222,
231, 336–347) and into the Python Cairo preview — but Clutter CSS is a styling grammar with no
`url()` fetch and no script execution, the values originate from the same user running the shell,
and a malformed string degrades to a no-op render, not code execution. An actor able to write
those settings already controls the user's session. So there is no untrusted-input path to trace;
a security audit doc would have nothing to analyze. Classification stays SHAPE.

**State vs. the 2026-05-29 findings:** finding #2 (dead imports / `UUID` / `_suppress_handler` /
stray `highlightColor`) remains applied and committed (`69c2115`). Findings #1 (4-source
appearance defaults) and #3 (tripled cell-style string) are **still present and still host-gated**
— they live in `extension.js`, which only loads under Cinnamon's GJS runtime; `node --check` proves
syntax, not behavior, so a behavior-preserving refactor there cannot be verified green in a
display-less VM and is not applied. Re-verified this pass: `py_compile` clean on both widgets,
`node --check` clean on both JS files. This pass also corrected drift inside this document itself
(hardcoded mount path → workspace; `master` → `main`).

---

## Snapshot — 2026-05-29

**What it is:** ~1,250 LOC of hand-shaped code across a clean split:

| File | LOC | Runtime | Role |
|------|-----|---------|------|
| `GridWidget.py` | 536 | GTK3/PyGObject | visual grid editor (Cairo-drawn preview, click-to-assign keys) |
| `extension.js` | 388 | GJS | overlay, modal keyboard capture, window tiling |
| `AppearanceWidget.py` | 289 | GTK3/PyGObject | color/size controls, linked-color theming |
| `common.js` | 70 | GJS (pure) | weighted-grid geometry math |
| `settings-schema.json` | 145 | — | Cinnamon settings declaration (the canonical defaults) |

**Git state:** on `main`; functional history (UUID migration, live key-binding sync) below a stack
of privacy-guard infra commits and the finding-#2 cleanup (`69c2115`). Privacy hook is active
(`core.hooksPath=scripts/hooks`), `.gitleaks.toml` present. `nohup.out` (Cinnamon log) sits in the
working tree but is **gitignored** — local litter, not committed cruft, so out of audit scope.

**Slop profile — counts lie, name the real shape:** this is **low-slop, well-structured code with
light residue**, not a slop pile. The residue is the *classic AI-codegen tell set* in miniature:
imports added "just in case" and never used, a defensive guard flag wired for a reentrancy that
**cannot happen**, a local variable copied into a function that never reads it, and one genuine
constant restated across files. There is no god-object, no dead feature, no copy-paste explosion.

**Strengths (credit what's genuinely good):**
- **`common.js` is exemplary.** Pure functions, JSDoc, zero Cinnamon deps, an explicit header
  comment ("safe for reuse and testing"), honest upstream attribution to Tactile, and a real
  divide-by-zero guard (`if (totalColWeight === 0 …) return zero-rect`). This is what right looks
  like — the geometry kernel is isolated from the framework on *both* sides (mirrored in the
  Python preview's own `_on_draw`).
- **Defensive at the right edges:** modal-grab failure is handled (`if (!Main.pushModal…)`),
  invalid monitor index is logged and bailed, every `JSON.parse` of stored bindings is wrapped in
  try/catch. The defensiveness is real where input is untrusted — it's only *misplaced* in the one
  flag finding below.
- **Honest README** with a real Technical Notes section (cites the actual Cinnamon bug #9336 that
  forces the Python-writes-JSON workaround). Not a stock template.

---

## Findings (ranked by leverage)

### 1 — [MEDIUM] Appearance defaults have four sources of truth
**Tell.** The default colors/sizes (`rgba(74, 144, 217, 0.3)`, text-size `48`, border `2`, …) are
written out in **four** places: `settings-schema.json` (Cinnamon's canonical store),
`AppearanceWidget.py`'s `DEFAULTS` dict, and **twice** inside `extension.js` as `||` fallbacks —
once in `displayGridOnMonitor` (lines 176–182) and again in `highlightCell` (lines 331–334). A
`grep` for the four default color literals finds **19** occurrences across the files.

**Why an AI does it.** Each function is generated in isolation with "safe defaults so it never
renders blank." The model optimizes locally — every consumer gets its own fallback — and never
asks "where does the default *live*?" The result reads as defensive but is really four copies that
drift independently (change the theme blue in the schema and the JS overlay silently keeps the old
one until every fallback is hand-edited).

**Detect.**
```bash
grep -rn "rgba(74, 144, 217" extension.js AppearanceWidget.py GridWidget.py settings-schema.json | wc -l
```
Any single default literal appearing in 3+ files is the smell.

**Fix (partly host-gated — see triage).** The cross-*runtime* copies are a real boundary: GJS and
Python can't share a module, and Cinnamon reads `settings-schema.json` natively, so those three
*must* each state a default. That leaves **one** removable duplication: the **two** `||`-fallback
blocks inside `extension.js` collapse into a single `getAppearance(config)` helper, so the overlay
and the highlight read defaults from one place. Behavior-preserving but it runs only under
Cinnamon (GJS) — **deferred to a host-verify session**, documented not yet applied. The schema ↔
Python ↔ JS split is *inherent*; the right move there is a one-line comment in each pointing at the
schema as canonical, not a refactor.

### 2 — [LOW] Dead imports, dead constant, dead flag, dead local (the AI residue) — ✅ FIXED
**Tell.** Scaffolding that was generated, then never wired:
- `AppearanceWidget.py`: `import json`, `import os`, `GLib`, `Gio` — **none used**. Plus a
  module-level `UUID = "cintile@d-harbinger"` constant that's never read.
- `GridWidget.py`: `import os`, `GLib` unused; same dead `UUID` constant; `import math` buried
  *inside* `_rounded_rect` instead of at the top.
- `AppearanceWidget.py`: `self._suppress_handler = False` — a reentrancy guard, checked at the top
  of `_on_color_set` and `_on_spin_changed`, but **never set to `True` anywhere**. It guards a
  feedback loop that cannot occur: `_apply_theme_color` calls `set_rgba()` programmatically, and
  GTK's `color-set` signal fires only on *user* interaction, not on `set_rgba()`. The loop the flag
  defends against is structurally impossible.
- `extension.js`: `let highlightColor = …` declared in `displayGridOnMonitor` (line 181) and never
  used there — the real uses live in `highlightCell`, which correctly declares its own.

**Why an AI does it.** Two distinct tells. The unused imports are **"import the usual suspects"** —
GUI codegen front-loads `os`/`json`/`GLib`/`Gio` because most GTK files need *some* of them, then
the actual code only touches `Gtk`/`Gdk`. The `_suppress_handler` flag is **defensive cargo-cult**:
reentrancy guards are a real PyGObject pattern, so the model adds one prophylactically without
tracing whether *this* code can actually re-enter. The stray `highlightColor` is **copy-paste
drift** — the appearance-unpacking block was pasted into both functions; only one uses every field.

**Detect.**
```bash
python3 - <<'PY'   # zero-dep unused-import check (pyflakes wasn't installed)
import ast
for fn in ("GridWidget.py","AppearanceWidget.py"):
    t=ast.parse(open(fn).read()); imp={}
    for n in ast.walk(t):
        if isinstance(n,ast.Import):      [imp.setdefault((a.asname or a.name).split('.')[0],n.lineno) for a in n.names]
        if isinstance(n,ast.ImportFrom):  [imp.setdefault(a.asname or a.name,n.lineno) for a in n.names]
    used={x.id for x in ast.walk(t) if isinstance(x,ast.Name)}
    print(fn, [k for k in imp if k not in used] or "CLEAN")
PY
grep -n "_suppress_handler" AppearanceWidget.py   # flag set True anywhere? (no = dead guard)
```

**Fix.** Delete all of it. The `_suppress_handler` removal is the instructive one: the two
`if self._suppress_handler: return` guards always fell through (flag was always `False`), so
removing them is *behavior-identical* — proven by the fact that nothing sets the flag. Moved
`import math` to the top of `GridWidget.py`. Verified: `py_compile` clean, AST reports both files
have zero unused imports, `node --check` parses both JS files.

### 3 — [LOW] Tripled style-string construction in `extension.js`
**Tell.** The cell CSS string — `background-color: …; border: …px solid …; border-radius: 4px;` —
is built three times: once in `displayGridOnMonitor` (the base cell, lines 220–223) and twice in
`highlightCell` (the highlight branch and the un-highlight/restore branch, lines 337–347).

**Why an AI does it.** Same root as #1 — each function is authored standalone, so the same template
literal is re-typed wherever a cell needs styling, rather than factored into a
`cellStyle(bg, borderColor, borderSize)` helper.

**Detect.** `grep -c "border-radius: 4px" extension.js` → 3.

**Fix (host-gated).** Extract a `cellStyle(bg, border, size)` helper; the three call sites become
one-liners. Behavior-preserving string assembly, but GJS-only — **bundled with #1 into the
host-verify session**, not yet applied. Documented here so the host session has the exact target.

### 4 — [INFORMATIONAL] JS↔Python key-table duplication is *inherent*, not slop
**Tell.** `AVAILABLE_KEYS`/`KEY_LABELS` in `extension.js` are byte-for-byte the same Q-W-E-R… grids
as `DEFAULT_CODES`/`DEFAULT_LABELS` in `GridWidget.py`.

**Why it's here.** The editor (Python) and the runtime (GJS) are different processes in different
languages with **no shared module** — GDK keysyms and Clutter keysyms happen to share integer
values, which is *why* the tables can be identical. This is a genuine cross-runtime boundary, the
same one as #1's schema/Python/JS split.

**Detect.** N/A — flagged so a future reader doesn't "fix" it by inventing a build step.

**Fix.** **None.** Don't DRY across a process/language boundary for a 21-entry static table; a
shared codegen step would cost more than it saves. The correct treatment is a comment in each table
noting the other copy must be kept in sync. Recorded so this isn't re-litigated.

### Non-findings (looked, cleared)
- `self.key` / `self.info` are stored-but-never-read in both widgets — but that mirrors Cinnamon's
  `SettingsWidget(info, key, settings)` constructor idiom. Left as framework convention, not slop.
- README says *"Reset All"* button; the code labels it *"Reset Keys"*. Trivial doc drift, noted
  only — not worth a commit on its own; fold into any future README touch.

---

## Triage / cleanup plan

| # | Finding | Severity | Action | Status |
|---|---------|----------|--------|--------|
| 1 | 4-source appearance defaults | MEDIUM | Collapse the **two** `extension.js` `||` fallback blocks → one `getAppearance(config)`; comment schema as canonical for the cross-runtime copies | ⬜ host-verify (GJS, can't run in VM) |
| 2 | Dead imports / `UUID` / `_suppress_handler` / `highlightColor` | LOW | Delete all; move `math` import to top | ✅ done 2026-05-29 (py_compile + AST + node --check) |
| 3 | Tripled cell-style string | LOW | Extract `cellStyle()` helper | ⬜ host-verify (bundled with #1) |
| 4 | JS↔Python key tables | INFO | Keep; add sync comment | ⬜ optional (comment-only) |

---

## What I did — and why (2026-05-29)

**Landed the safe tier only (finding #2), deferred the GJS refactors (#1, #3).** The split is the
whole point of this session's discipline:

- **#2 is statically provable safe.** Removing unused imports can't change behavior; removing the
  `_suppress_handler` guards is behavior-identical *because the flag was never set* — the early
  returns never fired. I didn't have to *run* anything to know that; the proof is in the absence of
  any `= True` assignment. So I removed it and verified three ways with tools that work in a
  display-less VM: `python3 -m py_compile` (both compile), an inline AST pass (both report zero
  unused imports), and `node --check` (both JS files parse).

- **#1 and #3 touch `extension.js`, which only runs inside Cinnamon (GJS/SpiderMonkey).** I cannot
  start a Cinnamon session in the VM — it's display-less and the user's Cinnamon is host-side. A
  string-assembly refactor is *almost certainly* behavior-preserving, but "almost certainly" on
  code I can't execute is exactly the gap this audit's verification gate exists to close. So I
  wrote the exact target into the triage table and left application to a `make deploy-restart`
  host session, consistent with how chef-calc's behavior-touching refactors were deferred.

- **#4 I deliberately did *not* "fix".** The instinct to DRY the duplicated key tables is the
  wrong instinct across a language boundary — the teaching point is *knowing when duplication is
  cheaper than the abstraction that removes it.* Recorded as a non-fix so it isn't re-opened.

The meta-lesson for the learning pass: **most of this file's "slop" is the residue of local,
per-function generation** — each piece is reasonable alone; the waste only shows when you read the
file as a whole and ask "where does this value/guard/string actually *need* to live?" The fix is
almost never "write more code," it's "delete the copies and name the one source."

---

## Verification gate

`py_compile` / `node --check` / "it parses" is **necessary but not sufficient** — it proves the
code loads, not that the extension behaves. What's been proven and what's owed:

**Proven (VM, this session):**
- `python3 -m py_compile GridWidget.py AppearanceWidget.py` → clean.
- Inline AST unused-import check → both files CLEAN (0 unused).
- `node --check extension.js && node --check common.js` → both parse.
- `grep` confirms `_suppress_handler`, dead `UUID`, `import os`, and the stray `highlightColor`
  local are gone; the surviving `highlightColor` references are the live ones (the property
  binding + the real use in `highlightCell`).

**Owed (host, before any "#1/#3 fixed" claim):** the user runs `make deploy-restart`, then in
Cinnamon: `Super+T` shows the grid → two-key tile works → spacebar cycles monitors → Escape hides;
open Settings → grid editor renders, +/- weights and click-to-assign work; appearance panel link
toggle + color buttons + spin buttons all still apply live. Only after that does the GJS-side work
graduate from "should be fine" to "verified."

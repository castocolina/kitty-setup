## Context

`phase2-friendly-color-input` shipped the scenes color layer (`normalize_color`,
`launch_scene`, recipe loader). Four polish gaps remain (see proposal). Two
touch the runtime scene engine (`scenes/launcher.py`, `scenes/colors.py`), one
the shell-completion surface (`cli.py` + a completer), one the install path
(`installer.py`, `pyproject.toml`, `tools/setup.sh`).

Two facts are probe-grounded against kitty 0.47.1 on this host
(`tmp/h26-perpane-opacity/run.py` + `run_tabs.py`):
- `set-background-opacity --match id:<pane>` changes the **whole OS window**
  (`background_opacity` 1.0→0.5); kitty `ls` exposes opacity only on the
  OS-window object, never on a tab or window. **No per-pane or per-tab opacity.**
- The current-tab fill bug: `launch_scene` keys on `$KITTY_WINDOW_ID` presence
  alone, never querying the origin tab's window count.

## Goals / Non-Goals

**Goals:**
- Color names autocomplete on the single-noun color commands and `--tab-accent`.
- A multi-pane scene reuses the current tab **only** when that tab holds exactly
  one window; otherwise it opens a clean new tab.
- `my-kitty install` seeds packaged example scenes copy-if-absent; user edits and
  user-authored scenes are never overwritten or deleted.
- Alpha hex (`#rgba` / `#rrggbbaa`) is accepted and silently reduced to its solid
  color; no confusing rejection.

**Non-Goals:**
- Per-pane or per-tab opacity (kitty cannot; proven by probe).
- Mapping a color's alpha to OS-window opacity (rejected: it would dim unrelated
  tabs sharing the OS window). Opacity stays the explicit `os-window opacity`.
- Completing hex values or completing `bg=` inside the inline `--pane` token
  (single opaque arg — out of reach for argcomplete).
- Changing the single-pane scene path (it still joins the current tab; see D2
  risk note).

## Decisions

### D1 — `_origin_tab_is_solo(origin_window, to) -> bool` gates fill-current-tab
A new helper runs `kitten @ ls`, parses the JSON tree, finds the tab whose
`windows` contains `id == origin_window`, and returns `len(windows) == 1`. The
condition in `launch_scene` becomes:

```
if origin_window is not None and not single and _origin_tab_is_solo(origin_window, to):
    return _fill_current_tab(...)
# else → existing new-tab path (launch --type=tab …)
```

**Fail-safe:** any failure (ls non-zero, JSON error, origin id not found) returns
`False` → open a new tab. Rationale: never silently add windows to a populated
tab; a spurious new tab is recoverable, a corrupted layout is annoying. This is
the probe-observable lesson — verify tab state, don't infer it from "inside
kitty". The `ls` shape is already grounded (harness + h23 traverse it).

### D2 — Single-pane path unchanged
A single-pane scene keeps launching one `--type=window` into the current tab.
It adds exactly one window (not a layout), which is a mild, expected effect; the
reported bug is specifically the multi-pane 4-window case. Narrowing single-pane
too is deferred (open question, noted as a risk) to keep this change scoped.

### D3 — `normalize_color` accepts 4/8-digit hex and strips alpha
`_HEX_RE` widens to also match 4 and 8 hex digits. When matched:
- 8 digits (`rrggbbaa`) → return `#rrggbb` (drop last 2).
- 4 digits (`rgba`) → return `#rgb` (drop last 1).
- 3/6 digits → unchanged (existing behavior).

Resolution order is preserved: empty→None, `none`→`NONE`, `:`/`(` passthrough,
**then** the widened hex match, then name lookup, then `ColorError`. Strip is
**silent** (flexible; no stderr noise) — the chosen default. Because the strip
happens in the one shared normalizer, it covers per-pane `bg`, `tab_accent`, and
the single-noun commands uniformly. Tabs have no opacity and panes can't be
individually translucent, so dropping alpha loses nothing kitty could honor.

### D4 — Color completion mirrors `scene_name_completer`
A `color_completer(prefix="", **_)` returns color **names** from
`COLOR_NAMES` matching `prefix`, plus `NONE`. To keep the list usable, the
numbered grays/greys (`gray0`..`gray100`) are **excluded** from completion
(≈200 low-signal entries) — base names + `gray`/`grey` still complete; the full
table still *resolves*, only the suggestion list is trimmed. Wired via
`.completer = color_completer` on the relevant argparse arguments in `cli.py`,
exactly like the scene-name positional. Lives next to the table it reads
(`scenes/colors.py` or `scenes/_color_table.py`), exported through
`scenes/__init__`.

### D5 — Seeding lives in `installer.py`, examples packaged as data
`my-kitty install` calls a new `seed_scenes()`:
- Source: example scenes **bundled into the package** (mirror `_payload_source()`
  — `pyproject.toml` force-includes `examples/scenes` → `kitty_setup/_scenes`).
  This is why it must be Python, not bash: the installed binary has no repo.
- Target: `$XDG_CONFIG_HOME/kitty-setup/scenes/` (the recipe loader's
  `scenes_dir()`), created if absent.
- Policy: **copy-if-absent per file** — copy each bundled `*.toml` only when the
  target filename does not exist. Never overwrite. Log a one-line summary
  (`scenes: seeded N, kept M existing`). Idempotent.
- The `cp -r examples/scenes/*` line added to `tools/setup.sh` is removed.

**Uninstall:** unchanged — it strips the sentinel block + payload + backups and
never touches `~/.config/kitty-setup/scenes/` (user data, outside the payload).
A user-deleted example reappears on the next install (accepted wrinkle of
copy-if-absent; documented).

### D6 — Probe verdict promoted to a repro doc
`docs/repro/h26-perpane-opacity.md` records the OS-window-only opacity finding
(Why, Manual repro, Linux Status verified on kitty 0.47.1, macOS deferred,
Known limitations) so the conclusion outlives `tmp/`.

## Risks / Trade-offs

- **`ls` adds one round trip** to every in-kitty multi-pane launch (~a few ms).
  Acceptable; correctness over a marginal call. Fail-safe means an `ls` hiccup
  degrades to "new tab", never to a wrong layout.
- **Copy-if-absent re-seeds a user-deleted example** on reinstall. Chosen over a
  `.seeded` manifest (state/complexity) and over first-run-only (existing users
  never get new examples). Documented behavior.
- **Silent alpha strip can surprise** a user who expected translucency from
  `#rrggbbaa`. Mitigated by the repro doc + example comments; revisitable to a
  soft stderr note if it bites.
- **Single-pane still joins a populated tab** (D2). If this also annoys in
  practice, a follow-up applies the same solo predicate to the single-pane path.
- **Packaging `examples/` as data** couples the wheel to that directory; if
  examples move, the force-include path must move with them (same constraint the
  `config/kitty` payload already lives under).

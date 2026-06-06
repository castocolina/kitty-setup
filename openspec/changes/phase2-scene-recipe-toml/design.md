## Context

`phase2-scene-launcher` shipped the imperative composition primitive:
`launch_scene(layout, tab_title, tab_accent, panes: list[Pane], *, to)` in
`src/kitty_setup/scenes/launcher.py`, driven by `my-kitty scene launch --pane
'k=v,…'`. The engine is probe-grounded (h25, kitty 0.46.2 on the user's host)
and green. Its one ergonomic wart is the inline authoring surface: a
comma-separated, backslash-escaped flag string. Phase 2 §12 / roadmap bullet 7
asks for the recipe form — author once in a file, launch by name.

This change is almost entirely a **front-end**: parse a TOML file into the four
arguments `launch_scene()` already takes. No wire behavior changes, so no new
hypothesis probe is warranted (the kitten-call algorithm is settled by h25). The
risk surface is local file IO, TOML schema validation, and CLI dispatch — all
deterministic and unit-testable.

Requirements §13 (named *presets* referenced by name — window presets, tab
presets, scenes composed from presets) is a richer, separate capability. This
change deliberately ships only the **flat** recipe: `[[pane]]` tables hold inline
definitions, not preset references.

## Goals / Non-Goals

**Goals:**

- Launch a named scene from a TOML file via `my-kitty scene launch <name>`,
  reusing `launch_scene()` and `Pane` unchanged.
- A flat TOML schema that maps 1:1 onto the engine arguments and `Pane` fields.
- Enumerate scenes via `my-kitty scene list` with a rich, human-readable summary.
- Treat scene files as user data that the installer/uninstaller never touch.
- Match the inline parser's validation strictness (unknown keys, types) and add
  a path-traversal guard on the scene name.
- Zero new dependencies (`tomllib` is stdlib in 3.12).

**Non-Goals:**

- §13 preset layer (named window/tab presets, reference-by-name composition).
- `scene close`/`scene down` (scene→tab teardown).
- One-off override flags in name mode (`scene launch monitoring --tab-accent=…`).
- Any change to the kitten-call algorithm, `launch_scene()`, or `Pane`.
- A `cmd` argv-array form (string + `bash -lc` only, as today).
- macOS visual verification (deferred-with-reason in the repro doc).

## Decisions

### D1 — Overload `scene launch` with an optional positional, add sibling `scene list`

`scene launch` gains a positional `name` (`nargs='?'`, default `None`).
Dispatch in `cli_scene_launch`:

```
name set      and  --pane set   → error: contradictory forms
name set      and  no --pane    → recipe.load_scene(name) → launch_scene(...)
name unset    and  --pane set   → today's inline path (unchanged)
name unset    and  no --pane    → error: need a name or at least one --pane
name set      and  style flag   → error: file is authoritative
```

`scene list` is a **separate** sub-subcommand, not `scene launch list` — under
the overload, `scene launch list` parses as "launch the scene named `list`", so
listing must be its own verb. This is the single most important naming decision:
it keeps the positional namespace clean.

*Alternatives considered:* (a) a distinct verb like `scene up <name>` /
`scene load <name>` — rejected in explore in favor of one verb, two modes, so the
inline and named forms read as the same gesture. (b) `scene launch list` as the
enumeration path — rejected because it collides with a scene literally named
`list`.

### D2 — Flat TOML schema, keys = engine vocabulary

```toml
layout     = "tall:mirrored=true"   # optional → launch_scene(layout=…)
tab_title  = "monitoring"           # optional
tab_accent = "#001f3f"              # optional

[[pane]]                            # 1+ required
title = "docker"                    # → Pane.title
cmd   = "docker ps"                 # → Pane.cmd  (run via bash -lc)
cwd   = "/srv"                      # → Pane.cwd
bg    = "#001f3f"                   # → Pane.bg
```

Top-level recognised keys: exactly `layout`, `tab_title`, `tab_accent`. Pane
recognised keys: exactly the `Pane` field names `title`, `cmd`, `cwd`, `bg`.
`recipe.py` **imports `Pane` from `launcher.py`** — it never redefines the
dataclass or coins parallel names. (Direct lesson from the launcher's earlier
`active=` vs `active_bg=` drift: a composition layer that invents its own
vocabulary silently diverges from the primitive.) Empty string → `None`, so the
guard stays `if pane.title is not None`, identical to `parse_pane_spec`.

*Alternatives considered:* nested single-file schema (`[scenes.<name>]` with
`[[scenes.<name>.pane]]`) — rejected in explore for one-file-per-scene, which
makes `scene list` a directory read and keeps `[[pane]]` arrays flat.

### D3 — `recipe.py` owns file/IO; `launcher.py` keeps the wire

New module `src/kitty_setup/scenes/recipe.py`:

- `scenes_dir() -> Path` — `Path(os.environ.get("XDG_CONFIG_HOME",
  Path.home()/".config")) / "kitty-setup" / "scenes"`.
- `load_scene(name) -> tuple[str|None, str|None, str|None, list[Pane]]` —
  validate `name` (D4), resolve `<dir>/<name>.toml`, `tomllib.load`, validate
  schema, build `list[Pane]`. Raises a typed error (e.g. `SceneRecipeError`)
  with a clear message on any failure; the unknown-name error embeds
  `list_scenes()` names.
- `list_scenes() -> list[...]` — sorted summaries (name, tab_title, pane count,
  or a malformed marker) for `scene list`.
- `cli_scene_list(args)` — argparse handler; honors `--names`/`-q`.

`launcher.py`'s `cli_scene_launch` gains the name branch (calls
`recipe.load_scene` then `launch_scene`); the engine, `Pane`, and inline parser
are untouched. `scenes/__init__.py` exports `recipe` so `cli.py` references
`scenes.recipe.cli_scene_list` and tests can monkeypatch.

*Alternatives considered:* fold everything into `launcher.py` — rejected to keep
the file-IO/validation concern separate from the wire concern, mirroring the
one-module-per-concern shape of the scenes package.

### D4 — Path-traversal guard + strict validation

`name` becomes a filename, so before any IO: reject `name` containing `/`,
`os.sep`, `os.altsep`, a `..` segment, or that is empty — raise the typed error.
Resolve `<dir>/<name>.toml` and, defensively, assert the resolved path's parent
equals `scenes_dir()`.

Schema validation mirrors `parse_pane_spec`: unknown top-level key → error
naming it + the recognised set; unknown `[[pane]]` key → same; wrong TOML type
(e.g. `layout = 123`, `[[pane]]` not a table) → error naming the key and
expected type; no `[[pane]]` → the engine's existing "at least one pane"
rejection (raised here with a friendly message before any kitten call). All
validation happens before the first kitten call, so a bad recipe never leaves a
half-built tab.

### D5 — Verification surface (no new probe)

No `tmp/hNN` probe: the wire algorithm is h25-settled and untouched. Coverage:

- **Unit** `tests/unit/test_scenes_recipe.py`:
  - `load_scene` happy path (full schema → exact tuple); `Pane` imported from
    launcher (identity check); empty-string→None.
  - Schema errors: unknown top-level key, unknown pane key, wrong type, no
    `[[pane]]`.
  - Path-traversal: `../x`, `a/b`, `..`, empty → rejected without IO.
  - Unknown name → error lists available scenes.
  - `scenes_dir()` honors `$XDG_CONFIG_HOME`.
  - `list_scenes()` rich output, malformed-file marker, empty/missing dir.
  - `cli_scene_launch` mode conflicts: name+`--pane`, neither, name+style flag.
- **Integration** `tests/integration/test_scene_recipe_e2e.py`, gated on
  `KITTI_INTEGRATION=1`, reusing `tests/integration/_kitty_subprocess.py`: write
  a temp `.toml`, spawn kitty, run `my-kitty scene launch <name>` via
  `subprocess.run` with `KITTY_LISTEN_ON=unix:/tmp/kitty-<pid>` in env (same
  cross-process socket-pinning trick as the h25 e2e test), assert new tab title,
  3 windows in order, `layout_opts.mirrored == "y"`, and `p2` bg `#001f3f` — the
  same observables the h25 e2e test asserts for the inline form.
- **Repro** `docs/repro/scene-recipe-toml.md` — standard sections.

## Risks / Trade-offs

- **Scene-name collision with `list`** → mitigated by making `scene list` a
  sibling sub-subcommand, never `scene launch list`; a scene file named
  `list.toml` is still launchable via `scene launch list` unambiguously because
  the positional only ever names a scene.
- **Path traversal via `name`** → mitigated by the D4 guard (reject separators /
  `..`) plus a resolved-parent assertion before any read.
- **Silent schema drift between inline and recipe forms** → mitigated by D2
  importing `Pane` from `launcher.py` and reusing its field names verbatim; a
  shared unit test asserts the recipe keys equal the `Pane` fields.
- **Installer/uninstall clobbering user scenes** → mitigated by siting scenes at
  `~/.config/kitty-setup/scenes/` (user data), distinct from the managed payload
  at `~/.config/kitty/kitty-setup/`; no installer code writes there. A reviewer
  check confirms the path is never referenced by `installer.py`.
- **No new probe could hide a real wire change** → accepted: the engine is
  unchanged by construction (recipe only builds its arguments); the e2e
  integration test re-asserts the wire observables end-to-end as a backstop.
- **`tomllib` is read-only** → fine; the loader only reads. No write path is in
  scope (authoring is by hand or a future `scene save`, out of scope here).

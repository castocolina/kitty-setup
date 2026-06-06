## Why

Phase 2 §12 of `docs/requirements.md` (roadmap bullet 7) asks for a TOML
*recipe*: "Spawn N windows in a tab with per-window styles and startup commands,
from a TOML recipe." The imperative half shipped in `phase2-scene-launcher`
(`my-kitty scene launch --pane …`) — but the authoring surface there is a
comma-separated, backslash-escaped flag string (`--pane 'title=docker,cmd=docker
run --env VAR=value\, bash'`). That escaping is exactly what a recipe file should
make unnecessary. This change completes the *declarative* half: define a scene
once in a TOML file, launch it by name. It does not touch the launch engine —
`launch_scene()` already takes `(layout, tab_title, tab_accent, list[Pane])`, so
the only new work is a file front-end that builds those arguments.

## What Changes

- **OVERLOADED CLI subcommand `my-kitty scene launch <name>`** — the existing
  `scene launch` gains an optional positional `name` (`nargs='?'`).
  `scene launch <name>` loads `…/scenes/<name>.toml` and materialises it via the
  unchanged `launch_scene()` engine; `scene launch --pane …` is today's inline
  form, byte-for-byte unchanged. Mode errors: a `name` **and** `--pane` together
  is contradictory (exit 1); neither is "need a scene name or at least one
  `--pane`" (exit 1). In name mode the **file is authoritative** — passing
  `--layout`/`--tab-title`/`--tab-accent` alongside a name is rejected (one-off
  overrides are a deferred follow-up). `--to` stays global to both modes.
- **NEW CLI subcommand `my-kitty scene list`** — a sibling sub-subcommand (NOT
  `scene launch list`, which would collide with the positional and try to load a
  scene literally named `list`). Default output is a column-aligned table with a
  `NAME`/`TAB`/`PANES` header, parsed from each TOML (so a malformed scene
  surfaces here, early); column widths are computed by terminal display width
  (stdlib `unicodedata`, no `rich` dependency) so emoji tab titles stay aligned.
  An optional `--names`/`-q` flag prints bare names for scripting.
- **Shell tab-completion for the scene name** — the `scene launch` positional
  carries an argcomplete completer that globs `*.toml` stems in the scenes
  directory (no TOML parse, so a malformed recipe never breaks completion).
- **MODIFIED launch behavior (engine, affects inline + named):** a scene with
  **exactly one pane** launches that pane as a `--type=window` into the CURRENT
  tab (no new tab; `--layout`/`--tab-title`/`--tab-accent` not applied) — a
  multi-pane scene still opens a new tab. Every pane that does not set its own
  `cwd` inherits the launch directory (`os.getcwd()` of the `my-kitty` process),
  so the tab and its windows open where the scene was launched from.
- **TOML schema (flat, 1:1 with the engine):** top-level `layout`, `tab_title`,
  `tab_accent`; an array of `[[pane]]` tables with `title`, `cmd`, `cwd`, `bg`.
  Keys are exactly the `launch_scene` arguments and `Pane` field names. `cmd` is
  a string run via `bash -lc` (engine untouched). An empty string normalises to
  `None`/absent, mirroring `parse_pane_spec`. Unknown top-level or pane keys and
  wrong value types are **rejected** (same strictness as the inline parser).
- **Scene files are USER DATA at `$XDG_CONFIG_HOME/kitty-setup/scenes/<name>.toml`**
  (fallback `~/.config/kitty-setup/scenes/`). Scene name = filename stem. This
  directory is deliberately **separate** from the managed payload at
  `~/.config/kitty/kitty-setup/`: the installer never writes user scenes and
  uninstall never deletes them. A missing directory yields a friendly empty
  state, not an error.
- **New Python module `src/kitty_setup/scenes/recipe.py`** — `scenes_dir()`,
  `load_scene(name) -> (layout, tab_title, tab_accent, list[Pane])`,
  `list_scenes()`, and `cli_scene_list`. It **imports `Pane` from
  `launcher.py`** and does not redefine the dataclass or its field names
  (composition primitives reuse the primitive's vocabulary). `cli_scene_launch`
  in `launcher.py` gains the name branch: `recipe.load_scene(name)` then
  `launch_scene(...)`.
- **Path-traversal guard on `name`** — `/`, `..`, and path separators are
  rejected so a scene name can never escape the scenes directory. Unknown scene
  name errors list the available scenes (`list_scenes()` does double duty).
- **Verification.** No new `tmp/hNN` wire probe — the kitten call algorithm is
  already h25-grounded and unchanged; the new surface is deterministic
  TOML→args. Covered by unit tests (loader happy/error paths, schema validation,
  path-traversal guard, list output) plus ONE end-to-end integration test
  (`KITTI_INTEGRATION=1`) that writes a temp `.toml`, runs `scene launch <name>`
  against a real kitty, and asserts the same tab/pane/bg observables as the h25
  e2e test. Plus a repro doc under `docs/repro/`.
- **`tomllib` (Python 3.12 stdlib, read-only). Zero new dependencies.**
- **No config-payload changes, no new doctor check.** Scene launching is a
  runtime gesture, not an install-time invariant.

## Capabilities

### New Capabilities

None. The declarative recipe is a front-end onto the existing `kitty-scenes`
launcher; it adds Requirements to that capability rather than introducing a new
one.

### Modified Capabilities

- `kitty-scenes`: add "Named TOML scene recipes launch under `my-kitty scene
  launch <name>`", "Scene recipes are user data", "Scene enumeration ships under
  `my-kitty scene list`", "Scene recipe loader lives at `recipe.py`", "Scene name
  shell-completes", and the repro-doc Requirement. **MODIFY** the "Scene launcher
  composition primitive" Requirement: a single-pane scene now launches into the
  current tab (not a new tab), and panes default to the launch directory. No
  changes to the single-noun primitive Requirements (title, accent, background,
  font, opacity, socket discovery, package layout).

## Impact

- **Affected code (new):**
  - `src/kitty_setup/scenes/recipe.py` — `scenes_dir()`, `load_scene()`,
    `list_scenes()`, `cli_scene_list`, schema validation, path-traversal guard.
  - `tests/unit/test_scenes_recipe.py` — loader happy/error paths, schema
    strictness, empty-string→None, path-traversal rejection, `scene list` output.
  - `tests/integration/test_scene_recipe_e2e.py` — one e2e test gated on
    `KITTI_INTEGRATION=1`.
  - `docs/repro/scene-recipe-toml.md` — repro doc (Why, Manual repro, Linux
    Status, macOS Status, Attempted alternatives, Known limitations, Recipes).
- **Affected code (modified):**
  - `src/kitty_setup/scenes/launcher.py` — `cli_scene_launch` gains the name
    branch; mode-conflict and authoritative-file guards.
  - `src/kitty_setup/cli.py` — add the optional positional `name` to the
    existing `scene launch` subparser; add the sibling `scene list` subparser
    wired to `scenes.recipe.cli_scene_list`.
  - `src/kitty_setup/scenes/__init__.py` — export `recipe` so
    `scenes.recipe.*` is reachable from `cli.py` and monkeypatchable in tests.
- **Out of scope (explicit follow-ups):**
  - §13 preset layer — named window/tab presets referenced by name. This change
    ships FLAT inline scenes only; `[[pane]]` holds definitions, not references.
  - `scene close`/`scene down` — needs scene→tab identity tracking; fragile via
    title-match. Deferred with reason.
  - One-off override flags in name mode (`scene launch monitoring
    --tab-accent=…`).
  - macOS visual verification — deferred-with-reason in the repro doc; the
    `kitten @` protocol is platform-agnostic.
- **Dependencies:** none added (`tomllib` is stdlib in 3.12).
- **Performance:** identical to `phase2-scene-launcher` (6 kitten calls /
  ~85 ms for a 3-pane scene); the loader adds one local file read.

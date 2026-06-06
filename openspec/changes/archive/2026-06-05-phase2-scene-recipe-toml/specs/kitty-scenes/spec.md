## ADDED Requirements

### Requirement: Named TOML scene recipes launch under `my-kitty scene launch <name>`

The `my-kitty` binary SHALL accept an optional positional `name` on the existing
`scene launch` subcommand (`nargs='?'`). When a `name` is supplied,
`my-kitty scene launch <name>` SHALL load the scene recipe at
`<scenes_dir>/<name>.toml`, build the same `(layout, tab_title, tab_accent,
list[Pane])` arguments the inline `--pane` form produces, and materialise the
scene by invoking the **unchanged** `launch_scene()` engine. The declarative
form SHALL introduce no new kitten-call behavior: the wire algorithm, exit-code
semantics, and styling are exactly those of the `scene launch` composition
Requirement.

The two invocation modes SHALL be mutually exclusive and validated before any
kitten call:

- A `name` together with any `--pane` flag SHALL exit non-zero with a stderr
  message stating the two forms are contradictory.
- Neither a `name` nor any `--pane` SHALL exit non-zero with a stderr message
  stating that a scene name or at least one `--pane` is required.
- In name mode the recipe file SHALL be authoritative: supplying
  `--layout`, `--tab-title`, or `--tab-accent` alongside a `name` SHALL exit
  non-zero with a stderr message stating those flags are not accepted with a
  named scene.
- The `--to=unix:<socket>` flag SHALL remain valid in both modes.

The TOML schema SHALL be flat and map one-to-one onto the engine arguments.
Recognised top-level keys SHALL be exactly `layout`, `tab_title`, and
`tab_accent` (all optional strings). Panes SHALL be expressed as an array of
`[[pane]]` tables whose recognised keys SHALL be exactly `title`, `cmd`, `cwd`,
and `bg` — the `Pane` field names. The loader SHALL import the `Pane` dataclass
from `launcher.py` and SHALL NOT redefine it or rename its fields. A `cmd` value
SHALL be a string carried into the engine's `bash -lc <cmd>` wrapping unchanged.
A key whose value is an empty string SHALL normalise to `None` (absent),
mirroring `parse_pane_spec`.

Schema validation SHALL match the strictness of the inline parser: any unknown
top-level key or unknown `[[pane]]` key, and any value of the wrong TOML type,
SHALL cause the command to exit non-zero with a stderr message naming the
offending key (and, for an unknown key, the recognised set) before any kitten
call is issued. A recipe with no `[[pane]]` table SHALL be rejected with the
engine's existing "at least one pane" semantics.

#### Scenario: Named scene launches from its TOML file

- **WHEN** `<scenes_dir>/monitoring.toml` contains `tab_title = "🐳 mon"`, `layout = "tall:mirrored=true"`, and three `[[pane]]` tables (`title="p1", cmd="echo p1"`; `title="p2", bg="#001f3f", cmd="echo p2"`; `title="p3"`) and the user invokes `my-kitty scene launch monitoring`
- **THEN** a new tab titled `🐳 mon` appears with the `tall` layout (`layout_opts.mirrored == "y"`), the tab contains exactly 3 windows titled `p1`, `p2`, `p3` in order, `p2`'s `background` reads `#001f3f`, and the command exits 0 — identical to the equivalent inline `--pane` invocation

#### Scenario: Name and `--pane` together is rejected

- **WHEN** the user invokes `my-kitty scene launch monitoring --pane 'title=x'`
- **THEN** the command exits non-zero, prints a stderr message stating that a named scene and inline `--pane` flags are contradictory, and creates no new tab

#### Scenario: Neither name nor `--pane` is rejected

- **WHEN** the user invokes `my-kitty scene launch` with no positional name and no `--pane`
- **THEN** the command exits non-zero and prints a stderr message stating a scene name or at least one `--pane` is required

#### Scenario: Inline `--pane` form is unchanged

- **WHEN** the user invokes `my-kitty scene launch --tab-title=t --pane 'title=p1,cmd=echo p1'` with no positional name
- **THEN** the behavior is byte-for-byte identical to the `phase2-scene-launcher` inline form (same kitten calls, same exit code)

#### Scenario: Style flags with a named scene are rejected

- **WHEN** the user invokes `my-kitty scene launch monitoring --tab-accent=#ff0000`
- **THEN** the command exits non-zero and prints a stderr message stating `--layout`/`--tab-title`/`--tab-accent` are not accepted with a named scene (the recipe file is authoritative)

#### Scenario: Unknown key in a recipe is rejected before any kitten call

- **WHEN** `<scenes_dir>/bad.toml` contains a top-level `tab_color = "#fff"` (unknown key) and the user invokes `my-kitty scene launch bad`
- **THEN** the command exits non-zero, prints a stderr message naming the unknown key `tab_color`, and calls `kitten @ launch` zero times

#### Scenario: Empty-string value normalises to absent

- **WHEN** a `[[pane]]` table contains `title = ""` alongside `cmd = "echo hi"`
- **THEN** the constructed `Pane` has `title is None` (not `""`), so no `--title` flag is emitted, matching the inline parser's empty-value behavior

### Requirement: Scene recipes are user data under `$XDG_CONFIG_HOME/kitty-setup/scenes/`

The scenes directory SHALL resolve to `$XDG_CONFIG_HOME/kitty-setup/scenes/`
when `$XDG_CONFIG_HOME` is set, otherwise `~/.config/kitty-setup/scenes/`. This
location SHALL be distinct from the managed payload at
`~/.config/kitty/kitty-setup/`: the installer SHALL NOT write scene files there
and uninstall SHALL NOT delete them. A scene's name SHALL be the file stem
(`monitoring.toml` → `monitoring`).

The `name` positional SHALL be guarded against path traversal: a `name`
containing a path separator (`/`), a `..` segment, or any OS path separator
SHALL be rejected with a non-zero exit and a stderr message, so a scene name can
never resolve outside the scenes directory. A request for a name with no
matching file SHALL exit non-zero with a stderr message that lists the available
scene names. A missing scenes directory SHALL be treated as "no scenes" (a
friendly empty state), not an error.

The loader SHALL use `tomllib` from the Python standard library; the change SHALL
add no new third-party dependency.

#### Scenario: Path-traversal name is rejected

- **WHEN** the user invokes `my-kitty scene launch ../../etc/something`
- **THEN** the command exits non-zero with a stderr message about an invalid scene name, and reads no file outside the scenes directory

#### Scenario: Unknown scene name lists what is available

- **WHEN** the scenes directory contains `monitoring.toml` and `docker.toml`, and the user invokes `my-kitty scene launch nope`
- **THEN** the command exits non-zero and the stderr message lists `docker` and `monitoring` as the available scenes

#### Scenario: XDG override is honored

- **WHEN** `$XDG_CONFIG_HOME` is set to `/tmp/xdg` and `/tmp/xdg/kitty-setup/scenes/demo.toml` exists
- **THEN** `my-kitty scene launch demo` loads that file (the resolver prefers `$XDG_CONFIG_HOME` over `~/.config`)

### Requirement: Scene enumeration ships under `my-kitty scene list`

The `my-kitty` binary SHALL expose a `scene list` sub-subcommand — a sibling of
`scene launch`, NOT `scene launch list` (which would be parsed as a request to
launch a scene named `list`). With no flags it SHALL print, one scene per line
in sorted order, a rich summary of each `*.toml` recipe in the scenes directory:
the scene name, its `tab_title` (if any), and its pane count, parsed from the
file. A recipe that fails to parse SHALL be reported on its line as malformed
(with the parse error) rather than silently omitted. An empty or missing scenes
directory SHALL print a friendly empty-state message and exit 0.

The default output SHALL be a column-aligned table with a header row
(`NAME`, `TAB`, `PANES`); column widths SHALL be computed by terminal display
width (East-Asian wide / fullwidth code points counted as two cells, zero-width
combining marks skipped) so emoji-bearing tab titles do not collapse adjacent
columns. This alignment SHALL be done in-process with the standard library only
(no `rich` or other third-party table dependency).

`scene list` SHALL accept an optional `--names`/`-q` flag that prints only the
bare scene names, one per line, for scripting.

#### Scenario: Aligned table with a header

- **WHEN** the scenes directory contains `monitoring.toml` (3 panes, `tab_title="monitoring"`) and `docker.toml` (2 panes, `tab_title="docker"`) and the user invokes `my-kitty scene list`
- **THEN** the command exits 0, the first line is a `NAME`/`TAB`/`PANES` header, and there is one sorted, column-aligned row per scene showing the name, tab title, and pane count

#### Scenario: Malformed recipe is surfaced, not hidden

- **WHEN** the scenes directory contains a `broken.toml` with invalid TOML and the user invokes `my-kitty scene list`
- **THEN** the `broken` line indicates the file is malformed and includes the parse error, and the command still lists the other valid scenes

#### Scenario: Empty scenes directory is a friendly empty state

- **WHEN** the scenes directory is missing or contains no `*.toml` files and the user invokes `my-kitty scene list`
- **THEN** the command exits 0 and prints a message indicating there are no scenes yet

#### Scenario: `--names` prints bare names for scripting

- **WHEN** the user invokes `my-kitty scene list --names`
- **THEN** only the sorted bare scene names are printed, one per line, with no tab-title or pane-count decoration

### Requirement: Scene recipe loader lives at `src/kitty_setup/scenes/recipe.py`

The recipe loader SHALL ship as `src/kitty_setup/scenes/recipe.py`, a sibling of
`launcher.py`. It SHALL import the `Pane` dataclass from
`kitty_setup.scenes.launcher` (reusing the engine's vocabulary rather than
redefining it) and otherwise import only from the standard library
(`tomllib`, `pathlib`, `os`). The module SHALL export at minimum: `scenes_dir()`
returning the resolved scenes `Path`; `load_scene(name) -> (layout, tab_title,
tab_accent, list[Pane])` performing path-traversal guarding, file resolution,
TOML parsing, and schema validation; `list_scenes()` returning the sorted scene
summaries used by `scene list`; and a `cli_scene_list(args)` handler that
argparse calls via `set_defaults(func=…)`. The `cli_scene_launch` handler in
`launcher.py` SHALL gain the name branch that calls `recipe.load_scene(name)`
then `launch_scene(...)`.

The `scenes` package SHALL export `recipe` (added to
`src/kitty_setup/scenes/__init__.py`) so `cli.py` references the handler as
`scenes.recipe.cli_scene_list` (mirroring `scenes.launcher.cli_scene_launch`)
and tests can monkeypatch it.

#### Scenario: Loader reuses the engine's `Pane`, not a copy

- **WHEN** a reviewer inspects `src/kitty_setup/scenes/recipe.py`
- **THEN** `Pane` is imported from `kitty_setup.scenes.launcher` and is not redefined in `recipe.py`; the recognised pane keys are exactly the `Pane` field names

#### Scenario: `load_scene` is a pure function exercisable without kitty

- **WHEN** a unit test points `scenes_dir()` at a temp directory containing `demo.toml` and calls `load_scene("demo")` with no kitty running
- **THEN** the call returns the parsed `(layout, tab_title, tab_accent, [Pane, …])` tuple without making any subprocess call

### Requirement: Manual repro doc records the declarative recipe

A repro doc SHALL ship at `docs/repro/scene-recipe-toml.md` with the standard
sections (Why, Manual repro, Linux Status, macOS Status, Attempted alternatives,
Known limitations, Recipes). The Manual repro SHALL show authoring a
`<scenes_dir>/<name>.toml` and launching it with `my-kitty scene launch <name>`,
plus a `my-kitty scene list` example. macOS visual verification SHALL be
deferred-with-reason (the `kitten @` protocol is platform-agnostic; tab-bar
rendering nuances may differ). Verification SHALL note that no new `tmp/hNN`
wire probe is introduced because the kitten-call algorithm is unchanged from
h25; the declarative surface is covered by unit tests plus one end-to-end
integration test gated on `KITTI_INTEGRATION=1`.

#### Scenario: Repro doc exists with the standard sections

- **WHEN** a reviewer opens `docs/repro/scene-recipe-toml.md`
- **THEN** it contains the Why, Manual repro, Linux Status, macOS Status, Attempted alternatives, Known limitations, and Recipes sections, and the Manual repro demonstrates both `scene launch <name>` and `scene list`

#### Scenario: End-to-end integration test covers the named-launch path

- **WHEN** a reviewer reads `tests/integration/test_scene_recipe_e2e.py`
- **THEN** it contains at least one test, gated on `KITTI_INTEGRATION=1`, that writes a temp `.toml` recipe, runs `my-kitty scene launch <name>` against a freshly spawned kitty, and asserts the same tab/pane/bg observables as the h25 e2e test

### Requirement: Scene name shell-completes for `scene launch`

The positional `name` of `scene launch` SHALL carry an argcomplete completer
that returns the `*.toml` file stems in the scenes directory, so a user pressing
TAB after `my-kitty scene launch ` gets the available scene names. The completer
SHALL glob filenames only (no TOML parse), so a malformed recipe never breaks
completion, and SHALL filter by the current prefix.

#### Scenario: Tab-completion lists scene names by prefix

- **WHEN** the scenes directory holds `dev.toml`, `docker.toml`, `broken.toml` (malformed) and the user requests completion for prefix `d`
- **THEN** the completer returns `dev` and `docker` (sorted), does not raise on the malformed file, and excludes non-matching names

## MODIFIED Requirements

### Requirement: Scene launcher composition primitive ships under `my-kitty scene launch`

The `my-kitty` binary SHALL expose a `scene launch` subcommand that composes the existing scene primitives (title, accent, background, layout) into one user gesture. Invoking `my-kitty scene launch <args>` SHALL spawn one or more panes, each optionally pre-styled with title, working directory, background color, and a startup command.

The destination depends on the **pane count** and on whether the launch happens **from inside kitty** (the `$KITTY_WINDOW_ID` environment variable, exported by kitty into every window, identifies the origin window):

- A multi-pane scene launched **from inside kitty** (`$KITTY_WINDOW_ID` is set) SHALL be materialised INTO the current tab: the origin window becomes pane 0 (restyled in place via `set-window-title` / `set-colors`, with any explicit pane-0 `cwd`/`cmd` fed to the reused shell via `send-text`), the remaining panes open as `--type=window` splits in the same tab, and `--layout` / `--tab-title` / `--tab-accent` are applied to that current tab (kitty defaults `goto-layout` / `set-tab-title` / `set-tab-color` to the focused tab, so no `--match` is needed). NO new tab is created. This is the in-kitty path, so a multi-pane scene launched from a shell never steals a separate tab.
- A scene with **two or more panes** launched with **no origin window** (`$KITTY_WINDOW_ID` unset — e.g. driven over a socket from another terminal) SHALL open a NEW tab, optionally apply a layout, spawn the panes inside the new tab, and optionally tint the tab — the probe-grounded multi-pane algorithm.
- A scene with **exactly one pane** SHALL launch that pane as a `kitten @ launch --type=window` into the CURRENT tab (no new tab is created), regardless of `$KITTY_WINDOW_ID` (it does not commandeer the origin shell). For a single-pane scene the `--layout`, `--tab-title`, and `--tab-accent` inputs SHALL NOT be applied — there is no new tab to own them. Per-window styling (`title`, `cwd`, `bg`, `cmd`) SHALL still apply.

Every pane that does not set its own `cwd` SHALL inherit a caller-supplied default working directory (the `default_cwd` argument to `launch_scene`, wired to the launching process's `os.getcwd()` in `cli_scene_launch`), so a scene's tab AND windows open in the directory the user launched it from rather than kitty's startup directory. An explicit per-pane `cwd` SHALL override the default.

The CLI surface SHALL be:

```
my-kitty scene launch \
    [<name>] \
    [--layout=<name>[:<opts>]] \
    [--tab-title=<text>] [--tab-accent=<color>] \
    --pane 'key=value,key=value,...' \
    [--pane '...'] ... \
    [--to=unix:<socket>]
```

The `--pane` flag SHALL accept a comma-separated `key=value` group. Recognised keys SHALL be exactly `title`, `cmd`, `cwd`, and `bg`. Any unknown key SHALL cause the command to exit non-zero with a stderr message naming the offending key and listing the recognised set. Commas inside a value SHALL be escapable as `\,` and backslashes as `\\`. The `--pane` flag SHALL be repeatable. The inline `--pane` form and the named `<name>` form are mutually exclusive; at least one pane (inline or via a named recipe) MUST be provided (zero panes is rejected with exit non-zero).

The launcher SHALL use the existing `scenes._client.kitten_at()` surface for every kitten call, inheriting `$KITTY_LISTEN_ON` → `pgrep -x kitty` socket discovery and the kitten binary resolution from h22's foundation. No new socket-discovery code SHALL be introduced.

The launcher SHALL fail-hard on any `kitten @ launch` non-zero exit (propagate the kitten exit code and stop processing further panes). It SHALL fail-soft on `kitten @ set-colors` and `kitten @ set-tab-color` failures (print the kitten stderr to its own stderr, mark the overall exit code non-zero, but continue building the rest of the scene). The first non-zero kitten exit code SHALL be propagated as the launcher's exit code.

Every user-supplied `cmd=...` SHALL be wrapped as `bash -lc <cmd>` when passed to `kitten @ launch` so the user's shell features (`|`, `$VAR`, `;`, `&&`, etc.) work transparently without any quoting code in the launcher.

#### Scenario: Multi-pane scene composes a new tab in one user gesture

- **WHEN** the user invokes `my-kitty scene launch --layout=tall:mirrored=true --tab-title="🐳 mon" --pane 'title=p1,cmd=echo p1' --pane 'title=p2,bg=#001f3f,cmd=echo p2' --pane 'title=p3'` with `$KITTY_WINDOW_ID` unset (driven over a socket from another terminal)
- **THEN** a new tab whose title is `🐳 mon` appears, the active layout is `tall` with `layout_opts.mirrored == "y"`, the new tab contains exactly 3 windows whose titles are `p1`, `p2`, `p3` in order, `p2`'s `background` reads `#001f3f`, and the command exits 0

#### Scenario: Multi-pane scene fills the current tab when launched inside kitty

- **WHEN** the running kitty has one tab with one window, and the user invokes a 3-pane scene (`layout=tall`, `tab_title="DEV"`, panes `shell` / `git` / `watch`) from a shell **inside that window** so `$KITTY_WINDOW_ID` is set
- **THEN** NO new tab is created (the tab count is unchanged), the current tab holds exactly the 3 scene panes in order (`shell` is the reused origin window, `git` and `watch` are new splits), the tab's title becomes `DEV`, the active layout is `tall`, and the command exits 0

#### Scenario: Single-pane scene joins the current tab

- **WHEN** the running kitty has one tab and the user invokes a one-pane scene (inline `--pane 'title=solo'` or a named recipe with a single `[[pane]]`)
- **THEN** NO new tab is created (the tab count is unchanged), a new window titled `solo` is added to the current tab, and `--layout`/`--tab-title`/`--tab-accent` are not applied

#### Scenario: Panes inherit the launch directory

- **WHEN** the user runs `my-kitty scene launch <scene>` from directory `/some/dir` and the scene's panes do not set their own `cwd`
- **THEN** each spawned window reports `cwd == /some/dir` (the tab and its windows open where the scene was launched), and a pane that sets an explicit `cwd` keeps that value

#### Scenario: Zero panes is rejected with non-zero exit

- **WHEN** the user invokes `my-kitty scene launch --tab-title="empty"` with no `--pane` flags and no scene name
- **THEN** the command exits non-zero, prints a stderr message stating that a scene name or at least one `--pane` is required, and does NOT create a new tab

#### Scenario: Unknown key in `--pane` is rejected before any kitten call

- **WHEN** the user invokes `my-kitty scene launch --pane 'tile=mistyped'` (note the typo: `tile` instead of `title`)
- **THEN** the command exits non-zero, prints a stderr message naming the unknown key `tile` and listing the recognised keys (`title`, `cmd`, `cwd`, `bg`), and does NOT call `kitten @ launch` even once

#### Scenario: Escaped comma inside a pane value is preserved verbatim

- **WHEN** the user invokes `my-kitty scene launch --pane 'title=docker ps -a\, --filter status=running,cmd=docker ps'`
- **THEN** the resulting window's title equals the string `docker ps -a, --filter status=running` (single literal comma) and `cmd` is executed unchanged

#### Scenario: First non-zero kitten exit code propagates

- **WHEN** the launcher's first `kitten @ launch` invocation succeeds but a subsequent `kitten @ set-colors` for a pane with an invalid `bg=<not-a-color>` fails
- **THEN** the set-colors stderr is printed to the launcher's stderr, the launcher CONTINUES with the remaining panes, and the launcher's overall exit code equals the first non-zero kitten exit code

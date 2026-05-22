# Delta: kitty-scenes

## ADDED Requirements

### Requirement: Scene launcher composition primitive ships under `my-kitty scene launch`

The `my-kitty` binary SHALL expose a `scene launch` subcommand that composes the existing scene primitives (title, accent, background, layout) into one user gesture. Invoking `my-kitty scene launch <args>` SHALL open a new tab on the running kitty, optionally apply a layout, spawn one or more panes inside the new tab (each optionally pre-styled with title, working directory, background color, and a startup command), and optionally tint the tab.

The CLI surface SHALL be:

```
my-kitty scene launch \
    [--layout=<name>[:<opts>]] \
    [--tab-title=<text>] [--tab-accent=<color>] \
    --pane 'key=value,key=value,...' \
    [--pane '...'] ... \
    [--to=unix:<socket>]
```

The `--pane` flag SHALL accept a comma-separated `key=value` group. Recognised keys SHALL be exactly `title`, `cmd`, `cwd`, and `bg`. Any unknown key SHALL cause the command to exit non-zero with a stderr message naming the offending key and listing the recognised set. Commas inside a value SHALL be escapable as `\,` and backslashes as `\\`. The `--pane` flag SHALL be repeatable; at least one `--pane` MUST be provided (zero panes is rejected with exit non-zero).

The launcher SHALL use the existing `scenes._client.kitten_at()` surface for every kitten call, inheriting `$KITTY_LISTEN_ON` → `pgrep -x kitty` socket discovery and the kitten binary resolution from h22's foundation. No new socket-discovery code SHALL be introduced.

The launcher SHALL execute the kitten calls in this exact order (probe-grounded — `tmp/h25-scene-launcher/expected.json`):

1. `kitten @ launch --type=tab --hold` with `--tab-title`, `--title`, `--cwd`, and the positional `bash -lc <cmd>` form for the FIRST pane, all combined in one call. The new tab is focused synchronously by kitty.
2. If the first pane carries a `bg`: `kitten @ set-colors --match id:<win0> background=<bg>` (where `<win0>` is the window id returned on stdout by step 1).
3. If `--layout` is set: `kitten @ goto-layout <layout>` (operates on the focused — new — tab; no `--match` required).
4. For each remaining pane in order: `kitten @ launch --type=window --hold` with that pane's flags; if `bg` is set, follow with `kitten @ set-colors --match id:<win> background=<bg>` using the window id returned by the launch.
5. If `--tab-accent` is set: `kitten @ set-tab-color --match recent:0 active=<tab_accent>`. (This is a single-key, focused-state-only call — intentionally different from the `tab accent` primitive in `accent.py`, which sets both `active_bg=` and `inactive_bg=` to satisfy the focused-AND-unfocused invariant for persistent tab styling. In the launcher, setting only the focused-tab color for the newly created tab is the minimal correct behavior; `inactive_bg` is deliberately omitted because the tab is focused at launch time and the user can always call `my-kitty tab accent` explicitly for full persistent styling.)

The launcher SHALL fail-hard on any `kitten @ launch` non-zero exit (propagate the kitten exit code and stop processing further panes). It SHALL fail-soft on `kitten @ set-colors` and `kitten @ set-tab-color` failures (print the kitten stderr to its own stderr, mark the overall exit code non-zero, but continue building the rest of the scene so the user is not left with a half-built tab on a styling error). The first non-zero kitten exit code SHALL be propagated as the launcher's exit code.

Every user-supplied `cmd=...` SHALL be wrapped as `bash -lc <cmd>` when passed to `kitten @ launch` so the user's shell features (`|`, `$VAR`, `;`, `&&`, etc.) work transparently without any quoting code in the launcher.

#### Scenario: Three-pane scene composes in one user gesture

- **WHEN** the user invokes `my-kitty scene launch --layout=tall:mirrored=true --tab-title="🐳 mon" --pane 'title=p1,cmd=echo p1' --pane 'title=p2,bg=#001f3f,cmd=echo p2' --pane 'title=p3'`
- **THEN** a new tab whose title is `🐳 mon` appears on the running kitty, the active layout is `tall` with `layout_opts.mirrored == "y"`, the new tab contains exactly 3 windows whose titles are `p1`, `p2`, `p3` in order, `p2`'s `background` reads as the hex `#001f3f` from `kitten @ get-colors --match id:<p2>`, and the `my-kitty scene launch` command exits 0

#### Scenario: Zero panes is rejected with non-zero exit

- **WHEN** the user invokes `my-kitty scene launch --tab-title="empty"` with no `--pane` flags
- **THEN** the command exits non-zero, prints a stderr message stating that at least one `--pane` is required, and does NOT create a new tab on the running kitty

#### Scenario: Unknown key in `--pane` is rejected before any kitten call

- **WHEN** the user invokes `my-kitty scene launch --pane 'tile=mistyped'` (note the typo: `tile` instead of `title`)
- **THEN** the command exits non-zero, prints a stderr message naming the unknown key `tile` and listing the recognised keys (`title`, `cmd`, `cwd`, `bg`), and does NOT call `kitten @ launch` even once (no half-built tab)

#### Scenario: Escaped comma inside a pane value is preserved verbatim

- **WHEN** the user invokes `my-kitty scene launch --pane 'title=docker ps -a\, --filter status=running,cmd=docker ps'`
- **THEN** the resulting window's title equals the string `docker ps -a, --filter status=running` (single literal comma) and `cmd` is executed unchanged

#### Scenario: `--no-response` is NOT used so per-pane styling can target by exact window id

- **WHEN** the launcher executes the kitten call sequence
- **THEN** every `kitten @ launch` invocation SHALL omit `--no-response` so the new window id is captured from stdout, and the subsequent `set-colors` call for that pane SHALL target via `--match id:<captured_id>` rather than `--match recent:0`

#### Scenario: First non-zero kitten exit code propagates

- **WHEN** the launcher's first `kitten @ launch` invocation succeeds but a subsequent `kitten @ set-colors` for a pane with an invalid `bg=<not-a-color>` fails
- **THEN** the set-colors stderr is printed to the launcher's stderr, the launcher CONTINUES with the remaining panes, and the launcher's overall exit code equals the first non-zero kitten exit code

### Requirement: Scene launcher lives at `src/kitty_setup/scenes/launcher.py`

The launcher module SHALL ship as `src/kitty_setup/scenes/launcher.py`, a sibling of `title.py`, `accent.py`, `background.py`, `font.py`, and `opacity.py`. It SHALL import only from `kitty_setup.scenes._client` (for `kitten_at` + `SceneClientError`) and standard library; no other module of the package and no external dependency.

The module SHALL export at minimum:

- A `Pane` dataclass (frozen) with fields `title: str | None`, `cmd: str | None`, `cwd: str | None`, `bg: str | None`, all defaulting to `None`.
- A pure function `parse_pane_spec(s: str) -> Pane` that parses the `--pane key=value` form and raises a clear exception on malformed input (no `=`, duplicate key, unknown key, trailing comma, empty input).
- A `launch_scene(layout, tab_title, tab_accent, panes, *, to=None) -> int` callable that takes a parsed scene and returns the first non-zero kitten exit code (or 0 if all calls succeed). It SHALL NOT have an argparse dependency — argparse plumbing lives in the `cli_scene_launch` handler.
- A `cli_scene_launch(args)` handler that argparse calls via `set_defaults(func=…)`. This handler SHALL parse each `--pane` string via `parse_pane_spec`, build the `Pane` list, and invoke `launch_scene`. It SHALL catch `SceneClientError` and parser errors, print a clear stderr message, and return exit code 1.

#### Scenario: Module imports only from `_client` and stdlib

- **WHEN** a reviewer inspects `src/kitty_setup/scenes/launcher.py` imports
- **THEN** every non-stdlib import is from `kitty_setup.scenes._client`; there is no import of `accent`, `background`, `font`, `opacity`, or `title` (the launcher composes via raw `_client.kitten_at()` calls, not by reusing the per-primitive Python wrappers)

#### Scenario: `parse_pane_spec` is a pure function exercisable in unit tests

- **WHEN** a unit test calls `parse_pane_spec("title=docker ps,cmd=docker ps,bg=#001f3f")` with no kitty running
- **THEN** the call returns `Pane(title="docker ps", cmd="docker ps", cwd=None, bg="#001f3f")` without making any subprocess call

### Requirement: Hypothesis-driven shipping under `tmp/h25-scene-launcher/`

A hypothesis probe SHALL exist at `tmp/h25-scene-launcher/run.py` with companion `expected.json` and `repro.md` files, exercising the 5 wire-level questions that govern the launcher's call algorithm (probe Q1: launch combine; Q2: cmd shape; Q3: id capture + `--no-response`; Q4: tab focus race; Q5: 3-pane scene). The probe SHALL be autonomous (raw `subprocess` against a self-spawned kitty pinned via `/tmp/kitty-<pid>`), MUST exit 0 with output `[h25] green: actual == expected` when re-run on the user's host, and SHALL be deleted before the change is archived.

The integration test `tests/integration/test_h25_scene_launcher.py` SHALL promote the probe's assertions, one named test per question, all gated on `KITTI_INTEGRATION=1`. The test names SHALL match the mapping in `design.md` D5. The integration test layer SHALL import the shared `_kitty_subprocess.py` helpers established by h22+h23+h24 (no new spawn/socket primitives are introduced).

#### Scenario: Probe is green at apply time, deleted at archive time

- **WHEN** `/opsx:apply phase2-scene-launcher` begins on the user's host
- **THEN** `uv run python tmp/h25-scene-launcher/run.py` exits 0 with `[h25] green: actual == expected`

- **WHEN** the change is moved to `openspec/changes/archive/`
- **THEN** the directory `tmp/h25-scene-launcher/` does not exist

#### Scenario: Each probe question is reflected in one integration test

- **WHEN** a reviewer reads `tests/integration/test_h25_scene_launcher.py`
- **THEN** the file contains exactly the five named tests from `design.md` D5 plus one end-to-end test invoking `my-kitty scene launch` via subprocess; every probe key referenced in D5's mapping table is covered by at least one assertion in the corresponding test

### Requirement: Manual repro doc records Linux + macOS status

The change SHALL ship `docs/repro/h25-scene-launcher.md` with the standard sections: `## Why`, `## Manual repro`, `## Linux Status`, `## macOS Status`, `## Attempted alternatives`, `## Known limitations`, `## Recipes`. The Linux Status row MUST read `verified (<date>, <host details>)` before this change is archived; the macOS Status row MUST read `verified` or `deferred-with-reason` with at minimum a one-paragraph reason (no Mac host available; `kitten @ launch` is platform-agnostic; tab-strip / per-pane background visual fidelity is the only macOS-specific concern).

#### Scenario: Manual repro doc is verified before archive

- **WHEN** the change is moved to `openspec/changes/archive/`
- **THEN** `docs/repro/h25-scene-launcher.md` exists, its `## Linux Status` row reads `verified` with a date and host details, and its `## macOS Status` row reads `verified` or `deferred-with-reason` with a one-paragraph reason

## 1. Module `src/kitty_setup/scenes/recipe.py`

- [x] 1.1 Create `src/kitty_setup/scenes/recipe.py`. Top-of-file docstring SHALL cite Phase 2 §12 / roadmap bullet 7 (declarative half), note that it is the front-end onto the unchanged `launch_scene()` engine, and state that it imports `Pane` from `launcher.py` (does NOT redefine the dataclass or its field names — design D2). Imports limited to stdlib (`os`, `pathlib`, `tomllib`) plus `from kitty_setup.scenes.launcher import Pane, launch_scene`.
- [x] 1.2 Define a typed error (e.g. `class SceneRecipeError(Exception)`) for all loader-side failures (bad name, missing file, parse error, schema violation). One clear message per raise.
- [x] 1.3 Implement `scenes_dir() -> Path` resolving `$XDG_CONFIG_HOME` (fallback `~/.config`) → `…/kitty-setup/scenes/`. Must NOT be the managed payload path `~/.config/kitty/kitty-setup/` (design — user data, installer never writes here).
- [x] 1.4 Implement the path-traversal guard (design D4): reject a `name` that is empty, contains `/`, `os.sep`, `os.altsep`, or a `..` segment — raise `SceneRecipeError` before any IO. After resolving `<dir>/<name>.toml`, assert the resolved parent equals `scenes_dir()`.
- [x] 1.5 Implement `load_scene(name) -> tuple[str|None, str|None, str|None, list[Pane]]`: guard name (1.4), resolve file (missing file → `SceneRecipeError` whose message lists available scenes via `list_scenes`), `tomllib.load`, validate schema (1.6), build `list[Pane]`. Return `(layout, tab_title, tab_accent, panes)` — the exact `launch_scene` argument shape.
- [x] 1.6 Schema validation mirrors `parse_pane_spec` strictness: recognised top-level keys exactly `{layout, tab_title, tab_accent}`; recognised `[[pane]]` keys exactly the `Pane` field names `{title, cmd, cwd, bg}`. Unknown top-level/pane key → `SceneRecipeError` naming the key + recognised set. Wrong TOML type (e.g. `layout = 123`, `pane` not an array of tables) → `SceneRecipeError` naming the key + expected type. Empty-string value → `None` (absent), matching the inline parser. No `[[pane]]` → `SceneRecipeError` ("at least one pane"). All validation BEFORE returning (so no half-built tab downstream).
- [x] 1.7 Implement `list_scenes()` returning sorted per-scene summaries (name, `tab_title` or None, pane count) for valid `*.toml`; a malformed file is included with a malformed marker + parse error (not silently dropped). Missing/empty dir → empty list.
- [x] 1.8 Implement `cli_scene_list(args)` (argparse `set_defaults(func=…)` handler): default prints one rich line per scene (name + tab title + pane count); malformed lines show the parse error; empty/missing dir prints a friendly empty-state and exits 0. Honor `--names`/`-q` → bare sorted names only.

## 2. Name branch in `src/kitty_setup/scenes/launcher.py`

- [x] 2.1 Extend `cli_scene_launch(args)` with the mode dispatch (design D1): `name` + `--pane` → stderr "contradictory" + return 1; neither → stderr "need a scene name or at least one --pane" + return 1; `name` + any of `--layout`/`--tab-title`/`--tab-accent` → stderr "not accepted with a named scene" (file authoritative) + return 1.
- [x] 2.2 On `name` set (and no conflicts): call `recipe.load_scene(name)`, then `launch_scene(layout, tab_title, tab_accent, panes, to=args.to)`; return its exit code. Catch `recipe.SceneRecipeError` and `SceneClientError` → clear stderr + return 1.
- [x] 2.3 Leave the inline `--pane` path byte-for-byte unchanged (no `name`, `--pane` present → existing behavior). Import `recipe` lazily or at module top without creating an import cycle (recipe imports from launcher; launcher references `recipe` — import `recipe` inside the handler or via the package to avoid a circular import at module load).

## 3. CLI wiring in `src/kitty_setup/cli.py` and package export

- [x] 3.1 Add the optional positional `name` (`nargs='?'`, default `None`) to the existing `scene launch` subparser. Update its help/epilog to document both modes (`scene launch <name>` vs `scene launch --pane …`) and that style flags are rejected with a named scene.
- [x] 3.2 Add a sibling `scene list` sub-subcommand (NOT under `launch`) with `--names`/`-q` (`action='store_true'`), `set_defaults(func=scenes.recipe.cli_scene_list)`.
- [x] 3.3 Add `recipe` to the `from kitty_setup.scenes import …` export line in `src/kitty_setup/scenes/__init__.py` so `scenes.recipe.*` is reachable from `cli.py` and monkeypatchable in tests (consistent with `launcher`, `accent`, etc.).
- [x] 3.4 Run `my-kitty scene launch --help` and `my-kitty scene list --help`; confirm the help text lists the positional `name`, the inline flags, and `--names`.

## 4. Unit tests `tests/unit/test_scenes_recipe.py`

- [x] 4.1 Create `tests/unit/test_scenes_recipe.py`. Point `scenes_dir()` at a `tmp_path` fixture (monkeypatch `$XDG_CONFIG_HOME` or `recipe.scenes_dir`).
- [x] 4.2 `load_scene` happy path: full-schema `demo.toml` (layout + tab_title + tab_accent + 3 `[[pane]]`) → exact `(layout, tab_title, tab_accent, [Pane,…])` tuple. Assert the returned panes are `launcher.Pane` instances (reuse, not a copy).
- [x] 4.3 Empty-string normalisation: `title = ""` → `Pane.title is None` (NOT `""`).
- [x] 4.4 Schema errors (each `pytest.raises(SceneRecipeError)` asserting the message names the offender): unknown top-level key, unknown pane key, wrong type (`layout = 123`), no `[[pane]]`.
- [x] 4.5 Path-traversal: `../x`, `a/b`, `..`, `""` → `SceneRecipeError` and assert no file outside the dir is read (e.g. the resolved path never escapes `tmp_path`).
- [x] 4.6 Unknown name → `SceneRecipeError` whose message lists the available scene names.
- [x] 4.7 `scenes_dir()` honors `$XDG_CONFIG_HOME` over `~/.config`.
- [x] 4.8 `list_scenes()` / `cli_scene_list`: rich output for 2 valid scenes (sorted, name + tab_title + pane count); malformed file surfaced with its error; empty/missing dir → friendly empty-state, exit 0; `--names` → bare sorted names only (use `capsys`).
- [x] 4.9 `cli_scene_launch` mode conflicts (use `capsys`): name+`--pane` → exit 1 + "contradictory"; neither → exit 1 + "at least one --pane"; name+`--tab-accent` → exit 1 + "named scene". Monkeypatch `launcher.launch_scene`/`recipe.load_scene` so no kitty is needed.
- [x] 4.10 Run `pytest tests/unit/test_scenes_recipe.py` green, then full `pytest tests/unit/` green (zero regressions on the existing launcher tests).

## 5. Integration test `tests/integration/test_scene_recipe_e2e.py`

- [x] 5.1 Create `tests/integration/test_scene_recipe_e2e.py`, gated on `KITTI_INTEGRATION=1` via the existing `tests/conftest.py` mechanism; import helpers from `tests/integration/_kitty_subprocess.py`.
- [x] 5.2 Implement `test_my_kitty_scene_launch_named_recipe_creates_three_pane_tab`: write a temp `<scenes_dir>/<name>.toml` (layout `tall:mirrored=true`, tab_title, 3 panes incl. one `bg=#001f3f`), spawn kitty, run `my-kitty scene launch <name>` via `subprocess.run` with `KITTY_LISTEN_ON=unix:/tmp/kitty-<pid>` and `XDG_CONFIG_HOME` pointed at the temp config root (so the loader finds the recipe). Assert exit 0; new tab with the expected title; 3 windows titled `p1`/`p2`/`p3` in order; `layout_opts.mirrored == "y"`; `p2` background reads `#001f3f` — same observables as the h25 e2e test.
- [x] 5.3 Run `KITTI_INTEGRATION=1 pytest tests/integration/test_scene_recipe_e2e.py -v` on the user's host — green.

## 6. Repro doc

- [x] 6.1 Create `docs/repro/scene-recipe-toml.md` with the standard sections (Why, Manual repro, Linux Status, macOS Status, Attempted alternatives, Known limitations, Recipes). Manual repro authors a `<scenes_dir>/<name>.toml` and runs `my-kitty scene launch <name>` + `my-kitty scene list`. macOS = deferred-with-reason. Note: no new `tmp/hNN` probe (wire algorithm unchanged from h25); verification is unit tests + one e2e integration test.

## 7. Verification

- [x] 7.1 `make doctor` clean (no new doctor check expected; confirm no regression).
- [x] 7.2 Full `make test` (or `pytest`) green; `KITTI_INTEGRATION=1 pytest tests/integration/test_scene_recipe_e2e.py` green on host. Capture output for the PR/handoff.
- [x] 7.3 Confirm `src/kitty_setup/installer.py` does not reference the scenes dir (user data is never written/removed by install/uninstall).
- [x] 7.4 `openspec validate phase2-scene-recipe-toml` passes.

## 8. Round 2 — UX refinements (single-pane / cwd / table list / autocomplete)

- [x] 8.1 Engine: single-pane scene launches `--type=window` into the current tab (no new tab; skip layout/tab_title/tab_accent). Multi-pane unchanged. Factor `_apply_bg` helper.
- [x] 8.2 Engine: add `default_cwd` param to `launch_scene`; `_launch_argv` applies it to any pane without its own `cwd`. Wire `default_cwd=os.getcwd()` in both `cli_scene_launch` branches.
- [x] 8.3 `scene list`: column-aligned table with `NAME`/`TAB`/`PANES` header; display-width via stdlib `unicodedata` (no `rich` dep). Add `_display_width`/`_pad`.
- [x] 8.4 Autocomplete: `recipe.scene_name_completer` (glob stems, prefix filter, no parse); attach to the `scene launch` positional `name` via `.completer`.
- [x] 8.5 Samples: rename `docker-mon`→`docker`; add a bare single-pane `edit.toml`; keep them in `examples/scenes/` (tracked) and the live config.
- [x] 8.6 Unit tests: single-pane argv / cwd default / cwd override (launcher); table header + `_pad` display-width + completer (recipe). Update the accent test to a multi-pane scene.
- [x] 8.7 Integration: `test_single_pane_scene_joins_current_tab` + `test_scene_panes_inherit_launch_directory`, both green on host.
- [x] 8.8 Spec: MODIFY the launcher composition Requirement (single-pane + cwd); ADD the table-output, autocomplete scenarios. `openspec validate` passes.
- [x] 8.9 Repro doc + proposal updated for the round-2 behaviors.

## 9. Round 3 — multi-pane fills the CURRENT tab when launched inside kitty

- [x] 9.1 Probe (live kitty): reuse `$KITTY_WINDOW_ID` as pane 0 (`set-window-title`/`set-colors`), launch the rest as `--type=window` splits, apply `goto-layout`/`set-tab-title`/`set-tab-color` to the focused tab (no `--match`). Verified 1 tab → 1 tab, 3 windows, styled.
- [x] 9.2 Engine: add `origin_window` param to `launch_scene`; `_origin_window()` reads `$KITTY_WINDOW_ID`; `_fill_current_tab()` path for multi-pane + origin. Single-pane and the no-origin (socket-driven) multi-pane paths unchanged. Wire `origin_window=_origin_window()` in both `cli_scene_launch` branches.
- [x] 9.3 Unit tests: `test_multipane_with_origin_window_fills_current_tab` (argv order, no `--type=tab`, no `recent:0`); `test_origin_window_ignored_for_single_pane`. Recipe `_fake_launch_scene` accepts `origin_window`.
- [x] 9.4 Integration: `test_multipane_scene_fills_current_tab_when_launched_inside_kitty` (sets `KITTY_WINDOW_ID`, asserts tab count unchanged + 3 ordered panes + tab title/layout). Green on host (4/4 e2e).
- [x] 9.5 Spec: MODIFY the composition Requirement (in-kitty multi-pane fills current tab; clarify the no-origin new-tab path); ADD the fill-current-tab scenario. `openspec validate` passes.
- [x] 9.6 Samples + repro: `docker.toml` panes `shell` (left) / `docker-ps` / `docker-memory` (stacked right, plain `tall`); `dev.toml` git pane degrades cleanly outside a repo; `edit.toml` uses `${EDITOR:-vim}`; repro "Known limitations" updated. Live `~/.config` copies synced. `my-kitty` reinstalled.

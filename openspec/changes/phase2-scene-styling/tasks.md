## 1. Hypothesis probe (already green; preserve it green through apply)

- [ ] 1.1 Re-run `uv run python tmp/h23-styling/run.py` on the user's host — expect `[h23] green: actual == expected`. If RED, investigate before any other task.
- [ ] 1.2 Confirm `tmp/h23-styling/expected.json` is present and committed (it is, per the explore session).

## 2. Install-time payload — `config/kitty/dynamic-opacity.conf`

- [ ] 2.1 Create `config/kitty/dynamic-opacity.conf` containing the single directive `dynamic_background_opacity yes`, prefixed by a comment block citing this change (`phase2-scene-styling`), the `kitty-scenes` capability, and the kitten error message that fires without it. The comment block MUST state that the visual impact is zero on hosts that do not invoke `my-kitty os-window opacity` (kitty default opacity stays 1.0).
- [ ] 2.2 In `config/kitty/kitty-setup.conf`, add the line `include dynamic-opacity.conf` after the existing `include remote-control.conf` line.
- [ ] 2.3 Verify the directive parses: run `~/.local/kitty.app/bin/kitty --debug-config --config /tmp/h23-parse-check.conf` against a draft kitty.conf that contains a single `include /home/user-zero/git/cco/kitty-setup/config/kitty/kitty-setup.conf` line (write the file inline before invoking). Expect exit code 0. (This mirrors the probe's `_draft_conf` pattern in `tmp/h23-styling/run.py` lines 37–43.)

## 3. New scenes modules

- [ ] 3.0 **Shared rule for every new `cli_*` wrapper in tasks 3.1–3.4**: each `cli_*` function MUST catch `_client.SceneClientError`, write the exception message + newline to `sys.stderr`, and return exit code 1. This mirrors the established shape in `src/kitty_setup/scenes/title.py` (see `cli_set_window_title` lines 65–75). Domain functions (`set_tab_accent`, `set_window_background`, `set_os_window_font_size`, `set_os_window_opacity`) MUST NOT catch the exception — they let it propagate so unit tests can assert on it directly. The non-zero kitten exit-code path (which is a normal `CompletedProcess` return, not an exception) is handled by writing kitten's stderr to `sys.stderr` and returning kitten's exit code — also mirroring `title.py`.
- [ ] 3.1 Create `src/kitty_setup/scenes/accent.py` with `set_tab_accent(color: str, *, active_fg: str | None = None, inactive_fg: str | None = None, match: str | None = None, to: str | None = None) -> int` and `cli_set_tab_accent(args)`. Build kitten argv: `active_bg=<color>`, `inactive_bg=<color>`, optionally `active_fg=<...>` / `inactive_fg=<...>`, optionally `--match`. Propagate kitten's stderr verbatim on non-zero.
- [ ] 3.2 Create `src/kitty_setup/scenes/background.py` with `set_window_background(color: str, *, match: str | None = None, to: str | None = None) -> int` and `cli_set_window_background(args)`. Build kitten argv: `background=<color>`, optionally `--match`.
- [ ] 3.3 Create `src/kitty_setup/scenes/font.py` with `set_os_window_font_size(value: str, *, all_: bool = False, to: str | None = None) -> int` and `cli_set_os_window_font_size(args)`. Value is `type=str` (kitten accepts `14`, `+2`, `-2`, `*1.1`, `/2`, `0`). Add `--all` if requested.
- [ ] 3.4 Create `src/kitty_setup/scenes/opacity.py` with `set_os_window_opacity(value: float, *, toggle: bool = False, all_: bool = False, to: str | None = None) -> int` and `cli_set_os_window_opacity(args)`. **Implementation rule (D3, probe-grounded):** the kitten argv MUST be `[..., "--toggle", "<value>"]` — flag BEFORE positional. Reverse order fails with `"Must specify exactly 1 argument(s)"`.
- [ ] 3.5 Update `src/kitty_setup/scenes/__init__.py` to add `from kitty_setup.scenes import accent, background, font, opacity  # noqa: F401` re-exports alongside the existing `title` re-export.
- [ ] 3.6 All four modules invoke kitten exclusively through `_client.kitten_at(...)`. Grep `subprocess.run` under `src/kitty_setup/scenes/` — matches MUST be in `_client.py` only.

## 4. Wire `cli.py` — `tab accent`, `window background`, `os-window` noun + verbs

- [ ] 4.1 Add `os-window` to the top-level subparser group (alongside `install`, `uninstall`, `doctor`, `prune`, `keys`, `window`, `tab`, `help`). The argparse subparser name MAY use `os-window` (with hyphen — argparse accepts) or use the `os_window` Python-attribute mapping internally if needed.
- [ ] 4.2 Under the existing `tab` subparser, add `accent` sub-subparser with positional `<color>` (type=str), `--active-fg`, `--inactive-fg` (both type=str), `--match` (type=str, metavar=EXPR), `--to` (type=str, metavar=SOCKET). `set_defaults(func=scenes.accent.cli_set_tab_accent)`.
- [ ] 4.3 Under the existing `window` subparser, add `background` sub-subparser with positional `<color>`, `--match`, `--to`. `set_defaults(func=scenes.background.cli_set_window_background)`.
- [ ] 4.4 Under the new `os-window` subparser, add `font-size` sub-subparser with positional `<value>` (type=str — kitten's signed-prefix grammar; leading `-` like `-2` works as positional because there's no flag ambiguity at this position), `--all` (action="store_true"), `--to`. `set_defaults(func=scenes.font.cli_set_os_window_font_size)`.
- [ ] 4.5 Under `os-window` subparser, add `opacity` sub-subparser with positional `<value>` (type=float), `--toggle` (action="store_true"), `--all` (action="store_true"), `--to`. `set_defaults(func=scenes.opacity.cli_set_os_window_opacity)`.
- [ ] 4.6 Verify `my-kitty --help` lists `os-window` alongside the existing subcommands.
- [ ] 4.7 Verify `my-kitty tab accent --help`, `my-kitty window background --help`, `my-kitty os-window font-size --help`, `my-kitty os-window opacity --help` all render their flags correctly.

## 5. Unit tests — scenes modules + CLI dispatch

- [ ] 5.1 Create `tests/unit/test_scenes_accent.py`: assert `set_tab_accent("#0066cc")` calls `kitten_at("set-tab-color", "active_bg=#0066cc", "inactive_bg=#0066cc")` (and no `--match`); assert `set_tab_accent("blue", active_fg="white")` includes `active_fg=white`; assert `set_tab_accent("notacolor")` propagates kitten's non-zero exit by monkeypatching `kitten_at` to return `CompletedProcess(returncode=1, stderr="...")`. Each test stub carries the docstring `"Provisional per R7; grounded by tmp/h23-styling/run.py"`.
- [ ] 5.2 Create `tests/unit/test_scenes_background.py`: assert `set_window_background("#001a33")` calls `kitten_at("set-colors", "background=#001a33")`; assert `set_window_background("red", match="id:5")` includes `"--match", "id:5"`; propagation test for non-zero.
- [ ] 5.3 Create `tests/unit/test_scenes_font.py`: parametrized over `("14", "+2", "-2", "*1.1", "/2", "0")` — assert `set_os_window_font_size(v)` calls `kitten_at("set-font-size", v)`; assert `--all` flag adds `"--all"` to argv.
- [ ] 5.4 Create `tests/unit/test_scenes_opacity.py`: **the load-bearing test is the argv ordering invariant** — assert `set_os_window_opacity(0.7, toggle=True)` calls `kitten_at("set-background-opacity", "--toggle", "0.7")` with `--toggle` STRICTLY BEFORE `"0.7"`; assert `set_os_window_opacity(0.7)` (no toggle) calls `kitten_at("set-background-opacity", "0.7")`. Reading captured argv element-by-element and asserting index ordering catches future refactors that flip the order.
- [ ] 5.4.1 In `tests/unit/test_scenes_opacity.py` (representative for all four new modules), add `test_cli_handler_translates_scene_client_error`: monkeypatch `_client.kitten_at` to raise `_client.SceneClientError("no kitty process found")`, build an `argparse.Namespace` matching the `os-window opacity` parser, call `cli_set_os_window_opacity(ns)`, assert it returns 1 and `capsys.readouterr().err` contains the substring `"no kitty process found"`. (Mirrors the pattern in `tests/unit/test_scenes_title.py::test_cli_handler_translates_scene_client_error`.) The other three `cli_*` wrappers MAY rely on this single representative test since §3.0 establishes one shared rule for all four — but if any wrapper diverges from the shared shape (e.g. a custom error message), that wrapper SHALL get its own dedicated test.
- [ ] 5.5 Extend `tests/unit/test_cli.py` `test_top_level_help_lists_all_subcommands` (and the `help` variant) to assert `os-window` appears alongside the existing subcommands.
- [ ] 5.6 Add `test_tab_accent_routes_to_handler` to `tests/unit/test_cli.py`: monkeypatch `cli.scenes.accent.cli_set_tab_accent`; assert `my-kitty tab accent "#0066cc"` invokes it with `args.color == "#0066cc"`.
- [ ] 5.7 Add `test_window_background_routes_to_handler` to `tests/unit/test_cli.py`.
- [ ] 5.8 Add `test_os_window_font_size_routes_to_handler` to `tests/unit/test_cli.py`. The test SHALL exercise `["os-window", "font-size", "-2"]` to confirm argparse accepts the leading-`-` positional.
- [ ] 5.9 Add `test_os_window_opacity_routes_to_handler` to `tests/unit/test_cli.py`: assert `["os-window", "opacity", "0.7", "--toggle"]` routes with `args.value == 0.7` and `args.toggle is True`.
- [ ] 5.10 Run `pytest tests/unit/` — all green.

## 6. Integration tests — promote h23 probe

- [ ] 6.1 Extract subprocess helpers from `test_h22_window_title.py` into a new shared module `tests/integration/_kitty_subprocess.py` (this is required, not conditional — the helpers `_draft_conf` / `_spawn_kitty` / `_wait_for_socket` / `_stub_config` / `_pin_pgrep_to_pid` already span ~80 substantive lines in h22, and h23 needs the same set). Update `test_h22_window_title.py` to import from the new module. Note: `tests/integration/_helpers.py` exists with unrelated clear-variant helpers — do NOT merge subprocess helpers into it; the new file is `_kitty_subprocess.py`.
- [ ] 6.1.1 Create `tests/integration/test_h23_styling.py` (gated on `KITTI_INTEGRATION=1`), importing from `_kitty_subprocess.py`. The test SHALL replicate the 23 assertions from `tmp/h23-styling/run.py` and `expected.json`. design.md D7's mapping table groups 18 of the 23 keys into 8 named test functions; **the remaining 5 keys SHALL land as follows** (this enumeration is normative — supersedes D7's table for these keys):

  | expected.json key | Test function |
  |---|---|
  | `tab_color_invalid_stderr_excerpt` | `test_set_tab_color_rejects_invalid_color` (assert substring "is not a valid color" in stderr) |
  | `launch_second_pane_ok` | `test_set_colors_isolates_to_matched_pane` (setup precondition for per-pane assertion) |
  | `pane_count_after_launch` | `test_set_colors_isolates_to_matched_pane` (setup precondition — exactly 2 panes before set-colors call) |
  | `opacity_toggle_stderr_excerpt` | `test_set_opacity_toggle_resets_to_default` (assert stderr empty on success) |
  | `opacity_ls_precision_note` | comment in `test_set_opacity_reflected_in_ls_with_tolerance` explaining the tolerance choice (no assertion needed — the tolerance comparison IS the test) |

  All 23 keys must be covered. After implementing, grep `expected.json` keys against `test_h23_styling.py` to confirm complete coverage before §6.5.
- [ ] 6.2 The opacity-precondition test (`test_opacity_without_directive_errors_clearly`) MUST spawn kitty with a config that does NOT include `dynamic-opacity.conf`. The other opacity tests spawn with the full config (including dynamic-opacity.conf).
- [ ] 6.3 The opacity-tolerance test (`test_set_opacity_reflected_in_ls_with_tolerance`) MUST use `abs(actual - expected) < 0.01`, not `==`, per design.md D4.
- [ ] 6.4 The opacity-toggle-argv test (`test_set_opacity_toggle_constructs_argv_flag_first`) belongs in the UNIT suite (§5.4), not here — at the integration level, success simply means the toggle works end-to-end.
- [ ] 6.5 Run `KITTI_INTEGRATION=1 pytest tests/integration/test_h23_styling.py` on the user's host — all green.

## 7. Repro doc

- [ ] 7.1 Create `docs/repro/h23-styling.md` with the standard sections: `## Why`, `## Manual repro`, `## Linux Status`, `## macOS Status`, `## Attempted alternatives`, `## Known limitations`, `## Recipes`.
- [ ] 7.2 `## Manual repro` SHALL document the user-runnable scenarios for each primitive: set tab accent and observe color on focused/unfocused tabs, set per-pane background, set OS-window font-size and observe all panes re-render, set opacity and observe transparency on the OS window.
- [ ] 7.3 `## Linux Status` outcome `verified` after user sign-off (dated, on Pop!_OS 24.04 + COSMIC + kitty 0.46.2). Block archive until verified.
- [ ] 7.4 `## macOS Status` outcome `deferred-with-reason` (no Mac host; kitten @ protocol is platform-agnostic; tab-bar/opacity visual fidelity may differ). Track under follow-up `phase2-scene-styling-macos`.
- [ ] 7.5 `## Attempted alternatives` table: hide os-window scope under `window` (rejected — lies about what the command does), `--os-window` flag instead of new noun (rejected — inverts kitty's actual model), drop opacity entirely (rejected — half-addresses §10).
- [ ] 7.6 `## Known limitations` SHALL include: per-pane font-size is kitty-architecturally impossible; per-pane opacity is kitty-architecturally impossible; `kitten @ ls` does NOT expose font-size (visual outcome is the only observable); `set-tab-color` reverts on kitty restart (will be solved by §13 named scenes).
- [ ] 7.7 `## Recipes` SHALL include curated examples (analogous to h22's): tab accent with role-based colors (`my-kitty tab accent red` for prod, etc.), opacity toggle bound to a shell alias, font-size `+2` / `-2` for zoom.

## 8. Verification + archive prep

- [ ] 8.1 Run `make doctor` on the user's host — all checks pass (no new doctor check expected from this change; the existing `parse check` validates the new directive parses).
- [ ] 8.2 Run `make install` to rebuild the deployable binary so the new CLI surface lands on disk.
- [ ] 8.3 Run `make test` and `KITTI_INTEGRATION=1 pytest tests/` — both green.
- [ ] 8.4 Manually verify on the user's daily host: open a kitty, run each scenario from §7.2 by hand; observe tab accent visible on focused AND unfocused tabs, per-pane background isolation, font-size global to OS-window, opacity visible at 0.7 → toggle back to 1.0.
- [ ] 8.5 Confirm `dynamic-opacity.conf` ships: `cat ~/.config/kitty/kitty-setup/dynamic-opacity.conf` shows the directive; `grep -c 'include dynamic-opacity.conf' ~/.config/kitty/kitty-setup/kitty-setup.conf` returns 1.
- [ ] 8.6 Confirm shell autocomplete works for `os-window` (per §9.6 of the h22 tasks pattern — `_ARGCOMPLETE=1 ... my-kitty` returns `os-window` among candidates).
- [ ] 8.7 Delete `tmp/h23-styling/` (probe served its purpose; spec mandates deletion before archive).
- [ ] 8.8 Run `openspec validate phase2-scene-styling --strict` — passes.
- [ ] 8.9 Author `verification.md` capturing `make doctor` + `make test` outputs verbatim plus the manual-verification outcomes.

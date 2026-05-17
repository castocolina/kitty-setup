## 1. Hypothesis probe (autonomous green before promotion)

- [x] 1.1 Create `tmp/h22-window-title/` directory with `run.py`, `expected.json`, `repro.md` skeletons per docs/agent-iteration.md R1 + step 4
- [x] 1.2 Implement `tmp/h22-window-title/run.py`: spawn kitty subprocess (raw, not KittySession harness); drive `kitten @ set-window-title` with and without `--temporary`; drive `kitten @ set-tab-title`; emit OSC-2 escape from inside; capture `kitten @ ls` output before/after each step
- [x] 1.3 Verify byte-identical UTF-8 round-trip for `🐳 docker test` (window) and `🐋 monitoring` (tab) in the captured output
- [x] 1.4 Populate `expected.json` with the captured observable states; ensure `python tmp/h22-window-title/run.py` exits 0 with `actual.json == expected.json` on the user's host
- [x] 1.5 Populate `tmp/h22-window-title/repro.md` with the manual repro protocol for the user

## 2. Refactor: lift socket-discovery helpers out of doctor.py

- [x] 2.1 Create `src/kitty_setup/scenes/` package (empty `__init__.py` with one-line module docstring referencing Phase 2 §8-§14 in `docs/requirements.md`). The `title` re-export is deferred to §4.5 (once `title.py` exists).
- [x] 2.2 Create `src/kitty_setup/scenes/_client.py`; move `_pgrep_kitty_pids` and `_parse_listen_on_base` from `doctor.py` verbatim (function bodies unchanged)
- [x] 2.3 In `doctor.py`, replace the in-file definitions with `from kitty_setup.scenes._client import _pgrep_kitty_pids, _parse_listen_on_base` (keep the names private; this is internal re-import, not a public API change)
- [x] 2.4 Run `pytest tests/unit/test_doctor_remote_control.py` — every test must pass with no assertion changes (import paths in the test file MAY be updated to point at the new home if needed)
- [x] 2.5 Run `pytest tests/integration/test_h21_doctor_remote_control.py` (gated on `KITTI_INTEGRATION=1`) on the user's host — must still pass

## 3. Implement `_client.py` — the `kitten @` wrapper

- [x] 3.0 Define `SceneClientError(RuntimeError)` at the top of `_client.py` — a single-purpose exception raised by `_resolve_kitten_binary()` and `_resolve_socket()` on unrecoverable discovery failures. No other exception class is needed; callers catch `SceneClientError` and exit non-zero.
- [x] 3.1 Implement `_resolve_kitten_binary()` in `_client.py`: try `installer.DEFAULT_DEST / "kitty.app" / "bin" / "kitten"` first, fall back to `shutil.which("kitten")`, raise `SceneClientError` with a specific message if neither yields a file. Match the pattern at `doctor.py` lines 197–202.
- [x] 3.2 Implement `_resolve_socket(to: str | None) -> str` in `_client.py` following the spec's 3-step data flow: (1) if `to` is set, return it; (2) if `$KITTY_LISTEN_ON` is set, return it; (3) derive `rc_conf` internally via `config_updater.ConfigPaths.for_user().payload_dir / "remote-control.conf"` (mirroring how `doctor.py:_check_remote_control_per_probe_04` obtains it), then call `_parse_listen_on_base(rc_conf)` + `_pgrep_kitty_pids()` and apply the 4 discovery rules from kitty-scenes/spec.md (config-absent → error, zero PIDs → error, one PID → success, multi-PID → error). `_resolve_socket` takes no `rc_conf` parameter; the path is always derived internally. Steps 1 and 2 MUST NOT invoke `_pgrep_kitty_pids` or read the config file. `_resolve_socket` ALWAYS returns a `unix:`-prefixed string (e.g. `unix:/tmp/kitty-4242`) on the success path — branches (1) and (2) pass the caller-supplied value unchanged, and branch (3) constructs `f"unix:{base}-{pid}"` from the bare `base` path returned by `_parse_listen_on_base` (which strips the `unix:` prefix per the `_LISTEN_ON_RE` capture group in `doctor.py` line 121).
- [x] 3.3 Implement `kitten_at(verb: str, *args: str, to: str | None = None) -> subprocess.CompletedProcess[str]` in `_client.py` (no `match` parameter — callers pass `"--match", expr` through `*args`): resolve binary + socket via `_resolve_kitten_binary()` and `_resolve_socket(to)`, construct argv as `[str(kitten_bin), "@", f"--to={socket_path}", verb, *args]`, call `subprocess.run(..., capture_output=True, text=True)`, return the CompletedProcess.

  **Concrete worked example** (verifying the form is correct): for `kitten_at("set-window-title", "--temporary", "deploy logs")` invoked from inside a kitty where `$KITTY_LISTEN_ON=unix:/tmp/kitty-4242`, `_resolve_socket(None)` returns the string `"unix:/tmp/kitty-4242"`. The constructed argv is:

  ```
  ["/home/<user>/.local/kitty.app/bin/kitten",
   "@",
   "--to=unix:/tmp/kitty-4242",       # ← single unix: prefix, comes from socket_path
   "set-window-title",
   "--temporary",
   "deploy logs"]
  ```

  Note that `socket_path` already carries the `unix:` prefix from `_resolve_socket`; the f-string is `f"--to={socket_path}"` (NOT `f"--to=unix:{socket_path}"`). Constructing the f-string the wrong way produces `--to=unix:unix:/tmp/kitty-4242`, which kitty rejects. This differs from `doctor.py:_kitten_ls_succeeds`, which uses `f"--to=unix:{socket}"` because *its* `socket` is the bare path without prefix — `_resolve_socket`'s return value is the full transport specifier, not a bare path, so the prefix is already included.
- [x] 3.4 Confirm `installer.DEFAULT_DEST` is imported via `from kitty_setup import installer` (not a circular import; `installer.py` does not import `scenes`)

## 4. Implement `scenes/title.py` — the primitive

- [x] 4.1 Implement `set_window_title(text: str, temporary: bool = True, match: str | None = None, to: str | None = None) -> int`: returns the kitten exit code. When `temporary=True`, pass `--temporary` to kitten; otherwise omit the flag. Pass `match` to `kitten_at` as `"--match", match` inside `*args` (not as a keyword); omit `--match` entirely when `match is None`. Propagate kitten stderr verbatim on non-zero exit.
- [x] 4.2 Implement `set_tab_title(text: str, match: str | None = None, to: str | None = None) -> int`: no `temporary` parameter (kitten doesn't accept one for tabs). Pass `match` to `kitten_at` as `"--match", match` inside `*args` (not as a keyword); omit `--match` entirely when `match is None`. Same propagation contract.
- [x] 4.3 Implement CLI handler wrappers `cli_set_window_title(args)` and `cli_set_tab_title(args)` that unpack argparse `Namespace` into the kwargs above and forward exit code
- [x] 4.4 No inline subprocess invocation of the `kitten` binary in `title.py` — every kitten call goes through `_client.kitten_at`
- [x] 4.5 Add `from kitty_setup.scenes import title  # noqa: F401  (exposes scenes.title as an attribute so cli.scenes.title resolves at monkeypatch time)` to `src/kitty_setup/scenes/__init__.py`. Without this re-export, `monkeypatch.setattr(cli.scenes.title, ...)` in tests 6.5–6.6 raises `AttributeError` before the patch lands.

## 5. Wire `cli.py` — add `window` and `tab` subparsers

- [x] 5.0 Add `from kitty_setup import scenes` to the import block in `cli.py` (alongside the existing `from kitty_setup import binding_introspection, doctor, installer, pruner`). This import form makes `scenes.title` reachable as a module attribute of `cli` (i.e. `cli.scenes.title`), which is required for the monkeypatch targets in §6.5 and §6.6 (`monkeypatch.setattr(cli.scenes.title, "cli_set_window_title", ...)`). Do NOT use `from kitty_setup.scenes import title` or `import kitty_setup.scenes.title` — those forms do not expose `scenes.title` as `cli.scenes.title`.
- [x] 5.1 In `_build_parser()` add `window` subparser; under it add `title` sub-subparser with positional `<text>`, `--temporary / --no-temporary` (BooleanOptionalAction, default=True), `--match` (type=str, metavar="EXPR", help="kitty match expression to select the target window"), `--to` (type=str, metavar="SOCKET", help="kitty listen-on socket address, e.g. unix:/tmp/kitty; overrides auto-discovery"); `set_defaults(func=scenes.title.cli_set_window_title)`
- [x] 5.2 In `_build_parser()` add `tab` subparser; under it add `title` sub-subparser with positional `<text>`, `--match` (type=str, metavar="EXPR", help="kitty match expression to select the target tab"), `--to` (type=str, metavar="SOCKET", help="kitty listen-on socket address, e.g. unix:/tmp/kitty; overrides auto-discovery") (no `--temporary`); `set_defaults(func=scenes.title.cli_set_tab_title)`
- [x] 5.3 Verify `my-kitty window title --help` and `my-kitty tab title --help` render correctly (positional + flags listed; tab help does NOT mention `--temporary`)
- [x] 5.4 Verify `my-kitty` (no args) help banner lists `window` and `tab` alongside the existing subcommands

## 6. Unit tests — `_client.py` socket discovery + `cli.py` dispatch

- [x] 6.1 Create `tests/unit/test_scenes_client.py` with **at least 7** tests covering the discovery branches: `$KITTY_LISTEN_ON`-present, `--to`-explicit, pgrep-single-PID success, **config-absent (file missing on disk)**, **config-present-no-directive (file exists but `_parse_listen_on_base` returns `None`)**, zero-PID error, multi-PID error. The two config-`None` sub-cases SHALL each have a dedicated test — they reach the same error message but through different stub setups (filesystem absence vs. parser returning `None` for a non-empty file). Use `monkeypatch` for `subprocess.run` and filesystem stubs consistent with `tests/unit/test_doctor_remote_control.py`. Because `_resolve_socket` derives `rc_conf` internally via `ConfigPaths.for_user()` (no parameter), tests that exercise the discovery path must monkeypatch `config_updater.ConfigPaths.for_user` to return a `ConfigPaths` whose `payload_dir` points at a `tmp_path` fixture directory, alongside the `_pgrep_kitty_pids` and `_parse_listen_on_base` stubs.
- [x] 6.2 Each stub function in `test_scenes_client.py` carries the one-line docstring `"Provisional per R7; grounded by tmp/h22-window-title/run.py"`
- [x] 6.3 Create `tests/unit/test_scenes_title.py` with at minimum 4 tests: (a) `test_set_window_title_passes_temporary_flag` — monkeypatch `_client.kitten_at`; assert it is called with `"set-window-title"`, `"--temporary"`, and the text arg when `temporary=True`; (b) `test_set_window_title_omits_temporary_flag` — same but `temporary=False`; assert `"--temporary"` is absent from the call args; (c) `test_set_tab_title_no_temporary` — monkeypatch `_client.kitten_at`; assert it is called with `"set-tab-title"` and no `"--temporary"` arg; (d) `test_title_functions_propagate_nonzero_exit` — one test body that monkeypatches `_client.kitten_at` to return a `CompletedProcess` with `returncode=1`, then calls `set_window_title("x")` and asserts it returns 1, then calls `set_tab_title("x")` and asserts it returns 1 (both calls in the same test with the same stub — no separate setup per function needed). Each stub carries the one-line docstring `"Provisional per R7; grounded by tmp/h22-window-title/run.py"`.
- [x] 6.4 Extend `tests/unit/test_cli.py` `test_top_level_help_lists_all_subcommands` (and the `help` subcommand variant) to assert that `keys`, `window`, and `tab` all appear in the help output, in addition to the existing `install`, `uninstall`, `doctor`, `prune`, `help`
- [x] 6.5 Add `test_window_title_routes_to_handler` to `tests/unit/test_cli.py`: monkeypatch `scenes.title.cli_set_window_title` with a recorder; assert `my-kitty window title "x"` invokes it with the right Namespace
- [x] 6.6 Add `test_tab_title_routes_to_handler` to `tests/unit/test_cli.py` with the same shape for `cli_set_tab_title`
- [x] 6.7 Run `pytest tests/unit/` — all green

## 7. Integration tests — live kitty subprocess

- [x] 7.1 Create `tests/integration/test_client_socket_discovery.py` (gated on `KITTI_INTEGRATION=1`): spawn a real kitty via raw subprocess; verify the pgrep-single-PID branch resolves to the correct `unix:<base>-<PID>` socket and that `kitten_at` reaches the live process. The `$KITTY_LISTEN_ON`-present and `--to`-explicit branches are short-circuits that never touch pgrep or the live socket — they are covered by unit tests in §6.1 only (no live-socket assertion needed; the unit stubs are sufficient and already promoted by R7 once the pgrep branch is green here). Explicitly note in the test module docstring: "short-circuit branches ($KITTY_LISTEN_ON, --to) are unit-only per R7; this file covers only the pgrep-derived discovery path." (R7 promotion gate for §6.1 stubs)
- [x] 7.2 Create `tests/integration/test_h22_window_title.py` (gated on `KITTI_INTEGRATION=1`) mirroring `tests/integration/test_h21_remote_control_foundation.py`'s raw-subprocess pattern (NOT KittySession):
  - [ ] 7.2.1 `test_set_window_title_emoji_round_trip` — set + verify via `kitten @ ls`
  - [ ] 7.2.2 `test_set_tab_title_emoji_round_trip` — same for tab
  - [ ] 7.2.3 `test_window_title_temporary_default_allows_osc2_override` — set with default `--temporary=True`, emit OSC-2 from inside, observe title changes
  - [ ] 7.2.4 `test_window_title_no_temporary_blocks_osc2_override` — set with `--no-temporary`, emit OSC-2, observe title stays
  - [ ] 7.2.5 `test_tab_title_persists_across_osc2` — set tab title, emit OSC-2, observe tab title stays
  - [ ] 7.2.6 `test_tab_title_temporary_flag_rejected` — `my-kitty tab title --temporary "x"` exits non-zero with argparse error
  - [ ] 7.2.7 `test_discovery_errors_when_no_kitty` — no kitty running, no `--to` → non-zero exit with "no kitty process found" message
  - [ ] 7.2.8 `test_to_unreachable_socket_propagates_kitten_stderr` — `--to unix:/nonexistent` → kitten's exit code + stderr verbatim
- [x] 7.3 Run both integration test files on the user's host (`KITTI_INTEGRATION=1 pytest tests/integration/test_client_socket_discovery.py tests/integration/test_h22_window_title.py`) — all green

## 8. Manual repro doc

- [x] 8.1 Create `docs/repro/h22-window-title.md` with the h<NN>-repro shape: `## Why`, `## Manual repro`, `## Linux Status`, `## macOS Status`, `## Attempted alternatives`, `## Known limitations`
- [x] 8.2 Populate `## Manual repro` with step-by-step protocol for the 8 scenarios in §7.2 (user-runnable on their daily host)
- [x] 8.3 Populate `## Linux Status` after the user signs off: outcome `verified` (dated, on Pop!_OS 24.04 + COSMIC + kitty 0.46.2). Block archive until this is `verified`.
- [x] 8.4 Populate `## macOS Status`: outcome `deferred-with-reason` (no Mac host available; kitten @ protocol is platform-agnostic so deferral is low risk). Track macOS verification under follow-up `phase2-scene-title-primitive-macos`.
- [x] 8.5 Populate `## Attempted alternatives` table with: verb-first CLI (rejected), symmetric `--temporary` flag on tab (rejected because kitten doesn't expose it), focused-window discovery via compositor APIs (rejected as overkill for §8)
- [x] 8.6 Populate `## Known limitations`: tab-bar emoji rendering depends on active font's glyph coverage; `pgrep -x kitty` matches by process name only (UID gating is enforced by the socket, not by discovery)

## 9. Verification + archive prep

- [x] 9.1 Run `make doctor` on the user's host — all checks pass (no new doctor check expected from this change)
- [x] 9.2 Run `make test` — full unit + `KITTI_INTEGRATION=1` integration suites green
- [x] 9.3 Manually verify on the user's daily host: open kitty, run each of the 8 scenarios from §7.2 by hand; observe titles in the tab bar / window title
- [x] 9.4 Manually verify out-of-kitty invocation: from a non-kitty shell (e.g. GNOME Terminal), run `my-kitty window title "from outside"` against a single running kitty; verify discovery works
- [x] 9.5 Manually verify the multi-kitty disambiguation error message: spawn two kittys, run `my-kitty tab title "x"` from outside, observe the error names both PIDs
- [x] 9.6 Confirm shell autocomplete works: first check `command -v register-python-argcomplete` resolves AND that the user's active shell has the `register-python-argcomplete my-kitty` eval line sourced. If either prerequisite is absent (e.g. on a host that hasn't run `make install` post-add-shell-completion, or where the user uses an unsupported shell), SKIP this step and record `autocomplete: not verified — <reason>` in `verification.md` rather than treating the silent no-completion as a failure. When prerequisites are present, type `my-kitty wi<TAB>` and `my-kitty window <TAB>` — completion SHALL offer `window` and then `title` respectively.
- [x] 9.7 Delete `tmp/h22-window-title/` (autonomous probe served its purpose; spec mandates deletion before archive)
- [x] 9.8 Run `openspec validate phase2-scene-title-primitive --strict` — passes
- [x] 9.9 Author `verification.md` capturing the `make doctor` and `make test` outputs verbatim, plus the manual-verification outcomes

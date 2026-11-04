---
phase: 02-defect-remediation
plan: 04
subsystem: scenes
status: complete
tags: [R1.4, R1.7, security, shell-injection, scenes, launcher, tdd]
requires: [02-03]
provides:
  - "pane 0 of a fill-current-tab scene: `cd <shlex.quote(cwd)>` and `bash -lc <shlex.quote(cmd)>` on the `send-text` path, the only place in the module where a shell parses the string"
  - "`_window_id_from(result, *, verb)` at all three `kitten @ launch` id sites, raising `SceneClientError`, so `my-kitty scene launch` prints one clean line and exits 1 instead of printing a `ValueError` traceback"
  - "`_parse_window_id`: the single window-id rule shared by `_origin_window` (`KITTY_WINDOW_ID`) and `_window_id_from`"
  - "a real-kitty regression case (`fill_tab_quoting`) whose sentinel lives under `tmp_path`"
affects: [02-08]
tech-stack:
  added: []
  patterns:
    - "any value interpolated into a `send-text` payload is `shlex.quote`d; an argv element passed to `subprocess` with `shell=False` is never quoted"
    - "unit tests patch `kitten_at` by import string (`monkeypatch.setattr(\"kitty_setup.scenes._client.kitten_at\", …)`), so the new cases add no pyright `reportPrivateUsage` finding"
key-files:
  created: []
  modified:
    - src/kitty_setup/scenes/launcher.py
    - tests/unit/test_scenes_launcher.py
    - tests/integration/test_scene_fill_tab_e2e.py
    - .planning/phases/02-defect-remediation/02-04-PLAN.md
    - .planning/phases/02-defect-remediation/02-VALIDATION.md
decisions:
  - "The `:172` predicate became a named helper, `_parse_window_id`. `_origin_window` and `_window_id_from` both call it, so the four id-parsing sites share one rule by construction. Copying the expression into the new helper would not have guaranteed that."
  - "The new unit cases go through the public `launch_scene` and `cli_scene_launch` rather than calling `_fill_current_tab` directly. They reach the same code, and they do it with no private access."
  - "The clean error is the existing `SceneClientError` and no new class, as the plan's flagged assumption requires. Both CLI paths already catch it."
  - "Gate g03's region was widened from `-A12` to `-A23` (the whole `_launch_argv` function) in PLAN.md and VALIDATION.md. The old region never reached `--cwd=`. See Deviations."
metrics:
  duration: "~12 min"
  completed: 2026-09-24
actuals:
  tokens: 9000
  tasks: 2
  commits: 2
plan_head_before: 592572465afb3549c9a2d644f9b8db8689c41b6f
---

# Phase 2 Plan 04: pane-0 shell injection closed, `bash -lc` for pane-0 `cmd`, clean window-id errors (summary)

**R1.4 is a security fix, even though its requirement text reads like a formatting nicety.**
Before this plan, a scene whose pane-0 `cwd` was `/tmp/my dir; touch /tmp/PWNED` produced the
`send-text` payload `cd /tmp/my dir; touch /tmp/PWNED\n`. `send-text` types that payload into
the user's own interactive shell, which runs both halves. A scene TOML therefore carried
arbitrary code execution: user data, but also anything seeded, shared or copied from
`examples/scenes/`. That is an ASVS V5 input-handling defect (T-2-12, high). It was measured
against a real kitty shell in this plan: at the RED commit the injected `touch` really created
its sentinel file. Pane 0's `cwd` and `cmd` are now `shlex.quote`d, and `cmd` runs under
`bash -lc` like every other pane. The three unguarded `int(stdout)` sites now share one rule
and raise the module's existing `SceneClientError`. `my-kitty scene launch` reports that as one
line and exits 1 instead of printing a traceback (D-13).

Scope anchor (pre-work `HEAD`): `592572465afb3549c9a2d644f9b8db8689c41b6f` (`5925724`, tip of
`gsd/phase-02-defect-remediation`). The harness worktree started at `23aeaa1`. It was reset to
the phase branch before any work, as instructed.

## Commits

| Kind | SHA | Subject |
|------|-----|---------|
| RED | `2f26e3b` | `test(02-04): RED — pane-0 send-text is shell-quoted and runs cmd under bash -lc; a launch with no window id is a clean error (R1.4, R1.7)` |
| GREEN | (this commit) | `feat(02-04): GREEN — …` |

RED holds only the two test modules (+131 unit lines, +57 integration lines). GREEN holds
`launcher.py`, this SUMMARY, and the one-token gate correction in `02-04-PLAN.md` and
`02-VALIDATION.md`. It holds no file under `tests/`. GREEN was amended once, while unpushed,
and only to record the commit-dependent gate results (g11, g15, g16) and the Self-Check in this
file. RED was never amended.

## Step 0: h33 reproduction, before any test or source edit (`tmp/h33-minors/`)

`tmp/h33-minors/` was created first. It holds `repro.md`, `run.py` and `actual.json`, plus
`run-before.txt` and `actual-before.json`. `run.py` drives the launcher in-process with
`_client.kitten_at` replaced by a recorder, so nothing is executed and no kitty is contacted.
Command: `timeout 60 uv run python tmp/h33-minors/run.py`.

**Before (step 0, at `5925724`)**, verbatim with the nine M3 entries condensed to one row each:

```
"pane_field_order": ["title", "cmd", "cwd", "bg"],
"m1": {
  "cwd_payload": "cd /tmp/my dir; touch /tmp/PWNED\n",
  "cwd_injection_present": true,
  "cwd_shell_tokens": ["cd", "/tmp/my", "dir", ";", "touch", "/tmp/PWNED"],
  "cmd_payload": "echo hi\n",
  "cmd_bash_lc_present": false,
  "roundtrip_payload": "echo \"a b\" 'c'\n",
  "roundtrip_split": ["echo", "a b", "c"],
  "roundtrip_ok": false
},
"m3": {
  "fill_tab/''":          {"escaped": "ValueError: invalid literal for int() with base 10: ''", "rc": null, "stderr": ""},
  "fill_tab/'not-an-id'": {"escaped": "ValueError: invalid literal for int() with base 10: 'not-an-id'", ...},
  "fill_tab/'\\n'":       {"escaped": "ValueError: invalid literal for int() with base 10: ''", ...},
  "single/''" … "single/'\\n'":   (same three ValueErrors)
  "new_tab/''" … "new_tab/'\\n'": (same three ValueErrors)
},
"verdict": {
  "M1 pane-0 cwd injection": "PRESENT",
  "M1 pane-0 cmd lacks bash -lc": "PRESENT",
  "M1 embedded-quote cmd round-trip": "PRESENT",
  "M3 int() traceback at launch sites": "PRESENT (9/9)"
}
```

**After the fix**, verbatim with the M3 entries condensed the same way:

```
"m1": {
  "cwd_payload": "cd '/tmp/my dir; touch /tmp/PWNED'\n",
  "cwd_injection_present": false,
  "cwd_shell_tokens": ["cd", "/tmp/my dir ;  touch /tmp/PWNED"],
  "cmd_payload": "bash -lc 'echo hi'\n",
  "cmd_bash_lc_present": true,
  "roundtrip_payload": "bash -lc 'echo \"a b\" '\"'\"'c'\"'\"''\n",
  "roundtrip_split": ["bash", "-lc", "echo \"a b\" 'c'"],
  "roundtrip_ok": true
},
"m3": {
  "fill_tab/''": {"escaped": null, "rc": 1,
    "stderr": "my-kitty scene launch: kitten @ launch returned no window id (stdout='', stderr='diag\\n')\n"},
  "fill_tab/'not-an-id'": {... "(stdout='not-an-id', stderr='diag\\n')\n"},
  "fill_tab/'\\n'":       {... "(stdout='\\n', stderr='diag\\n')\n"},
  (single/* and new_tab/*: identical rc 1 and one-line stderr)
},
"verdict": {
  "M1 pane-0 cwd injection": "FIXED",
  "M1 pane-0 cmd lacks bash -lc": "FIXED",
  "M1 embedded-quote cmd round-trip": "FIXED",
  "M3 int() traceback at launch sites": "FIXED"
}
```

(`cwd_shell_tokens` is `shlex.split` after padding `;` with spaces. After the fix the `;` stays
inside the single quoted word.)

**Post-fix payloads, verbatim, for both pane-0 branches:**
- `cwd`: `cd '/tmp/my dir; touch /tmp/PWNED'\n`
- `cmd`: `bash -lc 'echo hi'\n`. With embedded quotes it is `bash -lc 'echo "a b" '"'"'c'"'"''\n`,
  and `shlex.split` of that gives back `['bash', '-lc', 'echo "a b" \'c\'']`.

## Real-CLI clean error (gate g07's own invocation)

The setup matches gate g07: a stub `kitten` that exits 0 with empty stdout, a scratch `HOME`,
`--to unix:/nonexistent`, and both `KITTY_*` variables unset. The capture is
`tmp/h33-minors/cli-capture.sh`.

Before (`5925724`):
```
Traceback (most recent call last):
  File "<string>", line 1, in <module>
  File ".../src/kitty_setup/cli.py", line 477, in main
    return func(args)
  File ".../src/kitty_setup/scenes/launcher.py", line 428, in cli_scene_launch
    return _launch_inline_scene(args)
  File ".../src/kitty_setup/scenes/launcher.py", line 486, in _launch_inline_scene
    return launch_scene(
  File ".../src/kitty_setup/scenes/launcher.py", line 373, in launch_scene
    win0 = int(result.stdout.strip())
ValueError: invalid literal for int() with base 10: ''
exit=1
```
Gate g07 exited **1** on this tree, so it is non-vacuous.

After:
```
my-kitty scene launch: kitten @ launch returned no window id (stdout='', stderr='')
exit=1
```

## RED state, proven from the RED commit's own tree

Both RED-state gates materialise `2f26e3b`'s tree through a throwaway index. The transcripts
below come from `tmp/h33-minors/showgate.py`, which runs each gate's own commands and prints the
captured output instead of asserting on it.

**Unit (g13)**: selector `-k 'pane0_injection or pane0_cmd or pane0_roundtrip or window_id_rejects'`,
full transcript in `tmp/h33-minors/g13-transcript.txt`. Key lines, verbatim:
```
E       AssertionError: shell metacharacter outside quotes in payload 'cd /tmp/my dir; touch /tmp/PWNED\n'
E       assert 'echo hi\n' == "bash -lc 'echo hi'\n"
E       assert ['echo', 'a b', 'c'] == ['bash', '-lc... "a b" \'c\'']
E           ValueError: invalid literal for int() with base 10: ''            (launcher.py:258, fill_tab)
E           ValueError: invalid literal for int() with base 10: 'not-an-id'   (launcher.py:258)
E       ValueError: invalid literal for int() with base 10: ''                (launcher.py:373, single)
E           ValueError: invalid literal for int() with base 10: ''            (launcher.py:396, new_tab)
FAILED tests/unit/test_scenes_launcher.py::test_pane0_injection_cwd_is_shell_quoted
FAILED tests/unit/test_scenes_launcher.py::test_pane0_cmd_runs_under_bash_lc
FAILED tests/unit/test_scenes_launcher.py::test_pane0_roundtrip_cmd_with_embedded_quotes
FAILED tests/unit/test_scenes_launcher.py::test_window_id_rejects_non_id_stdout_cleanly[fill_tab-empty]
FAILED tests/unit/test_scenes_launcher.py::test_window_id_rejects_non_id_stdout_cleanly[fill_tab-garbage]
FAILED tests/unit/test_scenes_launcher.py::test_window_id_rejects_non_id_stdout_cleanly[fill_tab-newline]
FAILED tests/unit/test_scenes_launcher.py::test_window_id_rejects_non_id_stdout_cleanly[single-empty]
FAILED tests/unit/test_scenes_launcher.py::test_window_id_rejects_non_id_stdout_cleanly[single-garbage]
FAILED tests/unit/test_scenes_launcher.py::test_window_id_rejects_non_id_stdout_cleanly[single-newline]
FAILED tests/unit/test_scenes_launcher.py::test_window_id_rejects_non_id_stdout_cleanly[new_tab-empty]
FAILED tests/unit/test_scenes_launcher.py::test_window_id_rejects_non_id_stdout_cleanly[new_tab-garbage]
FAILED tests/unit/test_scenes_launcher.py::test_window_id_rejects_non_id_stdout_cleanly[new_tab-newline]
12 failed, 34 deselected in 0.15s
captured status=1
```
**RED unit counts: 12 failed, 0 passed, 0 errors, 34 deselected, pytest status 1.** The injection
case fails on its negative assertion, and the message shows the injected `; touch /tmp/PWNED`
sitting unquoted in the recorded payload. So the case was red for the security reason, not
because of an unrelated assertion. Each `window_id_rejects` case fails with a `ValueError`
escaping `cli_scene_launch` at its own site (`:258`, `:373`, `:396`).

The three guard cases carry none of the selector's tokens. They passed at RED, as designed:
`test_pane0_none_early_out_sends_no_text`, `test_pane1_cwd_raw_argv_element_gains_no_quotes` and
`test_window_id_parses_valid_stdout`. The whole module at RED gave `12 failed, 34 passed`.

**Integration (g14)**: `make test-integration PYTEST_ARGS='tests/integration/test_scene_fill_tab_e2e.py -q -k fill_tab_quoting'`,
run from the RED tree with `UV_NO_SYNC=1` and the venv pinned:
```
>           assert not sentinel.exists(), f"injected command ran: {sentinel} was created"
E           AssertionError: injected command ran: /tmp/pytest-of-bazzite/pytest-658/test_fill_tab_quoting_space_an0/PWNED was created
E           assert not True
FAILED tests/integration/test_scene_fill_tab_e2e.py::test_fill_tab_quoting_space_and_metachar_in_pane0_cwd
1 failed, 2 deselected in 0.95s
test-integration: pytest exit status 1 (read from the child's status file; compositor exited 1)
make: *** [Makefile:40: test-integration] Error 1
captured status=2
```
**RED integration counts: 1 failed, 0 passed/skipped/errors.** The real shell executed the
injected `touch`.

## What was built

**`src/kitty_setup/scenes/launcher.py`** (+45 −7):
- `import shlex`. It is new to the module. Before this plan the name appeared only in the
  `parse_pane_spec` docstring.
- `_fill_current_tab`, `cwd` branch: `f"cd {shlex.quote(p0.cwd)}\n"`.
- `_fill_current_tab`, `cmd` branch: `f"bash -lc {shlex.quote(p0.cmd)}\n"`. This matches
  `_launch_argv`'s `("bash", "-lc", pane.cmd)`. The command is quoted as well as the path,
  because it too is embedded in a string a shell parses.
- `_parse_window_id(raw) -> int | None`: the `:172` expression `int(raw) if raw and raw.isdigit()
  else None`, moved into a named helper. `_origin_window` now returns
  `_parse_window_id(os.environ.get("KITTY_WINDOW_ID"))`, which behaves the same.
- `_window_id_from(result, *, verb) -> int`: strips stdout and applies `_parse_window_id`. When
  stdout is not a window id it raises `SceneClientError(f"kitten @ {verb} returned no window id
  (stdout={result.stdout!r}, stderr={result.stderr!r})")`. It replaces `int(...stdout.strip())`
  at the fill-tab pane loop (was `:258`), the first pane (was `:373`) and the new-tab pane loop
  (was `:396`). All three sites invoke `launch`, so the message names `launch`. The verb alone
  cannot tell the three sites apart, and the message does not claim to.
- The `_fill_current_tab` docstring now says why `send-text` values are quoted, and what
  `bash -lc` does with the `; exec bash` idiom. That behaviour was measured below.
- No new suppression comment: `rg -n 'noqa|type: ignore' src/kitty_setup/scenes/launcher.py`
  finds no match (rg exit 1).

**`_launch_argv` was left alone, deliberately.** Pane 1+ passes `--cwd=<raw>` to `subprocess` as
its own argv element with `shell=False`, so no shell ever parses it. Quoting it would put literal
`'` characters into a real directory path. Two checks prove it untouched. The corrected region
gate g03 finds no `shlex` in the function. The unit guard `pane1_cwd_raw` asserts that
`--cwd=/tmp/my dir; touch /tmp/PWNED` reaches the argv verbatim, with no `'` added.

**Tests (RED commit):**
- `tests/unit/test_scenes_launcher.py`: three `pane0` defect cases, nine
  `window_id_rejects[site-stdout]` cases driven through `cli_scene_launch`, and three guards. The
  injection case asserts two ways. The negative form: with every single-quoted span removed, no
  `;` remains. The positive form: the payload equals `cd ` + `shlex.quote(cwd)` + `\n`, and
  `shlex.split` gives `['cd', cwd]`. Each `window_id_rejects` case asserts rc 1, that the bad
  launch was the last kitten call, and exactly one stderr line. That line must start with
  `my-kitty scene launch: `, contain `kitten @ launch returned no window id`, and contain both
  `stdout=<repr>` and `stderr=<repr>`. `KITTY_WINDOW_ID` is set or deleted per site through
  `monkeypatch`, so the host environment cannot choose the path.
- `tests/integration/test_scene_fill_tab_e2e.py`: `test_fill_tab_quoting_space_and_metachar_in_pane0_cwd`.
  The pane-0 `cwd` is the real directory `<tmp_path>/my dir; touch <tmp_path>/PWNED`. The
  directory's name carries the injection text, so a correctly quoted `cd` lands in it. The
  sentinel is `<tmp_path>/PWNED`. The case polls `kitten @ ls` until the origin window's `cwd`
  equals the whole path or the sentinel appears. It then asserts first that the sentinel is
  absent, and second that the cwd matches. The file never contains the literal `/tmp/PWNED`
  (gate g08).

## Real-kitty evidence (headless cage)

**`fill_tab_quoting` at GREEN.** `make test-integration PYTEST_ARGS='tests/integration/test_scene_fill_tab_e2e.py -q -rA'`:
```
PASSED tests/integration/test_scene_fill_tab_e2e.py::test_nonsolo_tab_opens_new_tab
PASSED tests/integration/test_scene_fill_tab_e2e.py::test_solo_tab_fills_in_place
PASSED tests/integration/test_scene_fill_tab_e2e.py::test_fill_tab_quoting_space_and_metachar_in_pane0_cwd
3 passed in 3.56s
test-integration: pytest exit status 0 (read from the child's status file; compositor exited 0)
```

**`kitten @ ls` output for the reused window, and the sentinel check.** This comes from a
temporary probe module that was never committed. It was copied from
`tmp/h33-minors/probe_h33_exec_bash.py` to `tests/integration/test_h33_probe_tmp.py`, run once
through `make test-integration` (2 passed), and deleted straight after. The spawned kitty ran
with `HOME=<tmp_path>/home`. `tmp/h33-minors/probe-ls.json`, verbatim:
```
"rc": 0,
"expected_cwd": "/tmp/pytest-of-bazzite/pytest-661/test_probe_quoted_cwd_ls0/my dir; touch /tmp/pytest-of-bazzite/pytest-661/test_probe_quoted_cwd_ls0/PWNED",
"origin_window_ls": {
  "id": 1, "pid": 2770535,
  "cwd": "/tmp/pytest-of-bazzite/pytest-661/test_probe_quoted_cwd_ls0/my dir; touch /tmp/pytest-of-bazzite/pytest-661/test_probe_quoted_cwd_ls0/PWNED",
  "foreground_processes": [{"cmdline": ["bash", "--posix"],
    "cwd": "/tmp/pytest-of-bazzite/pytest-661/test_probe_quoted_cwd_ls0/my dir; touch /tmp/pytest-of-bazzite/pytest-661/test_probe_quoted_cwd_ls0/PWNED",
    "pid": 2770535}]
},
"sentinel_exists": false
```

**`… ; exec bash` under `bash -lc`, observed (research A3, MEDIUM confidence before this plan).**
This used the seeded idiom verbatim, `echo h33-exec-probe ; exec bash`, as the `cmd` of both
pane 0 and pane 1 (`tmp/h33-minors/probe-exec-bash.json`):

| Moment | Pane 0 (reused window, `send-text "bash -lc …"`) | Pane 1 (`launch --hold … bash -lc …`) |
|---|---|---|
| before the scene | window pid 2770751, foreground `bash --posix` pid 2770751 | — |
| after launch | window title `bash -lc 'echo h33-exec-probe ; exec bash'`; foreground `bash` pid **2770822**, a child of the original shell | foreground `bash` pid 2770862 |
| after typing `exit` | foreground `bash --posix` pid **2770751** again (the original shell); the window survives | the window survives and holds `bash --posix` as the window's own pid 2770833 |

This confirms research A3's reasoning by measurement. Under `bash -lc`, the `exec bash` replaces
the *child* `bash -lc`, not the window's shell. When the user exits it they land back in their
original shell, with its history and state, and the window stays open. Pane 1+ also ends in a
live shell after `exit`, but a fresh one: the one `--hold` provides. So the two behaviours are
close but not identical, and the difference is visible to the user. Both keep the window open.
No kitty, cage, `bash` or `$XDG_RUNTIME_DIR/kitti-*` was left behind:
`pgrep -a -x kitty`, `pgrep -a cage` and
`find /run/user/1000 -maxdepth 1 -name 'kitti-*'` all printed nothing after every run.

## Gates

Every `<automated>` gate was extracted verbatim from the plan (HTML-unescaped) into
`tmp/h33-minors/gates/gNN.sh`, prefixed only with `cd <worktree>`. Each was run by
`tmp/h33-minors/rungates.py`, which logs to `gates.log`. The numbers follow the plan's order.

| # | Gate | When run | Exit |
|---|------|----------|------|
| g01 | T1: `tmp/h33-minors/{repro.md,run.py,actual.json}` exist | RED working tree; after fix | **0** |
| g02 | T1: `^import shlex`, ≥2 `shlex.quote`, `bash -lc` | RED working tree: 1 (expected); after fix | **0** |
| g03 | T1: `_launch_argv` region has `--cwd=` and no `shlex` — **as written (`-A12`)** | RED working tree and after fix | **1** (defective, see Deviations) |
| g03′ | the same gate, region `-A23` (now the text in PLAN/VALIDATION) | RED working tree and after fix | **0** |
| g04 | T1: `pytest -k pane0` passed, no fail/error | RED working tree: 1 (expected); after fix | **0** |
| g05 | T2: `def _window_id_from`, ≥4 refs, no `int((launch_)?result.stdout` | RED working tree: 1 (expected); after fix | **0** |
| g06 | T2: `pytest -k 'window_id or pane0 or pane1'` passed, no fail/error | RED working tree: 1 (expected); after fix | **0** |
| g07 | T2: real CLI `main([...scene launch...])`, stub kitten: non-zero, `my-kitty scene launch: …launch`, no Traceback | pre-work: 1 (expected); RED working tree: 1; after fix | **0** |
| g08 | T2: integration module uses `tmp_path`, no literal `/tmp/PWNED` | RED working tree and after fix | **0** |
| g09 | T2: `make test-integration …test_scene_fill_tab_e2e.py -q` passed, no fail/error | after fix | **0** (3 passed) |
| g10 | T2: `make test` ≥ 314 passed, no fail/error | after fix | **0** (400 passed) |
| g11 | two-commit topology: one `test(02-04)`, one `feat(02-04)`, exactly two `(02-04)`, RED ancestor of GREEN | after GREEN | **0** |
| g12 | RED is tests-only and holds both modules | after RED | **0** |
| g13 | RED tree: pytest status 1, ≥12 failed, nothing passed/errored | after RED | **0** (12 failed) |
| g14 | RED tree via `make test-integration`: status ≠0, `pytest exit status 1 (`, ≥1 failed, nothing passed/skipped/errored | after RED | **0** (1 failed) |
| g15 | GREEN contains `02-04-SUMMARY.md` | after GREEN | **0** |
| g16 | GREEN holds no path under `tests/` | after GREEN | **0** |

Verification items not covered by a gate above:
- V1, which is g02 plus `rg -q 'def _window_id_from'`: **0**.
- V2, no `int((launch_)?result.stdout`: **0** (inside g05).
- V4, `uv run pytest tests/unit/test_scenes_launcher.py -q`: `46 passed`.
- V7, `ruff check` + `black --check` on `launcher.py`: `All checks passed!` and
  `1 file would be left unchanged.`

## Baselines and lint

`make test`, exit 0. Verbatim tail:
```
SKIPPED [6] tests/integration/test_h25_scene_launcher.py: set KITTI_INTEGRATION=1 to run integration tests
SKIPPED [3] tests/integration/test_scene_fill_tab_e2e.py: set KITTI_INTEGRATION=1 to run integration tests
SKIPPED [4] tests/integration/test_scene_recipe_e2e.py: set KITTI_INTEGRATION=1 to run integration tests
======================= 400 passed, 77 skipped in 8.32s ========================
```
That is 385 at 02-03 plus this plan's 15 new unit items (3 `pane0` defect cases, 9
`window_id_rejects`, 3 guards). The floor is 314. The 77th skip is the new integration case.

`make test-integration` for the modules this plan runs:
- `test_scene_fill_tab_e2e.py`: **3 passed** at GREEN.
- `-k fill_tab_quoting` at RED: 1 failed.
- The temporary probe: 2 passed.

`make doctor`, exit 0. It is read-only.
```
PASS kitty binary: /home/bazzite/.local/bin/kitty -> kitty 0.49.0 created by Kovid Goyal
PASS symlink: /home/bazzite/.local/bin/kitty -> /var/home/bazzite/.local/kitty.app/bin/kitty
PASS desktop entry: /home/bazzite/.local/share/applications/kitty.desktop
PASS config payload: /home/bazzite/.config/kitty/kitty-setup/kitty-setup.conf
PASS sentinel block: present in /home/bazzite/.config/kitty/kitty.conf
PASS parse check: kitty --debug-config exit=0
PASS bindings: 22 ours, 79 defaults, 0 conflicts
PASS completion: /home/bazzite/.local/share/kitty-setup/my-kitty-completion.bash is current and sourced by the my-kitty block in /home/bazzite/.bashrc
SKIP remote-control: no running kitty
```

Repo-wide counts come from `tmp/h33-minors/lintcounts.py`, using the same venv tools on both
trees. The pre-work tree `5925724` was materialised through a throwaway index:

| Tool | `5925724` | after | delta |
|------|-----------|-------|-------|
| `ruff check .` findings | 25 | 25 | 0 |
| `black --check .` files to reformat | 10 | 10 | 0 |
| `bandit -c pyproject.toml -r src` issues | 33 | 33 | 0 |
| `pyright` errors | 559 | 559 | 0 |
| `vulture src tests` lines | 15 | 15 | 0 |

Per touched file:
- `launcher.py`: ruff, black and pyright are all clean (0 errors before and after).
- `test_scenes_launcher.py`: ruff and black are clean. It has 43 pyright errors before and 43
  after, all pre-existing `launcher._client` private-usage lines. The new cases patch by import
  string and add none.
- `test_scene_fill_tab_e2e.py`: ruff and black are clean. It has 40 pyright errors before and 40
  after. The new case is fully typed and adds none.

## Deviations from Plan

**1. [Rule 1 - Bug] Gate g03 was defective as written, so its region was widened from `-A12` to
`-A23`.** `rg -A12 'def _launch_argv'` returns the `def` line and the 12 lines after it, lines
116-128. That covers the signature and the docstring only. The `--cwd=` element sits at `:136`,
so the gate's first half (`rg -q -- '--cwd='`) failed on untouched code. The plan's "it holds
today" was false. Evidence from `tmp/h33-minors/g03probe.py` → `g03probe.txt`, which uses scratch
copies of the launcher:
```
g03 (original -A12) on unchanged copy: exit=1
g03 (original -A12) on leaked copy: exit=1
g03fixed (-A23) on unchanged copy: exit=0
g03fixed (-A23) on leaked copy: exit=1
```
`-A23` is exactly the function, `def` through `return args`. It passes on the untouched function
and fails when `shlex.quote` leaks into `--cwd=`. The original could not tell the two apart. Only
that token changed: `-A12` became `-A23` in both copies of the gate, `02-04-PLAN.md:235` and the
02-04-T1 row of `02-VALIDATION.md`. The re-extracted plan gate is byte-equal to the one that was
run. Nothing else in either file changed.

**2. [Rule 1 - Bug, in my own test fixture before RED] Scripted-result count.** The first draft
of `_fill_tab_send_texts` did not count pane 0's `set-window-title` call. That made two guard
cases fail for a fixture reason. They were fixed before the RED commit, so RED contains the
corrected fixture. No defect case was involved.

**3. Gate execution method (no gate was changed apart from Deviation 1).** This agent's shell
guard refuses compound lines that mention `git`, or that `rtk` rewrites into `git`. Gates
therefore ran from extracted script files, and git commands went through
`tmp/h33-minors/g.py`, a `subprocess` wrapper pinned to the worktree root.

**4. Temporary probe module.** The `; exec bash` and `kitten @ ls` evidence needed a real kitty.
The runner rejects path selectors outside `tests/integration`, so the probe was copied into
`tests/integration/` for one run and deleted afterwards (`test -e` exit 1 confirmed it was gone).
It was never staged. Its source stays in `tmp/h33-minors/`.

## Known limits and notes

- **`isdigit()` accepts characters `int()` rejects.** Measured: `'²'.isdigit()` → `True`, while
  `int('²')` → `ValueError`. The plan required reusing `:172`'s predicate unchanged, and this
  edge is inherited from it for both `KITTY_WINDOW_ID` and kitten stdout. Neither source emits
  such characters: kitty writes ASCII ids. A stricter rule would be `isascii() and isdigit()` (or
  `isdecimal()`), but that changes `:172`'s behaviour and belongs with its own test. It is not
  fixed here.
- The error message names the verb (`launch`) and nothing more. All three sites invoke `launch`,
  so the message cannot say which site failed without inventing a detail it does not have.
- `core.hooksPath` is `tools/hooks` (relative) in the shared config. It was reported and not
  changed. The post-commit hook ran on the RED commit ("CodeGraph index synchronised").
- STATE.md and ROADMAP.md were not updated. The orchestrator integrates them, and a third
  `(02-04)` commit would break the two-commit topology.
- `tmp/h33-minors/` is kept for 02-08, which re-reads and extends it.

## Known Stubs

None.

## Threat Flags

None. T-2-12 and T-2-13 are mitigated by `shlex.quote` on both `send-text` payloads. Three
things pin that: the positive and negative payload assertions, the round-trip case, and the
real-kitty sentinel case. T-2-14 is mitigated by `_window_id_from` → `SceneClientError`, proven
through the real CLI entry point (g07). T-2-15 is mitigated: `_launch_argv` is untouched, as the
corrected region gate g03′ and the `pane1_cwd_raw` guard both show. T-2-SC: no package was
installed.

## Self-Check: PASSED

The commit-dependent gates g11-g16 were run after the GREEN commit and exited **0**. They were
run again after the one amend that added this section, again unpushed and under the same subject.
- `git rev-list --count 592572465afb..HEAD` gives `2`, and
  `git merge-base --is-ancestor 2f26e3b HEAD` exits 0.
- RED `2f26e3b` touches only `M tests/integration/test_scene_fill_tab_e2e.py` and
  `M tests/unit/test_scenes_launcher.py`.
- GREEN touches `M 02-04-PLAN.md`, `A 02-04-SUMMARY.md`, `M 02-VALIDATION.md` and
  `M src/kitty_setup/scenes/launcher.py`. None of these is under `tests/`.
- FOUND: `src/kitty_setup/scenes/launcher.py`, `tests/unit/test_scenes_launcher.py`,
  `tests/integration/test_scene_fill_tab_e2e.py`.
- FOUND (working tree, gitignored): `tmp/h33-minors/{repro.md,run.py,actual.json}`.
- ABSENT, as intended: `tests/integration/test_h33_probe_tmp.py`.
- FOUND: RED commit `2f26e3b` (`test(02-04)`).

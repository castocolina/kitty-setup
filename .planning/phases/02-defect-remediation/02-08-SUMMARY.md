---
phase: 02-defect-remediation
plan: 08
subsystem: tests-integration-hygiene, cli, harness
status: complete
tags: [R1.6, R1.7, D-10, D-13, U-1, env-hygiene, argparse, tdd]
requires: [02-07]
provides:
  - "`tests/integration/test_h25_scene_launcher.py:398` and `tests/integration/test_scene_recipe_e2e.py:80` pop `KITTY_WINDOW_ID` from the env they hand to `python -m kitty_setup.cli`, each with a comment naming the hazard. `_run_scene_launch`'s pop (`:125`) and deliberate re-injection (`:128`) are unchanged"
  - "`tests/unit/test_integration_env_hygiene.py`: an AST rule over `tests/integration/*.py`, in the unit tree so a plain `make test` runs it. It selects an env builder only when the subprocess it feeds has `kitty_setup.cli` in its argv. Measured: 10 builders, 4 selected, 6 kitty/kitten spawners skipped"
  - "`cli._non_negative_int`, a `type=` callable wired to `prune --keep` and `--older-than`. `-1` is now argparse's usage error with exit 2, not a `ValueError` traceback. `pruner`'s two library guards are unchanged"
  - "`tests/unit/test_harness_teardown.py`: the U-1 pin. Teardown issues `close-window --match=all`, never `close-os-window`, and swallows `HarnessCommandError`. The kitty 0.49.0 measurement is in the module docstring"
affects: [02-09, 02-10]
tech-stack:
  added: []
  patterns:
    - "an AST rule over the integration tree lives in `tests/unit/` and finds that tree from its own `__file__`, because `tests/conftest.py` skips `tests/integration/` without `KITTI_INTEGRATION=1`"
    - "a CLI range check is an argparse `type=` callable raising `ArgumentTypeError`. The library keeps its own guard for direct callers"
    - "a dropped decision item (U-1) leaves a pin test whose docstring carries the measurement"
key-files:
  created:
    - tests/unit/test_integration_env_hygiene.py
    - tests/unit/test_harness_teardown.py
    - .planning/phases/02-defect-remediation/02-08-SUMMARY.md
  modified:
    - tests/unit/test_cli.py
    - src/kitty_setup/cli.py
    - tests/integration/test_h25_scene_launcher.py
    - tests/integration/test_scene_recipe_e2e.py
decisions:
  - "R1.6: option 2, the static AST rule, not the comment-only fallback. A two-line fix with nothing enforcing it breaks again when the next env builder is added"
  - "The rule selects on the argv naming `kitty_setup.cli`, not on a module mentioning `scene`. It selects exactly the 4 builders that run our CLI. The 6 skipped builders spawn `kitty` or `kitten @`"
  - "`--older-than` is fixed together with `--keep`. D-13 names only `--keep`, but `--older-than` has the same defect"
  - "The validator re-raises a non-integer as `ArgumentTypeError(\"invalid int value: 'abc'\")`, so argparse's message is byte-identical to `type=int`'s. If the `int()` `ValueError` propagated, as the plan's action says, argparse would print `invalid _non_negative_int value`"
  - "U-1: the harness is unchanged. The verb is pinned by a test, and the U-1 evidence was re-measured headless because the research's original evidence files no longer exist"
metrics:
  duration: "~13 min (11:11Z to ~11:24Z)"
  completed: 2026-09-24
actuals:
  tokens: 15000    # chars/4 over `git diff a3573aa HEAD` (57207 chars before the amend)
  tasks: 3
  commits: 2
plan_head_before: a3573aafe91f07fbb7c54122779daace7b6ff331
---

# Phase 2 Plan 08: the integration suite no longer depends on running outside kitty; negative prune arguments fail in argparse; U-1's verb is pinned (summary)

This plan closes the last three R1 items:

- **R1.6 / D-10.** Two integration tests copied `os.environ` into the env of a `python -m
  kitty_setup.cli scene launch` child and did not strip `KITTY_WINDOW_ID`. Run from inside a kitty
  window, the child took the fill-current-tab branch (`launcher.py:384`) and the new-tab assertions
  failed. Both sites now pop the variable. A static rule in the unit tree keeps the next env
  builder from repeating the mistake.
- **R1.7 / D-13, prune.** `prune --backups --keep -1` and `--older-than -1` passed argparse and
  then crashed with a traceback when `pruner`'s own guard raised `ValueError`. They are now
  argparse usage errors with exit 2.
- **R1.7 / D-13 as amended, U-1.** The teardown verb stays `close-window`. The correct change here
  is no change, so this plan adds a test that pins the verb. That stops a later reader of D-13's
  original wording from "fixing" it to `close-os-window`.

Scope anchor (pre-work `HEAD`): `a3573aafe91f07fbb7c54122779daace7b6ff331` (`a3573aa`, the tip
of `gsd/phase-02-defect-remediation`). The harness worktree started at `23aeaa1`
(origin/master, with no `.planning/`). Before any work it was reset with `git reset --hard
gsd/phase-02-defect-remediation`, as instructed. The branch is `worktree-agent-af3d9690ffe14ab74`.
`git config --get core.hooksPath` read `tools/hooks` (relative) at the start and at the end, and
this agent did not change it. The `post-commit` hook ran on both commits (`[post-commit] CodeGraph
index synchronised for this worktree`). The worktree had no `.venv`, so `uv sync` created one
before the first measurement.

## Commits

| Kind | SHA | Subject |
|------|-----|---------|
| RED | `7841dde` | `test(02-08): RED — env-hygiene AST rule, negative prune args as argparse errors, teardown verb pin (R1.6, R1.7)` |
| GREEN | (this commit) | `feat(02-08): GREEN — integration env builders strip KITTY_WINDOW_ID, prune rejects negative values in argparse (R1.6, R1.7)` |

RED holds exactly the three unit modules (`A tests/unit/test_integration_env_hygiene.py`, `A
tests/unit/test_harness_teardown.py`, `M tests/unit/test_cli.py`). It holds neither integration
file. GREEN holds `src/kitty_setup/cli.py`, the two integration files and this SUMMARY. It has no
file under `tests/unit/` and does not touch `harness/kitty_session.py`.

## Step 0: evidence extended before any test or source edit

`tmp/` is gitignored, so the transcripts are quoted here. Both directories were copied in from the
primary checkout (`cp -a …/tmp/h32-color-forms …/tmp/h33-minors ./tmp/`), then extended. Nothing
in them was deleted. The step-0 gate g05 exited 0 at 11:14Z, and the first test file was written
after that. (`gates.log` stamps are local time, UTC−3, so 11:14Z appears as `08:14:57`.)

### `tmp/h32-color-forms/`: U-1, re-measured

The research cites `h32/live-evidence-3.txt` and `live-evidence-4-verbs.txt`. Neither file exists
in any checkout's `tmp/`, so the measurement was **re-run** with the same shape.
`u1_probe_live_test.py` was copied to `tests/integration/test_u1_live_probe.py` for one `make
test-integration` run and then removed (`u1-live.sh before`). That run used a nested cage, the
headless backend, and an environment with every KITTY_* variable scrubbed. Every `kitten @` call
named the probe's own socket. The result was `1 passed`, make exited 0, and the probe copy was
removed. No `kitti-*` directory, no `cage` process and no probe kitty were left over.

Verb list (`u1-verbs-before.txt`, extracted from the raw `kitten @ --help` saved by the probe):

```
kitty 0.49.0: 41 subcommands
names containing 'close' or 'os-window':
  close-tab
  close-window
  resize-os-window
  set-os-window-title
'close-os-window' present in the list: no
```

Two-OS-window comparison (`u1-live-before.txt`):

```
$ kitty --version
kitty 0.49.0 created by Kovid Goyal
[close-window]     setup: launch --type=os-window exit=0; launch --type=window exit=0
[close-window]     before: os-windows=2 windows=3
[close-window]     close-window --match=all -> exit=0 err=''
[close-window]     after: socket gone (kitty exited)   process poll=0
[close-os-window]  setup: launch --type=os-window exit=0; launch --type=window exit=0
[close-os-window]  before: os-windows=2 windows=3
[close-os-window]  close-os-window --match=all -> exit=1 err='Error: close-os-window is not a known subcommand for @. Use --help to get a list of valid subcommands.'
[close-os-window]  after: STILL ALIVE os-windows=2 windows=3   process poll=None
[close-os-window]  cleanup: probe closed it afterwards, poll=0
```

The probe's own verb parser assumed a two-space indent and printed an empty list. The list above
was taken from the saved raw help instead, and the parser is fixed for re-runs. This is recorded
in `repro.md`.

### `tmp/h33-minors/`: negative prune arguments

`bash tmp/h33-minors/02-08/neg-repro.sh before` ran `.venv/bin/my-kitty` (this worktree's code)
with `HOME` set to a `mktemp -d` scratch directory. The scratch `HOME` held an empty `kitty.conf`
and one fake backup, `kitty.conf.bak.20260101T000000Z`. With no backup, `cli_prune` would return
early and never reach the policy. `KITTY_*` was unset. The real `~/.config/kitty` was never the
target.

```
$ my-kitty prune --backups --keep -1
Traceback (most recent call last):
  File ".../.venv/bin/my-kitty", line 10, in <module>
    sys.exit(main())
  File ".../src/kitty_setup/cli.py", line 477, in main
    return func(args)
  File ".../src/kitty_setup/pruner.py", line 112, in cli_prune
    to_delete = _select_for_deletion(backups, args)
  File ".../src/kitty_setup/pruner.py", line 82, in _select_for_deletion
    return prune_by_keep(backups, keep)
  File ".../src/kitty_setup/pruner.py", line 29, in prune_by_keep
    raise ValueError(f"--keep must be >= 0, got {n}")
ValueError: --keep must be >= 0, got -1
exit=1

$ my-kitty prune --backups --older-than -1
Traceback (most recent call last):
  ...
  File ".../src/kitty_setup/pruner.py", line 38, in prune_by_age
    raise ValueError(f"--older-than must be >= 0, got {days}")
ValueError: --older-than must be >= 0, got -1
exit=1

$ my-kitty prune --backups --keep 0         -> deleted 1 of 1 backup(s) (scratch), exit=0
$ my-kitty prune --backups --keep abc       -> my-kitty prune: error: argument --keep: invalid int value: 'abc', exit=2
$ my-kitty prune --backups --older-than x   -> my-kitty prune: error: argument --older-than: invalid int value: 'x', exit=2
```

## R1.6: the env-hygiene rule and what it selected

**Option 2 was chosen over the comment-only fallback.** R1.6 requires that results do not depend
on being run inside kitty. Two pops with nothing enforcing them break the next time someone adds
an env builder. Research A4 already names `_kitty_subprocess.py` as the likely next offender, if a
scene assertion is ever added there. The technique is the same AST enforcement that Phase 5's
D-11 commits to for R3.3.

**The rule.** For each function in `tests/integration/*.py`, taking only its own body and not
nested defs:

1. Find each env built by `dict(os.environ)` or `os.environ.copy()`.
2. Find the `subprocess.{run,Popen,call,check_call,check_output}` call that receives it as `env=`.
3. Select the function only if that call's argv contains a string constant with
   `kitty_setup.cli`. A bare-name argv is resolved through its assignments in the same function.
4. A selected function complies if `<env>.pop("KITTY_WINDOW_ID", …)` appears **before** the call.

**The classifier was re-run over the tree before trusting the plan's numbers**
(`tmp/h33-minors/02-08/classify.py`). The RED-state run is `classify-red.txt`, and the GREEN run
is `classify-green.txt`:

```
env builders feeding a subprocess: 10
  skipped   _kitty_subprocess.py:58  spawn_kitty  -
  skipped   _kitty_subprocess.py:121  kitten_call  -
  skipped   test_client_socket_discovery.py:50  _spawn_kitty  -
  SELECTED  test_color_normalization_e2e.py:31  _run  pops
  skipped   test_h21_doctor_remote_control.py:51  _spawn_kitty  -
  skipped   test_h21_remote_control_foundation.py:54  _spawn_kitty  -
  skipped   test_h21_remote_control_foundation.py:95  _kitten_ls  -
  SELECTED  test_h25_scene_launcher.py:394  test_my_kitty_scene_launch_cli_creates_three_pane_tab  NO POP   (RED) -> pops (GREEN)
  SELECTED  test_scene_recipe_e2e.py:75  test_my_kitty_scene_launch_named_recipe_creates_three_pane_tab  NO POP   (RED) -> pops (GREEN)
  SELECTED  test_scene_recipe_e2e.py:119  _run_scene_launch  pops   (:122 at GREEN, after the +3 lines above it)
RED:   selected: 4; compliant: 2; non-compliant: 2
GREEN: selected: 4; compliant: 4; non-compliant: 0
```

**Count: 4 selected, as the plan expected.** No tightening was needed. There are **six** skipped
builders, not the "five" the plan's prose mentions. The plan counted by site, but
`test_h21_remote_control_foundation.py` has two builders (`:54` and `:95`). The research's
ten-site inventory matches: 4 + 6 = 10. All six spawn `kitty` or `kitten @` directly.

**Cases** (all in the RED commit):

- `test_env_hygiene_current_tree_cli_env_builders_pop_window_id`: the defect case. It also
  asserts the selection is non-empty, so the rule cannot pass by selecting nothing.
- `test_guard_rule_selects_the_known_cli_env_builders`: over the real tree, the four known CLI
  builders are selected, and the six known spawners are seen and skipped. It asserts a superset
  rather than an exact set, so a new compliant builder does not break it.
- `test_guard_rule_flags_missing_pop`: synthetic source with three functions.
  `dict(os.environ)` with no pop is flagged. `os.environ.copy()` with a bare-name argv that pops
  only after the call is flagged. The compliant function passes.
- `test_guard_rule_ignores_kitty_spawner`: a synthetic function that spawns `kitty` and
  `kitten @` has its two builders seen, and none selected.

**The fix.** `env.pop("KITTY_WINDOW_ID", None)` sits between the env assignments and the
subprocess call, copying `test_color_normalization_e2e.py:33`. Each pop has a two-line comment
naming the hazard. Corrected line references: the h25 builder is at `:394` (not `:393`, which is
the trailing comment line), and its pop landed at `:398`. The `scene_recipe_e2e` builder is at
`:75`. Its pop landed at `:80`, not the `:76` the plan predicted, because the comment and the
`XDG_CONFIG_HOME` assignment come first. That keeps the pattern of placing the pop after all env
assignments. The second builder (`_run_scene_launch`, now `:122`) is unchanged: it pops at `:125`
and deliberately re-injects the id at `:128`. Gate g02 checks both.

## R1.7: prune negative values, before and after

`cli._non_negative_int` parses an int and raises `argparse.ArgumentTypeError` when the value is
negative. It is wired to both `--keep` and `--older-than` (`cli.py:126`, `:134`).
`pruner.prune_by_keep` and `prune_by_age` keep their guards. The file still has exactly two
`raise ValueError` (g07), and `tests/unit/test_pruner.py`'s two library-level `ValueError` cases
pass unchanged.

**Widening beyond D-13's wording:** D-13 names only `--keep`. `--older-than` has the identical
defect three lines away (`pruner.py:37-38`), so both are fixed.

After (`tmp/h33-minors/02-08/neg-after.txt`, same scratch `HOME` method):

```
$ my-kitty prune --backups --keep -1
usage: my-kitty prune [-h] [--backups] [--keep N | --older-than DAYS | --all]
my-kitty prune: error: argument --keep: must be >= 0, got -1
exit=2

$ my-kitty prune --backups --older-than -1
usage: my-kitty prune [-h] [--backups] [--keep N | --older-than DAYS | --all]
my-kitty prune: error: argument --older-than: must be >= 0, got -1
exit=2

$ my-kitty prune --backups --keep 0         -> unchanged: deleted 1 of 1 (scratch), exit=0
$ my-kitty prune --backups --keep abc       -> unchanged: argument --keep: invalid int value: 'abc', exit=2
$ my-kitty prune --backups --older-than x   -> unchanged: argument --older-than: invalid int value: 'x', exit=2
```

Cases in `tests/unit/test_cli.py` (RED commit). They go through the public `cli.main` with
`pytest.raises(SystemExit)`, never through `cli._build_parser()`:

- `test_prune_negative_value_is_an_argparse_usage_error[--keep|--older-than]`: the **real**
  handler, against a scratch `HOME` (`monkeypatch.setenv("HOME", tmp_path)`) holding one backup.
  Asserts exit code **exactly 2**, `usage: my-kitty prune`, `argument <option>`, `-1`, and that
  the backup still exists.
- `test_guard_prune_zero_accepted`, `test_guard_prune_valid_values[keep-5|older_than-30]` and
  `test_guard_prune_non_int[--keep-abc|--older-than-x]` replace `cli_prune` with a recorder, so
  they never list or delete a backup. They check that zero is accepted for both flags, that a
  value reaches the handler as an `int`, unchanged, and argparse's exact invalid-int wording.

## U-1: the teardown pin

`tests/unit/test_harness_teardown.py` builds a `KittySession` without entering it, so nothing is
spawned and no socket directory is created. It passes fake `binaries`. It replaces `_kctl` with
`monkeypatch.setattr(session, "_kctl", …)` and calls the method as
`vars(type(session))["_close_window_then_terminate"](session)`. With `_process` unset, the method
returns right after the remote-control call (`kitty_session.py:321-327`, verb at `:323`, handler
at `:324-325`). The module has 0 pyright errors and no suppression comment.

- `test_teardown_issues_close_window_match_all`: the recorded argv is exactly `[("close-window",
  "--match=all")]`.
- `test_teardown_never_uses_close_os_window`: `kitty_session.py` contains `"close-window",
  "--match=all"`, and neither `close-os-window` nor `close_os_window`.
- `test_teardown_swallows_harness_command_error`: a `_kctl` that raises `HarnessCommandError`
  does not propagate. This is the property that would make a wrong verb invisible, so it is
  pinned rather than only described.

The module docstring records the measurement: kitty 0.49.0, 41 subcommands with `close-tab` and
`close-window` and no `close-os-window`, which is only a mappable action. `close-window
--match=all` exits 0 and kitty exits cleanly with 2 OS windows and 3 windows. The swap would be
silent, and its only symptom would be rising integration wall-clock time.

**This module is green at RED by design.** U-1's correct implementation is no change, so there is
no red run to show. The equivalent is that it would fail on a tree where D-13 had been
implemented literally. `test_teardown_issues_close_window_match_all` and
`test_teardown_never_uses_close_os_window` would both go red.

**Note for `02-09`:** that plan rewrites the `try/except HarnessCommandError: pass` at
`kitty_session.py:322-325` into `contextlib.suppress` (ruff SIM105). The rewrite must keep all
three cases green. They assert the verb and the non-propagation, and `contextlib.suppress`
changes neither. Treat the test as a deliberate constraint on that refactor, not as an obstacle.

## RED state, proven from the RED commit's own tree

Freshness first. Before any test was written, `uv run pytest tests/unit/test_cli.py
--collect-only -q -k 'prune_negative'` returned `no tests collected (32 deselected)`, exit 5.

In the worktree before the RED commit, `-k 'current_tree or prune_negative'` gave `3 failed, 40
deselected`, exit 1. The guards and the teardown pin gave `-k 'guard or teardown'`: `11 passed`.

Gate g16 materialises `7841dde`'s tree through a throwaway index and runs the defect selector
there. The status was 0 after RED and 0 again after GREEN. With an output trailer, and the gate
text unchanged (`gates/g16show.sh`, saved as `tmp/h33-minors/02-08/red-state.txt`):

```
E       AssertionError: these integration env builders run our own CLI without env.pop("KITTY_WINDOW_ID", None) before the subprocess call, so a run from inside a kitty window takes the fill-current-tab branch: ['test_h25_scene_launcher.py:394 (test_my_kitty_scene_launch_cli_creates_three_pane_tab)', 'test_scene_recipe_e2e.py:75 (test_my_kitty_scene_launch_named_recipe_creates_three_pane_tab)']
E           ValueError: --keep must be >= 0, got -1
E           ValueError: --older-than must be >= 0, got -1
FAILED tests/unit/test_integration_env_hygiene.py::test_env_hygiene_current_tree_cli_env_builders_pop_window_id
FAILED tests/unit/test_cli.py::test_prune_negative_value_is_an_argparse_usage_error[--keep]
FAILED tests/unit/test_cli.py::test_prune_negative_value_is_an_argparse_usage_error[--older-than]
3 failed, 40 deselected in 0.11s
--- gate status: 0; pytest exit: 1; N=3 ---
```

**3 failed, 0 passed, 0 errors.** The floor is 3. Each case failed for its defect. The hygiene
rule named exactly the two unfixed integration sites in the RED tree's own `tests/integration/`.
Both prune cases failed because the library `ValueError` escaped `cli.main`, not on setup.

## `make test`

```
======================= 475 passed, 78 skipped in 8.46s ========================
exit=0
```

475 = 461 at `a3573aa` + 14 new: 4 hygiene cases, 7 `test_cli.py` cases (2 negative, 1 zero,
2 valid, 2 non-int) and 3 teardown cases. That is above the floor of 314, with no failure and no
error.

## `make test-integration` for the two modified modules

Gate g13 ran `make test-integration PYTEST_ARGS='tests/integration/test_h25_scene_launcher.py
tests/integration/test_scene_recipe_e2e.py -q'` and exited 0. The transcript is
`tmp/h33-minors/02-08/integration-two-modules.txt` (from `gates/g13show.sh`):

```
..........                                                               [100%]
10 passed in 15.04s
test-integration: pytest exit status 0 (read from the child's status file; compositor exited 0)
--- gate status: 0 ---
```

After the run there was no `$XDG_RUNTIME_DIR/kitti-*` directory and no `cage` process.

**What this run proved and what it did not.** The `02-11` runner scrubs `KITTY_WINDOW_ID`,
`KITTY_LISTEN_ON` and `KITTY_PID`, and gives the run no controlling terminal. So the run proves the
**outside-kitty path by construction**: the two modules still pass with the new pops, from any
shell. `test_scene_recipe_e2e.py`'s deliberate re-injection still ran, because that test sets the
id for its own subprocess. **The inside-kitty path was not exercised.** That needs a human in a
kitty window and cannot be scripted from this session. The orchestrator also forbids touching the
user's live kitty. The static rule covers the inside-kitty path instead: it proves that every env
builder feeding our CLI strips the inherited id before the child starts. The existing
fill-current-tab assertion at `test_scene_recipe_e2e.py:201` (now `:204`) remains the canary.

## `make doctor`

`make doctor` runs the installed `my-kitty`, which is the pre-change binary. No install was run in
this plan. All nine lines passed or skipped, with exit 0:

```
PASS kitty binary: /home/bazzite/.local/bin/kitty -> kitty 0.49.0 created by Kovid Goyal
PASS symlink: /home/bazzite/.local/bin/kitty -> /var/home/bazzite/.local/kitty.app/bin/kitty
PASS desktop entry: /home/bazzite/.local/share/applications/kitty.desktop
PASS config payload: /home/bazzite/.config/kitty/kitty-setup/kitty-setup.conf
PASS sentinel block: present in /home/bazzite/.config/kitty/kitty.conf
PASS parse check: /home/bazzite/.local/bin/kitty +runpy '…' /home/bazzite/.config/kitty/kitty.conf exit=0
PASS bindings: 22 ours, 79 defaults, 0 conflicts
PASS completion: /home/bazzite/.local/share/kitty-setup/my-kitty-completion.bash is current and sourced by the my-kitty block in /home/bazzite/.bashrc
SKIP remote-control: no running kitty
exit=0
```

## Baselines and lint (repo-wide counts must not grow)

Measured with `tmp/h33-minors/02-08/lint.sh <rev>` on `a3573aa`'s materialised tree before any
edit, and with `lint-wt.sh` on the GREEN working tree's tracked files. The GREEN tree was also
re-measured after the commit (see "Post-commit gate results"). The pyright count needs the venv on
`PATH`. Without it, pyright cannot resolve `pytest` and reports 1834. That first reading was
discarded, and both measurements used the venv.

| measure | `a3573aa` | GREEN | delta |
|---|---|---|---|
| `ruff check .` findings | 25 | 25 | 0 |
| `black --check .` files to reformat | 10 | 10 | 0 |
| `bandit -c pyproject.toml -r src` issues | 33 | 33 | 0 |
| `pyright` errors (project config) | 559 | 559 | 0 |
| `vulture src tests` lines | 15 | 15 | 0 |
| `pyright tests/unit/test_cli.py` | 31 | 31 | 0 (ceiling ≤ 31) |
| `pyright` on the two new modules | n/a | **0 errors** | new files, clean |
| `pyright src/kitty_setup/cli.py` | 0 | 0 | 0 |

Touched files (`touched-lint.txt`). Every non-clean result was checked against `a3573aa`'s
version of the same file (`preexisting.sh` → `preexisting.txt`):

- The two new modules are clean under ruff (`All checks passed!`), black (`2 files would be left
  unchanged`) and pyright (`0 errors`). No suppression comment was added anywhere
  (`git diff a3573aa -- src tests | rg '^\+.*(noqa|type: ignore|pyright: ignore)'` exits 1).
- `src/kitty_setup/cli.py`: black is clean and bandit finds nothing. ruff reports only the
  **pre-existing** `RUF001` (EN DASH in `"(0.0–1.0)"`), now at `:338`. It was at `:321` at
  `a3573aa`, and moved by the 17 lines added above it. `02-09` owns it, and no second RUF001 was
  added. vulture's four `completer` findings are the same four as at `a3573aa` (`:197,250,385,404`
  → `:214,267,402,421`).
- `tests/unit/test_cli.py`: ruff is clean. black "would reformat" it, but it did so at `a3573aa`
  too, and every black hunk (`@@ -335`, `-373`, `-407`, `-455`) sits in pre-existing tests below
  the new cases.
- `tests/integration/test_h25_scene_launcher.py`: the pre-existing `F401 json imported but
  unused` at `:14` and the pre-existing black drift are both present at `a3573aa`. The six black
  hunks are the same, and the last one moved by 3 lines. `test_scene_recipe_e2e.py` is clean
  under ruff and black.

## Gates

Every `<automated>` gate was extracted verbatim from `02-08-PLAN.md` (HTML-unescaped) into
`tmp/h33-minors/02-08/gates/gNN.sh` by `extract_gates.py`. The only addition is a `cd <worktree>`
line. The runs were logged to `gates.log` by `rungates.py`. **No gate was changed.** The shell
guard blocks one-liners that mention `git`, so every gate ran from its script file. Where an output
transcript was needed (`g13show.sh`, `g16show.sh`), a copy with a trailing `printf "$OUT"` line was
run, and the gate text itself was not edited.

| Gate | What | When | Exit |
|---|---|---|---|
| g01 | T1: both integration files pop `KITTY_WINDOW_ID` | pre-edit; after RED; pre-GREEN | 1 (expected); 1 (expected); **0** |
| g02 | T1: `scene_recipe_e2e` has exactly 2 pops and keeps the re-injection | pre-edit; pre-GREEN | 1 (expected); **0** |
| g03 | T1: rule module in `tests/unit/`, not `tests/integration/`, AST-based, names `kitty_setup.cli` | pre-edit; after RED; pre-GREEN | 1 (expected); **0**; **0** |
| g04 | T1: hygiene module passes | after RED; pre-GREEN | 1 (expected at RED); **0** |
| g05 | T1: both hypothesis dirs extended (`close-os-window`, `--keep -1`) | step 0; after RED; pre-GREEN | **0**; **0**; **0** |
| g06 | T2: `ArgumentTypeError` present, validator wired exactly twice | pre-edit; pre-GREEN | 1 (expected); **0** |
| g07 | T2: `pruner.py` keeps exactly 2 `raise ValueError` | pre-edit; pre-GREEN | **0**; **0** |
| g08 | T2: `prune_negative` present, `-k 'negative or keep or older'` passes | after RED; pre-GREEN | 1 (expected at RED); **0** |
| g09 | T3: teardown module names `close-window`, `0.49.0`, `HarnessCommandError` | after RED; pre-GREEN | **0**; **0** |
| g10 | T3: harness has `close-window` and no `close-os-window` | pre-edit; after RED; pre-GREEN | **0**; **0**; **0** |
| g11 | T3: teardown module passes | after RED; pre-GREEN | **0**; **0** |
| g12 | T3: `make test` ≥ 314 passed, no fail or error | pre-GREEN | **0** (475 passed) |
| g13 | T3: `make test-integration` on the two modules | pre-GREEN | **0** (10 passed) |
| g14 | T3: topology (one `test(02-08)`, one `feat(02-08)`, RED is an ancestor of GREEN, 2 from RED onward) | after GREEN | **0** |
| g15 | T3: RED is tests-only, has the three unit modules, has neither integration file | after RED; after GREEN | **0**; **0** |
| g16 | T3: RED tree gives ≥ 3 failed, none passed or errored | after RED; after GREEN | **0** (N=3); **0** |
| g17 | T3: GREEN has no `tests/unit/` file and both integration fixes | after GREEN | **0** |
| g18 | T3: GREEN has the SUMMARY and not `harness/kitty_session.py` | after GREEN | **0** |

`<verification>` item 10, pre-GREEN (`touched-lint.sh`): the literal `uv run ruff check
src/kitty_setup/cli.py tests/unit/test_integration_env_hygiene.py
tests/unit/test_harness_teardown.py && uv run black --check …` exits **1**. The only finding is
the pre-existing `RUF001` at `cli.py:338`, which the item itself calls out ("`cli.py:321` already
carries a RUF001 that `02-09` owns; do not add a second"). No second one was added. The pyright
half passes: `0 errors` on the two new modules, and `31 errors` on `test_cli.py`, which is within
the ≤ 31 ceiling.

## Deviations from Plan

**1. [Rule 1 — plan action would change the standard message] A non-integer is re-raised as
`ArgumentTypeError`, instead of letting `int()`'s `ValueError` propagate.** The plan's action says
to "let the int conversion's own `ValueError` propagate so argparse produces its standard
invalid-int message". argparse builds that message from the `type=` callable's `__name__`. With
the error propagating, the message would read `invalid _non_negative_int value: 'abc'`, not
`invalid int value: 'abc'`. The validator therefore catches the `ValueError` and raises
`ArgumentTypeError(f"invalid int value: {raw!r}")`, which argparse prints verbatim after
`argument <option>:`. The output is byte-identical to `type=int`'s (`neg-before.txt` versus
`neg-after.txt`), and `test_guard_prune_non_int` pins the exact wording. The plan's intent, the
standard invalid-int message and exit 2, is met. The helper is named `_non_negative_int`, one of
g06's two accepted spellings, so no gate pattern changed.

**2. [Evidence] The U-1 evidence was re-measured, not re-read.** The plan says to extend
`tmp/h32-color-forms/` with the verb list, the two-OS-window comparison and the
unknown-subcommand error, "since that is where the research recorded it". The research's files
(`live-evidence-3.txt`, `live-evidence-4-verbs.txt`) exist in no checkout's `tmp/`. The
measurement was re-run headless through `make test-integration`, using a temporary probe file that
was removed afterwards, and the results match the research line for line.

**3. [Count note, no tightening] The rule skips six builders, not five.** See the R1.6 section.
Four are selected, as the plan expected, so the filter was not changed.

**4. [Line note] The `scene_recipe_e2e` pop is at `:80`, not `:76`.** It follows the
`XDG_CONFIG_HOME` assignment and a two-line comment, matching the plan's instruction to copy the
placement of `test_color_normalization_e2e.py:33` ("between the env assignments and the subprocess
call").

**5. [Recorded, not a gate change] Verification item 10's literal ruff command exits 1 on a
pre-existing finding.** The finding is the RUF001 at `cli.py:338`, as described above. It is a
`<verification>` prose item, not an `<automated>` gate, and it names the finding itself. Neither
`02-08-PLAN.md` nor `02-VALIDATION.md` was edited.

No gate was defective, so `02-08-PLAN.md` and `02-VALIDATION.md` were not edited.

## Known limits and notes

- The inside-kitty path is covered by the static rule, not by a run (see above).
- `make doctor` ran the installed pre-change binary. `doctor` does not read either changed code
  path.
- Hard-rule compliance:
  - No kitty window reached the desktop. Every kitty in this plan ran inside the runner's
    headless cage, and no `kitten @` call ran without an explicit `--to` to a probe or harness
    socket.
  - The real `~/.config` and rc files were not written.
  - The prune runs used scratch `HOME`s, and the prune unit cases use `tmp_path` or a recorder.
  - After every run: no `$XDG_RUNTIME_DIR/kitti-*` directory, no `cage` process, no probe kitty.

## Known Stubs

None.

## Threat Flags

None new.

- T-2-29 is mitigated: both pops are in place, and the rule is in the unit tree.
- T-2-30 is mitigated: the argparse `type=` validator is in place, and the library guards stay.
- T-2-31 is mitigated: there is no harness change, and the pin covers both the verb and the
  non-propagation.
- T-2-32 is mitigated: the pin exists before `02-09`'s refactor.
- T-2-SC: no package was installed. `uv sync` created the worktree venv from the existing lock.

## Post-commit gate results

These gates ran against the first GREEN commit, `edf4a4e` (`gates.log`, "# after GREEN
edf4a4e"). All exited **0**:

- g14: the topology gate.
- g15: RED is tests-only, has the three unit modules and neither integration file.
- g16: the RED tree gives N=3 failed, with nothing passed or errored.
- g17: GREEN has no `tests/unit/` path and has both integration fixes.
- g18: GREEN has the SUMMARY and not `harness/kitty_session.py`.
- Re-runs of g01, g02, g03, g04, g05, g06, g07, g08, g09, g10, g11 and g12 (`make test`: 475
  passed).

`lint.sh edf4a4e` on the committed tree: ruff 25, black 10, bandit 33, pyright 559, vulture 15.
That is identical to `a3573aa`.

For `edf4a4e`, `git diff-tree` lists `A .planning/phases/02-defect-remediation/02-08-SUMMARY.md`,
`M src/kitty_setup/cli.py`, `M tests/integration/test_h25_scene_launcher.py` and `M
tests/integration/test_scene_recipe_e2e.py`. For `7841dde` (RED) it lists `A
tests/unit/test_harness_teardown.py`, `A tests/unit/test_integration_env_hygiene.py` and `M
tests/unit/test_cli.py`. Neither commit contains a deletion. `git rev-list --count
a3573aa..HEAD` = 2.

GREEN was then amended once, while unpushed, to fill in this section and the Self-Check. The
amend changes only this file. The commit-dependent gates g14 to g18 were re-run on the amended
SHA ("# after amend" in `gates.log`).

## Self-Check: PASSED

- Found: this SUMMARY, `src/kitty_setup/cli.py`, the two integration files, the three unit
  modules, `tmp/h32-color-forms/{repro.md,u1-live-before.txt,u1-verbs-before.txt}` and
  `tmp/h33-minors/{repro.md,02-08/neg-before.txt,02-08/neg-after.txt}`. Gate g05 exits 0.
- Found commits: `7841dde` (RED) and the GREEN commit (`feat(02-08)`, the current `HEAD`).
- Exactly two `(02-08)` subjects exist from RED onward (g14).
- No `$XDG_RUNTIME_DIR/kitti-*` directory, no `cage` process and no probe kitty is left. No kitty
  window reached the desktop.
- `core.hooksPath` = `tools/hooks`, unchanged.

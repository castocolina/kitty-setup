---
phase: 02-defect-remediation
plan: 11
subsystem: testing
tags: [integration, headless, cage, wayland, pytest, makefile, unix-socket, R0.13]
status: complete
requires: []
provides:
  - "`make test-integration`: all of tests/integration/ headless under cage, pytest's own verdict out"
  - "kitty_setup.harness.integration_runner: main(argv), resolve_compositor, build_pytest_args, headless_env, run, --child"
  - "KittySession control socket independent of checkout depth (short 0700 dir under $XDG_RUNTIME_DIR)"
affects: [02-02, 02-04, 02-06, 02-08, 02-09, 02-10, 02-03]
actuals:
  tokens: 16000
  tasks: 3
  commits: 2
plan_head_before: 792ef8b8012ae9adfc35b8a149ec6a157102e393
tech-stack:
  added: []
  patterns:
    - "Verdict through a status file written inside the wrapper; the wrapper's exit status is recorded, never returned"
    - "Compositor in its own session (start_new_session=True); process group probed with killpg(pgid, 0) and terminated on every exit path"
    - "Unix sockets live in a mkdtemp 0700 dir under $XDG_RUNTIME_DIR, never under the repo, so sun_path's 107 usable bytes hold at any checkout depth"
key-files:
  created:
    - src/kitty_setup/harness/integration_runner.py
    - tests/unit/test_integration_runner.py
    - tests/unit/test_kitty_session_socket.py
  modified:
    - src/kitty_setup/harness/kitty_session.py
    - Makefile
    - pyproject.toml
    - .claude/conventions.md
    - docs/agent-iteration.md
key-decisions:
  - "Runner is a harness module (uv run python -m kitty_setup.harness.integration_runner) behind a one-line Makefile target; sanctioned by the AGENTS.md Stack exception added in 792ef8b"
  - "cage's exit status is never returned; pytest's status comes only from the child's status file"
  - "A process left in the compositor's group after a grace period is a failure (70), not a warning"
  - "SIGTERM and SIGHUP are turned into an exception in main so the finally-path kills the group (Rule 2 addition)"
  - "KittySession's socket moves out of <repo>/tmp/sessions/<id>/ into a short private dir under $XDG_RUNTIME_DIR (fallback tempfile.gettempdir()); logs, config and HOME stay under the session dir"
duration: ~55min (two passes)
completed: 2026-09-24
---

# Phase 2 Plan 11: Headless integration runner, `make test-integration`, and a depth-independent kitty socket — Summary

**`make test-integration` runs `tests/integration/` headless under cage and returns pytest's own
status, which it reads from a status file the child writes. It exits 69 and prints "NOT run"
when no compositor exists. A missing status, a timeout or a leftover process gives 70. The
compositor's whole process group is killed on every exit path. KittySession's control socket
now sits in a 34-byte path under `$XDG_RUNTIME_DIR` instead of a 114-byte path under the repo.
The whole suite therefore runs from a phase worktree: measured from this `.claude/worktrees/`
checkout, `70 passed in 43.68s`, with no cage, kitty or socket directory left behind.**

## Pre-work state

- The harness worktree was branched from `origin/master`, which has no `.planning/`. It was
  reset to `gsd/phase-02-defect-remediation`, first at `a200767`. For this rework it was reset
  again to the new phase tip `792ef8b`, and both commits were rebuilt on top of it
  (`plan_head_before`). `792ef8b` touches none of this plan's files: it changes only
  `AGENTS.md`, `REQUIREMENTS.md`, `ROADMAP.md` and `02-CONTEXT.md`.
- `core.hooksPath` **before**: `/var/home/bazzite/git/personal/kitty-setup/tools/hooks`
  (absolute, the known drift). `make hooks` → **after**: `tools/hooks`. It was still
  `tools/hooks` at the start and at the end of the rework.
- Worktree root: `/var/home/bazzite/git/personal/kitty-setup/.claude/worktrees/agent-af9886451355048d1`,
  **84 bytes**.

## Runner route and the Stack decision

The runner is a harness module invoked as
`uv run python -m kitty_setup.harness.integration_runner $(PYTEST_ARGS)`, behind a one-line
Makefile target. It is not a `my-kitty` subcommand. The plan flagged this as the planner's
call. A cross-AI reviewer rated it HIGH against the letter of `AGENTS.md` "Stack" as the rule
then stood ("anything beyond them is a subcommand under `src/kitty_setup/cli.py`"). The rule
was stale rather than the plan, so the coordinator amended it in **`792ef8b`**. It now allows
developer-only tooling that is not part of the installed product to be "a Python module under
`src/kitty_setup/harness/` run as `uv run python -m kitty_setup.harness.<name>` — today, only
the integration-test runner". The reason is that a `my-kitty` subcommand would hand end users
a pytest runner for a `tests/` tree they do not have. The Makefile clause now also names "such
a harness module" as a dispatch target. Nothing in the runner changed because of this.

## The socket fix (added in the rework)

**Why it belongs here.** `AGENTS.md`'s git policy runs every phase in its own worktree.
`KittySession` put its control socket at `<repo>/tmp/sessions/s<10 hex>/sock`, so the path
grew with checkout depth. `sockaddr_un.sun_path` is 108 bytes on Linux, including the NUL,
which leaves 107 usable. From this worktree the path was 114 bytes. kitty logged
`Invalid listen_on=unix:…/sock, ignoring`. The 4 KittySession tests (`test_h01_cwd.py` ×3 and
`test_h02_clear.py`) failed with `HarnessStartupError: socket … not ready within 5.0s`, and
`make test-integration` reported `4 failed, 66 passed` from the place every phase actually
runs. R0.13 was therefore not met until this was fixed.

**Research: what assumes the socket is inside `session_dir`.** I re-read
`src/kitty_setup/harness/kitty_session.py` and searched the repo (excluding `.planning/`) for
`socket_path|session_dir|tmp/sessions`. Only `kitty_session.py` itself matched, plus an
unrelated `socket_path` local in `scenes/_client.py`. Within the module, three places depended
on the layout:

- `__enter__` placed the socket at `session_dir / "sock"`.
- `__exit__` removed the socket only as a side effect of `rmtree(session_dir)`. It kept the
  socket whenever `KEEP_SESSIONS=1` was set or an exception occurred.
- The startup-failure path in `__enter__` (the old `except HarnessStartupError`) left the
  session dir, and the socket with it, in place.

No test or caller reads `.socket_path` or `.session_dir`. The two integration consumers
(`test_h01_cwd.py` and `test_h02_clear.py`) only drive the session through its methods.

**Experiment: measured before choosing.** `uv run python tmp/h35-headless-integration/socket_probe.py`
from this worktree printed:

```
repo root           : /var/home/bazzite/git/personal/kitty-setup/.claude/worktrees/agent-af9886451355048d1 (84 bytes)
old socket path     : …/agent-af9886451355048d1/tmp/sessions/s0123456789/sock (114 bytes; sun_path usable = 107)
mkdtemp under /run/user/1000: /run/user/1000/kitti-57a5loc2/sock (34 bytes, mode 0o700)
mkdtemp under /tmp          : /tmp/kitti-4421irs4/sock (24 bytes, mode 0o700)
```

**Decision and change** (`kitty_session.py`):

- `_make_socket_dir()` calls `tempfile.mkdtemp(prefix="kitti-", dir=…)` under
  `$XDG_RUNTIME_DIR` when that is set and is a directory. Otherwise it falls back to
  `tempfile.gettempdir()`, which is `/tmp` here since `TMPDIR` is unset. `mkdtemp` creates the
  directory with mode 0700. I used `gettempdir()` rather than a literal `"/tmp"` because a
  literal would add a ruff S108 finding, which could only be silenced with a forbidden `noqa`.
- The socket is `<socket_dir>/sock`. Config, log and `home/` stay under
  `<repo>/tmp/sessions/<id>/`, so the evidence stays in the repo's `tmp/`.
- `SOCKET_PATH_BUDGET = 107`. A path longer than that raises `HarnessStartupError` naming the
  budget and the variables that fix it. Before, kitty silently ignored the listen address.
- `_remove_socket_dir()` runs on every teardown, whatever `KEEP_SESSIONS` says, because the
  directory holds no evidence. It also runs on any failure inside `__enter__`. The old path
  caught only `HarnessStartupError`; the new one catches `BaseException` and re-raises, so a
  spawn failure or an interrupt during startup leaves no stale socket directory either.
  `KEEP_SESSIONS` still decides whether the session dir is kept.

**Measured after, from this worktree:** the socket path is **34 bytes**
(`/run/user/1000/kitti-XXXXXXXX/sock`), down from **114**. Inside cage, `XDG_RUNTIME_DIR` is
inherited as `/run/user/1000`, and `headless_env` keeps it. After every run below,
`ls -d /run/user/1000/kitti-* /tmp/kitti-*` found nothing (exit 2).

**Known limit.** If a KittySession's owner is SIGKILLed, its `__exit__` never runs, so a
socket directory can outlive it. This happens, for example, when the runner kills the group
on a timeout. The directory is empty of evidence, and `$XDG_RUNTIME_DIR` is cleared at logout.
The timeout probe below left none, but the risk exists in principle.

## What landed

- `src/kitty_setup/harness/integration_runner.py` (349 lines). Constants
  `COMPOSITORS=("cage",)`, `SCRUBBED_VARIABLES`, `HEADLESS_VARIABLES`, `INTEGRATION_ROOT`,
  exit codes `64`, `69` and `70`, `RUN_TIMEOUT_S=600`, and `LEFTOVER_GRACE_S=5.0`. Functions
  `resolve_compositor`, `build_pytest_args`, `headless_env`, `run`, the `--child` mode and
  `main`. It does not import pytest and has no suppression comments.
- `src/kitty_setup/harness/kitty_session.py`: the socket fix above.
- `tests/unit/test_integration_runner.py`: 25 cases, hermetic. The fake compositors are Python
  scripts, and the child is a real pytest run.
- `tests/unit/test_kitty_session_socket.py`: 5 cases, no kitty spawned.
  - From a sessions root 217+ bytes deep, the socket stays ≤ 107 bytes.
  - It sits under `$XDG_RUNTIME_DIR` with mode 0700.
  - It is removed on teardown with `KEEP_SESSIONS` set to 0 or 1, and the session dir follows
    `KEEP_SESSIONS`.
  - It is removed on a startup failure.
- `Makefile`:
  - `test-integration` is in `.PHONY` after `test`.
  - A help line sits under `test`, whose own help line no longer advises
    `KITTI_INTEGRATION=1`.
  - The target is one recipe line.
  - `test:`'s recipe is byte-identical.
  - `clean:` moved from `:27` to `:28`.
- `pyproject.toml`: one per-file entry, `"src/kitty_setup/harness/integration_runner.py" = ["S603"]`,
  with a rationale comment.
- `.claude/conventions.md:66` and `docs/agent-iteration.md` step 7 name the headless target.
- `tmp/h35-headless-integration/` holds `repro.md`, `run.py`, `expected.json`, `actual.json`
  and `socket_probe.py`. It is gitignored.

## Hypothesis ordering, stated plainly

The reviewer flagged that `tmp/h35-headless-integration/` was created after the
implementation. That is true of the **directory**. The substance of the hypothesis was
measured before this plan existed:
- the headless cage mechanism was measured at `1eb86bd` (70 passed in 43.81s) and at
  `bde7589` (43.89s);
- it is written into R0.13's own text in `.planning/REQUIREMENTS.md`;
- the planning session measured it again at `bbed580` through a scratch prototype (43.66s),
  together with cage's exit-status behaviour.

This plan materialised that evidence as `repro.md` and `run.py` late, after the runner was
written, rather than before. The socket fix did follow the order: `socket_probe.py` measured
both candidate locations before `kitty_session.py` was changed.

## RED transcript (commit `test(02-11)`, rebuilt on `792ef8b`)

`uv run pytest tests/unit/test_integration_runner.py tests/unit/test_kitty_session_socket.py -q --tb=line -rfE -p no:cacheprovider`
→ exit 1, **`29 failed, 1 passed in 0.06s`**. The failures break down as follows:

- **22 fail with `ModuleNotFoundError: No module named 'kitty_setup.harness.integration_runner'`.**
  This is the runner missing. The module is imported inside each test, so each case fails on
  its own and the file does not collapse into one collection error.
- **2 fail on the missing Makefile target.** The messages are `test-integration: defined 0 times`
  and `assert 'test-integration' in ['.PHONY:', …]`.
- **5 socket cases fail on the old layout:**
  - `assert 217 <= 107` twice: `socket_path_fits_sun_path_from_a_deep_checkout` and
    `…removed_when_startup_fails`.
  - The socket dir equals the session dir, twice: the teardown case, for `keep` 0 and for 1.
  - The socket dir's parent is `…/tmp/sessions`, not the runtime dir, once.
- **The single pass is `test_makefile_test_recipe_is_unchanged`.** It guards that `test:` stays
  `@uv run pytest tests/` and must be green before and after.

## Whole suite, from inside this worktree

`make test-integration PYTEST_ARGS='-q'` from
`/var/home/bazzite/git/personal/kitty-setup/.claude/worktrees/agent-af9886451355048d1` →
make exit 0, wall time 43.92s:

```
......................................................................   [100%]
70 passed in 43.68s
test-integration: pytest exit status 0 (read from the child's status file; compositor exited 0)
```

The plan's task 3 gate, run verbatim from the worktree, exits 0: at least 70 passed, no
failed or error line, an unchanged kitty PID set, and no cage.

For comparison, before the socket fix the same checkout gave make exit 2, with
`4 failed, 66 passed in 61.51s (0:01:01)`. The 4 were the KittySession cases, each failing
with the socket-path `HarnessStartupError`.

## Tracer from the worktree

`make test-integration PYTEST_ARGS='tests/integration/test_h01_cwd.py -q'` → make exit 0,
`3 passed in 0.84s`, closing line `pytest exit status 0 (… compositor exited 0)`. Before the
fix this was `3 failed in 15.09s` from the same path.

## No-compositor path on the real host

`env PATH=tmp/h35-headless-integration/no-compositor-bin /usr/bin/make test-integration PYTEST_ARGS=-q`
(the bin dir holds only a `uv` symlink) → **make exit 2, runner exit 69**:

```
test-integration: FAILED — no nested compositor found (looked for: cage). The integration suite was NOT run; this is a failure, not a skip.
test-integration: To fix: install cage, or run on a host that has a nested compositor.
make: *** [Makefile:39: test-integration] Error 69
```

## Process-leak proof

The check was `ps -eo pid,cmd | rg -i '(^| |/)cage( |$)|kitty.app/bin/kitty '`, excluding the
`rg` line itself, plus `pgrep -x cage` (exit 1) and `pgrep -x kitty` (empty). It found
**0 processes** after every run on each path:

- **Success.** The whole suite and the tracer, from the worktree.
- **Failure.** Before the fix, the worktree run with 4 real test failures: pytest's 1
  propagated. After the fix, `PYTEST_ARGS='tests/integration/test_h02_clear.py -q -k no_such_case'`:
  pytest's 5 propagated, `3 deselected`, make exit 2.
- **Timeout.** `uv run python tmp/gates/timeout_probe.py` from the worktree calls
  `run(cage, ["tests/integration", "-q"], timeout_s=10.0)`. It returned **70** after 41 tests
  had passed, with the message
  `test-integration: FAILED — the run hit its 10-second timeout; the compositor's process group was killed and pytest's verdict is unknown.`
  and the compositor log's path and tail. The kitty instances that were mid-test died with
  the group, because the harness spawns kitty without `setsid`.
- **Unit tests.** The leftover, timeout, Ctrl-C and SIGTERM cases each assert that the fake
  compositor and its sleeper are gone. No `time.sleep(60)` sleeper survived the suite.

No `kitti-*` socket directory remained in `/run/user/1000` or `/tmp` after any of these runs.

## cage's exit status, and why the runner ignores it

`cage-0.3.1-1.fc44`. It passes a normal child exit through: the planning session measured
`exit 7` → 7, and every closing line above reads `compositor exited <pytest's status>`. **The
runner still never returns it.** No cage contract guarantees it. A signalled child or a
compositor that dies yields the compositor's own status. Another version or compositor may
differ. And a wrapper that happens to pass the status through today is the
error-inverting-gate trap.

The status file is the only channel. Two unit cases pin this:
- `test_always_zero_compositor_cannot_turn_a_failure_into_a_pass`: a fake compositor that
  always exits 0, around a failing child, and `run` returns pytest's 1.
- `test_missing_status_file_is_a_runner_failure_never_a_pass`: no status file gives 70.

## Environment scrub, and what it means for D-10

The runner removes `WAYLAND_DISPLAY`, `WAYLAND_SOCKET`, `DISPLAY`, `KITTY_LISTEN_ON`,
`KITTY_WINDOW_ID`, `KITTY_PID` and `KITTY_PUBLIC_KEY`. It sets `WLR_BACKENDS=headless`,
`WLR_LIBINPUT_NO_DEVICES=1` and `KITTI_INTEGRATION=1`, and keeps `XDG_RUNTIME_DIR`, which the
socket fix needs. It also sets `stdin=DEVNULL` and `start_new_session=True`, so there is no
controlling terminal. All 70 tests passed under exactly these settings.

The consequence is that D-10's inside-kitty path (`02-08`) cannot be reproduced through this
runner. `02-08`'s unit-tree static rule stays its guard.

## Leftover-process policy

After the compositor exits, the runner waits up to `LEFTOVER_GRACE_S` (5 s) for the process
group to empty. It then sends SIGTERM, and SIGKILL after 2 s. If anything had to be
terminated, it reports `processes were left behind … they were terminated` and exits 70,
even when pytest passed. The full run needed no termination: its exit was 0 and no leftover
line was printed.

## Ruff on the runner, before and after the S603 entry

Before, after fixing N818 and E501 in the module itself, ruff reported `S603` twice at
`integration_runner.py:237` (Popen) and `:296` (the `--child` subprocess.run):
`Found 2 errors.` After: `All checks passed!`

`kitty_session.py` shows the same ruff (2 × SIM105), pyright (1, `reportUnnecessaryComparison`
in `launch`), bandit (B108 medium at the `XDG_RUNTIME_DIR` fallback line) and vulture findings
before and after the fix. All of them are pre-existing, out of this plan's scope, and none
was added.

## `make test`, `make doctor`, pyright

- `make test` → exit 0, `344 passed, 70 skipped in 8.06s`. That is 314 plus 25 runner cases
  plus 5 socket cases, and the integration items are still skipped.
- `make doctor` → exit 2 (Error 1 from `my-kitty doctor`). The only failure is
  `FAIL completion: register-python-argcomplete not on PATH`, with `SKIP remote-control`. This
  is R1.1 (waves 2–3), as expected.
- `uv run pyright` over the whole repo: `571 errors`, the baseline, unchanged. The three new
  test/runner files have 0.

## `tmp/h35-headless-integration/run.py`, verbatim output (from the worktree, KittySession module)

`uv run python tmp/h35-headless-integration/run.py tests/integration/test_h01_cwd.py` → exit 0:

```
...                                                                      [100%]
3 passed in 0.83s
test-integration: pytest exit status 0 (read from the child's status file; compositor exited 0)
test-integration: FAILED — no nested compositor found (looked for: cage). The integration suite was NOT run; this is a failure, not a skip.
test-integration: To fix: install cage, or run on a host that has a nested compositor.
make: *** [Makefile:39: test-integration] Error 69
h35: ok   one_module.make_exit
h35: ok   one_module.pytest_passed>=min
h35: ok   one_module.failed_or_error
h35: ok   one_module.cage_left
h35: ok   no_compositor.make_exit_nonzero
h35: ok   no_compositor.runner_exit_69
h35: ok   no_compositor.says_no_nested_compositor
h35: ok   no_compositor.says_not_run
h35: ok   no_compositor.passed_token
h35: actual.json written; GREEN
```

## Gates (run verbatim from this worktree, each saved to a file because the harness rejects compound shell lines)

| Gate | Result |
|------|--------|
| T1 existence (module, `main`, `start_new_session=True`, `--child`, target, dispatch) | exit 0 |
| T1 unit, `-k 'selector or headless_env or propagates or makefile'` | exit 0 |
| T1 tracer on `test_h01_cwd.py` | exit 0 (`3 passed`) |
| T1 `pgrep -x cage` absent | exit 0 |
| T2 unit, `-k 'no_compositor or … or forge'` | exit 0 |
| T2 no-compositor real host | exit 0 (runner 69, make 2) |
| T3 whole suite (≥70, no failed, kitty PID set unchanged, no cage) | **exit 0 (`70 passed`)** |
| T3 `make test` (recipe unchanged, ≥314 passed, ≥70 skipped) | exit 0 (`344 passed, 70 skipped`) |
| T3 Makefile shape and `make help` | exit 0 |
| T3 ruff, black, pyright, vulture and `bandit -ll` on the runner and its test | exit 0 |
| T3 no suppression, S603 entry with rationale | exit 0 |
| T3 docs | exit 0 |
| T3 `tmp/h35-headless-integration/` artefacts | exit 0 |
| T3 topology, RED tests-only, GREEN contents (commit-dependent) | run after the GREEN commit; results are in the executor's handoff |

The new socket test file also passes ruff and black and has 0 pyright errors. Bandit at low
severity reports B404 and B603 ×2 on the runner, which are left to `02-10`'s `skips` policy.

## Deviations from Plan

1. **[Rule 3, blocking] Socket-path fix in `kitty_session.py` plus a new test module.** This
   was not in the plan's file list. The coordinator folded it in because, without it,
   `make test-integration` cannot pass from a phase worktree (see above). It lives in both
   commits: RED holds `tests/unit/test_kitty_session_socket.py`, and GREEN holds the harness
   change.
2. **[Rule 2] SIGTERM and SIGHUP cleanup in `main`.** A runner killed by CI or by a closed
   terminal would otherwise skip `finally` and orphan cage and kitty.
   `test_leftover_group_is_killed_when_the_runner_is_terminated` forks `main`, sends SIGTERM,
   and asserts exit 143 with the fake compositor's group gone.
3. **[Rule 1] A pytest killed by a signal.** A negative status in the status file gives 70
   rather than a negative exit.
4. **Extra runner cases beyond the behaviour list:** a `::node` selector, extra outside-root
   selectors, `--child` propagation, an absolute `resolve_compositor`, and a Ctrl-C case named
   `leftover_…` so task 2's selector covers it.
5. **STATE.md and ROADMAP.md were not updated.** The coordinator integrates this branch
   itself. No plan or validation file is in either commit, because a planner is editing those
   concurrently.

## Deliberately untouched

`README.md:40-41` and `:209` are left to Phase 8 / R6.1. They are still true.

## Known Stubs

None.

## Threat Flags

| Flag | File | Description |
|------|------|-------------|
| threat_flag: file-access | src/kitty_setup/harness/kitty_session.py | Control sockets now live in `mkdtemp` 0700 dirs under `$XDG_RUNTIME_DIR` (itself 0700 per XDG), not in the repo; owner-only, removed on teardown and on startup failure |

## Self-Check: PASSED

- Present: `src/kitty_setup/harness/integration_runner.py`, `tests/unit/test_integration_runner.py`,
  `tests/unit/test_kitty_session_socket.py`, `src/kitty_setup/harness/kitty_session.py`, and this SUMMARY.
- The RED commit's parent is `792ef8b`, and GREEN is RED's child.

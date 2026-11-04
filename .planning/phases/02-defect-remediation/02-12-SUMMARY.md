---
phase: 02-defect-remediation
plan: 12
subsystem: config
tags: [kitty.conf, sentinel-block, audit-hook, integration-sandbox, tdd, surrogateescape]
type: tdd

requires:
  - phase: 02-defect-remediation
    provides: plans 02-05 onward (kitty.conf sentinel block, uninstall, doctor parse check)
provides:
  - kitty.conf lifecycle fixes: restore on every failure path, marker-free backup selection, non-UTF-8 conf bytes preserved, parse-check failures mapped to ConfigUpdaterError, commit-step warning instead of failure
  - unit-tree host-state guard (sys.addaudithook) that fails any unit test reaching real HOME, XDG_RUNTIME_DIR or the real kitty binary
  - integration HOME sandbox (autouse fixture) and a sandbox case that refuses to spawn kitty when not sandboxed
affects: [02-13, 02-14, 02-15, phase-close install]

actuals:
  tokens: 13630      # chars/4 over added lines vs RED^ (tracked diff 52618 chars + untracked conftest 1902), SUMMARY excluded
  tasks: 3
  commits: 2         # RED test(02-12) and GREEN feat(02-12), counted at phase close

tech-stack:
  added: []
  patterns:
    - "sys.addaudithook guard with prefix-form path comparison and dir_fd resolution via /proc/self/fd, failing closed on unreadable context"
    - "conf writes wrapped so that any failure after the first write restores the user's kitty.conf from the backup"
    - "text I/O on the user's conf uses errors=surrogateescape so non-UTF-8 bytes round-trip"

key-files:
  created:
    - tests/unit/conftest.py
    - tests/unit/test_unit_hermeticity.py
    - tests/unit/test_makefile_clean.py
    - tests/integration/conftest.py
    - tests/integration/test_home_sandbox.py
  modified:
    - src/kitty_setup/config_updater.py
    - Makefile
    - pyproject.toml
    - tests/unit/test_config_updater.py
    - tests/unit/test_doctor.py
    - tests/unit/test_kitty_session_env.py

key-decisions:
  - "Restore kitty.conf on every failure path after the first write (copy the backup back, or delete the file when install created it). Rejected: restoring only on parse rejection, which leaves the conf changed when the check cannot run."
  - "Uninstall selects the newest backup that carries no marker line. Rejected: taking the newest backup unconditionally, which can restore a block-bearing file and re-inject our block."
  - "Conf text I/O uses errors=surrogateescape. Rejected: decoding as Latin-1, which would rewrite the user's bytes. Kitty's own load_config accepts such a file (measured)."
  - "The commit step (removing the previous payload) warns on OSError and keeps the payload instead of failing the install after the conf was already accepted (IN-04)."
  - "The unit guard fails closed: an unreadable audit context is a hit, not a pass. Path comparison uses prefix forms (_forms) so symlinked and alias paths to HOME are caught; dir_fd arguments are resolved through /proc/self/fd."
  - "The integration sandbox is an autouse fixture that points HOME, the four XDG dirs, HISTFILE and PATH at tmp_path. The sandbox case refuses to spawn kitty unless every one of those resolves under the pytest base temp."

patterns-established:
  - "Host-state guard: an audit hook records any unit-test access to real HOME, XDG_RUNTIME_DIR, or the real kitty binary, and the autouse fixture fails the test"
  - "Sandbox refusal: an integration case that spawns a real terminal checks its environment first and fails with the offending names"

requirements-completed: [R1.5, R1.2, R1.1, R1.3, R1.6]

duration: not measured
completed: 2026-11-03
status: complete
---

# Phase 02 Plan 12: kitty.conf lifecycle, unit hermeticity and integration HOME sandbox Summary

**kitty.conf install and uninstall restore the user's file on every failure path, keep non-UTF-8 bytes intact, and the test tree can no longer reach real HOME, XDG_RUNTIME_DIR or the real kitty binary**

## Performance

- **Duration:** not measured (no start timestamp was recorded for this sequential run)
- **Started:** not recorded (RED committed 2026-11-03 22:43 -0300)
- **Completed:** 2026-11-03
- **Tasks:** 3
- **Files modified:** 12 (5 created, 7 modified; GREEN adds the implementation, Makefile, pyproject.toml, integration conftest and this file)

## Accomplishments

- kitty.conf is restored on every failure after the first write: parse-check rejection, parse check that cannot run, interrupt, and failures in the backup or block write.
- Uninstall never restores a backup that carries our block; it picks the newest marker-free backup.
- A kitty.conf with Latin-1 bytes no longer raises UnicodeDecodeError in install, the sentinel check, doctor or uninstall, and its bytes outside our block round-trip.
- A parse check that cannot run (missing kitty, OSError, timeout) raises ConfigUpdaterError with a message instead of a traceback.
- `make clean` runs `my-kitty uninstall --keep-kitty --keep-backups` when my-kitty is on PATH and fails the target when that uninstall fails.
- The unit tree has a host-state guard that fails any test reaching real HOME, the real XDG_RUNTIME_DIR, or the real kitty binary.
- The integration tree runs every case under a sandboxed HOME, and the h47 sandbox case refuses to spawn kitty when not sandboxed.

## Task Commits

1. **Task 1: RED tests for the lifecycle, hermeticity and sandbox defects** - `7d05804` (test(02-12), amended once to fix four lint findings in two test files; see Deviations)
2. **Task 2: GREEN implementation, Makefile, pyproject and integration conftest** - `feat(02-12)` commit, the commit that carries this file (its hash is in `git log`, not here, because a commit cannot name itself)
3. **Task 3: verification captures and this SUMMARY** - included in the GREEN commit

**Plan metadata:** not committed separately; the final `docs(02-12)` metadata commit is skipped by the plan's topology gate.

## Files Created/Modified

- `src/kitty_setup/config_updater.py` - restore-on-failure wrapper, parse-check exception mapping, marker-free backup selection, surrogateescape I/O, commit-step warning
- `Makefile` - `clean` runs the scoped uninstall when my-kitty is on PATH; `tmp/` removal stays
- `pyproject.toml` - per-file S603 ignores for the two unit modules that spawn fake binaries, with one-line rationales
- `tests/unit/conftest.py` - the host-state audit guard (new)
- `tests/unit/test_unit_hermeticity.py` - guard self-tests and AST rules on the child-process env (new)
- `tests/unit/test_makefile_clean.py` - clean-target behaviour through a fake PATH (new)
- `tests/integration/conftest.py` - autouse sandboxed HOME, XDG dirs, HISTFILE and PATH (new, GREEN)
- `tests/integration/test_home_sandbox.py` - the h47 sandbox case with the refusal (new)
- `tests/unit/test_config_updater.py`, `tests/unit/test_doctor.py`, `tests/unit/test_kitty_session_env.py` - RED cases added to existing modules

## Decisions Made

See `key-decisions` in the frontmatter. Rejected alternatives are stated beside each decision.

Stated facts, not fixes:

- **Accepted WR-04 edge:** a conf that holds only comments and no marker-free backup exists is deleted by uninstall. The scratch-HOME run below shows this as `block removed` followed by `deleted (no other content)`.
- **CRLF translation:** `read_text` translates CRLF to LF, so a CRLF kitty.conf is rewritten with LF line endings on install and uninstall. This is today's behaviour too and is not changed by this plan.
- **h38 probe non-promotion (R5):** the h38 probe is not promoted into `tests/integration/`. Each decision it proves is pinned by a RED unit case. What it adds on top (kitty loads a Latin-1 conf and a symlinked payload) is kitty's behaviour, not the tool's. This is a deliberate deviation, as `02-14` states for its own probe. The h47 probe is promoted as `test_home_sandbox.py`.

## Evidence

Full captures are gitignored under `tmp/` and are cited by path. Status lines below are copied verbatim from those files.

### Pre-work

- Pre-work `HEAD`: `8f8f23e967fa17746d6c9bf1884d72ce0f76a928`.
- h47 probe (`tmp/h47-integration-home/probe-run.txt`, `probe-evidence.txt`): HOME, XDG and HISTFILE set under the sandbox; `found_in_sandbox=True`; `leak_lines=0`.
- h38 real-kitty transcripts: against HEAD `tmp/h38-conf-lifecycle/kitty-before.txt` shows `4 failed, 1 passed`; against the prototype `tmp/h38-conf-lifecycle/kitty-prototype.txt` shows `5 passed`. The before/after `run.py` outputs are in `tmp/h38-conf-lifecycle/actual.json` and `actual-after.json`.
- Unit-guard hit list before the guard: `tmp/h39-unit-hermeticity/before.txt` (see Deviations for the count).
- Child-process inventory and path-context notes: `tmp/h39-unit-hermeticity/repro.md`. The guard has no allow-list. A later spawner, the bandit child added by `02-15`, is recorded by the plan that adds it.

### Conf-restore and parse-check gates

- Task 2 token gates (run against the working-tree GREEN candidate): `conf_restore_on` 5 passed; `conf_restore_first_install` 2 passed; `parse_check_cannot_run` 2 passed; `uninstall_skips_block_bearing_backup` 1 passed; `uninstall_restores_newest_marker_free_backup` 1 passed; `conf_non_utf8` 3 passed; `commit_failure` 2 passed; `parse_cannot_run_is_a_fail_line` 1 passed; `sentinel_non_utf8` 1 passed; whole `test_config_updater.py` plus `test_doctor.py`: 85 passed.
- AST gate on `config_updater.py`: parse_check handlers are FileNotFoundError, OSError and TimeoutExpired, each converted; 7 read/write calls, all `surrogateescape`. Result: PASS.

## make test

Status lines from `tmp/h38-conf-lifecycle/make-test.txt` (full transcript in that file):

```
make test exit status: 0
======================= 531 passed, 79 skipped in 11.06s =======================
```

## make doctor

Verbatim from `tmp/h38-conf-lifecycle/make-doctor.txt`:

```
make doctor exit status: 2
PASS kitty binary: /home/bazzite/.local/bin/kitty -> kitty 0.49.2 created by Kovid Goyal
PASS symlink: /home/bazzite/.local/bin/kitty -> /var/home/bazzite/.local/kitty.app/bin/kitty
PASS desktop entry: /home/bazzite/.local/share/applications/kitty.desktop
PASS config payload: /home/bazzite/.config/kitty/kitty-setup/kitty-setup.conf
PASS sentinel block: present in /home/bazzite/.config/kitty/kitty.conf
PASS parse check: /home/bazzite/.local/bin/kitty +runpy 'import sys; from kitty.config import load_config; bad = []; load_config(sys.argv[-1], accumulate_bad_lines=bad); [print(b, file=sys.stderr) for b in bad]; sys.exit(1 if bad else 0)' /home/bazzite/.config/kitty/kitty.conf exit=0
PASS bindings: 22 ours, 79 defaults, 0 conflicts
FAIL completion: the my-kitty block in /home/bazzite/.bashrc does not match the current template that sources /home/bazzite/.local/share/kitty-setup/my-kitty-completion.bash; run `my-kitty install` to rewrite it
SKIP remote-control: no running kitty
```

This ran the already-installed `my-kitty` tool, not the code in this commit. The `FAIL completion:` line is stale: the installed block predates the current template. It is expected under 02-14's scope and is not fixed here. The doctor PASS for this plan is deferred to the orchestrator's phase-close install.

## make test-integration

Verbatim status lines from `tmp/h47-integration-home/sandbox-case.txt`:

```
make test-integration exit status: 0
1 passed in 0.80s
test-integration: pytest exit status 0 (read from the child's status file; compositor exited 0)
```

From `tmp/h47-integration-home/whole-suite.txt` (line 1 is RED `7d05804`, line 2 is the conftest blob, then the transcript):

```
collected: 79
make test-integration exit status: 0
79 passed in 49.01s
test-integration: pytest exit status 0 (read from the child's status file; compositor exited 0)
```

- History gate: `leak_lines before=0 after=0`, history gate PASS. Counts only; no history content was read by the gate.
- Stop-rule findings: none.

## RED evidence

RED sandbox run (`tmp/h47-integration-home/red-run.txt`), run from a materialised RED tree because the working tree holds the GREEN conftest:

```
7d0580410aae6b492a00e523305de50152159415
make test-integration exit status: 2
1 failed in 0.03s
test-integration: pytest exit status 1 (read from the child's status file; compositor exited 1)
E           Failed: refusing to spawn kitty: not sandboxed: ['HOME', 'XDG_CONFIG_HOME', 'XDG_DATA_HOME', 'XDG_CACHE_HOME', 'XDG_STATE_HOME', 'HISTFILE']
```

No kitty spawned. The `make` exit is 2 because make reports the child pytest status 1 as a recipe error.

RED-state (`tmp/h38-conf-lifecycle/red-state.txt`, run on RED's own tree):

```
pytest exit status: 1
19 failed, 69 deselected in 0.33s
```

Negative control (`tmp/h39-unit-hermeticity/negative-control.txt`, RED^ tests under RED's guard):

```
pytest exit status: 1
2 failed, 25 deselected, 2 errors in 0.08s
```

Lint against RED^ (`tmp/h38-conf-lifecycle/lint-vs-red.txt`):

```
tests/unit/test_config_updater.py pyright RED^=2 now=2 ruff RED^=0 now=0
tests/unit/test_doctor.py pyright RED^=22 now=22 ruff RED^=1 now=1
tests/unit/test_kitty_session_env.py pyright RED^=0 now=0 ruff RED^=0 now=0
```

The ruff hit in `test_doctor.py` is the S105 at line 34, present in RED^.

Guard self-tests on the materialised RED tree: `33 passed, 498 deselected in 2.93s`.

## Scratch-HOME uninstall

Run twice against a block-only conf beside one block-bearing backup, with `env -i` and a scratch HOME (`tmp/h38-conf-lifecycle/uninstall-home`), never the real HOME:

```
run 1: config: block removed ...; config: .../kitty.conf deleted (no other content)
run 2: config: no managed block found ...
```

The second run is a no-op. No `make install` ran.

## Leftovers

- `pgrep -x cage`: no process (exit 1).
- `kitti-*` directories under `/run/user/1000`: none.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] `make status <N>` is not a Makefile target**
- **Found during:** Task 1 probe recording
- **Issue:** the plan asks for `make status <N>`, which does not exist in the Makefile.
- **Fix:** the probe records its own exit status in its capture. No gate reads that line.

**2. [Rule 3 - Blocking] RED sandbox run cannot run in the working tree**
- **Found during:** Task 1 step 2
- **Issue:** the plan requires `tests/integration/conftest.py` absent during the RED run, but the working tree holds the uncommitted GREEN conftest.
- **Fix:** the RED run is done from a materialised RED tree (`git read-tree` plus `checkout-index` into a temp dir), with `UV_NO_SYNC=1` and the repo `.venv`. Refusal means no kitty was spawned.

**3. [Rule 3 - Blocking] `git status --porcelain --untracked-files=no` is not empty**
- **Found during:** Task 1 step 2
- **Issue:** the orchestrator's `.planning/config.json` change is always present, so the plan's empty-status precondition cannot hold.
- **Fix:** checked that only that file is modified. It is not staged or touched.

**4. [Rule 3 - Blocking] Pyright interpreter**
- **Found during:** lint captures
- **Issue:** pyright resolved the wrong interpreter and could not find pytest.
- **Fix:** run with `--pythonpath <repo>/.venv/bin/python`.

**5. [Rule 1 - Bug] Four lint findings in RED test files**
- **Found during:** lint-vs-RED gate after the RED commit
- **Issue:** `real_rmtree = shutil.rmtree` (reportDeprecated), a duplicate `_doctor_home` helper, two private-name accesses on `doctor`, and a `lambda` monkeypatch with an untyped argument.
- **Fix:** applied the four changes to the two test files. The RED commit was amended per coordinator instruction, since `5e243e5` existed only locally (`git branch -r --contains` empty). The amended RED is `7d05804`, with the same seven files and the same subject. Lint now matches RED^.

### Process notes

- **Plan count drift:** the plan estimated 481 unit tests at `1cbcaaa`. The hit-list run (`tmp/h39-unit-hermeticity/before.txt`) measured 479 passed, 2 failed, 2 errors on the materialised HEAD with the prototype guard attached. The cause of the 2-test gap is not established here.
- **Aborted planning prototype:** `tmp/h39-unit-hermeticity/guard.py` was an earlier guard prototype that was aborted and replaced by `tests/unit/conftest.py`. It is evidence only.
- **`make doctor` exit 2:** expected per the coordinator's decision. The stale `FAIL completion:` line is in 02-14's scope.

### Not inlined

The plan's `<output>` list is long. The following items are cited by path under `tmp/` rather than copied into this file, because the captures are large transcripts: `run.py` before/after output, `round5-forms.out`, `round6-forms.out`, `round6-exec.out`, `round6-dns.out`, the `od -c` Latin-1 excerpt, the IN-04 stderr line, the `make clean` sandbox transcripts, and the per-kind conf-restore bytes. The per-test coverage for each of these is in the RED unit cases listed in `provides`.

## Issues Encountered

- An early shell read of the user's shell history printed a plaintext credential into the session transcript. The value is not recorded here. The history file was not read again, and the gate that followed counts matches only. The user should rotate the credential. This is reported in the final message, not in this file.

## User Setup Required

None - no external service configuration required. The phase-close `my-kitty install` will rewrite the stale completion block; that is outside this plan.

## Next Phase Readiness

- Plans 02-13 to 02-15 build on the sandboxed integration tree and the unit guard.
- The bandit child added by 02-15 must be recorded in the guard's child-process inventory by that plan.
- The completion block in the installed `~/.bashrc` is stale and needs `my-kitty install` at phase close.

---
*Phase: 02-defect-remediation*
*Completed: 2026-11-03*

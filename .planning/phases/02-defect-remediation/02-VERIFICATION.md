---
phase: 02-defect-remediation
verified: 2026-11-04T04:14:59Z
status: passed
score: 8/8 must-haves verified (7/7 ROADMAP success criteria + the Universal Phase Gate's added-file clause, closed by 35ab251); 9/9 requirements satisfied
covered_files:
  - .planning/phases/02-defect-remediation/02-01-PLAN.md
  - .planning/phases/02-defect-remediation/02-01-SUMMARY.md
  - .planning/phases/02-defect-remediation/02-02-PLAN.md
  - .planning/phases/02-defect-remediation/02-02-SUMMARY.md
  - .planning/phases/02-defect-remediation/02-03-PLAN.md
  - .planning/phases/02-defect-remediation/02-03-SUMMARY.md
  - .planning/phases/02-defect-remediation/02-04-PLAN.md
  - .planning/phases/02-defect-remediation/02-04-SUMMARY.md
  - .planning/phases/02-defect-remediation/02-05-PLAN.md
  - .planning/phases/02-defect-remediation/02-05-SUMMARY.md
  - .planning/phases/02-defect-remediation/02-06-PLAN.md
  - .planning/phases/02-defect-remediation/02-06-SUMMARY.md
  - .planning/phases/02-defect-remediation/02-07-PLAN.md
  - .planning/phases/02-defect-remediation/02-07-SUMMARY.md
  - .planning/phases/02-defect-remediation/02-08-PLAN.md
  - .planning/phases/02-defect-remediation/02-08-SUMMARY.md
  - .planning/phases/02-defect-remediation/02-09-PLAN.md
  - .planning/phases/02-defect-remediation/02-09-SUMMARY.md
  - .planning/phases/02-defect-remediation/02-10-PLAN.md
  - .planning/phases/02-defect-remediation/02-10-SUMMARY.md
  - .planning/phases/02-defect-remediation/02-11-PLAN.md
  - .planning/phases/02-defect-remediation/02-11-SUMMARY.md
  - .planning/phases/02-defect-remediation/02-12-PLAN.md
  - .planning/phases/02-defect-remediation/02-12-SUMMARY.md
  - .planning/phases/02-defect-remediation/02-13-PLAN.md
  - .planning/phases/02-defect-remediation/02-13-SUMMARY.md
  - .planning/phases/02-defect-remediation/02-14-PLAN.md
  - .planning/phases/02-defect-remediation/02-14-SUMMARY.md
  - .planning/phases/02-defect-remediation/02-15-PLAN.md
  - .planning/phases/02-defect-remediation/02-15-SUMMARY.md
  - Makefile
  - README.md
  - pyproject.toml
  - src/kitty_setup/binding_introspection.py
  - src/kitty_setup/cli.py
  - src/kitty_setup/config_updater.py
  - src/kitty_setup/doctor.py
  - src/kitty_setup/harness/integration_runner.py
  - src/kitty_setup/harness/kitty_session.py
  - src/kitty_setup/installer.py
  - src/kitty_setup/path_integration.py
  - src/kitty_setup/scenes/__init__.py
  - src/kitty_setup/scenes/_client.py
  - src/kitty_setup/scenes/accent.py
  - src/kitty_setup/scenes/background.py
  - src/kitty_setup/scenes/colors.py
  - src/kitty_setup/scenes/launcher.py
  - src/kitty_setup/scenes/recipe.py
  - tests/conftest.py
  - tests/integration/conftest.py
  - tests/integration/test_completion_e2e.py
  - tests/integration/test_home_sandbox.py
  - tests/integration/test_scene_fill_tab_e2e.py
  - tests/unit/conftest.py
  - tests/unit/test_bandit_scope.py
  - tests/unit/test_config_updater.py
  - tests/unit/test_doctor.py
  - tests/unit/test_installer_completion.py
  - tests/unit/test_installer_download.py
  - tests/unit/test_installer_uninstall.py
  - tests/unit/test_integration_runner.py
  - tests/unit/test_kitty_session_env.py
  - tests/unit/test_makefile_clean.py
  - tests/unit/test_path_integration.py
  - tests/unit/test_scenes_launcher.py
  - tests/unit/test_scenes_recipe.py
  - tests/unit/test_tools_uninstall_sh.py
  - tests/unit/test_unit_hermeticity.py
  - tmp/phase2-close/install.txt
  - tmp/phase2-close/integration.txt
  - tmp/phase2-close/make-doctor.txt
  - tmp/phase2-close/make-test.txt
  - tools/uninstall.sh
  - vulture_allowlist.py
covered_digest: "v4:sha256:43009d6750b2924c5d81701c4a58496f5aa72f51c6705bbe8ebd02d981d43345"
behavior_unverified: 0
overrides_applied: 0
re_verification:
  previous_status: gaps_found
  previous_score: 7/8 must-haves verified (report at 35da608, 2026-11-04T04:11:26Z)
  previous_verified_at: "35da608 (02-01..02-15); before that d4a3a8c (02-01..02-11, passed)"
  gaps_closed:
    - "Universal Phase Gate step 5, added-file clause: tests/integration/test_completion_e2e.py black-formatted by 35ab251 (`style(02): black-format test_completion_e2e.py`, formatting only: one implicit string concatenation joined onto one line, the same string value). Verifier re-run at 35ab251: `uv run black --check` and `uv run ruff check` over all 19 phase-added .py files (git diff --diff-filter=A 5452f54..HEAD, src tests tools + vulture_allowlist.py) both exit 0; pyright over the 18 under src/tests: 0 errors; `make test` 619 passed, 88 skipped, exit 0"
    - "W1 (installed binary stale vs HEAD) and W2 (bookkeeping) from the d4a3a8c report: closed at 35da608 (see report body)"
  gaps_remaining: []
  regressions: []
deferred:
  - truth: "Parse check blind to a missing own-payload `include`, and skipped on an unchanged-conf reinstall (also security advisory A-5)"
    addressed_in: "Phase 5"
    evidence: "STATE.md Pending Todos [Phase 5] (carried from the prior report); 02-SECURITY.md A-5 routes it to the AR-03 follow-up"
  - truth: "`my-kitty window background none` exits 1"
    addressed_in: "Phase 6"
    evidence: "R4.1; carried from the prior report"
---

# Phase 2: Defect Remediation Verification Report

**Phase Goal:** A fresh install on Bazzite is provably healthy — `my-kitty doctor` is all PASS/SKIP and every known audit defect is fixed and pinned by a regression test, giving later phases a green baseline they can trust.
**Verified:** 2026-11-04T04:14:59Z, at `35ab251` on `gsd/phase-02-defect-remediation`, primary checkout (only this report modified)
**Status:** passed. Every truth is verified, and the one gate gap from the 35da608 run is closed by `35ab251`.
**Re-verification:** Yes, and gap-only. The full verification ran at `35da608`, 2026-11-04T04:11:26Z. This pass re-ran only the failed gate at `35ab251`. Since `35da608`, `git diff --stat 35da608 35ab251` touches only `tests/integration/test_completion_e2e.py` (+1/−2), so every other result below carries forward unchanged.

## Gap-Closure Re-run (verifier, this session, at 35ab251)

| Command | Output (key lines) | Exit |
|---|---|---|
| `git show 35ab251` | `style(02): black-format test_completion_e2e.py`. One hunk: the `dash_d` shape's two implicit-concatenation pieces are joined onto one line. The string value is unchanged | — |
| `uv run black --check <19 phase-added .py files>` | `19 files would be left unchanged.` | 0 |
| `uv run ruff check <same 19>` | `All checks passed!` | 0 |
| `uv run pyright <18 phase-added files under src/ and tests/>` | `0 errors, 0 warnings, 0 informations` | 0 |
| `uv run black --check src` / `uv run ruff check src` | `22 files would be left unchanged.` / `All checks passed!` | 0 / 0 |
| `uv run black --check src tests tools` | `10 files would be reformatted`. Down from 11; the 5452f54 baseline was 11. None of the 10 was added by Phase 2, and all are Phase 8.5's scope | 1 |
| `make test` | `619 passed, 88 skipped in 12.21s` | 0 |

The phase-added set is `git diff --name-only --diff-filter=A 5452f54 HEAD -- src tests tools vulture_allowlist.py`, where `5452f54` is the merge-base with `master`. It holds 19 `.py` files: 18 under `src/` and `tests/`, plus the root-level `vulture_allowlist.py`. That is a superset of the coordinator's 17, which were counted from `8faae07`. All 19 are clean.

## Gate Evidence

### Run by the verifier at 35da608 (carried forward; only one test file changed since)

| Command | Output (key lines) | Exit |
|---|---|---|
| `make test` | `619 passed, 88 skipped in 11.64s`. The 88 skips are all `tests/integration`, gated on `KITTI_INTEGRATION=1` | 0 |
| `make doctor` | 8 PASS + `SKIP remote-control: no running kitty`. Completion line: `…/my-kitty-completion.bash is current and sourced by the my-kitty block in /home/bazzite/.bashrc` | 0 |
| `uv run ruff check src` | `All checks passed!` | 0 |
| `uv run black --check src` | `22 files would be left unchanged.` | 0 |
| `uv run pyright src` | `0 errors, 0 warnings, 0 informations` | 0 |
| `uv run bandit -c pyproject.toml -q -r src` | (no output) | 0 |
| `uv run vulture src tests vulture_allowlist.py` | (no output) | 0 |
| `rg 'noqa\|type: ignore\|pyright: ignore\|nosec\|shell=True' src` | none | — |
| `uv run pytest tests/integration --collect-only -q \| rg -c '::'` | 88 | — |
| `diff -rq src/kitty_setup <uv tool site-packages>/kitty_setup` | only the build-time `_payload`, `_scenes` data dirs. The installed binary is HEAD's code | — |
| ruff `src tests tools` / whole-tree pyright / `vulture src tests` | 19 / 503 errors / 8 lines (baseline 28 / 571 / 12) | — |

### Captured by the orchestrator at 4093b55, after the one deliberate real install (`tmp/phase2-close/`)

Since `4093b55` there are only docs commits and `35ab251`'s formatting-only change to an integration test, so these captures apply to HEAD's code.

| File | Content |
|---|---|
| `install.txt` | `make install exit status: 0`. kitty 0.49.2. The config is already up to date. The `.bashrc` block body was rewritten to the current template, and the completion file was written. sha256 bracket: the bytes outside our block are IDENTICAL for `~/.bashrc`, `~/.zshrc` and `kitty.conf`. Of the three, only `.bashrc` changed, and only inside the block. `SHA-BRACKET VERDICT: PASS` |
| `make-doctor.txt` | identical to the verifier's run: 8 PASS + 1 SKIP, exit 0 |
| `make-test.txt` | `619 passed, 88 skipped`, exit 0 |
| `integration.txt` | `88 passed in 63.97s` / `test-integration: pytest exit status 0 (read from the child's status file; compositor exited 0)`, exit 0 |

## Goal Achievement

### Observable Truths (ROADMAP success criteria + the Universal Phase Gate)

| # | Truth | Status | Evidence |
|---|---|---|---|
| 1 | Doctor exits 0, all PASS/SKIP, on a fresh uv-tool install. Completion comes from an install-generated static file that the rc block sources. Former "skipped" checks report a real SKIP | ✓ VERIFIED | The fresh install is `install.txt`, followed by `make doctor` (exit 0), which runs HEAD's code. The bash file is `my-kitty-completion.bash`. Since 02-14, zsh uses `_my-kitty` on `fpath` (`path_integration.zsh_fpath_line`, `installer.py:55-61`), and the go-w bits on the dir are cleared (`installer.py:398`). There is no runtime `register-python-argcomplete` lookup: the only hits are comments. `CheckResult.render` emits SKIP (`doctor.py:34`). Doctor no longer judges block position (`doctor.py:243`). Staleness is a byte compare (`doctor.py:282`, `test_completion_byte_compare_flags_crlf_only_as_stale`). The rc is read with surrogateescape. Real-shell registration: the 8 `test_completion_e2e.py` items are inside the 88/88 integration capture |
| 2 | `make clean` never removes kitty.app or backups and its help matches. `tools/uninstall.sh` logs to stderr and its legacy branch works. Both are tested | ✓ VERIFIED | The `clean` recipe guards on `command -v my-kitty`, has no `\|\| true`, and passes `--keep-kitty --keep-backups` (Makefile:29-31). Tests: `test_makefile_clean.py::test_clean_failure_propagates`. `log()` writes `>&2` (uninstall.sh:17), and the legacy branch is at :28-35. The will-remove list names payload asides and `_my-kitty` (:70, :77), pinned by `test_will_remove_list_names_payload_asides_unless_kept`. The A-2 sandbox rule is now a committed test (`test_hermetic_uninstall_sandbox_rule_*`) |
| 3 | A scene whose `cwd` contains spaces fills the current tab, and pane 0 has `bash -lc` semantics | ✓ VERIFIED | R1.4 was reworded by 02-13 and is implemented. `_typeable` is `isprintable` with no `'` and no `\`, and `_pane0_typeable` requires an absolute, `$`-free `cwd`, normalised (launcher.py:229-252). Payloads are `cd -- '<normpath>'` and `bash -lc '<cmd>'` (:302, :313). An untypeable pane 0 writes one stderr note and takes the new-tab argv path (:417-428). The NUL refusal is in `recipe._require_str` (:84). Spot-check: `'/tmp/a b'` and `'/x/a==bash'` are typeable. `~/x`, `$HOME/x`, `rel/dir`, a quote, a backslash and U+202E are not. A NUL raises `SceneRecipeError`. The re-run 02-04-T1 AST payload gate passes. Real kitty: `test_scene_fill_tab_e2e.py` (10 items) is in the 88/88 capture |
| 4 | A failing parse check reports its command and stderr, rolls the payload back, and has the right label. Integration passes from inside kitty | ✓ VERIFIED | `parse_check` maps `TimeoutExpired` and `OSError` to `ConfigUpdaterError` (config_updater.py:248-255). Spot-check: a missing binary → "not found", and a directory → "could not be run". `_write_block_and_check`'s `try` opens before the first conf write, and its `except BaseException` restores the conf (:440-470). The payload rollback is at :393-399, and the commit step can no longer abort `cli_install` (:403-411). The conf codec is surrogateescape on all 7 I/O calls (the A-7 conf-codec AST gate re-run passes). `KITTY_WINDOW_ID` is popped in h25:393 and scene_recipe_e2e:80,125, and the runner's `SCRUBBED_VARIABLES` drops it. Tests: `test_config_updater.py` (58), with the ENOSPC, timeout and Ctrl-C injections at :722-767 |
| 5 | Every remaining minor defect has a regression test | ✓ VERIFIED | No regression since the d4a3a8c report. The install log is gone. `_window_id_from` is used at all 3 sites. Teardown is `close-window --match=all` (kitty_session.py:324). `my-kitty prune --backups --keep -1` → `must be >= 0, got -1`, exit 2. The unsupported-shell line is `# completion is not set up for …` (path_integration.py:242) |
| 6 | ruff, black, pyright, bandit and vulture are clean for `src/` (R0.11) | ✓ VERIFIED | All five exit 0. B310 and the installer S310 are gone with `urlopen`. B604 and B607 are fenced per site by `test_bandit_scope.py`, a test run by `make test` that includes the planted-site negative control `test_bandit_fence_sees_a_replaced_site`. Downloads are https-only on every redirect hop (`_HttpsOnlyRedirectHandler`, installer.py:170-189). The fd is closed and the temp file removed on failure (:201-210). `vulture_allowlist.py` is unchanged at the five permitted names |
| 7 | `make test-integration` runs all of `tests/integration/` headless and reports its real count. `make test` stays unit-fast. A run with no compositor fails loudly. Dead code is deleted | ✓ VERIFIED | Capture: `88 passed`, with the verdict read from the child's status file. `make test` takes ≈12s. With no compositor → `FAILED — … NOT run; this is a failure, not a skip.`, exit 69. `--noconftest` → usage error, exit 64, before any compositor. In-process `build_pytest_args`: `--ignore tests/integration/x.py`, `-k tests`, `--cov -k tests` and `-xk tests` keep the integration root. `--confcutdir=`, `-o addopts=`, `@file`, `-k @file`, `--child` and `tests/unit` are refused. `PYTEST_ADDOPTS` is scrubbed, and `main` has no `_child(` call. The `tests/conftest.py` backstop raises `pytest.UsageError` under `KITTI_INTEGRATION=1` for any item outside `tests/integration` (:57-64). The integration HOME sandbox is the autouse `sandbox_integration_home` (tests/integration/conftest.py:29-45), pinned by `test_home_sandbox.py`. The unit host-state guard is `sys.addaudithook` (tests/unit/conftest.py:358), with 20 self-tests |
| 8 | Universal Phase Gate step 5: a file the phase adds is clean under every tool, wherever it lives | ✓ VERIFIED (gap closed by `35ab251`) | It failed at `35da608`, because `tests/integration/test_completion_e2e.py` was black-dirty from 02-14 RED `b097c66`. At `35ab251`, all 19 phase-added `.py` files pass `black --check` and `ruff check` (both exit 0), and the 18 under `src/` and `tests/` have 0 pyright errors. Pyright reports strict-mode errors on `vulture_allowlist.py` only when it is named explicitly; it sits outside `[tool.pyright] include` (Info, below) |

**Score:** 8/8 truths verified (0 present-but-behavior-unverified).

### Deferred Items

| # | Item | Addressed In | Evidence |
|---|---|---|---|
| 1 | Parse check blind to a missing own-payload `include`, and skipped on an unchanged-conf reinstall (security A-5) | Phase 5 | STATE.md Pending Todos; 02-SECURITY.md A-5 |
| 2 | `my-kitty window background none` exits 1 | Phase 6 | R4.1 |

### Known open items (classified, non-blocking)

These are recorded in `.planning/todos/pending/2026-11-04-phase2-gap-review-followups.md`. None of them falsifies a ROADMAP success criterion or a plan must-have, so none is a gap. They are listed in order of risk.

| Item | Class | Why it does not block | Risk to note |
|---|---|---|---|
| WR-02 (MEDIUM): `_latest_backup` skips every block-bearing backup, so uninstall can restore an older snapshot and drop newer user edits | ⚠️ Warning | It is exactly the behaviour 02-12's must-have specifies ("restores only a backup that holds no marker line"), and it fixes the non-convergence defect (WR-04). The loss needs a multi-step sequence: edit inside the block, reinstall, then uninstall | This is real data loss, introduced in this phase, in an edge case. It is the most important follow-up |
| WR-01 / U-2 (MEDIUM/low): rc and conf rewrites are truncate-then-write; the rc has no backup | ⚠️ Warning | Pre-existing pattern; the phase-close install was protected by a sha256 bracket, which passed | ENOSPC or a kill mid-write truncates `~/.bashrc`/`~/.zshrc` |
| WR-03 (MEDIUM): doctor's zsh PASS ignores a compaudit-rejected `~/.local/share` | ⚠️ Warning | Not reachable on this host (user-private groups, umask 0022). Bash is the detected shell here | A false PASS on hosts without per-user groups |
| U-1: completion file mode not hardened | ℹ️ Info | Not exploitable on this host (umask 0022 + UPG) | — |
| U-3: unit guard fail-open edges | ℹ️ Info | The guard is defence-in-depth; it found and fixed the two IN-08 tests | — |
| A-7: plan-only AST gates | ℹ️ Info | I re-ran three of the four at `35da608`: the 02-04-T1 launcher payload gate, the conf-codec gate and the rc-I/O gate. All pass. The guard negative control was not re-run | Not yet in `tests/unit/` |
| 11 LOW code-review findings (IN-01..IN-11) | ℹ️ Info | Edge cases, cleanups, and a garbled docstring (`config_updater.py:310`, "Neither ``prune`` never touches") | — |
| 02-12-SUMMARY.md lacks `plan_head_before/after` | ℹ️ Info | The commits exist: `7d05804` (RED) and `f6e4432` (GREEN), one RED+GREEN pair per `type: tdd` plan as AGENTS.md requires. 02-13 and 02-14 carry only `plan_head_before` | Ledger completeness only |
| 02-14-SUMMARY.md:418 says "the five settled tools (… black …)" pass, though black ran only on `src/` | ℹ️ Info | The overclaim hid the truth-8 gap, which `35ab251` has now fixed | SUMMARY accuracy |

### Required Artifacts (plans 02-12..02-15; 02-01..02-11 regression-checked)

| Artifact | Expected | Status | Details |
|---|---|---|---|
| `src/kitty_setup/config_updater.py` | surrogateescape, a timeout/OSError mapping, a conf restore over the whole write region, `_latest_backup`, `list_payload_asides`, `discard_payload_aside` | ✓ VERIFIED | Read at :196-531. Used by `install()`, `cli_uninstall` and `doctor._check_payload` |
| `Makefile` | `clean` guarded on `command -v my-kitty` | ✓ VERIFIED | :29-31 |
| `tests/unit/conftest.py` | autouse audit-hook guard | ✓ VERIFIED | `sys.addaudithook` at :358; lookup events at :55; `dir_fd` via `/proc/self/fd` |
| `tests/unit/test_unit_hermeticity.py` | guard self-tests and the A-2/child-env AST rules | ✓ VERIFIED | 29 items pass |
| `tests/unit/test_makefile_clean.py` | `clean_failure_propagates` | ✓ VERIFIED | 3 items pass |
| `tests/integration/conftest.py` / `test_home_sandbox.py` | HOME/XDG/HISTFILE sandbox, plus a refusal to spawn | ✓ VERIFIED | :29-45; `refusing to spawn kitty` |
| `src/kitty_setup/scenes/launcher.py` / `recipe.py` | typeable rule, single-quoted payloads, argv fallback, NUL refusal | ✓ VERIFIED | see truth 3 |
| `src/kitty_setup/path_integration.py` / `installer.py` / `doctor.py` | fpath body, `_my-kitty`, go-w, byte rc I/O, duplicate convergence, no position FAIL, byte compare | ✓ VERIFIED | see truth 1; `test_duplicate_rc_blocks_converge`, `test_zsh_body_adds_fpath` |
| `src/kitty_setup/harness/integration_runner.py` | `_VALUE_OPTIONS`, `_OPTIONAL_VALUE_OPTIONS`, `_CONFTEST_BYPASS_OPTIONS`, `_CHILD_PROGRAM`, `PYTEST_ADDOPTS` scrub | ✓ VERIFIED | :55-155, :287-341, :441; no `import pytest` |
| `tests/conftest.py` | `UsageError` backstop | ✓ VERIFIED | :48-68 |
| `tests/unit/test_bandit_scope.py` | per-site B310/B604/B607 fence + `urllib.request` fence | ✓ VERIFIED | 4 items pass |
| `tests/integration/test_completion_e2e.py` | phase-added e2e module, gate-clean | ✓ VERIFIED | black/ruff clean at `35ab251` |
| `.planning/REQUIREMENTS.md`, `02-CONTEXT.md`, `02-VALIDATION.md` | R1.4 reworded; D-08 and D-01/D-03 amendments; 02-04-T1 no longer pins `shlex.quote` | ✓ VERIFIED | REQUIREMENTS.md:146; two dated amendments in CONTEXT; VALIDATION:166 and correction 21 |

### Key Link Verification

| From | To | Via | Status |
|---|---|---|---|
| `parse_check` | `doctor._check_parse`'s existing `except ConfigUpdaterError` | errors converted at the source | WIRED |
| `_write_block_and_check` `except BaseException` | `install()` payload rollback | the conf is restored, then the error re-raised into the payload handler | WIRED (:397-399, :468-470) |
| `discard_payload_aside` | `install()` commit step + `cli_uninstall` | one shared helper | WIRED (:405; installer.py:578) |
| `list_payload_asides` | `doctor._check_payload` + `cli_uninstall` | one strict pattern | WIRED (doctor.py:84; installer.py:570) |
| launcher fill decision | new-tab argv path | `if _pane0_typeable(...)` else stderr note | WIRED (:417-428) |
| `recipe._require_str` NUL refusal | `_launch_named_scene`'s `SceneRecipeError` handler | raises in `load_scene` | WIRED (`test_recipe_nul_refused_before_any_kitten_call`) |
| zsh `fpath` line | `installer.completion_script_path("zsh").parent` | rendered from the installer's path | WIRED (`zsh_fpath_line`) |
| `doctor._check_completion` | `path_integration._block_body_matches_template` | same predicate as install | WIRED (doctor.py:270) |
| runner `_CONFTEST_BYPASS_OPTIONS` + scrub | `tests/conftest.py` backstop | the hook always loads | WIRED (spot-checks) |
| `test_bandit_scope.py` | `pyproject.toml [tool.bandit] skips` | `test_bandit_skips_keep_only_the_scoped_ids` | WIRED |

### Data-Flow Trace (Level 4)

Not applicable. The phase renders no dynamic UI. Doctor's lines come from live filesystem and subprocess probes (`make doctor` transcript).

### Behavioral Spot-Checks (run at 35da608; no src change since)

| Behavior | Command | Result | Status |
|---|---|---|---|
| runner argv classification | in-process `build_pytest_args` over 12 vectors (verifier scratch `spot.py`) | value options keep the root; every bypass, `@file`, `--child` and `tests/unit` raises `UsageError`; `--pyargs` passes through to the backstop by design | ✓ PASS |
| runner, no compositor / bypass option | `env PATH=/nonexistent .venv/bin/python -m kitty_setup.harness.integration_runner [-q \| --noconftest]` | exit 69 / exit 64 | ✓ PASS |
| pane-0 typeable rule + NUL refusal | same script | see truth 3 | ✓ PASS |
| parse_check error mapping | same script, scratch dir | `ConfigUpdaterError` for a missing and an unrunnable binary | ✓ PASS |
| prune negative keep | `uv run my-kitty prune --backups --keep -1` | exit 2, argparse error | ✓ PASS |
| A-7 AST gates | verifier scratch `a7gates.py` | launcher payload, conf codec and rc I/O: all PASS | ✓ PASS |

### Probe Execution

No probe scripts are declared, and `scripts/*/tests/probe-*.sh` does not exist. SKIPPED.

### Requirements Coverage

The `requirements:` union across 02-01..02-15 is exactly the ROADMAP's Phase 2 list. No ID is orphaned: REQUIREMENTS.md maps only these nine IDs to Phase 2.

| Requirement | Source Plans | Status | Evidence |
|---|---|---|---|
| R1.1 | 02-01, 02-02, 02-12, 02-14 | ✓ SATISFIED | Truth 1; doctor PASS on the real install |
| R1.2 | 02-03, 02-12, 02-15 | ✓ SATISFIED | Truth 2; `clean` propagates failure and keeps backups and asides |
| R1.3 | 02-03, 02-12, 02-14, 02-15 | ✓ SATISFIED | Truth 2; the A-2 rule is committed |
| R1.4 | 02-04, 02-13 | ✓ SATISFIED | Truth 3 (reworded R1.4, REQUIREMENTS.md:146) |
| R1.5 | 02-05, 02-12, 02-15 | ✓ SATISFIED | Truth 4; asides removed or named |
| R1.6 | 02-08, 02-12 | ✓ SATISFIED | Truth 4; integration HOME sandbox |
| R1.7 | 02-04..02-08 | ✓ SATISFIED | Truth 5 |
| R0.11 | 02-09, 02-10, 02-15 | ✓ SATISFIED | Truth 6 |
| R0.13 | 02-09, 02-10, 02-11, 02-15 | ✓ SATISFIED | Truth 7; 88/88 captured |

REQUIREMENTS.md traceability: all nine IDs read `Complete` (lines 443-452), and the R0.13 row the d4a3a8c report found missing is present.

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|---|---|---|---|---|
| `src tests tools Makefile pyproject.toml` | — | `TBD\|FIXME\|XXX`, `TODO\|HACK\|PLACEHOLDER` | — | none found |
| `src/kitty_setup/config_updater.py` | 310 | garbled docstring "Neither ``prune`` never touches" | ℹ️ Info | IN-10 |
| `Makefile` | 8-21 | `help` is 13 lines, against the five-line target rule | ℹ️ Info | pre-existing at `5452f54` (11 lines); the phase added only entries |
| `vulture_allowlist.py` | 3-10 | pyright strict reports unknown types when the file is named explicitly | ℹ️ Info | outside `[tool.pyright] include = ["src","tests"]`, so no gate counts it |
| 10 pre-existing `tests/` files | — | black-dirty | ℹ️ Info | not added by Phase 2; the count is below the 5452f54 baseline (11); Phase 8.5's scope |
| `.planning/ROADMAP.md` | 66 | Phase 2 checkbox still `[ ]` | ℹ️ Info | the orchestrator's phase-complete step |

### Human Verification Required

None. The physical Tab keypress in the user's own terminal stays on 02-VALIDATION's manual-only list by design. The orchestrator resolved it on 2026-09-24 through argcomplete's protocol, and the real-zsh/bash e2e items pass in the 88/88 capture. It is not a gate.

### Gaps Summary

There are no remaining gaps. The phase goal is achieved in the code. The real install at phase close passed its sha256 bracket. Doctor on HEAD's installed code is 8 PASS + 1 SKIP. Every original audit defect (R1.1–R1.7) and every gap-closure defect from 02-12..02-15 (WR-01..WR-06, IN-01..IN-08, A-1..A-4, T-2-79) is implemented, wired and pinned. The pins are 619 unit tests, 88 headless integration tests, and the src quality tools, all green. The one gate gap found at `35da608`, the black-dirty phase-added `tests/integration/test_completion_e2e.py`, is closed by `35ab251`, and this re-run confirms it. The MEDIUM review findings WR-02, WR-01 and WR-03, and the security flags U-1..U-3, A-5 and A-7, remain warnings and info items in the pending todo. WR-02 deserves priority, because the data loss it describes was introduced in this phase.

---

_Verified: 2026-11-04T04:14:59Z (gap re-run at 35ab251; full verification 2026-11-04T04:11:26Z at 35da608)_
_Verifier: Claude (gsd-verifier)_

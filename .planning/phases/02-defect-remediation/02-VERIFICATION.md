---
phase: 02-defect-remediation
verified: 2026-09-24T13:42:12Z
status: passed
score: 7/7 success criteria verified; 9/9 requirements satisfied
covered_files:
  - .planning/REQUIREMENTS.md
  - .planning/ROADMAP.md
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
  - Makefile
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
  - tools/uninstall.sh
  - vulture_allowlist.py
covered_digest: "v1:sha256:412cfb3e580606db6b52fd1371c52de50ed744d0e5e2d4edc157d3a760d31a3e"
behavior_unverified: 0
overrides_applied: 0
deferred:
  - truth: "Parse check fails on a missing include of our own payload, and runs on every payload replacement (so payload rollback engages on an ordinary reinstall)"
    addressed_in: "Phase 5"
    evidence: "STATE.md Pending Todos: '[Phase 5 — found by 02-05, measured on kitty 0.49.0] ... Proposed requirement: the check fails on a missing include of our own payload and runs on every payload replacement ... Phase 5 is the next phase to touch config_updater'. Outside R1.5's four asks; 02-VALIDATION manual-only row confirms it is reported, not fixed."
  - truth: "`my-kitty window background none` resets the background"
    addressed_in: "Phase 6"
    evidence: "STATE.md Blockers/Concerns [Phase 6]; 02-06-SUMMARY pins rc=1 'The color background cannot be set to none' unchanged; R4.1 owns it."
human_verification:
  - test: "From the HEAD of gsd/phase-02-defect-remediation, reinstall the tool (`make install`), then run `make doctor`"
    expected: "Exit 0; nine lines, each PASS or SKIP (remote-control SKIP when no kitty runs); `tmp/install.log` is not rewritten"
    why_human: "The installed my-kitty was built at 07:59 from agent worktree .claude/worktrees/agent-af203166903a592d0 and predates 02-07..02-10 (it still carries `_record_install_log` and lacks the prune `--keep` guard). `make doctor` in this report ran that stale binary. The doctor/completion/rc code paths differ from HEAD only by renames, and HEAD's own doctor (`uv run my-kitty doctor`) also passes against the live footprint, but criterion 1 says 'fresh uv-tool install' and the verifier is forbidden from installing."
  - test: "Open a fresh login bash (and, if used, zsh) shell and type `my-kitty <Tab>`"
    expected: "Subcommands are offered"
    why_human: "02-VALIDATION manual-only row: the e2e tests drive argcomplete's protocol and prove registration in real bash/zsh, but no pty or human keypress is driven. The deferred-compinit plugin-manager case (zinit turbo, zsh-defer) is a disclosed limitation (README lines 161-165), not a defect."
---

# Phase 2: Defect Remediation Verification Report

**Phase Goal:** A fresh install on Bazzite is provably healthy — `my-kitty doctor` is all PASS/SKIP and every known audit defect is fixed and pinned by a regression test, giving later phases a green baseline they can trust.
**Verified:** 2026-09-24T13:39:04Z, at `d4a3a8c` on `gsd/phase-02-defect-remediation`, primary checkout, clean tree
**Status:** passed (both human-verification items resolved by the orchestrator, 2026-09-24 — see the resolution section below)
**Re-verification:** No. This is the first verification.

## Gate Evidence (run by the verifier, this session)

| Command | Output (key lines) | Exit |
|---------|--------------------|------|
| `make doctor` | 8 PASS + `SKIP remote-control: no running kitty`. The completion line reads `PASS completion: /home/bazzite/.local/share/kitty-setup/my-kitty-completion.bash is current and sourced by the my-kitty block in /home/bazzite/.bashrc`. The parse-check line names the real `kitty +runpy ... load_config ...` command | 0 |
| `uv run my-kitty doctor` (HEAD source, same live footprint) | identical 9 lines, 8 PASS / 1 SKIP | 0 |
| `make test` | `481 passed, 78 skipped in 8.22s` (the 78 skips are all `tests/integration`) | 0 |
| `timeout 900 make test-integration PYTEST_ARGS='-q'` | `78 passed in 46.11s` / `test-integration: pytest exit status 0 (read from the child's status file; compositor exited 0)` | 0 |
| `uv run ruff check src` | `All checks passed!` | 0 |
| `uv run black --check src` | `22 files would be left unchanged.` | 0 |
| `uv run pyright src` | `0 errors, 0 warnings, 0 informations` | 0 |
| `uv run bandit -c pyproject.toml -q -r src` | (no output) | 0 |
| `uv run vulture src tests vulture_allowlist.py` | (no output) | 0 |
| Post-run leftovers: `pgrep -a cage; pgrep -ax kitty; ls $XDG_RUNTIME_DIR \| grep kitti` | nothing | — |

## Goal Achievement

### Observable Truths (ROADMAP success criteria)

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | `my-kitty doctor` exits 0, all PASS/SKIP, on a uv-tool install; completion works from an install-generated static file the rc block sources (no runtime `register-python-argcomplete` lookup); former "skipped" checks report a real SKIP | ✓ VERIFIED (fresh-HEAD reinstall routed to human) | `make doctor` exits 0, and so does HEAD-source doctor. `installer.generate_completion_script` calls `argcomplete.shellcode` in-process (installer.py:332-341). `cli_install` writes the script after the rc edit (installer.py:450-470). The live `~/.bashrc` block reads `[ -f "$HOME/.local/share/kitty-setup/my-kitty-completion.bash" ] && . "…"`. `rg register-python src/` finds no runtime lookup. `CheckResult.render` emits `SKIP` (doctor.py:32-36), and three named tests pin it (`test_skip_state_parse_check_without_kitty_binary`, `test_skip_state_bindings_without_kitty_binary`, `test_skip_state_bindings_when_introspection_fails`). Real-shell registration passed inside the integration run: 6 `test_completion_e2e.py` items, bash and zsh, including `test_doctor_verdict_matches_real_zsh_registration`. |
| 2 | `make clean` keeps `kitty.app` and backups and its help matches; `tools/uninstall.sh` logs `resolve_binary` output to stderr and its legacy branch works; both covered by tests | ✓ VERIFIED | The Makefile `clean` recipe is `my-kitty uninstall --keep-kitty --keep-backups \|\| true` plus `rm -rf tmp/`. Its help text says "strip our config block + payload, wipe ./tmp/ scratch (keeps kitty + backups)". `cli_uninstall` guards removal of kitty.app, the symlink, the desktop entry and the completion script behind `do_kitty` (installer.py:487-547). In uninstall.sh, `log()` writes `>&2`. Tests: `test_makefile_targets.py` (recipe flag set == help keep set), `test_clean_recipe_flags_keep_kitty_and_backups`, `test_legacy_binary_branch_forwards_to_my_kitty_setup`, `test_error_branch_diagnostics_are_visible_on_stderr`, `test_home_local_bin_fallback_is_used`. Named run: `28 passed`. |
| 3 | A scene whose `cwd` has spaces fills the current tab (pane-0 `cwd` shell-quoted); pane 0 uses `bash -lc` like every other pane | ✓ VERIFIED | launcher.py:266-280 sends `cd {shlex.quote(p0.cwd)}` and `bash -lc {shlex.quote(p0.cmd)}`; `_launch_argv` uses `["bash","-lc",pane.cmd]` (:139). A real-kitty test, `test_scene_fill_tab_e2e.py::test_fill_tab_quoting_space_and_metachar_in_pane0_cwd`, passed in the headless run. |
| 4 | A failing parse check reports the command it ran, surfaces parser stderr, rolls the payload dir back, and has the right doctor label; the integration suite passes from inside a kitty window (`KITTY_WINDOW_ID` stripped in h25 and `scene_recipe_e2e`) | ✓ VERIFIED | `parse_check` returns `command=shlex.join(argv)` and `stderr` (config_updater.py:213-238). `_rejection_message` prints both. `install()` renames the previous payload to a `.rollback` sibling and restores it on any `BaseException` (:311-355). The doctor line reads `parse check: <actual command> exit=0` (and `--debug-config` appears nowhere in src). Rollback tests: `test_rollback_parse_fails_restores_previous_payload`, `test_rollback_copy_fails_restores_previous_payload[oserror\|ctrl_c]`, `test_rollback_restore_fails_keeps_and_names_the_aside[*]`. `env.pop("KITTY_WINDOW_ID", None)` sits at test_h25_scene_launcher.py:393 and test_scene_recipe_e2e.py:80,125. The AST rule `test_integration_env_hygiene.py` runs in the ungated unit tree, and the runner also scrubs `KITTY_*` (integration_runner.py SCRUBBED_VARIABLES). |
| 5 | Remaining minors each have a regression test: install log removed; launcher `int(stdout)` guarded; empty/whitespace color treated as absent, passthrough `rgb:` only; `prune --keep <0` is an argparse error; teardown stays `close-window`; PATH-migration messages printed; unsupported-shell hint prints the export plus an explicit no-completion line | ✓ VERIFIED | `rg 'install\.log\|_record_install_log' src/` finds nothing, pinned by `test_install_log_producer_is_gone`. The launcher uses `_window_id_from`, which raises `SceneClientError` (launcher.py:169-182) at all 3 sites, pinned by `test_window_id_rejects_non_id_stdout_cleanly`. Spot-check of `normalize_color`: `''`→None, `'   '`→None, `rgb:ff/00/00` passes, `rgba:…`, `rgb(1,2,3)`, `hsl(…)` and `foo:bar` each raise ColorError. background/accent send no kitten call when the color is absent. `uv run my-kitty prune --backups --keep -1` → `error: argument --keep: must be >= 0, got -1`, exit 2. kitty_session.py:324 has `close-window --match=all`, pinned by `test_teardown_never_uses_close_os_window`. `_print_path_result` prints `result.reason`, pinned by `test_path_report_reason_printed[migrated-legacy\|removed-duplicate]`. The unsupported-shell `manual_lines` = export plus `# completion is not set up for <shell>: …` (path_integration.py:213-224), pinned by `test_print_path_result_unsupported_shell_prints_manual_lines_without_completion`. |
| 6 | ruff, black, pyright, bandit, vulture all clean for `src/` (R0.11) | ✓ VERIFIED | All five gate commands exit 0 (table above). src/ has no `noqa`, `type: ignore`, `pyright: ignore` or `nosec`. Every ruff per-file-ignore and every bandit skip (B404/B603/B604/B607/B310) carries a written reason. `shell=True` does not occur in src/. The B310 compensating control is real: `_download_installer` raises ValueError on a non-https scheme before `mkstemp`/`urlopen` (installer.py:161-169). |
| 7 | `make test-integration` runs all of `tests/integration/` headless and reports its real count; `make test` stays unit-fast; a no-compositor run fails loudly; dead code deleted; only framework idioms allowlisted; fixtures excluded via `ignore_decorators` | ✓ VERIFIED | Headless run: `78 passed in 46.11s`, with the verdict read from the child's status file. `make test` finishes in 8.22s. No-compositor spot-check (`env PATH=/nonexistent .venv/bin/python -m kitty_setup.harness.integration_runner -q`) → `FAILED — no nested compositor found … NOT run; this is a failure, not a skip.`, exit 69. Widening spot-check (`… integration_runner tests/unit`) → usage error, exit 64. `vulture_allowlist.py` holds exactly `completer`, `exc_type`, `tb`, `pytest_collection_modifyitems` and `BASH`, each with a reason. `[tool.vulture] ignore_decorators = ["@pytest.fixture"]` is in place. Dead code is deleted rather than allowlisted: `send_key` and `TARGET_DIR_REL` are gone, and so is the `env_path` kwarg (compare the installed-vs-HEAD diff). |

**Score:** 7/7 truths verified (0 present-but-behavior-unverified)

### Deferred Items

| # | Item | Addressed In | Evidence |
|---|------|--------------|----------|
| 1 | Parse check blind to a missing own-payload `include`, and skipped on an unchanged-conf reinstall, so rollback never engages there | Phase 5 | STATE.md Pending Todos (recorded correctly, with evidence pointer `02-05-SUMMARY.md § T-2-19`) |
| 2 | `my-kitty window background none` exits 1 | Phase 6 | STATE.md Blockers; 02-06-SUMMARY pins it unchanged |
| 3 | zsh plugin managers that defer `compinit` past `~/.zshrc` undo registration while doctor PASSes | Disclosed limitation (no owning phase needed) | README.md:161-165; 02-VALIDATION manual-only row |
| 4 | Phase 1 branch merge | Phase 2 end (Universal Phase Gate step 6) | STATE.md Blockers [Phase 1]; `PHASE-1-DOCTOR-CARVE-OUT` absent from AGENTS.md/ROADMAP.md/PROJECT.md (`rg` exit 1) |

All four are recorded where the orchestrator said they would be. None is mis-recorded.

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `src/kitty_setup/installer.py` | in-process completion generation, install-log removal, https guard, honest PATH report | ✓ VERIFIED | substantive and wired into `cli_install`/`cli_uninstall` |
| `src/kitty_setup/path_integration.py` | per-shell rc block sourcing the static file; honest unsupported-shell lines | ✓ VERIFIED | block body is live in `~/.bashrc` |
| `src/kitty_setup/doctor.py` | completion check, real SKIP state, parse-check label/command | ✓ VERIFIED | exercised by `make doctor` |
| `src/kitty_setup/config_updater.py` | parse check reports command and stderr, with payload rollback | ✓ VERIFIED | 11 rollback/parse unit tests |
| `src/kitty_setup/scenes/{launcher,colors,accent,background}.py` | quoting, `bash -lc`, int guard, absent color, `rgb:`-only passthrough | ✓ VERIFIED | unit tests plus real-kitty fill-tab e2e |
| `src/kitty_setup/cli.py` | `_non_negative_int` on `--keep`/age | ✓ VERIFIED | live spot-check exit 2 |
| `src/kitty_setup/harness/integration_runner.py` | headless runner, loud failure, verdict from the status file | ✓ VERIFIED | 349 lines, wired via Makefile `test-integration` |
| `tools/uninstall.sh` | stderr logging and the legacy branch | ✓ VERIFIED | subprocess tests in a fake HOME |
| `Makefile` | `clean` safe and help-consistent; `test-integration` target | ✓ VERIFIED | every target is ≤5 lines |
| `pyproject.toml`, `vulture_allowlist.py` | justified tool configuration | ✓ VERIFIED | every exemption carries a reason |

### Key Link Verification

| From | To | Via | Status |
|------|----|-----|--------|
| `Makefile:test-integration` | `kitty_setup.harness.integration_runner` | `uv run python -m …` | WIRED |
| `cli_install` | `write_completion_script(path_result.shell)` | direct call after the rc edit | WIRED |
| rc block (`~/.bashrc`) | `~/.local/share/kitty-setup/my-kitty-completion.bash` | `[ -f … ] && . …` | WIRED (live file) |
| `doctor._check_completion` | `installer.completion_script_path` / `generate_completion_script` / `path_integration._block_body_matches_template` | same predicates install uses | WIRED |
| `doctor._check_parse` | `config_updater.parse_check` | shared function, reports `result.command` | WIRED |
| `Makefile:clean` | `my-kitty uninstall --keep-kitty --keep-backups` | recipe | WIRED |
| `set_window_background` / `set_tab_accent` | `normalize_color` → `None` short-circuit | no kitten call when the color is absent | WIRED |

### Data-Flow Trace (Level 4)

Not applicable. This phase has no rendered dynamic UI data. Doctor's output lines come from live filesystem and subprocess probes, as the `make doctor` transcript above shows.

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| prune rejects negative keep | `uv run my-kitty prune --backups --keep -1` | `error: argument --keep: must be >= 0, got -1`, exit 2 | ✓ PASS |
| color normalisation | `uv run python -c '…normalize_color…'` over 9 inputs | absent → None; only `rgb:` passes; kitty-rejected forms raise | ✓ PASS |
| runner fails loudly with no compositor | `env PATH=/nonexistent .venv/bin/python -m kitty_setup.harness.integration_runner -q` | `FAILED — … NOT run; this is a failure, not a skip.`, exit 69 | ✓ PASS |
| runner refuses to widen | `.venv/bin/python -m kitty_setup.harness.integration_runner tests/unit` | usage error, exit 64 | ✓ PASS |
| named R1.2/R1.3/R1.4/R1.7 unit tests | `uv run pytest -q tests/unit/test_tools_uninstall_sh.py tests/unit/test_makefile_targets.py tests/unit/test_harness_teardown.py tests/unit/test_scenes_launcher.py -k '…'` | `28 passed` | ✓ PASS |
| integration collection count | `uv run pytest tests/integration --collect-only -q \| rg -c '::'` | 78 | ✓ PASS |

### Probe Execution

No probe scripts are declared by the phase plans; `scripts/*/tests/probe-*.sh` does not exist in this repo. SKIPPED.

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|-------------|-------------|--------|----------|
| R1.1 | 02-01, 02-02 | Static completion file, doctor checks the file plus the rc source line | ✓ SATISFIED | SC1 |
| R1.2 | 02-03 | `make clean` matches its help and never deletes kitty.app or backups | ✓ SATISFIED | SC2 |
| R1.3 | 02-03 | uninstall.sh logs to stderr; legacy branch works | ✓ SATISFIED | SC2 |
| R1.4 | 02-04 | pane-0 cwd quoted, pane-0 `bash -lc` | ✓ SATISFIED | SC3 |
| R1.5 | 02-05 | parse check reports command and stderr, rolls back, label fixed | ✓ SATISFIED | SC4 (the missing-include gap is outside R1.5 and deferred to Phase 5) |
| R1.6 | 02-08 | integration tests strip `KITTY_WINDOW_ID` | ✓ SATISFIED | SC4 |
| R1.7 | 02-04..02-08 | minor defects | ✓ SATISFIED | SC5 |
| R0.11 | 02-09, 02-10 | src clean under all five tools | ✓ SATISFIED | SC6 |
| R0.13 | 02-09, 02-10, 02-11 | integration suite runs headless in the gate | ✓ SATISFIED | SC7; ROADMAP Universal Phase Gate step 5 now requires the captured integration output |

No orphaned requirements: every Phase 2 ID in ROADMAP is claimed by at least one plan. Note that **R0.13 has no row in REQUIREMENTS.md's traceability table** (see W2).

`tests/` non-regression against the `5452f54` baseline (Universal Phase Gate): ruff over src+tests+tools went from 28 to 19, black from 11 files to 10, pyright on tests from 556 to 535 errors (571 − 15 at baseline), and vulture on `src tests` from 12 to 10. No tool grew. The ten test files Phase 2 added pass ruff, black and pyright with 0 errors, and whole-tree vulture reports them clean.

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| (50 phase-modified files) | — | `TBD\|FIXME\|XXX` | — | none found |
| (50 phase-modified files) | — | `TODO\|HACK\|PLACEHOLDER` | — | none found |
| `src/kitty_setup/doctor.py` | 1-6, 305 | module docstring says output is `PASS\|FAIL`, and the `cli_doctor` docstring names `my-kitty-setup doctor` | ℹ️ Info | stale wording only; the output does include SKIP. This falls under Phase 8's doc hygiene |
| `tmp/install.log` | — | leftover `kitty 0.46.2` line dated 2026-07-14, written by the pre-removal installer | ℹ️ Info | not rewritten by anything at HEAD; `make clean` wipes `tmp/` |
| `tests/unit/test_installer_completion.py`, `tests/integration/test_completion_e2e.py`, `tests/unit/test_kitty_session_env.py` | several | bandit B604 ×8 (the same `shell=` kwarg false positive justified for src) and B108 ×1 | ℹ️ Info | `tests` is excluded from bandit by `[tool.bandit] exclude_dirs`, so nothing is gated |

### Warnings (non-blocking)

- **W1: the installed binary is stale relative to HEAD.** `~/.local/share/uv/tools/kitty-setup/.../direct_url.json` points at `.claude/worktrees/agent-af203166903a592d0`, installed 07:59, and `diff -rq src/kitty_setup <site-packages>/kitty_setup` shows 9 differing modules. The installed copy still has `_record_install_log` and lacks `_non_negative_int`. `make doctor`, the gate AGENTS.md names, therefore ran pre-02-07 code. The doctor, completion and rc-block paths differ only by symbol renames, and HEAD-source doctor gives the identical 8 PASS / 1 SKIP. Routed to human verification item 1: reinstall, then re-run `make doctor` before the phase merge.
- **W2: tracking artifacts were not updated for phase completion.** REQUIREMENTS.md has no traceability row for R0.13, and R0.11 and R1.1–R1.7 are still `[ ]` / `Pending`. The ROADMAP Phase 2 entry still reads `**Plans**: TBD`, with a `[ ]` checkbox and a progress row of `0/TBD Not started`. The STATE.md frontmatter says `status: planning`, and its body says "6 of 11 … 02-06..02-10 are under plan revision". 02-VALIDATION.md frontmatter is still `status: draft`, `nyquist_compliant: false`. This is bookkeeping for the orchestrator's phase-complete step, but the missing R0.13 row needs adding by hand, or a tool keyed on the table will not mark it.
- **W3: three hypothesis evidence directories are absent from the primary checkout.** `tmp/h30-argcomplete-static`, `tmp/h31-uninstall-sh` and `tmp/h35-headless-integration` were produced in agent worktrees that have since been removed; `tmp/` is gitignored. Their evidence survives as verbatim quotes in 02-01/02-02, 02-03 and 02-11 SUMMARY, which is the durable record 02-VALIDATION's manual-only row sanctions. h32, h33, h34, h36, h37 and r011-sizing are present.

### Human Verification Required

#### 1. Fresh HEAD install, then doctor

**Test:** From `d4a3a8c` (or the phase tip), run `make install`, then `make doctor`.
**Expected:** Exit 0 with nine lines, all PASS or SKIP, and no new `tmp/install.log`.
**Why human:** The installed tool predates 02-07..02-10 (W1). The verifier may not install.

#### 2. Real Tab completion

**Test:** In a new login bash (and zsh, if used) shell, type `my-kitty <Tab>`.
**Expected:** Subcommands are offered.
**Why human:** No pty keypress is driven by any test (02-VALIDATION manual-only). The deferred-compinit case is a disclosed limitation, not a failure.

### Gaps Summary

No blocking gaps. Every roadmap success criterion and every requirement the phase claims (R1.1–R1.7, R0.11, R0.13) is implemented in the source, wired, and pinned by tests that pass in this session: 481 unit, 78 headless integration, and all five src quality tools clean. The known deferrals are recorded where expected. Status is `human_needed` rather than `passed` for two reasons. First, the `make doctor` evidence ran an installed binary built from a mid-phase worktree, so "doctor green on a fresh install" has not been shown at HEAD. Second, interactive Tab completion is manual-only by the phase's own validation contract. W2 (the REQUIREMENTS/ROADMAP/STATE bookkeeping, including the missing R0.13 traceability row) should be fixed in the phase-complete step before the merge.

---

_Verified: 2026-09-24T13:39:04Z_
_Verifier: Claude (gsd-verifier)_

## Human Verification — Resolution (orchestrator, 2026-09-24)

1. **Fresh install from HEAD, then doctor.** `make install` from the primary checkout at `d4a3a8c` →
   exit 0 (`config: already up to date`, `PATH: already configured`, `completion: wrote
   ~/.local/share/kitty-setup/my-kitty-completion.bash`). `sha256sum ~/.bashrc ~/.zshrc
   ~/.config/kitty/kitty.conf` identical before and after (`diff` of the two hash lists → empty), and
   the `~/.config/kitty/` listing unchanged. Then `make doctor` → exit 0: eight `PASS` lines and
   `SKIP remote-control: no running kitty`, now executing HEAD's code (W1 resolved).
2. **Completion in a real shell.** `bash --norc --noprofile -c 'source
   ~/.local/share/kitty-setup/my-kitty-completion.bash && complete -p my-kitty'` → `complete -o
   bashdefault -o default -o nospace -F _python_argcomplete my-kitty`; the installed binary answers
   argcomplete's protocol: `COMP_LINE='my-kitty '` → `-h --help install uninstall doctor prune keys
   window tab os-window scene help`, and `COMP_LINE='my-kitty uninstall --keep'` → `--keep-backups
   --keep-config --keep-kitty`; `~/.bashrc:72` sources the generated file inside the my-kitty
   sentinel block. A physical Tab keypress in the user's own terminal stays on 02-VALIDATION's
   manual-only list by design — it is not a gate, and no test may drive the user's live terminal.


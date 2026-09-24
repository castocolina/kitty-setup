# Phase 2 — Cross-AI Plan Review

**Reviewer:** `opencode run --auto --model router-env/my-plan-review` (from `review.models.opencode`)
**Reviewed snapshot:** `a200767` (the committed 11-plan set)
**Method:** three lanes run **sequentially**, not in parallel. Phase 1's cycle 4 measured
parallel dispatch failing with `Structurally heavy chat request capacity is busy` and a single
96k-token prompt failing admission. Each lane got a lean prompt and read the plans off disk
itself. Each ran in a throwaway `git worktree` at `a200767`, so the reviewer could run read-only
verification (`rg`, `git log`, pytest collection) without any risk to the repo. Edits were
counted and then discarded, and none were attempted.

| Lane | Plans | rc | Duration | Edits attempted | Findings |
|---|---|---|---|---|---|
| A | 02-11, 02-01, 02-02 | 0 | 707 s | 0 | 6 HIGH, 2 MEDIUM, 1 LOW |
| B | 02-03 … 02-08 | 0 | 977 s | 0 | 3 HIGH, 4 MEDIUM |
| C | 02-09, 02-10, 02-VALIDATION | 0 | 830 s | 0 | 8 HIGH, 2 MEDIUM |
| **Total** | | | | | **17 HIGH, 8 MEDIUM, 1 LOW** |

No `opencode` process, worktree or scratch file survived the run.

## Disposition

The orchestrator checked every finding against the tree before routing it. Resolutions fall into
three kinds:

**The rule was stale, not the plan, so the rule was amended** (`792ef8b`):
- **A1:** `02-11`'s runner route broke the letter of `AGENTS.md` Stack. The rule gained a narrow
  exception for developer-only harness modules run with `python -m`, rather than shipping a pytest
  runner in the end-user CLI.
- **A4:** R1.7/D-13's "prints both lines" predates the static completion file and would hand a fish
  user a bash line. It was reworded to what `02-02` already specified.

**Already executed, so recorded rather than redone:**
- **A6** (`02-11` hypothesis directory created late): the mechanism was measured three times
  before the plan existed. The substance is recorded in `02-11-SUMMARY.md`.

**Routed to the plan-revision pass (all others).** The notable ones:
- **B2** is a data-loss bug in `02-05`'s rollback. A generic `finally` could delete the set-aside
  payload after `copytree` failed, leaving neither directory. It is rewritten as an explicit state
  machine in which the aside is deleted only after a committed success.
- **C1**, confirmed and widened by the orchestrator: bandit 1.9.4 does not auto-load
  `pyproject.toml`. `uv run bandit -q -r src tests` reports **1094** issues and the same run with
  `-c pyproject.toml` reports **30**. So the existing `[tool.bandit] exclude_dirs` never applied to
  an unqualified run. It was dead configuration, recorded as active by Phase 1.
- **C2** and **C3** were proven hollow by simulation. The baseline gate passed with `999`
  substituted, and the criteria gate passed with all seven Phase 2 criteria deleted.

**A systemic finding outside the review**, found by the `02-11` executor: from a harness worktree
the kitty control socket path was 114 bytes, over the 108-byte `sun_path` limit. The integration
suite could not run from where every phase executes, so R0.13 was not met. This was fixed inside
`02-11` before merge (socket moved under `$XDG_RUNTIME_DIR`, 34 bytes). The fix was proven with
`70 passed` from inside a worktree.

## Raw lane output

### Lane A

```
FINDING HIGH .planning/phases/02-defect-remediation/02-11-PLAN.md:124 — The plan deliberately routes nontrivial tooling through a Python module even though the canonical Stack rule requires anything beyond the allowed Bash dispatchers to be a `my-kitty` subcommand. || EVIDENCE: `rtk rg -n 'anything beyond them is a|subcommand under|Runner route: a harness module run as' AGENTS.md .planning/phases/02-defect-remediation/02-11-PLAN.md` → plan line 124 selects the module while AGENTS.md:108-110 requires a subcommand.
FINDING HIGH .planning/phases/02-defect-remediation/02-01-PLAN.md:256 — Task 2 adds behavioral tests only after the RED commit, so those new tests land in GREEN and violate the required tests-only RED topology. || EVIDENCE: `rtk rg -n 'RED first|Extend \`tests/unit/test_installer_completion.py\`|staging the implementation, the tests|RED commit of the new tests only' AGENTS.md .planning/phases/02-defect-remediation/02-01-PLAN.md` → RED is committed at line 204, Task 2 tests are added at line 256, GREEN stages tests at line 284, while AGENTS.md:69 requires new tests in RED.
FINDING HIGH .planning/phases/02-defect-remediation/02-02-PLAN.md:332 — Task 3 creates four behavioral integration tests after the shared RED commit, so they cannot genuinely fail in RED and instead land with implementation in GREEN. || EVIDENCE: `rtk rg -n 'RED first|same RED commit|Create \`tests/integration/test_completion_e2e.py\`|GREEN commit staging|RED commit of the new tests only' AGENTS.md .planning/phases/02-defect-remediation/02-02-PLAN.md` → RED is fixed by lines 207/289, the integration test is first created at line 332, GREEN stages it at line 385, contrary to AGENTS.md:69.
FINDING HIGH .planning/phases/02-defect-remediation/02-02-PLAN.md:195 — The plan explicitly narrows the locked R1.7/D-13 deliverable from printing both unsupported-shell hint lines to omitting the completion line. || EVIDENCE: `rtk rg -n 'unsupported-shell hint prints \*\*both\*\*|unsupported-shell hint prints both lines|there is no correct source line|narrowing of D-13' .planning/phases/02-defect-remediation/02-CONTEXT.md .planning/REQUIREMENTS.md .planning/phases/02-defect-remediation/02-02-PLAN.md` → CONTEXT:49 and REQUIREMENTS:167 require both lines, but plan lines 195-199 replace that requirement.
FINDING HIGH .planning/phases/02-defect-remediation/02-01-PLAN.md:167 — Implementation is ordered before creation of the required in-repo hypothesis directory, contradicting the canonical hypothesis-before-implementation rule. || EVIDENCE: `rtk rg -n 'Hypothesis before implementation|Add to \`src/kitty_setup/installer.py\`|Create \`tmp/h30-argcomplete-static/' AGENTS.md .planning/phases/02-defect-remediation/02-01-PLAN.md` → AGENTS.md:39 requires the hypothesis first, while implementation starts at line 167 and evidence is only created at line 262.
FINDING HIGH .planning/phases/02-defect-remediation/02-11-PLAN.md:255 — The runner is implemented before `tmp/h35-headless-integration/` is created, reversing the canonical hypothesis-before-implementation order. || EVIDENCE: `rtk rg -n 'Hypothesis before implementation|Then the one path, end to end|Hypothesis evidence.*Create \`tmp/h35' AGENTS.md .planning/phases/02-defect-remediation/02-11-PLAN.md` → AGENTS.md:39 requires hypothesis first, implementation begins at line 255, and hypothesis evidence is deferred to line 407.
FINDING MEDIUM .planning/phases/02-defect-remediation/02-02-PLAN.md:225 — The gate pins five `reason=` assignments although the current file has six and the refactor does not remove an outcome, so correct work fails unless the plan is silently altered during execution. || EVIDENCE: `rtk rg -c 'reason=' src/kitty_setup/path_integration.py; rtk rg -n "rg -c 'reason='|number of distinct.*reason" .planning/phases/02-defect-remediation/02-02-PLAN.md` → `6`, while line 225 requires `5` and line 226 acknowledges the sixth.
FINDING MEDIUM .planning/phases/02-defect-remediation/02-11-PLAN.md:338 — KeyboardInterrupt process-group cleanup is required behavior but is absent from both the named RED cases and the selector-scoped verification gate, permitting it to ship untested. || EVIDENCE: `rtk rg -n 'process group is also terminated.*KeyboardInterrupt|no_compositor or runtime_dir or always_zero or missing_status or leftover or timeout or forge' .planning/phases/02-defect-remediation/02-11-PLAN.md` → line 338 requires interrupt cleanup, while line 375 selects no interrupt case.
FINDING LOW .planning/phases/02-defect-remediation/02-11-PLAN.md:430 — The definitive whole-suite gate can fail on correct work whenever the user independently opens or closes kitty during the 45-second run. || EVIDENCE: `rtk rg -n 'K0=.*pgrep -x kitty|user opens or closes a kitty window.*red on correct work' .planning/phases/02-defect-remediation/02-11-PLAN.md` → lines 430-431 compare all host kitty PIDs and explicitly admit this false failure.
COUNTS: HIGH=6 MEDIUM=2 LOW=1
```

### Lane B

```
FINDING HIGH .planning/phases/02-defect-remediation/02-04-PLAN.md:210 — The plan requires a new `SceneLaunchError` but never defines where it is declared or adds it to either CLI catch list, so malformed launch stdout will still escape as an uncaught traceback. || EVIDENCE: `rtk rg -n 'class SceneLaunchError|except SceneLaunchError|except (ColorError|SceneClientError)' src/kitty_setup/scenes/launcher.py` → only `ColorError`/`SceneClientError` catches at lines 463,466,495,498; no `SceneLaunchError` exists.
FINDING HIGH .planning/phases/02-defect-remediation/02-05-PLAN.md:238 — The rollback algorithm promises exactly one payload directory after any exception but specifies a `finally` cleanup that can delete the aside after `copytree` fails, leaving neither directory and destroying the previous payload. || EVIDENCE: `src/kitty_setup/config_updater.py:237-240` currently performs destructive replacement before later parse validation; plan lines 232-241 require rename-aside plus generic `finally` cleanup without specifying commit/restore state.
FINDING HIGH .planning/phases/02-defect-remediation/02-08-PLAN.md:164 — The two R1.6 production fixes are test-file edits but the plan says to make them after the RED commit, while its RED-scope gate only checks that paths begin with `tests/`, so the supposedly RED commit can include both fixes and be fully green. || EVIDENCE: `rtk rg -n 'Add env.pop|RED first|RED commit contains only files under tests|git diff-tree.*02-08' 02-08-PLAN.md` → fixes at line 164, RED instruction at 196, tests-only criterion at 207, and path-only gate at 361.
FINDING MEDIUM .planning/phases/02-defect-remediation/02-05-PLAN.md:171 — Truncating the recorded command contradicts R1.5’s deliverable to report the actual command and the immediately preceding copy-pasteable-command contract. || EVIDENCE: `rtk rg -n 'actual command used|actually passes|copy-pasteable|truncate it in command' .planning/REQUIREMENTS.md 02-05-PLAN.md` → requirement at REQUIREMENTS.md:148, exact/copy-pasteable command at plan:168, truncation at plan:171.
FINDING MEDIUM .planning/phases/02-defect-remediation/02-05-PLAN.md:339 — The SKIP gate can pass after changing only two of the three required sites because 02-02 already adds one unrelated `skipped=True`, making the `>=3` total insufficient. || EVIDENCE: `rtk rg -n 'skipped=True' src/kitty_setup/doctor.py 02-02-PLAN.md 02-05-PLAN.md` → 02-02 mandates one at line 259 while 02-05 gates only a total of three at line 339.
FINDING MEDIUM .planning/phases/02-defect-remediation/02-05-PLAN.md:113 — The plan repeatedly names a nonexistent `ConfigUpdateResult`, leaving the public type contract and referenced test target factually wrong. || EVIDENCE: `rtk rg -n 'ConfigUpdateResult|class InstallResult' 02-05-PLAN.md src/kitty_setup/config_updater.py` → four plan references to `ConfigUpdateResult`; tree defines only `InstallResult` at config_updater.py:83.
FINDING MEDIUM .planning/phases/02-defect-remediation/02-07-PLAN.md:144 — Removing `_record_install_log` is a behavior removal but this plan specifies no hypothesis directory or recorded pre-decision experiment, violating AGENTS.md’s mandatory removal workflow. || EVIDENCE: `rtk rg -n 'Delete _record_install_log|tmp/h|repro.md|run.py|actual.json' 02-07-PLAN.md` → only the deletion at line 144; no hypothesis artifact instructions or gates.
COUNTS: HIGH=3 MEDIUM=4 LOW=0
```

### Lane C

```
FINDING HIGH .planning/phases/02-defect-remediation/02-10-PLAN.md:231 — The planned Bandit `skips` in `pyproject.toml` cannot make the unqualified `uv run bandit -q -r src` gate green because Bandit does not auto-load that file. || EVIDENCE: `uv run python -c 'import inspect, bandit.cli.main as m; ...'` → `auto_pyproject False`, `discovers_dot_bandit True`, `config_requires_option True`; current `uv run bandit -q -r src` → exit 1 with 27 issues.
FINDING HIGH .planning/phases/02-defect-remediation/02-10-PLAN.md:454 — The baseline-correction gate checks only that old `19` phrasings disappeared, so arbitrary replacements pass while the required pyright 15 and vulture 16 values remain absent or wrong. || EVIDENCE: replacing both `19` phrases with `999` in memory and evaluating the planned predicates → `planned_gate_passes=True`, `correct_pyright_15_present=False`, `wrong_vulture_12_survives=True`.
FINDING HIGH .planning/phases/02-defect-remediation/02-10-PLAN.md:452 — The supposed Phase 2 criteria-integrity check counts numbered criteria across the entire roadmap, so deleting all seven Phase 2 criteria still passes its `-ge 7` floor. || EVIDENCE: Python count over `.planning/ROADMAP.md` → `total=64 phase2=7 after_deleting_phase2=57 gate_floor=7 passes=True`.
FINDING HIGH .planning/phases/02-defect-remediation/02-VALIDATION.md:254 — Validation says 02-10 task 3 runs all four map-completeness gates, but 02-10 contains none of them and does not modify `02-VALIDATION.md`, leaving 28 pending rows and `nyquist_compliant: false` unchecked at phase close. || EVIDENCE: `rg -n 'Map Completeness|nyquist_compliant|⬜ pending' 02-10-PLAN.md` → no matches; the same search in `02-VALIDATION.md` finds `nyquist_compliant: false`, the Map Completeness Gate, and all pending rows.
FINDING HIGH .planning/phases/02-defect-remediation/02-10-PLAN.md:400 — No automated gate verifies that ROADMAP criterion 6 was changed to the settled vulture command, despite that being a required deliverable inherited by every later phase. || EVIDENCE: `rg -n '<automated>.*ROADMAP' 02-10-PLAN.md` → only lines 452 and 454, which check section counts and stale baseline text, not the vulture command.
FINDING HIGH .planning/phases/02-defect-remediation/02-10-PLAN.md:460 — Phase-close evidence captures `my-kitty doctor` instead of the canonically required `make doctor` output. || EVIDENCE: `rg -n 'Verify before declaring done|make doctor|Every gate in this phase is written against' AGENTS.md 02-VALIDATION.md 02-10-PLAN.md` → `AGENTS.md:87-88` requires `make doctor` output, while `02-VALIDATION.md:52` explicitly says every phase gate uses `my-kitty doctor`.
FINDING HIGH .planning/phases/02-defect-remediation/02-10-PLAN.md:190 — The plan claims it adds no behavior even though it introduces rejection of non-HTTPS installer URLs and changes runtime-directory fallback behavior, without the hypothesis directory and recorded experiment AGENTS.md requires before such implementation. || EVIDENCE: `rg -n 'tmp/|hypothesis|experiment' 02-10-PLAN.md` → no matches; `rg -n '_download_installer|urlopen' src/kitty_setup/installer.py` → `_download_installer(url: str = INSTALLER_URL)` currently accepts caller-supplied URLs.
FINDING HIGH .planning/phases/02-defect-remediation/02-10-PLAN.md:283 — The HTTPS control is “verified” only by finding the text `https` within four source lines before `urlopen`, which a comment or dead expression can satisfy, and no test exercises rejection of a non-HTTPS URL. || EVIDENCE: `rg -n '_download_installer|INSTALLER_URL|urlopen' tests src/kitty_setup/installer.py` → matches only `src/kitty_setup/installer.py`; zero test references exist.
FINDING MEDIUM .planning/phases/02-defect-remediation/02-10-PLAN.md:293 — The five public renames omit five test files that directly reference the old private symbols, so execution following the declared file scope leaves stale monkeypatch targets and helper references. || EVIDENCE: `rg -l -- '_parse_listen_on_base|_pgrep_kitty_pids|_kitty_bin|_parse_check|_find_block' tests` finds unlisted `tests/unit/test_doctor_remote_control.py`, `tests/unit/test_scenes_client.py`, `tests/integration/_kitty_subprocess.py`, `tests/integration/test_client_socket_discovery.py`, and `tests/integration/test_h22_window_title.py`.
FINDING MEDIUM .planning/phases/02-defect-remediation/02-10-PLAN.md:279 — The RUF100 diagnostic gate ignores Ruff’s exit status, so a Ruff crash or invocation error with no literal `RUF100` is reported as success. || EVIDENCE: the command stores `OUT="$(uv run ruff ...)"` without testing `$?`, then passes whenever `rg -c 'RUF100'` exits 1; the later whole-tool gate catches this only at task 3, not at the task-1 checkpoint this gate claims to verify.
COUNTS: HIGH=8 MEDIUM=2 LOW=0
```

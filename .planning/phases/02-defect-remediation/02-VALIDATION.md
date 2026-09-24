---
phase: "2"
slug: "defect-remediation"
# status lifecycle: draft (seeded by plan-phase) → validated (set by validate-phase §6)
status: draft
nyquist_compliant: false
wave_0_complete: false
created: "2026-09-23"
---

# Phase 2 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.
> Sourced from `02-RESEARCH.md` "Validation Architecture", which established that unlike Phase 1 —
> whose requirements were documentation, config and git-hook assertions — **every requirement in this
> phase is application behaviour**, so the right instrument is almost always a pytest case in the
> ungated `tests/unit/` tree, with a real-kitty integration case where the behaviour only exists
> against a live terminal, and a tool invocation for R0.11.
>
> One requirement is different in kind and is the reason the phase exists: **R1.1 is a release gate for
> two phases.** `make doctor` exits 2 today with one FAIL, and Phase 1's merge is deferred until it
> exits 0. The doctor spine gate below therefore appears in five plans, not one.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 8.3.0 (`[tool.pytest.ini_options]` in `pyproject.toml`) — pre-existing, not introduced by this phase |
| **Config file** | `pyproject.toml` |
| **Quick run command** | `uv run pytest tests/unit -x` |
| **Full suite command** | `make test` |
| **Integration suite (R0.13)** | `make test-integration` (created by `02-11`): all of `tests/integration/` headless under a nested compositor (`cage`), pytest's own verdict read from the child's status file, `PYTEST_ARGS='<files> -k <expr> -q'` for a subset. It fails loudly (exit 69), never skips, when no compositor exists. Needs kitty and `cage`, and never opens a window on the desktop. Since `02-11` task 4, kitty's control socket lives under `$XDG_RUNTIME_DIR` rather than under the checkout, so the suite also runs from a phase worktree |
| **Quality gate (R0.11)** | `uv run ruff check src` · `uv run black --check src` · `uv run pyright src` · `uv run bandit -c pyproject.toml -q -r src` · `uv run vulture src tests vulture_allowlist.py` (bandit reads `pyproject.toml` only through `-c`; the vulture command is the one `02-10` task 3 recommends, and the one it settles replaces it here) |
| **Behaviour gate (spine)** | `make doctor`, which runs the installed `my-kitty doctor` — nine checks, every one PASS or SKIP, exit 0 |
| **Estimated runtime** | ~8 s for `make test` (2.97 s at `bbed580`; 7.97 s at `be69103`, after `02-11`'s subprocess-driven unit cases); ~44 s for the whole integration suite (43.66 s through the planning-session prototype of `02-11`'s runner at `bbed580`, 43.81 s and 43.89 s by hand at `1eb86bd` and `bde7589`, and 44.0 s through the shipped runner at `be69103`) |

**The integration-gate trap, restated because this phase adds two integration modules.**
`tests/conftest.py:44-53` skips *every* item under `tests/integration/` unless `KITTI_INTEGRATION=1`.
A verify command pointed there without the variable **reports green while running nothing**. Two
consequences are wired into the plans. First, every integration gate in this phase goes through
`make test-integration` (`02-11`, R0.13), which sets the variable for the child only, runs headless, and
fails loudly when it cannot run. Each gate also asserts pytest's own passing count and the absence of
`failed|error` in captured output, so a silent skip fails the gate — and so does a wrapper whose exit status
is not pytest's (gate rule 7). Second, `02-08`'s
env-hygiene AST rule was deliberately moved out of `tests/integration/` into
`tests/unit/test_integration_env_hygiene.py` — a static rule over integration sources needs no kitty,
and placing it in the gated tree would have made it invisible in a plain `make test`.

**`make doctor` versus `my-kitty doctor`.** `doctor.py:263` returns 1 on failure, and `make` turns that
into its own exit 2. Every spine gate in this phase runs `make doctor`, because `AGENTS.md`'s
verify-before-done rule and the Universal Phase Gate both name it. The gate captures make's status before
reading the lines. A red run still names the failing check: doctor prints its `FAIL` line before make adds
`make: *** [Makefile:32: doctor] Error 1`. `Makefile:32` runs the installed binary, so a stale install is
re-made first. An earlier draft gated on `my-kitty doctor` directly; the cross-AI review held it to the
rule's own wording.

---

## Measured Baseline (at `1eb86bd`; suite, integration and vulture-scope rows re-measured at `bbed580`; tool rows re-measured at `be69103` and at the recorded `5452f54` in the 2026-09-23 revision)

Every floor gate in this phase is anchored to these numbers. They were re-measured rather than inherited.
`bbed580` is a documentation-only descendant of `22b99f1`, and `src/` is byte-identical to `1eb86bd`'s,
so the five `src` tool rows still hold. Only `tests/unit/test_git_hooks.py` and `tools/hooks/pre-push`
changed in between (Phase 1's `01-06`).

| Instrument | Measured | Recorded in `.planning/` | Note |
|------------|----------|--------------------------|------|
| `uv run pytest tests/ -q` (`make test`) | **314 passed, 0 failed, 70 skipped** at `bbed580` (the same suite as `22b99f1` and `8faae07`); it was 311 at `1eb86bd` | 311 — stale since the rebase onto Phase 1's gap-closure tip | `01-06` added three tests (`tests/unit/test_git_hooks.py` is now **21 passed**, not 18). Every whole-suite gate is `-ge 314`, never an equality: each plan in this phase adds cases, and a floor at 311 would let the three disappear unnoticed. **344 passed, 70 skipped** at `be69103`, after `02-11`; the floors stay at 314, because no plan owns the increase |
| `make test-integration` (prototype of `02-11`'s runner) | **70 passed in 43.66 s**, no `cage` or `kitty` left; **70 passed in 44.0 s** through the shipped runner at `be69103`, with a harness-owned kitty sampled during the run and none after | — (R0.13 is new) | All 70 are skipped by `make test`. Every integration floor in this phase is `-ge 70` |
| `cage` | `cage-0.3.1-1.fc44`, the only nested compositor on the host (`xvfb-run`, `Xvfb`, `Xephyr`, `weston`, `sway` absent). `cage -- sh -c 'exit 7'` exited **7** | — | Cage did pass a normal exit through, but the runner still ignores its status and reads the child's status file (see `02-11` `<flagged_assumptions>`) |
| `make doctor` (runs `my-kitty doctor`) | **one FAIL** (`register-python-argcomplete not on PATH`): doctor exits 1 and make exits 2 | red, correct | That single FAIL *is* R1.1; it is Phase 1's deferred-merge precondition |
| `uv run ruff check src` | **9** findings | 28 (`src`+`tests`+`tools`) | Not a contradiction — different scopes. The `src`-only figure is recorded in `02-09`'s SUMMARY, not substituted for the repo-wide one |
| `uv run black --check src` | **2** files | 11 files (`src`+`tests`+`tools`) | Same: different scopes |
| `uv run pyright src` | **15** errors | **19** — wrong, same scope | Re-measured at `5452f54` itself: `uv run pyright` 571 errors, 15 of them in `src/`. Corrected by `02-10` task 3 |
| `uv run bandit -c pyproject.toml -q -r src` | **0 high, 8 medium, 19 low** at `1eb86bd`; **30 = 0 / 8 / 22** at `be69103` (`02-11`'s harness module added three lows: one B404, two B603) | 0 high / 8 / 19 (correct for its commit) | Whether "clean" means zero-at-any-severity or zero-high is a stated open question, not a planner decision |
| `uv run bandit -q -r src tests`, **without** `-c` | **1094** at `be69103`, against **30** with `-c pyproject.toml` | — | Bandit reads `pyproject.toml` only when `-c` names it, so `[tool.bandit] exclude_dirs` never applied to a run without `-c`. With `02-10`'s four skips written into a scratch copy, the form without `-c` still reported 30 and the `-c` form 2. Every bandit command in this phase carries `-c pyproject.toml` |
| `uv run vulture src` | **16** findings | **12** — a whole-repo figure, not a `src` one | Re-measured at `5452f54`: `uv run vulture src tests` 12, the whole repository 12, `src` alone 16. The sentence it sits in is the `tests/` baseline, whose ruff and black figures are whole-repo too. The record lacks a scope rather than holding a wrong number, so `02-10` task 3 names the scope beside the 12 instead of substituting 16 |
| `uv run vulture src tests` | **12** findings at `bbed580`; **11** at `be69103`: 4 dead (`env_path`, `TARGET_DIR_REL`, `send_key`, `_find_tab_with_window`) and 7 framework idioms (`completer` ×4, `exc_type`, `tb`, `pytest_collection_modifyitems`). `session_dir` left the list when `02-11`'s socket tests began reading it | — | ROADMAP criterion 7: `02-09` deletes the four and `02-10` allowlists the four idiom names. A scratch allowlist with exactly those names left exactly the dead findings |
| `# noqa` in `src/` | **13** (10× S603, 1× S310, 1× S108, 1× F401) | — | `.claude/conventions.md:22-24` forbids all of them; `02-09` and `02-10` remove every one |
| Every suppression comment in `src/` (`noqa\|type: ignore\|nosec\|pylint: disable`) | **17** at `bbed580`: the 13 above plus four `# type: ignore[attr-defined]` on `cli.py`'s `completer` lines | — | The four were missing from `02-10`'s inventory. Task 1 now owns them, using the measured `typing.cast(Any, …)` form |
| `codegraph status --json` | `initialized: true`, `fileCount: 88` | — | Queried with `status --json \| jq -e`, not with a symbol query, which is a different capability |
| argcomplete | 3.6.3 (repo venv) / 3.7.2 (installed tool venv); bash and zsh shellcode **byte-identical**, 2685 bytes, **zero** subcommand names | — | U-3: D-03's instruction stands, its rationale did not |

**Pitfall 10, carried from research and owned by `02-10` task 3:** merging this phase while the recorded
pyright figure is still wrong, and the vulture figure still has no scope, makes Universal Phase Gate step
5's no-regression clause vacuous for exactly those two tools. The correction is in the same commit as the work, not deferred.

---

## Sampling Rate

- **After every task verification:** that task's own `<verify>` gates — greps and `-k`-scoped pytest,
  all under ~30 s. The sampling unit is the **task's verification**, not a commit: under `AGENTS.md`'s
  commit-granularity rule a `type: tdd` plan produces exactly two commits (RED then GREEN) and every
  other plan exactly one, so there is no per-task commit to sample after.
- **After every plan:** `make test` as a floor (`-ge 314`, zero failed/errored). **Every plan in this
  phase must leave `make test` green on its own** — which is why the eleven plans are serialized one per
  wave rather than parallelized: a RED commit leaves the suite red by design, and co-wave plans sharing
  a worktree would observe each other's RED state.
- **After every plan that touches `doctor.py`, `installer.py` or `path_integration.py`:**
  the doctor spine gate, as `make doctor` (`02-02`, `02-05`, `02-07`, `02-09` and `02-10` all carry it).
- **Integration sampling:** the integration modules a plan touched, run through
  `make test-integration PYTEST_ARGS='<modules> -q'` (`02-11`'s headless runner) with a check on pytest's own
  passing count. The runner's exit status is never checked alone. The whole suite runs four times: in
  `02-11` task 3 (the runner's own proof) and task 4 (from a phase worktree, after the socket fix); in
  `02-09` task 3 (after the deletions in the harness and the integration tree, which `make test` cannot
  see); and in `02-10` task 3 (phase close, the R0.13 bullet of Universal Phase Gate step 5). The gates in
  `02-11` task 3, `02-09` task 3 and `02-10` task 3 sample **harness-owned** kitty processes, those
  carrying `WLR_BACKENDS=headless`, during and after the run. They do not compare every kitty PID, so the
  user's own kitty cannot turn one red.
- **R0.11 sampling:** the five tools. Three gates in `02-09` are **red until `02-10` lands** and say so
  in their own `<fails_when>`; they are recorded as red rather than weakened.
- **Before `/gsd-verify-work`:** `make test` green, `make test-integration` green with pytest's own
  count, the five tools clean for `src/`, the doctor spine gate green, and every row below at ✅.
- **Max feedback latency:** ~30 s for greps and unit tests; ~60 s for an integration module through the
  runner (the compositor adds about a second); the whole integration suite (~45 s) and the five-tool
  sweep are the only slower steps.

---

## Per-Task Verification Map

Task IDs assigned by the planner on 2026-09-23. **Twenty-nine rows, one per task**, across eleven plans
in eleven waves. `02-11` gained task 4, its socket fix, in the 2026-09-23 revision. Waves are strictly sequential. `02-11` is wave 1 with no dependency; it was added for
R0.13 after the other ten were written, and plan ids and waves are independent. `02-0N` is wave N+1,
`02-10` is wave 11, and each depends on the plan before it in wave order (`02-01` on `02-11`). The
dependency is a **suite-state** dependency rather than a symbol one: every plan must leave `make test`
green, and a `type: tdd` plan is red between its own two commits.

Ordering is by risk, after one piece of infrastructure. `02-11` runs first because every later integration
gate goes through the runner it creates. Then comes the phase's spine: `02-01` and `02-02` close R1.1
because that is what makes doctor green and unblocks Phase 1's merge; `02-03` through `02-08` follow in descending blast
radius; and **R0.11 is last, in its own two plans**, because three of its findings
(`kitty_session.py:291`, `path_integration.py:58`, `config_updater._parse_check`) are simultaneously
R0.11 findings *and* defect sites owned by earlier plans — cleaning them first would have meant editing
the same lines twice and would have let a formatter decide a question a defect fix owns.

The `Automated Command` column holds a command that is **re-runnable at wave 11**, so `02-10` task 3 can
re-run the whole map as phase-close evidence. Commands that are only satisfiable before their own plan's
commit (a working-tree diff, an index scope) are deliberately **not** in this column; they live inside
their plan's `<verify>` blocks, which say so in their own `<fails_when>`, and their re-runnable
equivalents appear in that plan's `<verification>` list. Commit-dependent gates that stay true once
their commit exists **are** in the column. For each `type: tdd` plan, the last task's row carries the
RED-state gate (RED's own tree, materialised through a throwaway index, fails its new tests) and the
GREEN-adds-no-test gate. Those two are what the sweep claims, so they are what phase close re-checks.
Every command is copied from its plan's `<verify>` block, with one exception. `02-05`'s own task-1 gate
also asserts that `_parse_check` kept its private name, which `02-10` then renames, so the `02-05-T1`
row keeps only the half that is still true at wave 11: a name-agnostic variant of the same AST gate,
which finds the one module-level function annotated to return `ParseCheckResult`.

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command (re-runnable at wave 11) | Host Needs | Status |
|---------|------|------|-------------|------------|-----------------|-----------|--------------------------------------------|------------|--------|
| 02-11-T1 | 02-11 | 1 | R0.13 | T-2-43, T-2-45 | **The tracer.** One real integration module runs headless end to end through `make test-integration`. The verdict is pytest's own, read from a status file the child writes inside the compositor. The compositor runs in its own session with the display and kitty remote-control variables scrubbed and stdin detached, so no window reaches the desktop and nothing reaches the user's live kitty | unit + integration | `F=src/kitty_setup/harness/integration_runner.py && test -f "$F" && rg -q '^def main\(' "$F" && rg -q 'start_new_session=True' "$F" && rg -q -- '--child' "$F" && rg -q '^test-integration:' Makefile && rg -q 'python -m kitty_setup\.harness\.integration_runner \$\(PYTEST_ARGS\)' Makefile` ; `OUT="$(make test-integration PYTEST_ARGS='tests/integration/test_h01_cwd.py -q' 2>&1)" && printf '%s\n' "$OUT" \| rg -q '(^\|[^0-9])[0-9]+ passed' && { printf '%s\n' "$OUT" \| rg -c '[0-9]+ (failed\|error)' >/dev/null; RGST=$?; test "$RGST" -eq 1; }` ; `{ pgrep -x cage >/dev/null; PC=$?; test "$PC" -eq 1; }` | kitty and `cage` on PATH, `XDG_RUNTIME_DIR` set (headless, no desktop window) | ⬜ pending |
| 02-11-T2 | 02-11 | 1 | R0.13 | T-2-43, T-2-44, T-2-46, T-2-47 | **A run that did not happen is never a pass.** No compositor, no usable `XDG_RUNTIME_DIR`, a missing status file, a leftover process and a timeout each exit non-zero with a message. An interrupt, or `SIGTERM`/`SIGHUP` to the runner itself, still kills the compositor's process group. A compositor that always exits 0 cannot turn a failing child into a pass, and the runner's own text never forges a pytest summary. **Each behaviour has its own named case**, so none can ship untested behind an `or`-joined selector | unit + shell | `for K in no_compositor runtime_dir always_zero missing_status leftover keyboard_interrupt runner_is_terminated timeout forge; do OUT="$(uv run pytest tests/unit/test_integration_runner.py -q -p no:cacheprovider -k "$K" 2>&1)" \|\| exit 1; printf '%s\n' "$OUT" \| rg -q '(^\|[^0-9])[0-9]+ passed' \|\| exit 1; { printf '%s\n' "$OUT" \| rg -c '[0-9]+ (failed\|error)' >/dev/null; RGST=$?; test "$RGST" -eq 1; } \|\| exit 1; done` ; `B=tmp/h35-headless-integration/no-compositor-bin && MK="$(command -v make)" && UV="$(command -v uv)" && test -n "$MK" && test -n "$UV" && rm -rf "$B" && mkdir -p "$B" && ln -s "$UV" "$B/uv" && OUT="$(env PATH="$B" "$MK" test-integration PYTEST_ARGS='-q' 2>&1)"; ST=$?; test "$ST" -ne 0 && printf '%s\n' "$OUT" \| rg -q 'no nested compositor' && printf '%s\n' "$OUT" \| rg -q 'NOT run' && { printf '%s\n' "$OUT" \| rg -c '(^\|[^0-9])[0-9]+ passed' >/dev/null; RGST=$?; test "$RGST" -eq 1; }` | `uv` on PATH (the stubbed PATH holds only `uv`) | ⬜ pending |
| 02-11-T3 | 02-11 | 1 | R0.13 | T-2-44, T-2-46 | **The whole suite, seen to run.** `make test-integration` reports pytest's own count: at least 70, zero failed. A harness-owned kitty, one carrying `WLR_BACKENDS=headless`, is seen during the run and none after, and no `cage` is left. The user's own kitty is never counted, so opening or closing it cannot turn the gate red. `make test` keeps its recipe, its fast unit-only default and its skips | integration + grep | `hk() { K="$(pgrep -x kitty)"; P=$?; test "$P" -le 1 \|\| return 2; for p in $K; do tr '\0' '\n' < "/proc/$p/environ" 2>/dev/null \| rg -qx 'WLR_BACKENDS=headless' && printf '%s\n' "$p"; done; return 0; }; H0="$(hk)" \|\| exit 1; test -z "$H0" \|\| exit 1; S="$(mktemp)" \|\| exit 1; touch "$S.on" \|\| exit 1; trap 'rm -f "$S.on"; wait; rm -f "$S"' EXIT; ( while test -e "$S.on"; do hk >> "$S"; sleep 0.5; done ) & OUT="$(make test-integration PYTEST_ARGS='-q' 2>&1)" \|\| exit 1; rm -f "$S.on"; wait; N="$(printf '%s\n' "$OUT" \| rg -o '([0-9]+) passed' -r '$1' \| tail -1)"; test -n "$N" && test "$N" -ge 70 \|\| exit 1; { printf '%s\n' "$OUT" \| rg -c '[0-9]+ (failed\|error)' >/dev/null; RGST=$?; test "$RGST" -eq 1; } \|\| exit 1; test -s "$S" \|\| exit 1; H1="$(hk)" \|\| exit 1; test -z "$H1" \|\| exit 1; { pgrep -x cage >/dev/null; PC=$?; test "$PC" -eq 1; }` ; `R="$(rg -A1 '^test:' Makefile)" && printf '%s\n' "$R" \| rg -q '^\t@uv run pytest tests/$' && OUT="$(make test 2>&1)" && N="$(printf '%s\n' "$OUT" \| rg -o '([0-9]+) passed' -r '$1' \| tail -1)" && test -n "$N" && test "$N" -ge 314 && S="$(printf '%s\n' "$OUT" \| rg -o '([0-9]+) skipped' -r '$1' \| tail -1)" && test -n "$S" && test "$S" -ge 70 && { printf '%s\n' "$OUT" \| rg -c '[0-9]+ (failed\|error)' >/dev/null; RGST=$?; test "$RGST" -eq 1; }` | kitty and `cage` | ⬜ pending |
| 02-11-T4 | 02-11 | 1 | R0.13 | T-2-46 | **The suite runs from where phases execute.** kitty's control socket lives in a private 0700 `kitti-` directory under `$XDG_RUNTIME_DIR` (or the temp directory), not under the checkout. It is checked against `sun_path`'s 107 usable bytes before kitty starts, and it is removed on every exit path. Measured from a phase worktree whose old socket path was 114 bytes: `70 passed in 43.68s`. RED held both new test modules and failed 29 cases; GREEN holds no test | unit + integration (worktree) | `for K in socket_path_fits socket_dir_is_private socket_dir_is_removed_on_teardown socket_dir_is_removed_when_startup_fails; do OUT="$(uv run pytest tests/unit/test_kitty_session_socket.py -q -p no:cacheprovider -k "$K" 2>&1)" \|\| exit 1; printf '%s\n' "$OUT" \| rg -q '(^\|[^0-9])[0-9]+ passed' \|\| exit 1; { printf '%s\n' "$OUT" \| rg -c '[0-9]+ (failed\|error)' >/dev/null; RGST=$?; test "$RGST" -eq 1; } \|\| exit 1; done` ; `RED="$(git log --format='%H %s' \| rg '^[0-9a-f]+ test\(02-11\)' \| head -1 \| cut -d' ' -f1)" && test -n "$RED" && VENV="$(uv run python -c 'import sys; print(sys.prefix)')" && test -x "$VENV/bin/python" && D="$(mktemp -d)" && trap 'rm -rf "$D"' EXIT && GIT_INDEX_FILE="$D/.idx" git read-tree "$RED" && GIT_INDEX_FILE="$D/.idx" git checkout-index -a --prefix="$D/t/" && cd "$D/t" && OUT="$(PYTHONPATH="$D/t/src" "$VENV/bin/python" -m pytest tests/unit/test_integration_runner.py tests/unit/test_kitty_session_socket.py -q -p no:cacheprovider -k 'not test_recipe_is_unchanged' 2>&1)"; ST=$?; test "$ST" -eq 1 && N="$(printf '%s\n' "$OUT" \| rg -o '([0-9]+) failed' -r '$1' \| tail -1)" && test -n "$N" && test "$N" -ge 29 && { printf '%s\n' "$OUT" \| rg -c '[0-9]+ (passed\|error)' >/dev/null; RGST=$?; test "$RGST" -eq 1; }` ; `H="$(git log --format='%H %s')" && GREEN="$(printf '%s\n' "$H" \| rg '^[0-9a-f]+ feat\(02-11\)' \| head -1 \| cut -d' ' -f1)" && test -n "$GREEN" && ST="$(git diff-tree --no-commit-id -r -M --name-status "$GREEN")" && test -n "$ST" && for T in 02-11-SUMMARY.md src/kitty_setup/harness/integration_runner.py src/kitty_setup/harness/kitty_session.py Makefile; do printf '%s\n' "$ST" \| cut -f2- \| rg -q -F -- "$T" \|\| exit 1; done && { printf '%s\n' "$ST" \| cut -f2- \| rg -c '(^\|\t)tests/' >/dev/null; RGST=$?; test "$RGST" -eq 1; }` | — for these commands; the plan's worktree gate needs a linked worktree whose old socket path exceeds 107 bytes, and its transcript is in `02-11-SUMMARY.md` | ⬜ pending |
| 02-01-T1 | 02-01 | 2 | R1.1 | T-2-01, T-2-02 | The completion script is generated **in-process** from the installed argcomplete, so no helper binary the uv tool venv does not expose is ever looked up | unit + grep | `test -f src/kitty_setup/installer.py && rg -q 'argcomplete\.shellcode' src/kitty_setup/installer.py && rg -q 'COMPLETION_DIR' src/kitty_setup/installer.py && rg -q 'def write_completion_script' src/kitty_setup/installer.py && rg -q 'def completion_script_path' src/kitty_setup/installer.py` ; `OUT="$(uv run pytest tests/unit/test_installer_completion.py -q -k 'shellcode or no_subcommand or compdef or unsupported_shell or idempotent' 2>&1)" && printf '%s\n' "$OUT" \| rg -q '(^\|[^0-9])[0-9]+ passed' && { printf '%s\n' "$OUT" \| rg -c '[0-9]+ (failed\|error)' >/dev/null; RGST=$?; test "$RGST" -eq 1; }` | — | ⬜ pending |
| 02-01-T2 | 02-01 | 2 | R1.1 | T-2-02, T-2-03 | Removal is tied to `do_kitty`, not `do_config`, so `make clean` — which passes `--keep-kitty --keep-backups` — cannot orphan a surviving binary's completion; and nothing ever `rmtree`s the parent directory. The whole RED set failed before any implementation, and GREEN adds no test | unit + grep | `test -f src/kitty_setup/installer.py && rg -q 'def remove_completion_script' src/kitty_setup/installer.py && { rg -c 'rmtree\(.*COMPLETION_DIR' src/kitty_setup/installer.py >/dev/null; RGST=$?; test "$RGST" -eq 1; }` ; `OUT="$(uv run pytest tests/unit/test_installer_completion.py -q -k 'remove or keep_kitty or keep_config' 2>&1)" && printf '%s\n' "$OUT" \| rg -q '(^\|[^0-9])[0-9]+ passed' && { printf '%s\n' "$OUT" \| rg -c '[0-9]+ (failed\|error)' >/dev/null; RGST=$?; test "$RGST" -eq 1; }` ; `RED="$(git log --format='%H %s' \| rg '^[0-9a-f]+ test\(02-01\)' \| head -1 \| cut -d' ' -f1)" && test -n "$RED" && VENV="$(uv run python -c 'import sys; print(sys.prefix)')" && test -x "$VENV/bin/python" && D="$(mktemp -d)" && trap 'rm -rf "$D"' EXIT && GIT_INDEX_FILE="$D/.idx" git read-tree "$RED" && GIT_INDEX_FILE="$D/.idx" git checkout-index -a --prefix="$D/t/" && cd "$D/t" && OUT="$(PYTHONPATH="$D/t/src" "$VENV/bin/python" -m pytest tests/unit/test_installer_completion.py -q -p no:cacheprovider -k 'shellcode or no_subcommand or compdef or unsupported_shell or idempotent or remove or keep_kitty or keep_config' 2>&1)"; ST=$?; test "$ST" -eq 1 && N="$(printf '%s\n' "$OUT" \| rg -o '([0-9]+) failed' -r '$1' \| tail -1)" && test -n "$N" && test "$N" -ge 11 && { printf '%s\n' "$OUT" \| rg -c '[0-9]+ (passed\|error)' >/dev/null; RGST=$?; test "$RGST" -eq 1; }` ; `GREEN="$(git log --format='%H %s' \| rg '^[0-9a-f]+ feat\(02-01\)' \| head -1 \| cut -d' ' -f1)" && test -n "$GREEN" && ST="$(git diff-tree --no-commit-id -r -M --name-status "$GREEN")" && test -n "$ST" && { printf '%s\n' "$ST" \| cut -f2- \| rg -c '(^\|\t)tests/' >/dev/null; RGST=$?; test "$RGST" -eq 1; }` | — | ⬜ pending |
| 02-02-T1 | 02-02 | 3 | R1.1 | T-2-04, T-2-06 | The rc block body is a **function of the shell**: bash sources the file; zsh starts `compinit -i` itself when `compdef` is missing, then sources behind a `compdef` guard, and a zsh block is kept **last** in `~/.zshrc`, because a `compinit` that runs after it resets the registration (measured 2026-09-24). An upgrade that finds both markers rewrites the retained block's obsolete body. All six existing edit reasons survive, plus the zsh move-only seventh. The real-shell e2e module drives argcomplete's own protocol, with no pty | unit + grep | `F=src/kitty_setup/path_integration.py && test -f "$F" && rg -q 'def _block_body_lines' "$F" && rg -q 'def _block_followed_only_by_comments' "$F" && rg -q 'command -v compdef' "$F" && rg -q 'compinit -i' "$F" && rg -q 'manual_lines' "$F" && { rg -c '_BLOCK_BODY_LINES' "$F" >/dev/null; RGST=$?; test "$RGST" -eq 1; }` ; `F=src/kitty_setup/path_integration.py && test -f "$F" && for R in 'reason=f"unsupported shell: ' 'reason="removed duplicate legacy marker"' 'reason="migrated legacy marker"' 'reason="rc block already matches current template"' 'reason="rewrote rc block body to current template"' 'reason="appended sentinel-bracketed block"' 'reason="moved rc block to end of file"'; do rg -q -F -- "$R" "$F" \|\| exit 1; done` ; `OUT="$(uv run pytest tests/unit/test_path_integration.py tests/unit/test_installer_completion.py -q 2>&1)" && printf '%s\n' "$OUT" \| rg -q '(^\|[^0-9])[0-9]+ passed' && { printf '%s\n' "$OUT" \| rg -c '[0-9]+ (failed\|error)' >/dev/null; RGST=$?; test "$RGST" -eq 1; }` ; `F=tests/integration/test_completion_e2e.py && test -f "$F" && rg -q '_python_argcomplete' "$F" && rg -q 'which\("zsh"\)' "$F" && rg -q '_ARGCOMPLETE' "$F" && rg -q '_block_body_lines' "$F" && rg -q 'ensure_local_bin_in_path' "$F" && rg -q '_check_completion' "$F" && { rg -c '\bimport pty\b\|\bfrom pty import\b\|\bpty\.[a-z_]+\(\|\bopenpty\b\|\bpexpect\b' "$F" >/dev/null; RGST=$?; test "$RGST" -eq 1; }` | — | ⬜ pending |
| 02-02-T2 | 02-02 | 3 | R1.1 | T-2-05, T-2-07 | Doctor verifies what it can honestly check: the file exists, the rc block's body is exactly the current template, nothing executable follows a zsh block, and the file's bytes match freshly generated shellcode. It judges the block with the same two predicates install uses, so every zsh shape measured to register nothing is a FAIL, never a structural PASS. It **SKIPs** on a shell it has no script for instead of guessing; the `.zshrc` fallback that reported on a file the user may not use is gone | unit + grep | `F=src/kitty_setup/doctor.py && test -f "$F" && rg -q 'generate_completion_script' "$F" && rg -q 'completion_script_path' "$F" && rg -q 'skipped=True' "$F" && rg -q '_block_body_matches_template' "$F" && rg -q '_block_followed_only_by_comments' "$F"` ; `F=src/kitty_setup/doctor.py && test -f "$F" && { rg -c 'register-python-argcomplete' "$F" >/dev/null; RGST=$?; test "$RGST" -eq 1; }` ; `OUT="$(uv run pytest tests/unit/test_doctor.py -q -k 'completion' 2>&1)" && printf '%s\n' "$OUT" \| rg -q '(^\|[^0-9])[0-9]+ passed' && { printf '%s\n' "$OUT" \| rg -c '[0-9]+ (failed\|error)' >/dev/null; RGST=$?; test "$RGST" -eq 1; }` | — | ⬜ pending |
| 02-02-T3 | 02-02 | 3 | R1.1 | T-2-05 | **The phase spine.** Registration is proven in real bash and real zsh — including a zsh block that install moved from above `compinit` — doctor's verdict is proven equal to real zsh registration, and `README.md:155-161`'s now-false paragraph is corrected. Doctor is measured through `make doctor` on a real install rather than asserted. The whole RED set failed before any implementation, counted **exactly** against the frozen RED tree (25 unit, 6 integration, with bash and zsh asserted present first), and GREEN adds no test | integration + shell | `OUT="$(make doctor 2>&1)"; ST=$?; test "$ST" -eq 0 && test "$(printf '%s\n' "$OUT" \| rg -c '^(PASS\|SKIP) ')" -ge 9 && { printf '%s\n' "$OUT" \| rg -c '^FAIL ' >/dev/null; RGST=$?; test "$RGST" -eq 1; }` ; `command -v bash >/dev/null 2>&1 \|\| { echo 'integration precondition failed: bash is not on PATH' >&2; exit 1; }; command -v zsh >/dev/null 2>&1 \|\| { echo 'integration precondition failed: zsh is not on PATH' >&2; exit 1; }; OUT="$(make test-integration PYTEST_ARGS='tests/integration/test_completion_e2e.py -q' 2>&1)" && printf '%s\n' "$OUT" \| rg -q '(^\|[^0-9])[0-9]+ passed' && { printf '%s\n' "$OUT" \| rg -c '[0-9]+ (failed\|skipped\|error)' >/dev/null; RGST=$?; test "$RGST" -eq 1; }` ; `RED="$(git log --format='%H %s' \| rg '^[0-9a-f]+ test\(02-02\)' \| head -1 \| cut -d' ' -f1)" && test -n "$RED" && VENV="$(uv run python -c 'import sys; print(sys.prefix)')" && test -x "$VENV/bin/python" && D="$(mktemp -d)" && trap 'rm -rf "$D"' EXIT && GIT_INDEX_FILE="$D/.idx" git read-tree "$RED" && GIT_INDEX_FILE="$D/.idx" git checkout-index -a --prefix="$D/t/" && cd "$D/t" && OUT="$(PYTHONPATH="$D/t/src" "$VENV/bin/python" -m pytest tests/unit/test_path_integration.py tests/unit/test_doctor.py tests/unit/test_installer_completion.py::test_cli_install_completion_write_failure_is_one_clean_line -q -p no:cacheprovider -k completion 2>&1)"; ST=$?; test "$ST" -eq 1 && N="$(printf '%s\n' "$OUT" \| rg -o '([0-9]+) failed' -r '$1' \| tail -1)" && test -n "$N" && test "$N" -eq 25 && { printf '%s\n' "$OUT" \| rg -c '[0-9]+ (passed\|error)' >/dev/null; RGST=$?; test "$RGST" -eq 1; }` ; `GREEN="$(git log --format='%H %s' \| rg '^[0-9a-f]+ feat\(02-02\)' \| head -1 \| cut -d' ' -f1)" && test -n "$GREEN" && ST="$(git diff-tree --no-commit-id -r -M --name-status "$GREEN")" && test -n "$ST" && { printf '%s\n' "$ST" \| cut -f2- \| rg -c '(^\|\t)tests/' >/dev/null; RGST=$?; test "$RGST" -eq 1; }` | installed `my-kitty` (run `make install` first); bash **and** zsh on PATH; `cage` for the integration half (headless) | ⬜ pending |
| 02-03-T1 | 02-03 | 4 | R1.3 | T-2-09, T-2-10, T-2-11 | Every diagnostic the bootstrap script emits goes to **stderr**, so a `resolve_binary` failure is visible rather than swallowed into a captured stdout; both branches are pinned from a `tmp_path` sandbox whose code never reads the real environment (an AST gate, not a text grep); and the confirm prompt's will-remove list names the completion file `my-kitty uninstall` removes under `do_kitty`, read by answering `n` to the real prompt | unit + grep | `F=tools/uninstall.sh && test -f "$F" && rg -q "^log\(\) \{ printf '\[uninstall\] %s.n' \"\\\$\*\" >&2; \}" "$F"` ; `OUT="$(uv run pytest tests/unit/test_tools_uninstall_sh.py -q -k 'legacy or error_branch or preferred or fallback or keep_env' 2>&1)" && printf '%s\n' "$OUT" \| rg -q '(^\|[^0-9])[0-9]+ passed' && { printf '%s\n' "$OUT" \| rg -c '[0-9]+ (failed\|error)' >/dev/null; RGST=$?; test "$RGST" -eq 1; }` ; `test "$(fd -e sh . tools --type f \| wc -l \| tr -d '[:space:]')" = '2' && test "$(fd -e bats . --type f 2>/dev/null \| wc -l \| tr -d '[:space:]')" = '0'` ; `F=tests/unit/test_tools_uninstall_sh.py && test -f "$F" && uv run python -c 'import ast,sys; t=ast.parse(open(sys.argv[1]).read()); ds={id(s.value) for s in ast.walk(t) if isinstance(s,ast.Expr) and isinstance(s.value,ast.Constant)}; k=[n.value for n in ast.walk(t) if isinstance(n,ast.Constant) and isinstance(n.value,str) and id(n) not in ds]; runs=[n for n in ast.walk(t) if isinstance(n,ast.Call) and ast.unparse(n.func)=="subprocess.run"]; env=[n for n in ast.walk(t) if (isinstance(n,ast.Attribute) and isinstance(n.value,ast.Name) and n.value.id=="os" and n.attr in ("environ","environb","getenv")) or (isinstance(n,ast.ImportFrom) and n.module=="os" and any(a.name in ("environ","environb","getenv") for a in n.names))]; ok=len(runs)>0 and all({k.arg for k in n.keywords}.issuperset({"env","timeout","cwd"}) for n in runs) and not env and "KITTI_FORCE" in k and not any("shellcheck" in v for v in k); sys.exit(0 if ok else 1)' "$F"` ; `OUT="$(uv run pytest tests/unit/test_tools_uninstall_sh.py -q -k 'will_remove' 2>&1)" && printf '%s\n' "$OUT" \| rg -q '(^\|[^0-9])[0-9]+ passed' && { printf '%s\n' "$OUT" \| rg -c '[0-9]+ (failed\|error)' >/dev/null; RGST=$?; test "$RGST" -eq 1; }` | — | ⬜ pending |
| 02-03-T2 | 02-03 | 4 | R1.2 | T-2-08 | `make clean` does what its help text says: it keeps `kitty.app` and the backups, proven by the flags in the recipe **and** by a test asserting the help line's keep-set equals the recipe's `--keep-*` set, with no special case; the help line and `README.md` both say `(keeps kitty + backups)`, and "binary", which no flag keeps, is gone. The whole RED set failed before any implementation, and GREEN adds no test | unit + grep | `R="$(rg -A3 '^clean:' Makefile)" && printf '%s\n' "$R" \| rg -q -- '--keep-kitty' && printf '%s\n' "$R" \| rg -q -- '--keep-backups' && printf '%s\n' "$R" \| rg -q 'rm -rf tmp/'` ; `H="$(rg '^\t@echo "  clean ' Makefile)" && test "$(printf '%s\n' "$H" \| wc -l \| tr -d '[:space:]')" = '1' && printf '%s\n' "$H" \| rg -q '\(keeps kitty \+ backups\)"$' && { printf '%s\n' "$H" \| rg -c 'binary' >/dev/null; RGST=$?; test "$RGST" -eq 1; } && D="$(rg '^make clean ' README.md)" && printf '%s\n' "$D" \| rg -q '\(keeps kitty \+ backups\)$' && { printf '%s\n' "$D" \| rg -c 'binary' >/dev/null; RGST2=$?; test "$RGST2" -eq 1; }` ; `OUT="$(uv run pytest tests/unit/test_makefile_targets.py -q 2>&1)" && printf '%s\n' "$OUT" \| rg -q '(^\|[^0-9])2 passed' && { printf '%s\n' "$OUT" \| rg -c '[0-9]+ (failed\|error)' >/dev/null; RGST=$?; test "$RGST" -eq 1; }` ; `OUT="$(uv run pytest tests/unit/test_installer_uninstall.py -q -k 'keep_kitty_and_backups' 2>&1)" && printf '%s\n' "$OUT" \| rg -q '(^\|[^0-9])[0-9]+ passed' && { printf '%s\n' "$OUT" \| rg -c '[0-9]+ (failed\|error)' >/dev/null; RGST=$?; test "$RGST" -eq 1; }` ; `RED="$(git log --format='%H %s' \| rg '^[0-9a-f]+ test\(02-03\)' \| head -1 \| cut -d' ' -f1)" && test -n "$RED" && VENV="$(uv run python -c 'import sys; print(sys.prefix)')" && test -x "$VENV/bin/python" && D="$(mktemp -d)" && trap 'rm -rf "$D"' EXIT && GIT_INDEX_FILE="$D/.idx" git read-tree "$RED" && GIT_INDEX_FILE="$D/.idx" git checkout-index -a --prefix="$D/t/" && cd "$D/t" && OUT="$(PYTHONPATH="$D/t/src" "$VENV/bin/python" -m pytest tests/unit/test_tools_uninstall_sh.py tests/unit/test_makefile_targets.py tests/unit/test_installer_uninstall.py -q -p no:cacheprovider -k 'legacy or error_branch or preferred or fallback or keep_env or will_remove or clean_recipe or clean_help' 2>&1)"; ST=$?; test "$ST" -eq 1 && N="$(printf '%s\n' "$OUT" \| rg -o '([0-9]+) failed' -r '$1' \| tail -1)" && test -n "$N" && test "$N" -ge 9 && { printf '%s\n' "$OUT" \| rg -c '[0-9]+ (passed\|error)' >/dev/null; RGST=$?; test "$RGST" -eq 1; }` ; `GREEN="$(git log --format='%H %s' \| rg '^[0-9a-f]+ feat\(02-03\)' \| head -1 \| cut -d' ' -f1)" && test -n "$GREEN" && ST="$(git diff-tree --no-commit-id -r -M --name-status "$GREEN")" && test -n "$ST" && { printf '%s\n' "$ST" \| cut -f2- \| rg -c '(^\|\t)tests/' >/dev/null; RGST=$?; test "$RGST" -eq 1; }` | — | ⬜ pending |
| 02-04-T1 | 02-04 | 5 | R1.4 | T-2-12, T-2-13, T-2-15 | **The phase's one genuine vulnerability.** Both pane-0 `send-text` payloads are `shlex.quote`d and pane-0's `cmd` gets the same `bash -lc` semantics as every other pane — while `_launch_argv`'s `--cwd=<raw>` argv element, which no shell parses, is left exactly as it is | unit + grep | `F=src/kitty_setup/scenes/launcher.py && test -f "$F" && rg -q '^import shlex' "$F" && test "$(rg -c 'shlex\.quote' "$F")" -ge 2 && rg -q 'bash -lc' "$F"` ; `F=src/kitty_setup/scenes/launcher.py && test -f "$F" && B="$(rg -A23 'def _launch_argv' "$F")" && printf '%s\n' "$B" \| rg -q -- '--cwd=' && { printf '%s\n' "$B" \| rg -c 'shlex' >/dev/null; RGST=$?; test "$RGST" -eq 1; }` ; `OUT="$(uv run pytest tests/unit/test_scenes_launcher.py -q -k 'pane0' 2>&1)" && printf '%s\n' "$OUT" \| rg -q '(^\|[^0-9])[0-9]+ passed' && { printf '%s\n' "$OUT" \| rg -c '[0-9]+ (failed\|error)' >/dev/null; RGST=$?; test "$RGST" -eq 1; }` | — | ⬜ pending |
| 02-04-T2 | 02-04 | 5 | R1.4, R1.7 | T-2-14 | One `_window_id_from` rule for all four id-parsing sites. A stdout that is not a window id raises the existing `SceneClientError`, so the CLI prints a clean `my-kitty scene launch:` error instead of a traceback. A real-kitty case with a space in the cwd proves the quoting is the right quoting, with its sentinel under `tmp_path` rather than a fixed absolute path | unit + integration | `F=src/kitty_setup/scenes/launcher.py && test -f "$F" && rg -q 'def _window_id_from' "$F" && test "$(rg -c '_window_id_from' "$F")" -ge 4 && { rg -c 'int\((launch_)?result\.stdout' "$F" >/dev/null; RGST=$?; test "$RGST" -eq 1; }` ; `OUT="$(uv run pytest tests/unit/test_scenes_launcher.py -q -k 'window_id or pane0 or pane1' 2>&1)" && printf '%s\n' "$OUT" \| rg -q '(^\|[^0-9])[0-9]+ passed' && { printf '%s\n' "$OUT" \| rg -c '[0-9]+ (failed\|error)' >/dev/null; RGST=$?; test "$RGST" -eq 1; }` ; `PY="$(uv run python -c 'import sys; print(sys.executable)')" && B="$(mktemp -d)" && trap 'rm -rf "$B"' EXIT && printf '#!%s\nimport sys\nsys.exit(0)\n' "$PY" > "$B/kitten" && chmod +x "$B/kitten" && OUT="$(env -u KITTY_WINDOW_ID -u KITTY_LISTEN_ON HOME="$B" PATH="$B:/usr/bin:/bin" "$PY" -c 'import sys; from kitty_setup.cli import main; sys.exit(main(["scene", "launch", "--to", "unix:/nonexistent", "--pane", "title=ok"]))' 2>&1)"; ST=$?; test "$ST" -ne 0 && printf '%s\n' "$OUT" \| rg -q '^my-kitty scene launch: .*launch' && { printf '%s\n' "$OUT" \| rg -c 'Traceback' >/dev/null; RGST=$?; test "$RGST" -eq 1; }` ; `OUT="$(make test-integration PYTEST_ARGS='tests/integration/test_scene_fill_tab_e2e.py -q' 2>&1)" && printf '%s\n' "$OUT" \| rg -q '(^\|[^0-9])[0-9]+ passed' && { printf '%s\n' "$OUT" \| rg -c '[0-9]+ (failed\|error)' >/dev/null; RGST=$?; test "$RGST" -eq 1; }` ; `RED="$(git log --format='%H %s' \| rg '^[0-9a-f]+ test\(02-04\)' \| head -1 \| cut -d' ' -f1)" && test -n "$RED" && VENV="$(uv run python -c 'import sys; print(sys.prefix)')" && test -x "$VENV/bin/python" && D="$(mktemp -d)" && trap 'rm -rf "$D"' EXIT && GIT_INDEX_FILE="$D/.idx" git read-tree "$RED" && GIT_INDEX_FILE="$D/.idx" git checkout-index -a --prefix="$D/t/" && cd "$D/t" && OUT="$(PYTHONPATH="$D/t/src" "$VENV/bin/python" -m pytest tests/unit/test_scenes_launcher.py -q -p no:cacheprovider -k 'pane0_injection or pane0_cmd or pane0_roundtrip or window_id_rejects' 2>&1)"; ST=$?; test "$ST" -eq 1 && N="$(printf '%s\n' "$OUT" \| rg -o '([0-9]+) failed' -r '$1' \| tail -1)" && test -n "$N" && test "$N" -ge 12 && { printf '%s\n' "$OUT" \| rg -c '[0-9]+ (passed\|error)' >/dev/null; RGST=$?; test "$RGST" -eq 1; }` ; `GREEN="$(git log --format='%H %s' \| rg '^[0-9a-f]+ feat\(02-04\)' \| head -1 \| cut -d' ' -f1)" && test -n "$GREEN" && ST="$(git diff-tree --no-commit-id -r -M --name-status "$GREEN")" && test -n "$ST" && { printf '%s\n' "$ST" \| cut -f2- \| rg -c '(^\|\t)tests/' >/dev/null; RGST=$?; test "$RGST" -eq 1; }` | kitty and `cage` (headless, no desktop window) | ⬜ pending |
| 02-05-T1 | 02-05 | 6 | R1.5 | T-2-17, T-2-18, T-2-20 | The parse check **returns** its diagnostics instead of dropping them. A frozen `ParseCheckResult` carries `ok`, the complete command actually run (`shlex.split` of it equals the argv executed), and the parser's stderr. The `--debug-config` name the code's own docstring admitted was wrong is gone | unit + grep | `F=src/kitty_setup/config_updater.py && test -f "$F" && uv run python -c 'import ast,sys; t=ast.parse(open(sys.argv[1]).read()); c=[n for n in t.body if isinstance(n,ast.ClassDef) and n.name=="ParseCheckResult"]; d=[x for x in (c[0].decorator_list if c else []) if isinstance(x,ast.Call) and ast.unparse(x.func)=="dataclasses.dataclass"]; kw={k.arg: ast.unparse(k.value) for k in (d[0].keywords if d else [])}; f=[(s.target.id, ast.unparse(s.annotation)) for s in (c[0].body if c else []) if isinstance(s,ast.AnnAssign) and isinstance(s.target,ast.Name)]; p=[n for n in t.body if isinstance(n,ast.FunctionDef) and n.returns is not None and ast.unparse(n.returns).strip(chr(34)+chr(39))=="ParseCheckResult"]; r=[n for q in p for n in ast.walk(q) if isinstance(n,ast.Return)]; ok=len(c)==1 and kw.get("frozen")=="True" and kw.get("slots")=="True" and f==[("ok","bool"),("command","str"),("stderr","str")] and len(p)==1 and len(r)>0 and all(isinstance(x.value,ast.Call) and ast.unparse(x.value.func)=="ParseCheckResult" for x in r); sys.exit(0 if ok else 1)' "$F"` ; `F=src/kitty_setup/config_updater.py && test -f "$F" && { rg -c -- '--debug-config' "$F" >/dev/null; RGST=$?; test "$RGST" -eq 1; }` ; `OUT="$(uv run pytest tests/unit/test_config_updater.py -q -k 'parse_result' 2>&1)" && printf '%s\n' "$OUT" \| rg -q '(^\|[^0-9])[0-9]+ passed' && { printf '%s\n' "$OUT" \| rg -c '[0-9]+ (failed\|error)' >/dev/null; RGST=$?; test "$RGST" -eq 1; }` | — | ⬜ pending |
| 02-05-T2 | 02-05 | 6 | R1.5 | T-2-16 | The payload directory is rolled back too, as an **explicit state machine**. The previous payload is set aside as a `.rollback` sibling, and the aside is deleted only after the new payload and conf pass. On any failure — Ctrl-C included, because the handler catches `BaseException` — the aside is restored, and a failed restore (of either step) keeps the aside and names it after the conf is restored. A stale aside from an interrupted install is preserved under a unique dated name and named on one stderr line, never deleted. So a rejected `kitty.conf` never leaves a half-written payload, and no failure path deletes the only good copy | unit + grep | `F=src/kitty_setup/config_updater.py && test -f "$F" && uv run python -c 'import ast,sys; t=ast.parse(open(sys.argv[1]).read()); fs=[n for n in ast.walk(t) if isinstance(n,ast.FunctionDef)]; r={f.name for f in fs for n in ast.walk(f) if isinstance(n,ast.Call) and isinstance(n.func,ast.Attribute) and n.func.attr=="rename"}; s=[n for n in ast.walk(t) if isinstance(n,ast.Constant) and n.value==".rollback"]; sys.exit(0 if (r - {"_select_clear_variant"}) and s else 1)' "$F"` ; `for K in rollback_copy_fails rollback_parse_fails rollback_restore_fails rollback_no_previous_payload rollback_stale_aside_preserved guard_success_leaves_no_aside; do OUT="$(uv run pytest tests/unit/test_config_updater.py -q -k "$K" 2>&1)" \|\| exit 1; printf '%s\n' "$OUT" \| rg -q '(^\|[^0-9])[0-9]+ passed' \|\| exit 1; { printf '%s\n' "$OUT" \| rg -c '[0-9]+ (failed\|error)' >/dev/null; RGST=$?; test "$RGST" -eq 1; } \|\| exit 1; done` ; `OUT="$(uv run pytest tests/unit/test_config_updater.py -q 2>&1)" && printf '%s\n' "$OUT" \| rg -q '(^\|[^0-9])[0-9]+ passed' && { printf '%s\n' "$OUT" \| rg -c '[0-9]+ (failed\|error)' >/dev/null; RGST=$?; test "$RGST" -eq 1; }` | — | ⬜ pending |
| 02-05-T3 | 02-05 | 6 | R1.5, R1.7 | T-2-18, T-2-19 | Doctor's three false FAILs become three **real SKIPs**. Each skip site, probed one by one, renders `SKIP <label>: ` with no doubled `skipped`. Its parse-check label is built from the result's own `command` field rather than from a hard-coded string that was never true. The whole RED set failed before any implementation, and GREEN adds no test | unit + grep | `H="$(mktemp -d)" && trap 'rm -rf "$H"' EXIT && uv run python -c 'import sys; from pathlib import Path; from kitty_setup import doctor, config_updater, binding_introspection as bi; p = config_updater.ConfigPaths.for_user(home=Path(sys.argv[1])); p.conf_file.parent.mkdir(parents=True, exist_ok=True); p.conf_file.write_text(""); bi.enumerate_bindings = lambda *a, **k: (_ for _ in ()).throw(bi.BindingIntrospectionError("probe")); rs = [doctor._check_parse(p, None), doctor._check_bindings(p, None), doctor._check_bindings(p, Path(sys.executable))]; sys.exit(0 if all(r.render().startswith(w) and "skipped" not in r.render()[5:] for r, w in zip(rs, ["SKIP parse check: ", "SKIP bindings: ", "SKIP bindings: "])) else 1)' "$H"` ; `F=src/kitty_setup/doctor.py && test -f "$F" && rg -q 'result\.command\|parse_result\.command\|\.command' "$F" && { rg -c '\+runpy' "$F" >/dev/null; RGST=$?; test "$RGST" -eq 1; }` ; `OUT="$(uv run pytest tests/unit/test_doctor.py -q -k 'skip or exits' 2>&1)" && printf '%s\n' "$OUT" \| rg -q '(^\|[^0-9])[0-9]+ passed' && { printf '%s\n' "$OUT" \| rg -c '[0-9]+ (failed\|error)' >/dev/null; RGST=$?; test "$RGST" -eq 1; }` ; `OUT="$(make doctor 2>&1)"; ST=$?; test "$ST" -eq 0 && test "$(printf '%s\n' "$OUT" \| rg -c '^(PASS\|SKIP) ')" -ge 9 && { printf '%s\n' "$OUT" \| rg -c '^FAIL ' >/dev/null; RGST=$?; test "$RGST" -eq 1; }` ; `RED="$(git log --format='%H %s' \| rg '^[0-9a-f]+ test\(02-05\)' \| head -1 \| cut -d' ' -f1)" && test -n "$RED" && VENV="$(uv run python -c 'import sys; print(sys.prefix)')" && test -x "$VENV/bin/python" && D="$(mktemp -d)" && trap 'rm -rf "$D"' EXIT && GIT_INDEX_FILE="$D/.idx" git read-tree "$RED" && GIT_INDEX_FILE="$D/.idx" git checkout-index -a --prefix="$D/t/" && cd "$D/t" && OUT="$(PYTHONPATH="$D/t/src" "$VENV/bin/python" -m pytest tests/unit/test_config_updater.py tests/unit/test_doctor.py -q -p no:cacheprovider -k 'parse_result or rollback_copy_fails or rollback_parse_fails or rollback_restore_fails or rollback_no_previous_payload or rollback_stale_aside or skip_state or parse_detail' 2>&1)"; ST=$?; test "$ST" -eq 1 && N="$(printf '%s\n' "$OUT" \| rg -o '([0-9]+) failed' -r '$1' \| tail -1)" && test -n "$N" && test "$N" -ge 18 && { printf '%s\n' "$OUT" \| rg -c '[0-9]+ (passed\|error)' >/dev/null; RGST=$?; test "$RGST" -eq 1; }` ; `GREEN="$(git log --format='%H %s' \| rg '^[0-9a-f]+ feat\(02-05\)' \| head -1 \| cut -d' ' -f1)" && test -n "$GREEN" && ST="$(git diff-tree --no-commit-id -r -M --name-status "$GREEN")" && test -n "$ST" && { printf '%s\n' "$ST" \| cut -f2- \| rg -c '(^\|\t)tests/' >/dev/null; RGST=$?; test "$RGST" -eq 1; }` | — | ⬜ pending |
| 02-06-T1 | 02-06 | 7 | R1.7 | T-2-21, T-2-24 | Passthrough is narrowed to an **anchored `rgb:` `fullmatch`** — the one functional form kitty 0.49.0's own parser accepts — and the test that asserted `rgba(1,2,3,0.5)` passes through is **inverted and renamed**, because U-2 made it a wrong test rather than an incomplete one | unit + grep | `F=src/kitty_setup/scenes/colors.py && test -f "$F" && rg -q 'rgb:' "$F" && rg -q 'fullmatch' "$F" && { rg -c '":" in v or "\(" in v' "$F" >/dev/null; RGST=$?; test "$RGST" -eq 1; }` ; `F=tests/unit/test_scenes_colors.py && test -f "$F" && { rg -c 'def test_functional_and_rgb_forms_pass_through' "$F" >/dev/null; RGST=$?; test "$RGST" -eq 1; }` ; `OUT="$(uv run pytest tests/unit/test_scenes_colors.py -q 2>&1)" && printf '%s\n' "$OUT" \| rg -q '(^\|[^0-9])[0-9]+ passed' && { printf '%s\n' "$OUT" \| rg -c '[0-9]+ (failed\|error)' >/dev/null; RGST=$?; test "$RGST" -eq 1; }` | — | ⬜ pending |
| 02-06-T2 | 02-06 | 7 | R1.7 | T-2-22, T-2-23 | An empty or whitespace colour is **absent**: no kitten argument is emitted at all, matching the recipe loader's convention — and the `normalize_color(color) or color` truthiness fallback, which silently resurrected the raw value whenever normalisation returned a falsy result, is replaced by an explicit `is None` branch. The whole RED set failed before any implementation, and GREEN adds no test | unit + integration | `for F in src/kitty_setup/scenes/background.py src/kitty_setup/scenes/accent.py; do test -f "$F" \|\| exit 1; rg -q 'is None' "$F" \|\| exit 1; rg -c 'normalize_color\(color\) or color' "$F" >/dev/null; RGST=$?; test "$RGST" -eq 1 \|\| exit 1; done` ; `OUT="$(uv run pytest tests/unit/test_scenes_background.py tests/unit/test_scenes_accent.py -q 2>&1)" && printf '%s\n' "$OUT" \| rg -q '(^\|[^0-9])[0-9]+ passed' && { printf '%s\n' "$OUT" \| rg -c '[0-9]+ (failed\|error)' >/dev/null; RGST=$?; test "$RGST" -eq 1; }` ; `OUT="$(make test-integration PYTEST_ARGS='tests/integration/test_color_normalization_e2e.py -q' 2>&1)" && printf '%s\n' "$OUT" \| rg -q '(^\|[^0-9])[0-9]+ passed' && { printf '%s\n' "$OUT" \| rg -c '[0-9]+ (failed\|error)' >/dev/null; RGST=$?; test "$RGST" -eq 1; }` ; `RED="$(git log --format='%H %s' \| rg '^[0-9a-f]+ test\(02-06\)' \| head -1 \| cut -d' ' -f1)" && test -n "$RED" && VENV="$(uv run python -c 'import sys; print(sys.prefix)')" && test -x "$VENV/bin/python" && D="$(mktemp -d)" && trap 'rm -rf "$D"' EXIT && GIT_INDEX_FILE="$D/.idx" git read-tree "$RED" && GIT_INDEX_FILE="$D/.idx" git checkout-index -a --prefix="$D/t/" && cd "$D/t" && OUT="$(PYTHONPATH="$D/t/src" "$VENV/bin/python" -m pytest tests/unit/test_scenes_colors.py tests/unit/test_scenes_background.py tests/unit/test_scenes_accent.py -q -p no:cacheprovider -k 'passthrough_rejects or absent_no_call or absent_keeps_fg' 2>&1)"; ST=$?; test "$ST" -eq 1 && N="$(printf '%s\n' "$OUT" \| rg -o '([0-9]+) failed' -r '$1' \| tail -1)" && test -n "$N" && test "$N" -ge 14 && { printf '%s\n' "$OUT" \| rg -c '[0-9]+ (passed\|error)' >/dev/null; RGST=$?; test "$RGST" -eq 1; }` ; `GREEN="$(git log --format='%H %s' \| rg '^[0-9a-f]+ feat\(02-06\)' \| head -1 \| cut -d' ' -f1)" && test -n "$GREEN" && ST="$(git diff-tree --no-commit-id -r -M --name-status "$GREEN")" && test -n "$ST" && { printf '%s\n' "$ST" \| cut -f2- \| rg -c '(^\|\t)tests/' >/dev/null; RGST=$?; test "$RGST" -eq 1; }` | kitty and `cage` (headless, no desktop window) | ⬜ pending |
| 02-07-T1 | 02-07 | 8 | R1.7 | T-2-27, T-2-28 | The install log is **removed outright** — D-11, because nothing reads it and the spec that required it is frozen history — and `_repo_root` survives, because deleting the writer's only remaining reason to exist would also have deleted a helper two other callers still need. `tmp/h36-install-log/` recorded that nothing reads the log before it was removed | unit + grep | `F=src/kitty_setup/installer.py && test -f "$F" && rg -q 'def _repo_root' "$F" && { rg -c '_record_install_log\|install\.log' "$F" >/dev/null; RGST=$?; test "$RGST" -eq 1; }` ; `{ rg -c -g '!.planning/**' -g '!tests/**' -g '!docs/**' '_record_install_log' . >/dev/null; RGST=$?; test "$RGST" -eq 1; }` ; `OUT="$(uv run pytest tests/unit/test_installer_uninstall.py -q -k 'install_log' 2>&1)" && printf '%s\n' "$OUT" \| rg -q '(^\|[^0-9])[0-9]+ passed' && { printf '%s\n' "$OUT" \| rg -c '[0-9]+ (failed\|error)' >/dev/null; RGST=$?; test "$RGST" -eq 1; }` | — | ⬜ pending |
| 02-07-T2 | 02-07 | 8 | R1.7 | T-2-25, T-2-26 | `_print_path_result` prints the `reason` that was **already computed** at six sites and then discarded. It also prints **every** manual hint line the result carries rather than the first, which is what the amended D-13 hint requirement means once a fish user must not be handed a bash line. The whole RED set failed before any implementation, and GREEN adds no test | unit + grep | `F=src/kitty_setup/installer.py && test -f "$F" && rg -q 'result\.reason' "$F" && rg -q 'manual_lines' "$F" && B="$(rg -A14 'def _print_path_result' "$F")" && printf '%s\n' "$B" \| rg -q 'result\.reason' && printf '%s\n' "$B" \| rg -q 'manual_lines'` ; `F=src/kitty_setup/installer.py && test -f "$F" && B="$(rg -A14 'def _print_path_result' "$F")" && { printf '%s\n' "$B" \| rg -c 'result\.manual_line[^s]' >/dev/null; RGST=$?; test "$RGST" -eq 1; }` ; `OUT="$(uv run pytest tests/unit/test_path_integration.py tests/unit/test_installer_uninstall.py -q -k 'reason or manual or hint or unsupported' 2>&1)" && printf '%s\n' "$OUT" \| rg -q '(^\|[^0-9])[0-9]+ passed' && { printf '%s\n' "$OUT" \| rg -c '[0-9]+ (failed\|error)' >/dev/null; RGST=$?; test "$RGST" -eq 1; }` ; `OUT="$(make doctor 2>&1)"; ST=$?; test "$ST" -eq 0 && test "$(printf '%s\n' "$OUT" \| rg -c '^(PASS\|SKIP) ')" -ge 9 && { printf '%s\n' "$OUT" \| rg -c '^FAIL ' >/dev/null; RGST=$?; test "$RGST" -eq 1; }` ; `RED="$(git log --format='%H %s' \| rg '^[0-9a-f]+ test\(02-07\)' \| head -1 \| cut -d' ' -f1)" && test -n "$RED" && VENV="$(uv run python -c 'import sys; print(sys.prefix)')" && test -x "$VENV/bin/python" && D="$(mktemp -d)" && trap 'rm -rf "$D"' EXIT && GIT_INDEX_FILE="$D/.idx" git read-tree "$RED" && GIT_INDEX_FILE="$D/.idx" git checkout-index -a --prefix="$D/t/" && cd "$D/t" && OUT="$(PYTHONPATH="$D/t/src" "$VENV/bin/python" -m pytest tests/unit/test_installer_uninstall.py tests/unit/test_path_integration.py -q -p no:cacheprovider -k 'install_log or path_report_reason or path_report_hint' 2>&1)"; ST=$?; test "$ST" -eq 1 && N="$(printf '%s\n' "$OUT" \| rg -o '([0-9]+) failed' -r '$1' \| tail -1)" && test -n "$N" && test "$N" -ge 4 && { printf '%s\n' "$OUT" \| rg -c '[0-9]+ (passed\|error)' >/dev/null; RGST=$?; test "$RGST" -eq 1; }` ; `GREEN="$(git log --format='%H %s' \| rg '^[0-9a-f]+ feat\(02-07\)' \| head -1 \| cut -d' ' -f1)" && test -n "$GREEN" && ST="$(git diff-tree --no-commit-id -r -M --name-status "$GREEN")" && test -n "$ST" && { printf '%s\n' "$ST" \| cut -f2- \| rg -c '(^\|\t)tests/' >/dev/null; RGST=$?; test "$RGST" -eq 1; }` | — | ⬜ pending |
| 02-08-T1 | 02-08 | 9 | R1.6 | T-2-29 | Both env builders that invoke `kitty_setup.cli` strip the ambient `KITTY_WINDOW_ID`, so a result no longer depends on whether the suite was launched from inside kitty — while `test_scene_recipe_e2e.py:125`'s **deliberate re-injection** survives, because that one is load-bearing for the fill-current-tab assertion; a static rule in the **unit** tree stops the seventh builder from repeating the mistake. RED holds only the unit-tree tests. The two integration env builders' `env.pop` edits are the fix, not a test, so they land in GREEN | unit + grep | `for F in tests/integration/test_h25_scene_launcher.py tests/integration/test_scene_recipe_e2e.py; do test -f "$F" \|\| exit 1; rg -q 'env\.pop\("KITTY_WINDOW_ID", None\)' "$F" \|\| exit 1; done` ; `test "$(rg -c 'env\.pop\("KITTY_WINDOW_ID", None\)' tests/integration/test_scene_recipe_e2e.py)" = '2' && rg -q 'env\["KITTY_WINDOW_ID"\] = str\(window_id\)' tests/integration/test_scene_recipe_e2e.py` ; `OUT="$(uv run pytest tests/unit/test_integration_env_hygiene.py -q 2>&1)" && printf '%s\n' "$OUT" \| rg -q '(^\|[^0-9])[0-9]+ passed' && { printf '%s\n' "$OUT" \| rg -c '[0-9]+ (failed\|error)' >/dev/null; RGST=$?; test "$RGST" -eq 1; }` | — | ⬜ pending |
| 02-08-T2 | 02-08 | 9 | R1.7 | T-2-30 | `prune --keep -1` and `--older-than -1` are rejected by **argparse**, the layer that owns CLI range checks, with a usage error rather than a traceback — and `pruner`'s own two `ValueError` guards stay, because they are the contract for a direct library caller | unit + grep | `F=src/kitty_setup/cli.py && test -f "$F" && rg -q 'ArgumentTypeError' "$F" && test "$(rg -c 'type=_non_negative_int\|type=_nonnegative_int' "$F")" = '2'` ; `F=src/kitty_setup/pruner.py && test -f "$F" && test "$(rg -c 'raise ValueError' "$F")" = '2'` ; `OUT="$(uv run pytest tests/unit/test_cli.py tests/unit/test_pruner.py -q -k 'negative or keep or older' 2>&1)" && printf '%s\n' "$OUT" \| rg -q '(^\|[^0-9])[0-9]+ passed' && { printf '%s\n' "$OUT" \| rg -c '[0-9]+ (failed\|error)' >/dev/null; RGST=$?; test "$RGST" -eq 1; }` | — | ⬜ pending |
| 02-08-T3 | 02-08 | 9 | R1.7 | T-2-31, T-2-32 | **U-1 pinned rather than implemented.** The teardown verb stays `close-window`, and the measurement that made that a decision — `close-os-window` is not a `kitten @` subcommand in kitty 0.49.0, and the call sits inside `except HarnessCommandError: pass`, so the swap would leak one kitty process per integration test *silently* — is recorded in the test's own docstring so a later reader cannot mistake it for an oversight | unit + grep | `F=tests/unit/test_harness_teardown.py && test -f "$F" && rg -q 'close-window' "$F" && rg -q '0\.49\.0' "$F" && rg -q 'HarnessCommandError' "$F"` ; `F=src/kitty_setup/harness/kitty_session.py && test -f "$F" && rg -q 'close-window' "$F" && { rg -c 'close-os-window' "$F" >/dev/null; RGST=$?; test "$RGST" -eq 1; }` ; `OUT="$(uv run pytest tests/unit/test_harness_teardown.py -q 2>&1)" && printf '%s\n' "$OUT" \| rg -q '(^\|[^0-9])[0-9]+ passed' && { printf '%s\n' "$OUT" \| rg -c '[0-9]+ (failed\|error)' >/dev/null; RGST=$?; test "$RGST" -eq 1; }` ; `OUT="$(make test-integration PYTEST_ARGS='tests/integration/test_h25_scene_launcher.py tests/integration/test_scene_recipe_e2e.py -q' 2>&1)" && printf '%s\n' "$OUT" \| rg -q '(^\|[^0-9])[0-9]+ passed' && { printf '%s\n' "$OUT" \| rg -c '[0-9]+ (failed\|error)' >/dev/null; RGST=$?; test "$RGST" -eq 1; }` ; `RED="$(git log --format='%H %s' \| rg '^[0-9a-f]+ test\(02-08\)' \| head -1 \| cut -d' ' -f1)" && test -n "$RED" && VENV="$(uv run python -c 'import sys; print(sys.prefix)')" && test -x "$VENV/bin/python" && D="$(mktemp -d)" && trap 'rm -rf "$D"' EXIT && GIT_INDEX_FILE="$D/.idx" git read-tree "$RED" && GIT_INDEX_FILE="$D/.idx" git checkout-index -a --prefix="$D/t/" && cd "$D/t" && OUT="$(PYTHONPATH="$D/t/src" "$VENV/bin/python" -m pytest tests/unit/test_integration_env_hygiene.py tests/unit/test_cli.py -q -p no:cacheprovider -k 'current_tree or prune_negative' 2>&1)"; ST=$?; test "$ST" -eq 1 && N="$(printf '%s\n' "$OUT" \| rg -o '([0-9]+) failed' -r '$1' \| tail -1)" && test -n "$N" && test "$N" -ge 3 && { printf '%s\n' "$OUT" \| rg -c '[0-9]+ (passed\|error)' >/dev/null; RGST=$?; test "$RGST" -eq 1; }` ; `GREEN="$(git log --format='%H %s' \| rg '^[0-9a-f]+ feat\(02-08\)' \| head -1 \| cut -d' ' -f1)" && test -n "$GREEN" && ST="$(git diff-tree --no-commit-id -r -M --name-status "$GREEN")" && test -n "$ST" && { printf '%s\n' "$ST" \| cut -f2- \| rg -c '(^\|\t)tests/unit/' >/dev/null; RGST=$?; test "$RGST" -eq 1; } && printf '%s\n' "$ST" \| cut -f2- \| rg -q 'tests/integration/test_h25_scene_launcher\.py' && printf '%s\n' "$ST" \| cut -f2- \| rg -q 'tests/integration/test_scene_recipe_e2e\.py'` | kitty and `cage` for the integration half (the runner scrubs the ambient kitty variables, so this proves the outside-kitty path) | ⬜ pending |
| 02-09-T1 | 02-09 | 10 | R0.11 | T-2-33, T-2-35 | Everything a formatter and an auto-fixer can close is closed by them, and the four mechanical residuals by hand — including the two `SIM105` rewrites at the U-1 teardown line, which **keep the verb `02-08` pinned**. The before-state of all five tools was recorded in `tmp/r011-sizing/` before the first edit | tool + grep | `uv run black --check src` ; `OUT="$(uv run ruff check src --output-format concise 2>&1)" && { printf '%s\n' "$OUT" \| rg -c 'RUF001\|E501\|SIM105\|RUF100' >/dev/null; RGST=$?; test "$RGST" -eq 1; }` ; `F=src/kitty_setup/harness/kitty_session.py && test -f "$F" && test "$(rg -c 'contextlib\.suppress' "$F")" -ge 2 && rg -q 'close-window' "$F" && { rg -c 'close-os-window' "$F" >/dev/null; RGST=$?; test "$RGST" -eq 1; }` | — | ⬜ pending |
| 02-09-T2 | 02-09 | 10 | R0.11 | — | The eight submodule re-exports in `scenes/__init__.py` are **deliberate** — they are what makes `cli.scenes.<name>` resolve for `monkeypatch.setattr` — so they are declared with `__all__` where pyright can see the intent, rather than kept alive by a blanket `# noqa: F401` the conventions forbid | tool + grep | `F=src/kitty_setup/scenes/__init__.py && test -f "$F" && { rg -c 'noqa' "$F" >/dev/null; RGST=$?; test "$RGST" -eq 1; } && { rg -q '__all__' "$F" \|\| rg -q 'import accent as accent' "$F"; }` ; `OUT="$(uv run pyright src 2>&1)" && { printf '%s\n' "$OUT" \| rg -c 'reportUnusedImport' >/dev/null; RGST=$?; test "$RGST" -eq 1; }` ; `OUT="$(uv run pytest tests/unit/test_cli.py -q 2>&1)" && printf '%s\n' "$OUT" \| rg -q '(^\|[^0-9])[0-9]+ passed' && { printf '%s\n' "$OUT" \| rg -c '[0-9]+ (failed\|error)' >/dev/null; RGST=$?; test "$RGST" -eq 1; }` | — | ⬜ pending |
| 02-09-T3 | 02-09 | 10 | R0.11, R0.13 | T-2-34, T-2-35 | Only the **four** symbols proven dead against `src`, `tests` **and** `tools` are deleted, per ROADMAP criterion 7: `TARGET_DIR_REL`; `env_path`, with its 17 call sites; the uncalled `KittySession.send_key`; and the uncalled `_find_tab_with_window` in `tests/integration/`. `session_dir` is **kept**: `02-11`'s socket tests read it, so it is test-consumed, not dead. The six test-consumed wrappers and the seven framework-idiom findings are kept. The whole integration suite, run headless with harness-owned kitty processes sampled, proves the harness deletions broke nothing | tool + grep + integration | `for S in send_key _find_tab_with_window TARGET_DIR_REL env_path; do { rg -c -g '!.planning/**' -- "$S" . >/dev/null; RGST=$?; test "$RGST" -eq 1; } \|\| exit 1; done` ; `F=src/kitty_setup/harness/kitty_session.py && test -f "$F" && for M in ls send_text launch get_text session_dir _make_socket_dir _remove_socket_dir; do rg -q "def ${M}\(" "$F" \|\| exit 1; done && { rg -c 'send_key' "$F" >/dev/null; RGST=$?; test "$RGST" -eq 1; }` ; `OUT="$(uv run vulture src tests 2>&1)"; ST=$?; test "$ST" -le 3 && N="$(printf '%s\n' "$OUT" \| rg -c 'unused' \|\| true)" && test -n "$N" && test "$N" -le 7 && { printf '%s\n' "$OUT" \| rg 'unused' \| rg -c -v "'(completer\|exc_type\|tb\|pytest_collection_modifyitems)'" >/dev/null; RGST=$?; test "$RGST" -eq 1; }` ; `hk() { K="$(pgrep -x kitty)"; P=$?; test "$P" -le 1 \|\| return 2; for p in $K; do tr '\0' '\n' < "/proc/$p/environ" 2>/dev/null \| rg -qx 'WLR_BACKENDS=headless' && printf '%s\n' "$p"; done; return 0; }; H0="$(hk)" \|\| exit 1; test -z "$H0" \|\| exit 1; S="$(mktemp)" \|\| exit 1; touch "$S.on" \|\| exit 1; trap 'rm -f "$S.on"; wait; rm -f "$S"' EXIT; ( while test -e "$S.on"; do hk >> "$S"; sleep 0.5; done ) & OUT="$(make test-integration PYTEST_ARGS='-q' 2>&1)" \|\| exit 1; rm -f "$S.on"; wait; N="$(printf '%s\n' "$OUT" \| rg -o '([0-9]+) passed' -r '$1' \| tail -1)"; test -n "$N" && test "$N" -ge 70 \|\| exit 1; { printf '%s\n' "$OUT" \| rg -c '[0-9]+ (failed\|error)' >/dev/null; RGST=$?; test "$RGST" -eq 1; } \|\| exit 1; test -s "$S" \|\| exit 1; H1="$(hk)" \|\| exit 1; test -z "$H1" \|\| exit 1; { pgrep -x cage >/dev/null; PC=$?; test "$PC" -eq 1; }` ; `OUT="$(make test 2>&1)" && N="$(printf '%s\n' "$OUT" \| rg -o '([0-9]+) passed' -r '$1' \| tail -1)" && test -n "$N" && test "$N" -ge 314 && { printf '%s\n' "$OUT" \| rg -c '[0-9]+ (failed\|error)' >/dev/null; RGST=$?; test "$RGST" -eq 1; }` | kitty and `cage` for the integration half | ⬜ pending |
| 02-10-T1 | 02-10 | 11 | R0.11 | T-2-37, T-2-38, T-2-39 | Two findings are closed by **real code**, each a behaviour change pinned by tests that failed first. `_download_installer` rejects a non-https URL before it creates a file or opens a connection. The kitty child's runtime-directory fallback is `tempfile.gettempdir()`. The rest is configured with a per-id rationale that bandit actually reads (`-c pyproject.toml`). No inline suppression remains under `src/`, and the config change and the directive removal land in **one** edit, so no `RUF100` appears | tool + grep | `uv run bandit -c pyproject.toml -q -r src` ; `F=.claude/conventions.md && test -f "$F" && rg -q -F 'uv run bandit -c pyproject.toml -q -r' "$F" && test "$(rg -o 'uv run bandit' "$F" \| wc -l)" -eq 1` ; `{ rg -c -g '!tests/**' 'noqa\|type: ignore\|nosec\|pylint: disable' src >/dev/null; RGST=$?; test "$RGST" -eq 1; }` ; `OUT="$(uv run ruff check src --output-format concise 2>&1)"; ST=$?; test "$ST" -le 1 && printf '%s\n' "$OUT" \| rg -q 'All checks passed\|Found [0-9]+ error' && { printf '%s\n' "$OUT" \| rg -c 'RUF100' >/dev/null; RGST=$?; test "$RGST" -eq 1; }` ; `F=src/kitty_setup/harness/kitty_session.py && test -f "$F" && rg -q -F 'env.setdefault("XDG_RUNTIME_DIR", tempfile.gettempdir())' "$F" && rg -q -F 'else tempfile.gettempdir()' "$F" && { rg -c -F '"/tmp"' "$F" >/dev/null; RGST=$?; test "$RGST" -eq 1; }` ; `for K in download_scheme guard_download_installer_url runtime_dir_fallback guard_runtime_dir_kept; do OUT="$(uv run pytest tests/unit/test_installer_download.py tests/unit/test_kitty_session_env.py -q -p no:cacheprovider -k "$K" 2>&1)" \|\| exit 1; printf '%s\n' "$OUT" \| rg -q '(^\|[^0-9])[0-9]+ passed' \|\| exit 1; { printf '%s\n' "$OUT" \| rg -c '[0-9]+ (failed\|error)' >/dev/null; RGST=$?; test "$RGST" -eq 1; } \|\| exit 1; done` ; `T="tests/unit/test_installer_download.py tests/unit/test_kitty_session_env.py" && uv run ruff check $T && uv run black --check $T && PY="$(uv run pyright $T 2>&1)" && printf '%s\n' "$PY" \| rg -q '(^\|[^0-9])0 errors'` | — | ⬜ pending |
| 02-10-T2 | 02-10 | 11 | R0.11 | — | The five cross-module private accesses become **public names in place**, under names that shadow nothing (`kitty_bin_path`, not `kitty_bin`). This is deliberately *not* a neutral module, which Phase 5's R3.3 owns. Every string target in both test trees follows the rename. The one dead comparison among the fifteen findings is removed, and its reachable half is kept | tool + grep | `uv run pyright src` ; `for S in _parse_listen_on_base _pgrep_kitty_pids _kitty_bin _parse_check; do { rg -c -- "\b${S}\b" src tests tools >/dev/null; RGST=$?; test "$RGST" -eq 1; } \|\| exit 1; done; { rg -c -F 'path_integration._find_block' src tests tools >/dev/null; RGST=$?; test "$RGST" -eq 1; } \|\| exit 1; { rg -c '^def _find_block' src/kitty_setup/path_integration.py >/dev/null; RGST=$?; test "$RGST" -eq 1; } \|\| exit 1; rg -q '^def parse_listen_on_base\(' src/kitty_setup/scenes/_client.py && rg -q '^def pgrep_kitty_pids\(' src/kitty_setup/scenes/_client.py && rg -q '^def kitty_bin_path\(' src/kitty_setup/installer.py && rg -q '^def parse_check\(' src/kitty_setup/config_updater.py && rg -q '^def find_block\(' src/kitty_setup/path_integration.py && rg -q '^def _find_block\(' src/kitty_setup/config_updater.py` ; `F=src/kitty_setup/harness/kitty_session.py && test -f "$F" && { rg -c 'value is True' "$F" >/dev/null; RGST=$?; test "$RGST" -eq 1; } && rg -q 'value == ""' "$F"` ; `OUT="$(make test-integration PYTEST_ARGS='tests/integration/test_h01_cwd.py tests/integration/test_client_socket_discovery.py tests/integration/test_h22_window_title.py tests/integration/test_h23_styling.py tests/integration/test_h25_scene_launcher.py -q' 2>&1)" && N="$(printf '%s\n' "$OUT" \| rg -o '([0-9]+) passed' -r '$1' \| tail -1)" && test -n "$N" && test "$N" -ge 25 && { printf '%s\n' "$OUT" \| rg -c '[0-9]+ (failed\|error)' >/dev/null; RGST=$?; test "$RGST" -eq 1; }` | kitty and `cage` for the integration half | ⬜ pending |
| 02-10-T3 | 02-10 | 11 | R0.11, R0.13 | T-2-40, T-2-41, T-2-42, T-2-44 | The vulture gate's scope is **settled by measuring all three candidate commands**, and `vulture_allowlist.py` holds only criterion 7's four framework idioms. ROADMAP criterion 6 and `.claude/conventions.md` name the settled vulture command and the `-c` bandit form. The pyright baseline is corrected and vulture's is scoped, both asserted positively. The roadmap keeps its eleven phase sections, and Phase 2 keeps its seven criteria. The phase closes on `make doctor` and on the whole integration suite, with harness-owned kitty processes sampled | tool + shell | `F=vulture_allowlist.py && test -f "$F" && for N in completer exc_type '\btb\b' pytest_collection_modifyitems; do rg -q "${N}.*#" "$F" \|\| exit 1; done && rg -q 'R0\.11' "$F" && test "$(rg -c '^[a-zA-Z_]' "$F")" -le 6 && { rg -c 'send_key\|session_dir\|TARGET_DIR_REL\|env_path\|_find_tab_with_window\|uninstall_config_only\|send_text\|get_text' "$F" >/dev/null; RGST=$?; test "$RGST" -eq 1; }` ; `uv run ruff check src && uv run black --check src && uv run pyright src && uv run bandit -c pyproject.toml -q -r src` ; `OUT="$(uv run vulture src tests vulture_allowlist.py 2>&1)"; ST=$?; test "$ST" -eq 0 && { printf '%s\n' "$OUT" \| rg -c 'unused' >/dev/null; RGST=$?; test "$RGST" -eq 1; }` ; `RM=.planning/ROADMAP.md && test -f "$RM" && test "$(rg -c '^### Phase [0-9]+(\.[0-9]+)?:' "$RM")" = '11' && test "$(awk '/^### Phase 2:/{p=1;next} /^### Phase 3:/{p=0} p' "$RM" \| rg -c '^  [0-9]\.')" = '7'` ; `RM=.planning/ROADMAP.md && test -f "$RM" && C6="$(awk '/^### Phase 2:/{p=1;next} /^### Phase 3:/{p=0} p' "$RM" \| awk '/^  6\./{f=1} /^  7\./{f=0} f' \| tr '\n' ' ' \| tr -s ' ')" && test -n "$C6" && printf '%s\n' "$C6" \| rg -q -F 'uv run vulture src tests vulture_allowlist.py' && printf '%s\n' "$C6" \| rg -q -F 'uv run bandit -c pyproject.toml -q -r src' && test "$(printf '%s\n' "$C6" \| rg -o 'uv run vulture' \| wc -l)" -eq 1 && test "$(printf '%s\n' "$C6" \| rg -o 'uv run bandit' \| wc -l)" -eq 1` ; `RM=.planning/ROADMAP.md && RQ=.planning/REQUIREMENTS.md && test -f "$RM" && test -f "$RQ" && G="$(awk '/must not regress/{f=1} /A phase that \*adds\*/{f=0} f' "$RM" \| tr '\n' ' ' \| tr -s ' ')" && test -n "$G" && Q="$(awk '/\*\*R0\.11\*\*/{f=1} /\*\*R0\.12\*\*/{f=0} f' "$RQ" \| tr '\n' ' ' \| tr -s ' ')" && test -n "$Q" && printf '%s\n' "$G" \| rg -q -F 'of which 15 are in' && printf '%s\n' "$G" \| rg -q -F 'uv run pyright src' && printf '%s\n' "$G" \| rg -q -F 'vulture 12 (' && printf '%s\n' "$G" \| rg -q -F 'uv run vulture src tests' && printf '%s\n' "$Q" \| rg -q -F 'carries **15** of pyright' && printf '%s\n' "$Q" \| rg -q -F 'uv run pyright src' && { printf '%s\n' "$G" \| rg -c -F 'of which 19 are' >/dev/null; RGST=$?; test "$RGST" -eq 1; } && { printf '%s\n' "$Q" \| rg -c -F 'carries **19**' >/dev/null; RGST2=$?; test "$RGST2" -eq 1; }` ; `F=.claude/conventions.md && test -f "$F" && rg -q -F 'uv run vulture src tests vulture_allowlist.py' "$F" && test "$(rg -o 'uv run vulture' "$F" \| wc -l)" -eq 1` ; `OUT="$(make doctor 2>&1)"; ST=$?; test "$ST" -eq 0 && test "$(printf '%s\n' "$OUT" \| rg -c '^(PASS\|SKIP) ')" -ge 9 && { printf '%s\n' "$OUT" \| rg -c '^FAIL ' >/dev/null; RGST=$?; test "$RGST" -eq 1; }` ; `hk() { K="$(pgrep -x kitty)"; P=$?; test "$P" -le 1 \|\| return 2; for p in $K; do tr '\0' '\n' < "/proc/$p/environ" 2>/dev/null \| rg -qx 'WLR_BACKENDS=headless' && printf '%s\n' "$p"; done; return 0; }; H0="$(hk)" \|\| exit 1; test -z "$H0" \|\| exit 1; S="$(mktemp)" \|\| exit 1; touch "$S.on" \|\| exit 1; trap 'rm -f "$S.on"; wait; rm -f "$S"' EXIT; ( while test -e "$S.on"; do hk >> "$S"; sleep 0.5; done ) & OUT="$(make test-integration PYTEST_ARGS='-q' 2>&1)" \|\| exit 1; rm -f "$S.on"; wait; N="$(printf '%s\n' "$OUT" \| rg -o '([0-9]+) passed' -r '$1' \| tail -1)"; test -n "$N" && test "$N" -ge 70 \|\| exit 1; { printf '%s\n' "$OUT" \| rg -c '[0-9]+ (failed\|error)' >/dev/null; RGST=$?; test "$RGST" -eq 1; } \|\| exit 1; test -s "$S" \|\| exit 1; H1="$(hk)" \|\| exit 1; test -z "$H1" \|\| exit 1; { pgrep -x cage >/dev/null; PC=$?; test "$PC" -eq 1; }` | installed `my-kitty`; kitty and `cage` for the whole-suite run | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

**Prohibition guards, listed separately because they are vacuous by design.** Four gates in this phase
assert the absence of something that has **zero occurrences today**, so they can never evidence progress —
they exist to catch a defect being *reintroduced*, and each says so in its own `<fails_when>` rather than
being presented as a passing check:

1. `02-01`: `shutil.which` absent from `installer.py`. Measured zero today — the PATH lookup D-02 rules
   out lives in `doctor.py:207`, not here, and `doctor.py:37` and `:166` use `shutil.which`
   legitimately for `kitty` and `kitten`. The guard is against the lookup being rebuilt in the installer.
2. `02-04`: `shlex` absent from the `_launch_argv` region. The argv path must stay unquoted; this is a
   scope guard, region-scoped precisely because `shlex` is *required* elsewhere in the same file.
3. `02-06`: `rgba`/`hsl` absent from `colors.py`. Zero today; the guard is against the U-2 narrowing
   being widened back to forms kitty rejects.
4. `02-08`: `close-os-window` absent from `kitty_session.py`. Zero today; the guard is U-1 itself.

---

## Requirement Coverage

Every requirement the ROADMAP assigns to this phase, with the task that closes it and the one command a
later phase can re-run to ask whether it is still closed. **Nine rows, nine requirements.** R1.8 is
deliberately absent, because `02-CONTEXT.md` defers it to Phase 3. R0.13 was added on 2026-09-23, after
the first eight.

| Requirement | Owning tasks | Definitive re-runnable command | Phase criterion |
|-------------|--------------|--------------------------------|-----------------|
| R1.1 | 02-01-T1, 02-01-T2, 02-02-T1, 02-02-T2, **02-02-T3** | `OUT="$(make doctor 2>&1)"; ST=$?; test "$ST" -eq 0 && test "$(printf '%s\n' "$OUT" \| rg -c '^(PASS\|SKIP) ')" -ge 9 && { printf '%s\n' "$OUT" \| rg -c '^FAIL ' >/dev/null; RGST=$?; test "$RGST" -eq 1; }` | 1 — **and Phase 1's deferred-merge precondition** |
| R1.2 | 02-03-T2 | `OUT="$(uv run pytest tests/unit/test_makefile_targets.py -q 2>&1)" && printf '%s\n' "$OUT" \| rg -q '(^\|[^0-9])2 passed'` | 2 |
| R1.3 | 02-03-T1 | `OUT="$(uv run pytest tests/unit/test_tools_uninstall_sh.py -q 2>&1)" && printf '%s\n' "$OUT" \| rg -q '(^\|[^0-9])[0-9]+ passed' && { printf '%s\n' "$OUT" \| rg -c '[0-9]+ (failed\|error)' >/dev/null; RGST=$?; test "$RGST" -eq 1; }` | 2 |
| R1.4 | 02-04-T1, 02-04-T2 | `OUT="$(uv run pytest tests/unit/test_scenes_launcher.py -q -k 'pane0 or window_id' 2>&1)" && printf '%s\n' "$OUT" \| rg -q '(^\|[^0-9])[0-9]+ passed'` plus `make test-integration PYTEST_ARGS='tests/integration/test_scene_fill_tab_e2e.py -q'` | 3 |
| R1.5 | 02-05-T1, 02-05-T2, 02-05-T3 | `OUT="$(uv run pytest tests/unit/test_config_updater.py tests/unit/test_doctor.py -q 2>&1)" && printf '%s\n' "$OUT" \| rg -q '(^\|[^0-9])[0-9]+ passed' && { printf '%s\n' "$OUT" \| rg -c '[0-9]+ (failed\|error)' >/dev/null; RGST=$?; test "$RGST" -eq 1; }` | 4 |
| R1.6 | 02-08-T1 | `OUT="$(uv run pytest tests/unit/test_integration_env_hygiene.py -q 2>&1)" && printf '%s\n' "$OUT" \| rg -q '(^\|[^0-9])[0-9]+ passed'` — the **static** rule, which runs in a plain `make test`; the behavioural half is `make test-integration` over the two modules | 4 |
| R1.7 | 02-04-T2, 02-05-T3, 02-06-T1, 02-06-T2, 02-07-T1, 02-07-T2, 02-08-T2, 02-08-T3 | No single command: R1.7 is eight independent minor defects across six modules. The aggregate is `make test` at its floor plus each owning row above. **Seven of the eight are pinned by a regression test; the eighth is U-1, pinned by a test that asserts the verb did *not* change.** | 5 |
| R0.11 | 02-09-T1, 02-09-T2, 02-09-T3, 02-10-T1, 02-10-T2, 02-10-T3 | `uv run ruff check src && uv run black --check src && uv run pyright src && uv run bandit -c pyproject.toml -q -r src` plus the vulture command `02-10` task 3 settles (recommended: `uv run vulture src tests vulture_allowlist.py`) | 6 — **a hard gate for every later phase from here on**; and 7's dead-code sentence (`02-09-T3` deletes, `02-10-T3` allowlists only idioms) |
| R0.13 | **02-11-T1, 02-11-T2, 02-11-T3, 02-11-T4**. Every integration gate routes through the runner: 02-02-T3, 02-04-T2, 02-06-T2, 02-08-T3, 02-09-T3, 02-10-T2, 02-10-T3 | `OUT="$(make test-integration PYTEST_ARGS='-q' 2>&1)" && N="$(printf '%s\n' "$OUT" \| rg -o '([0-9]+) passed' -r '$1' \| tail -1)" && test -n "$N" && test "$N" -ge 70 && { printf '%s\n' "$OUT" \| rg -c '[0-9]+ (failed\|error)' >/dev/null; RGST=$?; test "$RGST" -eq 1; }` — a run with no compositor exits non-zero and prints no count, so it fails this command rather than passing it | 7 — **and Universal Phase Gate step 5's integration bullet for every later phase** |

---

## Gate Inventory

| Plan | `<automated>` gates | Commit-dependent | Commits | Notes |
|------|--------------------:|-----------------:|---------|-------|
| 02-11 | 20 | 4 | 2 (RED, GREEN) | Wave 1. Runs the whole integration suite through the target it creates, proves the no-compositor path on the real host, and (task 4) moves kitty's control socket out of the checkout and proves the suite from a worktree |
| 02-01 | 12 | 5 | 2 (RED, GREEN) | |
| 02-02 | 21 | 6 | 2 | Carries the spine gate. One gate, a one-hunk `README.md` diff, is pre-commit only and says so. RED-state is proven twice, unit and integration |
| 02-03 | 17 | 5 | 2 | |
| 02-04 | 16 | 6 | 2 | RED-state proven twice, unit and integration |
| 02-05 | 18 | 5 | 2 | Carries the spine gate |
| 02-06 | 16 | 6 | 2 | One gate (launcher untouched) is worktree/index scoped and says so. RED-state proven twice |
| 02-07 | 15 | 5 | 2 | Carries the spine gate |
| 02-08 | 18 | 5 | 2 | Its GREEN gate forbids unit tests only: the two integration env builders are the fix |
| 02-09 | 22 | 2 | 1 | Carries the spine gate. **Three gates are red until `02-10` lands** and are recorded as red, not weakened |
| 02-10 | 28 | 2 | 1 | Carries the spine gate, the whole-gate sweep and the verification-map gate |
| **Total** | **203** | **51** | **20** | Nine `type: tdd` plans × 2 commits + two `execute` plans × 1 |

**Why 51 are commit-dependent and all 51 run last.** A `type: tdd` plan carries between four and six:
  - the topology gate: exactly one `test(02-0N)` subject, exactly one `feat(02-0N)`, exactly two
    `(02-0N)` in total, and RED an ancestor of GREEN;
  - the RED-scope gate: RED touches only `tests/` and holds every new test module;
  - one or two RED-state gates, which materialise RED's own tree and require its new tests to fail
    (unit tests, plus integration tests through the runner for `02-02`, `02-04` and `02-06`);
  - the GREEN-contains-the-SUMMARY gate;
  - the GREEN-adds-no-test gate. `02-11` folds it into its GREEN-contents gate.
An `execute` plan carries two: exactly one `(02-0N)` subject, and that commit contains the SUMMARY. None of
them can pass before the commit they describe exists, so each is ordered last inside its task, and each
`<fails_when>` states the dependency explicitly.

**Four instrument decisions behind those 51, each measured rather than assumed:**

1. **`git log --format=%s`, never `--grep`.** `--grep` searches the whole message, so a commit body that
   merely *mentions* `(02-04)` would satisfy a subject gate. Reading `%s` restricts the match to the
   subject line, which is what the commit-granularity rule constrains.
2. **Full history, never `merge-base master HEAD`.** On this branch `git merge-base master HEAD` is
   `5452f54` — Phase 1's base, because **Phase 1 has not merged** — and it collapses to empty once the
   phase merges, which would make every range-scoped gate vacuous on re-run. Measured: the full-history
   form returns 0 for every `02-0N` id today (so the gates are non-vacuous) and 1 for `01-05` (so the
   instrument works).
3. **`git diff-tree --no-commit-id -r -M --name-status "$C"` against a resolved SHA, never
   `git diff --cached … HEAD`.** The `--cached` form reads the **index**, which is empty on any re-run
   after the commit — Phase 1 hit exactly this and its `01-VALIDATION.md` records the fix. `-M` is
   required so a rename reads as `R100` rather than as a delete plus an add; `--no-commit-id` is
   required because without it `diff-tree` prints the SHA as an output line that matches no status
   prefix and fails the gate on correct work.
4. **A throwaway index, never `git archive`, for the RED-state gates.** `.gitattributes:47` marks
   `tests/` `export-ignore`, so an archived RED tree has no tests to fail. `GIT_INDEX_FILE=<tmp> git
   read-tree` plus `checkout-index` materialises RED's own tree, and `PYTHONPATH` points at its `src/`,
   so the run sees RED's source rather than the working tree's.

---

## Map Completeness Gate

The map must be provably resolved, not merely look resolved. `02-10` task 3 runs these commands, and its
own verification-map gate chains the three counts:

```bash
V=.planning/phases/02-defect-remediation/02-VALIDATION.md
test -f "$V" || exit 1
test "$(rg -c '^\| 02-[0-9]+-T[0-9]' "$V")" = '29'                                  # no row added or lost
test "$(rg -c '^\| 02-[0-9]+-T[0-9].*\| *✅ *\|[[:space:]]*$' "$V")" = '29'           # every row passed
test "$(rg -c '^\| R[01]\.[0-9]+ ' "$V")" = '9'                                     # every requirement still has a coverage row
```

**Why each.** The count alone passes on a map of twenty-nine pending rows. The second command is the
positive assertion that every row passed. It accepts ✅ only, because the Sampling Rate section requires
every row at ✅ before `/gsd-verify-work`, and an honestly recorded ❌ still stops the phase. It is
**anchored to the row's last cell**, because Phase 1 measured the unanchored form passing on precisely
the all-pending map it was introduced to reject: its `File Exists` column was also a ✅/❌ column, so the
glyph matched mid-row. The third command guards the coverage table separately, because a requirement row
silently dropped would hide a requirement with no owner.

**The pending-marker check was retired in the 2026-09-23 revision.** It was an absence-of-literal gate
over this document. It was row-scoped, but it was still the kind of gate rule 3 below forbids. The
positive ✅ count subsumes it, because a row whose Status is pending does not end in ✅. Simulated on a
scratch copy of this finished document:
  - every row at ✅ passes;
  - one row left pending fails;
  - one row at ❌ fails;
  - the all-pending map as committed fails, with an empty count.

**Four scoping rules this document imposes on its own gates**, each learned from a measured Phase 1
failure rather than from reading:

1. **Status is resolved positively, never by the absence of the pending marker.** The legend line and
   this very section both contain the marker, so a whole-file absence form can never pass on a correct
   document. The row-scoped form this rule used to prescribe was still an absence gate over this
   document. This is structural, not incidental: a file that catalogues commands contains every string
   those commands search for.
2. **The row pattern requires `-T<digit>`.** The Gate Inventory table's rows begin `| 02-01 |`, and a
   bare `^\| 02-` prefix would count them as map rows — twenty-nine would read as forty. Re-measured
   against this file after the 2026-09-23 revision.
3. **No gate anywhere in this phase asserts the absence of a literal over this document or over a
   `PLAN.md`.** Absence gates target source files, `tools/`, the `Makefile`, `README.md`,
   `pyproject.toml`, `REQUIREMENTS.md` and `ROADMAP.md` — policy and code, never a document that quotes
   its own patterns as data. Where a plan's `<action>` had to name a literal its own gate negative-greps,
   it carries an explicit `planner-discipline-allow` directive instead of being silently exempt
   (`02-02`: `register-python-argcomplete`; `02-06`: the truthiness-fallback expression).
4. **`rg -c` never has its count compared to `'0'`.** `rg -c` prints nothing and exits 1 when there is
   no match, so `test "$(rg -c PAT f)" = '0'` **fails in exactly its passing state** — measured this
   session against a control file. Every absence gate in this phase instead captures ripgrep's status
   and requires exactly 1, which also fails closed on a malformed pattern (exit 2). One gate written in
   the broken form was found and corrected during planning; see correction 1 below.

---

## Wave 0 Requirements

Ten test modules this phase's gates name **did not exist when the phase was planned**, plus one harness
module and one config file. Each is created by the plan that first needs it — this phase has no separate Wave 0, because the
serialized wave structure means the creating plan always runs before any plan that re-runs its gate.
Verified absent at `1eb86bd`; the two `02-11` files re-verified absent at `bbed580`:

- [ ] `tests/unit/test_integration_runner.py` — created by `02-11` (RED commit, wave 1). It is the
      runner's contract and it is hermetic: a stubbed `PATH` with no compositor; fake compositors written
      as Python scripts, one of which **always exits 0**; a real pytest child over a `tmp_path` test file;
      leftover-process and timeout cases; the no-forgery rule for the runner's own text; and the Makefile
      shape. It deliberately does **not** extend `tests/unit/test_makefile_targets.py`, which `02-03`
      creates with an exact `2 passed` gate.
- [ ] `src/kitty_setup/harness/integration_runner.py` — created by `02-11` (GREEN). It is run as
      `uv run python -m kitty_setup.harness.integration_runner`, behind `make test-integration`.
- [ ] `tests/unit/test_kitty_session_socket.py` — created by `02-11` (RED commit, wave 1; `b3917b9`
      holds it with `test_integration_runner.py`). The socket-placement contract, with no kitty started:
      the path fits `sun_path` from a deliberately deep root, the directory is private and under the
      runtime dir, and it is removed on teardown and on failed startup.
- [ ] `tests/unit/test_installer_download.py` — created by `02-10` (wave 11). The `download_scheme`
      cases (an `http://`, a `file://` and an `ftp://` URL rejected, with no connection and no temporary
      file) and a guard that `INSTALLER_URL` still downloads, the network replaced by a recorder.
- [ ] `tests/unit/test_kitty_session_env.py` — created by `02-10`. The `runtime_dir_fallback` case and its
      guard, with `subprocess.Popen` replaced by a recorder, so no kitty is started.

- [ ] `tests/unit/test_installer_completion.py` — created by `02-01` (RED commit). The in-process
      shellcode generation, the zero-subcommand-names property (U-3), the `#compdef` first line, the
      unsupported-shell path, idempotence, and removal tied to `do_kitty`.
- [ ] `tests/integration/test_completion_e2e.py` — created by `02-02`. Real bash and real zsh, driven
      through argcomplete's own `_ARGCOMPLETE` protocol rather than a pty, and **skipping explicitly**
      when `zsh` is absent rather than passing quietly.
- [ ] `tests/unit/test_tools_uninstall_sh.py` — created by `02-03`. A `tmp_path` sandbox, `KITTI_FORCE`
      to bypass the confirm prompt (except in the one case that answers `n` to it, to read the
      will-remove list), an explicit `timeout=` on every subprocess call, and no dependency on
      `shellcheck` being installed.
- [ ] `tests/unit/test_makefile_targets.py` — created by `02-03`. Two cases, text-level: the `clean`
      help line's keep-set equals the set of `--keep-*` flags the recipe passes.
- [ ] `tests/unit/test_integration_env_hygiene.py` — created by `02-08`. The AST rule over
      `tests/integration/*.py`. **In the unit tree deliberately** (see the integration-gate trap above).
      The filter is *"the module builds an env for a subprocess whose argv contains `kitty_setup.cli`"* —
      measured to select exactly the four builders that matter with zero false positives. The research's
      sketched filter (*"the module references `scene`"*) would have flagged three harmless modules.
- [ ] `tests/unit/test_harness_teardown.py` — created by `02-08`. The U-1 pin, with the kitty-0.49.0
      measurement in its docstring.
- [ ] `vulture_allowlist.py` — created by `02-10`. It holds four names only, the framework idioms ROADMAP
      criterion 7 admits: `completer` (argcomplete), `exc_type` and `tb` (the `__exit__` signature), and
      `pytest_collection_modifyitems` (a pytest hook). Each has a one-line reason referencing R0.11 and
      criterion 7. `.claude/conventions.md:41` already
      names this file as vulture's config; that it has never existed is itself one of the sixteen
      findings.

**Already exists, corrected from the pattern map:** `tests/integration/test_scene_fill_tab_e2e.py` is a
98-line module with two cases. `02-04` **adds** its real-kitty space-in-cwd case to it rather than
creating it, and reads it in full first.

**No new package is installed by any plan in this phase.** pytest 8.3.0 is configured; all five quality
tools are already in `[dependency-groups] dev` and locked in `uv.lock`; `shlex`, `tempfile`,
`contextlib` and `enum` are stdlib. `02-RESEARCH.md`'s Package Legitimacy Audit records no package and
no `[ASSUMED]`/`[SUS]` entry, so no legitimacy checkpoint applies anywhere in the phase. `cage`, which
`02-11`'s runner needs, is a pre-existing host binary (`cage-0.3.1-1.fc44`) and not an install.

**One `pyproject.toml` prerequisite the new test modules create.** `tests/unit/test_tools_uninstall_sh.py`
and `tests/unit/test_makefile_targets.py` run subprocesses, which trips ruff's `S603`/`S607` under the
existing `"tests/**/*.py"` per-file-ignores list. `.claude/conventions.md:22-24` forbids an inline
`# noqa`, so the codes go in the config with a one-line rationale each — following the measured narrowing
lesson already recorded at `pyproject.toml:85-89`. This is `tests/` scope, so it does not affect R0.11,
which is `src/`-only, but a missing entry would make `make test`'s own lane noisy.

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| The hypothesis directories under `tmp/` | R1.1–R1.7, R0.11, R0.13 | **`tmp/` is gitignored** (bare `tmp/` in `.gitignore`; `git ls-files tmp/` returns nothing). A gate can assert the directory exists in the working tree at verification time — and every plan that runs an experiment does — but **no gate can assert it from a commit**, because the commit cannot contain it | Each owning plan's `<verify>` asserts that its artefacts exist. The directory is written **before** the plan's first source edit: the 2026-09-23 revision moved every one to step 0. The evidence itself is carried **into the SUMMARY**, quoted, because the SUMMARY is tracked and the directory is not. Directories: `h30-argcomplete-static` (02-01; 02-02 adds `rc-body.md` first), `h31-uninstall-sh` (02-03), `h32-color-forms` (02-06, re-read and extended by 02-08), `h33-minors` (02-04, re-read and extended by 02-08), `h34-parse-check` (02-05), `h35-headless-integration` (02-11), `h36-install-log` (02-07), `h37-r011-behaviour` (02-10), `r011-sizing` (02-09) |
| Whether real-shell completion actually *completes* for a human | R1.1 | The e2e test drives argcomplete's protocol directly, which proves registration and the byte match. Registration itself is proven in real bash and zsh, including a zsh block that install moved from above `compinit`, and doctor FAILs every zsh shape measured to register nothing. Two things stay manual. The first is whether a human pressing Tab in their own terminal sees the completions, since no pty and no kitty is driven. The second is zsh start-up that doctor does not read: a `compinit` in `~/.zlogin`, a `ZDOTDIR` away from `$HOME`, an `exec` before our block, or a plugin manager that defers `compinit` until after `~/.zshrc` finishes (zinit turbo `wait`, zsh-defer, a precmd-hooked `zicompinit`) — measured 2026-09-24 by the 02-02 interim check to wipe the registration while doctor PASSes, because the block is last and its body matches. No hermetic test can assert either about a stranger's shell | Read `02-02-SUMMARY.md`'s recorded bash and zsh transcripts, then optionally open a fresh login shell and press Tab. **Do not test this by talking to a running kitty session** |
| Does "bandit reports clean" mean **zero findings** or **zero HIGH**? | R0.11 | R0.11's own text records `0 high (8 medium, 19 low)` as the baseline while the criterion says "reports clean". Twenty-eight findings of configuration work (at `be69103`) hang on the reading, and it is the user's call, not a command's | `02-10`'s `<flagged_assumptions>` states both readings and the consequence of each; task 1 takes the stricter one (zero at any severity) and the SUMMARY presents it as overturnable. Read it and confirm or overturn |
| The vulture gate's final scope | R0.11 | Three candidate commands give three different finding sets, and the choice becomes a hard gate every later phase inherits. Which trade-off is right is a judgement | `02-10` task 3 runs all three (`src`; `src tests`; `src tests vulture_allowlist.py`) and records every count. Read the justification and confirm the settled command is the one written into ROADMAP criterion 6 |
| The parse check's blindness to a missing `include` (T-2-19) | R1.5 | Measured: the check collects value-conversion errors and does not report a missing `include` line at all. Fixing it is a different requirement from the four R1.5 asks for | `02-05` **reports and does not fix** it, with the measurement in the SUMMARY. Confirm the report exists and that no plan silently widened R1.5's scope to cover it |
| `my-kitty window background none` (the Phase 6 blocker) | — | Out of scope. `02-06` pins the current `none` behaviour with a test and attributes the gap to Phase 6 rather than fixing it here | Read `02-06-SUMMARY.md` and confirm the behaviour is pinned and attributed, and that nothing in this phase changed it |
| Whether doctor's `remote-control` check is PASS or SKIP | R1.1 | It depends on whether a kitty with remote control is live on the host at the moment the gate runs. Criterion 1 accepts either | Every spine gate accepts PASS **or** SKIP and requires neither. Read the nine recorded lines in `02-02-SUMMARY.md` and `02-10-SUMMARY.md` and confirm which |
| A host with **no** nested compositor | R0.13 | The loud-fail path is unit-tested with a stubbed `PATH` and exercised on this host through the real target with a `PATH` holding only `uv`. A host that genuinely lacks one, such as macOS in Phase 10, cannot be simulated further from here | Read `02-11-SUMMARY.md`'s no-compositor transcript. On such a host, `make test-integration` must exit non-zero and say the suite was NOT run; it is never a pass. Integration evidence for that phase must come from a host that has a compositor |

---

## Known Threat Patterns (ASVS V5 / V12 / V14-adjacent, level 1)

Forty-seven numbered threats across the eleven plans, plus `T-2-SC` (supply chain), which appears in every
plan as **accept / not applicable** because the phase installs nothing. Roll-up: **7 high, 23 medium, 17
low**; **43 mitigate, 4 accept** (`T-2-07`, `T-2-10`, `T-2-19`, `T-2-20`), plus `T-2-SC`. `02-11` added
`T-2-43` to `T-2-47`. Each plan carries its own full register with per-threat mitigations. The seven
**high** rows are repeated here because they are the phase's real security surface.

| ID | Threat | STRIDE | Control | Severity | Disposition | Plan |
|----|--------|--------|---------|----------|-------------|------|
| T-2-08 | `make clean` removes `kitty.app`, the symlink, the desktop entry and the backups — its help text promises the opposite | Denial of Service | The recipe passes `--keep-kitty --keep-backups`, the help line says `(keeps kitty + backups)`, and a test asserts the help line's keep-set equals the recipe's `--keep-*` set, so the two cannot drift again in either direction | high | mitigate | 02-03 |
| T-2-09 | A test module that exercises an **uninstall** script runs it against the real install | Tampering | Every case runs in a `tmp_path` sandbox with a fabricated binary on a scoped `PATH`, a complete replacement `env=` (an AST gate fails if the module's code reads `os.environ` in any form), `KITTI_FORCE` to bypass the prompt — or, in the one will-remove case, `n` piped to it, which exits before any binary is resolved — and an explicit `timeout=`; the real `~/.local` is never a subject | high | mitigate | 02-03 |
| T-2-12 | `launcher.py:238` interpolates pane 0's `cwd` into a `send-text` payload a live interactive shell then parses — a directory name containing `;` is command execution | Tampering / Elevation of Privilege | `shlex.quote` every interpolated value on the `send-text` path, proven by a payload assertion and a real-kitty case with a space in the cwd whose sentinel file must not appear | high | mitigate | 02-04 |
| T-2-13 | The same for pane 0's `cmd` at `:244`, which is sent raw while every other pane goes through `bash -lc` | Tampering | `bash -lc` with a quoted argument, matching the path already proven for panes 1+ | high | mitigate | 02-04 |
| T-2-42 | A whole-file write to `.planning/ROADMAP.md` while correcting two baseline numbers destroys the eleven phase sections outside the edited region | Denial of Service | Scoped `Edit` replacements only, with a gate counting `^### Phase [0-9]+(\.[0-9]+)?:` — the decimal component is required because `### Phase 8.5:` exists and a plain `[0-9]+:` pattern cannot match it, a gap Phase 1 measured | high | mitigate | 02-10 |
| T-2-43 | The integration run's verdict comes from a wrapper (the compositor) whose exit status is not pytest's, so a failing suite can report green | Repudiation | The verdict is read from a status file the child writes. A fake compositor that always exits 0 is a unit case. Every gate over the runner asserts pytest's own `N passed` and the absence of `failed\|error` in captured output | high | mitigate | 02-11 |
| T-2-44 | An integration run that did not happen (no compositor, no display, everything skipped) is counted as green, which is the defect R0.13 exists to remove | Repudiation | Every non-run path exits non-zero (69 or 70) with a message saying the suite was NOT run. A real-host gate runs the target with a `PATH` lacking `cage` and requires a non-zero exit and no passing count. Integration floors are `-ge 70` | high | mitigate | 02-11 |

**Scope honesty, carried from research.** Two of the phase's controls are hygiene rather than boundaries
and the plans say so: the `shlex.quote` fix is a real injection fix on a real path, but the *threat model*
is a user's own directory name, not a remote attacker — there is no untrusted network input anywhere in
this phase; and `02-10`'s https-scheme check guards a URL that is a module-level constant today, so it is
a guard against a future edit rather than a live exposure. Claiming more than that would be the same class
of untruth R2.8 exists to eliminate.

---

## Corrections to this map and to the plans, made at planning time with the reason recorded

1. *(2026-09-23)* **One gate was written in a form that fails in exactly its passing state and was fixed
   before any executor saw it.** `02-05-PLAN.md:341` read
   `test "$(rg -c '\+runpy' "$F")" = '0'`. Measured against a control file: `rg -c` prints **nothing**
   and exits 1 when there is no match, so the substitution captures the empty string and `test '' = '0'`
   is false — the gate would have reported red on correct work and could never report green. Rewritten
   into this phase's fail-closed idiom
   (`{ rg -c PAT "$F" >/dev/null; RGST=$?; test "$RGST" -eq 1; }`), which also fails closed on a
   malformed pattern. Same defect family as Phase 1's `01-VALIDATION.md` correction 3.
2. *(2026-09-23)* **`README.md:155-161` becomes false the moment R1.1 lands** and `02-RESEARCH.md` did
   not flag it. The paragraph tells the reader the rc block contains a guarded
   `register-python-argcomplete` eval line; after `02-01`/`02-02` it contains a source line for a
   generated file. `02-02` task 3 owns the one-paragraph correction, gated positively on the new
   mechanism and negatively on the old literal. `README.md` is otherwise Phase 8 / R6.1 territory, so
   the plan also gates the diff to a single hunk.
3. *(2026-09-23)* **The R1.6 static filter in the research would have produced three false positives.**
   *"The module references `scene`"* flags modules that never build a subprocess env. Measured correct
   filter: *"the module builds an env for a subprocess whose argv contains `kitty_setup.cli`"* → exactly
   four sites, zero false positives.
4. *(2026-09-23)* **The env-hygiene rule moved from `tests/integration/` to `tests/unit/`.** Under
   `tests/conftest.py:44-53` a module in the gated tree reports green while running nothing in a plain
   `make test`. A static AST rule needs no kitty, so the gate would have been invisible exactly where it
   matters.
5. *(2026-09-23)* **Four drifted or wrong line references, corrected and re-verified against `1eb86bd`.**
   `Makefile:26-28` → **`:27-29`** (`clean:` at `:27`); `test_h25_scene_launcher.py:393` → **`:394`**;
   `test_doctor.py`'s three completion tests are at **`:171`, `:189`, `:208`** (research said
   173/192/208); `cli.py`'s `--keep` is **`:107-113`** and `--older-than` **`:114-121`** (research said
   108-113 / 114-120). Every other file:line in the plans was re-read at `1eb86bd` rather than inherited.
6. *(2026-09-23)* **`env_path` has 17 call sites in `tests/unit/test_path_integration.py`, not 15**, so
   `02-09` task 3's deletion is a wider edit than research sized it.
7. *(2026-09-23)* **The house instrument for parse-check tests is `_fake_kitty_bin`**
   (`test_config_updater.py:48-53`, a generated shell script exiting with a scripted code) — not
   *"real kitty, skip if absent"* as the research's test shape said. The house form is hermetic and
   extends naturally to scripted **stderr**, which is exactly what R1.5 needs; `02-05` uses it.
8. *(2026-09-23)* **`_repo_root` has three callers and keeps two after D-11**, so it must not be deleted
   along with `_record_install_log`. Research asked the question; this answers it, and `02-07`'s gate
   asserts the definition survives.
9. *(2026-09-23)* **Only the `session_dir` *property* is dead** — `self._session_dir` is used at ten
   sites. A gate written against the attribute would have deleted working code.
10. *(2026-09-23)* **`kitty_session.py:179`'s `value is True` is genuinely unreachable**: the parameter is
    annotated `str` and `launch`'s only caller (`tests/integration/test_h01_cwd.py:40-62`) passes a
    `dict[str, str]`. The reachable half (`value == ""`) is kept. This is the one real bug among
    pyright's fifteen findings.
11. *(2026-09-23)* **A config-versus-suppression ordering trap.** Adding a rule id to ruff's ignore list
    turns every existing `# noqa` for that id into a `RUF100` finding. `02-10` task 1 therefore lands the
    config entry and the directive removal in **one** edit. The precedent is already in the repo at
    `pyproject.toml:85-89`.
12. *(2026-09-23)* **`docs/agent-iteration.md` steps 2 and 8 still reference the frozen OpenSpec system.**
    Reported here, planned nowhere: it is documentation drift that Phase 8 / R6.1 owns, and inventing a
    task for it would widen this phase past its requirements.
13. *(2026-09-23)* **`codegraph` query shapes, measured.** `codegraph files --json --filter <pattern>`
    returns *"No files found"* — `--filter` takes a **directory**; a path query needs
    `--pattern '**/<file>'`. Index health is `codegraph status --json \| jq -e '.initialized == true and
    .fileCount > 0'`. No gate in this phase uses a symbol query to answer a path question.

14. *(2026-09-23, R0.13 delta)* **A new first plan, and every integration gate routed through it.** R0.13
    was added after the ten plans were written. `02-11` (wave 1, `depends_on: []`) creates
    `make test-integration`, and every existing plan's `wave:` moved up by one, with `02-01` now depending
    on `02-11`. Twelve bare integration invocations in five plans were rewritten to go through the runner.
    Each keeps the property it already had (a skipped run fails the gate) and adds gate rule 7: pytest's own
    `N passed` and no `failed|error` from captured output, never the wrapper's status alone. The five plans
    are `02-02` ×2 (plus one new `<automated>` gate that replaces a capture-only step), `02-04` ×2, `02-06`
    ×2, `02-08` ×2 (plus two prose mentions) and `02-10` ×4. The last includes the phase-close full-suite
    gate, which could previously pass having run nothing.
15. *(2026-09-23, R0.13 delta)* **The suite floor was stale after the rebase.** The phase was rebased onto
    Phase 1's gap-closure tip, and `01-06` added three tests (`tests/unit/test_git_hooks.py`: 21 passed, not
    18). Every `-ge 311` floor became `-ge 314`, and "the 311 measured at `1eb86bd`" became "the 314
    measured at `22b99f1`". Measured with `make test 2>&1 | tail -1`, giving `314 passed, 70 skipped`.
16. *(2026-09-23, R0.13 delta)* **The vulture triage was wrong twice, and criterion 7 changes what the
    allowlist may hold.** `KittySession.send_key` was filed as test-used, but measured, nothing calls it. Its
    one mention in `tests/` is a docstring explaining why the test avoids it. `02-09` now deletes it,
    together with `tests/integration/`'s uncalled `_find_tab_with_window`: five deletions, not three.
    Scanning `tests` does not clear every false positive either: `completer` ×4 and the
    `pytest_collection_modifyitems` hook survive it. Per criterion 7, the allowlist holds four
    framework-idiom names, not two, and nothing dead. In a scratch copy, the simulated deletions left
    `vulture src tests` reporting exactly the seven idiom findings, with 314 unit tests passing.
17. *(2026-09-23, R0.13 delta)* **`02-10`'s suppression inventory missed four comments.** `src/` carries 17
    suppression comments, not 13: there are four `# type: ignore[attr-defined]` on `cli.py`'s `completer`
    lines, which `02-10`'s no-suppression gate would have caught red on its own plan. Task 1 now owns them.
    Measured: `typing.cast(Any, action).completer = fn` gives pyright strict 0 errors (the bare
    assignment's control reports `reportAttributeAccessIssue`), and ruff stays clean.
18. *(2026-09-23, R0.13 delta)* **Two host facts the runner depends on, measured.** First, `cage` 0.3.1
    **did** pass a normal child exit through (`exit 7` → 7). The runner still ignores its status, because
    a pass-through observed once is not a contract. Second, `KittySession`'s control socket must fit
    AF_UNIX's 108 bytes. From a 155-byte scratch path, kitty logged `Invalid listen_on … ignoring`, and
    exactly the four `KittySession` tests failed while the other 66 passed. From the repository path
    (72 bytes), all 70 pass.
19. *(2026-09-23, R0.13 delta)* **Makefile line drift caused by the new first plan.** `02-11` adds one help
    line above `clean:`, so `02-03`'s `Makefile:27-29` became `:28-30` and its `.PHONY` claim now names
    `test-integration`. `02-03`'s gates were already pattern-scoped (`rg -A3 '^clean:'`) and needed no
    change.
20. *(2026-09-23, cross-AI plan-review revision)* **Three review lanes (A, B, C) and a sweep over every
    `type: tdd` plan, applied to the plans and to this map.**
    - **Test-first order.** Every `type: tdd` plan now writes its hypothesis directory at step 0 and its
      whole RED set before any source edit, and no later task changes a test. Each plan carries a
      RED-state gate, run against RED's own tree through a throwaway index, and a GREEN-adds-no-test
      gate. The last-task row of each plan here carries both.
    - **`02-11`.** It gained task 4, the socket fix that landed inside it, so the map has twenty-nine rows.
      Its interrupt and `SIGTERM`/`SIGHUP` cases are named and gated one name at a time.
    - **Whole-suite gates.** They sample harness-owned kitty processes, where the old form compared every
      kitty PID.
    - **Doctor and bandit.** Every spine gate runs `make doctor`. Every bandit command carries
      `-c pyproject.toml`: 1094 findings without it against 30 with it, measured, and with the skips
      written in, 30 against 2, simulated.
    - **`02-10`'s behaviour changes.** They are recorded first, in `h37-r011-behaviour`, and pinned by
      tests run red.
    - **`02-10`'s renames.** They use names that shadow nothing: `kitty_bin_path`, because a plain
      `kitty_bin` is unbound inside `install()`. Its rename gate is word-bounded. The old gate could not
      pass on correct work, because of `_fake_kitty_bin` and config_updater's own `_find_block`.
    - **`02-10`'s other gates.**
      - The RUF100 gate checks ruff's own status.
      - The baseline gate asserts the corrected sentences positively. The old one passed with `999`
        substituted.
      - The criteria gate is scoped to Phase 2. The old one passed with all seven criteria deleted.
      - Criterion 6 is gated on its own text.
      - The map is resolved positively at phase close.
    - **The baseline.** Re-measured at `5452f54` itself, the recorded vulture **12** is the whole-repo
      figure (`src tests` 12, `src` 16), so `02-10` names its scope rather than substituting 16. Pyright's
      19 was simply wrong: it is 15.
    - **This map.** The pending-marker check was retired, because it was an absence gate over this
      document. The `02-05-T1` row drops the plan gate's `def _parse_check` half, which `02-10`'s rename
      falsifies at wave 11.
---

## Hand-off Notes

- **`ROADMAP.md:132` still reads `**Plans**: TBD`.** The planner was instructed not to edit
  `.planning/ROADMAP.md`, so the placeholder is deliberately left for the phase-end flow, the same step
  that performs the merges. `02-10` task 3 *does* edit two passages in that file with scoped `Edit`
  replacements: criterion 6's vulture and bandit commands, and the baseline sentence. It also edits
  `.claude/conventions.md`'s bandit and vulture commands. Filling the `Plans` line is the only other change
  the roadmap needs for this phase, and it is not a plan's job.
- **Every integration run in this phase goes through `make test-integration`.** No plan runs
  `KITTI_INTEGRATION=1` pytest bare, because that opens kitty windows on the user's desktop and skips
  silently where no display exists. The runner needs `cage` on `PATH` and `XDG_RUNTIME_DIR` set.
- **No plan merges and no plan pushes.** Both merges — this phase's branch and Phase 1's deferred
  `gsd/phase-01-governance-freeze` — are Universal Phase Gate step 6, performed after every plan is
  committed, because `02-02` is what satisfies their shared precondition. A plan that merged would also
  have to contain evidence produced after its own commit, which is the impossibility Phase 1's `01-05`
  identified and removed.
- **`AGENTS.md`'s git-policy bullet lists seven disclosed limits of the pre-push guard.** If a legitimate
  post-merge push is rejected, that bullet — not this document — is the reference, and
  `KITTI_ALLOW_MASTER_PUSH=1` is the sanctioned route for the by-design rejections.

---

## Validation Sign-Off

- [ ] Every one of the 29 tasks has an automated verify command
- [ ] Sampling continuity: no 3 consecutive tasks without an automated verify
- [ ] Every requirement in the ROADMAP's Phase 2 list has a coverage row with an owning task
- [ ] Every `<automated>` gate has a `<fails_when>` stating what non-zero means and whether it is
      satisfiable before its own plan's commit exists (203 / 203)
- [ ] All 51 commit-dependent gates are ordered last within their task
- [ ] No whole-suite gate asserts an equality; every one is a floor against the measured 314 (unit) or 70
      (integration)
- [ ] Every integration gate goes through `make test-integration` and asserts pytest's own `N passed`
      and the absence of `failed|error` in captured output — never the wrapper's exit status alone
- [ ] No absence gate is asserted over a `PLAN.md` or over this document
- [ ] No `rg -c` count is compared to `'0'`
- [ ] Negative controls present (`_launch_argv` untouched; the library `ValueError` guards kept; the
      deliberate `KITTY_WINDOW_ID` re-injection kept; bash-and-zsh both exercised)
- [ ] Feedback latency < 60 s for every non-integration gate
- [ ] `nyquist_compliant: true` set in frontmatter
- [ ] `make doctor` exits 0 with all nine checks PASS or SKIP — **the phase's spine, and Phase 1's
      deferred-merge precondition**

**Approval:** pending



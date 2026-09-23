---
phase: "1"
slug: "governance-freeze"
# status lifecycle: draft (seeded by plan-phase) → validated (set by validate-phase §6)
status: draft
nyquist_compliant: false
wave_0_complete: false
created: "2026-09-23"
---

# Phase 1 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.
> Sourced from `01-RESEARCH.md` "Validation Architecture", which established that this
> phase's requirements are documentation, config, and git-hook assertions — **not**
> application behaviour. The right instrument per requirement is a direct command or a
> disposable-sandbox git experiment, not a unit test over `src/`.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 8.3.0 (`[tool.pytest.ini_options]` in `pyproject.toml`) — pre-existing, not introduced by this phase |
| **Config file** | `pyproject.toml` |
| **Quick run command** | `uv run pytest tests/unit -x` |
| **Full suite command** | `make test` |
| **Estimated runtime** | ~30 seconds (unit); full suite longer. **Note:** `tests/integration/` is skipped entirely unless `KITTI_INTEGRATION=1` (`tests/conftest.py:44-53`) — a verify command pointed there reports green while running nothing. |

**Caveat carried forward from research:** neither `make test` nor `make doctor` currently
covers governance content, so this phase's real gate is the per-requirement checks below
*plus* the Universal Phase Gate. A green `make test` alone does not evidence this phase.

---

## Sampling Rate

- **After every task verification:** the grep/shell check for that task's requirement (cheap,
  instant). **Corrected 2026-09-23:** this row previously read "After every task commit", which
  contradicts R0.10 / D-16 — a plan produces **one** commit, at its end, so there is no per-task
  commit to sample after. The sampling unit is the task's verification, which runs while the work is
  still unstaged or staged against `HEAD`. A `commit per task` grep does not match the old phrasing,
  which is why plan 01-05's absence gate uses the broadened alternation
  `commits? per task|per-task commit|task commit` over this file as well as ROADMAP and PROJECT.
- **After every plan wave:** `uv run pytest tests/unit -x` plus every governance check landed so far
- **Git-hook behaviour:** exercised in a **disposable sandbox repo** (pytest `tmp_path`),
  never against the real working tree — these tests mutate git state, including force-pushes
- **Before `/gsd-verify-work`:** full suite green, and every row below at ✅
- **Max feedback latency:** ~30 seconds for greps and unit tests; ~60 seconds for the sandbox git tests

---

## Per-Task Verification Map

Task IDs assigned by the planner on 2026-09-23, renumbered after the cross-AI review (`56f9df1`).
Waves reflect the plan set's dependency order, which honours the archive → move → banner →
instruction-file ordering constraint: the shell allow-list is widened and the hook mechanism proven
first (wave 1), the lifecycle hooks expand from it (wave 2), the tree is relocated and the
`sync`-after-rename question settled by a direct experiment (wave 3), and only then does the
instruction file make claims that are already true on disk (wave 4), with validation and planning-doc
alignment last (wave 5).

The review confirmed this chain is genuinely forced rather than merely chosen. The one ordering change
it forced is that the shell allow-list amendment moved from wave 4 into wave 1, because wave 1 creates
the files that amendment permits.

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 01-01-T1 | 01-01 | 1 | R0.4 | T-1-01 | The shell allow-list names `tools/hooks/` **before** the first hook file exists, in all four places the repo states it | grep | `rg -q 'tools/hooks' CLAUDE.md && rg -q 'tools/hooks' README.md && rg -q 'tools/hooks' .planning/PROJECT.md && test -f tools/setup.sh && ! rg -q 'only bash logic in this repo' tools/setup.sh` **(added 2026-09-23 after cross-AI review: the amendment moved from wave 4 to wave 1 so no tracked file is created against a rule that forbids it)** | ✅ | ⬜ pending |
| 01-01-T1 | 01-01 | 1 | R0.4 | T-1-01 | Non-fast-forward push is rejected, with a guard-specific `non-fast-forward` diagnostic; fast-forward and new-branch pushes are allowed | integration | `OUT="$(uv run pytest tests/unit/test_git_hooks.py -q 2>&1)" && printf '%s\n' "$OUT" \| rg -q '(^\|[^0-9])3 passed'` (disposable sandbox under `tmp_path`) | ❌ W0 | ⬜ pending |
| 01-01-T1 | 01-01 | 1 | R0.4 | T-1-01 | `core.hooksPath` resolves per worktree from one shared setting, with no per-worktree override possible | shell | `test "$(git config --get core.hooksPath)" = 'tools/hooks'` ; `! git config --get extensions.worktreeConfig` **(replaces `git config --get --worktree core.hooksPath` finds nothing — execution on git 2.55.0 showed that prints `tools/hooks` and exits 0 when worktree config is disabled, i.e. the old criterion asserted the opposite of the truth)** | ❌ W0 | ⬜ pending |
| 01-01-T2 | 01-01 | 1 | R0.4 | T-1-01 | Direct-to-master commits rejected with a `provenance` diagnostic; phase-branch AND milestone-branch merges allowed; escape hatch announced | integration | `OUT="$(uv run pytest tests/unit/test_git_hooks.py -q 2>&1)" && printf '%s\n' "$OUT" \| rg -q '(^\|[^0-9])7 passed'` | ❌ W0 | ⬜ pending |
| 01-01-T3 | 01-01 | 1 | R0.4 | T-1-01 | The three undefined edges are decided and tested (first push of `master`, `master` deletion, phase-branch deletion), and all seven limits are enumerated in the hook header | integration + grep | `OUT="$(uv run pytest tests/unit/test_git_hooks.py -q 2>&1)" && printf '%s\n' "$OUT" \| rg -q '(^\|[^0-9])10 passed'` ; `for L in 'no-verify' 'KITTI_ALLOW_MASTER_PUSH' 'squash' 'cherry-pick' 'first' 'delet'; do rg -qi -- "$L" tools/hooks/pre-push \|\| exit 1; done` | ❌ W0 | ⬜ pending |
| 01-02-T1 | 01-02 | 2 | R0.6 | T-1-04 | A new worktree is indexed with argv exactly `init -y` and a tagged success line; a codegraph failure **and** an absent codegraph each leave it intact and print an asserted warning | integration | `OUT="$(uv run pytest tests/unit/test_git_hooks.py -q 2>&1)" && printf '%s\n' "$OUT" \| rg -q '(^\|[^0-9])14 passed'` | ❌ W0 | ⬜ pending |
| 01-02-T2 | 01-02 | 2 | R0.6 | T-1-04 | Every commit syncs incrementally with argv exactly `sync -q`; a failing, absent **or hanging** codegraph never blocks a commit | integration | `OUT="$(uv run pytest tests/unit/test_git_hooks.py -q 2>&1)" && printf '%s\n' "$OUT" \| rg -q '(^\|[^0-9])18 passed'` ; `rg -q 'KITTI_CODEGRAPH_TIMEOUT_S' tools/hooks/post-commit` | ❌ W0 | ⬜ pending |
| 01-02-T3 | 01-02 | 2 | R0.6 | — | The lifecycle is demonstrated against the real binary, not only against shims | shell + human-check | `OUT="$(uv run pytest tests/unit/test_git_hooks.py -q 2>&1)" && printf '%s\n' "$OUT" \| rg -q '(^\|[^0-9])18 passed'` plus the recorded `[post-checkout]` / `[post-commit]` **success** transcripts and the two separately labelled timings in `01-02-SUMMARY.md` | ❌ W0 | ⬜ pending |
| 01-03-T1 | 01-03 | 3 | R0.2 | T-1-03 | The relocation preserves tracked history as a pure rename and leaves `specs/` byte-identical | shell | `test ! -e openspec` ; `test "$(find .planning/legacy/openspec/changes/archive -mindepth 1 -maxdepth 1 -type d -name '*-phase1-curated-bindings-revert-defaults' \| wc -l \| tr -d '[:space:]')" = '1'` ; `STATUS="$(git diff --cached --name-status HEAD -- openspec .planning/legacy/openspec)" && test -n "$STATUS" && ! printf '%s\n' "$STATUS" \| rg -qv '^R100'` **(replaces the earlier `openspec list` form — after D-02 the CLI has no root in this repo, so a filesystem assertion is the only honest instrument — and replaces the `ls \| rg -c \| rg -x '1'` count, which accepted a regular file and mis-handled zero matches)** | ✅ | ⬜ pending |
| 01-03-T2 | 01-03 | 3 | R0.2 | — | N/A | shell | `for f in .planning/legacy/openspec/README.md docs/requirements.md docs/propossal_roadmap.md; do test -f "$f" && rg -q 'FROZEN — history only' "$f" \|\| exit 1; done` ; `for f in …; do sed -n '1p' "$f" \| rg -q '^# ' && sed -n '3p' "$f" \| rg -q '^> ' \|\| exit 1; done` **(per file, so a failure names the file; replaces the `rg -l \| wc -l \| rg -x '3'` count)** | ✅ | ⬜ pending |
| 01-03-T3 | 01-03 | 3 | R0.6 | — | The `sync`-after-bulk-rename question is answered by a direct `codegraph sync -q` experiment, before the plan's single commit | shell + human-check | `codegraph status` (exit status only — the indexed-file count is a Manual-Only row below) plus the before/after captures and verdict in `01-03-SUMMARY.md` | ✅ | ⬜ pending |
| 01-04-T2 | 01-04 | 4 | R0.1 | — | N/A | grep | `rg -ni 'research.*experiment.*decide' AGENTS.md` **(`-i` added: the rule's bullet title begins with a capital and the pattern is lowercase)** | ❌ W0 | ⬜ pending |
| 01-04-T1 | 01-04 | 4 | R0.3 | — | N/A | grep | `rg -q '\.planning/legacy/openspec/' AGENTS.md && ! rg -n 'openspec' AGENTS.md \| rg -qv 'legacy'` ; `for T in 'openspec list' 'openspec archive' 'openspec validate' '\.claude/skills/openspec' 'opsx'; do if rg -q -- "$T" AGENTS.md; then exit 1; fi; done` — every remaining hit must be a `.planning/legacy/` history reference, never a process pointer **(replaces the `\| wc -l \| rg -x '0'` form, which execution showed prints `0` but exits 1 under `set -o pipefail` — failing in exactly its passing state — and which also passed when no reference existed at all; the token loop is the semantic half the lexical line check cannot cover)** | ❌ W0 | ⬜ pending |
| 01-04-T2 | 01-04 | 4 | R0.5 | — | N/A | grep | `rg -q 'codegraph_explore' AGENTS.md` | ❌ W0 | ⬜ pending |
| 01-04-T2 | 01-04 | 4 | R0.7 | — | N/A | grep | `rg -q 'cross_ai: true' AGENTS.md` | ❌ W0 | ⬜ pending |
| 01-04-T1 | 01-04 | 4 | R0.9 | — | N/A | grep | `rg -q 'agent-md-refactor' AGENTS.md && rg -q 'crafting-effective-readmes' AGENTS.md` | ❌ W0 | ⬜ pending |
| 01-04-T2 | 01-04 | 4 | R0.10 | — | N/A | grep | `test "$(rg -ci 'one commit per plan' AGENTS.md)" = '1'` ; `test "$(rg -l --glob '!.planning/**' -- 'one commit per plan' . )" = './AGENTS.md'` — present **and exactly once**, and nowhere else outside `.planning/`, which is what ROADMAP criterion 11 actually requires | ❌ W0 | ⬜ pending |
| 01-04-T3 | 01-04 | 4 | R0.8 | — | N/A | shell | `printf '@AGENTS.md\n' \| cmp -s - CLAUDE.md` ; `test "$(jq -r .claude_md_path .planning/config.json)" = './AGENTS.md'` **(`cmp` replaces `test "$(cat CLAUDE.md)" = '@AGENTS.md'`, which execution showed passes on a three-line file because command substitution strips all trailing newlines, leaving `max_lines: 1` ungated)** | ❌ W0 | ⬜ pending |
| 01-04-T2 | 01-04 | 4 | R0.4 | T-1-01 | The documented policy discloses **every** way past the guard, not two of seven | grep | `for L in 'no-verify' 'KITTI_ALLOW_MASTER_PUSH' 'squash' 'cherry-pick' 'first' 'delet'; do rg -qi -- "$L" AGENTS.md \|\| exit 1; done` | ❌ W0 | ⬜ pending |
| 01-04-T3 | 01-04 | 4 | R0.8 | — | No non-frozen tracked file still points a reader at `CLAUDE.md` for a rule | grep | `rg -q 'AGENTS\.md' .claude/conventions.md && ! rg -q 'CLAUDE' .claude/conventions.md` ; `rg -q 'AGENTS\.md' tools/setup.sh && ! rg -q 'CLAUDE\.md' tools/setup.sh` ; `rg -q 'AGENTS\.md' docs/agent-iteration.md && ! rg -q 'CLAUDE\.md' docs/agent-iteration.md` | ✅ | ⬜ pending |
| 01-05-T1 | 01-05 | 5 | R0.9 | — | N/A | manual + grep | `agent-md-refactor` skill invoked, every finding triaged Applied/Deferred/Rejected in `01-05-SUMMARY.md`; then **every** `AGENTS.md` content check from the 01-04 rows above re-run, including the exactly-one-line count and the forbidden-token loop | ❌ W0 | ⬜ pending |
| 01-05-T2 | 01-05 | 5 | R0.4, R0.10 | T-1-01 | The planning docs state the same policy as `AGENTS.md`, in every place each states one | shell | `rg -ni 'one commit per plan' .planning/ROADMAP.md && rg -ni 'one commit per plan' .planning/PROJECT.md` ; `for F in .planning/ROADMAP.md .planning/PROJECT.md .planning/phases/01-governance-freeze/01-VALIDATION.md; do test -f "$F" \|\| exit 1; if rg -qiE -- 'commits? per task\|per-task commit\|task commit' "$F"; then exit 1; fi; done` ; `test -f .planning/PROJECT.md && ! rg -q 'agents push a feature branch only' .planning/PROJECT.md` ; `test "$(rg -c '^### Phase [0-9]+(\.[0-9]+)?:' .planning/ROADMAP.md)" = '11'` | ✅ | ⬜ pending |
| 01-05-T3 | 01-05 | 5 | R0.1–R0.10 | T-1-01 | The whole gate is run and recorded, and the quality baseline did not regress | shell | `OUT="$(make test 2>&1)" && printf '%s\n' "$OUT" \| rg -q '(^\|[^0-9])18 passed'` ; the per-requirement checks above ; the Map Completeness Gate below ; the baseline-vs-post quality table in `01-05-SUMMARY.md` | ✅ | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

**Corrections to this map, made at planning time with the reason recorded:**

1. *(2026-09-23)* The R0.2 row's original `openspec list | grep -c …` command cannot run after plan
   01-03: the `git mv` leaves the CLI with no root in this repo, which is D-02's intended end state.
   Replaced with filesystem assertions over the archive directory. A command that errors because its
   own subject was deliberately removed is not evidence of anything.
2. *(2026-09-23)* The R0.1 row's `rg -n` is now `rg -ni`. The pattern `research.*experiment.*decide`
   is lowercase and `rg` is case-sensitive by default, so against a bullet titled with a capital
   letter the original command would have reported red on a correct file.
3. *(2026-09-23, after cross-AI review `56f9df1`)* **Every `rg … | wc -l | rg -x 'N'` and
   `rg -c … | rg -x 'N'` form in this map was replaced.** Execution established three independent
   defects in that family: the pipeline prints the expected count but exits **1** under
   `set -o pipefail` (this repo's own shell convention), so it fails in precisely its passing state;
   it passes **vacuously** on a missing file; and BSD/macOS `wc -l` pads its pipe output, so
   `rg -x '0'` false-fails on the Mac this project verifies on in Phases 9-10. The replacements are
   `test -f <f> && ! rg -q PAT <f>` for absence, a per-file loop for presence-across-several-files,
   and `test "$(… | wc -l | tr -d '[:space:]')" = 'N'` where a count is genuinely needed.
4. *(2026-09-23, after cross-AI review `56f9df1`)* **Every pytest row now asserts a literal
   passed-count** via `OUT="$(… -q 2>&1)" && printf '%s\n' "$OUT" | rg -q '(^|[^0-9])N passed'`.
   Pytest exits 0 when a selected test is skipped, so a bare `uv run pytest …` cannot detect the
   "0 skipped" condition the old rows claimed. A skipped case reports `N-1 passed, 1 skipped` and
   fails the new pattern. Pytest's own status is captured before the grep so a broken run cannot
   read as clean.
5. *(2026-09-23, after cross-AI review `56f9df1`)* **Plan 01-01's task structure changed** — the
   allow-list amendment moved into it from wave 4, and the negative controls folded into the tracer —
   so its rows were renumbered and one row was added. The test-case total also grew from 12 to **18**.

---

## Map Completeness Gate

The map itself must be provably resolved, not merely look resolved. Plan 01-05 task 3 runs all three:

```bash
V=.planning/phases/01-governance-freeze/01-VALIDATION.md
test -f "$V" && ! rg -q '⬜ pending' "$V"                       # nothing left unrun
test "$(rg -c '^\| 01-0' "$V")" = '23'                          # no row silently added or lost
test "$(rg -c '^\| 01-0.*(✅|❌|⚠️)' "$V")" = '23'               # every row carries a real verdict
```

**Why all three.** The pending-marker check alone would pass on a row whose Status cell was blanked
rather than resolved; the row-count check alone would pass on a map of twenty-three pending rows. The
third is the positive assertion that each row reached a verdict.

**What this replaces, and why that gate was worthless.** The previous plan gated on
`test "$(rg -nic 'TBD' "$V" | wc -l)" = '0'`. This file has **never** contained the string `TBD`, so
that gate passed before any work was done and could never fail — a gate that cannot fail is not a
gate. `TBD` is still checked, but only as a guard against a placeholder being *introduced*, and it is
labelled that way in the plan rather than presented as evidence of progress.

---

## Wave 0 Requirements

Research found **no existing test covers any git-hook behaviour**. Both gaps below are Wave 0
because R0.4 and R0.6 are the only two requirements in this phase whose truth is *behavioural*
rather than textual — and ROADMAP criterion 7 says the CodeGraph lifecycle must be
"demonstrated, not asserted", which a grep cannot do.

- [ ] `tests/unit/test_git_hooks.py` — new file. `subprocess` + pytest's **`tmp_path`**
      disposable-repo harness.

      **Location and fixture corrected 2026-09-23 from the pattern map, to remove a false-pass
      and a non-idiomatic fixture — both were defects in this file as first written:**
      - `tests/conftest.py:44-53` skips *every* item under `tests/integration/` unless
        `KITTI_INTEGRATION=1`. Placing these there would make the verify command **report green
        while running nothing** — precisely the silent false pass this project exists to remove.
        The gate's real meaning is "needs a live kitty"; these tests need only `git`, so they
        belong in the ungated tree and must run in plain `make test`.
      - `tempfile.TemporaryDirectory` has **0 occurrences** anywhere in `tests/`; the house
        fixture is pytest's `tmp_path`. RESEARCH.md's `TemporaryDirectory` was the researcher's
        own sandbox vocabulary, not this repo's.

      Cases, following the pattern the research used in its sandboxes. The planner expanded the
      original four into nine on 2026-09-23, then into **eighteen** after the cross-AI review
      (`56f9df1`) so every guard has a negative control and every previously undefined edge has a
      test (plans 01-01 tasks 1-3 and 01-02 tasks 1-2). The plan-level gates assert the literal
      passed-count — `3`, `7`, `10`, `14`, `18` at their respective points — because pytest exits 0
      on a skip and so cannot itself detect one:
  - [ ] `test_force_push_rejected` — force-push / amend-after-push rejection by `tools/hooks/pre-push`,
        asserting **both** a non-zero exit and the `[pre-push]` stderr tag **and** the rewrite guard's
        own word `non-fast-forward` (exit code alone cannot distinguish "hook rejected" from "hook
        crashed", and once a second guard exists it cannot say which one fired). The amend changes a
        tracked file first, so the test cannot pass for the wrong reason
  - [ ] `test_fast_forward_push_allowed` — the negative control; a hook that rejects everything
        would pass a rejection-only test
  - [ ] `test_new_branch_push_allowed` — the all-zero `remote_sha` case is skipped by design
  - [ ] `test_direct_commit_to_master_rejected` — a commit no `gsd/*` branch contains; stderr carries
        the master guard's own word `provenance`
  - [ ] `test_phase_branch_merge_to_master_allowed` — the negative control for the master guard
  - [ ] `test_milestone_branch_merge_to_master_allowed` — **added after review.** The negative control
        for the widened `gsd/*` glob: `.planning/config.json` configures
        `milestone_branch_template: "gsd/{milestone}-{slug}"` and `gsd/planning-bootstrap` already
        exists, neither of which matches the old `gsd/phase-*` pattern
  - [ ] `test_master_escape_hatch_allows_direct_push` — `KITTI_ALLOW_MASTER_PUSH=1` honoured and announced
  - [ ] `test_first_push_of_master_to_empty_remote_rejected` — **added after review.** The zero-SHA /
        master-guard interaction was undefined; the decision is to reject, because with no remote tip
        there is no range to enumerate and the guard must not pretend it checked
  - [ ] `test_master_deletion_rejected` and `test_phase_branch_deletion_allowed` — **added after
        review.** A deletion arrives with an all-zero `local_sha`; the policy is now explicit rather
        than an accident of `git merge-base` erroring
  - [ ] `test_post_checkout_indexes_new_worktree` plus `test_post_checkout_ignores_ordinary_branch_switch`
        — `post-checkout` fires on `git worktree add` with a zeroed prev-HEAD and indexes with argv
        **exactly** `init -y`, while an ordinary branch switch does not
  - [ ] `test_post_checkout_codegraph_failure_leaves_worktree_intact`,
        `test_post_checkout_codegraph_absent_leaves_worktree_intact` (**added after review** — the
        must-have required it and no test existed),
        `test_post_commit_codegraph_failure_does_not_block_commit` and
        `test_post_commit_codegraph_absent_does_not_block_commit` — a failing **and** an absent
        `codegraph` binary each leave the commit and the worktree intact **and print a warning the
        test asserts on**. R0.6 requires the warning, so an unasserted warning is an unmet requirement
  - [ ] `test_post_commit_syncs_index` — argv **exactly** `sync -q`, plus a tagged success line, which
        is what makes plan 01-02 task 3's live demonstration capturable at all
  - [ ] `test_post_commit_codegraph_hang_does_not_block_commit` — **added after review.** A sleeping
        shim with `KITTI_CODEGRAPH_TIMEOUT_S=1`; skips with an explicit message on a host without a
        `timeout` binary, because the mitigation is then unavailable rather than broken
- [ ] No pytest framework install needed — pytest 8.3.0 already configured.
- [ ] A ruff `per-file-ignores` entry for the subprocess rules the new module trips must be added to
      `pyproject.toml`'s existing `"tests/**/*.py"` list, each code with a one-line rationale.
      `.claude/conventions.md:20-23` forbids an inline suppression, and `pyproject.toml:79` does not
      currently include `S603`.

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| `agent-md-refactor` skill review of AGENTS.md | R0.9 | The skill is an interactive Claude Code skill, not a CLI; its findings require judgement to apply | Invoke the `agent-md-refactor` skill against `AGENTS.md`, record which findings were applied and which were consciously rejected, in the plan's SUMMARY |
| AGENTS.md reads as one coherent rule set | R0.8, R0.9 | Coherence of prose is not greppable | Read the finished file end to end; confirm no rule is stated twice and none contradicts another |
| `codegraph status` reports a **non-zero** indexed-file count | R0.6 | `codegraph status` prints aggregate counts and freshness in a human-readable form; no machine-readable count is confirmed to exist, so no `<automated>` command in this phase can read the number. Added 2026-09-23 after the review noted that two plans' `<fails_when>` clauses claimed a zero-file condition their paired command's exit status could not detect | Read the recorded `codegraph status` capture in `01-02-SUMMARY.md` and `01-03-SUMMARY.md` and confirm a non-zero file count. If `codegraph status --help` turns out to offer a `--json` or equivalent form, the executor promotes this to an automated gate and says so |
| Whether `codegraph`'s index still holds **stale old-path entries** after the bulk rename | R0.6 | `codegraph explore` surfaces textual references, and `README.md`, `docs/repro/*.md`, `config/kitty/*.conf` and several `src/` docstrings legitimately still contain the string `openspec/`. A hit is therefore not evidence of a stale index record, and no enumerate-indexed-paths capability is confirmed | Plan 01-03 task 3 records the question as **UNRESOLVED** unless the tool provides a way to enumerate indexed paths. Guessing is forbidden; the verdict rests on whether the **new** paths resolve plus the before/after count delta |
| Whether the merge precondition had to be narrowed, and whether that narrowing is acceptable | R0.4 | Plan 01-05 task 2 step 0 measures `make doctor` and branches. Whether narrowing R0.4/D-06's literal "doctor green" text to "captured, no regression, hard gate from Phase 2" is the right call is the user's decision, not a command's | Read the `make doctor` capture, its exit status and the verdict paragraph in `01-05-SUMMARY.md`, plus the stated alternative (defer Phase 1's merge until after Phase 2), and confirm or overturn |

---

## Known Threat Patterns (ASVS V4-adjacent)

| ID | Threat | STRIDE | Control | Severity | Disposition |
|----|--------|--------|---------|----------|-------------|
| T-1-01 | An agent rewrites published history (force-push / amend-after-push), destroying a teammate's or a prior phase's commits | Tampering | `tools/hooks/pre-push` rejects a push whose remote sha is not an ancestor of the local sha (`git merge-base --is-ancestor`) | medium | mitigate |
| T-1-02 | A buggy or malicious hook committed under `tools/hooks/` runs with the pusher's privileges — git hooks have no sandbox | Elevation of Privilege | Code review of `tools/hooks/*` changes, which this repo applies to every tracked file; each hook is kept to a thin dispatcher so the review surface stays small | low | accept |
| T-1-03 | The relocation loses or silently alters history that exists nowhere else | Tampering | `git mv` (tracked rename, one `git revert` undoes it) plus a tracked-file count and a specs-tree checksum asserted equal before and after (plan 01-03 task 1) | medium | mitigate |
| T-1-04 | A hanging or failing `codegraph` invocation blocks every commit in the repo | Denial of Service | Three failure shapes, three controls: **absence** → `command -v codegraph` guard; **eventual non-zero exit** → `\|\| log warning` suffix plus no non-zero exit path and a terminal `exit 0`; **never returns** → a `timeout`-wrapped call with an overridable `KITTI_CODEGRAPH_TIMEOUT_S` budget (default 60s) and a `command -v timeout` fallback. Each has a test: failing shim, minimal-PATH absence, sleeping shim (plan 01-02). **Corrected 2026-09-23 after review:** the previous row claimed a hang was mitigated when only absence and termination were handled. Residual risk, accepted and stated: on a host with no `timeout` binary (a default macOS install) the hang path is unbounded, the test skips with an explicit message, and the SUMMARY records it | low | mitigate |

Added 2026-09-23 by the planner: T-1-02 and T-1-04 come from `01-RESEARCH.md`'s Security Domain
section; T-1-03 is the relocation risk plan 01-03 owns. No other threat was minted — this phase has
no auth, session, or network surface, and installs no package, so no supply-chain (`T-1-SC`) row
applies (`01-RESEARCH.md` "Package Legitimacy Audit: Not applicable").

**Scope honesty, carried from research:** this is a **compliance guard for cooperating agents,
not a security boundary** — `--no-verify` bypasses it, as does any direct `git push` from
outside the repo's hook path. The plan and AGENTS.md must both say so; claiming enforcement
the mechanism cannot deliver would be the same class of untruth R2.8 exists to eliminate.

---

## Validation Sign-Off

- [ ] All tasks have an automated verify command or a Wave 0 dependency
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers both MISSING behavioural references (R0.4, R0.6)
- [ ] No watch-mode flags
- [ ] Feedback latency < 60s
- [ ] Negative controls present (fast-forward allowed; codegraph failure non-fatal)
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending

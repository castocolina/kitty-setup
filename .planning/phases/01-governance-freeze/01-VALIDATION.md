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

- **After every task commit:** the grep/shell check for that task's requirement (cheap, instant)
- **After every plan wave:** `uv run pytest tests/unit -x` plus every governance check landed so far
- **Git-hook behaviour:** exercised in a **disposable sandbox repo** (pytest `tmp_path`),
  never against the real working tree — these tests mutate git state, including force-pushes
- **Before `/gsd-verify-work`:** full suite green, and every row below at ✅
- **Max feedback latency:** ~30 seconds for greps and unit tests; ~60 seconds for the sandbox git tests

---

## Per-Task Verification Map

Task IDs assigned by the planner on 2026-09-23. Waves reflect the plan set's dependency order, which
honours the archive → move → banner → instruction-file ordering constraint: the hook mechanism is
proven first (wave 1), expanded (wave 2), the tree is relocated through the live commit hook
(wave 3), and only then does the instruction file make claims that are already true on disk
(wave 4), with validation and planning-doc alignment last (wave 5).

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 01-01-T1 | 01-01 | 1 | R0.4 | T-1-01 | Non-fast-forward push is rejected | integration | `uv run pytest tests/unit/test_git_hooks.py -k force_push -x` (disposable sandbox under `tmp_path`) | ❌ W0 | ⬜ pending |
| 01-01-T1 | 01-01 | 1 | R0.4 | T-1-01 | `core.hooksPath` resolves per worktree from one shared setting | shell | `test "$(git config --get core.hooksPath)" = 'tools/hooks'` | ❌ W0 | ⬜ pending |
| 01-01-T2 | 01-01 | 1 | R0.4 | T-1-01 | The guard discriminates — fast-forward and new-ref pushes are allowed | integration | `uv run pytest tests/unit/test_git_hooks.py -k 'fast_forward or new_branch' -x` | ❌ W0 | ⬜ pending |
| 01-01-T3 | 01-01 | 1 | R0.4 | T-1-01 | Direct-to-master commits rejected; phase-branch merges allowed; escape hatch announced | integration | `uv run pytest tests/unit/test_git_hooks.py -x` (6 passed, 0 skipped) | ❌ W0 | ⬜ pending |
| 01-02-T1 | 01-02 | 2 | R0.6 | T-1-04 | A new worktree is indexed; a codegraph failure leaves it intact | integration | `uv run pytest tests/unit/test_git_hooks.py -k post_checkout -x` | ❌ W0 | ⬜ pending |
| 01-02-T2 | 01-02 | 2 | R0.6 | T-1-04 | Every commit syncs incrementally; a failing or absent codegraph never blocks a commit | integration | `uv run pytest tests/unit/test_git_hooks.py -k post_commit -x` | ❌ W0 | ⬜ pending |
| 01-02-T3 | 01-02 | 2 | R0.6 | — | The lifecycle is demonstrated against the real binary, not only against shims | shell + human-check | `uv run pytest tests/unit/test_git_hooks.py -x` (12 passed, 0 skipped) plus the recorded `[post-checkout]` / `[post-commit]` transcripts in `01-02-SUMMARY.md` | ❌ W0 | ⬜ pending |
| 01-03-T1 | 01-03 | 3 | R0.2 | T-1-03 | The relocation preserves tracked history and leaves `specs/` byte-identical | shell | `test ! -e openspec` ; `ls .planning/legacy/openspec/changes/archive \| rg -c -- '-phase1-curated-bindings-revert-defaults$' \| rg -x '1'` **(replaces the earlier `openspec list` form — after D-02 the CLI has no root in this repo, so a filesystem assertion is the only honest instrument)** | ✅ | ⬜ pending |
| 01-03-T2 | 01-03 | 3 | R0.2 | — | N/A | shell | `rg -l 'FROZEN — history only' .planning/legacy/openspec/README.md docs/requirements.md docs/propossal_roadmap.md \| wc -l \| rg -x '3'` | ✅ | ⬜ pending |
| 01-04-T2 | 01-04 | 4 | R0.1 | — | N/A | grep | `rg -ni 'research.*experiment.*decide' AGENTS.md` **(`-i` added: the rule's bullet title begins with a capital and the pattern is lowercase)** | ❌ W0 | ⬜ pending |
| 01-04-T1 | 01-04 | 4 | R0.3 | — | N/A | grep | `rg -n 'openspec' AGENTS.md \| rg -v 'legacy' \| wc -l \| rg -x '0'` — every remaining hit must be a `.planning/legacy/` history reference, never a process pointer | ❌ W0 | ⬜ pending |
| 01-04-T2 | 01-04 | 4 | R0.5 | — | N/A | grep | `rg -q 'codegraph_explore' AGENTS.md` | ❌ W0 | ⬜ pending |
| 01-04-T2 | 01-04 | 4 | R0.7 | — | N/A | grep | `rg -q 'cross_ai: true' AGENTS.md` | ❌ W0 | ⬜ pending |
| 01-04-T1 | 01-04 | 4 | R0.9 | — | N/A | grep | `rg -q 'agent-md-refactor' AGENTS.md && rg -q 'crafting-effective-readmes' AGENTS.md` | ❌ W0 | ⬜ pending |
| 01-04-T2 | 01-04 | 4 | R0.10 | — | N/A | grep | `rg -ni 'one commit per plan' AGENTS.md` | ❌ W0 | ⬜ pending |
| 01-04-T3 | 01-04 | 4 | R0.8 | — | N/A | shell | `test "$(cat CLAUDE.md)" = '@AGENTS.md'` ; `test "$(jq -r .claude_md_path .planning/config.json)" = './AGENTS.md'` | ❌ W0 | ⬜ pending |
| 01-04-T2 | 01-04 | 4 | R0.4 | T-1-01 | The documented policy discloses both ways past the guard | grep | `rg -q 'no-verify' AGENTS.md && rg -q 'KITTI_ALLOW_MASTER_PUSH' AGENTS.md` | ❌ W0 | ⬜ pending |
| 01-05-T1 | 01-05 | 5 | R0.9 | — | N/A | manual + grep | `agent-md-refactor` skill invoked, every finding triaged Applied/Deferred/Rejected in `01-05-SUMMARY.md`; then the six content greps above re-run | ❌ W0 | ⬜ pending |
| 01-05-T2 | 01-05 | 5 | R0.4, R0.10 | T-1-01 | The planning docs state the same policy as `AGENTS.md` | shell | `rg -ni 'one commit per plan' .planning/ROADMAP.md .planning/PROJECT.md` ; `test "$(rg -nic 'commit per task' .planning/ROADMAP.md .planning/PROJECT.md \| wc -l)" = '0'` | ✅ | ⬜ pending |
| 01-05-T3 | 01-05 | 5 | R0.1–R0.10 | T-1-01 | The whole gate is run and recorded, and the quality baseline did not regress | shell | `make test` ; the per-requirement checks above ; the baseline-vs-post quality table in `01-05-SUMMARY.md` | ✅ | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

**Two corrections to this map, made at planning time with the reason recorded (2026-09-23):**

1. The R0.2 row's original `openspec list | grep -c …` command cannot run after plan 01-03: the
   `git mv` leaves the CLI with no root in this repo, which is D-02's intended end state. Replaced
   with filesystem assertions over the archive directory. A command that errors because its own
   subject was deliberately removed is not evidence of anything.
2. The R0.1 row's `rg -n` is now `rg -ni`. The pattern `research.*experiment.*decide` is lowercase
   and `rg` is case-sensitive by default, so against a bullet titled with a capital letter the
   original command would have reported red on a correct file.

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
      original four into nine on 2026-09-23 so every guard has a negative control (plans 01-01
      tasks 1-3 and 01-02 tasks 1-2):
  - [ ] `test_force_push_rejected` — force-push / amend-after-push rejection by `tools/hooks/pre-push`,
        asserting **both** a non-zero exit and the `[pre-push]` stderr tag (exit code alone cannot
        distinguish "hook rejected" from "hook crashed")
  - [ ] `test_fast_forward_push_allowed` — the negative control; a hook that rejects everything
        would pass a rejection-only test
  - [ ] `test_new_branch_push_allowed` — the all-zero `remote_sha` case is skipped by design
  - [ ] `test_direct_commit_to_master_rejected` — a commit no `gsd/phase-*` branch contains
  - [ ] `test_phase_branch_merge_to_master_allowed` — the negative control for the master guard
  - [ ] `test_master_escape_hatch_allows_direct_push` — `KITTI_ALLOW_MASTER_PUSH=1` honoured and announced
  - [ ] `test_post_checkout_indexes_new_worktree` plus `test_post_checkout_ignores_ordinary_branch_switch`
        — `post-checkout` fires on `git worktree add` with a zeroed prev-HEAD and indexes, while an
        ordinary branch switch does not
  - [ ] `test_post_checkout_codegraph_failure_leaves_worktree_intact`,
        `test_post_commit_codegraph_failure_does_not_block_commit` and
        `test_post_commit_codegraph_absent_does_not_block_commit` — a failing **and** an absent
        `codegraph` binary each warn but leave the commit and the worktree intact
- [ ] No pytest framework install needed — pytest 8.3.0 already configured.

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| `agent-md-refactor` skill review of AGENTS.md | R0.9 | The skill is an interactive Claude Code skill, not a CLI; its findings require judgement to apply | Invoke the `agent-md-refactor` skill against `AGENTS.md`, record which findings were applied and which were consciously rejected, in the plan's SUMMARY |
| AGENTS.md reads as one coherent rule set | R0.8, R0.9 | Coherence of prose is not greppable | Read the finished file end to end; confirm no rule is stated twice and none contradicts another |

---

## Known Threat Patterns (ASVS V4-adjacent)

| ID | Threat | STRIDE | Control | Severity | Disposition |
|----|--------|--------|---------|----------|-------------|
| T-1-01 | An agent rewrites published history (force-push / amend-after-push), destroying a teammate's or a prior phase's commits | Tampering | `tools/hooks/pre-push` rejects a push whose remote sha is not an ancestor of the local sha (`git merge-base --is-ancestor`) | medium | mitigate |
| T-1-02 | A buggy or malicious hook committed under `tools/hooks/` runs with the pusher's privileges — git hooks have no sandbox | Elevation of Privilege | Code review of `tools/hooks/*` changes, which this repo applies to every tracked file; each hook is kept to a thin dispatcher so the review surface stays small | low | accept |
| T-1-03 | The relocation loses or silently alters history that exists nowhere else | Tampering | `git mv` (tracked rename, one `git revert` undoes it) plus a tracked-file count and a specs-tree checksum asserted equal before and after (plan 01-03 task 1) | medium | mitigate |
| T-1-04 | A hanging or failing `codegraph` invocation blocks every commit in the repo | Denial of Service | `command -v` guard, `\|\| log warning` suffix, no `exit 1` path, terminal `exit 0` — each asserted by a verify gate and by the failing-shim and absent-binary tests (plan 01-02) | low | mitigate |

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

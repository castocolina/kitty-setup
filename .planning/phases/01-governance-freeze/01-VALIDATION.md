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

Task IDs are assigned by the planner; the Requirement → check mapping is fixed here.

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| TBD | TBD | 1 | R0.2 | — | N/A | shell | `openspec list \| grep -c phase1-curated-bindings-revert-defaults` (expect 0) ; `test -d .planning/legacy/openspec && ! test -d openspec` | ✅ | ⬜ pending |
| TBD | TBD | 1 | R0.2 | — | N/A | shell | `rg -l 'FROZEN — history only' .planning/legacy/openspec/README.md docs/requirements.md docs/propossal_roadmap.md` (3 hits) | ✅ | ⬜ pending |
| TBD | TBD | 1 | R0.1 | — | N/A | grep | `rg -n 'research.*experiment.*decide' AGENTS.md` | ❌ W0 | ⬜ pending |
| TBD | TBD | 1 | R0.3 | — | N/A | grep | `rg -n 'openspec' AGENTS.md` — every hit must be a history/banner mention, not a process pointer | ❌ W0 | ⬜ pending |
| TBD | TBD | 1 | R0.5 | — | N/A | grep | `rg -n 'codegraph_explore' AGENTS.md` | ❌ W0 | ⬜ pending |
| TBD | TBD | 1 | R0.7 | — | N/A | grep | `rg -n 'cross_ai: true' AGENTS.md` | ❌ W0 | ⬜ pending |
| TBD | TBD | 1 | R0.9 | — | N/A | grep | `rg -n 'agent-md-refactor\|crafting-effective-readmes' AGENTS.md` | ❌ W0 | ⬜ pending |
| TBD | TBD | 1 | R0.10 | — | N/A | grep | `rg -ni 'one commit per plan' AGENTS.md` | ❌ W0 | ⬜ pending |
| TBD | TBD | 1 | R0.8 | — | N/A | shell | `test "$(cat CLAUDE.md)" = '@AGENTS.md'` ; `jq -r .claude_md_path .planning/config.json` = `./AGENTS.md` | ❌ W0 | ⬜ pending |
| TBD | TBD | 2 | R0.4 | T-1-01 | Non-fast-forward push is rejected | integration | `uv run pytest tests/unit/test_git_hooks.py -k force_push` (disposable sandbox) | ❌ W0 | ⬜ pending |
| TBD | TBD | 2 | R0.4 | T-1-01 | `core.hooksPath` resolves per worktree | shell | `git config --get core.hooksPath` = `tools/hooks` | ❌ W0 | ⬜ pending |
| TBD | TBD | 2 | R0.6 | — | CodeGraph failure never aborts the git operation | integration | `uv run pytest tests/unit/test_git_hooks.py -k codegraph` (worktree-add + post-commit, sandbox) | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

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

      Cases, following the pattern the research used in its sandboxes:
  - [ ] force-push / amend-after-push rejection by `tools/hooks/pre-push`, asserting non-zero exit
  - [ ] fast-forward push is **allowed** (the negative control — a hook that rejects everything
        would pass a rejection-only test)
  - [ ] `post-checkout` fires on `git worktree add` with a zeroed prev-HEAD, and indexes
  - [ ] a failing/absent `codegraph` binary warns but leaves the commit and the worktree intact
- [ ] No pytest framework install needed — pytest 8.3.0 already configured.

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| `agent-md-refactor` skill review of AGENTS.md | R0.9 | The skill is an interactive Claude Code skill, not a CLI; its findings require judgement to apply | Invoke the `agent-md-refactor` skill against `AGENTS.md`, record which findings were applied and which were consciously rejected, in the plan's SUMMARY |
| AGENTS.md reads as one coherent rule set | R0.8, R0.9 | Coherence of prose is not greppable | Read the finished file end to end; confirm no rule is stated twice and none contradicts another |

---

## Known Threat Patterns (ASVS V4-adjacent)

| ID | Threat | Control | Severity |
|----|--------|---------|----------|
| T-1-01 | An agent rewrites published history (force-push / amend-after-push), destroying a teammate's or a prior phase's commits | `tools/hooks/pre-push` rejects a push whose remote sha is not an ancestor of the local sha (`git merge-base --is-ancestor`) | medium |

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

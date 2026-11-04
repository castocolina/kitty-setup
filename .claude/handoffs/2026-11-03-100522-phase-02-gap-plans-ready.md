# Handoff: Phase 02 gap-closure plans 02-12..02-15 — planned, cross-AI reviewed twice, NOT executed

## Session Metadata
- Created: 2026-11-03 10:05:22
- Project: /var/home/bazzite/git/personal/kitty-setup
- Branch: gsd/phase-02-defect-remediation
- Baseline commit: 0060d77 (see `git log` for the final commit of this session)
- Session duration: one long GSD session (2026-09-22 → 2026-11-03, many compactions)

### Recent Commits (for context)
  - 0060d77 docs(02): gap plans 02-13..02-15, convergence round 2
  - 6e6b863 docs(02): gap-closure plans 02-12..02-15, cross-AI reviewed and revised
  - 3d249dd docs: point Phase 6 and Phase 9 at their pending todos
  - 1cbcaaa docs(02): phase-end verification, deep code review and security audit
  - d4a3a8c Merge 02-10 (R0.11): src/ clean under all five tools; phase-end verification map 29/29

## Handoff Chain

- **Continues from**: None (fresh start)
- **Supersedes**: None

## Current State Summary

Phase 2 (defect remediation) executed plans 02-01..02-11 and passed verification, security audit
and deep code review at `1cbcaaa`. The deep review (02-REVIEW.md: 6 MEDIUM, 8 LOW) and the security
audit's advisories (02-SECURITY.md A-1..A-6) became four gap-closure plans, **02-12, 02-13, 02-14,
02-15** (all `type: tdd`, `gap_closure: true`, `cross_ai: true`, waves 12→13→14→15). They went
through two rounds of cross-AI plan review (round 1: all REVISE; round 2: 02-13/14/15 REVISE, all
findings applied). 02-12's round-2 review timed out once, crashed once (router: `Combo has no
executable targets`), and then finished on my-referee-one: **REVISE, 2 HIGH + 2 MEDIUM, NOT yet
applied** (`02-GAP-REVIEWS.md`, last section). **Nothing in the gap plans has been executed.** The user's
directive for this session was: "stop after fix the plan and execute session-hands-off and commit
all and push" — so the session stopped at planning. `master` is not merged: Phase 1 and Phase 2
merge only after the gap plans land and `make doctor` + `make test` are green.

## Codebase Understanding

### Architecture Overview

Python CLI `my-kitty` (`src/kitty_setup/cli.py`), kitty config payload installer
(`config_updater.py`, `installer.py`), rc-file PATH/completion block (`path_integration.py`),
`doctor.py` health checks, scenes (`src/kitty_setup/scenes/launcher.py`), and a headless integration harness
(`src/kitty_setup/harness/integration_runner.py`, run only via `make test-integration`).

### Critical Files

| File | Purpose | Relevance |
|------|---------|-----------|
| .planning/phases/02-defect-remediation/02-12-PLAN.md | kitty.conf lifecycle (WR-01/04/06, IN-04/07/08, A-2) + unit hermeticity guard | first to execute |
| .planning/phases/02-defect-remediation/02-13-PLAN.md | pane-0 send-text injection + cwd semantics (WR-02/03) | wave 13 |
| .planning/phases/02-defect-remediation/02-14-PLAN.md | zsh fpath completion, no block move, byte-exact rc I/O (WR-05/06, IN-01, A-4) | wave 14 |
| .planning/phases/02-defect-remediation/02-15-PLAN.md | runner selectors, rollback asides, bandit scope, https redirects, integration HOME sandbox (IN-02/03/05/06, A-1/A-3) | wave 15 |
| .planning/phases/02-defect-remediation/02-GAP-REVIEWS.md | every cross-AI finding + per-finding disposition, rounds 1-2 | read before round 3 |
| .planning/phases/02-defect-remediation/02-VERIFICATION.md | content-fingerprinted; now STALE (covers ROADMAP/REQUIREMENTS/src) | re-fingerprint at phase close |
| .planning/config.json | GSD config | changed this session, see Decisions |

### Key Patterns Discovered

- Hypothesis evidence lives in gitignored `tmp/h<NN>-<slug>/`; numbers are allocated in order.
  Taken: h38-h41 (02-12..02-14), h42 (tab-bg todo), h43-h47 (02-15). Next free: **h48**.
- Threat IDs: 02-15 T-2-66..73, 02-14 T-2-74..76, 02-13 T-2-77..78. **Collision:** 02-15 also
  claims T-2-78 (HOME isolation); round 3 renumbers 02-15's to **T-2-79** (then next free: T-2-80).
- 02-VALIDATION.md corrections: last is 20; 02-13 takes the next free, then 02-14 (both gate on
  the plan tag, not the number).
- Gate-defect catalogue (avoid in every `<verify>`): self-quoting absence greps; `git log --grep`;
  negative gates inverted by an erroring command (`test -z "$(cmd)"` — use `X="$(cmd)" && test -z "$X"`);
  unguarded missing files; `git diff --cached` after the commit; `rg -c` prints nothing on zero;
  pipeline status is the last command's; wrapper status ≠ pytest status; "no match" gates must be
  shown to match the bad case; no cumulative counts; topology = `GREEN^ == RED` and exactly 2
  commits in `RED^..GREEN`.

## Work Completed

### Tasks Finished

- [x] Triage of todos (tab-wide bg chord → Phase 6 discuss; headless latest-kitty install → Phase 9 discuss); ROADMAP pointers (3d249dd)
- [x] 02-15 planned (the earlier planner died on an API 403 after 02-12..02-14)
- [x] A-6 fixed directly (split fused T-2-09/T-2-10 row in 02-03-PLAN.md)
- [x] Cross-AI plan review round 1 (4 plans) + revisions; round 2 + revisions (6e6b863, 0060d77)
- [x] `.planning/config.json` updated (see Decisions); `.gitignore` covers the local GSD install
- [x] Hypothesis-dir clash fixed: tab-bg research renamed `tmp/h38-…` → `tmp/h42-tab-bg-chord-research`

### Files Modified

| File | Changes | Rationale |
|------|---------|-----------|
| .planning/phases/02-defect-remediation/02-1[2-5]-PLAN.md | new + revised twice | gap closure |
| .planning/phases/02-defect-remediation/02-GAP-REVIEWS.md | new | review audit trail |
| .planning/phases/02-defect-remediation/02-03-PLAN.md | row split | A-6 |
| .planning/config.json | cross-AI exec off, executor→haiku, reviewers | user directive |
| .gitignore | GSD install block | user directive |
| .planning/ROADMAP.md | Phase 6/9 todo pointers | todo triage |
| .planning/todos/pending/2026-10-15-tab-wide-background-toggle-chord.md | h38→h42 | numbering clash |

### Decisions Made

| Decision | Options Considered | Rationale |
|----------|-------------------|-----------|
| `workflow.cross_ai_execution: false`, `model_overrides.gsd-executor: haiku` | keep opencode my-coding runner | user directive 2026-11-03; set with project-local `gsd-tools config-set` |
| Plans keep `cross_ai: true` | strip the flag | user: required to activate cross-AI plan-review convergence |
| Reviewers = tools-installer's `reviewer_instances` (opencode-referee-one/three), default `opencode-referee-one`; `review.models` removed | keep `opencode`→`router-env/my-plan-review` | user directive; my-plan-review is "Model unavailable" in opencode |
| No plan runs `make install`; ONE deliberate real install at phase close | per-plan live install | reviewer BLOCKER; safety rule (real rc/kitty.conf sha256 before/after, byte-identical outside the sentinel block) |
| IN-03: remove rollback asides on full uninstall, keep and name them otherwise | list-as-kept only | four places promise full removal (02-15) |
| IN-05: drop B310, keep B404/B603 global, fence B604/B607 per call site in a unit test | bandit baseline file | bandit ignores a TOML `baseline` key (02-15) |

## Pending Work

### Immediate Next Steps

1. Apply 02-12's round-2 findings (last section of `02-GAP-REVIEWS.md`) with a `gsd-planner`
   revision exactly like rounds 1-2 (verify each finding, apply, append a disposition):
   HIGH Step 0 needs a green headless `make test-integration` prototype recorded in
   `tmp/h38-conf-lifecycle/` before shipping-file edits; HIGH the hermeticity guard must resolve
   `Popen(cwd=…)` and `dir_fd` paths and fail closed; MEDIUM `make test` status + output kept in
   the SUMMARY; MEDIUM renumber 02-15's T-2-78 → T-2-79.
2. **Round-3 cross-plan fix before ANY execution — integration HOME sandbox ordering.** 02-15 adds
   `tests/integration/conftest.py` (planned, not yet created; autouse `sandbox_integration_home`), but 02-13 and 02-14 run
   `make test-integration` earlier and would keep writing the real `~/.bash_history`. Move that
   fixture into 02-12 (first wave), or make 02-13/14 depend on it. Also: 02-13's planned private
   `_sandbox_home` fixture likely trips pyright strict `reportUnusedFunction` (measured by 02-15's
   reviser on a scratch copy) — rename without the underscore.
3. Run cross-AI review round 3 until no BLOCKER/HIGH remains. Lane rule (from the user's other
   projects): probe first (`echo 'Reply with exactly: OK' | timeout 90 opencode run --model
   router-env/my-referee-one -`); if it fails use my-referee-three for that run; never re-send a
   review that died mid-run to the same lane; on 429/quota retry every 10 min (router-env fails over
   internally). Run with `timeout 3600` via `run_in_background` (never a `pgrep -f` waiter — it
   matches its own command line and never exits).
4. Execute 02-12 → 02-15 with `/gsd-execute-phase 2` (native `gsd-executor` at haiku). After each
   `Agent(isolation="worktree")` dispatch: check `git config --get core.hooksPath` is relative
   (`make hooks` if not) and copy `tmp/h*` from the worktree to the primary before removing it.
5. Phase close: one deliberate `make install` (sha256 bracket), `make doctor` + `make test` +
   `make test-integration` green, re-fingerprint 02-VERIFICATION (`gsd-tools query verification
   fingerprint`), `phase complete 2`, merge `gsd/phase-01-governance-freeze` then
   `gsd/phase-02-defect-remediation` into master (no squash, no force), push master + both branches.
6. Then Phases 3-6 (`/gsd-autonomous --to 6`). Phase 6 needs `/gsd-discuss-phase 6` (update) for
   the tab-wide background todo first.

### Blockers/Open Questions

- [ ] `make doctor` is RED right now on the installed tool (exit 2, `FAIL completion:`), most likely
      WR-05 (something appended to `~/.zshrc` after our block). Fixed by 02-14 + the phase-close install.
- [x] `~/.bash_history`: with the user's consent the 143 test-typed lines (`printf '2;…'`,
      `cd …/my dir; touch …/PWNED`) were removed (1010 → 867 lines, nothing else changed; backup
      deleted after verification). Integration runs keep polluting it until the HOME sandbox lands.
- [ ] Pending user answer: apply `review.timeouts.opencode: 2400` and `review.effort.opencode:
      "inherit"` (tools-installer values; GSD's default opencode timeout floor is 660 s, and with
      opencode 2.x `"high"` appends `#high` to the model id). Not applied.
- [ ] Will haiku cope with 540-900-line TDD plans? Unknown; GSD `dynamic_routing` is not enabled here.

### Deferred Items

- A-5 / T-2-19 (parse check blind to a missing `include`, no check on unchanged-conf reinstall) → Phase 5.
- Phase 6 blocker: `my-kitty window background none` fails (`set-colors background=NONE` exits 1 on kitty 0.49).
- Leftovers: 36-byte `install.log` in the uv tool venv; doctor docstrings still say `PASS|FAIL` and
  `my-kitty-setup doctor`; ROADMAP/STATE progress counters need updating at phase close.

## Context for Resuming Agent

### Important Context

- **Safety rules (non-negotiable, from the user):** never spawn kitty windows; never bare `kitten @`
  or bare `KITTI_INTEGRATION=1 pytest` — integration only via `make test-integration
  PYTEST_ARGS='…'`; never write the real `~/.bashrc`, `~/.zshrc`, `~/.config/kitty`, `~/.local/*`
  except the deliberate phase-close install; never `uv tool uninstall`; never force-push or amend
  pushed commits; stage with explicit pathspecs; leave no orphan processes, `cage` processes or
  `$XDG_RUNTIME_DIR/kitti-*` dirs; English everywhere; don't kill other sessions' processes.
- GSD is installed **per project only** (`.claude/gsd-core`, now gitignored). Never run a global
  GSD install/update; use `node .claude/gsd-core/bin/gsd-tools.cjs …`.
- `type: tdd` plans make exactly two commits, RED then GREEN, `(02-NN)`-scoped. Orchestrator
  commits use `docs(02)`.
- AGENTS.md git policy: Phase 1 merges after Phase 2's R1.1 makes `make doctor` green.

### Assumptions Made

- GSD `/gsd-review` has no lane fallback: it runs every `default_reviewers` entry and treats an
  instance as available if its CLI binary exists (`.claude/gsd-core/references/reviewer-instances.md`).
- The user's stated reason for keeping `cross_ai: true` (it activates plan-review convergence) was
  not verified in GSD's source.

### Potential Gotchas

- `Agent(isolation="worktree")` forks from `origin/master` (`23aeaa1`), not the phase branch — the
  executor must `git reset --hard gsd/phase-02-defect-remediation` — and it rewrites
  `core.hooksPath` to an absolute path (8/8 times), silently disabling hooks.
- `git worktree remove` deletes the worktree's gitignored `tmp/` evidence.
- Editing any file in 02-VERIFICATION's `covered_files` (ROADMAP, REQUIREMENTS, plans, `src/*`)
  makes it stale, so `phase complete 2` fails until re-fingerprinted.
- opencode reviews of these long plans take 30-60 min; 2400 s timed out once.

## Environment State

### Tools/Services Used

- `opencode run --model router-env/my-referee-one` (read-only plan reviews); `router-env/my-referee-two` is unavailable, `my-referee-three` answers.
- `.claude/gsd-core/bin/gsd-tools.cjs` (project-local GSD 1.19.0).

### Active Processes

- None left by this session (reviews finished; no kitty, no cage).

### Environment Variables

- `XDG_RUNTIME_DIR`, `HOME`, `HISTFILE`, `KITTY_WINDOW_ID`, `KITTI_INTEGRATION` (names only).

## Related Resources

- AGENTS.md, .claude/conventions.md, docs/agent-iteration.md
- .planning/ROADMAP.md, .planning/REQUIREMENTS.md, .planning/STATE.md
- .planning/phases/02-defect-remediation/02-REVIEW.md, 02-SECURITY.md, 02-GAP-REVIEWS.md

---

**Security Reminder**: Before finalizing, run `validate_handoff.py` to check for accidental secret exposure.

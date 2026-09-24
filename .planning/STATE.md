---
gsd_state_version: "1.0"
milestone: v1.0
current_phase: 2
current_phase_name: Defect Remediation
status: planning
stopped_at: Phase 1 complete (5/5 plans); its merge to `master` is deferred until Phase 2's R1.1 turns `make doctor` green
last_updated: "2026-09-23T00:00:00.000Z"
last_activity: 2026-09-23
last_activity_desc: Phase 1 (Governance & Freeze) complete — 5 plans committed, 23/23 verification-map rows green, `make test` 311 passed / 70 skipped
state_head: 508087c73f1dc57825d04f557acf1c26ef748e09
progress:
  total_phases: 10
  completed_phases: 1
  total_plans: 5
  completed_plans: 5
---

# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-09-22)

**Core value:** One trustworthy kitty setup that feels native on both Linux and macOS, where `my-kitty doctor` is green and everything `my-kitty keys` prints is exactly what kitty actually does in a live session.
**Current focus:** Phase 2 — Defect Remediation

## Current Position

Phase: 2 of 10 (Defect Remediation)
Plan: 6 of 11 in current phase executed and merged into `gsd/phase-02-defect-remediation` (02-11, 02-01, 02-02, 02-03, 02-04, 02-05); 02-06..02-10 are under plan revision
Status: Executing
Last activity: 2026-09-24 — 02-05 merged (`a60afed`): parse check reports its command and stderr; payload rollback never loses the previous payload. From the primary checkout: `make doctor` exit 0 (8 PASS, 1 SKIP), `make test` 423 passed, `make test-integration` 77 passed

Progress: [█░░░░░░░░░] 10%

## Performance Metrics

**Velocity:**

- Total plans completed: 0
- Average duration: —
- Total execution time: 0.0 hours

**By Phase:**

| Phase | Plans | Total | Avg/Plan |
|-------|-------|-------|----------|
| - | - | - | - |

**Recent Trend:**

- Last 5 plans: —
- Trend: —

*Updated after each plan completion*

## Accumulated Context

### Decisions

Decisions are logged in PROJECT.md Key Decisions table.
Recent decisions affecting current work:

- [Phase 0]: Every phase runs research → experiment (real kitty session, evidence in `tmp/h<NN>-<slug>/`) → decide → implement → verify with `make doctor` + `make test` output.
- [Phase 1, D-06/D-16 — supersedes the Phase 0 entry]: Git policy — each phase runs in its own worktree on `gsd/phase-{phase}-{slug}`; work lands at the granularity `AGENTS.md` states (the rule lives there and nowhere else); at phase end, once `make doctor` and `make test` are green, merge into `master` and push. Never force-push or amend pushed commits.
- [Phase 0]: Execution is autonomous — no clarifying questions during execute; ambiguity is resolved in discuss-phase.
- [Phase 0]: `.planning/` is the single source of truth; `openspec/` is frozen as history-only (delivered by Phase 1).
- [Phase 0]: The R2.8 oracle test (`my-kitty keys --json` == kitty's live effective keymap, 1:1 on chord/action/source) is built in Phase 3 **before** any binding change; it gates R2 and R5.3.
- [Phase 0]: Keybinding model is native per-OS — kitty's own defaults are authoritative; the payload only adds/overrides for a new action, a behaviour change, or a conflict it owns.

### Pending Todos

- [Phase 5 — found by 02-05, measured on kitty 0.49.0]: the install-time parse check (a) passes a `kitty.conf` whose `include` of our own payload is missing — `load_config(accumulate_bad_lines=…)` only collects value-conversion failures, so the diagnosis reaches stderr (and doctor's PASS line) but not the verdict — and (b) runs only when `install()` changed the conf, so an ordinary reinstall never checks the new payload and the payload rollback never engages. Proposed requirement: the check fails on a missing include of our own payload and runs on every payload replacement. It changes when `my-kitty install` exits non-zero, so it needs its own decision; Phase 5 is the next phase to touch `config_updater`. Evidence: `02-05-SUMMARY.md` § T-2-19.

### Blockers/Concerns

- [Phase 6]: `my-kitty window background none` **fails** on kitty 0.49.0 — `set-colors background=NONE` exits 1 — while `tab accent none` succeeds. R4.1 requires the `none` slot to reset **both**, so Phase 6's palette cycle cannot ship until this is resolved. Found while researching Phase 2 (`.planning/phases/02-defect-remediation/02-RESEARCH.md`), not yet experimented on directly; kitty's config parser also rejects both `none` and `NONE` (`to_color` → `ValueError: Invalid color name`), so the reset sentinel is not a colour value and needs its own mechanism. Phase 6's D-03 already requires pinning `get-colors`' exact output before writing comparison logic — that experiment should cover this too.
- [Phase 10]: Requires one-time manual prerequisites from the user before it can start — enable Remote Login on the Mac, add this host's SSH key, install uv + git, clone the repo, log into the GUI session, share the host alias. No other phase depends on Phase 10, so an unreachable Mac blocks only this phase. It is also the milestone's only human-in-the-loop phase (needs a logged-in Mac GUI session), so an autonomous run must stop there deliberately.
- [Phase 4]: The macOS half of cwd inheritance, instant clear, and conflict-free custom chords stays a documented hypothesis until Phase 10 runs it on a real Mac. Repro docs must say so rather than assume parity.
- [Phase 3]: Whether redundant payload restatement lines (tab-nav, window-nav, font-zoom, url-hints) can be removed depends on the R2.5 experiment's verdict. Phase 4's scope shifts based on that outcome.
- [Phase 1]: Phase 1's branch `gsd/phase-01-governance-freeze` is **not** merged to `master` and nothing is pushed. Its precondition, R1.1, is now met on the Phase 2 branch — 02-02 turned `make doctor` green (exit 0 after a real install, 2026-09-24) — so both branches merge together at Phase 2's end, once `make doctor` and `make test` are green there.

## Deferred Items

Items acknowledged and deferred at milestone close, most recent first:

| Category | Item | Status | Deferred At | Milestone |
|----------|------|--------|-------------|-----------|
| *(none)* | | | | |

## Session Continuity

Last session: 2026-09-24
Stopped at: Phase 2 wave 6 (02-05) merged; 02-06..02-10 plan revision in progress, then waves 7-11
Resume file: .planning/phases/02-defect-remediation/02-06-PLAN.md

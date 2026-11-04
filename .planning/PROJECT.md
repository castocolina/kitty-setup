# kitty-setup

## What This Is

A hypothesis-driven toolkit for the [kitty terminal](https://sw.kovidgoyal.net/kitty/), shipped
as one Python CLI (`my-kitty`, installed via `uv tool`) plus a declarative kitty `.conf`
payload, in two independently installable components: **Foundation** (config and small scripts
that fix daily friction — cwd-preserving tabs/windows, instant clear, paste fidelity, binding
introspection, an install diagnostic) and **Scenes** (declarative TOML recipes that summon a
themed working mode by name). It has exactly one user: the owner, daily-driving kitty on Linux
(Bazzite/KDE, kitty 0.49) and macOS.

This milestone is a remediation milestone on a mature codebase (~4.5k LOC `src/`, ~7.3k LOC
`tests/`), not a greenfield build. The code already tracks the owner's intent; what has drifted
is trustworthiness — the health gate fails on a healthy install, several defects are known and
unfixed, macOS was never verified, the specs contradict the code, and past agents added curated
rebinds mainly to make `my-kitty keys` *look* clean rather than to be *true*.

## Core Value

One trustworthy kitty setup that feels native on both Linux and macOS, where `my-kitty doctor`
is green and everything `my-kitty keys` prints is exactly what kitty actually does in a live
session.

## Requirements

### Validated

<!-- Already shipped in the existing codebase and relied upon daily. -->

- ✓ `my-kitty` single-entry-point CLI installed via `uv tool install --force .`, with
  `tools/setup.sh` / `tools/uninstall.sh` limited to prerequisite bootstrap
- ✓ Declarative kitty `.conf` payload under `~/.config/kitty/kitty-setup/`, with per-OS variant
  selection (`config_updater._select_clear_variant`)
- ✓ cwd inheritance and instant clear-screen behaviours on Linux
- ✓ Binding introspection (`my-kitty keys`) and an install diagnostic (`my-kitty doctor`)
- ✓ Declarative named TOML scenes, fill-current-tab, friendly color-name normalization,
  scene-launch polish, install seeding
- ✓ Autonomous integration harness (`harness/kitty_session.KittySession`), gated by
  `KITTI_INTEGRATION=1`
- ✓ Hypothesis-driven workflow documented in `docs/agent-iteration.md`

### Active

<!-- This milestone's scope. Detail and per-requirement IDs in REQUIREMENTS.md. -->

- [ ] **R0 Governance** — research→experiment→decide rule in `CLAUDE.md`, `.planning/` as source
      of truth, `openspec/` archived and frozen, git policy written down
- [ ] **R1 Defect remediation** — each known audit defect becomes a requirement with a
      regression test; `my-kitty doctor` green on a fresh uv-tool install
- [ ] **R2 Cross-OS keybinding harmonization** — kitty's own defaults authoritative per OS, and
      `my-kitty keys` truthful, proven by an oracle test against kitty's live effective keymap
- [ ] **R3 Foundation/scenes separation** — components install/uninstall independently, no
      cross-imports, doctor enforces a minimum kitty version
- [ ] **R4 Pane color cycle** — `ctrl+shift+alt+c` rotates focused pane background + tab accent
      through an editable palette, statelessly, ≤300 ms
- [ ] **R5 Presets + chord→scene** — named window/tab presets in user TOML, scenes reference them,
      a chord summons a named scene
- [ ] **R6 Live-doc hygiene** — help text, docstrings, README, examples, and repro docs match
      behaviour, with Linux + macOS status sections
- [ ] **R7 macOS end-to-end verification over SSH** — the whole setup proven on a real Mac, not
      assumed

### Out of Scope

- **Suspend/resume survival work** — the existing behaviour stays as-is; no new investigation or
  hardening this milestone (unbounded, not blocking daily use)
- **kitty auto-upgrade on reinstall** — upgrading kitty itself stays the user's action; doctor
  only reports a too-old version (R3.4)
- **Kitten promotion** — deferred to a later milestone; the CLI + `kitten @` remote control is
  sufficient for everything in scope here
- **Rewriting frozen OpenSpec specs** — `openspec/` becomes history-only (R0.2); correcting its
  stale contents would be archaeology with no payoff now that `.planning/` is authoritative
- **Merging to `master`** — merging at a green phase boundary is in scope per D-06: the
  phase-end flow merges into `master` and pushes once `make doctor` and `make test` are green,
  and no force-push or amend of pushed commits is ever allowed. What stays out of scope is any
  merge or force-push outside that boundary — the pre-push guard rejects it, and this phase
  defers its own merge until Phase 2's R1.1 makes `make doctor` green.

## Context

- **Where the distrust comes from**: `my-kitty keys` previously listed chords that did not exist
  or were not effective, and payload lines were added to shape that output rather than to change
  behaviour. This milestone inverts that: kitty's live effective keymap is the oracle, and the
  payload earns every line it keeps.
- **Two hosts, unequal evidence**: Linux (Bazzite/KDE, X11-via-XWayland, kitty 0.49) is the
  daily driver and is verifiable in-session. macOS has never been verified at all — everything
  macOS in this milestone is a hypothesis until Phase 10 runs it over SSH.
- **Existing harness is an asset**: `tests/integration` behind `KITTI_INTEGRATION=1` plus
  `KittySession` means the R2.8 oracle test is buildable today, which is why it lands in Phase 3
  before any binding changes.
- **Governance drift is the root cause**: OpenSpec specs are stale and self-contradictory. They
  are frozen rather than fixed, and `.planning/` replaces them, so there is exactly one place an
  agent can look for intent.
- **Prior art to reuse, not reinvent**: `scenes/colors.normalize_color`,
  `scenes/background.set_window_background`, `scenes/accent.set_tab_accent`,
  `scenes/_client.kitten_at`, `scenes/recipe.load_scene`, `harness/kitty_session.KittySession`,
  `binding_introspection.py`, `config_updater._select_clear_variant`.

## Constraints

- **Tech stack**: Python 3.12+; `my-kitty` is the single `[project.scripts]` entry point. Bash
  exists only in `tools/setup.sh` and `tools/uninstall.sh` for prerequisite bootstrap, and in the
  git-invoked hook entry points under `tools/hooks/` (`pre-push`, `post-commit`, `post-checkout`),
  each a thin dispatcher that delegates to a `my-kitty` subcommand if it outgrows that. No shell
  scripts outside those two clauses. Makefile targets stay ≤5 lines and dispatch into `tools/` or a
  `my-kitty` subcommand — Why: the repo's `CLAUDE.md` "Stack" rule; one entry point is what makes
  behaviour introspectable and testable.
- **Compatibility**: kitty ≥ the minimum constant decided in R3.4 (≥0.46 baseline; hosts run
  0.49). Linux (Bazzite/KDE) and macOS both first-class — Why: same muscle memory on both
  machines is the point of the project.
- **Performance**: instant clear ≤200 ms; color cycle ≤300 ms per press — Why: a chord that lags
  stops being muscle memory; both are measured in integration tests, not eyeballed.
- **Security**: the kitty remote-control socket stays user-scoped, no new network surface, and
  SSH to the Mac is key-auth only — Why: remote control is arbitrary command execution in the
  user's session.
- **Quality gates**: ruff, black, pyright, bandit, vulture clean per `.claude/conventions.md`;
  every requirement carries unit and/or integration tests; integration gated by
  `KITTI_INTEGRATION=1` and green — Why: these are the repo's existing standing gates, not new
  ceremony.
- **Process**: every behaviour change runs through a hypothesis dir `tmp/h<NN>-<slug>/` per
  `docs/agent-iteration.md` — Why: the previous attempt failed by implementing before
  understanding.

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Every phase follows **research → experiment (real kitty session, recorded evidence in `tmp/h<NN>-<slug>/`) → decide → implement → verify with `make doctor` + `make test` output**. No removal or replacement of a config line, chord, or code path without documented research and a recorded experiment first. | The previous attempt's failures all trace to deciding before knowing. "Should work" is not evidence; `<command>` → `<output>` is. | — Pending |
| **Git policy** (revised 2026-09-23, phase-1 discussion D-06/D-16): each phase runs in its own git worktree on branch `gsd/phase-{phase}-{slug}`; work lands as **one commit per plan** (the granularity rule lives in `AGENTS.md` and is pointed to, not restated here) and, at phase end with `make doctor` + `make test` green, merge into `master` and push. Phase 1's branch merges after Phase 2's R1.1 turns `make doctor` green. Agents MUST NOT force-push or amend pushed commits. A `tools/hooks/` pre-push guard enforces it structurally, with all its limits disclosed in `AGENTS.md`. | A plan-sized commit is a coherent unit of review, and the plan boundary is where the requirements a change satisfies are already enumerated; worktrees keep phases isolated; merging at a green phase boundary keeps the owner's history linear without making every integration manual. | — Pending |
| **Execution is autonomous — no clarifying questions during execute phases.** Anything ambiguous is resolved in discuss-phase, before a plan exists. | An autonomous run that stops to ask has failed at its one job. Ambiguity is a planning defect, not a runtime event. | — Pending |
| **`.planning/` is the single source of truth. `openspec/` is frozen as history-only.** | Two authoritative spec systems produced the stale, self-contradictory state this milestone exists to fix. | — Pending |
| **Keybinding model is native per-OS**: kitty's own defaults are authoritative on each OS. The payload adds or overrides a chord only for (a) a new action, (b) a behaviour change, or (c) a conflict with a chord our helper owns — each justified in the allow-list. | Organic kitty chords mean nothing to relearn and nothing to maintain. Curated rebinds existed to prettify `my-kitty keys` output, which is exactly the wrong reason. | — Pending |
| **The R2.8 oracle test is built FIRST (Phase 3), before any binding change**: an integration test that starts a real kitty session, reads kitty's effective keymap independently of `binding_introspection`, and asserts `my-kitty keys --json` matches it 1:1 on chord, action, and source. | It is the acceptance gate for every later binding change (R2 and R5.3). Building it after the changes would mean grading our own homework. | — Pending |
| **macOS verification (R7) is the last phase and nothing depends on it.** Its one-time manual prerequisites are the user's, done before the phase starts. | The Mac may be unreachable. Isolating it means an unavailable Mac blocks exactly one phase instead of the milestone. | — Pending |

---
*Last updated: 2026-09-22 after initial ingest of `docs/prds/kitty-setup-remediation-v1.0-prd.md` (v1.0)*

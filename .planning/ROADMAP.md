# Roadmap: kitty-setup

## Overview

Nine phases that turn a mature-but-untrustworthy kitty setup into a verified one. The order is
the PRD's own execution order and is not negotiable: first the rules and the source of truth are
fixed (Phase 1), then the known defects so `make doctor` / `make test` give a green baseline
worth measuring against (Phase 2). Only then do bindings get touched — and the oracle test that
judges every binding change is built *before* the first change (Phase 3), not after. Harmonized
bindings (Phase 4) land against that oracle. With the binding surface trustworthy, the component
boundary and version floor are enforced (Phase 5), the two new behaviours are built (Phases 6-7),
docs are brought back in line with reality (Phase 8), and finally the whole thing is proven on a
packaged for distribution including the macOS install path (Phase 9), and finally the whole thing — installer included — is proven on a real Mac over SSH and repaired there (Phase 10, the one phase needing a human).

Phase 10 is deliberately terminal and load-bearing for nothing. If the Mac is unreachable, exactly
one phase blocks.

## Universal Phase Gate

Every phase, without exception, runs the mantra and must produce the evidence. These are not
repeated in each phase's success criteria — they are preconditions for calling any phase done:

1. **Research** — kitty docs/source/introspection, written down.
2. **Experiment** — on a real kitty session, evidence recorded in `tmp/h<NN>-<slug>/` per
   `docs/agent-iteration.md`. No behaviour is removed or replaced without this.
3. **Decide** — the decision and its rationale recorded.
4. **Implement**.
5. **Verify** — `make doctor` and `make test` output captured. ruff, black, pyright, bandit,
   vulture clean. "Should work" is not an outcome.
6. **Commit + merge + push** — each phase runs in its own git worktree on branch
   `gsd/phase-{phase}-{slug}`; commit per task, then at phase end (gates green) merge into
   `master` and push. Never force-push or amend pushed commits. A `tools/hooks/` pre-push guard
   enforces this (updated 2026-09-22, phase-1 discussion D-06/D-07).

Phases that touch bindings (3, 4, 7 on Linux; 10 on macOS) additionally re-run the R2.8 oracle
test as a gate.

Execution is autonomous: no clarifying questions during execute. Ambiguity belongs in
discuss-phase.

## Phases

**Phase Numbering:**

- Integer phases (1-9): planned milestone work, in PRD execution order
- Decimal phases (2.1, 2.2): urgent insertions (marked INSERTED), executing between integers

- [ ] **Phase 1: Governance & Freeze** - Lock the mantra, the git policy, and `.planning/` as the one source of truth; archive and freeze `openspec/`
- [ ] **Phase 2: Defect Remediation** - Fix every known audit defect with a regression test so a fresh install is all PASS/SKIP
- [ ] **Phase 3: Keybinding Research & Oracle** - Build the `keys`-vs-live-kitty oracle test first, then the chord matrix and the categorisation experiment
- [ ] **Phase 4: Keybinding Harmonization** - Make chords kitty-organic per OS, judged by the oracle
- [ ] **Phase 5: Component Separation & Version Floor** - Foundation and scenes install independently, no cross-imports, doctor enforces a minimum kitty version
- [ ] **Phase 6: Pane Color Cycle** - `ctrl+shift+alt+c` rotates focused pane background + tab accent through an editable palette, statelessly, ≤300 ms
- [ ] **Phase 7: Presets & Chord→Scene** - Named window/tab presets in user TOML, and a chord that summons a named scene
- [ ] **Phase 8: Live-Doc Hygiene** - Every doc a user or agent reads describes what the code now actually does
- [ ] **Phase 9: Distribution & Release Channels** - Ship a `curl | bash` installer with channel selection
- [ ] **Phase 10: macOS E2E Over SSH** - Prove the whole setup, installer included, on a real Mac driven from Bazzite over SSH — and fix what it finds (human-in-the-loop)

## Phase Details

### Phase 1: Governance & Freeze

**Goal**: An agent opening this repo finds exactly one authoritative source of intent and one set of non-negotiable process rules, so an autonomous run never has to re-litigate how work happens.
**Depends on**: Nothing (first phase)
**Requirements**: R0.1, R0.2, R0.3, R0.4, R0.5, R0.6, R0.7, R0.8, R0.9
**Success Criteria** (what must be TRUE):

  1. `CLAUDE.md` states, as a non-negotiable rule, that research and a recorded real-kitty-session experiment precede any decision to remove or replace a config line, chord, or code path.
  2. `CLAUDE.md` states the git policy explicitly: commit per task, push feature branch `gsd/<phase>`, never merge to `master`, force-push, amend pushed commits, or push `master`.
  3. `CLAUDE.md`'s authoritative-sources list points at `.planning/` with no OpenSpec process references remaining, while still pointing at `docs/agent-iteration.md`.
  4. `phase1-curated-bindings-revert-defaults` is retired via `openspec archive --skip-specs` (main specs untouched — the delta is never fixed), and the tree now lives at `.planning/legacy/openspec/` with no `openspec/` directory at the repo root.
  5. FROZEN banners ("FROZEN — history only; source of truth is `.planning/`") open `.planning/legacy/openspec/README.md`, `docs/requirements.md`, and `docs/propossal_roadmap.md`.
  6. `CLAUDE.md` carries the research-tooling rule: `codegraph_explore` before opening files; size a file (`wc -l`, `rg -n`) and read only the relevant range when it must be opened; prefer `rg`/`fd`/`wc`/`bat`/`sd`/`eza`.
  7. A newly created phase worktree gets a CodeGraph index automatically, and a commit refreshes it; a CodeGraph failure warns without aborting either operation. Demonstrated, not asserted.
  8. The canonical instruction file states that every new GSD plan carries `cross_ai: true` in its frontmatter.
  9. `AGENTS.md` is the canonical instruction file holding every rule, `CLAUDE.md` is the single line `@AGENTS.md`, and `.planning/config.json`'s `claude_md_path` points at the canonical file — so Claude, codex, and opencode all read the same rules.
  10. `AGENTS.md` states the placement rule: rules in `AGENTS.md` (validated with `agent-md-refactor`), project information in `README.md` (validated with `crafting-effective-readmes`), stack conventions in `.claude/conventions.md`; each rule in exactly one file.

**Plans**: TBD

### Phase 2: Defect Remediation

**Goal**: A fresh install on Bazzite is provably healthy — `my-kitty doctor` is all PASS/SKIP and every known audit defect is fixed and pinned by a regression test, giving later phases a green baseline they can trust.
**Depends on**: Phase 1
**Requirements**: R1.1, R1.2, R1.3, R1.4, R1.5, R1.6, R1.7
**Success Criteria** (what must be TRUE):

  1. `my-kitty doctor` exits 0 with every check PASS or SKIP on a fresh Bazzite uv-tool install: completion works via an install-generated static completion file that the rc block sources (no runtime `register-python-argcomplete` PATH lookup), and checks that previously printed "skipped" now report a real SKIP state.
  2. `make clean` never removes `kitty.app` or backups and its help text matches what it does; `tools/uninstall.sh` logs `resolve_binary` failures to stderr where they are visible and its legacy-binary branch works — both branches covered by tests.
  3. A scene whose `cwd` contains spaces fills the current tab correctly (pane-0 `cwd` shell-quoted), and pane 0 honours the same `bash -lc` semantics as every other pane.
  4. A failing config-parse check reports the actual command it ran, surfaces the parser's stderr, rolls the payload directory back, and is labelled correctly in doctor; the integration suite passes when run from inside a kitty window (`KITTY_WINDOW_ID` stripped in h25 and `scene_recipe_e2e`).
  5. Every remaining minor defect has a regression test: the install log removed outright, launcher `int(stdout)` guarded into a clean error, empty/whitespace colors treated as absent and passthrough restricted to real `rgb:`/`rgba:`/functional forms, `prune --keep <0` raising an argparse error, harness teardown issuing `close-os-window`, and the PATH-migration and unsupported-shell hint messages printed exactly as specified (both lines).

**Plans**: TBD

### Phase 3: Keybinding Research & Oracle

**Goal**: Before a single chord changes, there exists an independent oracle that can prove `my-kitty keys` truthful, plus an evidence-backed picture of kitty's own chords on both OSes and a recorded verdict on whether redundant payload lines can safely go.
**Depends on**: Phase 2
**Requirements**: R2.8, R2.2, R2.5, R1.8
**Success Criteria** (what must be TRUE):

  1. The R2.8 oracle integration test exists and is green on Linux: it starts a real kitty session (harness) with the installed config, obtains kitty's effective keymap **independently of `binding_introspection`** by calling kitty's own `debug_config`/`ShortcutMap` renderer, and asserts `my-kitty keys --json` equals it 1:1 on **chord and action**. Source/attribution is asserted separately by targeted fixture tests, because kitty cannot report origin — `definition_location` is empty for every definition (reworded 2026-09-22, phase-3 discussion D-03).
  2. The oracle proves all five truthfulness properties, each with a failing-case test: shadowed lines never shown as active (only as "shadowed by …"), attribution resolving to the real origin (payload file vs kitty default vs user `kitty.conf`), the host OS's default set only, no phantom/duplicate/stale entry or drifted action wording, and user `kitty.conf` bindings outside our block listed and flagged when they shadow ours.
  2b. Sequence bindings render as full sequences (`ctrl+shift+p > f`) from `KeyDefinition.rest`, so the pre-existing duplicate-line bug is gone: `ctrl+shift+p` no longer appears 10 times and `ctrl+shift+a` no longer 4 times (found 2026-09-22, phase-3 discussion D-02).
  3. `docs/research/kitty-default-chords.md` exists with a kitty ≥0.49 Linux-vs-macOS chord matrix sourced from kitty docs/source plus `kitty +runpy` introspection, and classifies every current payload line as new / behaviour-override / redundant restatement.
  4. The R2.5 categorisation experiment is recorded under `tmp/h<NN>-<slug>/` with an explicit verdict: either an in-code action→category table reproduces identical grouping output for kitty defaults (so redundant restatements may be removed in Phase 4), or it does not (so they stay, with the rationale written down).
  5. `cmd+k` and `super+k` normalise to the same chord through kitty's own parser, so payload chords attribute to our file on macOS rather than to a kitty default — proven by test.

**Plans**: TBD
**Note**: Criterion 1 is the acceptance gate for R2 and R5.3 and must land before any work in Phase 4. macOS-side assertions in criteria 2, 3, and 5 are researched here from docs/source and re-run against a real Mac in Phase 10.

### Phase 4: Keybinding Harmonization

**Goal**: Muscle memory is kitty's own on each OS — ctrl+shift on Linux, cmd on macOS — with the payload keeping only the lines that earn their place, and the oracle confirming that what `my-kitty keys` prints is what kitty does.
**Depends on**: Phase 3
**Requirements**: R2.1, R2.3, R2.4, R2.6, R2.7
**Success Criteria** (what must be TRUE):

  1. The payload adds or overrides a chord only for a new action, a behaviour change, or a conflict with a chord our helper owns; every remaining line carries its justification in the allow-list, consistent with the Phase 3 classification and the recorded R2.5 verdict.
  2. New tabs and windows inherit the current directory on `ctrl+shift+t`, `ctrl+shift+n`, and `ctrl+shift+enter` (Linux) and on `cmd+t`, `cmd+n`, `cmd+enter` plus the ctrl+shift variants kitty binds there (macOS).
  3. Instant clear wipes screen **and** scrollback in ≤200 ms via `super+k` on Linux, `cmd+k` on macOS as a declared override of kitty's `clear_terminal to_cursor`, with `ctrl+shift+alt+k` working as a fallback on both — covering the case where the compositor grabs `super+k`.
  4. `my-kitty keys` reports 0 conflicts and the per-OS chord set is documented; `ctrl+shift+m`, `ctrl+shift+i`, `ctrl+shift+d`, `ctrl+shift+alt+d`, and `ctrl+shift+alt+c` are each verified free on both OSes' default maps.
  5. The R2.8 oracle test is green after every binding change in this phase — no phantom, duplicate, stale, or wrongly attributed entry appears at any point.

**Plans**: TBD
**Note**: Linux criteria are verified in this phase. The macOS half of criteria 2, 3, and 4 (including `cmd+k` attributed to `clear`) is verified against a real Mac in Phase 10; until then it is a documented hypothesis, and the repro docs' macOS sections say so.

### Phase 5: Component Separation & Version Floor

**Goal**: Foundation and scenes are genuinely two components rather than one tangled install, and doctor stops implying an unsupported kitty is fine.
**Depends on**: Phase 4 (PRD execution order; technically requires only Phase 2's installer/doctor fixes)
**Requirements**: R3.1, R3.2, R3.3, R3.4
**Success Criteria** (what must be TRUE):

  1. `my-kitty install` and `my-kitty uninstall` accept `--component foundation|scenes|all` (default `all`) and each component installs and uninstalls without disturbing the other; `install --no-config` seeds no scenes unless the scenes component is selected.
  2. After a foundation-only uninstall, scenes behave exactly as the recorded experiment decided — either still working because `remote-control.conf` is owned by scenes, or failing with an actionable error that names what to reinstall.
  3. The `doctor.py`→`scenes._client`, `installer.py`→`scenes.recipe`, and `scenes/_client.py`→`config_updater`/`installer` cross-imports are gone, replaced by a shared neutral module, and an import-boundary check fails `make test` (and pre-commit) if any of them returns.
  4. `my-kitty doctor` FAILs with an upgrade hint when kitty is below the declared minimum-version constant, and PASSes at or above it.

**Plans**: TBD

### Phase 6: Pane Color Cycle

**Goal**: One keypress recolors the pane you are looking at, and its tab, so panes stay visually distinguishable without a menu or a stored state file.
**Depends on**: Phase 5
**Requirements**: R4.1, R4.2, R4.3, R4.4
**Success Criteria** (what must be TRUE):

  1. Pressing `ctrl+shift+alt+c` rotates the focused pane's background **and** its tab accent together to the next palette entry using exactly the existing `my-kitty window background <color>` and `my-kitty tab accent <color>` behaviours with no color transformation, and `none` resets both.
  2. The palette lives in an editable user file seeded copy-if-absent next to scenes, defaulting to `blue, green, red, yellow, purple, teal, orange, gray, none` in that order, with entries validated through `normalize_color`.
  3. The next color is derived from the pane's current background via `kitten @ get-colors` with no persisted state, and a pane whose current background is not a palette entry jumps to the first entry.
  4. `my-kitty window cycle-color [--reverse] [--match] [--to]` works from the shell, the chord invokes it against the focused window id, and an integration test measures ≤300 ms per press on Linux — including with multiple kitty instances running (socket disambiguated).

**Plans**: TBD

### Phase 7: Presets & Chord→Scene

**Goal**: A working mode is described once by name and summoned by a keypress, instead of being re-spelled inline in every scene recipe.
**Depends on**: Phase 6
**Requirements**: R5.1, R5.2, R5.3
**Success Criteria** (what must be TRUE):

  1. Window presets (title + emoji, background, accent, optional cmd) and tab presets (title, accent, layout) are defined once by name in user TOML, and a scene can reference a preset by name while overriding individual fields.
  2. Existing inline scene recipes and the seeded examples keep working unchanged, with no migration step required of the user.
  3. A user-declared scene-name→chord mapping is rendered into the payload, its chords are verified free on both OSes' default maps, and `my-kitty keys` lists them under the `scenes` category.
  4. Pressing a mapped chord summons the named scene composed from its presets, and the R2.8 oracle test is green with the scene chords present.

**Plans**: TBD

### Phase 8: Live-Doc Hygiene

**Goal**: Nothing a user or a future agent reads about this project is a lie — the docs describe the code as it now is, and where macOS is still unproven they say so rather than guessing.
**Depends on**: Phase 7
**Requirements**: R6.1, R6.2
**Success Criteria** (what must be TRUE):

  1. CLI help text, docstrings, README, scene example headers, and the `CLAUDE.md` "Stack" section all match current behaviour — every claim checkable against a command's actual output.
  2. Every behaviour changed in Phases 2-7 has a repro doc carrying both a Linux status section (filled with recorded evidence) and a macOS status section (filled, or explicitly marked pending Phase 10 rather than left blank or assumed).
  3. Frozen `openspec/` specs are left unrewritten, with the freeze banner from Phase 1 still the only change to them.

**Plans**: TBD

### Phase 9: Distribution & Release Channels

**Goal**: Someone who has never cloned this repo can install a chosen release channel with one command, and the channel they get is the one they asked for.
**Depends on**: Phase 8 (Linux behaviour is settled and documented before it is packaged)
**Requirements**: R8.1, R8.2, R8.3, R8.4
**Success Criteria** (what must be TRUE):

  1. `tools/install.sh` installs kitty-setup end-to-end on a clean Linux host via `curl -fsSL <raw-url> | bash`, with no repo clone required beforehand, and the trust model is documented the way `../wezterm-setup/docs/install.md` documents its own.
  2. The installer accepts a channel selection (rolling vs pinned release) and installs the selected one; the default channel is explicit in `--help` and in the README, never implied.
  3. Uninstall remains exact after a `curl | bash` install: `my-kitty uninstall` leaves no trace, verified on a host that never had the repo.
  4. The installer's macOS path is **built here**, not deferred: host-OS detection selects the macOS steps (kitty.app placement, PATH edit for the host shell, per-OS `clear.conf` variant) and channel selection behaves identically on both OSes. Linux is verified in this phase; the macOS path ships as a documented hypothesis that Phase 10 runs and repairs.

**Plans**: TBD
**Note**: Added 2026-09-22 during Phase 1 discussion, modeled on `../wezterm-setup/tools/install.sh`; moved ahead of macOS verification on 2026-09-22 at the user's request. The installer's macOS run moved with it — it is now criterion 5 of Phase 10, which owns every Mac-side check. Out of scope: publishing to a package manager (brew/apt), and any signing/notarization work.

### Phase 10: macOS E2E Over SSH

**Goal**: The macOS half of this project stops being a hypothesis — the same install, doctor, chords, oracle, and installer are exercised on a real Mac in a real GUI session, and whatever they surface is **fixed here**, not filed.
**Depends on**: Phase 9, plus one-time manual prerequisites completed by the user
**Requirements**: R7.1, R7.2, R7.3, R7.4, R7.5, R7.6, R8.3
**Success Criteria** (what must be TRUE):

  1. The plan opens with the one-time prerequisite checklist the user performs — Remote Login enabled on the Mac, this host's SSH key added, uv + git installed, repo cloned, GUI session logged in, host alias shared — and execution does not begin until they are confirmed done.
  2. Driven from Bazzite over SSH in a single session, `make install` succeeds on the Mac, `my-kitty doctor` exits 0 with every check PASS or SKIP, and `my-kitty keys` reports 0 conflicts with `cmd+k` attributed to `clear`.
  3. kitty launches in the Mac GUI session (`open -a kitty` / `launchctl asuser`), is driven via `kitten @` over its unix socket, and the integration suite — including the R2.8 oracle test asserting `my-kitty keys --json` equals kitty's live macOS effective keymap 1:1 — is green.
  4. Every repro doc's macOS status section is filled with recorded evidence from this run, and a short manual UAT checklist covers what cannot be automated (physical keypress feel) and is completed.
  5. The Phase 9 `curl | bash` installer is exercised on the Mac over the same SSH harness, including channel selection and a trace-free `my-kitty uninstall`, and the run is recorded as evidence (R8.3).
  6. `docs/ssh-macos-runbook.md` exists and works: key-based Remote Login, a multiplexed connection (`ControlMaster`/`ControlPersist`) so repeated commands do not re-authenticate, and kitty's remote-control unix socket forwarded to the Linux host (`ssh -L /tmp/kitty-mac.sock:/tmp/kitty-<pid> <host>`) so `kitten @ --to unix:/tmp/kitty-mac.sock` drives the Mac's kitty from Bazzite. The forwarding is proven by experiment before anything relies on it.
  7. Every macOS-specific defect the run surfaces is fixed inside this phase under the Universal Phase Gate, with the macOS oracle test green afterwards (R7.4). Non-macOS defects are recorded and routed to their owning phase rather than fixed here.

**Plans**: TBD
**Note**: No phase depends on Phase 10. If the Mac is unreachable, this phase blocks and the other nine are unaffected — that isolation is the reason it is last. **This is the milestone's one human-in-the-loop phase** (R7.6): it needs a logged-in Mac GUI session plus the one-time prerequisites, so an autonomous run must stop here and say so rather than fail obscurely.

## Progress

**Execution Order:**
Phases execute in numeric order: 1 → 2 → 3 → 4 → 5 → 6 → 7 → 8 → 9 → 10

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 1. Governance & Freeze | 0/TBD | Not started | - |
| 2. Defect Remediation | 0/TBD | Not started | - |
| 3. Keybinding Research & Oracle | 0/TBD | Not started | - |
| 4. Keybinding Harmonization | 0/TBD | Not started | - |
| 5. Component Separation & Version Floor | 0/TBD | Not started | - |
| 6. Pane Color Cycle | 0/TBD | Not started | - |
| 7. Presets & Chord→Scene | 0/TBD | Not started | - |
| 8. Live-Doc Hygiene | 0/TBD | Not started | - |
| 9. Distribution & Release Channels | 0/TBD | Not started | - |
| 10. macOS E2E Over SSH | 0/TBD | Not started | - |

---
*Roadmap created: 2026-09-22 from `docs/prds/kitty-setup-remediation-v1.0-prd.md` (v1.0). Phase
decomposition and order preserved verbatim from the PRD's "Execution Phases" section.*

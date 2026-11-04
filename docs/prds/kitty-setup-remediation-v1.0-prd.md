# kitty-setup Remediation & Cross-OS Harmonization — PRD

> **FROZEN — history only; source of truth is `.planning/`.**
> The dated input `.planning/REQUIREMENTS.md` was ingested from, and still cites as its
> `Source:`. Superseded wherever the two differ — notably R0.4's git policy, reworded
> 2026-09-22/23 per phase-1 decisions D-06 and D-16. Retained for provenance; do not edit.

## Requirements Description

### Background
- **Business Problem**: kitty-setup's code tracks the user's intent, but its OpenSpec specs
  are stale and self-contradictory, the health gate (`my-kitty doctor`) fails on a healthy
  install, several defects exist, macOS was never verified, and Phase 2 §13/§14 plus the
  foundation/scenes separation contract are unfinished. Past agents also added curated
  rebinds mainly to make `my-kitty keys` look clean, diverging from kitty's organic chords.
- **Target Users**: the single owner, daily-driving kitty on Linux (Bazzite/KDE, previously
  Pop!_OS/COSMIC) and macOS.
- **Value Proposition**: one trustworthy, low-maintenance kitty setup that feels native on
  both OSes, whose health check is green, whose docs match reality, and that is driven by a
  GSD workflow able to run autonomously.

### Feature Overview
- **Core Features (requirement groups)**:
  - **R0 Governance** — research→experiment→decide rule; GSD as source of truth; OpenSpec frozen; git policy.
  - **R1 Defect remediation** — audit defects become requirements.
  - **R2 Cross-OS keybinding harmonization** — kitty-organic defaults first.
  - **R3 Foundation/scenes separation** + doctor minimum kitty version.
  - **R4 Pane color cycle chord** (`ctrl+shift+alt+c`).
  - **R5 Presets (§13) + chord→scene (§14)**.
  - **R6 Live-doc hygiene**.
  - **R7 macOS end-to-end verification over SSH**.
- **Feature Boundaries (NOT included)**: suspend/resume survival work; kitty auto-upgrade on
  reinstall; kitten promotion (Phase 3); rewriting frozen OpenSpec specs; merging to master.
- **User Scenarios**:
  - Same muscle memory on both OSes: ctrl+shift+… on Linux, cmd+… on macOS, per kitty's own defaults.
  - `my-kitty doctor` → all PASS on a fresh install.
  - Press `ctrl+shift+alt+c` repeatedly to recolor the focused pane + its tab.
  - Press a chord to summon a named scene composed from presets.

### Detailed Requirements

**R0 Governance**
- R0.1 Add to `CLAUDE.md` a non-negotiable rule: *"Research, then experiment, then decide,
  then implement."* Any removal/replacement of behaviour (config line, chord, code path)
  requires (a) documented research (kitty docs/source/introspection), (b) an experiment on a
  real kitty session with recorded evidence, before the decision.
- R0.2 Archive `openspec/changes/phase1-curated-bindings-revert-defaults` after fixing its
  delta so it syncs cleanly (ADDED vs MODIFIED/REMOVED targets that don't exist in main; keep
  `layout` in the categories list; `scroll_line_* smooth`). Then freeze `openspec/`: add a
  `openspec/README.md` "FROZEN — history only; source of truth is `.planning/`" banner.
- R0.3 Update `CLAUDE.md` + authoritative-sources list to point to `.planning/`; retire
  OpenSpec process references (keep hypothesis playbook `docs/agent-iteration.md`).
- R0.4 Git policy (update CLAUDE.md "No auto-commit"): agents MAY commit per task and push a
  feature branch (`gsd/<milestone-or-phase>`); MUST NOT merge to `master`, force-push, amend
  pushed commits, or push `master`.

**R1 Defects** (each = requirement with regression test)
- R1.1 `my-kitty doctor` completion check passes on a uv-tool install (expose/locate
  `register-python-argcomplete`, e.g. `uv tool install --with argcomplete` + PATH, or detect
  the helper inside the tool venv) — chosen by experiment.
- R1.2 `make clean` behaviour and help text agree; `clean` MUST NOT delete kitty.app or backups.
- R1.3 `tools/uninstall.sh`: logs to stderr inside `resolve_binary`; legacy branch works; errors visible.
- R1.4 Scene fill-current-tab: shell-quote pane-0 `cwd` (`shlex.quote`); pane-0 `cmd` honours the same `bash -lc` semantics as other panes.
- R1.5 Config parse check: report the actual command used, surface parser stderr on failure, roll back the payload dir on failure; fix doctor label.
- R1.6 Integration tests strip `KITTY_WINDOW_ID` (h25, scene_recipe_e2e) so results don't depend on being run inside kitty.
- R1.7 Minor: install log location/content (outside the uv venv, records path+version); guard `int(stdout)` in launcher → clean error; reject empty/whitespace colors and restrict passthrough to `rgb:`/functional forms; `prune --keep <0` → argparse error; harness teardown `close-os-window`; doctor "skipped" → SKIP state; PATH-migration messages printed as specified; unsupported-shell hint prints both lines.
- R1.8 Introspection macOS attribution: normalise payload chords through kitty's parser so `cmd+k` ≡ `super+k` attributes to our file.

**R2 Cross-OS keybinding harmonization**
- R2.1 Model = **native per-OS**: kitty's own defaults are authoritative on each OS
  (ctrl+shift on Linux; cmd on macOS where kitty defines cmd chords). We add/override a chord
  only for (a) a new action, (b) a behaviour change (cwd inheritance, instant clear), or (c) a
  conflict with a chord our helper owns. Every such line is justified in the allow-list.
- R2.2 Research deliverable: a chord matrix `docs/research/kitty-default-chords.md` for kitty
  ≥0.49 (Linux vs macOS), sourced from kitty docs/source + `kitty +runpy` introspection, and
  a list of every current payload line classified: new / behaviour-override / redundant restatement.
- R2.3 cwd inheritance applies to both OSes' chords: Linux `ctrl+shift+t/n/enter`; macOS
  `cmd+t`, `cmd+n`, `cmd+enter` (+ ctrl+shift variants kitty binds there).
- R2.4 Instant clear: `super+k` (Linux), `cmd+k` (macOS, **declared override** of kitty's
  `clear_terminal to_cursor`), `ctrl+shift+alt+k` fallback on both. Wipes screen+scrollback.
- R2.5 Redundant restatement lines (tab-nav, window-nav, font-zoom, url-hints): **remove only
  if an experiment proves** `my-kitty keys` can categorise kitty defaults in code (action→
  category table) with identical grouping output, verified on Bazzite and macOS. Otherwise keep
  and document why.
- R2.6 `my-kitty keys` reports 0 conflicts on both OSes; per-OS chord set documented.
- R2.8 **`my-kitty keys` is truthful (primary goal, not a side effect of cleanup)**. Past
  contradictions came from `keys` listing things that did not exist or were not effective.
  Every line `keys` prints MUST be what kitty actually does in a live session:
  (a) **effective** — the chord→action is the binding kitty resolves at runtime after all
  includes/overrides (no shadowed/dead lines shown as active; shadowed ones shown only as
  "shadowed by …");
  (b) **correct attribution** — source file/category is the real origin (payload file vs
  kitty default vs user kitty.conf), with chords normalised by kitty's own parser;
  (c) **OS-correct** — the default set is the one for the host OS (macOS cmd chords appear on
  macOS only), never a Linux list reused on macOS;
  (d) **no phantoms/duplicates/stale entries** — no entry for a chord kitty does not bind, no
  double-listing, no action text that differs from kitty's current wording (e.g. `… smooth`);
  (e) **user overrides visible** — bindings from the user's own kitty.conf outside our block
  are listed and flagged if they shadow ours.
  **Oracle test**: an integration test starts a real kitty session (harness) with the installed
  config, obtains kitty's effective keymap independently of `binding_introspection`
  (kitty's own runtime/debug-config output), and asserts `my-kitty keys --json` equals it
  1:1 (chord, action, source). The test runs on Linux in every phase that touches bindings and
  on macOS in R7; it is the acceptance gate for R2 and R5.3.
- R2.7 Custom chords (`ctrl+shift+m`, `ctrl+shift+i`, `ctrl+shift+d`, `ctrl+shift+alt+d`,
  `ctrl+shift+alt+c`, scene chords) verified free on BOTH OSes' default maps.

**R3 Separation + doctor**
- R3.1 Foundation and scenes installable/uninstallable independently (`my-kitty install/uninstall --component foundation|scenes|all`, default all); `install --no-config` doesn't seed scenes unless scenes component selected.
- R3.2 Scenes keep working after foundation uninstall only if `remote-control.conf` is owned by scenes or scenes fail with an actionable error — decided by experiment.
- R3.3 Remove cross-imports (`doctor.py`→`scenes._client`, `installer.py`→`scenes.recipe`, `scenes/_client.py`→`config_updater/installer`) via a shared neutral module; add an import-boundary check (pre-commit/`make test` gate).
- R3.4 Doctor enforces a minimum supported kitty version (constant; FAIL below it with upgrade hint).

**R4 Pane color cycle**
- R4.1 `ctrl+shift+alt+c` (both OSes) rotates the **focused pane's background AND its tab
  accent** through the palette, using exactly the existing behaviours of
  `my-kitty window background <color>` and `my-kitty tab accent <color>` (no color
  transformation).
- R4.2 Default palette = existing color names, in order: `blue, green, red, yellow, purple,
  teal, orange, gray, none` (`none` resets both). Stored in an editable user file (seeded
  copy-if-absent next to scenes); names validated with `normalize_color`.
- R4.3 Stateless: next color derived from the pane's current background (`kitten @
  get-colors`); unknown current color → first entry.
- R4.4 New CLI `my-kitty window cycle-color [--reverse] [--match] [--to]`; the chord invokes it
  with the focused window id (mechanism chosen by experiment: `launch --type=background` with
  `@active-kitty-window-id` vs `remote_control_script`). Latency target ≤300 ms per press on Linux.

**R5 Presets + chord→scene**
- R5.1 Window presets (title+emoji, bg, accent, optional cmd) and tab presets (title, accent,
  layout) defined once by name in user TOML; scenes reference presets by name, may override fields.
- R5.2 Backward compatible with existing inline scene recipes and seeded examples.
- R5.3 Chord→scene: user-declared mapping (scene name → chord) rendered into the payload;
  chords validated free on both OSes; `my-kitty keys` shows them under `scenes`.

**R6 Live-doc hygiene** — repro docs, CLI help text, docstrings, README, example headers,
CLAUDE.md "Stack" section match behaviour; every changed behaviour has a repro doc with Linux
+ macOS status sections. Frozen OpenSpec is not rewritten.

**R7 macOS verification over SSH**
- R7.1 Separate phase + plan. Prerequisites the user performs once (documented in the plan):
  enable Remote Login on the Mac, add this host's SSH key, install uv + git, clone the repo,
  log into the GUI session (kitty needs it), share host alias.
- R7.2 Agents drive e2e from Bazzite over SSH within the same session: `make install`,
  `my-kitty doctor`, `my-kitty keys`, launch kitty in the Mac GUI session
  (`open -a kitty` / `launchctl asuser`), drive it via `kitten @` over its unix socket, run the
  integration suite, record evidence into repro docs' macOS sections.
- R7.3 Anything not automatable (physical keypress feel) → a short manual UAT checklist.

- **Edge Cases**: multiple kitty instances (socket disambiguation); pane with custom bg not in
  palette; `none` reset; compositor grabbing `super+k`; kitty versions below minimum; paths with
  spaces; running tests inside kitty; Mac unreachable (R7 blocked, other phases unaffected).

## Design Decisions

### Technical Approach
- **Architecture Choice**: keep Python `my-kitty` single entry point; config payload stays
  declarative `.conf`; per-OS variants follow the existing clear-linux/clear-mac installer
  selection pattern (`config_updater._select_clear_variant`), generalised if needed.
- **Key Components**: `binding_introspection.py` (chord normalisation, category table),
  `config_updater.py`/`installer.py` (components, per-OS variants), `scenes/` (palette,
  cycle, presets, chord→scene), `doctor.py` (completion, min version), `tools/uninstall.sh`.
- **Reuse**: `scenes/colors.normalize_color`, `scenes/background.set_window_background`,
  `scenes/accent.set_tab_accent`, `scenes/_client.kitten_at`, `scenes/recipe.load_scene`,
  `harness/kitty_session.KittySession`.
- **Data Storage**: user TOML under `$XDG_CONFIG_HOME/kitty-setup/` (scenes/, palette,
  presets); managed payload under `~/.config/kitty/kitty-setup/`.

### Constraints
- **Performance**: color-cycle chord ≤300 ms; clear ≤200 ms (existing spec).
- **Compatibility**: kitty ≥ minimum decided in R3.4 (≥0.46 baseline, host runs 0.49);
  Linux (Bazzite KDE X11-via-XWayland) + macOS.
- **Security**: remote-control socket stays user-scoped; no new network surface; SSH to Mac uses key auth only.
- **Process**: every behaviour change follows R0.1 (hypothesis dir `tmp/h<NN>-<slug>/`, experiment evidence) and `docs/agent-iteration.md`.

### Risk Assessment
- **Technical**: macOS kitty key semantics differ from docs → mitigated by R7 SSH e2e.
  Removing redundant rebinds breaks categorisation → gated by R2.5 experiment.
- **Dependency**: Mac availability/SSH → R7 isolated as last phase; other phases never block on it.
- **Schedule**: §13/§14 largest → sequenced after defects and harmonization.

## Acceptance Criteria

### Functional Acceptance
- [ ] `my-kitty doctor` exits 0 with all PASS/SKIP on fresh Bazzite install (and on macOS in R7).
- [ ] `make clean` never removes kitty.app or backups; help text matches.
- [ ] `tools/uninstall.sh` legacy + error branches verified by test.
- [ ] Scene with `cwd` containing spaces fills current tab correctly.
- [ ] Chord matrix doc exists; every payload line classified and justified.
- [ ] `my-kitty keys`: 0 conflicts on Linux and macOS; `cmd+k` attributed to `clear` on macOS.
- [ ] Oracle test green: `my-kitty keys --json` == kitty's live effective keymap 1:1 (chord, action, source), Linux + macOS; no phantom, duplicate, stale, or wrongly attributed entry.
- [ ] cwd inheritance verified for `ctrl+shift+t/n/enter` (Linux) and `cmd+t/n/enter` (macOS).
- [ ] Redundant rebinds removed only with recorded experiment evidence (or kept with rationale).
- [ ] Foundation and scenes install/uninstall independently; import-boundary check enforced.
- [ ] Doctor FAILs below min kitty version.
- [ ] `ctrl+shift+alt+c` cycles pane bg + tab accent through the 9-entry palette and resets on `none`.
- [ ] Presets referenced by name from scenes; a chord launches a named scene.
- [ ] `openspec/` archived + frozen; `.planning/` is the source of truth.

### Quality Standards
- [ ] Code Quality: ruff, black, pyright, bandit, vulture clean (`.claude/conventions.md`).
- [ ] Test Coverage: each requirement has unit and/or integration tests; integration gated by `KITTI_INTEGRATION=1` and green.
- [ ] Performance Metrics: clear ≤200 ms, color cycle ≤300 ms measured in integration tests.
- [ ] Security Review: no new world-readable sockets; SSH key-only.

### User Acceptance
- [ ] UX: same organic kitty chords per OS; only justified customisations.
- [ ] Documentation: repro docs with Linux + macOS status for every changed behaviour; CLAUDE.md rules updated.
- [ ] Manual macOS UAT checklist completed.

## Execution Phases
1. **Governance & freeze** (R0) — CLAUDE.md rules, fix+archive pending change, freeze openspec, git branch policy.
2. **Defect remediation** (R1) — highest first: doctor completion, make clean, uninstall.sh, cwd quoting, parse check, env-dependent tests, minors.
3. **Keybinding research & experiments** (R2.2, R2.5 experiment, R1.8, R2.8 oracle) — chord matrix, classification, categorisation experiment; build the `keys`-vs-live-kitty oracle test FIRST so every later binding change is judged by it.
4. **Keybinding harmonization implementation** (R2.1, R2.3, R2.4, R2.6, R2.7).
5. **Foundation/scenes separation + doctor min version** (R3).
6. **Pane color cycle** (R4).
7. **Presets + chord→scene** (R5).
8. **Live-doc hygiene** (R6).
9. **macOS e2e over SSH** (R7) — separate plan; prerequisites checklist first.
Each phase: hypothesis → experiment → decide → implement → `make doctor` + `make test` evidence → commit + push branch.

---
**Document Version**: 1.0 · **Created**: 2026-09-22 · **Clarification Rounds**: 3 · **Quality Score**: 92/100

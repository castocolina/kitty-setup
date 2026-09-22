# Requirements

Synthesized from classified PRD(s) in `.planning/intel/classifications/`. One entry per
requirement group as structured in the source PRD's "Detailed Requirements" section.

## REQ-governance

- source: docs/prds/kitty-setup-remediation-v1.0-prd.md
- description: R0 Governance — research→experiment→decide rule; GSD as source of truth; OpenSpec frozen; git policy.
- acceptance:
  - R0.1: Add to `CLAUDE.md` a non-negotiable rule: "Research, then experiment, then decide, then implement." Any removal/replacement of behaviour (config line, chord, code path) requires (a) documented research (kitty docs/source/introspection), (b) an experiment on a real kitty session with recorded evidence, before the decision.
  - R0.2: Archive `openspec/changes/phase1-curated-bindings-revert-defaults` after fixing its delta so it syncs cleanly (ADDED vs MODIFIED/REMOVED targets that don't exist in main; keep `layout` in the categories list; `scroll_line_* smooth`). Then freeze `openspec/`: add an `openspec/README.md` "FROZEN — history only; source of truth is `.planning/`" banner.
  - R0.3: Update `CLAUDE.md` + authoritative-sources list to point to `.planning/`; retire OpenSpec process references (keep hypothesis playbook `docs/agent-iteration.md`).
  - R0.4: Git policy (update CLAUDE.md "No auto-commit"): agents MAY commit per task and push a feature branch (`gsd/<milestone-or-phase>`); MUST NOT merge to `master`, force-push, amend pushed commits, or push `master`.
  - Top-level: `openspec/` archived + frozen; `.planning/` is the source of truth.
- scope: governance, CLAUDE.md, OpenSpec freeze, git policy

## REQ-defect-remediation

- source: docs/prds/kitty-setup-remediation-v1.0-prd.md
- description: R1 Defect remediation — audit defects become requirements, each with a regression test.
- acceptance:
  - R1.1: `my-kitty doctor` completion check passes on a uv-tool install (expose/locate `register-python-argcomplete`, e.g. `uv tool install --with argcomplete` + PATH, or detect the helper inside the tool venv) — chosen by experiment.
  - R1.2: `make clean` behaviour and help text agree; `clean` MUST NOT delete kitty.app or backups.
  - R1.3: `tools/uninstall.sh`: logs to stderr inside `resolve_binary`; legacy branch works; errors visible.
  - R1.4: Scene fill-current-tab: shell-quote pane-0 `cwd` (`shlex.quote`); pane-0 `cmd` honours the same `bash -lc` semantics as other panes.
  - R1.5: Config parse check: report the actual command used, surface parser stderr on failure, roll back the payload dir on failure; fix doctor label.
  - R1.6: Integration tests strip `KITTY_WINDOW_ID` (h25, scene_recipe_e2e) so results don't depend on being run inside kitty.
  - R1.7: Minor: install log location/content (outside the uv venv, records path+version); guard `int(stdout)` in launcher → clean error; reject empty/whitespace colors and restrict passthrough to `rgb:`/functional forms; `prune --keep <0` → argparse error; harness teardown `close-os-window`; doctor "skipped" → SKIP state; PATH-migration messages printed as specified; unsupported-shell hint prints both lines.
  - R1.8: Introspection macOS attribution: normalise payload chords through kitty's parser so `cmd+k` ≡ `super+k` attributes to our file.
  - Top-level: `my-kitty doctor` exits 0 with all PASS/SKIP on fresh Bazzite install (and on macOS in R7); `make clean` never removes kitty.app or backups, help text matches; `tools/uninstall.sh` legacy + error branches verified by test; scene with `cwd` containing spaces fills current tab correctly.
- scope: defects, doctor, make clean, uninstall.sh, scenes, tests

## REQ-cross-os-keybinding-harmonization

- source: docs/prds/kitty-setup-remediation-v1.0-prd.md
- description: R2 Cross-OS keybinding harmonization — kitty-organic defaults first.
- acceptance:
  - R2.1: Model = native per-OS: kitty's own defaults are authoritative on each OS (ctrl+shift on Linux; cmd on macOS where kitty defines cmd chords). Add/override a chord only for (a) a new action, (b) a behaviour change (cwd inheritance, instant clear), or (c) a conflict with a chord our helper owns. Every such line justified in the allow-list.
  - R2.2: Research deliverable: a chord matrix `docs/research/kitty-default-chords.md` for kitty ≥0.49 (Linux vs macOS), sourced from kitty docs/source + `kitty +runpy` introspection, and a list of every current payload line classified: new / behaviour-override / redundant restatement.
  - R2.3: cwd inheritance applies to both OSes' chords: Linux `ctrl+shift+t/n/enter`; macOS `cmd+t`, `cmd+n`, `cmd+enter` (+ ctrl+shift variants kitty binds there).
  - R2.4: Instant clear: `super+k` (Linux), `cmd+k` (macOS, declared override of kitty's `clear_terminal to_cursor`), `ctrl+shift+alt+k` fallback on both. Wipes screen+scrollback.
  - R2.5: Redundant restatement lines (tab-nav, window-nav, font-zoom, url-hints): remove only if an experiment proves `my-kitty keys` can categorise kitty defaults in code (action→category table) with identical grouping output, verified on Bazzite and macOS. Otherwise keep and document why.
  - R2.6: `my-kitty keys` reports 0 conflicts on both OSes; per-OS chord set documented.
  - R2.7: Custom chords (`ctrl+shift+m`, `ctrl+shift+i`, `ctrl+shift+d`, `ctrl+shift+alt+d`, `ctrl+shift+alt+c`, scene chords) verified free on BOTH OSes' default maps.
  - R2.8: `my-kitty keys` is truthful (primary goal, not a side effect of cleanup): (a) effective — the chord→action is the binding kitty resolves at runtime after all includes/overrides (no shadowed/dead lines shown as active; shadowed ones shown only as "shadowed by …"); (b) correct attribution — source file/category is the real origin (payload file vs kitty default vs user kitty.conf), chords normalised by kitty's own parser; (c) OS-correct — default set is the one for the host OS (macOS cmd chords appear on macOS only, never a Linux list reused on macOS); (d) no phantoms/duplicates/stale entries; (e) user overrides visible — bindings from user's own kitty.conf outside our block are listed and flagged if they shadow ours. Oracle test: an integration test starts a real kitty session (harness) with the installed config, obtains kitty's effective keymap independently of `binding_introspection` (kitty's own runtime/debug-config output), and asserts `my-kitty keys --json` equals it 1:1 (chord, action, source). Runs on Linux in every phase that touches bindings and on macOS in R7; acceptance gate for R2 and R5.3.
  - Top-level: chord matrix doc exists, every payload line classified and justified; `my-kitty keys`: 0 conflicts on Linux and macOS, `cmd+k` attributed to `clear` on macOS; Oracle test green: `my-kitty keys --json` == kitty's live effective keymap 1:1 (chord, action, source), Linux + macOS, no phantom/duplicate/stale/wrongly attributed entry; cwd inheritance verified for `ctrl+shift+t/n/enter` (Linux) and `cmd+t/n/enter` (macOS); redundant rebinds removed only with recorded experiment evidence (or kept with rationale).
- scope: keybindings, macOS, Linux, cross-OS harmonization

## REQ-foundation-scenes-separation

- source: docs/prds/kitty-setup-remediation-v1.0-prd.md
- description: R3 Foundation/scenes separation + doctor minimum kitty version.
- acceptance:
  - R3.1: Foundation and scenes installable/uninstallable independently (`my-kitty install/uninstall --component foundation|scenes|all`, default all); `install --no-config` doesn't seed scenes unless scenes component selected.
  - R3.2: Scenes keep working after foundation uninstall only if `remote-control.conf` is owned by scenes or scenes fail with an actionable error — decided by experiment.
  - R3.3: Remove cross-imports (`doctor.py`→`scenes._client`, `installer.py`→`scenes.recipe`, `scenes/_client.py`→`config_updater/installer`) via a shared neutral module; add an import-boundary check (pre-commit/`make test` gate).
  - R3.4: Doctor enforces a minimum supported kitty version (constant; FAIL below it with upgrade hint).
  - Top-level: foundation and scenes install/uninstall independently; import-boundary check enforced; doctor FAILs below min kitty version.
- scope: foundation, scenes, doctor, installer

## REQ-pane-color-cycle

- source: docs/prds/kitty-setup-remediation-v1.0-prd.md
- description: R4 Pane color cycle chord (`ctrl+shift+alt+c`).
- acceptance:
  - R4.1: `ctrl+shift+alt+c` (both OSes) rotates the focused pane's background AND its tab accent through the palette, using exactly the existing behaviours of `my-kitty window background <color>` and `my-kitty tab accent <color>` (no color transformation).
  - R4.2: Default palette = existing color names, in order: `blue, green, red, yellow, purple, teal, orange, gray, none` (`none` resets both). Stored in an editable user file (seeded copy-if-absent next to scenes); names validated with `normalize_color`.
  - R4.3: Stateless: next color derived from the pane's current background (`kitten @ get-colors`); unknown current color → first entry.
  - R4.4: New CLI `my-kitty window cycle-color [--reverse] [--match] [--to]`; the chord invokes it with the focused window id (mechanism chosen by experiment: `launch --type=background` with `@active-kitty-window-id` vs `remote_control_script`). Latency target ≤300 ms per press on Linux.
  - Top-level: `ctrl+shift+alt+c` cycles pane bg + tab accent through the 9-entry palette and resets on `none`; color cycle ≤300 ms measured in integration tests.
- scope: color cycling, scenes, keybindings

## REQ-presets-chord-to-scene

- source: docs/prds/kitty-setup-remediation-v1.0-prd.md
- description: R5 Presets (§13) + chord→scene (§14).
- acceptance:
  - R5.1: Window presets (title+emoji, bg, accent, optional cmd) and tab presets (title, accent, layout) defined once by name in user TOML; scenes reference presets by name, may override fields.
  - R5.2: Backward compatible with existing inline scene recipes and seeded examples.
  - R5.3: Chord→scene: user-declared mapping (scene name → chord) rendered into the payload; chords validated free on both OSes; `my-kitty keys` shows them under `scenes`.
  - Top-level: presets referenced by name from scenes; a chord launches a named scene.
- scope: scenes, presets

## REQ-live-doc-hygiene

- source: docs/prds/kitty-setup-remediation-v1.0-prd.md
- description: R6 Live-doc hygiene — repro docs, CLI help text, docstrings, README, example headers, CLAUDE.md "Stack" section match behaviour; every changed behaviour has a repro doc with Linux + macOS status sections. Frozen OpenSpec is not rewritten.
- acceptance:
  - Top-level: documentation — repro docs with Linux + macOS status for every changed behaviour; CLAUDE.md rules updated.
- scope: documentation

## REQ-macos-verification-ssh

- source: docs/prds/kitty-setup-remediation-v1.0-prd.md
- description: R7 macOS end-to-end verification over SSH.
- acceptance:
  - R7.1: Separate phase + plan. Prerequisites the user performs once (documented in the plan): enable Remote Login on the Mac, add this host's SSH key, install uv + git, clone the repo, log into the GUI session (kitty needs it), share host alias.
  - R7.2: Agents drive e2e from Bazzite over SSH within the same session: `make install`, `my-kitty doctor`, `my-kitty keys`, launch kitty in the Mac GUI session (`open -a kitty` / `launchctl asuser`), drive it via `kitten @` over its unix socket, run the integration suite, record evidence into repro docs' macOS sections.
  - R7.3: Anything not automatable (physical keypress feel) → a short manual UAT checklist.
  - Top-level: manual macOS UAT checklist completed.
- scope: macOS, SSH, integration tests

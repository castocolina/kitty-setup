# Requirements: kitty-setup

**Defined:** 2026-09-22
**Source:** `docs/prds/kitty-setup-remediation-v1.0-prd.md` (v1.0, precedence override 0 via
`docs/prds/ingest-manifest.yaml`) — the PRD's own numbering (R0.1–R7.3) is preserved verbatim as
the requirement IDs.
**Core Value:** One trustworthy kitty setup that feels native on both Linux and macOS, where
`my-kitty doctor` is green and everything `my-kitty keys` prints is exactly what kitty actually
does in a live session.

## v1 Requirements

Requirements for this remediation milestone. Each maps to exactly one roadmap phase.

### R0 — Governance

- [ ] **R0.1**: `CLAUDE.md` carries a non-negotiable rule — *"Research, then experiment, then
      decide, then implement."* Any removal or replacement of behaviour (config line, chord, code
      path) requires (a) documented research (kitty docs/source/introspection) and (b) an
      experiment on a real kitty session with recorded evidence, **before** the decision.
- [ ] **R0.2**: `openspec/changes/phase1-curated-bindings-revert-defaults` is archived after
      fixing its delta so it syncs cleanly (ADDED vs MODIFIED/REMOVED targets that don't exist in
      main; keep `layout` in the categories list; `scroll_line_* smooth`). Then `openspec/` is
      frozen: `openspec/README.md` carries a "FROZEN — history only; source of truth is
      `.planning/`" banner.
- [ ] **R0.3**: `CLAUDE.md` and its authoritative-sources list point to `.planning/`; OpenSpec
      process references are retired (the hypothesis playbook `docs/agent-iteration.md` stays).
- [ ] **R0.4**: Git policy written into `CLAUDE.md` (replacing "No auto-commit"): agents MAY
      commit per task and push a feature branch (`gsd/<phase>`); MUST NOT merge to `master`,
      force-push, amend pushed commits, or push `master`.

### R1 — Defect remediation

Each defect is a requirement with a regression test.

- [ ] **R1.1**: `my-kitty doctor`'s shell-completion check passes on a uv-tool install — expose or
      locate `register-python-argcomplete` (e.g. `uv tool install --with argcomplete` + PATH, or
      detect the helper inside the tool venv). Mechanism chosen by experiment.
- [ ] **R1.2**: `make clean` behaviour and help text agree; `clean` MUST NOT delete `kitty.app` or
      backups.
- [ ] **R1.3**: `tools/uninstall.sh` logs to stderr inside `resolve_binary`; the legacy-binary
      branch works; errors are visible.
- [ ] **R1.4**: Scene fill-current-tab shell-quotes pane-0 `cwd` (`shlex.quote`), and pane-0 `cmd`
      honours the same `bash -lc` semantics as every other pane.
- [ ] **R1.5**: Config parse check reports the actual command used, surfaces parser stderr on
      failure, and rolls back the payload dir on failure; the doctor label is fixed.
- [ ] **R1.6**: Integration tests strip `KITTY_WINDOW_ID` (h25, `scene_recipe_e2e`) so results do
      not depend on being run inside kitty.
- [ ] **R1.7**: Minor defects: install log location/content (outside the uv venv, records path +
      version); guard `int(stdout)` in the launcher → clean error; reject empty/whitespace colors
      and restrict passthrough to `rgb:`/functional forms; `prune --keep <0` → argparse error;
      harness teardown `close-os-window`; doctor "skipped" → real SKIP state; PATH-migration
      messages printed as specified; unsupported-shell hint prints both lines.
- [ ] **R1.8**: Introspection macOS attribution — normalise payload chords through kitty's own
      parser so `cmd+k` ≡ `super+k` attributes to our file.

### R2 — Cross-OS keybinding harmonization

- [ ] **R2.1**: Model is **native per-OS**: kitty's own defaults are authoritative on each OS
      (ctrl+shift on Linux; cmd on macOS where kitty defines cmd chords). Add or override a chord
      only for (a) a new action, (b) a behaviour change (cwd inheritance, instant clear), or (c) a
      conflict with a chord our helper owns. Every such line is justified in the allow-list.
- [ ] **R2.2**: Research deliverable — a chord matrix `docs/research/kitty-default-chords.md` for
      kitty ≥0.49 (Linux vs macOS), sourced from kitty docs/source + `kitty +runpy` introspection,
      plus a list of every current payload line classified as new / behaviour-override / redundant
      restatement.
- [ ] **R2.3**: cwd inheritance applies to both OSes' chords: Linux `ctrl+shift+t/n/enter`; macOS
      `cmd+t`, `cmd+n`, `cmd+enter` (plus the ctrl+shift variants kitty binds there).
- [ ] **R2.4**: Instant clear — `super+k` (Linux), `cmd+k` (macOS, a **declared override** of
      kitty's `clear_terminal to_cursor`), `ctrl+shift+alt+k` fallback on both. Wipes screen +
      scrollback.
- [ ] **R2.5**: Redundant restatement lines (tab-nav, window-nav, font-zoom, url-hints) are
      removed **only if an experiment proves** `my-kitty keys` can categorise kitty defaults in
      code (action→category table) with identical grouping output, verified on Bazzite and macOS.
      Otherwise they stay and the reason is documented.
- [ ] **R2.6**: `my-kitty keys` reports 0 conflicts on both OSes; the per-OS chord set is
      documented.
- [ ] **R2.7**: Custom chords (`ctrl+shift+m`, `ctrl+shift+i`, `ctrl+shift+d`,
      `ctrl+shift+alt+d`, `ctrl+shift+alt+c`, scene chords) verified free on BOTH OSes' default
      maps.
- [ ] **R2.8**: **`my-kitty keys` is truthful** (primary goal, not a side effect of cleanup):
      (a) **effective** — the chord→action shown is what kitty resolves at runtime after all
      includes/overrides; no shadowed or dead line shown as active, shadowed ones shown only as
      "shadowed by …";
      (b) **correct attribution** — source file/category is the real origin (payload file vs kitty
      default vs user `kitty.conf`), chords normalised by kitty's own parser;
      (c) **OS-correct** — the default set is the host OS's (macOS cmd chords appear on macOS
      only, never a Linux list reused on macOS);
      (d) **no phantoms/duplicates/stale entries** — no entry for a chord kitty does not bind, no
      double-listing, no action text differing from kitty's current wording (e.g. `… smooth`);
      (e) **user overrides visible** — bindings from the user's own `kitty.conf` outside our block
      are listed and flagged if they shadow ours.
      **Oracle test**: an integration test starts a real kitty session (harness) with the
      installed config, obtains kitty's effective keymap **independently of
      `binding_introspection`** (kitty's own runtime/debug-config output), and asserts
      `my-kitty keys --json` equals it **1:1 on chord, action, and source**. It runs on Linux in
      every phase that touches bindings and on macOS in R7. It is the acceptance gate for R2 and
      R5.3.

### R3 — Foundation/scenes separation + doctor minimum version

- [ ] **R3.1**: Foundation and scenes are installable/uninstallable independently
      (`my-kitty install/uninstall --component foundation|scenes|all`, default `all`);
      `install --no-config` does not seed scenes unless the scenes component is selected.
- [ ] **R3.2**: Scenes keep working after a foundation uninstall only if `remote-control.conf` is
      owned by scenes, or scenes fail with an actionable error — decided by experiment.
- [ ] **R3.3**: Cross-imports removed (`doctor.py`→`scenes._client`,
      `installer.py`→`scenes.recipe`, `scenes/_client.py`→`config_updater`/`installer`) via a
      shared neutral module; an import-boundary check is added as a pre-commit / `make test` gate.
- [ ] **R3.4**: Doctor enforces a minimum supported kitty version (a constant; FAIL below it with
      an upgrade hint).

### R4 — Pane color cycle

- [ ] **R4.1**: `ctrl+shift+alt+c` (both OSes) rotates the **focused pane's background AND its tab
      accent** through the palette, using exactly the existing behaviours of
      `my-kitty window background <color>` and `my-kitty tab accent <color>` (no color
      transformation).
- [ ] **R4.2**: Default palette = existing color names, in order: `blue, green, red, yellow,
      purple, teal, orange, gray, none` (`none` resets both). Stored in an editable user file
      (seeded copy-if-absent next to scenes); names validated with `normalize_color`.
- [ ] **R4.3**: Stateless — the next color is derived from the pane's current background
      (`kitten @ get-colors`); an unknown current color → first entry.
- [ ] **R4.4**: New CLI `my-kitty window cycle-color [--reverse] [--match] [--to]`; the chord
      invokes it with the focused window id (mechanism chosen by experiment:
      `launch --type=background` with `@active-kitty-window-id` vs `remote_control_script`).
      Latency target ≤300 ms per press on Linux.

### R5 — Presets + chord→scene

- [ ] **R5.1**: Window presets (title+emoji, bg, accent, optional cmd) and tab presets (title,
      accent, layout) are defined once by name in user TOML; scenes reference presets by name and
      may override individual fields.
- [ ] **R5.2**: Backward compatible with existing inline scene recipes and the seeded examples.
- [ ] **R5.3**: Chord→scene — a user-declared mapping (scene name → chord) rendered into the
      payload; chords validated free on both OSes; `my-kitty keys` shows them under `scenes`.

### R6 — Live-doc hygiene

> The PRD states R6 as one unnumbered paragraph. It is split here into two checkable items
> (R6.1, R6.2) without adding scope; the "frozen OpenSpec is not rewritten" clause is recorded
> under Out of Scope rather than as a requirement.

- [ ] **R6.1**: CLI help text, docstrings, README, scene example headers, and the `CLAUDE.md`
      "Stack" section match actual behaviour.
- [ ] **R6.2**: Every changed behaviour has a repro doc with both a Linux status section and a
      macOS status section.

### R7 — macOS end-to-end verification over SSH

- [ ] **R7.1**: Separate phase + plan. Prerequisites the user performs once, documented in the
      plan: enable Remote Login on the Mac, add this host's SSH key, install uv + git, clone the
      repo, log into the GUI session (kitty needs it), share the host alias.
- [ ] **R7.2**: Agents drive e2e from Bazzite over SSH within the same session: `make install`,
      `my-kitty doctor`, `my-kitty keys`, launch kitty in the Mac GUI session (`open -a kitty` /
      `launchctl asuser`), drive it via `kitten @` over its unix socket, run the integration
      suite, and record evidence into the repro docs' macOS sections.
- [ ] **R7.3**: Anything not automatable (physical keypress feel) becomes a short manual UAT
      checklist.

## Cross-Cutting Gates

These are not phase-scoped requirements; they apply to **every** phase and are verified before a
phase can be called done. Sourced from the PRD's "Quality Standards" and "Constraints".

- **Process gate**: research → experiment (real kitty session, recorded evidence in
  `tmp/h<NN>-<slug>/`) → decide → implement → verify (R0.1, `docs/agent-iteration.md`).
- **Green gate**: `make doctor` and `make test` output captured as evidence. No "should work".
- **Code quality**: ruff, black, pyright, bandit, vulture clean (`.claude/conventions.md`).
- **Test coverage**: each requirement has unit and/or integration tests; integration gated by
  `KITTI_INTEGRATION=1` and green.
- **Performance**: instant clear ≤200 ms; color cycle ≤300 ms — measured in integration tests.
- **Security**: no new world-readable sockets; remote-control socket stays user-scoped; SSH
  key-auth only.
- **Binding gate**: any phase that touches bindings re-runs the R2.8 oracle test on Linux
  (Phases 3, 4, 7; macOS in Phase 9).
- **Git gate**: commit per task, push branch `gsd/<phase>`; never merge to `master`, force-push,
  amend pushed commits, or push `master` (R0.4).

## Edge Cases To Cover

From the PRD's "Edge Cases". Each belongs to the phase that owns the relevant behaviour.

| Edge case | Owning phase |
|-----------|--------------|
| Multiple kitty instances (socket disambiguation) | Phase 6 |
| Pane with a custom background not in the palette | Phase 6 |
| `none` resets both background and tab accent | Phase 6 |
| Compositor grabbing `super+k` (fallback `ctrl+shift+alt+k`) | Phase 4 |
| kitty versions below the minimum | Phase 5 |
| Paths containing spaces | Phase 2 |
| Running tests from inside kitty | Phase 2 |
| Mac unreachable → Phase 9 blocked, all other phases unaffected | Phase 9 |

## v2 Requirements

Acknowledged but deferred; not in this roadmap.

### Deferred

- **Kitten promotion** — promote helper behaviour into a real kitty kitten.
- **Suspend/resume survival hardening** — beyond the existing behaviour.

## Out of Scope

Explicitly excluded. Documented to prevent scope creep.

| Feature | Reason |
|---------|--------|
| Suspend/resume survival work | Existing behaviour stays as-is; unbounded investigation, not blocking daily use |
| kitty auto-upgrade on reinstall | Upgrading kitty stays the user's action; doctor only reports a too-old version (R3.4) |
| Kitten promotion | Deferred; the CLI + `kitten @` remote control covers everything in scope here |
| Rewriting frozen OpenSpec specs | `openspec/` is history-only after R0.2; correcting stale specs has no payoff now that `.planning/` is authoritative |
| Merging to `master` | Agents push a feature branch only; integration is the owner's call (R0.4) |

## Traceability

Every v1 requirement maps to exactly one phase.

| Requirement | Phase | Status |
|-------------|-------|--------|
| R0.1 | Phase 1 | Pending |
| R0.2 | Phase 1 | Pending |
| R0.3 | Phase 1 | Pending |
| R0.4 | Phase 1 | Pending |
| R1.1 | Phase 2 | Pending |
| R1.2 | Phase 2 | Pending |
| R1.3 | Phase 2 | Pending |
| R1.4 | Phase 2 | Pending |
| R1.5 | Phase 2 | Pending |
| R1.6 | Phase 2 | Pending |
| R1.7 | Phase 2 | Pending |
| R1.8 | Phase 3 | Pending |
| R2.2 | Phase 3 | Pending |
| R2.5 | Phase 3 | Pending |
| R2.8 | Phase 3 | Pending |
| R2.1 | Phase 4 | Pending |
| R2.3 | Phase 4 | Pending |
| R2.4 | Phase 4 | Pending |
| R2.6 | Phase 4 | Pending |
| R2.7 | Phase 4 | Pending |
| R3.1 | Phase 5 | Pending |
| R3.2 | Phase 5 | Pending |
| R3.3 | Phase 5 | Pending |
| R3.4 | Phase 5 | Pending |
| R4.1 | Phase 6 | Pending |
| R4.2 | Phase 6 | Pending |
| R4.3 | Phase 6 | Pending |
| R4.4 | Phase 6 | Pending |
| R5.1 | Phase 7 | Pending |
| R5.2 | Phase 7 | Pending |
| R5.3 | Phase 7 | Pending |
| R6.1 | Phase 8 | Pending |
| R6.2 | Phase 8 | Pending |
| R7.1 | Phase 9 | Pending |
| R7.2 | Phase 9 | Pending |
| R7.3 | Phase 9 | Pending |

**Note on R1.8 and R2.8:** R1.8 (chord normalisation through kitty's parser) sits in Phase 3, not
Phase 2, because it is a prerequisite of the R2.8 oracle's attribution assertion. R2.8's oracle
test is *built* in Phase 3 and *re-run as a gate* in Phases 4, 7, and 9 — it is owned by Phase 3
and is not double-mapped.

**Coverage:**
- v1 requirements: 36 total
- Mapped to phases: 36
- Unmapped: 0 ✓

---
*Requirements defined: 2026-09-22*
*Last updated: 2026-09-22 after initial ingest of `docs/prds/kitty-setup-remediation-v1.0-prd.md`*

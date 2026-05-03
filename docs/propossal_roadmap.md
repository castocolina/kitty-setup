# kitty-scenes — Proposal & Roadmap

Date: 2026-05-01. Companion to [requirements.md](requirements.md). Captures the strategic decisions for the restart and the staged path to ship.

## Strategy decisions

### One repo, two components — not two repos
Keep the foundation (config + bindings) and the scenes layer in a single repo with a surgical-removal contract: each component owns its own leaf paths, has its own install and uninstall target, and never imports from the other. Splitting into two repos would duplicate CI, issue tracking, and release coordination for no current benefit. Revisit only if one component grows independent users or a separate release cadence.

### Foundation and scenes can coexist
The contract that keeps them clean is mechanical, not aspirational: a pre-commit check that forbids cross-imports, separate make targets, and disjoint install paths under a shared parent. Shared tooling (package manager, linters, type checker, tests, docs) lives once.

### Scripts first, kitten last
Earlier work failed because kitten packaging, vendored runtime dependencies, and a boss adapter layer all landed before a single styled window was proven end-to-end. New rule: every scene capability begins as a plain script driving Kitty through its remote-control socket. One script per hypothesis. Each script comes with a manual repro doc. The kitten layer is a packaging step, not a prerequisite — it gets built only after the scripts have earned it.

## Roadmap

### Phase 0 — Reset and align (this week)
- Lock requirements.md as the single source of truth for v1 scope.
- Archive or set aside the prior `kitty_scenes` runtime code; keep `kitty_prefs` config bundle as the foundation seed if it already works.
- Decide the experiment script home (`scripts/experiments/` or similar) and document the conventions: one script per hypothesis, top-of-file manual repro, exit non-zero on failure.

### Phase 1 — Foundation (config + scripts)
Ship the five daily-friction fixes plus the binding introspection helper:
1. Suspend / monitor disconnect stability.
2. Paste preserves CLI output exactly.
3. New tabs and windows inherit cwd.
4. Cmd+K parity for clear screen and scrollback.
5. Curated, conflict-free keybindings, identical on Linux and macOS.
6. Introspection command listing every active binding by category.

Each item is a config diff plus a manual repro. No kitten code. Phase 1 is dogfooded for at least a week before Phase 2 starts.

### Phase 2 — Scenes as scripts (hypothesis-driven)
One script per capability, run from any shell, talking to Kitty over remote control:
- Set window title with text and emoji.
- Set tab title.
- Set window background color.
- Set window font and transparency (verify Kitty surface; defer if global-only).
- Set tab accent color.
- Add one extra layout orientation.
- Spawn N windows in a tab with per-window styles and startup commands, from a TOML recipe.

Stop and reassess after each script. Promote shared logic to a small library only when duplication actually hurts.

### Phase 3 — Kitten promotion (only if earned)
Build the kitten when at least one of these is true:
- Five or more scripts share enough logic that duplication is a real cost.
- A required surface (verified per-feature) is reachable only in-process via the boss API.
- Subprocess and socket latency materially affects the user experience.

Otherwise, ship as scripts plus config. Kitten is not the goal; working scenes are.

## Promotion criteria, restated
A capability moves from script to library, and later to kitten, only when its current form is the bottleneck. No speculative abstractions. No vendoring runtime dependencies until something needs vendoring.

## Risks and mitigations
- **Remote-control gaps.** Some boss-only surfaces may not be reachable through `kitty @`. Mitigation: verify per-capability before committing to the script path; record the gap and decide kitten promotion on evidence, not on guess.
- **Cross-platform drift.** macOS and Linux differ on modifiers and on display-server quirks. Mitigation: every Phase 1 item has a manual repro on both before it is declared done.
- **Scope creep into Phase 2 during Phase 1.** Mitigation: Phase 1 ships and is dogfooded standalone; scenes scripts live in a separate folder and are not wired into install until Phase 2.
- **Reintroducing the prior over-engineering.** Mitigation: any pull request that adds a vendor directory, a boss adapter, or a Protocol layer must justify it against the promotion criteria above.

## What success looks like
End of Phase 1: a fresh machine runs `make install`, gets the six foundation behaviors, and removing the foundation leaves no trace in the user's Kitty config.
End of Phase 2: a small catalog of scene scripts can be invoked from any shell to produce themed tabs and windows, each backed by its own repro test.
End of Phase 3 (if reached): the same capabilities exposed as a kitten, with no new behavior — only better packaging.

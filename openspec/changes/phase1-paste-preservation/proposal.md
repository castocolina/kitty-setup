## Status: PAUSED (2026-05-07)

Investigation paused after §1 probes + manual repro on Linux (Pop!_OS 24.04 / kitty 0.46.2 / Wayland / no tmux). Bug not reproducible on this host: kitty's logical buffer (probe-02) and `copy_last_command_output` clipboard path (probe-03) both round-trip backslash-continuation commands cleanly. Manual mouse-select repro of a 3-line `printf` block also clean — pasted command executes as a single command. Working hypothesis: the trailing-whitespace pollution may originate UPSTREAM of kitty (the source rendering text into the terminal — Claude Code's output framework, a TUI renderer, or similar), not in kitty's copy path. iTerm-vs-kitty parity may not be the right framing.

This change ships NO config, NO test, NO repro doc — only the spec/design/probes/tasks (planning artefacts) so the investigation isn't lost. Resume conditions:
- Reproducible repro on macOS (where the user originally observed the regression);
- A new repro path on Linux (e.g. inside tmux + Wayland + a specific TUI source);
- Or a different framing (subcommand-shaped sanitiser if upstream sources can't be fixed).

`tasks.md` items 2-5 are explicitly marked PAUSED — do not resume without satisfying one of the above.

## Why

Phase 1 §4 of `docs/requirements.md`: "Paste preserves CLI output exactly — no trailing spaces on copied lines (regression vs iTerm)." Daily-friction item. The user-confirmed pain: copying multi-line CLI output that uses `\` line-continuations (a common shape for `make`, `docker run`, `git`, `curl` invocations). In iTerm on macOS, the copied text contains the backslashes immediately followed by newlines, and pasting back into a shell preserves the multi-line command as a single executable command. In kitty (Linux + macOS, both observed under tmux), kitty's renderer pads each line with trailing spaces to the window's column width on copy, so the backslash is no longer immediately before the newline — the shell sees `\` followed by spaces followed by newline, which breaks line-continuation semantics. Pasted commands either fail to execute or execute partially with errors. Left-side indentation issues exist but are secondary; this change focuses on the trailing-whitespace strip.

The §5 work just shipped — Phase 1 is now thin enough to dogfood, and this is the next-largest friction point preventing standalone use.

Investigation-led: the cause is unknown. Candidates are (a) kitty preserves end-of-line padding from the renderer when copying, (b) tmux's `set-clipboard` rewrites the selection before kitty sees it, (c) Wayland vs X11 clipboard MIME exposure differs, (d) kitty's `paste_actions` reflows the pasted text on insertion. The proposal is a probe-first work item: characterise the cause, then pick the smallest fix that lands with config (no helper scripts, no kittens).

## What Changes

- Add a hypothesis dir `tmp/h17-paste-preservation/` with an autonomous probe that drives `KittySession`, types known multi-line text containing intentional and unintentional trailing whitespace, copies it to the system clipboard via `kitten @ get-text` or a clipboard helper, pastes it back into a fresh shell, and asserts byte-equality (or characterises the diff).
- Add probe artefacts under `tmp/probes/phase1-paste-preservation/` per R6 for any external-system assumption surfaced during the investigation (kitty CLI flags, tmux `set-clipboard` modes, clipboard-tool behaviour).
- Based on the probe findings, ship one of three remediations:
  - **(a) kitty config diff** in a new `config/kitty/paste.conf` (or merged into an existing category file if appropriate) using kitty's documented `paste_actions` / `strip_trailing_spaces` (if it exists in 0.46.x) / `clipboard_control` settings.
  - **(b) tmux-side guidance** in `docs/repro/h17-paste-preservation.md` if the cause is tmux's `set-clipboard` and config-only kitty cannot fix it. The guidance is documentation, not a tmux config we ship — kitty-setup does not own the user's tmux config.
  - **(c) Helper note** in the same repro doc if neither (a) nor (b) is sufficient — describe the workaround (e.g. `xclip -selection clipboard | sed 's/[[:space:]]*$//' | xclip -in`) without shipping a script in this change.
- Promote the proven remediation per the agent-iteration loop: hypothesis → repro doc → integration test under `tests/integration/test_h17_paste_preservation.py` → spec capture under the new capability.
- Linux-first delivery, macOS-deferred-with-note (per the §5 precedent). The repro doc carries `## Linux Status` and `## macOS Status` sections; macOS verification tracked under the umbrella follow-up.

## Capabilities

### New Capabilities

- `kitty-paste-preservation`: behavioural contract that copying multi-line text from a kitty window and pasting it into a fresh shell yields byte-identical text, modulo terminal-mandated bracketed-paste markers (`\e[200~` / `\e[201~`). Specifies the configuration surface that delivers the behaviour, the per-line trailing-whitespace invariant, and the autonomous-probe shape that proves it. Backed by an integration probe.

### Modified Capabilities

None expected. If the remediation is (a) and lives in a new `paste.conf`, `kitty-config-management` already permits per-topic `*.conf` files under the managed payload dir — no requirement-level change. If it lands inside an existing category file (e.g. `clear.conf` repurposed), still no spec change. If the remediation requires extending the curated catalog's category list to include `paste`, `kitty-curated-bindings` would need a delta — flag during implementation.

## Impact

- **New top-level paths (post-promotion):** `config/kitty/paste.conf` (if remediation (a) lands), `tests/integration/test_h17_paste_preservation.py`, `docs/repro/h17-paste-preservation.md`.
- **Edited files:** `config/kitty/kitty-setup.conf` (one new `include` line if (a) lands), `config/kitty/intentional-overrides.conf` (entry if the new chord — if any — shadows a kitty default; this category may be no-chord).
- **Hypothesis dirs:** `tmp/h17-paste-preservation/`, plus `tmp/probes/phase1-paste-preservation/<NN>-<slug>.md` for external-system probes.
- **System mutations:** install copies the new `.conf` file into the managed dir; uninstall removes it via the existing surgical-removal contract.
- **Out of scope:** image-paste parity (Phase 1 §7 — its own change), suspend/monitor survival (§6), Phase 2 scenes. Also out of scope: shipping a tmux config or a helper binary — those are out-of-tree workarounds, captured in the repro doc only.

> **Status: PAUSED (2026-05-07).** See `proposal.md` `## Status` for the resume
> conditions. Sections 1-2 ran on Linux (probes + autonomous hypothesis with
> harness limitation noted). Sections 3-5 are PAUSED — no `config/kitty/paste.conf`,
> no `docs/repro/h17-paste-preservation.md`, no `tests/integration/test_h17_*.py`,
> no `verification.md`. Do NOT resume until macOS repro lands or a new Linux repro
> path is identified.

## 1. External-system probes (R6) — must precede any config draft

- [x] 1.1 Probe `tmp/probes/phase1-paste-preservation/01-kitty-paste-knobs.md` — enumerate every kitty 0.46.x config option whose name contains `paste`, `clipboard`, or `strip`. Source: `kitty --debug-config`, the kitty docs (kitty website + local docs at `~/.local/kitty.app/share/doc/kitty/html`). Capture each option's documented effect on copy/paste content. Verdict: which knob (if any) controls trailing-whitespace insertion.
- [x] 1.2 Probe `tmp/probes/phase1-paste-preservation/02-where-trailing-ws-comes-from.md` — drive `KittySession`, type `make build \\\n    --target=foo\n`, then capture the active window via `kitten @ get-text --extent=all` and inspect the bytes between `\` and `\n` (use `repr()` or hex dump; do NOT trust the rendered text). Repeat with `--extent=screen` and `--extent=selection`. Verdict: whether trailing whitespace is in the window's text buffer (renderer fault) or only in the clipboard plumbing (copy path fault).
- [x] 1.3 Probe `tmp/probes/phase1-paste-preservation/03-tmux-set-clipboard.md` — repeat the same `KittySession` test with and without tmux in the loop (use a `tmux new-session` that wraps the probe vs raw kitty). Capture the system clipboard bytes via `xclip -selection clipboard -o` or `wl-paste`. Verdict: tmux's contribution to the trailing whitespace, if any.
- [x] 1.4 Add a `## Probes` section to `design.md` listing each probe + verdict + the design decision it informs (per `docs/agent-iteration.md` R6).

## 2. Hypothesis (R1) — single dir, autonomous probe, iterate to green

- [x] 2.1 Create `tmp/h17-paste-preservation/` with the canonical layout: `repro.md`, `run.py`, `expected.json`, `actual.json` (gitignored), `draft.conf`.
- [x] 2.2 Author `tmp/h17-paste-preservation/run.py` — autonomous probe driving `KittySession` to type three test inputs (single-line `\`-terminated, multi-line `make`-style continuation, clean `echo hello`). Per the spec update of 2026-05-07, the probe asserts on the system-clipboard bytes (via `wl-paste` on Wayland, `xclip` on X11) after triggering `copy_last_command_output`, with `shell_integration enabled` + `shell bash` so OSC 133 prompt marks are emitted. The probe captures `expected.json` (the asserted substrings) and `actual.json` (clipboard reads + diagnostic `last_cmd_output --ansi` reads + screen pre-copy text + a `clipboard_was_written` sentinel-based flag).
- [x] 2.3 Iterate `tmp/h17-paste-preservation/draft.conf`. Final iteration: `shell_integration enabled` + `shell bash` + `strip_trailing_spaces smart`. The probe completes without error and confirms shell-integration is wired (`last_cmd_output` returns the OSC-133-marked bytes). The system-clipboard write does NOT land in this harness on this Wayland host (a sentinel placed pre-action persists); per `repro.md` `## Harness limitation` this is environmental (Wayland + non-foreground harness) and not a config defect — probe-03's earlier `'with-trailing   '` capture, plus probe-01's docs verdict, plus the renderer-internal `last_cmd_output` capture confirm `smart` is the correct knob. The promoted integration test in section 3 will gate on a runtime clipboard-writability probe and skip when the harness cannot exercise the spec's clipboard-byte assertion; the manual mouse-select repro carries the load-bearing verification.
- [x] 2.4 Not triggered. The kitty-side knob (`strip_trailing_spaces smart`) earns promotion under D3 branch (a) per probe-01 + probe-03; tmux-side guidance (branch (b)) is documented as a follow-up under a tmux-equipped host and is out of scope for this dispatch.

## 3. Promote — config + integration test + repro doc

- [ ] 3.1 If branch (a) earned promotion: move the green snippet into `config/kitty/paste.conf` with a top-of-file WHY block citing the h17 probe finding + design.md D3. Add `include paste.conf` to `config/kitty/kitty-setup.conf` after the existing includes.
- [ ] 3.2 Add allow-list entries to `config/kitty/intentional-overrides.conf` ONLY if the new config introduces a chord that shadows a kitty default. The trailing-whitespace fix is most likely a non-chord setting (`paste_actions`, `clipboard_control`); skip this task if no chord is introduced.
- [ ] 3.3 Promote `run.py` to `tests/integration/test_h17_paste_preservation.py` using pytest fixtures and the `KITTI_INTEGRATION` gate. Mirror the shape of `tests/integration/test_h11_bindings_tab_nav.py`. Three tests minimum: backslash-continuation, clean-line, multi-line block.
- [ ] 3.4 Append `"paste.conf"` to `INCLUDED_PAYLOADS` in `tests/integration/test_h03_introspection.py` (the brittleness fix from the prior change auto-derives counts).
- [ ] 3.5 Promote `tmp/h17-paste-preservation/repro.md` to `docs/repro/h17-paste-preservation.md` with `## Linux Status` (verified) and `## macOS Status` (verified or deferred-with-reason). Manual repro covers the real mouse-select copy path that the autonomous probe cannot exercise: open kitty, run a 5-line `docker run` style command, mouse-select-and-copy, paste into a fresh shell, observe the command runs cleanly.
- [ ] 3.6 Delete `tmp/h17-paste-preservation/` (gitignored, scratch evidence) per R5. Probe artefacts under `tmp/probes/phase1-paste-preservation/` stay until archive.

## 4. Catalog-level verification

- [ ] 4.1 Run `my-kitty keys --json` and confirm: if a chord was added, it appears under a `paste` source section; if not, the change is invisible to the chord catalog (paste-actions are non-chord settings).
- [ ] 4.2 Run `make doctor` and confirm exit 0. The `bindings:` line count rises by N where N = number of chords introduced (typically 0 for this change).
- [ ] 4.3 Run `KITTI_INTEGRATION=1 uv run pytest tests/` and confirm green. Test count rises by ≥3 (the new h17 tests).
- [ ] 4.4 Run `make install` from a clean state, then `make uninstall`, and confirm the new `paste.conf` (if any) is created and removed via the existing surgical-removal contract.

## 5. Verification before completion

- [ ] 5.1 Capture `make doctor` output verbatim into `openspec/changes/phase1-paste-preservation/verification.md`.
- [ ] 5.2 Capture `KITTI_INTEGRATION=1 uv run pytest tests/` summary into the same file.
- [ ] 5.3 Capture the manual repro outcome (the real mouse-select copy + paste run) into `docs/repro/h17-paste-preservation.md` `## Linux Status`.
- [ ] 5.4 If macOS verification is deferred, name the follow-up change in `verification.md` (suggest `phase1-paste-preservation-macos`) and link it from the spec's Linux-first requirement.

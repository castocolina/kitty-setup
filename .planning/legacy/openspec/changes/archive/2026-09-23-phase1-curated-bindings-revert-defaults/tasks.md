# Tasks — phase1-curated-bindings-revert-defaults

## 1. Spec & requirements alignment

- [x] 1.1 Read this change's `proposal.md` and `design.md`. Confirm D1–D9 still match user intent before touching files.
- [x] 1.2 Edit `docs/requirements.md` line 14 per D6: drop "vim-style window navigation (h/j/k/l)" and "splits (horizontal/vertical)"; codify the instant-clear iTerm-parity carve-out. Exact replacement text is in design.md D6.
- [x] 1.3 Run `openspec validate phase1-curated-bindings-revert-defaults --strict`. Fix any spec-delta parse errors before moving to §2.

## 2. Hypothesis scaffolding

- [x] 2.1 Pick the next free hypothesis numbers (probably h19 + h20). Create `tmp/h19-bindings-revert/` and `tmp/h20-bindings-clear-relocation-superK/`. Each directory MUST contain a `hypothesis.md` (R1–R7 from `docs/agent-iteration.md`) before any payload edit.
- [x] 2.2 In h19, state the hypothesis: "after removing the hjkl/]/[/0/x/\/​/ overrides from the curated catalog, every released chord resolves to its kitty default in `KittySession.list_keymap()`, and `my-kitty keys` reports `0 conflicts`."
- [x] 2.3 In h20, state the hypothesis: "after binding instant clear to `super+k` (Linux) and `cmd+k` (macOS) with `ctrl+shift+alt+k` fallback, the instant-clear scenario from `kitty-instant-clear` passes on the new chords within 200 ms."

## 3. Payload edits

- [x] 3.1 Rewrite `config/kitty/window-nav.conf` per design D1: drop hjkl, drop `f` → `next_window`. Bind redundant rebinds for `ctrl+shift+]` `next_window`, `ctrl+shift+[` `previous_window`, `ctrl+shift+f` `move_window_forward`, `ctrl+shift+w` `close_window`. Update the file's leading comment to record the revert.
- [x] 3.2 Edit `config/kitty/windowing.conf` per design D2: delete the `ctrl+shift+\ launch --location=vsplit --cwd=current` line and the `ctrl+shift+/ launch --location=hsplit --cwd=current` line. Keep `ctrl+shift+t`, `ctrl+shift+n`, `ctrl+shift+enter`. Update the comment block to describe kitty's compose-model (new_window + next_layout) approach.
- [x] 3.3 Rewrite `config/kitty/tab-nav.conf` per design D3: drop `ctrl+shift+]` `next_tab` and `ctrl+shift+[` `previous_tab`. Bind redundant rebinds for `ctrl+shift+right` `next_tab`, `ctrl+shift+left` `previous_tab`, `ctrl+shift+.` `move_tab_forward`, `ctrl+shift+,` `move_tab_backward`, `ctrl+shift+q` `close_tab`.
- [x] 3.4 Rewrite `config/kitty/font-zoom.conf` per design D4: drop `ctrl+shift+0` `change_font_size all 0`. Bind redundant rebinds for `ctrl+shift+=` `change_font_size all +2.0`, `ctrl+shift+-` `change_font_size all -2.0`, `ctrl+shift+backspace` `change_font_size all 0`.
- [x] 3.5 Rewrite `config/kitty/clear.conf` per design D5: drop `ctrl+shift+x`. Add `super+k` (Linux) and `cmd+k` (macOS) — gated by an `os` conditional or by per-OS includes — plus `ctrl+shift+alt+k` on both OSes. All three lines bind the same instant-clear `combine : clear_terminal scrollback active : send_text ... \x0c` action.
- [x] 3.6 Prune `config/kitty/intentional-overrides.conf` per design D7: remove entries for `ctrl+shift+]`, `ctrl+shift+[`, `ctrl+shift+h`, `ctrl+shift+j`, `ctrl+shift+k`, `ctrl+shift+l`, `ctrl+shift+f`, `ctrl+shift+0`, `ctrl+shift+x`, `ctrl+shift+.`, `ctrl+shift+,`, `ctrl+shift+q`, `ctrl+shift+w`, `ctrl+shift+=`, `ctrl+shift+-`, `ctrl+shift+e`, `ctrl+shift+/`. Add entries for `super+k`, `cmd+k`, `ctrl+shift+alt+k` (each "new chord; no kitty default"). Keep entries for `ctrl+shift+t`, `ctrl+shift+n`, `ctrl+shift+enter` (cwd overrides).

## 4. Test surface

- [x] 4.1 Update `tests/integration/test_h01_cwd.py`: drop assertions on the `vsplit`/`hsplit` chord names. Keep the cwd-inheritance assertion on `ctrl+shift+enter`.
- [x] 4.2 Update `tests/integration/test_h02_clear.py` (or the equivalent clear test): switch the chord under test from `ctrl+shift+x` to `super+k` on Linux (gate with `platform.system() == "Linux"`) and `cmd+k` on macOS. Add a third sub-test for the `ctrl+shift+alt+k` fallback on both OSes.
- [x] 4.3 Write `tests/integration/test_h19_bindings_revert.py`: asserts that `KittySession.list_keymap()` resolves `ctrl+shift+h` → `show_scrollback`, `ctrl+shift+j` → `scroll_line_down`, `ctrl+shift+k` → `scroll_line_up`, `ctrl+shift+l` → `next_layout`, `ctrl+shift+0` → `tenth_window`, `ctrl+shift+x` → `scroll_to_prompt 1`, `ctrl+shift+/` → `search_scrollback`. The catalog files MUST be appended to the session config.
- [x] 4.4 Update or delete the prior `tests/integration/test_h12_bindings_window_nav.py` (vim hjkl) and `tests/integration/test_h13_bindings_font_zoom.py` (was asserting on `ctrl+shift+0` → font reset). Either delete the obsolete assertions outright or rewrite them to match the new catalog. Either way, no test SHALL assert on the dropped behaviours.
- [x] 4.5 Run `make test` and confirm every integration test passes. No new failures, no skipped tests, no `xfail` added by this change.

## 5. Manual repro docs

- [x] 5.1 Write `docs/repro/h19-bindings-revert.md`: per-chord recipe to verify the released chords now resolve to their kitty defaults under a real kitty session (`ctrl+shift+h` opens pager; `ctrl+shift+l` cycles layout; etc.). Linux-verified at apply time; macOS `## macOS Status: deferred` per D9.
- [x] 5.2 Write `docs/repro/h20-bindings-clear-relocation-superK.md`: recipe for triggering `super+k` (Linux) / `cmd+k` (macOS) and observing screen + scrollback wipe; same recipe with the `ctrl+shift+alt+k` fallback chord. Linux-verified at apply time; macOS `## macOS Status: deferred` per D9.
- [x] 5.3 Update `docs/repro/h02-clear.md` and `docs/repro/h09-bindings-clear-relocation.md`: each gains a "Superseded by h20" marker pointing readers at the new repro doc. Keep the old docs (history) but flag them.
- [x] 5.4 Update `docs/repro/h12-bindings-window-nav.md` and `docs/repro/h13-bindings-font-zoom.md`: each gains a "Superseded by h19" marker. Same handling — keep, flag.
- [x] 5.5 Update `docs/repro/h10-bindings-hsplit-relocation.md`: gains a "Superseded — vsplit/hsplit chord pair removed; split workflow is now `ctrl+shift+enter` + `ctrl+shift+l`" marker.

## 6. Doctor + verification

- [x] 6.1 Run `make install` and then `my-kitty doctor`. Expect exit 0 with `PASS bindings: <ours_count> ours, <defaults_count> defaults, 0 conflicts`. Capture the line into `openspec/changes/phase1-curated-bindings-revert-defaults/verification.md` (create this file at this step).
- [x] 6.2 Run `my-kitty keys` and confirm: every released chord is under "kitty defaults" (not under a curated section); the new clear chord(s) are under `clear`; the seven category sections are populated.
- [x] 6.3 Open a fresh kitty session via the just-installed catalog and exercise the user-facing repros: `ctrl+shift+enter` opens a window with inherited cwd; `ctrl+shift+l` cycles layout; `super+k` clears; `ctrl+shift+h` opens scrollback pager. Capture into `verification.md`.
- [x] 6.4 Run the full `make test` once more after `make install` to catch any regression the install introduced. Capture the exit code and pass/skip counts into `verification.md`.

## 7. Spec sync + archive prep

- [x] 7.1 After tasks 1–6 pass, run `openspec validate phase1-curated-bindings-revert-defaults --strict` again. Expect 0 errors.
- [x] 7.2 Mark this change ready for archive by adding a `## Status: ready` line to `verification.md` along with the captured doctor + test output.
- [x] 7.3 Do NOT archive in this work item — archive is a separate, post-merge step driven by the openspec-archive-change skill.

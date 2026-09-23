## 1. Pin kitty_mod and rename clear file

- [x] 1.1 Add `kitty_mod ctrl+shift` as the first non-comment line of `config/kitty/kitty-setup.conf`, before any `include` directive.
- [x] 1.2 Rename `config/kitty/bindings.conf` → `config/kitty/clear.conf`. Update the `include` line in `kitty-setup.conf` to match.
- [x] 1.3 Move the instant-clear chord inside `clear.conf` from `ctrl+shift+k` to `ctrl+shift+x`. Keep the `combine : clear_terminal scrollback active : send_text normal,application \\x0c` action verbatim.
- [x] 1.4 Update `intentional-overrides.conf`: remove the `ctrl+shift+k` line and its comment. (Note: `ctrl+shift+x` shadows kitty's `scroll_to_prompt 1`, so it is now allow-listed in its place — the design D3 prediction "x is unbound in default kitty" was incorrect.)

## 2. Move horizontal-split chord (resolve ctrl+shift+- collision)

- [x] 2.1 In `config/kitty/windowing.conf`, change the hsplit `map` line from `ctrl+shift+-` to `ctrl+shift+/`. Leave vsplit on `ctrl+shift+\\` unchanged. (Note: `ctrl+shift+/` shadows kitty's `search_scrollback`, so it is allow-listed — the design D4 prediction "`/` is unbound in default kitty" was incorrect.)
- [x] 2.2 Add a hypothesis dir `tmp/h10-bindings-hsplit-relocation/` with one probe note explaining why the chord moved.
- [x] 2.3 Add `tests/integration/test_h10_bindings_hsplit_relocation.py` asserting: (a) `ctrl+shift+/` triggers a hsplit window (via the bound launch action — kitty remote control's `send-key` does not traverse the keymap, see test docstring), (b) `ctrl+shift+-` no longer triggers a hsplit (no map line in `windowing.conf`; verified via introspection), (c) `ctrl+shift+-` is reported by `my-kitty keys` under `kitty defaults` with action `change_font_size all -2.0`.
- [x] 2.4 Add manual repro `docs/repro/h10-bindings-hsplit-relocation.md` with `## Linux Status` (verified) and `## macOS Status` (deferred — no Mac access).

## 3. tab-nav category (h11; renumbered from h03 because test_h03_introspection.py owns the h03 slot)

- [x] 3.1 Create `config/kitty/tab-nav.conf` with five `map` lines: `ctrl+shift+]` → `next_tab`, `ctrl+shift+[` → `previous_tab`, `ctrl+shift+.` → `move_tab_forward`, `ctrl+shift+,` → `move_tab_backward`, `ctrl+shift+q` → `close_tab`.
- [x] 3.2 Add the five chords to `intentional-overrides.conf` with the comment "redundant binding for tab-nav.conf categorisation; same action as kitty default".
- [x] 3.3 Add `include tab-nav.conf` to `kitty-setup.conf`.
- [x] 3.4 Hypothesis dir `tmp/h11-bindings-tab-nav/` with probe notes (renumbered from h03; rationale captured in the dir's `repro.md`).
- [x] 3.5 Integration test `tests/integration/test_h11_bindings_tab_nav.py` (renumbered from h03): assert each chord registered with the expected action; assert `my-kitty keys --json` reports a `tab-nav` section with five entries.
- [x] 3.6 Manual repro `docs/repro/h11-bindings-tab-nav.md` (Linux + macOS sections).

## 4. window-nav category (h12; renumbered from h04 per the h11 precedent — h<NN> integers stay contiguous after h09/h10/h11)

- [x] 4.1 Create `config/kitty/window-nav.conf` with six `map` lines: `ctrl+shift+h` → `neighboring_window left`, `ctrl+shift+j` → `neighboring_window down`, `ctrl+shift+k` → `neighboring_window up`, `ctrl+shift+l` → `neighboring_window right`, `ctrl+shift+w` → `close_window`, `ctrl+shift+f` → `next_window`.
- [x] 4.2 Add allow-list entries for all six chords to `intentional-overrides.conf`. **Probe finding (2026-05-06) — D6 correction:** the original task note "the four vim chords and `ctrl+shift+f` are NOT shadows" was wrong. Kitty 0.46.x defaults `ctrl+shift+h` → `show_scrollback`, `ctrl+shift+j` → `scroll_line_down`, `ctrl+shift+k` → `scroll_line_up`, `ctrl+shift+l` → `next_layout`, `ctrl+shift+f` → `move_window_forward`, and `ctrl+shift+w` → `close_window`. Five chords replace different actions; one (`w`) is a redundant same-action rebind. All six are allow-listed.
- [x] 4.3 Add `include window-nav.conf` to `kitty-setup.conf` (after `include tab-nav.conf` to keep reading order).
- [x] 4.4 Hypothesis dir `tmp/h12-bindings-window-nav/` (renumbered from h04 per the h11 precedent; rationale captured in the dir's `repro.md`).
- [x] 4.5 Integration test `tests/integration/test_h12_bindings_window_nav.py` (renumbered from h04): assert each chord registered with the expected action via `binding_introspection.enumerate_bindings(...)`; assert `my-kitty keys --json` reports a `window-nav` section with six entries. Behavioural 2x2 split test skipped — the chord-to-action wiring is validated through introspection (same mechanism as `my-kitty keys`); behavioural focus motion lives in the manual repro.
- [x] 4.6 Manual repro `docs/repro/h12-bindings-window-nav.md` (Linux + macOS sections).

## 5. font-zoom category (h13; renumbered from h05 per the h11/h12 precedent — h<NN> integers stay contiguous after h09/h10/h11/h12)

- [x] 5.1 Create `config/kitty/font-zoom.conf` with three `map` lines: `ctrl+shift+=` → `change_font_size all +2.0`, `ctrl+shift+-` → `change_font_size all -2.0`, `ctrl+shift+0` → `change_font_size all 0`.
- [x] 5.2 Add the three chords to `intentional-overrides.conf`. **Probe finding (2026-05-06) — D6 correction:** the design.md note "all three are kitty defaults" was wrong for `ctrl+shift+0`. Kitty 0.46.x maps `ctrl+shift+0` to `tenth_window` and binds font-reset on `ctrl+shift+backspace`. So `=` and `-` are redundant rebinds (same action as kitty default); `0` replaces `tenth_window` with `change_font_size all 0` (the §5-spec reset chord). All three are allow-listed.
- [x] 5.3 Add `include font-zoom.conf` to `kitty-setup.conf`.
- [x] 5.4 Hypothesis dir `tmp/h13-bindings-font-zoom/` (renumbered from h05; rationale captured in the dir's `repro.md`).
- [x] 5.5 Integration test `tests/integration/test_h13_bindings_font_zoom.py` (renumbered from h05): assert each chord registered with the expected action via `binding_introspection.enumerate_bindings(...)`; assert `my-kitty keys --json` reports a `font-zoom` section with three entries; assert `ctrl+shift+-` is attributed to `font-zoom` and NOT `windowing` (load-bearing for the §2 collision fix — closes the archived `fix-ctrl-shift-minus-collision` follow-up).
- [x] 5.6 Manual repro `docs/repro/h13-bindings-font-zoom.md` (Linux + macOS sections). Manual section confirms visible font size change.

## 6. detach category (h14; renumbered from h06 per the h11/h12/h13 precedent — h<NN> integers stay contiguous after h09/h10/h11/h12/h13)

- [x] 6.1 Probe in `tmp/h14-bindings-detach/` (renumbered from h06) confirmed `detach_window ask` and `detach_tab ask` parse cleanly via kitty's binding introspection, and that the §6 spec wording "kitty-supported equivalent that prompts the user for target" maps directly to the `ask` variants. **Decision: bind both `ask` variants** (matches design.md D6's listed actions). Rationale: (a) `ask` aligns with the spec's prompt requirement; (b) `new-tab` / `new-os-window` would always create a fresh container without prompting, less aligned with D6 and the spec; (c) behavioural confirmation of the picker UX is gated on a manual repro regardless, since kitty remote control's `send-key` cannot drive interactive pickers — same precedent as §4/§5.
- [x] 6.2 Created `config/kitty/detach.conf` with two `map` lines: `ctrl+shift+d detach_window ask`, `ctrl+shift+alt+d detach_tab ask`.
- [x] 6.3 **Probe finding (2026-05-06) — D6 confirmed:** kitty 0.46.x has neither `ctrl+shift+d` nor `ctrl+shift+alt+d` bound by default. Both chords are genuinely new (no kitty-default shadow), so neither needs an `intentional-overrides.conf` allow-list entry. This is the first §-category in the change where no allow-list entry is needed. (Defaults touching the letter `d` only cover `ctrl+shift+down`, `ctrl+shift+page_down`, `ctrl+shift+end`, `ctrl+shift+kp_add`, `ctrl+shift+delete` — none collide.)
- [x] 6.4 Added `include detach.conf` to `kitty-setup.conf` (after `include font-zoom.conf` to keep reading order).
- [x] 6.5 Integration test `tests/integration/test_h14_bindings_detach.py` (renumbered from h06): asserts each chord registered with the expected action via `binding_introspection.enumerate_bindings(...)`; asserts `my-kitty keys --json` reports a `detach` section with two entries; asserts neither chord carries an `override_of` (probe-confirmed) or `conflicts_with`. Behavioural picker test skipped — chord-to-action wiring is validated through introspection (same mechanism as `my-kitty keys`); interactive picker UX lives in the manual repro.
- [x] 6.6 Manual repro `docs/repro/h14-bindings-detach.md` (Linux + macOS sections).

## 7. broadcast category (h15; renumbered from h07 per the h11/h12/h13/h14 precedent — h<NN> integers stay contiguous after h09/h10/h11/h12/h13/h14)

- [x] 7.1 Probe in `tmp/h15-bindings-broadcast/` (renumbered from h07) chose the action `launch --allow-remote-control kitty +kitten broadcast` — the form documented in kitty's own broadcast kitten manual (`share/doc/kitty/html/_sources/kittens/broadcast.rst.txt` ships `map f1 launch --allow-remote-control kitty +kitten broadcast`). Probe ran three candidate strings through `binding_introspection.enumerate_bindings`; all parse cleanly. Picked the `kitty +kitten` form for upstream-doc parity. The custom-remote-control alternative (Option B) was not chosen — it duplicates the kitten's behaviour at maintenance cost.
- [x] 7.2 Created `config/kitty/broadcast.conf` with one `map` line: `ctrl+shift+i launch --allow-remote-control kitty +kitten broadcast`. **Probe finding (h15, 2026-05-06):** kitty 0.46.x has no default on `ctrl+shift+i`, so the chord is genuinely new and does not collide.
- [x] 7.3 No allow-list entry needed — the chord does not shadow a kitty default (probe-confirmed). Same precedent as the §6 detach chords.
- [x] 7.4 Added `include broadcast.conf` to `kitty-setup.conf` (after `include detach.conf` to keep reading order).
- [x] 7.5 Integration test `tests/integration/test_h15_bindings_broadcast.py` (renumbered from h07): asserts the chord is registered with the expected action via `binding_introspection.enumerate_bindings(...)`; asserts `my-kitty keys --json` reports a `broadcast` section with one entry; asserts the chord carries no `override_of` (probe-confirmed) or `conflicts_with`. Behavioural mirroring test skipped — the broadcast kitten reads interactive input that the harness cannot drive; sibling-window mirroring lives in the manual repro.
- [x] 7.6 Manual repro `docs/repro/h15-bindings-broadcast.md` (Linux + macOS sections).

## 8. url-hints category (h16; renumbered from h08 per the h11/h12/h13/h14/h15 precedent — h<NN> integers stay contiguous after h09/h10/h11/h12/h13/h14/h15)

- [x] 8.1 Created `config/kitty/url-hints.conf` with one `map` line: `ctrl+shift+e` → `open_url_with_hints`.
- [x] 8.2 Added `ctrl+shift+e` to `intentional-overrides.conf` ("redundant binding for url-hints.conf categorisation; same action as kitty default"). **Probe finding (h16, 2026-05-06) — D6 confirmed:** kitty 0.46.x defaults `ctrl+shift+e` to `open_url_with_hints`, exactly matching the §5 spec action. So this is a true redundant rebind (same action as the kitty default), restated under `url-hints.conf` for categorisation per D5. The action string `open_url_with_hints` is a bare identifier — kitty's parser preserves it verbatim (no whitespace or case rewriting).
- [x] 8.3 Added `include url-hints.conf` to `kitty-setup.conf` (after `include broadcast.conf` to keep reading order).
- [x] 8.4 Hypothesis dir `tmp/h16-bindings-url-hints/` (renumbered from h08; rationale captured in the dir's `repro.md`).
- [x] 8.5 Integration test `tests/integration/test_h16_bindings_url_hints.py` (renumbered from h08): asserts the chord registered with the expected action via `binding_introspection.enumerate_bindings(...)`; asserts `my-kitty keys --json` reports a `url-hints` section with one entry; asserts the chord carries `override_of == 'open_url_with_hints'` (redundant-rebind annotation per D5) and no `conflicts_with`. Behavioural overlay test skipped — chord-to-action wiring is validated through introspection (same mechanism as `my-kitty keys`); URL-hint overlay UX and browser-launch side effect live in the manual repro.
- [x] 8.6 Manual repro `docs/repro/h16-bindings-url-hints.md` (Linux + macOS sections). Manual section opens a URL via the chord.

## 9. instant-clear chord move (h09)

- [x] 9.1 Hypothesis dir `tmp/h09-bindings-clear-relocation/`.
- [x] 9.2 Update existing integration test `tests/integration/test_h02_clear.py` to assert: (a) the bound action chain triggers screen + scrollback wipe (kitty remote control's `send-key` does not traverse the keymap, see test docstring), (b) `ctrl+shift+k` is no longer a `map` line in `clear.conf`, (c) `my-kitty keys` reports the clear binding under `clear` source (not `bindings`).
- [x] 9.3 Renamed `docs/repro/h02-clear.md` → `docs/repro/h09-bindings-clear-relocation.md` to reflect the new chord and file rename. Linux + macOS sections present.

## 10. Catalog-level verification

- [x] 10.1 Ran `my-kitty keys --json` (2026-05-06): nine source sections present (`broadcast`, `clear`, `detach`, `font-zoom`, `tab-nav`, `url-hints`, `window-nav`, `windowing`, plus `kitty-default`); summary `{"ours": 24, "defaults": 79, "conflicts": 0}`. Verbatim capture in `verification.md`.
- [x] 10.2 Ran `make doctor` (2026-05-06): exit 0; `PASS bindings: 24 ours, 79 defaults, 0 conflicts`. Verbatim capture in `verification.md`.
- [x] 10.3 Ran `KITTI_INTEGRATION=1 uv run pytest tests/` (2026-05-06): 150 passed, 0 failed in 4.43s. Per-file counts in `verification.md`.
- [x] 10.4 Ran a fresh uninstall + install cycle (`KITTI_FORCE=1 KEEP_KITTY=1 make uninstall` → `my-kitty install`, 2026-05-06): install created all 8 category files + `intentional-overrides.conf` + `kitty-setup.conf` under `~/.config/kitty/kitty-setup/`; uninstall removed the entire payload directory and the kitty.conf entry. Cold-kitty leg covered by `tools/setup.sh` and unchanged by this change — caveat documented in `verification.md`.
- [x] 10.5 Updated `README.md` Quickstart with a chord-catalog table (one row per chord, grouped by category, reflecting the corrected actions discovered during implementation, not the original D6 prediction). Stack-and-layout directory tree updated to list every new `.conf` file.
- [x] 10.6 Open-questions sweep in `design.md`: Q1 resolved (h15 probe), Q2 resolved (h14 probe), Q3 follow-up (`phase1-curated-bindings-macos-overrides`), Q4 resolved (sanity sweep — `bindings` is the doctor section name, not the file name), Q5 added and tracked as follow-up `phase1-curated-bindings-broadcast-tab-scope` (broadcast scope wider than spec preamble; loose interpretation kept per the spec's unconstrained-action-string clause).

## 11. Verification before completion

- [x] 11.1 `make doctor` output captured verbatim in `openspec/changes/phase1-curated-bindings/verification.md` §11.1.
- [x] 11.2 `my-kitty keys` text + JSON-summary output captured verbatim in `verification.md` §11.1; per-source counts table covers the 24-ours breakdown.
- [x] 11.3 `KITTI_INTEGRATION=1 uv run pytest tests/` summary captured in `verification.md` §11.1; per-file pass counts table covers all 17 test files.
- [x] 11.4 All eight category repro docs carry `## Linux Status` (verified 2026-05-06) and `## macOS Status` (deferred — no Mac host; tracked under `phase1-curated-bindings-macos-overrides`). Confirmed in `verification.md` §11.2 / §11.3.

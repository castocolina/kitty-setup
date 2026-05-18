## 1. Hypothesis probe (already green; preserve through apply)

- [x] 1.1 Re-run `uv run python tmp/h24-tall-mirrored-right/run.py` on the user's host — expect `[h24] green: actual == expected`. If RED, investigate before any other task.
- [x] 1.2 Confirm `tmp/h24-tall-mirrored-right/expected.json` is present (already committed during /opsx:explore). The Phase B (`B_*`) keys are the load-bearing claims this change ships against.

## 2. Install-time payload — `config/kitty/layout.conf` + windowing.conf comment edit

- [x] 2.1 Create `config/kitty/layout.conf` containing BOTH a curated `enabled_layouts` directive (`enabled_layouts tall,tall:mirrored=true,fat,grid,horizontal,vertical,splits,stack`) AND the chord binding (`map ctrl+shift+m goto_layout tall:mirrored=true`). The file SHALL be prefixed by a comment block citing this change (`phase2-extra-layout-mirrored-tall`), the `kitty-curated-bindings` capability, kitty's `docs/layouts.rst` quote ("`mirrored` shifts the full-height windows to the right"), the empirical grounding (Phase A vs Phase B of `tmp/h24-tall-mirrored-right/expected.json` — option silently ignored without the pin), and the cycle-length consequence (7→8 entries; mirrored Tall appears as a step immediately after plain Tall).
- [x] 2.2 In `config/kitty/kitty-setup.conf`, add the line `include layout.conf` after the existing `include dynamic-opacity.conf` line.
- [x] 2.3 Verify the directive parses against a draft kitty.conf that includes our managed `kitty-setup.conf`. First, create the temp conf file: `printf 'include /home/user-zero/git/cco/kitty-setup/config/kitty/kitty-setup.conf\n' > /tmp/h24-parse-check.conf`. Then reuse the `_parse_check` helper invoked in `phase2-scene-styling/tasks.md` §2.3: `python -c "from kitty_setup.config_updater import _parse_check; from pathlib import Path; print(_parse_check(Path('/tmp/h24-parse-check.conf'), Path.home() / '.local/kitty.app/bin/kitty'))"`. Expect `True`.
- [x] 2.4 Edit `config/kitty/windowing.conf` header comment block (lines 1-11 approximately): replace the paragraph that says "we deliberately do NOT pin `enabled_layouts splits` because that would remove the user's `next_layout` workflow" with a one-line pointer "see `layout.conf` for the curated `enabled_layouts` directive (Phase 2 §11)." Do NOT touch any `map` lines in `windowing.conf`. Verify no `map` line was modified: `git diff config/kitty/windowing.conf` shows only comment-line changes.

## 3. Wire `my-kitty keys` recognition (verify, no code changes expected)

- [x] 3.1 Run `make install` to ship the new `layout.conf` payload.
- [x] 3.2 Run `my-kitty keys` and confirm a `layout:` (or equivalent) section appears, listing exactly one binding whose chord is `ctrl+shift+m` and whose action contains `goto_layout tall:mirrored=true`. NO new code in `binding_introspection.py` SHOULD be required — the introspection already groups by source-file basename. If a code change IS required (e.g. the layout section doesn't appear), pause and surface — this would indicate a hidden coupling.
- [x] 3.3 Run `my-kitty keys --json` and assert the JSON output's `bindings` array contains an entry with `source: "layout"`, `chord: "ctrl+shift+m"`, and an action mentioning `tall:mirrored=true`. Capture the exact action-string format (whitespace, escaping) for the unit test in §4.
- [x] 3.4 Confirm `Summary: 0 conflicts` is still reported (no shadow added, per design D4).
- [x] 3.5 Confirm the new chord does NOT appear in `intentional-overrides.conf` (the spec asserts `ctrl+shift+m` is unbound by kitty default and must not be allow-listed): `grep 'ctrl+shift+m' config/kitty/intentional-overrides.conf` MUST return empty (exit 1). If it matches, the allow-list has been incorrectly updated and must be reverted.

## 4. Unit tests — catalog seventh-category contract

- [x] 4.1 Extend `tests/unit/test_binding_introspection.py`; that file already covers per-source grouping (see `test_render_text_groups_by_source` and related tests). Do NOT create a separate `test_keys_layout_category.py`.
- [x] 4.2 Test: after install, `my-kitty keys --json` reports `layout` as a source group with exactly one binding. Use the existing test-fixture pattern that mocks the payload directory + `kitty +runpy load_config` introspection.
- [x] 4.3 Test: the binding routes to `goto_layout tall:mirrored=true` (action string match — record exact format from §3.3).
- [x] 4.4 Run `pytest tests/unit/` — all green; expect +2 tests minimum (+0 regressions).

## 5. Integration tests — promote h24 probe (Phase B-aligned)

- [x] 5.1 Create `tests/integration/test_h24_layout_mirrored.py` (gated on `KITTI_INTEGRATION=1`), importing helpers from `tests/integration/_kitty_subprocess.py` (already extracted during the h23 apply pass).
- [x] 5.2 Port the `_layout_signature` and `_pane_summary` helpers from `tmp/h24-tall-mirrored-right/run.py` into the new test file as private helpers — they're test-specific and don't belong in `_kitty_subprocess.py` (which holds spawn/socket/discovery primitives shared across hypotheses).
- [x] 5.3 The integration tests spawn kitty with a config that includes the SHIPPED `layout.conf` (so the curated `enabled_layouts` directive is loaded — this is what the change actually ships, and what users will experience). Per design.md D5 mapping table, ship these named tests:
  - [x] `test_curated_enabled_layouts_initial_state_is_plain_tall` — covers probe `B_initial_layout`, `B_goto_tall_ok`, `B_layout_after_goto_tall`. Spawn kitty + the layout.conf payload; assert that `goto-layout tall` lands on `tall:bias=50;full_size=1;mirrored=n`.
  - [x] `test_goto_layout_tall_mirrored_true_applies_option_with_curated_pin` — covers `B_goto_tall_mirrored_after_cycle_ok` + `B_layout_after_goto_tall_mirrored_after_cycle`. After `goto-layout tall:mirrored=true`, assert `kitten @ ls` reports `(ls)[0]["tabs"][0]["layout_opts"]["mirrored"] == "y"`. This is the load-bearing user-visible guarantee.
  - [x] `test_mirrored_tall_puts_main_pane_on_right_with_curated_pin` — covers `B_geometry_after_mirrored`. Launches 2 extra panes for 3 total; runs `goto-layout tall:mirrored=true`; reads `_pane_summary`; asserts main pane (max `lines`) has `neighbors["left"]` populated and `neighbors["right"]` empty.
  - [x] `test_curated_enabled_layouts_cycle_includes_mirrored_variant` — covers `B_next_layout_sequence`. Drives `kitten @ action next_layout` repeatedly starting from plain `tall`; asserts the cycle sequence visits BOTH `(tall, "n")` AND `(tall, "y")` as distinct entries within one full pass through the 8-entry curated list.
- [x] 5.4 Phase A's behaviour (unpinned `enabled_layouts` silently fails the option) is NOT promoted to an integration test — Phase A documents an empirically rejected configuration, and shipping a test for it would create maintenance surface for behaviour this change deliberately does not ship. The Phase A finding is preserved in the repro doc's Attempted-Alternatives section (§6.5) and in the locked `expected.json`.
- [x] 5.5 Run `KITTI_INTEGRATION=1 pytest tests/integration/test_h24_layout_mirrored.py -v` on the user's host — all green.

## 6. Repro doc

- [x] 6.1 Create `docs/repro/h24-bindings-layout.md` with the standard sections: `## Why`, `## Manual repro`, `## Linux Status`, `## macOS Status`, `## Attempted alternatives`, `## Known limitations`, `## Recipes`.
- [x] 6.2 `## Manual repro` SHALL document the user-runnable scenarios: open a kitty window, launch 2 additional windows (`ctrl+shift+enter` × 2), invoke `ctrl+shift+m`, observe one pane full-height on the right and the other two stacked top/bottom on the left. Document the return path via `ctrl+shift+l` (next_layout) — note that the cycle now has 8 entries (mirrored Tall is the second step from plain Tall).
- [x] 6.3 `## Linux Status` outcome `verified (YYYY-MM-DD, Pop!_OS 24.04 + COSMIC + kitty 0.46.2)` after user sign-off in §7.4. Block archive until verified.
- [x] 6.4 `## macOS Status` outcome `deferred-with-reason` — note: "no Mac host available; `kitten @ goto-layout` is platform-agnostic; rendered layout visual fidelity (divider anti-aliasing, transition animation) is the only macOS-specific concern." Track under follow-up `phase2-extra-layout-mirrored-tall-macos`.
- [x] 6.5 `## Attempted alternatives` table: no `enabled_layouts` pinning (rejected — Phase A of h24 probe empirically demonstrated the option is silently ignored without pinning); toggle pair (rejected — user chose single-chord Shape A in explore); pin to a curated subset that drops layouts (rejected — removes fat/grid/horizontal/vertical/splits/stack from next_layout reach); append to `windowing.conf` (rejected — violates catalog's per-file-per-category contract).
- [x] 6.6 `## Known limitations` SHALL include: `next_layout` cycle is now 8 entries instead of 7 (mirrored Tall appears as a step immediately after plain Tall); return path from mirrored to plain Tall is multi-keystroke (cycle via `ctrl+shift+l`); kitty's `kitten @ ls` exposes `mirrored` as `"y"`/`"n"` strings rather than booleans; `kitten @ ls` does not expose pixel geometry so visual position verification relies on `window["neighbors"]`; the chord's exit code does NOT reflect whether the mirror option was applied (Phase A success ≠ option success; the assertion must be against `layout_opts.mirrored`).
- [x] 6.7 `## Recipes` SHALL include: shell alias for chord-equivalent invocation (`alias kl-mir='kitten @ goto-layout tall:mirrored=true'` for non-kitty contexts), composition preview using h22's title primitive (`my-kitty tab title "🔍 review" && <invoke chord>`).

## 7. Verification + archive prep

- [x] 7.1 Run `make doctor` on the user's host — all checks pass. The `bindings` check SHOULD report exactly 1 more "ours" entry than the pre-apply baseline (absolute count is informational and MUST NOT be treated as a blocking gate); the `parse check` SHOULD exit 0.
- [x] 7.2 Run `make install` to rebuild the deployable binary so the new payload lands on disk.
- [x] 7.3 Run `make test` and `KITTI_INTEGRATION=1 pytest tests/` — both green.
- [x] 7.4 Manually verify on the user's daily host: open a kitty with 3 panes (e.g. `ctrl+shift+enter` × 2 from a fresh window); press `ctrl+shift+m`; observe one pane full-height on the right. Press `ctrl+shift+l` repeatedly to confirm the cycle is 8 entries (including the mirrored variant as a step) and that plain `tall` is reachable again on the next pass.
- [x] 7.5 Confirm `layout.conf` ships: `cat ~/.config/kitty/kitty-setup/layout.conf` shows BOTH the `enabled_layouts tall,tall:mirrored=true,fat,grid,horizontal,vertical,splits,stack` line and the `map ctrl+shift+m goto_layout tall:mirrored=true` line; `grep -c 'include layout.conf' ~/.config/kitty/kitty-setup/kitty-setup.conf` returns 1.
- [x] 7.6 Confirm `my-kitty keys` reports `0 conflicts` and includes a `layout` section with the expected binding.
- [x] 7.7 Confirm `windowing.conf` header comment was edited to point at `layout.conf` and that no `map` lines were touched: `git diff config/kitty/windowing.conf` shows only comment-line changes (verify diff hunk by inspection).
- [x] 7.8 Delete `tmp/h24-tall-mirrored-right/` (probe served its purpose; spec mandates deletion before archive, mirroring the h23 contract).
- [x] 7.9 Run `openspec validate phase2-extra-layout-mirrored-tall --strict` — passes.
- [x] 7.10 Author `verification.md` capturing `make doctor` + `make test` outputs verbatim plus the manual-verification outcomes.

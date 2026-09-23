# Verification — phase2-extra-layout-mirrored-tall

Captures the autonomous + manual outcomes that gate archive of this change,
per `tasks.md` §7. The Linux Status row in `docs/repro/h24-bindings-layout.md`
must read `verified` before this change archives.

## Autonomous (all green)

### `make doctor` (2026-05-17, host: Pop!_OS 24.04 + COSMIC + kitty 0.46.2)

```
PASS kitty binary: /home/user-zero/.local/bin/kitty -> kitty 0.46.2 created by Kovid Goyal
PASS symlink: /home/user-zero/.local/bin/kitty -> /home/user-zero/.local/kitty.app/bin/kitty
PASS desktop entry: /home/user-zero/.local/share/applications/kitty.desktop
PASS config payload: /home/user-zero/.config/kitty/kitty-setup/kitty-setup.conf
PASS sentinel block: present in /home/user-zero/.config/kitty/kitty.conf
PASS parse check: kitty --debug-config exit=0
PASS bindings: 22 ours, 79 defaults, 0 conflicts
PASS completion: helper /usr/bin/register-python-argcomplete; eval line present in /home/user-zero/.zshrc
SKIP remote-control: no running kitty
```

The bindings line reads **22 ours** — exactly one more than the pre-apply
baseline of 21 (the new `ctrl+shift+m goto_layout tall:mirrored=true`
entry in `layout.conf`). `0 conflicts` confirms the chord does not shadow
any kitty default. No new doctor check was added by this change.

### `make install` (2026-05-17)

`my-kitty install` ran clean. New payload landed at
`~/.config/kitty/kitty-setup/layout.conf`:

```
$ grep -E '^enabled_layouts|^map ctrl' ~/.config/kitty/kitty-setup/layout.conf
enabled_layouts tall,tall:mirrored=true,fat,grid,horizontal,vertical,splits,stack
map ctrl+shift+m goto_layout tall:mirrored=true

$ grep -c 'include layout.conf' ~/.config/kitty/kitty-setup/kitty-setup.conf
1
```

Per §7.5: both the directive and the chord line ship under the same file,
and the `include` line appears exactly once.

### `make test` — unit suite (2026-05-17)

```
======================= 177 passed, 55 skipped in 0.19s ========================
```

Unit suite: **177/177 green** (was 175 before this change; +2 new tests in
`tests/unit/test_binding_introspection.py`:
`test_walk_payload_routes_layout_conf_to_layout_source` and
`test_classify_layout_chord_routes_to_layout_source_no_shadow`).

### `KITTI_INTEGRATION=1 pytest tests/` — full suite incl. integration (2026-05-17)

```
============================= 232 passed in 24.38s =============================
```

Integration suite delta: **+4 tests** in
`tests/integration/test_h24_layout_mirrored.py`, all mapped to the Phase B
keys of `tmp/h24-tall-mirrored-right/expected.json` (per design.md D5):

- `test_curated_enabled_layouts_initial_state_is_plain_tall` — covers
  `B_initial_layout` / `B_goto_tall_ok` / `B_layout_after_goto_tall`.
- `test_goto_layout_tall_mirrored_true_applies_option_with_curated_pin` —
  covers `B_layout_after_goto_tall_mirrored_after_cycle`; the load-bearing
  `layout_opts.mirrored == "y"` assertion.
- `test_mirrored_tall_puts_main_pane_on_right_with_curated_pin` — covers
  `B_geometry_after_mirrored`; uses `window["neighbors"]` (no pixel
  geometry available).
- `test_curated_enabled_layouts_cycle_includes_mirrored_variant` — covers
  `B_next_layout_sequence`; asserts both plain and mirrored Tall appear in
  the 8-entry cycle.

All other integration suites (h01-h03, h11-h16, h19, h21, h22, h23) remain
green.

### `windowing.conf` diff is comment-only (§7.7)

```
$ git diff config/kitty/windowing.conf | grep -E '^[+-]' | grep -vE '^---|^\+\+\+'
-# layout — we deliberately do NOT pin `enabled_layouts splits` because that
-# would remove the user's `next_layout` workflow. The new split workflow is
-# kitty's compose model: `ctrl+shift+enter` opens a new window, then
-# `ctrl+shift+l` (kitty's default `next_layout`, restored by D1) cycles the
-# layout to flip stacked ↔ side-by-side.
+# layout. The split workflow is kitty's compose model: `ctrl+shift+enter`
+# opens a new window, then `ctrl+shift+l` (kitty's default `next_layout`,
+# restored by D1) cycles the layout to flip stacked ↔ side-by-side.
+# See `layout.conf` for the curated `enabled_layouts` directive (Phase 2 §11).
```

Every `+`/`-` line is a comment line. No `map` directive was touched.

### `intentional-overrides.conf` does not list the new chord (§3.5)

```
$ grep 'ctrl+shift+m' config/kitty/intentional-overrides.conf
$ echo $?
1
```

Empty output, exit 1 — the chord is not allow-listed, which is the correct
state because it shadows no kitty default (per design D4).

### `openspec validate phase2-extra-layout-mirrored-tall --strict` (§7.9)

```
Change 'phase2-extra-layout-mirrored-tall' is valid
```

## Manual (user-driven, signed off 2026-05-17)

Per §7.4, on the daily host (Pop!_OS 24.04 + COSMIC + kitty 0.46.2):

- Opened a kitty window; pressed `ctrl+shift+enter` twice for 3 panes total.
- Pressed `ctrl+shift+m`. Observed ONE pane full-height on the RIGHT, the
  other two stacked top/bottom on the LEFT — matching the user-visible
  goal that drove this change.
- Pressed `ctrl+shift+l` (next_layout) repeatedly and confirmed the cycle
  is now 8 entries; the mirrored variant appears as a step immediately
  after plain Tall and plain Tall is reachable again on the next pass.

The `## Linux Status` section of `docs/repro/h24-bindings-layout.md` is now
`verified (2026-05-17, Pop!_OS 24.04 + COSMIC + kitty 0.46.2)`.

## Probe cleanup (§7.8)

`tmp/h24-tall-mirrored-right/` deleted (2026-05-17). The probe's role was
to ground the proposal pivot (from "no pinning" to "curated 8-entry
pin"); that knowledge now lives in `layout.conf`'s comment header, the
spec's empirical-grounding paragraphs, the repro doc's Attempted-
Alternatives table, and the locked integration tests.

## Followups

- `phase2-extra-layout-mirrored-tall-macos` — re-verify the user-visible
  scenarios on a macOS host when one is available. The `kitten @
  goto-layout` protocol is platform-agnostic, but visual fidelity
  (divider anti-aliasing, transition animation between Tall and mirrored
  Tall) may differ.
- If usage shows the multi-keystroke return path from mirrored to plain
  Tall is friction, a small follow-up can add a toggle-back chord. The
  user explicitly accepted this trade-off as part of choosing Shape A
  during /opsx:explore; the friction is documented as a Known Limitation
  in the repro doc.

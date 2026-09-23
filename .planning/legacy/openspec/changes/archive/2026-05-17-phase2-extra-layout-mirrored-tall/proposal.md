# phase2-extra-layout-mirrored-tall

## Why

Phase 2 §11 of `docs/requirements.md` (roadmap line 41) asks for one extra
layout orientation beyond kitty defaults. The user's specific need: with
three panes in one OS-window, **one pane full-height on the RIGHT and the
other two stacked top/bottom on the LEFT**. Kitty's default Tall layout
puts the full-height pane on the left, and there's no out-of-the-box chord
to reach the mirrored variant.

The h24 probe (`tmp/h24-tall-mirrored-right/run.py`) is green against
kitty 0.46.2 on the user's host. The mechanism is kitty's
**`tall:mirrored=true`** option (verified against kitty's `docs/layouts.rst`
via context7 — "`mirrored` shifts the full-height windows to the right").

A critical empirical finding from the probe drives the design below:
`kitten @ goto-layout tall:mirrored=true` exits 0 with empty stderr
**whether or not `enabled_layouts` is pinned**, but the `mirrored=true`
option is **silently ignored unless `tall:mirrored=true` is an explicit
entry in `enabled_layouts`**. Phase A of `expected.json` (vanilla
`enabled_layouts *`) records `A_layout_after_goto_tall_mirrored:
"tall:bias=50;full_size=1;mirrored=n"` and main-pane-on-the-LEFT geometry;
Phase B (with `enabled_layouts tall,tall:mirrored=true,…` pinned) records
`mirrored=y` and main-pane-on-the-RIGHT geometry. The chord only does what
the user wants when the enabled-layouts list explicitly carries the
option-bearing variant.

## What Changes

- New chord: `ctrl+shift+m` → `goto_layout tall:mirrored=true`. Single
  direct-jump chord; no toggle pair. The chord is identical on Linux and
  macOS because our managed config pins `kitty_mod ctrl+shift` on both
  OSes (per the existing `kitty-curated-bindings` "Pin kitty_mod for
  cross-OS chord parity" requirement).
- New install-time payload `config/kitty/layout.conf` shipping BOTH the
  chord binding AND a curated `enabled_layouts` directive that pins the
  list to: `tall,tall:mirrored=true,fat,grid,horizontal,vertical,splits,stack`.
  This preserves access to all 7 of kitty's base layouts (matching what
  the default `*` expands to) and adds `tall:mirrored=true` as a distinct
  enabled entry so the chord's `goto_layout` actually applies the option.
- Cycle trade-off: with the pin in place, `ctrl+shift+l` (`next_layout`)
  visits 8 entries instead of 7 — the mirrored variant becomes a step in
  the cycle, immediately after plain `tall`. The user can still reach
  every base layout via the cycle; the cycle is just one step longer.
- The previously-undocumented "we deliberately do NOT pin
  `enabled_layouts`" comment in `config/kitty/windowing.conf:7-11` is
  updated to point readers at `layout.conf` for the new directive (a
  one-line comment edit; no semantic change to windowing.conf bindings).
- New comment in `intentional-overrides.conf` documenting that
  `ctrl+shift+m` is unbound by kitty default and so does NOT need an
  override entry. This is annotation-only; the binding adds to a
  previously-unbound chord, so `my-kitty keys` will continue to report
  `0 conflicts`.
- Hypothesis scratch `tmp/h24-tall-mirrored-right/` already green;
  promoted to integration tests during apply; deleted at archive (same
  contract as h22, h23).

Not in scope:

- Toggle pair (one chord to mirror, another back). The single-chord shape
  was the user's explicit choice during /opsx:explore.
- `my-kitty` CLI subcommand for runtime layout switching. Defer to Phase 2
  §13 (named scenes) where composition lives.
- Other layout-changing chords (no `ctrl+shift+m` companion to jump to
  `splits`, `grid`, `stack`, etc.). §11 is one extra; not a catalog.
- Pin `enabled_layouts` to a curated SUBSET (e.g. just `tall,tall:mirrored=true`).
  The curated 8-entry list deliberately includes every layout that `*`
  would have enabled, so the user's existing layout reach via `next_layout`
  is preserved.

## Capabilities

### New Capabilities
(none)

### Modified Capabilities

- `kitty-curated-bindings`: extends with one MODIFIED Requirement
  ("Curated catalog covers six categories" → "covers seven categories",
  with `layout` added to the bullet list and scenarios updated to mention
  `layout.conf`), and one ADDED Requirement ("Layout orientation chord")
  defining the chord, the required `enabled_layouts` directive, payload
  file shape, and macOS parity.

No `kitty-config-management` delta needed — the generic "Payload lives
under our own subdirectory" requirement already covers any per-topic
`*.conf` we add. No `my-kitty-cli` delta — no CLI surface change. No
`kitty-scenes` delta — this is a chord binding, not a runtime scene
primitive. No new doctor check; the existing `parse check` validates the
new `map` line + `enabled_layouts` directive parse, and the `bindings`
check already accounts for the new category.

## Impact

- Config payload: `config/kitty/layout.conf` (new — contains a curated
  `enabled_layouts tall,tall:mirrored=true,fat,grid,horizontal,vertical,splits,stack`
  directive AND one `map ctrl+shift+m goto_layout tall:mirrored=true`
  binding. The chord works identically on Linux and macOS via the
  `kitty_mod ctrl+shift` pin in `kitty-setup.conf`; no OS-conditional
  branching needed).
- Config payload: `config/kitty/kitty-setup.conf` (+ `include layout.conf`
  line).
- Config payload: `config/kitty/windowing.conf` (header comment edit ONLY
  — replace the "we deliberately do NOT pin `enabled_layouts splits`"
  paragraph with a one-line "see `layout.conf` for the curated
  `enabled_layouts` directive (Phase 2 §11)." No directive or map-line
  changes.).
- Tests: `tests/integration/test_h24_layout_mirrored.py` (new, raw
  subprocess pattern, promoted from `tmp/h24-tall-mirrored-right/run.py` —
  ~4 named tests covering Phase B `expected.json` behaviour against the
  promoted `layout.conf` directive, gated on `KITTI_INTEGRATION=1`).
- Tests: extension of `tests/unit/test_binding_introspection.py` (extends
  the existing per-source-grouping pattern — assert `my-kitty keys`
  reports a `layout` source group with exactly one binding routing to
  `goto_layout tall:mirrored=true`).
- Docs: `docs/repro/h24-bindings-layout.md` (new manual repro per
  `kitty-curated-bindings`'s "Linux-first delivery, macOS-deferred-with-note"
  contract).
- Hypothesis scratch: `tmp/h24-tall-mirrored-right/` (already green;
  deleted at archive).
- Dependencies: none added. No new kitten verbs, no new CLI surfaces.
- Runtime surface: one new chord + one curated `enabled_layouts`
  directive that lengthens the `next_layout` cycle by exactly one entry
  (the mirrored variant).
- Risk: low-to-medium. The mechanism is config-only (an `enabled_layouts`
  directive + a `map` line + an include); the wire format is grounded by
  h24's probe Phase B (`expected.json` `B_layout_after_goto_tall_mirrored_after_cycle`
  is `"tall:bias=50;full_size=1;mirrored=y"` and
  `B_geometry_after_mirrored.main_pane_has_left_neighbors` is `true`). The
  cycle-length change (7 → 8) is a deliberate, documented trade-off; the
  alternative — no pinning — was empirically shown to silently fail. The
  biggest unknown remaining is macOS rendering of the mirrored layout
  (visual verification deferred under the existing
  `macOS-deferred-with-note` contract).

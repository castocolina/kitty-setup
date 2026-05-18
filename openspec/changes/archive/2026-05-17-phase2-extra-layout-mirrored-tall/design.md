# Design — phase2-extra-layout-mirrored-tall

## Context

`phase1-curated-bindings` (archived) established the six-category catalog
under `~/.config/kitty/kitty-setup/`: `tab-nav.conf`, `window-nav.conf`,
`font-zoom.conf`, `detach.conf`, `broadcast.conf`, `url-hints.conf`. Each
file ships a focused set of chords; each chord is authored with the
explicit `ctrl+shift+<key>` form (per the catalog requirement); each
shadow of a kitty default is allow-listed in `intentional-overrides.conf`.

Phase 2 §11 of `docs/requirements.md` (and roadmap line 41) asks for one
extra layout orientation beyond kitty defaults. The h24 probe
(`tmp/h24-tall-mirrored-right/run.py`) is green against kitty 0.46.2 on
the user's daily host (Pop!_OS 24.04 + COSMIC), and grounded every spec
claim below.

Inputs to this design:

- `docs/requirements.md` §11 ("Provide one extra layout orientation
  beyond Kitty defaults").
- `docs/propossal_roadmap.md` line 41 ("Add one extra layout orientation").
- `openspec/specs/kitty-curated-bindings/spec.md` (existing; gets one
  MODIFIED + one ADDED Requirement).
- Probe findings under `tmp/h24-tall-mirrored-right/expected.json` and
  `repro.md`.
- Kitty's official `docs/layouts.rst` (confirmed via context7): the Tall
  layout accepts `bias`, `full_size`, and `mirrored` options; "`mirrored`
  shifts the full-height windows to the right."

The /review-spec iter-3 reviewer caught a load-bearing flaw in the prior
"no pinning" design: kitten's `goto-layout tall:mirrored=true` exits 0
even when the option is silently ignored, so exit-code success was
mistaken for option success. The probe data records BOTH the success
exit code AND the actual `layout_opts.mirrored` value (`"n"` in Phase A
without pinning; `"y"` in Phase B with pinning), and the correct
interpretation is the one captured by Phase B. This design is rebuilt
around that ground truth.

## Goals / Non-Goals

**Goals:**

- Ship one chord (`ctrl+shift+m`) that takes the user from the default
  3-pane Tall layout (full-height pane on the left) to the mirrored
  variant (full-height pane on the right), with the option actually
  applied (`layout_opts.mirrored == "y"`).
- Preserve the user's existing layout reach: every base layout
  reachable today via `next_layout` (the 7 layouts that `*` enables)
  SHALL remain reachable after this change. The curated `enabled_layouts`
  list is a SUPERSET of `*` plus the mirrored variant.
- Honour the existing `kitty-curated-bindings` discipline: per-topic
  payload file, explicit-modifier `map` line, Linux-verified repro doc
  with macOS deferred-with-note.
- Promote the h24 probe to an integration test that re-runs in CI when
  `KITTI_INTEGRATION=1`. Delete the probe before archive.

**Non-Goals:**

- A toggle pair (one chord to mirrored, another back). The user picked
  Shape A during /opsx:explore. Trading one chord slot for the ability
  to invert the layout in one keystroke wasn't worth it for their
  workflow.
- A `my-kitty` CLI subcommand for runtime layout switching. Phase 2 §13
  (named scenes) is the right home for composed layout+style switches;
  exposing a `my-kitty layout …` surface here would conflate primitive
  and composition.
- Other layout chords (no `ctrl+shift+g` for grid, no `ctrl+shift+s` for
  stack, etc.). §11 says "one extra"; this change ships one.
- `enabled_layouts` pinned to a curated SUBSET (e.g. just
  `tall,tall:mirrored=true`). That would remove fat, grid, horizontal,
  vertical, splits, stack from `next_layout`'s reach. The curated
  8-entry list explicitly preserves all of them.
- macOS visual verification. Deferred-with-reason under the existing
  `kitty-curated-bindings` "Linux-first delivery, macOS-deferred-with-note"
  requirement.

## Decisions

### D1: Single direct-jump chord, not a toggle pair

Final CLI surface (one new chord, no companion):

```
ctrl+shift+m  →  goto_layout tall:mirrored=true
```

The user's mental model from /opsx:explore: "one pane should be full
height on the right." A single chord that takes you there is the
load-bearing affordance. The return path (back to default Tall) uses
the existing `ctrl+shift+l` (`next_layout`) workflow, which now cycles
through 8 entries (see D2). The user accepted this trade-off as part of
choosing Shape A.

Alternatives considered:

- **Toggle pair** (`ctrl+shift+m` to mirror, `ctrl+shift+alt+m` to revert)
  — rejected by the user during explore.
- **Self-toggling chord** (one chord that conditionally goes to mirrored
  or back to plain based on current state). kitty has `last_used_layout`
  but it's history-dependent, not state-dependent. Rejected as too
  magical.

### D2: Curated `enabled_layouts` pinning is REQUIRED (probe-grounded)

Probe Phase A (vanilla `enabled_layouts *`) and Phase B (curated pin)
together establish the load-bearing finding:

| Phase | enabled_layouts | After `kitten @ goto-layout tall:mirrored=true` |
|---|---|---|
| A | `*` (default) | exit 0, empty stderr, BUT `layout_opts.mirrored == "n"` and main pane on the LEFT. Option silently ignored. |
| B | `tall,tall:mirrored=true,fat,grid,horizontal,vertical,splits,stack` (the 8-entry shipped list) | exit 0, empty stderr, `layout_opts.mirrored == "y"`, main pane on the RIGHT. Option applied. The full `next_layout` cycle from initial `tall` visits `tall:mirrored=y`, `fat`, `grid`, `horizontal`, `vertical`, `splits`, `stack`, then wraps to `tall:mirrored=n` — 8 entries in list order. |

The chord only does what the user wants when the enabled-layouts list
explicitly carries the option-bearing variant. So this change pins
`enabled_layouts` to a curated 8-entry list:

```
enabled_layouts tall,tall:mirrored=true,fat,grid,horizontal,vertical,splits,stack
```

That list is a strict superset of what kitty's default `*` would have
enabled (the 7 base layouts), plus `tall:mirrored=true`. The user's
existing layout reach via `next_layout` is preserved; only the cycle
length changes (7 → 8 entries).

The previously-undocumented "we deliberately do NOT pin
`enabled_layouts`" comment in `config/kitty/windowing.conf:7-11` was
written before this change existed and predates the empirical
verification that pinning is unavoidable for `tall:mirrored=true`. The
windowing.conf comment SHALL be updated to point at `layout.conf` for
the new directive (a one-line comment edit; no semantic change to the
windowing bindings themselves).

Alternatives considered:

- **Pin to a subset** (e.g. `tall,tall:mirrored=true,splits,stack`) —
  smaller cycle, but removes fat, grid, horizontal, vertical from
  `next_layout`'s reach. Rejected because preserving the existing
  7-layout reach is a goal. (An earlier draft of the h24 probe
  exercised this subset; the probe has since been updated to the shipped
  8-entry list and re-run green.)
- **Add `tall:mirrored=true` to enabled_layouts AND keep `*`**
  (`enabled_layouts *,tall:mirrored=true`) — would be the cleanest if
  kitty accepted it, but per kitty's docs `*` and explicit entries are
  not composable in a single directive. The curated 8-entry list is the
  equivalent expansion.
- **Don't pin and accept that the chord silently fails** — rejected;
  defeats the load-bearing user-visible goal.

### D3: Payload file `layout.conf` follows the per-category pattern

The existing six payload files map 1:1 to "binding categories" reported
by `my-kitty keys`. Adding `layout.conf` adds a seventh category. The
file ships the `enabled_layouts` directive AND one `map` line:

```
# config/kitty/layout.conf — Phase 2 §11.
#
# Owner: phase2-extra-layout-mirrored-tall, kitty-curated-bindings.
# Ships one direct-jump chord to the mirrored Tall layout (main pane
# on the right), plus the curated `enabled_layouts` directive REQUIRED
# for `goto_layout tall:mirrored=true` to actually apply the mirror
# option (empirically verified — see tmp/h24-tall-mirrored-right/repro.md).
#
# The enabled_layouts list is a strict superset of what kitty's default
# `*` enables (all 7 base layouts) plus `tall:mirrored=true`. Side
# effect: `ctrl+shift+l` (next_layout) cycles through 8 entries instead
# of 7; the mirrored variant appears as a step immediately after plain
# `tall`. The return path from mirrored to plain Tall is multi-keystroke
# (cycle via `ctrl+shift+l`).

enabled_layouts tall,tall:mirrored=true,fat,grid,horizontal,vertical,splits,stack
map ctrl+shift+m goto_layout tall:mirrored=true
```

Authored with the explicit `ctrl+shift+m` chord form per the catalog
requirement ("no `kitty_mod+` shorthand"); works identically on macOS
via the `kitty_mod ctrl+shift` pin in `kitty-setup.conf`.

`kitty-setup.conf` adds `include layout.conf` after the existing
`include dynamic-opacity.conf` line.

Alternatives considered:

- **Split the directive and the map line across two files** (e.g.
  `enabled-layouts.conf` + `layout.conf`) — over-decomposition. Both
  pieces are required together for the chord to function; separating
  them invites future readers to remove one without understanding the
  coupling.
- **Append to `windowing.conf`** — would make `my-kitty keys` report
  the layout chord under the `windowing` category, violating the
  catalog's per-file-per-category contract.

### D4: No `intentional-overrides.conf` entry — chord is not a shadow

Probe-adjacent verification: `my-kitty keys 2>&1 | grep 'ctrl+shift+m'`
returned empty against the current install. `ctrl+shift+m` is NOT a
kitty default and NOT bound by any of our six existing category files.

Per the catalog requirement: "Each chord that shadows a kitty default
SHALL be present in `intentional-overrides.conf`." Since this chord
shadows nothing, no entry is required, and `my-kitty keys` will
continue to report `0 conflicts` post-install. Tasks include an
explicit verification step (`grep` returns empty against
`intentional-overrides.conf`).

### D5: Probe → integration test promotion (Phase B-aligned)

`tmp/h24-tall-mirrored-right/run.py` Phase B is the load-bearing
behavioural claim of this change. Promotion lands as
`tests/integration/test_h24_layout_mirrored.py` (gated on
`KITTI_INTEGRATION=1`), importing helpers from the shared
`tests/integration/_kitty_subprocess.py` that h22 + h23 already use.

Mapping (probe Phase B → integration test):

| Probe assertion(s) | Test name |
|---|---|
| `B_initial_layout`, `B_goto_tall_ok`, `B_layout_after_goto_tall` | `test_curated_enabled_layouts_initial_state_is_plain_tall` |
| `B_goto_tall_mirrored_after_cycle_ok` + `B_layout_after_goto_tall_mirrored_after_cycle == "tall:bias=50;full_size=1;mirrored=y"` | `test_goto_layout_tall_mirrored_true_applies_option_with_curated_pin` |
| `B_geometry_after_mirrored.main_pane_has_left_neighbors: true`, `…has_right_neighbors: false` | `test_mirrored_tall_puts_main_pane_on_right_with_curated_pin` |
| `B_next_layout_sequence` (4 unique signatures including both `tall` variants) | `test_curated_enabled_layouts_cycle_includes_mirrored_variant` |

Phase A's vanilla-config behaviour (the empirical evidence that
unpinned `enabled_layouts` silently fails the option) is recorded in
the repro doc's Attempted-Alternatives section as documentation, NOT as
an integration test — shipping a test that exercises the rejected
configuration would create maintenance surface for behaviour the change
deliberately does not ship.

Unit tests cover the catalog seventh-category contract:
`my-kitty keys` reports a `layout` section after install with exactly
one binding routing to `goto_layout tall:mirrored=true`. Extension of
`tests/unit/test_binding_introspection.py` (which already covers
per-source grouping; reusing the established pattern).

### D6: macOS deferred-with-reason

Per `kitty-curated-bindings` "Linux-first delivery,
macOS-deferred-with-note": `docs/repro/h24-bindings-layout.md` ships
with `## Linux Status` = `verified (date, host)` after user manual
sign-off in apply §verify, and `## macOS Status` = `deferred` with the
note: "no Mac host available; kitten verb `goto-layout` is
platform-agnostic; the rendered layout's visual fidelity (anti-aliasing
at the divider, transition animation) is the only macOS-specific
concern." Tracked under follow-up `phase2-extra-layout-mirrored-tall-macos`.

## Risks / Trade-offs

- **`next_layout` cycle grows from 7 to 8 entries**. The mirrored Tall
  variant appears as a step in the cycle immediately after plain
  `tall`. Users with muscle memory for "exactly 7 cycle steps" will
  notice the change. → Mitigation: documented in
  `docs/repro/h24-bindings-layout.md` Known Limitations + `layout.conf`
  header comment. The alternative — no pinning — was empirically shown
  to silently fail. The cycle-length cost is the actual cost of
  shipping §11.
- **Return path from mirrored back to plain Tall is multi-keystroke**.
  To return to default Tall after invoking `ctrl+shift+m`, the user
  cycles via `ctrl+shift+l` through 6-7 other layouts before landing on
  plain `tall`. → Mitigation: documented as a known trade-off of Shape A.
  If usage shows this is friction, a Phase 2 follow-up can add the
  toggle-back chord.
- **`mirrored` option value is string `"y"`/`"n"`, not boolean** in
  `kitten @ ls`. Probe-grounded. → Mitigation: codified in the
  integration test (any future test that reads `layout_opts["mirrored"]`
  must compare against `"y"` or use a truthy helper).
- **`kitten @ ls` does NOT expose pixel geometry**. The only programmatic
  signal for "which side the main pane is on" is `window["neighbors"]`.
  → Mitigation: D5's test uses neighbor structure (main has left
  neighbors → mirrored; right neighbors → plain). Codified.
- **windowing.conf header comment edit may surprise future readers**.
  The "we deliberately do NOT pin enabled_layouts" comment in
  windowing.conf becomes stale with this change. → Mitigation: the
  comment edit (proposal Impact section) updates the language to
  acknowledge the layout.conf directive. No bindings change in
  windowing.conf.
- **Kitty defaults may bind `ctrl+shift+m` in a future release**. If
  upstream kitty adds a default action for that chord, our binding
  becomes a shadow and must move to `intentional-overrides.conf`.
  → Mitigation: `make doctor` would catch it via the bindings check.
- **macOS visual fidelity unverified**. → Mitigation: deferred per D6.
- **Exit code success ≠ option success on `goto-layout`**. The reviewer
  caught this with the iter-3 probe re-read; the design is now built on
  the actual `layout_opts` observable, not the exit code. → Mitigation:
  recorded as a feedback-memory item for future probes — when a kitten
  call's "did it work" semantics span multiple observables, every
  observable must be checked, not just exit code + stderr.

## Migration Plan

No migration. The change adds one new file under the managed payload,
one include line in `kitty-setup.conf`, and one comment edit in
`windowing.conf`. The user's existing layout behaviour is unchanged
until they hit the new chord (or until they next cycle layouts and
notice the extra step). Rollback is `make uninstall` (removes the
payload file along with the rest); the chord binding + the
`enabled_layouts` directive disappear with the umbrella.

## Open Questions

- **Should the `enabled_layouts` order list `tall:mirrored=true` adjacent
  to `tall` or somewhere else in the cycle?** The proposed order
  (`tall,tall:mirrored=true,fat,…`) places mirrored immediately after
  plain `tall` so cycling reveals the variant as a related-to-tall step.
  Tentative answer: keep adjacent. If user feedback wants mirrored further
  away in the cycle (so `next_layout` from plain tall lands on `fat`),
  reorder in a small follow-up.
- **Should `layout.conf` ship a comment placeholder for future layout
  chords**? Tentative answer: no — YAGNI. The single chord + the
  `enabled_layouts` directive are what's needed.

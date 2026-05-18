# H24 — Layout orientation chord: mirrored Tall

**Capability:** kitty-curated-bindings (Phase 2 §11).

**Status:** Promoted. Implementation in
[`config/kitty/layout.conf`](../../config/kitty/layout.conf) (curated
`enabled_layouts` directive + one chord binding). Integration tests under
[`tests/integration/test_h24_layout_mirrored.py`](../../tests/integration/test_h24_layout_mirrored.py).
Unit tests extend `tests/unit/test_binding_introspection.py` to cover the
new `layout` source group.

## Why

Phase 2 §11 of `docs/requirements.md` asks for one extra layout orientation
beyond kitty defaults. User goal (from /opsx:explore): with 3 panes in one OS
window, ONE pane is full-height on the RIGHT, the other two stacked top/bottom
on the LEFT. The mechanism is kitty's Tall layout with the `mirrored` option:
upstream's `docs/layouts.rst` describes it as "shifts the full-height
windows to the right."

The wire-level question — "does `kitten @ goto-layout tall:mirrored=true`
work as a one-shot target?" — was answered by `tmp/h24-tall-mirrored-right/run.py`
(green against kitty 0.46.2 on the user's daily host). Two probe findings
forced a load-bearing design pivot:

1. **Exit-code success is not option success.** With `enabled_layouts *`
   (kitty default), the kitten call exits 0 with empty stderr but the
   `mirrored` option is SILENTLY IGNORED — `tabs[0].layout_opts.mirrored`
   stays `"n"` and the main pane stays on the LEFT. The probe records this
   as Phase A.
2. **A curated `enabled_layouts` directive that explicitly lists
   `tall:mirrored=true` makes the option apply.** Phase B of the probe
   exercises the shipped 8-entry list and verifies `mirrored == "y"` plus
   main-pane-on-the-right via `window["neighbors"]`.

The shipped change pins `enabled_layouts` to a strict superset of kitty's
default `*` (the 7 base layouts) plus `tall:mirrored=true`, so the user's
existing `next_layout` reach is preserved; the cycle simply grows from 7 to
8 entries.

## Manual repro

1. `make install` to ship `~/.config/kitty/kitty-setup/layout.conf` and the
   `include layout.conf` line in `kitty-setup.conf`.
2. Open a kitty window. Press `ctrl+shift+enter` twice to launch two more
   panes — three total.
3. Press `ctrl+shift+m`. Observe: one pane spans the full height of the
   window and sits on the RIGHT; the other two are stacked top/bottom on
   the LEFT.
4. To return to plain Tall, cycle with `ctrl+shift+l` (kitty's default
   `next_layout`). The cycle now has 8 entries (plain `tall`, mirrored
   `tall`, `fat`, `grid`, `horizontal`, `vertical`, `splits`, `stack`);
   the mirrored variant appears as the second step from plain Tall.
5. Confirm via `kitten @ ls`: `tabs[0].layout` is `"tall"` for both
   orientations; `tabs[0].layout_opts.mirrored` is `"y"` after the chord
   and `"n"` after the cycle returns to plain Tall.

## Linux Status

`verified (2026-05-17, Pop!_OS 24.04 + COSMIC + kitty 0.46.2)` — user
confirmed: with 3 panes and `ctrl+shift+m`, the full-height pane lands on
the right and the other two stack on the left; the `next_layout` cycle
now has 8 entries and the mirrored variant appears as the step immediately
after plain Tall.

## macOS Status

`deferred-with-reason` — no Mac host available. `kitten @ goto-layout` is
platform-agnostic; the rendered layout's visual fidelity (divider
anti-aliasing, transition animation) is the only macOS-specific concern.
Tracked under follow-up `phase2-extra-layout-mirrored-tall-macos`.

## Attempted alternatives

| Approach | Status | Why rejected |
|---|---|---|
| No `enabled_layouts` pinning; rely on kitty's default `*` | Rejected | Phase A of the h24 probe empirically demonstrated that `kitten @ goto-layout tall:mirrored=true` exits 0 with empty stderr but the option is silently ignored — `layout_opts.mirrored` stays `"n"`. The chord becomes a no-op. |
| Toggle pair (`ctrl+shift+m` to mirror, `ctrl+shift+alt+m` to revert) | Rejected | User chose single-chord Shape A during /opsx:explore. Trading a chord slot for one-keystroke inversion was not worth it for their workflow. |
| Pin to a curated SUBSET (e.g. `tall,tall:mirrored=true,splits,stack`) | Rejected | Would remove `fat`, `grid`, `horizontal`, `vertical` from `next_layout`'s reach. Preserving the existing 7-layout reach is a stated goal. |
| Append the directive + map line to `windowing.conf` | Rejected | Violates the catalog's per-file-per-category contract — `my-kitty keys` would report the chord under the `windowing` category instead of giving it its own `layout` group. |

## Known limitations

- The `next_layout` cycle is now 8 entries instead of 7. The mirrored Tall
  variant appears as a step immediately after plain `tall`. Users with
  muscle memory for "exactly 7 cycle steps" will notice the change.
- The return path from mirrored Tall back to plain Tall is multi-keystroke
  — there is no inverse chord; cycle via `ctrl+shift+l` through the other
  layouts until plain `tall` is reached again.
- Kitty exposes the `mirrored` option as the STRING `"y"` or `"n"` in
  `kitten @ ls`, NOT a boolean. Any code that reads
  `layout_opts["mirrored"]` must compare against `"y"` (or use a truthy
  helper).
- `kitten @ ls` (kitty 0.46.2) does NOT expose pixel geometry — `at_x`,
  `geometry`, etc. are `null`. The only reliable observable for
  "which side is the main pane on" is `window["neighbors"]`: in mirrored
  mode, the main pane has `neighbors.left` populated and `neighbors.right`
  empty; in plain mode, the inverse.
- The chord's exit code does NOT reflect whether the mirror option was
  applied. Phase A success ≠ option success; any future assertion of
  "the user is in mirrored mode" must read `layout_opts.mirrored`, not
  the kitten exit code.

## Recipes

### Invoke the chord from a non-kitty shell

```bash
alias kl-mir='kitten @ goto-layout tall:mirrored=true'
```

Useful when scripting layout switches from a non-kitty context (e.g. a
COSMIC keybinding or a launcher). Pairs with `$KITTY_LISTEN_ON` auto-
discovery or an explicit `--to=unix:/tmp/kitty-<pid>`.

### Compose with h22's title primitive

```bash
my-kitty tab title "🔍 review" && kitten @ goto-layout tall:mirrored=true
```

Sets a curated tab title, then drops into the right-handed reviewing
layout in one composed command. Once Phase 2 §14 (chord-to-scene) ships,
this composition becomes a single chord.

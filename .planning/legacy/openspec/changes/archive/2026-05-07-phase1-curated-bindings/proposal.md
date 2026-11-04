## Why

Phase 1 §5 of `docs/requirements.md` calls for a curated keybinding set, conflict-free, identical on Linux and macOS, covering at minimum tabs, windows/splits, vim-style window navigation, font zoom, detach, broadcast, and URL hints. Today the payload only ships the cwd-inheriting creators (`windowing.conf`) and instant-clear (`bindings.conf`) — five chords total. The roadmap blocks Phase 2 (scenes) on Phase 1 being dogfooded standalone, and the current set is too thin to dogfood as a daily driver. Without curated navigation/zoom/detach/broadcast/hints chords, the user falls back to kitty defaults — some of which we already silently shadow (the `ctrl+shift+-` collision history) and several of which differ unhelpfully between Linux and macOS keyboards.

## What Changes

- Add a curated set of bindings across six categories, all under the pinned `kitty_mod ctrl+shift` modifier so the chord style is **literally identical on Linux and macOS** (no `cmd` remap, no per-OS divergence). Categories:
  - **tab navigation**: next, prev, move-left, move-right, close-tab.
  - **window/split navigation**: vim `h/j/k/l` via `neighboring_window`, close-window, focus-cycle.
  - **font zoom**: `change_font_size +/-/0` (reset).
  - **detach**: `detach_window` and `detach_tab` to a new target.
  - **broadcast**: send-input across all windows in the active tab.
  - **url hints**: `open_url_with_hints`.
- Split bindings into per-category `.conf` files under `config/kitty/` so the file-basename = category convention used by `my-kitty keys` continues to make the catalog legible. Existing `bindings.conf` (instant clear) is renamed/split accordingly so every category stands alone.
- Extend `intentional-overrides.conf` to allow-list every new chord that shadows a kitty default, with a one-line reason per entry. Any unlisted shadow fails `make doctor`.
- Pin `kitty_mod ctrl+shift` once, in the top-level managed entry (`kitty-setup.conf`), so the curated chords resolve identically on both OSes regardless of kitty's per-OS default modifier.
- Each subgroup ships as its own hypothesis under `tmp/h<NN>-bindings-<subgroup>/` with an autonomous probe (`KITTI_INTEGRATION=1`) that asserts the binding is registered, has the expected action, and is reported in the right category by `my-kitty keys`. Manual repro doc per subgroup under `docs/repro/`.
- Linux is the first-class target. Each subgroup's repro doc carries a **macOS Status** section: either "verified" or "deferred — <reason>". Deferred subgroups still ship; the doc records the open question.

## Capabilities

### New Capabilities

- `kitty-curated-bindings`: the behavioral contract for the curated chord catalog. Specifies the categories that MUST be bound, the modifier-pinning rule (`kitty_mod ctrl+shift`), the cross-OS parity requirement (literal chord identity), the file-per-category layout, and the override-justification rule. Backed by per-subgroup integration probes and a single umbrella catalog test.

### Modified Capabilities

- `kitty-instant-clear`: the requirement that ties the clear behavior to `config/kitty/bindings.conf` MUST relax to allow delivery from any category file under the curated catalog (most likely `clear.conf` after the file-per-category split). The instant-clear *chord* SHALL also move off `ctrl+shift+k`, freeing that chord for the vim-style "focus window up" binding required by Phase 1 §5. Behavior — single keystroke clears screen + scrollback, no shell hook — is unchanged.
- `kitty-binding-introspection`: the "distinguish intentional overrides from real conflicts" requirement MUST recognize same-`(chord, action)` redundant rebinds as overrides, not as self-collisions. Required because kitty's parsed keymap returns the upstream default and our redundant rebind as two distinct `defs[]` entries with identical action, which the original conflict rule misclassified as "two of ours" before the allow-list check could fire.

`kitty-config-management` and `kitty-cwd-inheritance` are NOT modified at the requirement level. The former already generalises over arbitrary per-topic `*.conf` files and file-basename categorisation. The latter pins behavior, not chord choice — so moving the horizontal-split chord off `ctrl+shift+-` (to free that chord for the kitty default `change_font_size all -2.0`, as required by §5 font zoom) is an implementation detail of this change. That move also discharges the silent regression flagged in the archived `phase1-binding-introspection` proposal (its planned follow-up `fix-ctrl-shift-minus-collision` is folded in here).

## Impact

- **New top-level paths**: `config/kitty/tab-nav.conf`, `config/kitty/window-nav.conf`, `config/kitty/font-zoom.conf`, `config/kitty/detach.conf`, `config/kitty/broadcast.conf`, `config/kitty/url-hints.conf`. One `tmp/h<NN>-bindings-<subgroup>/` hypothesis dir per category; one `docs/repro/h<NN>-bindings-<subgroup>.md` per category. Per-subgroup integration tests under `tests/integration/test_h<NN>_bindings_<subgroup>.py`.
- **Edited files**: `config/kitty/kitty-setup.conf` (pin `kitty_mod`; add new `include` lines), `config/kitty/intentional-overrides.conf` (add allow-list entries with reasons), `config/kitty/bindings.conf` (kept for instant-clear only, or merged into a renamed `clear.conf` — design decision). No CLI surface changes; `my-kitty keys` already enumerates whatever the payload contains.
- **System mutations**: install copies the additional `.conf` files into the managed dir; uninstall removes them via the same surgical-removal contract. No new dependencies, no new `[project.scripts]` entries.
- **Out of scope**: paste preservation (Phase 1 §4), suspend/monitor survival (§6), image-paste parity (§7), and Phase 2 scenes. Also out of scope: a global rebind of all kitty defaults — only the categories listed above are touched.

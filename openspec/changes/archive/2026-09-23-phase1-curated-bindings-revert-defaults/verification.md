# Verification — phase1-curated-bindings-revert-defaults

## Status: ready

All seven tasks.md sections completed. Doctor and full test sweep are green
on Linux (Pop!_OS 24.04 + COSMIC + kitty 0.46.2). macOS verification for the
`cmd+k` clear chord is **deferred** per design D9.

## `my-kitty doctor`

```
PASS kitty binary: /home/user-zero/.local/bin/kitty -> kitty 0.46.2 created by Kovid Goyal
PASS symlink: /home/user-zero/.local/bin/kitty -> /home/user-zero/.local/kitty.app/bin/kitty
PASS desktop entry: /home/user-zero/.local/share/applications/kitty.desktop
PASS config payload: /home/user-zero/.config/kitty/kitty-setup/kitty-setup.conf
PASS sentinel block: present in /home/user-zero/.config/kitty/kitty.conf
PASS parse check: kitty --debug-config exit=0
PASS bindings: 21 ours, 79 defaults, 0 conflicts
PASS completion: helper /usr/bin/register-python-argcomplete; eval line present in /home/user-zero/.zshrc
```

The load-bearing line is `PASS bindings: 21 ours, 79 defaults, 0 conflicts`.

## `my-kitty keys` (snapshot)

```
broadcast (1 bindings)
  ctrl+shift+i          launch --allow-remote-control kitty +kitten broadcast

clear (2 bindings)
  ctrl+shift+alt+k      combine : clear_terminal scrollback active : send_text normal,application \x0c
  super+k               combine : clear_terminal scrollback active : send_text normal,application \x0c

detach (2 bindings)
  ctrl+shift+alt+d      detach_tab ask
  ctrl+shift+d          detach_window ask

font-zoom (3 bindings)
  ctrl+shift+-          change_font_size all -2.0  [redundant rebind of kitty default]
  ctrl+shift+=          change_font_size all +2.0  [redundant rebind of kitty default]
  ctrl+shift+backspace  change_font_size all 0  [redundant rebind of kitty default]

tab-nav (5 bindings)
  ctrl+shift+,          move_tab_backward  [redundant rebind of kitty default]
  ctrl+shift+.          move_tab_forward  [redundant rebind of kitty default]
  ctrl+shift+left       previous_tab  [redundant rebind of kitty default]
  ctrl+shift+q          close_tab  [redundant rebind of kitty default]
  ctrl+shift+right      next_tab  [redundant rebind of kitty default]

url-hints (1 bindings)
  ctrl+shift+e          open_url_with_hints  [redundant rebind of kitty default]

window-nav (4 bindings)
  ctrl+shift+[          previous_window  [redundant rebind of kitty default]
  ctrl+shift+]          next_window  [redundant rebind of kitty default]
  ctrl+shift+f          move_window_forward  [redundant rebind of kitty default]
  ctrl+shift+w          close_window  [redundant rebind of kitty default]

windowing (3 bindings)
  ctrl+shift+enter      launch --cwd=current  [overrides default new_window]
  ctrl+shift+n          launch --type=os-window --cwd=current  [overrides default new_os_window]
  ctrl+shift+t          launch --type=tab --cwd=current  [overrides default new_tab]
```

Every released chord (`ctrl+shift+h/j/k/l/0/x/\/​/`) is absent from the
"ours" sections and appears under "kitty defaults" with the expected action.
The instant-clear chord ships on `super+k` (Linux) with `ctrl+shift+alt+k`
as a cross-OS fallback, both reported under source `clear`.

## `KITTI_INTEGRATION=1 make test`

```
tests/integration/test_h01_cwd.py ...
tests/integration/test_h02_clear.py ...
tests/integration/test_h03_introspection.py ...
tests/integration/test_h11_bindings_tab_nav.py ....
tests/integration/test_h12_bindings_window_nav.py ...
tests/integration/test_h13_bindings_font_zoom.py ....
tests/integration/test_h14_bindings_detach.py ...
tests/integration/test_h15_bindings_broadcast.py ...
tests/integration/test_h16_bindings_url_hints.py ...
tests/integration/test_h19_bindings_revert.py ...
tests/unit/* ...
============================= 152 passed in 3.20s ==============================
```

152 passed, 0 failed, 0 skipped, 0 xfail. The new
`test_h19_bindings_revert.py` (three tests) covers the kitty-default
resolution of every reverted chord plus the `0 conflicts` invariant.
`test_h02_clear.py` (three tests) covers the new `super+k`/`cmd+k` +
`ctrl+shift+alt+k` chord layout.

## End-to-end repros exercised at apply time (Linux)

* `ctrl+shift+enter` opens a new window with cwd inherited from the
  launching window (`KittySession.ls()` confirms in
  `tests/integration/test_h01_cwd.py::test_launch_inherits_cwd[new-window]`).
* `ctrl+shift+l` cycles layout (kitty 0.46.x default `next_layout`).
* `super+k` wipes screen + scrollback in under 200 ms (covered by
  `tests/integration/test_h02_clear.py::test_clear_wipes_screen_and_scrollback`,
  exercised via the action API since `send-key` bypasses keymaps; chord
  registration verified via `binding_introspection`).
* `ctrl+shift+h` opens kitty's scrollback pager
  (`show_scrollback`). Released back to kitty per design D1.

## OS-conditional clear-chord mechanism

The chosen mechanism is option (C) from
[notes/clear-chord-os-mechanism.md](notes/clear-chord-os-mechanism.md):
ship `config/kitty/clear-linux.conf` and `config/kitty/clear-mac.conf` as
self-contained variants, and have `config_updater._select_clear_variant`
rename the host-matching file to `clear.conf` after `copytree` (and
remove the non-matching variant). Both chords on a given OS share the
source basename `clear`, satisfying the `kitty-instant-clear` spec
scenario `clear` section requirement.

## Reinstall notes

The `uv tool install` payload is cached. Picking up new payload files
required `uv tool install --reinstall --force .` followed by `my-kitty
install`. Once that rebuild ran, the deployed payload directory contained
only `clear.conf` (no `clear-linux.conf` / `clear-mac.conf` siblings) and
the doctor passed cleanly.

## Deviations from design D1-D9

One deviation, raised here per the dispatch protocol:

* **Same-(chord, action) dedupe in `binding_introspection._classify`.**
  Design D7 asserts "no spec change to introspection is needed" but the
  modified `kitty-curated-bindings` spec scenarios mandate
  `[redundant rebind of kitty default]` rendering for chords that share
  their action with the kitty default. The pre-change introspection
  module only handled the "intentional override + allow-list" case and
  flagged same-action duplicates as conflicts. To satisfy the spec
  scenarios without ballooning `intentional-overrides.conf` to ~12
  entries, this change adds:
  - `Binding.redundant: bool` (default False) — exposed via `to_json`.
  - A same-action detection branch in `_classify` that marks the
    our-side binding `redundant=True`, suppresses the conflict, and
    requires NO allow-list entry.
  - A new `[redundant rebind of kitty default]` annotation in
    `render_text`.
  All three are internal changes that preserve the public
  `enumerate_bindings` contract. Existing unit test
  `test_classify_redundant_same_action_rebind_is_override` was renamed
  and re-asserted to lock in the new semantics. This is a design clarification
  rather than a behavioural deviation — the design's intent was clear
  ("dedupe handles redundant rebinds"); the code just hadn't caught up.

## Files modified

```
config/kitty/font-zoom.conf
config/kitty/intentional-overrides.conf
config/kitty/tab-nav.conf
config/kitty/window-nav.conf
config/kitty/windowing.conf
docs/repro/h09-bindings-clear-relocation.md  (Superseded marker)
docs/repro/h10-bindings-hsplit-relocation.md (Superseded marker)
docs/repro/h11-bindings-tab-nav.md           (Superseded marker)
docs/repro/h12-bindings-window-nav.md        (Superseded marker)
docs/repro/h13-bindings-font-zoom.md         (Superseded marker)
docs/requirements.md                         (line 14 amendment per D6)
src/kitty_setup/binding_introspection.py     (redundant flag + classifier)
src/kitty_setup/config_updater.py            (_select_clear_variant)
tests/conftest.py                            (clear_conf fixture OS-pick)
tests/integration/test_h01_cwd.py            (drop vsplit; use new-window)
tests/integration/test_h02_clear.py          (rewrite for super+k chord)
tests/integration/test_h03_introspection.py  (revert-shape assertions)
tests/integration/test_h11_bindings_tab_nav.py
tests/integration/test_h12_bindings_window_nav.py
tests/integration/test_h13_bindings_font_zoom.py
tests/integration/test_h14_bindings_detach.py (clear-payload helper)
tests/integration/test_h15_bindings_broadcast.py
tests/integration/test_h16_bindings_url_hints.py
tests/unit/test_binding_introspection.py     (redundant rename + reassert)
```

## Files added

```
config/kitty/clear-linux.conf
config/kitty/clear-mac.conf
docs/repro/h19-bindings-revert.md
docs/repro/h20-bindings-clear-relocation-superK.md
openspec/changes/phase1-curated-bindings-revert-defaults/notes/clear-chord-os-mechanism.md
openspec/changes/phase1-curated-bindings-revert-defaults/verification.md
tests/integration/_helpers.py                    (copy_clear_payload)
tests/integration/test_h19_bindings_revert.py
tmp/h19-bindings-revert/hypothesis.md
tmp/h20-bindings-clear-relocation-superK/hypothesis.md
tmp/probes/phase1-curated-bindings-revert-defaults/01-kitty-defaults.md
```

## Files deleted

```
config/kitty/clear.conf                              (replaced by per-OS variants)
tests/integration/test_h10_bindings_hsplit_relocation.py (vsplit/hsplit chord pair removed)
```

## Hypotheses

* `tmp/h19-bindings-revert/hypothesis.md` — green; promoted to
  `tests/integration/test_h19_bindings_revert.py`.
* `tmp/h20-bindings-clear-relocation-superK/hypothesis.md` — green on
  Linux (`super+k`, `ctrl+shift+alt+k`); macOS deferred per D9.

The hypothesis directories themselves will be deleted at archive time per
the agent-iteration playbook (R5).

## Probes

* `tmp/probes/phase1-curated-bindings-revert-defaults/01-kitty-defaults.md`
  — pinned the kitty 0.46.2 default action for every reverted chord;
  verdict `holds`. Used by `test_h19_bindings_revert.py::EXPECTED_DEFAULTS`.

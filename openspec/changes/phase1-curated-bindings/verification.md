# phase1-curated-bindings — verification capture

This file captures the verbatim output of the §11 verification gate for the
`phase1-curated-bindings` change. It exists to make the archive note self-contained:
anyone reading the archived change later can confirm the catalog-level invariants
(`24 ours, 79 defaults, 0 conflicts`) without re-running the commands themselves.

Captured: 2026-05-06 on Pop!_OS 24.04, kitty 0.46.2, Python 3.14.3, pytest 9.0.3.

## §11.1 — `make doctor`

```
$ make doctor
PASS kitty binary: /home/user-zero/.local/bin/kitty -> kitty 0.46.2 created by Kovid Goyal
PASS symlink: /home/user-zero/.local/bin/kitty -> /home/user-zero/.local/kitty.app/bin/kitty
PASS desktop entry: /home/user-zero/.local/share/applications/kitty.desktop
PASS config payload: /home/user-zero/.config/kitty/kitty-setup/kitty-setup.conf
PASS sentinel block: present in /home/user-zero/.config/kitty/kitty.conf
PASS parse check: kitty --debug-config exit=0
PASS bindings: 24 ours, 79 defaults, 0 conflicts
PASS completion: helper /usr/bin/register-python-argcomplete; eval line present in /home/user-zero/.zshrc
$ echo $?
0
```

The load-bearing line is `PASS bindings: 24 ours, 79 defaults, 0 conflicts` — that is
the catalog-level invariant declared by `kitty-curated-bindings` (and re-declared by
the `kitty-binding-introspection` doctor check).

## §11.1 — `my-kitty keys` (text, more readable than JSON for archive)

```
$ my-kitty keys
broadcast (1 bindings)
  ctrl+shift+i          launch --allow-remote-control kitty +kitten broadcast

clear (1 bindings)
  ctrl+shift+x          combine : clear_terminal scrollback active : send_text normal,application \x0c  [overrides default scroll_to_prompt 1]

detach (2 bindings)
  ctrl+shift+alt+d      detach_tab ask
  ctrl+shift+d          detach_window ask

font-zoom (3 bindings)
  ctrl+shift+-          change_font_size all -2.0  [overrides default change_font_size all -2.0]
  ctrl+shift+0          change_font_size all 0  [overrides default tenth_window]
  ctrl+shift+=          change_font_size all +2.0  [overrides default change_font_size all +2.0]

tab-nav (5 bindings)
  ctrl+shift+,          move_tab_backward  [overrides default move_tab_backward]
  ctrl+shift+.          move_tab_forward  [overrides default move_tab_forward]
  ctrl+shift+[          previous_tab  [overrides default previous_window]
  ctrl+shift+]          next_tab  [overrides default next_window]
  ctrl+shift+q          close_tab  [overrides default close_tab]

url-hints (1 bindings)
  ctrl+shift+e          open_url_with_hints  [overrides default open_url_with_hints]

window-nav (6 bindings)
  ctrl+shift+f          next_window  [overrides default move_window_forward]
  ctrl+shift+h          neighboring_window left  [overrides default show_scrollback]
  ctrl+shift+j          neighboring_window down  [overrides default scroll_line_down]
  ctrl+shift+k          neighboring_window up  [overrides default scroll_line_up]
  ctrl+shift+l          neighboring_window right  [overrides default next_layout]
  ctrl+shift+w          close_window  [overrides default close_window]

windowing (5 bindings)
  ctrl+shift+/          launch --location=hsplit --cwd=current  [overrides default search_scrollback]
  ctrl+shift+\          launch --location=vsplit --cwd=current
  ctrl+shift+enter      launch --location=after --cwd=current  [overrides default new_window]
  ctrl+shift+n          launch --type=os-window --cwd=current  [overrides default new_os_window]
  ctrl+shift+t          launch --type=tab --cwd=current  [overrides default new_tab]

kitty defaults (79 bindings)
  ... [79 entries elided for archive readability — re-run `my-kitty keys` for the full
       upstream-default listing; counts and the 0-conflicts invariant are doctored above.]

Summary: 24 ours, 79 defaults, 0 conflicts.
```

Eight "ours" sections: `broadcast`, `clear`, `detach`, `font-zoom`, `tab-nav`,
`url-hints`, `window-nav`, `windowing`. Plus `kitty defaults` = nine total source
sections, exactly as required by §10.1 of the tasks list.

`my-kitty keys --json` summary block:

```json
{
  "summary": {
    "ours": 24,
    "defaults": 79,
    "conflicts": 0
  }
}
```

Per-source counts (24 ours total):

| Source       | Count |
| ------------ | ----- |
| windowing    | 5     |
| clear        | 1     |
| tab-nav      | 5     |
| window-nav   | 6     |
| font-zoom    | 3     |
| detach       | 2     |
| broadcast    | 1     |
| url-hints    | 1     |
| **Total**    | **24** |
| kitty-default| 79    |

## §11.1 — `KITTI_INTEGRATION=1 uv run pytest tests/`

```
$ KITTI_INTEGRATION=1 uv run pytest tests/ -q
........................................................................ [ 48%]
........................................................................ [ 96%]
......                                                                   [100%]
150 passed in 4.43s
```

Per-file pass counts:

| File                                                           | Tests |
| -------------------------------------------------------------- | ----- |
| tests/integration/test_h01_cwd.py                              | 3     |
| tests/integration/test_h02_clear.py                            | 3     |
| tests/integration/test_h03_introspection.py                    | 3     |
| tests/integration/test_h10_bindings_hsplit_relocation.py       | 3     |
| tests/integration/test_h11_bindings_tab_nav.py                 | 3     |
| tests/integration/test_h12_bindings_window_nav.py              | 3     |
| tests/integration/test_h13_bindings_font_zoom.py               | 3     |
| tests/integration/test_h14_bindings_detach.py                  | 3     |
| tests/integration/test_h15_bindings_broadcast.py               | 3     |
| tests/integration/test_h16_bindings_url_hints.py               | 3     |
| tests/unit/test_binding_introspection.py                       | 19    |
| tests/unit/test_cli.py                                         | 21    |
| tests/unit/test_config_updater.py                              | 27    |
| tests/unit/test_doctor.py                                      | 12    |
| tests/unit/test_installer_uninstall.py                         | 8     |
| tests/unit/test_path_integration.py                            | 15    |
| tests/unit/test_pruner.py                                      | 18    |
| **Total**                                                      | **150** |
| Failures                                                       | **0** |

## §10.4 — install / uninstall cycle

Verbatim from a fresh cycle on 2026-05-06:

```
$ KITTI_FORCE=1 KEEP_KITTY=1 make uninstall
[uninstall] KITTI_FORCE=1 set; skipping interactive confirm
backups:       nothing to delete under /home/user-zero/.config/kitty/
config:        block removed from /home/user-zero/.config/kitty/kitty.conf
config:        payload directory removed
config:        /home/user-zero/.config/kitty/kitty.conf deleted (no other content)
binary:        the my-kitty binary itself was NOT removed. To remove it:
    uv tool uninstall my-kitty
[uninstall] done

$ ls ~/.config/kitty/kitty-setup/
ls: cannot access '/home/user-zero/.config/kitty/kitty-setup/': No such file or directory

$ my-kitty install
kitty version: kitty 0.46.2 created by Kovid Goyal
kitty.app:     /home/user-zero/.local/kitty.app
symlink:       /home/user-zero/.local/bin/kitty -> /home/user-zero/.local/kitty.app/bin/kitty
desktop entry: /home/user-zero/.local/share/applications/kitty.desktop
status:        kitty already installed; skipped upstream installer
config:        created /home/user-zero/.config/kitty/kitty.conf
PATH:          already configured

$ ls ~/.config/kitty/kitty-setup/
broadcast.conf
clear.conf
detach.conf
font-zoom.conf
intentional-overrides.conf
kitty-setup.conf
tab-nav.conf
url-hints.conf
windowing.conf
window-nav.conf
```

Surgical-removal contract verified: every category file was removed by uninstall, and
every category file (`broadcast.conf`, `clear.conf`, `detach.conf`, `font-zoom.conf`,
`tab-nav.conf`, `url-hints.conf`, `windowing.conf`, `window-nav.conf`) was created by
install — plus the `intentional-overrides.conf` allow-list and the `kitty-setup.conf`
managed entry.

**Caveat (uv-tool-install caching paper-cut, prior implementers):** the cycle above was
run with `KEEP_KITTY=1` to skip the kitty-binary leg; a true cold install with no kitty
binary on disk would also re-download the kitty tarball from upstream and re-install
into `~/.local/kitty.app`. That leg is exercised by `tools/setup.sh` and is unchanged
by this proposal. The end-state is verified for the config-payload and bindings legs,
which is what this change actually touches.

## §11.2 — repro doc status sweep

All eight category repro docs carry both a `## Linux Status` and a `## macOS Status`
section.

| Repro doc                                              | Linux                | macOS                 |
| ------------------------------------------------------ | -------------------- | --------------------- |
| `docs/repro/h09-bindings-clear-relocation.md`          | verified (2026-05-06)| deferred (no Mac host)|
| `docs/repro/h10-bindings-hsplit-relocation.md`         | verified (2026-05-06)| deferred (no Mac host)|
| `docs/repro/h11-bindings-tab-nav.md`                   | verified (2026-05-06)| deferred (no Mac host)|
| `docs/repro/h12-bindings-window-nav.md`                | verified (2026-05-06)| deferred (no Mac host)|
| `docs/repro/h13-bindings-font-zoom.md`                 | verified (2026-05-06)| deferred (no Mac host)|
| `docs/repro/h14-bindings-detach.md`                    | verified (2026-05-06)| deferred (no Mac host)|
| `docs/repro/h15-bindings-broadcast.md`                 | verified (2026-05-06)| deferred (no Mac host)|
| `docs/repro/h16-bindings-url-hints.md`                 | verified (2026-05-06)| deferred (no Mac host)|

Plus the pre-existing `docs/repro/h01-cwd.md` (untouched by this change).

**macOS-deferral rationale (uniform across all eight docs):** the agent does not have
access to a macOS host. The chord is in pure-explicit-modifier form
(`ctrl+shift+<key>`) and `kitty-setup.conf` pins `kitty_mod ctrl+shift`, so the chord
SHOULD resolve to the same physical chord on macOS. Verification under a Mac is gated
on a Mac probe and is tracked under the follow-up
`phase1-curated-bindings-macos-overrides` (see Open Question 3 in
`design.md`).

## §11.3 — repro doc shape sweep

Each `docs/repro/h<NN>-bindings-<subgroup>.md` carries the expected sections
(`## Why this category exists` or `## Why the chord moved`, `## Manual repro`,
`## Verifying autonomously`, `## Linux Status`, `## macOS Status`,
`## Known limitations`). h09 also carries `## How the binding decomposes` (preserved
from the pre-rename `h02-clear.md`); h11–h16 carry `## Renumbered from h<NN>`
breadcrumbs. h14 and h15 carry an extra `## Why <action> and not <alternatives>?`
section justifying the action-string choice (resolved Q1 / Q2 in `design.md`).

## §10.6 — Open-questions sweep result

| Q   | Topic                            | Status                                                                                  |
| --- | -------------------------------- | --------------------------------------------------------------------------------------- |
| Q1  | broadcast mechanism              | resolved during §7 (h15 probe; chose `kitty +kitten broadcast` for upstream-doc parity) |
| Q2  | detach prompt vs `new-tab`       | resolved during §6 (h14 probe; bound both `ask` variants per §6 spec)                   |
| Q3  | macOS-only iTerm-parity overrides| follow-up `phase1-curated-bindings-macos-overrides`                                     |
| Q4  | `bindings` doctor check rename   | resolved (sanity sweep — section name independent of file name; no rename needed)        |
| Q5  | broadcast scope (all vs tab)     | follow-up `phase1-curated-bindings-broadcast-tab-scope` (loose interpretation kept; spec preamble allows it via the unconstrained-action-string clause) |

All five open questions have either a resolved answer (linked to the relevant probe)
or a named follow-up change. The change is ready for archive.

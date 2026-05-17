# Verification — phase2-scene-title-primitive

Captures the autonomous + manual outcomes that gate archive of this change,
per `tasks.md` §9. The Linux Status row in `docs/repro/h22-window-title.md`
must read `verified` before this change archives.

## Autonomous (already green)

### `make doctor` (2026-05-15, host: Pop!_OS 24.04 + COSMIC + kitty 0.46.2)

```
PASS kitty binary: /home/user-zero/.local/bin/kitty -> kitty 0.46.2 created by Kovid Goyal
PASS symlink: /home/user-zero/.local/bin/kitty -> /home/user-zero/.local/kitty.app/bin/kitty
PASS desktop entry: /home/user-zero/.local/share/applications/kitty.desktop
PASS config payload: /home/user-zero/.config/kitty/kitty-setup/kitty-setup.conf
PASS sentinel block: present in /home/user-zero/.config/kitty/kitty.conf
PASS parse check: kitty --debug-config exit=0
PASS bindings: 21 ours, 79 defaults, 0 conflicts
PASS completion: helper /usr/bin/register-python-argcomplete; eval line present in /home/user-zero/.zshrc
PASS remote-control: reachable on 1 kitty instance
```

All 9 checks PASS. No new doctor check was added by this change.

### `make test` — unit suite (2026-05-15)

```
======================= 149 passed, 43 skipped in 0.16s ========================
```

Unit suite: **149/149 green** (was 129 before this change; 20 new tests added
across `test_scenes_client.py`, `test_scenes_title.py`, and the `test_cli.py`
extensions).

### `KITTI_INTEGRATION=1 pytest tests/` — full suite incl. integration (2026-05-15)

```
192 passed in 10.30s
```

Integration suite: **43 tests** including:

- `tests/integration/test_client_socket_discovery.py` — 1 test, R7 promotion
  gate for the `_resolve_socket` unit stubs (verifies the pgrep-derived
  discovery path against a live kitty subprocess).
- `tests/integration/test_h22_window_title.py` — 7 tests covering the 6
  load-bearing scenarios in `kitty-scenes/spec.md`:
  - emoji round-trip on window title
  - emoji round-trip on tab title
  - `--temporary` default ON allows OSC-2 override (window)
  - `--no-temporary` blocks OSC-2 (window)
  - tab title persists across OSC-2 (no `--temporary` flag exists for tabs)
  - discovery errors when no kitty is running
  - `--to` unreachable socket propagates kitten's exit code
- `tests/integration/test_h21_remote_control_foundation.py` and
  `tests/integration/test_h21_doctor_remote_control.py` — unchanged from
  pre-refactor, still green after the doctor-helper lift to
  `scenes/_client.py`.

### Autocomplete (`my-kitty <TAB>` simulation, §9.6)

```
$ _ARGCOMPLETE=1 COMP_LINE="my-kitty wi" COMP_POINT=11 my-kitty
window

$ _ARGCOMPLETE=1 COMP_LINE="my-kitty window " COMP_POINT=16 my-kitty
-h
--help
title
```

Pre-reqs: `command -v register-python-argcomplete` resolves to
`/usr/bin/register-python-argcomplete`; the `register-python-argcomplete
my-kitty` eval line is sourced from `~/.zshrc` (verified by the doctor
`completion` check above). Completion offers `window` after `wi<TAB>` and
`title` after `window <TAB>` — the new subcommands inherit completion from
the existing argcomplete registration with no additional wiring required
by this change.

### `openspec validate phase2-scene-title-primitive --strict` (§9.8)

```
Change 'phase2-scene-title-primitive' is valid
```

## Manual (user-driven, signed off 2026-05-16)

All §9 manual checks signed off by the user on the daily host (Pop!_OS
24.04 + COSMIC + kitty 0.46.2):

- **§9.3** — 8 manual repro scenarios in `docs/repro/h22-window-title.md`
  all green: window/tab emoji round-trip, `--temporary` default permits
  OSC-2 overrides, `--no-temporary` blocks them, tab title sticks across
  OSC-2 emitted from windows inside it, `tab title --temporary` rejected
  with argparse error, out-of-kitty invocation discovers the single kitty
  via pgrep, `--to unix:<nonexistent>` propagates kitten's exit code +
  stderr verbatim.
- **§9.4** — Out-of-kitty invocation verified: `my-kitty window title
  "from outside"` from a non-kitty terminal updates the running kitty's
  focused window title (briefly — shell-integration's own OSC-2 resets to
  cwd on next prompt redraw under default `--temporary` mode, as designed).
- **§9.5** — Multi-kitty disambiguation message verified: with two kitty
  processes running, `my-kitty tab title "x"` from a non-kitty shell
  exits non-zero and the error names both PIDs.

The `## Linux Status` section of `docs/repro/h22-window-title.md` is now
`verified (2026-05-16, Pop!_OS 24.04 + COSMIC + kitty 0.46.2)`.

## Probe cleanup (§9.7)

`tmp/h22-window-title/` deleted (2026-05-16). The kitty-scenes spec's
"Probe directory is gone at archive time" scenario is satisfied.

## Followups

- `phase2-scene-title-primitive-macos` — re-verify on a macOS host when one
  is available. The `kitten @` protocol is platform-agnostic so wire-level
  behaviour should be identical; macOS font fallback may differ for tab-bar
  emoji rendering.

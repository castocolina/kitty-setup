# Verification — phase2-remote-control-foundation

Captured 2026-05-12 on Pop!_OS 24.04 / Wayland (`WAYLAND_DISPLAY=wayland-1`) / kitty 0.46.2 / Python 3.14.3 / `umask 0022`.

## `make doctor` output

```
$ uv run my-kitty doctor
PASS kitty binary: /home/user-zero/.local/bin/kitty -> kitty 0.46.2 created by Kovid Goyal
PASS symlink: /home/user-zero/.local/bin/kitty -> /home/user-zero/.local/kitty.app/bin/kitty
PASS desktop entry: /home/user-zero/.local/share/applications/kitty.desktop
PASS config payload: /home/user-zero/.config/kitty/kitty-setup/kitty-setup.conf
PASS sentinel block: present in /home/user-zero/.config/kitty/kitty.conf
PASS parse check: kitty --debug-config exit=0
PASS bindings: 21 ours, 79 defaults, 0 conflicts
PASS completion: helper /home/user-zero/git/cco/kitty-setup/.venv/bin/register-python-argcomplete; eval line present in /home/user-zero/.zshrc
SKIP remote-control: managed remote-control.conf not installed (run `make install`)
$ echo $?
0
```

The `SKIP remote-control: managed remote-control.conf not installed` line reflects the user's daily install pre-dating this change — `make install` has not yet been rerun on the user's `~/.config/kitty/kitty-setup/`. After `make install`, the line becomes either:

- `SKIP remote-control: no running kitty` — exit 0, when no kitty is running.
- `SKIP remote-control: no managed kitty socket found (running kitty pre-dates `make setup`?)` — exit 0, when running kitty was launched before this change.
- `PASS remote-control: reachable on N kitty instance(s)` — exit 0, when one or more managed kitties expose reachable sockets.
- `FAIL remote-control: <socket> (<stderr>)` — exit non-zero, when at least one managed socket is unreachable.

## `KITTI_INTEGRATION=1 pytest tests/` summary

```
$ KITTI_INTEGRATION=1 uv run pytest tests/
... (164 passed in 3.77s)
============================= 164 passed in 3.77s ==============================
```

New tests added by this change (12 total):

| Path | Tests |
|---|---|
| `tests/unit/test_doctor_remote_control.py` | 9 — parser, three SKIP branches, PASS branch, FAIL branch, CLI exit-code |
| `tests/integration/test_h21_remote_control_foundation.py` | 2 — single-instance reachable + two-instance no-collision |
| `tests/integration/test_h21_doctor_remote_control.py` | 1 — end-to-end doctor PASS with running managed kitty |

## Manual repro — Linux

Verified end-to-end via the h21 autonomous probe + the two h21 integration tests, all green on first iteration. The repro doc at `docs/repro/h21-remote-control-foundation.md` carries the full step-by-step. Key observations:

- `listen_on unix:/tmp/kitty` resolves to `/tmp/kitty-<PID>` automatically (probe 01, verdict `partial-with-workaround` — `$KITTY_PID` is NOT a valid expansion variable).
- Two concurrent kitty instances land at distinct, non-colliding sockets (probe 02).
- Socket file mode is umask-determined (`0775` under `umask 0022`); access scoping is via the kernel's UDS UID check, NOT mode `0600` (probe 03).
- `kitten @ --to unix:/tmp/kitty-<PID> ls` from a shell with `KITTY_LISTEN_ON` unset returns valid JSON (probe 04).

## macOS — deferred

No macOS host accessible at the time of apply (2026-05-12). Follow-up change name: **`phase2-remote-control-foundation-macos`**.

Scope of the follow-up:

- Probe 05 (`tmp/probes/phase2-remote-control-foundation/05-macos-tmp-symlink.md`): rerun probes 01 + 02 + 04 on a macOS Sequoia (15.x) host.
- Update `docs/repro/h21-remote-control-foundation.md` `## macOS Status` from `deferred-with-reason` to `verified` (or `partial-with-workaround` with a recorded delta).
- Update spec `kitty-remote-control` "macOS is deferred" scenario to reflect the verified outcome.
- Update design.md D1 — drop the macOS asterisk on the cross-platform claim.

## Out of scope, recorded here for trail

- §7 image-paste parity remains paused pending a reproducible repro (a `requirements.md` Phase 1 §7 note was added in task 6.5). It is NOT a hard prerequisite for Phase 2.
- §4 paste-preservation remains paused per its own change `phase1-paste-preservation`.

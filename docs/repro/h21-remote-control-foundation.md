# H21 — remote-control foundation

**Capability:** `kitty-remote-control` (Phase 2 §8-§14 foundation, openspec change `phase2-remote-control-foundation`).

**Status:** Promoted. Configuration in [`config/kitty/remote-control.conf`](../../config/kitty/remote-control.conf). Autonomous test in [`tests/integration/test_h21_remote_control_foundation.py`](../../tests/integration/test_h21_remote_control_foundation.py).

## Why this hypothesis exists

Phase 2 of `docs/requirements.md` is a stack of "scenes" capabilities (§8-§14) that each drive a running kitty over its remote-control socket. The pre-Phase-2 managed payload shipped zero RC surface to the user's daily kitty (the harness has its own per-session `--listen-on`, invisible to user-facing kitty). Phase 2 is dead on arrival without `allow_remote_control yes` + a stable `listen_on` in the managed config.

H21 is the probe loop that proves the minimum surface works: one `.conf` file, one `include` line, one socket per kitty instance, reachable from any shell on the host without `KITTY_LISTEN_ON` set.

## Renumbered from h18

Tasks.md, design.md, and the openspec change initially numbered this hypothesis `h18`. After promoting we discovered that `docs/repro/h18-monitor-disconnect-survival.md` already claims that number (it was archived under `phase1-monitor-disconnect-survival`). Per the repo-wide repro numbering rule, this hypothesis became h21 (the next free integer after h20). All references in `openspec/changes/phase2-remote-control-foundation/{proposal,design,tasks}.md`, the probe artefacts, and the integration test file have been updated.

## Key probe findings (see `tmp/probes/phase2-remote-control-foundation/`)

| Probe | Verdict | Finding |
|---|---|---|
| 01 | `partial-with-workaround` | `$KITTY_PID` is NOT an expansion variable in `listen_on` value. The literal substring survives on disk. Workaround: drop the placeholder; kitty's documented auto-`-<PID>` suffix produces the per-instance path on its own. |
| 02 | `holds` | Two concurrent kitty instances → two distinct sockets at `/tmp/kitty-<PID1>` and `/tmp/kitty-<PID2>`; each `kitten @ ls` returns only its own instance's tabs. |
| 03 | `partial-with-workaround` | Socket file mode is umask-determined (`0775` under `umask 0022`), NOT `0600`. Kitty does not chmod after creation. Access scoping is the kernel's UDS UID check, not file mode bits. |
| 04 | `holds` | A shell with `KITTY_LISTEN_ON` unset can call `kitten @ --to unix:/tmp/kitty-<PID> ls` and receive valid JSON. This is the Phase 2 invocation shape (load-bearing). |
| 05 | `deferred-with-reason` | macOS leg of probes 01-04 deferred — no macOS host. Follow-up change name: `phase2-remote-control-foundation-macos`. |

## Manual repro

```bash
# 1. Open a kitty instance (the user's daily kitty, post-`make setup`).
~/.local/bin/kitty &
KPID=$!
sleep 1

# 2. Confirm the socket landed at /tmp/kitty-<PID>.
ls -la /tmp/kitty-$KPID
# Expected:
#   srwxrwxr-x 1 <user> <user> 0 <date> /tmp/kitty-<PID>

# 3. From a SEPARATE shell on the same host (KITTY_LISTEN_ON unset):
unset KITTY_LISTEN_ON
~/.local/kitty.app/bin/kitten @ --to=unix:/tmp/kitty-$KPID ls | head -c 200
# Expected: a non-empty JSON array starting with `[ { "active_tab_history": ...`.

# 4. Tear down.
kill $KPID
```

## Linux Status

`verified` on Pop!_OS 24.04 / Wayland (`WAYLAND_DISPLAY=wayland-1`) / kitty 0.46.2.

- Autonomous probe: `uv run python tmp/h21-remote-control-foundation/run.py` exited 0 on first iteration (2026-05-12). `actual.json` captured `socket=/tmp/kitty-979647`, `socket_mode_octal=0o775`, `os_window_count=1`, `tabs_in_first=1`.
- Integration tests: `KITTI_INTEGRATION=1 uv run pytest tests/integration/test_h21_remote_control_foundation.py` → 2/2 PASSED.

## macOS Status

`deferred-with-reason` — no macOS host accessible at the time of promotion (2026-05-12). Follow-up change: `phase2-remote-control-foundation-macos` (probe 05 + macOS-specific repro). Until that lands:

- The cross-platform claim in `kitty-remote-control` ("the configured kitty instance exposes a per-instance unix socket") is verified on Linux only.
- `D1` in `openspec/changes/phase2-remote-control-foundation/design.md` notes the macOS leg explicitly.

## Stale-socket remediation

If a kitty crashed and left `/tmp/kitty-<old-PID>` behind, no kitty is currently listening on it. `my-kitty doctor` enumerates *running* kitty PIDs and never tries the stale path, so its check stays clean. Manual cleanup while no kitty is running:

```bash
rm /tmp/kitty-*
```

The system MUST NOT auto-delete files under `/tmp/kitty-*` outside of an explicit uninstall (spec requirement "Stale socket files do not block recovery").

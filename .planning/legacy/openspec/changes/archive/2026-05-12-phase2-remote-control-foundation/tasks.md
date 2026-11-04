## 1. External-system probes (R6) — must precede any config draft

- [x] 1.1 Probe `tmp/probes/phase2-remote-control-foundation/01-kitty-pid-expansion.md` — verdict `partial-with-workaround`. `$KITTY_PID` is NOT substituted; corrected to `listen_on unix:/tmp/kitty` (kitty auto-appends `-<PID>`). D1 + OQ-1 + spec wording revised.
- [x] 1.2 Probe `tmp/probes/phase2-remote-control-foundation/02-two-instances-no-collision.md` — verdict `holds`. Two parallel instances landed at distinct sockets; each `kitten @ ls` saw only its own instance.
- [x] 1.3 Probe `tmp/probes/phase2-remote-control-foundation/03-socket-mode.md` — verdict `partial-with-workaround`. Mode is umask-determined (`0775` under `umask 0022`), not `0600`. Spec "Socket permission scoping" scenario reworded to "Socket ownership scoping" with platform-determined mode.
- [x] 1.4 Probe `tmp/probes/phase2-remote-control-foundation/04-out-of-process-ls.md` — verdict `holds`. `KITTY_LISTEN_ON` unset, `kitten @ --to unix:/tmp/kitty-<PID> ls` returns valid JSON.
- [x] 1.5 Probe `tmp/probes/phase2-remote-control-foundation/05-macos-tmp-symlink.md` — verdict `deferred-with-reason`. No macOS host accessible; follow-up change `phase2-remote-control-foundation-macos` recorded.
- [x] 1.6 `## Probes` section appended to `design.md` with the 5-row table linking each probe → verdict → design decision.

## 2. Hypothesis (R1) — single dir, autonomous probe, iterate to green

- [x] 2.1 Created `tmp/h21-remote-control-foundation/` with `repro.md`, `run.py`, `expected.json`, `draft.conf`.
- [x] 2.2 `draft.conf` contains corrected `listen_on unix:/tmp/kitty` (post-probe-01) + WHY block.
- [x] 2.3 `run.py` spawns raw kitty subprocess (no harness), polls socket, calls out-of-process `kitten @ ls`, asserts list-of-OS-windows shape with `tabs` key. Teardown via SIGTERM → SIGKILL → unlink.
- [x] 2.4 `uv run python tmp/h21-remote-control-foundation/run.py` exited 0 on first iteration. `actual.json`: `socket=/tmp/kitty-979647`, `socket_mode_octal=0o775`, `os_window_count=1`, `tabs_in_first=1`.

## 3. Promote — config + integration test + repro doc

- [x] 3.1 `config/kitty/remote-control.conf` written with `allow_remote_control yes` + `listen_on unix:/tmp/kitty` + WHY block citing D1, D2, probe 01.
- [x] 3.2 `include remote-control.conf` appended to `config/kitty/kitty-setup.conf` after the existing nine includes.
- [~] 3.3 **SKIPPED.** `INCLUDED_PAYLOADS` lists only files that ship `map` lines (per its comment); `remote-control.conf` has 0 map lines (same as `monitor.conf`, which is also absent from the list). Adding it would diverge from the existing precedent without changing test behaviour. The introspection test stays green.
- [x] 3.4 `tests/integration/test_h21_remote_control_foundation.py` written. Two tests: `test_single_instance_socket_reachable`, `test_two_instances_no_collision`. `KITTI_INTEGRATION=1 uv run pytest tests/integration/test_h21_remote_control_foundation.py` → 2/2 PASSED.
- [x] 3.5 `docs/repro/h21-remote-control-foundation.md` written with `## Linux Status` (verified, Pop!_OS 24.04 / kitty 0.46.2) and `## macOS Status` (`deferred-with-reason`, follow-up change `phase2-remote-control-foundation-macos`). Stale-socket remediation documented.
- [x] 3.6 `tmp/h21-remote-control-foundation/` deleted. Probe artefacts under `tmp/probes/phase2-remote-control-foundation/` retained until archive.

## 4. Doctor wiring (D3 + `kitty-install` MODIFIED requirement)

- [x] 4.1 `_check_remote_control_per_probe_04()` added to `src/kitty_setup/doctor.py`. Enumerates running kitty PIDs via `pgrep -x kitty`, resolves the socket path by parsing `listen_on unix:<base>` from the installed `remote-control.conf` and appending `-<PID>` (kitty's auto-suffix per probe 01). Runs `kitten @ --to unix:<path> ls` with timeout 2s per socket. Returns SKIP when no PIDs found OR no managed socket found OR rc.conf absent; PASS when ≥1 reachable; FAIL when ≥1 managed socket fails.
- [x] 4.2 New check wired into `run_checks()` output list; `CheckResult` gained a `skipped: bool` field; `render()` emits `SKIP|PASS|FAIL <name>: <detail>`; `cli_doctor()` exit code treats SKIP as not-a-fail (`r.passed or r.skipped`).
- [x] 4.3 `tests/unit/test_doctor_remote_control.py` — 9 tests covering parser, SKIP branches (rc.conf missing, no kitty, no managed socket), PASS branch, FAIL branch, and CLI-level exit-code behaviour. Stub functions reference probe 04 via the `_per_probe_04` suffix on the SUT. All green.
- [x] 4.4 `tests/integration/test_h21_doctor_remote_control.py` — spawns raw kitty (not KittySession; harness CLI flag would override config), calls doctor function directly, asserts PASS with "reachable on 1 kitty instance". Green.

## 5. Catalog-level verification

- [x] 5.1 `my-kitty keys --json` source enumeration: `remote-control` does NOT appear (file has 0 map lines, like `monitor.conf`). Chord catalog count unchanged: 21 ours / 79 defaults / 0 conflicts. Task original expectation (file appears in source enumeration) corrected — the catalog enumerates chord-emitting files only.
- [~] 5.2 SKIPPED. No chord introduced; allow-list entry and curated-bindings delta not needed.
- [x] 5.3 `uv run my-kitty doctor` → exit 0 on host with the user's current install (pre-promotion of the new file, since `make install` not yet rerun on user's daily kitty). Output line: `SKIP remote-control: managed remote-control.conf not installed (run \`make install\`)`. After running install the line becomes `SKIP remote-control: no running kitty` (if no managed kitty running) or `PASS remote-control: reachable on N kitty instance(s)`.
- [x] 5.4 `KITTI_INTEGRATION=1 uv run pytest tests/` → 164 passed. Test count rose by 12 (9 unit + 2 h21 reachability + 1 h21 doctor end-to-end).
- [x] 5.5 Install/uninstall round-trip verified in a tempdir via `config_updater.install/uninstall` directly. Post-install: `remote-control.conf` present with `allow_remote_control yes` + `listen_on unix:/tmp/kitty`, `kitty-setup.conf` contains `include remote-control.conf`. Post-uninstall: file removed AND payload dir removed (surgical-removal contract).

## 6. Verification before completion

- [x] 6.1 `make doctor` output captured in `verification.md` (exit 0, `SKIP remote-control: managed remote-control.conf not installed` on the user's pre-promotion install state).
- [x] 6.2 `KITTI_INTEGRATION=1 uv run pytest tests/` summary captured in `verification.md` (164 passed, 12 new).
- [x] 6.3 Linux manual repro captured in `docs/repro/h21-remote-control-foundation.md` `## Linux Status` (verified on Pop!_OS 24.04 / Wayland / kitty 0.46.2, autonomous probe + 3 new integration tests all green first-shot).
- [x] 6.4 macOS deferred; follow-up change `phase2-remote-control-foundation-macos` named in `verification.md` and linked from spec scenario "macOS is deferred".
- [x] 6.5 `docs/requirements.md` Phase 1 §7 prefixed with `**PAUSED (2026-05-12)** pending reproducible repro on a host accessible to the agent — same pattern as §4 paste-preservation; not a hard prerequisite for Phase 2.`

## Why

Phase 2 of `docs/requirements.md` (§8-§14, "scenes") is a stack of capabilities that all drive the user's running kitty through its remote-control socket: set window/tab title, set tab accent, spawn N pre-styled windows, launch a scene by name. Every one of those scripts shells to `kitty @ <verb>` against a unix socket exposed by the running kitty instance.

The current managed payload (`config/kitty/kitty-setup.conf` + nine `*.conf` includes) ships zero remote-control surface. The only existing `--allow-remote-control` reference is on a per-launch basis inside `broadcast.conf` (the §5 broadcast chord) — that flag toggles RC for the single window launched by the kitten, not for the whole kitty instance. The integration harness (`KittySession`) drives RC via per-session CLI flags (`-o allow_remote_control=yes --listen-on=unix:tmp/sessions/<id>/sock`), which proves the mechanism but does not help a user's daily kitty.

Without a stable, predictable socket on the user's instance, no Phase 2 hypothesis script can talk to that instance — neither from a kitty key chord, nor from a shell prompt outside kitty, nor from `my-kitty scene <name>`. This change is the pure unblock: it ships the remote-control surface and nothing else. Zero scene logic, zero new chords, zero behaviour the user perceives until the first Phase 2 capability lands on top.

Decided concurrently: §7 (image-paste parity, investigation-led) stays paused until a reproducible repro exists (Linux or macOS). It is not a hard gate for Phase 2 — same shape as §4, which is already paused.

## What Changes

- Add `config/kitty/remote-control.conf` containing `allow_remote_control yes` and `listen_on unix:/tmp/kitty`. Kitty appends `-<PID>` to the path automatically at startup (its documented behaviour — verified by probe 01 in `tmp/probes/phase2-remote-control-foundation/01-kitty-pid-expansion.md`; the `$KITTY_PID` placeholder is NOT a valid expansion variable in `listen_on` values, despite a prior assumption to the contrary). The same literal value works on Linux and macOS subject to probe 05 (deferred-with-reason until macOS host available). The file carries a top-of-file WHY block citing Phase 2 requirements §8-§14 and this proposal.
- Add `include remote-control.conf` to `config/kitty/kitty-setup.conf`, after the existing nine includes.
- Append `"remote-control.conf"` to `INCLUDED_PAYLOADS` in `tests/integration/test_h03_introspection.py` so the introspection test continues to auto-derive its counts.
- Extend `my-kitty doctor` with a single new check: "remote control reachable on the user's running kitty." The check is best-effort — when no kitty is running, it reports `SKIP remote-control: no running kitty` and does NOT fail. When a kitty is running, it resolves the socket path from the config, runs `kitty @ --to <socket> ls`, and reports `PASS` or `FAIL` based on exit code. This is the diagnostic-only surface; the install/uninstall contract is unchanged from `kitty-config-management`.
- Update `intentional-overrides.conf` allow-list **only** if the new file introduces a chord that shadows a kitty default. `allow_remote_control` and `listen_on` are non-chord directives, so no entry is expected; the implementation must verify with `my-kitty keys --json` and skip the entry if no chord lands.
- Hypothesis dir `tmp/h21-remote-control-foundation/` with an autonomous probe: spawn kitty with a config that contains `remote-control.conf`'s directives and assert `kitten @ --to unix:/tmp/kitty-<PID> ls` from *outside* the spawning process returns valid JSON. Probe artefacts under `tmp/probes/phase2-remote-control-foundation/` for per-platform socket-path resolution (Linux auto-PID-suffix behaviour, macOS `/tmp` symlink resolution, socket mode).
- Manual repro under `docs/repro/h21-remote-control-foundation.md` covering Linux (`Pop!_OS 24.04 / kitty 0.46.x / Wayland`) and macOS-deferred-with-note (same pattern as §5 and §6). Repro: open kitty, run `echo $KITTY_LISTEN_ON` (or `pgrep kitty` + `ls /tmp/kitty-*`), confirm the socket file exists at `/tmp/kitty-<PID>`, run `kitten @ --to unix:/tmp/kitty-<PID> ls` from a separate shell, observe JSON listing the running kitty's tabs/windows.
- §7 image-paste parity is explicitly deferred. A line in `docs/requirements.md` and/or a parking-lot note records the pause; no change proposal is opened until a reproducible repro lands.

## Capabilities

### New Capabilities

- `kitty-remote-control`: behavioural contract that a kitty instance launched from the managed config exposes a discoverable, stable unix socket at a per-PID path on Linux and the documented macOS equivalent; that the socket accepts `kitty @` verbs from any shell on the same host as the user running the instance; that the socket is per-instance (no cross-instance leakage); that `my-kitty doctor` reports the reachability of the socket without failing when no kitty is running; and that uninstall removes the new config file via the existing surgical-removal contract. Backed by an integration probe (h21) and a manual repro.

### Modified Capabilities

None at the requirements level.

- `kitty-config-management` already permits per-topic `*.conf` files under the managed payload dir — the new `remote-control.conf` lands on that contract unchanged.
- `kitty-install` keeps its install/uninstall contract. The new payload file is just another entry in the same surgical-removal sweep.
- `kitty-test-harness` keeps its per-session `--listen-on` flow. The harness does not read the new file; it continues to spawn kitty with its own session-local socket. If a future task needs harness-and-user-config parity, that is its own change.

If implementation discovers the new file must introduce a chord (it should not), the curated catalog (`kitty-curated-bindings`) would need a delta — flagged during tasks.md drafting and surfaced at review, not silently added.

## Impact

- **New top-level paths:** `config/kitty/remote-control.conf`, `docs/repro/h21-remote-control-foundation.md`, `tmp/h21-remote-control-foundation/` (gitignored, scratch, deleted on promotion).
- **Edited files:** `config/kitty/kitty-setup.conf` (one new `include` line), `tests/integration/test_h03_introspection.py` (one new entry in `INCLUDED_PAYLOADS`), `src/kitty_setup/doctor.py` (one new check function and one new line in the output assembly), optionally `src/kitty_setup/cli.py` if the doctor wiring needs a new subcommand surface (likely not — doctor stays as today's `make doctor`).
- **Hypothesis dirs:** `tmp/h21-remote-control-foundation/`, plus `tmp/probes/phase2-remote-control-foundation/<NN>-<slug>.md`.
- **System mutations:** install copies the new `.conf` into `~/.config/kitty/kitty-setup/`. Uninstall removes it via the existing block-strip contract. The user's `kitty.conf` itself gains nothing new (only the managed include line, which is already there).
- **Security surface:** `allow_remote_control yes` opens a kitty socket to local processes. The socket is filesystem-scoped (`/tmp/kitty-<PID>`, owned by the user, mode `0775` under default `umask 0022` per probe 03), and access is scoped by UID via the kernel's UDS permission check. This is the same posture used by every kitty user who runs `kitty @` interactively. The design document records the trade-off vs `socket-only` and `password` modes and the reasoning for picking `yes`.
- **Out of scope:** Phase 2 scene capabilities (§8-§14 — each is its own change), §7 image-paste parity (paused, separate change when reproducible), §4 paste preservation (already paused). Also out of scope: any helper binary that wraps `kitty @` (premature — wait for a real Phase 2 caller before abstracting).

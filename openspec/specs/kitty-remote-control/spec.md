# kitty-remote-control Specification

## Purpose
TBD - created by archiving change phase2-remote-control-foundation. Update Purpose after archive.
## Requirements
### Requirement: Ship a remote-control include file as part of the managed payload

The system SHALL place a file `remote-control.conf` under the managed payload directory (`~/.config/kitty/kitty-setup/remote-control.conf`) and SHALL add `include remote-control.conf` to `~/.config/kitty/kitty-setup/kitty-setup.conf` after the existing per-topic includes. The file MUST contain at least two directives: `allow_remote_control yes` and `listen_on unix:/tmp/kitty`. The file MUST carry a top-of-file comment block citing `docs/requirements.md` Phase 2 and the `kitty-remote-control` capability as the justification.

#### Scenario: Install lands the file and the include
- **WHEN** a user runs `make setup` (or `my-kitty install`) on a host with no prior install
- **THEN** the file `~/.config/kitty/kitty-setup/remote-control.conf` exists with `allow_remote_control yes` and `listen_on unix:/tmp/kitty` present
- **AND** `~/.config/kitty/kitty-setup/kitty-setup.conf` contains the line `include remote-control.conf`
- **AND** `kitty --debug-config --config ~/.config/kitty/kitty.conf` exits 0

#### Scenario: Re-running install is a no-op
- **WHEN** the user runs `make setup` a second time with no intervening changes
- **THEN** the file's content is byte-identical to the first run AND no new `kitty.conf.bak.*` file is produced (per the existing `kitty-config-management` no-op contract)

### Requirement: Uninstall removes the file via the existing surgical-removal contract

The system SHALL remove `remote-control.conf` from the managed payload directory whenever the managed payload directory itself is removed. The system MUST NOT leave a dangling `include remote-control.conf` line in `kitty-setup.conf` after uninstall — uninstall removes the entire payload directory per `kitty-config-management`, so the include line vanishes with it. The `--keep-config` flag SHALL preserve `remote-control.conf` alongside the rest of the payload.

#### Scenario: Default uninstall removes the file
- **WHEN** the user runs `my-kitty uninstall` after a successful install that shipped `remote-control.conf`
- **THEN** the file no longer exists AND the managed payload directory no longer exists AND the sentinel block in `~/.config/kitty/kitty.conf` is gone

#### Scenario: --keep-config preserves the file
- **WHEN** the user runs `my-kitty uninstall --keep-config`
- **THEN** `~/.config/kitty/kitty-setup/remote-control.conf` is preserved AND the sentinel block is preserved AND no backup is deleted

### Requirement: The configured kitty instance exposes a per-instance unix socket

When the user launches a kitty instance using the managed config (directly or via the user's shell), that instance SHALL listen on a unix socket at the path produced by appending `-<PID>` to the `listen_on` value, where `<PID>` is the kitty process PID. With `listen_on unix:/tmp/kitty` the resolved path is `/tmp/kitty-<PID>`. The `-<PID>` suffix is appended by kitty itself (documented `listen_on` behaviour, verified by probe 01); the config value MUST NOT include a literal `$KITTY_PID` placeholder because kitty does not substitute it. Two concurrent kitty instances launched as the same user MUST end up with two distinct socket paths and MUST NOT collide.

#### Scenario: Single instance exposes a socket
- **WHEN** the user launches `kitty` after `make setup` on a host where no kitty was running
- **THEN** a unix socket file exists at `/tmp/kitty-<PID>` where `<PID>` is the PID of the running kitty process
- **AND** `kitty @ --to unix:/tmp/kitty-<PID> ls` returns valid JSON describing that instance's tabs and windows

#### Scenario: Two concurrent instances each have their own socket
- **WHEN** the user launches two kitty instances in parallel
- **THEN** two distinct socket files exist at `/tmp/kitty-<PID1>` and `/tmp/kitty-<PID2>`
- **AND** `kitty @ --to unix:/tmp/kitty-<PID1> ls` and `kitty @ --to unix:/tmp/kitty-<PID2> ls` each return JSON describing only their respective instance

### Requirement: The socket accepts remote-control verbs from any process running as the same UID

A process running as the user's UID, with no `KITTY_LISTEN_ON` environment variable set, SHALL be able to invoke `kitten @ --to unix:/tmp/kitty-<PID> <verb>` against the socket and receive a valid response. The socket MUST NOT require the caller to be a child of the kitty process. Access scoping SHALL rely on the kernel's UDS permission check against the calling process's UID, not on a specific file mode value — kitty creates the socket with the spawning process's umask applied to `0777`, so the file mode is platform-determined and NOT guaranteed to be `0600`.

#### Scenario: Out-of-process call reaches the socket
- **WHEN** the user opens a kitty instance, then from a separate (non-kitty-spawned) shell on the same host runs `kitten @ --to unix:/tmp/kitty-<PID> ls`
- **THEN** the call returns JSON identical in shape to the response from inside the kitty instance

#### Scenario: Socket ownership scoping
- **WHEN** the socket file `/tmp/kitty-<PID>` is created
- **THEN** its owner UID is the UID of the user who spawned kitty
- **AND** its file mode is the result of `0777 & ~umask` for the spawning shell (e.g. `0775` under umask `0022`, `0700` under umask `0077`); the spec does NOT mandate a specific mode value

### Requirement: Stale socket files do not block recovery

If a kitty instance crashes leaving a stale socket file at `/tmp/kitty-<PID>`, the system MUST surface the staleness through `my-kitty doctor` rather than fail silently. The diagnostic check MUST report the path and the failing `kitty @ ls` error so the user can `rm` the stale file. The system MUST NOT auto-delete files under `/tmp/kitty-*` in any non-uninstall path.

#### Scenario: Stale socket surfaces in doctor
- **WHEN** a kitty instance was running, crashed, and left `/tmp/kitty-12345` behind, and no kitty with PID 12345 is currently running
- **THEN** `my-kitty doctor` does NOT include `/tmp/kitty-12345` in its enumeration of reachable sockets (because no kitty matches that PID)
- **AND** the doctor's overall exit code is 0 if all *currently running* kitties are reachable

#### Scenario: Stale file colliding with a new PID
- **WHEN** a kitty starts up and `$KITTY_PID` happens to match a stale `/tmp/kitty-<PID>` left by an unrelated process
- **THEN** kitty's own startup behaviour (documented `listen_on` semantics) determines the outcome — if it refuses to overwrite, doctor reports `FAIL remote-control: <path> not reachable: <stderr>` and the remediation in `docs/repro/h21-remote-control-foundation.md` is to remove the stale file

### Requirement: A repro doc carries the manual verification

The repository SHALL contain `docs/repro/h21-remote-control-foundation.md` with at minimum two sections: `## Linux Status` and `## macOS Status`. The Linux section MUST describe a manual verification (open kitty, read `$KITTY_LISTEN_ON`, run `kitty @ ls` from a separate shell, observe JSON). The macOS section MUST either describe the verified manual repro or carry `deferred-with-reason` with the explicit follow-up change name in `verification.md`.

#### Scenario: Linux repro is documented and verified
- **WHEN** the user follows the Linux section's instructions on a Pop!_OS 24.04 host with kitty 0.46.x
- **THEN** the user observes a non-empty JSON response from the out-of-process `kitten @ --to unix:/tmp/kitty-<PID> ls` call AND the repro doc records the verification outcome

#### Scenario: macOS is deferred
- **WHEN** no macOS host is available at apply time
- **THEN** the `## macOS Status` section names the follow-up change (suggested `phase2-remote-control-foundation-macos`) AND `verification.md` includes the same name in its follow-up section

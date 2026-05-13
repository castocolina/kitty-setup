## MODIFIED Requirements

### Requirement: Doctor reports install state

The system SHALL provide a `doctor` command that reports, in deterministic plain-text form: (a) the resolved kitty binary path and version, (b) the presence and validity of the sentinel-bracketed include block in `~/.config/kitty/kitty.conf`, (c) the result of `kitty --debug-config` parse exit code, (d) the absolute paths of our config payload, the desktop entry, and the symlink, (e) a binding-introspection summary line of the form `bindings: <N> ours, <N> defaults, <N> conflicts` produced by invoking the `kitty-binding-introspection` enumeration, AND (f) a remote-control reachability line of the form `remote-control: <status> <detail>` where `<status>` is one of `PASS`, `FAIL`, or `SKIP`. `SKIP` MUST be emitted when no kitty process is running on the host; `PASS` MUST be emitted when at least one running kitty is reachable at its resolved `listen_on` socket; `FAIL` MUST be emitted when at least one running kitty is unreachable. It MUST exit 0 when all non-skipped checks pass — including a `0` value for the `conflicts` count and the remote-control line being either `PASS` or `SKIP` — and non-zero on any failure, where a non-zero `conflicts` count or a `FAIL` on remote-control each count as a failure.

#### Scenario: Doctor on a healthy install
- **WHEN** the user runs `make doctor` after a successful `make setup`
- **THEN** the command prints each check on its own line with a `PASS`, `FAIL`, or `SKIP` prefix, exits 0, lists the kitty version, includes a `PASS bindings: <N> ours, <N> defaults, 0 conflicts` line, AND includes either a `PASS remote-control: reachable on <N> kitty instance(s)` line or a `SKIP remote-control: no running kitty` line

#### Scenario: Doctor on a partial install
- **WHEN** kitty is installed but the sentinel include block is missing from the user's `kitty.conf`
- **THEN** the command marks the include check `FAIL`, names the missing file or line, exits non-zero, and suggests `make setup` as the remediation

#### Scenario: Doctor with a non-zero conflict count
- **WHEN** the user runs `make doctor` on an install whose binding introspection reports one or more real conflicts
- **THEN** the command marks the bindings check `FAIL bindings: <N> ours, <N> defaults, <K> conflicts (run `my-kitty keys` for details)`, exits non-zero, and the other checks still report their own status independently

#### Scenario: Doctor when no kitty is running
- **WHEN** the user runs `make doctor` on a host where the install is correct but no kitty process is currently running
- **THEN** the remote-control line reports `SKIP remote-control: no running kitty` AND the overall exit code is 0 (the install is correct; the user has not yet launched kitty)

#### Scenario: Doctor when remote control is unreachable
- **WHEN** the user runs `make doctor` while at least one kitty process is running and its resolved socket at `unix:/tmp/kitty-<PID>` cannot be reached by `kitty @ --to <socket> ls`
- **THEN** the remote-control line reports `FAIL remote-control: <path> not reachable: <stderr>`, the command exits non-zero, the user is pointed at `docs/repro/h21-remote-control-foundation.md` for remediation, and the other checks still report their own status independently

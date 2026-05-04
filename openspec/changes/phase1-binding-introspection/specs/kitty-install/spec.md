## MODIFIED Requirements

### Requirement: Doctor reports install state

The system SHALL provide a `doctor` command that reports, in deterministic plain-text form: (a) the resolved kitty binary path and version, (b) the presence and validity of the sentinel-bracketed include block in `~/.config/kitty/kitty.conf`, (c) the result of `kitty --debug-config` parse exit code, (d) the absolute paths of our config payload, the desktop entry, and the symlink, AND (e) a binding-introspection summary line of the form `bindings: <N> ours, <N> defaults, <N> conflicts` produced by invoking the `kitty-binding-introspection` enumeration. It MUST exit 0 when all checks pass — including a `0` value for the `conflicts` count — and non-zero on any failure, where a non-zero `conflicts` count counts as a failure.

#### Scenario: Doctor on a healthy install
- **WHEN** the user runs `make doctor` after a successful `make setup`
- **THEN** the command prints each check on its own line with a `PASS` or `FAIL` prefix, exits 0, lists the kitty version, and includes a `PASS bindings: <N> ours, <N> defaults, 0 conflicts` line

#### Scenario: Doctor on a partial install
- **WHEN** kitty is installed but the sentinel include block is missing from the user's `kitty.conf`
- **THEN** the command marks the include check `FAIL`, names the missing file or line, exits non-zero, and suggests `make setup` as the remediation

#### Scenario: Doctor with a non-zero conflict count
- **WHEN** the user runs `make doctor` on an install whose binding introspection reports one or more real conflicts
- **THEN** the command marks the bindings check `FAIL bindings: <N> ours, <N> defaults, <K> conflicts (run `kitty-setup-bindings` for details)`, exits non-zero, and the other five checks still report their own status independently

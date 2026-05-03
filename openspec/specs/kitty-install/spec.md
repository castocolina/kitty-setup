# kitty-install Specification

## Purpose
TBD - created by archiving change bootstrap-foundation-phase1-popos. Update Purpose after archive.
## Requirements
### Requirement: Install kitty from upstream into per-user prefix

The system SHALL install kitty from the upstream installer (`https://sw.kovidgoyal.net/kitty/installer.sh`) into `~/.local/kitty.app`, symlink the binary at `~/.local/bin/kitty`, and write a desktop entry at `~/.local/share/applications/kitty.desktop`. The install MUST NOT require `sudo` and MUST NOT touch any path under `/usr/`, `/opt/`, or `/etc/`.

#### Scenario: Fresh install on a host without kitty
- **WHEN** the user runs `make setup` on a Pop!_OS 24.04 host with no kitty present
- **THEN** `~/.local/kitty.app/bin/kitty` exists, `~/.local/bin/kitty` is a symlink pointing to it, the desktop entry is present, and `kitty --version` reports a version string
- **AND** the absolute path of the resolved kitty version is written to `tmp/install.log`

#### Scenario: Re-running setup is idempotent
- **WHEN** the user runs `make setup` a second time on a host where the install already succeeded
- **THEN** the install step exits non-zero only on real failure, no duplicate desktop entries are written, and the existing `~/.local/kitty.app` is reused or replaced atomically
- **AND** the user is informed (via stdout) that no new install was needed if the resolved upstream version matches the installed version

### Requirement: Uninstall removes only files written by setup

The system SHALL provide an uninstall path that removes `~/.local/kitty.app`, the `~/.local/bin/kitty` symlink, and the desktop entry, AND nothing else. It MUST leave any pre-existing `~/.local/kitty.app` backup or unrelated `~/.local/bin/` entries untouched.

#### Scenario: Uninstall after a clean install
- **WHEN** the user runs `make uninstall` after a previous `make setup`
- **THEN** the three install paths above are gone and the rest of `~/.local/` is unchanged
- **AND** `command -v kitty` returns non-zero unless another kitty install exists elsewhere on PATH

#### Scenario: Uninstall when nothing is installed
- **WHEN** the user runs `make uninstall` on a host where `make setup` has never run
- **THEN** the command exits 0 and reports that there is nothing to remove
- **AND** no files are created or modified

### Requirement: Doctor reports install state

The system SHALL provide a `doctor` command that reports, in deterministic plain-text form: (a) the resolved kitty binary path and version, (b) the presence and validity of the sentinel-bracketed include block in `~/.config/kitty/kitty.conf`, (c) the result of `kitty --debug-config` parse exit code, (d) the absolute paths of our config payload, the desktop entry, and the symlink. It MUST exit 0 when all checks pass and non-zero on any failure.

#### Scenario: Doctor on a healthy install
- **WHEN** the user runs `make doctor` after a successful `make setup`
- **THEN** the command prints each check on its own line with a `PASS` or `FAIL` prefix, exits 0, and lists the kitty version

#### Scenario: Doctor on a partial install
- **WHEN** kitty is installed but the sentinel include block is missing from the user's `kitty.conf`
- **THEN** the command marks the include check `FAIL`, names the missing file or line, exits non-zero, and suggests `make setup` as the remediation


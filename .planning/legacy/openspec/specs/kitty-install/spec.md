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

### Requirement: Install seeds example scene recipes copy-if-absent

`my-kitty install` SHALL seed the bundled example scene recipes into the user
scenes directory (`$XDG_CONFIG_HOME/kitty-setup/scenes/`, the same directory the
recipe loader reads), creating the directory if it does not exist. The example
recipes SHALL be packaged as data inside the installed wheel (force-included from
`examples/scenes/`, mirroring the existing config-payload packaging) so seeding
works from the installed binary without the source repository present. The
seeding logic SHALL live in the Python install path (`installer.py`), NOT in the
bootstrap shell script — `tools/setup.sh` SHALL NOT copy scene files.

Seeding SHALL be **copy-if-absent per file**: each bundled `*.toml` is copied
only when a file of that name does not already exist in the user scenes
directory. An existing file (including one the user has edited) SHALL NEVER be
overwritten. Seeding SHALL be idempotent and SHALL print a one-line summary of
how many recipes were seeded versus left untouched.

Once copied, a seeded recipe is **user data**: the uninstall path SHALL NOT
remove the user scenes directory or any file in it (consistent with "Uninstall
removes only files written by setup" — the scenes directory lives outside the
managed config payload and is owned by the user thereafter). A user who deletes a
seeded example MAY see it reappear on a subsequent install (an accepted
consequence of copy-if-absent).

#### Scenario: Fresh install seeds the example recipes

- **WHEN** the user runs `my-kitty install` on a host where
  `~/.config/kitty-setup/scenes/` does not yet exist
- **THEN** the directory is created and each bundled example `*.toml` is copied
  into it, and a summary line reports the count seeded

#### Scenario: Re-install never overwrites an edited recipe

- **WHEN** the user has edited `~/.config/kitty-setup/scenes/docker.toml` and then
  runs `my-kitty install` again
- **THEN** the edited `docker.toml` is left byte-for-byte unchanged, any bundled
  example whose name is absent is added, and the summary reports the edited file
  among those kept

#### Scenario: Uninstall leaves seeded scenes in place

- **WHEN** the user runs `my-kitty uninstall` after an install that seeded scenes
- **THEN** the managed config payload and install paths are removed per the
  uninstall contract, but `~/.config/kitty-setup/scenes/` and its `*.toml` files
  remain untouched


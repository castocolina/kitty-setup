# kitty-config-management Specification

## Purpose
TBD - created by archiving change bootstrap-foundation-phase1-popos. Update Purpose after archive.
## Requirements
### Requirement: Inject our config via a sentinel-bracketed include

The system SHALL add exactly one `include kitty-setup/kitty-setup.conf` line to the user's `~/.config/kitty/kitty.conf`, surrounded by sentinel comments `# >>> kitty-setup managed (do not edit between markers) >>>` and `# <<< kitty-setup managed <<<`. The system MUST NOT modify any line outside that block. If `~/.config/kitty/kitty.conf` does not exist, the system SHALL create a minimal file containing only the marker block.

#### Scenario: User has an existing kitty.conf with their own bindings
- **WHEN** the install runs against a `~/.config/kitty/kitty.conf` containing user content
- **THEN** the file ends with the sentinel block, the user's prior content is byte-identical above the block, and a backup `kitty.conf.bak.<UTC-ts>` is present in the same directory

#### Scenario: User has no kitty.conf
- **WHEN** the install runs against a host where `~/.config/kitty/kitty.conf` is absent
- **THEN** the file is created containing only the sentinel block and the include line, no backup file is created (nothing to back up), and the parent directory is created if missing

### Requirement: Re-running setup is a no-op when the block is already correct

The system SHALL detect when the sentinel block already contains the exact expected content and SHALL skip the write. The system MUST NOT create a new backup file in that case.

#### Scenario: Setup is run twice in a row
- **WHEN** the user runs `make setup` twice with no intervening config changes
- **THEN** the second run leaves `kitty.conf` byte-identical and does not create an additional `kitty.conf.bak.*` file
- **AND** the run reports "config already up to date" on stdout

### Requirement: Backup before any mutation

The system SHALL copy `~/.config/kitty/kitty.conf` to `~/.config/kitty/kitty.conf.bak.<UTC-ts>` before performing any write that would change its content. The timestamp MUST be UTC, in `YYYYMMDDTHHMMSSZ` format. Old backups MUST NOT be deleted by the install.

#### Scenario: First mutation creates a backup
- **WHEN** the install mutates `kitty.conf` for the first time
- **THEN** a `kitty.conf.bak.<ts>` file exists with the pre-mutation content and a timestamp matching the install run

### Requirement: Payload lives under our own subdirectory

The system SHALL place all per-topic config files under `~/.config/kitty/kitty-setup/` (entry file `kitty-setup.conf`, plus per-topic `*.conf`). The system MUST NOT create or modify any file under `~/.config/kitty/` outside that subdirectory and the user's `kitty.conf`.

#### Scenario: Footprint is enumerable
- **WHEN** the user runs `find ~/.config/kitty -type f` after a successful setup
- **THEN** every file we own is under `~/.config/kitty/kitty-setup/`, plus the user's `kitty.conf` and any `kitty.conf.bak.*` we wrote
- **AND** no other path under `~/.config/kitty/` has been created or touched

### Requirement: Mutated config must parse cleanly

After every write that changes the user's `kitty.conf`, the system SHALL run `kitty --debug-config --config <path>` in a subprocess. If the exit code is non-zero, the system MUST restore the latest backup and SHALL fail the install with a non-zero exit code, surfacing the parser output.

#### Scenario: Parse failure triggers rollback
- **WHEN** the post-mutation parse check returns non-zero
- **THEN** `kitty.conf` is restored from the most recent `kitty.conf.bak.<ts>`, the parser stderr is printed, and the install exits non-zero

### Requirement: Uninstall strips the block cleanly

The system SHALL provide an uninstall path that removes only the sentinel block (and the marker lines themselves) from `~/.config/kitty/kitty.conf`, AND removes the `~/.config/kitty/kitty-setup/` directory. If after stripping the file contains no non-blank, non-comment lines, the system SHALL replace it with the most recent `kitty.conf.bak.<ts>` if present, else delete it. Backup files themselves MUST NOT be deleted by uninstall.

#### Scenario: Uninstall after a normal install
- **WHEN** the user runs `make uninstall`
- **THEN** the sentinel block is gone, the user's prior content is preserved byte-identical, the `~/.config/kitty/kitty-setup/` directory no longer exists, and any `kitty.conf.bak.*` files are still present

#### Scenario: Uninstall when the user's kitty.conf had no prior content
- **WHEN** uninstall runs on a `kitty.conf` that contained only our block (no prior user content, no backup)
- **THEN** the file is deleted (not left empty), and the parent directory is left in place if it contains other entries


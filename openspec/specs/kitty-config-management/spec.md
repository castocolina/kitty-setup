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

### Requirement: Backup pruning is an explicit, opt-in user action

The system SHALL expose a `my-kitty-setup prune` subcommand that, with no
flags, produces a dry-run listing of `kitty.conf.bak.*` files under
`~/.config/kitty/` and SHALL NOT delete any file. The dry run MUST print one
line per backup with filename, modification time in ISO-8601 UTC, and byte
size, plus a summary line with total count and total size, then exit 0.

The system SHALL accept a `--backups` flag that gates deletion. When
`--backups` is provided, the system SHALL apply exactly one of three
mutually-exclusive policies:

* `--keep N` (default policy when `--backups` is provided alone, with
  default N of 3) — sort all `kitty.conf.bak.*` files lexicographically by
  filename, retain the N most recent, delete the rest.
* `--older-than DAYS` — delete every `kitty.conf.bak.*` file whose
  modification time is older than DAYS days from the current UTC clock.
* `--all` — delete every `kitty.conf.bak.*` file.

The system MUST validate each candidate filename against the strict pattern
`kitty.conf.bak.YYYYMMDDTHHMMSSZ` before considering it for deletion;
unmatched filenames in the same directory MUST NOT be deleted. Passing two
or more policy flags simultaneously MUST exit non-zero with an error
message.

The existing `kitty-config-management` requirements stating "Old backups
MUST NOT be deleted by the install" and "Backup files themselves MUST NOT be
deleted by uninstall" remain in force; the prune subcommand is the only path
that may delete backup files, and only when the user explicitly invokes it
with `--backups`.

#### Scenario: User runs prune with no flags
- **WHEN** the user runs `my-kitty-setup prune` against a directory containing 5 `kitty.conf.bak.<ts>` files
- **THEN** stdout lists each filename with its mtime and size, prints a summary "5 backups, <total> bytes", exits 0, and the directory still contains all 5 files

#### Scenario: User runs prune --backups with no policy
- **WHEN** the user runs `my-kitty-setup prune --backups` against a directory containing 7 backup files
- **THEN** the 3 most recent (by filename timestamp) are kept, the other 4 are deleted, stdout reports the 4 deletions, and exit code is 0

#### Scenario: User runs prune --backups --keep 1
- **WHEN** the user runs `my-kitty-setup prune --backups --keep 1` against a directory containing 4 backup files
- **THEN** only the file with the lexicographically greatest `kitty.conf.bak.<ts>` filename remains, exit code is 0

#### Scenario: User runs prune --backups --older-than 30
- **WHEN** the user runs `my-kitty-setup prune --backups --older-than 30` and the directory contains backups with mtimes 5, 20, 40, and 60 days old
- **THEN** the two backups older than 30 days are deleted, the two within 30 days remain, exit code is 0

#### Scenario: User runs prune --backups --all
- **WHEN** the user runs `my-kitty-setup prune --backups --all` against a directory containing N backup files
- **THEN** all N files are deleted, stdout reports the deletions, exit code is 0, and `~/.config/kitty/kitty.conf` itself is not touched

#### Scenario: User combines two policy flags
- **WHEN** the user runs `my-kitty-setup prune --backups --keep 3 --older-than 30`
- **THEN** the command exits non-zero with an error message naming the conflicting flags, no backup is deleted

#### Scenario: Directory contains a non-backup file
- **WHEN** the user runs `my-kitty-setup prune --backups --all` against a directory containing `kitty.conf.bak.20260101T000000Z` and `my-notes.txt`
- **THEN** the backup file is deleted, `my-notes.txt` is left untouched

#### Scenario: Directory contains a malformed bak file
- **WHEN** the user runs `my-kitty-setup prune --backups --all` against a directory containing `kitty.conf.bak.notadate`
- **THEN** that file is left untouched and exit code is 0 (the file does not match the strict timestamp pattern)

#### Scenario: Directory contains zero backups
- **WHEN** the user runs `my-kitty-setup prune` (or `--backups` with any policy) against a directory containing no `kitty.conf.bak.*` files
- **THEN** stdout reports "no backups under ~/.config/kitty/" and exit code is 0

### Requirement: `make prune` orchestrates the recommended policy

The Makefile SHALL provide a `prune` target that invokes
`my-kitty-setup prune --backups --keep 3` (the recommended routine-
maintenance policy). The target MUST be at most five lines per the project
"Makefile is thin" rule.

#### Scenario: User runs make prune
- **WHEN** the user runs `make prune` after at least 4 prior `make install` runs that each produced a backup
- **THEN** the 3 most recent backups remain and the older ones are deleted, exit code is 0

#### Scenario: User wants a different policy
- **WHEN** the user wants a non-default policy (e.g. `--all` or `--older-than 60`)
- **THEN** the user invokes `my-kitty-setup prune --backups <flags>` directly; the Makefile target is the convenience for the recommended policy only


## ADDED Requirements

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

## MODIFIED Requirements

### Requirement: Uninstall strips the block cleanly

The system SHALL provide an uninstall path that removes the sentinel block
(and the marker lines themselves) from `~/.config/kitty/kitty.conf` AND
removes the `~/.config/kitty/kitty-setup/` directory AND deletes every
`kitty.conf.bak.*` file by default. If after stripping the
sentinel block the file contains no non-blank, non-comment lines, the
system SHALL replace it with the most recent `kitty.conf.bak.<ts>` if one
is present at the moment of restoration (i.e. the user passed
`--keep-backups`), else delete it.

The `--keep-backups` flag SHALL preserve every `kitty.conf.bak.*` file
without preventing the rest of the uninstall scope. The `--keep-config`
flag SHALL preserve the sentinel block, the payload directory, AND every
backup file (the entire `~/.config/kitty/` footprint we created).

#### Scenario: Default uninstall removes block, payload, AND backups
- **WHEN** the user runs `my-kitty uninstall` with no flags after a successful install that produced backups
- **THEN** the sentinel block is gone, the user's prior content above the block is preserved byte-identical, the `~/.config/kitty/kitty-setup/` directory no longer exists, AND every `kitty.conf.bak.*` file is deleted

#### Scenario: --keep-backups preserves backup files
- **WHEN** the user runs `my-kitty uninstall --keep-backups` after an install that produced two backup files
- **THEN** both backup files survive AND the sentinel block + payload directory are still removed

#### Scenario: --keep-config leaves the entire ~/.config/kitty/ footprint
- **WHEN** the user runs `my-kitty uninstall --keep-config`
- **THEN** the sentinel block is preserved, the payload directory is preserved, AND every `kitty.conf.bak.*` file is preserved

#### Scenario: Uninstall when the user's kitty.conf had no prior content and --keep-backups is set
- **WHEN** `my-kitty uninstall --keep-backups` runs on a `kitty.conf` that contained only our block, with at least one backup present
- **THEN** the file is restored from the most recent `kitty.conf.bak.<ts>`, every backup file survives, AND the parent directory is left in place

#### Scenario: Uninstall when the user's kitty.conf had no prior content and no --keep-backups
- **WHEN** `my-kitty uninstall` runs (no flags) on a `kitty.conf` that contained only our block, with at least one backup present
- **THEN** every `kitty.conf.bak.<ts>` file is deleted AND the `kitty.conf` is deleted (no file to restore from since backups went too)

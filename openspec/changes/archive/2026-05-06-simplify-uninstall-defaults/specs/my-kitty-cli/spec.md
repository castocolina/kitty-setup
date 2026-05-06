## REMOVED Requirements

### Requirement: Uninstall has three layered scopes

**Reason**: Inverted by simplify-uninstall-defaults. The pre-rename
`--kitty` / `--self` flags + the config-only default scope are replaced
by the new `Uninstall removes everything by default; opt-out flags
preserve subsets` requirement (added in this same change).

**Migration**: Users who relied on the old config-only default run
`my-kitty uninstall --keep-kitty --keep-backups` (or
`make uninstall KEEP_KITTY=1 KEEP_BACKUPS=1`) for the closest mapping.

## ADDED Requirements

### Requirement: Uninstall removes everything by default; opt-out flags preserve subsets

`my-kitty uninstall` SHALL accept three opt-in `--keep-*` flags
(`--keep-backups`, `--keep-config`, `--keep-kitty`) plus the no-flag
default scope. The default scope (no flags) SHALL strip the
sentinel-bracketed include block from the user's
`~/.config/kitty/kitty.conf`, remove the `~/.config/kitty/kitty-setup/`
payload directory, delete every `kitty.conf.bak.*` file, remove
`~/.local/kitty.app/`, remove `~/.local/bin/kitty`, and remove
`~/.local/share/applications/kitty.desktop`. Every uninstall invocation
(regardless of flags) SHALL print, AT THE END, the literal command
`uv tool uninstall my-kitty` on its own line plus a one-line description
of how to remove the sentinel-bracketed PATH block from the user's shell
rc; the binary itself is NEVER removed by the invocation.

The `--keep-backups` flag SHALL preserve every `kitty.conf.bak.*` file;
all other default-scope removals still happen. The `--keep-config` flag
SHALL preserve the config block, the payload directory, AND every
backup file (the entire `~/.config/kitty/` footprint we created); only
kitty.app + symlink + desktop entry are removed. The `--keep-kitty`
flag SHALL preserve `~/.local/kitty.app/`, the kitty symlink, and the
desktop entry; everything under `~/.config/kitty/` is still removed.
The flags compose: combining any subset preserves the union. Combining
all three reduces uninstall to a no-op that only prints the
self-removal banner.

The system MUST NOT expose `--kitty` or `--self` flags. Those flags
existed in the pre-rename design and are removed by this change.

#### Scenario: User runs uninstall with no flags
- **WHEN** the user runs `my-kitty uninstall` with no flags after a successful `make install` that produced at least one backup
- **THEN** the sentinel block in `~/.config/kitty/kitty.conf` is removed, `~/.config/kitty/kitty-setup/` is deleted, every `kitty.conf.bak.*` file under `~/.config/kitty/` is deleted, `~/.local/kitty.app/` is removed, `~/.local/bin/kitty` is removed, the desktop entry at `~/.local/share/applications/kitty.desktop` is removed, AND stdout contains the literal command `uv tool uninstall my-kitty` on its own line plus a one-line PATH-block-cleanup description, AND the binary at `~/.local/bin/my-kitty` is NOT removed

#### Scenario: --keep-backups preserves backup files only
- **WHEN** the user runs `my-kitty uninstall --keep-backups` against a host with three `kitty.conf.bak.*` files
- **THEN** all three backup files survive AND every other default-scope removal happens AND the self-removal banner prints

#### Scenario: --keep-config preserves the entire ~/.config/kitty/ footprint
- **WHEN** the user runs `my-kitty uninstall --keep-config`
- **THEN** the sentinel block stays in `~/.config/kitty/kitty.conf`, `~/.config/kitty/kitty-setup/` stays intact, every `kitty.conf.bak.*` file stays, AND `~/.local/kitty.app/` + symlink + desktop entry are still removed

#### Scenario: --keep-kitty preserves kitty.app + symlink + desktop entry
- **WHEN** the user runs `my-kitty uninstall --keep-kitty`
- **THEN** `~/.local/kitty.app/` + `~/.local/bin/kitty` + the desktop entry survive AND the config block + payload + every backup are still removed

#### Scenario: Combining --keep-backups and --keep-kitty composes
- **WHEN** the user runs `my-kitty uninstall --keep-backups --keep-kitty`
- **THEN** backups + kitty.app + symlink + desktop entry all survive AND only the config block + payload are removed

#### Scenario: Combining all three keep flags reduces uninstall to a no-op
- **WHEN** the user runs `my-kitty uninstall --keep-backups --keep-config --keep-kitty`
- **THEN** the filesystem under `~/.config/kitty/` is unchanged AND `~/.local/kitty.app/` + symlink + desktop entry are unchanged AND the self-removal banner still prints AND exit code is 0

#### Scenario: Self-removal banner prints regardless of flags
- **WHEN** the user runs `my-kitty uninstall` with any flag combination
- **THEN** stdout contains the literal command `uv tool uninstall my-kitty` on its own line followed by a one-line description of the PATH-block cleanup

#### Scenario: Legacy --kitty flag is no longer recognised
- **WHEN** a user runs `my-kitty uninstall --kitty` (pre-rename flag)
- **THEN** the command exits non-zero with an argparse error mentioning the unrecognised argument

#### Scenario: Legacy --self flag is no longer recognised
- **WHEN** a user runs `my-kitty uninstall --self` (pre-rename flag)
- **THEN** the command exits non-zero with an argparse error mentioning the unrecognised argument

## MODIFIED Requirements

### Requirement: `make` orchestrates the install and uninstall flows

The `Makefile` SHALL provide `install` and `uninstall` targets that
encapsulate the full deploy and rollback flows respectively. `make install`
SHALL run, in order: ensure `uv` is on PATH (delegating to existing
`tools/setup.sh`), run `uv sync` to provision the dev `.venv`, run
`uv tool install --force .` to provision the deployable, ensure
`~/.local/bin` is on the user's shell PATH, then invoke
`my-kitty install` to perform the kitty download + config injection.
`make uninstall` SHALL invoke `my-kitty uninstall` with no flags by
default. `tools/uninstall.sh` MAY fall back to invoking the legacy
`my-kitty-setup` binary when `my-kitty` is not yet on PATH (covers the
brief upgrade window).

The Makefile SHALL accept three opt-in env-var knobs that map 1:1 to
CLI flags: `KEEP_BACKUPS=1` adds `--keep-backups`, `KEEP_CONFIG=1` adds
`--keep-config`, `KEEP_KITTY=1` adds `--keep-kitty`. Multiple knobs
compose; setting any subset together passes the corresponding flags
together. The Makefile MUST NOT expose an `ALL=1` knob — the new
default IS the aggressive scope.

#### Scenario: Fresh `make install` from a clean machine
- **WHEN** the user clones the repo on a host with no kitty and no `~/.local/bin/my-kitty`
- **THEN** `make install` exits 0 and at the end of the run all of `~/.local/bin/my-kitty`, `~/.local/bin/kitty`, `~/.local/kitty.app/`, the desktop entry, the sentinel-bracketed include in `~/.config/kitty/kitty.conf`, and the payload at `~/.config/kitty/kitty-setup/` exist

#### Scenario: `make uninstall` with no env vars
- **WHEN** the user runs `make uninstall` after a successful `make install`
- **THEN** the entire footprint we created is removed (config block + payload + kitty.app + symlink + desktop entry + every backup file) AND the self-removal banner prints AND exit code is 0 (assuming the user types `y` at the confirm prompt or sets `KITTI_FORCE=1`)

#### Scenario: `make uninstall KEEP_BACKUPS=1`
- **WHEN** the user runs `make uninstall KEEP_BACKUPS=1`
- **THEN** every `kitty.conf.bak.*` file survives AND every other default-scope removal happens

#### Scenario: `make uninstall KEEP_BACKUPS=1 KEEP_KITTY=1` composes
- **WHEN** the user runs `make uninstall KEEP_BACKUPS=1 KEEP_KITTY=1`
- **THEN** both backups AND kitty.app + symlink + desktop entry survive

#### Scenario: Legacy `ALL=1` knob is silently ignored
- **WHEN** the user runs `make uninstall ALL=1` (legacy knob from the consolidate-era design)
- **THEN** the Makefile ignores the knob; behavior is identical to `make uninstall` with no env vars (because the new default IS the aggressive scope)

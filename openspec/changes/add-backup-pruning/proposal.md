## Why

Every `make install` that detects drift on `~/.config/kitty/kitty.conf` writes a
new `kitty.conf.bak.<UTC-ts>` next to the file. Over many upgrades the directory
fills with backup files the install never reads again. `config_updater` only
consults the SAME-PROCESS backup (rollback target on parse-check failure) and
the LATEST backup (uninstall safety net for "user content was empty"). All
older backups are pure history with no automatic prune. Users who run
`make install` weekly will accumulate 50+ files in `~/.config/kitty/` within a
year. There is no first-class command to inspect or thin out that pile.

## What Changes

- Add `my-kitty-setup prune` subcommand. With no flags it lists the count and
  total size of `kitty.conf.bak.*` files under `~/.config/kitty/` and exits 0
  without touching disk (safe-by-default dry run).
- Add `my-kitty-setup prune --backups` with three mutually-exclusive policy
  flags:
  - `--keep N` (default when only `--backups` is passed; default N is 3) —
    keep the N most recent backups by timestamp embedded in the filename,
    delete older.
  - `--older-than DAYS` — delete backups whose mtime is older than N days.
  - `--all` — delete every backup file. Most aggressive scope.
- Add `make prune` Makefile target that wraps `my-kitty-setup prune --backups
  --keep 3` (the recommended policy for routine maintenance).
- Document the new subcommand in README quickstart and in the help output (the
  argparse subparser registers `prune` automatically; `my-kitty-setup help`
  lists it without further work).

## Capabilities

### New Capabilities

(none)

### Modified Capabilities

- `kitty-config-management`: ADDS a "Backup pruning" requirement covering the
  prune subcommand's three policies plus the dry-run default. Existing
  requirements ("Old backups MUST NOT be deleted by the install" and "Backup
  files themselves MUST NOT be deleted by uninstall") remain unchanged — prune
  is an explicit, opt-in user action, distinct from install and uninstall.

## Impact

- **Edited files**: `src/kitty_setup/cli.py` (register new `prune` subparser),
  `src/kitty_setup/config_updater.py` (add `prune_backups` policy function +
  `list_backups` helper), `Makefile` (add `prune` target + `help` line update),
  `README.md` (quickstart entry).
- **New files**: `src/kitty_setup/pruner.py` (handler for the `prune`
  subcommand — keeps `installer.py` focused on install/uninstall),
  `tests/unit/test_pruner.py`.
- **No new external dependencies.** Pure stdlib: `pathlib`, `os.stat`,
  `re` (timestamp parse), `argparse`.
- **No probes required.** All operations are filesystem ops on a directory we
  own. No external CLI / API contract is being relied on.
- **Builds on top of**: `consolidate-into-my-kitty-setup-cli` (commits the
  `my-kitty-setup` single entry point + subcommand dispatcher this change
  extends). That change must commit + archive before this one applies.
- **Out of scope** (explicit non-goals):
  - Pruning anything other than `kitty.conf.bak.*`. No `tmp/`, no logs, no
    payload directory.
  - Auto-pruning during install or uninstall. Opt-in only this round.
  - Cron / systemd-timer integration.
  - Restoring a specific backup as the active `kitty.conf` (the user can do
    that with `cp` themselves; one-line operation).

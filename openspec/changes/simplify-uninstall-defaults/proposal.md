## Why

Today's `make uninstall` strips only the config block + payload directory.
`~/.local/kitty.app/`, the kitty symlink, the desktop entry, and every
`kitty.conf.bak.*` file all stay. To clean them up the user has to discover
`make uninstall ALL=1`. Most users mentally model "uninstall" as "remove
everything you put on my system", so opt-in escalation reads as the inverse
of intuition.

Reported during 2026-05-05 testing: the confirm prompt's
`Backups under ~/.config/kitty/kitty.conf.bak.* will be kept` line is
confusing because (a) backup retention should be the opt-in path, not the
default, and (b) the message prints unconditionally even when no backup
files exist on disk.

Inverting the defaults brings the interface in line with intuition. The
established `--self` print-only pattern stays intact (per consolidate D2 —
auto-self-uninstall has surprising failure modes); everything else moves to
default-on with `--keep-*` opt-outs.

## What Changes

- `my-kitty uninstall` (no flags) SHALL remove: the config block,
  the payload directory, `~/.local/kitty.app/`, the kitty symlink, the
  desktop entry, AND every `kitty.conf.bak.*` file. It SHALL print (NOT
  execute) the manual `uv tool uninstall my-kitty` self-removal command +
  the rc-file PATH cleanup line at the end of every uninstall regardless of
  flags.
- New opt-in flags compose to preserve subsets:
  - `--keep-backups` — preserve `kitty.conf.bak.*` files.
  - `--keep-config` — preserve the config block, the payload directory, and
    backups (i.e. nothing under `~/.config/kitty/` is touched). Removes
    only kitty.app + symlink + desktop entry.
  - `--keep-kitty` — preserve `~/.local/kitty.app/`, the kitty symlink, and
    the desktop entry. Removes config block + payload + backups.
- Drop `--kitty` and `--self`. `--self` print-only behavior moves to
  default. `--kitty` was opt-in to remove kitty.app; now it's the default
  and `--keep-kitty` is the opt-out.
- Rewrite `tools/uninstall.sh` confirm prompt to enumerate exactly what
  WILL be removed for the chosen flag set, dropping the always-on
  "Backups will be kept" line.
- `make uninstall` invokes `my-kitty uninstall` (no flags). New env-var
  knobs forward to flags: `KEEP_BACKUPS=1`, `KEEP_CONFIG=1`,
  `KEEP_KITTY=1`. Multiple knobs compose. Drop the `ALL=1` knob — it is
  no-op now (the new default is "all").
- Reuse `pruner.prune_all` + `pruner.delete_each` for the backup deletion
  step inside `cli_uninstall`. No new prune helper needed.
- Document the breaking change in README + the help text for both
  `my-kitty uninstall --help` and `make help`. Add a one-paragraph note
  on the upgrade ritual (`make uninstall KEEP_CONFIG=1` is the closest
  match to the legacy default for users who specifically wanted only the
  config-side teardown).

## Capabilities

### New Capabilities

(none)

### Modified Capabilities

- `my-kitty-cli`: MOD the `Uninstall has three layered scopes` requirement.
  Old form: default = config-only, `--kitty` adds kitty.app removal,
  `--self` prints the self-removal command. New form: default = remove
  everything, `--keep-backups` / `--keep-config` / `--keep-kitty` preserve
  subsets, the self-removal command prints unconditionally. Also MOD the
  `make orchestrates the install and uninstall flows` requirement to
  describe the new env-var knobs.

- `kitty-config-management`: MOD the `Uninstall strips the block cleanly`
  requirement. The existing clause "Backup files themselves MUST NOT be
  deleted by uninstall" is INVERTED — uninstall DOES delete every backup
  by default; opt-in via `--keep-backups` preserves them. The block-
  stripping mechanics + payload-removal mechanics + restore-from-backup
  branch are all unchanged. The `Backup before any mutation` requirement
  is unchanged: install never touches existing backups.

## Impact

- **Edited files**: `src/kitty_setup/installer.py` (rewrite
  `cli_uninstall` + `_SELF_REMOVAL_BANNER` semantics; the unconditional
  banner-print moves out of the `--self` branch),
  `src/kitty_setup/cli.py` (drop `--kitty` / `--self`; add
  `--keep-backups` / `--keep-config` / `--keep-kitty`),
  `tools/uninstall.sh` (rewrite confirm prompt),
  `Makefile` (replace `ALL=1` with `KEEP_*` env vars),
  `README.md` (quickstart + upgrade-ritual note),
  `CLAUDE.md` (Stack paragraph references the uninstall flow).
- **New tests**: `tests/unit/test_installer_uninstall.py` (or extend
  existing `test_installer.py` if added) covering each `--keep-*`
  combination via monkeypatched filesystem helpers.
- **Edited tests**: `tests/unit/test_cli.py` — replace the `--kitty` /
  `--self` assertions with the new flag set.
- **No new external dependencies.** Pure refactor + reuse of
  `pruner.prune_all` + `pruner.delete_each`.
- **No probes required.** All operations are filesystem ops on directories
  we own + invocation of helpers proven during prior changes' apply.
- **Breaking change** for any user who learned the current interface.
  Single-user today (just me); blast radius small. Migration: explicitly
  pass `KEEP_CONFIG=1` (or `--keep-config`) to recover the old default
  behavior.
- **Out of scope** (separate follow-up changes):
  - Auto-removing the `my-kitty` binary. Print-only stays per consolidate D2.
  - A `--dry-run` flag on uninstall. Confirm prompt + `KITTI_FORCE` cover
    the safety story.
  - Pruning anything under `~/.local/share/uv/tools/kitty-setup/`.
  - Changing `prune` subcommand semantics. `prune` (routine maintenance)
    and `uninstall` (teardown) stay distinct.
  - Fixing the `ctrl+shift+-` regression that doctor surfaces. That is
    its own change (`fix-ctrl-shift-minus-collision`).

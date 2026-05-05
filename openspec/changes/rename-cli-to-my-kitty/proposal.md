## Why

`my-kitty-setup` was a stop-gap binary name picked during the
`consolidate-into-my-kitty-setup-cli` change ("olvida fluffy, dejemos por
ahora en duro `my-kitty-setup`"). With more subcommands landing — `prune`
shipped via `add-backup-pruning`, `keys` next via the parked
`phase1-binding-introspection` change — the verbose form reads worse
every time it's typed: `my-kitty-setup doctor`, `my-kitty-setup keys`,
`my-kitty-setup prune --backups --keep 3`. Shorter is better for daily
use, and the `-setup` suffix was always semantically wrong (the binary
does install, uninstall, doctor, prune, and soon keys — "setup" only
covers one of those).

A second cleanup goes with it: the OpenSpec capability folder, currently
`openspec/specs/my-kitty-setup-cli/`, gets renamed to
`openspec/specs/my-kitty-cli/`. Capability-name drift between spec and
binary is a future-reader trap.

## What Changes

- Replace the `[project.scripts]` entry: `my-kitty = "kitty_setup.cli:main"`
  (drop `my-kitty-setup`).
- Update every code site that hard-codes the binary name: `cli.py`'s
  `PROG` constant, `installer.py`'s `_SELF_REMOVAL_BANNER` (now prints
  `uv tool uninstall my-kitty`), `path_integration.py`'s sentinel
  markers (now `# >>> my-kitty PATH >>>` / `# <<< my-kitty PATH <<<`).
- Update the bootstrap shell layer: `tools/setup.sh` looks up
  `~/.local/bin/my-kitty`; `tools/uninstall.sh`'s `resolve_binary`
  prefers `my-kitty` and falls back to `my-kitty-setup` for users
  upgrading mid-install.
- Update `Makefile`, `README.md`, and `CLAUDE.md` to use `my-kitty`
  everywhere. Tests with `PROG`/argv[0]/help-banner expectations
  updated.
- **Migration logic** in `path_integration.ensure_local_bin_in_path`:
  when the user's rc file contains the OLD marker block
  (`# >>> my-kitty-setup PATH >>>`), the function MUST recognise it as
  already configured AND rewrite the marker lines to the new form
  in-place. Without this the rc would end up with two stacked PATH
  blocks after the first `make install` post-upgrade.
- **Migration notice** in `cli_install`: when `~/.local/bin/my-kitty-setup`
  exists, print one line telling the user to run
  `uv tool uninstall my-kitty-setup` to remove it. Do NOT auto-remove
  (mirrors the print-don't-execute pattern from D2 of the consolidate
  change).
- Rename the OpenSpec capability folder
  `openspec/specs/my-kitty-setup-cli/` → `openspec/specs/my-kitty-cli/`
  via two delta specs in this change: REMOVE all 5 requirements from
  the legacy capability with `**Reason**` + `**Migration**`, and ADD
  the same 5 requirements (refreshed for the new binary name) plus 1
  new requirement (PATH block migration) to the new capability.

## Capabilities

### New Capabilities

- `my-kitty-cli`: the single-binary, subcommand-dispatched CLI for the
  whole project. Same scope as the legacy `my-kitty-setup-cli` plus the
  PATH-block migration requirement. The binary name on PATH is
  `my-kitty`. Future behavior subcommands (`keys`, scenes, themes)
  extend this capability.

### Modified Capabilities

- `my-kitty-setup-cli`: REMOVE all 5 requirements with **Reason:**
  capability renamed to `my-kitty-cli` and binary renamed to `my-kitty`,
  **Migration:** see `my-kitty-cli` requirements (same surface, new
  binary name). The legacy capability folder will be deleted after this
  change archives.

## Impact

- **Edited files**: `pyproject.toml` (entry rename), `src/kitty_setup/cli.py`
  (PROG), `src/kitty_setup/installer.py` (banner + migration notice in
  cli_install), `src/kitty_setup/path_integration.py` (markers + legacy
  marker recognition + rewrite), `Makefile`, `tools/setup.sh`,
  `tools/uninstall.sh`, `README.md`, `CLAUDE.md`,
  `tests/unit/test_cli.py`, `tests/unit/test_path_integration.py` (new
  migration cases).
- **New files**: none beyond the change directory itself.
- **Removed files**: `openspec/specs/my-kitty-setup-cli/spec.md` (after
  archive — the openspec CLI removes the directory once REMOVE deltas
  apply).
- **No new external dependencies.** Pure refactor + small migration
  helpers.
- **No probes required.** No external CLI / API contract being relied on
  for the first time.
- **Breaking change** for users with the existing `my-kitty-setup` shim:
  they must run `uv tool uninstall my-kitty-setup` (the install prints
  the line). The new binary at `~/.local/bin/my-kitty` is installed
  automatically by `make install`.
- **Out of scope** (separate follow-up changes):
  - Renaming the `kitty_setup` Python package on disk / on PyPI. The
    package layout stays; only the entry-point name changes.
  - Auto-removing the old `my-kitty-setup` shim during install. Print
    only, per D2 of consolidate.
  - The `keys` subcommand. Lives on the parked
    `phase1-binding-introspection` change, retargeted onto `my-kitty
    keys` after this archives.

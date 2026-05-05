# my-kitty-cli Specification

## Purpose
TBD - created by archiving change rename-cli-to-my-kitty. Update Purpose after archive.
## Requirements
### Requirement: Single binary on PATH with subcommand dispatch

The system SHALL expose exactly one entry point under `[project.scripts]`,
named `my-kitty`, whose `main()` parses subcommands via argparse
subparsers. The supported subcommands SHALL be `install`, `uninstall`,
`doctor`, `prune`, `keys`, and `help` (the latter implicit via
argparse). The system MUST NOT expose any other `[project.scripts]`
entry — historic entries `kitty-setup-install`, `kitty-setup-doctor`,
`kitty-setup-harness`, and `my-kitty-setup` SHALL be removed.

#### Scenario: User runs the binary with no arguments
- **WHEN** the user runs `my-kitty` with no arguments after a successful `make install`
- **THEN** the command prints the help banner listing every supported subcommand on its own line and exits 0

#### Scenario: User runs an unknown subcommand
- **WHEN** the user runs `my-kitty whatever-doesnt-exist`
- **THEN** the command prints an error mentioning the unknown subcommand and the help banner, then exits non-zero

#### Scenario: Legacy entry point name is no longer registered
- **WHEN** a user inspects `~/.local/share/uv/tools/kitty-setup/bin/` after a fresh `make install`
- **THEN** the directory contains `my-kitty` and does NOT contain `my-kitty-setup`

#### Scenario: `keys` subcommand appears in the help banner
- **WHEN** the user runs `my-kitty --help` or `my-kitty help`
- **THEN** the printed subcommand list includes `keys` alongside `install`, `uninstall`, `doctor`, `prune`, and `help`

### Requirement: Install via `uv tool install --force .`, source-independent after install

`make install` SHALL provision the deployable binary by running
`uv tool install --force .` against the source repository. The system MUST NOT
use `--editable` for this install (editable would couple the binary to the
source repo, breaking the user's "delete the repo afterwards" requirement).
After `make install` completes successfully, the source repository MAY be
moved or deleted and the installed binary at `~/.local/bin/my-kitty`
SHALL continue to function correctly.

#### Scenario: Install completes and produces a working binary on PATH
- **WHEN** the user runs `make install` on a fresh clone
- **THEN** `~/.local/bin/my-kitty` exists, `~/.local/share/uv/tools/kitty-setup/` contains a tool venv with our package source copied in, and `my-kitty help` prints the help banner

#### Scenario: Source repo is deleted after install
- **WHEN** the user moves or deletes the source repository directory after `make install`
- **THEN** invocations of `my-kitty` (any subcommand that does not itself need the source) continue to work and exit 0 on success

#### Scenario: Re-running install picks up a newer source
- **WHEN** the user updates the source (`git pull`) and re-runs `make install`
- **THEN** `uv tool install --force .` rebuilds the tool venv from the new source within sub-second latency and the new binary is on PATH

#### Scenario: Install detects a legacy `my-kitty-setup` shim
- **WHEN** the user runs `make install` on a host where `~/.local/bin/my-kitty-setup` exists from a prior install
- **THEN** the install prints a one-line notice with the literal command `uv tool uninstall my-kitty-setup` on its own line, the install still exits 0, and the legacy binary is NOT auto-removed

### Requirement: `~/.local/bin` is on PATH after install

`make install` SHALL ensure that `~/.local/bin` is on the user's interactive
shell PATH by appending an idempotent, sentinel-bracketed export line to the
user's shell rc file (`~/.zshrc` for zsh, `~/.bashrc` for bash). The block
MUST be `# >>> my-kitty PATH >>>` / `# <<< my-kitty PATH <<<`.
The system MUST NOT add the block when `~/.local/bin` is already in the
current process `$PATH` or already exported from the rc file. Re-running
`make install` MUST be a no-op for this rc edit.

#### Scenario: User's rc file already exports ~/.local/bin
- **WHEN** the user runs `make install` against a shell rc that already places `~/.local/bin` on PATH (whether via our block or any other line)
- **THEN** the rc file is not modified and the install reports "PATH: already configured" on stdout

#### Scenario: User's rc file does not export ~/.local/bin
- **WHEN** the user runs `make install` against a shell rc with no `~/.local/bin` PATH entry
- **THEN** the rc file ends with the sentinel-bracketed block and a one-line message tells the user to start a new shell or `source` the rc

#### Scenario: Unsupported shell (fish, nushell, etc.)
- **WHEN** `$SHELL` resolves to something other than zsh or bash
- **THEN** the install prints a one-line warning naming the shell and the exact line the user must add manually, and the install does NOT attempt the rc edit
- **AND** the install still exits 0 (the rc edit is best-effort, not a hard prerequisite for install success)

### Requirement: PATH block migration recognizes the legacy marker

`path_integration.ensure_local_bin_in_path` SHALL recognize a rc file
that contains the legacy sentinel marker block
(`# >>> my-kitty-setup PATH >>>` / `# <<< my-kitty-setup PATH <<<`) as
"already configured" AND SHALL rewrite the marker lines in place to the
new form (`# >>> my-kitty PATH >>>` / `# <<< my-kitty PATH <<<`) on the
same call. If both the legacy and new marker blocks are present, the
new block wins and the legacy block is removed (markers and the
`export` line between them). The function MUST NOT append a new block
when the legacy block is present.

#### Scenario: rc file has only the legacy marker block
- **WHEN** the user upgrades from a `my-kitty-setup`-era install and runs `make install`, and the rc file contains exactly one `# >>> my-kitty-setup PATH >>>` block
- **THEN** the rc file ends with a `# >>> my-kitty PATH >>>` block (markers rewritten in place), the `export PATH=...` line between markers is byte-identical, and no `# >>> my-kitty-setup PATH >>>` marker remains
- **AND** the install reports "PATH: migrated legacy marker" on stdout

#### Scenario: rc file has both legacy and new marker blocks
- **WHEN** a degenerate rc file contains both a legacy block and a new block
- **THEN** the legacy block (markers + the line between them) is removed, the new block is preserved unchanged, and the install reports "PATH: removed duplicate legacy marker" on stdout

#### Scenario: rc file has neither legacy nor new marker block
- **WHEN** the user runs `make install` against a rc file with no kitty-related PATH entry
- **THEN** the rc file ends with a fresh `# >>> my-kitty PATH >>>` block (existing fresh-install behavior, regression guard for this rename)

#### Scenario: Idempotent re-run after migration
- **WHEN** the user runs `make install` twice in a row, the first run migrating the legacy marker
- **THEN** the second run reports "PATH: already configured" and the rc file content is byte-identical to the post-first-run state

### Requirement: Uninstall has three layered scopes

`my-kitty uninstall` SHALL accept two opt-in flags `--kitty` and
`--self`, plus the no-flag default scope. The default scope (no flags)
SHALL strip the sentinel-bracketed include block from the user's
`~/.config/kitty/kitty.conf` and remove the `~/.config/kitty/kitty-setup/`
payload directory (delegating to existing `config_updater.uninstall`). The
`--kitty` flag SHALL additionally remove `~/.local/kitty.app/`,
`~/.local/bin/kitty`, and the desktop entry. The `--self` flag SHALL print
(NOT execute) the manual command `uv tool uninstall my-kitty` and a
companion message describing how to remove the sentinel-bracketed PATH
block from the user's shell rc.

#### Scenario: Default uninstall removes config only
- **WHEN** the user runs `my-kitty uninstall` with no flags
- **THEN** the sentinel block in `~/.config/kitty/kitty.conf` is removed, `~/.config/kitty/kitty-setup/` is deleted, the kitty install at `~/.local/kitty.app/` is untouched, and the binary at `~/.local/bin/my-kitty` is untouched

#### Scenario: --kitty also removes the kitty install
- **WHEN** the user runs `my-kitty uninstall --kitty`
- **THEN** the default-scope removals happen AND `~/.local/kitty.app/`, `~/.local/bin/kitty`, and `~/.local/share/applications/kitty.desktop` are removed

#### Scenario: --self prints the manual self-removal command
- **WHEN** the user runs `my-kitty uninstall --self`
- **THEN** stdout contains the literal command `uv tool uninstall my-kitty` on its own line, plus a one-line description of how to remove the PATH block from the user's shell rc, AND the binary itself is NOT removed by this invocation

### Requirement: `make` orchestrates the install and uninstall flows

The `Makefile` SHALL provide `install` and `uninstall` targets that
encapsulate the full deploy and rollback flows respectively. `make install`
SHALL run, in order: ensure `uv` is on PATH (delegating to existing
`tools/setup.sh`), run `uv sync` to provision the dev `.venv`, run
`uv tool install --force .` to provision the deployable, ensure
`~/.local/bin` is on the user's shell PATH, then invoke
`my-kitty install` to perform the kitty download + config injection.
`make uninstall` SHALL invoke `my-kitty uninstall` (default scope).
`make uninstall ALL=1` SHALL invoke `my-kitty uninstall --kitty
--self`. `tools/uninstall.sh` MAY fall back to invoking the legacy
`my-kitty-setup` binary when `my-kitty` is not yet on PATH (covers the
brief upgrade window).

#### Scenario: Fresh `make install` from a clean machine
- **WHEN** the user clones the repo on a host with no kitty and no `~/.local/bin/my-kitty`
- **THEN** `make install` exits 0 and at the end of the run all of `~/.local/bin/my-kitty`, `~/.local/bin/kitty`, `~/.local/kitty.app/`, the desktop entry, the sentinel-bracketed include in `~/.config/kitty/kitty.conf`, and the payload at `~/.config/kitty/kitty-setup/` exist

#### Scenario: `make uninstall` with no flag
- **WHEN** the user runs `make uninstall` after a successful `make install`
- **THEN** the kitty config block and payload are stripped (per `my-kitty uninstall` default scope) and kitty + the binary remain installed

#### Scenario: `make uninstall` during the upgrade window with only the legacy binary on disk
- **WHEN** the user runs `make uninstall` after upgrading to this change but before re-running `make install`, so only `~/.local/bin/my-kitty-setup` is present
- **THEN** `tools/uninstall.sh` resolves the binary to the legacy `my-kitty-setup`, logs which one it picked, and the uninstall still completes with exit 0


## ADDED Requirements

### Requirement: Single binary on PATH with subcommand dispatch

The system SHALL expose exactly one entry point under `[project.scripts]`,
named `my-kitty-setup`, whose `main()` parses subcommands via argparse
subparsers. The supported subcommands SHALL be `install`, `uninstall`,
`doctor`, and `help` (the latter implicit via argparse). The system MUST
NOT expose any other `[project.scripts]` entry — historic entries
`kitty-setup-install`, `kitty-setup-doctor`, and `kitty-setup-harness`
SHALL be removed.

#### Scenario: User runs the binary with no arguments
- **WHEN** the user runs `my-kitty-setup` with no arguments after a successful `make install`
- **THEN** the command prints the help banner listing every supported subcommand on its own line and exits 0

#### Scenario: User runs an unknown subcommand
- **WHEN** the user runs `my-kitty-setup whatever-doesnt-exist`
- **THEN** the command prints an error mentioning the unknown subcommand and the help banner, then exits non-zero

### Requirement: Install via `uv tool install --force .`, source-independent after install

`make install` SHALL provision the deployable binary by running
`uv tool install --force .` against the source repository. The system MUST NOT
use `--editable` for this install (editable would couple the binary to the
source repo, breaking the user's "delete the repo afterwards" requirement).
After `make install` completes successfully, the source repository MAY be
moved or deleted and the installed binary at `~/.local/bin/my-kitty-setup`
SHALL continue to function correctly.

#### Scenario: Install completes and produces a working binary on PATH
- **WHEN** the user runs `make install` on a fresh clone
- **THEN** `~/.local/bin/my-kitty-setup` exists, `~/.local/share/uv/tools/kitty-setup/` contains a tool venv with our package source copied in, and `my-kitty-setup help` prints the help banner

#### Scenario: Source repo is deleted after install
- **WHEN** the user moves or deletes the source repository directory after `make install`
- **THEN** invocations of `my-kitty-setup` (any subcommand that does not itself need the source) continue to work and exit 0 on success

#### Scenario: Re-running install picks up a newer source
- **WHEN** the user updates the source (`git pull`) and re-runs `make install`
- **THEN** `uv tool install --force .` rebuilds the tool venv from the new source within sub-second latency and the new binary is on PATH

### Requirement: `~/.local/bin` is on PATH after install

`make install` SHALL ensure that `~/.local/bin` is on the user's interactive
shell PATH by appending an idempotent, sentinel-bracketed export line to the
user's shell rc file (`~/.zshrc` for zsh, `~/.bashrc` for bash). The block
MUST be `# >>> my-kitty-setup PATH >>>` / `# <<< my-kitty-setup PATH <<<`.
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

### Requirement: Uninstall has three layered scopes

`my-kitty-setup uninstall` SHALL accept two opt-in flags `--kitty` and
`--self`, plus the no-flag default scope. The default scope (no flags)
SHALL strip the sentinel-bracketed include block from the user's
`~/.config/kitty/kitty.conf` and remove the `~/.config/kitty/kitty-setup/`
payload directory (delegating to existing `config_updater.uninstall`). The
`--kitty` flag SHALL additionally remove `~/.local/kitty.app/`,
`~/.local/bin/kitty`, and the desktop entry. The `--self` flag SHALL print
(NOT execute) the manual command `uv tool uninstall my-kitty-setup` and a
companion message describing how to remove the sentinel-bracketed PATH
block from the user's shell rc.

#### Scenario: Default uninstall removes config only
- **WHEN** the user runs `my-kitty-setup uninstall` with no flags
- **THEN** the sentinel block in `~/.config/kitty/kitty.conf` is removed, `~/.config/kitty/kitty-setup/` is deleted, the kitty install at `~/.local/kitty.app/` is untouched, and the binary at `~/.local/bin/my-kitty-setup` is untouched

#### Scenario: --kitty also removes the kitty install
- **WHEN** the user runs `my-kitty-setup uninstall --kitty`
- **THEN** the default-scope removals happen AND `~/.local/kitty.app/`, `~/.local/bin/kitty`, and `~/.local/share/applications/kitty.desktop` are removed

#### Scenario: --self prints the manual self-removal command
- **WHEN** the user runs `my-kitty-setup uninstall --self`
- **THEN** stdout contains the literal command `uv tool uninstall my-kitty-setup` on its own line, plus a one-line description of how to remove the PATH block from the user's shell rc, AND the binary itself is NOT removed by this invocation

### Requirement: `make` orchestrates the install and uninstall flows

The `Makefile` SHALL provide `install` and `uninstall` targets that
encapsulate the full deploy and rollback flows respectively. `make install`
SHALL run, in order: ensure `uv` is on PATH (delegating to existing
`tools/setup.sh`), run `uv sync` to provision the dev `.venv`, run
`uv tool install --force .` to provision the deployable, ensure
`~/.local/bin` is on the user's shell PATH, then invoke
`my-kitty-setup install` to perform the kitty download + config injection.
`make uninstall` SHALL invoke `my-kitty-setup uninstall` (default scope).
`make uninstall ALL=1` SHALL invoke `my-kitty-setup uninstall --kitty
--self`.

#### Scenario: Fresh `make install` from a clean machine
- **WHEN** the user clones the repo on a host with no kitty and no `~/.local/bin/my-kitty-setup`
- **THEN** `make install` exits 0 and at the end of the run all of `~/.local/bin/my-kitty-setup`, `~/.local/bin/kitty`, `~/.local/kitty.app/`, the desktop entry, the sentinel-bracketed include in `~/.config/kitty/kitty.conf`, and the payload at `~/.config/kitty/kitty-setup/` exist

#### Scenario: `make uninstall` with no flag
- **WHEN** the user runs `make uninstall` after a successful `make install`
- **THEN** the kitty config block and payload are stripped (per `my-kitty-setup uninstall` default scope) and kitty + the binary remain installed

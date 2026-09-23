# my-kitty-cli Specification

## Purpose
TBD - created by archiving change rename-cli-to-my-kitty. Update Purpose after archive.
## Requirements
### Requirement: Single binary on PATH with subcommand dispatch

The system SHALL expose exactly one entry point under `[project.scripts]`,
named `my-kitty`, whose `main()` parses subcommands via argparse
subparsers. The supported subcommands SHALL be `install`, `uninstall`,
`doctor`, `prune`, `keys`, `window`, `tab`, `os-window`, and `help` (the
latter explicitly registered via `sub.add_parser("help", ...)` with a
`set_defaults(func=…)` handler, consistent with every other subcommand).
The `window` and `tab` subcommands SHALL each host nested verbs as defined
by the `kitty-scenes` spec — `title` (from
`phase2-scene-title-primitive`), `accent` (added on `tab` by
`phase2-scene-styling`), `background` (added on `window` by
`phase2-scene-styling`). The new `os-window` top-level subcommand SHALL
host `font-size <value>` and `opacity <value>` sub-subcommands.
Additional nested verbs MAY be added by later Phase 2 changes
(§11-§12). The system MUST NOT expose any other `[project.scripts]`
entry — historic entries `kitty-setup-install`, `kitty-setup-doctor`,
`kitty-setup-harness`, and `my-kitty-setup` SHALL be removed.

The `main()` function SHALL register an `argcomplete` completion hook
between parser construction and `parse_args()` so that the parser tree
is available for shell tab completion. The source file SHALL contain
the literal `# PYTHON_ARGCOMPLETE_OK` magic comment within its first
1024 bytes so that `register-python-argcomplete` recognises the script
as completion-enabled. In normal interactive runs (without
`_ARGCOMPLETE` set in the environment) the registered hook SHALL be a
near-no-op (one env-var check, return). The `window`, `tab`, and
`os-window` subparsers — and their nested sub-subcommands — SHALL be
visible to the same argcomplete hook with no additional registration
beyond standard argparse subparser construction (i.e. autocomplete
SHALL work for `my-kitty os-window <TAB>`, `my-kitty tab accent
<TAB>`, etc. on a host with a healthy install).

Handler dispatch for the new subcommands SHALL follow the existing
`set_defaults(func=…)` pattern used by `install`, `uninstall`,
`doctor`, `prune`, `keys`, `window title`, and `tab title`. The new
sub-subcommands SHALL register handlers as follows:
- `tab accent` → `kitty_setup.scenes.accent.cli_set_tab_accent`
- `window background` → `kitty_setup.scenes.background.cli_set_window_background`
- `os-window font-size` → `kitty_setup.scenes.font.cli_set_os_window_font_size`
- `os-window opacity` → `kitty_setup.scenes.opacity.cli_set_os_window_opacity`

The specific function names are implementation detail; the requirement
is that the handlers live in the per-attribute `scenes/<attr>.py`
modules (per `kitty-scenes`) and are wired via `set_defaults(func=…)`
from inside `cli.py`'s `_build_parser()`.

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
- **THEN** the printed subcommand list includes `keys` alongside `install`, `uninstall`, `doctor`, `prune`, `window`, `tab`, `os-window`, and `help`

#### Scenario: `os-window` subcommand appears in the help banner
- **WHEN** the user runs `my-kitty --help` or `my-kitty help`
- **THEN** the printed subcommand list includes `os-window` alongside the other registered subcommands

#### Scenario: `window title` is reachable through the subparser dispatch
- **WHEN** the user runs `my-kitty window title --help`
- **THEN** argparse prints the `window title` subcommand's help (including the `<text>` positional and the `--temporary / --no-temporary`, `--match`, `--to` flags) and exits 0

#### Scenario: `tab title` is reachable through the subparser dispatch
- **WHEN** the user runs `my-kitty tab title --help`
- **THEN** argparse prints the `tab title` subcommand's help (including the `<text>` positional and the `--match`, `--to` flags; `--temporary` is intentionally absent because `kitten @ set-tab-title` does not expose it) and exits 0

#### Scenario: `tab accent` is reachable through the subparser dispatch
- **WHEN** the user runs `my-kitty tab accent --help`
- **THEN** argparse prints the `tab accent` subcommand's help (including the `<color>` positional and the `--active-fg`, `--inactive-fg`, `--match`, `--to` flags) and exits 0

#### Scenario: `window background` is reachable through the subparser dispatch
- **WHEN** the user runs `my-kitty window background --help`
- **THEN** argparse prints the `window background` subcommand's help (including the `<color>` positional and the `--match`, `--to` flags) and exits 0

#### Scenario: `os-window font-size` is reachable through the subparser dispatch
- **WHEN** the user runs `my-kitty os-window font-size --help`
- **THEN** argparse prints the `os-window font-size` subcommand's help (including the `<value>` positional and the `--all`, `--to` flags) and exits 0

#### Scenario: `os-window opacity` is reachable through the subparser dispatch
- **WHEN** the user runs `my-kitty os-window opacity --help`
- **THEN** argparse prints the `os-window opacity` subcommand's help (including the `<value>` positional and the `--toggle`, `--all`, `--to` flags) and exits 0

#### Scenario: Argcomplete hook fires when the shell requests completion
- **WHEN** a process invokes `my-kitty` with `_ARGCOMPLETE=1` set in its environment (the contract `register-python-argcomplete` uses to request completion candidates)
- **THEN** the argcomplete hook intercepts the run and emits completion candidates for the current cursor position based on the live argparse parser, without dispatching to any subcommand handler

#### Scenario: PYTHON_ARGCOMPLETE_OK magic comment is present
- **WHEN** a tool grep's the first 1024 bytes of the installed `cli.py` for `PYTHON_ARGCOMPLETE_OK`
- **THEN** the marker is present so `register-python-argcomplete my-kitty` will accept the script as completion-enabled

#### Scenario: Completion offers `window`, `tab`, and `os-window` as top-level candidates
- **WHEN** a shell with the `register-python-argcomplete` eval line active completes `my-kitty <TAB>`
- **THEN** the candidate list includes `window`, `tab`, and `os-window` alongside the other registered subcommands

#### Testing approach for CLI dispatch changes
`tests/unit/test_cli.py` SHALL be updated to cover the new subcommands
added by this change:

- The two existing help-banner tests SHALL be extended to also assert
  `os-window` appears (alongside the already-asserted `keys`, `window`,
  `tab`).
- A new test SHALL assert that `my-kitty tab accent <color>` routes to
  the correct handler in `scenes/accent.py` (following the same
  `monkeypatch` + `set_defaults` pattern as
  `test_window_title_routes_to_handler`).
- A new test SHALL assert that `my-kitty window background <color>`
  routes to the correct handler in `scenes/background.py`.
- A new test SHALL assert that `my-kitty os-window font-size <value>`
  routes to the correct handler in `scenes/font.py`. The test SHALL
  also exercise a leading-`-` value (e.g. `-2`) to confirm argparse
  accepts it as the positional `<value>` (not as an unrecognized flag).
- A new test SHALL assert that `my-kitty os-window opacity <value>
  --toggle` routes to the correct handler in `scenes/opacity.py` with
  `args.toggle is True`.

These tests cover the CLI dispatch layer; the kitten-argv ordering
invariants (especially `--toggle` BEFORE positional for opacity) are
covered by unit tests in `tests/unit/test_scenes_opacity.py` per the
`kitty-scenes` spec.

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

Inside the same sentinel-bracketed block, the system SHALL inject a
guarded `eval "$(register-python-argcomplete my-kitty)"` line so that
`my-kitty <TAB>` produces shell completion in bash and zsh. The guard
SHALL skip the eval when `register-python-argcomplete` is not on PATH
(printed via `command -v`), so that uninstall-then-reinstall windows
do not produce a "command not found" error on shell-init.

The block content SHALL be regenerated from a single template on every
install. Hosts running an older PATH-only block (no completion eval
line) SHALL have the block rewritten in place — same sentinel markers,
new content — on the next `make install`, with no second migration
window required. Re-running `make install` against a host whose block
already matches the current template MUST be a no-op for this rc edit.

#### Scenario: User's rc file already exports ~/.local/bin AND has the completion eval line
- **WHEN** the user runs `make install` against a shell rc whose sentinel block already contains both the PATH export and the `register-python-argcomplete` eval line
- **THEN** the rc file is not modified and the install reports "PATH: already configured" on stdout

#### Scenario: User's rc file does not export ~/.local/bin
- **WHEN** the user runs `make install` against a shell rc with no `~/.local/bin` PATH entry
- **THEN** the rc file ends with the sentinel-bracketed block containing both the PATH export and the guarded `register-python-argcomplete` eval line, and a one-line message tells the user to start a new shell or `source` the rc

#### Scenario: Old block (PATH-only) migrates in place to include the completion line
- **WHEN** the user runs `make install` against a shell rc whose sentinel block contains the PATH export but no completion eval line (a host on the pre-add-shell-completion block)
- **THEN** the block contents are rewritten in place between the existing markers to include both lines, the file is otherwise byte-identical, and the install reports a one-line message that the rc was updated

#### Scenario: Unsupported shell (fish, nushell, etc.)
- **WHEN** `$SHELL` resolves to something other than zsh or bash
- **THEN** the install prints a one-line warning naming the shell and the exact two lines the user must add manually (PATH export + completion eval), and the install does NOT attempt the rc edit
- **AND** the install still exits 0 (the rc edit is best-effort, not a hard prerequisite for install success)

#### Scenario: Completion eval line is guarded against missing helper
- **WHEN** the eval line runs in a shell whose PATH does not contain `register-python-argcomplete` (e.g. between an `uv tool uninstall my-kitty` and the next `make install`)
- **THEN** the guard `command -v register-python-argcomplete >/dev/null 2>&1` short-circuits and the eval is not executed, producing no error output

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

### Requirement: Doctor reports tab-completion health

`my-kitty doctor` SHALL include a check named `completion` that PASSes
iff (a) the `register-python-argcomplete` helper resolves on `$PATH`
AND (b) the user's active sentinel-bracketed shell-rc block contains a
`register-python-argcomplete my-kitty` eval line. If either condition
fails, the check SHALL FAIL and its render line SHALL describe which
condition was unmet, alongside the existing `bindings` / `kitty` /
`config` / `payload` / `parse` / `path` checks.

#### Scenario: Both conditions hold
- **WHEN** the user runs `my-kitty doctor` on a host with a healthy install AND the rc block updated by add-shell-completion
- **THEN** stdout contains a line `PASS completion: ...` and the doctor exit code is 0 (assuming all other checks also pass)

#### Scenario: register-python-argcomplete is missing from PATH
- **WHEN** the user runs `my-kitty doctor` after `uv tool uninstall my-kitty` (which removes the helper) but before reinstalling
- **THEN** stdout contains a line `FAIL completion: ...` describing that the helper is not on PATH, and the doctor exit code is non-zero

#### Scenario: rc block is missing the completion eval line
- **WHEN** the user runs `my-kitty doctor` on a host whose rc file has the PATH-only block (pre-add-shell-completion shape) but the helper IS on PATH
- **THEN** stdout contains a line `FAIL completion: ...` describing that the rc block is missing the eval line, and the doctor exit code is non-zero


## MODIFIED Requirements

### Requirement: Single binary on PATH with subcommand dispatch

The system SHALL expose exactly one entry point under `[project.scripts]`,
named `my-kitty`, whose `main()` parses subcommands via argparse
subparsers. The supported subcommands SHALL be `install`, `uninstall`,
`doctor`, `prune`, `keys`, and `help` (the latter implicit via
argparse). The system MUST NOT expose any other `[project.scripts]`
entry — historic entries `kitty-setup-install`, `kitty-setup-doctor`,
`kitty-setup-harness`, and `my-kitty-setup` SHALL be removed.

The `main()` function SHALL register an `argcomplete` completion hook
between parser construction and `parse_args()` so that the parser tree
is available for shell tab completion. The source file SHALL contain
the literal `# PYTHON_ARGCOMPLETE_OK` magic comment within its first
1024 bytes so that `register-python-argcomplete` recognises the script
as completion-enabled. In normal interactive runs (without
`_ARGCOMPLETE` set in the environment) the registered hook SHALL be a
near-no-op (one env-var check, return).

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

#### Scenario: Argcomplete hook fires when the shell requests completion
- **WHEN** a process invokes `my-kitty` with `_ARGCOMPLETE=1` set in its environment (the contract `register-python-argcomplete` uses to request completion candidates)
- **THEN** the argcomplete hook intercepts the run and emits completion candidates for the current cursor position based on the live argparse parser, without dispatching to any subcommand handler

#### Scenario: PYTHON_ARGCOMPLETE_OK magic comment is present
- **WHEN** a tool grep's the first 1024 bytes of the installed `cli.py` for `PYTHON_ARGCOMPLETE_OK`
- **THEN** the marker is present so `register-python-argcomplete my-kitty` will accept the script as completion-enabled

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

## ADDED Requirements

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

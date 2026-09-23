# Delta: my-kitty-cli

## MODIFIED Requirements

### Requirement: Single binary on PATH with subcommand dispatch

The system SHALL expose exactly one entry point under `[project.scripts]`,
named `my-kitty`, whose `main()` parses subcommands via argparse
subparsers. The supported subcommands SHALL be `install`, `uninstall`,
`doctor`, `prune`, `keys`, `window`, `tab`, and `help` (the latter
explicitly registered via `sub.add_parser("help", ...)` with a
`set_defaults(func=…)` handler, consistent with every other subcommand). The `window` and `tab` subcommands SHALL each
host a nested `title <text>` sub-subcommand (per the `kitty-scenes` spec);
additional nested verbs on `window` / `tab` MAY be added by later
Phase 2 changes (§9-§12). The system MUST NOT expose any other
`[project.scripts]` entry — historic entries `kitty-setup-install`,
`kitty-setup-doctor`, `kitty-setup-harness`, and `my-kitty-setup` SHALL be
removed.

The `main()` function SHALL register an `argcomplete` completion hook
between parser construction and `parse_args()` so that the parser tree
is available for shell tab completion. The source file SHALL contain
the literal `# PYTHON_ARGCOMPLETE_OK` magic comment within its first
1024 bytes so that `register-python-argcomplete` recognises the script
as completion-enabled. In normal interactive runs (without
`_ARGCOMPLETE` set in the environment) the registered hook SHALL be a
near-no-op (one env-var check, return). The `window` and `tab`
subparsers — and their nested `title` sub-subcommands — SHALL be
visible to the same argcomplete hook with no additional registration
beyond standard argparse subparser construction (i.e. autocomplete
SHALL work for `my-kitty window <TAB>`, `my-kitty tab <TAB>`, and
`my-kitty window title <TAB>` on a host with a healthy install).

Handler dispatch for the new subcommands SHALL follow the existing
`set_defaults(func=…)` pattern used by `install`, `uninstall`,
`doctor`, `prune`, and `keys`. The `window title` sub-subcommand
SHALL register a handler callable exported from
`src/kitty_setup/scenes/title.py` (e.g. `cli_set_window_title`); the
`tab title` sub-subcommand SHALL register a handler callable from the
same module (e.g. `cli_set_tab_title`). The specific names are
implementation detail; the requirement is that the handlers live in
`scenes/title.py` (per `kitty-scenes`) and are wired via
`set_defaults(func=…)` from inside `cli.py`'s `_build_parser()`.

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
- **THEN** the printed subcommand list includes `keys` alongside `install`, `uninstall`, `doctor`, `prune`, `window`, `tab`, and `help`

#### Scenario: `window` and `tab` subcommands appear in the help banner
- **WHEN** the user runs `my-kitty --help` or `my-kitty help`
- **THEN** the printed subcommand list includes `window` and `tab` alongside the other registered subcommands

#### Scenario: `window title` is reachable through the subparser dispatch
- **WHEN** the user runs `my-kitty window title --help`
- **THEN** argparse prints the `window title` subcommand's help (including the `<text>` positional and the `--temporary / --no-temporary`, `--match`, `--to` flags) and exits 0

#### Scenario: `tab title` is reachable through the subparser dispatch
- **WHEN** the user runs `my-kitty tab title --help`
- **THEN** argparse prints the `tab title` subcommand's help (including the `<text>` positional and the `--match`, `--to` flags; `--temporary` is intentionally absent because `kitten @ set-tab-title` does not expose it) and exits 0

#### Scenario: Argcomplete hook fires when the shell requests completion
- **WHEN** a process invokes `my-kitty` with `_ARGCOMPLETE=1` set in its environment (the contract `register-python-argcomplete` uses to request completion candidates)
- **THEN** the argcomplete hook intercepts the run and emits completion candidates for the current cursor position based on the live argparse parser, without dispatching to any subcommand handler

#### Scenario: PYTHON_ARGCOMPLETE_OK magic comment is present
- **WHEN** a tool grep's the first 1024 bytes of the installed `cli.py` for `PYTHON_ARGCOMPLETE_OK`
- **THEN** the marker is present so `register-python-argcomplete my-kitty` will accept the script as completion-enabled

#### Scenario: Completion offers `window` and `tab` as top-level candidates
- **WHEN** a shell with the `register-python-argcomplete` eval line active completes `my-kitty <TAB>`
- **THEN** the candidate list includes `window` and `tab` alongside the other registered subcommands

#### Testing approach for CLI dispatch changes
`tests/unit/test_cli.py` SHALL be updated to cover the new subcommands
added by this change:

- The two existing help-banner tests that assert
  `("install", "uninstall", "doctor", "prune", "help")` appear in
  `--help` / `help` output SHALL be extended to also assert `keys`,
  `window`, and `tab` appear.
- A new test SHALL assert that `my-kitty window title <text>` routes to
  the correct handler in `scenes/title.py` (following the same
  `monkeypatch` + `set_defaults` pattern as `test_prune_routes_to_cli_prune`).
- A new test SHALL assert that `my-kitty tab title <text>` routes to
  the correct handler in `scenes/title.py` via the same pattern.

These tests cover the CLI dispatch layer (the `cli.py` → `scenes/title.py`
wiring); the `_client.py` socket-discovery layer is covered separately by
the unit tests specified in `kitty-scenes/spec.md`.

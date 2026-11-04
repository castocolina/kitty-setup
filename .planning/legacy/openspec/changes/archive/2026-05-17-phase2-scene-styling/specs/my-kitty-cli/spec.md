# Delta: my-kitty-cli

## MODIFIED Requirements

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

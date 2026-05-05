## MODIFIED Requirements

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

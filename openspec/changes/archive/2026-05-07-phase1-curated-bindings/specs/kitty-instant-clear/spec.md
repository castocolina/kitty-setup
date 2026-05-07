## MODIFIED Requirements

### Requirement: Clear behavior is delivered via config, not a shell hook

The configuration that delivers instant clear MUST be expressible entirely in a single payload `*.conf` file under `~/.config/kitty/kitty-setup/` (loaded via the sentinel-bracketed include). The system MUST NOT depend on any shell PROMPT_COMMAND, zsh hook, or external script to achieve the clear. The specific file basename is not pinned by this requirement; the curated catalog convention (file-basename = category, see `kitty-curated-bindings`) selects the file.

#### Scenario: Config alone is sufficient
- **WHEN** an integration test boots `KittySession` with only the curated catalog appended to the session config and a vanilla `bash -c` shell launched into it
- **THEN** the existing instant-clear scenarios (screen + scrollback empty after the chord fires; subsequent input still works) pass without any shell-side configuration

## ADDED Requirements

### Requirement: Instant-clear chord does not collide with curated navigation chords

The chord bound to instant clear SHALL NOT be `ctrl+shift+h`, `ctrl+shift+j`, `ctrl+shift+k`, or `ctrl+shift+l`. Those chords are reserved for the vim-style window-navigation bindings in `kitty-curated-bindings`. The instant-clear chord MUST otherwise satisfy the `kitty-curated-bindings` rules: explicit-modifier form (`ctrl+shift+<key>`), allow-listed in `intentional-overrides.conf` if it shadows a kitty default, and reported as its own category section by `my-kitty keys`.

#### Scenario: Instant-clear chord is not on h/j/k/l
- **WHEN** the user runs `my-kitty keys --json` after install
- **THEN** the entry whose action is `combine : clear_terminal scrollback active : send_text normal,application \\x0c` (or the equivalent canonical form) has a chord whose final key is not `h`, `j`, `k`, or `l`

#### Scenario: Instant-clear behavior survives the chord move
- **WHEN** an integration test sends 50 marker lines, then triggers the new instant-clear chord
- **THEN** all existing scenarios from "A single keybinding clears screen and scrollback instantly" still pass with the new chord

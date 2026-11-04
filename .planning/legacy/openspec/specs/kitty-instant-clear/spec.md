# kitty-instant-clear Specification

## Purpose
TBD - created by archiving change bootstrap-foundation-phase1-popos. Update Purpose after archive.
## Requirements
### Requirement: A single keybinding clears screen and scrollback instantly

The system SHALL configure kitty so that one keybinding (delivered as part of the curated set) clears both the visible screen and the scrollback buffer of the active window in a single keystroke, without invoking `reset` and without a perceptible delay. After the binding fires, the screen MUST be empty above the cursor and the scrollback MUST contain no recoverable lines.

#### Scenario: Screen and scrollback are empty after the binding fires
- **WHEN** the session writes 50 unique marker lines to the active window, then triggers the clear keybinding
- **THEN** `KittySession.get_text(extent="all")` returns text that contains none of the 50 marker lines
- **AND** the call returns within 200 milliseconds of the keybinding being sent

#### Scenario: Subsequent input still works
- **WHEN** the session triggers the clear keybinding and then sends `echo post-clear`
- **THEN** `get_text(extent="all")` returns text containing `post-clear`

### Requirement: Clear behavior is delivered via config, not a shell hook

The configuration that delivers instant clear MUST be expressible entirely in a single payload `*.conf` file under `~/.config/kitty/kitty-setup/` (loaded via the sentinel-bracketed include). The system MUST NOT depend on any shell PROMPT_COMMAND, zsh hook, or external script to achieve the clear. The specific file basename is not pinned by this requirement; the curated catalog convention (file-basename = category, see `kitty-curated-bindings`) selects the file.

#### Scenario: Config alone is sufficient
- **WHEN** an integration test boots `KittySession` with only the curated catalog appended to the session config and a vanilla `bash -c` shell launched into it
- **THEN** the existing instant-clear scenarios (screen + scrollback empty after the chord fires; subsequent input still works) pass without any shell-side configuration

### Requirement: Instant-clear chord does not collide with curated navigation chords

The chord bound to instant clear SHALL NOT be `ctrl+shift+h`, `ctrl+shift+j`, `ctrl+shift+k`, or `ctrl+shift+l`. Those chords are reserved for the vim-style window-navigation bindings in `kitty-curated-bindings`. The instant-clear chord MUST otherwise satisfy the `kitty-curated-bindings` rules: explicit-modifier form (`ctrl+shift+<key>`), allow-listed in `intentional-overrides.conf` if it shadows a kitty default, and reported as its own category section by `my-kitty keys`.

#### Scenario: Instant-clear chord is not on h/j/k/l
- **WHEN** the user runs `my-kitty keys --json` after install
- **THEN** the entry whose action is `combine : clear_terminal scrollback active : send_text normal,application \\x0c` (or the equivalent canonical form) has a chord whose final key is not `h`, `j`, `k`, or `l`

#### Scenario: Instant-clear behavior survives the chord move
- **WHEN** an integration test sends 50 marker lines, then triggers the new instant-clear chord
- **THEN** all existing scenarios from "A single keybinding clears screen and scrollback instantly" still pass with the new chord


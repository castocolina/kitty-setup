## ADDED Requirements

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

The configuration that delivers instant clear MUST be expressible entirely in `config/kitty/bindings.conf` (loaded via the sentinel-bracketed include). The system MUST NOT depend on any shell PROMPT_COMMAND, zsh hook, or external script to achieve the clear.

#### Scenario: Config alone is sufficient
- **WHEN** an integration test boots `KittySession` with only `config/kitty/bindings.conf` appended to the session config and a vanilla `bash -c` shell launched into it
- **THEN** the scenarios above pass without any shell-side configuration

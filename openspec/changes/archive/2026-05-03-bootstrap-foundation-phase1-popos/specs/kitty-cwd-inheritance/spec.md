## ADDED Requirements

### Requirement: New tabs inherit the launching window's cwd

The system SHALL configure kitty so that opening a new tab from an existing window via the curated keybinding starts the new tab's shell in the same working directory as the launching window. This MUST hold whether the launching shell has changed directory since being spawned or not.

#### Scenario: New tab from /tmp inherits /tmp
- **WHEN** an autonomous test session changes directory to `/tmp` in the active window and triggers the new-tab keybinding
- **THEN** `KittySession.ls()` reports a new tab whose foreground window's `cwd` is `/tmp`

#### Scenario: New tab from a deep nested path inherits that path
- **WHEN** the session changes directory to a freshly created `tmp/cwd-test/<uuid>/` and triggers the new-tab keybinding
- **THEN** the new tab's foreground window `cwd` matches that path byte-for-byte

### Requirement: New OS windows inherit the launching window's cwd

The system SHALL configure kitty so that opening a new OS window via the curated keybinding starts the new OS window's shell in the launching window's cwd, with the same guarantees as for tabs.

#### Scenario: New OS window inherits cwd
- **WHEN** the session triggers the new-OS-window keybinding from a window in `/tmp`
- **THEN** `KittySession.ls()` reports an additional OS window whose first window's `cwd` is `/tmp`

### Requirement: New splits inherit the launching window's cwd

The system SHALL configure kitty so that opening a new split (window within the current tab) via the curated keybinding starts the split's shell in the launching window's cwd.

#### Scenario: New split inherits cwd
- **WHEN** the session triggers the new-split keybinding from a window in `/tmp`
- **THEN** `KittySession.ls()` reports an additional window in the same tab whose `cwd` is `/tmp`

### Requirement: cwd inheritance behavior is delivered via config, not a wrapper script

The configuration that delivers cwd inheritance MUST be expressible entirely in `config/kitty/windowing.conf` (loaded via the sentinel-bracketed include). The system MUST NOT require a shell wrapper, a kitten, or remote-control round-trip to achieve cwd inheritance.

#### Scenario: Config alone is sufficient
- **WHEN** an integration test boots `KittySession` with only `config/kitty/windowing.conf` appended to the session config
- **THEN** all three scenarios above pass without any additional setup

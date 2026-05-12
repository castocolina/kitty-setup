## MODIFIED Requirements

### Requirement: New splits inherit the launching window's cwd

The system SHALL configure kitty so that opening a new window (split) in the current tab via the curated `ctrl+shift+enter` chord starts the new window's shell in the launching window's cwd. The placement of the new window within the tab is governed by kitty's active layout (and is changed by the user via `ctrl+shift+l`, kitty's default `next_layout`) — the curated binding does NOT pin `--location=vsplit` or `--location=hsplit`, and SHALL NOT depend on `enabled_layouts splits` being set.

#### Scenario: New window from ctrl+shift+enter inherits cwd
- **WHEN** the session triggers `ctrl+shift+enter` from a window in `/tmp`
- **THEN** `KittySession.ls()` reports an additional window in the same tab whose `cwd` is `/tmp`

#### Scenario: Placement follows the active layout, not a directional chord
- **WHEN** the session is running under kitty's default layout order (e.g. `tall`, `splits`, `stack`, or whichever kitty selects first)
- **AND** the session triggers `ctrl+shift+enter` to open a new window
- **THEN** the new window's placement matches what kitty's active layout produces for `new_window` — no curated binding requires a specific orientation

## REMOVED Requirements

### Requirement: New splits inherit the launching window's cwd (vsplit/hsplit chord pair)

**Reason:** The pre-change requirement implicitly assumed two split chords (`ctrl+shift+\` and `ctrl+shift+/`) with `--location=vsplit`/`hsplit`. Without `enabled_layouts splits` pinned (which the catalog deliberately does not set, per the user's preference for kitty's layout-cycle workflow), `--location=vsplit`/`hsplit` is silently ignored — the two chords collapsed to the same observable behaviour as `ctrl+shift+enter` while costing `search_scrollback` on `ctrl+shift+/`. Replacing this requirement with the single-chord version above eliminates the broken contract.

**Migration:** Tests or harnesses that asserted on the `vsplit`/`hsplit` chord names MUST switch to asserting on `ctrl+shift+enter` only. The `KittySession.ls()` post-condition (new window in the same tab with inherited cwd) is unchanged.

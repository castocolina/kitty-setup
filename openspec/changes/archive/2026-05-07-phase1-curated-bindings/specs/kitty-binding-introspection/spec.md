## MODIFIED Requirements

### Requirement: Distinguish intentional overrides from real conflicts

The system SHALL flag a chord as a real conflict when any of the following
hold: (a) two of our bindings target the same chord with **different**
actions, (b) three or more definitions target the same chord, or (c) one of
our bindings shadows a kitty default whose chord is NOT listed in
`~/.config/kitty/kitty-setup/intentional-overrides.conf`. A chord whose only
collision is between one of our bindings and a kitty default whose chord IS
in that allow-list SHALL be reported as an intentional override
(annotated `[overrides default <action>]`), not as a conflict.

When kitty's parsed keymap returns two entries for the same chord with the
**same** action — one originating from kitty's defaults and one from our
payload (the "redundant rebind for category attribution" case described in
the `kitty-curated-bindings` design D5) — the system SHALL attribute exactly
one entry to our payload source and exactly one entry to `kitty-default`,
and SHALL report the chord as an intentional override (not as a self-collision
of "two of ours") provided the chord is allow-listed. The deduplication is
per `(chord, action)`: each pair is consumed from the payload map at most
once, so duplicate entries with the same action fall through to
`kitty-default` for source attribution.

The intentional-overrides file is plain text, one chord per line (with
`#`-prefixed comment lines allowed). Format example: `ctrl+shift+t`,
`ctrl+shift+n`. The file is shipped from `config/kitty/intentional-overrides.conf`
to `~/.config/kitty/kitty-setup/intentional-overrides.conf` by the same
config injection that ships the binding files.

#### Scenario: Allow-listed override is reported as override, not conflict
- **WHEN** the report enumerates a chord like `ctrl+shift+t` that is listed
  in `intentional-overrides.conf` and shadows the kitty default `new_tab`
- **THEN** the report annotates it `[overrides default new_tab]`
- **AND** the chord does NOT count toward the `conflicts` summary total

#### Scenario: Non-allow-listed shadow is reported as a conflict
- **WHEN** the report enumerates a chord like `ctrl+shift+-` that shadows a
  kitty default but is not listed in `intentional-overrides.conf`
- **THEN** the report annotates it `[CONFLICT: kitty default <action>]`
- **AND** the chord counts toward the `conflicts` summary total

#### Scenario: Two of our bindings collide
- **WHEN** the report enumerates a chord that appears as a `map` line in two
  different payload files (or twice in the same file) with **different**
  actions
- **THEN** the report annotates each entry with `[CONFLICT: also defined in <other file>]`
- **AND** the chord counts toward the `conflicts` summary total regardless
  of allow-list membership

#### Scenario: Same-action redundant rebind is reported as override
- **WHEN** kitty's parsed keymap contains two entries for `ctrl+shift+.` both
  with action `move_tab_forward`, the chord is listed in
  `intentional-overrides.conf`, and `tab-nav.conf` contains a `map` line
  `ctrl+shift+. move_tab_forward`
- **THEN** the report annotates the chord `[overrides default move_tab_forward]`
- **AND** the chord is attributed to source `tab-nav` (exactly one entry)
  and to `kitty-default` (exactly one entry)
- **AND** the chord does NOT count toward the `conflicts` summary total

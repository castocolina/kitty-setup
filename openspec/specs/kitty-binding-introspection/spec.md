# kitty-binding-introspection Specification

## Purpose
TBD - created by archiving change phase1-binding-introspection. Update Purpose after archive.
## Requirements
### Requirement: Enumerate every active binding from the parsed kitty config

The system SHALL provide a `keys` subcommand of the `my-kitty` CLI
(`my-kitty keys`) that loads
the user's effective kitty configuration via `kitty +runpy` and emits, for
every chord active in the default keyboard mode, a record containing: the
human-readable chord (e.g. `ctrl+shift+t`), the action string (e.g.
`launch --type=tab --cwd=current`), the source file the binding was authored
in (one of our payload files, or the literal `kitty-default`), and any
`override_of` / `conflicts_with` annotations explained below.

The default output is grouped plain text (one section per source file, plus
a `kitty defaults` section, plus a one-line summary). When the `--json` flag
is passed, the system SHALL emit a single JSON document with the same data
suitable for machine consumption.

#### Scenario: Plain-text report on a healthy install
- **WHEN** a user runs `my-kitty keys` after `make install`
- **THEN** stdout contains a `windowing (N bindings)` section with each of our
  windowing bindings on its own line, a `bindings (N bindings)` section with
  the clear-screen binding, a `kitty defaults (N bindings)` section, and a
  trailing `Summary:` line with the totals
- **AND** the process exits 0 even when intentional overrides are present

#### Scenario: JSON output for machine consumers
- **WHEN** a user runs `my-kitty keys --json`
- **THEN** stdout contains a single parseable JSON document with a `bindings`
  list (each item has the chord, action, source, override_of, conflicts_with
  fields) and a `summary` object with `ours`, `defaults`, and `conflicts` counts
- **AND** the JSON document is the only thing on stdout (no log lines, no banners)

### Requirement: Attribute each binding to its source file by manual config-file walk

The system SHALL determine the source file for each active binding by reading
the files under `~/.config/kitty/kitty-setup/` directly (regex-matching `^\s*map\s+\S+\s+.+$`)
and matching the parsed `(chord, action)` pair from the kitty config load
against the files. Any binding present in the parsed keymap but not present
in any of our payload files SHALL be labelled `kitty-default`. The system
MUST NOT rely on `KeyDefinition.definition_location` for source attribution
(the field is reset to empty after parse — see probe 03).

#### Scenario: A binding from windowing.conf is attributed to "windowing"
- **WHEN** the report enumerates a binding whose `(chord, action)` pair matches
  a `map` line in `~/.config/kitty/kitty-setup/windowing.conf`
- **THEN** the binding's `source` is the literal string `windowing` (the file
  basename minus the `.conf` suffix)

#### Scenario: A binding not in any payload file is labelled "kitty-default"
- **WHEN** the report enumerates a binding present in the parsed keymap but
  not in any `~/.config/kitty/kitty-setup/*.conf` file
- **THEN** the binding's `source` is the literal string `kitty-default`

### Requirement: Distinguish intentional overrides from real conflicts

The system SHALL flag a chord as a real conflict when any of the following
hold: (a) two of our bindings target the same chord, (b) three or more
definitions target the same chord, or (c) one of our bindings shadows a
kitty default whose chord is NOT listed in
`~/.config/kitty/kitty-setup/intentional-overrides.conf`. A chord whose only
collision is between one of our bindings and a kitty default whose chord IS
in that allow-list SHALL be reported as an intentional override
(annotated `[overrides default <action>]`), not as a conflict.

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
  different payload files (or twice in the same file)
- **THEN** the report annotates each entry with `[CONFLICT: also defined in <other file>]`
- **AND** the chord counts toward the `conflicts` summary total regardless
  of allow-list membership

### Requirement: Read-only — no system mutations

The introspection command SHALL NOT modify any file under `~/.config/`,
`~/.local/`, or anywhere else outside its own stdout/stderr. It MUST be
safe to run repeatedly without side effects.

#### Scenario: Repeated runs leave the filesystem unchanged
- **WHEN** a user runs `my-kitty keys` twice in succession
- **THEN** no file under `~/.config/kitty/` or `~/.local/` is modified
- **AND** both runs produce byte-identical output (assuming no concurrent edits)

### Requirement: Chord rendering is normalised

The system SHALL render chords in a canonical, explicit-modifier form
(`ctrl+shift+t`, never `kitty_mod+t`) so the same chord is reported
identically regardless of how it was authored. Modifier ordering MUST be
deterministic (`ctrl` before `shift` before `alt` before `super`).

#### Scenario: kitty_mod-style and explicit-modifier author the same chord
- **WHEN** one binding is authored as `map kitty_mod+t ...` and another as
  `map ctrl+shift+t ...` (with `kitty_mod = ctrl+shift` in effect)
- **THEN** the report renders both chords as the same string `ctrl+shift+t`
- **AND** the report flags them as colliding under the conflict rule above


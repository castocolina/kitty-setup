# kitty-curated-bindings Specification

## Purpose
TBD - created by archiving change phase1-curated-bindings. Update Purpose after archive.
## Requirements
### Requirement: Pin kitty_mod for cross-OS chord parity

The system SHALL pin `kitty_mod ctrl+shift` in `~/.config/kitty/kitty-setup/kitty-setup.conf` so every curated binding resolves to the same literal chord on Linux and macOS regardless of kitty's per-OS default modifier. The pin SHALL be authored once at the top of the managed entry file, before any `include` line. Curated bindings SHALL be authored using explicit-modifier form (`ctrl+shift+<key>`) rather than `kitty_mod+<key>`, so the chord is unambiguous when read by humans and by `my-kitty keys`.

#### Scenario: Pin is present in the managed entry
- **WHEN** the user runs `make install` and inspects `~/.config/kitty/kitty-setup/kitty-setup.conf`
- **THEN** the file contains exactly one `kitty_mod ctrl+shift` directive, on its own line, before any `include` directive

#### Scenario: A curated chord renders identically on Linux and macOS
- **WHEN** the same curated binding (e.g. `ctrl+shift+]` for next-tab) is loaded by kitty on Linux and on macOS
- **THEN** `my-kitty keys --json` reports the chord as the literal string `ctrl+shift+]` on both hosts

### Requirement: Curated catalog covers six categories

The payload SHALL ship one `.conf` file per binding category under `~/.config/kitty/kitty-setup/`, with the file basename matching the category name reported by `my-kitty keys`. The required categories are:

* `tab-nav` — next tab, previous tab, move tab left, move tab right, close tab.
* `window-nav` — vim-style focus to the neighbouring window left / down / up / right (`h` / `j` / `k` / `l`), close window, focus next window in tab.
* `font-zoom` — increase font size, decrease font size, reset font size.
* `detach` — detach current window to a new tab, detach current tab to a new OS window.
* `broadcast` — toggle input broadcast across all windows in the active tab.
* `url-hints` — open URL under hints (`open_url_with_hints`).

Each category file SHALL contain at least one `map` line. Each `map` line SHALL be authored with an explicit `ctrl+shift+<key>` chord (no `kitty_mod+` shorthand). Each chord that shadows a kitty default SHALL be present in `intentional-overrides.conf` with a comment explaining the override.

#### Scenario: All six category files ship under the payload dir
- **WHEN** the user runs `make install` and lists `~/.config/kitty/kitty-setup/`
- **THEN** the listing contains `tab-nav.conf`, `window-nav.conf`, `font-zoom.conf`, `detach.conf`, `broadcast.conf`, and `url-hints.conf`, each with at least one `map` line

#### Scenario: Each category appears as its own section in the binding report
- **WHEN** the user runs `my-kitty keys` after install
- **THEN** the report contains one section per category file, named after the file basename, listing every binding authored in that file

#### Scenario: Every shadow is allow-listed
- **WHEN** the user runs `my-kitty keys` after install
- **THEN** the `Summary:` line reports `0 conflicts`, every chord that shadows a kitty default is annotated `[overrides default <action>]`, and `make doctor` exits 0

### Requirement: Tab navigation chords

The `tab-nav.conf` file SHALL bind, at minimum:

* next tab — `next_tab` action.
* previous tab — `previous_tab` action.
* move tab left — `move_tab_backward` action.
* move tab right — `move_tab_forward` action.
* close tab — `close_tab` action.

Each chord SHALL be of the form `ctrl+shift+<key>` and SHALL NOT collide with any chord defined in any other category file or in `windowing.conf` / `clear.conf`.

#### Scenario: Five tab-nav chords are active and reported
- **WHEN** the user runs `my-kitty keys --json` after install
- **THEN** the `bindings` list contains exactly five entries with `source: "tab-nav"`, whose actions are `next_tab`, `previous_tab`, `move_tab_backward`, `move_tab_forward`, and `close_tab`
- **AND** none of those five chords appears in any other source file's section

### Requirement: Window/split navigation chords

The `window-nav.conf` file SHALL bind, at minimum:

* focus left window — `neighboring_window left`.
* focus down window — `neighboring_window down`.
* focus up window — `neighboring_window up`.
* focus right window — `neighboring_window right`.
* close window — `close_window` action.
* focus next window in tab — `next_window` action.

Vim-style direction chords SHALL use the literal letter keys `h`, `j`, `k`, `l` under the pinned modifier. The chords SHALL NOT collide with the cwd-inheriting creator chords already shipped in `windowing.conf`.

#### Scenario: Vim direction chords land on h/j/k/l
- **WHEN** the user runs `my-kitty keys --json` after install
- **THEN** the report contains four `window-nav` entries whose chords are `ctrl+shift+h`, `ctrl+shift+j`, `ctrl+shift+k`, `ctrl+shift+l`, with actions `neighboring_window left`, `neighboring_window down`, `neighboring_window up`, `neighboring_window right` respectively
- **AND** none of those four chords appears in `windowing` or `clear` sections

#### Scenario: Window-nav does not collide with instant-clear
- **WHEN** the curated catalog is installed with `clear.conf` containing the instant-clear binding (chord `ctrl+shift+x` after the §1 chord move)
- **THEN** `my-kitty keys` reports `ctrl+shift+k` under `window-nav` (vim-up) and `ctrl+shift+x` under `clear`, with no collision between them — the §1 chord move from `ctrl+shift+k` to `ctrl+shift+x` is the prerequisite that makes window-nav vim-up land cleanly

### Requirement: Font zoom chords

The `font-zoom.conf` file SHALL bind, at minimum:

* increase font size — `change_font_size all +2.0`.
* decrease font size — `change_font_size all -2.0`.
* reset font size — `change_font_size all 0`.

The decrease-font chord SHALL NOT be `ctrl+shift+-` — that chord is shadowed by `windowing.conf`'s horizontal-split binding and must remain free for split usage.

#### Scenario: Font zoom triplet is present and chord-distinct
- **WHEN** the user runs `my-kitty keys --json` after install
- **THEN** the `font-zoom` section lists three bindings whose actions are `change_font_size all +2.0`, `change_font_size all -2.0`, and `change_font_size all 0`
- **AND** the decrease-font chord is not `ctrl+shift+-`

### Requirement: Detach chords

The `detach.conf` file SHALL bind:

* detach window to a new tab — `detach_window new-tab` (or kitty-supported equivalent that prompts the user for target).
* detach tab to a new OS window — `detach_tab new-os-window` (or kitty-supported equivalent).

#### Scenario: Detach pair is present
- **WHEN** the user runs `my-kitty keys --json` after install
- **THEN** the `detach` section lists at least two bindings whose actions begin with `detach_window` and `detach_tab` respectively

### Requirement: Broadcast chord

The `broadcast.conf` file SHALL bind one chord that toggles input broadcast to every window in the active tab. The implementation SHOULD use kitty's documented mechanism for this behaviour (e.g. `launch --allow-remote-control kitten broadcast`, or a remote-control-driven equivalent). The exact action string is not constrained, but the binding MUST be a single chord — no chord sequence — and MUST appear in `my-kitty keys` under the `broadcast` section.

#### Scenario: Broadcast section has at least one chord
- **WHEN** the user runs `my-kitty keys --json` after install
- **THEN** the `bindings` list contains at least one entry with `source: "broadcast"`

### Requirement: URL hints chord

The `url-hints.conf` file SHALL bind one chord to `open_url_with_hints`.

#### Scenario: URL hints chord is present
- **WHEN** the user runs `my-kitty keys --json` after install
- **THEN** the `bindings` list contains exactly one entry with `source: "url-hints"` whose action is `open_url_with_hints`

### Requirement: Linux-first delivery, macOS-deferred-with-note

Each category SHALL ship with a Linux-verified manual repro under `docs/repro/h<NN>-bindings-<category>.md`. The repro doc SHALL include a `## macOS Status` section that is either `verified` (with the macOS kitty version and date) or `deferred` (with a one-paragraph reason — e.g. no access to a Mac, blocked on a kitty surface bug). A `deferred` macOS Status SHALL NOT block merge of the category, but the catalog as a whole SHALL NOT be declared "Phase 1 §5 complete" until every category is `verified` on macOS.

#### Scenario: Every category has a Linux-verified repro doc with macOS status
- **WHEN** the change merges
- **THEN** every category file under `config/kitty/` has a corresponding `docs/repro/h<NN>-bindings-<category>.md` with a Linux verification section dated and a `## macOS Status` section whose value is `verified` or `deferred`

#### Scenario: Phase 1 §5 closure gate
- **WHEN** the user later runs `openspec list` to check Phase 1 progress
- **THEN** `phase1-curated-bindings` is not declared closed for §5 unless every category's macOS Status is `verified`


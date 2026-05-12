## MODIFIED Requirements

### Requirement: Pin kitty_mod for cross-OS chord parity

The system SHALL pin `kitty_mod ctrl+shift` in `~/.config/kitty/kitty-setup/kitty-setup.conf` so every curated binding resolves to the same literal chord on Linux and macOS regardless of kitty's per-OS default modifier — with one carve-out: the instant-clear chord (delivered via `clear.conf` per the `kitty-instant-clear` capability) matches host-OS iTerm convention and therefore diverges per OS by design (`super+k` on Linux, `cmd+k` on macOS). Every other curated chord SHALL render identically on Linux and macOS. The pin SHALL be authored once at the top of the managed entry file, before any `include` line. Curated bindings SHALL be authored using explicit-modifier form (`ctrl+shift+<key>`) rather than `kitty_mod+<key>`, so the chord is unambiguous when read by humans and by `my-kitty keys`.

#### Scenario: Pin is present in the managed entry
- **WHEN** the user runs `make install` and inspects `~/.config/kitty/kitty-setup/kitty-setup.conf`
- **THEN** the file contains exactly one `kitty_mod ctrl+shift` directive, on its own line, before any `include` directive

#### Scenario: A non-clear curated chord renders identically on Linux and macOS
- **WHEN** the same curated binding (e.g. `ctrl+shift+t` for new-tab-with-cwd) is loaded by kitty on Linux and on macOS
- **THEN** `my-kitty keys --json` reports the chord as the literal string `ctrl+shift+t` on both hosts

#### Scenario: The instant-clear chord diverges per OS
- **WHEN** the curated catalog is installed on Linux
- **THEN** `my-kitty keys --json` reports an instant-clear binding whose chord starts with `super+` on Linux, and `cmd+` on macOS
- **AND** the fallback chord `ctrl+shift+alt+k` is also reported as an instant-clear binding on both hosts

### Requirement: Curated catalog covers seven categories

The payload SHALL ship one `.conf` file per binding category under `~/.config/kitty/kitty-setup/`, with the file basename matching the category name reported by `my-kitty keys`. The required categories are:

* `windowing` — open new tab / OS-window / window (split) with cwd inheritance.
* `clear` — instant clear of screen and scrollback (host-OS native chord).
* `tab-nav` — next tab, previous tab, move tab left, move tab right, close tab.
* `window-nav` — focus next window, focus previous window, move window forward, close window.
* `font-zoom` — increase font size, decrease font size, reset font size.
* `detach` — detach current window to a new tab, detach current tab to a new OS window.
* `broadcast` — toggle input broadcast across all windows in the active tab.
* `url-hints` — open URL under hints (`open_url_with_hints`).

Each category file SHALL contain at least one `map` line. Each `map` line SHALL be authored with an explicit chord (no `kitty_mod+` shorthand). Wherever a category overlaps with kitty's own defaults, the curated `map` line SHALL restate the kitty default verbatim (redundant rebind for `my-kitty keys` category attribution) rather than introduce a new action on the same chord. Each chord that semantically overrides a kitty default — i.e. binds a different action than kitty's default for the same chord — SHALL be present in `intentional-overrides.conf` with a comment explaining the override.

#### Scenario: All seven category files ship under the payload dir
- **WHEN** the user runs `make install` and lists `~/.config/kitty/kitty-setup/`
- **THEN** the listing contains `windowing.conf`, `clear.conf`, `tab-nav.conf`, `window-nav.conf`, `font-zoom.conf`, `detach.conf`, `broadcast.conf`, and `url-hints.conf`, each with at least one `map` line

#### Scenario: Each category appears as its own section in the binding report
- **WHEN** the user runs `my-kitty keys` after install
- **THEN** the report contains one section per category file, named after the file basename, listing every binding authored in that file

#### Scenario: Every semantic override is allow-listed
- **WHEN** the user runs `my-kitty keys` after install
- **THEN** the `Summary:` line reports `0 conflicts`, every chord that semantically overrides a kitty default is annotated `[overrides default <action>]`, and `make doctor` exits 0

### Requirement: Tab navigation chords

The `tab-nav.conf` file SHALL bind, at minimum:

* next tab — `next_tab` action on `ctrl+shift+right` (kitty default chord).
* previous tab — `previous_tab` action on `ctrl+shift+left` (kitty default chord).
* move tab right — `move_tab_forward` action on `ctrl+shift+.` (kitty default chord).
* move tab left — `move_tab_backward` action on `ctrl+shift+,` (kitty default chord).
* close tab — `close_tab` action on `ctrl+shift+q` (kitty default chord).

Each binding SHALL be a redundant rebind of kitty's default — the file's purpose is `my-kitty keys` category attribution, not semantic override. The chords `ctrl+shift+]` and `ctrl+shift+[` SHALL NOT appear in `tab-nav.conf`; those chords are owned by `window-nav.conf` (kitty's own next_window/previous_window defaults).

#### Scenario: Five tab-nav chords are active, on kitty's default chords, and reported
- **WHEN** the user runs `my-kitty keys --json` after install
- **THEN** the `bindings` list contains exactly five entries with `source: "tab-nav"`, whose chords are `ctrl+shift+right`, `ctrl+shift+left`, `ctrl+shift+.`, `ctrl+shift+,`, and `ctrl+shift+q`, and whose actions are `next_tab`, `previous_tab`, `move_tab_forward`, `move_tab_backward`, and `close_tab`
- **AND** none of those five chords appears in any other source file's section

#### Scenario: ] and [ are NOT in tab-nav
- **WHEN** the user runs `my-kitty keys --json` after install
- **THEN** no entry with `source: "tab-nav"` has chord `ctrl+shift+]` or `ctrl+shift+[`

### Requirement: Window/split navigation chords

The `window-nav.conf` file SHALL bind, at minimum:

* focus next window — `next_window` action on `ctrl+shift+]` (kitty default chord).
* focus previous window — `previous_window` action on `ctrl+shift+[` (kitty default chord).
* move window forward — `move_window_forward` action on `ctrl+shift+f` (kitty default chord).
* close window — `close_window` action on `ctrl+shift+w` (kitty default chord).

Each binding SHALL be a redundant rebind of kitty's default. The file SHALL NOT bind vim-style direction chords (`ctrl+shift+h`, `ctrl+shift+j`, `ctrl+shift+k`, `ctrl+shift+l`) — those chords are released to their kitty defaults (`show_scrollback`, `scroll_line_down`, `scroll_line_up`, `next_layout`). The file SHALL NOT use `neighboring_window` as an action.

#### Scenario: Window-nav holds four redundant rebinds on kitty default chords
- **WHEN** the user runs `my-kitty keys --json` after install
- **THEN** the report contains exactly four `window-nav` entries whose chords are `ctrl+shift+]`, `ctrl+shift+[`, `ctrl+shift+f`, and `ctrl+shift+w`, with actions `next_window`, `previous_window`, `move_window_forward`, and `close_window` respectively
- **AND** the `Summary:` line shows those entries as `[redundant rebind of kitty default]`, not as `[overrides default <action>]`

#### Scenario: hjkl are released back to kitty defaults
- **WHEN** the user runs `kitty +runpy 'from kitty.fast_data_types import current_os_window; print(...)'` or equivalent kitty-keymap inspection after install
- **THEN** the chord `ctrl+shift+h` resolves to `show_scrollback`, `ctrl+shift+j` resolves to `scroll_line_down`, `ctrl+shift+k` resolves to `scroll_line_up`, and `ctrl+shift+l` resolves to `next_layout` — kitty's own defaults, with no curated binding shadowing them

### Requirement: Font zoom chords

The `font-zoom.conf` file SHALL bind, at minimum:

* increase font size — `change_font_size all +2.0` on `ctrl+shift+=` (kitty default chord).
* decrease font size — `change_font_size all -2.0` on `ctrl+shift+-` (kitty default chord).
* reset font size — `change_font_size all 0` on `ctrl+shift+backspace` (kitty default chord).

Each binding SHALL be a redundant rebind of kitty's default. The file SHALL NOT bind `ctrl+shift+0` to font reset — that chord is released to its kitty default (`tenth_window`).

#### Scenario: Font zoom triplet is on kitty default chords
- **WHEN** the user runs `my-kitty keys --json` after install
- **THEN** the `font-zoom` section lists three bindings whose chords are `ctrl+shift+=`, `ctrl+shift+-`, and `ctrl+shift+backspace`, with actions `change_font_size all +2.0`, `change_font_size all -2.0`, and `change_font_size all 0`
- **AND** the `Summary:` line shows those entries as `[redundant rebind of kitty default]`

#### Scenario: ctrl+shift+0 is released to tenth_window
- **WHEN** kitty's keymap is inspected after install
- **THEN** the chord `ctrl+shift+0` resolves to kitty's default `tenth_window`

### Requirement: Windowing chords (cwd-inheriting creators)

The `windowing.conf` file SHALL bind, at minimum:

* new tab in current OS window, in the launching window's cwd — `launch --type=tab --cwd=current` on `ctrl+shift+t`.
* new OS window, in the launching window's cwd — `launch --type=os-window --cwd=current` on `ctrl+shift+n`.
* new window (split) in the current tab, in the launching window's cwd — `launch --cwd=current` on `ctrl+shift+enter`.

The file SHALL NOT bind any chord to `launch --location=vsplit` or `launch --location=hsplit`. Users who want directional split control SHALL use kitty's compose model: open a new window with `ctrl+shift+enter`, then cycle the layout with `ctrl+shift+l` (kitty default `next_layout`, released back to kitty per the window-nav requirement above).

#### Scenario: Three cwd-inheriting creators are active, no vsplit/hsplit chords
- **WHEN** the user runs `my-kitty keys --json` after install
- **THEN** the `windowing` section lists exactly three bindings whose chords are `ctrl+shift+t`, `ctrl+shift+n`, and `ctrl+shift+enter`
- **AND** no entry in any section has action `launch --location=vsplit` or `launch --location=hsplit`

## REMOVED Requirements

### Requirement: Curated catalog covers six categories

**Reason:** Replaced by the seven-category requirement above (adds `windowing` and `clear` to the explicit enumeration; the original six were tab-nav/window-nav/font-zoom/detach/broadcast/url-hints).

**Migration:** N/A — the categories themselves continue to ship; only the requirement text widens to include `windowing` and `clear` and pins them per-category.

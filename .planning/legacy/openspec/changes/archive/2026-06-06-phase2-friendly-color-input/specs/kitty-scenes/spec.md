## ADDED Requirements

### Requirement: Color inputs are normalized and validated by `my-kitty`

`my-kitty` SHALL pass every user-supplied color through a single shared
normalizer `normalize_color(value) -> str` (in
`src/kitty_setup/scenes/colors.py`) before any `kitten @` call. This covers the
`<color>` of `my-kitty tab accent` and `my-kitty window background`, the
`--active-fg`/`--inactive-fg` overrides, the inline scene `--pane 'bg=...'` and
`--tab-accent=...`, and the TOML `bg` / `tab_accent` keys. The call sites SHALL
import and reuse this one normalizer; none SHALL re-implement color parsing.

`normalize_color` SHALL resolve a value in this order:

1. An empty string normalizes to **absent** (`None`), unchanged from the inline
   pane parser and recipe loader.
2. A value matching `^#?[0-9a-fA-F]{3}$` or `^#?[0-9a-fA-F]{6}$` is **hex**: it
   is returned with a leading `#` added if missing (so the bare `fff` / `000` /
   `1a2b3c` a user types is accepted). Case is preserved or lowercased
   consistently.
3. A value equal to a recognized **color name** SHALL be translated to its hex
   value from a baked table built **X11 `rgb.txt` first (precedence), then
   CSS/SVG filling only the names X11 lacks** (`teal`, `olive`, `lime`, `aqua`,
   `silver`, `fuchsia`, `indigo`, `crimson`), plus `rebeccapurple`. Lookup is
   case-insensitive. Because X11 wins for any name in both, a name kitty already
   accepts translates to the **identical** hex kitty would have produced — so
   there is no tone change for `green`/`gray`/`purple`/`maroon`. Both
   `gray`/`grey` spellings (and `grayN`/`greyN`) resolve. ("X11" names a
   color-name database, not the display server — the table is OS-independent.)
4. The reset sentinel `NONE` (and `rgb:`/functional color forms) SHALL pass
   through unchanged.
5. Any other value is **unrecognized**: `normalize_color` SHALL raise a typed
   `ColorError` whose message names the offending value and shows both a hex and
   a name example. No `kitten @` call SHALL be made for that value.

The baked name table SHALL be a verified **superset** of kitty's native
named-color set, so any name kitty previously accepted continues to work.

For a **scene** (inline or named recipe), all colors SHALL be normalized and
validated **before the first `kitten @ launch`**, so an unrecognized color
rejects the whole scene without opening any window or tab.

The normalizer SHALL add **no new runtime dependency** (the table is a static
literal) and SHALL introduce no new `kitten @` wire format (kitty still receives
`background=#rrggbb` / `active_bg=<value>`).

#### Scenario: Hashless hex gets a leading `#`

- **WHEN** the user supplies `bg=fff` (inline, TOML, or `window background fff`)
- **THEN** `normalize_color` returns `#fff`, the `kitten @ set-colors` call
  carries `background=#fff`, and the command exits 0

#### Scenario: A name kitty lacks is translated to hex

- **WHEN** the user supplies `teal` (which kitty's native table rejects)
- **THEN** `normalize_color` returns `#008080`, the kitten call carries the hex,
  and the color applies — no `"is not a valid color"` error

#### Scenario: A name kitty already knows is unchanged in effect

- **WHEN** the user supplies `green`
- **THEN** `normalize_color` returns kitty's X11 value `#00ff00` (NOT the CSS
  `#008000`), so the rendered color is identical to passing `green` raw — no
  tone regression

#### Scenario: An unrecognized color is rejected before any window opens

- **WHEN** the user launches a multi-pane scene in which one pane sets
  `bg=notacolor`
- **THEN** the command exits non-zero with a client-side error naming
  `notacolor` and suggesting a hex/name, and NO window or tab is opened (the
  scene does not half-build)

#### Scenario: Empty value remains absent

- **WHEN** a pane sets `bg=` (empty) or `tab_accent = ""`
- **THEN** the color normalizes to `None` (the kitten flag is omitted), matching
  the pre-existing empty-string behavior

### Requirement: Manual repro doc records friendly color input

A repro document `docs/repro/friendly-color-input.md` SHALL exist with the
standard sections (Why, Manual repro, Linux Status, macOS Status, Attempted
alternatives, Known limitations). The Manual repro SHALL demonstrate a hashless
hex (`window background fff`), a gap name (`tab accent teal`), and a rejected
unknown (`scene launch` with a bad `bg`, showing no window opens). macOS Status
SHALL be `deferred-with-reason` (value normalization is platform-agnostic; the
`kitten @` protocol is unchanged). The doc SHALL note that no new `tmp/hNN` wire
probe was warranted (the transform is deterministic value→value), with coverage
by unit tests plus one end-to-end integration test.

#### Scenario: Repro doc exists with the standard sections

- **WHEN** a reader opens `docs/repro/friendly-color-input.md`
- **THEN** it contains Why, Manual repro, Linux Status (dated, verified on the
  host), macOS Status (`deferred-with-reason`), Attempted alternatives, and
  Known limitations sections

## MODIFIED Requirements

### Requirement: Tab-accent scene primitive ships under `my-kitty tab accent`

The system SHALL expose a `my-kitty tab accent <color>` subcommand that
sets a kitty tab's accent color so the tab is visibly distinguishable
both when focused and when unfocused (the load-bearing PRD §9 invariant).
Implementation SHALL invoke `kitten @ set-tab-color` with BOTH
`active_bg=<color>` AND `inactive_bg=<color>` keys in the same call, so a
single user-supplied color satisfies the focused-and-unfocused
requirement without any auto-derivation logic.

The `<color>` positional argument SHALL be passed through `normalize_color`
(see "Color inputs are normalized and validated by `my-kitty`") and accepts:
- a named color from the **full X11/CSS set** (e.g. `blue`, `darkblue`,
  `forestgreen`, `teal`, `olive`, `lime`) — translated to its hex value, so
  names kitty's own table lacks still render correctly,
- a hex string of the form `#rrggbb` or `#rgb`, **with or without** the leading
  `#` (`#0066cc`, `0066cc`, `#0a7`, `0a7`),
- the keyword `NONE` to reset the tab's accent to kitty's configured default.

The subcommand SHALL accept the following options:
- `--active-fg <color>` — override the foreground when the tab is focused.
  Normalized, then passed to kitten as `active_fg=<color>`.
- `--inactive-fg <color>` — override the foreground when the tab is
  unfocused. Normalized, then passed to kitten as `inactive_fg=<color>`.
- `--match <expression>` — kitty match expression passed through to
  `kitten @ --match`. When omitted, the default tab selector is the
  active tab.
- `--to unix:<path>` — explicit remote-control socket path, bypassing
  auto-discovery.

The wrapper SHALL normalize the color client-side **before** the kitten call.
An unrecognized value (neither valid hex nor a known name, e.g. `notacolor`) is
rejected by `normalize_color` with a `ColorError`: the subcommand exits non-zero
with a client-side message naming the value and suggesting a hex/name, and makes
**no** kitten call. (This replaces the former "MUST NOT validate the color
string client-side" contract.)

#### Scenario: Setting tab accent with a hex color
- **WHEN** the user runs `my-kitty tab accent "#0066cc"` from inside a kitty window where `$KITTY_LISTEN_ON` is set
- **THEN** the kitten invocation includes both `active_bg=#0066cc` and `inactive_bg=#0066cc`, the subcommand exits 0, and the tab visibly carries the color whether focused or not

#### Scenario: Setting tab accent with a hashless hex
- **WHEN** the user runs `my-kitty tab accent 0066cc` (no leading `#`)
- **THEN** the kitten invocation includes `active_bg=#0066cc` and `inactive_bg=#0066cc`, and the subcommand exits 0

#### Scenario: Setting tab accent with a name kitty lacks
- **WHEN** the user runs `my-kitty tab accent teal`
- **THEN** `normalize_color` translates it to `#008080`, the kitten invocation carries that hex, and the subcommand exits 0 (no `"is not a valid color"` error)

#### Scenario: Resetting tab accent to default
- **WHEN** the user runs `my-kitty tab accent NONE`
- **THEN** the subcommand exits 0 and the tab's accent reverts to whatever the kitty config defined for `active_tab_*` / `inactive_tab_*`

#### Scenario: Unrecognized color is rejected client-side
- **WHEN** the user runs `my-kitty tab accent notacolor`
- **THEN** the subcommand exits non-zero, stderr names `notacolor` and suggests a hex/name, and NO `kitten @` call is made (no tab state changes)

#### Scenario: --active-fg and --inactive-fg flags pass through to kitten keys
- **WHEN** the user runs `my-kitty tab accent "#0066cc" --active-fg white --inactive-fg "#cccccc"`
- **THEN** the kitten invocation includes `active_bg=#0066cc`, `inactive_bg=#0066cc`, `active_fg=white`, and `inactive_fg=#cccccc`

### Requirement: Window-background scene primitive ships under `my-kitty window background`

The system SHALL expose a `my-kitty window background <color>`
subcommand that sets the background color of a kitty pane (a kitty
"window") via `kitten @ set-colors background=<color> --match <expr>`.
The default selector is the active window; the change SHALL be scoped to
the matched pane only and SHALL NOT affect other panes in the same tab
(probe-grounded: pane A bg = `#001a33`, pane B bg = `#000000` after a
single matched call).

The `<color>` positional argument SHALL be passed through `normalize_color`
(see "Color inputs are normalized and validated by `my-kitty`") — accepting the
full X11/CSS named set (translated to hex when kitty lacks the name), hashless or
`#`-prefixed hex, or `NONE` — and an unrecognized value is rejected client-side
(exit non-zero, no kitten call), the same contract as `tab accent`.

The subcommand SHALL accept `--match <expression>` and
`--to unix:<path>` with the same semantics as the other scene
primitives.

#### Scenario: Setting background on the active window
- **WHEN** the user runs `my-kitty window background "#001a33"` from inside a kitty pane
- **THEN** `kitten @ get-colors` for that pane reports `background #001a33`, the subcommand exits 0, and no other pane's background changed

#### Scenario: Per-pane isolation
- **WHEN** the user has 2 panes (id 1 and id 2) and runs `my-kitty window background "#001a33" --match id:1`
- **THEN** `kitten @ get-colors --match id:1` reports `background #001a33`, AND `kitten @ get-colors --match id:2` reports the unchanged default `background #000000`

#### Scenario: Hashless hex on a window background
- **WHEN** the user runs `my-kitty window background 001a33` (no leading `#`)
- **THEN** `kitten @ get-colors` reports `background #001a33` and the subcommand exits 0

#### Scenario: Name kitty lacks resolves to hex
- **WHEN** the user runs `my-kitty window background teal`
- **THEN** `kitten @ get-colors` reports `background #008080` for the active window, and the subcommand exits 0

# Delta: kitty-curated-bindings

## MODIFIED Requirements

### Requirement: Curated catalog covers seven categories

The payload SHALL ship one `.conf` file per binding category under `~/.config/kitty/kitty-setup/`, with the file basename matching the category name reported by `my-kitty keys`. The required categories are:

* `tab-nav` — next tab, previous tab, move tab left, move tab right, close tab.
* `window-nav` — focus next window (`ctrl+shift+]`), focus previous window (`ctrl+shift+[`), move window forward (`ctrl+shift+f`), close window (`ctrl+shift+w`); all four are redundant rebinds of kitty defaults. Vim-style hjkl direction chords are NOT used (dropped in `phase1-curated-bindings-revert-defaults`); `neighboring_window` is NOT used.
* `font-zoom` — increase font size, decrease font size, reset font size.
* `detach` — detach current window to a new tab, detach current tab to a new OS window.
* `broadcast` — toggle input broadcast across all windows in the active tab.
* `url-hints` — open URL under hints (`open_url_with_hints`).
* `layout` — one direct-jump chord to a non-default layout orientation
  (Phase 2 §11 of `docs/requirements.md`). The `layout.conf` file ships
  BOTH a curated `enabled_layouts` directive AND one `map` line
  (`map ctrl+shift+m goto_layout tall:mirrored=true`). The pin is REQUIRED
  for the chord to actually apply the mirror option — see the
  "Layout orientation chord" Requirement below for the empirical
  grounding.

Each category file SHALL contain at least one `map` line. Each `map` line SHALL be authored with an explicit `ctrl+shift+<key>` chord (no `kitty_mod+` shorthand). Each chord that shadows a kitty default SHALL be present in `intentional-overrides.conf` with a comment explaining the override.

#### Scenario: All seven category files ship under the payload dir
- **WHEN** the user runs `make install` and lists `~/.config/kitty/kitty-setup/`
- **THEN** the listing contains `tab-nav.conf`, `window-nav.conf`, `font-zoom.conf`, `detach.conf`, `broadcast.conf`, `url-hints.conf`, and `layout.conf`, each with at least one `map` line

#### Scenario: Each category appears as its own section in the binding report
- **WHEN** the user runs `my-kitty keys` after install
- **THEN** the report contains one section per category file, named after the file basename, listing every binding authored in that file

#### Scenario: Every shadow is allow-listed
- **WHEN** the user runs `my-kitty keys` after install
- **THEN** the `Summary:` line reports `0 conflicts`, every chord that shadows a kitty default is annotated `[overrides default <action>]`, and `make doctor` exits 0

## ADDED Requirements

### Requirement: Layout orientation chord

The `layout.conf` file SHALL bind exactly one chord (`ctrl+shift+m`) to `goto_layout tall:mirrored=true` — kitty's Tall layout with the `mirrored=true` option, which (per kitty's `docs/layouts.rst`) "shifts the full-height windows to the right." With 3 panes, this produces one pane full-height on the right and the other two stacked top/bottom on the left.

The `layout.conf` file SHALL ALSO include a curated `enabled_layouts` directive with exactly these 8 entries in this order: `tall,tall:mirrored=true,fat,grid,horizontal,vertical,splits,stack`. The pin is REQUIRED — empirically verified by `tmp/h24-tall-mirrored-right/expected.json` Phase A vs Phase B: `kitten @ goto-layout tall:mirrored=true` exits 0 with empty stderr even when `enabled_layouts` is left at the default `*`, BUT the `mirrored=true` option is silently ignored unless `tall:mirrored=true` is an explicit entry in the enabled-layouts list. The curated 8-entry list is a strict superset of kitty's default `*` (which expands to the 7 base layouts) plus the mirrored variant; this preserves the user's existing layout reach via `next_layout` while adding the entry needed for the chord to function.

The chord MUST NOT appear in `intentional-overrides.conf` because `ctrl+shift+m` is unbound by kitty default (no shadow occurs). If a future kitty release introduces a default binding for `ctrl+shift+m`, the chord SHALL move to `intentional-overrides.conf` and `make doctor`'s `bindings` check SHALL surface the conflict until the override is allow-listed.

The `kitten @ ls` JSON shape that this requirement's scenarios reference: kitten returns a top-level **array of OS window objects**. Each OS window has a `"tabs"` array; each tab has a string `"layout"` key (the base name, e.g. `"tall"`) and a `"layout_opts"` dict (e.g. `{"bias": "50", "full_size": "1", "mirrored": "y"}`). The path expression `(kitten @ ls)[0]["tabs"][0]["layout"]` reads the first tab of the first OS window's base layout name; `(kitten @ ls)[0]["tabs"][0]["layout_opts"]["mirrored"]` reads its mirrored option as the string `"y"` or `"n"` (not the booleans `true`/`false` written in `enabled_layouts`).

#### Scenario: Layout chord appears as its own section in the binding report
- **WHEN** the user runs `my-kitty keys` after install
- **THEN** the report contains a `layout` section listing exactly one entry whose chord is `ctrl+shift+m` and whose action is `goto_layout tall:mirrored=true`

#### Scenario: Layout chord routes to `goto_layout` and the mirrored option IS applied
- **WHEN** the user inside a kitty window with 3 panes presses `ctrl+shift+m` and the curated `enabled_layouts` directive from `layout.conf` is loaded
- **THEN** `(kitten @ ls)[0]["tabs"][0]["layout"] == "tall"` and `(kitten @ ls)[0]["tabs"][0]["layout_opts"]["mirrored"] == "y"`, AND the pane with the maximum `lines` value has `neighbors["left"]` populated (the secondary panes are on its left) and `neighbors["right"]` empty (no panes to its right)

#### Scenario: `enabled_layouts` is pinned to the curated 8-entry list
- **WHEN** the user reads `~/.config/kitty/kitty-setup/layout.conf` after install
- **THEN** the file contains the line `enabled_layouts tall,tall:mirrored=true,fat,grid,horizontal,vertical,splits,stack`

#### Scenario: `next_layout` cycle includes the mirrored Tall variant
- **WHEN** the user invokes `kitten @ action next_layout` repeatedly starting from plain `tall`
- **THEN** the sequence of `((kitten @ ls)[0]["tabs"][0]["layout"], (kitten @ ls)[0]["tabs"][0]["layout_opts"]["mirrored"])` tuples cycles through the 8 curated entries: `("tall", "n")`, `("tall", "y")`, `("fat", "n")`, then on into `grid`, `horizontal`, `vertical`, `splits`, `stack` (which do not carry a `mirrored` option), then wraps back to `("tall", "n")`

#### Scenario: Layout chord does not shadow a kitty default
- **WHEN** the user runs `my-kitty keys --json` after install
- **THEN** the binding whose source is `layout` and chord is `ctrl+shift+m` carries no `[overrides default …]` annotation, and the global `Summary:` line still reports `0 conflicts`. A `grep 'ctrl+shift+m' config/kitty/intentional-overrides.conf` returns empty (exit 1)

#### Scenario: Manual repro doc records Linux + macOS status
- **WHEN** the change merges and a reviewer reads `docs/repro/h24-bindings-layout.md`
- **THEN** the document contains `## Linux Status` set to `verified` with a date and the host details, and a `## macOS Status` set to either `verified` or `deferred` with a one-paragraph reason (per the existing "Linux-first delivery, macOS-deferred-with-note" requirement in this capability)

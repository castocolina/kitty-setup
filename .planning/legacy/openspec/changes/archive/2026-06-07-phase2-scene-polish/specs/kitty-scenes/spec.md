## ADDED Requirements

### Requirement: Color names shell-complete for color commands

`my-kitty` SHALL provide shell tab-completion of color **names** for every
single-noun color argument, mirroring the existing `scene launch <name>`
completion. A `color_completer(prefix="", **_) -> list[str]` SHALL return the
keys of the baked color table (`COLOR_NAMES`) that start with `prefix`, plus the
reset sentinel `NONE`. It SHALL be wired via argparse `.completer` onto the
`<color>` positional of `my-kitty tab accent` and `my-kitty window background`,
and onto the `--tab-accent` option of `my-kitty scene launch`.

To keep the suggestion list usable, the numbered grays/greys (`gray0`..`gray100`
and `grey0`..`grey100`) SHALL be excluded from the **completion** list (the base
`gray`/`grey` names still complete). Excluding them from completion SHALL NOT
affect resolution — `normalize_color` still resolves every numbered gray.

Hex values SHALL NOT be completed (they are not enumerable). The `bg=` key inside
the inline `--pane 'key=value,...'` token is a single opaque argparse argument and
SHALL be out of scope for completion (a stated known limit).

#### Scenario: Color name completes on a single-noun color command

- **WHEN** the user types `my-kitty tab accent te` and presses TAB in a shell
  with `my-kitty` completion installed
- **THEN** `teal` is offered as a completion

#### Scenario: NONE completes and numbered grays are excluded

- **WHEN** the user requests completions for the `<color>` argument with an empty
  prefix
- **THEN** `NONE` appears in the suggestions, and `gray50` (a numbered gray) does
  NOT appear, while `gray` and `teal` do

## MODIFIED Requirements

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
2. A value matching `^#?[0-9a-fA-F]{3}$`, `^#?[0-9a-fA-F]{4}$`,
   `^#?[0-9a-fA-F]{6}$`, or `^#?[0-9a-fA-F]{8}$` is **hex**:
   - 3- and 6-digit values are returned with a leading `#` added if missing (so
     the bare `fff` / `000` / `1a2b3c` a user types is accepted).
   - 4-digit (`#rgba`) and 8-digit (`#rrggbbaa`) values carry an **alpha
     channel**; the alpha is **stripped** and the solid `#rgb` / `#rrggbb` is
     returned. kitty has no per-pane or per-tab opacity (probe-grounded against
     kitty 0.47.1: `set-background-opacity` is OS-window scope only, and `ls`
     exposes opacity only on the OS-window object), so a color's alpha cannot
     become a per-pane translucency and is dropped **silently**. Runtime opacity
     remains the explicit, OS-window-scoped `my-kitty os-window opacity` gesture.
   - Case is lowercased consistently.
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

#### Scenario: Alpha hex is accepted and stripped to its solid color

- **WHEN** the user supplies `bg=#001f3faa` (8-digit) or `bg=#f007` (4-digit)
- **THEN** `normalize_color` returns `#001f3f` (resp. `#f00`), the kitten
  `set-colors` call carries the solid color, the command exits 0, and no opacity
  is changed — the alpha is silently dropped

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

### Requirement: Scene launcher composition primitive ships under `my-kitty scene launch`

The `my-kitty` binary SHALL expose a `scene launch` subcommand that composes the existing scene primitives (title, accent, background, layout) into one user gesture. Invoking `my-kitty scene launch <args>` SHALL spawn one or more panes, each optionally pre-styled with title, working directory, background color, and a startup command.

The destination depends on the **pane count** and on whether the launch happens **from inside kitty** (the `$KITTY_WINDOW_ID` environment variable, exported by kitty into every window, identifies the origin window):

- A multi-pane scene launched **from inside kitty** (`$KITTY_WINDOW_ID` is set) **AND whose origin tab holds exactly one window** SHALL be materialised INTO the current tab: the origin window becomes pane 0 (restyled in place via `set-window-title` / `set-colors`, with any explicit pane-0 `cwd`/`cmd` fed to the reused shell via `send-text`), the remaining panes open as `--type=window` splits in the same tab, and `--layout` / `--tab-title` / `--tab-accent` are applied to that current tab (kitty defaults `goto-layout` / `set-tab-title` / `set-tab-color` to the focused tab, so no `--match` is needed). NO new tab is created. The "exactly one window" test SHALL query `kitten @ ls`, locate the tab whose windows contain the origin window id, and count those windows.
- A multi-pane scene launched **from inside kitty** whose origin tab holds **more than one window** — OR whose window count cannot be determined (the `kitten @ ls` call fails, returns unparseable output, or the origin window id is not found in the tree) — SHALL fall back to opening a NEW tab (the no-origin multi-pane path below), leaving the existing tab's windows untouched. This fallback is **fail-safe**: ambiguity SHALL NEVER add windows to a populated tab.
- A scene with **two or more panes** launched with **no origin window** (`$KITTY_WINDOW_ID` unset — e.g. driven over a socket from another terminal) SHALL open a NEW tab, optionally apply a layout, spawn the panes inside the new tab, and optionally tint the tab — the probe-grounded multi-pane algorithm.
- A scene with **exactly one pane** SHALL launch that pane as a `kitten @ launch --type=window` into the CURRENT tab (no new tab is created), regardless of `$KITTY_WINDOW_ID` (it does not commandeer the origin shell). For a single-pane scene the `--layout`, `--tab-title`, and `--tab-accent` inputs SHALL NOT be applied — there is no new tab to own them. Per-window styling (`title`, `cwd`, `bg`, `cmd`) SHALL still apply.

Every pane that does not set its own `cwd` SHALL inherit a caller-supplied default working directory (the `default_cwd` argument to `launch_scene`, wired to the launching process's `os.getcwd()` in `cli_scene_launch`), so a scene's tab AND windows open in the directory the user launched it from rather than kitty's startup directory. An explicit per-pane `cwd` SHALL override the default.

The CLI surface SHALL be:

```
my-kitty scene launch \
    [<name>] \
    [--layout=<name>[:<opts>]] \
    [--tab-title=<text>] [--tab-accent=<color>] \
    --pane 'key=value,key=value,...' \
    [--pane '...'] ... \
    [--to=unix:<socket>]
```

The `--pane` flag SHALL accept a comma-separated `key=value` group. Recognised keys SHALL be exactly `title`, `cmd`, `cwd`, and `bg`. Any unknown key SHALL cause the command to exit non-zero with a stderr message naming the offending key and listing the recognised set. Commas inside a value SHALL be escapable as `\,` and backslashes as `\\`. The `--pane` flag SHALL be repeatable. The inline `--pane` form and the named `<name>` form are mutually exclusive; at least one pane (inline or via a named recipe) MUST be provided (zero panes is rejected with exit non-zero).

The launcher SHALL use the existing `scenes._client.kitten_at()` surface for every kitten call, inheriting `$KITTY_LISTEN_ON` → `pgrep -x kitty` socket discovery and the kitten binary resolution from h22's foundation. No new socket-discovery code SHALL be introduced.

The launcher SHALL fail-hard on any `kitten @ launch` non-zero exit (propagate the kitten exit code and stop processing further panes). It SHALL fail-soft on `kitten @ set-colors` and `kitten @ set-tab-color` failures (print the kitten stderr to its own stderr, mark the overall exit code non-zero, but continue building the rest of the scene). The first non-zero kitten exit code SHALL be propagated as the launcher's exit code.

Every user-supplied `cmd=...` SHALL be wrapped as `bash -lc <cmd>` when passed to `kitten @ launch` so the user's shell features (`|`, `$VAR`, `;`, `&&`, etc.) work transparently without any quoting code in the launcher.

#### Scenario: Multi-pane scene composes a new tab in one user gesture

- **WHEN** the user invokes `my-kitty scene launch --layout=tall:mirrored=true --tab-title="🐳 mon" --pane 'title=p1,cmd=echo p1' --pane 'title=p2,bg=#001f3f,cmd=echo p2' --pane 'title=p3'` with `$KITTY_WINDOW_ID` unset (driven over a socket from another terminal)
- **THEN** a new tab whose title is `🐳 mon` appears, the active layout is `tall` with `layout_opts.mirrored == "y"`, the new tab contains exactly 3 windows whose titles are `p1`, `p2`, `p3` in order, `p2`'s `background` reads `#001f3f`, and the command exits 0

#### Scenario: Multi-pane scene fills the current tab when it holds exactly one window

- **WHEN** the running kitty has one tab with one window, and the user invokes a 3-pane scene (`layout=tall`, `tab_title="DEV"`, panes `shell` / `git` / `watch`) from a shell **inside that window** so `$KITTY_WINDOW_ID` is set
- **THEN** NO new tab is created (the tab count is unchanged), the current tab holds exactly the 3 scene panes in order (`shell` is the reused origin window, `git` and `watch` are new splits), the tab's title becomes `DEV`, the active layout is `tall`, and the command exits 0

#### Scenario: Multi-pane scene opens a new tab when the current tab is not solo

- **WHEN** the running kitty's current tab already holds **two** windows, and the user invokes a 3-pane scene from a shell inside one of them (`$KITTY_WINDOW_ID` set)
- **THEN** a NEW tab is created containing exactly the 3 scene panes, the original tab still holds exactly its 2 original windows (NOT 4), and the command exits 0

#### Scenario: Single-pane scene joins the current tab

- **WHEN** the running kitty has one tab and the user invokes a one-pane scene (inline `--pane 'title=solo'` or a named recipe with a single `[[pane]]`)
- **THEN** NO new tab is created (the tab count is unchanged), a new window titled `solo` is added to the current tab, and `--layout`/`--tab-title`/`--tab-accent` are not applied

#### Scenario: Panes inherit the launch directory

- **WHEN** the user runs `my-kitty scene launch <scene>` from directory `/some/dir` and the scene's panes do not set their own `cwd`
- **THEN** each spawned window reports `cwd == /some/dir` (the tab and its windows open where the scene was launched), and a pane that sets an explicit `cwd` keeps that value

#### Scenario: Zero panes is rejected with non-zero exit

- **WHEN** the user invokes `my-kitty scene launch --tab-title="empty"` with no `--pane` flags and no scene name
- **THEN** the command exits non-zero, prints a stderr message stating that a scene name or at least one `--pane` is required, and does NOT create a new tab

#### Scenario: Unknown key in `--pane` is rejected before any kitten call

- **WHEN** the user invokes `my-kitty scene launch --pane 'tile=mistyped'` (note the typo: `tile` instead of `title`)
- **THEN** the command exits non-zero, prints a stderr message naming the unknown key `tile` and listing the recognised keys (`title`, `cmd`, `cwd`, `bg`), and does NOT call `kitten @ launch` even once

#### Scenario: Escaped comma inside a pane value is preserved verbatim

- **WHEN** the user invokes `my-kitty scene launch --pane 'title=docker ps -a\, --filter status=running,cmd=docker ps'`
- **THEN** the resulting window's title equals the string `docker ps -a, --filter status=running` (single literal comma) and `cmd` is executed unchanged

#### Scenario: First non-zero kitten exit code propagates

- **WHEN** the launcher's first `kitten @ launch` invocation succeeds but a subsequent `kitten @ set-colors` for a pane with an invalid `bg=<not-a-color>` fails
- **THEN** the set-colors stderr is printed to the launcher's stderr, the launcher CONTINUES with the remaining panes, and the launcher's overall exit code equals the first non-zero kitten exit code

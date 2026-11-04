# Design — phase2-scene-styling

## Context

`phase2-scene-title-primitive` (archived 2026-05-16) shipped the first scene
primitive (`my-kitty window title` / `tab title`) along with `scenes/_client.py`
(socket discovery + `kitten_at()` wrapper) and the `scenes/` package layout.
The h22 probe + integration tests proved the design works end-to-end on the
user's host.

§9 (tab accent for role-identification) and §10 (window background, font,
transparency) extend the same pattern with four more primitives. The h23
probe (`tmp/h23-styling/run.py`) ran green against a live kitty 0.46.2 on
the user's daily host (Pop!_OS 24.04 + COSMIC) and grounded every spec
claim below, including the kitten quirks that bite implementers.

Inputs to this design:
- `docs/requirements.md` §9 ("tab role identifiable at a glance, focused or
  not") and §10 ("background, font, transparency to a window").
- `docs/requirements.md` cross-cutting line 35: "per-window opacity and
  per-window font size depend on Kitty boss surface that is global today;
  defer until verified" — partially confirmed by the probe (it's not just
  "today" — it's architectural per kitten verb help text).
- `openspec/specs/kitty-scenes/spec.md` (existing; gets 4 new ADDED
  Requirements).
- `openspec/specs/my-kitty-cli/spec.md` (existing; gets an updated MODIFIED
  Requirement to enumerate the new subparsers).
- Probe findings under `tmp/h23-styling/expected.json` and `repro.md`.

## Goals / Non-Goals

**Goals:**

- Ship 4 new primitives that complete the styling-attribute side of Phase 2:
  `tab accent`, `window background`, `os-window font-size`, `os-window
  opacity`.
- Honestly name the noun-scope split: `window` is per-pane (a kitty
  sub-window), `os-window` is the whole top-level window. Users discover the
  kitty architecture from the command, not from the docs.
- Ship the install-time precondition for opacity (`dynamic_background_opacity
  yes` directive) as a managed payload with the existing surgical
  install/uninstall contract.
- Reuse `scenes/_client.py` unchanged. Every new module is a thin caller.
- Hypothesis-first: the h23 probe is already green. Promotion lands as
  integration tests; the probe is deleted at archive.

**Non-Goals:**

- Per-pane font size or per-pane opacity. Kitty's architecture forbids
  them — `kitten @ set-font-size --help` says "in kitty all sub-windows in
  the same OS window must have the same font size"; `kitten @
  set-background-opacity --help` says "the background opacity affects all
  kitty windows in a single OS window." The honest naming surfaces this
  without us re-litigating it at every callsite.
- A doctor check for `dynamic_background_opacity`. The existing `parse
  check: kitty --debug-config exit=0` already validates the directive
  parses; no runtime-reachability check applies (opacity is a runtime
  command, not a service).
- Curated role-color palette (`role=prod`, `role=dev`, etc.). That's a §13
  preset concern; this change's primitive accepts any color string and
  passes it through.
- §11 (extra layout) and §12-§14 (scene composition / named presets /
  chord wiring). Each lands as its own change.
- macOS verification. Tracked as deferred-with-reason under follow-up
  `phase2-scene-styling-macos`.

## Decisions

### D1: Four primitives, two new nouns, one new install-time file

Final CLI surface (probe-verified):

```
my-kitty tab accent <color>                     ⮕  kitten @ set-tab-color
            [--active-fg <color>]                       active_bg=<color>
            [--inactive-fg <color>]                     inactive_bg=<color>
            [--match EXPR]                              (+ optional fg overrides)
            [--to SOCKET]

my-kitty window background <color>              ⮕  kitten @ set-colors
                  [--match EXPR]                       background=<color>
                  [--to SOCKET]                        --match=<expr>
                                                       (per-pane; default = active window)

my-kitty os-window font-size <value>            ⮕  kitten @ set-font-size <value>
                       [--all]                         --all: current + future OS windows
                       [--to SOCKET]                   value: 14 / +2 / -2 / *1.1 / /2 / 0

my-kitty os-window opacity <value>              ⮕  kitten @ set-background-opacity
                    [--toggle]                         --toggle <value>
                    [--all]                            (TOGGLE FLAG MUST PRECEDE VALUE)
                    [--to SOCKET]                      (precondition: dynamic_background_opacity yes)
```

Two CLI nouns are pre-existing (`tab`, `window` — from
`phase2-scene-title-primitive`); one is new (`os-window`). The new noun is
introduced exactly because §10 has two attributes (font, opacity) that
kitty scopes to the OS window. Naming them under `window` would lie about
what they do.

Alternatives considered:
- **Hide the OS-window scope under `window`** (`my-kitty window font 14`
  applies to all panes in the OS window). Honest about the result, dishonest
  about the noun. Future readers asking "why does `window` affect all
  panes?" never get a clean answer. Rejected.
- **Expose a `--os-window` flag on `window font` / `window opacity`** (no
  new noun). Equally honest, slightly fewer top-level subcommands. But makes
  per-pane the default and OS-window the opt-in, which inverts the kitty
  reality (font/opacity ARE OS-window only). Rejected.
- **Drop opacity entirely** (only ship 3 primitives). Half-addresses §10
  and leaves the `dynamic_background_opacity` precondition + payload work
  for a follow-up. Option B from the explore was "cover both fully" —
  shipping all 4 honours that.

### D2: Color grammar passed through to kitten verbatim

Both `tab accent` and `window background` accept a color string and pass it
unchanged to the underlying kitten verb. The grammar is kitten's, not ours:

| Form | Example | Kitten resolves to |
|---|---|---|
| Named (X11 rgb.txt) | `blue`, `darkblue`, `forestgreen` | `#0000ff`, `#00008b`, `#228b22` |
| Hex `#rrggbb` | `#0066cc` | unchanged |
| `NONE` keyword | `NONE` | reset to kitty default |

No client-side validation; kitten errors clearly on invalid names ("Error:
notacolor is not a valid color", probe-verified). Our wrapper propagates
stderr verbatim, exit code propagates.

Rationale: zero new validation surface. Kitten's grammar is the source of
truth. If kitty extends the grammar in a future release, our CLI inherits
the extension for free.

### D3: `--toggle` argv ordering is fixed in `_client.kitten_at` callers

Probe-verified kitten quirk: `kitten @ set-background-opacity --toggle 0.7`
works, but `kitten @ set-background-opacity 0.7 --toggle` errors with
`Must specify exactly 1 argument(s)`. Kitten parses positional-first and
treats the trailing `--toggle` as a stray arg.

Implementation rule: `scenes/opacity.py` constructs the kitten argv as

```python
args: list[str] = []
if toggle:
    args.append("--toggle")
if all_:
    args.append("--all")
args.append(format_opacity(value))  # e.g. "0.7"
return _client.kitten_at("set-background-opacity", *args, to=to)
```

— flags FIRST, positional value LAST. The integration test exercises this
ordering explicitly.

### D4: Float-precision tolerance on opacity comparisons

Probe-verified: `kitten @ set-background-opacity 0.7` stores the value as
`0.699999988079071` (float32-ish in kitty's internals). `kitten @ ls` reflects
the stored value. Any code that compares "current opacity == requested
opacity" MUST use tolerance, not equality.

`scenes/opacity.py` itself does not compare values (it just calls kitten).
But the integration test that reads `os_window.background_opacity` from
`kitten @ ls` MUST assert with `abs(actual - expected) < 0.01`, not `==`.
Codified in `tests/integration/test_h23_styling.py`.

### D5: `dynamic-opacity.conf` shipped as a managed payload

New file `config/kitty/dynamic-opacity.conf` with a single directive:

```
# Required by `my-kitty os-window opacity` (phase2-scene-styling).
# Without this, kitten @ set-background-opacity errors with
# "You must turn on the dynamic_background_opacity option in kitty.conf
#  to be able to set background opacity".
#
# Visual impact: none. With this directive AND no explicit background_opacity
# directive, kitty starts at opacity 1.0 (fully opaque, the default). The
# opacity primitive opt-in changes the runtime value; the default rendering
# is unchanged on hosts that don't invoke the primitive.
dynamic_background_opacity yes
```

Included from `kitty-setup.conf` after the `monitor.conf` and
`remote-control.conf` include lines. Same surgical contract: `make install`
drops the file into `~/.config/kitty/kitty-setup/`, `make uninstall` removes
it along with the rest of the payload.

No new doctor check needed. The existing `parse check` exit code covers
"directive parses" because `kitty --debug-config` loads the include chain.

Alternatives considered:
- **Bake the directive into `kitty-setup.conf` directly** (no new file).
  Smaller install footprint, but breaks the "one payload file per concern"
  pattern monitor.conf and remote-control.conf established. The opt-in for
  removing opacity-support requires editing the umbrella file rather than
  dropping a single managed file. Rejected.
- **Split into a separate change** (`phase2-dynamic-opacity-payload` lands
  first; this change adds the primitive). Surface area would be tiny, but
  the user has zero use for the directive between the two changes. Rejected
  per the explore decision.

### D6: Module split — one file per primitive

```
src/kitty_setup/scenes/
├── __init__.py    (already exposes title; add accent/background/font/opacity exports)
├── _client.py     (unchanged)
├── title.py       (unchanged)
├── accent.py      (NEW: set_tab_accent + cli_set_tab_accent)
├── background.py  (NEW: set_window_background + cli_set_window_background)
├── font.py        (NEW: set_os_window_font_size + cli_set_os_window_font_size)
└── opacity.py     (NEW: set_os_window_opacity + cli_set_os_window_opacity)
```

Each file is the same shape as `title.py`: a domain function +
`cli_*` Namespace-unpacking wrapper. No shared base class; the abstraction
is `_client.kitten_at()`.

Alternatives considered:
- **One `styling.py`** holding all four functions. Tighter file layout, but
  forces unrelated concerns into one test file too. Rejected.
- **A `_attribute_primitive.py` base** abstracting the
  "verb + args + Namespace → exit code" pattern. Tempting; would shave maybe
  20 lines per file. Two reasons to skip: (a) the per-primitive arg shapes
  differ enough that the abstraction either becomes a kwargs-bag or grows
  hooks for each variation; (b) the project rule "don't add abstractions
  beyond what the task requires" applies here — three more sibling files
  with no shared inheritance is fine. Rejected.

### D7: Probe → integration test promotion

`tmp/h23-styling/run.py` ran green for all 23 assertions before this
proposal. The integration test `tests/integration/test_h23_styling.py`
will replicate every probe assertion at the `KITTI_INTEGRATION=1`-gated
level, then `tmp/h23-styling/` is deleted at archive (mirrors h22).

Mapping (probe → integration test):

| Probe assertion | Test name |
|---|---|
| `opacity_without_directive_fails` + stderr | `test_opacity_without_directive_errors_clearly` |
| `tab_color_{named,hex,NONE}_accepted` | `test_set_tab_color_accepts_named_hex_NONE` |
| `tab_color_invalid_rejected` | `test_set_tab_color_rejects_invalid_color` |
| `set_colors_per_pane_ok` + pane_a / pane_b backgrounds | `test_set_colors_isolates_to_matched_pane` |
| `set_colors_named_ok` + pane_b_background_named | `test_set_colors_accepts_named_color` |
| `font_set_{14,plus2,reset}_ok` | `test_set_font_size_absolute_relative_reset` |
| `opacity_set_ok` + opacity_in_ls_after_set (tolerance) | `test_set_opacity_reflected_in_ls_with_tolerance` |
| `opacity_toggle_ok` + opacity_in_ls_after_toggle | `test_set_opacity_toggle_resets_to_default` |

Unit tests cover the CLI dispatch + flag-ordering invariants (especially
the `--toggle` precedence rule from D3) with `_client.kitten_at`
monkeypatched. Same pattern as `tests/unit/test_scenes_title.py`.

## Risks / Trade-offs

- **Tab accent persistence across kitty session restarts**: `kitten @
  set-tab-color` is a runtime state change. If the user closes the OS
  window or restarts kitty, the accent reverts to kitty's configured
  default. → Mitigation: documented in `docs/repro/h23-styling.md` under
  Known Limitations. §13 (named scenes) will solve persistence by making
  scene invocation re-apply primitives on every load.
- **`set-font-size --all` is persistent across new OS windows**: kitten's
  `--all` flag is more than a one-shot — it changes the configured default
  for newly-spawned OS windows. → Mitigation: kitten's own help text says
  so; our `--help` text mirrors that. Surface as a power-user knob; default
  invocation is one-shot.
- **`dynamic_background_opacity yes` toggles a kitty mode**: even though the
  default rendering is unchanged (opacity stays 1.0 until invoked), the
  directive activates a runtime opacity-update path that some users with
  finicky GPUs may not want. → Mitigation: the directive is in a discrete
  payload file (`dynamic-opacity.conf`); a user can remove it surgically by
  editing the include chain without losing the rest of the install. Same
  contract `monitor.conf` ships under.
- **Float-precision foot-gun in future primitives**: any future primitive
  that reads back opacity (e.g. a `--toggle` re-implementation, or a "what's
  the current opacity?" surface) hits the same float-storage issue. →
  Mitigation: design.md D4 codifies tolerance comparison; the integration
  test enforces it. New primitives reading opacity inherit the convention.
- **kitten `--toggle` argv-ordering quirk** is silent on success but loud on
  failure with a confusing message. → Mitigation: design.md D3 fixes the
  order in code; a dedicated unit test asserts the argv structure so any
  future refactor that re-orders the args fails loud.
- **Per-pane font / opacity false expectations**: a user reading PRD §10's
  "Apply background color, font, and transparency to a window" might expect
  per-pane font and per-pane opacity. → Mitigation: the honest noun naming
  (`os-window font-size`, `os-window opacity`) tells the user the truth at
  the CLI level. Repro doc carries an explicit Known Limitations section
  citing kitten's verb help.

## Migration Plan

No migration. New subcommands and one new managed payload file. Rollback
is `make uninstall` (removes the payload file along with the rest); the new
CLI surface disappears with the uv tool venv. `set-tab-color`,
`set-colors`, `set-font-size`, `set-background-opacity` are all kitten
verbs that act on the live kitty process — there is no persisted state to
unwind.

The one wrinkle: the FIRST `make install` that picks up this change adds
the `include dynamic-opacity.conf` line + the file itself. A user who had
this change's directive elsewhere in their own kitty.conf already would
see no functional change (kitty merges directives idempotently). A user
who DIDN'T have `dynamic_background_opacity` set anywhere now has it on.
Visual impact: still none — kitty default opacity stays 1.0.

## Open Questions

- **Should `tab accent` also accept a single `--fg <color>` shortcut** that
  sets both `active_fg` and `inactive_fg` to the same value? Power users
  who want maximum contrast on a colored tab might use it. **Tentative
  answer:** no for now; ship `--active-fg` + `--inactive-fg` as the
  expressive surface. If usage shows everyone passes the same value to
  both, add the shortcut in a small follow-up. (Project rule: don't add
  features the task doesn't require.)
- **Should `window background` accept `foreground` / `cursor` keys too?**
  `kitten @ set-colors` accepts dozens of color keys (foreground,
  background, cursor, selection_*, color0..15, etc.). Exposing one key
  per subcommand explodes the surface; exposing a single
  `--key=value ...` kwarg-bag turns the CLI into a YAML transport. **Tentative
  answer:** ship only `background` here (the §10 ask). Future §10-adjacent
  primitives (`window foreground`, `window cursor`) ship in follow-ups
  if and when the PRD asks for them.
- **Naming of the toggle behaviour in the CLI**: should it be
  `--toggle <value>` (current proposal) or `--toggle-to <value>`? The
  latter reads slightly better aloud but adds a hyphen for no real win.
  **Tentative answer:** keep `--toggle` to match the kitten flag name
  and reduce surprise for users who already know the kitten interface.

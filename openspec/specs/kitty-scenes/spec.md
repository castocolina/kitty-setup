# kitty-scenes Specification

## Purpose
TBD - created by archiving change phase2-scene-title-primitive. Update Purpose after archive.
## Requirements

### Requirement: Window-title scene primitive ships under `my-kitty window title`

The system SHALL expose a `my-kitty window title <text>` subcommand that
sets the title of a running kitty window via the kitty remote-control
socket. The subcommand SHALL accept a single positional `<text>` argument
which is passed through to `kitten @ set-window-title` byte-for-byte
(UTF-8, including emoji). The default behaviour SHALL be equivalent to
passing `--temporary` to `kitten @ set-window-title` (i.e. programs running
inside the window MAY override the title via OSC-2 escape sequences).

The subcommand SHALL accept the following options:
- `--temporary / --no-temporary` (argparse `BooleanOptionalAction`,
  available since Python 3.9; `pyproject.toml` declares
  `requires-python = ">=3.12"` so this is satisfied, defaults to ON) —
  controls whether subsequent OSC-2 title escapes from inside the window
  are allowed to override the title.
- `--match <expression>` — kitty match-expression passed through to
  `kitten @ --match`. When omitted, the default window selector is
  whichever window `kitten @` resolves as "the window where the command
  ran" (the focused window when invoked from inside kitty; otherwise the
  selector dictated by D3 socket discovery).
- `--to unix:<path>` — explicit remote-control socket path, bypassing
  auto-discovery.

#### Scenario: Setting a plain-text title from inside kitty
- **WHEN** the user runs `my-kitty window title "deploy logs"` from a shell inside a kitty window where `$KITTY_LISTEN_ON` is set
- **THEN** the window's title (as observed via `kitten @ ls`) becomes `"deploy logs"` byte-identical to the argument, and the subcommand exits 0

#### Scenario: Setting an emoji-containing title from inside kitty
- **WHEN** the user runs `my-kitty window title "🐳 docker test"` from a shell inside a kitty window where `$KITTY_LISTEN_ON` is set
- **THEN** the window's title (as observed via `kitten @ ls`) is byte-identical to `"🐳 docker test"` (UTF-8 round-trip preserved), and the subcommand exits 0

#### Scenario: Programs inside the window CAN override the title by default
- **WHEN** the user runs `my-kitty window title "before"` then runs `printf '\e]2;after\a'` from inside the same window
- **THEN** the window's title (as observed via `kitten @ ls`) becomes `"after"` (because `--temporary` defaults ON for `window title`)

#### Scenario: --no-temporary makes the title sticky against OSC-2
- **WHEN** the user runs `my-kitty window title --no-temporary "sticky"` then runs `printf '\e]2;ignored\a'` from inside the same window
- **THEN** the window's title remains `"sticky"` after the OSC-2 sequence is processed

### Requirement: Tab-title scene primitive ships under `my-kitty tab title`

The system SHALL expose a `my-kitty tab title <text>` subcommand that sets
the title of a running kitty tab via the kitty remote-control socket. The
subcommand SHALL accept a single positional `<text>` argument passed
through to `kitten @ set-tab-title` byte-for-byte (UTF-8, including emoji).

Tab titles set via `kitten @ set-tab-title` are always permanent at the
kitty layer: `kitten @ set-tab-title --help` exposes no `--temporary`
flag, and OSC-2 escapes from programs running inside any window of the
tab do not affect the tab title in the first place (they affect window
titles only). The asymmetry with `my-kitty window title` is therefore at
the *subcommand surface*: `my-kitty tab title` MUST NOT accept a
`--temporary` flag (passing `--temporary` SHALL produce the standard
argparse "unrecognized argument" error). Curated tab titles always stick
by construction — no flag is needed to express that.

The subcommand SHALL accept the `--match <expression>` and
`--to unix:<path>` options with the same semantics as `my-kitty window
title`.

#### Scenario: Setting a plain-text tab title from inside kitty
- **WHEN** the user runs `my-kitty tab title "monitoring"` from a shell inside a kitty window where `$KITTY_LISTEN_ON` is set
- **THEN** the containing tab's title (as observed via `kitten @ ls`) becomes `"monitoring"` byte-identical to the argument, and the subcommand exits 0

#### Scenario: Setting an emoji-containing tab title
- **WHEN** the user runs `my-kitty tab title "🐋 monitoring"` from a shell inside a kitty window
- **THEN** the containing tab's title is byte-identical to `"🐋 monitoring"`, and the subcommand exits 0

#### Scenario: Tab title persists across OSC-2 escape sequences
- **WHEN** the user runs `my-kitty tab title "labeled"` then runs `printf '\e]2;ignored\a'` from inside any window of the tab
- **THEN** the tab's title remains `"labeled"` after the OSC-2 sequence (kitty's OSC-2 handling does not route to tab titles, and `set-tab-title` has no temporary mode)

#### Scenario: --temporary is rejected with an argparse error
- **WHEN** the user runs `my-kitty tab title --temporary "anything"`
- **THEN** the subcommand exits non-zero with an argparse error mentioning the unrecognized argument `--temporary`, and the tab title is unchanged

### Requirement: Socket auto-discovery falls back to `pgrep -x kitty`

The system SHALL implement a socket-discovery procedure for the scene
primitives' `kitten @` wrapper that resolves the target remote-control
socket from one of three sources, in priority order: an explicit `--to`
flag, the `$KITTY_LISTEN_ON` environment variable, or fallback
auto-discovery via `pgrep -x kitty`. The procedure MUST exit non-zero
with a specific error message on every ambiguity case (zero kitties,
multiple kitties, missing managed config).

When `$KITTY_LISTEN_ON` is unset and the user has not passed `--to`, the
system SHALL discover the kitty remote-control socket by enumerating
running kitty processes via `pgrep -x kitty`. The discovery rules SHALL
be:

1. If the managed `remote-control.conf` is absent or contains no
   `listen_on unix:` directive (i.e. `_parse_listen_on_base` returns
   `None`), the subcommand SHALL exit non-zero with a message on stderr of
   the form `"remote-control.conf missing or has no listen_on directive;
   run \`make install\` or pass --to unix:<path>"`. `pgrep` SHALL NOT be
   invoked in this case.
2. If zero PIDs are returned by `pgrep`, the subcommand SHALL exit
   non-zero with a message of the form `"no kitty process found; run
   kitty first or pass --to unix:<path>"` on stderr.
3. If exactly one PID is returned, the socket path resolves to
   `unix:<base>-<PID>`, where `<base>` is read from the `listen_on`
   directive in the managed `remote-control.conf` via `_parse_listen_on_base`
   — the same helper used by `doctor.py`. For a default install where
   `listen_on unix:/tmp/kitty` is configured, this yields
   `unix:/tmp/kitty-<PID>`; non-default `listen_on` paths are honoured
   without special-casing.
4. If two or more PIDs are returned, the subcommand SHALL exit non-zero
   with a message of the form `"multiple kitty processes (PIDs: X, Y);
   pass --to unix:/tmp/kitty-<pid> to disambiguate"` on stderr.

When `$KITTY_LISTEN_ON` is set (i.e. the subcommand is invoked from inside
a kitty window), the system SHALL use its value unchanged and SHALL NOT
invoke `pgrep`. When `--to` is passed, the system SHALL use the explicit
value unchanged and SHALL NOT inspect `$KITTY_LISTEN_ON` or `pgrep`.

When the resolved socket path is unreachable for any reason (e.g.
`--to unix:<path>` points at a non-existent socket, the kitty process
behind a discovered PID has terminated between discovery and dispatch,
or `kitten @` returns a non-zero exit code for any other reason), the
subcommand SHALL propagate `kitten @`'s stderr verbatim to its own
stderr and SHALL exit with `kitten @`'s exit code. The subcommand MUST
NOT wrap, paraphrase, or suppress `kitten @`'s error output — the user
sees what kitty saw.

#### Scenario: Single kitty, invocation from a non-kitty shell
- **WHEN** the user runs `my-kitty window title "from outside"` from a non-kitty shell (e.g. a GNOME Terminal launched from a keybinding) on a host where exactly one kitty process is running with PID 4242
- **THEN** the subcommand resolves the socket to `unix:/tmp/kitty-4242`, sets the focused kitty window's title to `"from outside"`, and exits 0

#### Scenario: Zero kitties, clear error message
- **WHEN** the user runs `my-kitty tab title "anything"` from a shell where `$KITTY_LISTEN_ON` is unset and `pgrep -x kitty` returns no PIDs
- **THEN** the subcommand exits non-zero and stderr contains the literal substrings `"no kitty process found"` and `"--to unix:"`

#### Scenario: Multiple kitties, disambiguation message
- **WHEN** the user runs `my-kitty window title "anything"` from a shell where `$KITTY_LISTEN_ON` is unset and `pgrep -x kitty` returns two PIDs
- **THEN** the subcommand exits non-zero and stderr contains the literal substring `"multiple kitty processes"` and lists every returned PID

#### Scenario: $KITTY_LISTEN_ON takes precedence over pgrep
- **WHEN** the user runs `my-kitty window title "anything"` from a shell where `KITTY_LISTEN_ON=unix:/tmp/kitty-1111` is set and `pgrep -x kitty` would return a different PID 2222
- **THEN** the subcommand targets the `unix:/tmp/kitty-1111` socket, never invokes `pgrep`, and the PID-2222 kitty is unaffected

#### Scenario: --to takes precedence over both $KITTY_LISTEN_ON and pgrep
- **WHEN** the user runs `my-kitty window title --to unix:/tmp/kitty-3333 "anything"`
- **THEN** the subcommand targets `unix:/tmp/kitty-3333` regardless of `$KITTY_LISTEN_ON` and regardless of how many kitties `pgrep` would return

#### Scenario: --to points at an unreachable socket
- **WHEN** the user runs `my-kitty window title --to unix:/tmp/kitty-does-not-exist "anything"` on a host where no socket exists at that path
- **THEN** the subcommand exits with the same non-zero code `kitten @` returned, and its stderr contains the exact stderr `kitten @` produced (typically a connection or no-such-file error message)

### Requirement: Scene primitives live under `src/kitty_setup/scenes/`

The system SHALL house scene primitives — title and every future Phase 2
§9-§14 primitive — under the Python package `src/kitty_setup/scenes/`.
The title primitive SHALL be implemented in
`src/kitty_setup/scenes/title.py`. A shared module
`src/kitty_setup/scenes/_client.py` SHALL encapsulate the `kitten @`
subprocess wrapper and the socket-discovery rules in one place, so that
§9-§14 primitives reuse one code path. The kitten binary path SHALL
resolve via the existing `installer.DEFAULT_DEST / "kitty.app" / "bin" /
"kitten"` pattern. If that path is not a file, `_client.py` SHALL fall
back to `shutil.which("kitten")` — the same two-step resolution used by
`doctor.py:_check_remote_control_per_probe_04` (lines 197–202). If
neither path yields a file, the subcommand SHALL exit non-zero with a
message on stderr of the form `"no kitten binary found; reinstall kitty
or ensure kitten is on PATH"`.

The existing `src/kitty_setup/doctor.py` helpers `_pgrep_kitty_pids` and
`_parse_listen_on_base` SHALL be lifted into
`src/kitty_setup/scenes/_client.py` (or a lower-level shared module if a
circular import requires it) and re-imported by `doctor.py`. The
`kitty-remote-control` doctor check behaviour SHALL be unchanged
post-refactor.

`_client.py`'s socket resolution SHALL follow this data flow: (1) if
`--to` was passed, use it directly; (2) if `$KITTY_LISTEN_ON` is set,
use it directly; (3) otherwise, call `_parse_listen_on_base(rc_conf)` to
read the base path from the managed `remote-control.conf`, then append
`-<PID>` from the single PID returned by `_pgrep_kitty_pids()`. Steps
(1) and (2) SHALL NOT invoke `_pgrep_kitty_pids` or read
`remote-control.conf`. The individual helpers `_pgrep_kitty_pids` and
`_parse_listen_on_base` are lifted from `doctor.py`; the dispatch logic
itself does not mirror `_check_remote_control_per_probe_04` (which
unconditionally enumerates all PIDs and has no `--to` or
`$KITTY_LISTEN_ON` short-circuit).

When `_client.py` constructs the `kitten @` subprocess argv, the socket
argument SHALL use the equals-sign form `--to=unix:<path>` (a single
argv element), matching the existing `doctor.py` invocation pattern
(`doctor.py:_kitten_ls_succeeds` builds `[str(kitten_bin), "@", f"--to=unix:{socket}", "ls"]`,
where `kitten_bin` is the fully-resolved binary path, not the bare string `"kitten"`).
The space-separated form `--to unix:<path>` SHALL NOT be used in the
subprocess argv, even though kitty accepts both forms — pinning the
form prevents subtle drift between scene primitives and the doctor's
behaviour. (User-facing `--help` text MAY render the option either way;
this requirement constrains only the constructed argv.)

#### Scenario: Title module imports the shared client
- **WHEN** a developer inspects `src/kitty_setup/scenes/title.py`
- **THEN** the file imports `kitten_at` (or equivalent) from `src/kitty_setup/scenes/_client.py` and contains no inline subprocess invocation of the `kitten` binary

#### Scenario: Doctor still uses the lifted helpers
- **WHEN** a developer runs the existing unit test suite at `tests/unit/test_doctor_remote_control.py` after the refactor
- **THEN** every test in that file passes without modification to the test logic itself (import paths in the test MAY be updated; assertions MUST NOT)

#### Testing approach for `_client.py`
`_client.py`'s socket-discovery paths (the `$KITTY_LISTEN_ON`-present
branch, the `--to`-explicit branch, the pgrep-single-PID branch, the
config-absent / `None`-base error branch, the zero-PID error branch, and
the multiple-PID error branch) SHALL each have a dedicated unit test
under `tests/unit/`, using subprocess and filesystem stubs consistent
with the patterns in `tests/unit/test_doctor_remote_control.py`. The
hypothesis probe (`tmp/h22-window-title/run.py`) exercises the promoted
behaviour end-to-end but is NOT a substitute for unit coverage of the
discovery logic.

Per `docs/agent-iteration.md` R7, the unit stubs in `tests/unit/` are
*provisional* until a corresponding integration test under
`tests/integration/` exercises the real `pgrep` and `kitten @` code
paths against a live kitty process. The task list SHALL include a task
"add integration test for `_client.py` socket-discovery (tests/integration/test_client_socket_discovery.py)
before promotion" to satisfy the R7 requirement. Until that integration
test exists and is green, each stub function in the unit test MUST carry
a one-line docstring naming the hypothesis probe (e.g.
`"Provisional per R7; grounded by tmp/h22-window-title/run.py"`).

Additionally, the change SHALL ship a CLI-level integration test under
`tests/integration/test_h22_window_title.py` that drives the full
`my-kitty window title` and `my-kitty tab title` dispatch path through
`cli.py` → `scenes/title.py` → `scenes/_client.py` against a live kitty
process spawned by the test (mirroring the raw-subprocess pattern of
`tests/integration/test_h21_remote_control_foundation.py`, not the
`KittySession` harness which overrides `listen_on`). This CLI-level
integration test covers the dispatch path that the unit tests stub out
and that `test_client_socket_discovery.py` exercises only at the
socket-discovery layer.

### Requirement: Hypothesis-driven shipping under `tmp/h22-window-title/`

The change SHALL be driven by a hypothesis-first promotion flow per
`docs/agent-iteration.md` R1, with all autonomous probe artefacts living
under `tmp/h22-window-title/` and SHALL be deleted before archive.

The hypothesis number `h22` is confirmed available: no `tmp/h22-*` or
`docs/repro/h22-*` path exists in the repository as of this spec.

The change SHALL include a hypothesis scratch directory at
`tmp/h22-window-title/` containing `run.py`, `expected.json`, and
`repro.md` per `docs/agent-iteration.md` R1 and step 4 of the loop. `run.py` SHALL be a
self-contained autonomous probe that spawns a kitty, exercises both the
window-title and tab-title primitives via direct `kitten @` shellouts
(not yet via the promoted `my-kitty` subcommand), and verifies the
observable state via `kitten @ ls`. For window titles, the probe SHALL
test that `kitten @ set-window-title --temporary` allows a subsequent
OSC-2 escape to override the title, and that `kitten @ set-window-title`
without `--temporary` keeps the title stable across the same escape.
For tab titles, the probe SHALL test that `kitten @ set-tab-title` sets
the title and that no OSC-2 escape from inside the tab affects it
(grounding the spec's claim that tab titles have no temporary mode and
no OSC-2 override path).

The directory SHALL be deleted after the promoted subcommand integration
tests pass. The change MUST NOT archive while `tmp/h22-window-title/`
still exists.

#### Scenario: Probe runs green on the user's host before promotion
- **WHEN** the user runs `python tmp/h22-window-title/run.py` on a host where kitty is installed and the managed config (with remote-control enabled) is loaded
- **THEN** the probe exits 0 and writes `actual.json` byte-identical to `expected.json`

#### Scenario: Probe directory is gone at archive time
- **WHEN** a reviewer inspects the change at archive time (when `openspec status` reports all artifacts done)
- **THEN** the path `tmp/h22-window-title/` does not exist

### Requirement: Manual repro doc records Linux + macOS status

The change SHALL ship `docs/repro/h22-window-title.md` documenting the
manual repro protocol (following the h<NN> repro shape used elsewhere in
`docs/repro/`). The doc SHALL include:
- A `## Manual repro` section: step-by-step instructions for running each
  scenario from the spec.
- A `## Linux Status` section, dated, with outcome `verified` (signed off
  by the user on Pop!_OS 24.04 + COSMIC + kitty 0.46.2) or `not yet
  verified` (blocks archive).
- A `## macOS Status` section with outcome `verified` or
  `deferred-with-reason` (likely deferred unless a macOS host is
  available — the kitten @ protocol is platform-agnostic so deferral is
  low risk).
- An `## Attempted alternatives` table capturing surface-shape decisions
  considered (e.g., verb-first CLI) with date + outcome, so future
  contributors don't re-litigate.
- A `## Known limitations` section covering at minimum: tab-bar emoji
  rendering depends on the active font's glyph coverage; `pgrep -x kitty`
  matches all kitty processes by name only (UID gating is enforced by the
  socket itself, not by discovery).

#### Scenario: Repro doc exists with both status sections
- **WHEN** the change is presented for archive
- **THEN** the file `docs/repro/h22-window-title.md` exists, contains a `## Linux Status` section dated with outcome `verified`, contains a `## macOS Status` section with outcome `verified` or `deferred-with-reason`, contains a non-empty `## Attempted alternatives` table, and contains a `## Known limitations` section that names emoji font coverage and the pgrep-by-name behaviour

### Requirement: Tab-accent scene primitive ships under `my-kitty tab accent`

The system SHALL expose a `my-kitty tab accent <color>` subcommand that
sets a kitty tab's accent color so the tab is visibly distinguishable
both when focused and when unfocused (the load-bearing PRD §9 invariant).
Implementation SHALL invoke `kitten @ set-tab-color` with BOTH
`active_bg=<color>` AND `inactive_bg=<color>` keys in the same call, so a
single user-supplied color satisfies the focused-and-unfocused
requirement without any auto-derivation logic.

The `<color>` positional argument accepts kitty's full color grammar:
- a named color from kitty's named-color table (e.g. `blue`, `darkblue`,
  `forestgreen`),
- a hex string of the form `#rrggbb` (e.g. `#0066cc`),
- the keyword `NONE` to reset the tab's accent to kitty's configured
  default.

The subcommand SHALL accept the following options:
- `--active-fg <color>` — override the foreground when the tab is focused.
  Passed to kitten as `active_fg=<color>`.
- `--inactive-fg <color>` — override the foreground when the tab is
  unfocused. Passed to kitten as `inactive_fg=<color>`.
- `--match <expression>` — kitty match expression passed through to
  `kitten @ --match`. When omitted, the default tab selector is the
  active tab.
- `--to unix:<path>` — explicit remote-control socket path, bypassing
  auto-discovery.

The wrapper MUST NOT validate the color string client-side; an invalid
color (probe-grounded example: `notacolor`) is rejected by kitten with
`"Error: notacolor is not a valid color"`. The wrapper SHALL propagate
kitten's stderr verbatim and exit with kitten's exit code.

#### Scenario: Setting tab accent with a hex color
- **WHEN** the user runs `my-kitty tab accent "#0066cc"` from inside a kitty window where `$KITTY_LISTEN_ON` is set
- **THEN** the kitten invocation includes both `active_bg=#0066cc` and `inactive_bg=#0066cc`, the subcommand exits 0, and the tab visibly carries the color whether focused or not

#### Scenario: Setting tab accent with a named color
- **WHEN** the user runs `my-kitty tab accent darkblue` from inside a kitty window
- **THEN** the subcommand exits 0 (kitten accepts the name; X11 rgb.txt convention applies)

#### Scenario: Resetting tab accent to default
- **WHEN** the user runs `my-kitty tab accent NONE`
- **THEN** the subcommand exits 0 and the tab's accent reverts to whatever the kitty config defined for `active_tab_*` / `inactive_tab_*`

#### Scenario: Invalid color is rejected with kitten's error message
- **WHEN** the user runs `my-kitty tab accent notacolor`
- **THEN** the subcommand exits non-zero, stderr contains the substring `"is not a valid color"`, and no tab state has changed

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

The `<color>` positional argument accepts the same color grammar as
`tab accent` (named, hex, or `NONE`).

The subcommand SHALL accept `--match <expression>` and
`--to unix:<path>` with the same semantics as the other scene
primitives.

#### Scenario: Setting background on the active window
- **WHEN** the user runs `my-kitty window background "#001a33"` from inside a kitty pane
- **THEN** `kitten @ get-colors` for that pane reports `background #001a33`, the subcommand exits 0, and no other pane's background changed

#### Scenario: Per-pane isolation
- **WHEN** the user has 2 panes (id 1 and id 2) and runs `my-kitty window background "#001a33" --match id:1`
- **THEN** `kitten @ get-colors --match id:1` reports `background #001a33`, AND `kitten @ get-colors --match id:2` reports the unchanged default `background #000000`

#### Scenario: Named color resolves via kitty's named-color table
- **WHEN** the user runs `my-kitty window background darkblue`
- **THEN** `kitten @ get-colors` reports `background #00008b` (X11 rgb.txt convention) for the active window, and the subcommand exits 0

### Requirement: OS-window font-size scene primitive ships under `my-kitty os-window font-size`

The system SHALL expose a `my-kitty os-window font-size <value>`
subcommand that sets the font size for ALL sub-windows in the active OS
window via `kitten @ set-font-size <value>`. The primitive is OS-window
scoped because kitty's architecture binds font size to the OS window:
`kitten @ set-font-size --help` states "in kitty all sub-windows in the
same OS window must have the same font size." The CLI noun (`os-window`)
SHALL surface this scope honestly so users learn the model from the
command rather than from a surprise.

The `<value>` positional argument accepts kitten's full grammar:
- absolute (e.g. `14` — interpreted as 14 pt),
- relative with `+`/`-`/`*`/`/` prefix (e.g. `+2`, `-2`, `*1.1`, `/2`),
- `0` to reset to the configured default.

The subcommand SHALL accept:
- `--all` — applies the change to all current AND future OS windows
  (kitten's "configured" semantics). The flag's persistence behaviour
  SHALL be documented in `--help`.
- `--to unix:<path>` — explicit remote-control socket path.

The subcommand SHALL NOT expose `--match` because the kitten verb
operates at the OS-window level, not the window level.

The subcommand MUST handle the argparse quirk where a leading-`-` value
(e.g. `-2`) looks like a flag. The CLI SHALL accept the value as a
single string argument (no client-side numeric parsing) and pass it
through to kitten verbatim.

#### Scenario: Setting absolute font size
- **WHEN** the user runs `my-kitty os-window font-size 14`
- **THEN** the kitten invocation is `kitten @ set-font-size 14`, the subcommand exits 0, and all sub-windows in the active OS window re-render at 14 pt

#### Scenario: Setting relative font size with + prefix
- **WHEN** the user runs `my-kitty os-window font-size +2`
- **THEN** the kitten invocation is `kitten @ set-font-size +2`, the subcommand exits 0, and the font size increases by 2 pt from the current value

#### Scenario: Resetting font size to configured default
- **WHEN** the user runs `my-kitty os-window font-size 0`
- **THEN** the kitten invocation is `kitten @ set-font-size 0`, the subcommand exits 0, and the font size returns to the value in kitty.conf

#### Scenario: --all flag applies to current + future OS windows
- **WHEN** the user runs `my-kitty os-window font-size 14 --all`
- **THEN** the kitten invocation includes `--all`, the subcommand exits 0, and any subsequently-spawned OS windows also start at 14 pt

### Requirement: OS-window opacity scene primitive ships under `my-kitty os-window opacity`

The system SHALL expose a `my-kitty os-window opacity <value>`
subcommand that sets the background opacity of the active OS window via
`kitten @ set-background-opacity <value>`. The primitive is OS-window
scoped because kitty's architecture binds opacity to the OS window:
`kitten @ set-background-opacity --help` states "the background opacity
affects all kitty windows in a single OS window."

The `<value>` positional argument SHALL be a float in the range
`0.0`–`1.0` inclusive, passed unchanged to kitten. Client-side range
validation is OPTIONAL; kitten errors on out-of-range values.

The subcommand SHALL accept:
- `--toggle` — exposes kitten's "reset to default if current opacity
  equals the requested value, else set" semantics. **Implementation
  invariant:** when `--toggle` is passed, the kitten argv SHALL be
  constructed as `[..., "--toggle", "<value>"]` (flag BEFORE positional).
  The reverse order causes kitten to fail with `"Must specify exactly 1
  argument(s) for set_background_opacity"` because kitten consumes the
  positional first and treats the trailing `--toggle` as a stray arg.
- `--all` — apply to all current AND future OS windows.
- `--to unix:<path>` — explicit socket.

This primitive requires `dynamic_background_opacity yes` in the kitty
config (shipped by this change as `config/kitty/dynamic-opacity.conf`,
per the `kitty-install` capability delta). Without the directive, kitten
errors with `"You must turn on the dynamic_background_opacity option in
kitty.conf to be able to set background opacity"`. The wrapper SHALL
propagate this error verbatim — no special handling, no user-facing
re-wording.

#### Scenario: Setting opacity to 0.7
- **WHEN** the user runs `my-kitty os-window opacity 0.7` on a host where `dynamic_background_opacity yes` is configured
- **THEN** the kitten invocation is `kitten @ set-background-opacity 0.7`, the subcommand exits 0, and `kitten @ ls` reports `os_window[0].background_opacity` approximately equal to `0.7` (with tolerance `< 0.01` — kitty stores opacity as a float32 so the stored value is `0.699999988`)

#### Scenario: Toggle resets opacity to default when value matches current
- **WHEN** the user has just set opacity to `0.7` and then runs `my-kitty os-window opacity 0.7 --toggle`
- **THEN** the kitten invocation argv is `["set-background-opacity", "--toggle", "0.7"]` (flag before positional), the subcommand exits 0, and `kitten @ ls` reports `os_window[0].background_opacity` equal to `1.0` (kitty default)

#### Scenario: Opacity without dynamic_background_opacity errors with clear stderr
- **WHEN** the user runs `my-kitty os-window opacity 0.5` on a host where `dynamic_background_opacity yes` is NOT configured
- **THEN** the subcommand exits non-zero and stderr contains the literal substring `"You must turn on the dynamic_background_opacity option in kitty.conf"`

### Requirement: Scenes package extends with one module per primitive

The system SHALL house each new primitive in a dedicated module under
`src/kitty_setup/scenes/`. The layout post-change SHALL be:

```
src/kitty_setup/scenes/
├── __init__.py     (already exposes title; extends to expose accent / background / font / opacity)
├── _client.py      (unchanged)
├── title.py        (unchanged)
├── accent.py       (NEW: set_tab_accent + cli_set_tab_accent)
├── background.py   (NEW: set_window_background + cli_set_window_background)
├── font.py         (NEW: set_os_window_font_size + cli_set_os_window_font_size)
└── opacity.py      (NEW: set_os_window_opacity + cli_set_os_window_opacity)
```

Each new module SHALL follow the same shape as `title.py`: a
domain-typed callable plus a `cli_*(args: argparse.Namespace)` wrapper.
Each module SHALL invoke kitten exclusively via
`_client.kitten_at(...)`; no module SHALL build a `subprocess.run(...)`
call directly against the kitten binary.

`__init__.py` SHALL re-export each new module via `from kitty_setup.scenes
import accent, background, font, opacity` so `cli.scenes.<module>` is
reachable as a module attribute (required for `monkeypatch.setattr`
targets in the CLI dispatch unit tests, same pattern as the existing
`title` re-export).

#### Scenario: Each new module imports the shared client
- **WHEN** a developer greps for `subprocess.run` under `src/kitty_setup/scenes/`
- **THEN** matches appear only in `_client.py`; `accent.py`, `background.py`, `font.py`, `opacity.py`, and `title.py` invoke kitten exclusively through `_client.kitten_at`

#### Scenario: __init__.py re-exports the new modules
- **WHEN** a developer runs `python -c "from kitty_setup import scenes; print(scenes.accent, scenes.background, scenes.font, scenes.opacity)"`
- **THEN** the four module objects print without ImportError or AttributeError

### Requirement: Managed payload ships `dynamic-opacity.conf`

The system SHALL place a file `dynamic-opacity.conf` under the managed
payload directory (`~/.config/kitty/kitty-setup/dynamic-opacity.conf`)
and SHALL add `include dynamic-opacity.conf` to
`~/.config/kitty/kitty-setup/kitty-setup.conf` after the existing
per-topic includes. The file MUST contain the single directive
`dynamic_background_opacity yes`. The file MUST carry a top-of-file
comment block citing this change (`phase2-scene-styling`), the
`kitty-scenes` capability, and the fact that the directive enables
`kitten @ set-background-opacity` (without which the verb errors with
`"You must turn on the dynamic_background_opacity option in kitty.conf
to be able to set background opacity"`).

The directive's visual impact MUST be characterised in the comment
block as zero on hosts that do not invoke `my-kitty os-window opacity`
(kitty's default opacity stays at 1.0 unless the user runs the
primitive).

The file SHALL be removed from the managed payload directory whenever
the managed payload directory itself is removed. The system MUST NOT
leave a dangling `include dynamic-opacity.conf` line in
`kitty-setup.conf` after uninstall — uninstall removes the entire
payload directory per `kitty-config-management`, so the include line
vanishes with it. The `--keep-config` flag SHALL preserve
`dynamic-opacity.conf` alongside the rest of the payload.

#### Scenario: Fresh install ships dynamic-opacity.conf
- **WHEN** the user runs `make install` on a host where the change is applied
- **THEN** the file `~/.config/kitty/kitty-setup/dynamic-opacity.conf` exists with `dynamic_background_opacity yes` present
- **AND** `~/.config/kitty/kitty-setup/kitty-setup.conf` contains the line `include dynamic-opacity.conf`
- **AND** `kitty --debug-config` exits 0

#### Scenario: Re-install is byte-identical
- **WHEN** the user runs `make install` twice with no intervening changes
- **THEN** the second run leaves `dynamic-opacity.conf` byte-identical and does not create a new `kitty.conf.bak.*` file (no-op contract from `kitty-config-management`)

#### Scenario: Uninstall removes the file
- **WHEN** the user runs `my-kitty uninstall` after a successful install that shipped `dynamic-opacity.conf`
- **THEN** the file is removed AND the include line in `kitty-setup.conf` is gone with the rest of the payload directory

#### Scenario: --keep-config preserves the file
- **WHEN** the user runs `my-kitty uninstall --keep-config`
- **THEN** `~/.config/kitty/kitty-setup/dynamic-opacity.conf` is preserved alongside the rest of the payload

### Requirement: Hypothesis-driven shipping under `tmp/h23-styling/`

The change SHALL be driven by a hypothesis-first promotion flow per
`docs/agent-iteration.md` R1 and step 4 of the loop. The hypothesis
scratch directory `tmp/h23-styling/` SHALL exist with `run.py`,
`expected.json`, and `repro.md` during proposal and apply, and SHALL be
deleted before archive.

`run.py` SHALL be a self-contained autonomous probe that spawns a raw
kitty subprocess (NOT KittySession — the harness's `--listen-on` CLI
flag overrides config-level `listen_on`), drives `kitten @
set-tab-color`, `set-colors`, `set-font-size`, and `set-background-opacity`
directly, and asserts the spec's behavioural claims:

- `set-tab-color` accepts named colors, hex colors, and `NONE`; rejects
  invalid colors with a clear error message.
- `set-colors --match` isolates the background change to the matched
  pane only (verified via `kitten @ get-colors --match` on each pane).
- `set-font-size` exits 0 for absolute, relative, and reset forms. Font
  size is NOT programmatically observable via `kitten @ ls`; visual
  outcome is the load-bearing observable (covered by the manual repro).
- `set-background-opacity` requires `dynamic_background_opacity yes` in
  the kitty config and errors with the canonical message otherwise. With
  the directive set, the value is reflected in
  `kitten @ ls -> os_window[0].background_opacity` (with float-precision
  tolerance). `--toggle` resets to default when the requested value
  matches the current value.

The directory SHALL be deleted after the promoted integration tests are
green. The change MUST NOT archive while `tmp/h23-styling/` still exists.

#### Scenario: Probe runs green on the user's host before proposal lands
- **WHEN** the user runs `uv run python tmp/h23-styling/run.py` on a host where kitty is installed and the managed config (with remote-control enabled) is loaded
- **THEN** the probe exits 0 and writes `actual.json` byte-identical to `expected.json`

#### Scenario: Probe directory is gone at archive time
- **WHEN** a reviewer inspects the change at archive time (when `openspec status` reports all artifacts done)
- **THEN** the path `tmp/h23-styling/` does not exist

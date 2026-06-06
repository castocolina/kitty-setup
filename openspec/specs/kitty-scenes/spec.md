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

#### Scenario: Manual repro doc is verified before archive
- **WHEN** the change is moved to `openspec/changes/archive/`
- **THEN** `docs/repro/h25-scene-launcher.md` exists, its `## Linux Status` row reads `verified` with a date and host details, and its `## macOS Status` row reads `verified` or `deferred-with-reason` with a one-paragraph reason

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

### Requirement: Scene launcher composition primitive ships under `my-kitty scene launch`

The `my-kitty` binary SHALL expose a `scene launch` subcommand that composes the existing scene primitives (title, accent, background, layout) into one user gesture. Invoking `my-kitty scene launch <args>` SHALL spawn one or more panes, each optionally pre-styled with title, working directory, background color, and a startup command.

The destination depends on the **pane count** and on whether the launch happens **from inside kitty** (the `$KITTY_WINDOW_ID` environment variable, exported by kitty into every window, identifies the origin window):

- A multi-pane scene launched **from inside kitty** (`$KITTY_WINDOW_ID` is set) SHALL be materialised INTO the current tab: the origin window becomes pane 0 (restyled in place via `set-window-title` / `set-colors`, with any explicit pane-0 `cwd`/`cmd` fed to the reused shell via `send-text`), the remaining panes open as `--type=window` splits in the same tab, and `--layout` / `--tab-title` / `--tab-accent` are applied to that current tab (kitty defaults `goto-layout` / `set-tab-title` / `set-tab-color` to the focused tab, so no `--match` is needed). NO new tab is created. This is the in-kitty path, so a multi-pane scene launched from a shell never steals a separate tab.
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

#### Scenario: Multi-pane scene fills the current tab when launched inside kitty

- **WHEN** the running kitty has one tab with one window, and the user invokes a 3-pane scene (`layout=tall`, `tab_title="DEV"`, panes `shell` / `git` / `watch`) from a shell **inside that window** so `$KITTY_WINDOW_ID` is set
- **THEN** NO new tab is created (the tab count is unchanged), the current tab holds exactly the 3 scene panes in order (`shell` is the reused origin window, `git` and `watch` are new splits), the tab's title becomes `DEV`, the active layout is `tall`, and the command exits 0

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

### Requirement: Scene launcher lives at `src/kitty_setup/scenes/launcher.py`

The launcher module SHALL ship as `src/kitty_setup/scenes/launcher.py`, a sibling of `title.py`, `accent.py`, `background.py`, `font.py`, and `opacity.py`. It SHALL import only from `kitty_setup.scenes._client` (for `kitten_at` + `SceneClientError`) and standard library; no other module of the package and no external dependency.

The module SHALL export at minimum:

- A `Pane` dataclass (frozen) with fields `title: str | None`, `cmd: str | None`, `cwd: str | None`, `bg: str | None`, all defaulting to `None`.
- A pure function `parse_pane_spec(s: str) -> Pane` that parses the `--pane key=value` form and raises a clear exception on malformed input (no `=`, duplicate key, unknown key, trailing comma, empty input).
- A `launch_scene(layout, tab_title, tab_accent, panes, *, to=None) -> int` callable that takes a parsed scene and returns the first non-zero kitten exit code (or 0 if all calls succeed). It SHALL NOT have an argparse dependency — argparse plumbing lives in the `cli_scene_launch` handler.
- A `cli_scene_launch(args)` handler that argparse calls via `set_defaults(func=…)`. This handler SHALL parse each `--pane` string via `parse_pane_spec`, build the `Pane` list, and invoke `launch_scene`. It SHALL catch `SceneClientError` and parser errors, print a clear stderr message, and return exit code 1.

#### Scenario: Module imports only from `_client` and stdlib

- **WHEN** a reviewer inspects `src/kitty_setup/scenes/launcher.py` imports
- **THEN** every non-stdlib import is from `kitty_setup.scenes._client`; there is no import of `accent`, `background`, `font`, `opacity`, or `title` (the launcher composes via raw `_client.kitten_at()` calls, not by reusing the per-primitive Python wrappers)

#### Scenario: `parse_pane_spec` is a pure function exercisable in unit tests

- **WHEN** a unit test calls `parse_pane_spec("title=docker ps,cmd=docker ps,bg=#001f3f")` with no kitty running
- **THEN** the call returns `Pane(title="docker ps", cmd="docker ps", cwd=None, bg="#001f3f")` without making any subprocess call

### Requirement: Hypothesis-driven shipping under `tmp/h25-scene-launcher/`

A hypothesis probe SHALL exist at `tmp/h25-scene-launcher/run.py` with companion `expected.json` and `repro.md` files, exercising the 5 wire-level questions that govern the launcher's call algorithm (probe Q1: launch combine; Q2: cmd shape; Q3: id capture + `--no-response`; Q4: tab focus race; Q5: 3-pane scene). The probe SHALL be autonomous (raw `subprocess` against a self-spawned kitty pinned via `/tmp/kitty-<pid>`), MUST exit 0 with output `[h25] green: actual == expected` when re-run on the user's host, and SHALL be deleted before the change is archived.

The integration test `tests/integration/test_h25_scene_launcher.py` SHALL promote the probe's assertions, one named test per question, all gated on `KITTI_INTEGRATION=1`. The test names SHALL match the mapping in `design.md` D5. The integration test layer SHALL import the shared `_kitty_subprocess.py` helpers established by h22+h23+h24 (no new spawn/socket primitives are introduced).

#### Scenario: Probe is green at apply time, deleted at archive time

- **WHEN** `/opsx:apply phase2-scene-launcher` begins on the user's host
- **THEN** `uv run python tmp/h25-scene-launcher/run.py` exits 0 with `[h25] green: actual == expected`

- **WHEN** the change is moved to `openspec/changes/archive/`
- **THEN** the directory `tmp/h25-scene-launcher/` does not exist

#### Scenario: Each probe question is reflected in one integration test

- **WHEN** a reviewer reads `tests/integration/test_h25_scene_launcher.py`
- **THEN** the file contains exactly the five named tests from `design.md` D5 plus one end-to-end test invoking `my-kitty scene launch` via subprocess; every probe key referenced in D5's mapping table is covered by at least one assertion in the corresponding test

### Requirement: Named TOML scene recipes launch under `my-kitty scene launch <name>`

The `my-kitty` binary SHALL accept an optional positional `name` on the existing
`scene launch` subcommand (`nargs='?'`). When a `name` is supplied,
`my-kitty scene launch <name>` SHALL load the scene recipe at
`<scenes_dir>/<name>.toml`, build the same `(layout, tab_title, tab_accent,
list[Pane])` arguments the inline `--pane` form produces, and materialise the
scene by invoking the **unchanged** `launch_scene()` engine. The declarative
form SHALL introduce no new kitten-call behavior: the wire algorithm, exit-code
semantics, and styling are exactly those of the `scene launch` composition
Requirement.

The two invocation modes SHALL be mutually exclusive and validated before any
kitten call:

- A `name` together with any `--pane` flag SHALL exit non-zero with a stderr
  message stating the two forms are contradictory.
- Neither a `name` nor any `--pane` SHALL exit non-zero with a stderr message
  stating that a scene name or at least one `--pane` is required.
- In name mode the recipe file SHALL be authoritative: supplying
  `--layout`, `--tab-title`, or `--tab-accent` alongside a `name` SHALL exit
  non-zero with a stderr message stating those flags are not accepted with a
  named scene.
- The `--to=unix:<socket>` flag SHALL remain valid in both modes.

The TOML schema SHALL be flat and map one-to-one onto the engine arguments.
Recognised top-level keys SHALL be exactly `layout`, `tab_title`, and
`tab_accent` (all optional strings). Panes SHALL be expressed as an array of
`[[pane]]` tables whose recognised keys SHALL be exactly `title`, `cmd`, `cwd`,
and `bg` — the `Pane` field names. The loader SHALL import the `Pane` dataclass
from `launcher.py` and SHALL NOT redefine it or rename its fields. A `cmd` value
SHALL be a string carried into the engine's `bash -lc <cmd>` wrapping unchanged.
A key whose value is an empty string SHALL normalise to `None` (absent),
mirroring `parse_pane_spec`.

Schema validation SHALL match the strictness of the inline parser: any unknown
top-level key or unknown `[[pane]]` key, and any value of the wrong TOML type,
SHALL cause the command to exit non-zero with a stderr message naming the
offending key (and, for an unknown key, the recognised set) before any kitten
call is issued. A recipe with no `[[pane]]` table SHALL be rejected with the
engine's existing "at least one pane" semantics.

#### Scenario: Named scene launches from its TOML file

- **WHEN** `<scenes_dir>/monitoring.toml` contains `tab_title = "🐳 mon"`, `layout = "tall:mirrored=true"`, and three `[[pane]]` tables (`title="p1", cmd="echo p1"`; `title="p2", bg="#001f3f", cmd="echo p2"`; `title="p3"`) and the user invokes `my-kitty scene launch monitoring`
- **THEN** a new tab titled `🐳 mon` appears with the `tall` layout (`layout_opts.mirrored == "y"`), the tab contains exactly 3 windows titled `p1`, `p2`, `p3` in order, `p2`'s `background` reads `#001f3f`, and the command exits 0 — identical to the equivalent inline `--pane` invocation

#### Scenario: Name and `--pane` together is rejected

- **WHEN** the user invokes `my-kitty scene launch monitoring --pane 'title=x'`
- **THEN** the command exits non-zero, prints a stderr message stating that a named scene and inline `--pane` flags are contradictory, and creates no new tab

#### Scenario: Neither name nor `--pane` is rejected

- **WHEN** the user invokes `my-kitty scene launch` with no positional name and no `--pane`
- **THEN** the command exits non-zero and prints a stderr message stating a scene name or at least one `--pane` is required

#### Scenario: Inline `--pane` form is unchanged

- **WHEN** the user invokes `my-kitty scene launch --tab-title=t --pane 'title=p1,cmd=echo p1'` with no positional name
- **THEN** the behavior is byte-for-byte identical to the `phase2-scene-launcher` inline form (same kitten calls, same exit code)

#### Scenario: Style flags with a named scene are rejected

- **WHEN** the user invokes `my-kitty scene launch monitoring --tab-accent=#ff0000`
- **THEN** the command exits non-zero and prints a stderr message stating `--layout`/`--tab-title`/`--tab-accent` are not accepted with a named scene (the recipe file is authoritative)

#### Scenario: Unknown key in a recipe is rejected before any kitten call

- **WHEN** `<scenes_dir>/bad.toml` contains a top-level `tab_color = "#fff"` (unknown key) and the user invokes `my-kitty scene launch bad`
- **THEN** the command exits non-zero, prints a stderr message naming the unknown key `tab_color`, and calls `kitten @ launch` zero times

#### Scenario: Empty-string value normalises to absent

- **WHEN** a `[[pane]]` table contains `title = ""` alongside `cmd = "echo hi"`
- **THEN** the constructed `Pane` has `title is None` (not `""`), so no `--title` flag is emitted, matching the inline parser's empty-value behavior

### Requirement: Scene recipes are user data under `$XDG_CONFIG_HOME/kitty-setup/scenes/`

The scenes directory SHALL resolve to `$XDG_CONFIG_HOME/kitty-setup/scenes/`
when `$XDG_CONFIG_HOME` is set, otherwise `~/.config/kitty-setup/scenes/`. This
location SHALL be distinct from the managed payload at
`~/.config/kitty/kitty-setup/`: the installer SHALL NOT write scene files there
and uninstall SHALL NOT delete them. A scene's name SHALL be the file stem
(`monitoring.toml` → `monitoring`).

The `name` positional SHALL be guarded against path traversal: a `name`
containing a path separator (`/`), a `..` segment, or any OS path separator
SHALL be rejected with a non-zero exit and a stderr message, so a scene name can
never resolve outside the scenes directory. A request for a name with no
matching file SHALL exit non-zero with a stderr message that lists the available
scene names. A missing scenes directory SHALL be treated as "no scenes" (a
friendly empty state), not an error.

The loader SHALL use `tomllib` from the Python standard library; the change SHALL
add no new third-party dependency.

#### Scenario: Path-traversal name is rejected

- **WHEN** the user invokes `my-kitty scene launch ../../etc/something`
- **THEN** the command exits non-zero with a stderr message about an invalid scene name, and reads no file outside the scenes directory

#### Scenario: Unknown scene name lists what is available

- **WHEN** the scenes directory contains `monitoring.toml` and `docker.toml`, and the user invokes `my-kitty scene launch nope`
- **THEN** the command exits non-zero and the stderr message lists `docker` and `monitoring` as the available scenes

#### Scenario: XDG override is honored

- **WHEN** `$XDG_CONFIG_HOME` is set to `/tmp/xdg` and `/tmp/xdg/kitty-setup/scenes/demo.toml` exists
- **THEN** `my-kitty scene launch demo` loads that file (the resolver prefers `$XDG_CONFIG_HOME` over `~/.config`)

### Requirement: Scene enumeration ships under `my-kitty scene list`

The `my-kitty` binary SHALL expose a `scene list` sub-subcommand — a sibling of
`scene launch`, NOT `scene launch list` (which would be parsed as a request to
launch a scene named `list`). With no flags it SHALL print, one scene per line
in sorted order, a rich summary of each `*.toml` recipe in the scenes directory:
the scene name, its `tab_title` (if any), and its pane count, parsed from the
file. A recipe that fails to parse SHALL be reported on its line as malformed
(with the parse error) rather than silently omitted. An empty or missing scenes
directory SHALL print a friendly empty-state message and exit 0.

The default output SHALL be a column-aligned table with a header row
(`NAME`, `TAB`, `PANES`); column widths SHALL be computed by terminal display
width (East-Asian wide / fullwidth code points counted as two cells, zero-width
combining marks skipped) so emoji-bearing tab titles do not collapse adjacent
columns. This alignment SHALL be done in-process with the standard library only
(no `rich` or other third-party table dependency).

`scene list` SHALL accept an optional `--names`/`-q` flag that prints only the
bare scene names, one per line, for scripting.

#### Scenario: Aligned table with a header

- **WHEN** the scenes directory contains `monitoring.toml` (3 panes, `tab_title="monitoring"`) and `docker.toml` (2 panes, `tab_title="docker"`) and the user invokes `my-kitty scene list`
- **THEN** the command exits 0, the first line is a `NAME`/`TAB`/`PANES` header, and there is one sorted, column-aligned row per scene showing the name, tab title, and pane count

#### Scenario: Malformed recipe is surfaced, not hidden

- **WHEN** the scenes directory contains a `broken.toml` with invalid TOML and the user invokes `my-kitty scene list`
- **THEN** the `broken` line indicates the file is malformed and includes the parse error, and the command still lists the other valid scenes

#### Scenario: Empty scenes directory is a friendly empty state

- **WHEN** the scenes directory is missing or contains no `*.toml` files and the user invokes `my-kitty scene list`
- **THEN** the command exits 0 and prints a message indicating there are no scenes yet

#### Scenario: `--names` prints bare names for scripting

- **WHEN** the user invokes `my-kitty scene list --names`
- **THEN** only the sorted bare scene names are printed, one per line, with no tab-title or pane-count decoration

### Requirement: Scene recipe loader lives at `src/kitty_setup/scenes/recipe.py`

The recipe loader SHALL ship as `src/kitty_setup/scenes/recipe.py`, a sibling of
`launcher.py`. It SHALL import the `Pane` dataclass from
`kitty_setup.scenes.launcher` (reusing the engine's vocabulary rather than
redefining it) and otherwise import only from the standard library
(`tomllib`, `pathlib`, `os`). The module SHALL export at minimum: `scenes_dir()`
returning the resolved scenes `Path`; `load_scene(name) -> (layout, tab_title,
tab_accent, list[Pane])` performing path-traversal guarding, file resolution,
TOML parsing, and schema validation; `list_scenes()` returning the sorted scene
summaries used by `scene list`; and a `cli_scene_list(args)` handler that
argparse calls via `set_defaults(func=…)`. The `cli_scene_launch` handler in
`launcher.py` SHALL gain the name branch that calls `recipe.load_scene(name)`
then `launch_scene(...)`.

The `scenes` package SHALL export `recipe` (added to
`src/kitty_setup/scenes/__init__.py`) so `cli.py` references the handler as
`scenes.recipe.cli_scene_list` (mirroring `scenes.launcher.cli_scene_launch`)
and tests can monkeypatch it.

#### Scenario: Loader reuses the engine's `Pane`, not a copy

- **WHEN** a reviewer inspects `src/kitty_setup/scenes/recipe.py`
- **THEN** `Pane` is imported from `kitty_setup.scenes.launcher` and is not redefined in `recipe.py`; the recognised pane keys are exactly the `Pane` field names

#### Scenario: `load_scene` is a pure function exercisable without kitty

- **WHEN** a unit test points `scenes_dir()` at a temp directory containing `demo.toml` and calls `load_scene("demo")` with no kitty running
- **THEN** the call returns the parsed `(layout, tab_title, tab_accent, [Pane, …])` tuple without making any subprocess call

### Requirement: Manual repro doc records the declarative recipe

A repro doc SHALL ship at `docs/repro/scene-recipe-toml.md` with the standard
sections (Why, Manual repro, Linux Status, macOS Status, Attempted alternatives,
Known limitations, Recipes). The Manual repro SHALL show authoring a
`<scenes_dir>/<name>.toml` and launching it with `my-kitty scene launch <name>`,
plus a `my-kitty scene list` example. macOS visual verification SHALL be
deferred-with-reason (the `kitten @` protocol is platform-agnostic; tab-bar
rendering nuances may differ). Verification SHALL note that no new `tmp/hNN`
wire probe is introduced because the kitten-call algorithm is unchanged from
h25; the declarative surface is covered by unit tests plus one end-to-end
integration test gated on `KITTI_INTEGRATION=1`.

#### Scenario: Repro doc exists with the standard sections

- **WHEN** a reviewer opens `docs/repro/scene-recipe-toml.md`
- **THEN** it contains the Why, Manual repro, Linux Status, macOS Status, Attempted alternatives, Known limitations, and Recipes sections, and the Manual repro demonstrates both `scene launch <name>` and `scene list`

#### Scenario: End-to-end integration test covers the named-launch path

- **WHEN** a reviewer reads `tests/integration/test_scene_recipe_e2e.py`
- **THEN** it contains at least one test, gated on `KITTI_INTEGRATION=1`, that writes a temp `.toml` recipe, runs `my-kitty scene launch <name>` against a freshly spawned kitty, and asserts the same tab/pane/bg observables as the h25 e2e test

### Requirement: Scene name shell-completes for `scene launch`

The positional `name` of `scene launch` SHALL carry an argcomplete completer
that returns the `*.toml` file stems in the scenes directory, so a user pressing
TAB after `my-kitty scene launch ` gets the available scene names. The completer
SHALL glob filenames only (no TOML parse), so a malformed recipe never breaks
completion, and SHALL filter by the current prefix.

#### Scenario: Tab-completion lists scene names by prefix

- **WHEN** the scenes directory holds `dev.toml`, `docker.toml`, `broken.toml` (malformed) and the user requests completion for prefix `d`
- **THEN** the completer returns `dev` and `docker` (sorted), does not raise on the malformed file, and excludes non-matching names

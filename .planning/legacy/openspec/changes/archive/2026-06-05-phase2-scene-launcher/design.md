# Design — phase2-scene-launcher

## Context

`phase2-scene-title-primitive` (h22, archived), `phase2-scene-styling`
(h23, archived), and `phase2-extra-layout-mirrored-tall` (h24, archived)
landed the five single-noun primitives plus the curated mirrored Tall
layout. The `kitty-scenes` capability now covers: window/tab title, tab
accent, window background, OS-window font, OS-window opacity, and a
shared `scenes/_client.py` that handles socket discovery + the
`kitten @ <verb>` wrapper. Each primitive is a thin CLI handler over
`_client.kitten_at()`.

Phase 2 §12 of `docs/requirements.md` (and roadmap line 42) asks for one
extra capability: launch a tab with a chosen layout, multiple pre-styled
windows, and per-window startup commands — a "scene" — invoked once
from the daily shell. This is the first composition primitive, sitting
on top of the existing single-noun primitives. §13 (named scenes /
TOML) and §14 (chord-to-scene wiring) both depend on this landing first.

Inputs to this design:

- `docs/requirements.md` §12 ("Launch a tab with a chosen layout,
  multiple pre-styled windows, and per-window startup commands").
- `docs/propossal_roadmap.md` line 42 ("Spawn N windows in a tab with
  per-window styles and startup commands, from a TOML recipe").
- `openspec/specs/kitty-scenes/spec.md` (existing; gets one ADDED
  Requirement for the launcher plus the standard hypothesis-discipline
  + repro-doc ADDED Requirements per the h22/h23/h24 pattern).
- Probe findings under `tmp/h25-scene-launcher/expected.json` and
  `repro.md`.
- Kitty's official `kitten @ launch` surface (verified via context7
  against `kovidgoyal/kitty`'s `launch.rst` + `kitten/launch`): supports
  `--type={window,tab,os-window,overlay}`, `--title`, `--tab-title`,
  `--cwd`, `--env`, `--keep-focus`, `--location`, `--match`, `--hold`,
  `--no-response`; returns the new window id on stdout.

The h25 probe answered the load-bearing wire-level questions before any
design choice was locked. The most consequential findings, restated:

1. `kitten @ launch --type=tab` combines `--tab-title`, `--cwd`,
   `--title`, `--hold`, and a positional `bash -lc "..."` startup
   command in ONE call. Verified via tab.title, window.title,
   window.cwd, and `get-text` markers.
2. The new tab is focused synchronously. Subsequent bare
   `kitten @ launch --type=window` calls land in the new tab without
   `--match`. No race.
3. `--type=tab` returns the new tab's first **window** id on stdout, NOT
   the tab id. To target the tab afterward (e.g. `set-tab-color`), use
   `--match recent:0` (probe-verified to still route correctly after
   intervening launches).
4. Bare argv, `bash -lc "cmd"`, AND `bash -lc "cmd1; cmd2"` all work as
   the launch positional. Wrapping every user-supplied command as
   `bash -lc <cmd>` gives shell features (`|`, `$VAR`, `;`, `&&`) for
   free without any quoting code on our side.
5. A full 3-pane scene (1 tab + 2 panes + 1 layout + 1 per-pane bg + 1
   tab accent) completes in 6 kitten calls and ~85 ms — well inside one
   human-perception frame. Phase 3 kitten promotion under the
   "latency materially affects UX" criterion is NOT justified.

## Goals / Non-Goals

**Goals:**

- Ship one new `my-kitty scene launch` subcommand that takes a layout,
  optional tab-level styling, and one or more `--pane key=value` groups,
  and composes them into a kitten call sequence that materialises a
  new tab on the user's running kitty in one user gesture.
- Reuse the existing `scenes/_client.kitten_at()` surface — same socket
  discovery (`$KITTY_LISTEN_ON` → pgrep fallback), same error path,
  same kitten binary resolution. Zero net-new wiring at the client layer.
- Promote the h25 probe to integration tests (one named test per
  probe question), gated on `KITTI_INTEGRATION=1`. Delete the probe
  directory before archive.
- Author a repro doc with Linux Status verified by the user manually,
  macOS deferred-with-reason — same template as h22/h23/h24.

**Non-Goals:**

- TOML recipe schema, named-scene resolution, scene lookup from
  `~/.config/kitty-setup/scenes/` — that is §13's job (`phase2-named-scenes`).
  §12 ships the imperative engine; §13 will wrap it.
- Chord-to-scene wiring — that is §14's job (`phase2-chord-to-scene`).
  No `map ctrl+shift+...` line is added by this change.
- A `my-kitty scene close <name>` or `my-kitty scene list` surface.
  Scenes in §12 are one-shot launches; persistence concepts belong to §13.
- Per-pane opacity. Kitty's opacity is OS-window-scoped (per h23's
  findings); per-pane is not on offer. `--pane bg=...` IS supported
  because `kitten @ set-colors background=...` IS per-window.
- macOS visual verification of the composed scene. Deferred to a
  follow-up under the existing `kitty-scenes` "macOS-deferred-with-note"
  pattern.

## Decisions

### D1: CLI shape — `--pane key=value` (Shape A from /opsx:explore)

Final surface:

```
my-kitty scene launch \
    [--layout=<name>[:<opts>]] \
    [--tab-title=<text>] [--tab-accent=<color>] \
    --pane 'title=<text>,cmd=<command>,cwd=<path>,bg=<color>' \
    [--pane '...'] ... \
    [--to=unix:<socket>]
```

- `--pane` is repeatable; argparse `action='append'` aggregates them
  into a list of strings, each parsed by `parse_pane_spec()` into a
  `Pane` dataclass.
- Recognised keys inside a `--pane` value: `title`, `cmd`, `cwd`, `bg`.
  Unknown keys raise a `ValueError` with a clear message
  listing the recognised set.
- Commas inside values are escaped as `\,`. Backslashes as `\\`. The
  parser is a tiny hand-written state machine, NOT shlex or csv — both
  of which mis-handle `\,` semantics for our use case.
- At least one `--pane` is REQUIRED. Zero panes is rejected with exit
  non-zero and a clear stderr ("scene launch requires at least one
  `--pane`").
- `--layout` is a string passed verbatim as the `kitten @ goto-layout`
  argument (so `tall:mirrored=true` works directly). Default: omit the
  `goto-layout` call entirely (kitty picks the first entry of
  `enabled_layouts`).

Alternatives rejected (recorded from /opsx:explore):

- **Shape B (repeated per-attr flags)** — `--pane-title X --pane-cmd Y
  --pane-bg Z` triples are position-coupled implicitly; verbose for >2
  panes; misalignment is easy to introduce by deleting a partial triple.
- **Shape C (single JSON blob)** — unambiguous and scales, but shell
  quoting is awful for hand typing; saves the parser at the cost of
  the user's experience.
- **Shape D (defer §12; only ship §13 TOML)** — violates requirements.md
  ordering (§12 BEFORE §13) and removes the one-shot daily-shell use
  case.

### D2: Pane spec parser — hand-written, NOT shlex/csv

`parse_pane_spec(s: str) -> Pane` is implemented as a tiny state
machine that walks the input character-by-character, treats `\,` as a
literal comma, `\\` as a literal backslash, and splits on bare commas.
Then each segment is split on the FIRST `=` (so the value side may
contain `=`, e.g. `cmd=docker run --env VAR=value bash`).

Why not `shlex`: `shlex` is shell-like quoting (single quotes, double
quotes, escape sequences inside quotes); we want literal-comma escape
ONLY, with no other shell-quoting machinery — that's the surface area
of the `kitten @ launch --env VAR=value` style. Using `shlex` would
make `--pane "title=docker ps"` (with a literal space) parse
differently than `--pane title='docker ps'`, which is the kind of
surprise we want to avoid.

Why not `csv`: `csv.reader` does not support backslash escapes; it uses
double-quoting (`"a,b"` for a comma inside a field). That's another
syntax to teach users and clashes with shell quoting layered above.

The hand-written parser is ~30 lines and unit-testable as a pure
function. Edge cases covered in tests:

- Empty value: `title=` → empty string title (treated as "no title").
- No `=` in segment: `title` → error ("malformed pane spec; expected
  key=value, got 'title'").
- Repeated key: `title=a,title=b` → error ("duplicate key 'title' in
  pane spec").
- Trailing comma: `title=a,` → error ("trailing comma in pane spec").
- Escaped comma: `title=a\,b,cmd=echo` → title="a,b", cmd="echo".
- Escaped backslash: `title=a\\b` → title="a\b".

### D3: kitten call algorithm (probe-grounded)

Given a parsed scene `(layout, tab_title, tab_accent, panes=[p0, p1, ..., pN-1])`:

```
# 1. Launch the new tab + first pane in one call.
win0 = launch --type=tab \
              [--tab-title=<tab_title>]   if tab_title else omit \
              [--title=<p0.title>]        if p0.title else omit \
              [--cwd=<p0.cwd>]            if p0.cwd else omit \
              --hold \
              [bash -lc <p0.cmd>]         if p0.cmd else omit (no positional)

# 2. Apply per-pane background to p0, if requested.
if p0.bg:
    set-colors --match id:<win0> background=<p0.bg>

# 3. Apply the layout, if --layout was passed.
if layout:
    goto-layout <layout>    # operates on the new (focused) tab; no --match needed

# 4. For each subsequent pane p1..pN-1:
for p in panes[1:]:
    win = launch --type=window \
                 [--title=<p.title>]      if p.title else omit \
                 [--cwd=<p.cwd>]          if p.cwd else omit \
                 --hold \
                 [bash -lc <p.cmd>]       if p.cmd else omit
    if p.bg:
        set-colors --match id:<win> background=<p.bg>

# 5. Tab accent, if requested.
if tab_accent:
    set-tab-color --match recent:0 active=<tab_accent>
```

Call count: `1 (tab launch) + (1 if p0.bg) + (1 if layout) + (N-1) (window launches) + sum(1 for p in panes[1:] if p.bg) + (1 if tab_accent)`.

For the canonical 3-pane / 1-bg / 1-accent scene from h25: `1 + 0 + 1 + 2 + 1 + 1 = 6` — matches `Q5_kitten_call_count`.

Notable choices:

- **`--hold` is always passed.** Without it, panes whose startup command
  exits immediately (`echo something`, `docker ps | head`) close as soon
  as the command finishes. The user typically wants to see the output;
  `--hold` keeps the pane open after the child exits. If the user wants
  the pane to close on exit, they can pass `cmd=bash -c '<cmd>'`
  without `--hold` — but our wrapper always uses `--hold` for the
  predictable visible-output default.
- **No `--no-response`.** We always capture the window id from stdout
  so per-pane styling (Step 2 / inner Step in 4) targets by exact id,
  not by `--match recent:0` (which drifts if anything else launches
  between our calls).
- **`--match recent:0` ONLY for the tab-accent call** (Step 5). At that
  point we know the most-recently-affected tab is the one we just
  built. The probe verified `recent:0` works after the intervening
  pane launches.
- **Wrap all user-supplied commands as `bash -lc <cmd>`.** Gives the
  user shell features for free without us doing any quoting. The
  `--noprofile --norc` flag we use in tests is NOT used at runtime —
  the user's daily shell rc DOES get sourced (so aliases, $PATH
  customisations, etc. are available inside scene panes).

### D4: Error handling — fail-soft on per-pane bg, fail-hard on launch

If `kitten @ launch` fails (returncode != 0), the scene aborts and
the caller gets the kitten exit code propagated. We do NOT try to
clean up partially-built scenes — kitty has no "undo last launch"
verb, and the user can close the partial tab with `ctrl+shift+q` if
something went wrong.

If `kitten @ set-colors` fails (e.g. an invalid color string), we
print the kitten stderr to our stderr, mark the scene's overall exit
code non-zero, but CONTINUE building the rest of the scene. Rationale:
a bad color on pane 2 of 4 shouldn't leave the user with a half-built
tab. The user gets a useful error message AND a usable scene.

Same logic for `set-tab-color`: the accent failing is a soft warning,
not a hard abort.

### D5: Probe → integration test mapping

`tmp/h25-scene-launcher/run.py` Phase findings → integration tests:

| Probe assertion(s) | Test name |
|---|---|
| `Q1_launch_ok`, `Q1_tab_title_matches`, `Q1_window_title_matches`, `Q1_window_cwd`, `Q1_get_text_contains_marker` | `test_launch_tab_combines_tab_title_window_title_cwd_and_cmd_in_one_call` |
| `Q2a_bare_argv_marker_seen`, `Q2b_bash_lc_simple_marker_seen`, `Q2c_bash_lc_compound_first/second_marker_seen` | `test_startup_command_accepts_bare_argv_bash_lc_and_compound_shell` |
| `Q3a_window_stdout_is_int`, `Q3b_returned_id_matches_window_id`, `Q3b_returned_id_matches_tab_id`, `Q3c_no_response_stdout_empty`, `Q3d_recent_zero_title_landed` | `test_launch_stdout_is_window_id_and_recent_zero_still_targets_after_no_response` |
| `Q4_exactly_one_new_tab`, `Q4_new_tab_window_count == 3`, `Q4_old_tab_count_unchanged` | `test_new_tab_focuses_synchronously_subsequent_window_launches_land_in_new_tab` |
| `Q5_kitten_call_count == 6`, `Q5_new_tab_window_count == 3`, `Q5_layout_mirrored == True`, `Q5_all_three_titles_seen` | `test_three_pane_scene_takes_six_kitten_calls_with_mirrored_tall_and_distinct_titles` |

Plus one integration test that exercises the **CLI surface end-to-end**
(invokes `my-kitty scene launch` via `subprocess.run` and verifies the
resulting kitty state). This is what gives the change confidence that
the parser + the call algorithm + the kitten wire format all integrate.

Unit tests under `tests/unit/test_scenes_launcher.py`:

- `parse_pane_spec` happy paths (one key, multiple keys, escaped comma,
  escaped backslash, value with `=`).
- `parse_pane_spec` error paths (no `=`, duplicate key, trailing comma,
  unknown key, empty input).
- `launch_scene` argv composition: given a parsed scene, the produced
  kitten argv lists match a recorded golden (monkeypatch the
  `_client.kitten_at` so no real kitten runs in unit tests).
- `cli_scene_launch` error paths: zero panes, parser errors, kitten
  call failure.

### D6: Latency budget and Phase 3 trigger

The h25 probe measured 6 kitten calls / ~85 ms for a 3-pane scene.
The Phase 3 promotion criterion that's relevant here is "subprocess
and socket latency materially affects the user experience" — 85 ms is
well under any human-perception threshold (the common "feels instant"
budget is 100-200 ms). No kitten promotion is justified by §12.

If §13 (named scenes) introduces scenes with 8+ panes or large numbers
of per-pane styles, the call count grows. The threshold to revisit is
~300 ms total invocation time on the user's host. Until that's
measured against a real scene the user wants to use, we ship scripts +
config.

### D7: macOS deferred-with-reason

Per `kitty-scenes` "Linux-first delivery, macOS-deferred-with-note"
pattern (established by h22 and continued by h23 + h24):
`docs/repro/h25-scene-launcher.md` ships with `## Linux Status` =
`verified (date, host)` after user manual sign-off in apply §verify,
and `## macOS Status` = `deferred-with-reason` with the note:
"no Mac host available; `kitten @ launch` is platform-agnostic; tab
strip composition / per-pane background visual fidelity is the only
macOS-specific concern." Tracked under follow-up
`phase2-scene-launcher-macos`.

## Risks / Trade-offs

- **Comma-as-separator in `--pane` values.** Titles, commands, and
  paths can contain literal commas. → Mitigation: `\,` escape, codified
  in the parser + documented in `--help` + tested explicitly. The vast
  majority of practical scenes have no commas in any value.
- **Partial-scene state on mid-launch failure.** If `launch` succeeds
  for panes 1 and 2 but pane 3's command is malformed, the user sees
  a half-built tab. → Mitigation: fail-hard on launch (D4) means the
  user gets a clean error and can close the partial tab with
  `ctrl+shift+q`. We do NOT auto-clean because there's no kitten verb
  for "close this exact tab id"; closing-by-match is risky if the user
  has switched tabs.
- **`--hold` blocks the visual close of short-lived commands.** A pane
  running `echo hi` stays open showing `hi\n` until the user explicitly
  closes it. This is the desired default but may surprise. → Mitigation:
  documented in the repro doc's Known Limitations; a future flag like
  `--pane no-hold=true` or a `cmd-mode=transient` key could be added if
  the friction is real.
- **`recent:0` for tab accent.** This works AFTER all per-pane launches
  because the new tab is the most-recently-affected. But if a user
  switches tabs between the scene-launch invocation and the
  set-tab-color call (~85 ms window), accent lands on the wrong tab.
  → Mitigation: the time window is too small for a user to react;
  documented as a Known Limitation; an upgrade path is to walk `ls`
  from `win0` (returned by step 1) up to its tab id and use
  `--match tab_id:<id>` for set-tab-color, at the cost of one extra
  kitten call.
- **No idempotency.** Re-running `my-kitty scene launch ...` builds a
  SECOND tab; there's no "update if exists" semantic. → Mitigation:
  scenes in §12 are one-shot. Named scenes (§13) may grow an idempotency
  story; not §12's problem.
- **Cmd quoting subtleties when the user passes `--pane cmd='echo "hi"'`.**
  Shell does the outer quoting; we pass the result verbatim to
  `bash -lc`. → Mitigation: integration test exercises a command with
  embedded quotes to verify behaviour. Documented as a Recipe in the
  repro doc.

## Migration Plan

No migration. The change adds one Python module + one CLI subparser +
one set of tests + one repro doc. The user's existing kitty + payload
+ binding catalog are untouched. Rollback is `make uninstall` (removes
the deployable `my-kitty` binary along with the rest of the install);
the scene-launching capability disappears with the umbrella.

## Open Questions

- **Should `--pane cmd=...` automatically append a `; exec bash` so the
  user's shell prompt appears after the command finishes**? Without it,
  with `--hold`, the user sees the command output frozen at exit. With
  it, the pane reaches an interactive shell. Tentative answer: NO — the
  user-supplied command is the contract; adding `exec bash` is a
  surprising side effect. If the user wants interactivity, they pass
  `cmd='docker stats ; exec bash'` explicitly. Defer the decision to
  /review-spec; reviewer may push back.
- **Should the kitten exit codes feed into our own exit code as a sum,
  or just "non-zero if any kitten call failed"**? Argparse-native is
  the latter; matches the existing scene primitives. Tentative answer:
  match existing primitives (returncode = first non-zero kitten exit).

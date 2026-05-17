# H22 — Window / tab title with text + emoji (first scene primitive)

**Capability:** kitty-scenes (Phase 2 §8).

**Status:** Promoted. Implementation in
[`src/kitty_setup/scenes/`](../../src/kitty_setup/scenes/) (`title.py` + `_client.py`).
CLI surface: `my-kitty window title <text>` (`--temporary` defaults ON; programs
inside the window may override via OSC-2) and `my-kitty tab title <text>` (no
`--temporary` flag; tab titles always stick because `kitten @ set-tab-title`
exposes no such flag and OSC-2 escapes don't route to tab titles).

Autonomous integration tests under
[`tests/integration/test_h22_window_title.py`](../../tests/integration/test_h22_window_title.py)
and
[`tests/integration/test_client_socket_discovery.py`](../../tests/integration/test_client_socket_discovery.py)
exercise the 6 spec scenarios end-to-end plus the live-socket discovery branch
(R7 promotion gate for the unit stubs).

## Why

Phase 2 §8 of `docs/requirements.md` calls for the first scene primitive — set
a kitty window or tab title to arbitrary UTF-8 (including emoji). It is the
foundation that §9 (accent), §10 (background), §11 (font), §13 (named scene)
and §14 (chord-to-scene) all layer on top of, so the CLI shape lands here.

The protocol-level unknown ("does the remote-control socket round-trip emoji
byte-faithfully?") was killed during the h22 explore: `kitten @
set-window-title "🐳 docker test"` followed by `kitten @ ls` returned the
emoji unchanged.

## Manual repro

Pre-reqs: `make install` has been run (so `~/.local/kitty.app/bin/kitten`
and `my-kitty` are on PATH).

### 1. Emoji round-trip — window

From inside a kitty window:

```bash
my-kitty window title "🐳 docker test"
kitten @ ls | python -c "import json,sys; p=json.load(sys.stdin); print(p[0]['tabs'][0]['windows'][0]['title'])"
```

Expected: prints `🐳 docker test` exactly.

### 2. Emoji round-trip — tab

```bash
my-kitty tab title "🐋 monitoring"
kitten @ ls | python -c "import json,sys; p=json.load(sys.stdin); print(p[0]['tabs'][0]['title'])"
```

Expected: prints `🐋 monitoring` exactly.

### 3. Window `--temporary` default — programs CAN override

```bash
my-kitty window title "before"
printf '\e]2;after\a'
```

Expected: the window title changes from `before` (titles can be observed in
the OS window manager or via `kitten @ ls`).

### 4. Window `--no-temporary` — programs CANNOT override

```bash
my-kitty window title --no-temporary "sticky"
printf '\e]2;ignored\a'
```

Expected: the window title stays `sticky` after the printf.

### 5. Tab title persists across OSC-2

```bash
my-kitty tab title "labeled"
printf '\e]2;ignored\a'
```

Expected: the tab title stays `labeled` (OSC-2 escapes don't route to tab
titles regardless of mode — kitten has no `--temporary` flag for tabs).

### 6. `tab title --temporary` is rejected

```bash
my-kitty tab title --temporary "anything"
```

Expected: argparse error mentioning the unrecognized argument; exit non-zero;
the tab title is unchanged.

### 7. Out-of-kitty invocation auto-discovers a single kitty

From a non-kitty terminal (e.g. GNOME Terminal, WezTerm) while exactly one
kitty is running:

```bash
my-kitty window title "from outside"
```

Expected: the title of the running kitty's focused window changes to `from
outside`.

### 8. `--to` unreachable socket propagates kitten's exit

```bash
my-kitty window title --to unix:/tmp/kitty-does-not-exist "anything"
echo "exit: $?"
```

Expected: non-zero exit code, kitten's stderr printed verbatim (typically
a connection or no-such-file error).

## Linux Status

**verified (2026-05-16, Pop!_OS 24.04 + COSMIC + kitty 0.46.2)** — all
8 manual scenarios above (window/tab emoji round-trip, `--temporary`
default + override, OSC-2 routing asymmetry, `tab title --temporary`
rejection, out-of-kitty invocation, `--to` unreachable) signed off by
the user. Autonomous integration tests under
`tests/integration/test_h22_window_title.py` and
`tests/integration/test_client_socket_discovery.py` are green
(`KITTI_INTEGRATION=1 pytest tests/integration/`).

## macOS Status

**deferred-with-reason** — no Mac host available. The `kitten @` protocol is
platform-agnostic, so the wire-level behaviour is expected to be identical;
tab-bar emoji rendering may differ (macOS font fallback rules apply). Tracked
under follow-up change `phase2-scene-title-primitive-macos`.

## Attempted alternatives

| Date       | Approach considered                                  | Outcome   |
| ---------- | ---------------------------------------------------- | --------- |
| 2026-05-13 | Verb-first CLI (`my-kitty title window <text>`)      | ❌ rejected: explodes the top-level verb space when §9-§14 land (`title`, `accent`, `background`, `font`, `transparency`, `layout`, `scene`); noun-first scales better |
| 2026-05-13 | Symmetric `--temporary` flag on `tab title`          | ❌ rejected: `kitten @ set-tab-title --help` exposes no `--temporary` flag, so the option would be a no-op (or worse, a silent lie); spec drops the flag from `tab title` and rejects it loudly via argparse |
| 2026-05-13 | Compositor-API focused-window discovery (X11/Wayland)| ❌ rejected as overkill: heavy, X11-only on the daily host, doesn't actually answer "which kitty socket" without traversing `_NET_WM_PID`. `pgrep -x kitty` covers 95% of cases ergonomically and fails loudly otherwise |
| 2026-05-13 | Auto-discovery via X11 focused-window walk           | ❌ rejected: same reason — fails on Wayland, and the `pgrep` single-PID path is the actual ergonomic 95% case |

## Recipes — dynamic titles via shell substitution

The primitive does not implement template placeholders (`{path}`,
`{branch}`, etc.) on purpose — the shell is already a templating engine,
and §13 (named scenes) in `docs/propossal_roadmap.md` is the right home
for curated recipes. Until then, drive dynamic content with `$(…)`:

```bash
# basename of cwd, decorated
my-kitty tab title "🐋 monitoring on <<$(basename "$PWD")>>"

# basename + current git branch (empty when not in a repo)
my-kitty tab title "🐋 $(basename "$PWD") · $(git branch --show-current 2>/dev/null)"

# last two path segments
my-kitty tab title "📂 $(pwd | rev | cut -d/ -f1-2 | rev)"

# permanent label that survives vim/ssh title changes
my-kitty window title --no-temporary "🛠  $(basename "$PWD") · build"

# shell alias for terseness
alias tt='my-kitty tab title'
tt "🐋 mon <<$(basename "$PWD")>>"
```

These work because `$(…)` expands **before** `my-kitty` sees the
argument — the byte-faithful UTF-8 round-trip applies to the post-expansion
string. Cross-shell note: zsh and bash use `$(…)`; fish uses `(…)`; nushell
uses `($"...(pwd | path basename)...")` string-interpolation.

When a recipe stabilises into something you invoke from a chord (Phase 2
§14), promote it to a named scene rather than keeping the literal command
on hand.

## Known limitations

- **Tab-bar emoji rendering depends on the active font's glyph coverage.**
  The wire protocol round-trips bytes faithfully (verified empirically), but
  whether the user *sees* `🐳` in the tab bar depends on the font configured
  in kitty for tab-bar text (default kitty font, or whatever the user's
  `font_family` directive points at, augmented by emoji-font fallback).
- **`pgrep -x kitty` matches by process name only.** On shared hosts this can
  surface processes the user doesn't own; the resulting socket path is
  UID-gated by the kernel UDS (per the `kitty-remote-control` spec), so a
  stranger's socket fails closed with a permission error from kitty. The
  user-facing error names the PIDs found.
- **Auto-discovery requires exactly one kitty.** Two or more running kitty
  processes → non-zero exit with a message listing all PIDs and the `--to
  unix:<path>` escape hatch. Verified by `test_h22_window_title.py::test_discovery_errors_when_no_kitty`
  (zero case) and by manual repro (multi case — see §9.5 of tasks.md).
- **No autonomous test for the multi-kitty disambiguation message.**
  `test_h22_window_title.py` covers zero-PIDs but not multi-PIDs at the
  integration level (the unit test `test_resolve_socket_multi_pids_raises`
  covers the discovery code path; the message format is verified manually
  per §9.5). Rationale: integration multi-PIDs would race against the
  user's daily kitty; unit + manual is the right split.

## Follow-ups

- `phase2-scene-title-primitive-macos` — re-verify on a macOS host when one
  is available.

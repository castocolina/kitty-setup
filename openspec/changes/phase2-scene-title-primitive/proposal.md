# phase2-scene-title-primitive

## Why

Phase 2 §8 of `docs/requirements.md` calls for the first "scene" primitive — a
command that sets a kitty window or tab title to arbitrary text (including
emoji). It is the foundation that §9 (accent), §10 (background), §11 (font),
§13 (named scene), and §14 (chord-to-scene) all layer on top of, so the
surface decisions taken here (CLI shape, defaults, code location) propagate
across the rest of Phase 2.

The protocol-level unknown that historically blocked this work — "does
kitty's remote-control socket round-trip emoji byte-faithfully?" — was killed
during the h22 explore: `kitten @ set-window-title "🐳 docker test"` followed
by `kitten @ ls` returned `'🐳 docker test'` unchanged. The wire format
works, the remote-control surface is live (shipped by
`phase2-remote-control-foundation`), and there is no longer a reason to
defer.

## What Changes

- New `my-kitty window title <text>` subcommand: sets the focused (or
  selector-matched) kitty window's title, defaulting to `--temporary` ON so
  programs running inside the window (vim, ssh, npm, docker) keep their
  ability to update the title via OSC-2.
- New `my-kitty tab title <text>` subcommand: sets the focused (or
  selector-matched) kitty tab's title. Tab titles are always permanent at
  the kitty layer (`kitten @ set-tab-title` has no `--temporary` flag, and
  OSC-2 escapes don't route to tab titles), so the subcommand does NOT
  expose `--temporary` — passing it produces an argparse error.
- Both subcommands expose `--match <expr>` for kitty match-expressions and
  `--to unix:<path>` as the manual escape hatch when socket auto-discovery
  is undesirable. The window subcommand additionally exposes
  `--temporary / --no-temporary` (argparse `BooleanOptionalAction`,
  default ON), reflecting `kitten @ set-window-title`'s flag.
- Out-of-kitty invocation honours `$KITTY_LISTEN_ON` when set; otherwise
  auto-discovers the sole running kitty via `pgrep -x kitty`. Zero or
  multiple kitty processes → non-zero exit with a message pointing at
  `--to`.
- New `src/kitty_setup/scenes/` package houses the primitive
  (`scenes/title.py`) plus a shared `scenes/_client.py` thin wrapper around
  `kitten @`. §9-§14 primitives will land as sibling modules in this
  package.
- Refactor: `_pgrep_kitty_pids` and `_parse_listen_on_base` lift out of
  `src/kitty_setup/doctor.py` into `scenes/_client.py` so future scene
  primitives reuse one socket-discovery code path without a circular import.
  The existing `kitty-remote-control` doctor check imports them back. No
  doctor behaviour change.
- New autonomous integration test file
  `tests/integration/test_h22_window_title.py` covering emoji round-trip,
  `--temporary` asymmetric defaults, and discovery error paths. Mirrors the
  raw-subprocess pattern from `test_h21_remote_control_foundation.py`.
- Hypothesis-first: scratch under `tmp/h22-window-title/run.py` per
  `docs/agent-iteration.md`, deleted on promotion. Manual repro under
  `docs/repro/h22-window-title.md` with Linux Status verified and macOS
  Status deferred-with-reason.

Not in scope (explicit follow-ups):
- §9-§12 sibling primitives (accent, background, font, transparency) → each
  ships as its own change once §8 is in place.
- §13 named scenes + §14 chord-to-scene wiring.
- macOS verification of the title primitive → tracked under follow-up
  `phase2-scene-title-primitive-macos`.

## Capabilities

### New Capabilities

- `kitty-scenes`: Runtime scene primitives that drive kitty via the
  remote-control socket. Ships with one primitive (window/tab title) and is
  designed to grow as §9-§14 land. Covers CLI surface shape, socket
  discovery, `--temporary` semantics, and the out-of-kitty invocation
  contract.

### Modified Capabilities

- `my-kitty-cli`: gains two new top-level subcommands (`window` and `tab`),
  each with a `title <text>` sub-subcommand. The CLI capability's existing
  requirements about argparse-driven subcommand dispatch are unchanged in
  shape; the requirement list grows to enumerate the new verbs.

## Impact

- Code: `src/kitty_setup/cli.py` (new subparsers),
  `src/kitty_setup/scenes/` (new package: `__init__.py`, `_client.py`,
  `title.py`), `src/kitty_setup/doctor.py` (helper extraction, behaviour
  unchanged).
- Tests: `tests/unit/test_scenes_title.py` (new),
  `tests/integration/test_h22_window_title.py` (new),
  `tests/unit/test_doctor_remote_control.py` (import path update only).
- Hypothesis scratch: `tmp/h22-window-title/` (created and deleted within
  this change).
- Docs: `docs/repro/h22-window-title.md` (new manual repro).
- Dependencies: none added. The thin `kitten @` wrapper shells out to the
  same binary the doctor already uses.
- Runtime surface: kitty's remote-control socket already exposed by
  `phase2-remote-control-foundation`; this change consumes it, does not
  extend it.
- Risk: small. The wire format is empirically verified, the socket
  discovery code is lifted from already-tested doctor helpers, and the
  primitive is invoked only on explicit user command (no install-time
  changes, no auto-applied side effects).

---
created: 2026-10-15T12:13:10.983Z
title: Headless install that always fetches latest kitty
area: tooling
severity: minor
files:
  - tools/setup.sh
  - .planning/ROADMAP.md (Phase 9)
---

## Problem

The owner wants kitty-setup installable fully headless (no prompts, no TTY, no GUI session), and in
that mode it must always download the latest upstream kitty. Later, `../tools-installer` should be
able to link/delegate to this project instead of installing bare kitty.

## Solution

TBD. Likely folds into Phase 9 (Distribution & Release Channels): `tools/install.sh` /
`tools/setup.sh` gain a non-interactive path (flag and/or env, no confirm prompts) and a
"latest kitty" resolution via the upstream installer. Needs a stable, scriptable contract for
`../tools-installer` (exit codes, flags, idempotence).

Conflicts to settle in discuss-phase before planning:

- `PROJECT.md` Out of Scope: "kitty auto-upgrade on reinstall — upgrading kitty stays the user's
  action; doctor only reports a too-old version (R3.4)". "Always latest" in headless mode contradicts
  this; decide whether it is opt-in headless-only or amends that decision.
- Phase 9 channel selection (rolling vs pinned release) is about kitty-setup itself; define how it
  interacts with the kitty version (latest kitty on any channel, or pinned per channel).
- Version floor (R3.4, 0.49) still applies after a "latest" install; doctor stays the check.
- macOS path: headless kitty.app placement is a Phase 9/10 hypothesis until run on a real Mac.
- Bash allow-list (`AGENTS.md` Stack): any new shell must stay inside `tools/setup.sh` /
  `tools/uninstall.sh` or become a `my-kitty` subcommand.

## Context

`consolidate-into-my-kitty-setup-cli` (D2) shipped uninstall with three
layered scopes: default (config-only), `--kitty` (also remove kitty.app +
symlink + desktop entry), `--self` (print the manual self-removal command).
That layout was chosen to make the most aggressive paths opt-in, on the
theory that "uninstall" should default to the smallest blast radius.

User testing on 2026-05-05 surfaced two problems with that theory:

1. **Discoverability**: a user typing `make uninstall` expects "everything
   you put on my system" to be removed. They don't know about `ALL=1`. The
   current default leaves kitty.app + binary + backups behind without
   warning.
2. **Confirm-prompt drift**: the prompt always prints "Backups under
   ~/.config/kitty/kitty.conf.bak.* will be kept", even when no backups
   exist. That line is informational about a CURRENT-default behavior the
   user didn't realise was the default.

The fix is structural: invert the defaults, keep `--self`'s print-only
restraint, and let opt-out flags handle the niche "I want to keep
something" cases.

## Goals / Non-Goals

**Goals:**

- `make uninstall` (no env vars) wipes the entire footprint we created
  (config block, payload, kitty.app, symlink, desktop entry, every
  backup file).
- The self-removal command for the `my-kitty` binary still prints; never
  executes. D2 of consolidate stays in force.
- Three opt-out flags (`--keep-backups`, `--keep-config`, `--keep-kitty`)
  cover the discoverable preservation cases. Flags COMPOSE — combining
  any subset preserves the union.
- `make uninstall` env-var knobs (`KEEP_BACKUPS=1`, `KEEP_CONFIG=1`,
  `KEEP_KITTY=1`) map 1:1 to the CLI flags. Multiple knobs work via
  multiple env vars set together.
- Confirm prompt enumerates only the items that WILL be removed for the
  chosen flag set. No "will be kept" fluff.
- Drop the `--kitty` and `--self` flags entirely from the CLI surface.
- Drop the `make uninstall ALL=1` knob entirely from the Makefile.
- Update README, CLAUDE.md, and `make help` to describe the new defaults.

**Non-Goals:**

- Auto-removing the `my-kitty` binary. Print-only stays.
- A `--dry-run` flag. The confirm prompt + KITTI_FORCE bypass cover the
  safety story.
- Pruning the `kitty-setup` tool venv under
  `~/.local/share/uv/tools/`. uv owns its lifecycle; the install
  re-creates it on demand.
- Reworking the `prune` subcommand. `prune` is for routine maintenance;
  `uninstall` is for teardown.
- Backwards-compatibility shim for `--kitty` / `--self` / `ALL=1`. Single
  user today; clean break is cheaper than carrying aliases.

## Decisions

### D1 — Invert defaults; opt-OUT via `--keep-*` flags

Default `my-kitty uninstall` removes everything. Three orthogonal
preserve-flags: `--keep-backups`, `--keep-config`, `--keep-kitty`. They
compose (multiple flags preserve the union). No mutual exclusion; passing
all three reduces uninstall to a no-op that only prints the self-removal
banner.

**Alternative considered:** keep the old default (config-only) and add a
single `--all` flag for the aggressive scope. Rejected — perpetuates the
discoverability problem the user flagged. The aggressive case is the
common case; the niche case ("I want to keep my settings") is the one
that should require ceremony.

**Alternative considered:** allow `--scope=all|config|kitty` style
exclusive arg. Rejected — combinatorial cases (preserve backups AND keep
kitty.app) need composability, exclusive choices don't get there
cleanly.

### D2 — Self-removal banner: print on every uninstall, regardless of flags

The `_SELF_REMOVAL_BANNER` (manual `uv tool uninstall my-kitty` + the
rc-file PATH cleanup line) printed only with `--self` in the old design.
That made the banner a third layer in the scope hierarchy. Inversion
removes the layering: the banner is two short lines, costs nothing, and
ALWAYS being told "to also remove the binary, run X" is friendlier than
silent omission.

The print-not-execute restraint stays — see consolidate D2 for the
rationale (running binary deleting its own files has cross-distro
failure modes; cost-of-asking-user-to-type-one-line is low).

**Alternative considered:** have the binary auto-remove via
`os.execvp("uv", ["uv", "tool", "uninstall", "my-kitty"])` so the user
gets one-shot teardown. Rejected — same reasoning as consolidate D2; not
worth the failure modes.

### D3 — Make `KEEP_*=1` env vars instead of `KEEP=...` space-list

Initial sketch: `make uninstall KEEP="backups kitty"`. Cleaner: three
boolean env vars `KEEP_BACKUPS=1`, `KEEP_CONFIG=1`, `KEEP_KITTY=1`. Make
maps each to its CLI flag with a `$(if $(filter ...))`. Reasons:

1. Each knob is independently discoverable in `make help`.
2. No string-parsing in the Makefile (`make` doesn't need to split a
   space-list).
3. Multi-knob composition is mechanical (each variable gets its own
   `$(if ...)` line; concatenation is automatic).
4. Shell completion in zsh / bash works with env-var-name completion
   already; no custom completer needed.

**Alternative considered:** `KEEP=backups,kitty` comma-list. Rejected —
adds a parser step in the Makefile for no incremental capability.

### D4 — Confirm prompt enumerates "will remove" only

The prompt computes the list of items that WILL be removed based on the
flags, and prints them. No "will be kept" line. Sample default-path
prompt:

```
About to remove (with no --keep-* flags):
  - kitty config block from ~/.config/kitty/kitty.conf
  - payload directory ~/.config/kitty/kitty-setup/
  - all kitty.conf.bak.* backup files
  - ~/.local/kitty.app/
  - ~/.local/bin/kitty symlink
  - ~/.local/share/applications/kitty.desktop

After this completes, run `uv tool uninstall my-kitty` to remove the
binary itself. Continue? [y/N]
```

Sample `KEEP_BACKUPS=1` prompt:

```
About to remove (preserving: backups):
  - kitty config block from ~/.config/kitty/kitty.conf
  - payload directory ~/.config/kitty/kitty-setup/
  - ~/.local/kitty.app/
  - ~/.local/bin/kitty symlink
  - ~/.local/share/applications/kitty.desktop

After this completes, run `uv tool uninstall my-kitty` to remove the
binary itself. Continue? [y/N]
```

The bash dispatcher computes the prompt; the Python CLI doesn't print
the prompt itself (already today's pattern). One round-trip from
Makefile → bash → Python.

**Alternative considered:** Python computes + prints the prompt; bash
just confirms. Rejected — bash already owns the confirm; moving prompt
to Python means we need argparse to know KITTI_FORCE etc. Stay with
current architecture.

### D5 — Reuse `pruner.prune_all` + `pruner.delete_each` for backup nuke

`add-backup-pruning` shipped these helpers already. They take
`list[Path]` of backups (from `config_updater.list_backups`) and unlink
each, swallowing FileNotFoundError. Exactly the semantics
`cli_uninstall` needs for the "delete every backup" step. No new
function; just call the existing pair. Add a one-line note in the
backup-deletion path that points at the prune helpers (helps the next
reader understand we're reusing).

### D6 — Drop `--kitty` and `--self` and `ALL=1` cleanly, no aliases

Single-user repo, no installed-base of automation that depends on the
old flags. Aliases would carry forward the discoverability bug
(`--kitty` would still be a working flag, just hidden). Better: clean
break, document migration in README, the next time the user sees
`--kitty: not recognized` they'll consult `--help` and learn the new
shape.

**Alternative considered:** keep `--kitty` as a deprecated alias for
"do nothing extra" (since aggressive is now default). Rejected —
silently no-op aliases are worse than hard errors at the boundary.

## Risks / Trade-offs

* **Risk: a user who memorised `make uninstall` (config-only) runs the
  new default and loses their backups.** → *Mitigation:* the confirm
  prompt enumerates exactly what WILL be removed. KITTI_FORCE=1 still
  bypasses the prompt for scripted use, but a human in a terminal
  reads the list before pressing y. Documented in README's "Updates"
  section as part of the upgrade ritual.
* **Risk: scripted callers using `make uninstall ALL=1` break.** →
  *Mitigation:* `ALL=1` becomes a no-op (Makefile no longer reads it).
  The script still works because the new default IS what `ALL=1` used
  to be. No silent-data-loss risk.
* **Risk: scripted callers using `my-kitty uninstall --kitty --self`
  fail with `unrecognized arguments`.** → *Mitigation:* the failure is
  immediate and loud; the user sees the new flag list in the help text.
  Acceptable — single-user repo.
* **Risk: the prompt's "will remove" enumeration drifts from what the
  Python actually does.** → *Mitigation:* the Python computes the
  enumeration from the same flag-to-action mapping the deletion code
  uses. Single source of truth. Add a unit test that asserts prompt
  text matches the actions for each flag combination.
* **Trade-off: the `--keep-config` flag preserves backups too.**
  Reasoning: backups belong to the config-side surface (they're written
  by config_updater under `~/.config/kitty/`); preserving the
  config-side without preserving its backups would be surprising.
  Documented in the spec scenario.

## Migration Plan

1. Land the four code commits + the docs commit + archive.
2. The user re-runs `make install` if needed (the new uninstall flow
   doesn't require a re-install — install is unchanged).
3. The user types `make uninstall` to nuke the world. Confirm prompt
   describes the scope; user types `y` or aborts.
4. To recover the old "config-only" default, the user runs
   `make uninstall KEEP_KITTY=1 KEEP_BACKUPS=1` — preserves kitty.app +
   backups, removes only the config block + payload. Documented.

Rollback: revert the change set. Old `--kitty` / `--self` flags + `ALL=1`
knob come back; new `--keep-*` flags + `KEEP_*=1` knobs go away.
Filesystem state from any uninstall already run with the new default
stays as-is (irreversible — but that's true of any uninstall).

## Open Questions

* **Q1 — Should we add a `--dry-run` flag despite the design saying we
  shouldn't?** Pressure point: the confirm prompt enumerates everything,
  but the user has to type `y` to verify nothing was touched. A dry-run
  could decouple "show me the plan" from "execute". *Default decision:*
  no, KITTI_FORCE=0 + reading the prompt is enough. Re-evaluate if a
  scripted use case surfaces.
* **Q2 — Should the self-removal banner skip when `--keep-kitty`
  preserves the kitty install?** Argument for skipping: if the user is
  preserving kitty, they're likely also preserving the binary. Argument
  against: the user might still want to remove `my-kitty` itself even
  when keeping kitty.app. *Default decision:* always print. Cheap;
  decoupled from kitty.app preservation; one less branch to maintain.
* **Q3 — `--keep-config` preserves the payload + backups + config block.
  Is that the right grouping?** The "config side" is one mental category
  to most users; splitting backups from config when both live under
  `~/.config/kitty/` would surprise. *Default decision:* group them.
  Add `--keep-backups` + drop `--keep-config` if a user surfaces wanting
  finer control.

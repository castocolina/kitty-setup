## Context

`config_updater` writes timestamped backups (`kitty.conf.bak.<UTC-ts>`) on
every install that detects drift, per the
`kitty-config-management/Backup before any mutation` requirement. Existing
text on that requirement: *"Old backups MUST NOT be deleted by the install."*
The same capability's uninstall requirement says: *"Backup files themselves
MUST NOT be deleted by uninstall."* Both rules stay intact. This change opens
a third, explicitly opt-in path — a `prune` user action — for users who want
to thin the directory.

Two filesystem realities shape the design:

1. The timestamp lives in the filename (`kitty.conf.bak.YYYYMMDDTHHMMSSZ`).
   Sorting filenames lexicographically equals sorting by creation order. No
   filesystem-mtime dependency required for `--keep N`.
2. `--older-than DAYS` is a separate axis. It needs filesystem mtime, not the
   filename timestamp, because the filename timestamp is *creation* and a
   user may legitimately want to keep recently-touched files.

## Goals / Non-Goals

**Goals:**

- One subcommand, three policies, all opt-in. Default with no flags = dry-run
  list.
- Dry-run output: filenames, mtime, byte size, total. No surprise deletions.
- Atomic-enough deletion. Each `unlink()` is independent; a partial run still
  leaves a coherent directory (the surviving backups remain valid).
- Pure stdlib. No new runtime dependency.
- Keep the existing capability spec intact; ADD a single requirement.

**Non-Goals:**

- Pruning anything other than `kitty.conf.bak.*`. No `tmp/`, no logs, no
  payload directory.
- Auto-prune on install/uninstall. Defer until a user actually asks.
- Restoring a backup as the active `kitty.conf`. The user runs `cp` themselves.
- Cron / systemd-timer scheduling.
- Cross-host sync of backup state.

## Decisions

### D1 — Subcommand `prune`, not flag-on-uninstall

`my-kitty-setup uninstall --prune-backups` would conflate two semantics
(remove our footprint vs. trim history). A dedicated `prune` verb leaves
uninstall single-purpose and makes future `prune --tmp` / `prune --logs`
extensions natural. Cost: one extra subparser registration in `cli.py`.

**Alternative considered:** flag on uninstall. Rejected — semantic overload.

**Alternative considered:** Make-target only. Rejected — requires the source
repo to be present, which contradicts the "delete the repo after install"
property of `consolidate-into-my-kitty-setup-cli`.

### D2 — Dry-run by default

`my-kitty-setup prune` (no flags) prints a backup count + total size and
exits 0 without deleting anything. The `--backups` flag is the gate: nothing
on disk changes without it. This mirrors `rm -i` / `git clean -n` defaults.

### D3 — `--keep N` default; mutually exclusive with `--older-than` / `--all`

When `--backups` is passed without a policy flag, default to `--keep 3`. The
default tracks the rollback story: `config_updater` only ever needs the
single LATEST backup, so 3 is a generous safety buffer that covers two
"oh-no" undo cycles. Mutual exclusion is enforced by argparse using a
mutually exclusive group; passing two policy flags fails with a non-zero exit
and an error.

**Alternative considered:** allow combining (`--keep 3 --older-than 30` =
"keep at least 3, then trim by age"). Rejected — adds reasoning surface for
no current user need. Add later if asked.

### D4 — Filename-timestamp sort for `--keep`, mtime for `--older-than`

`--keep N`: sort all `kitty.conf.bak.*` matches lexicographically (filename
timestamp), keep the last N, delete the rest. No filesystem stat needed.
Robust against clock skew at the filesystem level — the writer of the
timestamp owns the truth.

`--older-than DAYS`: stat each candidate, compare `time.time() - st_mtime`
against `DAYS * 86400`. Use mtime (not filename timestamp) because mtime
reflects "when did I last care about this file" — a user who manually
re-touched a backup signals intent to keep it. Filename ts is creation only.

### D5 — Module placement: new `pruner.py`

`installer.py` already owns install + uninstall + kitty-removal handlers.
Adding a third concern (history management) bloats it. New `pruner.py`
exposes `cli_prune(args) -> int` as the subcommand handler plus pure helpers
(`list_backups(dir)`, `prune_by_keep(dir, n)`, `prune_by_age(dir, days)`,
`prune_all(dir)`). `cli.py` imports it like the others.

`config_updater.py` gets one new public helper (`list_backups`) so unit
tests can stay close to the existing `_latest_backup` and so future
behaviors (e.g. `doctor` reporting backup count) reuse it without touching
`pruner.py`.

### D6 — Output format: human-readable, no JSON yet

For each backup printed (dry run, or "would delete" preview, or
post-deletion summary): `<filename>  <iso-mtime>  <size>`. No JSON output
flag this round; defer until a scripting consumer surfaces. Counts +
totals are summed at the end, comma-separated thousands.

## Risks / Trade-offs

* **Risk: user runs `--all` and immediately needs a rollback.** The next
  install's parse-check failure has no backup to restore from. → *Mitigation:*
  the install's parse-check rollback uses the SAME-PROCESS backup, written
  fresh at the start of the install. As long as the user does NOT prune
  mid-install, `--all` is safe. Document this in the prune help text and in
  the README quickstart.
* **Risk: filename timestamp diverges from real ordering.** A user who
  manually `touch`es an old backup file changes mtime but not the filename
  timestamp. → *Mitigation:* `--keep` uses filename ts (creation order is
  what we want for "keep N most recent CREATIONS"). `--older-than` uses
  mtime (matches user's "I touched it recently" signal). Documented in
  the spec.
* **Risk: glob `kitty.conf.bak.*` accidentally matches a file the user
  authored manually.** → *Mitigation:* validate each match's name against a
  strict regex (`r'^kitty\.conf\.bak\.\d{8}T\d{6}Z$'`) before considering it
  for deletion. Anything else is left alone.
* **Risk: prune races with a concurrent install writing a new backup.** →
  *Mitigation:* prune lists files first, then deletes. A new file written
  after the listing is ignored. Worst case: the new file survives this
  prune run. Acceptable; user can re-run.
* **Risk: spec-text for `kitty-config-management` says "Old backups MUST NOT
  be deleted by the install / uninstall".** → *Mitigation:* prune is neither
  install nor uninstall. Existing requirements stand. The new requirement
  scopes prune as a third, explicit user action.

## Migration Plan

No data migration. The new `prune` subcommand is additive. Deploy is the
same `make install` flow — `uv tool install --force .` rebuilds the tool
venv with the new subcommand registered.

Rollback: revert the change set. `prune` disappears from the help banner.
No state remains on the user's filesystem from the feature itself (the
backup files it would have deleted are user-owned).

## Open Questions

* **Q1 — Should `make prune` be silent on a clean directory (zero backups)
  or print "no backups"?** Default proposal: print `"no backups under
  ~/.config/kitty/"` and exit 0. Re-evaluate if quietness is requested.
* **Q2 — Should `--older-than` accept fractional days (`--older-than 0.5`
  = 12 h)?** Default proposal: integer days only this round. Add float
  parsing if a user surfaces with a real "prune hourly" need.
* **Q3 — Should we eventually offer `--dry-run` as an explicit flag to
  pair with a policy?** Today: no. Without `--backups`, the command is
  inherently dry. With `--backups`, the user opted in. Re-evaluate after
  observing usage.

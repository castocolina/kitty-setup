## Context

`my-kitty-setup` came from a single-line user instruction during the
`consolidate-into-my-kitty-setup-cli` change: *"Olvida fluffy, dejemos
por ahora en duro `my-kitty-setup`"*. That made it a stop-gap. Two
months and two archived changes later, every help banner, README block,
sentinel marker, and rc-file edit carries the longer name. The cost of
fixing it grows with every new subcommand we add (`prune` already; `keys`
next). Better to rename now, before more user-facing surface ossifies
around the verbose form.

The OpenSpec capability folder is a second piece of drift. The
`consolidate-into-my-kitty-setup-cli` change created
`openspec/specs/my-kitty-setup-cli/`. Leaving it under the legacy name
while the binary moves to `my-kitty` invites future-reader confusion
("is `my-kitty-setup-cli` the spec for an old binary?"). Rename both at
once.

The single migration trap is the user's shell rc file: a previous
install wrote a sentinel-bracketed PATH block with `# >>> my-kitty-setup
PATH >>>`. Without migration, the new install would walk the rc, find
no `# >>> my-kitty PATH >>>` block, and APPEND a second one. The user
ends up with two stacked PATH exports. The fix lives in
`path_integration.ensure_local_bin_in_path`: recognise either marker
form as "already configured" AND, when the legacy form is present,
rewrite the marker lines in place to the new form on the same call.

## Goals / Non-Goals

**Goals:**

- Single binary on PATH after the rename: `~/.local/bin/my-kitty`. The
  legacy `~/.local/bin/my-kitty-setup` is detected and the install
  prints the manual `uv tool uninstall my-kitty-setup` line; no
  auto-removal.
- Existing rc-file PATH block migrates from the old marker to the new
  marker form on the next `make install`. Idempotent: re-runs after
  migration are no-ops.
- Capability folder rename: `openspec/specs/my-kitty-setup-cli/` →
  `openspec/specs/my-kitty-cli/`. Performed via two delta specs in
  this change (REMOVE + ADD) so `openspec archive` does the work
  mechanically.
- All test assertions on `PROG` / argv[0] / help-banner expectations
  updated; no test reads `my-kitty-setup` from a string literal after
  this change.
- README + CLAUDE.md show `my-kitty` everywhere; no remaining literal
  `my-kitty-setup` outside archived openspec changes.

**Non-Goals:**

- Auto-removing the legacy `~/.local/bin/my-kitty-setup` shim. Print
  only, per consolidate D2.
- Renaming the `kitty_setup` Python package on disk or on PyPI. The
  import path stays `kitty_setup.cli`, etc.
- Renaming or relocating the openspec change directories already
  archived (e.g. `archive/2026-05-05-consolidate-into-my-kitty-setup-cli`).
  Archived changes are read-only history.
- The `keys` subcommand. Owned by the parked
  `phase1-binding-introspection` change, retargeted afterwards.

## Decisions

### D1 — Capability rename via REMOVE + ADD deltas

`openspec` does not expose a "rename capability" delta operation. The
mechanical equivalent is two delta specs in this change directory:

- `specs/my-kitty-setup-cli/spec.md` with `## REMOVED Requirements`
  listing all 5 existing requirements, each with a `**Reason:**`
  pointing at the rename and a `**Migration:**` pointing at the new
  capability.
- `specs/my-kitty-cli/spec.md` with `## ADDED Requirements` re-stating
  the same 5 requirements (text refreshed for the new binary name)
  plus the new "PATH block migration" requirement.

On `openspec archive`, the legacy capability folder is removed and the
new one is created. No spec content is lost — the REMOVE deltas carry
the full original requirement bodies and would archive into history.

**Alternative considered:** keep the capability name as
`my-kitty-setup-cli` and only update the body text to refer to
`my-kitty`. Rejected — perpetuates the drift the rename is trying to
fix. Spec/identifier hygiene matters for grep-ability.

### D2 — Migration is "recognise legacy + rewrite", not "delete legacy + append new"

`ensure_local_bin_in_path` already has an "already configured" detection
path. Extend it to recognise the legacy `# >>> my-kitty-setup PATH >>>`
markers in the same scan. Two sub-cases:

1. **Legacy markers present, new markers absent:** rewrite the legacy
   marker lines in place to the new form. Same line, same `export`
   between them. Returns `changed=True, reason="migrated legacy
   marker"`.
2. **Both legacy and new markers present:** the new form wins. Strip
   the legacy block (markers + the line between them). Returns
   `changed=True, reason="removed duplicate legacy marker"`.
3. **Only new markers present, or both absent and `~/.local/bin` already
   on PATH:** existing behavior unchanged.

This keeps the migration mechanical and reversible — the user's shell
rc is mutated only between sentinel markers, same invariant as before.

**Alternative considered:** delete legacy block + append new block.
Rejected — produces an unnecessary shell-rc diff (the actual
`export PATH=...` line is identical in both block forms). Rewriting in
place leaves the user's rc minimally touched.

### D3 — Legacy shim detection in `cli_install`, not in setup.sh

The migration NOTICE for the old `~/.local/bin/my-kitty-setup` shim
lives in `cli_install` (Python), not in `tools/setup.sh` (bash). Two
reasons:

1. `cli_install` runs after `tools/setup.sh` has just installed the
   new binary, so the detection window is correct.
2. Future similar migrations (renaming subcommands, renaming options)
   live naturally in Python alongside the install logic. Bash should
   stay thin.

Format of the notice:

```
legacy:        ~/.local/bin/my-kitty-setup detected; remove it with:
                   uv tool uninstall my-kitty-setup
```

Non-fatal. The notice is informational and does not block the install
from succeeding.

### D4 — `tools/uninstall.sh` falls back to legacy binary

Users mid-upgrade may have only the legacy `~/.local/bin/my-kitty-setup`
on disk when they run `make uninstall`. The dispatcher's
`resolve_binary` function first looks up `my-kitty` (preferred), then
falls back to `my-kitty-setup`. Logs which one it picked. After this
change archives the fallback can stay indefinitely — it costs nothing
when the legacy binary is absent.

### D5 — Test updates: replace literals, do not parameterize

`test_cli.py` and `test_path_integration.py` carry literal references
to the old binary name in help-banner expectations and marker constants.
Direct string replacement, not a fixture or parameter. The literal IS
the spec — parameterizing would let a future refactor accidentally pass
a wrong PROG without test failure.

New cases in `test_path_integration.py`:

* rc with old block alone → migrated; markers rewritten; export line
  byte-identical; result `changed=True, reason="migrated legacy marker"`.
* rc with old block + unrelated content → only marker lines change;
  unrelated content untouched.
* rc with new block alone → no-op (existing behavior, regression
  guard).
* rc with both blocks (degenerate) → legacy stripped, new kept; result
  `changed=True, reason="removed duplicate legacy marker"`.
* idempotent re-run after migration → no further change.

## Risks / Trade-offs

* **Risk: breaking change for users with the existing
  `my-kitty-setup` shim.** They must run
  `uv tool uninstall my-kitty-setup` after upgrading. → *Mitigation:*
  the install prints the exact command (D3). The legacy binary keeps
  working until removed. Single-user repo today, so the blast radius
  is small.
* **Risk: capability folder rename leaves a stale archive reference.**
  Archived changes (e.g. `archive/2026-05-05-consolidate-into-my-kitty-setup-cli`)
  reference `my-kitty-setup-cli` in their spec deltas. → *Mitigation:*
  archived changes are read-only history. The reference is correct
  AS-OF that change's archive date. Future readers get the rename
  context from this change's archive entry.
* **Risk: rc-file migration corrupts a user's hand-edited rc.** →
  *Mitigation:* the migration is a marker-line rewrite, not a content
  rewrite. The `export PATH=...` line between markers is byte-identical.
  If the user hand-edited the export line, the rewrite preserves it.
  If the user hand-edited the marker lines (unlikely — they're
  documented as "do not edit"), the rewrite restores them to canonical
  form.
* **Risk: pyproject.toml `[project.scripts]` entry rename leaves the
  legacy entry in `~/.local/share/uv/tools/`.** → *Mitigation:* `uv
  tool install --force .` installs the new entry; the OLD tool venv
  for `my-kitty-setup` is independent. Users explicitly remove it via
  the printed `uv tool uninstall my-kitty-setup` command.

## Migration Plan

**Existing user (single-user today, just me)**:

1. `git pull`.
2. `make install` → builds `my-kitty`, prints "legacy
   ~/.local/bin/my-kitty-setup detected; remove with: uv tool uninstall
   my-kitty-setup".
3. Run the printed command.
4. `~/.zshrc` PATH block was migrated automatically; new shell sessions
   pick up `my-kitty` from PATH (already on PATH via the migrated
   block).

**Fresh install** (no legacy state): nothing to migrate. `make install`
behaves like a fresh consolidate-era install with the new name.

**Rollback**: revert this change set. Re-run `make install` against the
reverted source rebuilds the `my-kitty-setup` binary. The user's PATH
block does NOT auto-migrate backward; the old install would APPEND a
new `# >>> my-kitty-setup PATH >>>` block. Acceptable risk — rollback
is unlikely and the duplicate block is harmless (both export the same
path).

## Open Questions

* **Q1 — Should `tools/uninstall.sh`'s legacy fallback log a warning?**
  Default: log "[uninstall] using legacy binary `my-kitty-setup`; run
  `uv tool uninstall my-kitty-setup` after this completes." Re-evaluate
  if the noise becomes annoying.
* **Q2 — Should `cli_install` auto-remove the legacy shim eventually?**
  Default: print only, per D3. Re-evaluate after observing whether
  users actually copy-paste the printed line. Mirrors the same
  open question from the `consolidate-into-my-kitty-setup-cli` design
  (Q1 there).
* **Q3 — Should we keep an alias `my-kitty-setup` that just dispatches
  to `my-kitty`?** Default: no. `[project.scripts]` aliasing adds
  surface area for confusing-error reports ("which binary did I
  invoke?"). The legacy shim either gets removed (preferred) or stays
  installed but stale (harmless until the user uninstalls it).

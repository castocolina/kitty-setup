# Phase 5: Component Separation & Version Floor - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-09-22
**Phase:** 5-Component Separation & Version Floor
**Areas discussed:** Payload ownership split, uninstall semantics, version floor, import-boundary
enforcement
**Mode:** discuss + `--analyze` overlay (trade-off table before each question; requested as `—analyze`)

---

## Findings presented before the questions

Four facts from scouting that constrained every answer:

1. **The payload is monolithic** — one dir, one sentinel block, one include list, and
   `config_updater.uninstall` does `rmtree(payload_dir)`. A foundation-only uninstall cannot leave
   scenes working without splitting something.
2. **Only two payload files are scenes preconditions** — `remote-control.conf` and
   `dynamic-opacity.conf`. `layout.conf` only mentions kitten in a comment.
3. **`seed_scenes()` runs unconditionally** at `installer.py:229`, including under `--no-config` —
   R3.1's second clause is a live bug, not a design question.
4. **Nothing removes user scene files today**, locked in by
   `test_uninstall_config_only_leaves_scenes_untouched` — so a scenes uninstall is new destructive
   behaviour on user-authored content.

All three R3.3 cross-imports were confirmed to exist, with a small surface: path constants,
`ConfigPaths`, `scenes_dir`, and two socket-discovery helpers.

---

## Payload ownership split (R3.1)

| Option | Description | Selected |
|--------|-------------|----------|
| Component subdirectories | `foundation/` and `scenes/` subdirs, each with its own entry file | ✓ |
| Per-file ownership manifest | Files stay put; a code table marks ownership; uninstall rewrites the include list | |
| Two sentinel blocks | One managed block per component in `kitty.conf` | |

**User's choice:** Component subdirectories — against the recommendation, which was the manifest.
**Notes:** The recommendation favoured the manifest on diff size (only 2 of 14 files are
scene-owned) and on not disturbing the `keys` category mapping. The user preferred a boundary
visible on disk. Accepting it surfaced a blocker, verified immediately and recorded as D-03:
`_walk_payload` globs non-recursively (`binding_introspection.py:183`), so under subdirs it returns
`{}` and every payload binding is attributed to "kitty default" — `keys` would report 0 ours / 101
defaults and 0 conflicts vacuously. One-word fix (`rglob`), but it must ship in the same plan as
the move, with the Phase 3 oracle re-run. Two further consequences recorded: Phase 4's generalised
per-OS selector operates on payload-root paths and must be re-pointed (making the Phase 4 → 5
dependency real rather than mere ordering), and the one-level entry-file nesting depends on kitty
resolving relative includes against the including file's directory — flagged as this phase's
required experiment rather than assumed.

---

## `remote-control.conf` ownership (R3.2)

| Option | Description | Selected |
|--------|-------------|----------|
| Scenes own it | Survives a foundation uninstall; scenes keep working, no new error paths | ✓ |
| Foundation owns it | Scenes break and must fail with an actionable error naming what to reinstall | |
| Duplicated in both | Survives either uninstall | |

**User's choice:** Scenes own it.
**Notes:** Makes the roadmap criterion true by construction. Evidence came from the files' own
headers, which already declare the dependency. Honest consequence recorded: a foundation-only
install has no remote control, so `doctor`'s remote-control check needs to distinguish
"not installed yet" from "scenes component not selected" — otherwise it tells a foundation-only
user to run a command that will not help them. Duplication was rejected on the one-place rule and
because `keys` would see duplicate directives.

---

## `--component` vs the existing `--keep-*` flags

Hard constraint presented first: Phase 2 D-04 wired `make clean` to `--keep-kitty --keep-backups`,
so the keep-flags cannot be deprecated without reopening a decided phase.

| Option | Description | Selected |
|--------|-------------|----------|
| Orthogonal, no-op reported | `--component` selects, `--keep-*` narrows; an inapplicable keep-flag is a stated no-op | ✓ |
| Orthogonal, reject bad combos | Same axes, but an inapplicable keep-flag is an argparse error | |
| `--keep-*` only with `all` | Keep flags valid only for a full uninstall | |
| `--component` supersedes `--keep-*` | One flag family | |

**User's choice:** Orthogonal, no-op reported.
**Notes:** The "state it" form follows Phase 2 D-13, which replaced doctor's fake "skipped" string
with a real SKIP state rather than letting output imply something untrue. The rejected strict
variant would turn predictable scripted commands into errors.

---

## User data on a scenes uninstall

| Option | Description | Selected |
|--------|-------------|----------|
| Never delete user data | Remove the payload subdir and only seeded examples still byte-identical to what we shipped; print the paths kept | ✓ |
| Delete the whole scenes dir | Symmetric with foundation; needs a confirmation prompt | |
| Leave every scene file | Only the payload subdir goes | |

**User's choice:** Never delete user data.
**Notes:** Makes uninstall the exact inverse of `seed_scenes()`'s copy-if-absent contract, so the
two halves stop disagreeing. Rated **one-way** in CONTEXT.md: unlike `kitty.conf`, the scenes
directory has no backup mechanism, so a deleted user recipe is unrecoverable. This is the second
phase where "user data is not ours to delete" decided the answer (Phase 2 D-04 was the first),
which is why it is recorded as a project value rather than a local preference.

---

## Version floor (R3.4)

| Option | Description | Selected |
|--------|-------------|----------|
| 0.49 | The only version anything was verified against | ✓ |
| 0.47 | Lowest version where the payload's action text is correct | |
| 0.46 | The number the frozen specs named | |

**User's choice:** 0.49.
**Notes:** Decided by applying the mantra to a *claim* rather than to code — a supported-version
range is a behavioural claim and the evidence covers 0.49 only. Two concrete disqualifiers for
0.46 were presented: `scroll_line_*` became `smooth` in ≥0.47 (Phase 3 D-08), so the payload's
expected action text is wrong there; and the oracle's `debug_config`/`KeyDefinition.rest` surface
is unverified below 0.49. The floor is lowerable later by testing an older version — cheap — but
could not honestly be set low first and verified never.

### Detection mechanism

| Option | Description | Selected |
|--------|-------------|----------|
| Parse the `--version` string | Reuse the subprocess `_check_kitty_binary` already runs | ✓ |
| `kitty +runpy` version tuple | Structured, no regex, but a second ~150 ms subprocess | |

**User's choice:** Parse the `--version` string.
**Notes:** The data is already in hand at `doctor.py:43-55`. Recorded either way: an unparseable
version string is a FAIL that says so, never a silent pass.

---

## Import-boundary enforcement (R3.3)

A correction to the options as first framed: **ruff cannot express this rule.** Its
`flake8-tidy-imports` `banned-api` is global, and `per-file-ignores` filters by rule code
(`TID251`) rather than by banned name, so un-banning a module for one file un-bans every banned
name for it. Also clarified that "pre-commit" here means a hook under `tools/hooks/` via
`core.hooksPath` (Phase 1 D-07/D-08) — the pre-commit framework is not installed and adding it is
out of scope.

| Option | Description | Selected |
|--------|-------------|----------|
| pytest test over `ast` | Walks `src/`, catches deferred in-function imports, asserts the neutral module imports neither side | ✓ |
| `import-linter` contracts | Purpose-built declarative layer contracts | |
| Hook-only grep check | Trivial regex check in the git hook | |

**User's choice:** pytest test over `ast`.
**Notes:** The only option that catches the deferred-import form this codebase actually uses —
`installer.py:98` defers `from kitty_setup.scenes.recipe import scenes_dir` precisely to dodge a
load-time cycle, which is the cycle this phase removes. A grep check would miss it entirely.
`import-linter` was rejected as a new dev dependency plus a second config file for one rule.

---

## Claude's Discretion

- Names and split of the neutral module(s); whether the two socket helpers shed their leading
  underscore on becoming public API.
- Whether the version floor extends `_check_kitty_binary` or becomes its own `CheckResult` row.
- Representation of the component enum, and whether `--component` accepts repetition.
- Plan decomposition under `granularity: fine`.

## Decided without a question

- **D-03 (`rglob` in the same plan as the move)** — follows from the R2.8 standing gate; a silent
  attribution failure is not something to schedule separately.
- **D-05 (allow-list and entry file stay at the payload root)** — component-neutral metadata, and
  leaving it put means no code change in `_read_allow_list`.
- **D-08 (`--no-config` stops seeding scenes)** — a live bug at `installer.py:229`, outside the
  `inject_config` branch. No design choice to make.
- **Stale header paths** — every payload header moves in this phase anyway, so the
  `openspec/changes/...` citations Phase 1 relocated get repointed in the same edit.

## Deferred Ideas

- **macOS verification** of components, the floor, and the relative-include behaviour — Phase 10.
- **Doc updates for the 0.49 floor** (README and anything citing 0.46) — Phase 8 owns doc accuracy.
- **Scene-directory backups** — the gap that makes D-07 one-way; a real idea, out of scope here.
- **Per-component `doctor` output** — attractive once components exist; not in this phase's criteria.
- **`--component` for Makefile targets** — the Makefile stays thin glue per the stack rule.

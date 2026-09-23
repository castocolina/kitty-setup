# Phase 5: Component Separation & Version Floor - Context

**Gathered:** 2026-09-22
**Status:** Ready for planning

<domain>
## Phase Boundary

Make foundation and scenes two genuinely separable components — installable and uninstallable
independently — remove the three cross-imports that currently tangle them, and give `doctor` a
real minimum-kitty-version floor instead of a version string it merely prints.

Delivers R3.1–R3.4. Does **not** add scene features, chords, or presets (Phases 6 and 7), and does
not verify any of it on macOS (Phase 10, which owns fixing what it finds there).

</domain>

<decisions>
## Implementation Decisions

### Payload ownership split (R3.1, R3.2)
- **D-01:** The payload splits into **component subdirectories**: `kitty-setup/foundation/` and
  `kitty-setup/scenes/`, each with its own entry file, and `kitty-setup.conf` at the payload root
  includes whichever components are installed. A component uninstall is then one `rmtree` of its
  subdir plus removal of its include line. Rejected: a per-file ownership manifest in code (smaller
  diff, but ownership invisible in the payload dir) and two sentinel blocks in `kitty.conf`
  (doubles the most load-bearing parsing code in the repo — `_find_block`, drift detection,
  backup/rollback — for the least gain). — **Reversibility:** costly — moving 14 payload files
  changes every file header, the include list, the installed layout on every user's disk, and the
  path every code site that touches the payload computes.
- **D-02:** `remote-control.conf` and `dynamic-opacity.conf` are **scenes-owned** (they live under
  `scenes/`). This makes R3.2's criterion true by construction: a foundation-only uninstall leaves
  `allow_remote_control` / `listen_on` in place, so scenes keep working with **no new error paths**
  in `_client._resolve_socket`. Evidence: both files' own headers already declare the dependency —
  `remote-control.conf` says it exists so scene capabilities can reach kitty, and
  `dynamic-opacity.conf` names `phase2-scene-styling` as its owner. Consequence recorded honestly:
  a foundation-only install has **no remote control at all**, and `doctor`'s remote-control check
  must report that as a SKIP-with-reason (scenes not installed), not a FAIL. Rejected:
  foundation-owned (breaks scenes, requiring new actionable-error code and tests) and duplicating
  the directives in both subdirs (violates the one-place rule and `keys` would see duplicates).
- **D-03:** **`_walk_payload` must be made recursive in the same plan as the move.** It currently
  globs `payload_dir.glob("*.conf")` (`binding_introspection.py:183`) — non-recursive. Under
  subdirectories it returns `{}`, so **every** payload binding is attributed to "kitty default":
  `my-kitty keys` would report 0 ours / 101 defaults and 0 conflicts *vacuously*. That is exactly
  the R2.8 truthfulness class this project exists to eliminate, and it fails silently. The fix is
  `rglob`; `basename = conf.stem` keeps working because basenames stay unique across subdirs. The
  Phase 3 oracle must be re-run to prove it, per the R2.8 standing gate.
- **D-04:** The nesting is **one level, with per-component entry files**: `kitty-setup.conf`
  includes `foundation/foundation.conf` and `scenes/scenes.conf`; each entry file includes its own
  category files by bare basename. This is what makes a component uninstall mechanical (one line,
  one directory). It **depends on kitty resolving a relative `include` against the including file's
  directory** — treat that as a hypothesis to verify by experiment on a real kitty session before
  building on it (R0.1), not as a documented fact to assume.
- **D-05:** `intentional-overrides.conf` and `kitty-setup.conf` stay at the **payload root**,
  component-neutral. The allow-list is metadata for both components and is never `include`d by
  kitty, and `_read_allow_list` already reads `payload_dir / ALLOW_LIST_BASENAME` — leaving it in
  place means no code change and it survives either single-component uninstall.

### Uninstall semantics (R3.1)
- **D-06:** `--component` and the existing `--keep-*` flags are **orthogonal axes**: `--component`
  selects which component(s) to remove, `--keep-*` narrows what is removed within that selection.
  A `--keep-*` that cannot apply to the selected component (e.g. `--component scenes --keep-kitty`)
  is a **no-op that the output states explicitly** — never silently ignored, never an error.
  Rationale: the "report it" form matches Phase 2 D-13, which replaced doctor's fake "skipped"
  string with a real SKIP state rather than letting output imply something untrue. Hard constraint
  that rules out deprecating the keep-flags: Phase 2 D-04 wired `make clean` to
  `--keep-kitty --keep-backups`, so removing them would reopen a decided phase.
- **D-07:** A scenes-component uninstall **never deletes user data**. It removes the `scenes/`
  payload subdir, and removes a seeded example recipe only when the file is still **byte-identical
  to what we shipped**; anything the user edited stays on disk and its path is printed. This makes
  uninstall the exact inverse of `seed_scenes()`'s copy-if-absent contract (`installer.py:88-113`),
  which already refuses to overwrite an edited file. Note the starting point: nothing removes user
  scene files today, and `tests/unit/test_installer_seed_scenes.py::test_uninstall_config_only_leaves_scenes_untouched`
  locks that in — so this is new behaviour whose blast radius is user-authored content, and it
  needs its own test alongside the existing one. — **Reversibility:** one-way — a deleted
  user-authored recipe is not recoverable from anything this project writes; there is no backup of
  the scenes directory the way there is for `kitty.conf`.
- **D-08:** `install --no-config` must **not** seed scenes unless the scenes component is selected.
  Today `seed_scenes()` runs unconditionally at `installer.py:229`, outside the `inject_config`
  branch — a live bug, not a design question. Seeding moves under the scenes-component condition.

### Version floor (R3.4)
- **D-09:** The minimum supported kitty version is **0.49** — the only version anything in this
  project was ever verified against. Reasoning is the mantra applied to a claim rather than to
  code: a supported-version range is a behavioural claim, and the evidence covers 0.49 only. The
  frozen specs named 0.46, but the payload's expected action text is provably wrong there
  (`scroll_line_*` became `smooth` in ≥0.47, Phase 3 D-08) and the oracle's mechanism
  (`kitty.debug_config.ShortcutMap`, `KeyDefinition.rest`) is unverified below 0.49. The floor can
  be lowered later by *testing* an older version — a cheap experiment — but it cannot honestly be
  set low first and verified never. Rejected: 0.47 (action text correct, API surface still
  unverified) and 0.46 (untested and demonstrably wrong).
- **D-10:** Detection **parses the `kitty --version` string** that `_check_kitty_binary` already
  captures (`doctor.py:43-55`) into a comparable tuple, rather than adding a second `+runpy` round
  trip (~150 ms) for a number the existing subprocess already returns. Below the floor, `doctor`
  FAILs with an upgrade hint; at or above it, PASSes. An unparseable version string is a FAIL that
  says so, not a silent pass.

### Import boundary (R3.3)
- **D-11:** Enforcement is a **pytest test that walks the AST of `src/`** and asserts no forbidden
  import edge exists — including **deferred, in-function imports**, which is the form this
  codebase actually uses (`installer.py:98` defers `from kitty_setup.scenes.recipe import
  scenes_dir` specifically to dodge a load-time cycle). It also asserts the positive direction:
  the new neutral module imports neither `installer`/`config_updater` nor `scenes`. One artifact
  satisfies both halves of the roadmap criterion — it fails `make test`, and the `tools/hooks/`
  pre-commit hook from Phase 1 D-07/D-08 runs it.
  Rejected with a reason worth recording: **ruff cannot express this rule.** Its
  `flake8-tidy-imports` `banned-api` is global, and `per-file-ignores` filters by rule code
  (`TID251`) rather than by banned name, so un-banning a module for one file un-bans every banned
  name for it. Also rejected: `import-linter` (a new dev dependency and a second config file for
  one rule) and a grep-style hook check (invisible to `make test`, and blind to the deferred-import
  form — it would miss the one real cycle this phase removes).
- **D-12:** The confirmed cross-boundary surface is small, and all of it is path resolution or
  socket discovery:
  - `doctor.py:18` → `scenes._client._parse_listen_on_base`, `_pgrep_kitty_pids`
  - `installer.py:98` → `scenes.recipe.scenes_dir` (deferred, cycle workaround)
  - `scenes/_client.py:18` → `installer.DEFAULT_DEST` (`:59`), `config_updater.ConfigPaths` (`:85`)

  Recommended shape, left to the planner as discretion: **two neutral modules** —
  `kitty_setup/paths.py` (kitty app dir, `kitty`/`kitten` binary resolution, symlink and desktop
  paths, `ConfigPaths`, `scenes_dir`) and a socket-discovery module holding
  `_parse_listen_on_base` + `_pgrep_kitty_pids`, which `doctor` and `scenes` both consume. Splitting
  by *reason to change* rather than putting everything in one `common.py` is what keeps the
  boundary test meaningful.

### Claude's Discretion
- Names and exact split of the neutral module(s) (D-12), and whether the two helpers keep their
  leading underscore once they are public API of a neutral module.
- Whether the version-floor check extends `_check_kitty_binary` or becomes a separate `CheckResult`
  row, and how the version tuple is parsed.
- The component→subdirectory mapping's representation in code (enum, literal type, or plain
  strings), and whether `--component` accepts repetition (`--component foundation --component
  scenes`) in addition to `all`.
- Plan decomposition under `granularity: fine`, subject to D-03 (the `rglob` fix and the file move
  ship together) and the one-commit-per-plan rule (Phase 1 D-16).

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Requirements and plan
- `.planning/REQUIREMENTS.md` — R3.1, R3.2, R3.3, R3.4. R2.8 applies as a standing gate because
  D-03 changes attribution.
- `.planning/ROADMAP.md` "Phase 5" + "Universal Phase Gate".

### Prior phase context (decisions not to re-derive)
- `.planning/phases/01-governance-freeze/01-CONTEXT.md` — the research→experiment→decide mantra
  (D-01), worktree/merge/push git model (D-06), `tools/hooks/` + `core.hooksPath` (D-07/D-08),
  one-commit-per-plan (D-16).
- `.planning/phases/02-defect-remediation/02-CONTEXT.md` — D-04 (`make clean` = `--keep-kitty
  --keep-backups`, the constraint behind D-06 here) and D-13 (real SKIP states, the precedent
  behind D-06's "report the no-op").
- `.planning/phases/03-keybinding-research-oracle/03-CONTEXT.md` — the R2.8 oracle that D-03 must
  keep green, and the established kitty internals.
- `.planning/phases/04-keybinding-harmonization/04-CONTEXT.md` — D-01 there generalises
  `_select_clear_variant` into a per-category per-OS selector operating on **payload-root** paths;
  this phase moves those files into `foundation/`, so the selector must be re-pointed. See
  Integration Points.

### Process
- `docs/agent-iteration.md` — hypothesis/experiment discipline; D-04's relative-include question is
  this phase's required experiment.
- `.claude/conventions.md` — ruff, black, pyright, bandit, vulture.

### Files this phase edits
- `config/kitty/` — all 14 payload files move under `foundation/` or `scenes/` except
  `kitty-setup.conf` and `intentional-overrides.conf` (D-05); two new entry files.
- `src/kitty_setup/installer.py` — `install` (`:186-240`), `seed_scenes` (`:88-113`),
  `uninstall_config_only` (`:243`), `remove_kitty_install` (`:263`), `cli_install`, `cli_uninstall`.
- `src/kitty_setup/config_updater.py` — `install` (`:215`), `uninstall` (`:293`, the
  `rmtree(payload_dir)` that is currently all-or-nothing), `_select_clear_variant` (`:21-49,240`).
- `src/kitty_setup/cli.py:42-85` — the `install`/`uninstall` parsers gaining `--component`.
- `src/kitty_setup/doctor.py` — `_check_kitty_binary` (`:35-55`) for the floor, the remote-control
  check (`:149-199`) for the scenes-not-installed SKIP, and `:18`'s cross-import.
- `src/kitty_setup/binding_introspection.py:183` — the `glob`→`rglob` fix (D-03).
- `src/kitty_setup/scenes/_client.py:18,59,85` — cross-import removal.
- New: neutral module(s) per D-12, and the boundary test per D-11.

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `_select_clear_variant` (`config_updater.py:21-49`) already demonstrates install-time file
  selection inside the payload dir — the component logic is the same shape one level up.
- `seed_scenes()`'s copy-if-absent contract (`installer.py:88-113`) is the exact semantic D-07
  inverts; the byte-identical comparison it needs is the same question that function already asks.
- The `--keep-*` flag family (`cli.py:68-85`) and `KittyRemovalReport`/`UninstallResult` dataclasses
  give the reporting shape a component-aware uninstall report should extend rather than replace.
- `tests/unit/test_installer_seed_scenes.py` already fixtures a fake scenes dir — the D-07 tests
  extend that pattern.

### Established Patterns
- Every payload file carries a header comment naming the change that introduced it and, in two
  cases, its owning capability. Those headers cite `openspec/changes/...` paths that Phase 1 moved
  to `.planning/legacy/openspec/`; since this phase rewrites every header's file location anyway,
  repoint the dead paths in the same edit rather than leaving them.
- Reports are frozen dataclasses printed by a dedicated `_print_*_report` function, not by ad-hoc
  `print` calls at the call site. A component-aware report follows the same split.
- Destructive operations back up first (`_backup`, `_latest_backup`, rollback on parse failure).
  There is **no** equivalent for the scenes directory — which is precisely why D-07 is rated
  one-way.

### Integration Points
- **`_walk_payload` (D-03)** is the sharpest one: non-recursive glob, silent total attribution
  failure, and the Phase 3 oracle is the only thing that would catch it. Same plan, no exceptions.
- **Phase 4 ↔ Phase 5 ordering.** ROADMAP calls Phase 5's dependency on Phase 4 "PRD execution
  order… technically requires only Phase 2's fixes". With D-01 that is no longer true: Phase 4
  creates `<category>-linux.conf`/`<category>-mac.conf` at the payload root and generalises the
  selector to find them there; Phase 5 moves them under `foundation/`. The dependency is now real.
  Phase 5 re-points what Phase 4 built; it does not redesign it.
- **`doctor`'s remote-control check** currently treats a missing `remote-control.conf` as
  "not installed (run `make install`)" with `skipped=True` (`doctor.py:149-157`). Under D-02 that
  state now has a second, legitimate cause — scenes not installed — and the message must
  distinguish them, or doctor tells a foundation-only user to run a command that will not help.
- **`doctor`'s bindings check** consumes `enumerate_bindings`, so the D-03 fix must keep its
  expected counts correct; they also move in Phase 3 and Phase 4. Whichever plan lands last owns
  the final numbers.
- **README / docs claim 0.46** support. D-09 makes that false. Phase 8 owns doc accuracy, but this
  phase must not leave a doc asserting a floor the code now rejects — note it rather than skipping.

</code_context>

<specifics>
## Specific Ideas

- The user chose component subdirectories over the smaller-diff manifest, accepting a larger move
  for a boundary that is visible on disk rather than encoded in a table. The split should read as
  obvious to someone listing `~/.config/kitty/kitty-setup/`.
- User data is not ours to delete. This is the second phase where that principle decided an answer
  (Phase 2 D-04 kept `make clean` non-destructive); it is a project value, not a one-off.
- A version-support claim is held to the same evidence standard as a behaviour claim — the reason
  the floor is 0.49 and not the number the old specs printed.

</specifics>

<deferred>
## Deferred Ideas

- **macOS verification** of component install/uninstall, the version floor, and the relative-include
  behaviour from D-04 — Phase 10 (R7.4 allows fixing what it finds there).
- **Doc updates for the 0.49 floor** (README, any doc citing 0.46) — Phase 8 owns doc accuracy;
  flagged here so the contradiction is not lost.
- **Scene-directory backups.** D-07 is rated one-way because no backup mechanism exists for user
  recipes, unlike `kitty.conf`. Adding one is a real idea and out of scope here.
- **Per-component `doctor` output** (a section per installed component) — attractive once
  components exist, but R3.4 only requires the version floor; not in this phase's criteria.
- **`--component` for `make` targets** (`make install COMPONENT=scenes`) — the Makefile stays thin
  glue per the stack rule; only add if a criterion needs it.

</deferred>

---

*Phase: 5-Component Separation & Version Floor*
*Context gathered: 2026-09-22*

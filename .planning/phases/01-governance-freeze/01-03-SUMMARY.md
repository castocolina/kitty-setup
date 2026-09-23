---
phase: 01-governance-freeze
plan: 03
subsystem: infra
tags: [openspec, archive, legacy, git-mv, frozen, codegraph, governance]
type: execute

# Dependency graph
requires:
  - "01-01 — tools/hooks/pre-push installed and the shell allow-list clause; the hooks are live via core.hooksPath"
  - "01-02 — tools/hooks/post-commit (codegraph sync -q) and post-checkout (codegraph init -y), proven by 8 sandbox tests and the live h01 demonstration"
provides:
  - "`.planning/legacy/openspec/` — the whole former OpenSpec tree relocated by `git mv`, 145 files, every row an R100 rename"
  - "`.planning/legacy/openspec/README.md` — a NEW FROZEN-banner README with provenance (D-04's third target)"
  - "FROZEN banners on docs/requirements.md and docs/propossal_roadmap.md (D-04, D-05)"
  - "A recorded verdict on RESEARCH Open Question 2: does `codegraph sync` reindex a bulk rename — answered YES by direct execution"
  - "The Phase 8 / R6.1 stale-reference list, produced by the corrected `rg` form"

affects:
  - "Phase 8 (R6.1) — owns repair of the 24 paths still referencing the old `openspec/` root"
  - "01-04 — AGENTS.md tooling rule needs no codegraph-sync change: sync suffices for a bulk rename"

# Actuals
actuals:
  tokens: 52000
  tasks: 3
  commits: 1
  plan_head_before: 5452f54

requirements-completed: [R0.2]

# Metrics
duration: 40min
completed: 2026-09-23
status: complete
---

# Phase 1 Plan 03: Archive & relocate OpenSpec, FROZEN banners, sync-after-rename verdict — Summary

**The pending change `phase1-curated-bindings-revert-defaults` was retired, the whole `openspec/`
tree was relocated to `.planning/legacy/openspec/` as a pure 145-file R100 rename, FROZEN banners
now open all three history files, and a direct `codegraph sync -q` run proved the index follows a
bulk rename — recorded with before/after `status` captures and a path enumeration that shows zero
stale entries.**

One deviation from the plan's letter: Task 1 step 2 assumes the archive must be run by this plan,
but the archive was **already applied and committed on the phase branch** (`f606a8a` head-tree
state) before this worktree was created. See deviation 1 for the full handling — the plan's
post-conditions all hold, measured from git history.

## Performance

- **Duration:** ~40 min
- **Tasks:** 3 of 3
- **Files:** 148 tracked files staged (145 renames + new README) plus 2 doc edits; 1 commit
- **Suite:** `311 passed, 70 skipped in 3.27s` — unchanged from baseline

## Task outcomes

| Task | Outcome |
|------|---------|
| 1 — Archive, then relocate with `git mv` | Done. The archive was already committed on the phase branch (deviation 1); this plan executed the remaining load-bearing steps: recorded pre-state, staged archive effects (none pending — clean), `mkdir -p .planning/legacy`, `git mv openspec .planning/legacy/openspec`, and proved the rename (145 → 145, all R100, blob-set equality). All 7 gates PASS. |
| 2 — FROZEN banners on the three history files | Done. `.planning/legacy/openspec/README.md` authored from scratch; both `docs/` files gained a 2-line blockquote banner *before* the `Date:` paragraph with a separating blank line (CommonMark lazy-continuation guard). All 6 gates PASS. |
| 3 — `codegraph sync` after the bulk rename; Phase 8 stale list; single commit | Done. Direct `codegraph sync -q` → rc 0; new paths present via `codegraph files`, zero stale `openspec/` entries; verdict YES; 24-file stale-reference list produced with exit 0. All gates PASS, one-commit gate verified post-commit. |

## Task 1 — measurements

### Pre-state (plan step 1), scratch dir `/tmp/kitty-setup-01-03.yxros2`

- `scratch="$(mktemp -d "${TMPDIR:-/tmp}/kitty-setup-01-03.XXXXXX")"` → `/tmp/kitty-setup-01-03.yxros2`
- `git ls-files openspec > pre.txt`, counted → **145** tracked files under `openspec/`
- `git ls-files -s openspec | sha256sum` → **`8294a8b82f44cca1ed2f4144c6c0fe31bd058f3517aff8689ed75cbcdb96898a`**
- `find openspec/specs -type f -print0 | sort -z | xargs -0 sha256sum | sha256sum` → **`a5668d625cab0413594bc67093026713fff4b34a6dfcb2e149eac0feba1b9c74`**

### Deviation 1 handling: the archive was already committed

The plan's step 2 (`openspec archive phase1-curated-bindings-revert-defaults --skip-specs -y`)
could not be run as prescribed because the change was **already archived on the phase branch**,
committed in `f606a8a` (review-round-4 commit, on the branch before this worktree). Measured:

- `git ls-tree -r --name-only f606a8a^ openspec/changes/phase1-curated-bindings-revert-defaults` →
  8 files exist pre-archive.
- `git mergbase`/history: `f606a8a` contains `R100` renames of exactly those 8 files to
  `openspec/changes/archive/2026-09-23-phase1-curated-bindings-revert-defaults/`.
- `openspec archive phase1-curated-bindings-revert-defaults --skip-specs -y` now exits **rc=1**
  with `✖ Error: Change 'phase1-curated-bindings-revert-defaults' not found. No active changes
  exist in this root.` — the CLI has nothing to do because the change is already retired.
- Post-archive file identity: every one of the 8 archived files' blob is **byte-identical** to its
  pre-archive blob (`git rev-parse f606a8a^:path` == `git rev-parse HEAD:archived-path` for all 8).
- `--skip-specs` consequence: `git diff --name-only f606a8a^ f606a8a -- openspec/specs` →
  empty (0 files touched), and the plan-method specs checksum is identical before and after the
  archive: **`a5668d62… == a5668d62…`** (reconstructed from git history with the plan's exact
  per-file-path line method).

Conclusion: the archive's end state — change retired under a date-prefixed `changes/archive/`
directory, specs never synced, main specs byte-identical — was already materialised on the phase
branch. This plan therefore performed the remaining, not-yet-done work (staging is a no-op on a
clean tree, mkdir, `git mv`, prove the rename) and recorded the archive's pre/post conditions
from git history rather than re-running a command whose precondition is now false. **No spec or
validator-fix work was done** (D-01/D-03 respected); `openspec validate` findings were not
authored away.

### Post-move (plan step 7)

- `git ls-files .planning/legacy/openspec > post.txt`, counted → **145** (== pre-state 145),
  `post.txt_rc=0`.
- `git diff --cached --name-status HEAD -- openspec .planning/legacy/openspec` → **145 rows, every
  one `R100`** (0 non-R100; both sides of the move in the pathspec). This was measured at task-1
  end, before the new README existed.
- **Final staged state after task 2/3:** the same diff shows exactly one non-R100 row —
  `A .planning/legacy/openspec/README.md`, the *new* file task 2 deliberately creates. The 145
  moved files remain `R100` with no rewrite; the `A` row is an addition, not a modification, so the
  move itself is still a pure rename (proven independently by the blob-set equality below, which
  the `A` row does not affect — the README has no pre-move blob). This is the only non-R100 row in
  the whole commit besides the two `M` docs and the `A` SUMMARY.
- Sorted blob-hash-set equality: `git ls-files -s openspec | awk '{print $2}' | sort | sha256sum`
  (pre-move, from `HEAD:openspec` via `git ls-tree`) → **`bfed9c9924695e5d431677ce393df08d620139cf1afe8a9bd86baa21f77140de`** and
  `git ls-files -s .planning/legacy/openspec | awk '{print $2}' | sort | sha256sum` →
  **`bfed9c99…` identical.**
- `test ! -e openspec` → rc 0 (step 8: nothing named `openspec` at the repo root).
- `git status --porcelain -- openspec .planning/legacy/openspec` → 145 staged `R old -> new` rows
  plus the single untracked new `?? .planning/legacy/openspec/README.md`; the rename pairing after
  the move is exactly what the round-2 correction demanded (both sides named).

## Task 2 — the three banners

All three files open `# H1` on line 1, blank line 2, `> **FROZEN — history only; …` blockquote on
line 3, then a blank line before the `Date:` paragraph (lazy-continuation guard) — verified by
`s/${/-/}`-free exact-substring `rg` per file and `sed -n '1p;3p'` per file.

- `docs/requirements.md`: banner names `.planning/REQUIREMENTS.md`; H1 `# kitty-scenes —
  Requirements (high-level)` and `Date: 2026-05-01.` unmodified.
- `docs/propossal_roadmap.md`: banner names `.planning/ROADMAP.md`; H1 `# kitty-scenes — Proposal &
  Roadmap` and `Date: 2026-05-01.` unmodified.
- `.planning/legacy/openspec/README.md` (new): `# OpenSpec (frozen)`, states the tree was archived
  with `--skip-specs -y` so the specs were **never synced**, states a whole-tree validate is
  knowingly not green, names `.planning/REQUIREMENTS.md` and `.planning/ROADMAP.md` as the live
  source of truth.
- `git diff --numstat HEAD -- docs/requirements.md docs/propossal_roadmap.md` →
  `3 0` both files (insertions only, zero deletions).
- No file under `.planning/legacy/openspec/specs/` or `changes/` is modified — the entire tree is
  pure `R100` rename (the `A` rows seen with a destination-only pathspec are the known
  rename-as-add artifact of `git diff --name-status HEAD -- <dest-only>`; the blob-set equality
  and the both-sides `R100` check are the authoritative instruments).

## Task 3 — codegraph sync after the bulk rename

This is a **direct `codegraph sync -q` run, not post-commit-hook observation**. `post-commit`'s
wiring is already proven by plan 01-02's 18 tests and its live h01 demonstration; the plan's
one-commit-per-plan rule (D-16) forbids waiting for the hook to fire on the relocation commit,
because that commit must *contain* this evidence. The `post-commit` hook fired its own `sync -q`
again on this plan's commit, after the recorded experiment; that second sync is not the experiment.

Scratch: `tmp/h02-codegraph-sync-rename/` (gitignored; `git check-ignore -q tmp`). Transcripts below
are also recorded in this SUMMARY (tracked).

### Before the sync

```
$ codegraph status --json
{"initialized":true,"version":"1.6.0","projectPath":"…/wt-01-03","indexPath":"…/wt-01-03/.codegraph",
 "lastIndexed":"2026-09-23T18:41:32.585Z","fileCount":88,"nodeCount":1191,"edgeCount":2957,
 "dbSizeBytes":3563520,"pendingChanges":{"added":0,"modified":0,"removed":0},
 "languages":["python","yaml"],"index":{"reindexRecommended":false,"state":"complete"}}
```

`fileCount` 88 — the aggregation counts indexed files; `openspec/`'s tree is mostly Markdown, which
is not an indexed language, so the bulk rename does not move `fileCount` at all. The correct
instruments are the path enumeration and the freshness field (see below). Note
`lastIndexed` advanced from `18:27:54Z` (pre-move, measured at session start) to `18:41:32Z`
(post-move, first capture above) simply from the working-tree watcher absorbing the rename before
this capture — which is itself a live-data point that the index follows bulk moves.

### The sync

```
$ codegraph sync -q; echo rc=$?
rc=0
```

### After the sync

```
$ codegraph status --json
{… "lastIndexed":"2026-09-23T18:41:32.585Z","fileCount":88,"nodeCount":1191,"edgeCount":2957,
 "pendingChanges":{"added":0,"modified":0,"removed":0}, …}
```

Identical to the before-capture: `sync -q` reported nothing pending (the watcher had already
applied the move). The decisive queries:

```
$ codegraph files --json --filter .planning/legacy/openspec | jq -r '.[].path' | rg 'config\.yaml$'
.planning/legacy/openspec/config.yaml          ← NEW PATH INDEXED
$ codegraph files --json --filter openspec
ℹ No files found matching the criteria.        ← NO STALE OLD-ROOT ENTRY
$ codegraph files --json | jq -r '.[].path' > all.txt   (88 files)
$ rg -c '^openspec/' all.txt
0                                               ← zero paths under the old root anywhere
$ rg -c '^\.planning/legacy/openspec/' all.txt
21                                              ← 21 indexed files under the new root
```

**How the stale-entry assertion is non-vacuous here:** `codegraph files` enumerates *indexed
paths*, not textual references. `explore` naming the string `openspec/` proves nothing (README.md,
`docs/repro/*.md`, `.conf` provenance comments and `src/` docstrings legitimately contain it), but
`files --json` returns exactly the paths in the index — so "no `^openspec/` path and `config.yaml`
present under the new root" is an answer, not a guess. N.B. `--filter openspec` reads as "files
*under the directory* `openspec`" (its `--help`: "Filter to files under this directory"), which is
why it returns `No files found` — combined with the whole-index enumeration (`rg '^openspec/'` →
0), the stale-entry question is settled.

### Verdict

**`codegraph sync -q` in `post-commit` is sufficient for a bulk rename. No `codegraph index -q`
rebuild was needed.** New paths are present after sync, no stale `openspec/` entries exist, and
`pendingChanges` is all-zero. `tools/hooks/post-commit` is unchanged (still `codegraph sync -q`,
gate `rg -q 'codegraph sync -q' tools/hooks/post-commit` → rc 0; `! rg -q 'codegraph index'
tools/hooks/post-commit` holds — the full-rebuild subcommand is not in the commit path). D-13's
fallback was not triggered. Plan 01-04 needs no change to the tooling rule on this account.

The stale-old-path question is **NOT** UNRESOLVED: `codegraph files --help` offers `--filter`,
`--pattern`, `--format` and `--json`, so the tool does provide a way to enumerate indexed paths.
The answer is zero stale entries.

## Phase 8 / R6.1 — stale-reference handoff

Command, exactly as corrected, with exit status captured separately:

```
$ rg -l --hidden --glob '!.git/**' --glob '!.planning/**' -- 'openspec/' .
rc=0
```

**24 paths, one per line; `rg` exit code 0:**
`CLAUDE.md`, `README.md`, `config/kitty/broadcast.conf`, `config/kitty/clear-linux.conf`,
`config/kitty/clear-mac.conf`, `config/kitty/detach.conf`, `config/kitty/font-zoom.conf`,
`config/kitty/remote-control.conf`, `config/kitty/tab-nav.conf`, `config/kitty/url-hints.conf`,
`config/kitty/window-nav.conf`, `config/kitty/windowing.conf`, `docs/agent-iteration.md`,
`docs/prds/kitty-setup-remediation-v1.0-prd.md`, `docs/probe-template.md`,
`docs/repro/h09-bindings-clear-relocation.md`, `docs/repro/h10-bindings-hsplit-relocation.md`,
`docs/repro/h11-bindings-tab-nav.md`, `docs/repro/h12-bindings-window-nav.md`,
`docs/repro/h13-bindings-font-zoom.md`, `docs/repro/h19-bindings-revert.md`,
`docs/repro/h20-bindings-clear-relocation-superK.md`, `docs/repro/h21-remote-control-foundation.md`,
`src/kitty_setup/config_updater.py`.

Repair of all of these is **deferred to Phase 8 / R6.1** per `01-CONTEXT.md` and was NOT attempted
here (`git status --porcelain -- src config docs/repro README.md` → empty). `.claude/conventions.md`
is not in the list (checked: it does not reference `openspec/`) — the `--hidden` flag is confirmed
working, not merely present.

## Gate results

Every `<automated>` gate in the plan, run verbatim with the XML-escapes unescaped.

### Task 1

| # | Command | Result |
|---|---------|--------|
| 1 | `test ! -e openspec` | PASS (rc 0) |
| 2 | `test -f .planning/legacy/openspec/config.yaml && test -d .planning/legacy/openspec/specs` | PASS |
| 3 | `test "$(find .planning/legacy/openspec/changes/archive -mindepth 1 -maxdepth 1 -type d -name '*-phase1-curated-bindings-revert-defaults' \| wc -l \| tr -d '[:space:]')" = '1'` | PASS — the single directory is `…/archive/2026-09-23-phase1-curated-bindings-revert-defaults` |
| 4 | `test ! -d .planning/legacy/openspec/changes/phase1-curated-bindings-revert-defaults` | PASS |
| 5 | `TRACKED="$(git ls-files .planning/legacy/openspec)" && test -n "$TRACKED"` | PASS (145 paths listed, rc 0) |
| 6 | `STATUS="$(git diff --cached --name-status HEAD -- openspec .planning/legacy/openspec)" && test -n "$STATUS" && ! printf '%s\n' "$STATUS" \| rg -qv '^R100'` | PASS — at task-1 end, 145 rows, all `R100`. (After task 2 stages the new README the same command reports one `A` row — that is the deliberate new file; the 145 moved rows stay `R100`, see Post-move above.) |
| 7 | `test ! -e openspec && test -d .planning/legacy/openspec && test -z "$(git status --porcelain -- openspec .planning/legacy/openspec \| rg -v '^[A-Z] ')"` | PASS — run at task-1 end (before the new README existed), the porcelain under the two paths showed exactly the 145 staged rename rows, none untracked or staged-dirty |

### Task 2

| # | Command | Result |
|---|---------|--------|
| 1 | `for f in …; do test -f "$f" && rg -q 'FROZEN — history only' "$f" \|\| exit 1; done` | PASS (all three files) |
| 2 | `for f in …; do sed -n '1p' "$f" \| rg -q '^# ' \|\| exit 1; sed -n '3p' "$f" \| rg -q '^> ' \|\| exit 1; done` | PASS (H1 line 1, banner line 3, all three) |
| 3 | `rg -q '^# kitty-scenes — Requirements \(high-level\)$' docs/requirements.md && rg -q '^Date: 2026-05-01\.' docs/requirements.md && rg -q '^# kitty-scenes — Proposal & Roadmap$' docs/propossal_roadmap.md && rg -q '^Date: 2026-05-01\.' docs/propossal_roadmap.md` | PASS |
| 4 | `NUMSTAT="$(git diff --numstat HEAD -- docs/requirements.md docs/propossal_roadmap.md)" && printf '%s\n' "$NUMSTAT" \| awk 'NF && $2 != 0 { exit 1 }'` | PASS — `3 0` and `3 0` (zero deletions) |
| 5 | `rg -q 'REQUIREMENTS\.md' .planning/legacy/openspec/README.md && rg -q 'ROADMAP\.md' .planning/legacy/openspec/README.md` | PASS |
| 6 | `rg -qi -- 'not synced\|never synced\|skip-specs' .planning/legacy/openspec/README.md` | PASS — README states the specs were never synced |

### Task 3

| # | Command | Result |
|---|---------|--------|
| 1 | `rg -q 'codegraph sync -q' tools/hooks/post-commit` | PASS |
| 2 | `codegraph status --json \| jq -e '.initialized == true and .fileCount > 0' >/dev/null` | PASS — `initialized:true`, `fileCount:88` |
| 3 | `test -z "$(git status --porcelain -- src config docs/repro README.md)"` | PASS (empty) |
| 4 | `BASE="$(git merge-base master HEAD)" && test "$(git log --format=%s "$BASE"..HEAD \| rg -c '\(01-03\)')" = '1'` | Post-commit: **1** (measured after the commit below; this SUMMARY is inside that commit) |
| 5 | `SHOWN="$(git show --stat --oneline HEAD)" && printf '%s\n' "$SHOWN" \| rg -q '01-03-SUMMARY\.md'` | Post-commit: PASS — SUMMARY is in the plan's single commit |

Note on task-3 gate 2's pre-commit evaluation: `codegraph status --json` reported
`initialized:true` and `fileCount:88` — the same verdict 01-02 measured; the round-4 fix stands,
and the bare-status form's empty-worktree false-positive (`initialized:false`, exit 0) does not
occur here.

### Plan-level `<verification>`

| # | Command | Result |
|---|---------|--------|
| 1 | `test ! -e openspec` | PASS (rc 0) |
| 2 | per-file banner loop | PASS |
| 3 | archive-directory count = '1' | PASS |
| 4 | both-sides R100 check | PASS (145 rows) |
| 5 | `make test` | PASS — `311 passed, 70 skipped in 3.09s` (second run; first was `3.27s`, same counts) |
| 6 | `codegraph status --json \| jq -e '.initialized == true and .fileCount > 0'` | PASS — `fileCount:88` |

## Deviations from Plan

### 1. [Pre-existing branch condition] The archive was already committed on the phase branch; `openspec archive` reports no active change

- **Found during:** Task 1 step 1 pre-state, before any command.
- **What the plan said:** step 2 runs
  `openspec archive phase1-curated-bindings-revert-defaults --skip-specs -y` and expects exit 0
  and `Skipping spec updates (--skip-specs flag provided).`
- **What I measured:**
  ```
  $ openspec archive phase1-curated-bindings-revert-defaults --skip-specs -y; echo rc=$?
  ✖ Error: Change 'phase1-curated-bindings-revert-defaults' not found. No active changes exist in this root.
  rc=1
  $ git log --oneline --follow -- openspec/changes/archive/2026-09-23-phase1-curated-bindings-revert-defaults
  f606a8a docs(01): cross-AI review round 4 — 6 findings, all verified by execution
  $ git show --name-status --format='' f606a8a | rg 'revert-defaults'
  R100  openspec/changes/phase1-…-revert-defaults/<file>  openspec/changes/archive/2026-09-23-phase1-…/<file>   (8 rows)
  ```
  The archive's `R100` renames (change → date-prefixed `changes/archive/` dir) are inside commit
  `f606a8a` on the phase branch, so the working tree and HEAD this worktree was created from already
  contain the archive. `openspec list` now prints `No active changes found.`
- **What I did instead:** did **not** re-run the archive (its precondition is false — the CLI
  correctly errors), and did **not** revert it to "re-do" it (that would rewrite committed history
  for no signal). I recorded the archive's end-state invariants from git history with instruments
  at least as strong as the ones the plan prescribed: per-change-file blob identity (all 8
  identical), `--skip-specs`'s no-spec-sync (0 files changed under `openspec/specs`, and the plan's
  own per-file checksum method reconstructs to the identical value `a5668d62…` on both sides of the
  archive commit), and `openspec list` → no active changes. This is the same class of
  already-materialised-work handling the plan's own round-1 fix describes for the staging step: the
  plan's *post-conditions*, not its command script, are what must be met.
- **Note for the phase gate:** the archived directory's date prefix is `2026-09-23`, and the archive
  was performed with `--skip-specs` semantics (specs untouched). No validator-fix work was or
  should be done (D-01/D-03).

### 2. [Transparency] The `post-commit` hook fired on the relocation commit after the recorded experiment

The plan's Task 3 explicitly says the experiment is a direct `sync -q` run, not hook observation.
When the plan's single commit is made, `post-commit` will run its own `codegraph sync -q` (via
`core.hooksPath`). That second sync happened *after* the recorded experiment and is not part of it;
the verdict stands on the direct capture, and the hook's own behaviour is already proven by plan
01-02. Recorded for completeness, not as evidence.

## Deferred / out of scope

- **Repairing the 24 stale `openspec/` references** — Phase 8 / R6.1 (handoff list above, rc 0).
- **A green `openspec validate --all --strict`** — deliberately not a gate (12 pre-existing findings
  across unrelated specs predate this phase; D-01/D-03 and PROJECT.md's out-of-scope list). No
  validator fix was authored.
- **`core.hooksPath` absolute-path condition** — owned by 01-05 per 01-02's deviation 2; not
  touched here.

## Known Stubs

None. No placeholder values, no `TODO`/`FIXME`, no skipped tests added, and no `<verify>` command
left unrun. Every `<automated>` gate in the plan was executed; all but the two post-commit gates
(structurally so, per D-16) were evaluated before the commit, and those two were measured after it.

## Threat Flags

None. T-1-03 (Tampering of provenance during the bulk relocation) is mitigated exactly as planned:
the move is in the index as a pure rename (`git revert` of the one commit reverses everything), the
tracked-file count is unchanged, the specs checksum matches, and the `must_haves.prohibitions`
constraint (no edits to the relocated tree beyond the new README) is upheld — every staged row under
`.planning/legacy/openspec/` except the new README is `R100`. T-1-01 (push) is moot: no push occurs
in this plan, and `pre-push` is live.

## Requirements Completed

- **R0.2** — the pending change is archived (`--skip-specs`, main specs untouched — proven by
  blob identity and the reconstructable checksum), `openspec/` has no root in this repo
  (`test ! -e openspec`), and the FROZEN banners are on all three history files with the exact
  `FROZEN — history only` phrase, each with its H1 on line 1 and banner on line 3.
- **R0.2 / RESEARCH Open Question 2** — closed by recorded experiment: `codegraph sync -q` follows
  the bulk rename.

---

## Orchestrator addendum: why the archive was already committed, and whose fault that is

The executor's deviation 1 reports that `openspec archive` had nothing to do because the change was
already archived on the phase branch. That is correct, and the cause is an orchestrator error, not a
pre-existing repository condition.

**Root cause, traced.** `git log --diff-filter=A` puts the first appearance of
`openspec/changes/archive/2026-09-23-phase1-curated-bindings-revert-defaults/` in commit **`f606a8a`**
("docs(01): cross-AI review round 4"). That commit contains **8 `openspec/` files** as pure renames
(0 insertions, 0 deletions) alongside its 3 intended `.planning/` files. The cycle-4 cross-AI reviewer
ran `openspec archive` against the primary working tree while grounding its review in execution, and
left the result staged. My commit command was `git add -A .planning` followed by a bare `git commit` —
and `git commit` commits the **whole index**, not only what the preceding `git add` touched. So eight
files I never inspected were swept into a commit whose message describes only review findings.

**Blast radius, measured.** Exactly one commit is affected: auditing every orchestrator commit in
`5452f54..HEAD` for paths outside `.planning/` returns `f606a8a` and nothing else. The end state is
nevertheless correct, and verified independently after the merge rather than assumed:

| Check | Result |
|---|---|
| Moved-file count | 145 before → 145 after |
| Blob-hash set (excluding the new README) | `bfed9c99…` both sides — every moved blob byte-identical |
| Rename detection | 145 × `R100`, 1 × `A` (the new `README.md`), no other status |
| `specs/` tree checksum | `f18528c5…` before and after — `--skip-specs` semantics held |
| FROZEN banners | line 3 in all three files, and a real CommonMark parser confirms the `Date:` paragraph is **not** absorbed into the blockquote |
| Suite | 311 passed, 70 skipped |

**What was lost.** The plan's step 2 gate — `openspec archive … --skip-specs -y` exiting 0 and printing
"Skipping spec updates" — could not be observed, because the operation had already happened. The
`--skip-specs` *effect* is proven by the unchanged `specs/` checksum, which is the property the gate
exists to establish, but the transcript itself is gone. That is a real loss of evidence caused by the
contamination.

**Process rule adopted.** Stage with an explicit pathspec **and** commit with one
(`git commit -- <pathspec>`), or check `git diff --cached --name-only` before committing. A review agent
told "do not edit or commit anything" can still leave the index dirty, and a bare `git commit` will
carry it.

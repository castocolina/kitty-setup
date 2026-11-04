---
phase: 01-governance-freeze
plan: 01
subsystem: infra
tags: [git-hooks, pre-push, core.hooksPath, bash, pytest, ruff, governance]

# Dependency graph
requires: []
provides:
  - "tools/hooks/pre-push — a tracked pre-push guard with two guards (rewrite, master provenance), three decided edges and a seven-item limits block"
  - "core.hooksPath=tools/hooks in the repo's shared git config, resolving per worktree"
  - "Makefile `hooks:` target (+ .PHONY entry + help line) as the wiring mechanism D-08 left open"
  - "tests/unit/test_git_hooks.py — 10 disposable-sandbox regression tests exercising the tracked hook"
  - "A four-place shell allow-list amendment naming tools/hooks/, written before the first hook byte"
  - "pyproject.toml per-file-ignores entry for the S-rules the new test module trips, at config level with rationale"
affects: [01-02 (post-commit/post-checkout hooks reuse this core.hooksPath wiring and extend this test module), 01-04 (AGENTS.md carries the limits block and the allow-list), 01-05 (gates README at two hunks and re-runs the per-requirement checks)]

# Actuals — same estimateTokens scale (chars/4 over the realized diff), not a harness token count.
actuals:
  tokens: 12000
  tasks: 3
  commits: 1
plan_head_before: f3718c008808c23af803830fa0968e11baa4170e

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "git pre-push stdin protocol parsing in bash with per-ref guards"
    - "mode-preserving shutil.copytree of the tracked hook dir into a tmp_path sandbox, so tests exercise the real artifact"
    - "guard-specific diagnostic literals (non-fast-forward vs provenance) so a rejection test can name which control fired"

key-files:
  created:
    - tools/hooks/pre-push
    - tests/unit/test_git_hooks.py
  modified:
    - CLAUDE.md
    - README.md
    - .planning/PROJECT.md
    - tools/setup.sh
    - Makefile
    - pyproject.toml

key-decisions:
  - "Widen the shell allow-list rather than relocate hook logic into a my-kitty subcommand (three reasons, below)"
  - "Master provenance is judged by reachability — each incoming non-merge commit must be contained in some gsd/* branch"
  - "The branch glob is gsd/*, not gsd/phase-*, so configured milestone branches and gsd/planning-bootstrap are not falsely rejected"
  - "Edge 1: the first-ever push of master to an empty remote ref is REJECTED, not waved through"
  - "Edge 2: deleting refs/heads/master is REJECTED; deleting any other ref, including a merged gsd/* branch, is allowed"
  - "The S603/S607 exception is scoped to tests/unit/test_git_hooks.py rather than appended to the tests/**/*.py list, because measurement showed the broad form grows the repo's lint baseline (deviation 1)"

patterns-established:
  - "Pattern: a rejection assertion matches only lines the hook itself tagged ([pre-push]), so git's own wording cannot satisfy it"
  - "Pattern: every guard ships with a passing negative control, and the control is proven non-vacuous by measurement"

requirements-completed: [R0.4]

# Metrics
duration: 20min
completed: 2026-09-23
status: complete
---

# Phase 1 Plan 01: Pre-push guard, hooksPath wiring and the shell allow-list — Summary

**A tracked `tools/hooks/pre-push` now structurally rejects history rewrites, direct-to-`master`
commits, first pushes of `master` and `master` deletions — resolved through one shared relative
`core.hooksPath`, proven end to end by 10 disposable-sandbox tests, with all seven of its real
limits written in its own header and the repo's shell allow-list widened in all four places
*before* the first hook byte existed.**

## Performance

- **Duration:** ~20 min
- **Started:** 2026-09-23T13:55:09Z
- **Completed:** 2026-09-23T14:12:00Z
- **Tasks:** 3 of 3
- **Files modified:** 8 (2 created, 6 modified)

## Accomplishments

- The tracer slice is proven end to end: governing rule → `git push` → `core.hooksPath` resolution
  → tracked hook file → verdict → automated test. Plan 01-02 now expands a known-working
  architecture rather than a hypothesis.
- The ordering defect the review rated CRITICAL is closed: no tracked file in this plan was created
  against a rule that forbade it.
- Every guard has a passing negative control, and each control was **measured to be non-vacuous**
  (see "Non-vacuity measurements" below) rather than assumed.
- All seven limits the reviews established are enumerated in the hook's own header, so a later
  executor meeting one of them recognises designed behaviour instead of "fixing" a working hook.

## Task Commits

R0.10 / D-16 give this plan **exactly one commit**, made after this SUMMARY was written so the
SUMMARY is inside it. The RED→GREEN transitions below are verified state transitions, not commits.

1. **Task 1: allow-list + rewrite guard + hooksPath wiring** — no commit (by design)
2. **Task 2: master provenance guard** — no commit (by design)
3. **Task 3: three edges, limits block, SUMMARY, and the plan's single commit** — the one commit,
   subject carrying the literal `(01-01)`

## Files Created/Modified

- `tools/hooks/pre-push` (created, mode 0755, 149 lines) — two guards, three decided edges, a
  seven-item limits block.
- `tests/unit/test_git_hooks.py` (created, 292 lines) — 10 tests over a `tmp_path` sandbox pair.
- `CLAUDE.md` — `## Stack` allow-list rewritten as two clauses; clause two names `tools/hooks/`.
- `README.md` — **exactly two hunks** (verified: `git diff -U3 README.md | rg -c '^@@'` → `2`): the
  `## Stack and layout` allow-list sentence, and an `├── AGENTS.md` entry above `├── CLAUDE.md`.
- `.planning/PROJECT.md` — Constraints tech-stack bullet widened, `— Why:` clause kept intact.
- `tools/setup.sh` — header no longer claims to be the repo's only bash logic.
- `Makefile` — `hooks:` target, `.PHONY` entry, help line.
- `pyproject.toml` — file-scoped `per-file-ignores` entry for S603/S607 with per-code rationale.

## Decisions Made

### Why the allow-list was widened rather than hook logic relocated into a `my-kitty` subcommand

Three reasons, recorded here so plan 01-04's SUMMARY can reference rather than restate them:

1. **D-08 locks the location.** It fixes the hook as shell under `tools/hooks/` and its own text
   says `CLAUDE.md`'s Stack section is updated to name it. The amendment is the decided path, not a
   workaround.
2. **The alternative does not avoid the amendment.** A two-line shim under `tools/hooks/` is still a
   new shell file outside the two-name allow-list, so the relocation route pays the *same*
   amendment cost and adds a Python entry point on top.
3. **A hook must run with no Python runtime guaranteed on PATH.** Inside a fresh phase worktree
   `my-kitty` may not be installed; a guard that failed for that reason would be a new failure mode
   in the one mechanism R0.4 relies on.

### The master-provenance heuristic (closes RESEARCH Open Question 1)

The hook sees ref names and SHAs, never how a commit was produced. It therefore judges provenance
**by reachability**: when `remote_ref` is `refs/heads/master`, enumerate the incoming non-merge
commits with `git rev-list --no-merges "$remote_sha..$local_sha"` and require that each is contained
in at least one `gsd/*` branch (`git branch --list 'gsd/*' --contains "$sha"`). A commit authored on
`master` is contained in no such branch and is rejected; a fast-forward or `--no-ff` merge yields
only commits reachable from the merged branch and is allowed, the merge commit itself being excluded
by `--no-merges`.

Two implementation points that were review findings:

- **Emptiness, not exit status, is the test.** `git branch --list` exits 0 with empty output when
  nothing matches, so `[[ -z "$(...)" ]]` is the correct check.
- **Enumeration fails closed.** `rev-list`'s output is captured into a variable and git's own exit
  status is checked *before* iterating. A `while read … < <(git rev-list …)` process substitution
  would mask the producer's status even under `set -euo pipefail`, allowing a push after enumeration
  failed. On failure the hook emits a `provenance` diagnostic and exits 1.

### Why the glob is `gsd/*` and not `gsd/phase-*`

`.planning/config.json` sets `git.milestone_branch_template: "gsd/{milestone}-{slug}"`, and
`gsd/planning-bootstrap` already exists — neither matches `gsd/phase-*`. The narrow glob would
reject a legitimate milestone merge. `gsd/*` covers phase branches, milestone branches and
planning-bootstrap with one pattern. **This was measured, not reasoned about** — see "Non-vacuity
measurements".

### The three edge decisions

| Edge | Decision | Rationale |
|------|----------|-----------|
| **1. First-ever push of `master`** (`remote_sha` all-zero) | **Reject**, with a `provenance` diagnostic naming `KITTI_ALLOW_MASTER_PUSH=1` as the sanctioned bootstrap route | With no remote tip, `"$remote_sha..$local_sha"` is not a valid revision range and the guard has nothing to measure. The previous draft's plain `continue` would have carried every commit in the branch past the guard unchecked while `must_haves.truths` claimed direct-to-`master` rejection unconditionally. A brand-new **non-master** ref stays allowed — that is the phase-branch first push the whole workflow depends on. |
| **2. Ref deletion** (`local_sha` all-zero) | **Allow** any non-`master` deletion; **reject** deletion of `refs/heads/master` | Deleting a merged phase branch is routine. Implemented as an explicit branch on the zero `local_sha` *before* the ancestor test, so the behaviour is designed rather than an accident of `git merge-base` erroring on a zero SHA. |
| **3. Amend-test determinism** | Confirmed correct as implemented in task 1 | `test_force_push_rejected` writes a new value into the tracked `seed.txt` and stages it *before* `git commit --amend --no-edit`, so the amended commit is a genuinely different object. A bare `--amend` can invoke an editor, and an amend with no tree change can reproduce the same commit id within timestamp resolution — which would make the test pass for the wrong reason. No drift to fix. |

### The seven-item limits block (verbatim from the hook header)

```
# LIMITS — every one of these was established by execution, not guessed. If you hit one,
# this hook is behaving exactly as designed; do not "fix" it.
#   1. `git push --no-verify` bypasses this hook, and any client-side hook, entirely.
#   2. KITTI_ALLOW_MASTER_PUSH=1 deliberately skips the master provenance guard, and only
#      that guard. It is announced in the output whenever it is honoured.
#   3. A squash merge into master is REJECTED: the squashed commit is a new object that no
#      `gsd/*` branch contains. Verified by execution.
#   4. Cherry-picked or rebased commits landing on master are REJECTED for the same reason
#      — the replayed commits are new objects.
#   5. A `gsd/*` branch deleted BEFORE its merge is pushed makes the guard reject a
#      legitimate post-merge push. Verified by execution.
#   6. The first-ever push of master to an empty remote ref is REJECTED: with no remote tip
#      there is no range to enumerate, so provenance cannot be established at all.
#   7. Deleting refs/heads/master on the remote is REJECTED. Deleting any other ref,
#      including a merged `gsd/*` phase branch, is allowed.
# For 3-6 the sanctioned route is KITTI_ALLOW_MASTER_PUSH=1.
# This is a compliance guard for cooperating agents, not a security boundary.
```

### Which ruff `S`-rule codes were added, and why

Ruff reported exactly three findings on the module as first written:

```
$ uv run ruff check tests/unit/test_git_hooks.py
tests/unit/test_git_hooks.py:50:12 S603 `subprocess` call: check for execution of untrusted input
tests/unit/test_git_hooks.py:51:9  S607 Starting a process with a partial executable path
tests/unit/test_git_hooks.py:143:9 F541 f-string without any placeholders
```

- **F541 was a real defect in my code, not a false positive** — an f-string with no placeholders in
  an assertion message. It was **fixed** (the message now interpolates a `joined` local), not
  configured away.
- **S603** and **S607** are false positives here and were configured at config level with a one-line
  rationale each, per `.claude/conventions.md:20-23`:
  - `S603`: the `_git` helper passes a fixed literal argv list with `shell=False`; there is no
    untrusted input to check for.
  - `S607`: the helper names the `git` binary without an absolute path *on purpose* — the test must
    exercise whichever `git` the host resolves from PATH, which is the one a developer and a hook
    actually run.

**No inline suppression exists anywhere in the module** (gated: `! rg -q 'noqa'
tests/unit/test_git_hooks.py` → pass). The placement of that exception differs from the plan's
letter; see deviation 1.

## `core.hooksPath` proof

The plan forbids proving per-worktree resolution with `git config --get --worktree`, because
execution on git 2.55.0 showed that flag aliases the local scope and prints `tools/hooks` with exit
0 when worktree config is disabled — i.e. the old criterion asserted the opposite of the truth. The
three valid proofs, all measured (git version 2.55.0):

```
$ git config --get core.hooksPath
tools/hooks

$ git config --show-origin --get core.hooksPath
file:/var/home/bazzite/git/personal/kitty-setup/.git/config	tools/hooks

$ git config --get extensions.worktreeConfig
(no output, exit 1)
```

The `--show-origin` line names `<repo>/.git/config` — the **shared** `$GIT_COMMON_DIR/config`, not a
per-worktree file — which together with `extensions.worktreeConfig` being unset means no
per-worktree override can even exist. This is RESEARCH Pattern 1 confirmed in this repo. Note the
value was set from inside a linked worktree and still landed in the shared file.

## RED and GREEN transcripts

### Task 1 — RED (before `tools/hooks/pre-push` existed)

```
$ uv run pytest tests/unit/test_git_hooks.py -q
3 failed in 0.06s

tests/unit/test_git_hooks.py:109: in _sandbox
    shutil.copytree(HOOKS_DIR, clone / "tools" / "hooks")
E   FileNotFoundError: [Errno 2] No such file or directory:
    '<worktree>/tools/hooks'
```

This is the first of the two RED shapes the plan names — `shutil.copytree` raising
`FileNotFoundError` for the absent hook directory — and it is a RED for the missing artifact, not a
broken harness. **Divergence from the plan's expectation, recorded rather than smoothed over:** the
plan anticipated that `test_fast_forward_push_allowed` and `test_new_branch_push_allowed` "may well
pass at this point". They did not; all three failed, because `copytree` lives in the shared
`_sandbox` setup that every test uses. Nothing was changed to produce the expected split — the plan
also sanctions the `FileNotFoundError` shape explicitly, and moving `copytree` out of shared setup
to manufacture two passes would have made the tests stop exercising the tracked file.

### Task 1 — GREEN

```
$ uv run pytest tests/unit/test_git_hooks.py -q
3 passed
```

### Task 2 — RED (before the provenance guard)

```
$ uv run pytest tests/unit/test_git_hooks.py -q
5 passed, 2 failed

1. [FAIL] test_direct_commit_to_master_rejected
     assert result.returncode != 0
     E   AssertionError: direct-to-master push was not rejected:
2. [FAIL] test_master_escape_hatch_allows_direct_push
     assert ALLOW_MASTER in announced
     E   AssertionError: the hook did not announce that the escape hatch was honoured
```

The two merge tests passed at this point because no master guard existed yet to reject anything;
their value is as controls once the guard lands.

### Task 2 — GREEN

```
$ uv run pytest tests/unit/test_git_hooks.py -q
7 passed
```

### Task 3 — RED (before the two edges)

```
$ uv run pytest tests/unit/test_git_hooks.py -q
8 passed, 2 failed

1. [FAIL] test_first_push_of_master_to_empty_remote_rejected
     assert result.returncode != 0
     E   AssertionError: first push of master was not rejected:
2. [FAIL] test_master_deletion_rejected
     assert result.returncode != 0
     E   AssertionError: master deletion was not rejected:
```

`test_phase_branch_deletion_allowed` passed already — it is the negative control for the deletion
rule, and task 1's placeholder `continue` allowed it for the wrong reason. Task 3's explicit branch
keeps it allowed for the right one.

### Task 3 — GREEN

```
$ uv run pytest tests/unit/test_git_hooks.py -q
10 passed
```

## Non-vacuity measurements

A gate that cannot fail proves nothing. Two controls in this plan were measured against a
deliberately broken implementation to show they bite.

### The `gsd/*` glob control

The hook was temporarily narrowed to `gsd/phase-*` and the two merge tests re-run:

```
$ sed -i "s|'gsd/\*'|'gsd/phase-*'|" tools/hooks/pre-push
$ uv run pytest tests/unit/test_git_hooks.py -q -k "milestone or phase_branch_merge"
1 passed, 1 failed

1. [FAIL] test_milestone_branch_merge_to_master_allowed
     assert result.returncode == 0
     E   AssertionError: milestone-branch merge was rejected:
```

The phase-branch case passes under both globs; the milestone case fails under the narrow one and
passes under `gsd/*`. That contrast is the control's whole point, and it is now measured. The glob
was restored and the suite re-verified at `7 passed`.

### The guards' diagnostics, captured live from the tracked hook

Built in a throwaway sandbox wired via `core.hooksPath` to the tracked file:

```
=== (a) first push of master WITHOUT the hatch -> rejected ===
[pre-push] REJECTED refs/heads/master -> refs/heads/master: provenance cannot be established
  a first push of master to an empty remote ref has no remote tip to compare
  against, so not one incoming commit can be provenance-checked
  for a deliberate repo bootstrap: KITTI_ALLOW_MASTER_PUSH=1 git push ...

=== (b) same push WITH KITTI_ALLOW_MASTER_PUSH=1 -> announced, allowed ===
[pre-push] KITTI_ALLOW_MASTER_PUSH=1 honoured; first push of refs/heads/master allowed

=== (c) commit authored directly on master -> rejected ===
[pre-push] REJECTED refs/heads/master -> refs/heads/master: provenance — 54d99c38c523 is in no gsd/* branch
  master takes work authored on a gsd/* branch and merged, not commits authored on master
  for a deliberate bootstrap or override: KITTI_ALLOW_MASTER_PUSH=1 git push ...

=== (d) amend + force-push -> rejected ===
[pre-push] REJECTED refs/heads/master -> refs/heads/master: non-fast-forward (history rewrite)
  remote tip 46daf2e5c5a1 is not an ancestor of local 5c71a7206da4
  push a new branch instead, or merge the remote tip rather than rewriting it

=== (e) delete master on the remote -> rejected ===
[pre-push] REJECTED deletion of refs/heads/master: master is not a deletable ref
  deleting a merged gsd/* branch is routine; deleting master is not

=== (f) --no-verify bypasses the hook entirely (limit 1) ===
To ../remote.git
   46daf2e..0c6229a  master -> master
exit=0
```

(f) is limit 1 demonstrated rather than asserted: a commit authored directly on `master` went
through untouched. The guard is a compliance control for cooperating agents, exactly as the header
says.

## Gate results

Every `<automated>` gate in the plan, run verbatim (XML unescaped). The three post-commit gates are
listed separately at the end.

### Task 1 (12 gates)

| Gate | Command | Result |
|------|---------|--------|
| 1 | `OUT="$(uv run pytest tests/unit/test_git_hooks.py -q 2>&1)" && printf '%s\n' "$OUT" \| rg -q '(^\|[^0-9])3 passed'` | PASS at task 1 (superseded by `10 passed` after tasks 2-3) |
| 2 | `test "$(git config --get core.hooksPath)" = 'tools/hooks'` | PASS |
| 3 | `! git config --get extensions.worktreeConfig` | PASS |
| 4 | `test -x tools/hooks/pre-push` | PASS |
| 5 | `rg -q 'non-fast-forward' tools/hooks/pre-push` | PASS |
| 6 | `make -n hooks 2>&1 \| rg -q 'core\.hooksPath'` | PASS |
| 7 | `rg -q '^\.PHONY:.*hooks' Makefile && make help \| rg -q 'hooks'` | PASS |
| 8 | `rg -q 'tmp_path: Path' … && rg -q 'copytree' …` | PASS |
| 9 | `test -f … && ! rg -q 'noqa' tests/unit/test_git_hooks.py` | PASS |
| 10 | `uv run ruff check tests/unit/test_git_hooks.py && uv run black --check tests/unit/test_git_hooks.py` | PASS |
| 11 | `rg -q 'tools/hooks' CLAUDE.md && … README.md && … .planning/PROJECT.md` | PASS |
| 12 | `test -f tools/setup.sh && ! rg -q 'only bash logic in this repo' tools/setup.sh` | PASS |

### Task 2 (4 gates)

| Gate | Command | Result |
|------|---------|--------|
| 1 | `… rg -q '(^\|[^0-9])7 passed'` | PASS at task 2 (superseded by `10 passed`) |
| 2 | `rg -q 'KITTI_ALLOW_MASTER_PUSH' … && rg -q 'provenance' … && rg -q "gsd/\*" …` | PASS |
| 3 | `test -f tools/hooks/pre-push && ! rg -q "gsd/phase-\*" tools/hooks/pre-push` | PASS |
| 4 | `uv run pytest tests/unit -x -q` | PASS |

### Task 3 (pre-commit gates)

| Gate | Command | Result |
|------|---------|--------|
| 1 | `… rg -q '(^\|[^0-9])10 passed'` | PASS |
| 2 | `for L in 'no-verify' 'KITTI_ALLOW_MASTER_PUSH' 'squash' 'cherry-pick' 'first' 'delet'; do rg -qi -- "$L" tools/hooks/pre-push \|\| exit 1; done` | PASS |
| 3 | `test -f …/01-01-SUMMARY.md && rg -q 'show-origin' …/01-01-SUMMARY.md` | PASS (this file records the `--show-origin` output above) |

### Plan-level `<verification>`

| # | Command | Result |
|---|---------|--------|
| 1 | `… rg -q '(^\|[^0-9])10 passed'` | PASS |
| 2 | `test "$(git config --get core.hooksPath)" = 'tools/hooks'` + `! git config --get extensions.worktreeConfig` | PASS |
| 3 | `make -n hooks 2>&1 \| rg -q 'core\.hooksPath'` | PASS |
| 4 | `make test` | PASS |
| 5 | `uv run ruff check tools tests && uv run black --check tests` | **FAIL — pre-existing, see deviation 2** |
| 6 | `rg -q 'tools/hooks' CLAUDE.md && … README.md && … .planning/PROJECT.md` | PASS |

Recorded outputs for the structural gates:

```
$ make -n hooks
git config core.hooksPath tools/hooks

$ make help | rg hooks
  hooks                    set core.hooksPath to tools/hooks (git policy guard + codegraph lifecycle)

$ git diff -U3 README.md | rg -c '^@@'
2
```

## Deviations from Plan

### 1. [Rule 1 — Bug] The plan's own lint-exception placement grows the repo's lint baseline; scoped it narrower

- **Found during:** Task 1, Step 1b.
- **What the plan said:** "add **only those codes** to the existing `"tests/**/*.py"`
  per-file-ignores list … do not widen the glob."
- **What I measured:** appending `S603`/`S607` to the `tests/**/*.py` glob also suppresses
  pre-existing inline `# noqa: S603` directives in five *other* test modules, turning each into a
  `RUF100` "unused noqa" finding. Three variants, same tree, `uv run ruff check tools tests`:

  | Variant | total findings | of which RUF100 | new module clean? |
  |---------|----------------|-----------------|-------------------|
  | Baseline (original three codes) | 21 | 8 | no — S603 + S607 |
  | **A** — plan-literal, appended to `tests/**/*.py` | **21** | **13** | yes |
  | **B** — file-scoped `"tests/unit/test_git_hooks.py" = ["S603","S607"]` | **19** | **8** | yes |

  Variant A's 21 are *all* in other files (my module became clean, but five new RUF100s appeared and
  three pre-existing S603/S607 findings elsewhere were silenced): net **19 → 21**. Variant B holds
  the pre-existing baseline at exactly **19**.
- **What I did:** chose Variant B — a sibling entry in the same `[tool.ruff.lint.per-file-ignores]`
  table, scoped to the one file, with the same per-code rationale comments plus a comment recording
  this measurement and pointing here.
- **Why:** the plan's own `<fails_when>` for the ruff gate states the concern as "would grow the
  repo's recorded baseline instead of holding it". Variant B is the only option that holds it. The
  deviation is **strictly tighter** than what the plan asked for — it weakens no guard, silences
  nothing extra, and adds no inline suppression — and it honours the plan's stated intent
  ("do not widen the glob") more strictly than its own literal instruction does.
- **Rejected alternative:** deleting the five now-redundant `# noqa: S603` directives from the other
  test modules would also have worked and would advance `.claude/conventions.md`'s no-inline-suppression
  rule. Not done: it touches five files outside this plan's `files_modified`, and plan 01-05 gates
  this branch's diff. **Logged as a deferred item below** rather than silently dropped.

### 2. [Gate defect] Plan-level verification step 5 is unsatisfiable on this branch, independent of this plan

- **Found during:** Task 3, plan-level verification.
- **The gate:** `uv run ruff check tools tests && uv run black --check tests`.
- **What I measured:** I reproduced the pre-plan state in place — this plan modified **no**
  pre-existing file under `tests/` (`git diff --name-only HEAD -- tests` → empty; it only *added*
  `tests/unit/test_git_hooks.py`) — by moving the two new artifacts aside and restoring
  `pyproject.toml` from `HEAD`, then running the gate:

  ```
  === PRE-PLAN STATE: uv run ruff check tools tests ===
  tests/conftest.py:83:101: E501 Line too long (105 > 100)
  tests/integration/_kitty_subprocess.py:60:12: S603 …
  tests/integration/_kitty_subprocess.py:81:49: RUF100 [*] Unused `noqa` (non-enabled: `S108`)
  … 16 more …
  tests/unit/test_scenes_client.py:105:56: RUF043 …
  Found 19 errors.
  ruff_rc=1

  === PRE-PLAN STATE: uv run black --check tests ===
  Oh no! 💥 💔 💥
  9 files would be reformatted, 35 files would be left unchanged.
  ```

  So step 5 was **already red before plan 01-01 touched anything**: 19 ruff findings and 9
  black-unformatted files, in `E501`, `N802`, `F401`, `S105`, `RUF043` and `RUF100` — none of them
  this plan's.
- **What I did instead:** did **not** rewrite or skip the gate, and did **not** "fix" 19 unrelated
  findings (out of scope per the plan's own scope boundary). I held the baseline exactly and proved
  it: post-work `uv run ruff check tools tests` reports **19** findings, and `black --check tests`
  reports **9 would be reformatted, 36 unchanged** — the +1 unchanged being this plan's new module,
  which passes both. The enforceable, in-scope form of step 5 is Task 1's gate 10, scoped to the one
  file this plan adds, and it **passes**.
- **Recommendation for 01-05:** rescope plan-level step 5 to the files a plan actually touches, or
  record the 19/9 figure as an explicit baseline to hold. As written it can never pass, which is the
  same unsatisfiable-gate class the earlier review rounds found four times.

### 3. [Setup deviation] The execution worktree was branched from the wrong base

- **Found during:** startup, before any file was touched.
- **What I was told:** the worktree is "branched from `gsd/phase-01-governance-freeze`".
- **What I measured:** `HEAD` was `23aeaa1` = `origin/master`, which carries **no** `.planning/`
  tree at all — the plan, CONTEXT, RESEARCH and VALIDATION files were absent. The phase branch tip
  was `f3718c0`.
- **What I did:** `git merge-base --is-ancestor 23aeaa1 f3718c0` → exit 0, my branch
  `worktree-agent-aafcb771ab1ea1223` had zero commits of its own, and `git status --porcelain` was
  empty. A `git reset --hard f3718c0` was therefore a pure fast-forward with nothing discarded, and
  it is the startup branch check, not a mid-flight recovery. Verified after:
  `git merge-base master HEAD` → `5452f54`, which is what the commit-count gate uses as `BASE`.
- **Why it matters downstream:** any sibling wave-1 executor spawned the same way is also sitting on
  `origin/master` and will report the plan file as missing.

### 4. [Observation] `must_haves.truths` states a stale test count

- `must_haves.truths` item 8 says the captured run "reports `8 passed`". The task-level gates and
  acceptance criteria say `3` (task 1), `7` (task 2) and `10` (task 3) — and 3 + 4 + 3 = 10.
- I followed the **gates** (10), which are the automated, enforceable statements, and did not edit
  the plan. Recording it so 01-05 does not read the `8` as a regression.

## Deferred / out of scope

- **19 pre-existing ruff findings and 9 black-unformatted files under `tests/`** (`E501` ×3,
  `RUF100` ×8, `S603` ×3, `RUF043` ×2, `N802`, `F401`, `S105`). Untouched by this plan; fixing them
  is not in R0.4's scope. Measured figures are in deviation 2 so a later phase has a baseline.
- **Five redundant inline `# noqa: S603` directives** in `tests/integration/_kitty_subprocess.py`,
  `test_client_socket_discovery.py`, `test_h21_doctor_remote_control.py`,
  `test_h21_remote_control_foundation.py`, `test_color_normalization_e2e.py` and
  `test_scene_recipe_e2e.py`. Each violates `.claude/conventions.md:20-23`. Removing them would let
  the `S603`/`S607` exception move to the shared `tests/**/*.py` glob as plan 01-01 originally
  intended. Natural owner: Phase 8 (live-doc/code hygiene), or a follow-up plan in this phase.
- **No shell linter is wired into `make validate`** (noted by `01-PATTERNS.md` invariant 9). This
  plan adds the repo's third tracked shell file, which strengthens the case; adding one is out of
  scope. `bash -n tools/hooks/pre-push` was run and passes.
- **`STATE.md` / `ROADMAP.md` were deliberately not updated.** This plan's `files_modified` does not
  include them and R0.10/D-16 give it exactly one commit whose file set 01-05 gates; the phase-end
  gate owns that bookkeeping.

## Known Stubs

None. No placeholder values, no `TODO`/`FIXME`, no skipped tests, and no `<verify>` command left
unrun. Every `<automated>` gate in the plan was executed; its verbatim result is in "Gate results".

## Threat Flags

None. The plan's `<threat_model>` covers both surfaces this plan creates (T-1-01 push-to-remote
tampering, mitigated; T-1-02 hook-executes-as-pusher elevation, accepted). No new network, auth or
session surface was introduced, and no package was installed.

## Requirements Completed

- **R0.4** — the git policy is enforced structurally rather than by acknowledgment: force-push,
  amend-after-push, direct-to-`master`, first-push-of-`master` and `master`-deletion are all
  rejected by a versioned hook, wired via one shared `core.hooksPath`, regression-tested in the
  ungated test tree, with every limit disclosed in the guard's own header.

---

## Orchestrator addendum (2026-09-23): commit topology changed to RED/GREEN after execution

This section was written by the orchestrator, not the plan's executor, after the executor had
finished. It records a change to the plan's commit rule that landed between execution and merge, and
the evidence that the change is faithful.

**What changed.** At execution time the plan required **one** commit for the whole plan, with RED and
GREEN as *recorded states* rather than commits. While the executor was running, `/gsd-config` surfaced
that `workflow.tdd_mode: true` and that rule are mutually unsatisfiable: GSD's harness gate requires a
RED commit touching `tests/` before a behavior-adding task's implementation, and this plan is
`type: tdd` with `query task.is-behavior-adding` returning true. The user's direction was that **TDD is
kept**, so R0.10 and D-16 were amended — a `type: tdd` plan now makes exactly two commits, RED then
GREEN — and this plan's gate moved from a count of 1 to a count of 2 plus a RED-before-GREEN ancestry
check.

**What was done.** The executor's single commit (`0736fea`) was split, without altering any file
content, into:

| Commit | Subject | Contents |
|--------|---------|----------|
| `178cd4b` | `test(01-01): failing pre-push guard tests before implementation (R0.4)` | `tests/unit/test_git_hooks.py` only |
| (this one) | `feat(01-01): …` | the hook, allow-list edits, `pyproject.toml`, the Makefile target, and this SUMMARY |

**Why this is a faithful RED, not a relabelled GREEN.** The split was verified by running the suite at
each commit rather than by reasoning about it:

```
# at 178cd4b (RED) — tools/hooks/pre-push does not exist
$ uv run pytest tests/unit/test_git_hooks.py -q
10 failed in 0.19s                                    (exit 1)
FileNotFoundError: [Errno 2] No such file or directory: '.../kitty-setup/tools/hooks'

# at the GREEN commit
$ uv run pytest tests/unit/test_git_hooks.py -q
10 passed
$ make test
303 passed, 70 skipped in 0.50s                       (baseline was 293 passed, 70 skipped)
```

All ten cases fail at RED for the intended reason — the directory and guard they exercise are absent —
so they test the implementation rather than themselves.

**Honest limitation.** The tests were *authored* in the same pass as the implementation; the RED state
was established by removing the implementation from the first commit, not by the executor writing tests
first and watching them fail before writing any hook. The commit topology is now correct and the RED
state is real and verified, but this pair is a reconstruction. Plan `01-02` runs under the amended rule
from the start, so its RED is genuine in authoring order as well.

**Consequence for this SUMMARY's own gate table.** The commit-count gate recorded above was evaluated
against the pre-amendment rule (`= '1'`). The current, amended gate asserts two `(01-01)`-scoped
subjects — one `test(`, one `feat(` — with RED an ancestor of GREEN. Its result is recorded in the
phase-level verification rather than here, because it can only be evaluated after the GREEN commit
exists.

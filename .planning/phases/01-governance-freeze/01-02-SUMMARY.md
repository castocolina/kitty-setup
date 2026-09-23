---
phase: 01-governance-freeze
plan: 02
subsystem: infra
tags: [git-hooks, post-checkout, post-commit, codegraph, worktree, bash, pytest, governance]

# Dependency graph
requires:
  - "01-01 — core.hooksPath wiring, the tools/hooks/ shell allow-list clause, and tests/unit/test_git_hooks.py with its _git/_sandbox/_check helpers"
provides:
  - "tools/hooks/post-checkout — first-checkout-gated, timeout-bounded `codegraph init -y` with tagged success and warning lines and no non-zero exit path"
  - "tools/hooks/post-commit — timeout-bounded incremental `codegraph sync -q` after every commit, same tagged shape, no non-zero exit path"
  - "tests/unit/test_git_hooks.py extended from 10 to 18 cases: recording / failing / sleeping codegraph shims, a minimal-PATH absence case, and argv+cwd assertions"
  - "A measured correction to 01-RESEARCH.md Pattern 3: git resolves the post-checkout hook FILE from the INVOKING worktree, not the new one — so the house REPO_ROOT `cd` idiom is a bug in these two hooks"
affects:
  - "01-03 (the `git mv openspec/` bulk rename now has a live post-commit sync to re-measure against)"
  - "01-04 (AGENTS.md carries the shell allow-list clause that already names post-commit and post-checkout)"
  - "01-05 (gates the branch diff and re-runs the per-requirement checks; three gate defects below need its attention)"

# Actuals — same estimateTokens scale (chars/4 over the realized diff), not a harness token count.
actuals:
  # chars/4 over the realized diff: test module diff 19,246 + post-checkout 4,263 +
  # post-commit 3,716 + this SUMMARY 39,235 = 66,460 chars. Not rounded toward the
  # plan's 68,000 estimate — the under-run is real and a flattering number would
  # corrupt every later projection.
  tokens: 16600
  tasks: 3
  commits: 2
plan_head_before: c352dc6fd43bfb717aaf30da0c753c8411a154dc

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "git post-checkout first-checkout detection by the (branch_flag == 1 AND prev_head == all-zero SHA) pair"
    - "advisory git hook shape: `command -v` precondition, `timeout`-bounded external call with a `command -v timeout` fallback, tagged line on BOTH the success and the warning path, single terminal `exit 0`, no `cd`"
    - "PATH-shim testing of a git hook's external call: a recording shim that logs argv AND cwd, a failing shim, a sleeping shim under a 1-second budget, and a PATH of symlinks for the genuine-absence case — all via a copied env, never os.environ"
    - "negative controls whose RED state is vacuous by construction are proven non-vacuous against a deliberately broken hook, and the measurement is recorded"

key-files:
  created:
    - tools/hooks/post-checkout
    - tools/hooks/post-commit
  modified:
    - tests/unit/test_git_hooks.py

key-decisions:
  - "Neither CodeGraph hook uses the house `REPO_ROOT` + `cd` idiom — measured: it would index/sync the WRONG tree (deviation 1)"
  - "post-commit carries the incremental refresh and post-checkout carries the first build, closing both of D-13's discretion items"
  - "The live demonstration overrode core.hooksPath per command with `git -c` rather than mutating the shared config, because the shared value is currently an absolute path into the main checkout (deviation 2)"
  - "The index-moved verdict rests on `codegraph status --json` field deltas, and the first demonstration run was thrown away and redone because its chosen file was outside the indexed language set (deviation 3)"

patterns-established:
  - "Pattern: an assertion on a hook's external call checks the EXACT argv (`init -y`, `sync -q`) and the cwd it ran in, because a correct argv in the wrong directory is still the wrong operation"
  - "Pattern: the success path is asserted to NOT contain the word `warning`, which is what makes 'the hook logs a tagged success line' a testable claim rather than a hope"

requirements-completed: [R0.6]

# Metrics
duration: 55min
completed: 2026-09-23
status: complete
---

# Phase 1 Plan 02: CodeGraph index lifecycle hooks — Summary

**`tools/hooks/post-checkout` now builds a CodeGraph index in a freshly created worktree and
`tools/hooks/post-commit` refreshes it incrementally, each bounded by an overridable `timeout`,
each logging a tagged line on both its success and its warning path, and neither able to exit
non-zero — proven by 8 new sandbox tests (module 10 → 18, suite 303 → 311) and by one live run
against the real `codegraph` 1.6.0 in which a worktree that had no `.codegraph/` at all got an
88-file / 1,191-node index and the next commit moved it to 1,192 nodes.**

## Performance

- **Duration:** ~55 min
- **Tasks:** 3 of 3
- **Files:** 3 (2 created, 1 modified) — 84 + 71 lines of new shell, +352/-6 lines of test
- **Suite:** `303 passed, 70 skipped in 0.68s` → `311 passed, 70 skipped in 2.66s`

## Setup note — the execution worktree was branched from the wrong base again

Identical to plan 01-01's deviation 3, and it is now a reproducible property of how these
worktrees are spawned rather than a one-off.

- **What I measured:** `HEAD` was `23aeaa1` (`origin/master`), which carries no `.planning/`
  tree — the plan file would have read as missing.
- **Safety before acting:** `git merge-base --is-ancestor 23aeaa1 gsd/phase-01-governance-freeze`
  → exit 0; `git rev-list --count gsd/phase-01-governance-freeze..HEAD` → `0` (my branch had no
  commits of its own); `git status --porcelain` → empty. A `git reset --hard` was therefore a
  pure fast-forward with nothing discarded.
- **After:** `git merge-base master HEAD` → `5452f54df59b65532aea89517c0b813bfd450af6`, which is
  what the commit-topology gate uses as `BASE`.

## Task outcomes

| Task | Outcome |
|------|---------|
| 1 — `post-checkout` indexes a new worktree, survives a codegraph failure | Done. 4 cases; `tools/hooks/post-checkout` (84 lines, mode 0755). Gate 1 (`14 passed`) fails for a topology reason, not a code reason — deviation 4. |
| 2 — `post-commit` refreshes incrementally and never blocks a commit | Done. 4 cases; `tools/hooks/post-commit` (71 lines, mode 0755). All four gates pass; the hang case ran (this host has `timeout`). |
| 3 — live lifecycle demonstration against the real binary | Done, on the **second** attempt; the first run's measurement did not measure the claim — deviation 3. Cleanup verified. |

## Commit topology

R0.10 as amended 2026-09-23 / D-16, TDD mode: **exactly two** commits.

1. **RED — `706a694`** `test(01-02): failing post-checkout/post-commit codegraph lifecycle tests (R0.6)`
   — `tests/unit/test_git_hooks.py` only (+352/-6). Neither hook existed at this commit
   (`ls tools/hooks/` → `pre-push` alone).
2. **GREEN — this commit** `feat(01-02): codegraph lifecycle hooks — post-checkout init, post-commit sync (R0.6)`
   — both hooks plus this SUMMARY.

The tests were **authored first, before a single byte of either hook**, and the RED state was
observed before the RED commit was made. This is not plan 01-01's reconstruction: the hook files
did not exist on disk at any point before the RED transcript below was captured.

`actuals.commits: 2` is the deterministic post-GREEN value of
`git rev-list --count c352dc6..HEAD`; measured at `1` immediately after RED, and GREEN is the
second and last commit of the plan. The same-instrument re-measurement is reported to the
orchestrator, because a count that includes this commit cannot be written inside it.

## RED and GREEN transcripts

### RED — both hooks absent, all 8 new cases present

`ls -l tools/hooks/` at this point → `755 pre-push` and nothing else.

```
$ uv run pytest tests/unit/test_git_hooks.py -k "post_checkout or post_commit" -rA --tb=no -q
F.FFFFFF                                                                 [100%]
=========================== short test summary info ============================
PASSED tests/unit/test_git_hooks.py::test_post_checkout_ignores_ordinary_branch_switch
FAILED tests/unit/test_git_hooks.py::test_post_checkout_indexes_new_worktree
FAILED tests/unit/test_git_hooks.py::test_post_checkout_codegraph_failure_leaves_worktree_intact
FAILED tests/unit/test_git_hooks.py::test_post_checkout_codegraph_absent_leaves_worktree_intact
FAILED tests/unit/test_git_hooks.py::test_post_commit_syncs_index - Assertion...
FAILED tests/unit/test_git_hooks.py::test_post_commit_codegraph_failure_does_not_block_commit
FAILED tests/unit/test_git_hooks.py::test_post_commit_codegraph_absent_does_not_block_commit
FAILED tests/unit/test_git_hooks.py::test_post_commit_codegraph_hang_does_not_block_commit
7 failed, 1 passed, 10 deselected in 0.21s

$ uv run pytest tests/unit/test_git_hooks.py --tb=no -q
7 failed, 11 passed in 0.58s
```

The RED state is established **per case**, not by a bare pytest exit status, because the 10
inherited `pre-push` cases from plan 01-01 pass throughout and a non-zero exit would prove
nothing about the new ones. Two representative failure reasons, verbatim:

```
E   AssertionError: the hook did not run `codegraph init -y`; recorded invocations were: (none at all)
E   assert 'init -y' in []
E    +  where [] = _argvs([])
tests/unit/test_git_hooks.py:439: AssertionError

E   AssertionError: no [post-checkout] line at all:
E     HEAD is now at 19a781a seed
E     Preparing worktree (new branch 'wt-codegraph')
E   assert ''
tests/unit/test_git_hooks.py:486: AssertionError
```

**One of the eight passes at RED, by construction, and that is stated rather than hidden.**
`test_post_checkout_ignores_ordinary_branch_switch` asserts that an ordinary branch switch
records **no** index build; with no hook at all, nothing is recorded, so it passes vacuously. A
negative control cannot fail in the absence of the thing it controls. Its non-vacuity — and that
of the "the success path does not warn" assertion, which is the other claim no RED can exercise —
is measured against deliberately broken hooks under "Non-vacuity measurements" below.

### Task 1 GREEN — after `tools/hooks/post-checkout`

```
$ uv run pytest tests/unit/test_git_hooks.py -k post_checkout -rA --tb=no -q
....                                                                     [100%]
PASSED tests/unit/test_git_hooks.py::test_post_checkout_indexes_new_worktree
PASSED tests/unit/test_git_hooks.py::test_post_checkout_ignores_ordinary_branch_switch
PASSED tests/unit/test_git_hooks.py::test_post_checkout_codegraph_failure_leaves_worktree_intact
PASSED tests/unit/test_git_hooks.py::test_post_checkout_codegraph_absent_leaves_worktree_intact
4 passed, 14 deselected in 0.12s

$ uv run pytest tests/unit/test_git_hooks.py --tb=no -q
..............FFFF                                                       [100%]
4 failed, 14 passed in 0.47s
```

`14 passed` is exactly the count task 1's acceptance criteria name. The four remaining failures
are task 2's cases, whose hook does not exist yet — see deviation 4 for why the task-1 gate's
`&&` cannot be green here.

### Task 2 GREEN — after `tools/hooks/post-commit`

```
$ uv run pytest tests/unit/test_git_hooks.py -k post_commit -rA --tb=no -q
....                                                                     [100%]
PASSED tests/unit/test_git_hooks.py::test_post_commit_syncs_index
PASSED tests/unit/test_git_hooks.py::test_post_commit_codegraph_failure_does_not_block_commit
PASSED tests/unit/test_git_hooks.py::test_post_commit_codegraph_absent_does_not_block_commit
PASSED tests/unit/test_git_hooks.py::test_post_commit_codegraph_hang_does_not_block_commit
4 passed, 14 deselected in 1.29s

$ uv run pytest tests/unit/test_git_hooks.py -q
..................                                                       [100%]
18 passed in 2.47s
```

The hang case **ran** rather than skipping: this host has `/usr/bin/timeout` (GNU coreutils 9.10).
Its ~1.2 s is the `KITTI_CODEGRAPH_TIMEOUT_S=1` budget expiring against a 120-second shim.

## Live lifecycle demonstration

Real `codegraph 1.6.0` at `/home/bazzite/.local/bin/codegraph`; `git 2.55.0`;
`/usr/bin/timeout` (GNU coreutils 9.10) present, so **the host took the `timeout` branch** in both
hooks and the hang mitigation was exercised rather than skipped. Transcripts also in
`tmp/h01-codegraph-lifecycle/` (gitignored: `git check-ignore -q tmp` → rc 0).

The shared `core.hooksPath` currently holds an **absolute** path into the main checkout, which does
not carry these two hooks — see deviation 2. Each demonstration command therefore overrode it with
`git -c core.hooksPath=<this worktree>/tools/hooks`, which mutates no shared state and exercises the
harder absolute-path case the hooks are explicitly designed for.

### Step 1 — `git worktree add` builds an index where there was none

```
$ ls -d <wt>/.codegraph   (before: the path does not even exist)
ls: cannot access '.../tmp/kitty-setup-h01/.codegraph': No such file or directory

$ git -c core.hooksPath=<this worktree>/tools/hooks worktree add <wt> -b h01/codegraph-lifecycle
Preparing worktree (new branch 'h01/codegraph-lifecycle')
HEAD is now at 706a694 test(01-02): failing post-checkout/post-commit codegraph lifecycle tests (R0.6)
[post-checkout] CodeGraph index built for this new worktree
rc=0
TIMING LABEL 'total worktree-add wall-clock' = .862519845s  (git checkout + post-checkout + codegraph init -y)

$ ls -la <wt>/.codegraph
total 3484
drwxr-xr-x. 1 bazzite bazzite      44 Sep 23 13:14 .
drwxr-xr-x. 1 bazzite bazzite     294 Sep 23 13:14 ..
-rw-r--r--. 1 bazzite bazzite 3563520 Sep 23 13:14 codegraph.db
-rw-r--r--. 1 bazzite bazzite     229 Sep 23 13:14 .gitignore
```

The `[post-checkout]` **success** tag is present in the captured output, which is only possible
because the hook logs one — the whole point of the round-1 finding that the previous draft
demanded a tag from a hook that emitted nothing.

### Step 2 — a commit refreshes it, and the index demonstrably moved

```
$ codegraph status --json   (BEFORE)
{"initialized":true,"version":"1.6.0","projectPath":".../tmp/kitty-setup-h01",
 "indexPath":".../tmp/kitty-setup-h01/.codegraph","lastIndexed":"2026-09-23T16:14:38.576Z",
 "fileCount":88,"nodeCount":1191,"edgeCount":2957,"dbSizeBytes":3563520,"walSizeBytes":0,
 "backend":"node-sqlite","journalMode":"wal",
 "nodesByKind":{"class":21,"file":66,"function":607,"import":342,"method":25,"variable":130},
 "languages":["python","yaml"],"pendingChanges":{"added":0,"modified":0,"removed":0},
 "worktreeMismatch":null,
 "index":{"builtWithVersion":"1.6.0","builtWithExtractionVersion":25,
          "currentExtractionVersion":25,"reindexRecommended":false,"state":"complete","pendingRefs":0}}

$ git diff --stat
 src/kitty_setup/cli.py | 4 ++++
 1 file changed, 4 insertions(+)

$ git -c core.hooksPath=<...>/tools/hooks commit -m 'probe: add one function so the index has something to move'
[post-commit] CodeGraph index synchronised for this worktree
[h01/codegraph-lifecycle 560800e] probe: add one function so the index has something to move
 1 file changed, 4 insertions(+)
rc=0
TIMING LABEL 'total commit wall-clock' = .204873292s   (git + object creation + EVERY hook + the sync)

$ codegraph status --json   (AFTER)
{... "lastIndexed":"2026-09-23T16:14:39.433Z","fileCount":88,"nodeCount":1192,"edgeCount":2958,
 "dbSizeBytes":3563520, "nodesByKind":{"class":21,"file":66,"function":608,"import":342,
 "method":25,"variable":130}, ...}
```

Field-by-field comparison of the two captures:

```
  lastIndexed    before='2026-09-23T16:14:38.576Z'   after='2026-09-23T16:14:39.433Z'   MOVED
  fileCount      before=88                           after=88                           same
  nodeCount      before=1191                         after=1192                         MOVED
  edgeCount      before=2957                         after=2958                         MOVED
  dbSizeBytes    before=3563520                      after=3563520                      same
  nodesByKind.function before=607 after=608

VERDICT: the index moved
fields that changed: ['lastIndexed', 'nodeCount', 'edgeCount']

$ diff step2-status-before.json step2-status-after.json
diff_rc=1  (1 = the two captures differ)
```

**A machine-readable form does exist and was used:** `codegraph status --help` documents
`-j, --json`, so the verdict rests on parsed field deltas rather than on eyeballing prose. The
verdict is `lastIndexed` advancing by 0.857 s together with `nodeCount` 1191 → 1192,
`edgeCount` 2957 → 2958 and `nodesByKind.function` 607 → 608 — exactly the one function the
probe commit added. **No claim is made that `codegraph status` named the changed file**: it does
not report filenames in either form, only aggregate counts, freshness and a `pendingChanges`
roll-up.

The refresh was a `sync`, not a full rebuild: `fileCount` and `dbSizeBytes` are unchanged while
`lastIndexed` advanced by under a second on an 88-file tree, and the hook's own gate
(`! rg -q 'codegraph index' tools/hooks/post-commit` → rc 0) proves the whole-repo rebuild
subcommand is not in the commit path at all.

### Step 3 — two timings, two labels

```
  total commit wall-clock  = .204873292s   (git + object creation + every hook + the sync)
  codegraph sync -q alone  = .206614653s   (the sync and nothing else, timed directly after a
                                            second one-line change so it was not a no-op)
```

These are two separate measurements of two different things and neither is presented as the
other. The near-identical magnitudes are not a coincidence to hide: on this 88-file tree the
sync dominates the commit almost entirely, git's own share being sub-10 ms. The
`total worktree-add wall-clock` of **0.863 s** in step 1 is a third, separately labelled number
(checkout + `codegraph init -y`, i.e. a full build rather than a sync) — comfortably inside the
60-second `KITTI_CODEGRAPH_TIMEOUT_S` default, with ~70x headroom.

### Step 4 — cleanup

```
$ git worktree remove --force <wt>
rc=0
$ git branch -D h01/codegraph-lifecycle
Deleted branch h01/codegraph-lifecycle (was 560800e).
rc=0
$ WORKTREES="$(git worktree list)" && ! printf '%s\n' "$WORKTREES" | rg -q 'kitty-setup-h01'
rc=0
/var/home/bazzite/git/personal/kitty-setup                                           c352dc6 [gsd/phase-01-governance-freeze]
/var/home/bazzite/git/personal/kitty-setup/.claude/worktrees/agent-a6b46270a8eba496c 706a694 [worktree-agent-a6b46270a8eba496c] locked
$ BRANCHES="$(git branch --list 'h01/codegraph-lifecycle')" && test -z "$BRANCHES"
rc=0
$ git status --porcelain
?? tools/hooks/post-checkout
?? tools/hooks/post-commit
```

Both scratch artifacts are gone: no `kitty-setup-h01` worktree and no `h01/*` branch. The two
untracked entries are this plan's own hooks, staged into the GREEN commit.

## Non-vacuity measurements

A control that cannot fail proves nothing. Two claims in this plan are unreachable by any RED
state — one because it is a negative control, one because it asserts something about a success
path that does not exist yet — so both were measured against a deliberately broken hook.

### Control 1 — the first-checkout marker

The all-zero prev-HEAD condition was removed from the gate, so **any** branch checkout would
index:

```
# patched: `if [[ "${branch_flag}" != "1" || "${prev_head}" != "${ZERO_SHA}" ]]; then`
#       -> `if [[ "${branch_flag}" != "1" ]]; then`
$ uv run pytest tests/unit/test_git_hooks.py -k post_checkout -rA --tb=short -q
.F..                                                                     [100%]
______________ test_post_checkout_ignores_ordinary_branch_switch _______________
tests/unit/test_git_hooks.py:471: in test_post_checkout_ignores_ordinary_branch_switch
    assert not initialised, "an ordinary branch switch triggered an index build: " f"{initialised}"
E   AssertionError: an ordinary branch switch triggered an index build: ['init -y', 'init -y']
E   assert not ['init -y', 'init -y']
1 failed, 3 passed, 14 deselected in 0.30s
```

Two recorded `init -y` invocations — one per `git checkout` — and the other three cases stay
green, which is exactly the contrast a control exists to produce. Hook restored; module
re-verified at `18 passed`.

### Control 2 — "the success path does not warn"

The success branch of `post-commit` was made to print a warning:

```
# patched: log "CodeGraph index synchronised..."  ->  log "warning: CodeGraph index synchronised..."
$ uv run pytest tests/unit/test_git_hooks.py -k post_commit_syncs -rA --tb=line -q
    assert 'warning' not in '[post-commi...his worktree'
      'warning' is contained here:
        [post-commit] warning: CodeGraph index synchronised for this worktree
      ?               +++++++
tests/unit/test_git_hooks.py:554: AssertionError: the success path warned:
1 failed, 17 deselected in 0.07s
```

Hook restored; module re-verified at `18 passed`.

## Gate results

Every `<automated>` gate in the plan, run verbatim with the XML unescaped.

### Task 1

| # | Command | Result |
|---|---------|--------|
| 1 | `OUT="$(uv run pytest tests/unit/test_git_hooks.py -q 2>&1)" && printf '%s\n' "$OUT" \| rg -q '(^\|[^0-9])14 passed'` | **FAIL — gate defect, deviation 4.** `14 passed` was reached and is recorded above; the `&&` cannot be satisfied at this point under the two-commit topology |
| 2 | `test -x tools/hooks/post-checkout` | PASS |
| 3 | `test -f tools/hooks/post-checkout && ! rg -q 'exit 1' tools/hooks/post-checkout` | PASS |
| 4 | `rg -q 'codegraph init -y' tools/hooks/post-checkout && rg -q 'KITTI_CODEGRAPH_TIMEOUT_S' tools/hooks/post-checkout` | PASS |

### Task 2

| # | Command | Result |
|---|---------|--------|
| 1 | `OUT="$(uv run pytest tests/unit/test_git_hooks.py -q 2>&1)" && printf '%s\n' "$OUT" \| rg -q '(^\|[^0-9])18 passed'` | PASS (rc 0) |
| 2 | `rg -q 'codegraph sync -q' tools/hooks/post-commit && rg -q 'KITTI_CODEGRAPH_TIMEOUT_S' tools/hooks/post-commit` | PASS |
| 3 | `test -f tools/hooks/post-commit && ! rg -q 'exit 1' tools/hooks/post-commit` | PASS |
| 4 | `test -f tools/hooks/post-commit && ! rg -q 'codegraph index' tools/hooks/post-commit` | PASS |

### Task 3

| # | Command | Result |
|---|---------|--------|
| 1 | `OUT="$(uv run pytest … -q 2>&1)" && printf … \| rg -q '(^\|[^0-9])18 passed'` | PASS (rc 0) |
| 2 | `WORKTREES="$(git worktree list)" && ! printf '%s\n' "$WORKTREES" \| rg -q 'kitty-setup-h01'` | PASS (rc 0) |
| 3 | `BRANCHES="$(git branch --list 'h01/codegraph-lifecycle')" && test -z "$BRANCHES"` | PASS (rc 0) |
| 4 | `git check-ignore -q .codegraph` | **FAIL — gate defect, deviation 5.** rc 1 here; the underlying fact is true and proven three other ways |
| 5 | `BASE="$(git merge-base master HEAD)" && test "$(git log --format=%s "$BASE"..HEAD \| rg -c '\(01-02\)')" = '2' && … && git merge-base --is-ancestor "$RED" "$GREEN"` | Evaluated **after** the GREEN commit; cannot be recorded inside it. Reported to the orchestrator |
| 6 | `SHOWN="$(git show --stat --oneline HEAD)" && printf '%s\n' "$SHOWN" \| rg -q '01-02-SUMMARY\.md'` | Same — post-GREEN. This file is staged into the GREEN commit, which is what the gate asks |

### Plan-level `<verification>`

| # | Command | Result |
|---|---------|--------|
| 1 | `OUT="$(uv run pytest tests/unit/test_git_hooks.py -q 2>&1)" && … rg -q '(^\|[^0-9])18 passed'` | PASS (rc 0) — `18 passed in 2.47s` |
| 2 | `for f in tools/hooks/post-checkout tools/hooks/post-commit; do test -f "$f" && ! rg -q 'exit 1' "$f" \|\| exit 1; done` | PASS (rc 0) |
| 3 | `make test` | PASS — `311 passed, 70 skipped in 2.66s` |
| 4 | `uv run ruff check tests && uv run black --check tests` | **FAIL — pre-existing, identical to 01-01 deviation 2.** Baseline held exactly: `Found 19 errors`, `9 files would be reformatted, 36 files would be left unchanged`. Scoped to this plan's file: `uv run ruff check tests/unit/test_git_hooks.py && uv run black --check tests/unit/test_git_hooks.py` → rc 0, `All checks passed!` |
| 5 | `rg -q 'KITTI_CODEGRAPH_TIMEOUT_S' tools/hooks/post-checkout && rg -q 'KITTI_CODEGRAPH_TIMEOUT_S' tools/hooks/post-commit` | PASS (rc 0) |

Structural checks beyond the plan's list, recorded because the acceptance criteria name them:

```
$ head -1 tools/hooks/post-checkout ; head -1 tools/hooks/post-commit
#!/usr/bin/env bash
#!/usr/bin/env bash
$ tail -1 tools/hooks/post-checkout ; tail -1 tools/hooks/post-commit
exit 0
exit 0
$ stat -c '%a %n' tools/hooks/post-checkout tools/hooks/post-commit
755 tools/hooks/post-checkout
755 tools/hooks/post-commit
$ bash -n tools/hooks/post-checkout && bash -n tools/hooks/post-commit
(clean)
$ rg -n 'command -v timeout' tools/hooks/post-checkout tools/hooks/post-commit
tools/hooks/post-commit:56:if command -v timeout >/dev/null 2>&1; then
tools/hooks/post-checkout:67:if command -v timeout >/dev/null 2>&1; then
$ rg -c '0000000000000000000000000000000000000000' tools/hooks/post-checkout
1
```

## Deviations from Plan

### 1. [Rule 1 — Bug] The house `REPO_ROOT` + `cd` idiom the plan prescribes would make both hooks operate on the WRONG tree

- **Found during:** Task 1, before writing the hook, from a throwaway research probe.
- **What the plan said:** task 1's `<action>` requires the prelude to include
  `REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"` and `cd "${REPO_ROOT}"`
  (plan 01-01's shape), *and*, two clauses later, records "the fact that git sets cwd to the
  checked-out worktree's root before invoking it". Those two statements are mutually exclusive.
- **What I measured** (disposable repo, `core.hooksPath=tools/hooks`, git 2.55.0):

  ```
  $ git worktree add ../wt -b wt-branch
  Preparing worktree (new branch 'wt-branch')
  PROBE-CHECKOUT args=[0000000000000000000000000000000000000000 13a70c2… 1]
                 cwd=/…/probe1/wt
                 src=/…/probe1/clone/tools/hooks/post-checkout
  ```

  git set cwd to the **new** worktree but resolved the hook **file** from the **invoking**
  worktree. So `dirname "${BASH_SOURCE[0]}"/../..` is the *old* repo root, and `cd`-ing there
  would have run `codegraph init -y` against the already-indexed original tree while leaving the
  new worktree with no index at all — the exact behaviour R0.6 exists to deliver, silently
  inverted. With an absolute `core.hooksPath` (this repo's current state, deviation 2) the same
  `cd` misdirects **every** invocation of **both** hooks, not just worktree creation.

  This also corrects `01-RESEARCH.md` Pattern 3, which reasons that the hook works because
  "`tools/hooks/post-checkout` is already present in the new worktree" before the hook runs.
  The hook's presence in the new worktree is irrelevant: resolution never looks there. The probe
  confirms the hook fires even when the new worktree contains no `tools/hooks/` at all.
- **What I did:** neither hook contains a `cd` or a `REPO_ROOT`. Both stay in the directory git
  hands them, and each carries a `CWD IS LOAD-BEARING` header block recording the measurement
  and an explicit "Do not add a `cd`."
- **How it is now tested rather than trusted:** `test_post_checkout_indexes_new_worktree` and
  `test_post_commit_syncs_index` assert the recorded **cwd** of the `codegraph` call, not only its
  argv — `_cwds_for(rows, "init -y") == [worktree.resolve()]`. A correct argv in the wrong
  directory is still the wrong operation, and before this deviation nothing in the plan would
  have caught it.
- **Consequence for the plan's `_minimal_path` helper:** it symlinks `dirname` because the
  `REPO_ROOT` idiom calls it. The hooks no longer do, so `dirname` is now unnecessary. The
  symlink is kept anyway, with a comment saying so, because the helper is shared and a future
  hook may reintroduce the idiom legitimately.

### 2. [Environment drift, worked around without mutating shared state] `core.hooksPath` is an absolute path into the main checkout

- **Found during:** Task 3 setup.
- **What plan 01-01 recorded:** `git config --get core.hooksPath` → `tools/hooks` (relative),
  from `file:<repo>/.git/config`, which is what makes it resolve per worktree.
- **What I measured today:**

  ```
  $ git config --show-origin --get core.hooksPath
  file:/var/home/bazzite/git/personal/kitty-setup/.git/config	/var/home/bazzite/git/personal/kitty-setup/tools/hooks
  ```

  An **absolute** path, in the shared config, pointing at the main checkout — whose working tree
  is at `c352dc6` and therefore carries `pre-push` only. Consequences, both real: no worktree
  agent's commits run `post-commit`, and `git worktree add` from any worktree would find no
  `post-checkout`. It also defeats the per-worktree resolution that D-13 and 01-RESEARCH Pattern 1
  rely on. I did not establish who set it; it was not this plan, and `make -n hooks` still prints
  the relative form.
- **What I did:** **not** rewrite the shared config. Changing `core.hooksPath` would alter the
  user's main checkout and every sibling worktree mid-flight, for every concurrent agent — a
  side effect far outside this plan's file set. Instead each demonstration command passed
  `git -c core.hooksPath=<this worktree>/tools/hooks`, which is process-local. That is strictly
  the harder case: it is an absolute path, so it is exactly the configuration in which
  deviation 1's `cd` bug would have bitten, and the hooks are demonstrated surviving it.
- **What still needs an owner:** restoring `core.hooksPath` to the relative `tools/hooks`
  (i.e. running `make hooks`) so the hooks fire for ordinary work. Flagged for **01-05**, which
  owns the phase-end gate, rather than silently done here. Until then the two new hooks are
  tracked, tested and demonstrated but not *active* for day-to-day commits in this repo.

### 3. [Rule 1 — Bug in my own measurement] The first live demonstration run did not measure the claim; it was thrown away and redone

- **Found during:** Task 3, immediately after run 1.
- **What happened:** run 1 followed the plan's letter — "make a one-line change to a tracked
  file" — and changed `README.md`. Both hooks fired with their success tags, but the before/after
  `codegraph status --json` captures were **byte-identical**, `diff` exit 0, `lastIndexed`
  unmoved. `codegraph sync -q` still exited 0.
- **Why:** `codegraph status --json` reports `"languages":["python","yaml"]`. Markdown is not
  indexed at all, so a README change is genuinely nothing for `sync` to do. Reporting that run as
  "the index moved" would have been false; reporting it as "the hook is broken" would have been
  equally false.
- **What I did:** discarded run 1, and re-ran the whole demonstration with a change the index
  actually covers — one new module-level function in the tracked `src/kitty_setup/cli.py` — which
  produced the unambiguous `nodeCount` 1191 → 1192 / `function` 607 → 608 delta recorded above. I
  also added a second one-line change before timing `codegraph sync -q` alone, so that number is
  the cost of real work rather than of a no-op.
- **Worth keeping:** the run-1 finding is a real property of this toolchain — a commit touching
  only Markdown leaves the index untouched and the hook still correctly reports success. Any
  later plan that tries to prove "the index moved" by editing a doc will get a false negative.
  Plan **01-03** is the immediate consumer: its `git mv openspec/` bulk rename moves mostly
  Markdown, so a before/after `codegraph status` there may legitimately show little movement.

### 4. [Gate defect] Task 1's `14 passed` gate cannot pass under the two-commit topology it ships with

- **The gate:** `OUT="$(uv run pytest tests/unit/test_git_hooks.py -q 2>&1)" && printf '%s\n' "$OUT" | rg -q '(^|[^0-9])14 passed'`.
- **What I measured:** at the end of task 1, `14 passed` — exactly the count the criteria name —
  **and** four failures, so pytest exits 1 and the `&&` short-circuits before the grep:

  ```
  $ uv run pytest tests/unit/test_git_hooks.py --tb=no -q
  ..............FFFF                                                       [100%]
  4 failed, 14 passed in 0.47s
  $ echo "pytest_rc=$?"
  pytest_rc=1
  ```
- **Why it is structural, not my error:** the amended R0.10 requires **exactly two** commits, the
  first containing *only* the new test cases. All eight new tests must therefore exist before
  either hook does. Task 2's four cases are present during task 1 by construction, and their hook
  is not. A clean `14 passed` could only exist if task 2's tests were written after task 1's hook,
  which would need a second `test(` commit and break the topology gate. The gate was written for
  the superseded one-commit rule, where RED/GREEN were merely recorded states.
- **What I did instead:** did **not** rewrite or skip the gate, and did not reorder the tests to
  manufacture a green. I recorded both halves of what the gate is really asking:
  `uv run pytest … -k post_checkout` → `4 passed, 14 deselected` (task 1's cases all green) and
  the module's `4 failed, 14 passed` (the count matches; the failures are task 2's). The plan's
  own end-state gate, `18 passed`, passes with rc 0.
- **Recommendation for 01-05:** for a `type: tdd` plan, an intermediate per-task passed-count gate
  should scope to that task's cases (`-k`) or drop the `&&` and assert the count alone. As written
  it is the same unsatisfiable-gate class the five review rounds found repeatedly.

### 5. [Gate defect] `git check-ignore -q .codegraph` is existence-dependent and fails in a worktree that has no index yet

- **The gate:** `git check-ignore -q .codegraph`.
- **What I measured:**

  ```
  $ rg -n 'codegraph' .gitignore
  70:.codegraph/
  $ ls -d .codegraph
  ls: cannot access '.codegraph': No such file or directory
  $ git check-ignore -q .codegraph          # the gate, verbatim
  rc=1
  $ git check-ignore -q .codegraph/         # same question, asked as a directory
  rc=0
  $ git check-ignore -v .codegraph/
  .gitignore:70:.codegraph/	.codegraph/
  $ mkdir .codegraph && git check-ignore -v .codegraph
  .gitignore:70:.codegraph/	.codegraph
  rc=0                                       # the verbatim gate, now green
  $ git -C <main checkout> check-ignore -v .codegraph
  .gitignore:70:.codegraph/	.codegraph
  rc=0
  ```
- **Why:** the pattern `.codegraph/` has a trailing slash, so it matches directories only. Given a
  bare pathname that does not exist on disk, git cannot know it is a directory and reports no
  match. The gate therefore fails in exactly the situation this plan creates — a fresh worktree
  with no index yet — and passes only where an index already exists.
- **What I did instead:** did **not** rewrite the gate or edit `.gitignore`. I measured the fact
  the gate exists to assert, three existence-independent ways: the directory form
  (`check-ignore -q .codegraph/` → rc 0, pattern `.gitignore:70`), the verbatim form with the
  directory materialised (rc 0, then removed again), and the main checkout where it genuinely
  exists (rc 0). Additionally the live demonstration created a real 3.5 MB `.codegraph/` in a
  worktree and `git status --porcelain` never listed it. The index cannot be committed by
  accident.
- **Recommendation for 01-05:** use `git check-ignore -q .codegraph/` — one character, and it
  stops depending on machine-local state.

### 6. [Transparency] The RED commit was made with hooks disabled, and nothing was bypassed by it

Recorded because it would otherwise look like a hook bypass. The RED commit
(`706a694`) was created with `git -c core.hooksPath=/nonexistent-no-hooks commit`, for
determinism. At that moment no `post-commit` hook existed at *either* candidate path — not in this
worktree (it was written after the RED commit) and not at the shared absolute `core.hooksPath`
(deviation 2) — so the override suppressed nothing. The GREEN commit was made with the same
process-local override for the identical reason: at commit time `core.hooksPath` still points at
the main checkout, so the repo's own `post-commit` would not run either way, and the hook's real
behaviour on a real commit is already demonstrated live in step 2 above. `pre-push` was never
touched; no push occurred.

## Deferred / out of scope

- **`core.hooksPath` is an absolute path into the main checkout** (deviation 2). Restoring the
  relative form via `make hooks` belongs to whoever owns shared repo state — flagged for 01-05.
  Until then both new hooks are inert for ordinary commits in this repo.
- **19 pre-existing ruff findings and 9 black-unformatted files under `tests/`** — the same
  baseline 01-01 measured and held. This plan modified no pre-existing test file and its own
  module is clean under both tools.
- **No shell linter is wired into `make validate`** (01-PATTERNS invariant 9). This plan adds the
  repo's 4th and 5th tracked shell files, strengthening the case further. `bash -n` was run on
  both and passes. Out of scope.
- **`STATE.md` / `ROADMAP.md` / `REQUIREMENTS.md` deliberately not updated** — this plan's
  `files_modified` does not include them and the two-commit rule fixes the file set that 01-05
  gates. Same choice as 01-01; the phase-end gate owns that bookkeeping.
- **The 60-second `KITTI_CODEGRAPH_TIMEOUT_S` default is still unvalidated on a large repo.** The
  plan defers this. New data point: a **full** `codegraph init -y` on this 88-file tree costs
  ~0.86 s wall-clock including the checkout, so the default carries ~70x headroom for the
  expensive operation, not just for `sync`.
- **A no-`timeout` host (default macOS) still has an unbounded hang path** — accepted residual
  risk per T-1-04. Not applicable here: this host has GNU coreutils `timeout` and the hang case
  ran rather than skipping.

## Known Stubs

None. No placeholder values, no `TODO`/`FIXME`, no skipped tests (`make test` →
`311 passed, 70 skipped`, and all 70 skips are the pre-existing `tests/integration/`
`KITTI_INTEGRATION=1` gate, none of them this plan's), and no `<verify>` command left unrun.
Every `<automated>` gate in the plan was executed and its verbatim result is in "Gate results" —
including the three that failed, each with the measurement that shows why.

## Threat Flags

None. The plan's `<threat_model>` covers both surfaces this plan creates: T-1-02
(hooks execute unsandboxed as the invoking user, accepted — both hooks are thin, one guarded
external call each) and T-1-04 (an absent, failing or hanging `codegraph`, mitigated on all three
shapes, each with a passing test). No network, auth or session surface was introduced and no
package was installed. The threat register's `mitigate` disposition for T-1-04 is now backed by
mechanism in both hooks, not just the tested one: plan-level verification item 5 checks
`KITTI_CODEGRAPH_TIMEOUT_S` in `post-checkout` **and** `post-commit`.

## Requirements Completed

- **R0.6** — the CodeGraph index lifecycle is automated rather than remembered, and demonstrated
  rather than asserted: a new worktree gets an index from `post-checkout` (`codegraph init -y`,
  exact argv asserted, in the new worktree's own directory, cwd asserted), every commit refreshes
  it incrementally from `post-commit` (`codegraph sync -q`, exact argv asserted, full rebuild
  proven absent), an ordinary branch switch does neither, and an absent, failing or hanging
  `codegraph` produces a tagged warning while leaving both the commit and the worktree fully
  intact — eight passing tests in the ungated tree plus one live run against the real binary in
  which the index measurably moved.

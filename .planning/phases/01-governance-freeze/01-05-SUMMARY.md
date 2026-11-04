---
phase: 01-governance-freeze
plan: 05
subsystem: governance
tags: [governance, git-policy, agents-md, validation-map, quality-baseline]
status: complete
requires:
  - "01-04: AGENTS.md exists as the canonical instruction file"
  - "01-01: tools/hooks/pre-push + Makefile hooks: target"
  - "01-02: tools/hooks/post-commit, tools/hooks/post-checkout"
  - "01-03: .planning/legacy/openspec/ relocation + FROZEN banners"
provides:
  - "AGENTS.md validated by the agent-md-refactor skill, with every finding triaged"
  - "One git policy stated identically in AGENTS.md, ROADMAP step 6 and PROJECT.md (both places PROJECT.md states one)"
  - "A fully resolved 23-row per-requirement verification map"
  - "core.hooksPath restored to its relative form, with per-worktree resolution proven live"
  - "The phase's Universal Phase Gate evidence, captured rather than claimed"
affects:
  - "Phase 2 / R1.1 — owns turning make doctor green, which unblocks Phase 1's deferred merge"
  - "Phase 8 / R6.1 — proposed owner of the conventions-vs-Makefile target mismatch and of the deferred AGENTS.md refactor findings"
  - "Phase 8.5 / R0.12 — owns tests/ type-check + lint cleanliness"
tech-stack:
  added: []
  patterns:
    - "Relative core.hooksPath so hooks resolve against each worktree's own root"
    - "Explicit Mapping parameter instead of **kwargs when a bool keyword-only param shares the signature"
key-files:
  created:
    - .planning/phases/01-governance-freeze/01-05-SUMMARY.md
  modified:
    - AGENTS.md
    - .planning/ROADMAP.md
    - .planning/PROJECT.md
    - .planning/phases/01-governance-freeze/01-VALIDATION.md
    - tests/unit/test_git_hooks.py
decisions:
  - "Phase 1 does not merge to master. make doctor is red on this host (exit 2, one FAIL, which is R1.1 by name), so the merge is deferred until Phase 2 turns it green rather than the precondition being narrowed or an exemption written."
  - "No carve-out marker was written into any of the three policy documents, and the marker string earlier drafts named is deliberately not reproduced anywhere in this SUMMARY either, so a repo-wide grep for it stays a true absence check."
  - "core.hooksPath restored repo-wide from its absolute value to the relative tools/hooks, because an absolute value silently prevents every worktree's commits from running post-commit at all."
  - "The three 01-01 pytest map rows were rescoped with -k to their own cases: their cumulative wave-1 counts (3/7/10) cannot hold at wave 5, where the module reports 18 passed."
  - "The five new pyright errors in tests/unit/test_git_hooks.py were fixed rather than deferred, because a phase that adds a file owns that file being clean (ROADMAP step 5 clause 3) and leaving them grew the recorded baseline from 571 to 576."
metrics:
  duration: "~80 min"
  completed: "2026-09-23"
plan_head_before: 27a152a2d4a5a322e71bbd549da745c8c5808035
actuals:
  tokens: 21000
  tasks: 3
  commits: 1
---

# Phase 1 Plan 05: Close the Governance Phase Summary

Ran `AGENTS.md` through the skill that owns its shape and triaged all nine findings, removed
the last two places the planning docs still stated the superseded git policy, restored
`core.hooksPath` to the relative form that actually resolves per worktree, and resolved every
one of the 23 per-requirement verification-map rows from a real command — in one commit.

---

## Step 1 — The immutable phase-base SHA

```
$ git merge-base master HEAD
5452f54df59b65532aea89517c0b813bfd450af6
```

**`BASE` = `5452f54df59b65532aea89517c0b813bfd450af6`** (short `5452f54`), exactly the SHA the
plan expected. Every phase-scope diff below names this literal SHA rather than a recomputed
merge-base, so the checks stay reproducible after the phase gate's eventual merge — at which
point a recomputed range would go empty and the scope gate would become vacuous regardless of
what the phase changed.

---

## Task 1 — `agent-md-refactor` validation of `AGENTS.md`

The skill was invoked through the Skill tool (it is a global Claude Code skill). Nothing was
installed or vendored: `test ! -d .claude/skills` → exit 0, and this repo still has no
project-local skills directory. `crafting-effective-readmes` was **not** invoked and
`README.md` was **not** edited by this task.

The pass ran all five of the skill's phases. Every finding is below, in exactly one bucket.

### Applied (3)

| # | Finding | Skill phase | Edit |
|---|---------|-------------|------|
| A1 | **The preamble contradicted the `## Stack` section.** The opening paragraph said "Project identity, structure, and **stack** live in `README.md` and the swappable convention files below — never duplicated here", while the file itself carries a `## Stack` section stating the shell allow-list. A reader following the preamble would conclude the Stack section does not belong. | 1 (contradictions) | Preamble now separates the two: identity/structure → `README.md`, stack and tooling **conventions** → `.claude/conventions.md`, and what this file states about the stack is the **allow-list** — "a rule about what may exist in the repo, not a tooling convention". |
| A2 | **Two rules gave different thresholds for the same two commands without saying how they relate.** The git-policy bullet requires `make doctor` + `make test` **green** to merge; "Verify before declaring done" says "both commands, **captured rather than green**". Read alone, the second licenses ignoring the first. | 1 (contradictions) | "Verify before declaring done" now states the relation explicitly: capturing is the evidence duty, the merge precondition additionally requires green, "so a captured-but-red run satisfies this rule and still blocks the merge". |
| A3 | **"Skill outputs land on disk" listed `.planning/` and `docs/` only**, while the mantra rule two bullets above mandates experiment evidence under `tmp/h<NN>-<slug>/` — a location the placement rule appeared to disallow. | 1 (contradictions) | The bullet now names the `tmp/h<NN>-<slug>/` hypothesis dir alongside `.planning/` and `docs/`, pointing back at the mantra rule that requires it. |

### Deferred (4) — real, outside Phase 1's scope

| # | Finding | Skill phase | Owner |
|---|---------|-------------|-------|
| D1 | **Root file exceeds the skill's 50-line target** (111 lines; the skill's verification step asks for "under 50 lines, only universal info") and should be split into linked files under `.claude/`. | 2-4 | **Phase 8 / R6.1** — deferred by **D-09** (surgical edit, not a restructure, because Phase 8 edits this same file) and **D-11** (findings outside Phase 1's scope become deferred ideas, not edits). This is the predictable progressive-disclosure finding the plan named in advance. |
| D2 | **The git-policy bullet is 16 lines**, including the seven-item disclosure block; the skill would move that detail into a linked `git-workflow.md`. | 3-4 | **Phase 8 / R6.1.** Constraint to carry forward: **R0.4**'s disclosure duty means all seven limits must stay reachable from wherever the rule lives — a split may relocate them but not drop them. |
| D3 | **The `## Stack` paragraph is a 16-line prose block** the skill would reformat into a bulleted allow-list; it also carries an awkward self-reference ("a hook that outgrows `tools/uninstall.sh`'s dispatcher"). | 3-5 | **Phase 8 / R6.1** — `01-CONTEXT.md:139` already defers "`CLAUDE.md` Stack-section inaccuracies beyond D-08's hook line" to Phase 8 / R6.1, and that deferral now reads onto `AGENTS.md`'s inherited Stack section. See Deviations §D3 — a cross-AI partial had edited this and it was deliberately dropped. |
| D4 | **`.claude/conventions.md` is the only linked instruction file**; the skill's Phase 3 asks for 3-8 self-contained topic files. | 3 | **Phase 8 / R6.1**, as the same restructure as D1. |

### Rejected (2) — conflicts with a locked decision

| # | Finding | Conflicts with | Reasoning |
|---|---------|----------------|-----------|
| R1 | Move the `## Stack` allow-list's content into `.claude/conventions.md`, since the preamble already routes stack matters there. | **D-15** | D-15 keeps stack **conventions** in `.claude/conventions.md` and the **allow-list** in the instruction file. The allow-list is a rule about what may exist in the repo — a governance constraint an agent must obey — not a tooling convention that swaps out with the language. Applied finding A1 resolves the preamble's imprecision instead, which is the actual defect. |
| R2 | Adopt the skill's root-file template, which replaces prose sections with a "Quick Reference" command block plus a links list — dropping "Authoritative sources". | **D-09** (and **R0.3**) | R0.3 *requires* the authoritative-sources list pointing at `.planning/`, and plan 01-04 delivered it; D-09 forbids a restructure here. Following the template literally would delete content this phase exists to install. |

### Flagged for deletion (0)

The skill's Phase 5 looks for redundant, vague, obvious, default-behaviour or outdated
instructions. **None was found.** Every bullet in `## Universal rules` is a genuine override of
default agent behaviour (`English everywhere`, `Questions are not orders`, `Re-read before
edit`, the mantra) rather than a restatement of it, and there is no "write clean code"-class
instruction anywhere in the file. Recorded as an explicit nil finding rather than omitted.

### Link integrity (skill Phase 4 verification)

All **10** markdown link targets resolve, and all **6** additional inline code paths exist:

```
OK .claude/conventions.md   OK docs/agent-iteration.md      OK docs/propossal_roadmap.md
OK docs/requirements.md     OK .planning/legacy/openspec/   OK .planning/phases/
OK .planning/PROJECT.md     OK .planning/REQUIREMENTS.md    OK .planning/ROADMAP.md
OK .planning/STATE.md
OK tools/setup.sh  OK tools/uninstall.sh  OK src/kitty_setup/cli.py
OK README.md       OK .planning/config.json  OK tools/hooks/pre-push
```

No broken internal link — so no Applied finding was due on that axis.

### Task 1 gates — every `AGENTS.md` content check from plan 01-04, re-run after the edits

| Gate | Command | Result |
|------|---------|--------|
| No project-local skills dir | `test ! -d .claude/skills` | **exit 0** |
| This task does not touch README | `test -z "$(git diff --numstat HEAD -- README.md)"` | **exit 0** (empty) |
| README whole-branch diff is exactly two hunks | `git diff -U0 5452f54..HEAD -- README.md \| rg -c '^@@'` | **`2`** |
| …and both sanctioned edits present | same diff `\| rg -c '^\+.*(AGENTS\.md\|tools/hooks)'` | **`2`** (`tools/hooks` allow-list sentence; `├── AGENTS.md` tree entry) |
| Five rule greps + exactly-one commit-granularity line | `rg -ni 'research.*experiment.*decide' && test "$(rg -ci 'one commit per plan' AGENTS.md)" = '1' && rg -q 'cross_ai: true' && rg -q 'codegraph_explore' && rg -q 'agent-md-refactor'` | **exit 0** |
| Frozen-path positive + pipefail-safe openspec line check | `rg -q '\.planning/legacy/openspec/' AGENTS.md && ! rg -n 'openspec' AGENTS.md \| rg -qv 'legacy'` | **exit 0** |
| Forbidden-token loop, fail-closed | `test -f AGENTS.md && for T in 'openspec list' … 'opsx'; do …; done` | **exit 0** |
| R0.9 row — both validating skills named | `rg -q 'agent-md-refactor' && rg -q 'crafting-effective-readmes'` | **exit 0** |
| R0.10 row — and nowhere else outside `.planning/` | `test "$(rg -l --glob '!.planning/**' -- 'one commit per plan' .)" = './AGENTS.md'` | **exit 0** |
| R0.4 row — all seven disclosed limits in `AGENTS.md` | `for L in 'no-verify' 'KITTI_ALLOW_MASTER_PUSH' 'squash' 'cherry-pick' 'first' 'delet'; do …; done` | **exit 0** |
| R0.8 row — `CLAUDE.md` stub is byte-exact | `printf '@AGENTS.md\n' \| cmp -s - CLAUDE.md` | **exit 0** |
| R0.8 row — config repointed | `test "$(jq -r .claude_md_path .planning/config.json)" = './AGENTS.md'` | **exit 0** |

No rule was reworded out from under its own check. In particular the commit-granularity rule is
still on **exactly one** line, which is the failure mode a refactor pass most easily introduces.

---

## Task 2 — The merge precondition, and the last two statements of the superseded policy

### Step 0 — `make doctor`, captured verbatim

Run once, in this worktree, and **reused** by task 3 step 3 rather than run twice:

```
$ make doctor
make: *** [Makefile:32: doctor] Error 1
PASS kitty binary: /home/bazzite/.local/bin/kitty -> kitty 0.49.0 created by Kovid Goyal
PASS symlink: /home/bazzite/.local/bin/kitty -> /var/home/bazzite/.local/kitty.app/bin/kitty
PASS desktop entry: /home/bazzite/.local/share/applications/kitty.desktop
PASS config payload: /home/bazzite/.config/kitty/kitty-setup/kitty-setup.conf
PASS sentinel block: present in /home/bazzite/.config/kitty/kitty.conf
PASS parse check: kitty --debug-config exit=0
PASS bindings: 22 ours, 79 defaults, 0 conflicts
FAIL completion: register-python-argcomplete not on PATH
SKIP remote-control: no running kitty
```

**Exit status: `make` exits 2**; make's own diagnostic reports the recipe (`my-kitty doctor`)
exited 1. Either way it is non-zero and the gate is red.

**The single failing check:** `completion: register-python-argcomplete not on PATH`. Everything
else is PASS or SKIP. This reproduces the plan's recorded measurement exactly.

**This failure *is* requirement R1.1**, which Phase 2 owns by name: `.planning/REQUIREMENTS.md:105-121`
names the same root cause (the helper lives inside the uv tool venv but `uv tool install` exposes
only `my-kitty`) and states "**R1.1 unblocks Phase 1's merge**".

**Verdict: the merge is deferred, not excused.** R0.4's and D-06's literal precondition — "once
`make doctor` and `make test` are green" — is not satisfiable at the end of Phase 1. The
precondition was **not** narrowed and **no exemption was written**. Phase 1 commits its plans and
stops; `gsd/phase-01-governance-freeze` merges once Phase 2's R1.1 makes doctor green. Concretely:

- **No carve-out marker was written.** The marker string earlier drafts of this plan named is
  absent from `AGENTS.md`, `.planning/ROADMAP.md` and `.planning/PROJECT.md` — verified,
  exit 1 (no match) — and it is deliberately not reproduced anywhere in this SUMMARY either,
  so that a repo-wide grep for it remains a true absence check rather than one this document
  defeats by explaining it.
- **ROADMAP step 6's doctor clause is untouched.** Its literal "gates green" precondition stays
  true as written, because Phase 1 simply never reaches the merge step. Only step 6's *commit*
  clause changed.
- **The deferral is stated as a fact about Phase 1**, one sentence each, in `AGENTS.md`'s
  git-policy bullet and in PROJECT.md's Key Decisions git row — not as a general exception.

`01-VALIDATION.md`'s Manual-Only row "Whether the merge precondition had to be narrowed, and
whether that narrowing is acceptable" resolves as: **it was not narrowed.** There is no narrowing
to confirm or overturn; the alternative the row names (defer Phase 1's merge until after Phase 2)
is the one taken.

### Step 0b — `core.hooksPath` restored to its relative form, and proven per worktree

**Before:**

```
$ git config --get core.hooksPath
/var/home/bazzite/git/personal/kitty-setup/tools/hooks
```

An **absolute** value. The consequence, as wave 2 established and this plan confirms from the
hooks' own headers (`tools/hooks/post-commit` LIMITS item 1, `tools/hooks/post-checkout` "CWD IS
LOAD-BEARING"): every worktree resolves the hook *file* out of the main checkout, so **R0.6's
per-commit index refresh silently does not happen anywhere except the primary tree.**

**Restored via the tracked target** (`Makefile:43-44` → `@git config core.hooksPath tools/hooks`):

```
$ make hooks
$ git config --get core.hooksPath
tools/hooks
```

**After: `tools/hooks`.**

**Proven, not asserted.** A throwaway worktree was cut and a real commit made inside it:

```
$ git worktree add .claude/worktrees/hookproof-01-05 -b agent-01-05-hookproof
Preparing worktree (new branch 'agent-01-05-hookproof')
HEAD is now at 27a152a docs(01-04): AGENTS.md as the canonical instruction file (R0.3, R0.8, R0.9, R0.10)
[post-checkout] CodeGraph index built for this new worktree

$ git add HOOKPROOF.txt && git commit -m "chore: throwaway hook-resolution proof"
[post-commit] CodeGraph index synchronised for this worktree
[agent-01-05-hookproof fd102a5] chore: throwaway hook-resolution proof
 1 file changed, 1 insertion(+)
 create mode 100644 HOOKPROOF.txt
```

Both hooks fired **inside the new worktree** — the `[post-commit]` tag is the property the
absolute value defeats, and it is the live demonstration 01-01's RESEARCH Pattern 1 claimed.
Torn down cleanly afterwards (`git worktree remove --force` → exit 0; `git branch -D
agent-01-05-hookproof` → "Deleted branch … (was fd102a5)"); `git worktree list` shows only the
main checkout and this executor's worktree, and `git status --short` carried no residue.

**No per-worktree override exists or was created:** `git config --get extensions.worktreeConfig`
→ **exit 1 (unset)**, both before and after.

**Scope note, stated plainly:** worktrees share `.git/config`, so this is a **repo-wide**
restoration to plan 01-01's intended value, affecting the user's checkout and any concurrent
agent. That is what the plan asked for — the alternative (a `--worktree` override) was explicitly
not invented, and would have needed `extensions.worktreeConfig`, which this row requires to stay
unset.

### The document edits

All three edits are targeted replacements on the named passages. **No whole-file write** was made
to either planning document — `.planning/ROADMAP.md`'s other ten phases and PROJECT.md's other six
Key Decisions rows are byte-untouched, and the integrity gates below prove it.

**1. `.planning/ROADMAP.md` Universal Phase Gate step 6.** The commit clause now reads "work lands
as **one commit per plan** — the granularity rule lives in `AGENTS.md` and is pointed to, not
restated here", satisfying ROADMAP criterion 11 (the rule lives in exactly one file). The merge
clause is unchanged per Step 0. The date stamp now reads "updated 2026-09-23, phase-1 execution,
discussion D-06/D-07/D-16", naming D-16 alongside D-06/D-07. The guard sentence gained the R0.4
disclosure it was missing: it is now described as "a compliance guard for cooperating agents, not
a security boundary; its seven disclosed limits are listed in `AGENTS.md`'s git-policy bullet and
are not repeated here" — so the restatement points at the disclosure instead of over-claiming.

**2. `.planning/PROJECT.md` Key Decisions, the Git policy row. Both cells changed.** The Decision
cell states one commit per plan and points at `AGENTS.md`; it adds the Phase 1 deferral sentence
and notes the guard's limits are disclosed in `AGENTS.md`. The **Rationale** cell no longer
justifies the superseded rule — the clause that did has been replaced with "A plan-sized commit is
a coherent unit of review, and the plan boundary is where the requirements a change satisfies are
already enumerated". Rewriting only the Decision cell would have left the negative gate red, since
the Rationale carried the rule in a second phrasing.

**3. `.planning/PROJECT.md` out-of-scope, the "Merging to `master`" bullet.** It previously said
"agents push a feature branch only; integration is the owner's call (R0.4)" — the **opposite** of
D-06. It is **rewritten, not deleted**, so a reader who remembers the old policy finds the
correction where the old policy was: merging at a green phase boundary is in scope per D-06, what
remains out of scope is any merge or force-push outside that boundary, and Phase 1's own merge is
deferred until R1.1.

**4. `AGENTS.md` git-policy bullet** gained the one-sentence Phase 1 deferral: "Phase 1's branch
merges after Phase 2's R1.1 turns `make doctor` green."

**No provenance text naming the old rule was written into `ROADMAP.md` or `PROJECT.md`** — that
would have re-tripped the negative gate. Provenance lives here, in this SUMMARY, which is exactly
where the plan's `<fails_when>` trap says to put it.

### Was a further occurrence of the superseded rule found anywhere?

**Within the three files the plan names — no.**
- `.planning/ROADMAP.md`: none (gate exit 0).
- `.planning/PROJECT.md`: none (gate exit 0).
- `01-VALIDATION.md:39` carries the corrected form — "**After every task verification**" — and the
  correction paragraph is present and intact. Its remaining occurrences of the phrasing are
  *quotations*, in the prose that explains the supersession and inside row `01-05-T2`, which
  records the gate's own search pattern verbatim. That is why the file is excluded from the grep:
  a document that catalogues commands necessarily contains every string those commands search for.
  No **new** instance appeared.

**Outside those three files, a whole-tree sweep found exactly one occurrence, and it is reported
rather than fixed.** The sweep:

```
$ rg -ni --glob '!.planning/legacy/**' -- 'commits? per task|per-task commit|task commit' .
./docs/prds/kitty-setup-remediation-v1.0-prd.md:48:
    - R0.4 Git policy (update CLAUDE.md "No auto-commit"): agents MAY commit per task and push a
```

**Not fixed, deliberately.** That line is the source PRD's own R0.4 text — the very wording D-06
and D-16 superseded. `.planning/REQUIREMENTS.md` R0.4 already records the supersession ("reworded
2026-09-22 per phase-1 discussion D-06") and R0.10 records that it supersedes "agents commit per
task" in R0.4. Rewriting a dated v1.0 input document to match a later decision would destroy the
provenance of that supersession and make REQUIREMENTS.md's citation unverifiable against its own
source — the mirror image of the drift `AGENTS.md` forbids. It is also outside this plan's
`files_modified`. **Proposed owner: Phase 8 / R6.1**, whose live-doc hygiene remit is the right
place to decide whether `docs/prds/` should carry a FROZEN banner like the other two history docs
(it currently has none of its own; its single `FROZEN` hit is a quotation of the banner it asked
plan 01-03 to add elsewhere).

### Task 2 gates

| Gate | Command | Result |
|------|---------|--------|
| Rule present in ROADMAP **and** in PROJECT, asserted separately | `rg -ni 'one commit per plan' .planning/ROADMAP.md && rg -ni 'one commit per plan' .planning/PROJECT.md` | **exit 0** — ROADMAP `:40` (inside the Universal Phase Gate), PROJECT `:130` (inside Key Decisions). ROADMAP `:82` and `:91` already carried it in Phase 1's own criteria. |
| No phrasing of the superseded rule in either policy file | `for F in .planning/ROADMAP.md .planning/PROJECT.md; do test -f "$F" \|\| exit 1; if rg -qi -- 'commits? per task\|per-task commit\|task commit' "$F"; then exit 1; fi; done` | **exit 0** |
| Eleven `### Phase N[.N]:` detail headings | `test "$(rg -c '^### Phase [0-9]+(\.[0-9]+)?:' .planning/ROADMAP.md)" = '11'` | **exit 0** (`rg -c` → `11`) |
| Three untouched Key Decisions rows still present | `rg -q 'R2\.8 oracle test is built FIRST' && rg -q 'Keybinding model is native per-OS' && rg -q 'macOS verification'` | **exit 0** |
| Out-of-scope bullet no longer states the replaced policy | `test -f .planning/PROJECT.md && ! rg -q 'agents push a feature branch only' .planning/PROJECT.md` | **exit 0** |
| Branch convention + enforcing hook still named in both | `rg -q 'gsd/phase-\{phase\}-\{slug\}' ROADMAP && rg -q 'tools/hooks' ROADMAP && rg -q 'gsd/phase-' PROJECT && rg -q 'tools/hooks' PROJECT` | **exit 0** |
| Carve-out marker absent from all three policy files | grep over `AGENTS.md`, `ROADMAP.md`, `PROJECT.md` | **exit 1 (no match)** |
| Seven Key Decisions rows intact | row count over the Key Decisions table | **`7`** |
| No commit made by this task | `git log --oneline -1` | still `27a152a` |

**The ROADMAP Progress list is complete — do not report it as missing Phase 8.5.** Measured on
disk: the Progress table has **eleven** rows and does include
`| 8.5. Test-Suite Type & Lint Cleanup | 0/TBD | Not started | - |` at `:284`. The round-1
self-raised finding that asserted this gap was **false** and was withdrawn; recording it would put
a false finding in this SUMMARY.

---

## Task 3 — The phase governance gate, run and recorded

### Step 2 — the per-requirement checks: all 23 rows resolved

Every Automated Command in `01-VALIDATION.md`'s verification map was run against the real tree.
**23 rows, 23 resolved, 0 pending, 0 `TBD`.** The Map Completeness Gate, all three parts plus the
`TBD` regression guard:

```
$ V=.planning/phases/01-governance-freeze/01-VALIDATION.md
$ test -f "$V" && ! rg '^\| 01-0' "$V" | rg -q '⬜ pending'                          → exit 0
$ test "$(rg -c '^\| 01-0' "$V")" = '23'                                            → exit 0
$ test "$(rg -c '^\| 01-0.*\| *(✅|❌|⚠️) *\|[[:space:]]*$' "$V")" = '23'             → exit 0
$ test -f "$V" && ! rg '^\| 01-0' "$V" | rg -q 'TBD'                                → exit 0
```

Both planning-time corrections are present and were confirmed: the R0.2 row substitutes
filesystem assertions for the `openspec list` form (the CLI has no root here after 01-03, which is
D-02's intended end state), and the R0.1 row uses `rg -ni` rather than `rg -n`.

**Task ID / Plan / Wave columns re-checked against what each plan actually delivered — all
correct, no correction needed.** Plan 01-01 was the named concern because it was restructured
after the review; its three tasks are Task 1 "End-to-end 'a force-push is rejected' — widen the
allow-list…", Task 2 "Direct-to-master rejection by provenance…", Task 3 "Settle the three
undefined edges, enumerate every limit…", which match the row subjects assigned to
`01-01-T1` (×3), `01-01-T2` and `01-01-T3`. The 01-04 assignments were also checked at source:
the placement rule (R0.9) and the authoritative-sources rewrite (R0.3) are in 01-04 Task 1
(`01-04-PLAN.md:183`, task spans `:161-288`), the commit-granularity rule (R0.10) and the other
new rules are in Task 2 (`:335`, spans `:289-403`), and the R0.8 rows are Task 3 (`:404+`).

Selected results, by row:

| Row | Requirement | Command result |
|-----|-------------|----------------|
| `01-01-T1` allow-list | R0.4 | exit 0 — `tools/hooks` in `README.md` (1), `.planning/PROJECT.md` (2), `AGENTS.md` (2); `tools/setup.sh` present; the forbidden "only bash logic in this repo" sentence absent. `CLAUDE.md` has 0 hits, which the round-3 `\|\|` term anticipates. |
| `01-01-T1` non-fast-forward | R0.4 | **`3 passed, 15 deselected`** (rescoped — see below) |
| `01-01-T1` hooksPath | R0.4 | exit 0 **after** step 0b. `core.hooksPath` = `tools/hooks`; `extensions.worktreeConfig` unset (exit 1). This row was **red** when the plan began. |
| `01-01-T2` master guard | R0.4 | **`4 passed, 14 deselected`** (rescoped) |
| `01-01-T3` undefined edges | R0.4 | **`3 passed, 15 deselected`** (rescoped); the seven-limit loop over `tools/hooks/pre-push` → exit 0 |
| `01-02-T1` post-checkout | R0.6 | **`4 passed, 14 deselected`**, no `failed` |
| `01-02-T2` post-commit | R0.6 | **`18 passed`**; `KITTI_CODEGRAPH_TIMEOUT_S` present in `tools/hooks/post-commit` → exit 0 |
| `01-02-T3` live lifecycle | R0.6 | **`18 passed`**; `01-02-SUMMARY.md` carries 5 tagged `[post-checkout]`/`[post-commit]` transcript occurrences and the two separately labelled timings (`:199` `4 passed, 14 deselected in 1.29s`, `:203` `18 passed in 2.47s`, `:207` the `KITTI_CODEGRAPH_TIMEOUT_S=1` budget note) |
| `01-03-T1` relocation | R0.2 | `test ! -e openspec` → exit 0; archive dir count → `1`; `git diff-tree --no-commit-id -r -M --name-status f6b0e26 -- openspec .planning/legacy/openspec` → non-empty, **145 × `R100` + 1 × `A`**, zero other statuses. The `A` is `.planning/legacy/openspec/README.md`, a genuinely new file, exactly as the round-4 note describes. |
| `01-03-T2` banners | R0.2 | exit 0 — all three files carry `FROZEN — history only` once, line 1 is an `# ` heading and line 3 is `> **FROZEN — history only; source of truth is `.planning/`.**` in each |
| `01-03-T3` codegraph after rename | R0.6 | `codegraph status` → **exit 0**, `✓ Index is up to date`, **66 files** indexed (python 66, yaml 22 by symbol language) — a non-zero count, which also resolves the Manual-Only row that asks for one |
| `01-04-T2` R0.1 / R0.5 / R0.7 / R0.10 / R0.4 | — | all exit 0 (see the Task 1 gate table; these are the same commands) |
| `01-04-T1` R0.3 / R0.9 | — | exit 0 |
| `01-04-T3` R0.8 ×2 | — | exit 0; plus `AGENTS.md` referenced and `CLAUDE.md` unreferenced in `.claude/conventions.md`, `tools/setup.sh` and `docs/agent-iteration.md` |
| `01-05-T1` | R0.9 | exit 0 — skill invoked, nine findings triaged, every 01-04 content check re-run |
| `01-05-T2` | R0.4, R0.10 | exit 0 — the four gates in the Task 2 table |
| `01-05-T3` | R0.1–R0.10 | exit 0 — `18 passed`, `311 passed`, the per-requirement checks, the Map Completeness Gate, the quality table below |

**`01-VALIDATION.md`'s frontmatter was not touched:** `status: draft`, `nyquist_compliant: false`,
`wave_0_complete: false` are unchanged. Those belong to `/gsd-validate-phase`, not to execution.

### Step 3 — the Universal Phase Gate evidence

**`make test`, verbatim tail:**

```
$ make test
SKIPPED [8] tests/integration/test_h23_styling.py: set KITTI_INTEGRATION=1 to run integration tests
SKIPPED [4] tests/integration/test_h24_layout_mirrored.py: set KITTI_INTEGRATION=1 to run integration tests
SKIPPED [6] tests/integration/test_h25_scene_launcher.py: set KITTI_INTEGRATION=1 to run integration tests
SKIPPED [2] tests/integration/test_scene_fill_tab_e2e.py: set KITTI_INTEGRATION=1 to run integration tests
SKIPPED [4] tests/integration/test_scene_recipe_e2e.py: set KITTI_INTEGRATION=1 to run integration tests
======================= 311 passed, 70 skipped in 2.72s ========================
```

Exit 0. Machine-checked rather than eyeballed:

| Assertion | Command | Result |
|-----------|---------|--------|
| Whole-suite total is 311 | `rg -c '(^\|[^0-9])311 passed'` over the captured output | **`1`** |
| No failure or error anywhere | `rg -c '[0-9]+ (failed\|error)'` | **exit 1 (no match)** |
| The new module's own 18 cases pass, none skipped | `uv run pytest tests/unit/test_git_hooks.py -q` → `18 passed in 2.56s`; `rg -c '(^\|[^0-9])18 passed'` → `1`; `rg -c 'skipped'` → **exit 1** | **exit 0** |
| The module is collected by the whole-tree run | `uv run pytest tests/ --collect-only -q \| rg -c 'test_git_hooks.py'` | **`18`** |

The 70 skips are structural — `tests/conftest.py:44-53` gates `tests/integration/` behind
`KITTI_INTEGRATION=1` — which is why the zero-skip assertion is scoped to the new module rather
than the whole suite.

**`make doctor`** is the capture in Step 0 above, **reused and not re-run**. It is recorded as
**captured evidence, not as a passed gate**: making every doctor check PASS or SKIP is Phase 2's
requirement R1.1. The assertion that stands in for it is that Phase 1 touched no file doctor reads:

```
$ git diff --name-only 5452f54df59b65532aea89517c0b813bfd450af6..HEAD -- src config   → empty
$ git diff --name-only HEAD -- src config                                             → empty
```

Both empty, using the recorded SHA. Doctor's output does **not** differ in substance from its
pre-phase behaviour — same eight checks, same single FAIL, same skip — so there is no runtime
deviation to report.

### Step 4 — the quality tools

**Tier 1 — must be clean: the one Python file this phase adds.**

| Tool | Command | Result |
|------|---------|--------|
| ruff | `uv run ruff check tests/unit/test_git_hooks.py` | **clean** (`[]`) |
| black | `uv run black --check tests/unit/test_git_hooks.py` | **clean** (`1 file would be left unchanged`) |
| pyright | `uv run pyright tests/unit/test_git_hooks.py` | **`0 errors, 0 warnings, 0 informations`** — *after* the fix in Deviations §1; it was **5 errors** as delivered |
| bandit | n/a | `tests` is excluded by config (`pyproject.toml:87-88`) |
| vulture | `uv run vulture src tests` | no finding names this module (`rg -c 'test_git_hooks\.py'` → exit 1) |

**Tier 2 — must not regress: whole-repo counts against the corrected baseline at `5452f54`.**

| Tool | Command | Baseline @ `5452f54` | Post-phase | Δ |
|------|---------|----------------------|------------|---|
| ruff | `uv run ruff check src tests tools --output-format concise` | **28** findings | **28** (`Found 28 errors.`; 0 in the added module) | **0** |
| black | `uv run black --check src tests tools` | **11** files would be reformatted | **11** (`11 files would be reformatted, 55 files would be left unchanged`) | **0** |
| pyright | `uv run pyright` | **571** errors | **571** (`571 errors, 0 warnings, 0 informations`; **0** in the added module) | **0** |
| bandit | `uv run bandit -q -r src` | **27** issues — **0 high / 8 medium / 19 low** | **27** — **`19 Severity: Low`, `8 Severity: Medium`, 0 high** | **0** |
| vulture | `uv run vulture src tests` | **12** findings | **12** (0 in the added module) | **0** |

**No count grew.** None shrank either, so there is no bonus to note.

**Bandit is reported by severity.** The tally above is `rg -o 'Severity: [A-Za-z]+' | sort | uniq -c`
over bandit's own output: 19 Low, 8 Medium, no High row at all. Bandit's `Confidence:` column is a
*different* tally over the same 27 issues, and that column — not severity — is the source of the
misread figure `.planning/REQUIREMENTS.md:70-72` documents. This SUMMARY does not restate that
figure; it names where it came from. Both columns were re-derived independently here, which is why
the distinction is asserted as measured rather than repeated on trust.

**One honest measurement caveat, recorded rather than smoothed over.** The baseline records pyright's
571 as "of which **19** in `src/`". My instrument for that sub-count —
`rg ' - error: ' <pyright output> | rg -c '/src/'` — returns **15**, both before and after this
plan's edits. Since `git diff --name-only 5452f54..HEAD -- src config` is **empty**, the tree under
`src/` is bit-identical to the baseline commit, so the difference is in how the sub-count is taken,
not in the code. The gated number is the **total**, 571 → 571, which matches exactly. I am not
asserting 19 on the strength of a command that produced 15.

**The `src/` and `tests/` quality gaps are owned, not unowned.**

- **R0.11** (`.planning/REQUIREMENTS.md:67-73`) assigns "`src/` clean under all five tools" to
  **Phase 2**, the earliest phase that already edits those files. From the moment it lands, "src
  clean" is a hard gate in Universal Phase Gate step 5.
- **R0.12** (`:74-81`) assigns "`tests/` type-checks and lints clean" to **Phase 8.5**; 96% of that
  debt is `typeCheckingMode = "strict"` applied to pytest bodies.
- **`.planning/ROADMAP.md:29-38` already states the measured gate**, not the aspirational one:
  "**`src/` must be clean** under ruff, black, pyright, bandit and vulture. Phase 2 brings it there
  (R0.11); from then on this is a hard gate." / "**`tests/` must not regress** — no tool's finding
  count may grow against the recorded baseline (measured at `5452f54`: ruff 28, black 11 files,
  pyright 571 errors of which 19 are in `src/`, bandit 0 high / 8 medium / 19 low, vulture 12).
  Phase 8.5 drives the `tests/` remainder down." / "A phase that *adds* a file owns that file being
  clean, wherever it lives."

  Tier 1 above is exactly that third clause, and Deviations §1 is this phase honouring it.

**The one genuinely unowned defect — reported, not fixed.**

`.claude/conventions.md:59-69` documents a Make interface the `Makefile` does not have:

```
$ sed -n '59,69p' .claude/conventions.md
### Make targets (when Makefile exists)
    make format            # black + ruff --fix on src/ and tests/
    make validate          # full pre-commit pipeline
    make test              # pytest with coverage
    make test-unit
    make test-integration  # real Kitty session; KITTI_INTEGRATION=1 to enable
Never commit code that fails `make validate`.

$ rg '^validate' Makefile          → no match (exit 1)
$ Makefile targets, measured:      clean doctor help hooks install prune setup test uninstall
```

**Four of the five named targets do not exist** — `format`, `validate`, `test-unit`,
`test-integration`; only `test` does. So `.claude/conventions.md:69` instructs every agent never to
commit code that fails a command that cannot be run. **No R0–R8 requirement owns this mismatch.**

**Proposed owner: Phase 8 / R6.1 (live-doc hygiene).** **Not fixed here**, for the two reasons the
plan's Deferred ledger gives: `01-CONTEXT.md` states `.claude/conventions.md` is otherwise
unchanged by this phase, and the fix is a real choice between adding four Makefile targets and
rewriting a conventions section — neither of which this phase's decisions cover. Nothing in the
repo was changed to fix it.

### Step 5 — the pre-push guard, and the hand-off

**No merge into `master` and no push of anything** was performed by this plan.
`git rev-parse --abbrev-ref HEAD` → `worktree-agent-ad6a93182013128f4` (≠ `master`), and
`git branch -r` → **`origin/master` only**, so the phase branch has **never been pushed** — stated
as a measured fact rather than assumed either way.

**No live pre-push transcript is recorded, and none is required.** The plan's task 3 action
(round 4) withdrew that requirement on two measured grounds: no prior plan pushes anything, so the
guard has not been traversed during this phase; and a plan whose single commit must contain its own
SUMMARY cannot also contain the transcript of a push that necessarily happens *after* that commit.
One commit cannot hold evidence produced after it, whichever ref is pushed. *(Residual plan
inconsistency, flagged for the record: the task's `<acceptance_criteria>` at `01-05-PLAN.md:602`
still reads "records one real traversal of the pre-push guard on the phase branch". That line is
stale against the same task's `<action>` at `:550-575`, which withdraws it in as many words, and
against the plan's `<verification>` block, which lists no such item. The action governs.)*

**The guard evidence that *is* available pre-commit, and is recorded:**

- **Plan 01-02's 18 sandbox tests**, all passing here (`18 passed in 2.56s`). They are real
  executions in disposable `tmp_path` repos, not assertions, and they cover the non-`master`
  fast-forward path (`test_fast_forward_push_allowed`), the new-branch/all-zero-`remote_sha` path
  (`test_new_branch_push_allowed`, `test_first_push_of_master_to_empty_remote_rejected`), the
  amend-then-force rejection (`test_force_push_rejected`), the `master`-merge allowance
  (`test_phase_branch_merge_to_master_allowed`,
  `test_milestone_branch_merge_to_master_allowed`), the escape hatch
  (`test_master_escape_hatch_allows_direct_push`) and both deletion edges.
- **The measured never-pushed state** of `gsd/phase-01-governance-freeze`.

A note for whoever reads the eventual push transcript: a **first** push of a new branch reaches the
hook with an all-zero `remote_sha`, so the guard takes its "no remote ref yet" path and the
force-detection branch (`git merge-base --is-ancestor`) is not exercised live. Deliberately
force-pushing to exercise it would violate the policy this phase installs, which is why that path
is covered by 01-02's tests instead.

**Hand-off to Universal Phase Gate step 6.** The merge is the gate's to perform, after every plan in
this phase is committed — and for Phase 1 it is a **branch push only**, because the merge is
deferred until Phase 2's R1.1 turns `make doctor` green. If the guard rejects the push, consult
`tools/hooks/pre-push`'s seven-item limits block **first**. If the rejection matches a **disclosed**
limit — a squash merge, a cherry-picked or rebased commit, a `gsd/*` branch deleted before its merge
was pushed, the first push of `master`, or a `master` deletion — that is **designed behaviour**, and
`KITTI_ALLOW_MASTER_PUSH=1` is the sanctioned route, to be recorded when used. Only a rejection
matching **none** of the seven is a defect in plan 01-01's heuristic, and that is fixed in 01-01
rather than routed around. Do not treat the escape hatch as flatly forbidden — that instruction
would send an executor to "fix" a hook behaving exactly as specified.

---

## Deviations from Plan

### 1. [Rule 1 — Bug] Fixed 5 pyright errors in `tests/unit/test_git_hooks.py`, a file outside this plan's declared edit set

- **Found during:** Task 3 step 4, tier 1.
- **Issue:** `uv run pyright tests/unit/test_git_hooks.py` reported **5 errors**, not 0, so the
  plan's tier-1 gate failed. Four were the same defect —
  `Argument of type "str" cannot be assigned to parameter "prepend" of type "bool" in function
  "_path_env"` at `:433`, `:465`, `:537`, `:623` — caused by unpacking a `dict[str, str]`
  (`**{SHIM_LOG_ENV: …}`) into a signature that also carries the keyword-only `prepend: bool`.
  The fifth was `reportDeprecated` at `:222`: annotating a `@contextlib.contextmanager` function's
  return as `Iterator[...]` is deprecated in favour of `Generator[...]`.
  Whole-repo pyright measured **576** errors — the recorded baseline is **571** — so these 5 were a
  live regression of the number ROADMAP step 5 gates on.
- **Fix:** `_path_env` now takes an explicit `overrides: Mapping[str, str] | None = None` parameter
  instead of `**overrides: str`, with the reason recorded in its docstring, and the four call sites
  pass `overrides={...}`. `_sandbox`'s annotation became
  `Generator[tuple[Path, Path], None, None]`, and the import changed from `Iterator` to
  `Generator, Mapping`. Behaviour-neutral: no test logic changed.
- **Verified:** `uv run pyright tests/unit/test_git_hooks.py` → `0 errors`; whole-repo
  `uv run pyright` → **571**, back on baseline, with 0 errors attributable to this module;
  `uv run ruff check` and `uv run black --check` still clean on the file;
  `uv run pytest tests/unit/test_git_hooks.py -q` → `18 passed`; `make test` → `311 passed,
  70 skipped`, exit 0.
- **Why this was the right call rather than deferring:** the plan's own tier-1 gate demands the file
  be clean, ROADMAP step 5's third clause makes it this phase's obligation ("a phase that *adds* a
  file owns that file being clean"), and the plan's `must_haves` truth requires that "this phase
  introduced no new … pyright … finding relative to the recorded baseline at `5452f54`". Deferring
  would have failed a gate and a must-have simultaneously. My instruction was to fix the work, not
  the gate.
- **Consequence for the commit:** `tests/unit/test_git_hooks.py` is a **sixth** path in the commit,
  beyond the five the plan's task 3 step 5 enumerates. Staged explicitly by name; no `git add -A`
  was used.

### 2. [Deviation — map correction] Rescoped three verification-map commands whose cumulative counts cannot hold at wave 5

- **Found during:** Task 3 step 2.
- **Issue:** rows `01-01-T1` (non-fast-forward), `01-01-T2` and `01-01-T3` asserted the
  **cumulative** wave-1 pass counts `3`, `7` and `10` over the whole module. At wave 5 the module
  carries all eighteen cases and reports `18 passed`, so `rg -q '(^|[^0-9])3 passed'` fails and each
  row would have recorded **❌ against work that is correct** — the same "fails in exactly its
  passing state" defect that map corrections 3 and 4 already removed, and that the plan's own R0.9
  prohibition forbids ("A gate scoped so wide that it cannot pass, or so narrow that it measures
  nothing, is worse than an absent gate").
- **Fix:** each of the three is now scoped with `-k` to its own task's cases with its count restated
  (3, 4, 3) — precisely how review round 5 had already rescoped `01-02-T1` for the identical reason.
  Recorded as **correction 6** in `01-VALIDATION.md`'s own corrections list, with the measurement.
- **Verified:** `3 passed, 15 deselected` / `4 passed, 14 deselected` / `3 passed, 15 deselected`.
  The `01-02-T2`, `01-02-T3` and `01-05-T3` rows keep the whole-module `18 passed` form, which is
  correct at wave 5 and was measured so.
- **Not a gate weakening:** the rescoped commands still fail if any of those cases regresses; they
  simply name the cases the row is about instead of a running total from a different wave.

### 3. [Deviation — partial-work triage] Dropped one hunk of the cross-AI partial patch

- **Context:** a prior cross-AI executor produced task 2's document edits without committing. Its
  diff was reviewed against task 2's action and gates, applied for `.planning/PROJECT.md` (both
  hunks) and `.planning/ROADMAP.md` (`git apply --include=.planning/… ` → "Applied … cleanly"), and
  its `AGENTS.md` git-policy deferral sentence was reproduced by hand.
- **Dropped:** its second `AGENTS.md` hunk, a `## Stack` rewording
  ("a hook that outgrows `tools/uninstall.sh`'s dispatcher" → "a hook that outgrows that dispatcher
  shape"). Task 2's action authorises no Stack edit, and `01-CONTEXT.md:139` defers Stack-section
  wording to **Phase 8 / R6.1**. It is recorded instead as Deferred finding **D3** in Task 1's
  triage, where it belongs.
- **Checked as instructed:** PROJECT.md's *Rationale* cell no longer says "Per-task commits" — the
  negative gate over both policy files passes (exit 0), which it could not have done had either
  cell kept a phrasing.

### 4. [Deviation — reported, not fixed] One further occurrence of the superseded rule, in the source PRD

See "Was a further occurrence … found anywhere?" above. `docs/prds/kitty-setup-remediation-v1.0-prd.md:48`
carries the PRD's original R0.4 text. Reported with **Phase 8 / R6.1** proposed as owner, not
rewritten, because falsifying a dated input document would destroy the provenance of the
supersession that `.planning/REQUIREMENTS.md` R0.4 and R0.10 both cite.

### 5. [Deviation — GSD executor default] No `STATE.md` / `ROADMAP.md`-progress metadata commit

The GSD executor's default flow ends with a separate `docs(…)` commit carrying `STATE.md`,
ROADMAP progress and `REQUIREMENTS.md` checkboxes. That is **not** done here: `01-05` is
`type: execute`, so R0.10 / D-16 permit **exactly one** commit, and the plan's task 3 step 5
enumerates the staging set. A second commit would violate the rule this very plan installs.
`STATE.md` and the requirement checkboxes are therefore left for the phase-end flow.

### 6. [Environment note, no work product affected] `core.hooksPath` change is repo-wide

Recorded again here because it reaches beyond this worktree: restoring `core.hooksPath` mutates the
shared `.git/config`, so the user's checkout and any concurrent agent now resolve hooks relatively.
This is the value plan 01-01 intended and the plan explicitly asked for; the alternative
(`--worktree` override) was *not* invented, since it would require
`extensions.worktreeConfig`, which the `01-01-T1` row requires to stay unset.

---

## Known Stubs

**None.** No file in this plan's edit set contains a placeholder, a hardcoded empty value flowing
to output, or a TODO/FIXME introduced by it. The verification map has no `TBD` in any row and no
`⬜ pending` marker; the `TBD` occurrences that remain in the file are in the prose explaining why
the retired whole-file `TBD` gate was replaced, and the `⬜ pending` occurrences are the Status
legend and the file's own documented copy of the row-scoped gate — neither is a row, and both are
required for the document to explain itself.

## Threat Flags

None. This plan edited markdown, fixed type annotations in a test helper, and ran commands. It
added no network endpoint, auth path, file-access pattern or schema change, and installed no
package — so no new surface exists beyond `01-05-PLAN.md`'s `<threat_model>` register.

`T-1-01`'s disposition (`mitigate`) holds and was honoured: every restatement of the git policy in
`ROADMAP.md` and `PROJECT.md` now points at the guard's disclosed limits in `AGENTS.md` rather than
describing it as absolute, which is R0.4's transparency prohibition discharged in both files.

---

## Requirements

- **R0.4** — the git policy is stated once, identically, in `AGENTS.md`, ROADMAP step 6 and both
  places PROJECT.md states one; every restatement discloses rather than over-claims the guard.
- **R0.9** — `AGENTS.md` has been through an `agent-md-refactor` validation pass with all nine
  findings triaged Applied (3) / Deferred (4) / Rejected (2), plus an explicit nil for the skill's
  deletion phase.
- **R0.10** — the commit-granularity rule lives on exactly one line in exactly one file, and this
  plan is one commit.

---

## Self-Check: PASSED

- `.planning/phases/01-governance-freeze/01-05-SUMMARY.md` — FOUND
- `AGENTS.md`, `.planning/ROADMAP.md`, `.planning/PROJECT.md`,
  `.planning/phases/01-governance-freeze/01-VALIDATION.md`, `tests/unit/test_git_hooks.py` — all
  FOUND and modified
- Base SHA `5452f54df59b65532aea89517c0b813bfd450af6` — confirmed by `git merge-base master HEAD`
- Commit-dependent gates (exactly one `(01-05)` subject on the branch; `git show --stat HEAD`
  includes `01-05-SUMMARY.md`) are run **after** the commit and their results appended below.

### Post-commit gate results

Two gates cannot pass until this plan's commit exists, so they run **after** it:

- `BASE="$(git merge-base master HEAD)" && test "$(git log --format=%s "$BASE"..HEAD | rg -c '\(01-05\)')" = '1'`
- `SHOWN="$(git show --stat --oneline HEAD)" && printf '%s\n' "$SHOWN" | rg -q '01-05-SUMMARY\.md'`

The commit's **subject** is known in advance and carries the required literal scope —
`feat(01-05): close the governance phase — validated AGENTS.md, one git policy, resolved gate
(R0.4, R0.9, R0.10)` — so the first gate's `\(01-05\)` match is determined by this file's own
commit. The commit **hash** is deliberately not written here: this file is staged *into* that
commit, so no value it could contain would be the hash of the commit containing it. That is the
same "one commit cannot hold evidence produced after it" constraint that moved the push transcript
to Universal Phase Gate step 6. Both gates' measured results, and the hash, are recorded in the
execution report handed to the phase-end flow, and are reproducible at any time from
`git log --format=%s 5452f54df59b65532aea89517c0b813bfd450af6..HEAD` and `git show --stat HEAD`.

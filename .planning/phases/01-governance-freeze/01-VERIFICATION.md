---
phase: 01-governance-freeze
verified: 2026-09-23T23:10:00Z
status: passed
score: 10/10 must-haves verified (after gap closure 01-06)
re_verification:
  at: bde7589
  initial_status: gaps_found
  initial_score: 7/10
  closed_by: [bf48fa8, bde7589]
covered_files:
  - ".claude/conventions.md"
  - ".planning/PROJECT.md"
  - ".planning/REQUIREMENTS.md"
  - ".planning/ROADMAP.md"
  - ".planning/config.json"
  - ".planning/phases/01-governance-freeze/01-01-PLAN.md"
  - ".planning/phases/01-governance-freeze/01-01-SUMMARY.md"
  - ".planning/phases/01-governance-freeze/01-02-PLAN.md"
  - ".planning/phases/01-governance-freeze/01-02-SUMMARY.md"
  - ".planning/phases/01-governance-freeze/01-03-PLAN.md"
  - ".planning/phases/01-governance-freeze/01-03-SUMMARY.md"
  - ".planning/phases/01-governance-freeze/01-04-PLAN.md"
  - ".planning/phases/01-governance-freeze/01-04-SUMMARY.md"
  - ".planning/phases/01-governance-freeze/01-05-PLAN.md"
  - ".planning/phases/01-governance-freeze/01-05-SUMMARY.md"
  - ".planning/phases/01-governance-freeze/01-CONTEXT.md"
  - ".planning/phases/01-governance-freeze/01-DISCUSSION-LOG.md"
  - ".planning/phases/01-governance-freeze/01-PATTERNS.md"
  - ".planning/phases/01-governance-freeze/01-RESEARCH.md"
  - ".planning/phases/01-governance-freeze/01-REVIEWS.md"
  - ".planning/phases/01-governance-freeze/01-VALIDATION.md"
  - "AGENTS.md"
  - "CLAUDE.md"
  - "Makefile"
  - "README.md"
  - "docs/agent-iteration.md"
  - "docs/propossal_roadmap.md"
  - "docs/requirements.md"
  - "tests/unit/test_git_hooks.py"
  - "tools/hooks/post-checkout"
  - "tools/hooks/post-commit"
  - "tools/hooks/pre-push"
  - "tools/setup.sh"
covered_digest: "v1:sha256:36228de714900434b775e7109552e6405f46cd60e8cac050e4126616fe76b3fc"
behavior_unverified: 0
overrides_applied: 0
gaps:
  - truth: "R0.4 — `AGENTS.md`, `.planning/ROADMAP.md` step 6 and `.planning/PROJECT.md` state ONE git policy with no surviving contradiction"
    status: failed
    reason: >-
      The three named documents do agree, but `.planning/REQUIREMENTS.md` — the first entry in
      AGENTS.md's own authoritative-sources list, and the file that DEFINES R0.4 — still states
      the superseded policy normatively in two places. The gate that certified "the planning docs
      state the same policy as AGENTS.md, in every place each states one" never searched that file,
      and its absence pattern is case-blind besides.
    artifacts:
      - path: ".planning/REQUIREMENTS.md"
        issue: >-
          Line 355 (Cross-Cutting universal gates): "**Git gate**: commit per task, push branch
          `gsd/<phase>`; never merge to `master`, force-push, amend pushed commits, or push
          `master` (R0.4)." — contradicts R0.10 (one commit per plan) and R0.4 as reworded
          (phase-end merge into `master`). Line 392 (Out of Scope table): "| Merging to `master` |
          Agents push a feature branch only; integration is the owner's call (R0.4) |" — cites
          R0.4 while asserting its opposite.
      - path: ".planning/phases/01-governance-freeze/01-VALIDATION.md"
        issue: >-
          Row 01-05-T2's gate is scoped to `.planning/ROADMAP.md` and `.planning/PROJECT.md` only,
          and its third clause `! rg -q 'agents push a feature branch only' .planning/PROJECT.md`
          is case-sensitive lowercase, so it could not match REQUIREMENTS.md:392's capitalised
          "Agents push a feature branch only" even if the file list were widened.
    missing:
      - "Rewrite `.planning/REQUIREMENTS.md:355` to point at AGENTS.md's git-policy bullet instead of restating a superseded policy."
      - "Replace or annotate the `.planning/REQUIREMENTS.md:392` Out-of-Scope row the way `.planning/PROJECT.md:74-78` already was."
      - "Widen row 01-05-T2's file list to include `.planning/REQUIREMENTS.md` and make both absence patterns case-insensitive (`rg -qi`)."
  - truth: "R0.9 — `AGENTS.md` is internally consistent, with each rule in exactly one of `AGENTS.md` / `README.md` / `.claude/conventions.md` and no rule stated twice"
    status: failed
    reason: >-
      The placement rule is stated (AGENTS.md:3-11) and the commit-granularity rule really does
      appear in exactly one file. But a fourth de-facto rules file exists — `docs/agent-iteration.md`,
      which AGENTS.md itself declares an authoritative source — and it restates three AGENTS.md
      rules, two of them with content that contradicts AGENTS.md. `.claude/conventions.md` also
      carries two process rules that belong in AGENTS.md.
    artifacts:
      - path: "docs/agent-iteration.md"
        issue: >-
          R2 (lines 15-20) restates AGENTS.md's "Verify before declaring done" with an incompatible
          threshold: "`make doctor` and `KITTI_INTEGRATION=1 make test` both exit 0", versus
          AGENTS.md:82-87's "captured rather than green … a captured-but-red run satisfies this
          rule". Phase 1 closed with `make doctor` red on the AGENTS.md reading; R2 says that is
          not "ready". R3 (lines 22-27) states the PRE-widening shell allow-list — "bash, only
          allowed in bootstrap territory", extract to `tools/<name>.sh` — and never mentions
          `tools/hooks/`, so the three hook files this phase added are outside the allow-list as
          that document states it. R1 (lines 9-13) duplicates AGENTS.md's "Hypothesis before
          implementation".
      - path: ".claude/conventions.md"
        issue: >-
          Line 69 "Never commit code that fails `make validate`" and line 75 "TDD is the default
          for new modules: write a failing test first, then implement" are process rules, not stack
          conventions; the first names a Makefile target that does not exist.
      - path: ".planning/phases/01-governance-freeze/01-VALIDATION.md"
        issue: >-
          Row 01-04-T2's uniqueness gate `test "$(rg -l --glob '!.planning/**' -- 'one commit per
          plan' . )" = './AGENTS.md'` is structurally blind to hidden directories, so a duplicate
          planted in `.claude/conventions.md` — one of exactly three files the placement rule
          governs — leaves the gate green.
    missing:
      - "Reconcile `docs/agent-iteration.md` R2 with AGENTS.md's capture-vs-green wording, in one file only."
      - "Update `docs/agent-iteration.md` R3 to the two-clause shell allow-list, or delete the clause and point at AGENTS.md's `## Stack`."
      - "Move `.claude/conventions.md:69,75` process rules into AGENTS.md or restate them as conventions."
      - "Add `--hidden` to the 01-04-T2 uniqueness gate."
  - truth: "R0.3 — OpenSpec process references are retired"
    status: partial
    reason: >-
      AGENTS.md's authoritative-sources list is clean (its only `openspec` hit is the
      `.planning/legacy/` history pointer; the forbidden-token loop is clean; all ten links
      resolve). But two live, non-frozen documents still drive a reader into the process this
      phase retired, and one of them is an AGENTS.md-declared authoritative source. R0.3's clause
      "OpenSpec process references are retired" is not scoped to the canonical file.
    artifacts:
      - path: "docs/agent-iteration.md"
        issue: >-
          Lines 4-5 tell the reader to "Read this before opening another OpenSpec change or picking
          the next item from [docs/requirements.md]" — a FROZEN file. Lines 113-119 instruct
          `openspec new change <kebab-case-name>` plus the `/opsx:propose` skill and reference
          `openspec/specs/`. Lines 164-165 instruct `openspec archive <name>`. Line 192 instructs
          opening a follow-up OpenSpec change. None of these can run: 01-03 removed the openspec
          root, which 01-VALIDATION.md's own correction 1 states is D-02's intended end state. No
          later phase owns this file (R6.1 names CLI help, docstrings, README, scene headers and
          the Stack section — not `docs/agent-iteration.md`).
    missing:
      - "Retire or rewrite the OpenSpec workflow steps in `docs/agent-iteration.md` (lines 4-5, 113-119, 164-165, 192) against the `.planning/` phase/plan workflow."
      - "Widen the R0.3 gate beyond `AGENTS.md` to every non-frozen tracked doc, case-insensitively."
deferred:
  - truth: "README.md describes the repo as it now is — no `openspec/` at the root, no broken OpenSpec links"
    addressed_in: "Phase 8"
    evidence: >-
      Phase 8 success criterion 1: "CLI help text, docstrings, README, scene example headers, and
      the `CLAUDE.md` \"Stack\" section all match current behaviour — every claim checkable against
      a command's actual output." (R6.1). Recorded as MEDIUM finding 6 below because the broken
      link and the stale root-layout entry are direct consequences of Phase 1's own `git mv`.
  - truth: "`.claude/conventions.md` and the `Makefile` agree on which targets exist"
    addressed_in: "Phase 8"
    evidence: >-
      `.planning/REQUIREMENTS.md` R6.3, mapped to Phase 8 in the Traceability table. NOTE: Phase 8
      declares `**Requirements**: R6.1, R6.2, R6.3` but writes success criteria only for R6.1,
      R6.2 and the frozen-specs out-of-scope clause — R6.3 has no criterion and will run ungated.
      See MEDIUM finding 9.
  - truth: "`docs/prds/kitty-setup-remediation-v1.0-prd.md:48` no longer reads as a live statement of the superseded git policy"
    addressed_in: "Phase 8"
    evidence: >-
      Proposed by plan 01-05 as Phase 8 / R6.1 work. Accepted as deferrable, but the stated reason
      is rejected — see MEDIUM finding 10 for the verdict.
---

## Re-verification after gap closure (plan 01-06)

The report below is the **initial** verification, preserved unchanged as the record of what was
found. Every CRITICAL and HIGH finding in it was closed by plan `01-06` (`bf48fa8` RED,
`bde7589` GREEN). Re-run by the orchestrator at `bde7589`, from the tree, not from the SUMMARY:

| Previously | Gate re-run at `bde7589` | Result |
|---|---|---|
| CRITICAL — `REQUIREMENTS.md` stated the superseded git policy; row `01-05-T2` could not see it | `01-05-T2`, now over ROADMAP + PROJECT + **REQUIREMENTS**, case-insensitive | PASS |
| HIGH — uniqueness gate blind to dotted dirs | `01-04-T2` with `--hidden`, `.git` excluded | PASS |
| HIGH — `docs/agent-iteration.md` named dead OpenSpec commands | `! rg -n 'openspec new change\|/opsx:\|openspec archive' docs/agent-iteration.md docs/probe-template.md` | PASS |
| HIGH — its allow-list omitted `tools/hooks/` | now points at `AGENTS.md`'s `## Stack` | PASS |
| HIGH — undisclosed pre-push bypass `master:refs/heads/main` | closed; guard keys on both refspec sides; residual disclosed as a limit in the hook header and `AGENTS.md` | 21/21 in `tests/unit/test_git_hooks.py` |
| MEDIUM — PRD carried the superseded R0.4 text | FROZEN banner added, no word below it changed | PASS |
| MEDIUM — Phase 8 declared R6.3 with no criterion | criterion added; ROADMAP still has 11 phase headings | PASS |
| — `core.hooksPath` had drifted absolute again (harness worktree creation) | `test "$(git config --get core.hooksPath)" = 'tools/hooks'` after `make hooks` | PASS |

Map Completeness Gate: 23 rows, 23 anchored verdicts, no pending row. `make test` → `314 passed,
70 skipped`; `uv run pytest tests/unit/test_git_hooks.py -q` → `21 passed`; `uv run pyright` →
`571 errors` (baseline, no regression). **The 70 skipped integration tests were run as well**,
headless under a nested compositor so nothing touched the user's session:
`env -u WAYLAND_DISPLAY -u DISPLAY WLR_BACKENDS=headless WLR_LIBINPUT_NO_DEVICES=1 cage -- bash -c
'KITTI_INTEGRATION=1 uv run pytest tests/integration -q'` → `70 passed in 43.89s`, no `cage` or
`kitty` process left behind. That run is what R0.13 (Phase 2) makes a standing gate.

`make doctor` remains red on exactly one check, `completion` — R1.1, Phase 2's. Phase 1's merge
stays deferred until that turns green; no carve-out was written.


# Phase 1: Governance & Freeze — Verification Report

**Phase Goal:** An agent opening this repo finds exactly one authoritative source of intent and one
set of non-negotiable process rules, so an autonomous run never has to re-litigate how work happens.
**Verified:** 2026-09-23
**Verified against:** `gsd/phase-01-governance-freeze` = `c288c46` (range `5452f54..c288c46`)
**Status:** gaps_found
**Re-verification:** No — initial verification

> Method note. No claim below is taken from a SUMMARY or from `01-VALIDATION.md`. Every gate command
> recorded in the validation map was re-run in this session; the hooks were exercised live against a
> throwaway worktree and a local bare remote created under the session scratch directory; both RED
> commits were checked out and their test module run. Where a recorded claim and the tree disagree,
> the tree is reported. `origin` was never contacted.

---

## Goal Achievement

### Observable Truths

| #  | Truth (requirement) | Status | Evidence |
|----|---------------------|--------|----------|
| 1  | **R0.1** — the mantra is stated in the canonical file with the `tmp/h<NN>-<slug>/` evidence requirement, and `docs/agent-iteration.md` exists and agrees | ✓ VERIFIED | `rg -ni 'research.*experiment.*decide' AGENTS.md` → `33:- **Research, then experiment, then decide, then implement.**`; AGENTS.md:33-38 carries "recorded evidence under `tmp/h<NN>-<slug>/`, both **before** the decision" and "No \"should work\" — only \"verified by `<command>` → `<output>`\"". `docs/agent-iteration.md` exists (194 lines); R1 and R6 agree on hypothesis-first and probe-first shape. (Its R2 disagrees on the *verify* threshold — booked against R0.9, truth 9.) |
| 2  | **R0.2** — `openspec/` is gone from the root, relocated under `.planning/legacy/openspec/` with a FROZEN banner, content-preserving | ✓ VERIFIED | `ls -d openspec` → ENOENT; `git ls-files \| grep -c '^openspec/'` → `0`; `git ls-files \| grep -c '^\.planning/legacy/openspec/'` → `146`. `git diff-tree --no-commit-id -r -M --name-status f6b0e26 -- openspec .planning/legacy/openspec` → **145 × R100 + 1 × A**, nothing else. `git ls-tree -r f6b0e26^:openspec/specs \| sha256sum` == `git ls-tree -r f6b0e26:.planning/legacy/openspec/specs \| sha256sum` → `3409d411…b6f16f` both sides. Whole-tree blob+path diff pre/post: the only delta is the added `README.md`. Archive dir: exactly 1 `*-phase1-curated-bindings-revert-defaults` match. See "FROZEN Banner Rendering" below. |
| 3  | **R0.3** — OpenSpec process references are retired | ⚠️ PARTIAL → FAILED | AGENTS.md side clean: only `openspec` hit is line 22's `.planning/legacy/` pointer, case-insensitively too; forbidden-token loop clean; all 10 links resolve. But `docs/agent-iteration.md` (an AGENTS.md-declared authoritative source) still instructs `openspec new change`, `/opsx:propose`, `openspec archive <name>`, references `openspec/specs/`, and points at the FROZEN `docs/requirements.md` for "the next item". See gap 3 and HIGH finding 3. |
| 4  | **R0.4** — `AGENTS.md`, ROADMAP step 6 and `PROJECT.md` state ONE git policy with no surviving contradiction, and each place naming `tools/hooks/pre-push` discloses its limits rather than claiming it unbypassable | ✗ FAILED | Hook and its disclosure are sound — all seven limits reproduced live, none under-stated (see "Pre-push Guard: Reproduced Behaviour"). AGENTS.md:42-58, ROADMAP:39-47 and PROJECT.md:74-78,130 agree. **But** `.planning/REQUIREMENTS.md:355` and `:392` still state the superseded policy normatively, and the gate that certified "in every place each states one" never searched that file. See gap 1 and CRITICAL finding 1. |
| 5  | **R0.5** — the research-tooling rule is in the canonical file | ✓ VERIFIED | `rg -q 'codegraph_explore' AGENTS.md` → exit 0. AGENTS.md:72-77 carries `codegraph_explore` / `codegraph explore` before opening files, `wc -l` + `rg -n '<symbol>'` sizing, read-only-the-range, and the `rg`/`fd`/`wc`/`bat`/`sd`/`eza` preference. |
| 6  | **R0.6** — `post-checkout` / `post-commit` exist and the CodeGraph lifecycle actually works, from a single **relative** `core.hooksPath`, failing without aborting | ✓ VERIFIED | `git config --show-origin --get-all core.hooksPath` → exactly one scope, `file:.git/config  tools/hooks` (relative). `git config --get extensions.worktreeConfig` → absent. Proven live, not asserted — see "CodeGraph Lifecycle: Live Proof". Both hooks are advisory by construction: `exit 0` on every path, absence/failure/timeout each warned only. |
| 7  | **R0.7** — the canonical file states that every new GSD plan carries `cross_ai: true` | ✓ VERIFIED | `rg -q 'cross_ai: true' AGENTS.md` → exit 0; AGENTS.md:78-81. |
| 8  | **R0.8** — `AGENTS.md` is canonical, `CLAUDE.md` is reduced to a pointer, `claude_md_path` repointed, and the authoritative-source links all resolve | ✓ VERIFIED | `printf '@AGENTS.md\n' \| cmp -s - CLAUDE.md` → exit 0 (byte-exact, 11 bytes, 1 line). `jq -r .claude_md_path .planning/config.json` → `./AGENTS.md`. All ten AGENTS.md link targets exist (scripted `[ -e ]` over every `](…)`): conventions, agent-iteration, propossal_roadmap, requirements, legacy/openspec, phases, PROJECT, REQUIREMENTS, ROADMAP, STATE. `.claude/conventions.md`, `tools/setup.sh` and `docs/agent-iteration.md` each name `AGENTS.md` with no `CLAUDE.md` residue. |
| 9  | **R0.9** — `AGENTS.md` is internally consistent, each rule in exactly one of the three files, no rule stated twice | ✗ FAILED | Placement rule stated at AGENTS.md:3-11. Commit-granularity rule genuinely unique: `rg -l --hidden --glob '!.planning/**' -- 'one commit per plan' .` → only `./AGENTS.md`. **But** `docs/agent-iteration.md` is a fourth rules file that AGENTS.md declares authoritative and restates three AGENTS.md rules — R2 and R3 with contradicting content — and `.claude/conventions.md:69,75` carries two process rules. See gap 2 and HIGH findings 4 and 5. |
| 10 | **R0.10** — the commit topology on the branch matches the rule | ✓ VERIFIED | Rule stated once (`rg -ci 'one commit per plan' AGENTS.md` → `1`), and `tdd_mode: true` in `.planning/config.json` satisfies R0.10's "must move together". Topology and RED-failure proof: see "Commit Topology" below. One blemish recorded as MEDIUM finding 8 (one of the eight RED-commit tests passes vacuously); it does not break the rule's stated shape (two commits, RED before GREEN, RED touching only `tests/`). |

**Score:** 7/10 truths verified · 1 partial-counted-failed · 2 failed · 0 present-behaviour-unverified

### ROADMAP Success Criteria (11)

| # | Criterion | Status | Evidence |
|---|-----------|--------|----------|
| 1 | Canonical file states research+experiment precede any removal/replacement decision | ✓ | AGENTS.md:33-38 |
| 2 | Canonical file states the git policy explicitly (worktree, one commit per plan, merge when green, no force-push, hook-enforced) | ✓ | AGENTS.md:42-58 — every clause present, including the seven disclosed limits |
| 3 | Authoritative-sources list points at `.planning/`, no OpenSpec process references remaining, still points at `docs/agent-iteration.md` | ✓ (list) / ✗ (target) | The *list* is clean and points at agent-iteration.md; the *target* still teaches the retired process. Booked against R0.3. |
| 4 | Change retired via `--skip-specs`, tree at `.planning/legacy/openspec/`, no root `openspec/` | ✓ | 145×R100+1×A; `specs/` tree hash identical; archive dir present |
| 5 | FROZEN banners open the three history files | ✓ | All three, verbatim `FROZEN — history only; source of truth is \`.planning/\`.` |
| 6 | Canonical file carries the research-tooling rule | ✓ | AGENTS.md:72-77 |
| 7 | New worktree indexed automatically, commit refreshes, failure warns without aborting — **demonstrated, not asserted** | ✓ | Demonstrated in this session; see below |
| 8 | Canonical file states `cross_ai: true` | ✓ | AGENTS.md:78-81 |
| 9 | `AGENTS.md` canonical, `CLAUDE.md` == `@AGENTS.md`, `claude_md_path` repointed | ✓ | `cmp` clean; `./AGENTS.md` |
| 10 | Placement rule stated **and each rule in exactly one file** | ✗ FAILED | Stated, but not true — three violations (gap 2) |
| 11 | Commit-granularity rule stated and appears in exactly one file | ✓ | `rg -ci` = 1; `rg -l --hidden` across the repo finds only `AGENTS.md` |

---

## FROZEN Banner Rendering (R0.2)

Each of the three files has the identical safe structure — heading on line 1, **blank** line 2,
a two-line `>` blockquote on lines 3-4, **blank** line 5, prose from line 6. Verified per file:

| File | L1 `# ` | L2 blank | L3-L4 `>` | L5 blank | L1 is a blockquote? |
|------|---------|----------|-----------|----------|---------------------|
| `.planning/legacy/openspec/README.md` | yes | yes | 2/2 | yes | no |
| `docs/requirements.md` | yes | yes | 2/2 | yes | no |
| `docs/propossal_roadmap.md` | yes | yes | 2/2 | yes | no |

No CommonMark lazy continuation is possible in either direction: no blockquote precedes the banner
(so it cannot be merged *into* an adjacent quote), and line 5 is blank (so the following paragraph
cannot be lazily absorbed *into* the banner). The banner renders as its own block quote.

Note the recorded gate for this row (`sed -n '1p' … '^# '` and `sed -n '3p' … '^> '`) checks only
lines 1 and 3; it would not have detected a non-blank line 2 or 5. The tree happens to be correct,
so this is a gate-strength observation, not a defect.

## Pre-push Guard: Reproduced Behaviour (R0.4, R0.7-adjacent)

Run against a bare repo created under the session scratch directory. `origin` was never contacted.

| # | Scenario | Result | Expected by disclosure |
|---|----------|--------|------------------------|
| T1 | First-ever push of `master` to an empty remote ref | REJECTED — `provenance cannot be established` | limit 6 ✓ |
| T2 | Same, with `KITTI_ALLOW_MASTER_PUSH=1` | ALLOWED, announced: `KITTI_ALLOW_MASTER_PUSH=1 honoured; first push of refs/heads/master allowed` | limit 2 ✓ |
| T3 | New `gsd/*` branch first push | ALLOWED, silent | by design ✓ |
| T4 | `--no-ff` merge of a `gsd/*` branch into `master`, pushed | ALLOWED | by design ✓ |
| T5 | Commit authored directly on `master`, pushed | REJECTED — `provenance — ee19da631ed6 is in no gsd/* branch` | guard 2 ✓ |
| T6b | `git push --force` after an amend | REJECTED — `non-fast-forward (history rewrite)` | guard 1 ✓ |
| T6c | Same `--force` **with** `KITTI_ALLOW_MASTER_PUSH=1` | still REJECTED | "guard 1 stays unconditional" ✓ |
| T7 | `git push origin :master` | REJECTED — `master is not a deletable ref` | limit 7 ✓ |
| T7b | `git push origin :gsd/phase-99-probe` | ALLOWED — `- [deleted]` | limit 7 ✓ |
| T8 | Squash-merge of a `gsd/*` branch into `master`, pushed | REJECTED — `provenance` | limit 3 ✓ |
| T9 | `git push --no-verify` | ALLOWED (hook never runs) | limit 1 ✓ |
| U4 | `git branch -f gsd/fabricated HEAD` on a direct-on-master commit, then push | ALLOWED | disclosed in substance: header lines 21-22 "judges provenance by reachability", plus "compliance guard for cooperating agents, not a security boundary" ✓ |
| **U2** | **`git push origin master:refs/heads/main` carrying the same commit T5 rejected** | **ALLOWED** | **NOT DISCLOSED — see MEDIUM finding 7** |

**Verdict on the disclosure:** the seven listed limits are accurate and none is under-stated — each
was reproduced, and the escape hatch really does skip guard 2 only. One bypass is missing from the
list (U2).

## CodeGraph Lifecycle: Live Proof (R0.6)

`core.hooksPath` = **relative** `tools/hooks`, one scope only (`file:.git/config`);
`extensions.worktreeConfig` absent. A throwaway worktree was cut under the session scratch
directory on a throwaway branch, then removed:

1. `git worktree add -b verify/throwaway-p1 <scratch>/wt-r06 HEAD` → the NEW worktree contains
   `.codegraph/codegraph.db`, 3 563 520 bytes, timestamped at the `worktree add`. `post-checkout`
   resolved out of the invoking worktree and indexed the new one — the relative-path behaviour the
   hook's header documents.
2. A commit inside that worktree printed, verbatim:
   `[post-commit] CodeGraph index synchronised for this worktree`
3. Cleanup: `git worktree remove --force` + `git branch -D verify/throwaway-p1` +
   `git worktree prune`. `git worktree list` → **one entry**.

## Commit Topology (R0.10)

Range `5452f54..gsd/phase-01-governance-freeze` (25 commits).

| Plan | Type | Commits | Shape | RED→GREEN ancestry | RED file scope |
|------|------|---------|-------|--------------------|----------------|
| 01-01 | tdd | `178cd4b` `test(01-01)` → `badb4d3` `feat(01-01)` | pair ✓ | `merge-base --is-ancestor` → YES | only `tests/unit/test_git_hooks.py` ✓ |
| 01-02 | tdd | `706a694` `test(01-02)` → `33cf0e9` `feat(01-02)` | pair ✓ | YES | only `tests/unit/test_git_hooks.py` ✓ |
| 01-03 | execute | `f6b0e26` `chore(01-03)` | exactly one ✓ | — | — |
| 01-04 | execute | `27a152a` `docs(01-04)` | exactly one ✓ | — | — |
| 01-05 | execute | `508087c` `feat(01-05)` | exactly one ✓ | — | — |

**RED commits genuinely failed** — proven by checking each out into a throwaway worktree and running
the module with the repo venv's interpreter (`REPO_ROOT` in the test file resolves to the worktree,
so the hooks under test are the ones at that commit):

- at `178cd4b`: `tools/hooks/` does not exist; `pytest tests/unit/test_git_hooks.py -q` → **`10 failed in 0.20s`** (0 passed).
- at `706a694`: `tools/hooks/pre-push` exists, the two new hooks do not; → **`7 failed, 11 passed in 0.52s`**.

Non-plan commits in the range are `(01)`-scoped planning/housekeeping (`aad464b` SUMMARY correction,
`05c2722` plan+map gate fixes, `c352dc6`, `c288c46` phase close, and the pre-execution review
commits). None is plan implementation work, so the one-commit-per-plan rule holds.

## Phase Gate: Independently Re-run

| Gate | Command | Result | Expected |
|------|---------|--------|----------|
| Full suite | `make test` | `311 passed, 70 skipped in 2.70s`, exit 0 | 311/70 ✓ |
| Hook module | `uv run pytest tests/unit/test_git_hooks.py -q` | `18 passed in 2.51s`, exit 0, zero `skipped` | 18 passed ✓ |
| Health | `make doctor` | exit 2; 8 PASS, **1 FAIL** (`completion: register-python-argcomplete not on PATH`), 1 SKIP (`remote-control: no managed kitty socket found`) | exactly one FAIL, that one ✓ |
| Map completeness | 3-clause gate from `01-VALIDATION.md` | all three exit 0; 23 rows, 23 verdicts, no `⬜ pending` row | ✓ |
| Carve-out marker | `rg -n 'PHASE-1-DOCTOR-CARVE-OUT' AGENTS.md .planning/ROADMAP.md .planning/PROJECT.md` | exit 1 — **absent from all three**; the only repo-wide hits are `.planning/REQUIREMENTS.md:116-117` and `01-05-PLAN.md` recording it as *prohibited* | ✓ |

`make doctor` red is accepted: the single failure is R1.1, owned by Phase 2, and Phase 1 deferred its
merge instead of writing a carve-out. The deferral is recorded consistently in `AGENTS.md:45-46`,
`.planning/PROJECT.md:74-78` and `.planning/STATE.md`, and it defers the merge rather than lowering
the bar. One observation: a phase-specific, dated-in-effect sentence inside a file whose header
declares "Universal, non-negotiable rules" will go stale the moment Phase 2 lands — it should be
removed by the merge that satisfies it (LOW finding 11).

## Anti-Pattern Scan

The 15 non-`.planning/` files changed in `5452f54..c288c46` were scanned for `TBD|FIXME|XXX`
(blocker class) and `TODO|HACK|PLACEHOLDER` (warning class): **zero matches in either class**. No
stub returns, no empty handlers, no hardcoded-empty data. The three hook files are substantive
(149 / 71 / 84 lines), each with an argv/stdin contract and an enumerated limits block.

Residual `wc -l | rg -x 'N'` gate forms in `01-VALIDATION.md`: the 4 hits are all inside
"replaces the earlier form" annotations, not in live gate cells — the family really was remediated.
The `--no-commit-id` fix is present and I reproduced why it was needed: without it,
`git diff-tree -r -M --name-status f6b0e26` emits the commit SHA as its first line, matching neither
`R100` nor `A`, so the gate would have failed on correct work.

---

## Hollow Gates — Passing Without Testing

The phase catalogued six ways a gate can pass without testing anything. It shipped three more, two
of which are demonstrated by planting a violation and showing the gate still green.

### HG-1 (CRITICAL) — file list narrower than the rule's footprint, plus a case-sensitive absence pattern

Gate, from `01-VALIDATION.md` row `01-05-T2`, secure behaviour *"The planning docs state the same
policy as `AGENTS.md`, in every place each states one"*:

```bash
for F in .planning/ROADMAP.md .planning/PROJECT.md; do
  test -f "$F" || exit 1
  if rg -qi -- 'commits? per task|per-task commit|task commit' "$F"; then exit 1; fi
done
test -f .planning/PROJECT.md && ! rg -q 'agents push a feature branch only' .planning/PROJECT.md
```

Re-run now, verbatim: **both clauses exit 0.** The violation is already in the tree, unplanted:

```
$ rg -ni -- 'commits? per task|per-task commit|task commit' .planning/REQUIREMENTS.md
355:- **Git gate**: commit per task, push branch `gsd/<phase>`; never merge to `master`, force-push,
$ rg -ni 'agents push a feature branch only' .planning/REQUIREMENTS.md
392:| Merging to `master` | Agents push a feature branch only; integration is the owner's call (R0.4) |
```

Adding `.planning/REQUIREMENTS.md` to the file list flips the first clause to exit 1. The second
clause needs `-i` as well: PROJECT.md's old sentence read lowercase `agents push…` mid-sentence, so
the lowercase pattern matched there; REQUIREMENTS.md:392 starts a table cell with capital `Agents`,
which that pattern can never match. Two independent defects, either of which alone would have hidden
the violation.

### HG-2 (HIGH) — default-excluded search set (hidden directories)

Gate, from row `01-04-T2`, asserting the commit-granularity rule lives *"nowhere else outside
`.planning/`, which is what ROADMAP criterion 11 actually requires"*:

```bash
test "$(rg -l --glob '!.planning/**' -- 'one commit per plan' . )" = './AGENTS.md'
```

`rg` skips hidden directories unless `--hidden` is passed, so `.claude/` is outside the search set —
and `.claude/conventions.md` is **git-tracked** and is one of exactly three files the R0.9 placement
rule governs. Planted in a scratch replica (never in the repo):

```
# replica: AGENTS.md states the rule; .claude/conventions.md is clean
$ rg -l --glob '!.planning/**' -- 'one commit per plan' .   → ./AGENTS.md          GATE exit 0

# plant a duplicate: append "Work lands as one commit per plan." to .claude/conventions.md
$ rg -l --glob '!.planning/**' -- 'one commit per plan' .   → ./AGENTS.md          GATE exit 0  ← HOLLOW
$ rg -l --hidden --glob '!.planning/**' -- 'one commit per plan' .
  ./.claude/conventions.md
  ./AGENTS.md                                                                      ← would have caught it
```

ripgrep 15.2.0. The real tree is clean (verified with `--hidden`), so criterion 11 genuinely holds —
but the gate that certifies it cannot see the one file most likely to receive a duplicated rule.

### HG-3 (MEDIUM) — case-sensitive absence over a capitalised subject

Gate, from row `01-04-T1`, *"every remaining hit must be a `.planning/legacy/` history reference,
never a process pointer"*:

```bash
rg -q '\.planning/legacy/openspec/' AGENTS.md && ! rg -n 'openspec' AGENTS.md | rg -qv 'legacy'
for T in 'openspec list' 'openspec archive' 'openspec validate' '.claude/skills/openspec' 'opsx'; do
  if rg -q -- "$T" AGENTS.md; then exit 1; fi
done
```

Both halves are case-sensitive, while the retired system's own name is `OpenSpec`. In a scratch
replica: a planted lowercase `openspec validate` process reference is caught (exit 1); the same
reference written the way the project actually writes it — *"Follow the OpenSpec process: run
`OpenSpec validate` before every change."* — passes **both** the line check and the forbidden-token
loop. The live consequence is real: `docs/agent-iteration.md` spells it `OpenSpec` in every one of
its process instructions (HIGH finding 3), and no R0.3 gate is case-insensitive or scoped beyond
`AGENTS.md`.

### Also noted (not hollow, but weaker than advertised)

- The forbidden-phrasing alternation `commits? per task|per-task commit|task commit` misses trivial
  rewordings — `commit per every task`, `commit once per task` both pass. Inherent to lexical gates;
  recorded so a future author does not read it as semantic.
- Row `01-03-T2`'s banner gate inspects lines 1 and 3 only (see "FROZEN Banner Rendering").
- Row `01-04-T3`'s pointer gate over `docs/agent-iteration.md` checks only that it names `AGENTS.md`
  and not `CLAUDE.md`; it says nothing about that file's content, which is where the contradictions
  live.

---

## Findings, Ranked

### CRITICAL 1 — `.planning/REQUIREMENTS.md` still states the superseded git policy, and the gate that denied it is hollow

`.planning/REQUIREMENTS.md:355` is a normative universal gate reading *"**Git gate**: commit per
task, push branch `gsd/<phase>`; never merge to `master`, force-push, amend pushed commits, or push
`master` (R0.4)"*, and `:392` is an Out-of-Scope row reading *"| Merging to `master` | Agents push a
feature branch only; integration is the owner's call (R0.4) |"*. Both cite R0.4 while stating its
opposite; :355 additionally states the per-task granularity R0.10 supersedes. This is the **first**
entry in AGENTS.md's own authoritative-sources list, and AGENTS.md:26-28 instructs an agent that when
code conflicts with `.planning/REQUIREMENTS.md`, *the code* is refactored — so a future agent
following the canonical file is routed straight into the superseded policy. The 01-05-T2 gate that
certified "in every place each states one" never searched that file (HG-1). Both lines are present at
`c288c46`, inside the Phase 1 range; `.planning/PROJECT.md` and `.planning/STATE.md` were both
corrected, so this is an omission, not a decision.

*Fix (small, Phase 2 can absorb it): rewrite :355 to point at AGENTS.md's git-policy bullet; replace
:392 the way PROJECT.md:74-78 was; widen row 01-05-T2 to include REQUIREMENTS.md and make both
absence patterns `rg -qi`.*

### HIGH 2 — the uniqueness gate for the commit-granularity rule cannot see `.claude/conventions.md`

See HG-2. Demonstrated by planting. The tree is currently clean, so this is a latent gate defect
rather than a live violation — but it guards ROADMAP criterion 11, and the file it cannot see is one
of the three the placement rule names. One word (`--hidden`) fixes it.

### HIGH 3 — `docs/agent-iteration.md` still teaches the retired OpenSpec workflow

An AGENTS.md-declared authoritative source (AGENTS.md:21) instructs: *"Read this before opening
another OpenSpec change or picking the next item from `docs/requirements.md`"* (lines 4-5, and that
file is FROZEN); *"**Open an OpenSpec change** for the item… Use `openspec new change
<kebab-case-name>` and the `/opsx:propose` skill"* with capabilities landing *"under
`openspec/specs/`"* (113-119); *"**Archive** the OpenSpec change with `openspec archive <name>`"*
(164-165); *"open a follow-up OpenSpec change"* (192). None can run — 01-03 removed the openspec root,
which `01-VALIDATION.md`'s own correction 1 states is D-02's intended end state. R0.3's clause
"OpenSpec process references are retired" is unqualified, so this is in Phase 1's scope, and **no
later phase owns this file**: R6.1 names CLI help, docstrings, README, scene example headers and the
Stack section. This is the phase goal — "never has to re-litigate how work happens" — missed head-on.

### HIGH 4 — `docs/agent-iteration.md` R2 contradicts AGENTS.md's verify rule

R2 (lines 15-20): *"A behavior is \"ready\" only when `make doctor` and `KITTI_INTEGRATION=1 make
test` both exit 0 and their output is captured"*. AGENTS.md:82-87: both commands *"captured rather
than green … a captured-but-red run satisfies this rule and still blocks the merge"*. Two files,
one rule, incompatible thresholds — and Phase 1 closed on the AGENTS.md reading with `make doctor`
red, which R2 says is not "ready". R2 also pulls in `KITTI_INTEGRATION=1`, which the Universal Phase
Gate does not require. An R0.9 violation with immediate operational consequences.

### HIGH 5 — `docs/agent-iteration.md` R3 states the pre-widening shell allow-list

R3 (lines 22-27): *"extracted into `tools/<name>.sh` (bash, only allowed in bootstrap territory)"*.
The file never mentions `tools/hooks/` (`rg` → no match). Plan 01-01 widened the allow-list "in all
four places that state it" — `badb4d3` touched `README.md`, `.planning/PROJECT.md`, `CLAUDE.md`
(later moved to `AGENTS.md`) and `tools/setup.sh`. This is a fifth place, and `27a152a` opened the
file only to rename the `CLAUDE.md` pointer. As that authoritative document reads today, the three
hook files this phase created are outside the allow-list.

### MEDIUM 6 — `README.md` still describes the pre-freeze repo, with a broken link

Line 13-15: *"**Status**: Phase 0 → Phase 1 in flight. The first OpenSpec change
([`bootstrap-foundation-phase1-popos`](openspec/changes/bootstrap-foundation-phase1-popos/))"* — the
**only broken link in the file** (scripted `[ -e ]` over every relative target). Line 210:
`├── openspec/              # active and archived change proposals` in the root layout tree, where it
no longer exists, and `.planning/` is not listed. Line 229: *"Each lands as its own OpenSpec
change."* Deferred to Phase 8 / R6.1, which names README explicitly — but the broken link and the
layout entry are direct consequences of Phase 1's own `git mv`, and README is one of the three files
the R0.9 placement rule governs.

### MEDIUM 7 — undisclosed pre-push bypass: guard 2 is keyed on the *remote* ref name

`git push origin master:refs/heads/main` carrying the exact commit that `git push origin master`
rejects is **ALLOWED** (reproduced, U2 above). Guard 2 tests `remote_ref == refs/heads/master`
(`tools/hooks/pre-push:109`) and the empty-remote branch tests the same (`:83`), so any other remote
ref name skips provenance entirely. Guard 1 still applies there, so the pushed ref cannot later be
rewritten, and `origin`'s integration branch is `master` — so real-world impact is a stray remote
branch, not corrupted `master`. But the hook's header claims *"every one of these was established by
execution"* for a list of seven, and `AGENTS.md:50-57` reproduces that list as *"All its limits
disclosed"*. It is eight.

### MEDIUM 8 — the 01-02 RED commit is not fully red: one of its eight tests passes vacuously

`706a694` adds eight test functions; seven fail at that commit. `test_post_checkout_ignores_ordinary_
branch_switch` asserts the **absence** of an `init` argv (`assert not initialised`), which holds
trivially when `tools/hooks/post-checkout` does not exist — so it passes with no implementation at
all. R0.10's amendment requires "a RED commit containing only the new tests… at which those tests
**fail**". Separately, `01-VALIDATION.md` row `01-02-T1` records *"the module shows `4 failed, 14
passed` at this point"*; measured at that commit: **`7 failed, 11 passed`**. Both numbers are wrong,
and the phase that catalogued existence-dependent vacuous passes shipped one inside the very commit
meant to prove failure.

### MEDIUM 9 — `.claude/conventions.md` vs the `Makefile`: confirmed, owned by R6.3, but **ungated**

Confirmed: `.claude/conventions.md:59-69` requires `make format`, `make validate`, `make test-unit`,
`make test-integration` and states *"Never commit code that fails `make validate`"*; the `Makefile`'s
`.PHONY` line is `help install setup clean doctor test uninstall prune hooks` — none of the four
exists. **Correction to the standing assumption that no requirement owns this:** `R6.3` does, and the
Traceability table maps it to Phase 8. The live defect is one level up — Phase 8 declares
`**Requirements**: R6.1, R6.2, R6.3` but writes success criteria only for R6.1, R6.2 and the
frozen-specs clause that REQUIREMENTS.md itself files under *Out of Scope*. **R6.3 has no success
criterion and will run ungated.** Recommend a one-line ROADMAP edit adding a Phase 8 criterion for
R6.3; Phase 2 is already editing that file. Note also that R6.1 and Phase 8 criterion 1 both name
*"the `CLAUDE.md` \"Stack\" section"*, which no longer exists — Phase 8's own criterion carries a
pointer Phase 1 invalidated.

### MEDIUM 10 — verdict on `docs/prds/…-prd.md:48`: the deferral is survivable, the reasoning is not

Lines 48-50 carry the original R0.4 verbatim: *"agents MAY commit per task and push a feature branch
(`gsd/<milestone-or-phase>`); MUST NOT merge to `master`, force-push, amend pushed commits, or push
`master`."* The file carries **no banner of any kind**, and `.planning/REQUIREMENTS.md:4-5` names it
`**Source:**`.

Plan 01-05's reason — rewriting a dated input document destroys the provenance REQUIREMENTS.md cites
— **argues for the remedy Phase 1 already had in hand, not against acting.** `docs/requirements.md`
and `docs/propossal_roadmap.md` are dated input documents too, and R0.2's answer for both was a
FROZEN banner: a prepended header that changes not one word below it. The same one-line,
provenance-preserving banner ("superseded by `.planning/REQUIREMENTS.md` R0.4 as reworded
2026-09-22") costs nothing, destroys nothing, and closes the contradiction. Leaving the PRD as the
only unbannered superseded source, while REQUIREMENTS.md names it as its source, is the weaker of the
two options that were available.

That said: **it is materially less dangerous than CRITICAL 1**, and deferring it is acceptable. A
document titled "PRD v1.0" self-evidently reads as a dated input; `.planning/REQUIREMENTS.md` reads
as the live authority. Accept the deferral to Phase 8 / R6.1 **and** apply the banner there —
do not accept the reasoning, because the same reasoning would have blocked R0.2.

### LOW 11 — phase-completion bookkeeping is inconsistent with the phase being closed

- `.planning/REQUIREMENTS.md`: R0.1–R0.10 checkboxes are all still `- [ ]`, and the Traceability
  Status column reads `Pending` for all ten.
- `.planning/ROADMAP.md:61`: `- [ ] **Phase 1: Governance & Freeze**` still unticked, and all five
  plan checkboxes at :98-112 still `- [ ]`. `c288c46` flipped only the progress-table row
  (`5/5 | Complete (merge deferred) | 2026-09-23`).
- `.planning/STATE.md`: `state_head: 508087c…` is stale against `c288c46`.
- `.planning/REQUIREMENTS.md` **Coverage** block claims *"v1 requirements: 36 total / Mapped: 36"*
  against a Traceability table of 53 rows; `Last updated: 2026-09-22`, before R0.11, R0.12 and R6.3
  were added during this phase.
- `AGENTS.md:45-46`'s phase-specific sentence ("Phase 1's branch merges after Phase 2's R1.1 turns
  `make doctor` green") sits inside a file whose header declares universal, non-negotiable rules; it
  should be deleted by the merge that satisfies it.

### LOW 12 — `01-VALIDATION.md` frontmatter was never advanced

`status: draft`, `nyquist_compliant: false`, `wave_0_complete: false` — while all 23 rows are ✅, the
Map Completeness Gate is green, and the phase is closed. The file's own comment documents the
lifecycle `draft → validated`.

---

## Requirements Coverage

| Requirement | Source Plan | Status | Evidence |
|-------------|-------------|--------|----------|
| R0.1 | 01-04 | ✓ SATISFIED | AGENTS.md:33-38; `docs/agent-iteration.md` present and agreeing on hypothesis shape |
| R0.2 | 01-03 | ✓ SATISFIED | 145×R100 + 1×A; `specs/` tree hash identical; 3 banners, all structurally sound |
| R0.3 | 01-04 | ✗ PARTIAL | AGENTS.md clean; `docs/agent-iteration.md` still teaches the retired workflow |
| R0.4 | 01-01, 01-04, 01-05 | ✗ BLOCKED | Hook + disclosure sound (12 scenarios reproduced); REQUIREMENTS.md:355,392 contradict |
| R0.5 | 01-04 | ✓ SATISFIED | AGENTS.md:72-77 |
| R0.6 | 01-02, 01-05 | ✓ SATISFIED | Relative `core.hooksPath`; index built + synced live in a throwaway worktree |
| R0.7 | 01-04 | ✓ SATISFIED | AGENTS.md:78-81 |
| R0.8 | 01-04 | ✓ SATISFIED | `cmp` clean; `claude_md_path: ./AGENTS.md`; 10/10 links resolve |
| R0.9 | 01-04, 01-05 | ✗ BLOCKED | `docs/agent-iteration.md` R1/R2/R3; `.claude/conventions.md:69,75` |
| R0.10 | 01-04, 01-05 | ✓ SATISFIED | Topology verified on the range; both REDs run and failed; `tdd_mode: true` |

No orphaned requirements: ROADMAP Phase 1 declares R0.1–R0.10 and the plans collectively claim all
ten.

---

## Gaps Summary

The mechanism Phase 1 built is real and I verified it by running it, not by reading about it. The
pre-push guard rejects all five things it claims to reject and honours its one escape hatch exactly
where it says; all seven disclosed limits reproduce; the CodeGraph hooks index a new worktree and
sync on commit, from a single relative `core.hooksPath`, and warn without aborting; the `openspec/`
relocation is a byte-exact 145-file rename with three well-formed FROZEN banners; the commit topology
matches the two-commit TDD rule with both RED commits genuinely red; `AGENTS.md` is canonical,
`CLAUDE.md` is eleven bytes, and every authoritative link resolves. `make test`, the hook module and
`make doctor` all reproduce their recorded outputs exactly, and no debt marker survives anywhere in
the fifteen files the phase touched.

What did not land is the *documentary* half of the goal — "exactly one authoritative source of intent
and one set of non-negotiable process rules". Three documents still contradict the rules this phase
installed, and each was missed by a gate that was scoped too narrowly to see it:

1. `.planning/REQUIREMENTS.md` — the top authoritative source — states the superseded git policy
   twice, normatively, citing R0.4 while asserting its opposite. The gate that denied this searched
   two files and not that one, with a pattern that could not have matched it anyway.
2. `docs/agent-iteration.md` — an AGENTS.md-declared authoritative source — teaches the retired
   OpenSpec workflow with commands that cannot run, and restates two AGENTS.md rules with
   contradicting content, including the verify threshold Phase 1 itself relied on to close with
   `make doctor` red. No later phase owns this file.
3. `README.md` still describes the pre-freeze repo, with the file's only broken link pointing into
   the directory this phase removed. This one is legitimately Phase 8's.

Root cause, common to all three: every governance gate in this phase asserts a property of a
*named file*, never of the *repository*. A rule that must hold "in every place that states one"
cannot be gated by enumerating two of the places. The three hollow gates in this report all fail the
same way, and two of them fail additionally on `rg` defaults — case sensitivity and hidden-directory
exclusion. The remedy is cheap and belongs in Phase 2: widen the file lists to the repo, add
`--hidden`, and add `-i`.

None of this is unrecoverable, and none of it is large. Gaps 1 and 3 are prose edits to two files
plus three flags in `01-VALIDATION.md`; gap 2 is a reconciliation of four paragraphs. Phase 2 runs
next and can absorb all of it before the deferred merge to `master`.

---

_Verified: 2026-09-23_
_Verifier: Claude (gsd-verifier)_

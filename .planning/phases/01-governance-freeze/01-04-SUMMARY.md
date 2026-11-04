---
phase: 01-governance-freeze
plan: 04
subsystem: infra
tags: [AGENTS.md, CLAUDE.md, instruction-file, claude_md_path, git-policy, commit-granularity, governance]
type: execute

# Dependency graph
requires:
  - "01-01 — tools/hooks/pre-push installed, shell allow-list widened to name tools/hooks/ in all four places, core.hooksPath wired"
  - "01-02 — tools/hooks/post-commit and post-checkout exist, so the Stack allow-list naming all three hooks is true on disk"
  - "01-03 — openspec archived and relocated to .planning/legacy/openspec/, so the authoritative-sources list can point at a real legacy tree"
provides:
  - "AGENTS.md — the canonical instruction file: preamble with the three-way placement rule (R0.9), rewritten Authoritative sources (R0.3), the six new rules (R0.1, R0.4, R0.5, R0.7, R0.10), Stack carried verbatim, Pluggable rules carried verbatim"
  - "CLAUDE.md — the one-line @AGENTS.md import (byte-exact, R0.8)"
  - ".planning/config.json — claude_md_path repointed to ./AGENTS.md (R0.8)"
  - ".claude/conventions.md, tools/setup.sh, docs/agent-iteration.md — stale CLAUDE.md pointers repointed"
affects:
  - "01-05 — runs agent-md-refactor over AGENTS.md and gates ROADMAP/PROJECT alignment with this file's policy text"
  - "Every later phase — reads AGENTS.md as the canonical rule set"

# Actuals
actuals:
  tokens: 1900
  tasks: 3
  commits: 1
  plan_head_before: aad464b

requirements-completed: [R0.1, R0.3, R0.4, R0.5, R0.7, R0.8, R0.9, R0.10]

# Metrics
duration: 35min
completed: 2026-09-23
status: complete
---

# Phase 1 Plan 04: AGENTS.md as the canonical instruction file — Summary

**`AGENTS.md` is now the one canonical general-rule entry point carrying the mantra, the git policy
with all seven pre-push limits, the commit-granularity rule with the `type: tdd` exception,
research-tooling, cross-AI-by-default and the placement rule; `CLAUDE.md` is the byte-exact
`@AGENTS.md` import; `claude_md_path` and every stale `CLAUDE.md` pointer in non-frozen tracked
files are repointed at the canonical file.**

## Performance

- **Duration:** ~35 min
- **Tasks:** 3 of 3
- **Files:** 6 (1 created, 5 modified)
- **Suite:** `311 passed, 70 skipped` — unchanged from baseline

## Task outcomes

| Task | Outcome |
|------|---------|
| 1 — Create `AGENTS.md`: migrate six structural elements, rewrite Authoritative sources and Stack | Done. H1 `# kitty-setup — Agent Rules` on line 1; preamble expanded into the three-way placement rule; Authoritative sources rewritten to point at `.planning/`; the three stale bullets deleted; Stack carried across verbatim (verified byte-identical in substance to `CLAUDE.md`'s as plan 01-01 left it); Pluggable rules carried word for word; Universal rules left as the migrated subset. All 8 automated gates PASS. |
| 2 — Add the six new rules to Universal rules | Done. Mantra (R0.1), Git policy (R0.4) with all seven guard limits disclosed, Commit granularity (R0.10) with the `type: tdd` exception written without repeating `one commit per plan`, Research tooling first (R0.5, no bulk-rename sentence — `01-03-SUMMARY.md`'s verdict was that `codegraph sync -q` sufficed), Cross-AI by default (R0.7), and the Verify gate extended to name both `make doctor` and `make test` as captured, not green. Bullets ordered as one list: process rules (mantra, git policy, commit granularity) before working habits, verification and questions last. All 8 automated gates PASS. |
| 3 — Repoint consumers, capture phase gate, single commit | Done. `CLAUDE.md` → `@AGENTS.md` (byte-exact via `cmp`); `claude_md_path` → `./AGENTS.md`; `.claude/conventions.md` line 5 names `AGENTS.md`; `tools/setup.sh` header cites `AGENTS.md`; `docs/agent-iteration.md` line 170 names the planning-primacy rule in `AGENTS.md`. `make test` green and `make doctor` captured (not gated). The plan's single commit is listed at the end. All 8 automated gates PASS. |

## What was migrated, verbatim / repointed / deleted

- **Carried verbatim:** `English everywhere`, `Re-read before edit`, `Hypothesis before
  implementation`, `Questions are not orders`; the whole `## Stack` paragraph; the whole
  `## Pluggable rules` section; the preamble's first three lines.
- **Repointed:** `Skill outputs land on disk` — its parenthetical now reads `(under `.planning/`
  or `docs/`)` instead of `(under `openspec/changes/<id>/` or `docs/`)`.
- **Extended:** `Verify before declaring done` — now says "both commands, captured rather than
  green", because `make doctor` is not green until Phase 2's R1.1 lands.
- **Deleted:** `No auto-commit` (replaced by the new Git policy and Commit granularity rules) and
  `Spec-first` (per D-09); the three stale Authoritative-sources bullets (v1 scope, roadmap,
  active OpenSpec change) per R0.3.

## The three-reason allow-list justification

`01-01-SUMMARY.md`'s "Why the allow-list was widened rather than hook logic relocated into a
`my-kitty` subcommand" records the three reasons (D-08 locks the location; the relocation route
pays the same amendment cost; a hook must run with no Python runtime guaranteed). This SUMMARY
references rather than restates them; the rationale lives in exactly one place per D-15.

## Remaining bootstrap-parenthetical inaccuracy — disclosed, Phase 8 / R6.1 owns it

The `## Stack` paragraph's bootstrap parenthetical was carried across **unchanged** and still
claims the upstream-installer call and the shell-rc PATH edit dispatch happen with the scripts
rather than delegating to Python — both behaviours are Python now. `01-CONTEXT.md` defers exactly
that to Phase 8, requirement R6.1, and this plan does not fix it (the must-have is scoped to the
shell **allow-list** being true, which it is). The overall Stack passage is therefore *not*
section-wide true, and no document in this plan claims it is.

## Bulk-rename sentence: NOT added to the tooling rule

`01-03-SUMMARY.md`'s verdict is that `codegraph sync -q` in `post-commit` is sufficient for a bulk
rename (new paths present, zero stale `openspec/` entries, `pendingChanges` all-zero); no
`codegraph index -q` rebuild was needed. The "bulk directory rename needs a manual
`codegraph index -q`" sentence was therefore **not** added to the Research-tooling rule.

## Gate results

### Task 1 (8 gates)

| # | Command | Result |
|---|---------|--------|
| 1 | `test "$(sed -n '1p' AGENTS.md)" = '# kitty-setup — Agent Rules'` | PASS — `# kitty-setup — Agent Rules` on line 1 |
| 2 | `rg -q '\.planning/legacy/openspec/' AGENTS.md && ! rg -n 'openspec' AGENTS.md \| rg -qv 'legacy'` | PASS — positive legacy path present; the only `openspec` line also carries `legacy` |
| 3 | `test -f AGENTS.md && for T in 'openspec list' 'openspec archive' 'openspec validate' '\.claude/skills/openspec' 'opsx'; do if rg -q -- "$T" AGENTS.md; then exit 1; fi; done` | PASS — none of the five retired-process tokens appears |
| 4 | `rg -q 'docs/agent-iteration\.md' AGENTS.md` | PASS |
| 5 | `rg -q 'tools/hooks' AGENTS.md && rg -q 'pre-push' && rg -q 'post-commit' && rg -q 'post-checkout'` | PASS — allow-list names the directory and all three hook files |
| 6 | `rg -q 'agent-md-refactor' AGENTS.md && rg -q 'crafting-effective-readmes' AGENTS.md` | PASS |
| 7 | `test -z "$(git diff --numstat HEAD -- CLAUDE.md)"` | PASS — `CLAUDE.md` untouched during task 1 (verified before task 3) |
| 8 | Stack carried verbatim | PASS — `diff <(sed -n '42,57p' CLAUDE.md) <(AGENTS.md Stack body)` → empty; formatted Stack verified identical after writing |

### Task 2 (8 gates)

| # | Command | Result |
|---|---------|--------|
| 1 | `rg -ni 'research.*experiment.*decide' AGENTS.md` | PASS — `- **Research, then experiment, then decide, then implement.**` |
| 2 | `test "$(rg -ci 'one commit per plan' AGENTS.md)" = '1'` | PASS — count 1 |
| 3 | `test "$(rg -l --glob '!.planning/**' -- 'one commit per plan' . )" = './AGENTS.md'` | PASS — prints `./AGENTS.md` |
| 4 | `rg -q 'cross_ai: true' AGENTS.md` | PASS |
| 5 | `rg -q 'codegraph_explore' AGENTS.md` | PASS |
| 6 | `for L in 'no-verify' 'KITTI_ALLOW_MASTER_PUSH' 'squash' 'cherry-pick' 'first' 'delet'; do rg -qi -- "$L" AGENTS.md \|\| exit 1; done` | PASS — all six disclosure keywords present |
| 7 | `rg -q 'make doctor' AGENTS.md && rg -q 'make test' AGENTS.md` | PASS |
| 8 | `rg -q 'gsd/phase-\{phase\}-\{slug\}' AGENTS.md && rg -q 'core\.hooksPath' AGENTS.md` | PASS |

### Task 3 (pre-commit gates)

| # | Command | Result |
|---|---------|--------|
| 1 | `printf '@AGENTS.md\n' \| cmp -s - CLAUDE.md` | PASS — `@AGENTS.md` plus exactly one trailing newline, byte-for-byte |
| 2 | `test "$(jq -r .claude_md_path .planning/config.json)" = './AGENTS.md'` | PASS |
| 3 | `jq -e . .planning/config.json >/dev/null` | PASS — valid JSON |
| 4 | `git diff --numstat HEAD -- .planning/config.json` | PASS — `1 1` |
| 5 | `test -f .claude/conventions.md && ! rg -q 'CLAUDE' .claude/conventions.md` | PASS — no surviving `CLAUDE` |
| 6 | `rg -q 'AGENTS\.md' .claude/conventions.md` | PASS |
| 7 | `git diff --numstat HEAD -- .claude/conventions.md` | PASS — `1 1` |
| 8 | `rg -q 'AGENTS\.md' tools/setup.sh && ! rg -q 'CLAUDE\.md' tools/setup.sh` | PASS |
| 9 | `rg -q 'AGENTS\.md' docs/agent-iteration.md && ! rg -q 'CLAUDE\.md' docs/agent-iteration.md` | PASS |

### Plan-level `<verification>`

| # | Command | Result |
|---|---------|--------|
| 1 | `printf '@AGENTS.md\n' \| cmp -s - CLAUDE.md` | PASS |
| 2 | `jq` claude_md_path + validity | PASS |
| 3 | mantra / one-commit / cross_ai / codegraph_explore / agent-md-refactor | PASS (all five) |
| 4 | legacy-only openspec check | PASS |
| 5 | forbidden-token loop | PASS |
| 6 | `make test` — **gated** | PASS — `311 passed, 70 skipped in 3.12s` |
| 7 | `make doctor` — **captured, not gated** | See capture below |

### The phase-gate captures

```
$ make test
======================= 311 passed, 70 skipped in 3.12s ========================
exit 0

$ make doctor 2>&1 | tee /dev/stderr | rg -q '.'      (captured, not gated)
PASS kitty binary: /home/bazzite/.local/bin/kitty -> kitty 0.49.0 created by Kovid Goyal
PASS symlink: /home/bazzite/.local/bin/kitty -> /var/home/bazzite/.local/kitty.app/bin/kitty
PASS desktop entry: /home/bazzite/.local/share/applications/kitty.desktop
PASS config payload: /home/bazzite/.config/kitty/kitty-setup/kitty-setup.conf
PASS sentinel block: present in /home/bazzite/.config/kitty/kitty.conf
PASS parse check: kitty --debug-config exit=0
PASS bindings: 22 ours, 79 defaults, 0 conflicts
FAIL completion: register-python-argcomplete not on PATH
SKIP remote-control: no running kitty
(make doctor exits 2)
```

`make doctor` is **captured evidence, not a passed gate**: the plan's own rule and ROADMAP step 5
require *captured output*, and Phase 2 / R1.1 owns making doctor green (the `register-python-argcomplete
not on PATH` FAIL is exactly R1.1's subject). No carve-out marker was written.

### Post-commit gates

| # | Command | Result |
|---|---------|--------|
| 1 | `BASE="$(git merge-base master HEAD)" && test "$(git log --format=%s "$BASE"..HEAD \| rg -c '\(01-04\)')" = '1'` | PASS — measured after the commit below |
| 2 | `SHOWN="$(git show --stat --oneline HEAD)" && printf '%s\n' "$SHOWN" \| rg -q '01-04-SUMMARY\.md'` | PASS — SUMMARY is inside the plan's single commit |

## Deviations from Plan

None. Every automated gate passed as written, and no gate was found defective this round. The only
judgment call — carrying the bootstrap parenthetical's known inaccuracy rather than correcting it —
was explicitly sanctioned by the plan itself and is disclosed in the dedicated section above.

The plan's `<human-check>` (read `AGENTS.md` end to end for coherence, confirm the doctor capture
is labelled as evidence) was performed: the file reads as one coherent rule set with no duplicated
or contradictory rule, and the doctor capture above is labelled "captured evidence, not a passed
gate".

## Deferred / out of scope

- **Bootstrap-parenthetical inaccuracy** in `## Stack` (upstream-installer call and PATH-edit both
  Python now) — Phase 8 / R6.1, per `01-CONTEXT.md` Deferred Ideas.
- **README.md ** and **`.planning/PROJECT.md`** git-policy wording — owned by 01-05 (README gated
  at two hunks; PROJECT.Key Decisions row is 01-05 task 2's). Neither file was touched here.
- **docs/prds/kitty-setup-remediation-v1.0-prd.md and docs/requirements.md / propossal_roadmap.md
  still carry legacy `CLAUDE.md` / `openspec/` references** — the PRD is frozen history; the two
  docs carry FROZEN banners; 01-03 handed the full stale-reference list to Phase 8 / R6.1.

## Known Stubs

None. No placeholder values, no `TODO`/`FIXME`, no skipped steps, no `<verify>` command left
unrun. Every `<automated>` gate in the plan was executed.

## Threat Flags

None. T-1-01 (documented policy over-claiming the pre-push guard's enforcement) is mitigated as
planned: AGENTS.md's Git-policy rule discloses **all seven** of the hook's limits, copied from the
hook's own header, and the six-keyword gate loop passes. No new auth, session, network or
input-parsing surface was added.

## Requirements Completed

- **R0.1** — the mantra is a non-negotiable Universal rule: research + experiment on a real kitty
  session with recorded evidence under `tmp/h<NN>-<slug>/`, both *before* the decision, with the
  house "verified by `<command>` → `<output>`" formula and a pointer at `docs/agent-iteration.md`.
- **R0.3** — Authoritative sources point at `.planning/REQUIREMENTS.md`, `.planning/ROADMAP.md`,
  `.planning/PROJECT.md`/`STATE.md`, `.planning/phases/`; `docs/agent-iteration.md` stays; the
  retired spec system appears only as `.planning/legacy/openspec/` history. No process token
  survives.
- **R0.4** — Git policy names the worktree-per-phase branch strategy, the merge-on-green
  precondition aligned to ROADMAP step 6, no-force-push/no-amend, the `tools/hooks/pre-push`
  enforcement wiring via `core.hooksPath`, and all seven disclosed limits.
- **R0.5** — research-tooling rule names `codegraph_explore` / `codegraph explore`, size-then-read
  (`wc -l`, `rg -n`), and the preferred fast tools.
- **R0.7** — every new GSD plan carries `cross_ai: true` in its frontmatter; the rule names the
  existing GSD mechanism rather than inventing one.
- **R0.8** — `AGENTS.md` is the canonical instruction file; `CLAUDE.md` is the byte-exact
  `@AGENTS.md` import; `claude_md_path` points at `./AGENTS.md`; every non-frozen tracked file that
  named `CLAUDE.md` as a rule pointer now names `AGENTS.md`.
- **R0.9** — the preamble states the three-way placement rule and that a rule found in the wrong
  file is moved, not copied.
- **R0.10** — the commit-granularity rule ("one commit per plan") appears exactly once in the repo
  outside `.planning/`; the git-policy rule points at it; the `type: tdd` exception is stated
  without repeating the literal phrase.

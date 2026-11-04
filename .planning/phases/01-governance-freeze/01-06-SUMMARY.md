---
phase: 01-governance-freeze
plan: 06
subsystem: governance
tags: [governance, git-policy, hollow-gates, agent-iteration, validation-map, tdd]
status: complete
requires:
  - "01-VERIFICATION.md (2026-09-23, status gaps_found) — this plan's specification"
  - "01-01: tools/hooks/pre-push and its disclosed-limits block"
  - "01-04: AGENTS.md as the canonical instruction file"
  - "01-05: the 23-row verification map this plan corrects"
provides:
  - "One git policy in .planning/REQUIREMENTS.md too — the file AGENTS.md names first, and the last place the superseded policy survived normatively"
  - "The refspec bypass in tools/hooks/pre-push closed, with the residual name-keying limit disclosed in the hook header and in AGENTS.md"
  - "Three map gates that can be shown failing on the broken tree: the one-policy gate, the rule-uniqueness gate, the R0.3 retirement gate"
  - "docs/agent-iteration.md and docs/probe-template.md rewritten against the .planning/ workflow — no command in either can no longer run"
  - "A FROZEN banner on the PRD, the last unbannered superseded source"
  - "A Phase 8 success criterion for R6.3, which was declared and ungated"
affects:
  - "Phase 2 — inherits a REQUIREMENTS.md Git gate that no longer contradicts AGENTS.md, and a pre-push guard whose disclosure is complete"
  - "Phase 8 / R6.1 — README.md's OpenSpec residue and the stale `CLAUDE.md \"Stack\"` pointer in R6.1 and Phase 8 criterion 1 remain its work"
  - "Phase 8 / R6.3 — now has a success criterion naming the four Makefile targets"
tech-stack:
  added: []
  patterns:
    - "Guard a protected branch on BOTH sides of a push refspec: a guard keyed on the remote ref alone never sees `master:refs/heads/other`"
    - "An absence gate over a document that quotes what it retired must exempt the supersession line, not the file"
    - "`rg --hidden` with `.git` excluded: without --hidden a gate cannot see .claude/; with it, a commit message turns the gate red"
    - "An absence assertion in a test needs a liveness control in the same environment, or it passes when the subject does not exist"
key-files:
  created:
    - .planning/phases/01-governance-freeze/01-06-SUMMARY.md
  modified:
    - tools/hooks/pre-push
    - tests/unit/test_git_hooks.py
    - AGENTS.md
    - .planning/REQUIREMENTS.md
    - .planning/ROADMAP.md
    - .planning/phases/01-governance-freeze/01-VALIDATION.md
    - docs/agent-iteration.md
    - docs/probe-template.md
    - docs/prds/kitty-setup-remediation-v1.0-prd.md
decisions:
  - "The verification report's diagnosis of the pre-push bypass is corrected, not just applied: guard 2 was ALREADY keyed on the remote ref (`tools/hooks/pre-push:109`), which is why a renamed remote ref escaped it. Probe 01 measured that git hands the hook local_ref=refs/heads/master for `master:refs/heads/main`, so the closure is to key on BOTH sides."
  - "The bypass is closed rather than merely disclosed, because a probe established a fix that closes the reproduced form without breaking any legitimate flow (13/13 scenarios). The residual — master's content pushed from another local ref NAME — is disclosed as limit 8 instead of claimed closed: the only content-based alternative would reject the first push of a legitimate gsd/* branch."
  - "Limit 6 is widened from `refs/heads/master` to an empty remote ref of any name. That is the single behaviour change beyond the bypass itself, it is measured (probe 02 S6), and it is disclosed in the hook header rather than left for someone to discover."
  - "The RED commit carries only the two cases that fail at it. The negative control passes against the unfixed hook, so including it would have reproduced MEDIUM 8's own defect — a passing test inside a commit whose purpose is to fail."
  - "The widened one-policy gate exempts a line that says `supersed`, rather than exempting REQUIREMENTS.md. R0.10's text at :64 quotes the phrase it supersedes; a gate that forbids a document from naming what it retired is unsatisfiable, which is the same lesson 01-VALIDATION.md's own round-3 correction records."
  - "The whole-module `18 passed` and `311 passed` gates were replaced with count-free forms rather than bumped to 21/314. Bumping would reinstate the cumulative-count defect corrections 3, 4 and 6 removed — one plan after it was written down."
  - "README.md's OpenSpec residue is left to Phase 8 / R6.1, so the widened R0.3 gate deliberately excludes README.md and would go red if it did not. Naming the exclusion in the row is the honest form; a silently narrow file list is what made the gate hollow in the first place."
  - "docs/probe-template.md was rewritten too, though no finding named it. agent-iteration.md links to it from R6 and step 3, it taught the same retired `<change-id>` workflow, and its link into `../openspec/specs/` was broken by 01-03's own git mv."
metrics:
  duration: "~95 min"
  completed: "2026-09-23"
plan_head_before: c288c46
commits: 2
---

# Phase 1 Plan 06: Verification Gap Closure Summary

Closed the six gaps `/gsd-verify-work` found in Phase 1: the superseded git policy that survived
in `.planning/REQUIREMENTS.md`, three gates that certified properties they could not see, one
recorded RED figure that was never measured plus the vacuous test it counted, an undisclosed
pre-push bypass (closed, with its residual disclosed), the retired OpenSpec workflow still being
taught by two live docs, the last unbannered superseded source, and an ungated Phase 8 requirement.

There was no PLAN.md: the report plus the orchestrator prompt were the plan. Evidence for every
claim below was produced by the nine probes under `tmp/h06-prepush-refspec/` (gitignored — the
captures are reproduced here, which is the durable record).

## Item 1 — `.planning/REQUIREMENTS.md` stated the superseded git policy (CRITICAL)

Both places, at `:355` (the Cross-Cutting **Git gate**) and `:392` (the Out of Scope row), cited
R0.4 while asserting its opposite; `:355` additionally stated the per-task granularity R0.10
supersedes. Rewritten to the policy that holds — worktree per phase on `gsd/phase-{phase}-{slug}`,
work landing at the granularity `AGENTS.md` states (pointed at, never restated, because that bullet
is the only place in the repo the rule may be written), merge into `master` and push at phase end
once `make doctor` and `make test` are green, no force-push or amend of pushed commits. The
Out-of-Scope row now follows `.planning/PROJECT.md:74-78`: merging **at** a green phase boundary is
in scope; what stays out is any merge or force-push outside it.

`:64` was not touched — it already states the supersession correctly, and it is the line the
widened gate has to exempt.

**Proof** (`tmp/h06-prepush-refspec/policy-gate-before.txt` → `policy-gate-after.txt`):

```
tree bf48fa8, BEFORE the rewrite        tree bf48fa8, AFTER the rewrite
  old_gate  exit 0 (green)  ← hollow      old_gate  exit 0 (green)
  new_gate  exit 1 (red)                  new_gate  exit 0 (green)

what the widened patterns see in REQUIREMENTS.md, before:
  64:  … This supersedes "agents commit per task" in R0.4 …     (exempt: says `supersed`)
  355: - **Git gate**: commit per task, push branch `gsd/<phase>` …
  392: | Merging to `master` | Agents push a feature branch only …
after: line 64 only.
```

## Item 2 — three hollow gates and one figure that was never measured (HIGH)

### `01-05-T2` — the one-policy gate

Widened to three files (`.planning/REQUIREMENTS.md` added), both absence patterns made `-i`, and a
surviving occurrence allowed only on a line that also says `supersed`. Demonstrated failing on the
broken tree and passing after the fix — the capture above. Without `-i` the second clause could
never have matched `:392`'s capitalised `Agents` even with the file in the list; two independent
defects, either of which alone hid the violation.

### `01-04-T2` — the rule-uniqueness gate

`rg` skips dotted directories without `--hidden`, so `.claude/conventions.md` — git-tracked, and
one of exactly three files the R0.9 placement rule governs — was outside the search set. The fix
adds `--hidden` and excludes `.git`, because `--hidden` otherwise searches it and a commit message
carrying the phrase would turn the gate red on a correct tree. All four states measured on a
scratch replica, never on the repo (`hidden-gate.txt`):

| state | `old_gate` | `--hidden`, no `.git` exclusion | `new_gate` |
|-------|-----------|--------------------------------|-----------|
| A. clean replica | green | green | green |
| B. duplicate planted in `.claude/conventions.md` | **green ← HOLLOW** | red | **red** |
| C. clean, phrase inside `.git/COMMIT_EDITMSG` | green | **red ← FALSE RED** | **green** |
| D. phrase inside `.planning/` | green | green | green (excluded by design) |

### `01-02-T1` — the recorded RED result was wrong

The row's round-5 parenthetical recorded `4 failed, 14 passed` at `706a694`. **It was never true.**
The verifier checked that commit out and measured `7 failed, 11 passed`; the recorded figure came
from the plan's expectation, not from a run. Corrected in the row, with that provenance stated.

And one of that commit's eight cases passed **vacuously**:
`test_post_checkout_ignores_ordinary_branch_switch` asserted only the *absence* of an `init` argv
(`assert not initialised`), which holds trivially when `tools/hooks/post-checkout` does not exist.
It now carries a liveness control in the same clone, PATH and recording shim: `init -y` must be
recorded when the first-checkout marker **is** present, so the absence can only pass because the
hook read the marker and declined. Two shim logs keep the phases apart.

- **Was asserting:** "no `init*` argv was recorded during two ordinary branch switches" — true of a
  repo with no `post-checkout` hook at all.
- **Now asserts:** that, **and** that the identical environment records exactly `init -y` on a
  first checkout. The test fails if the hook is absent, indiscriminate, or silently broken.

**Proof** (`vacuous.txt`) — a scratch tree whose `tools/hooks/` deliberately lacks `post-checkout`,
with `REPO_ROOT` resolving into it:

```
=== c288c46 version (pre-01-06) ===      1 passed, 17 deselected   ← vacuous
=== 01-06 version (strengthened) ===     1 failed, 20 deselected
  AssertionError: control: the hook did not run `codegraph init -y` on a first checkout
  either, so the absence asserted above proves nothing … Recorded invocations were: (none at all)
```

### `01-04-T1` — the R0.3 retirement gate (found in the report's gap list, not in the prompt's item 2)

Scoped to `AGENTS.md` alone and case-sensitive over a system spelled `OpenSpec`, so it could not see
item 3 at all. Widened to `docs/agent-iteration.md` and `docs/probe-template.md`, `-i` throughout,
`openspec new` added to the token list. Measured red against the `c288c46` copies of both docs (8 and
3 stale hits) and green against the rewritten ones (`r03-gate.txt`). `README.md` is deliberately
excluded and the row says so — its residue is the report's MEDIUM 6, accepted as Phase 8 / R6.1 work.

### The whole-module count gates

`01-02-T2`, `01-02-T3` and `01-05-T3` pinned `18 passed` and `311 passed`. This plan adds three
cases, so both literals would have failed on correct work — the defect corrections 3, 4 and 6
removed. Replaced with count-free forms: pytest exited 0, reported a passed count, and reported no
failure or error (and, for the module, no skip; `make test` legitimately skips the 70 integration
cases). Recorded in the map as correction 7 alongside every other change above.

## Item 3 — `docs/agent-iteration.md` contradicted the rules and named dead commands (HIGH)

Rewritten against the `.planning/` workflow. Every OpenSpec instruction is gone: `openspec new
change` / `/opsx:propose` → open a phase plan under `.planning/phases/<NN>-<slug>/` via
`/gsd-discuss-phase` + `/gsd-plan-phase`; `openspec archive <name>` → write the plan's SUMMARY and
advance STATE.md and the ROADMAP row, with "the phase directory *is* the archive"; the pointer into
the FROZEN `docs/requirements.md` → `.planning/REQUIREMENTS.md` in the order `.planning/ROADMAP.md`
sets; `design.md` (an OpenSpec change artifact) → the plan's SUMMARY; `<change-id>` → `<phase>-<plan>`.

- **R2** no longer sets its own threshold. It points at `AGENTS.md`'s "Verify before declaring done"
  and states the capture-vs-green distinction that file draws, including that a captured-but-red run
  satisfies the rule and still blocks the merge — the reading Phase 1 closed on. What it keeps is the
  playbook-level detail: where a hypothesis's capture goes, and that `tests/integration/` does not
  run at all without `KITTI_INTEGRATION=1`, so a bare `make test` reports green while skipping it.
- **R3** no longer states the pre-widening allow-list. It points at `AGENTS.md`'s `## Stack`, naming
  the bootstrap pair and `tools/hooks/` as the two places shell is permitted — so the three hook
  files Phase 1 added are inside the allow-list as this document now reads it.
- **R1** gained one clause making `AGENTS.md`'s bullet the rule and R1 its scope, so the duplication
  the report booked against R0.9 is a pointer rather than a second statement.
- A new paragraph at the top states the precedence outright: where a rule appears in both files,
  `AGENTS.md` states it and this one points at it; where they disagree, `AGENTS.md` wins.

**Beyond the report:** `docs/probe-template.md` had the same defects — `<change-id>` as an "OpenSpec
change" identifier, findings flowing into `design.md`, "cannot archive", and a **broken link** into
`../openspec/specs/agent-iteration-discipline/spec.md`, a casualty of 01-03's own `git mv`. It is
reachable from R6 and step 3 of an authoritative source, so leaving it would have left the retired
process one click away. Rewritten the same way. Every relative link in both files now resolves
(scripted `[ -e ]` over each target), and the only surviving `openspec` string in either is
`agent-iteration.md`'s `.planning/legacy/openspec/` history pointer.

## Item 4 — the undisclosed pre-push bypass: CLOSED, with its residual disclosed (HIGH)

**The report's diagnosis needed a correction before it could be acted on.** It says the bypass
exists "because the guard keys on the wrong side of the refspec", and the prompt asked for a guard
that "keys on the remote ref being pushed to". The guard *already* keyed on the remote ref
(`tools/hooks/pre-push:109`, and `:83` for the empty-remote branch) — that is precisely why a
renamed remote ref escaped it. Probe 01 settled which side carries what by replacing the hook with a
logger (`stdin.log`):

```
### git push origin master                     refs/heads/master  … refs/heads/master  000…0
### git push origin master:refs/heads/main     refs/heads/master  … refs/heads/main    000…0
### git push origin HEAD:refs/heads/main2      HEAD               … refs/heads/main2   000…0
### git push origin alias-x:refs/heads/main3   refs/heads/alias-x … refs/heads/main3   000…0
### git push origin :refs/heads/main3          (delete)           … refs/heads/main3   e22637cd
```

So the closure is to apply guard 2 when **either** side names `refs/heads/master` — a `names_master`
predicate used at both `:83` and `:109`. The `HEAD:` and `alias-x:` rows are what no name-keyed
guard can see; they are disclosed as limit 8 rather than claimed closed. The only content-based
alternative — enumerating every push against the local `master` tip — would reject the first push of
a legitimate `gsd/*` branch, which has no remote tip to enumerate against either (limit 6's own
cause), so it is not available.

**Probe 02, 13 scenarios, own bare remote + clone each, under the session scratch dir. `origin` was
never contacted and no worktree of the real repo was created** (`before.txt` → `after.txt`):

| # | Scenario | tracked hook | fixed hook |
|---|----------|--------------|-----------|
| S1 | commit authored on master → `push origin master` | reject (`provenance — <sha> is in no gsd/* branch`) | reject |
| **S2** | **same commit → `master:refs/heads/main`, remote ref absent** | **ALLOW ← the bypass** | **reject (`provenance cannot be established`)** |
| **S2b** | **same, remote `main` present** | **ALLOW ← the bypass** | **reject (`provenance — <sha> is in no gsd/* branch`)** |
| S3 | S2 form with `KITTI_ALLOW_MASTER_PUSH=1` | allow, announced | allow, announced |
| S4 | new `gsd/*` branch first push | allow | allow |
| S5 | `--no-ff` merge of `gsd/*` → push master | allow | allow |
| S6 | provenance-clean master → **new** `refs/heads/main` | allow | reject (limit 6, widened) |
| S6b | provenance-clean master → **existing** `refs/heads/main`, fast-forward | allow | allow |
| S7 | master's commit via `alias-x:refs/heads/main` | allow | allow — **limit 8** |
| S8 / S8b | delete remote master / delete a `gsd/*` branch | reject / allow | reject / allow |
| S9 | first push of master to an empty remote | reject | reject |
| S10 | `--force` on the renamed ref, hatch set | reject (guard 1, unconditional) | reject |

`10 pass, 3 fail` against the tracked hook → `13 pass, 0 fail` against the fix.

Three defects the probe found in **itself**, not in the hook, each recorded in the script where it
was fixed: S6's expectation (an absent remote tip leaves nothing to enumerate, so rejecting is
correct — which is what widened limit 6); S10's setup push needed the hatch, or the scenario measured
the new-ref path instead of the rewrite path; and a relatively-addressed sandbox made **every** push
fail with no `[pre-push]` output at all, because `git remote add origin <relative-path>` resolves
against the clone's directory rather than the invoking cwd — a reading that would have been
mistakable for the hook rejecting everything. The final run above is against the installed, tracked
hook, with the sandbox paths absolutised.

**Disclosure.** The hook's header gains limit 8 and a widened limit 6, and its guard-2 description
now says "either side of its refspec" with the measurement pointer. `AGENTS.md`'s git-policy bullet
carries both, because it claims to reproduce that list "from the hook's own header" — an incomplete
reproduction there is the R0.4 transparency violation this phase wrote for itself. The map row that
said "all seven limits" now says eight.

**Regression tests** (`tests/unit/test_git_hooks.py`, 18 → 21 cases):
`test_master_to_renamed_remote_ref_rejected` (S2b — the enumeration path, so the rejection can be
asserted to name `provenance`), `test_master_to_new_remote_ref_name_rejected` (S2 — the widened limit
6, asserting the escape hatch is named), and `test_clean_master_to_renamed_remote_ref_allowed` (S6b —
the negative control, without which a guard that rejected every renamed-ref push would pass).

## Item 5 — the PRD carried the superseded R0.4 text (MEDIUM)

A FROZEN banner was added, matching the style 01-03 used on `docs/requirements.md` and
`docs/propossal_roadmap.md`: the same verbatim first line, then the supersession note. Not one word
below it changed, which is the whole point — the provenance `.planning/REQUIREMENTS.md` cites as its
`Source:` is preserved, and the contradiction is closed. The report is right that 01-05's reasoning
argued *for* this remedy rather than against acting: it is the answer R0.2 already had in hand.

**The CommonMark trap was checked, not eyeballed.** Structural assertions per file (`banner.txt`),
plus a real parse with `markdown_it` in CommonMark mode (`render.txt`), asserted from the token
stream that the `h1` is outside every blockquote and that the blockquote holds exactly one paragraph
— i.e. the following prose is a sibling, not lazily absorbed:

```
docs/prds/kitty-setup-remediation-v1.0-prd.md   h1 depth=0   quote-paras=1   quote lines 3-6, prose from 8
docs/requirements.md / docs/propossal_roadmap.md / .planning/legacy/openspec/README.md — same shape
failures: 0
```

## Item 6 — Phase 8 declared R6.3 and wrote no criterion for it (MEDIUM)

Added criterion 4 to Phase 8, naming `make validate`, `make format`, `make test-unit` and
`make test-integration`, and requiring each to either exist and run or be removed from
`.claude/conventions.md` — verified by invoking all four, not by reading either file. No target was
added and `.claude/conventions.md` was not touched: that is Phase 8's work. The edit is one inserted
line (`git diff --stat` → `1 insertion`), and `rg -c '^### Phase [0-9]+(\.[0-9]+)?:'` still returns
**11**.

## Gate re-run

Every automated gate in the map, re-run in the form this plan leaves it
(`tmp/h06-prepush-refspec/map-gates.txt`, 33 clauses over the 23 rows plus the completeness gate):
**32 pass, 1 fail.**

| Gate | Result |
|------|--------|
| 28 per-task map clauses | 27 pass, 1 fail (`01-01-T1c`, below) |
| Map Completeness Gate (4 clauses) | pass — 23 rows, 23 verdicts, no `⬜ pending`, no `TBD` in a row |
| Carve-out marker absent from all three policy docs | pass |
| `uv run pytest tests/unit/test_git_hooks.py -q` | **21 passed**, exit 0, zero skipped |
| `make test` | **314 passed, 70 skipped**, exit 0 (baseline 311/70 — +3 new cases, no regression) |
| `make doctor` | exit 2; 8 PASS, 1 FAIL (`completion: register-python-argcomplete not on PATH`), 1 SKIP. Exactly the expected R1.1 failure, Phase 2's |
| `uv run pyright` | **571 errors** — baseline exactly; `tests/unit/test_git_hooks.py` alone: 0 |
| `uv run ruff check` / `black --check` on `tests/unit/test_git_hooks.py` | clean (the 11 files the repo-wide run flags are Phase 8.5's pre-existing debt; this file is not among them) |

**The one red row is an environment regression, not a tracked-file one.** `01-01-T1c` asserts
`core.hooksPath` is the relative `tools/hooks`; it measures
`file:…/.git/config  /var/home/…/kitty-setup/tools/hooks` — **absolute**. `make hooks` sets the
relative form, so no file this plan touches can fix it, and a worktree must not rewrite the primary
checkout's config. Note that `01-05-SUMMARY.md` records fixing this exact value once already, so
something resets it (the harness's worktree creation is the likeliest candidate). The consequence is
the one `tools/hooks/post-checkout`'s header documents: an absolute value resolves the hook file out
of a different worktree on every invocation. **Remedy: run `make hooks` from the primary checkout.**
Reported rather than silently "fixed" — and the gate catching it is the gate working.

## Deviations and judgement calls

- **The report's diagnosis of the bypass is wrong in its mechanism** (guard 2 already keyed on the
  remote ref). Its *finding* is exactly right, and reproducible. Documented above; the fix keys on
  both sides.
- **`docs/probe-template.md` was rewritten although no finding named it** — R0.3's clause is
  unqualified, the file is one click from an authoritative source, and its `../openspec/specs/…`
  link was broken.
- **Limit 6 widened** — a behaviour change beyond closing the bypass, measured (S6) and disclosed.
- **No new map row was added.** The R0.3 widening strengthens the existing `01-04-T1` row instead,
  because the Map Completeness Gate pins the row count at 23 in this file *and* in `01-05-PLAN.md`,
  and a 24th row would have required editing a closed plan's gate to keep both truthful.

## Noted, deliberately not fixed

- **MEDIUM 6** — `README.md` still describes the pre-freeze repo, with the file's only broken link
  pointing into the removed `openspec/`. Phase 8 / R6.1 owns README explicitly; the widened R0.3 gate
  names the exclusion rather than hiding it.
- **MEDIUM 9's last sentence** — R6.1 and Phase 8 criterion 1 both name the `CLAUDE.md` "Stack"
  section, which Phase 1 moved to `AGENTS.md`. Left to whoever rewrites R6.1: correcting a
  requirement's acceptance text was outside this plan's brief, and Phase 8's criterion is where it
  bites. **Recommended**: swap both pointers to `AGENTS.md`'s `## Stack`.
- **LOW 11 / LOW 12** — the phase-completion bookkeeping (unticked R0.x checkboxes, `Pending`
  traceability rows, stale `state_head`, the `36 total / 53 rows` coverage block) and
  `01-VALIDATION.md`'s `status: draft` frontmatter. Neither is in this plan's brief, both are
  bookkeeping over a phase whose merge is still deferred, and `status: draft → validated` is a
  transition `validate-phase §6` owns.
- **`.claude/conventions.md:69,75`** — the two process rules the report books against R0.9. The
  prompt scopes that file to Phase 8; moving them is R6.3-adjacent work with a live gate now
  attached (Phase 8 criterion 4).

## Commit topology

`type: tdd`, so exactly two commits, RED an ancestor of GREEN:

| | Commit | Contents |
|---|--------|----------|
| RED | `bf48fa8` `test(01-06)` | the two failing cases only — measured `0 passed, 2 failed` at that commit, each on the `returncode != 0` assertion |
| GREEN | this commit `feat(01-06)` | the hook fix, the negative control, the vacuous-test fix, all six items' documentation, and this SUMMARY |

The negative control is deliberately in GREEN: it passes against the unfixed hook, and a passing
test inside a RED commit is MEDIUM 8's defect reproduced.

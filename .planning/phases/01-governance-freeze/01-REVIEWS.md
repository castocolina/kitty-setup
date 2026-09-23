---
phase: 1
reviewers: [opencode]
reviewed_at: 2026-09-23T00:00:00Z
plans_reviewed:
  - .planning/phases/01-governance-freeze/01-01-PLAN.md
  - .planning/phases/01-governance-freeze/01-02-PLAN.md
  - .planning/phases/01-governance-freeze/01-03-PLAN.md
  - .planning/phases/01-governance-freeze/01-04-PLAN.md
  - .planning/phases/01-governance-freeze/01-05-PLAN.md
models:
  opencode: "router-env/my-plan-review (reasoning=high)"
model_sources:
  opencode: "pinned"
source_grounding:
  authority: "grep"
  performed_by: "opencode + orchestrator"
  verdicts: { verified: 103, missing: 5, ambiguous: 1, uncheckable: 8 }
---

# Cross-AI Plan Review — Phase 1

<!-- gsd:plan-revision-conflicts:begin -->
## Plan-Revision Conflicts

None recorded.
<!-- gsd:plan-revision-conflicts:end -->

> **Lane note.** The `opencode` lane needed 14 attempts over ~40 minutes to get through: the
> model pinned by `review.models.opencode` (`router-env/my-plan-review`) was returning
> `Service temporarily unavailable due to resource pressure`, and once it recovered, the
> provider's request-size admission control (`Chat admission capacity is temporarily
> unavailable`) rejected the ~61k-token combined prompt several more times. Both a
> full-context pass and a smaller per-plan pass eventually completed. Two reviews from the
> same lane and model are recorded below; they are **one** reviewer, not two, and are weighted
> as one.

## OpenCode Review

Full-context pass — all five plans, with `PROJECT.md`, `ROADMAP.md`, `REQUIREMENTS.md`,
`01-CONTEXT.md` and `01-RESEARCH.md` in the prompt, and repo file access enabled. Verbatim:


**Document type:** GSD plans  
**Status:** Issues found — revise before execution

### 01-01

#### Summary

A strong tracer plan with sensible sandbox tests and accurate use of `core.hooksPath`. The non-fast-forward guard is sound, and `tests/unit/` is the correct ungated location. The main weakness is the direct-to-`master` provenance heuristic: it supports normal fast-forward and `--no-ff` phase merges, but rejects several legitimate integration strategies and leaves first-push behavior ambiguous.

#### Strengths

- `tests/unit/` is necessary, not arbitrary: `tests/conftest.py:44-53` skips all `tests/integration/` cases unless `KITTI_INTEGRATION=1`, while `Makefile:33-34` runs the whole `tests/` tree.
- The shell prelude follows existing conventions in `tools/setup.sh:1-21` and `tools/uninstall.sh:1-17`.
- `if ! git merge-base --is-ancestor ...` correctly prevents `set -e` from terminating before the hook can print its diagnostic.
- Tests exercise the tracked hook via a mode-preserving copy instead of duplicating its logic.
- Negative controls for fast-forward and new-branch pushes prevent a blanket-rejecting hook from appearing correct.
- Bypass disclosure is machine-gated: the plan checks both `KITTI_ALLOW_MASTER_PUSH` and `no-verify` at `01-01-PLAN.md:317-323`.
- Sandbox execution confirmed that the proposed heuristic:
  - rejects a commit authored directly on `master`;
  - allows a fast-forward merge while the phase branch exists;
  - allows a `--no-ff` merge while the phase branch exists;
  - rejects after the containing phase branch is deleted.

#### Concerns

- **HIGH — The plan requires TDD commits per task, contradicting R0.10 before that rule is installed.** Task 1 requires separate RED and GREEN commits at `01-01-PLAN.md:167-170,203`, Task 3 repeats this at `01-01-PLAN.md:308-309`, and the done criterion requires both commits at `01-01-PLAN.md:227`. R0.10 requires one commit per plan in `.planning/REQUIREMENTS.md:59-65`. This plan would create at least four commits for one plan.
- **MEDIUM — Legitimate integration strategies falsely reject.** The reachability test at `01-01-PLAN.md:286-304` rejects squash merges and cherry-picked integration because the new `master` commit is not contained in the phase branch. It also rejects merges from configured milestone branches such as `gsd/{milestone}-{slug}` in `.planning/config.json:17`.
- **MEDIUM — A first push of `master` is underspecified.** Task 1 says to skip checking a zero `remote_sha` at `01-01-PLAN.md:183-191`, while Task 3 places the master guard afterward at `01-01-PLAN.md:296-300`. A `continue` skips the master guard entirely; merely skipping the ancestor command leaves an invalid `ZERO_SHA..local_sha` revision range.
- **MEDIUM — The force-push test does not distinguish every expected failure source.** It checks nonzero plus `[pre-push]`, but the hook may reject the amended `master` push through either the ancestor guard or the master-provenance guard. A specific diagnostic should identify which control fired.
- **LOW — “0 skipped” is not enforced by pytest’s exit status.** The `<fails_when>` text at `01-01-PLAN.md:216-217` describes an observable output condition, but the command itself exits zero for skips. Unit-tree placement substantially mitigates this, but the plan should not claim the command enforces the count.
- **LOW — `git config --get --worktree core.hooksPath` is not a robust absence check.** With `extensions.worktreeConfig` disabled it can exit nonzero because worktree config is unavailable, not because an override was proven absent.

#### Suggestions

- Remove all task-level RED/GREEN commits. Run TDD within the working tree, then create one plan commit after all six cases pass.
- Decide and test the supported merge model explicitly. If only ordinary phase-branch merges are supported, document squash, cherry-pick, rebase, deleted branches, and milestone branches as limitations.
- Define first-ever `master` push behavior explicitly and add a test.
- Assert distinct rejection messages for non-fast-forward and direct-master provenance failures.
- Redirect nested git commands from stdin where appropriate so they cannot consume subsequent pre-push ref lines.

#### Risk Assessment

**MEDIUM.** The base hook mechanics are good, but the plan currently violates its own commit-granularity requirement and under-specifies several master-push cases.

### 01-02

#### Summary

The CodeGraph lifecycle design is appropriate and well tested with success, failure, and absence shims. The main technical gap is that “never blocks” does not cover a hanging `codegraph` process, and the live evidence expects output that `-q` and redirected output may suppress.

#### Strengths

- `post-checkout` uses the correct fresh-worktree discriminator: branch flag `1` plus zero previous HEAD at `01-02-PLAN.md:157-165`.
- The `codegraph` flags are valid: `init -y` is non-interactive and `sync -q` is hook-oriented quiet mode.
- `.codegraph/` is genuinely ignored at `.gitignore:69-70`.
- Failure and absent-binary paths test that the git operation succeeds and state changes occur, not merely that a warning was printed.
- Minimal PATH construction correctly accounts for `/usr/bin/env bash`, `dirname`, and `git`.
- `|| log ...` plus terminal `exit 0` correctly neutralizes ordinary nonzero exits under `set -e`.
- Six new tests plus six from 01-01 correctly total twelve.

#### Concerns

- **HIGH — This plan also violates one-commit-per-plan.** It requires RED and GREEN commits in both TDD tasks at `01-02-PLAN.md:139-168,203-227`, conflicting with `.planning/REQUIREMENTS.md:59-65`.
- **MEDIUM — A hanging CodeGraph process can still block commits indefinitely.** The threat model says a “hanging or failing” tool is mitigated at `01-02-PLAN.md:316-319`, but `command -v`, `|| log`, and `exit 0` only handle absence or eventual nonzero termination. No timeout handles a process that never returns.
- **MEDIUM — The live transcript requires tags the quiet hooks may never emit.** Task 3 expects `[post-checkout]` and `[post-commit]` in command output at `01-02-PLAN.md:265-284`, but successful `codegraph init` output is explicitly discarded at `01-02-PLAN.md:162-165`, and successful `codegraph sync -q` is silent at `01-02-PLAN.md:219-225`. Unless the hooks log a success message after each command, those acceptance criteria cannot pass.
- **MEDIUM — `codegraph status` does not report a changed filename.** Task 3 requires status to “report the changed file” at `01-02-PLAN.md:269-271`; the actual command reports aggregate file/node counts and freshness, not changed-file names.
- **MEDIUM — The post-checkout failure test does not require the warning.** R0.6 requires failures to warn, but the behavior at `01-02-PLAN.md:133-136` only asserts successful worktree creation and contents.
- **LOW — The absence idiom is only safe when paired with an existence gate.** `rg 'exit 1' file | wc -l | rg -x '0'` at `01-02-PLAN.md:183,242` returns success if `file` is missing because `wc` still prints zero. The post-checkout block has `test -x`; the post-commit block has a content check, but the dependency should be explicit.
- **LOW — The plan-level verification reintroduces the broken `rg -c` form.** `01-02-PLAN.md:325-329` expects `rg -c` to report zero for both files, but with zero matches ripgrep emits no count and exits 1.
- **LOW — The `wc -l | rg -x '0'` form is Linux-specific.** BSD `wc` commonly pads counts, relevant to this cross-platform repository even though Phase 1 runs on Linux.

#### Suggestions

- Keep TDD execution but commit once after the entire plan passes.
- Add an external timeout around both CodeGraph calls, with a nonblocking timeout warning.
- Make each hook print a tagged success line, or remove tag requirements from the live transcript.
- Replace “status reports the changed file” with a query that can actually establish the new symbol/path is indexed.
- Assert warning text in both failure tests.
- Replace absence pipelines with `test -f file && ! rg -q 'exit 1' file`.
- Correct the final verification block to use the same robust check.

#### Risk Assessment

**MEDIUM.** The lifecycle architecture is sound, but the evidence contract and hang mitigation need revision.

### 01-03

#### Summary

The intended archive → move → banner ordering is correct, and the banner target is properly created only after relocation. However, the literal archive-then-`git mv` sequence fails because `openspec archive` moves tracked files in the working tree without staging those changes; `git mv openspec ...` then encounters missing source paths.

#### Strengths

- Cross-plan ordering is sound: 01-03 depends on 01-02, and archive/move precede the instruction-file claims.
- Within the plan, archive is explicitly ordered before relocation at `01-03-PLAN.md:133-160`.
- The new legacy README is only created after `.planning/legacy/openspec/` exists, at `01-03-PLAN.md:191-226`.
- The current legacy docs have the stated H1/blank/Date shape at `docs/requirements.md:1-3` and `docs/propossal_roadmap.md:1-3`.
- Suffix matching avoids hardcoding the archive date.
- Specs checksuming before and after `--skip-specs` is the right safety control.
- Whole-tree strict OpenSpec validation is correctly excluded as an unrelated legacy-debt gate.

#### Concerns

- **CRITICAL — The prescribed `git mv` fails after `openspec archive`.** In a disposable copy, `openspec archive ... --skip-specs -y` deleted the tracked source paths and created untracked archived paths; a direct `git mv openspec .planning/legacy/openspec` failed with `fatal: bad source`. The plan omits the necessary `git add -A openspec` between archive and relocation. This breaks Task 1’s central sequence at `01-03-PLAN.md:144-160`.
- **HIGH — The tracked-file count invariant is wrong unless it accounts for the new archive paths.** The plan compares the pre-archive tracked count with the post-move count at `01-03-PLAN.md:137-160,172`. Before staging, the archived copies are untracked; after correctly staging them, the total remains stable, but the plan must specify staging before `git mv` and before counting.
- **MEDIUM — `"$TMPDIR/pre.txt"` assumes `TMPDIR` exists.** At `01-03-PLAN.md:137-142`, an unset variable under `set -u` or normal shell expansion can produce `/pre.txt`. Use the required hypothesis directory or `${TMPDIR:-/tmp}`.
- **MEDIUM — The specs “unmodified” acceptance command cannot pass after a correct move.** `git diff --name-only HEAD -- .planning/legacy/openspec/specs` at `01-03-PLAN.md:174` lists moved destination files. Test rename status/content identity instead.
- **MEDIUM — CodeGraph testing is sequenced after a vaguely placed commit.** Task 3 requires the relocation commit to have landed at `01-03-PLAN.md:260-263`, but the plan also says one commit per plan and still needs to produce the tracked summary containing the experiment at `01-03-PLAN.md:361-365`. This creates a commit/evidence ordering conflict.
- **LOW — `codegraph status` only checks exit status.** The `<fails_when>` at `01-03-PLAN.md:300-301` additionally claims zero indexed files is detected, but the automated command does not parse the count.
- **LOW — Banner verification counts matching arguments, not the whole repository.** `rg -l ... three-explicit-files | wc -l` proves all three targets match, but not that no unintended fourth banner exists. The acceptance wording is limited to the three files, so this is acceptable if stated that way.

#### Suggestions

- Make the sequence explicit:
  1. checksum and count;
  2. run `openspec archive`;
  3. verify checksum;
  4. `git add -A openspec`;
  5. `git mv openspec .planning/legacy/openspec`;
  6. verify rename status and count.
- Use `tmp/hNN-.../pre.txt` rather than raw `$TMPDIR`.
- Verify the specs move with `git diff --cached --name-status` restricted to `R100` or compare content checksums at old-HEAD versus new paths.
- Resolve the single-commit/evidence sequencing: perform a manual `codegraph sync -q` before the sole commit, or keep post-commit evidence outside the tracked summary.
- Parse `codegraph status --json` for a nonzero file count.

#### Risk Assessment

**HIGH.** The ordering concept is right, but the literal central command sequence is not executable without an omitted staging step.

### 01-04

#### Summary

The canonical-file migration is carefully scoped and mostly well grounded. Dependencies ensure the hook and legacy paths exist before `AGENTS.md` claims they do. The primary issues are a knowingly false “Stack section is true” assertion and incomplete uniqueness gates.

#### Strengths

- Current sources support the migration:
  - `CLAUDE.md` has the stated 62-line structure at `CLAUDE.md:1-62`;
  - `.planning/config.json` points to `./CLAUDE.md` at `.planning/config.json:69`;
  - `.claude/conventions.md` names `CLAUDE.md` at `.claude/conventions.md:3-5`.
- 01-04 depends on all three earlier plans, so the Stack and legacy-path claims are made only after the artifacts exist.
- Bypass disclosure is genuinely gated at `01-04-PLAN.md:342-345`.
- The canonical-file repoint is exact and preserves valid JSON.
- The OpenSpec process-reference check has the right basic structure.
- The plan correctly keeps stack conventions in `.claude/conventions.md` while retaining the shell allow-list as an agent rule.

#### Concerns

- **HIGH — The plan claims the Stack section is true while explicitly retaining known false statements.** The must-have at `01-04-PLAN.md:31` says the section is true, but Task 1 deliberately carries known inaccuracies unchanged at `01-04-PLAN.md:209-211`. The existing paragraph at `CLAUDE.md:42-50` attributes the upstream installer and PATH edit dispatch to shell even though setup delegates those actions to Python.
- **HIGH — PROJECT remains contradictory unless 01-05 expands scope.** `.planning/PROJECT.md:99-103` still says Bash exists only in the two bootstrap scripts and “No new shell scripts.” Plan 01-04 makes AGENTS accurate but leaves another authoritative planning file stating the opposite.
- **MEDIUM — “One commit per plan appears exactly once” is not machine-enforced.** The verify command at `01-04-PLAN.md:336-337` proves presence, not uniqueness. The acceptance criterion at `01-04-PLAN.md:325` is stronger than its gate.
- **MEDIUM — The hook allow-list gate checks only one filename.** Task 1 requires all three hooks at `01-04-PLAN.md:231-233`, but verification only checks `tools/hooks` and `post-checkout` at `01-04-PLAN.md:246-247`.
- **MEDIUM — The OpenSpec check can pass a forbidden process reference if `legacy` appears on the same line.** `rg ... | rg -v legacy` at `01-04-PLAN.md:242` is a lexical approximation, not a semantic process-reference check.
- **MEDIUM — The sole plan commit excludes the required summary.** Task 3 commits at `01-04-PLAN.md:381-383`, while `01-04-SUMMARY.md` is created afterward at `01-04-PLAN.md:454-458`.
- **LOW — `@AGENTS.md` is ten characters, not nine.** The plan repeats the incorrect count at `01-04-PLAN.md:40,363-367,450`; its equality test is correct.

#### Suggestions

- Scope the must-have to “the shell allow-list is true,” or correct the entire Stack paragraph now.
- Add `.planning/PROJECT.md:99-103` to 01-05’s explicit alignment work.
- Gate the exact number and location of the normative commit-granularity statement.
- Assert `pre-push`, `post-commit`, and `post-checkout` individually.
- Forbid specific retired tokens such as `openspec list`, `openspec archive`, and `.claude/skills/openspec`.
- Generate the summary before the single plan commit.
- Remove character-count claims.

#### Risk Assessment

**MEDIUM.** The migration mechanism is good, but canonical truth and uniqueness claims are stronger than the planned checks.

### 01-05

#### Summary

This is the weakest plan. It correctly recognizes that governance needs direct verification, but it is stale against the current roadmap and requirements, contains vacuous checks, conflicts with the doctor-before-merge policy, and cannot both preserve one commit per plan and record post-push evidence in that commit.

#### Strengths

- `agent-md-refactor` findings receive explicit Applied/Deferred/Rejected dispositions.
- README and project-local skills are correctly kept out of scope.
- Targeted planning-document edits are safer than whole-file rewrites.
- The plan correctly recognizes that `make test` alone does not verify governance content; `01-VALIDATION.md:31-33` confirms this.
- The added Python test file is correctly required to pass focused ruff, black, and pyright checks.
- The master push is intended to exercise the real pre-push path rather than relying only on sandbox tests.

#### Concerns

- **CRITICAL — Phase-end merge/push violates the policy it just installs because doctor is not green.** The canonical policy requires green `make doctor` and `make test` before merge (`ROADMAP.md:28,39-42`; planned AGENTS wording at `01-04-PLAN.md:278-283`). Yet 01-05 explicitly treats doctor as evidence-only at `01-05-PLAN.md:289-297` and still merges and pushes at `01-05-PLAN.md:313-318`.
- **CRITICAL — The plan cannot record post-push output in its single commit.** It commits before merge/push at `01-05-PLAN.md:313-318`, then requires tracked `01-05-SUMMARY.md` to include push output at `01-05-PLAN.md:323-326,390-395`. This requires an uncommitted summary or a second commit.
- **HIGH — It misses the opposite merge policy in PROJECT.** `.planning/PROJECT.md:74-75` says agents push a feature branch only and the owner integrates. Task 2 only edits the Key Decisions row at `.planning/PROJECT.md:125`.
- **HIGH — Quality ownership and baseline claims are stale and false.** The plan calls the quality debt “unowned” at `01-05-PLAN.md:299-311`, but R0.11 assigns `src/` cleanup to Phase 2 and R0.12 assigns `tests/` cleanup to Phase 8.5 at `.planning/REQUIREMENTS.md:67-81`. The current roadmap already encodes the measured gate at `.planning/ROADMAP.md:29-38`.
- **HIGH — Bandit severity is misreported.** `01-05-PLAN.md:111-116` states 20 high/1 medium/6 low, but `.planning/REQUIREMENTS.md:70-72` records the corrected severity as 0 high/8 medium/19 low; 20/1/6 is confidence.
- **HIGH — The verification-map gate is vacuous.** `test "$(rg -nic 'TBD' ... | wc -l)" = '0'` at `01-05-PLAN.md:336` passes now because `01-VALIDATION.md` contains no `TBD`; it does not check the 21 pending markers visible at `01-VALIDATION.md:58-77`.
- **HIGH — The phase-scope diff becomes vacuous after merging into master.** The final gate computes `git merge-base master HEAD` at `01-05-PLAN.md:338`; after master contains the phase tip, the range can be empty regardless of what Phase 1 changed.
- **MEDIUM — The pyright match accepts nonzero errors ending in zero.** `rg -q '0 errors'` at `01-05-PLAN.md:334` matches `10 errors`, `20 errors`, or `570 errors`.
- **MEDIUM — The plan says twelve validation rows, but the file contains twenty.** See `01-05-PLAN.md:265-267` versus `01-VALIDATION.md:58-77`.
- **MEDIUM — The roadmap integrity check ignores Phase 8.5.** `^### Phase [0-9]+:` at `01-05-PLAN.md:254` intentionally matches only integer phases, so deletion of decimal Phase 8.5 would go undetected.
- **MEDIUM — “Commit per task” survives in the validation contract under reversed wording.** `01-VALIDATION.md:39` says “After every task commit,” contradicting one commit per plan even after exact `commit per task` matches are removed.
- **MEDIUM — The current conventions remain impossible to obey.** `.claude/conventions.md:21-23` requires strict Pyright with no suppressions, and `.claude/conventions.md:69` requires `make validate`, but `Makefile:1-40` has no `validate` target and the repo has known debt.
- **LOW — The two-file presence command does not enforce two files.** The `<fails_when>` at `01-05-PLAN.md:250-251` says fewer than two files is failure, but plain `rg` exits zero if either file matches.

#### Suggestions

- Do not merge or push in this phase until the doctor policy is reconciled. Either make doctor green first or define a narrowly scoped, authoritative Phase 1 exception before execution.
- Move merge/push outside the one-commit plan artifact lifecycle, or record push evidence externally.
- Update both `.planning/PROJECT.md:74-75` and `.planning/PROJECT.md:125`.
- Rebase quality logic on `.planning/ROADMAP.md:29-38` and `.planning/REQUIREMENTS.md:67-81`.
- Replace the pending gate with an explicit `! rg -q '⬜ pending' ...` check.
- Capture the immutable phase-base SHA before any merge.
- Anchor Pyright output, for example `rg -q '(^|[^0-9])0 errors,'`.
- Update `01-VALIDATION.md:39` to task verification, not task commits.
- Check all eleven phase detail sections, including Phase 8.5.
- Reconcile `.claude/conventions.md` with the staged quality policy or clearly mark future-state gates.

#### Risk Assessment

**HIGH.** The plan cannot execute as written without violating the newly documented git policy, the one-commit rule, or the evidence requirements.

### Cross-plan assessment

#### Ordering

The wave chain is correct:

1. 01-01 establishes hook wiring.
2. 01-02 expands it.
3. 01-03 archives, then relocates, then banners.
4. 01-04 writes claims only after their artifacts exist.
5. 01-05 aligns and verifies.

The archive-before-move and move-before-banner intent is sound. The execution defect is narrower but blocking: `openspec archive` must be staged before `git mv`.

#### Verification quality

Most `<fails_when>` clauses name observable signals, but several describe conditions the paired command does not enforce:

- pytest skip counts;
- two-file representation in an `rg` result;
- nonzero CodeGraph file count;
- pending validation statuses;
- exact plan-policy uniqueness.

The `rg PATTERN file | wc -l | rg -x '0'` replacement works on Linux when the file exists. It can pass vacuously for a missing file and may fail on padded BSD `wc` output. Prefer `test -f file && ! rg -q PATTERN file`.

#### Phase-goal coverage

Plans 01-01 through 01-04 substantially cover R0.1–R0.10 once the identified mechanics are corrected. Plan 01-05 presently prevents clean closure. The phase should not execute until these blockers are resolved:

1. one-commit-per-plan versus RED/GREEN/task commits;
2. archive staging before `git mv`;
3. doctor-before-merge policy;
4. post-push evidence versus single-commit sequencing;
5. stale quality ownership and Bandit baseline;
6. vacuous validation-map gate.

#### Overall Risk Assessment

**HIGH.** The architecture and ordering are mostly strong, but multiple execution-level contradictions would either stop the phase or force the executor to violate the governance rules the phase exists to establish.

---

## OpenCode Review — supplementary per-plan pass

Same lane, same model, run one plan at a time with a constrained read budget (the only shape
the provider would admit while under load). It reached plans 01-01 through 01-04; **01-05 was
not reached** before the run was stopped, and the full-context pass above covers it. This pass
surfaced findings the full pass did not, so it is recorded rather than discarded. Verbatim:

### 01-01

**Summary**

The plan has strong behavioral coverage and correctly treats the hook as a discriminating compliance guard rather than a security boundary. However, several ordering, Git-config, and test-determinism issues could make execution fail or leave stated guarantees unproven.

**Strengths**

- Uses the real tracked hook in disposable repositories instead of duplicating its logic.
- Correctly places tests under `tests/unit/`; integration tests are otherwise skipped unless `KITTI_INTEGRATION=1` (`tests/conftest.py:44-53`).
- Handles `set -e` correctly for expected non-zero ancestry results by placing `merge-base --is-ancestor` inside a conditional.
- Includes positive and negative controls: rewrite rejection, fast-forward allowance, new-ref allowance, master rejection, phase-branch merge allowance, and escape-hatch behavior.
- Requires a diagnostic tag in addition to non-zero status, reducing false positives from hook crashes.
- The proposed Makefile additions fit its explicit thin-target convention (`Makefile:1-3`) and existing `.PHONY`/manual-help structure (`Makefile:5-19`).
- The shell prelude matches the established scripts (`tools/setup.sh:16-21`, `tools/uninstall.sh:12-17`).

**Concerns**

- **HIGH — Dependency ordering violates the current repository rules.** Plan 01 creates `tools/hooks/pre-push` before plan 04 amends the shell allow-list, but the current rule permits Bash only in `tools/setup.sh` and `tools/uninstall.sh` and explicitly forbids new shell scripts (`CLAUDE.md:42-48`). Plan 01 therefore cannot truthfully state that the allow-list is already amended. Plan 04 must precede this plan, or the allow-list amendment must move into plan 01.
- **HIGH — Existing documentation becomes false.** `tools/setup.sh` currently calls itself “the only bash logic in this repo” (`tools/setup.sh:2-3`), and README repeats the two-script-only assertion (`README.md:165`). Adding three hooks without updating these assertions leaves the repository internally inconsistent even if AGENTS.md later gains the correct policy.
- **HIGH — The worktree-config acceptance criterion is contradictory.** Without `extensions.worktreeConfig`, `git config --worktree` aliases the local/common config scope. After `git config core.hooksPath tools/hooks`, expecting `git config --get --worktree core.hooksPath` to find nothing is therefore not a valid proof that no per-worktree override exists. Verify origin with `git config --show-origin --get core.hooksPath` and separately verify that `extensions.worktreeConfig`/`config.worktree` is absent.
- **HIGH — New remote `master` behavior is under-specified.** Task 1 skips zero-`remote_sha` refs, while Task 3 places the master guard after the ancestry check. A `continue` would bypass master provenance entirely; otherwise `"$ZERO_SHA..$local_sha"` is not a valid revision range. This conflicts with the unconditional must-have that direct commits to `master` are rejected. Add an explicit first-push-to-master decision and regression test.
- **MEDIUM — The amend test may be nondeterministic or fail for the wrong reason.** Bare `git commit --amend` can invoke an editor, and `--amend --no-edit` performed immediately without changing the tree can reproduce the same commit object within timestamp resolution. Modify a tracked file before `git commit --amend --no-edit`, or change the message explicitly.
- **MEDIUM — `rev-list` failure handling is unspecified.** A common implementation such as `while ... < <(git rev-list ...)` masks the producer’s exit status even under `set -euo pipefail`, potentially allowing a push after enumeration failed. Capture and check `git rev-list` explicitly before iterating; fail closed with a tagged diagnostic.
- **MEDIUM — Pytest commands do not mechanically enforce the stated counts.** Pytest exits successfully when selected tests are skipped, so commands such as `uv run pytest ...` do not themselves detect “any skipped count above 0.” The `<fails_when>` text is observable to a human, but not enforced by the automated command. Add an explicit summary assertion or a pytest configuration/plugin mechanism that fails on unexpected skips.
- **MEDIUM — Several structural verifications are too weak.** `rg -q 'tmp_path'` can match only the module docstring, and `make help | rg -q 'hooks'` does not prove `.PHONY` membership or that the target runs the intended command. Use signature-specific matching or collection output for the fixture, and verify `.PHONY` plus `make -n hooks`.
- **MEDIUM — The planned inline `# noqa: S603` conflicts with repository conventions.** Suppressions are explicitly forbidden; false positives must be configured with rationale (`.claude/conventions.md:20-23`). Ruff enables `S` rules (`pyproject.toml:58-72`) and the test exceptions do not include S603 (`pyproject.toml:75-79`). Either revise the convention deliberately or add a justified configuration-level exception.
- **LOW — Remote ref deletion is implicitly rejected but undocumented.** A deletion supplies an all-zero `local_sha`; the ancestry command will error and be reported as a rewrite. That may be desirable, but it should be an explicit policy decision and preferably tested.
- **LOW — `make hooks` is not independently verified.** The persistent config value could remain correct even if the target recipe later becomes broken. A dry-run assertion against `make -n hooks` would cover the wiring without mutating config.

**Suggestions**

- Move the shell-boundary documentation amendment ahead of hook creation; update `CLAUDE.md`, `tools/setup.sh`, and README together.
- Replace the invalid `--worktree` absence criterion with origin/config-file checks.
- Add tests for first push to `master`, malformed or unavailable ancestry input, and remote branch deletion.
- Specify deterministic amend commands and explicit failure handling for `git rev-list`.
- Make skip/count and Makefile structure checks executable assertions rather than human inspection.
- Resolve the S603 policy through configuration instead of an inline suppression.

**Risk Assessment**

**HIGH** — The core hook design is sound, but the current wave ordering directly conflicts with repository policy, one acceptance criterion is invalid under Git’s config semantics, and the zero-SHA/master interaction leaves a policy-critical path undefined. These should be corrected before execution.

### 01-02

**Summary**

The plan has sound dependency ordering and a strong sandbox-test strategy, but it cannot currently satisfy its own live-demonstration criteria: successful hooks emit no tagged output, warning behavior is not asserted, and the claimed sync timing measures the whole commit. Verification also contains a pipefail-sensitive absence check and an invalid final `rg -c` expectation.

**Strengths**

- Wave 2 correctly depends on 01-01’s hook installation and test infrastructure.
- Keeping hook tests under `tests/unit/` ensures default execution; only `tests/integration/` is conditionally skipped (`tests/conftest.py:44-53`), and `make test` runs the complete `tests/` tree (`Makefile:33-34`).
- Failure-prone `codegraph` calls are protected with `command -v` and `||`, followed by explicit `exit 0`.
- The tests exercise real Git operations rather than directly invoking hooks.
- The minimal-PATH test is a credible negative control and avoids mutating global process state.
- `.codegraph/` and hypothesis scratch data are already ignored (`.gitignore:60-70`).
- The proposed tests fit the project’s unit-test convention (`.claude/conventions.md:71-75`) and pytest configuration (`pyproject.toml:90-95`).

**Concerns**

- **HIGH — Successful live runs cannot produce the required tags.** Both hooks only call `log` for absent/failing `codegraph`; successful `codegraph init -y` output is discarded and `codegraph sync -q` is quiet. Therefore Task 3 cannot capture literal `[post-checkout]` or `[post-commit]` tags on successful operations, making its acceptance criteria impossible.
- **HIGH — Required warning behavior is not tested.** The failing-shim tests assert operation success and retained state but never assert that a warning was printed. The post-checkout path has no absent-binary test at all, despite the must-have explicitly requiring an absent binary to preserve the new worktree and print a warning.
- **MEDIUM — The timing claim is not valid.** Timing `git commit` measures Git, object creation, other hooks, and `codegraph sync`; it does not isolate “post-commit sync wall-clock.” Recording that value as sync cost would make the SUMMARY assertion false.
- **MEDIUM — The absence-check pipeline is brittle under `pipefail`.** `rg 'exit 1' file | wc -l | rg -x '0'` succeeds only when the first `rg` failure is ignored. Under `set -o pipefail`, the intended zero-match state makes the pipeline fail. Use direct negation instead.
- **MEDIUM — Final verification contradicts the plan’s own ripgrep analysis.** `rg -c 'exit 1' file1 file2` generally exits non-zero when there are no matches and may print no zero-count lines, so it does not reliably produce “0 for both files.”
- **MEDIUM — The DoS mitigation overclaims protection from hangs.** `command -v`, `|| log`, and `exit 0` handle absence and non-zero termination, but not a hanging `codegraph` process. The threat register says hanging is mitigated when it is not.
- **LOW — “Explicit `exit 0` on every path” is too broad.** With `set -e`, failures in `dirname`, command substitution, `cd`, or warning output can terminate before the final line. The narrower claim that handled `codegraph` absence/failure does not block Git is supportable.
- **LOW — Argument verification is incomplete.** Behavioral tests only require first arguments `init` and `sync`; they do not prove `init -y` or `sync -q`. Static verification checks the latter but not the former.

**Suggestions**

- Log a success line after each successful invocation, for example `[post-checkout] initialized CodeGraph index` and `[post-commit] synchronized CodeGraph index`.
- Assert warnings and hook tags from captured Git stdout/stderr; add an absent-CodeGraph post-checkout worktree test.
- Replace both absence checks with `! rg -q 'exit 1' <files>`.
- Either label the measurement “total commit wall-clock” or instrument the hook to measure only `codegraph sync -q`.
- Narrow the threat statement to terminating failures, or add a portable timeout mechanism and test it.
- Verify exact recorded argv: `["init", "-y"]` and `["sync", "-q"]`.
- Add `git branch --list h01/codegraph-lifecycle` to cleanup verification, not only the worktree-path check.

**Risk Assessment**

**HIGH** — the implementation approach is viable, but the plan as written cannot pass its live-evidence acceptance criteria, and two explicit warning/absence requirements are not behaviorally demonstrated.

### 01-03

**Summary**

The plan has strong preservation controls and appropriately limits scope, but it is not executable as written. The single-commit policy conflicts with the required post-commit CodeGraph experiment, one verification necessarily fails after `git mv`, and the stale-reference command misplaces `--glob` after `--`.

**Strengths**

- Correctly orders `openspec archive --skip-specs` before `git mv`, preserving CLI root discovery.
- Uses pre/post checksums and tracked-file counts instead of relying only on command success.
- The documentation insertion assumptions match the files: both H1s are on line 1 and both provenance lines are on line 3 (`docs/requirements.md:1-3`, `docs/propossal_roadmap.md:1-3`).
- `tmp/` is genuinely ignored, so the experiment directory will not pollute commits (`.gitignore:60-61`).
- Scope boundaries are explicit: stale references are deferred rather than silently repaired.
- The banner count idiom is sound because exactly three explicit input files are searched; each file can contribute at most one `rg -l` line.

**Concerns**

- **HIGH — Commit ordering is internally impossible.** Task 3 must run after the relocation commit so the `post-commit` hook has executed, but D-16 and the verification note require one commit at the end. Committing Tasks 1–2 first necessarily creates at least one additional commit for the tracked SUMMARY, while committing only at the end means Task 3 tests the pre-rename index.
- **HIGH — The specs diff acceptance criterion must fail after the move.** `git diff --name-only HEAD -- .planning/legacy/openspec/specs` reports the destination files because that path does not exist in `HEAD`; a staged rename remains a `HEAD`-relative change. It cannot demonstrate “moved, never modified” (`.planning/phases/01-governance-freeze/01-03-PLAN.md:174`).
- **HIGH — The Phase 8 inventory command parses `--glob` as a path.** In `rg -l -- 'openspec/' --glob '!.planning/**' .`, `--` terminates option parsing, so the exclusion is not applied and ripgrep may also report nonexistent-path errors. The resulting list can include `.planning/**`, contrary to the stated handoff (`.planning/phases/01-governance-freeze/01-03-PLAN.md:286-287`).
- **MEDIUM — `$TMPDIR` is unsafe under `set -u`.** `git ls-files openspec > "$TMPDIR/pre.txt"` aborts when `TMPDIR` is unset, which is common on Linux. A fixed filename also risks collision between runs.
- **MEDIUM — CodeGraph’s old-path probe lacks an unambiguous pass/fail rule.** `codegraph explore "openspec/config.yaml"` may surface textual references to that string—several intentionally remain, including `README.md:14`, `README.md:207`, `CLAUDE.md:11`, and `CLAUDE.md:29`—rather than prove that an indexed file record still exists at the old path.
- **MEDIUM — `codegraph status` does not enforce the stated zero-file failure.** The automated command only checks its exit status; if it exits zero while reporting zero indexed files, the documented `<fails_when>` condition is not machine-observed.
- **MEDIUM — Banner placement acceptance is not verified.** The checks prove the phrase exists and preserve only the requirements H1/date. They do not prove that all three H1s remain on line 1, all banners begin on line 3, or the roadmap date remains unchanged.
- **LOW — The archive check counts names, not directories.** `ls | rg -c` would accept a regular file with the required suffix even though the criterion requires a directory.
- **LOW — The checksum example can mask an upstream failure without `pipefail`.** A failing `find`, `sort`, or inner `sha256sum` can still leave the final `sha256sum` successful unless execution explicitly guarantees `set -o pipefail`.

**Suggestions**

- Either permit two commits—relocation/banners first, evidence SUMMARY second—or run an explicit `codegraph sync -q` experiment before the single final commit and stop describing it as post-commit-hook evidence.
- Remove the destination-only `git diff` gate; retain the pre/post manifest checksum, or compare a `HEAD:openspec/specs` manifest against the relocated working-tree manifest with path prefixes normalized.
- Correct the inventory command to `rg -l --glob '!.planning/**' -- 'openspec/' .` and capture its exit status separately from its output.
- Use `scratch="$(mktemp -d "${TMPDIR:-/tmp}/kitty-setup-01-03.XXXXXX")"` for temporary manifests.
- Define an exact indexed-file test for CodeGraph rather than interpreting free-form `explore` output.
- Add explicit line checks, such as `sed -n '1p;3p'`, for each banner target, and parse `codegraph status` to reject a zero file count.
- Count archive directories with `find … -mindepth 1 -maxdepth 1 -type d -name '*-phase1-curated-bindings-revert-defaults'`.

**Risk Assessment**

**HIGH** — provenance protection is thoughtfully designed, but the current sequencing cannot measure the claimed post-commit behavior under the one-commit rule, and a mandatory Task 1 acceptance check will report failure even when the relocation is correct.

### 01-04

**Summary**

The ordering and migration strategy are sound, but the plan has two blocking verification defects and one internally impossible documentation claim. Fix the pipefail-sensitive absence check, require both phase-gate commands, and distinguish the canonical general-rule entry point from the intentionally separate stack-specific rules.

**Strengths**

- Wave 4 and dependencies on 01-01 through 01-03 correctly ensure hook and archive claims exist before documentation describes them.
- The migration accurately targets the current source structure in `CLAUDE.md:1-62`.
- Repointing `claude_md_path` is appropriately narrow; the current value is isolated at `.planning/config.json:69`.
- Updating the plug-point sentence is necessary because it currently names `CLAUDE.md` at `.claude/conventions.md:3-5`.
- The plan explicitly discloses both client-side hook bypasses rather than overstating enforcement.
- Exact JSON parsing and value checks are good observable signals.

**Concerns**

- **HIGH:** `rg -n 'openspec' AGENTS.md | rg -v 'legacy' | wc -l | rg -x '0'` fails in the desired state under `set -o pipefail`: when no forbidden line exists, the middle `rg -v` exits 1, making the whole pipeline non-zero despite printing `0`. It also passes when there is no frozen-history OpenSpec reference at all.
- **HIGH:** “Exactly one file in the repo carries agent rules” and “AGENTS.md carries every agent rule” contradict the deliberately retained conventions file, which identifies itself as containing stack-specific rules and contains many normative requirements at `.claude/conventions.md:3-5` and `.claude/conventions.md:10-76`.
- **HIGH:** The plan creates a rule requiring captured `make doctor` and `make test` output but verifies only `make test`. The existing rule already requires both at `CLAUDE.md:35-37`, and both targets exist at `Makefile:30-34`.
- **MEDIUM:** `test "$(cat CLAUDE.md)" = '@AGENTS.md'` strips every trailing newline, so a file with multiple trailing blank lines passes despite the one-line requirement. Additionally, `@AGENTS.md` is ten characters, not nine.
- **MEDIUM:** Several exactness claims lack matching verification: the frozen-history path is not positively required, all three hook filenames are not checked, and “one commit per plan” is checked only for presence—not exactly once or exclusively outside `.planning/`.
- **LOW:** The H1 check proves the heading exists, but not that it is on line 1 as required.

**Suggestions**

- Replace the OpenSpec check with a positive frozen-path assertion plus a pipefail-safe forbidden-line check, such as `rg -q '\.planning/legacy/openspec/' AGENTS.md` followed by an explicit `if ...; then exit 1; fi`.
- Add `make doctor` before `make test` and capture both outputs before completion.
- Reword the canonicality claim to “one canonical general-rule entry point,” explicitly preserving `.claude/conventions.md` as the linked home of stack-specific rules.
- Validate the stub byte-for-byte with Python or `cmp`, accepting only `@AGENTS.md` with zero or one trailing newline.
- Count exact phrase occurrences and verify `pre-push`, `post-commit`, and `post-checkout` separately.
- Check the H1 with a first-line equality test rather than an unanchored line-number search.

**Risk Assessment**

**HIGH** — the intended successful state can fail under `pipefail`, the plan can declare completion without its own required doctor gate, and its “one rule file” success criterion conflicts with a retained authoritative file on disk.

### 01-05

_Not reached in this pass before the run was stopped; see the full-context pass above, which
covers 01-05 with two CRITICAL and five HIGH findings._

---

## Orchestrator adjudication of the reviewer's claims

The reviewer's load-bearing claims were re-executed independently rather than taken on trust.
Disposable sandboxes and a throwaway clone were used; **the project working tree was not
modified**.

### Confirmed by execution

| Reviewer claim | Verdict | Evidence |
|---|---|---|
| `openspec archive` leaves the tree unstaged, so the plan's next command `git mv openspec …` fails | **CONFIRMED — blocking** | In a `--no-hardlinks` clone at `gsd/phase-1-governance-freeze`: `openspec archive phase1-curated-bindings-revert-defaults --skip-specs -y` → exit 0, "archived as '2026-09-23-…'", leaving 8 paths ` D` (unstaged deletions) and the new archive dir `??`. `git mv openspec .planning/legacy/openspec` → `fatal: bad source, source=openspec/changes/phase1-curated-bindings-revert-defaults/design.md` |
| the fix is `git add -A openspec` between archive and `git mv` | **CONFIRMED** | `git add -A openspec` → "8 files changed, 0 insertions(+), 0 deletions(-)"; then `mkdir -p .planning/legacy && git mv openspec .planning/legacy/openspec` → success. Tracked count **145 → 145**, so the plan's count invariant survives once staging is specified. `mkdir -p` is required — `git mv` does not create the parent |
| `git diff --name-only HEAD -- .planning/legacy/openspec/specs` cannot be empty after the move | **CONFIRMED** | destination-only pathspec reports `12 A` rows with nonzero numstat. With **both** sides in the pathspec it is `12 R100`, and the whole move is `145 R100` — so the correct gate is `git diff --cached --name-status HEAD -- openspec/specs .planning/legacy/openspec/specs` asserting all `R100`, or the pre/post checksum the plan already takes |
| `rg -l -- 'openspec/' --glob '!.planning/**' .` parses `--glob` as a path | **CONFIRMED** | stderr: `rg: --glob: No such file or directory (os error 2)` and `rg: !.planning/**: No such file or directory (os error 2)`, exit 0. The exclusion is silently discarded. It *appears* to work only because `rg` skips dot-directories by default (`rg -l --hidden 'openspec/' .` finds 20 `.planning/` hits). Correct form: `rg -l --glob '!.planning/**' -- 'openspec/' .` |
| `git config --get --worktree core.hooksPath` is not a valid absence check | **CONFIRMED, and stronger than the reviewer said** | git 2.55.0, `extensions.worktreeConfig` unset: after `git config core.hooksPath tools/hooks`, `git config --get --worktree core.hooksPath` prints **`tools/hooks`** and exits **0**. The acceptance criterion "finds nothing" is therefore false on a *correct* execution. With `extensions.worktreeConfig=true` it correctly exits 1. Use `git config --show-origin --get core.hooksPath` (→ `file:.git/config`) instead |
| the absence idiom inverts under `pipefail` | **CONFIRMED** | `bash -c "set -o pipefail; rg … \| rg -v … \| wc -l \| rg -x '0'"` prints `0` but exits **1**; without `pipefail` it exits 0. This repo's own shell convention is `set -euo pipefail` (`tools/setup.sh:16`, `tools/uninstall.sh:12`), so every absence gate fails in its passing state if run that way |
| `rg -c PAT f1 f2` cannot print "0 for both files" | **CONFIRMED** | zero matches → no stdout, exit 1. `01-02-PLAN.md:327` is unsatisfiable as written |
| `test "$(cat CLAUDE.md)" = '@AGENTS.md'` does not enforce one line | **CONFIRMED** | `printf '@AGENTS.md\n\n\n'` is 3 lines and the test **passes**, because `$(…)` strips all trailing newlines. The `max_lines: 1` artifact constraint is ungated |
| `@AGENTS.md` is ten characters, not nine | **CONFIRMED** | `printf '@AGENTS.md' \| wc -c` → 10. The plan says "nine" at `01-04-PLAN.md:40`, `:363-367`, `:450` |
| `CLAUDE.md:35-37` already requires captured `make doctor` **and** `make test` | **CONFIRMED** | `CLAUDE.md:35-37`; `01-04-PLAN.md:405` runs only `make test` |
| R0.10 mandates one commit per plan, so per-task RED/GREEN commits violate it | **CONFIRMED** | `.planning/REQUIREMENTS.md:59-65`: "**one commit per plan**, not one per task". `01-01-PLAN.md:167-170,203,227,308-309` and `01-02-PLAN.md:139-168,203-227` require RED and GREEN commits per task; `01-03-PLAN.md:165` by contrast says "as part of the plan's single commit (D-16)" — the plan set is internally inconsistent |
| R0.11 / R0.12 own the quality gap the plan calls unowned | **CONFIRMED** | `.planning/REQUIREMENTS.md:67-73` (R0.11, `src/` clean, **Phase 2**) and `:74-81` (R0.12, `tests/` clean, **Phase 8.5**) |
| the bandit baseline in 01-05 misreads confidence as severity | **CONFIRMED, and already corrected upstream** | measured: `Total issues (by severity): Low: 19, Medium: 8, High: 0`; `(by confidence): Low: 6, Medium: 1, High: 20`. `.planning/REQUIREMENTS.md:70-72` already says so in as many words: "bandit reports **0 high** (8 medium, 19 low — an earlier report of '20 high' misread bandit's *confidence* column as severity)" |
| `.planning/PROJECT.md:74-75` states the opposite merge policy | **CONFIRMED** | "**Merging to `master`** — agents push a feature branch only; integration is the owner's call (R0.4)". Untouched by 01-05 task 2, which edits only the Key Decisions row at `:125` |
| `.planning/PROJECT.md:99-103` still forbids new shell scripts | **CONFIRMED** | "Bash exists only in `tools/setup.sh` and `tools/uninstall.sh` … **No new shell scripts.**" |
| `README.md:165` repeats the two-script-only assertion | **CONFIRMED** | `README.md:165-166`; and `01-05-PLAN.md:178` actively **gates `README.md` as unmodified**, so no plan in this phase may fix it |
| `CLAUDE.md:42-49` forbids new shell scripts until 01-04 amends it | **CONFIRMED** | `CLAUDE.md:42-49`; hooks land in waves 1-2, the amendment in wave 4 |
| `# noqa: S603` conflicts with repo convention | **CONFIRMED** | `.claude/conventions.md:21-23` ("Pyright strict mode … without suppressions"; "Never silence findings with `# noqa` … configure it explicitly with rationale in the config file"); ruff selects `"S"` at `pyproject.toml:58-73`; `per-file-ignores` for `tests/**/*.py` is `["S101","S108","S604"]` at `:79` — **S603 is absent**. `01-01-PLAN.md:159` instructs an inline `# noqa: S603` |
| `.claude/conventions.md` requires a `make validate` target that does not exist | **CONFIRMED** | `.claude/conventions.md:63` and `:69`; `Makefile` `.PHONY` has no `validate` (`rg '^validate' Makefile` → no match) |
| `01-VALIDATION.md:39` keeps commit-per-task wording under a phrasing task 2's grep misses | **CONFIRMED** | `:39` "**After every task commit:** the grep/shell check for that task's requirement" — `rg -ni 'commit per task'` does not match "task commit" |
| the master heuristic rejects squash merges and non-`gsd/phase-*` branches | **CONFIRMED** | sandbox: squash merge → `rc=1`. `.planning/config.json` sets `milestone_branch_template: "gsd/{milestone}-{slug}"`, and `gsd/planning-bootstrap` already exists — neither matches `gsd/phase-*` |

### Refuted or narrowed

| Claim | Adjudication |
|---|---|
| (my own earlier draft) the `--worktree` criterion is merely "judgement-only, LOW" | **Wrong — withdrawn.** Execution shows the criterion asserts the opposite of the truth. The reviewer's HIGH rating is correct |
| `.gitignore:69-70` / `:60-70` / `:60-61` (three different citations across the passes) | **Narrowed.** The operative line is `.gitignore:70` `.codegraph/`. The surrounding-range citations are loose but not wrong |
| "the plan's `rg -l … \| wc -l` banner check does not prove no unintended fourth banner exists" | **Narrowed to a non-issue.** The acceptance wording is scoped to exactly those three files, and each contributes at most one `rg -l` line, so the check matches its own claim. The reviewer says as much |
| `Makefile:33-34` / `Makefile:30-34` as the `make test` citation | **Confirmed but renumbered.** `make test` is `Makefile:33-34`; `doctor` is `:30-31` |

### Orchestrator findings not raised by the reviewer

- **MEDIUM — the zero-SHA skip also silently ungates the very first `master` push.** Both reviewer
  passes flag the ambiguity; neither states the consequence: if the skip is the `continue` that a
  working implementation needs (`$ZERO_SHA..$local_sha` is not a valid rev range), then a
  first-ever `master` push — a fresh remote, a fork, a re-created ref — carries every commit past
  the provenance guard unchecked, while `must_haves.truths` claims direct-to-`master` rejection
  unconditionally.
- **MEDIUM — `01-05-PLAN.md:265-267` sizes the verification map at twelve rows; it has twenty**
  (`rg -c '^\| 01-0' 01-VALIDATION.md` → 20) with 21 `⬜ pending` markers. Combined with the
  vacuous `TBD` gate, nothing detects an under-resolved map.
- **LOW — `01-PATTERNS.md` still carries the pre-decision test path.** `:18`, `:280`, `:523` and
  `:549` say `tests/integration/test_git_hooks.py` while the plans and `01-VALIDATION.md` say
  `tests/unit/`. To its credit `01-PATTERNS.md:300` poses the choice explicitly and demands the
  planner decide — and the planner decided correctly — but PATTERNS.md is loaded as `@context` by
  both hook plans, so the stale heading is the first thing an executor reads about that file's
  location.
- **LOW — `01-05-PLAN.md:198` cites `.planning/ROADMAP.md` lines 18-39 for the Universal Phase
  Gate "whose step 6 still says 'commit per task'", but step 6 spans `:39-42` and the phrase is on
  `:40`** — the cited range ends on the step's first line.
- **LOW — the absence idiom also passes vacuously on a missing file.** `rg PAT nosuchfile | wc -l |
  rg -x '0'` exits 0. Every instance happens to be paired with a sibling existence gate
  (`test -x tools/hooks/post-checkout` at `01-02-PLAN.md:181`; `rg -q 'codegraph sync -q' …` at
  `:240`; `rg -q '^# kitty-setup — Agent Rules$' AGENTS.md` at `01-04-PLAN.md:240`), so the plans
  are safe today — but none says the pairing is load-bearing.
- **LOW — BSD `wc` padding.** `printf '       0\n' | rg -x '0'` exits 1, and BSD/macOS `wc -l` pads
  pipe output, so these gates will false-fail on the Mac this project verifies on in Phases 9-10.
  Recorded LOW because it was simulated, not observed on a macOS host.

### What held up under execution — verified strengths

Every git mechanism the plan set depends on was executed and behaved as the plans claim:

- A relative `core.hooksPath=tools/hooks` in the **shared** config resolves against each
  worktree's own root; a new worktree's own `tools/hooks/post-checkout` ran
  (`01-RESEARCH.md` Pattern 1, Pitfall 4).
- `git worktree add` fires `post-checkout` with `$1` = all-zero SHA, `$3` = `1`, cwd = the **new**
  worktree; an ordinary `git checkout -b` / `git checkout master` gives a real prev-HEAD. The
  discriminator works, exactly as `01-RESEARCH.md:225-232` illustrates.
- The pre-push master heuristic: direct commit on `master` → rejected with `[pre-push]` on stderr;
  fast-forward merge of `gsd/phase-*` → allowed; `--no-ff` merge → allowed; phase branch deleted →
  rejected (the plan's own disclosed limit, confirmed real).
- `exit 1` inside the `while read` loop really aborts the push — git supplies the ref list on fd 0
  rather than through a pipe, so the loop is not a subshell.
- `tests/unit/` placement is **necessary, not arbitrary**: `tests/conftest.py:44-53` skips only
  `tests/integration/` unless `KITTI_INTEGRATION=1`, and `Makefile:34` runs `uv run pytest tests/`.
- The wave chain genuinely forces archive → move → banner → instruction file: `openspec/changes/
  phase1-curated-bindings-revert-defaults/` exists, `openspec/README.md` does **not**, and
  `.planning/legacy/` does **not**, so the banner target cannot exist before the move.
- The bypass disclosure is a grep gate, not a promise (`01-01-PLAN.md:320`, `01-04-PLAN.md:342`).
- `core.hooksPath` shadows nothing: no `.pre-commit-config.yaml`, no non-sample `.git/hooks/*`.
- All 53 `<fails_when>` clauses name an observable signal — an exit status plus the specific
  condition and what it means — rather than restating "it fails". The weakness is *enforceability*,
  not observability: several describe states the paired `<automated>` command's exit status cannot
  detect.

---

## Consensus Summary

One reviewer lane ran (`opencode`, per `review.default_reviewers`), so there is no multi-reviewer
consensus to compute. Under the single-reviewer rule its HIGH findings count at full weight, and
they are treated that way here. The orchestrator's independent execution pass is **first-party**
and is not counted as a second vote — it is used only to confirm, refute or sharpen what the
reviewer said, which it did in every case listed above.

**Verdict: do not execute Phase 1 as written.** The architecture, the wave ordering and four of the
five plans' mechanisms are sound and were verified by execution. What blocks the phase is a set of
execution-level contradictions, most of which would force the executor either to fail outright or
to violate the governance rules the phase exists to establish.

### Agreed Strengths

Single-reviewer, so nothing is "agreed" in the two-reviewer sense. Where the reviewer and the
orchestrator's execution pass independently landed on the same conclusion:

- `tests/unit/` placement is required by `tests/conftest.py:44-53`, not stylistic.
- The hook prelude, `if ! git merge-base --is-ancestor`, and the `|| log` + terminal `exit 0`
  pattern are all correct treatments of `set -e`.
- The tracer approach — prove `core.hooksPath` → tracked hook → verdict → test on one path before
  adding two more hooks — paid off; the mechanism holds under execution.
- The archive-before-move and move-before-banner intent is right and is structurally enforced.
- Negative controls (fast-forward, new-branch, failing shim, absent binary) are real controls, not
  decoration.
- The bypass disclosure is machine-gated rather than promised in prose.

### Agreed Concerns

The blockers, in the order they would bite an executor:

1. **01-01 / 01-02 — per-task RED/GREEN commits violate R0.10's one-commit-per-plan**
   (`.planning/REQUIREMENTS.md:59-65`), which this very phase is installing. 01-03 already does it
   correctly, so the plan set contradicts itself.
2. **01-01 — the Stack allow-list forbids the files wave 1 creates.** `CLAUDE.md:42-49` permits
   Bash only in the two bootstrap scripts; the amendment is in wave 4. The hook header is also
   instructed to cite an amendment that has not happened yet.
3. **01-01 — `git config --get --worktree core.hooksPath` "finds nothing" is false** on a correct
   execution (it prints `tools/hooks`, exit 0).
4. **01-01 — first-ever `master` push is undefined** where the zero-SHA skip and the master guard
   meet.
5. **01-02 — the live-demonstration acceptance criteria cannot pass.** Successful hooks emit no
   `[post-checkout]` / `[post-commit]` tag: `codegraph init` output is discarded and `sync -q` is
   silent. The required warning behaviour is also never asserted, and `post-checkout` has no
   absent-binary test at all.
6. **01-03 — the central command sequence does not run.** `openspec archive` leaves deletions
   unstaged, so the prescribed `git mv` dies with `fatal: bad source`. One missing
   `git add -A openspec` (reproduced, along with the fix).
7. **01-03 — the specs "unmodified" acceptance check cannot pass** after a correct move, and
   **01-03's post-commit CodeGraph experiment cannot coexist** with one commit per plan.
8. **01-03 — the Phase 8 hand-off inventory is malformed**: `--glob` lands after `--` and is
   silently consumed as a path.
9. **01-04 — the plan asserts the Stack section is true while deliberately keeping known-false
   text**, and its "exactly one file carries agent rules" success criterion contradicts the
   deliberately retained `.claude/conventions.md`.
10. **01-04 — its own verification omits `make doctor`**, which `CLAUDE.md:35-37` and the rule this
    plan writes both require.
11. **01-04 / 01-05 — `README.md:165` and `.planning/PROJECT.md:99-103` keep asserting "no new
    shell scripts"**, and `.planning/PROJECT.md:74-75` keeps asserting the *opposite* merge policy.
    No plan fixes any of them, and `01-05-PLAN.md:178` actively gates `README.md` as unmodified.
12. **01-05 — the phase-end merge/push violates the doctor-green policy it just installed**, and
    **the post-push evidence cannot land in the plan's single commit**.
13. **01-05 — the quality-ownership claim and the bandit baseline are stale and false**; R0.11 and
    R0.12 own the gap, and `.planning/REQUIREMENTS.md:70-72` already documents the exact
    misreading the plan repeats.
14. **01-05 — the verification-map gate is vacuous** (`TBD` has zero occurrences; the 21
    `⬜ pending` markers are ungated), and **the phase-scope diff goes vacuous** once the same task
    merges into `master`.

Cross-cutting: the `rg … | wc -l | rg -x '0'` absence idiom **inverts under `set -o pipefail`** —
it prints `0` and exits 1 in its passing state. Since this repo's shell convention is
`set -euo pipefail`, every absence gate in the phase is affected. `test -f <file> && ! rg -q PAT
<file>` is the robust replacement and also closes the missing-file vacuity and the BSD-`wc` padding
hole in one move.

### Divergent Views

- **Within the lane's two passes.** The full-context pass rated the zero-SHA/first-push question,
  the 01-02 live-transcript tags, the 01-03 commit ordering and the 01-03 specs-diff criterion as
  MEDIUM; the per-plan pass rated the same four as HIGH. Execution supports the higher rating for
  the specs-diff criterion (it cannot pass) and for the live-transcript tags (they cannot be
  emitted); the other two are judgement calls. They are counted at the higher severity.
- **Reviewer vs orchestrator.** The orchestrator's first draft rated the `--worktree` criterion LOW;
  execution showed the reviewer's HIGH was right, and the LOW is withdrawn. No finding went the
  other way.
- **Not a divergence, worth stating.** Both passes rate plans 01-01 through 01-04 as fundamentally
  sound designs with fixable defects, and both rate 01-05 as the weakest plan. The orchestrator's
  execution pass agrees.

---

## Verification coverage

Authority: `grep` plus live execution (`.planning/config.json` → `plan_review.source_grounding:
true`, `source_grounding_authority: "grep"`, `intel.enabled: false`). A signature mismatch is
therefore UNCHECKABLE, not MISSING, and a MISSING symbol is needs-acknowledgement rather than a
hard block. A clean row here means a command was run, not that nothing was looked at.

**Excluded from drift verification** per each plan's `<artifacts_this_phase_produces>` table —
created **by** this phase, and each absence positively confirmed rather than assumed:
`tools/hooks/pre-push`, `tools/hooks/post-commit`, `tools/hooks/post-checkout`,
`tests/unit/test_git_hooks.py`, `Makefile` target `hooks:`, `.planning/legacy/openspec/` (whole
tree), `.planning/legacy/openspec/README.md`, `AGENTS.md`.

### Repo files, line ranges and literals

| Cited symbol / path | Verdict | Evidence |
|---|---|---|
| `tests/conftest.py:44-53` `KITTI_INTEGRATION` path gate | VERIFIED | `:44` `def pytest_collection_modifyitems(...)` → `:53` `item.add_marker(skip)`; skips only `tests/integration` |
| `tests/conftest.py:18` `INTEGRATION_ENV_VAR` | VERIFIED | `:18` |
| `tests/conftest.py:87-92` `scratch_dir`/`tmp_path` | VERIFIED | `:87` `def scratch_dir(tmp_path: Path)` |
| `tmp_path` is the house fixture | VERIFIED | 29 files under `tests/` |
| stdlib temp-dir context manager unused under `tests/` | VERIFIED | `rg -c 'TemporaryDirectory\|mkdtemp' tests/` → no matches |
| `tools/setup.sh:1-21` prelude | VERIFIED | `:1` shebang, `:16` `set -euo pipefail`, `:18` `REPO_ROOT`, `:19` `cd`, `:21` `log()` |
| `tools/uninstall.sh:1-17` prelude | VERIFIED | `:1`, `:12`, `:14`, `:15`, `:17` |
| `tools/uninstall.sh:45-47` `${VAR:-} == "1"` idiom | VERIFIED | `:45-47` |
| `tools/uninstall.sh:82-85` `KITTI_*` namespace | VERIFIED | `:82` `KITTI_FORCE` |
| `Makefile:1-20` `.PHONY` + `help:` | VERIFIED | `:6`, `:8-19` |
| `Makefile:30-31` `doctor`, `Makefile:33-34` `test` | VERIFIED | `:31` `@my-kitty doctor`, `:34` `@uv run pytest tests/` |
| `Makefile` has NO `validate` target | VERIFIED (MISSING target) | `rg '^validate' Makefile` → no match, while `.claude/conventions.md:63,69` require it |
| `.gitignore:70` `.codegraph/` | VERIFIED | `:70` |
| `.claude/conventions.md:3-5` plug-point; `:5` names `CLAUDE.md` | VERIFIED | `:5` is the **only** `CLAUDE` occurrence, so the 1-insertion/1-deletion + `rg -n 'CLAUDE'`→0 criteria are jointly satisfiable |
| `.claude/conventions.md:21-23` no-suppressions rule | VERIFIED | `:21` strict pyright without suppressions; `:22-23` never `# noqa` |
| `.claude/conventions.md:48` "Targeted single-file commands" | VERIFIED | `:48` |
| `.claude/conventions.md:63,69` require `make validate` | VERIFIED | both lines |
| `pyproject.toml:58-73` ruff selects `"S"` | VERIFIED | `:68` `"S", # bandit-lite` |
| `pyproject.toml:75-79` test per-file-ignores `["S101","S108","S604"]` — **S603 absent** | VERIFIED | `:79` |
| `pyproject.toml:87-88` `[tool.bandit] exclude_dirs = ["tests","tmp"]` | VERIFIED | `:87-88` |
| `.planning/config.json:69` `claude_md_path": "./CLAUDE.md"` (2-space indent, `./`, trailing comma) | VERIFIED | `:69` |
| `.planning/config.json` `milestone_branch_template: "gsd/{milestone}-{slug}"` | VERIFIED | `git` block |
| `CLAUDE.md` is 62 lines | VERIFIED | `wc -l` → 62 |
| `CLAUDE.md:11-14` stale bullet (pending change dir + deleted skills path) | VERIFIED | `:11`, `:13` |
| `CLAUDE.md:24` `- **No auto-commit.**` | VERIFIED | `:24` |
| `CLAUDE.md:28-29` "Skill outputs land on disk" + `openspec/changes/<id>/` parenthetical | VERIFIED | `:28-29` |
| `CLAUDE.md:30-31` spec-primacy bullet | VERIFIED | `:30` |
| `CLAUDE.md:35-37` requires captured `make doctor` **and** `make test` | VERIFIED | `:35-37` |
| `CLAUDE.md:42-49` Stack rule "No new shell scripts elsewhere" | VERIFIED | `:42-49` |
| `README.md:165-166` "Bash exists only inside `tools/setup.sh` and `tools/uninstall.sh`" | VERIFIED | `:165-166` |
| `README.md` exists (01-05's unmodified-README gate target) | VERIFIED | 14.3K |
| `.claude/skills/` does NOT exist | VERIFIED | `.claude/` holds only `conventions.md`, `settings.local.json` |
| `docs/requirements.md:1` H1 literal; `:3` `Date: 2026-05-01.` | VERIFIED | both |
| `docs/propossal_roadmap.md:1` H1 literal; `:3` `Date: 2026-05-01.` | VERIFIED | both — banner-on-line-3 is achievable |
| `docs/agent-iteration.md` exists | VERIFIED | present |
| `openspec/changes/phase1-curated-bindings-revert-defaults/` | VERIFIED | present |
| `openspec/config.yaml`, `openspec/specs/` | VERIFIED | both present |
| `openspec/README.md` does NOT exist | VERIFIED | supports "authored from scratch" |
| `openspec/changes/archive/` has no pre-existing suffix match | VERIFIED | 20 dirs, suffix grep → 0 |
| `.planning/legacy/` does NOT exist | VERIFIED | `git mv` needs `mkdir -p` first (confirmed by execution) |
| `.planning/PROJECT.md:74-75` "agents push a feature branch only; integration is the owner's call" | VERIFIED | `:74-75` |
| `.planning/PROJECT.md:99-103` "No new shell scripts." | VERIFIED | `:99-103` |
| `.planning/PROJECT.md:121` Key Decisions header, 7 data rows | VERIFIED | 7 rows |
| `.planning/PROJECT.md:125` git row "agents commit per task" | VERIFIED | `:125` |
| PROJECT.md literals `R2.8 oracle test is built FIRST` / `Keybinding model is native per-OS` / `macOS verification` | VERIFIED | 3 matching lines |
| `.planning/ROADMAP.md:18-42` Universal Phase Gate; step 6 at `:39-42`, "commit per task" at `:40` | VERIFIED | plan cites 18-39, one line short |
| `.planning/ROADMAP.md:28,39-42` doctor-and-test-green-before-merge | VERIFIED | `:28` step 5, `:39-42` step 6 |
| `.planning/ROADMAP.md:29-38` reworded measured quality gate | VERIFIED | includes "bandit 0 high / 8 medium / 19 low" at `:35` |
| "commit per task" appears in exactly `.planning/ROADMAP.md:40` + `.planning/PROJECT.md:125` | VERIFIED | 2 hits repo-wide |
| "one commit per plan" absent from tracked files outside `.planning/` | VERIFIED | only `.planning/**` matches |
| `rg -c '^### Phase [0-9]+:' .planning/ROADMAP.md` → `10`, but 11 sections exist | VERIFIED | `### Phase 8.5:` at `:210` is unmatched by the regex |
| ROADMAP Progress list has 10 rows (Phase 8.5 absent from it) | VERIFIED | `:57-66` |
| `.planning/REQUIREMENTS.md:59-65` R0.10 one commit per plan | VERIFIED | `:59-65` |
| `.planning/REQUIREMENTS.md:67-73` R0.11 (`src/` clean, Phase 2) | VERIFIED | `:67`, and `:372` maps R0.11 → Phase 2 |
| `.planning/REQUIREMENTS.md:70-72` documents the bandit confidence-vs-severity misreading | VERIFIED | verbatim |
| `.planning/REQUIREMENTS.md:74-81` R0.12 (`tests/` clean, Phase 8.5) | VERIFIED | `:74-81` |
| phase base commit `5452f54` | VERIFIED | `git merge-base master HEAD` |
| local `master` ref and `origin` remote exist | VERIFIED | `origin git@gitlab.com:cco-open-src/kitty-setup.git` |
| no `.pre-commit-config.yaml`, no non-sample `.git/hooks/*`, `core.hooksPath` unset | VERIFIED | nothing shadowed |
| `gsd-core/bin/lib/profile-output.cjs:958-963` consumes `claude_md_path` | VERIFIED | honoured because no `runtime` key ⇒ `isClaudeRuntime` true |
| `agent-md-refactor` is a global skill | VERIFIED | in the session roster; no project-local skills dir |

### Baseline numbers cited by plan 01-05

| Cited | Verdict | Measured |
|---|---|---|
| ruff 28 (`src tests tools`) | VERIFIED | 28 |
| black 11 files would be reformatted | VERIFIED | "11 files would be reformatted, 54 would be left unchanged" |
| vulture 12 (`src tests`) | VERIFIED | 12 |
| bandit "27 issues (20 high, 1 medium, 6 low)" | MISSING / WRONG | severity High 0 / Medium 8 / Low 19; `20/1/6` is the confidence table |
| pyright 571 errors | UNCHECKABLE | not executed (multi-minute whole-repo run); `.planning/ROADMAP.md:34` and `REQUIREMENTS.md:70` corroborate and add "19 in `src/`", which 01-05 omits |

### Phase artifact anchors cited by heading

| Cited anchor | Verdict |
|---|---|
| `01-CONTEXT.md` D-01 … D-16 | VERIFIED — all sixteen present |
| `01-RESEARCH.md` Pattern 1 / 2 / 3 | VERIFIED — `:162`, `:182`, `:209` |
| `01-RESEARCH.md:225-232` illustrative post-checkout logic | VERIFIED — matches the zero-SHA + branch-flag gate |
| `01-RESEARCH.md` Pitfall 1-5 | VERIFIED — `:268`, `:274`, `:280`, `:286`, `:291` |
| `01-RESEARCH.md` Open Questions / Security Domain / Assumptions Log / Runtime State Inventory / Alternatives Considered / Package Legitimacy Audit | VERIFIED — `:361`, `:423`, `:351`, `:251`, `:105`, `:115` |
| `01-VALIDATION.md` Test Infrastructure / Sampling Rate / Per-Task Verification Map / Wave 0 / Manual-Only / Known Threat Patterns / Sign-Off | VERIFIED — `:21`, `:37`, `:48`, `:93`, `:137`, `:146`, `:167` |
| `01-VALIDATION.md:31-33` "neither make test nor make doctor covers governance content" | VERIFIED |
| `01-VALIDATION.md:39` "After every task commit" | VERIFIED — surviving commit-per-task wording |
| `01-VALIDATION.md:58-77` map rows | VERIFIED — **20** rows, 21 `⬜ pending`; plan 01-05 says "twelve" → MISSING |
| `01-VALIDATION.md` contains `TBD` | MISSING — zero occurrences, so `01-05-PLAN.md:336` is vacuous |
| `01-PATTERNS.md` Shell prelude / Error-abort / Env-var escape hatch / subprocess invocation + assertion / Makefile target / Markdown opening / `tools/hooks/pre-push…` / legacy README / `CLAUDE.md`+`config.json` / FROZEN banner | VERIFIED — `:488`, `:505`, `:510`, `:526`, `:531`, `:536`, `:139`, `:470`, `:474`, `:441` |
| `01-PATTERNS.md` test-module path | AMBIGUOUS — `:18`, `:280`, `:523`, `:549` say `tests/integration/`; `:300` demands the planner choose and the plans chose `tests/unit/` |

### External tools and flags

| Cited | Verdict | Evidence |
|---|---|---|
| `openspec` 1.13.1 at `~/.volta/bin/openspec` | VERIFIED | `--version` |
| `openspec archive --skip-specs` / `-y` | VERIFIED | `--skip-specs   Skip spec update operations`; `-y, --yes      Skip confirmation prompts` |
| `openspec archive` prints "Skipping spec updates (--skip-specs flag provided)." | VERIFIED | observed verbatim in the disposable clone |
| `codegraph` 1.6.0 at `/home/bazzite/.local/bin/codegraph` | VERIFIED | `--version` |
| `codegraph init -y` = "Non-interactive: skip every prompt" | VERIFIED | `--help` |
| `codegraph sync -q` = "Suppress output (for git hooks)" | VERIFIED | `--help`, verbatim |
| `codegraph status` reports a *changed filename* | MISSING | it reports aggregate file/node counts and freshness; `01-02-PLAN.md:269-271` and `01-03` rely on a filename |
| opencode 1.18.31 at `/home/bazzite/.opencode/bin/opencode` | VERIFIED | `--version` |
| git 2.55.0 (the version all git-semantics findings were established on) | VERIFIED | `git --version` |

### Live behavioural verification (disposable sandboxes and a throwaway clone; project tree untouched)

| Claim | Verdict |
|---|---|
| `git worktree add` → `post-checkout` with `$1`=zero SHA, `$3`=1, cwd=new worktree | VERIFIED |
| ordinary branch switch → real prev-HEAD (discriminator works) | VERIFIED |
| relative `core.hooksPath` in shared config resolves per worktree | VERIFIED |
| direct commit on `master` → rejected, `[pre-push]` on stderr | VERIFIED |
| fast-forward merge of `gsd/phase-*` → allowed | VERIFIED |
| `--no-ff` merge of `gsd/phase-*` → allowed | VERIFIED |
| `--no-ff` merge with phase branch deleted → rejected (disclosed limit) | VERIFIED |
| squash merge of `gsd/phase-*` → rejected (**undisclosed**) | VERIFIED |
| `exit 1` inside the `while read` loop aborts the push | VERIFIED |
| `openspec archive` leaves unstaged deletions; `git mv` → `fatal: bad source` | VERIFIED |
| `git add -A openspec` + `mkdir -p .planning/legacy` + `git mv` succeeds; tracked count 145 → 145 | VERIFIED |
| destination-only pathspec after `git mv` → `A` rows; both sides → `145 R100` | VERIFIED |
| `rg -l -- PAT --glob '!…' .` consumes `--glob` as a path (two `No such file or directory` errors, exit 0) | VERIFIED |
| `rg` skips dot-directories by default (`--hidden` yields 20 `.planning/` hits) | VERIFIED |
| `git config --get --worktree core.hooksPath` prints `tools/hooks`, exit 0, with `extensions.worktreeConfig` unset | VERIFIED |
| the absence idiom exits 1 under `set -o pipefail` in its passing state | VERIFIED |
| `rg -c PAT f1 f2` prints nothing and exits 1 on zero matches | VERIFIED |
| `rg PAT missingfile \| wc -l \| rg -x '0'` exits 0 (vacuous pass) | VERIFIED |
| `printf '       0\n' \| rg -x '0'` exits 1 (BSD `wc` padding would false-fail) | VERIFIED |
| `test "$(cat f)" = '@AGENTS.md'` passes on a 3-line file | VERIFIED |
| `@AGENTS.md` is 10 bytes | VERIFIED |

### UNCHECKABLE / skipped — and why

- **pyright's 571-error baseline** — not executed; a whole-repo pyright run is multi-minute and a
  read-only review does not need it. Two tracked documents corroborate the figure.
- **`--force-with-lease` producing the same non-ancestor stdin signature as `--force`**
  (`01-01-PLAN.md` assumption A2) — not reproduced; only `--force` was executed. Already carried as
  a flagged assumption.
- **codex CLI reading `AGENTS.md` by nearest-file-wins** (`01-04-PLAN.md` assumption A1) — no
  `codex` binary on this host. Already carried as a flagged assumption; `CLAUDE.md`'s `@AGENTS.md`
  import covers the Claude runtime independently.
- **`codegraph sync` behaviour after a bulk `git mv`** (RESEARCH Open Question 2) — not executed;
  it would mutate the machine-local index, and it is precisely the experiment `01-03` task 3 exists
  to run. UNCHECKABLE by design and correctly scoped as a plan task.
- **`agent-md-refactor` findings against `AGENTS.md`** — the file is an artifact of this phase.
  UNCHECKABLE by construction.
- **`make doctor` / `make test` current state** — not run; both invoke `my-kitty` against the live
  kitty install and could alter the user's config during a read-only review.
- **BSD/macOS `wc -l` padding as a field failure** — the padding was simulated, not observed on a
  macOS host (none reachable). This is why that item is LOW rather than MEDIUM.
- **Plan 01-05 in the supplementary per-plan pass** — not reached before the run was stopped. The
  full-context pass covers 01-05 in depth (2 CRITICAL + 5 HIGH), so this is a redundancy gap, not a
  coverage gap.
- **A genuinely independent second model** — only one lane is configured
  (`review.default_reviewers: ["opencode"]`). Every finding here therefore comes from one reviewer
  plus first-party execution. This is the largest remaining coverage limitation and the reason no
  multi-reviewer consensus is claimed.

Nothing was passed over silently: every symbol, path, line range, CLI flag and command the five
plans cite outside their own `<artifacts_this_phase_produces>` tables appears above with a verdict.

---

To incorporate this feedback into planning:

```
/gsd-plan-phase 1 --reviews
```

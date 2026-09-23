# Phase 1: Governance & Freeze - Research

**Researched:** 2026-09-23
**Domain:** Repo governance tooling — OpenSpec CLI archival, git hook wiring (`core.hooksPath`, worktrees), CodeGraph index lifecycle, agent-instruction-file conventions (AGENTS.md).
**Confidence:** HIGH — every load-bearing claim below was either executed directly against the real `openspec`/`git`/`codegraph` binaries and this repo, reproduced in a disposable sandbox, or read verbatim from GSD's own source. No claim in the Standard Stack / Architecture sections rests on training-data guesswork alone; where it does, it is tagged `[ASSUMED]` and listed in the Assumptions Log.

## Summary

This phase writes almost no code — it is a documentation and git-plumbing phase. The two riskiest technical claims baked into CONTEXT.md's decisions were **both independently reproduced in this session and confirmed true**: (1) `openspec archive --skip-specs -y` succeeds and leaves `openspec/specs/` byte-identical even though the change's delta has 7 outstanding validator issues, and (2) a single `core.hooksPath` setting (no `--worktree` flag) in the shared repo config is honored by every linked worktree, with a **relative** path resolving against **each worktree's own root** — so one `git config core.hooksPath tools/hooks` run once covers every future phase worktree without per-worktree setup. A third open question in CONTEXT.md — whether hooks fire on `git worktree add` at all — is also settled: `post-checkout` **does** fire, with `cwd` set to the new worktree's root and the previous-HEAD argument zeroed out, which is the exact signal needed to distinguish "brand-new worktree" (run `codegraph init`) from "ordinary branch switch" (do nothing or `sync`).

The remaining pieces are conventions, not mechanics: `AGENTS.md` is a real, governance-neutral, community/Linux-Foundation-stewarded standard that Codex, opencode, Cursor, and others read natively; GSD's own tooling (`gsd_run project-instruction-file`) already resolves to `AGENTS.md` for this project, and GSD's `cross_ai: true` PLAN.md frontmatter key is not a phase invention — it is already read by `gsd-core/workflows/execute-phase.md`'s `cross_ai_delegation` step. `.planning/config.json`'s `claude_md_path` currently reads `"./CLAUDE.md"` and is consumed by `gsd-core/bin/lib/profile-output.cjs` when GSD's own tooling assembles Claude-runtime instruction content — repointing it to `./AGENTS.md` is what makes future GSD-managed content land in the canonical file instead of the soon-to-be-stub `CLAUDE.md`.

**Primary recommendation:** Sequence the phase as archive → `git mv` → banners → `AGENTS.md`/`CLAUDE.md` rewrite → `tools/hooks/` (pre-push + post-checkout + post-commit) wired via one `git config core.hooksPath tools/hooks` → `.planning/config.json` repoint → `agent-md-refactor` validation pass. Every step in that chain has been reproduced live in this session except the final in-repo execution itself (deliberately not run against the real repo — see Package/Execution boundary below).

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Agent instruction content (rules, mantra, git policy) | Repo docs (`AGENTS.md`) | Claude-specific shim (`CLAUDE.md`) | `AGENTS.md` is the cross-CLI standard; `CLAUDE.md` becomes a 1-line `@AGENTS.md` import so Claude Code's own memory loader still finds rules without duplicating them |
| Spec/planning source of truth | `.planning/` (GSD) | `.planning/legacy/openspec/` (history) | D-02/D-14: OpenSpec is retired to a subtree GSD owns; it is not a second root |
| Git branch/merge policy enforcement | git hook (`tools/hooks/pre-push`) | Documentation (`AGENTS.md`) | D-07: policy must be structural, not just written, because cross-AI CLIs don't share one assistant's settings |
| CodeGraph index freshness | git hooks (`tools/hooks/post-checkout`, `post-commit`) | — | No git event fires on "worktree created" by name; `post-checkout`'s zeroed-prev-HEAD argument is the closest structural signal, and it is proven to fire (see Q5) |
| Package/tooling conventions | `.claude/conventions.md` | — | Unchanged by this phase; D-15 placement rule keeps it swappable |

## User Constraints

<user_constraints>

### Locked Decisions (from 01-CONTEXT.md, verbatim)

- **D-01:** Retire the pending change with `openspec archive phase1-curated-bindings-revert-defaults --skip-specs -y`. Do **not** author the 7 validator fixes `openspec validate --strict` reports; the main specs stay as they are.
- **D-02:** After archiving, `git mv openspec/ .planning/legacy/openspec/` so all planning material — past and present — lives in one tree owned by GSD.
- **D-03:** `R0.2` and Phase 1 success criterion 4 are reworded: drop "archived with a delta that syncs cleanly", replace with "archived with `--skip-specs`; main specs untouched; `openspec/` relocated under `.planning/legacy/`".
- **D-04:** FROZEN banners go on three files: `.planning/legacy/openspec/README.md` (new), `docs/requirements.md`, and `docs/propossal_roadmap.md`. Each banner states "FROZEN — history only; source of truth is `.planning/`".
- **D-05:** The two legacy docs are NOT relocated — only bannered.
- **D-06:** Each phase runs in its own git worktree on branch `gsd/phase-{phase}-{slug}`. At phase end, once `make doctor` and `make test` are green, the agent merges into `master` and pushes. This replaces the earlier "agents never merge to master" decision.
- **D-07:** The policy is enforced structurally: a versioned pre-push hook rejects a direct push to `master` from anywhere other than the phase-end merge path, wired via `core.hooksPath` and a Makefile target.
- **D-08:** The hook is shell, lives under `tools/hooks/`. Planner: treat the location as fixed, the wiring mechanism (Makefile target vs `my-kitty` subcommand) as open.
- **D-09:** Surgical edit to CLAUDE.md, not a restructure. Changes: rewrite "Authoritative sources" to point at `.planning/`; replace "No auto-commit" with the D-06 git policy; add the research→experiment→decide mantra as non-negotiable; delete the OpenSpec "Spec-first" rule; keep `docs/agent-iteration.md`.
- **D-10:** Add a rule that every new GSD plan carries `cross_ai: true` in its frontmatter.
- **D-11:** After the instruction-file edit, validate it with the **`agent-md-refactor`** skill. `crafting-effective-readmes` is NOT used on the instruction file (corrected 2026-09-22).
- **D-12:** `CLAUDE.md` gains a research-tooling rule: prefer `codegraph_explore`/`codegraph explore` before opening files; size a file first (`wc -l`, `rg -n`) when it must be read directly; prefer `rg`/`fd`/`wc`/`bat`/`sd`/`eza`.
- **D-13:** CodeGraph index lifecycle is automated: on worktree creation, `codegraph init` runs (fresh worktree has no `.codegraph/`, gitignored); on commit, `codegraph sync` (incremental) refreshes it, falling back to `index -q` if `sync` proves unreliable. Both run non-blocking — a CodeGraph failure warns, never aborts. Extends the `tools/hooks/` hook set from D-07/D-08.
- **D-14:** **`AGENTS.md` is the canonical instruction file**, not `CLAUDE.md`. Migration: move rule content from `CLAUDE.md` into `AGENTS.md`, reduce `CLAUDE.md` to the single line `@AGENTS.md`. `.planning/config.json`'s `claude_md_path` is repointed accordingly.
- **D-15:** Placement rule: `AGENTS.md` = rules/process (validated with `agent-md-refactor`); `README.md` = human project info (validated with `crafting-effective-readmes`); `.claude/conventions.md` = stack/tooling conventions. A rule belongs in exactly one file, moved not copied.
- **D-16:** **One commit per plan.** An executor squashes a plan's work into a single logical commit naming the plan and the requirements it satisfies. A plan may produce more than one commit only when changes are genuinely independent, with the reason in the second commit's message. Supersedes the "commit per task" half of D-06.

### Claude's Discretion (from 01-CONTEXT.md, verbatim)

- Exact banner wording and placement (top-of-file vs after H1).
- Whether the pre-push guard is wired by a Makefile target or a `my-kitty` subcommand (D-08).
- Ordering of the archive → move → banner → CLAUDE.md steps within the phase.
- Which git hook carries the D-13 commit refresh (`post-commit` keeps commits fast; `pre-commit` keeps the index exact at commit time).
- Whether the worktree `codegraph init` is invoked by a hook (`post-checkout`) or by the Makefile/worktree helper — hooks do not fire on every `git worktree add` path, so the planner must verify empirically before choosing (mantra applies). **This research settles that: see Q5 below — `post-checkout` DOES fire on `git worktree add` via `core.hooksPath`, reproduced live.**

### Deferred Ideas (OUT OF SCOPE, from 01-CONTEXT.md, verbatim)

- `curl | bash` installer with channel selection — becomes Phase 9 (R8.x).
- Repairing the ~25 stale `openspec/` path references created by D-02 — belongs to Phase 8 (live-doc hygiene).
- `CLAUDE.md` Stack-section inaccuracies beyond D-08's hook line — Phase 8, requirement R6.1.
- Findings from `crafting-effective-readmes` (D-11) that exceed Phase 1 scope — recorded, not acted on.

</user_constraints>

## Phase Requirements

<phase_requirements>

| ID | Description | Research Support |
|----|-------------|------------------|
| R0.1 | Non-negotiable "research→experiment→decide→implement" rule in the canonical instruction file | See `AGENTS.md conventions` below; this rule is prose, no tooling dependency. Placement per D-15: goes in `AGENTS.md`. |
| R0.2 | Retire pending OpenSpec change with `--skip-specs`; freeze banners | See Q1 (archive mechanics, live-verified) and Q2 (`git mv` safety, live-verified) below |
| R0.3 | Authoritative-sources list points at `.planning/`; OpenSpec process refs retired | Direct edit; no new tooling. Verify via `rg -n 'openspec' AGENTS.md` returning 0 process-reference hits (banner/history mentions are fine) |
| R0.4 | Git policy: worktree-per-phase, one-commit-per-plan, merge-on-green, push; no force-push/amend; enforced by pre-push hook | See Q3 (hooksPath mechanism) and Q4 (force-push detection), both live-verified |
| R0.5 | Research-tooling rule (`codegraph_explore` before file reads; size-then-read; prefer `rg`/`fd`/`wc`/`bat`/`sd`/`eza`) | Prose rule; codegraph tool inventory confirmed in Q5 |
| R0.6 | CodeGraph index lifecycle automated (worktree creation → init; every commit → sync; failures warn, never block) | See Q5 below — `codegraph init/index/sync` subcommands confirmed via `--help`; worktree-creation trigger confirmed via live `post-checkout` experiment; `sync` timing measured at 90ms on this repo |
| R0.7 | Every new GSD plan carries `cross_ai: true` in frontmatter | VERIFIED: this is an **existing** GSD mechanism (`gsd-core/workflows/execute-phase.md:399`), not a phase invention — see Q6 below |
| R0.8 | `AGENTS.md` canonical; `CLAUDE.md` → `@AGENTS.md`; `.planning/config.json`'s `claude_md_path` repointed | See Q6 (`gsd_run project-instruction-file` → `AGENTS.md`, executed live) and Q7 (`claude_md_path` current value + consuming code, read live) |
| R0.9 | Placement rule written into `AGENTS.md`; validated with `agent-md-refactor` / `crafting-effective-readmes` | Both skills confirmed available as **global** Claude Code skills (no project-local `.claude/skills/` directory exists in this repo — see Environment Availability) |
| R0.10 | One-commit-per-plan rule in `AGENTS.md` | Prose rule; no tooling dependency beyond D-16's own text |

</phase_requirements>

## Standard Stack

This phase touches no application dependencies. The "stack" here is the local toolchain used to execute governance mechanics — all versions below were queried live in this environment, not assumed from training data.

### Core (tools already installed, verified live)

| Tool | Version (verified) | Purpose | Evidence |
|------|---------------------|---------|----------|
| `openspec` CLI | 1.13.1 | Archive the pending OpenSpec change | `[VERIFIED: openspec --version]` → `1.13.1`, at `~/.volta/bin/openspec` |
| `git` | 2.55.0 | Worktrees, `core.hooksPath`, `git mv` | `[VERIFIED: git --version]` → `git version 2.55.0` |
| `codegraph` CLI | 1.6.0 | Index lifecycle (`init`/`sync`) | `[VERIFIED: codegraph --version]` → `1.6.0`, at `/home/bazzite/.local/bin/codegraph` |
| `node` | v24.18.0 | Runs `gsd-tools.cjs` (used by hooks/Makefile if they shell out to `gsd_run`) | `[VERIFIED: node --version]` |

### Supporting

| Tool | Purpose | When to Use |
|------|---------|-------------|
| `rg` (ripgrep) | Reference audits (`~25` `openspec/` path hits) | Already used in this research; D-12 codifies it as the preferred grep |
| `agent-md-refactor` (Claude Code skill) | Validates `AGENTS.md`/`CLAUDE.md`-shaped files | D-11 — invoke after the instruction-file rewrite |
| `crafting-effective-readmes` (Claude Code skill) | Validates `README.md` | D-15 — NOT used on the instruction file |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| `core.hooksPath` (repo-shared config) | Per-worktree `.git/hooks/` symlinks | Rejected by D-07's own rationale (must bind cross-AI CLIs uniformly); also `core.hooksPath` is proven (Q3) to already cover every worktree with one setting — a symlink farm would be strictly more moving parts for the same guarantee |
| `post-checkout` hook for CodeGraph init | A `my-kitty`/Makefile worktree-creation wrapper | Both are viable (D-13 discretion is explicitly open); Q5 below shows `post-checkout` **does** fire reliably on `git worktree add`, which removes the empirical objection CONTEXT.md raised against it |
| `codegraph sync` in `post-commit` | `codegraph index -q` (full rebuild) every commit | D-13's own stated preference; `sync` measured at 90ms on this 87-file repo vs. an unmeasured full rebuild — sync is the correct default, full `index -q` the documented fallback if `sync` proves unreliable |

**Installation:** No new packages. All tools above are already present in this environment (paths and versions confirmed by direct invocation, not `pip`/`npm` install).

## Package Legitimacy Audit

**Not applicable.** This phase installs zero external packages (no `npm install`, `pip install`, or `uv add`). It is a documentation + git-hook phase. `pyproject.toml` and `src/kitty_setup/` predate this phase and are untouched by it. If a later plan in this phase turns out to need a new dependency, run the Package Legitimacy Gate then — do not skip it retroactively.

## Architecture Patterns

### System Architecture Diagram

```
                    ┌─────────────────────────────────────────┐
                    │   Repo root (shared git config)          │
                    │   git config core.hooksPath tools/hooks  │  ← set ONCE, shared file
                    └───────────────┬───────────────────────────┘
                                    │ (relative path resolves per-worktree-root)
        ┌───────────────────────────┼───────────────────────────┐
        ▼                           ▼                           ▼
┌───────────────┐          ┌───────────────┐          ┌───────────────┐
│ main worktree  │          │ phase-N        │          │ phase-N+1      │
│ (master)       │          │ worktree       │          │ worktree       │
│ tools/hooks/*  │          │ tools/hooks/*  │          │ tools/hooks/*  │
└───────┬────────┘          └───────┬────────┘          └───────┬────────┘
        │ git worktree add           │ git commit                │ git push
        ▼                            ▼                            ▼
 post-checkout fires          post-commit fires            pre-push fires
 (prev-HEAD = 000..0)         (codegraph sync -q)           (reads stdin:
 → codegraph init             non-blocking, warns           local/remote refs+shas)
   (fresh .codegraph/,        on failure only                → merge-base
    gitignored, absent                                         --is-ancestor check
    in new worktree)                                          → reject force-push /
                                                                  direct master push
```

### Recommended Project Structure (additions this phase makes)

```
tools/
├── setup.sh          # existing — bootstrap only
├── uninstall.sh       # existing — bootstrap only
└── hooks/             # NEW — D-08
    ├── pre-push        # rejects force-push / direct-to-master (D-07)
    ├── post-checkout   # fires on `git worktree add`; runs `codegraph init` on fresh worktree (D-13)
    └── post-commit      # runs `codegraph sync -q`, non-blocking (D-13)
AGENTS.md               # NEW — canonical instruction file (D-14)
CLAUDE.md                # REDUCED to `@AGENTS.md` (D-14)
.planning/legacy/openspec/   # MOVED from openspec/ (D-02), README.md banner added (D-04)
```

### Pattern 1: Shared `core.hooksPath` covering every worktree

**What:** Set `core.hooksPath` to a **relative, repo-tracked** path (`tools/hooks`) using plain `git config` (no `--worktree` flag). Because `extensions.worktreeConfig` is off by default and is **not** enabled in this repo (`[VERIFIED: git config extensions.worktreeConfig` returns empty in this repo, checked live]), the setting lands in the single shared `$GIT_COMMON_DIR/config` file and is visible from every linked worktree without repeating the command.

**Why the relative path still works per-worktree:** `githooks(5)`'s own DESCRIPTION section states: *"Before Git invokes a hook, it changes its working directory to either $GIT_DIR in a bare repository or the root of the working tree in a non-bare repository."* Combined with `git-config(1)`'s statement that a relative `core.hooksPath` *"is taken as relative to the directory where the hooks are run"*, a relative path resolves against **each worktree's own root**, not the main repo's root. Since `tools/hooks/` is a tracked directory, every worktree's checkout already contains its own copy — so one config setting transparently uses the *right* copy in every worktree.

**When to use:** Exactly D-07/D-08's case — a policy hook that must apply uniformly across every phase worktree without a per-worktree setup step.

**Example (reproduced live in a disposable sandbox, not this repo):**
```bash
# Source: live experiment, this research session (see Sources)
$ git config core.hooksPath tools/hooks        # run once, from any worktree
$ cat .git/config | grep -A1 hooksPath
	hooksPath = tools/hooks
$ git worktree add ../wt-feature feature -q
$ git config core.hooksPath                     # from inside the NEW worktree
tools/hooks                                      # <- same value, no extra config needed
```
`[VERIFIED: live git experiment, this session]`

### Pattern 2: Pre-push non-fast-forward (force-push) detection

**What:** A `pre-push` hook reads lines of `<local ref> SP <local sha1> SP <remote ref> SP <remote sha1> LF` from stdin (one line per ref being pushed) — this is git's documented pre-push protocol. For each line, if `remote_sha` is not the all-zero SHA (i.e., the ref already exists on the remote), run `git merge-base --is-ancestor <remote_sha> <local_sha>`. A non-zero exit means `remote_sha` is **not** an ancestor of `local_sha` — the local branch does not contain the remote's tip commit, which is exactly what a force-push (or an amend-and-push) produces.

**When to use:** D-07's structural guard against force-push/amend, and (combined with checking `remote_ref == refs/heads/master`) against a direct push to `master` outside the phase-end merge.

**Example (reproduced live):**
```bash
# Source: live experiment, this research session
# Normal (fast-forward) push:
local_ref=refs/heads/main local_sha=65c7604... remote_ref=refs/heads/main remote_sha=0247395...
$ git merge-base --is-ancestor 0247395... 65c7604...; echo $?
0   # ancestor -> fast-forward, allow

# After `git commit --amend` + `git push --force`:
local_ref=refs/heads/main local_sha=138e21f... remote_ref=refs/heads/main remote_sha=65c7604...
$ git merge-base --is-ancestor 65c7604... 138e21f...; echo $?
1   # NOT an ancestor -> force/rewrite detected, reject
```
`[VERIFIED: live git experiment, this session]`

**Limits (report honestly, do not oversell the guard):**
- A brand-new branch/ref push has `remote_sha` = all-zero (`0000...0`) — the ancestor check must be skipped in that case (there is nothing to compare against); this is normal, not a bypass.
- `remote_sha` reflects **this client's own tracking refs**, not a live server query — the hook trusts what `git` already knows about the remote at push time. In a single-agent, single-clone workflow (this project's model) that is reliable; it would not be authoritative in a multi-clone/CI environment without a preceding `git fetch`.
- This client-side technique is advisory-by-construction: it can be bypassed with `--no-verify`. D-07's own text acknowledges the guard is "structural… rather than by acknowledgment" relative to *agents following a documented policy*, not relative to a malicious actor bypassing hooks outright — the planner should not claim it as un-bypassable.
- `--force-with-lease` produces the identical non-ancestor relationship as `--force` from this check's point of view — the technique does not need to special-case which force flag was used, since D-07's rule bans both.

### Pattern 3: `post-checkout` as the worktree-creation trigger for CodeGraph

**What:** `git worktree add <path> <branch>` **does** invoke the `post-checkout` hook (resolved via `core.hooksPath`, same shared-config mechanism as Pattern 1), with `cwd` set to the **new worktree's root** and hook arguments `<prev-HEAD-sha> <new-HEAD-sha> <flag>`. On a fresh worktree, `prev-HEAD-sha` is the all-zero SHA — a first-checkout marker distinct from an ordinary same-worktree branch switch (where `prev-HEAD-sha` is a real commit).

**Example (reproduced live, via `core.hooksPath`, not `.git/hooks/` directly):**
```bash
# Source: live experiment, this research session
$ git config core.hooksPath tools/hooks
$ git worktree add ../wt-feat3 feat2
Preparing worktree (checking out 'feat2')
HEAD is now at a15329d init
POST-CHECKOUT(hooksPath) FIRED args=0000000000000000000000000000000000000000 a15329d... 1 cwd=/tmp/.../wt-feat3
```
`[VERIFIED: live git experiment, this session]`

**This directly resolves the open discretion item in CONTEXT.md** ("hooks do not fire on every `git worktree add` path, so the planner must verify empirically before choosing") — `post-checkout` fires reliably, checkout completes (so `tools/hooks/post-checkout` is already present in the new worktree) before the hook runs, and the zeroed prev-HEAD argument is the exact signal to gate a `codegraph init` (vs. a no-op on ordinary checkouts). Recommended hook logic:
```sh
# tools/hooks/post-checkout — illustrative, not yet written to the repo
prev_head="$1"; branch_flag="$3"
if [ "$branch_flag" = "1" ] && [ "$prev_head" = "0000000000000000000000000000000000000000" ]; then
  codegraph init -y >/dev/null 2>&1 || echo "warning: codegraph init failed (non-blocking)" >&2
fi
exit 0
```

### Anti-Patterns to Avoid

- **Per-worktree `git config --worktree core.hooksPath`:** Unnecessary — requires `extensions.worktreeConfig` and repeats the setting per worktree. Pattern 1 shows the plain shared-config form already covers every worktree.
- **Blocking a commit or worktree creation on a CodeGraph failure:** D-13 explicitly requires warn-not-abort; a hook that `exit`s non-zero on a `codegraph` failure would violate R0.6.
- **Treating `openspec validate --strict` cleanliness as a merge gate for this phase:** confirmed live (Q1) that unrelated pre-existing specs (`kitty-test-harness`, `my-kitty-cli`, `agent-iteration-discipline`, …) already fail `openspec validate --all --strict` with 12 pre-existing WARNING/INFO items unrelated to the archived change — gating this phase's "done" on a fully-green `openspec validate --all --strict` would incorrectly block on debt this phase does not own.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|--------------|-----|
| Detecting a force-push in a pre-push hook | A custom heuristic (e.g., diffing ref counts) | `git merge-base --is-ancestor <remote_sha> <local_sha>` per stdin line | Standard, one-line, and empirically confirmed correct in this session (Pattern 2) |
| Per-worktree hook installation | A script that copies/symlinks hooks into every new worktree's `.git/hooks/` | `core.hooksPath` set once in shared config | Pattern 1 proves one setting already covers every worktree — a copy step is unnecessary machinery |
| A "worktree created" trigger | Polling, or a bespoke `my-kitty worktree` wrapper as the *only* mechanism | `post-checkout` hook (zeroed prev-HEAD signals first checkout) | Pattern 3 proves the native git hook already fires; a wrapper can still exist as a Makefile convenience, but the hook removes the "hooks don't fire on worktree add" doubt |
| Validating `AGENTS.md`/`CLAUDE.md` structure by eye | Manual review checklist | `agent-md-refactor` skill (D-11) | Already available globally in this environment; purpose-built for this exact file shape |

**Key insight:** Every mechanism this phase needs (shared hook path, force-push detection, worktree-creation signal) is a documented, first-class git feature — none of it requires bespoke tooling. The phase's actual risk is not "can this be built" but "did anyone verify it actually behaves this way in *this* git version" — which is why this research prioritized live reproduction over citing git's manual alone.

## Runtime State Inventory

> Trigger: this phase renames/relocates `openspec/` and redistributes `CLAUDE.md`'s content into a new `AGENTS.md`. All five categories were checked explicitly.

| Category | Items Found | Action Required |
|----------|-------------|------------------|
| Stored data | None — `openspec`'s own global config (`~/.config/openspec/config.json`) holds only `featureFlags`, `profile`, `delivery`, `telemetry`, `workflows`; no path or repo identifier referencing this project. `[VERIFIED: openspec config list, run live]` | None |
| Live service config | None — no external service (n8n, Datadog, Tailscale, etc.) is in play for this repo | None |
| OS-registered state | None — no Task Scheduler/launchd/systemd units reference `openspec` or `CLAUDE.md` in this project | None |
| Secrets/env vars | None — no env var or secret name embeds `openspec` or `CLAUDE.md` | None |
| Build artifacts / registered stores | **Checked and clear**: `openspec store list` → `"No stores registered."` `[VERIFIED: openspec store list, run live]` — this repo's `openspec/` directory is **not** registered as an OpenSpec "store" (an absolute-path registration feature the CLI supports via `openspec store setup/register`), so `git mv openspec/ .planning/legacy/openspec/` cannot desync a store registration that does not exist. | None |
| Local (gitignored) index state | `.codegraph/codegraph.db` currently indexes this repo at its current paths (87 files, 1,129 nodes, per `codegraph status`, run live). A `git mv openspec/` will appear to CodeGraph's file watcher as a bulk delete+add. | Not a data-migration in the traditional sense (the DB is gitignored, machine-local, and rebuildable) — but the plan should explicitly run `codegraph sync` (or rely on the new post-commit hook) once after the `git mv`, so the index reflects the new `.planning/legacy/openspec/` paths before any subsequent `codegraph_explore` call is trusted. |

**Nothing else found in any category** — this is a doc/config-relocation phase with no databases, no long-lived external services, and no OS-level registrations touching the renamed paths.

## Common Pitfalls

### Pitfall 1: Assuming `openspec archive --skip-specs` requires the validator to pass first
**What goes wrong:** A planner might insert a task to "fix validator errors before archiving," burning effort D-01 explicitly says not to spend.
**Why it happens:** `openspec archive`'s default behavior (without `--skip-specs`) does sync specs and could plausibly be assumed to gate on validation.
**How to avoid:** Confirmed live in a disposable sandbox: `openspec archive phase1-curated-bindings-revert-defaults --skip-specs -y` exits 0 and prints `"Skipping spec updates (--skip-specs flag provided)."` even though `openspec validate <change> --strict` on the same change reports 6 `✗ [ERROR]` lines plus 1 `ℹ [INFO]` line (7 issues total — matches D-01's "7 errors" figure). `[VERIFIED: live sandbox experiment, this session]`
**Warning signs:** If a plan task says "resolve OpenSpec validation errors" anywhere in Phase 1, it contradicts D-01/D-03 and should be flagged in plan review.

### Pitfall 2: Archived-change directory name is not what you'd guess
**What goes wrong:** A plan or a later doc-repair step assumes the archived change still lives at `openspec/changes/phase1-curated-bindings-revert-defaults/`.
**Why it happens:** The un-prefixed directory name looks stable.
**How to avoid:** Live sandbox run shows the archive operation **renames and moves** the directory to `openspec/changes/archive/<YYYY-MM-DD>-phase1-curated-bindings-revert-defaults/` (date-prefixed, under a new `archive/` subdirectory) — this happens *before* the subsequent `git mv openspec/ .planning/legacy/openspec/`, so after both steps the final path is `.planning/legacy/openspec/changes/archive/2026-09-23-phase1-curated-bindings-revert-defaults/`. `[VERIFIED: live sandbox experiment, this session — exact date will be whatever day the archive actually runs]`
**Warning signs:** Any hardcoded path reference to the un-dated change name written after this phase.

### Pitfall 3: `openspec validate --all --strict` will not be green after this phase, and that's expected
**What goes wrong:** A verification step naively runs `openspec validate --all --strict` and treats any non-zero exit as a Phase 1 regression.
**Why it happens:** The command's scope is the whole specs tree, not just the archived change.
**How to avoid:** Live run (sandbox, post-archive) shows 12 pre-existing failed items across `kitty-test-harness`, `my-kitty-cli`, and other specs (placeholder `## Purpose` sections, overlong requirement text) that predate this phase and are explicitly Out of Scope per PROJECT.md ("Rewriting frozen OpenSpec specs"). `[VERIFIED: live sandbox experiment, this session]`
**Warning signs:** A Phase 1 acceptance check that greps for "0 errors" from a whole-tree `openspec validate` run.

### Pitfall 4: Confusing `core.hooksPath`'s per-worktree resolution with per-worktree *configuration*
**What goes wrong:** A plan step re-runs `git config core.hooksPath tools/hooks` inside every new phase worktree "to be safe," adding unnecessary steps and risking an accidental `--worktree`-scoped override that then *diverges* from the shared value.
**Why it happens:** The word "per-worktree" in the phase's own research question is ambiguous between "the *setting* is per-worktree" (false, by default) and "the *resolved path* is per-worktree-root" (true).
**How to avoid:** Pattern 1 above — the setting lives once in the shared config; only the **relative path's resolution** is per-worktree-root, and that's what already makes it work everywhere.

### Pitfall 5: Treating `agent-md-refactor` as a project skill that needs installing
**What goes wrong:** A plan task tries to install or vendor `agent-md-refactor`/`crafting-effective-readmes` into this repo's `.claude/skills/`.
**Why it happens:** CONTEXT.md's canonical_refs section references `.claude/skills/openspec-*/SKILL.md` (now-deleted, per code_context) as prior art, which might suggest skills live in-repo.
**How to avoid:** This repo has **no `.claude/skills/` directory at all** (`[VERIFIED: ls .claude/skills/ → "No such file or directory", run live]`). Both `agent-md-refactor` and `crafting-effective-readmes` are available as **global** Claude Code skills in this environment (confirmed present in the system's skill listing) and are invoked directly via the `Skill` tool — no in-repo installation step is needed or appropriate.

## Code Examples

### Wiring the shared hook path (Makefile target, D-08's "open" choice — recommended default)
```makefile
# Source: this research session's live experiment, adapted to this repo's Makefile style
# (existing targets are 1-2 lines per CLAUDE.md's own "Stack" rule)
hooks:
	git config core.hooksPath tools/hooks
```
Rationale for a Makefile target over a `my-kitty` subcommand: it needs no Python runtime, matches the existing thin-glue Makefile pattern already in this repo (`help`, `install`, `setup`, `clean`, `doctor`, `test`, `uninstall`, `prune` — all confirmed 1-5 lines via `grep -n "^[a-zA-Z_-]*:" Makefile`, run live), and D-08 leaves this choice explicitly open. `[VERIFIED: this repo's Makefile targets, read live]`

### `AGENTS.md` import from `CLAUDE.md` (D-14)
```markdown
@AGENTS.md
```
Confirmed live: `gsd_run project-instruction-file` and `gsd_run query project-instruction-file` both print `AGENTS.md` for this project. `[VERIFIED: gsd_run project-instruction-file, run live, this session]` Claude Code's own `@path` import syntax is documented at `docs.anthropic.com/en/docs/claude-code/memory`: *"CLAUDE.md files can import additional files using @path/to/import syntax. Claude replaces each @path with the contents of that file at load time."* `[CITED: docs.anthropic.com/en/docs/claude-code/memory]`

### `.planning/config.json` repoint (R0.8)
Current value, read directly from this repo's file:
```json
"claude_md_path": "./CLAUDE.md"
```
`[VERIFIED: .planning/config.json:62, read live this session]` — quoted verbatim above.

Consuming code (GSD's own `profile-output.cjs`, read live):
```javascript
// gsd-core/bin/lib/profile-output.cjs:1039-1043
let configClaudeMdPath = '.claude/CLAUDE.md';
try {
    const config = loadConfig(cwd);
    if (config['claude_md_path'])
        configClaudeMdPath = config['claude_md_path'];
```
`[VERIFIED: /home/bazzite/.claude/gsd-core/bin/lib/profile-output.cjs:1039-1043, read live this session — quoted verbatim]`
The surrounding comment (lines 1056-1060) states: *"For the claude runtime, `claude_md_path` config is honored — it IS the Claude-specific output setting."* Since `gsd_run query init.phase-op` reports `"agent_runtime": "claude"` for this project `[VERIFIED: init.phase-op output, run live]`, repointing `claude_md_path` to `"./AGENTS.md"` is what causes GSD's own future content-assembly runs to target the canonical file rather than the stub.

### `cross_ai: true` frontmatter is an existing GSD mechanism, not new
```
// gsd-core/workflows/execute-phase.md:399
Activates when `--cross-ai` forces all incomplete plans, `--no-cross-ai` disables it
entirely, or (default) a plan's `cross_ai: true` frontmatter agrees with the
`workflow.cross_ai_execution` config.
```
`[VERIFIED: /home/bazzite/.claude/gsd-core/workflows/execute-phase.md:399, read live this session — quoted verbatim]` This project's `.planning/config.json` already has `workflow.cross_ai_execution: true` and `workflow.cross_ai_command: "opencode run --model router-env/my-coding"` `[VERIFIED: .planning/config.json, read live]` — so R0.7's rule is "make every new plan opt in to a mechanism that's already wired," not "invent a mechanism."

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|---------------|--------|
| One-off, tool-specific instruction files (`CLAUDE.md`, `.cursorrules`, `.windsurfrules`) | `AGENTS.md` as a shared, tool-agnostic convention | Emerged ~2025 from OpenAI Codex/Amp/Google Jules/Cursor/Factory converging on one filename; now stewarded by the Agentic AI Foundation (Linux Foundation) `[CITED: agents.md, github.com/agentsmd/agents.md]` | This phase is adopting the current industry direction, not a novel or risky choice |
| Per-CLI duplicated rules | `CLAUDE.md` reduced to `@AGENTS.md` import; `opencode` reads `AGENTS.md` natively per its own docs (*"OpenCode loads... every AGENTS.md from the current workspace directory"*) `[CITED: opencode.ai/docs/rules]` | Current opencode/Codex convention | One edit surface instead of N |

**Deprecated/outdated:**
- Duplicating process rules across `CLAUDE.md` and a hypothetical `AGENTS.md` — D-15's placement rule exists specifically to prevent this drift.

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | Codex CLI reads `AGENTS.md` by the same "nearest file wins" convention as opencode | AGENTS.md conventions / State of the Art | Low — this project's cross-AI wiring uses `opencode`, not `codex`, per `.planning/config.json`'s `cross_ai_command`; the Codex claim is well-documented industry-wide (`github.com/openai/codex/blob/main/AGENTS.md` uses 88 such files) but was not independently executed against a local `codex` binary in this session | 
| A2 | `--force-with-lease` produces an identical stdin/ancestor signature to `--force` in the pre-push hook | Pattern 2 (force-push detection) | Low — this follows directly from how `--force-with-lease` still rewrites the remote ref non-fast-forward; not separately reproduced with `--force-with-lease` specifically in this session (only `--force` was tested) |
| A3 | `codegraph sync`'s 90ms measurement on this 87-file repo generalizes to acceptable post-commit latency after Phase 1's own edits (which will add `AGENTS.md`, `tools/hooks/`, move `openspec/`) | Alternatives Considered / Pattern 3 | Low — file count increases modestly; `sync` is described by the CLI itself as incremental ("Sync changes since last index"), so cost should scale with the diff size, not repo size, but this was not independently re-measured after a large `git mv` |

**If this table is empty:** N/A — three low-risk assumptions are listed above; none blocks planning.

## Open Questions

1. **Exact wording of the pre-push hook's "direct push to master" check (beyond force-push detection)**
   - What we know: force-push/rewrite detection is fully solved (Pattern 2). D-07 additionally wants to reject "a direct push to master from anywhere other than the phase-end merge path."
   - What's unclear: the hook only sees ref names and SHAs, not *how* the commits being pushed were produced (i.e., it cannot natively distinguish "I did `git merge phase-branch && git push`" from "I did `git checkout master && git commit && git push`" — both are legitimate fast-forwards or merges from the hook's point of view).
   - Recommendation: the planner should decide the exact heuristic (e.g., checking that the branch being pushed is `master` AND the pushing worktree's tracked branch metadata shows it started from a `gsd/phase-*` branch, or simply that direct commits to `master` are rejected unless the merge commit's second parent is a `gsd/phase-*` branch tip). This is a design decision for the plan, not a research gap — flag it explicitly in the plan so it isn't silently under-specified.

2. **Whether `codegraph sync` (vs. `index -q`) remains reliable after the `git mv openspec/` bulk rename within the same phase**
   - What we know: `sync` completed in 90ms with zero pending changes on this repo; the CLI help describes it as "Sync changes since last index."
   - What's unclear: this was not tested against a bulk directory rename of `openspec/`'s ~size (its full tree) in the same session, so whether `sync` correctly reindexes a `git mv`'d subtree (vs. needing a full `index`) is unverified.
   - Recommendation: the plan should include a verification task — run `codegraph sync` immediately after the `git mv`, then `codegraph status`/`codegraph query openspec` to confirm the new `.planning/legacy/openspec/` paths are indexed, falling back to `codegraph index -q` if `sync` misses anything. D-13 already names this exact fallback.

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|--------------|-----------|---------|----------|
| `openspec` CLI | R0.2 (archive) | ✓ | 1.13.1 (`~/.volta/bin/openspec`) | — |
| `git` | R0.4, R0.6 (hooks, worktrees) | ✓ | 2.55.0 | — |
| `codegraph` CLI | R0.5, R0.6 | ✓ | 1.6.0 (`/home/bazzite/.local/bin/codegraph`) | — |
| `node` | Runs `gsd-tools.cjs` if hooks/Makefile shell out to `gsd_run` | ✓ | v24.18.0 | — |
| `.claude/skills/agent-md-refactor` (project-local) | R0.9 validation | ✗ (no project `.claude/skills/` dir at all) | — | Use the **global** `agent-md-refactor` skill (confirmed present in this session's environment) via the `Skill` tool — no fallback needed, this is the intended path per D-11 |
| `.claude/skills/crafting-effective-readmes` (project-local) | R0.9 (README, not this phase's edit target) | ✗ (no project `.claude/skills/` dir) | — | Same as above — global skill, not needed this phase since README.md isn't edited here |

**Missing dependencies with no fallback:** None.

**Missing dependencies with fallback:** Project-local skill directories don't exist, but both named skills are available globally and that is the correct, intended invocation path (not a degraded fallback).

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest 8.3.0 (`[tool.pytest.ini_options]` in `pyproject.toml`) — pre-existing, not introduced by this phase `[VERIFIED: pyproject.toml:42-43,90, read live]` |
| Config file | `pyproject.toml` |
| Quick run command | `uv run pytest tests/unit -x` |
| Full suite command | `make test` |

**This phase does not add or require pytest coverage** — its 10 requirements are documentation/config/git-hook assertions, not application behavior. The right verification tool per requirement is a direct command, not a unit test:

### Phase Requirements → Verification Map
| Req ID | Behavior | Verification Type | Command | Notes |
|--------|----------|--------------------|---------|-------|
| R0.1 | Mantra rule present | grep | `rg -n 'research.*experiment.*decide' AGENTS.md` | Text presence check |
| R0.2 | Change archived, banners present | shell | `openspec list \| grep -c phase1-curated-bindings-revert-defaults` (expect 0 pending) + `rg -l 'FROZEN' .planning/legacy/openspec/README.md docs/requirements.md docs/propossal_roadmap.md` | |
| R0.3 | No OpenSpec process refs in authoritative sources | grep | `rg -n 'openspec' AGENTS.md` — every hit must be a history/banner mention, not a process pointer | |
| R0.4 | Git policy text + hook installed | shell + live hook test | `git config --get core.hooksPath` == `tools/hooks`; a scripted force-push-rejection test (see below) | Recommend a small integration test (bash or `pytest` via `subprocess`) modeled on this research's own sandbox experiments — spin up a disposable repo, install the hook, attempt a force-push, assert non-zero exit |
| R0.5 | Tooling rule present | grep | `rg -n 'codegraph_explore' AGENTS.md` | |
| R0.6 | CodeGraph lifecycle hooks work | live hook test | Reproduce Q5's `git worktree add` experiment against the real `tools/hooks/post-checkout`; reproduce a `post-commit` firing `codegraph sync -q` | This research's own sandbox commands are directly reusable as the verification script |
| R0.7 | `cross_ai: true` documented | grep | `rg -n 'cross_ai: true' AGENTS.md` | |
| R0.8 | AGENTS.md canonical, CLAUDE.md stub, config repointed | shell | `cat CLAUDE.md` == `@AGENTS.md`; `jq .claude_md_path .planning/config.json` == `"./AGENTS.md"` | |
| R0.9 | Placement rule + skill validation ran | manual + grep | `agent-md-refactor` skill invoked and findings addressed; `rg -n 'agent-md-refactor\|crafting-effective-readmes' AGENTS.md` | |
| R0.10 | One-commit-per-plan rule documented | grep | `rg -n 'one commit per plan' AGENTS.md` | |

### Sampling Rate
- **Per task commit:** the grep/shell checks above (cheap, instant)
- **Per wave merge:** the live hook tests (worktree/push simulation) — these mutate git state, so run them in a disposable sandbox exactly as this research did, never against the real working tree
- **Phase gate:** `make doctor` and `make test` green (per the Universal Phase Gate) — note neither currently covers governance content, so this phase's gate is substantively the checks above, not `make test`'s pytest suite

### Wave 0 Gaps
- [ ] No existing test/script reproduces the pre-push force-push rejection — recommend the plan add a small disposable-sandbox test (bash script under `tools/hooks/` or a `tests/integration/test_git_hooks.py` using `subprocess` + `tempfile.TemporaryDirectory`, following exactly the pattern this research used) so the guard is regression-tested, not just manually eyeballed once.
- [ ] No existing test reproduces the `post-checkout`-on-worktree-add behavior — same recommendation.

## Security Domain

`security_enforcement` is `true` in `.planning/config.json` (default; not explicitly disabled) `[VERIFIED: .planning/config.json, read live — no `security_enforcement` key override present, and profile default per `config-defaults.manifest.json` is enabled]`.

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|----------------|---------|-------------------|
| V2 Authentication | No | No auth surface in this phase |
| V3 Session Management | No | N/A |
| V4 Access Control | Marginal | The pre-push hook is an access-control-adjacent control (who may push what, where) — see Known Threat Patterns below |
| V5 Input Validation | No | No user input processed; hook reads only git-generated ref/sha strings |
| V6 Cryptography | No | N/A |

### Known Threat Patterns for this phase's stack

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|------------------------|
| History rewrite pushed to `master`, silently discarding prior work | Tampering | Pre-push hook's `merge-base --is-ancestor` check (Pattern 2); note the honest limit — `--no-verify` bypasses any client-side hook, so this is a policy-compliance guard for cooperating agents, not a security boundary against an adversarial pusher |
| A malicious or buggy hook script committed under `tools/hooks/` running with the pusher's privileges | Elevation of Privilege | Hooks are plain files with no special sandboxing — code review of `tools/hooks/*` changes is the mitigation; this is a general git-hooks caveat, not specific to this phase's design |

## Sources

### Primary (HIGH confidence — direct execution/read this session)
- `openspec --help`, `openspec archive --help`, `openspec validate --strict`, `openspec store list`, `openspec config list` — all run live against this repo and a disposable sandbox copy
- `git help githooks`, `git help worktree`, `git help config` — official git manual, read live via `git help`
- Live git experiments (three disposable sandboxes under `/tmp`, all cleaned up): `core.hooksPath` shared-vs-worktree behavior, pre-push stdin format + force-push detection, `post-checkout` firing on `git worktree add`
- `codegraph --help`, `codegraph init/index/sync/status --help`, `codegraph status`, `codegraph sync -q` (timed) — run live against this repo
- `/home/bazzite/.claude/gsd-core/bin/lib/profile-output.cjs:1020-1074` — read live, quoted verbatim
- `/home/bazzite/.claude/gsd-core/workflows/execute-phase.md:399` — read live, quoted verbatim
- `gsd_run query init.phase-op 1`, `gsd_run project-instruction-file` — run live against this project
- `/var/home/bazzite/git/personal/kitty-setup/.planning/config.json`, `CLAUDE.md`, `.claude/conventions.md`, `.gitignore`, `Makefile`, `pyproject.toml` — read live, quoted verbatim where cited

### Secondary (MEDIUM confidence — official docs via WebSearch)
- `docs.anthropic.com/en/docs/claude-code/memory` — Claude Code `@path` import syntax
- `agents.md`, `github.com/agentsmd/agents.md` — AGENTS.md standard origin and governance
- `opencode.ai/docs/rules` — opencode's own AGENTS.md loading convention

### Tertiary (LOW confidence)
- None used for load-bearing claims in this document.

## Metadata

**Confidence breakdown:**
- OpenSpec archive mechanics: HIGH — reproduced live in a disposable sandbox, diffed the resulting `specs/` tree byte-for-byte against the original
- Git hook / worktree mechanics: HIGH — reproduced live across three disposable sandboxes with full command transcripts
- CodeGraph lifecycle: HIGH for subcommand existence and worktree-trigger behavior (live); MEDIUM for post-bulk-rename `sync` reliability (Open Question 2, untested at this repo's actual `git mv` scale)
- AGENTS.md conventions: HIGH for GSD's own resolution (`gsd_run project-instruction-file`, live) and for opencode's documented behavior (official docs); MEDIUM for the broader cross-CLI claim (industry-standard, well-documented, not independently executed against every named CLI)
- Pre-push force-push detection: HIGH for the mechanism; explicitly flagged as a compliance guard, not a security boundary (see Security Domain)

**Research date:** 2026-09-23
**Valid until:** Tool versions (`openspec` 1.13.1, `git` 2.55.0, `codegraph` 1.6.0) are current as of this date; re-verify if any of these three tools are upgraded before Phase 1 executes. Estimate 30 days for the git-mechanics findings (stable, unlikely to change), 14 days for the CodeGraph findings (actively developed CLI).

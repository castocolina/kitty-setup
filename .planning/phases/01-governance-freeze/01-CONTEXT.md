# Phase 1: Governance & Freeze - Context

**Gathered:** 2026-09-22
**Status:** Ready for planning

<domain>
## Phase Boundary

An agent opening this repo finds exactly one authoritative source of intent (`.planning/`) and
one set of non-negotiable process rules in `CLAUDE.md`, with the whole OpenSpec tree relocated
under `.planning/legacy/` and labelled as history. No source, config, or test file behaviour
changes in this phase — it writes `AGENTS.md` (canonical) with `CLAUDE.md` reduced to an
`@AGENTS.md` import, moves `openspec/`, adds banners, and installs one git guard.

</domain>

<decisions>
## Implementation Decisions

### Archive & freeze mechanics
- **D-01:** Retire the pending change with `openspec archive phase1-curated-bindings-revert-defaults --skip-specs -y`. Do **not** author the 7 validator fixes `openspec validate --strict` reports; the main specs stay as they are. Rationale: PROJECT.md already lists "rewriting frozen OpenSpec specs" as out of scope, so paying to make history-only specs self-consistent contradicts that decision. — **Reversibility:** reversible — the archive is a directory move under git.
- **D-02:** After archiving, `git mv openspec/ .planning/legacy/openspec/` so all planning material — past and present — lives in one tree owned by GSD. The `openspec` CLI then has no root in this repo, which is the intended end state. — **Reversibility:** costly — ~25 inbound path references in `.conf` comments, src docstrings, and repro docs break; Phase 8 (live-doc hygiene) repairs them and MUST be told they are now stale.
- **D-03:** `R0.2` and Phase 1 success criterion 4 are reworded: drop "archived with a delta that syncs cleanly" (the delta does not and will not sync), replace with "archived with `--skip-specs`; main specs untouched; `openspec/` relocated under `.planning/legacy/`".
- **D-04:** FROZEN banners go on three files: `.planning/legacy/openspec/README.md` (new), `docs/requirements.md`, and `docs/propossal_roadmap.md`. Each banner states "FROZEN — history only; source of truth is `.planning/`". Rationale: both docs are still cited as authoritative by `CLAUDE.md` today and are superseded by `.planning/REQUIREMENTS.md` / `ROADMAP.md`.
- **D-05:** The two legacy docs are NOT relocated — only bannered. Moving them would break the same reference set as D-02 for no extra signal.

### Git model (supersedes the PROJECT.md "never merge to master" decision)
- **D-06:** Each phase runs in its own git worktree on branch `gsd/phase-{phase}-{slug}` (`git.branching_strategy: phase`, `workflow.use_worktrees: true`). At phase end, once `make doctor` and `make test` are green, the agent merges into `master` and pushes. This **replaces** the earlier locked decision that agents never merge to `master`; PROJECT.md's Key Decisions table and ROADMAP.md's Universal Phase Gate step 6 must both be updated in this phase. — **Reversibility:** reversible — policy text plus config.
- **D-07:** The policy is enforced structurally, not only documented: a versioned pre-push hook rejects a direct push to `master` from anywhere other than the phase-end merge path, wired via `core.hooksPath` and a Makefile target. Rationale: cross-AI execution is now enabled, so a guard living in one assistant's settings would not bind the other CLIs. — **Reversibility:** reversible.
- **D-08:** The hook is shell, which the "Bash only inside `tools/`" stack rule constrains. It lives under `tools/hooks/` so the rule holds without amendment, and `CLAUDE.md`'s Stack section is updated to name it. Planner: treat the location as fixed, the wiring mechanism (Makefile target vs `my-kitty` subcommand) as open.

### CLAUDE.md content
- **D-09:** Surgical edit, not a restructure. The file is 62 lines and well organised; `agent-md-refactor` would collide with Phase 8's edits to the same file. Changes: rewrite "Authoritative sources" to point at `.planning/`; replace "No auto-commit" with the D-06 git policy; add the research→experiment→decide mantra as a non-negotiable rule; delete the OpenSpec "Spec-first" rule; keep `docs/agent-iteration.md` as the hypothesis playbook.
- **D-10:** Add a rule that every new GSD plan carries `cross_ai: true` in its frontmatter, so cross-AI execution is the default rather than opt-in per plan.
- **D-11:** After the instruction-file edit, validate it with the **`agent-md-refactor`** skill — that is the skill for AGENTS.md/CLAUDE.md-style files. `crafting-effective-readmes` is for `README.md` and is NOT used on the instruction file (corrected 2026-09-22; the earlier draft of this decision had the two skills swapped). Findings outside Phase 1's scope become deferred ideas, not edits.

### Instruction-file layout and content placement (added 2026-09-22 by user request)
- **D-14:** **`AGENTS.md` is the canonical instruction file**, not `CLAUDE.md`. Evidence: GSD's own `gsd-tools project-instruction-file` resolves to `AGENTS.md`, and codex and opencode — the CLIs now wired for cross-AI review and execution — read `AGENTS.md` by convention. Rules living only in `CLAUDE.md` would be invisible to the agents that execute plans. Migration: move the rule content from `CLAUDE.md` into `AGENTS.md`, and reduce `CLAUDE.md` to the single line `@AGENTS.md` (Claude Code's native import), so there is exactly one source of truth and no duplicated text to drift. `.planning/config.json`'s `claude_md_path` is repointed accordingly. — **Reversibility:** reversible — two files and a config key.
- **D-15:** A written placement rule governs where things go, so future agents do not have to guess:
  - **`AGENTS.md`** — rules and process for agents (the mantra, git policy, tooling discipline, `cross_ai: true`, verification gates, authoritative sources). Validated with `agent-md-refactor` (D-11).
  - **`README.md`** — project information for humans: what kitty-setup is, install, usage, uninstall. Validated with `crafting-effective-readmes`.
  - **`.claude/conventions.md`** — stack and tooling conventions (uv, black, ruff, pyright, bandit, vulture), keeping the existing "Pluggable rules" indirection so the language layer stays swappable.
  - A rule belongs in exactly one of these. A rule discovered in the wrong file is moved, not copied.
- **D-16:** **One commit per plan** (added 2026-09-22 by user request). The rule goes in `AGENTS.md`: an executor squashes a plan's work into a single logical commit naming the plan and the requirements it satisfies, rather than emitting a commit per task. A plan may produce more than one commit only when the changes are genuinely independent — an unrelated drive-by fix — and the second commit's message says why. This supersedes the "commit per task" half of D-06; D-06 keeps worktree-per-phase, merge-on-green, push, and the no-force-push/no-amend guard. Consequence for downstream planners: a plan is sized so that one commit is a coherent unit of review, and the executor is expected to stage the whole plan before committing. Applies from Phase 1 onward, including Phase 1's own execution. — **Reversibility:** reversible — a documented rule.

### Tooling discipline (added 2026-09-22 by user request)
- **D-12:** `CLAUDE.md` gains a research-tooling rule, because token/context cost is a first-class concern: prefer the `codegraph_explore` MCP tool (or `codegraph explore`) **before** opening files — it returns verbatim source plus call paths in one call. When a file must be opened directly, size it up first (`wc -l`, `rg -n '<symbol>'` to get the line number) and read only the relevant range instead of the whole file. Prefer the fast, focused tools — `rg`, `fd`, `wc`, `bat`, `sd`, `eza` — over their slower or more verbose equivalents. Rationale: this repo is CodeGraph-indexed, so a grep/read loop repeats work the index already did.
- **D-13:** CodeGraph index lifecycle is automated, not remembered:
  - **On worktree creation** — `.codegraph/` is gitignored, so a fresh phase worktree has no index. The worktree setup path runs `codegraph init` (first build) so `codegraph_explore` works inside it immediately.
  - **On commit** — the index is refreshed so it never lags the tree. Recommendation for the planner: use `codegraph sync` (incremental, "sync changes since last index") in the commit hook rather than the full `codegraph index` rebuild, and keep the full rebuild for worktree creation. Same guarantee, far cheaper per commit. If `sync` proves unreliable in practice, fall back to `index -q`.
  - Both run non-blocking with respect to correctness: a CodeGraph failure must warn, never abort a commit or a worktree creation.
  - This extends the hook set from D-07/D-08 (`tools/hooks/`, wired via `core.hooksPath`), so one mechanism covers the pre-push guard and both CodeGraph triggers.

### Claude's Discretion
- Exact banner wording and placement (top-of-file vs after H1).
- Whether the pre-push guard is wired by a Makefile target or a `my-kitty` subcommand (D-08).
- Ordering of the archive → move → banner → CLAUDE.md steps within the phase.
- Which git hook carries the D-13 commit refresh (`post-commit` keeps commits fast; `pre-commit` keeps the index exact at commit time).
- Whether the worktree `codegraph init` is invoked by a hook (`post-checkout`) or by the Makefile/worktree helper — hooks do not fire on every `git worktree add` path, so the planner must verify empirically before choosing (mantra applies).

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Phase intent and requirements
- `docs/prds/kitty-setup-remediation-v1.0-prd.md` §R0 — the source PRD for this phase's requirements (R0.1–R0.4; R0.5–R0.7 were added during this discussion).
- `.planning/REQUIREMENTS.md` R0.1–R0.7 — requirement IDs and acceptance text (R0.2/R0.4 reworded per D-03/D-06; R0.5–R0.7 added per D-12/D-13/D-10).
- `.planning/ROADMAP.md` "Phase 1" + "Universal Phase Gate" — success criteria and the per-phase gate (step 6 is being updated per D-06).
- `.planning/PROJECT.md` Key Decisions — the three locked decisions; the git row changes per D-06.

### Files this phase edits
- `AGENTS.md` — the canonical instruction file this phase creates (D-09, D-10, D-14, D-15).
- `CLAUDE.md` — reduced to a single `@AGENTS.md` import line (D-14).
- `README.md` — not edited here; named only so the placement rule in D-15 can point at it.
- `docs/requirements.md`, `docs/propossal_roadmap.md` — banner targets (D-04).
- `openspec/changes/phase1-curated-bindings-revert-defaults/` — the change being archived (D-01).
- `openspec/config.yaml` — moves with the tree (D-02).

### Process
- `docs/agent-iteration.md` — hypothesis/probe playbook; stays authoritative and must remain referenced from `CLAUDE.md`.
- `.claude/conventions.md` — Python tooling conventions (ruff, black, pyright, bandit, vulture); unchanged by this phase.

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `openspec` CLI v1.13.1 is installed via volta (`~/.volta/bin/openspec`) and works: `openspec list` shows the one pending change, `openspec archive --skip-specs` is the documented path for a doc-only retirement. Note: the openspec **skills and `opsx` commands were deleted** from `.claude/` on 2026-09-22 — the CLI is the only remaining tool.
- `Makefile` targets are thin (1–2 lines each, ≤5 by rule) — the right place to wire the hook installer (D-07).

### Established Patterns
- `CLAUDE.md` delegates stack conventions to `.claude/conventions.md` ("Pluggable rules"), so process rules belong in `CLAUDE.md` and tooling rules do not.
- Shell is confined to `tools/` by the Stack rule; `tools/hooks/` keeps D-07 compliant.

### Integration Points
- `.planning/config.json` now exists and encodes the phase-branch/worktree strategy that D-06 documents — config and prose must agree.
- ~25 files reference `openspec/` paths (`config/kitty/*.conf` provenance comments, `src/kitty_setup/{config_updater,pruner,binding_introspection}.py` docstrings, `docs/repro/*.md`, `README.md`). D-02 invalidates those paths; Phase 8 owns the repair.

</code_context>

<specifics>
## Specific Ideas

- The user's framing for D-02: the OpenSpec material should become "legacy inside GSD" rather than a second planning tree at the repo root.
- Cross-AI wiring requested explicitly, now in `.planning/config.json`: plan-review convergence and execution both through opencode — `router-env/my-plan-review` for review, `router-env/my-coding` for execution (`workflow.cross_ai_command: "opencode run --model router-env/my-coding"`, verified to read the prompt from stdin).
- Planning granularity `fine` and model profile `adaptive`, with the 9-phase roadmap structure explicitly preserved — granularity applies to plan decomposition inside a phase, never to re-deriving the phase count.

</specifics>

<deferred>
## Deferred Ideas

- **`curl | bash` installer with channel selection** — modeled on `../wezterm-setup/tools/install.sh`, letting a user install a chosen channel (nightly/release). Agreed to become a phase of its own: initially Phase 10 (after macOS verification), then moved to **Phase 9** on 2026-09-22 at the user's request, with the installer's Mac-side run carried into Phase 10 (macOS E2E) as criterion 5. Needs its own requirement IDs (R8.x) added to `.planning/REQUIREMENTS.md`.
- **Repairing the ~25 stale `openspec/` path references** created by D-02 — belongs to Phase 8 (live-doc hygiene), which already owns doc accuracy.
- **`CLAUDE.md` Stack-section inaccuracies** beyond D-08's hook line (it claims the upstream-installer call and PATH edit happen in bash; both are Python now) — Phase 8, requirement R6.1.
- **Findings from `crafting-effective-readmes` (D-11)** that exceed Phase 1 scope — recorded, not acted on.

</deferred>

---

*Phase: 1-Governance & Freeze*
*Context gathered: 2026-09-22*

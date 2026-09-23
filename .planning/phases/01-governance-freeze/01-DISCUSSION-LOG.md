# Phase 1: Governance & Freeze - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-09-22
**Phase:** 1-Governance & Freeze
**Areas discussed:** Archive mechanics, Rule enforcement, Freeze scope, CLAUDE.md shape, GSD configuration, Tooling discipline, Instruction-file layout
**Mode:** discuss + `--analyze` overlay (trade-off table before each question; requested as `—analyze`)

---

## Archive mechanics

| Option | Description | Selected |
|--------|-------------|----------|
| `openspec archive --skip-specs` | One command; `openspec list` goes clean; specs stay stale but frozen | ✓ |
| Fix the delta properly | Author the 7 validator fixes, archive with a real spec sync | |
| Manual `mv` | Move the directory by hand, ignoring the working CLI | |

**User's choice:** "2/3" initially, then a better idea — move all the OpenSpec docs into `.planning/` so they become legacy inside GSD.
**Notes:** A second round resolved it: archive with `--skip-specs`, then `git mv openspec/ .planning/legacy/openspec/`. Evidence that drove the recommendation: `openspec validate --strict` reports 7 errors (6 MODIFIED blocks drop scenarios the CLI requires restated or explicitly REMOVED; the instant-clear block targets a requirement absent from main), and PROJECT.md already lists "rewriting frozen OpenSpec specs" as out of scope. Correction made during discussion: the `openspec` CLI v1.13.1 *is* installed (volta) — an earlier check ran without volta on PATH.

---

## Rule enforcement

| Option | Description | Selected |
|--------|-------------|----------|
| Text + pre-push hook | CLAUDE.md states the policy; a versioned hook refuses the forbidden push | ✓ (with the policy itself changed) |
| Text only | Policy documented, nothing enforces it | |
| Hook + Claude deny rules | Both, plus settings.local.json entries | |

**User's choice:** Asked what "rules" meant, then set the policy themselves: worktrees per phase, merge at the end into main, push.
**Notes:** "Rules" was clarified as (a) the research→experiment→decide mantra and (b) the git policy, both as CLAUDE.md text. The answer **replaced the policy** that PROJECT.md had locked ("never merge to master"), so it was re-confirmed explicitly in round 2 before being written. The structural guard survives: a `tools/hooks/` pre-push hook via `core.hooksPath`, justified by cross-AI execution now being enabled — a guard in one assistant's settings would not bind the other CLIs.

---

## Freeze scope

| Option | Description | Selected |
|--------|-------------|----------|
| openspec/ + both legacy docs | Banners on the OpenSpec README plus `docs/requirements.md` and `docs/propossal_roadmap.md` | ✓ |
| openspec/README.md only | Literal R0.2 scope | |
| Banner + relocate to docs/history/ | Strongest signal, breaks ~25 inbound references | |

**User's choice:** openspec/ + both legacy docs.
**Notes:** Both legacy docs are still cited as authoritative by CLAUDE.md and are superseded by `.planning/`. They are bannered, not moved — relocating them would break the same reference set as the OpenSpec move for no extra signal.

---

## CLAUDE.md shape

| Option | Description | Selected |
|--------|-------------|----------|
| Surgical edit | Rewrite the affected blocks in the existing 62-line file | ✓ |
| Restructure via agent-md-refactor | Split into linked docs with progressive disclosure | |

**User's choice:** Surgical edit, then validate the result, and add the cross-AI frontmatter rule.
**Notes:** A restructure would also collide with Phase 8's edits to the same file. **Corrected later in the discussion:** the validating skill is `agent-md-refactor` (for AGENTS.md/CLAUDE.md-style files), not `crafting-effective-readmes` (for README.md) — the user caught the mismatch.

---

## GSD configuration

| Option | Description | Selected |
|--------|-------------|----------|
| All four as described | fine granularity, adaptive profile, cross-AI convergence + execution, `cross_ai: true` default | ✓ (with specific models) |
| Same, different reviewer order | User names the CLI priority | |
| Config now, cross-AI later | Defer the cross-AI wiring | |

**User's choice:** Option 1, plus specific models — plan-review convergence and execution both through opencode: `router-env/my-plan-review` for review, `router-env/my-coding` for execution.
**Notes:** Both model IDs verified present in `opencode models`. `opencode run` was tested and does read the prompt from stdin, which is how GSD pipes it — so `workflow.cross_ai_command` is `opencode run --model router-env/my-coding`. `.planning/config.json` was created during this discussion; two seeded values were corrected: `claude_md_path` pointed at a nonexistent `./.claude/CLAUDE.md`, and the UI gates (`ui_phase`, `ui_review`, `live_dom_uat`) were disabled since this project has no frontend.

---

## Tooling discipline

Raised by the user mid-discussion; no options were presented — it was a direct instruction.

**User's request:** A rule that creating a worktree runs `codegraph index`, and that committing refreshes it too. Prioritize the `codegraph_explore` MCP tool; use `wc`/`rg`/`bat`/`sd`/`eza`/`fd` and similar faster tools; be token- and context-aware — e.g. use CodeGraph before opening files, and for large files use `wc` to learn the size and `rg` to find a method's line before reading the whole thing.
**Notes:** Captured as D-12 (tooling rule) and D-13 (index lifecycle) plus requirements R0.5/R0.6. One deviation from the literal request, flagged for the planner: `codegraph sync` ("sync changes since last index") is recommended for the per-commit refresh instead of the full `codegraph index` rebuild — same guarantee, far cheaper per commit — with the full rebuild kept for worktree creation, where `.codegraph/` is absent because it is gitignored.

---

## Instruction-file layout

| Option | Description | Selected |
|--------|-------------|----------|
| AGENTS.md + `@AGENTS.md` import | AGENTS.md canonical; CLAUDE.md becomes a one-line native import | ✓ |
| AGENTS.md + CLAUDE.md symlink | One source, but symlink behaviour varies per tool and on Windows checkouts | |
| Keep CLAUDE.md canonical | Works for Claude, fights the convention GSD and the other CLIs assume | |

| Option | Description | Selected |
|--------|-------------|----------|
| Rules vs info vs conventions | AGENTS.md = rules; README.md = project info; `.claude/conventions.md` = stack conventions | ✓ |
| Rules vs everything else | AGENTS.md = rules; everything else folded into README.md | |

**User's choice:** AGENTS.md canonical via `@import`, with the three-way placement split.
**Notes:** Driven by evidence gathered during the discussion: `gsd-tools project-instruction-file` resolves to `AGENTS.md`, and codex/opencode read `AGENTS.md` by convention — so with cross-AI review and execution now enabled, rules kept only in `CLAUDE.md` would be invisible to the CLIs that execute plans. The repo currently has only `CLAUDE.md` (62 lines). Captured as D-14/D-15 plus requirements R0.8/R0.9.

## Claude's Discretion

- Banner wording and placement.
- Whether the pre-push guard is wired by a Makefile target or a `my-kitty` subcommand.
- Ordering of the archive → move → banner → CLAUDE.md steps.
- Which hook carries the per-commit CodeGraph refresh (`pre-commit` vs `post-commit`).
- How the worktree index build is triggered — hooks do not fire on every `git worktree add` path, so it must be verified empirically before choosing.

## Deferred Ideas

- **`curl | bash` installer with channel selection** (modeled on `../wezterm-setup/tools/install.sh`) — promoted to its own phase with requirements R8.1–R8.3 — added as Phase 10, then reordered to **Phase 9** on 2026-09-22 (macOS E2E became Phase 10 and absorbed the installer's Mac-side run as R8.3).
- **Repairing ~25 stale `openspec/` path references** created by the move — Phase 8.
- **CLAUDE.md Stack-section inaccuracies** beyond the new hook line — Phase 8, R6.1.
- **`crafting-effective-readmes` findings** beyond Phase 1 scope — recorded, not acted on.

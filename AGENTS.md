# kitty-setup — Agent Rules

Universal, non-negotiable rules for any agent (or human) working in this repo. Project
identity and structure live in `README.md`; stack and tooling **conventions** live in
`.claude/conventions.md` — neither is duplicated here. What this file states about the
stack is the **allow-list** (`## Stack` below): a rule about what may exist in the repo,
not a tooling convention. Rules and process for agents live in this file — the canonical
instruction file — validated with the `agent-md-refactor` skill. Project information for
humans lives in `README.md`, validated with the `crafting-effective-readmes` skill. A
rule belongs in exactly one of the three files; a rule found in the wrong file is moved,
not copied.

## Authoritative sources

- Requirements: [.planning/REQUIREMENTS.md](.planning/REQUIREMENTS.md).
- Roadmap and phase gate: [.planning/ROADMAP.md](.planning/ROADMAP.md).
- Project identity, key decisions and live state: [.planning/PROJECT.md](.planning/PROJECT.md),
  [.planning/STATE.md](.planning/STATE.md).
- Per-phase intent: [.planning/phases/](.planning/phases/) — each phase directory holds its
  CONTEXT, RESEARCH, PATTERNS, VALIDATION, PLAN and SUMMARY artifacts.
- Hypothesis playbook: [docs/agent-iteration.md](docs/agent-iteration.md).
- Frozen history, never authoritative and never edited: [.planning/legacy/openspec/](.planning/legacy/openspec/),
  [docs/requirements.md](docs/requirements.md), [docs/propossal_roadmap.md](docs/propossal_roadmap.md) —
  each carries a FROZEN banner.

If existing code conflicts with `.planning/REQUIREMENTS.md`, `.planning/ROADMAP.md`, or the
active phase's CONTEXT, refactor the code. The planning artifacts are not silently rewritten
to match drifted code.

## Universal rules

- **English everywhere** — code, comments, commits, PR text, agent responses.
- **Research, then experiment, then decide, then implement.** Non-negotiable. Any removal
  or replacement of behaviour — a config line, a chord, or a code path — requires
  documented research (kitty docs, source, or introspection) and an experiment on a real
  kitty session with recorded evidence under `tmp/h<NN>-<slug>/`, both **before** the
  decision. No "should work" — only "verified by `<command>` → `<output>`". See
  [docs/agent-iteration.md](docs/agent-iteration.md).
- **Hypothesis before implementation.** Every shipped behavior begins as a hypothesis in
  `tmp/h<NN>-<slug>/`. Promote only after an autonomous run is green. See
  [docs/agent-iteration.md](docs/agent-iteration.md).
- **Git policy.** Each phase runs in its own git worktree on branch
  `gsd/phase-{phase}-{slug}`. Work lands per the commit-granularity rule below. At phase
  end, once `make doctor` and `make test` are green, merge into `master` and push — the
  same precondition `.planning/ROADMAP.md`'s Universal Phase Gate step 6 states. Phase
  1's branch merges after Phase 2's R1.1 turns `make doctor` green. Never
  force-push or amend pushed commits. Enforced by `tools/hooks/pre-push`, wired once via
  `core.hooksPath` by `make hooks`; the hook rejects any push whose remote tip is not an
  ancestor of the local tip, plus any push naming `refs/heads/master` on either side of its
  refspec that carries a non-merge commit no `gsd/*` branch contains. All its limits
  disclosed, from the hook's own header: `git push
  --no-verify` bypasses any client-side hook; `KITTI_ALLOW_MASTER_PUSH=1` deliberately
  skips the `master` provenance guard; a squash merge into `master` is rejected;
  cherry-picked or rebased commits landing on `master` are rejected; a `gsd/*` branch
  deleted before its merge is pushed makes the guard reject a legitimate post-merge push;
  the first push of `master` to an empty remote ref of **any** name is rejected; a deletion of
  `refs/heads/master` is rejected; and the provenance guard is keyed on ref **names**, so
  master's content pushed from some other local ref name — `git push origin
  <other-branch>:refs/heads/main`, or `HEAD:` — is not seen, the same way a fabricated
  `gsd/*` pointer at a master-authored commit satisfies provenance by reachability.
  `KITTI_ALLOW_MASTER_PUSH=1` is the sanctioned route for
  the by-design rejections. This is a compliance guard for cooperating agents, not a
  security boundary.
- **Commit granularity.** Work lands as one commit per plan, not one per task. An executor
  stages the whole plan and squashes it into a single logical commit whose message names
  the plan and the requirements it satisfies. More than one commit only when the changes
  are genuinely independent — an unrelated drive-by fix — and the second commit's message
  states why. A plan whose frontmatter is `type: tdd` instead makes exactly two commits,
  RED then GREEN (`(<phase>-<plan>)` scoped): a RED commit of the new tests only, at which
  those tests fail, then a GREEN commit with the implementation and the SUMMARY. This
  bullet is the only place in the repo where the rule is written.
- **Re-read before edit.** The user may edit files between turns; never trust in-memory
  contents. Re-read before evaluating or modifying.
- **Skill outputs land on disk.** Brainstorms, designs, plans, analyses are written to
  files — under `.planning/`, `docs/`, or the `tmp/h<NN>-<slug>/` hypothesis dir the
  mantra rule above requires. If it isn't on disk, it doesn't exist.
- **Research tooling first.** Prefer the `codegraph_explore` MCP tool, or `codegraph
  explore` from the shell, **before** opening files — it returns verbatim source plus call
  paths in one call, and this repo is CodeGraph-indexed, so a grep-and-read loop repeats
  work the index already did. When a file must be opened directly, size it first (`wc -l`,
  and `rg -n '<symbol>'` for the line number) and read only the relevant range. Prefer
  `rg`, `fd`, `wc`, `bat`, `sd`, `eza` over their slower or more verbose equivalents.
- **Cross-AI by default.** Every new GSD plan carries `cross_ai: true` in its frontmatter,
  so cross-AI execution is the default rather than a per-plan opt-in. This is an existing
  GSD mechanism — read by `execute-phase`'s cross-AI delegation step and already wired in
  `.planning/config.json` — the rule makes plans opt in; it does not invent a mechanism.
- **Verify before declaring done.** Any "ready" claim is backed by `make doctor` and
  `make test` output captured into the PR / handoff — both commands, captured rather than
  green. No "should work" — only "verified by `<command>` → `<output>`". Capturing is the
  evidence duty and is a separate thing from the merge precondition: the git policy above
  additionally requires both commands to be green before a phase branch merges, so a
  captured-but-red run satisfies this rule and still blocks the merge.
- **Questions are not orders.** Answer questions; do not auto-change code.

## Stack

Python is the stack. Bash is allowed in exactly two places. **One**, the
prerequisite bootstrap pair `tools/setup.sh` and `tools/uninstall.sh` (uv
install, `uv tool install --force .`, the kitty upstream installer call, the
sentinel-bracketed shell-rc PATH edit dispatch, and a confirm +
KEEP_*→--keep-* flag-forward layer over `my-kitty uninstall` with a
will-remove enumeration in the prompt and a fallback to the legacy
`my-kitty-setup` binary during the rename upgrade window). **Two**, the
git-invoked hook entry points under `tools/hooks/` — `pre-push`,
`post-commit`, `post-checkout` — each of which stays a thin dispatcher (argv
or stdin parse plus one guarded call); a hook that outgrows
`tools/uninstall.sh`'s dispatcher delegates to a `my-kitty` subcommand. No
shell scripts outside those two clauses — anything beyond them is a
subcommand under `src/kitty_setup/cli.py`, the single `[project.scripts]`
entry point (`my-kitty`). One exception, for developer-only tooling that is
not part of the installed product: it may be a Python module under
`src/kitty_setup/harness/` run as `uv run python -m kitty_setup.harness.<name>`
— today, only the integration-test runner. It adds no shell and ships no
end-user command; a `my-kitty` subcommand would hand users a pytest runner
for a `tests/` tree they do not have. The Makefile is thin glue: each target
is at most five lines, and any target that grows past that dispatches into
`tools/`, a subcommand of `my-kitty`, or such a harness module.

## Pluggable rules

Stack-specific conventions live in dedicated files so they can be swapped or replaced
without touching this entry point:

- [.claude/conventions.md](.claude/conventions.md) — Python language and tooling
  conventions (uv, black, ruff, pyright, bandit, vulture, pytest). Replace this file
  wholesale when switching the primary language. Keep the filename; the agent always
  reads it.

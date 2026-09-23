# kitty-setup — Agent Rules

Universal, non-negotiable rules for any agent (or human) working in this repo. Project
identity, structure, and stack live in `README.md` and the swappable convention files
below — never duplicated here.

## Authoritative sources

- v1 scope: [docs/requirements.md](docs/requirements.md).
- Roadmap: [docs/propossal_roadmap.md](docs/propossal_roadmap.md).
- Active OpenSpec change: [openspec/changes/](openspec/changes/) (use `openspec list` to
  enumerate). Process: see the OpenSpec workflow in
  `.claude/skills/openspec-*/SKILL.md`. There is no `.claude/workflow.md` — that file
  came from a different framework and is not used here.
- Hypothesis playbook: [docs/agent-iteration.md](docs/agent-iteration.md).

If existing code conflicts with the constitution, `requirements.md`, or the active
OpenSpec change, refactor the code. The spec is not silently rewritten to match drifted
code.

## Universal rules

- **English everywhere** — code, comments, commits, PR text, agent responses.
- **No auto-commit.** Surface `git status` and `git diff --stat`; wait for an explicit
  go-ahead ("commit", "do it", "proceed") before any commit/push/amend/force-push.
- **Re-read before edit.** The user may edit files between turns; never trust in-memory
  contents. Re-read before evaluating or modifying.
- **Skill outputs land on disk.** Brainstorms, designs, plans, analyses are written to
  files (under `openspec/changes/<id>/` or `docs/`). If it isn't on disk, it doesn't exist.
- **Spec-first.** The OpenSpec change is authoritative. The agent that produces a design
  or plan is *not* the same agent that executes it.
- **Hypothesis before implementation.** Every shipped behavior begins as a hypothesis in
  `tmp/h<NN>-<slug>/`. Promote only after an autonomous run is green. See
  [docs/agent-iteration.md](docs/agent-iteration.md).
- **Verify before declaring done.** Any "ready" claim is backed by `make doctor` and
  `make test` output captured into the PR / handoff. No "should work" — only
  "verified by `<command>` → `<output>`".
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
entry point (`my-kitty`). The Makefile is thin glue: each target is at most
five lines, and any target that grows past that dispatches into `tools/` or a
subcommand of `my-kitty`.

## Pluggable rules

Stack-specific conventions live in dedicated files so they can be swapped or replaced
without touching this entry point:

- [.claude/conventions.md](.claude/conventions.md) — Python language and tooling
  conventions (uv, black, ruff, pyright, bandit, vulture, pytest). Replace this file
  wholesale when switching the primary language. Keep the filename; the agent always
  reads it.

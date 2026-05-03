# kitty-scenes — Agent Rules

Universal, non-negotiable rules for any agent (or human) working in this repo. Project
identity, structure, and stack live in `README.md`, the constitution, and the
swappable convention files below — never duplicated here.

## Authoritative sources


- v1 scope: [docs/requirements.md](docs/requirements.md).
- Roadmap: [docs/propossal_roadmap.md](docs/propossal_roadmap.md).

If existing code conflicts with the constitution or `requirements.md`, refactor the code.
The spec is not silently rewritten to match drifted code.

## Universal rules

- **English everywhere** — code, comments, commits, PR text, agent responses.
- **No auto-commit.** Surface `git status` and `git diff --stat`; wait for an explicit
  go-ahead ("commit", "do it", "proceed") before any commit/push/amend/force-push.
- **Re-read before edit.** The user may edit files between turns; never trust in-memory
  contents. Re-read before evaluating or modifying.
- **Skill outputs land on disk.** Brainstorms, designs, plans, analyses are written to
  files (under `specs/<feature>/` or `docs/`). If it isn't on disk, it doesn't exist.
- **Spec-first.** The plan/spec is authoritative. The agent that produces a design or plan
  is *not* the same agent that executes it.
- **Questions are not orders.** Answer questions; do not auto-change code.

## Pluggable rules

Stack-specific and process-specific rules live in dedicated files so they can be swapped
or replaced without touching this entry point:

- [.claude/conventions.md](.claude/conventions.md) — current language and tooling
  conventions. **Replace this file wholesale when switching primary language** (e.g. from
  Python to JavaScript). Keep the filename; the agent always reads it.
- [.claude/workflow.md](.claude/workflow.md) — git discipline, PR gates,
  promotion criteria. Stack-agnostic.

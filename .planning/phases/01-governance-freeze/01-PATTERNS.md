# Phase 1: Governance & Freeze - Pattern Map

**Mapped:** 2026-09-23
**Files analyzed:** 11 (4 created, 5 modified, 1 moved, 1 created-by-move)
**Analogs found:** 9 / 11
**Tracked-source gate:** every analog path below verified via `git ls-files` (all tracked; no gitignored mirrors).

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|-------------------|------|-----------|----------------|---------------|
| `AGENTS.md` (new) | config / instruction doc | transform (content migration) | `CLAUDE.md` (its own content, being migrated) | exact — the analog *is* the source |
| `CLAUDE.md` (modified → 1 line) | config shim | request-response (loader import) | none in-repo | no analog (1-line file) |
| `tools/hooks/pre-push` (new) | middleware (git guard) | event-driven (stdin refs → exit code) | `tools/uninstall.sh` | role-match (shell under `tools/`) |
| `tools/hooks/post-commit` (new) | middleware | event-driven (fire-and-forget) | `tools/setup.sh` | role-match |
| `tools/hooks/post-checkout` (new) | middleware | event-driven (argv flags) | `tools/setup.sh` | role-match |
| `Makefile` `hooks:` target (modified) | config glue | request-response | `Makefile` existing `doctor`/`test`/`prune` targets | exact |
| `tests/unit/test_git_hooks.py` (new) | test | file-I/O + subprocess | `tests/integration/test_h21_doctor_remote_control.py` + `tests/integration/_kitty_subprocess.py` | role-match (subprocess harness; git instead of kitty) |
| `tests/conftest.py` (unmodified, consumed) | test fixture/gate | — | itself — the `KITTI_INTEGRATION` gate | exact |
| `.planning/config.json` (modified) | config | — | itself, line 69 | exact |
| `docs/requirements.md`, `docs/propossal_roadmap.md` (banners) | doc | — | each other (identical opening shape) | exact |
| `.planning/legacy/openspec/README.md` (new) | doc | — | `docs/requirements.md` opening shape | role-match — **no `openspec/README.md` exists today**; this file is created from scratch |

---

## Pattern Assignments

### `AGENTS.md` (new canonical instruction file) — migrate, do not rewrite

**Analog:** `/var/home/bazzite/git/personal/kitty-setup/CLAUDE.md` (62 lines, tracked). Its content IS the migration source (D-14). Exact current structure, verbatim:

| Line | Element |
|------|---------|
| `CLAUDE.md:1` | `# kitty-setup — Agent Rules` (H1) |
| `CLAUDE.md:3-5` | Un-headed 3-line preamble stating the file's remit + delegation |
| `CLAUDE.md:7` | `## Authoritative sources` (4 bullets + a 3-line trailing paragraph) |
| `CLAUDE.md:21` | `## Universal rules` (8 bullets, each `- **Bold lead-in.** prose`) |
| `CLAUDE.md:40` | `## Stack` (one prose paragraph, no bullets) |
| `CLAUDE.md:54` | `## Pluggable rules` (2-line intro + 1 bullet) |

**Preamble (`CLAUDE.md:1-5`) — the delegation contract to preserve:**
```markdown
# kitty-setup — Agent Rules

Universal, non-negotiable rules for any agent (or human) working in this repo. Project
identity, structure, and stack live in `README.md` and the swappable convention files
below — never duplicated here.
```
This preamble already encodes D-15's placement rule in embryo (`README.md` = identity, convention files = stack). D-15's explicit three-way placement rule should be written as an *expansion* of this sentence, not as a competing new section.

**`## Authoritative sources` (`CLAUDE.md:7-19`) — the section D-09/R0.3 rewrites:**
```markdown
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
```
Style to keep: inline markdown links `[path](path)`, one bullet per source, sentence-terminating periods, a trailing "conflict resolution" paragraph. Bullets 1–3 all become stale this phase (banners + `.planning/` supersession + `openspec/` relocation + deleted openspec skills); bullet 4 (`docs/agent-iteration.md`) stays per D-09.

**`## Universal rules` (`CLAUDE.md:21-38`) — bullet style to replicate exactly:**
```markdown
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
```
Invariants: `- **Short imperative title.** ` then prose; em-dash variant used when the title is a noun phrase (`**English everywhere** —`); 95-ish column wrap with 2-space continuation indent; backticked commands; the "verified by `<command>` → `<output>`" formula is the house phrasing for verification claims and should be reused verbatim by the new mantra rule (R0.1) and the merge-on-green gate (R0.4).

Per-bullet disposition for the planner:
- `English everywhere`, `Re-read before edit`, `Verify before declaring done`, `Questions are not orders` — carry across verbatim.
- `No auto-commit` — replaced by the D-06/D-16 git policy (worktree-per-phase, one commit per plan, merge-on-green, push; no force-push/amend).
- `Skill outputs land on disk` — keep the rule, repoint `openspec/changes/<id>/` to `.planning/`.
- `Spec-first` — deleted (D-09).
- `Hypothesis before implementation` — keep; `docs/agent-iteration.md` link stays authoritative (D-09).

**`## Stack` (`CLAUDE.md:40-52`) — QUOTED VERBATIM; this is the constraint governing whether hook logic may be shell at all:**
```markdown
## Stack

Python is the stack. Bash exists only inside `tools/setup.sh` and
`tools/uninstall.sh` for prerequisite bootstrap (uv install, `uv tool install
--force .`, the kitty upstream installer call, the sentinel-bracketed shell-rc
PATH edit dispatch, and a confirm + KEEP_*→--keep-* flag-forward layer over
`my-kitty uninstall` with a will-remove enumeration in the prompt and a
fallback to the legacy `my-kitty-setup` binary during the rename upgrade
window). No new shell scripts elsewhere — anything
beyond the bootstrap line is a subcommand under `src/kitty_setup/cli.py`, the
single `[project.scripts]` entry point (`my-kitty`). The Makefile is thin
glue: each target is at most five lines, and any target that grows past that
dispatches into `tools/` or a subcommand of `my-kitty`.
```
**Reading for the planner (load-bearing):** the rule as written is an *allow-list of two named files*, not a directory-scoped allowance — "Bash exists only inside `tools/setup.sh` and `tools/uninstall.sh`" followed by "No new shell scripts elsewhere". D-08's claim that `tools/hooks/` "keeps the rule holding without amendment" is therefore **not** literally true against the current text: three new shell files outside the two named ones require the Stack paragraph to be amended to name `tools/hooks/` (D-08's own sentence concedes this: "`CLAUDE.md`'s Stack section is updated to name it"). So the AGENTS.md Stack paragraph must be rewritten to a three-clause allow-list: the two bootstrap scripts **plus** `tools/hooks/*` as git-invoked hook entry points, with the "anything beyond … is a subcommand under `src/kitty_setup/cli.py`" escape clause retained. Corollary for hook design: keep each hook *thin* — argv/stdin parsing plus a dispatch — so the spirit of the rule ("no business logic in shell") survives; any hook that grows past the size of `tools/uninstall.sh`'s dispatcher should delegate to a `my-kitty` subcommand.

**`## Pluggable rules` (`CLAUDE.md:54-62`) — the indirection to preserve word-for-word (D-15):**
```markdown
## Pluggable rules

Stack-specific conventions live in dedicated files so they can be swapped or replaced
without touching this entry point:

- [.claude/conventions.md](.claude/conventions.md) — Python language and tooling
  conventions (uv, black, ruff, pyright, bandit, vulture, pytest). Replace this file
  wholesale when switching the primary language. Keep the filename; the agent always
  reads it.
```
The other half of the contract lives in the target file — `.claude/conventions.md:1-5`:
```markdown
# Language & Tooling Conventions — Python (current)

This file is the **plug point** for stack-specific rules. To switch the project to a
different language, replace the contents of this file with the new stack's conventions.
The filename (`.claude/conventions.md`) and the link from `CLAUDE.md` stay the same.
```
**Planner note (a real edit, easy to miss):** `.claude/conventions.md:5` says "the link from `CLAUDE.md` stays the same". Once `CLAUDE.md` is a stub and `AGENTS.md` owns the link, that sentence becomes false. Either update that line to name `AGENTS.md`, or record it as a Phase 8 doc-hygiene item — but do not leave it silently contradicting D-14.

---

### `tools/hooks/pre-push`, `post-commit`, `post-checkout` (middleware, event-driven)

**Analogs:** `/var/home/bazzite/git/personal/kitty-setup/tools/setup.sh` and `/var/home/bazzite/git/personal/kitty-setup/tools/uninstall.sh` (the repo's only two shell files; both tracked, mode 755).

**House style, distilled — every element below is present in BOTH analogs, so treat it as the prelude contract:**

1. **Shebang:** `#!/usr/bin/env bash` (`setup.sh:1`, `uninstall.sh:1`) — not `#!/bin/sh`, not `#!/bin/bash`. Bashisms (`[[ ]]`, `BASH_SOURCE`) are therefore in-style.
2. **Header comment block** — mandatory, 6–14 lines, `path/name.sh — one-line purpose`, then a self-justification against the Stack rule, then a numbered `Steps:` list or a caller-contract note. `setup.sh:1-14`:
```bash
#!/usr/bin/env bash
# tools/setup.sh — bootstrap entry point. The only bash logic in this repo (paired with
# tools/uninstall.sh). See CLAUDE.md ("Stack") and docs/agent-iteration.md (R3).
#
# Steps:
#   1. Ensure `uv` is on PATH; install via the upstream installer if missing.
#   2. `uv sync` — provision the local dev .venv (used by tests).
...
```
`uninstall.sh:1-10` uses the same shape, with a caller contract instead of steps:
```bash
#!/usr/bin/env bash
# tools/uninstall.sh — bootstrap-territory bash. Thin dispatcher onto
# `my-kitty uninstall`. The CLI owns the actual removal logic; this script
# just confirms (skippable via KITTI_FORCE=1) and forwards flags. ...
#
# Caller (Makefile) sets KEEP_BACKUPS / KEEP_CONFIG / KEEP_KITTY (each =1) to
# preserve the corresponding subset. Default (no env vars) removes everything
# we created.
```
Each new hook's header must state which git event invokes it, its argv/stdin contract, and — per the Stack analysis above — why it is allowed to be shell.

3. **Strict mode, immediately after the header, then repo-root normalization** (`setup.sh:16-19`, identical at `uninstall.sh:12-15`):
```bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${REPO_ROOT}"
```
**Hook-specific adaptation the planner must call out:** `set -e` is *hostile* to the D-13 "warn, never abort" requirement (R0.6) — any failing `codegraph` invocation would abort the script and, in `post-checkout`/`post-commit`, exit non-zero. Two compatible options: keep `set -euo pipefail` and suffix every fallible call with `|| log "warning: …"`, plus a terminal explicit `exit 0` (this is exactly the shape RESEARCH.md's illustrative snippet at `01-RESEARCH.md:225-232` uses). Do not silently drop `set -euo pipefail` — that would break house style without a stated reason.
Also note the `REPO_ROOT` idiom resolves `../` from the hook file, which for `tools/hooks/x` is `tools/`, not the repo root — a hook needs `/../..` or `git rev-parse --show-toplevel`. Since git already `cd`s to the worktree root before invoking a hook (`01-RESEARCH.md:166`), the cleanest in-style form is to keep the two lines but compute `"$(dirname "${BASH_SOURCE[0]}")/../.."`.

4. **Logging: a one-line `log()` helper with a bracketed script tag — there is no shared prelude file; each script defines its own.** `setup.sh:21` / `uninstall.sh:17`:
```bash
log() { printf '[setup] %s\n' "$*"; }
```
```bash
log() { printf '[uninstall] %s\n' "$*"; }
```
So the hooks get `log() { printf '[pre-push] %s\n' "$*"; }` etc. Two observations the planner needs:
- **`log` writes to stdout, not stderr, including for errors.** Errors are `log "ERROR: …"` followed by `exit 1` — see `setup.sh:33-36` and `uninstall.sh:38-41`:
```bash
    if ! command -v uv >/dev/null 2>&1; then
        log "ERROR: uv install reported success but the binary is not on PATH"
        exit 1
    fi
```
```bash
    log "ERROR: neither my-kitty nor my-kitty-setup found on PATH or in ~/.local/bin"
    log "       run 'make install' first, or remove manually"
    exit 1
```
Note the continuation-line convention: a second `log` call whose message is space-padded to align under the first. For a `pre-push` **rejection** message, stderr is the better channel (git surfaces it either way, but a rejection is diagnostic output, not progress); if the planner chooses stderr, add a second helper (`err() { printf '[pre-push] %s\n' "$*" >&2; }`) rather than changing `log`'s semantics — deviating from the established `log` shape needs an inline comment saying why.
- Raw `printf` (not `log`) is used for multi-line user-facing text — `uninstall.sh:60-79` (`print_will_remove`) prints an itemized "About to remove" list with `printf '  - …\n'` per item. The pre-push rejection message should follow this: `log` for the verdict line, bare indented `printf` for the "how to proceed" enumeration.

5. **Structure: every unit of work is a named function; the bottom of the file is a flat call sequence, nothing else.** `setup.sh:67-72`:
```bash
ensure_uv
sync_dev_env
install_tool
run_install_subcommand "$@"

log "done"
```
`uninstall.sh:95-101` same, with locals captured first:
```bash
UNINSTALL_FLAGS="$(build_flags)"
confirm
binary="$(resolve_binary)"
# shellcheck disable=SC2086 — UNINSTALL_FLAGS expansion is intentional.
"${binary}" uninstall ${UNINSTALL_FLAGS}

log "done"
```
Both end with `log "done"`. For hooks, a terminal `exit 0` replaces/accompanies it.

6. **Preconditions are guarded by `command -v <tool> >/dev/null 2>&1` with an early `return`/fallback chain, never by `which`.** `uninstall.sh:19-41` (`resolve_binary`) is the canonical multi-candidate resolver — copy this shape for "is `codegraph` installed?" (absent binary must warn and continue, per R0.6, rather than `exit 1` as `resolve_binary` does):
```bash
resolve_binary() {
    if command -v my-kitty >/dev/null 2>&1; then
        echo "my-kitty"
        return
    fi
    if [[ -x "${HOME}/.local/bin/my-kitty" ]]; then
        echo "${HOME}/.local/bin/my-kitty"
        return
    fi
    ...
}
```
7. **Env-var-driven behavior is read with `${VAR:-}` + `== "1"` comparison** — `uninstall.sh:45-47, 82`:
```bash
    [[ "${KEEP_BACKUPS:-}" == "1" ]] && flags+=" --keep-backups"
```
```bash
    if [[ "${KITTI_FORCE:-}" == "1" ]]; then
        log "KITTI_FORCE=1 set; skipping interactive confirm"
        return
    fi
```
This is the in-style way to give the pre-push guard a documented escape hatch (if the plan wants one) and to make the hooks test-controllable from pytest's `env=`.
8. **Comment density: high, and comments justify decisions with evidence references.** `setup.sh:46-52` cites probe IDs and a dated incident; `uninstall.sh:98` carries an inline `# shellcheck disable=SCxxxx — reason.` The `merge-base --is-ancestor` logic in `pre-push` should carry the same treatment — a comment citing `01-RESEARCH.md` Pattern 2 and the zero-SHA new-branch exception.
9. **shellcheck is expected to run** (evidenced by the `disable` directive). `pyproject.toml`'s `[tool.ruff] src = ["src", "tests", "tools"]` covers `tools/` for Python only; no shell linter is wired into `make validate` today — the planner may note this as a gap but adding one is out of scope.

---

### `Makefile` — `hooks:` target (config glue)

**Analog:** the existing targets in `/var/home/bazzite/git/personal/kitty-setup/Makefile` (tracked). House style, verbatim:
```makefile
# kitty-setup — thin glue. Each target is at most five lines including its banner.
# Anything longer dispatches into tools/ or a [project.scripts] entry point.
# See docs/agent-iteration.md (R3 — Makefile is thin).

.DEFAULT_GOAL := help
.PHONY: help install setup clean doctor test uninstall prune
```
```makefile
doctor:
	@my-kitty doctor

test:
	@uv run pytest tests/
```
```makefile
uninstall:
	@KEEP_BACKUPS="$(KEEP_BACKUPS)" KEEP_CONFIG="$(KEEP_CONFIG)" KEEP_KITTY="$(KEEP_KITTY)" ./tools/uninstall.sh
```
Invariants for a new `hooks:` target: (a) add `hooks` to the `.PHONY` list; (b) add a `@echo "  hooks   …"` line to the `help:` block — every existing target has exactly one help line, and `help` is `.DEFAULT_GOAL`, so omitting it makes the target invisible; (c) recipe lines are prefixed `@` (silent) and are one command; (d) env-var pass-through uses the `VAR="$(VAR)" ./tools/x.sh` form shown above; (e) ≤5 lines per target, tab-indented (real tabs).

---

### `tests/unit/test_git_hooks.py` (test, subprocess + disposable filesystem)

**Analogs (three, each contributing a different piece):**
- `/var/home/bazzite/git/personal/kitty-setup/tests/conftest.py` — the `KITTI_INTEGRATION` gate and the `scratch_dir` fixture (tracked)
- `/var/home/bazzite/git/personal/kitty-setup/tests/integration/test_h21_doctor_remote_control.py` — a self-contained, subprocess-driven integration test with module-private `_helpers` (tracked, 102 lines)
- `/var/home/bazzite/git/personal/kitty-setup/tests/integration/_kitty_subprocess.py` — the extracted shared-helper module pattern (tracked, 151 lines)

**Gating idiom — there is NO decorator and NO `pytest.mark.integration` in use.** Gating is entirely path-based and centralized in `tests/conftest.py:44-53`:
```python
def pytest_collection_modifyitems(config: pytest.Config, items: list[pytest.Item]) -> None:
    """Skip ``tests/integration/`` items unless ``KITTI_INTEGRATION=1`` is set."""
    del config
    if os.environ.get(INTEGRATION_ENV_VAR) == "1":
        return
    skip = pytest.mark.skip(reason=f"set {INTEGRATION_ENV_VAR}=1 to run integration tests")
    integration_dir = REPO_ROOT / "tests" / "integration"
    for item in items:
        if str(item.path).startswith(str(integration_dir)):
            item.add_marker(skip)
```
with `tests/conftest.py:18` `INTEGRATION_ENV_VAR = "KITTI_INTEGRATION"`. **Consequence for the planner: placing the file at `tests/integration/test_git_hooks.py` auto-gates it — add nothing.** But `pyproject.toml` declares a marker `"integration: requires KITTI_INTEGRATION=1 and a real kitty install"` that no integration test actually applies (`grep pytest.mark tests/integration/*.py` → only a `parametrize` hit), so do not add `@pytest.mark.integration` "for consistency"; it would be the only such usage. Second consequence worth flagging: git-hook tests need **no kitty and no `KITTI_INTEGRATION` semantics** (they only need `git`) — yet living in `tests/integration/` means they are skipped by default and excluded from `make test`'s effective coverage. A verify command aimed at `tests/integration/test_git_hooks.py` **silently skips unless `KITTI_INTEGRATION=1` is exported**. The planner must either (a) require `KITTI_INTEGRATION=1` in the verify command, or (b) consciously decide these belong in `tests/unit/` (fast, hermetic, no kitty) and say so. Do not leave this ambiguous — an all-skipped run reports green.

> **RESOLVED 2026-09-23 — the planner chose (b): `tests/unit/test_git_hooks.py`.** Every other reference
> to this file in this document was corrected to `tests/unit/` on 2026-09-23 after the cross-AI review
> (`56f9df1`) noted that four of them (`:18`, `:280`, `:523`, `:549`) still carried the pre-decision
> `tests/integration/` path while the plans and `01-VALIDATION.md` correctly said `tests/unit/`. This
> document is loaded as `@context` by both hook plans, so a stale heading was the first thing an
> executor would read about where the file lives. The paragraph above is deliberately left in its
> original wording, because it is the record of a real choice and its reasoning — the two
> `tests/integration/` mentions in it are the *rejected* option, not a stale path.

**Fixture style — pytest fixtures + `contextlib.contextmanager`, and `tmp_path`, NOT `tempfile.TemporaryDirectory`.** `grep -rn "TemporaryDirectory" tests/` returns **zero hits** across the whole suite; every disposable-filesystem test takes pytest's `tmp_path: Path` or the `scratch_dir` fixture. VALIDATION.md and RESEARCH.md both say "`tempfile.TemporaryDirectory`" — that is the research's own sandbox vocabulary, not this repo's. **Recommend `tmp_path` to match house style** (it is auto-cleaned, and pytest retains the last few runs' dirs for post-mortem, which is strictly better for debugging a git-hook failure). `tests/conftest.py:87-92` is the derived-scratch pattern to copy for a `git_repo` fixture:
```python
@pytest.fixture()
def scratch_dir(tmp_path: Path) -> Iterator[Path]:
    """Yield a freshly created scratch directory inside pytest's tmp_path."""
    target = (tmp_path / "scratch").resolve()
    target.mkdir(parents=True, exist_ok=True)
    yield target
```
Note: bare `@pytest.fixture()` with empty parens, `Iterator[Path]` return type, `yield`.

For a process with setup **and** teardown, the house form is a module-private `@contextlib.contextmanager` used in a `with` block inside the test, not a fixture — `test_h21_doctor_remote_control.py:49-76`:
```python
@contextlib.contextmanager
def _spawn_kitty(conf_path: Path, scratch: Path) -> Iterator[int]:
    env = dict(os.environ)
    env.pop("KITTY_LISTEN_ON", None)
    proc = subprocess.Popen(  # noqa: S603 — trusted paths
        [...],
        env=env,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    try:
        yield proc.pid
    finally:
        if proc.poll() is None:
            proc.send_signal(signal.SIGTERM)
            ...
```
A `bare_remote` / `clone` pair for the push tests fits this shape (`try: yield paths / finally: cleanup`). Also note `# noqa: S603 — trusted paths` and `# noqa: S108` (`test_h21_doctor_remote_control.py:53, 74, 80`): bandit/ruff security rules are suppressed **inline with a trailing justification**, which is the only sanctioned suppression form given `.claude/conventions.md:22-24` ("Never silence findings with `# noqa` … if a tool is wrong, configure it explicitly with rationale"). A `test_git_hooks.py` calling `subprocess.run(["git", ...])` will trip S603/S607 — carry the same `# noqa: S603 — trusted git binary` style.

**Module docstring shape** — every test module opens with a multi-paragraph docstring naming what is materialised, why this shape was chosen over the alternative, and the gate. `test_h21_doctor_remote_control.py:1-16`:
```python
"""H21 — end-to-end doctor remote-control reachability check.

Materialises a fake ``ConfigPaths`` rooted at ``tmp_path/home`` carrying a
verbatim copy of ``config/kitty/remote-control.conf``, spawns a raw kitty
process pointing at the same config ...

Cannot use ``KittySession`` here: the harness passes ``--listen-on=<sock>``
on the CLI, which overrides the config's ``listen_on``. h21 needs the
config-level surface, so it spawns raw subprocess (same shape as
``test_h21_remote_control_foundation.py``).

Gated by ``KITTI_INTEGRATION=1`` per ``tests/conftest.py``.
"""
```
Then, invariably: `from __future__ import annotations`, stdlib imports, `REPO_ROOT = Path(__file__).resolve().parents[2]`, and `Final`-annotated module constants (`test_h21_doctor_remote_control.py:18-34`):
```python
from __future__ import annotations

import contextlib
import os
import signal
import subprocess
import time
from collections.abc import Iterator
from pathlib import Path
from typing import Final

from kitty_setup import config_updater, doctor

REPO_ROOT = Path(__file__).resolve().parents[2]
REMOTE_CONTROL_CONF: Final[Path] = REPO_ROOT / "config" / "kitty" / "remote-control.conf"
KITTY: Final[Path] = Path.home() / ".local" / "kitty.app" / "bin" / "kitty"
SOCKET_BUDGET_S: Final[float] = 5.0
```
For `test_git_hooks.py` the equivalents are `REPO_ROOT`, `HOOKS_DIR: Final[Path] = REPO_ROOT / "tools" / "hooks"`, and a `GIT_BUDGET_S`-style timeout constant. Note `parents[2]` for files in `tests/integration/` (vs `parents[1]` in `tests/conftest.py:19`).

**Copy-the-artifact-under-test-into-the-sandbox pattern** — `test_h21_doctor_remote_control.py:37-46` reads the real tracked config and writes a verbatim copy into `tmp_path`:
```python
def _materialise_paths(tmp_path: Path) -> config_updater.ConfigPaths:
    """Build a ``ConfigPaths`` whose ``payload_dir`` carries our ``remote-control.conf``."""
    home = tmp_path / "home"
    home.mkdir()
    paths = config_updater.ConfigPaths.for_user(home=home)
    paths.payload_dir.mkdir(parents=True)
    (paths.payload_dir / "remote-control.conf").write_text(
        REMOTE_CONTROL_CONF.read_text(encoding="utf-8"), encoding="utf-8"
    )
    return paths
```
Direct analogue: copy (or `shutil.copytree`) the real `tools/hooks/` into the sandbox repo and `git config core.hooksPath tools/hooks` there — so the test exercises the **tracked** hook files, not a fixture re-implementation. Always pass `encoding="utf-8"` explicitly to `read_text`/`write_text`; and copy mode bits (`shutil.copy2` / `chmod 0o755`) since git will not execute a non-executable hook.

**`subprocess.run` call + exit-code/stderr assertion shape** — the canonical end-to-end example, `test_h25_scene_launcher.py:397-422`:
```python
        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "kitty_setup.cli",
                ...
            ],
            capture_output=True,
            text=True,
            check=False,
            timeout=15,
            env=env,
        )
        assert result.returncode == 0, (
            f"my-kitty scene launch failed (rc={result.returncode}); "
            f"stderr={result.stderr!r}"
        )
```
and the shorter helper form, `_kitty_subprocess.py:119-130`:
```python
def kitten_call(socket: Path, *args: str, timeout: float = 5.0) -> subprocess.CompletedProcess[str]:
    """Run `kitten @ --to=unix:<socket> <args…>` and return the CompletedProcess."""
    env = dict(os.environ)
    env.pop("KITTY_LISTEN_ON", None)
    return subprocess.run(
        [str(KITTEN), "@", f"--to=unix:{socket}", *args],
        capture_output=True,
        text=True,
        check=False,
        timeout=timeout,
        env=env,
    )
```
Invariants to replicate for a `_git(*args, cwd)` helper: list-form argv (never `shell=True`); `capture_output=True, text=True, check=False` (the test asserts on `returncode`, it never relies on `CalledProcessError`); an explicit `timeout=`; `env=dict(os.environ)` copied then mutated, never mutating `os.environ`; return type annotated `subprocess.CompletedProcess[str]`. Assertion form: `assert result.returncode == <n>, f"… (rc={result.returncode}); stderr={result.stderr!r}"` — the `!r` on stderr is house style. `_kitty_subprocess.py:136` shows the terse variant: `assert result.returncode == 0, f"kitten @ ls failed: {result.stderr}"`.
For the negative control (fast-forward push allowed) and the rejection case, assert on **both** `returncode` and a substring of `stderr` — a rejection test that only checks non-zero cannot distinguish "hook rejected" from "hook crashed"; `_kitty_subprocess.py:140-151` (`get_color`) shows the house habit of parsing output line-by-line rather than trusting exit codes alone.

**Shared-helper placement:** if `test_git_hooks.py` needs helpers reused by a second module, extract to `tests/integration/_git_subprocess.py` — the underscore prefix is the deliberate collection-suppression mechanism, documented at `_kitty_subprocess.py:1-13`:
```python
"""Shared subprocess helpers for raw-kitty integration tests.

Extracted from `test_h22_window_title.py` (originally inline as `_draft_conf` /
`_spawn_kitty` / ...) so the h23 styling tests can reuse the same code path.
Pytest does not collect this module because the leading underscore in the
filename suppresses collection.
"""
```
For a single module, keep helpers module-private (`_name`) inline, as `test_h21_doctor_remote_control.py` does. **On CONTEXT.md's note that `tests/conftest.py` and `tests/integration/_helpers.py` duplicate helpers — confirmed:** `clear_variant_name()` and `copy_clear_payload()` exist verbatim in both (`tests/conftest.py:23-41` and `tests/integration/_helpers.py:18-37`), differing only in `parents[1]` vs `parents[2]`. `_helpers.py:1-6` states the rationale ("Kept out of conftest because conftest contains pytest fixtures + the KITTI_INTEGRATION gate, and we want callable helpers importable from test modules without fixture indirection"). The convention to follow: **callable helpers → `_*.py` module; pytest fixtures + gating → `conftest.py`.** Do not add git helpers to `conftest.py`. De-duplicating the existing pair is out of Phase 1 scope (it is `src`/test hygiene, not governance) — do not let it into a plan without a decision.

**Type/quality rules that apply (from `.claude/conventions.md`):** type hints on every function (`:18-19`), pyright strict with no suppressions, 100-column black/ruff (`pyproject.toml [tool.black] line-length = 100`), `from __future__ import annotations` at the top of every module, and tests invoked as `uv run pytest …` never bare `pytest`.

---

### `docs/requirements.md`, `docs/propossal_roadmap.md` — FROZEN banner insertion

**Analogs:** each other. Both open with the identical two-element shape — H1, blank line, then a `Date: …` provenance line. **No front matter, no blockquote, no badge.** First lines verbatim:

`docs/requirements.md:1-3`
```markdown
# kitty-scenes — Requirements (high-level)

Date: 2026-05-01. Clean restart. Hypothesis-driven, scripts before integration. Linux + macOS parity.
```
`docs/propossal_roadmap.md:1-3`
```markdown
# kitty-scenes — Proposal & Roadmap

Date: 2026-05-01. Companion to [requirements.md](requirements.md). Captures the strategic decisions for the restart and the staged path to ship.
```
(Both are 45 / 65 lines total; both still titled `kitty-scenes`, i.e. the pre-rename name — further evidence they are history.)

**House precedent for a prominent inline callout:** the repo does use `>`-blockquote banners in planning docs — e.g. `01-VALIDATION.md:14-17` and this file's own peers. But **neither `docs/` file nor `README.md` nor `CLAUDE.md` uses front matter or an opening blockquote.** The lowest-friction in-style banner is therefore: **after the H1, before the `Date:` line**, a single blockquote paragraph. This preserves the H1-first invariant every markdown file in the repo shares (`README.md:1`, `docs/agent-iteration.md:1`, `CLAUDE.md:1`, `.claude/conventions.md:1` — all `# Title` on line 1) while making the banner the first prose a reader meets:
```markdown
# kitty-scenes — Requirements (high-level)

> **FROZEN — history only; source of truth is `.planning/`.**
> Superseded by `.planning/REQUIREMENTS.md`. Retained for provenance; do not edit.

Date: 2026-05-01. ...
```
D-04 fixes the phrase "FROZEN — history only; source of truth is `.planning/`"; VALIDATION.md line 55 greps for the literal `FROZEN — history only`, so the banner **must contain that exact substring including the em dash** — the planner should not paraphrase it to "FROZEN - history only". Placement (top-of-file vs after H1) is explicitly Claude's Discretion; the H1-first recommendation above is the style-consistent choice.

### `.planning/legacy/openspec/README.md` — NEW, no analog to migrate

`openspec/` contains only `changes/`, `specs/`, and `config.yaml` — **there is no `openspec/README.md` today**, so this is authored from scratch (D-04 already says "(new)"). Use the same shape as the two docs above: H1 (e.g. `# OpenSpec (frozen)`), the FROZEN blockquote with the exact substring, then a short provenance paragraph in the `Date: …` register explaining what the tree was, that it was archived with `--skip-specs`, that `openspec validate --all --strict` is knowingly not green (per `01-RESEARCH.md` Pitfall 3), and where the live source of truth now is.

### `CLAUDE.md` (modified) and `.planning/config.json` (modified)

`CLAUDE.md` becomes exactly `@AGENTS.md` plus a single trailing newline: **no comment line, no H1, no blank line before, no extra blank lines after.**

> **Corrected 2026-09-23 after the cross-AI review (`56f9df1`).** This paragraph previously
> prescribed `test "$(cat CLAUDE.md)" = '@AGENTS.md'` as the proof and called the file "one line of
> nine characters". Both were wrong:
> - **The test does not enforce one line.** `$(…)` strips *every* trailing newline, so
>   `printf '@AGENTS.md\n\n\n'` — a three-line file — passes it. Execution confirmed this. The
>   `max_lines: 1` artifact constraint was therefore ungated. The gate is now
>   `printf '@AGENTS.md\n' | cmp -s - CLAUDE.md`, a byte-for-byte comparison that accepts exactly one
>   trailing newline (`01-04-PLAN.md` task 3).
> - **`@AGENTS.md` is ten characters, not nine** (`printf '@AGENTS.md' | wc -c` → 10). Every
>   character-count claim has been removed from the plans rather than corrected, because `cmp` already
>   asserts the exact bytes and a hand-maintained count is one more thing to get wrong.

`.planning/config.json` — current value at **line 69** (not line 62 as RESEARCH.md states):
```json
  "claude_md_path": "./CLAUDE.md",
```
Two-space indent, `./`-prefixed relative path, trailing comma (mid-object). New value `"./AGENTS.md"` preserves all three.

---

## Shared Patterns

### Shell prelude (applies to all three files under `tools/hooks/`)
**Source:** `tools/setup.sh:1-21`, `tools/uninstall.sh:1-17`
**Apply to:** `pre-push`, `post-commit`, `post-checkout`
```bash
#!/usr/bin/env bash
# tools/hooks/<name> — <one-line purpose>. Invoked by git on <event>.
# <argv/stdin contract>. See AGENTS.md ("Stack") for why this is shell.

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "${REPO_ROOT}"

log() { printf '[<name>] %s\n' "$*"; }
```
(`../..` instead of `..` because hooks sit one level deeper than `tools/*.sh`.)

### Error/abort pattern
**Source:** `tools/setup.sh:33-36`, `tools/uninstall.sh:38-41`
**Apply to:** `pre-push` (the only hook allowed to abort)
`log "ERROR: <what>"`, optional space-aligned second `log` line with remediation, then `exit 1`. Non-blocking hooks (`post-commit`, `post-checkout`) must instead use `log "warning: <what> (non-blocking)"` and fall through to `exit 0` (R0.6).

### Env-var escape hatch / test control
**Source:** `tools/uninstall.sh:82-85` (`KITTI_FORCE=1`)
**Apply to:** any hook the pytest harness must steer
```bash
    if [[ "${KITTI_FORCE:-}" == "1" ]]; then
        log "KITTI_FORCE=1 set; skipping interactive confirm"
        return
    fi
```
The `KITTI_*` prefix is the repo's env-var namespace (`KITTI_FORCE`, `KITTI_INTEGRATION`) — new hook env vars should follow it.

### Integration-test gate
**Source:** `tests/conftest.py:18, 44-53`
**Apply to:** `tests/unit/test_git_hooks.py`
Path-based; nothing to add in the test file. But every verify command for it must export `KITTI_INTEGRATION=1` or the test silently skips (green-but-empty). See the flagged decision above.

### subprocess invocation + assertion
**Source:** `tests/integration/_kitty_subprocess.py:119-137`, `tests/integration/test_h25_scene_launcher.py:397-422`
**Apply to:** every `git` call in `test_git_hooks.py`
List argv, `capture_output=True, text=True, check=False, timeout=<n>`, copied `env`, return `subprocess.CompletedProcess[str]`; assert `returncode` with an f-string message embedding `rc=` and `stderr={...!r}`; inline `# noqa: S603 — <reason>` for the bandit finding.

### Makefile target
**Source:** `Makefile:6` (`.PHONY`), `Makefile:9-20` (`help:`), `Makefile:31-38`
**Apply to:** the `hooks:` wiring target
Add to `.PHONY`, add one `@echo` help line, one `@`-prefixed tab-indented command, ≤5 lines.

### Markdown document opening
**Source:** `README.md:1`, `docs/requirements.md:1-3`, `docs/agent-iteration.md:1-3`, `CLAUDE.md:1-5`, `.claude/conventions.md:1-5`
**Apply to:** `AGENTS.md`, the three banner targets
H1 on line 1, blank line, then an orienting paragraph (provenance date for `docs/`, remit statement for instruction files). No YAML front matter anywhere in `docs/`, `README.md`, or instruction files — front matter appears only inside `.planning/phases/*` artifacts.

---

## No Analog Found

| File | Role | Data Flow | Reason |
|------|------|-----------|--------|
| `CLAUDE.md` (as reduced 1-line stub) | config shim | — | Nothing in the repo is a single-line import file; the form is dictated by Claude Code's `@path` syntax, not by a local pattern. `01-RESEARCH.md:307-311` is the reference. |
| `tools/hooks/*` — the *domain logic* (pre-push stdin protocol, `merge-base --is-ancestor`, zeroed-prev-HEAD detection, `codegraph` invocation) | middleware | event-driven | No git hook, and no `codegraph` call, exists anywhere in this repo (`tools/` has exactly two files; neither touches git). The **style** comes from `tools/*.sh` as mapped above; the **logic** must come from `01-RESEARCH.md` Patterns 1–3 (lines 162-232), all of which were live-verified. |
| `tests/unit/test_git_hooks.py` — the git-sandbox mechanics | test | file-I/O | No existing test creates a git repo, and `grep -rn TemporaryDirectory tests/` → 0 hits. The harness *shape* comes from `test_h21_doctor_remote_control.py`; the git command sequences come from `01-RESEARCH.md`'s reproduced sandbox transcripts (Patterns 1-3). |

---

## Metadata

**Analog search scope:** repo root (`CLAUDE.md`, `Makefile`, `README.md`, `.gitignore`, `pyproject.toml`), `tools/`, `tests/` (all 44 files enumerated; 3 read in full, 2 read in part), `docs/` (openings of 3 files), `.claude/`, `.planning/config.json`, `openspec/` (top level).
**Files scanned:** ~60 enumerated; 9 read.
**Tracked-source verification:** `git ls-files --` run over all 10 named analog paths; all returned tracked. No `.gsd/capabilities/` or other gitignored mirror path appears in this document.
**Pattern extraction date:** 2026-09-23

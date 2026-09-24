---
phase: 02-defect-remediation
plan: 03
subsystem: uninstall
status: complete
tags: [R1.2, R1.3, uninstall, makefile, bootstrap-shell, tdd]
requires: [02-02]
provides:
  - "`tools/uninstall.sh` `log()` writes to stderr, so `$(resolve_binary)` captures only a binary name; the legacy branch runs and the error branch is readable"
  - "the confirm prompt's will-remove list names `~/.local/share/kitty-setup/my-kitty-completion.{bash,zsh}` whenever `KEEP_KITTY` is unset"
  - "`make clean` passes `--keep-kitty --keep-backups`; its help line and README.md say `(keeps kitty + backups)`"
  - "pytest-subprocess regression module for the bootstrap script with a fully replaced env (D-07)"
  - "text-level Makefile test: help-line keep-set equals the recipe's `--keep-*` suffix set"
affects: [02-07]
tech-stack:
  added: []
  patterns:
    - "shell entry points tested from pytest with `subprocess.run(env=<complete replacement dict>, timeout=, cwd=)`; the module never reads `os.environ`"
    - "behavioural Makefile coverage by parsing the recipe's own flags and dispatching them through `cli.main`"
key-files:
  created:
    - tests/unit/test_tools_uninstall_sh.py
    - tests/unit/test_makefile_targets.py
  modified:
    - tools/uninstall.sh
    - Makefile
    - README.md
    - pyproject.toml
    - tests/unit/test_installer_uninstall.py
decisions:
  - "D-06 widened from `resolve_binary` to the whole script: `log()` itself writes to stderr, so every one of its seven call sites moves, and no future `$(...)` capture of a helper can be poisoned"
  - "`|| true` kept on `make clean`, with its reason in a comment above the target: the safe reset verb must succeed on a machine with nothing installed, including one without `my-kitty`"
  - "\"binary\" dropped from the `clean` help line rather than special-cased: no uninstall verb removes the `my-kitty` binary (`cli.py:64-65`), so the `(keeps ...)` items are exactly the recipe's `--keep-*` suffixes"
  - "the recipe-driven uninstall case dispatches through `cli.main([\"uninstall\", *flags])` instead of `cli._build_parser().parse_args(...)`: the same real parser plus the real dispatch, and no pyright `reportPrivateUsage` error"
  - "S603/S607 for the new subprocess module are a scoped per-file ruff entry with rationale, not a `# noqa`"
metrics:
  duration: "~35 min"
  completed: 2026-09-24
actuals:
  tokens: 10000
  tasks: 2
  commits: 2
plan_head_before: ca1df1a158c298a27211d576936685cd637644e0
---

# Phase 2 Plan 03: `tools/uninstall.sh` diagnostics go to stderr, and `make clean` keeps what it promises (summary)

Both uninstall-surface defects are fixed. `tools/uninstall.sh` had been logging into the stdout
that `$(resolve_binary)` captures. The legacy-binary branch therefore exited **127**, trying to
execute the log line plus the binary name, and the error branch exited 1 with **nothing on
stderr**. `log()` now writes to stderr. The confirm prompt also lists the completion file that
`my-kitty uninstall` removes. `make clean` used to forward no flag and so deleted `kitty.app`, the
symlink, the desktop entry and every backup. It now passes `--keep-kitty --keep-backups`, and its
help line (and the README's copy) promises exactly `kitty + backups`. A test now enforces that the
help line and the recipe agree.

Scope anchor (pre-work `HEAD`): `ca1df1a158c298a27211d576936685cd637644e0`.

## Commits

| Kind | SHA | Subject |
|------|-----|---------|
| RED | `06f59bd` | `test(02-03): RED — uninstall.sh diagnostics on stderr, prompt lists completion file, make clean keeps kitty + backups (R1.2, R1.3)` |
| GREEN | (this commit) | `feat(02-03): GREEN — …` |

The RED commit holds only the three test modules. GREEN holds the script, `Makefile`, `README.md`,
`pyproject.toml` and this SUMMARY, and no file under `tests/`. GREEN was amended once while
unpushed, only to record the commit-dependent gate results (g13, g16, g17) and the Self-Check
in this file. RED was never amended.

## Step 0: h31 reproduction, before any test or source edit (`tmp/h31-uninstall-sh/`)

The driver is `tmp/h31-uninstall-sh/run.py`, run with
`timeout 120 uv run python tmp/h31-uninstall-sh/run.py`. It uses a complete replacement env:
`HOME=$SANDBOX/home` and `PATH=$SANDBOX/bin:/usr/bin:/bin`, with stubs that echo their argv. It
never reads `os.environ`. Neither `/usr/bin` nor `/bin` holds `my-kitty*`. The artefacts are
`repro.md`, `run.py` and `actual.json`. The step-0 run was also kept as `run-before.txt` and
`actual-before.json`. `tmp/` is gitignored, so the transcripts are quoted here.

**Before the fix (step 0, at `ca1df1a`)**, verbatim. `<worktree>` shortens the absolute worktree path:

```
=== legacy-only (stub my-kitty-setup)
env: {'HOME': '$SANDBOX/home', 'PATH': '$SANDBOX/bin:/usr/bin:/bin', 'KITTI_FORCE': '1'}
exit=127
--- stdout ---
[uninstall] KITTI_FORCE=1 set; skipping interactive confirm
--- stderr ---
<worktree>/tools/uninstall.sh: line 99: $'[uninstall] using legacy binary \'my-kitty-setup\'; run \'uv tool uninstall my-kitty-setup\' after this completes\nmy-kitty-setup': command not found
=== no binary anywhere (error branch)
env: {'HOME': '$SANDBOX/home', 'PATH': '$SANDBOX/bin:/usr/bin:/bin', 'KITTI_FORCE': '1'}
exit=1
--- stdout ---
[uninstall] KITTI_FORCE=1 set; skipping interactive confirm
--- stderr ---

=== preferred my-kitty
env: {'HOME': '$SANDBOX/home', 'PATH': '$SANDBOX/bin:/usr/bin:/bin', 'KITTI_FORCE': '1'}
exit=0
--- stdout ---
[uninstall] KITTI_FORCE=1 set; skipping interactive confirm
STUB $SANDBOX/bin/my-kitty invoked: uninstall
[uninstall] done
--- stderr ---

=== prompt answered n
env: {'HOME': '$SANDBOX/home', 'PATH': '$SANDBOX/bin:/usr/bin:/bin'}
exit=1
--- stdout ---
About to remove (with no --keep-* flags):
  - kitty config block from ~/.config/kitty/kitty.conf
  - payload directory ~/.config/kitty/kitty-setup/
  - all kitty.conf.bak.* backup files
  - ~/.local/kitty.app/
  - ~/.local/bin/kitty symlink
  - ~/.local/share/applications/kitty.desktop

After this completes, run `uv tool uninstall my-kitty` to remove the binary itself.
Continue? [y/N] [uninstall] aborted
--- stderr ---

=== prompt answered n, KEEP_KITTY=1
env: {'HOME': '$SANDBOX/home', 'PATH': '$SANDBOX/bin:/usr/bin:/bin', 'KEEP_KITTY': '1'}
exit=1
--- stdout ---
About to remove (preserving: kitty):
  - kitty config block from ~/.config/kitty/kitty.conf
  - payload directory ~/.config/kitty/kitty-setup/
  - all kitty.conf.bak.* backup files

After this completes, run `uv tool uninstall my-kitty` to remove the binary itself.
Continue? [y/N] [uninstall] aborted
--- stderr ---
```

**After the fix**, verbatim. The only lines dropped are uv's own "Building/Installed" preamble,
which appeared because `pyproject.toml` changed:

```
=== legacy-only (stub my-kitty-setup)
env: {'HOME': '$SANDBOX/home', 'PATH': '$SANDBOX/bin:/usr/bin:/bin', 'KITTI_FORCE': '1'}
exit=0
--- stdout ---
STUB $SANDBOX/bin/my-kitty-setup invoked: uninstall
--- stderr ---
[uninstall] KITTI_FORCE=1 set; skipping interactive confirm
[uninstall] using legacy binary 'my-kitty-setup'; run 'uv tool uninstall my-kitty-setup' after this completes
[uninstall] done
=== no binary anywhere (error branch)
env: {'HOME': '$SANDBOX/home', 'PATH': '$SANDBOX/bin:/usr/bin:/bin', 'KITTI_FORCE': '1'}
exit=1
--- stdout ---

--- stderr ---
[uninstall] KITTI_FORCE=1 set; skipping interactive confirm
[uninstall] ERROR: neither my-kitty nor my-kitty-setup found on PATH or in ~/.local/bin
[uninstall]        run 'make install' first, or remove manually
=== preferred my-kitty
env: {'HOME': '$SANDBOX/home', 'PATH': '$SANDBOX/bin:/usr/bin:/bin', 'KITTI_FORCE': '1'}
exit=0
--- stdout ---
STUB $SANDBOX/bin/my-kitty invoked: uninstall
--- stderr ---
[uninstall] KITTI_FORCE=1 set; skipping interactive confirm
[uninstall] done
=== prompt answered n
env: {'HOME': '$SANDBOX/home', 'PATH': '$SANDBOX/bin:/usr/bin:/bin'}
exit=1
--- stdout ---
About to remove (with no --keep-* flags):
  - kitty config block from ~/.config/kitty/kitty.conf
  - payload directory ~/.config/kitty/kitty-setup/
  - all kitty.conf.bak.* backup files
  - ~/.local/kitty.app/
  - ~/.local/bin/kitty symlink
  - ~/.local/share/applications/kitty.desktop
  - ~/.local/share/kitty-setup/my-kitty-completion.{bash,zsh}

After this completes, run `uv tool uninstall my-kitty` to remove the binary itself.
Continue? [y/N] 
--- stderr ---
[uninstall] aborted
=== prompt answered n, KEEP_KITTY=1
env: {'HOME': '$SANDBOX/home', 'PATH': '$SANDBOX/bin:/usr/bin:/bin', 'KEEP_KITTY': '1'}
exit=1
--- stdout ---
About to remove (preserving: kitty):
  - kitty config block from ~/.config/kitty/kitty.conf
  - payload directory ~/.config/kitty/kitty-setup/
  - all kitty.conf.bak.* backup files

After this completes, run `uv tool uninstall my-kitty` to remove the binary itself.
Continue? [y/N] 
--- stderr ---
[uninstall] aborted
```

This also gives the will-remove list before and after, with and without `KEEP_KITTY=1`. The
completion line appears only when `KEEP_KITTY` is unset. The `[uninstall] aborted` line also moved
to stderr, as part of the whole-script widening below. The `Continue? [y/N] ` prompt is a plain
`printf` and stays on stdout.

**Mechanism.** `exit 1` inside `$( )` exits only the subshell. The script dies because
`set -euo pipefail` (`:12`) propagates the failing assignment at `:97`. That is why the error
branch exited 1 silently.

## RED state, proven from the RED commit's own tree

This used the same materialisation as the plan's RED-state gate: a throwaway index,
`checkout-index` into a temp dir, and the venv's interpreter with `PYTHONPATH=<tree>/src`. The
full output is kept in `tmp/h31-uninstall-sh/red-tree.txt`. Key lines, verbatim:

```
RED=06f59bdfb95078c3b5dd62500c4f359d3baa72c4
FFFFFFFFFFF                                                              [100%]
_____________ test_legacy_binary_branch_forwards_to_my_kitty_setup _____________
>       assert result.returncode == 0, f"stdout={result.stdout!r} stderr={result.stderr!r}"
E       AssertionError: stdout='[uninstall] KITTI_FORCE=1 set; skipping interactive confirm\n' stderr="$REDTREE/t/tools/uninstall.sh: line 99: $'[uninstall] using legacy binary \\'my-kitty-setup\\'; run \\'uv tool uninstall my-kitty-setup\\' after this completes\\nmy-kitty-setup': command not found\n"
E       assert 127 == 0
_____________ test_error_branch_diagnostics_are_visible_on_stderr ______________
E       AssertionError: assert '[uninstall] ERROR: neither my-kitty nor my-kitty-setup found on PATH or in ~/.local/bin' in ''
E        +  where '' = CompletedProcess(args=['bash', '$REDTREE/t/tools/uninstall.sh'], returncode=1, stdout='[uninstall] KITTI_FORCE=1 set; skipping interactive confirm\n', stderr='').stderr
______ test_will_remove_list_names_the_completion_file_unless_keep_kitty _______
E       AssertionError: assert '  - ~/.local/share/kitty-setup/my-kitty-completion.{bash,zsh}' in ['About to remove (with no --keep-* flags):', ...]
____________________ test_clean_help_keep_set_equals_recipe_flag_set ____________
E       AssertionError: assert {'binary', 'kitty'} == set()
FAILED tests/unit/test_tools_uninstall_sh.py::test_legacy_binary_branch_forwards_to_my_kitty_setup
FAILED tests/unit/test_tools_uninstall_sh.py::test_error_branch_diagnostics_are_visible_on_stderr
FAILED tests/unit/test_tools_uninstall_sh.py::test_preferred_binary_wins_over_legacy
FAILED tests/unit/test_tools_uninstall_sh.py::test_home_local_bin_fallback_is_used
FAILED tests/unit/test_tools_uninstall_sh.py::test_keep_env_forwards_as_flag[KEEP_BACKUPS---keep-backups]
FAILED tests/unit/test_tools_uninstall_sh.py::test_keep_env_forwards_as_flag[KEEP_CONFIG---keep-config]
FAILED tests/unit/test_tools_uninstall_sh.py::test_keep_env_forwards_as_flag[KEEP_KITTY---keep-kitty]
FAILED tests/unit/test_tools_uninstall_sh.py::test_will_remove_list_names_the_completion_file_unless_keep_kitty
FAILED tests/unit/test_makefile_targets.py::test_clean_recipe_passes_keep_kitty_and_keep_backups
FAILED tests/unit/test_makefile_targets.py::test_clean_help_keep_set_equals_recipe_flag_set
FAILED tests/unit/test_installer_uninstall.py::test_clean_recipe_flags_keep_kitty_and_backups
11 failed, 8 deselected in 0.12s
pytest status=1
```

**RED counts: 11 failed, 0 passed, 0 errors, 8 deselected. pytest status 1.** This matches the
plan's prototype measurement. Nine named cases, with `keep_env` parametrized ×3. The legacy case
fails at exit **127** and the error branch at exit 1 with empty stderr, both for the documented
reason. `preferred`, `fallback` and the three `keep_env` items fail because the `[uninstall]`
lines sit in stdout around the stub's argv. The recipe-driven uninstall case fails because the
recipe passed no flags, so `cli_uninstall` listed and deleted the backups and called
`remove_kitty_install` and `remove_completion_script`. Those were fakes from the `calls` fixture.

After the fix, the same selector in the working tree gave `11 passed, 8 deselected in 0.06s`, every
case listed as PASSED.

## What was built

**`tools/uninstall.sh`** (+2 −1):
- `:17` `log() { printf '[uninstall] %s\n' "$*" >&2; }`
- `print_will_remove`'s `if [[ "${keep_kitty}" != "1" ]]` block gained
  `printf '  - ~/.local/share/kitty-setup/my-kitty-completion.{bash,zsh}\n'` after the
  desktop-entry line. It sits inside the block because `cli_uninstall` removes the file only
  under `do_kitty`.

**D-06 widened, deliberately.** D-06 says "inside `resolve_binary`". The redirect is on the `log`
function body instead, so all seven call sites move (`:29, :34, :38, :39, :83, :91, :101`). The
script's real stdout is the forwarded `my-kitty uninstall` output, so bootstrap diagnostics belong
on stderr. A future `$(...)` capture of any other helper would otherwise hit the same trap.

**`Makefile`** (the `clean` target was at `:28`, recipe `:29-30`, at `6b26b07`/`ca1df1a`; not the
`:26-28` in `02-CONTEXT.md`):

Before:
```
	@echo "  clean                    strip our config block + wipe ./tmp/ scratch (keeps kitty + binary)"
clean:
	@my-kitty uninstall || true
	@rm -rf tmp/
```
After (comment at `:28`, `clean:` at `:29`, recipe `:30-31`):
```
	@echo "  clean                    strip our config block + payload, wipe ./tmp/ scratch (keeps kitty + backups)"
# `|| true`: the safe reset verb must succeed with nothing installed, even without my-kitty.
clean:
	@my-kitty uninstall --keep-kitty --keep-backups || true
	@rm -rf tmp/
```

- **`|| true` retained.** Without it, `make clean` fails on a machine with nothing to reset, and
  dies with "command not found" when `my-kitty` itself is absent. R1.2 is about *what* `clean`
  removes, not about error propagation. The destructive verb (`make uninstall`) still surfaces
  failures. The reason is the comment above the target, and the recipe stays at two lines.
- **"binary" dropped, not special-cased.** No uninstall verb removes the `my-kitty` binary.
  `cli.py:64-65` says so, and `_SELF_REMOVAL_BANNER` prints the manual `uv tool uninstall` step.
  "binary" is therefore not something `clean` keeps by choice, and it maps to no flag. With it gone,
  the `(keeps …)` items are exactly the recipe's `--keep-*` suffixes, which is what lets
  `clean_help` assert plain set equality. "+ payload" was added because `do_config` removes the
  payload directory as well as the block.
- The target was not renamed. D-04 rejected `purge`.

**`README.md:46`**
- Before: `make clean              # strip our config block + wipe ./tmp/ scratch (keeps kitty + binary)`
- After:  `make clean              # strip our config block + payload, wipe ./tmp/ scratch (keeps kitty + backups)`

**`pyproject.toml`** gained a scoped entry, directly after the `test_git_hooks.py` entry:
```toml
# S603/S607: test_tools_uninstall_sh.py (R1.3, 02-03) runs a fixed argv of `bash` and the tracked
#       tools/uninstall.sh with shell=False and a complete replacement env built from literals and
#       tmp_path values. `bash` is named without an absolute path on purpose: it is resolved from
#       that sandbox PATH, never the developer's. Scoped to this one file for the reason above.
"tests/unit/test_tools_uninstall_sh.py" = ["S603", "S607"]
```
Before the entry, `uv run ruff check` on the module gave exactly:
```
S603 `subprocess` call: check for execution of untrusted input
  --> tests/unit/test_tools_uninstall_sh.py:68:16
S607 Starting a process with a partial executable path
  --> tests/unit/test_tools_uninstall_sh.py:69:13
Found 2 errors.
```
After the entry: `All checks passed!`. No `# noqa` or `type: ignore` was added anywhere. Checked
with `git diff ca1df1a | rg '^\+.*(# noqa|type: ignore)'`, which gave rg exit 1, no match.

**Tests (RED commit):**
- `tests/unit/test_tools_uninstall_sh.py`: six named cases, 8 items. Each builds a `Sandbox`
  (fake `HOME` with an empty `~/.local/bin`, plus a fake `bin`). The single `subprocess.run` passes
  explicit `env=`, `timeout=` and `cwd=`. `env` is built only from literals and `tmp_path`. Every run
  sets `KITTI_FORCE=1` except the will-remove case, which pipes `n\n`. Every success-path case
  asserts stdout is **exactly** the stub's argv line and every `[uninstall]` line is on stderr.
- `tests/unit/test_makefile_targets.py`: `clean_recipe` extracts the tab-indented lines under the
  one `clean:` line. `clean_help` asserts that the `(keeps …)` set equals the recipe's `--keep-*`
  suffix set.
- `tests/unit/test_installer_uninstall.py`: `calls` now also patches and records
  `installer.remove_completion_script`. The new `test_clean_recipe_flags_keep_kitty_and_backups`
  parses the `--keep-*` flags out of the `clean` recipe and runs `cli.main(["uninstall", *flags])`.
  It asserts that no backup was listed or deleted, `config_updater.uninstall` ran once (the block
  was stripped and the payload removed), `remove_kitty_install` was not called, and
  `remove_completion_script` was not called.

**The five artefacts the `--keep-kitty --keep-backups` case proves preserved:** `kitty.app`, the
`~/.local/bin/kitty` symlink, the desktop entry (all three via `remove_kitty_install`), every
`kitty.conf.bak.*` (via `list_backups`/`delete_each`), and the completion file 02-01 wired (via
`remove_completion_script`).

## Gates

Every `<automated>` gate was extracted verbatim from the plan (HTML-unescaped) into a script and run
from the worktree root. The numbering follows the plan's order.

| # | Gate | When run | Exit |
|---|------|----------|------|
| g01 | T1: `log()` one-line stderr form (anchored `rg`) | before RED: 1 (expected); after fix | **0** |
| g02 | T1: `pytest -k 'legacy or error_branch or preferred or fallback or keep_env'` passed, no fail/error | before RED: 1 (expected); after fix | **0** |
| g03 | T1: exactly 2 `.sh` under `tools/`, 0 `.bats` | RED and after fix | **0** |
| g04 | T1: AST sandbox gate (explicit env/timeout/cwd, no `os.environ`/`environb`/`getenv`, `KITTI_FORCE`, no shellcheck) | RED and after fix | **0** |
| g05 | T1: `pytest -k will_remove` passed | before RED: 1 (expected); after fix | **0** |
| g06 | T1: `tmp/h31-uninstall-sh/{repro.md,run.py,actual.json}` exist | RED and after fix | **0** |
| g07 | T2: `clean` recipe (`rg -A3 '^clean:'`) has both flags and `rm -rf tmp/` | before RED: 1 (expected); after fix | **0** |
| g08 | T2: help line and README both end `(keeps kitty + backups)`, neither says "binary" | before RED: 1 (expected); after fix | **0** |
| g09 | T2: `clean` ≤5 recipe lines, defined once | RED and after fix | **0** |
| g10 | T2: `test_makefile_targets.py` exactly `2 passed` | before RED: 1 (expected); after fix | **0** |
| g11 | T2: `pytest test_installer_uninstall.py -k keep_kitty_and_backups` passed | before RED: 1 (expected); after fix | **0** |
| g12 | T2: `make test` ≥ 314 passed, no fail/error | after fix | **0** (385) |
| g13 | Two-commit topology (one `test(02-03)`, one `feat(02-03)`, RED ancestor of GREEN, exactly 2 `(02-03)` from `RED^`) | after GREEN | **0** |
| g14 | RED is tests-only and holds all three modules | after RED | **0** |
| g15 | RED-state: RED tree, pytest status 1, ≥9 failed, nothing passed/errored | after RED | **0** (11 failed) |
| g16 | GREEN has the SUMMARY, `Makefile`, `tools/uninstall.sh`, `README.md`, `pyproject.toml`; script numstat `2 1` | after GREEN | **0** |
| g17 | GREEN holds no path under `tests/` | after GREEN | **0** |

Verification items not already above:
- V1 `rg -q '>&2' tools/uninstall.sh`: **0**.
- V8, the three modules together: **0**, `19 passed`.
- V10, `ruff check` + `black --check` on the two new modules: **0**.

The "before RED" runs happened after the three test modules were written and before any source
edit. g01 and g07-g08 failed then for the documented reason, and g02, g05, g10 and g11 failed on
the RED cases.

## Baselines and lint

`make test`, exit 0. Verbatim tail:
```
SKIPPED [6] tests/integration/test_h25_scene_launcher.py: set KITTI_INTEGRATION=1 to run integration tests
SKIPPED [2] tests/integration/test_scene_fill_tab_e2e.py: set KITTI_INTEGRATION=1 to run integration tests
SKIPPED [4] tests/integration/test_scene_recipe_e2e.py: set KITTI_INTEGRATION=1 to run integration tests
======================= 385 passed, 76 skipped in 8.08s ========================
```
That is 374 at 02-02 plus the 11 new items. The floor is 314.

`make doctor`, exit 0. It is diagnostic and read-only. Its only `kitten @` use is an explicit
`--to=unix:<socket> ls`, and it SKIPped with no running kitty:
```
PASS kitty binary: /home/bazzite/.local/bin/kitty -> kitty 0.49.0 created by Kovid Goyal
PASS symlink: /home/bazzite/.local/bin/kitty -> /var/home/bazzite/.local/kitty.app/bin/kitty
PASS desktop entry: /home/bazzite/.local/share/applications/kitty.desktop
PASS config payload: /home/bazzite/.config/kitty/kitty-setup/kitty-setup.conf
PASS sentinel block: present in /home/bazzite/.config/kitty/kitty.conf
PASS parse check: kitty --debug-config exit=0
PASS bindings: 22 ours, 79 defaults, 0 conflicts
PASS completion: /home/bazzite/.local/share/kitty-setup/my-kitty-completion.bash is current and sourced by the my-kitty block in /home/bazzite/.bashrc
SKIP remote-control: no running kitty
```

The repo has no `make lint` target. The conventions' tools were run repo-wide on the pre-work tree
`ca1df1a` (materialised via a throwaway index) and on the working tree, using the same venv:

| Tool | `ca1df1a` | after | delta |
|------|-----------|-------|-------|
| `ruff check .` findings | 25 | 25 | 0 |
| `black --check .` files to reformat | 10 | 10 | 0 |
| `bandit -c pyproject.toml -r src` issues | 33 | 33 | 0 |
| `pyright` errors | 559 | 559 | 0 |
| `vulture src tests` lines | 15 | 15 | 0 |

Every repo-wide finding predates this plan (R0.11 owns them). Scoped to this plan's files:
`ruff check` and `black --check` are clean on all three test modules. `pyright` reports 0 errors on
the two new modules. `test_installer_uninstall.py` still has its 8 pre-existing errors (lines
169-174, the lambda-typed case), with none added.

## Deviations from Plan

**1. [Rule 3 - Blocking] `cli.main([...])` instead of `cli._build_parser().parse_args([...])`** in
`test_clean_recipe_flags_keep_kitty_and_backups`. Measured with a probe module:
`cli._build_parser()` from a test is a pyright strict `reportPrivateUsage` error (`1 error`), and
the conventions forbid suppressions. `cli.main` builds the same real parser and also runs the
real dispatch (`set_defaults(func=installer.cli_uninstall)`), which is the exact path
`my-kitty uninstall --keep-kitty --keep-backups` takes from `make clean`. The case still reads its
flags from the recipe, fails while the recipe passes none (proven RED above), and cannot pass on
a hand-built namespace. Pyright on the module: 8 errors before and after, all pre-existing.

**2. Gate execution method (no gate was changed).** This agent's worktree guard refuses compound
shell lines that mention `git`, so the gates could not be pasted into a single shell line. Each
`<automated>` block was extracted verbatim from the plan by a script (HTML-unescaped) into its own
file, prefixed only with `cd <worktree>`, and executed. No gate text was edited.

**3. Extra artefacts in `tmp/h31-uninstall-sh/`** beyond the three the plan names: `run-before.txt`,
`run-after.txt`, `actual-before.json` (`actual.json` now holds the after-fix run), `ruff-before.txt`,
`red-worktree.txt`, `red-tree.txt`, `green-worktree.txt`, `make-test.txt` and `make-doctor.txt`.
They are evidence only.

**4. `core.hooksPath` found absolute.** At the start it was
`/var/home/bazzite/git/personal/kitty-setup/tools/hooks`, not the relative `tools/hooks`. It was
reported and not changed from inside the worktree, as instructed. It still resolves to the
main checkout's tracked hooks, and the post-commit hook ran on both commits.

**5. Worktree base reset.** The harness worktree started at `23aeaa1` (no `.planning/`). It was
reset to `gsd/phase-02-defect-remediation` (`ca1df1a`) before any work, as instructed.

## Known limits and notes

- `make clean` is never executed by a test, deliberately (the plan's `<verification>`). The
  behavioural half is the recipe-driven `cli_uninstall` case.
- STATE.md and ROADMAP.md were not updated, following 02-02's precedent. A third `(02-03)` commit
  would break the plan's two-commit topology gate. The orchestrator integrates.
- Real-HOME safety: `ls -la ~/.local/bin/kitty ~/.local/bin/my-kitty ~/.local/share/kitty-setup/`
  was recorded before any work and compared (`diff`) after the RED run and before this commit.
  The two were identical. `~/.local/kitty.app/` and the desktop entry are still present.

## Known Stubs

None.

## Threat Flags

None. T-2-08 (the recipe flags plus the help-vs-recipe set equality plus the behavioural case),
T-2-09 (the AST-gated sandbox), T-2-10 (accepted) and T-2-11 (stderr removes the class) are
mitigated as the register specifies.

## Self-Check: PASSED

The commit-dependent gates g13-g17 were run after the GREEN commit, and again after the one
amend that added this section (unpushed, same subject). Every one exited **0**.
- The two-commit topology holds: `git rev-list --count ca1df1a..HEAD` gives `2`, and
  `git merge-base --is-ancestor 06f59bd HEAD` exits 0.
- `git diff --numstat 06f59bd HEAD -- tools/uninstall.sh` gives `2	1`.
- GREEN's paths are `A .planning/phases/02-defect-remediation/02-03-SUMMARY.md`, `M Makefile`,
  `M README.md`, `M pyproject.toml` and `M tools/uninstall.sh`. None is under `tests/`.
- FOUND: `tests/unit/test_tools_uninstall_sh.py`, `tests/unit/test_makefile_targets.py`,
  `tests/unit/test_installer_uninstall.py`, `tools/uninstall.sh`, `Makefile`, `README.md`,
  `pyproject.toml`.
- FOUND (working tree, gitignored): `tmp/h31-uninstall-sh/{repro.md,run.py,actual.json}`.
- FOUND: RED commit `06f59bd` (`test(02-03)`).

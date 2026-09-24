---
phase: 02-defect-remediation
plan: 02
subsystem: shell-completion
status: complete
tags: [R1.1, completion, zsh, bash, doctor, rc-block, tdd]
requires: [02-01]
provides:
  - "shell-aware rc block body (`_block_body_lines(shell)`) that sources the generated completion file"
  - "zsh block self-initialises compinit and is kept last in ~/.zshrc (move-to-end reason)"
  - "dual-marker upgrade rewrites the retained block (H3)"
  - "doctor completion check: file + exact template + zsh placement + shellcode byte match; SKIP on unsupported shell"
  - "`PathEditResult.manual_lines` with an honest no-completion line for unsupported shells"
  - "cli_install turns a completion-write OSError into one stderr line and exit 1 (E1)"
affects: [02-07, 02-05, 02-09, 02-10]
tech-stack:
  added: []
  patterns:
    - "module `__all__` declares the underscore names doctor and the tests share with install, so pyright strict reads them as public without a suppression"
key-files:
  created:
    - tests/integration/test_completion_e2e.py
  modified:
    - src/kitty_setup/path_integration.py
    - src/kitty_setup/doctor.py
    - src/kitty_setup/installer.py
    - tests/unit/test_path_integration.py
    - tests/unit/test_doctor.py
    - tests/unit/test_installer_completion.py
    - README.md
    - pyproject.toml
decisions:
  - "zsh: both mechanisms together, as the plan measured: a self-init line (`compinit -i`, no -D) in the body and the block kept last in ~/.zshrc; bash stays in place"
  - "The rc names the completion file through `$HOME`, built from `installer.completion_script_path(shell, home=Path('$HOME'))`, so one place knows the filename"
  - "The fd-8 producer check stays out of doctor: a ~100 ms subprocess on every `make doctor`, and integration case I4 covers it deterministically"
  - "`__all__` in path_integration and doctor declares the shared underscore names, holding pyright at zero added errors without suppressions"
  - "S603 for the new e2e module is a scoped per-file ignore in pyproject.toml with its rationale, not a `# noqa` (conventions forbid noqa)"
metrics:
  duration: "~16 min"
  completed: 2026-09-24
actuals:
  tokens: 14000
  tasks: 3
  commits: 2
plan_head_before: da4da2d51f207b320991de662948977b915931cc
---

# Phase 2 Plan 02: The rc block sources the completion file, and doctor checks only what it can prove — Summary

The rc block now differs per shell and sources the completion file `02-01` generates. bash
sources it unguarded. zsh first starts `compinit -i` when `compdef` does not exist yet, then
sources the file behind a `compdef` guard, and install keeps the zsh block last in `~/.zshrc`.
Doctor's completion check now verifies four things: the file exists, the block matches the
exact template, the zsh block is last, and the file's bytes match fresh shellcode. It SKIPs
unsupported shells. **After a real `make install` on this host, `make doctor` exits 0 with
eight PASS and one SKIP.** R1.1 is closed.

Scope anchor (pre-work `HEAD`): `da4da2d51f207b320991de662948977b915931cc`.

## Commits

| Kind | SHA | Subject |
|------|-----|---------|
| RED | `2570b63` | `test(02-02): RED — rc block sources the completion file per shell; doctor checks what it can prove (R1.1)` |
| GREEN | (this commit) | `feat(02-02): GREEN — …` |

The RED commit was amended once while unpushed. Black wrapped one line in
`tests/unit/test_path_integration.py`, and one f-string was shortened below 100 columns. The
commit stayed tests-only, and its RED state was re-proven afterwards (below).

## Task 1 step 0: the pre-edit record (`tmp/h30-argcomplete-static/rc-body.md`)

This was written before any test or source edit, from `da4da2d`, by
`tmp/h30-argcomplete-static/rc_body_probe.py`. Its throwaway homes were deleted afterwards.
Versions: bash `/usr/bin/bash`, zsh `/home/linuxbrew/.linuxbrew/bin/zsh` 5.9.2, argcomplete
`3.6.3`. Verbatim:

````
## 1. The block `path_integration._block_text()` renders today (one body for every shell)

```
# >>> my-kitty PATH >>>
export PATH="$HOME/.local/bin:$PATH"
if command -v register-python-argcomplete >/dev/null 2>&1; then
    eval "$(register-python-argcomplete my-kitty)"
fi
# <<< my-kitty PATH <<<
```

## 2. `doctor._check_completion` today, in a throwaway HOME built by the producers

- SHELL=bash: `PASS completion: helper <worktree>/.venv/bin/register-python-argcomplete; eval line present in <home>/.bashrc`
- SHELL=zsh: `PASS completion: helper <worktree>/.venv/bin/register-python-argcomplete; eval line present in <home>/.zshrc`

## 3. `compdef` matrix

- non-interactive bash, `command -v compdef` exit status: `1`
- zsh -f, no compinit, `command -v compdef` exit status: `1`
- zsh -f, after `autoload -Uz compinit && compinit`, `command -v compdef` exit status: `0`

## 4. zsh position matrix — `${_comps[my-kitty]-<none>}`, two consecutive starts

| shape | start 1 | start 2 | stderr mentions `compdef` |
|---|---|---|---|
| `<guard>` above a plain `compinit` | `<none>` | `<none>` | no |
| `<guard>` after a plain `compinit` | `_python_argcomplete` | `_python_argcomplete` | no |
| `<guard>` last, no `compinit` anywhere | `<none>` | `<none>` | no |
| `<self-init>` above a plain `compinit` | `<none>` | `<none>` | no |
| `<self-init>` last after a `compinit` | `_python_argcomplete` | `_python_argcomplete` | no |
| `<self-init>` last after a framework file that runs `compinit` | `_python_argcomplete` | `_python_argcomplete` | no |
| `<self-init>` last, no `compinit` anywhere | `_python_argcomplete` | `_python_argcomplete` | no |
| `<self-init>` last, followed only by a comment | `_python_argcomplete` | `_python_argcomplete` | no |
````

(Absolute paths are shortened to `<worktree>` and `<home>` here; the file on disk has them in
full.) **The re-measured matrix matches the plan's recorded one cell for cell**, so nothing had
to be stopped and reported. The mechanism taken is therefore the plan's: the self-init line
together with end-of-file placement. Its stated limits are ones doctor cannot see and does not
claim to see: a `compinit` in `~/.zlogin`, a `ZDOTDIR` pointing away from `$HOME`, and an
`exec` line that runs before our block.

## What was built

**`path_integration.py`**
- The four helper-eval constants and the module-level body tuple are gone.
- New `completion_source_line(shell)`, `_block_body_lines(shell)` and `ZSH_COMPINIT_LINE`,
  which is `(( $+functions[compdef] )) || { autoload -Uz compinit && compinit -i; }`.
- `_block_text(shell)` and `_block_body_matches_template(rc_text, bounds, shell)` now take the
  shell.
- New `_block_followed_only_by_comments(rc_text, bounds)`, the placement predicate doctor
  imports.
- One `_render_block` does every write. It splices in place, except for a zsh block with
  something executable after it: that block's lines are removed and it is appended with the
  existing separator rule.
- Rendered bodies:
  - bash: `export PATH="$HOME/.local/bin:$PATH"` / `[ -f "$HOME/.local/share/kitty-setup/my-kitty-completion.bash" ] && . "$HOME/.local/share/kitty-setup/my-kitty-completion.bash"`
  - zsh: the PATH export / `ZSH_COMPINIT_LINE` / `[ -f "…/my-kitty-completion.zsh" ] && command -v compdef >/dev/null 2>&1 && . "…/my-kitty-completion.zsh"`
- **Seven reasons.** The six from before, plus `"moved rc block to end of file"` for a
  current-template zsh block that fails only on placement. A stale zsh block that also needs
  moving reports the rewrite reason.
- **H3.** The dual-marker branch removes the legacy block, re-finds the retained block in the
  spliced text, and puts it through the same check and render as the single-block path. The
  reason stays `"removed duplicate legacy marker"`. Cases 13 and 14 (`eval-body` and
  `path-only-body`) pin it.
- **`manual_lines` (amended D-13, R1.7).** `PathEditResult.manual_lines: tuple[str, ...]`
  defaults to `(EXPORT_LINE,)`. For a shell outside bash and zsh it is the PATH export plus
  `# completion is not set up for <shell>: my-kitty generates completion for bash and zsh
  only`. It never carries a completion line in another shell's syntax, because this project
  generates no script for fish or tcsh, so no source line would be correct.

**`installer.py`**
- `_print_path_result` now reads `'; '.join(result.manual_lines)`. That was the field's one
  reader, and it changes in this same commit; the fuller printing is `02-07`'s.
- **E1.** `cli_install` catches `OSError` from `write_completion_script`, prints one line in
  the `install failed: …` style, and returns 1. The captured line, from
  `tmp/h30-argcomplete-static/e1_probe.py` with `~/.local` made a regular file in a throwaway
  home:
  ```
  install failed: cannot write the shell completion script: [Errno 20] Not a directory: '/tmp/h30-e1-1zm449_n/.local/share/kitty-setup'
  ```
  `cli_install returned 1`, with no traceback.
- **Known gap, not fixed here:** the rc edit on the line above
  (`path_integration.ensure_local_bin_in_path()` in `cli_install`, the plan's `installer.py:441`)
  can still raise an uncaught `OSError`. It is outside E1's scope.

**`doctor.py`**
- `_check_completion` no longer looks for the helper.
- An unrecognised `$SHELL` returns a SKIP that names the shell. The silent `.zshrc` default is
  gone.
- Otherwise the check asserts four things in order and reports the first failure:
  1. `installer.completion_script_path(shell, home=home)` exists. The injected home is passed
     through, so the check never reads the real `~/.local/share`.
  2. `_block_body_matches_template` holds, which compares the exact body.
  3. For zsh, `_block_followed_only_by_comments` holds.
  4. The file's text equals `installer.generate_completion_script(shell)`.
- Every FAIL names `my-kitty install` as the fix.
- The zsh PASS says what doctor checked (the block initialises completion itself and is the
  last command) and what it did not observe (a live registration, `~/.zlogin`, a `ZDOTDIR`
  elsewhere). It suggests `echo ${_comps[my-kitty]}`.
- No test checks the file against the CLI surface. U-3 showed the generated script names no
  subcommand.
- **The fd-8 producer check was considered and kept out of doctor.** It would cost a ~100 ms
  subprocess on every `make doctor`, and integration case I4 covers the same contract
  deterministically.

**`README.md`**: one paragraph, one hunk.
- Before: *"**Note as of `add-shell-completion`:** the sentinel-bracketed PATH block in your
  shell rc now contains a guarded `register-python-argcomplete` eval line in addition to the
  PATH export. Re-running `make install` rewrites the block body in place between the existing
  markers; nothing else in the rc file is touched. Open a fresh shell after the install — …"*
- After: *"**Note on shell completion:** `make install` generates a completion script under
  `~/.local/share/kitty-setup/` (`my-kitty-completion.bash` or `.zsh`), and the
  sentinel-bracketed PATH block in your shell rc sources it after the PATH export, so no helper
  has to be found on PATH at shell start. Re-running `make install` rewrites the block body
  between the existing markers; nothing else in the rc file is touched. For zsh, the block
  starts zsh's completion system (`compinit`) itself if your rc has not, and install keeps it
  as the last command in `~/.zshrc`, moving it there when anything but comments follows it,
  because a `compinit` that runs after it would undo the registration. Open a fresh shell after
  the install — …"* (The `<TAB>` sentence that follows is unchanged.)

## Task 3: the real run on this host

`$SHELL` is `/bin/bash`, so the real install and doctor exercised **bash only**. The zsh path
was proven in fake homes only: by the unit tests and by integration cases I2, I3, I5 and I6.
It was not proven by a real zsh run on the user's own rc.

**Backups:** `tmp/h30-argcomplete-static/bashrc.before` and `zshrc.before`.

**Before `make install`, the `~/.bashrc` block at lines 70-74, verbatim** (`cat -A`):
```
# >>> my-kitty PATH >>>$
if command -v register-python-argcomplete >/dev/null 2>&1; then$
    eval "$(register-python-argcomplete my-kitty)"$
fi$
# <<< my-kitty PATH <<<$
```
`~/.zshrc`: `rg -c my-kitty ~/.zshrc` found 0 matches, so it has no block.

Installed tool before: `uv tool list` showed `kitty-setup v0.0.0` / `- my-kitty`. `my-kitty`
has no `--version` flag (`my-kitty: error: unrecognized arguments: --version`), so the
installed `path_integration.py` hash stands in for it: `4dd7ad99…445a`, which still carried
`COMPLETION_LINE`.

**`make install`**, exit 0:
```
[setup] uv found at /home/bazzite/.local/bin/uv
[setup] running uv sync (dev .venv)
Resolved 27 packages in 0.60ms
Checked 26 packages in 0.22ms
[setup] running uv tool install --reinstall --force . (deployable binary)
Resolved 2 packages in 92ms
   Building kitty-setup @ file:///var/home/bazzite/git/personal/kitty-setup/.claude/worktrees/agent-a4b5a322d6795f3ac
      Built kitty-setup @ file:///var/home/bazzite/git/personal/kitty-setup/.claude/worktrees/agent-a4b5a322d6795f3ac
Prepared 2 packages in 263ms
Installed 2 packages in 4ms
 + argcomplete==3.7.2
 + kitty-setup==0.0.0 (from file:///var/home/bazzite/git/personal/kitty-setup/.claude/worktrees/agent-a4b5a322d6795f3ac)
Installed 1 executable: my-kitty
[setup] my-kitty installed at /home/bazzite/.local/bin/my-kitty
[setup] running my-kitty install
kitty version: kitty 0.49.0 created by Kovid Goyal
kitty.app:     /home/bazzite/.local/kitty.app
symlink:       /home/bazzite/.local/bin/kitty -> /home/bazzite/.local/kitty.app/bin/kitty
desktop entry: /home/bazzite/.local/share/applications/kitty.desktop
status:        kitty already installed; skipped upstream installer
config:        already up to date (/home/bazzite/.config/kitty/kitty.conf)
scenes:        seeded 0, kept 4 existing
PATH:          appended block to /home/bazzite/.bashrc; run `source /home/bazzite/.bashrc` or restart shell
completion:    wrote /home/bazzite/.local/share/kitty-setup/my-kitty-completion.bash
[setup] done
```
The `PATH:` line says "appended" although the block was rewritten in place. `_print_path_result`
ignores `result.reason`, which is the D-13 item `02-07` owns. The tool venv resolved
argcomplete 3.7.2 rather than the locked 3.6.3; that is T-2-01's recorded skew from `02-01`.
Doctor regenerates with the same interpreter, so the byte match holds.

After the install, `uv tool list` still shows `kitty-setup v0.0.0` / `- my-kitty`. The
installed `path_integration.py`, `doctor.py` and `installer.py` are sha256-identical to this
worktree's (`3faf96b6…6a13`, `42bae0d5…da88`, `3fff4bf1…a2c`). The user's `my-kitty` was
reinstalled from this worktree, as the plan intends. It was never uninstalled.

**After `make install`, the `~/.bashrc` block at lines 70-73, verbatim** (`cat -A`):
```
# >>> my-kitty PATH >>>$
export PATH="$HOME/.local/bin:$PATH"$
[ -f "$HOME/.local/share/kitty-setup/my-kitty-completion.bash" ] && . "$HOME/.local/share/kitty-setup/my-kitty-completion.bash"$
# <<< my-kitty PATH <<<$
```

**Nothing outside the sentinels changed, proven by diff rather than asserted:**
- The lines outside the markers, extracted from the before and after copies with the same awk
  filter, are byte-identical. `cmp` exits 0, and both hash to sha256
  `6197d5120598d5aab4da5c283803ae981ea2caff20312e6f9d1151ee0829c918`. That includes the user's
  own PATH export at `~/.bashrc:9-10`.
- The whole-file diff is only the block body:
  ```
  71,73c71,72
  < if command -v register-python-argcomplete >/dev/null 2>&1; then
  <     eval "$(register-python-argcomplete my-kitty)"
  < fi
  ---
  > export PATH="$HOME/.local/bin:$PATH"
  > [ -f "$HOME/.local/share/kitty-setup/my-kitty-completion.bash" ] && . "$HOME/.local/share/kitty-setup/my-kitty-completion.bash"
  ```
- `cmp ~/.zshrc tmp/h30-argcomplete-static/zshrc.before` shows it is byte-identical.
- `~/.local/share/kitty-setup/my-kitty-completion.bash` exists (2685 bytes).

**`make doctor`: exit status 0. This is the spine gate.**
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
Before this plan the same command was red. `02-01` measured exit 2, with `FAIL completion:
register-python-argcomplete not on PATH` followed by `make: *** [Makefile:33: doctor] Error 1`.
Red, `my-kitty doctor` exits 1 and `make` turns that into 2. `remote-control` may be PASS or
SKIP depending on whether a kitty with remote control is running; here it SKIPs.

**`make test-integration PYTEST_ARGS='tests/integration/test_completion_e2e.py -q'`**, exit 0:
```
......                                                                   [100%]
6 passed in 0.63s
test-integration: pytest exit status 0 (read from the child's status file; compositor exited 0)
```
Full `make test-integration`, exit 0: `76 passed in 44.49s` (baseline 70, plus 6).

## RED-state proof: transcripts from the materialised RED tree (`2570b63`)

Unit gate, exit 0. pytest status 1:
```
FAILED tests/unit/test_path_integration.py::test_completion_current_template_block_is_noop
FAILED tests/unit/test_path_integration.py::test_rc_block_renders_path_export_and_completion_lines
FAILED tests/unit/test_path_integration.py::test_completion_old_path_only_block_rewritten_and_moved_last_in_zsh
FAILED tests/unit/test_path_integration.py::test_legacy_block_migrates_with_completion_line
FAILED tests/unit/test_path_integration.py::test_completion_block_appended_despite_user_authored_export
FAILED tests/unit/test_path_integration.py::test_completion_block_appended_despite_tilde_export
FAILED tests/unit/test_path_integration.py::test_completion_block_appended_when_env_already_has_target
FAILED tests/unit/test_path_integration.py::test_completion_unsupported_shell_skips_with_honest_manual_lines
FAILED tests/unit/test_path_integration.py::test_completion_bash_body_sources_file_without_compdef
FAILED tests/unit/test_path_integration.py::test_completion_zsh_body_self_initialises_then_sources
FAILED tests/unit/test_path_integration.py::test_completion_template_match_is_per_shell
FAILED tests/unit/test_path_integration.py::test_completion_host_pre_d01_body_rewritten_in_place_bash
FAILED tests/unit/test_path_integration.py::test_completion_dual_markers_rewrite_retained_obsolete_body[eval-body]
FAILED tests/unit/test_path_integration.py::test_completion_dual_markers_rewrite_retained_obsolete_body[path-only-body]
FAILED tests/unit/test_path_integration.py::test_completion_zsh_block_above_compinit_moves_to_end
FAILED tests/unit/test_path_integration.py::test_print_path_result_unsupported_shell_prints_manual_lines_without_completion
FAILED tests/unit/test_doctor.py::test_completion_check_passes_bash_naming_the_file
FAILED tests/unit/test_doctor.py::test_completion_check_fails_when_file_absent
FAILED tests/unit/test_doctor.py::test_completion_check_fails_when_file_stale
FAILED tests/unit/test_doctor.py::test_completion_check_fails_when_block_lacks_source_line
FAILED tests/unit/test_doctor.py::test_completion_check_skips_unsupported_shell
FAILED tests/unit/test_doctor.py::test_completion_check_passes_zsh_and_says_what_it_did_not_observe
FAILED tests/unit/test_doctor.py::test_completion_check_fails_zsh_block_followed_by_commands
FAILED tests/unit/test_doctor.py::test_completion_check_fails_zsh_body_without_self_init
FAILED tests/unit/test_installer_completion.py::test_cli_install_completion_write_failure_is_one_clean_line
25 failed, 16 deselected in 0.17s
```
Integration gate, exit 0. Both shells were asserted present first:
```
FAILED tests/integration/test_completion_e2e.py::test_bash_registers_completion_from_rendered_block
FAILED tests/integration/test_completion_e2e.py::test_zsh_registers_completion_after_user_compinit
FAILED tests/integration/test_completion_e2e.py::test_zsh_registers_completion_with_no_user_compinit
FAILED tests/integration/test_completion_e2e.py::test_producer_protocol_returns_candidates_on_fd8
FAILED tests/integration/test_completion_e2e.py::test_zsh_block_above_compinit_is_moved_by_install_and_registers
FAILED tests/integration/test_completion_e2e.py::test_doctor_verdict_matches_real_zsh_registration
6 failed in 0.05s
test-integration: pytest exit status 1 (read from the child's status file; compositor exited 1)
make: *** [Makefile:39: test-integration] Error 1
```
Every doctor case failed on an assertion, not a setup error. Under `uv run`, the old check PASSed
with `helper …; eval line present`; from the materialised tree it failed with `…not on PATH`.
Either way, none of the details named the completion file, `_comps` or a SKIP.

## Gates

Every `<automated>` gate was run verbatim from a script (`&amp;` unescaped).

| Gate | Result |
|------|--------|
| T1: step-0 record carries `compdef`, `compinit`, `compinit -i`, `_python_argcomplete` | pass |
| T1: `_block_body_lines`, `_block_followed_only_by_comments`, `command -v compdef`, `compinit -i`, `manual_lines` present; `_BLOCK_BODY_LINES` absent | pass |
| T1: no `register-python-argcomplete` in `path_integration.py` | pass |
| T1: all seven `reason=` literals present | pass |
| T1: `pytest test_path_integration.py test_installer_completion.py`: passed, no fail/error | pass |
| T1: e2e module has the required tokens and no pty use | pass |
| T2: doctor reaches `generate_completion_script`, `completion_script_path`, `skipped=True`, both predicates | pass |
| T2: no `register-python-argcomplete` in `doctor.py` | pass |
| T2: no `default when shell is unknown` in `doctor.py` | pass |
| T2: `pytest test_doctor.py -k completion`: passed, no fail/error | pass |
| T3: README describes `compinit` and `local/share/kitty-setup`, with no helper literal | pass |
| T3: README diff is exactly one hunk (`git diff -U0 -- README.md \| rg -c '^@@'` gave `1`) | pass |
| **T3: spine gate, `make doctor` exit 0, ≥9 PASS/SKIP, no FAIL** | **pass** |
| T3: `make test` ≥ 314 passed, no fail/error | pass (374) |
| T3: integration gate, bash+zsh precondition, then `make test-integration` passed, no fail/skip/error | pass |
| V3: neither src file mentions the helper | pass |
| V4: all three unit modules passed | pass |
| V8: ruff + black on `path_integration.py`, `doctor.py`, `test_completion_e2e.py` | pass (after the deviation below) |
| RED-state unit: exactly 25 failed, nothing passed or errored, pytest status 1 | pass |
| RED-state integration: exactly 6 failed, nothing passed/skipped/errored, `pytest exit status 1 (` | pass |
| RED is tests-only and holds all four test modules | pass |
| SUMMARY inside GREEN | pass |
| GREEN holds no path under `tests/` | pass |
| V9 first half: `README.md` inside GREEN | pass |
| **Two-commit topology, and V9's second half: exactly two `(02-02)` subjects** | **fail (exit 1): genuinely unsatisfiable on this base, see below** |

**Why the two-commit-count clause cannot pass.** The command is `test "$(git log --format=%s | rg
-c '\(02-02\)')" = '2'`, which exits 1 because the count is `3`. The third subject is
`da4da2d docs(02-02): revise for review cycle 2 — two real product bugs, exact RED counts`. That
is the plan's own revision commit. It sits on `gsd/phase-02-defect-remediation`, the base this
plan was required to start from. The gate counts `(02-02)` subjects across the full history,
and its `fails_when` assumes planning commits do not carry that token in their subject; this one
does. No correct tree can satisfy the clause without rewriting a shared `gsd/*` branch's
history, which the git policy forbids. Every other clause of the gate was measured true:
- `^test\(02-02\)` → `1`
- `^feat\(02-02\)` → `1`
- `git merge-base --is-ancestor 2570b63 <GREEN>` → exit 0
- `(02-02)` subjects in `da4da2d..HEAD` → `2`

So the plan made exactly the two commits the topology asks for.

## Baselines

- `make test`: `374 passed, 76 skipped` (baseline 360 passed; 360 − 3 replaced + 17 new).
- `uv run pyright`: `559 errors` (baseline 571). Per file, measured by materialising `da4da2d`
  and diffing counts: `src/kitty_setup/doctor.py` 5 → 4 and `tests/unit/test_doctor.py`
  33 → 22. Every other file is unchanged, the new e2e module has 0, and no file rose.
- `make test-integration`: `76 passed` (baseline 70).
- Leak check after every headless run: no `cage` and no `kitty.app/bin/kitty` process (only the
  probe's own `rg` matched), and `ls -d /run/user/1000/kitti-*` found nothing.
- `uv run python -c "import kitty_setup; print(kitty_setup.__file__)"` gave
  `<worktree>/src/kitty_setup/__init__.py`.
- `core.hooksPath` was the absolute `/var/home/bazzite/git/personal/kitty-setup/tools/hooks`
  at the start. `make hooks` reset it to `tools/hooks`, and it was still `tools/hooks` at the
  end.

## Deviations from Plan

**1. [Rule 3 - Blocking] `__all__` in `path_integration.py` and `doctor.py`.** The plan requires
underscore names shared across modules: doctor calls `_block_body_matches_template` and
`_block_followed_only_by_comments`, and the tests call `_block_body_lines`, `_block_text` and
`_check_completion`. Under pyright strict, each such use is a `reportPrivateUsage` error. That
conflicts with the zero-added-errors baseline, and the conventions forbid suppressions.
Measured on a probe package: listing a name in the defining module's `__all__` makes pyright
treat it as public (0 errors), while unlisted names are still flagged. So each module declares
the names it shares. As a side effect, the pre-existing `_find_block`, `_block_text` and
`_check_completion` uses stopped counting, and the total fell 571 → 559.

**2. [Rule 3 - Blocking] `pyproject.toml` per-file ignore for S603** on
`tests/integration/test_completion_e2e.py`. Every `subprocess.run` trips S603, and verification
item 8 requires ruff to be clean on this file. The conventions forbid `# noqa` and say to
configure the tool with a rationale instead. The entry copies the existing
`integration_runner.py` entry and its comment style. `pyproject.toml` is not in the plan's
`files_modified`.

**3. [Rule 1] Two pre-existing E501 docstring lines in `doctor.py`** (`_kitten_ls_succeeds`
and `_check_remote_control_per_probe_04`) were wrapped. Verification item 8 runs ruff on the
whole of `doctor.py`, which this plan owns, and those two lines failed it. The change is to
docstrings only.

**4. [Rule 2] Doctor catches `OSError`/`UnicodeDecodeError` when reading the completion file**
and reports FAIL `cannot read <file>: <err>`. Without this, an unreadable file would make doctor
itself raise a traceback.

**5. RED commit amended once while unpushed** to fix formatting, as described under Commits.

## Known limits and notes

- **E1 gap:** the rc edit (`ensure_local_bin_in_path()` in `cli_install`) can still raise an
  uncaught `OSError`. It is recorded here and not fixed.
- **`02-07`'s prose is now out of date:** it says `ensure_local_bin_in_path` has six reasons,
  four of them on the changed branch. There are now **seven**, five on the changed branch,
  because of `"moved rc block to end of file"`. `02-07` was left unedited as instructed; its
  executor should print seven.
- The install's `PATH:` line says "appended" for an in-place rewrite. That is `02-07`'s D-13
  item, and this plan did not change it.
- STATE.md and ROADMAP.md were not updated. The orchestrator integrates this branch after its
  cross-AI re-review, and a third `(02-02)` commit would break the plan's two-commit gate.

## R1.1

**R1.1 is closed.** The rc block sources a completion file install generates and owns, with a
per-shell body. Doctor verifies only what it can prove, and `make doctor` exits 0 on this host
after a real `make install`. **Phase 1's deferred-merge precondition is therefore satisfied.**
The merge itself belongs to Universal Phase Gate step 6 and was not performed here.

## Known Stubs

None.

## Threat Flags

None. The rc-edit and completion-file surfaces are T-2-04, T-2-05 and T-2-06 in the plan's
register, each mitigated as specified. The zsh self-init line uses `compinit -i`.

## Self-Check: PASSED

- FOUND: `src/kitty_setup/path_integration.py`, `src/kitty_setup/doctor.py`,
  `src/kitty_setup/installer.py`, `README.md`, `pyproject.toml`,
  `tests/integration/test_completion_e2e.py`.
- FOUND: RED commit `2570b63` (test(02-02)).
- FOUND: `tmp/h30-argcomplete-static/{rc-body.md,rc_body_probe.py,e1_probe.py,bashrc.before,bashrc.after,zshrc.before,make-install.log,make-doctor.log,make-test-integration-full.log}` (working tree, gitignored).

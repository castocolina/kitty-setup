---
phase: 02-defect-remediation
plan: 01
subsystem: installer
tags: [completion, argcomplete, installer, uninstall, R1.1, tdd]
status: complete
requires: [02-11]
provides:
  - "installer.COMPLETION_DIR, CompletionShell, completion_script_path(shell, *, home), generate_completion_script(shell), write_completion_script(shell, *, home), remove_completion_script(*, home)"
  - "cli_install writes ~/.local/share/kitty-setup/my-kitty-completion.<shell> for the shell path_integration detected"
  - "cli_uninstall removes the completion file under do_kitty; --keep-kitty preserves it"
affects: [02-02, 02-03]
actuals:
  tokens: 5510
  tasks: 2
  commits: 2
plan_head_before: 0f828ce06ec894201eb523437aa35bc0fe94d44c
tech-stack:
  added: []
  patterns:
    - "Completion shellcode generated in-process by argcomplete; currency proven by byte match against a fresh call, never by content inspection (U-3)"
    - "Untyped third-party function bound once through the module namespace and narrowed by an annotation, instead of a suppression comment"
key-files:
  created:
    - tests/unit/test_installer_completion.py
  modified:
    - src/kitty_setup/installer.py
    - tests/unit/test_installer_uninstall.py
decisions:
  - "Completion-file removal is guarded by do_kitty, not do_config: the file belongs to the binary, and make clean passes --keep-kitty --keep-backups but not --keep-config"
  - "Default completion directory resolves through the module constant COMPLETION_DIR at call time, like SYMLINK_PATH and DESKTOP_PATH; an injected home uses home/.local/share/kitty-setup"
  - "argcomplete.shellcode is bound as vars(argcomplete)['shellcode'] annotated Callable[..., str]: argcomplete 3.6.3 leaves it unannotated and outside __all__, so pyright strict flags every direct call, and getattr trips ruff B009"
metrics:
  duration: "~20 min"
  completed: 2026-09-24
---

# Phase 2 Plan 01: Generate the completion script in-process and own the file (R1.1, producer half) Summary

`my-kitty install` now writes `~/.local/share/kitty-setup/my-kitty-completion.{bash|zsh}` for the
detected shell. The file is generated in-process by argcomplete's `shellcode()`, with no PATH lookup
for `register-python-argcomplete` anywhere. It is byte-identical to a fresh generation, and it is
removed by `my-kitty uninstall` unless `--keep-kitty` is given.

**`my-kitty doctor` is still red after this plan.** `_check_completion` is untouched and still looks
for the helper on PATH (`FAIL completion: register-python-argcomplete not on PATH`, captured below).
Plan `02-02` adds the rc source line and the doctor check, and it is `02-02` that closes R1.1. This
plan does not claim R1.1 closed.

Scope anchor (pre-work `HEAD`): `0f828ce06ec894201eb523437aa35bc0fe94d44c`.

## Commits

| Commit | Subject | Content |
|--------|---------|---------|
| RED `7dab724` | `test(02-01): RED — completion script generated in-process and owned by the installer (R1.1)` | `tests/unit/test_installer_completion.py` (new, 16 cases); `tests/unit/test_installer_uninstall.py` (HOME guard, see Deviations) |
| GREEN (this commit) | `feat(02-01): GREEN — generate the completion script in-process at install, own its removal (R1.1)` | `src/kitty_setup/installer.py`, this SUMMARY |

RED was amended twice while unpushed (`9c0a3eb` → `80b347b` → `7dab724`). The plan allows this
("fix it in the RED commit while it is still unpushed"). Both amendments are explained under
Deviations. `git branch -r --contains` was empty before each amend.

## Hypothesis h30 (`tmp/h30-argcomplete-static/`, gitignored — this SUMMARY is the durable record)

The directory was created before any test or source edit. The reflog proves the order: reset to
`0f828ce` at 23:50:12, `run1-pre-edit.txt` born at 23:52:57, first RED commit at 23:54:49 (all -0300).
Contents: `repro.md` (D-02 repro with the verdict appended), `run.py`, `expected.json`, `actual.json`,
`run1-pre-edit.txt`, `run2-post-impl.txt`. `run.py` writes only into a `mkdtemp` fake HOME under its
own directory and removes it on exit.

argcomplete version (`importlib.metadata.version("argcomplete")`, repo venv): **3.6.3**.

**Run 1: before any edit.** Hypothesis half green, promotion half red.

```
$ uv run python tmp/h30-argcomplete-static/run.py
{
  "hypothesis": {
    "argcomplete_version": "3.6.3",
    "byte_length": 2685,
    "bash_zsh_identical": true,
    "roundtrip_through_fake_home": true,
    "subcommand_name_count": 0,
    "first_line": "#compdef my-kitty",
    "green": true
  },
  "promotion": {
    "status": "not implemented",
    "green": false
  }
}
hypothesis half: GREEN
promotion half:  RED (not implemented)
exit=1
```

**Run 2: after the implementation.** Both halves green, and `actual.json` equals `expected.json`
field for field.

```
$ uv run python tmp/h30-argcomplete-static/run.py
{
  "hypothesis": {
    "argcomplete_version": "3.6.3",
    "byte_length": 2685,
    "bash_zsh_identical": true,
    "roundtrip_through_fake_home": true,
    "subcommand_name_count": 0,
    "first_line": "#compdef my-kitty",
    "green": true
  },
  "promotion": {
    "status": "implemented",
    "per_shell": {
      "bash": {
        "path": ".local/share/kitty-setup/my-kitty-completion.bash",
        "byte_match": true
      },
      "zsh": {
        "path": ".local/share/kitty-setup/my-kitty-completion.zsh",
        "byte_match": true
      }
    },
    "unsupported_shell_writes_nothing": true,
    "removed_count": 2,
    "dir_pruned_when_empty": true,
    "green": true
  }
}
hypothesis half: GREEN
promotion half:  GREEN (implemented)
exit=0
```

**Byte identity:** bash and zsh shellcode are byte-identical at 2685 bytes in 3.6.3, because the
script dispatches on `$ZSH_VERSION` at runtime. Per-shell filenames are kept anyway (flagged
assumption A2).
**Subcommand-name count: 0.** This pins U-3, and `test_generated_script_names_no_subcommand` is the
tombstone that keeps it pinned.

D-02 diagnosis, re-measured read-only this session:

```
$ command -v my-kitty                       -> /home/bazzite/.local/bin/my-kitty (exit 0)
$ command -v register-python-argcomplete    -> (exit 1)
$ ls ~/.local/share/uv/tools/kitty-setup/bin/ | rg argcomplete
activate-global-python-argcomplete
register-python-argcomplete
```

### Probes (`docs/agent-iteration.md` step 3)

| Probe | Assumption | Verdict |
|-------|------------|---------|
| `tmp/probes/02-01/01-argcomplete-shellcode.md` | argcomplete 3.6.3 exposes in-process `shellcode(executables, use_defaults=True, shell='bash', complete_arguments=None, argcomplete_script=None)` and ships `py.typed` | holds. **Why:** in 3.6.3 the function is unannotated and outside `__all__`, which is why `installer._ARGCOMPLETE_SHELLCODE` binds it through `vars(argcomplete)` with an annotation (inline comment at the call site) |

### `docs/agent-iteration.md` loop: what was followed

The plan says steps 2 and 8 "still tell an agent to open and archive an OpenSpec change". **That is
no longer true of the file at `0f828ce`.** Measured:
`rg -n -i 'openspec' docs/agent-iteration.md` returns one hit, `142: … .planning/legacy/openspec/ is
frozen history that is never a destination`. Step 2 now says "Open a phase plan … under
`.planning/phases/`", and step 8 says "Close the plan: write … SUMMARY.md". So nothing was skipped for
OpenSpec reasons. Step 2 is this plan itself, and step 8 is this SUMMARY. The step-2/8 doc fix the
plan attributes to Phase 8 / R6.1 appears to have already landed. There is nothing to hand to R6.1
from this plan.

Steps 3-7 were followed with one adaptation. Step 6's "move `repro.md` to `docs/repro/`, rewrite
`run.py` as an integration test, delete `tmp/h30…`" was **not** done. The plan makes the SUMMARY plus
the tombstone unit test the durable carrier, and its gate 6 requires the `tmp/` artefacts to still
exist. No integration test was added: the file generation is pure Python, and real TAB completion
through a sourced rc is `02-02`'s integration module (`tests/integration/test_completion_e2e.py`).

## RED transcript

The RED commit's own tree was materialised through a throwaway index, the same instrument as the
RED-state gate. `kitty_setup` resolved inside that tree, not the editable install.

```
RED=7dab724a8fc38e4ae8625d6254742c5deadfd440
<tmp>/t/src/kitty_setup/__init__.py
FAILED tests/unit/test_installer_completion.py::test_write_bash_shellcode_matches_fresh_generation
FAILED tests/unit/test_installer_completion.py::test_write_zsh_shellcode_matches_fresh_generation
FAILED tests/unit/test_installer_completion.py::test_generate_completion_script_is_the_in_process_shellcode
FAILED tests/unit/test_installer_completion.py::test_generated_script_names_no_subcommand
FAILED tests/unit/test_installer_completion.py::test_generated_script_starts_with_compdef_header
FAILED tests/unit/test_installer_completion.py::test_unsupported_shell_fish_writes_nothing
FAILED tests/unit/test_installer_completion.py::test_unsupported_shell_none_writes_nothing
FAILED tests/unit/test_installer_completion.py::test_write_is_idempotent - At...
FAILED tests/unit/test_installer_completion.py::test_cli_install_writes_shellcode_for_detected_shell
FAILED tests/unit/test_installer_completion.py::test_cli_install_unsupported_shell_reports_skip_and_writes_nothing
FAILED tests/unit/test_installer_completion.py::test_remove_completion_script_deletes_both_and_prunes_empty_dir
FAILED tests/unit/test_installer_completion.py::test_remove_completion_script_is_a_noop_when_nothing_exists
FAILED tests/unit/test_installer_completion.py::test_remove_completion_script_keeps_dir_holding_a_foreign_file
FAILED tests/unit/test_installer_completion.py::test_cli_uninstall_default_removes_completion
FAILED tests/unit/test_installer_completion.py::test_cli_uninstall_keep_kitty_preserves_completion
FAILED tests/unit/test_installer_completion.py::test_cli_uninstall_keep_config_still_removes_completion
16 failed in 0.09s
exit=1
--- existing uninstall module at RED (guard inert via raising=False):
8 passed in 0.02s
```

**16 failed, 0 passed, 0 errors** (the floor is 11). The plan's full selector matches all 16 cases.
Every failure is a missing-API `AttributeError`: 9 `write_completion_script`, 5 `COMPLETION_DIR`,
1 `generate_completion_script`, 1 `remove_completion_script`.

Cases beyond the eleven behaviour bullets:
- `test_generate_completion_script_is_the_in_process_shellcode` pins the name `02-02`'s doctor
  imports.
- Two `cli_install` cases pin the acceptance criterion that `cli_install` uses
  `PathEditResult.shell`, and that an unsupported shell is reported with no source line.
- The foreign-file case pins T-2-02 (never a recursive delete).

## The `do_kitty` guard and the three `--keep-*` cases

The removal is its own step in `cli_uninstall`, guarded by `do_kitty`, with the rationale written as
a code comment beside the guard. The completion file is the binary's footprint. `--keep-kitty` is
the only flag that preserves binary-adjacent state, and `make clean` passes
`--keep-kitty --keep-backups` (D-04) but not `--keep-config`. **`do_config` was rejected** because it
would make `make clean`, the safe verb, delete the completion of a binary that survives. The removal
is not buried in `remove_kitty_install()`, because that name means kitty.app.

| Case | Result |
|------|--------|
| `cli_uninstall` no flags | file removed (`test_cli_uninstall_default_removes_completion`, PASS) |
| `cli_uninstall --keep-kitty` | file preserved byte-for-byte (`test_cli_uninstall_keep_kitty_preserves_completion`, PASS) |
| `cli_uninstall --keep-config` | file removed (`test_cli_uninstall_keep_config_still_removes_completion`, PASS) |

## Generation mechanism and file location

- `generate_completion_script(shell)` calls argcomplete's `shellcode(["my-kitty"], shell=shell)`
  in-process, bound once as `_ARGCOMPLETE_SHELLCODE`.
- `completion_script_path(shell, *, home=None)` is pure path arithmetic. With no `home` it resolves
  to `COMPLETION_DIR / "my-kitty-completion.<shell>"`; with a `home` it resolves to
  `home/.local/share/kitty-setup/…`. It raises `ValueError` for a shell outside `CompletionShell`.
- `write_completion_script(shell | None, *, home=None)` returns `None` and creates nothing for
  `None` or an unsupported shell. It is idempotent.
- `remove_completion_script(*, home=None)` unlinks the two named basenames and calls `rmdir()` only
  when the directory is empty. There is no `rmtree` (gate 4).
- `cli_install` calls `write_completion_script(path_result.shell)` right after
  `ensure_local_bin_in_path()`, then prints `completion:    wrote <path>` or
  `completion:    shell <name> not supported; no script written`.
- File lands at `~/.local/share/kitty-setup/my-kitty-completion.bash` or `.zsh` (D-01 literal path;
  `XDG_DATA_HOME` not honoured, as the plan specified).

## Fake-HOME handling

- **No real `make install`, no `uv tool install` or `uv tool uninstall`, and no write to the real
  `~/.bashrc`, `~/.zshrc` or `~/.local/share/`.** This plan does not call for a real install. That is
  `02-02` task 3. `ls ~/.local/share/kitty-setup` → `No such file or directory`, before and after.
- Every new test uses `tmp_path` as home, with an autouse `HOME=tmp_path`. Cases that go through
  `cli_install` or `cli_uninstall` also redirect `installer.COMPLETION_DIR`, and `cli_install`'s kitty
  install and rc edit are stubbed.
- `run.py` writes only into a `mkdtemp` fake home that it deletes itself.
- The canary proof below used scratch `HOME` directories, which were removed afterwards.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 2 - Missing critical safety] Existing uninstall tests would delete the user's real completion file**
- **Found during:** task 2 wiring.
- **Issue:** `tests/unit/test_installer_uninstall.py` drives `cli_uninstall` with default flags and
  never redirects HOME. Once `cli_uninstall` calls `remove_completion_script()`, every `make test`
  run would unlink the real `~/.local/share/kitty-setup/my-kitty-completion.*`. That file does not
  exist yet, but `02-02` task 3 creates it.
- **Evidence:** a canary `HOME` holding `my-kitty-completion.bash` was used. With the unguarded module
  from `HEAD`: `8 passed`, `canary DELETED`. With the guarded module: `24 passed`,
  `canary SURVIVED: canary`.
- **Fix:** an autouse fixture `isolated_completion_dir` sets `HOME=tmp_path` and patches
  `installer.COMPLETION_DIR` with `raising=False`, which keeps it inert at RED (`8 passed` there).
- **Why in RED:** the GREEN-holds-no-test gate forbids `tests/` in GREEN. The RED-is-tests-only gate
  still passes. Pyright errors on that file are 8 before and 8 after.
- **Commit:** RED `7dab724`.

**2. [Rule 3 - Blocking] argcomplete 3.6.3's `shellcode` cannot be called directly under pyright strict without a suppression**
- **Issue:** `argcomplete.shellcode(...)` produced `reportPrivateImportUsage` (not in `__all__`) and
  `reportUnknownMemberType` (no annotations in 3.6.3). That is 12 errors across the new files, and
  conventions forbid suppressions.
- **Measured alternatives, on a throwaway probe module since deleted:**
  - `from argcomplete.shell_integration import shellcode` → `reportUnknownVariableType`.
  - `cast(..., shell_integration.shellcode)` → `reportUnknownMemberType`.
  - `getattr(...)` → pyright clean, but ruff `B009`.
  - A typed `Protocol` → vulture `unused variable` at 100%.
- **Fix:** `vars(argcomplete)["shellcode"]` annotated `Final[Callable[..., str]]`, in both
  `installer.py` and the test module. The test's reference therefore stays argcomplete itself, never
  the installer's generator.
- **RED amendment:** the test half was amended into RED (`9c0a3eb` → `80b347b`), with the RED state
  unchanged at 16 failed.
- **Gate 1 note:** gate 1's `rg 'argcomplete\.shellcode'` matches the explanatory comment above the
  binding. The call itself goes through `_ARGCOMPLETE_SHELLCODE`, which is argcomplete's
  `shellcode` function object. Stated plainly so a reviewer does not read the match as the literal
  call.

**3. [Plan text stale] `docs/agent-iteration.md` steps 2 and 8 no longer reference OpenSpec.** See the
loop section above. This is recorded as measured rather than as the plan predicted.

### Deferred / out-of-scope discoveries (not fixed)

- **Ruff S607 at `installer.py:170` (`_run_upstream_installer`, `["sh", …]`)** is pre-existing (line
  141 at `0f828ce`, in untouched code). Verification item 6's ruff check fails on this alone; black is
  clean, and ruff is clean on both test files. The research table at `02-RESEARCH.md:1334` assigns it
  to R0.11 (`02-09`/`02-10`). **Heads-up for that plan:** the research's suggested fix,
  `shutil.which("sh")`, would turn this plan's gate 2 (no `shutil\.which` in `installer.py`) red. An
  absolute `/bin/sh` or a ruff config entry with rationale would not.
- **`tools/uninstall.sh:72-75` will-remove enumeration** does not list
  `~/.local/share/kitty-setup/my-kitty-completion.*`, which `my-kitty uninstall` now removes when
  `KEEP_KITTY` is unset. The file is outside this plan's `files_modified`, and `02-03` owns
  `tools/uninstall.sh`'s tests. Proposed for `02-03`.
- **`cli_install` does not catch an `OSError` from writing the completion file.** It would surface as
  a traceback with a non-zero exit after a successful kitty install: loud, not silent. The plan
  specified no handling, and GREEN may not add a test for it. Candidate for `02-02`, which touches
  the same path.
- **`02-03` note:** `02-03` plans to extend `test_installer_uninstall.py`'s `calls` fixture to record
  the completion removal. The autouse `isolated_completion_dir` fixture added here composes with
  that.

## Supply-chain fact (not a defect)

The installed tool venv carries **argcomplete 3.7.2**
(`~/.local/share/uv/tools/kitty-setup/bin/python`), while `uv.lock` pins **3.6.3** (the repo venv).
The cause is that `tools/setup.sh` runs `uv tool install --reinstall --force .`, which resolves
outside `uv.lock`. From this plan onward, an unreviewed argcomplete version generates shell code that
the user's rc will source (once `02-02` lands). The byte comparison `02-02` adds to doctor is the
control that makes such a change visible. This plan installed no package (T-2-SC).

## Verification

Each gate's exact plan text was written to a file and run with `bash` from the worktree root.

| # | Gate | Result |
|---|------|--------|
| T1-1 | symbols present (`argcomplete\.shellcode`, `COMPLETION_DIR`, `def write_completion_script`, `def completion_script_path`) | PASS, exit 0 |
| T1-2 | no `shutil\.which` in `installer.py` | PASS, exit 0 |
| T1-3 | task 1 selector: passed, no failed/error | PASS, exit 0 |
| T2-1 | `def remove_completion_script`, no `rmtree(.*COMPLETION_DIR` | PASS, exit 0 |
| T2-2 | task 2 selector: passed, no failed/error | PASS, exit 0 |
| T2-3 | `tmp/h30-argcomplete-static/{repro.md,run.py,expected.json,actual.json}` exist (working tree) | PASS, exit 0 |
| T2-4 | `make test` passed ≥ 314, no failed/error | PASS, exit 0 |
| T2-5 | two-commit topology, RED ancestor of GREEN | PASS, exit 0 (run after GREEN) |
| T2-6 | RED commit touches only `tests/` | PASS, exit 0 (run against `7dab724`) |
| T2-7 | SUMMARY inside GREEN | PASS, exit 0 (run after GREEN) |
| T2-8 | RED-state from RED's own tree: exit 1, ≥ 11 failed, none passed/error | PASS, exit 0 (16 failed) |
| T2-9 | GREEN touches no `tests/` path | PASS, exit 0 (run after GREEN) |
| V-3 | whole module passes | 16 passed |
| V-6 | `ruff check` + `black --check` on `installer.py` and the new test module | ruff FAIL (pre-existing S607 only, see Deferred); black PASS |

Baselines:

```
$ make test          (exit 0)
======================= 360 passed, 70 skipped in 8.12s ========================
```
The prior baseline was 344 passed. 344 + 16 new = 360.

```
$ uv run pyright     -> 571 errors, 0 warnings, 0 informations   (baseline 571, unchanged)
$ uv run pyright src/kitty_setup/installer.py tests/unit/test_installer_completion.py
                     -> 0 errors
$ uv run pyright tests/unit/test_installer_uninstall.py
                     -> 8 errors before and after the edit (pre-existing)

$ make test-integration   (exit 0; this plan adds no integration case)
============================= 70 passed in 43.86s ==============================
test-integration: pytest exit status 0 (read from the child's status file; compositor exited 0)

$ make doctor        (exit 2 — expected; 02-02 closes this)
PASS kitty binary: /home/bazzite/.local/bin/kitty -> kitty 0.49.0 created by Kovid Goyal
PASS symlink: /home/bazzite/.local/bin/kitty -> /var/home/bazzite/.local/kitty.app/bin/kitty
PASS desktop entry: /home/bazzite/.local/share/applications/kitty.desktop
PASS config payload: /home/bazzite/.config/kitty/kitty-setup/kitty-setup.conf
PASS sentinel block: present in /home/bazzite/.config/kitty/kitty.conf
PASS parse check: kitty --debug-config exit=0
PASS bindings: 22 ours, 79 defaults, 0 conflicts
FAIL completion: register-python-argcomplete not on PATH
SKIP remote-control: no running kitty
make: *** [Makefile:33: doctor] Error 1
```
`make doctor` runs the installed `~/.local/bin/my-kitty`, not this worktree's code.

Leak check after the headless run:
- `ps -eo comm | awk '$1=="cage"||$1=="kitty"' | wc -l` → `0`.
- `ls -d /run/user/1000/kitti-*` → `No such file or directory`.

Environment:
- `uv run python -c "import kitty_setup; print(kitty_setup.__file__)"` → `<worktree>/src/kitty_setup/__init__.py`.
  The first `uv run` created the worktree's own `.venv`, which is uv's own behaviour.
- `core.hooksPath`: `tools/hooks` (relative) before the work and after it. `make hooks` was not
  needed.

## Known Stubs

None.

## Threat Flags

None. The only new surface is the generated file under `$HOME` and its removal, both in the plan's
threat register (T-2-01, T-2-02, T-2-03), and each is mitigated as specified.

## Self-Check: PASSED

- FOUND: `src/kitty_setup/installer.py` (COMPLETION_DIR, CompletionShell, completion_script_path,
  generate_completion_script, write_completion_script, remove_completion_script)
- FOUND: `tests/unit/test_installer_completion.py` (16 cases)
- FOUND: RED commit `7dab724`
- FOUND: `tmp/h30-argcomplete-static/{repro.md,run.py,expected.json,actual.json}` (working tree)

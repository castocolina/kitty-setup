---
phase: 02-defect-remediation
reviewed: 2026-09-24T13:42:54Z
depth: deep
base: 8faae07c15d7e594c0ce01bf450482812ee0f379
head: d4a3a8c
files_reviewed: 47
files_reviewed_list:
  - Makefile
  - pyproject.toml
  - src/kitty_setup/binding_introspection.py
  - src/kitty_setup/cli.py
  - src/kitty_setup/config_updater.py
  - src/kitty_setup/doctor.py
  - src/kitty_setup/harness/integration_runner.py
  - src/kitty_setup/harness/kitty_session.py
  - src/kitty_setup/installer.py
  - src/kitty_setup/path_integration.py
  - src/kitty_setup/scenes/__init__.py
  - src/kitty_setup/scenes/_client.py
  - src/kitty_setup/scenes/accent.py
  - src/kitty_setup/scenes/background.py
  - src/kitty_setup/scenes/colors.py
  - src/kitty_setup/scenes/launcher.py
  - tests/integration/_kitty_subprocess.py
  - tests/integration/test_client_socket_discovery.py
  - tests/integration/test_color_normalization_e2e.py
  - tests/integration/test_completion_e2e.py
  - tests/integration/test_h02_clear.py
  - tests/integration/test_h22_window_title.py
  - tests/integration/test_h25_scene_launcher.py
  - tests/integration/test_scene_fill_tab_e2e.py
  - tests/integration/test_scene_recipe_e2e.py
  - tests/unit/test_cli.py
  - tests/unit/test_config_updater.py
  - tests/unit/test_doctor.py
  - tests/unit/test_doctor_remote_control.py
  - tests/unit/test_harness_teardown.py
  - tests/unit/test_installer_completion.py
  - tests/unit/test_installer_download.py
  - tests/unit/test_installer_uninstall.py
  - tests/unit/test_integration_env_hygiene.py
  - tests/unit/test_integration_runner.py
  - tests/unit/test_kitty_session_env.py
  - tests/unit/test_kitty_session_socket.py
  - tests/unit/test_makefile_targets.py
  - tests/unit/test_path_integration.py
  - tests/unit/test_scenes_accent.py
  - tests/unit/test_scenes_background.py
  - tests/unit/test_scenes_client.py
  - tests/unit/test_scenes_colors.py
  - tests/unit/test_scenes_launcher.py
  - tests/unit/test_tools_uninstall_sh.py
  - tools/uninstall.sh
  - vulture_allowlist.py
findings:
  critical: 0
  warning: 6
  info: 8
  total: 14
status: issues_found
---

# Phase 2: Code Review Report

**Reviewed:** 2026-09-24T13:42:54Z
**Depth:** deep
**Scope:** `git diff 8faae07 d4a3a8c -- src tests tools Makefile pyproject.toml vulture_allowlist.py`. The base is `git merge-base gsd/phase-01-governance-freeze gsd/phase-02-defect-remediation`.
**Files Reviewed:** 47
**Status:** issues_found

## Summary

I reviewed every source and test change in Phase 2 and traced call chains across modules:
`installer.cli_install` → `config_updater.install` / `path_integration` / completion writer;
`cli_uninstall` → `config_updater.uninstall`; `doctor` → `parse_check` / `_check_completion`;
scene `launch_scene` → `_fill_current_tab` → `send-text`; and the integration runner plus the
harness. `src/` is clean under the five tools, so this report has no style findings.

Every MEDIUM finding was checked with a hermetic reproduction under the session scratchpad: fake
HOMEs, no kitty window, no `kitten @`, and no real rc or config file touched. The only real-kitty
call was `kitty +runpy`, which opens no window. It was used to inspect kitty's own `Child.__init__`
bytecode for WR-03.

Main concerns:
- The payload rollback is sound for the payload directory. It does not cover `kitty.conf` on any
  failure other than a parser rejection (WR-01).
- The R1.4 quoting fix is POSIX-only and changes what pane 0's `cwd` means (WR-02, WR-03).
- `make clean` now keeps backups, which exposes a pre-existing path where uninstall puts the block
  back (WR-04).
- Moving the zsh block to the end silently reorders the user's PATH (WR-05).
- Two error paths still end in a traceback (WR-01, WR-06).

Severity mapping: HIGH = BLOCKER (CR-), MEDIUM = WARNING (WR-), LOW = low-priority WARNING
(IN-). **No HIGH findings.**

## Warnings

### WR-01 (MEDIUM): A failed install restores the payload but not kitty.conf, and a parse-check timeout ends in a traceback

**File:** `src/kitty_setup/config_updater.py:224-237`, `:344-350`, `:395-404`. Also
`src/kitty_setup/installer.py:446`, `src/kitty_setup/doctor.py:106-109`.

**Defect:** `_write_block_and_check` restores the conf only on `not check.ok`. Every other failure
after the conf write skips that restore:
- `subprocess.TimeoutExpired` from the 15 s `parse_check` timeout
- `ConfigUpdaterError` for a missing binary
- `PermissionError`
- `KeyboardInterrupt` / `SystemExit` during the parse check

In each case the conf keeps the injected block, while `install()`'s `except BaseException` rolls
the payload back. The `install()` docstring promises a rollback on *any* failure, including
`KeyboardInterrupt`, but only the payload is rolled back. On top of that, `parse_check` catches
only `FileNotFoundError`. `TimeoutExpired` is neither `CalledProcessError`, `OSError` nor
`ConfigUpdaterError`, so it escapes `cli_install`'s handler and `doctor._check_parse` as a
traceback.

**Failure scenario:**
1. A first install on a loaded host: the parse check times out.
2. `kitty.conf` has just been created with `include kitty-setup/kitty-setup.conf`.
3. The payload directory is `rmtree`d by the rollback, so the include points at nothing.
4. The user sees a Python traceback instead of `install failed: …`.

On a re-install, the conf is left modified and a backup is left behind, but the payload is the old
one.

**Evidence (hermetic):** `subprocess.run` was patched to raise `TimeoutExpired`, then `install()`
was called with a pre-existing conf and payload. Result:
`raised: TimeoutExpired | ConfigUpdaterError: False | OSError: False`. The conf still contains the
marker block, the payload is `'# old payload'`, and one backup was written.

**Fix:** Make the conf restore part of the same failure contract as the payload, and turn a timeout
into a domain error.
```python
# parse_check
except FileNotFoundError as exc:
    raise ConfigUpdaterError(f"kitty binary not found at {kitty_bin}") from exc
except (subprocess.TimeoutExpired, PermissionError) as exc:
    raise ConfigUpdaterError(f"parse check could not run: {exc}") from exc

# _write_block_and_check: after the conf write, wrap the check
try:
    check = parse_check(conf, kitty_bin)
except BaseException:
    _restore_conf(conf, backup_path, created_conf)   # copy2 backup back, or unlink the created conf
    raise
```
Add a unit test for `TimeoutExpired` and one for `KeyboardInterrupt` during the parse check. Each
should assert that the conf bytes equal the pre-install bytes.

### WR-02 (MEDIUM): Pane-0 `send-text` quoting (R1.4) is POSIX-only; in fish a crafted `cwd` still runs commands

**File:** `src/kitty_setup/scenes/launcher.py:260-284`

**Defect:** `shlex.quote` produces POSIX single-quote quoting. The text goes to whatever
interactive shell the reused window runs. fish treats `\'` and `\\` as escapes *inside* single
quotes, so the closing quote shlex emitted becomes a literal in fish. This shifts the quoting and
leaves attacker-chosen text unquoted. The planning artifacts already treat fish users as real
(REQUIREMENTS R1.7 amendment), and fish is installed on this host (`/usr/bin/fish`).

**Failure scenario:** A shared or downloaded scene recipe has
`cwd = "/a\\'\"; touch ~/pwned; #"` (TOML escaping). For a fish user, `my-kitty scene launch
<name>` from a solo tab sends `cd '/a\'"'"'"; touch ~/pwned; #'`. fish runs `touch ~/pwned`. The
same shift affects `bash -lc {shlex.quote(cmd)}`. Also, a legitimate `cmd` ending in a backslash
leaves fish at an unbalanced-quote prompt that swallows later input.

**Evidence (hermetic, fish `--no-config`, sentinel in the scratchpad):**
- `cd {shlex.quote(cwd)}` with the payload above: `pwned_cwd: True`.
- `bash -lc {shlex.quote(cmd)}` with cmd `\'A"; touch …/pwned_fish; #`: `pwned_fish exists: True`.
  The `bash` stub received argv `-lc`, `'"'A`.
- The same line in bash is correctly one argument.

The R1.4 integration test (`test_fill_tab_quoting_space_and_metachar_in_pane0_cwd`) only proves
the fix under the host login shell, which is bash.

**Fix:** Do not route data through the reused shell's parser. Options, best first:
1. Reject a `cwd` or `cmd` that contains `'`, `\`, a newline or a control character on the
   fill-current-tab path. Or fall back to the new-tab path, which uses `launch --cwd` and argv.
2. Resolve the reused window's shell from `kitten @ ls` (`foreground_processes[].cmdline`) and use
   the fill path only for sh, bash or zsh.

Add a fish case to the integration test (skip when fish is absent).

### WR-03 (MEDIUM): Pane-0 `cwd` no longer expands `~` or `$VAR`, unlike every other pane

**File:** `src/kitty_setup/scenes/launcher.py:260-268` (compare `_launch_argv`, `:135-137`)

**Defect:** Before Phase 2, pane 0 sent `cd ~/src`, and the user's shell expanded it. Now it sends
`cd '~/src'`, which is a literal path. The other panes receive `--cwd=~/src`, and kitty itself
expands that. So the D-08 goal of "same semantics as every other pane" is not met for pane 0's
`cwd`: the same recipe opens pane 0 in the wrong directory, and only on the fill-current-tab
path. A `cwd` starting with `-` is also parsed as a `cd` option; `cwd = "-"` means `cd -`, which
is OLDPWD.

**Failure scenario:** A recipe with `cwd = "~/code/app"` is launched from a solo tab. Pane 0 shows
`cd: ~/code/app: No such file or directory` and stays in the launch directory. Panes 1+ open in
`~/code/app`, and the scene still exits 0.

**Evidence:**
- `bash --norc -c "cd '~/code'"` gives `cd: ~/code: No such file or directory` (rc 1).
- Disassembling kitty 0.49's `kitty.child.Child.__init__` (through `kitty +runpy`; no window) shows
  `os.path.expandvars(os.path.expanduser(cwd …))`. So `launch --cwd` expands both `~` and `$VAR`.

**Fix:** Mirror kitty client-side before quoting:
`target = os.path.expandvars(os.path.expanduser(p0.cwd))`, then send `f"cd -- {shlex.quote(target)}\n"`.
Add a unit test with `cwd="~/x"` and one with `cwd="-x"`.

### WR-04 (MEDIUM): `make clean` can never remove the block when the newest backup contains one; it reports success and puts the block back every time

**File:** `src/kitty_setup/config_updater.py:436-446` (unchanged code), made reachable by
`Makefile:30` (`clean` now passes `--keep-backups`) and `installer.py:501-514`.

**Defect:** When stripping the block leaves only comments or blank lines, `uninstall()` copies the
*latest* backup over the conf. A backup is taken whenever install repairs a drifted block, so the
backup holds that old block. Restoring it re-inserts the markers and an `include` line. The code
then still sets `block_removed = True`, so the CLI prints `config: block removed` and `restored
from …`. Before Phase 2, `make clean` ran a full uninstall, which deletes backups first. The
`cli_uninstall` comment on lines 501-504 depends on that ordering. With `--keep-backups`, this
branch now runs on the "safe reset verb".

**Failure scenario:**
1. `kitty.conf` holds only a block from an older release, for example with a different include line.
2. `make install` repairs the block and backs up the old one.
3. `make clean` restores that backup: the markers and the old include are back, and the payload is gone.
4. Each later `make clean` repeats the same "block removed / restored" cycle and never converges.

**Evidence (hermetic):**
- The conf held a block with `include kitty-setup/old.conf`. `install()` gave
  `backup kitty.conf.bak.20260101T000000Z`.
- `uninstall()` run twice gave `block_removed=True restored_from=kitty.conf.bak.20260101T000000Z`
  both times. Both times the conf was left with the full marker block and
  `include kitty-setup/old.conf`.

**Fix:** In `uninstall()`, choose the newest backup whose content has no marker block
(`_find_block(text) is None`). Or strip the block from the restored content before writing it,
and fall back to deleting when that leaves nothing. Add a regression test with a block-bearing
latest backup and `--keep-backups`.

### WR-05 (MEDIUM): Moving the zsh block to the end silently changes the user's PATH precedence and fights other "must be last" tools

**File:** `src/kitty_setup/path_integration.py:128-156`, `:264-293`; `src/kitty_setup/doctor.py:269-276`

**Defect:**
- A zsh block that anything executable follows is removed and appended again at the end on every
  install. The block runs `export PATH="$HOME/.local/bin:$PATH"`, so moving it past later PATH
  prepends (pyenv, conda, nvm, asdf, mise) changes which binary wins, and nothing reports it.
- Doctor FAILs `completion` whenever anything executable follows the block. Tool installers
  routinely append to `~/.zshrc`, so `make doctor` turns red after any unrelated tool install.
  `make doctor` green is also the repo's merge precondition.
- Tools that document their own block as having to be last (SDKMAN: "THIS MUST BE AT THE END OF
  THE FILE") are displaced by each `my-kitty install`.

**Evidence (hermetic zsh, `ZDOTDIR` = fake HOME):**
- Starting rc: our block, then `export PATH="/opt/pyenv/shims:$PATH"`, then an SDKMAN block.
- `ensure_local_bin_in_path(shell="zsh")` returned `moved rc block to end of file`, and our block
  now comes after SDKMAN's.
- `zsh -i` PATH order afterwards: `…/.local/bin`, `/opt/pyenv/shims`, `/usr/bin`. Before the move,
  pyenv shims came first.

**Fix:** Keep only the completion part last and leave the PATH line where it was. Split the block
into a PATH block, which stays in place, and a small completion-only block, which is the only part
that has to follow `compinit`. Or register completion so a later `compinit` keeps it, for example
by adding the script's directory to `fpath` as `_my-kitty` before `compinit`. Also, doctor should
warn rather than FAIL when non-`compinit` lines follow the block.

### WR-06 (MEDIUM): A non-UTF-8 byte in `~/.bashrc` or `~/.zshrc` causes a traceback in both `install` and `doctor`

**File:** `src/kitty_setup/path_integration.py:229`, `src/kitty_setup/doctor.py:256`, `src/kitty_setup/installer.py:450-457`

**Defect:** `rc_file.read_text(encoding="utf-8")` raises `UnicodeDecodeError`, which is a
`ValueError` and not an `OSError`. `cli_install` catches only `OSError` around the rc edit (R1.7).
`_check_completion` catches nothing around the rc read. Legacy rc files that contain Latin-1
comments are common.

**Failure scenario:** `my-kitty install` installs kitty and injects the config, then dies with a
traceback. The completion script is never written, and the rc is left unchanged. `my-kitty doctor`
tracebacks instead of printing its 9 lines.

**Evidence (hermetic):** `.bashrc = b"# caf\xe9 alias\n…"` gave
`UNCAUGHT UnicodeDecodeError isinstance OSError: False` from both
`doctor._check_completion(home=…)` and `ensure_local_bin_in_path(home=…, shell="bash")`.

**Fix:** Read and write the rc with `errors="surrogateescape"`, which preserves the user's bytes on
rewrite, in both the reader and the writer. Or catch `UnicodeDecodeError` and report one line:
`install failed: cannot update the shell rc file: <path> is not UTF-8`. Doctor should return a
FAIL result, not raise.

## Info

### IN-01 (LOW): Duplicate current-marker zsh blocks never converge; every install rewrites `.zshrc`

**File:** `src/kitty_setup/path_integration.py:264-293`

`find_block` returns only the first block. With two current blocks, the first always has something
executable after it (the second), so it is moved to the end. Next time, the other one is first.
**Evidence:** three consecutive calls each gave `True moved rc block to end of file`, with two
markers still present. Doctor also FAILs forever. **Fix:** When the begin marker occurs more than
once, remove every occurrence and append one block.

### IN-02 (LOW): The integration runner can widen past `tests/integration` via option values

**File:** `src/kitty_setup/harness/integration_runner.py:177-199`

Any existing path counts as a selector, including an option's *value*. So
`PYTEST_ARGS='--ignore tests/integration/x.py'` or `--deselect tests/integration/x.py::t` sets
`has_selector` and suppresses the `tests/integration` prefix. pytest then falls back to
`testpaths = ["tests"]` and runs the whole tree under `KITTI_INTEGRATION=1`. Conversely,
`-k tests` is rejected as a usage error. **Evidence:** `build_pytest_args(['--ignore',
'tests/integration/test_h02_clear.py'])` returns the argv unchanged, with no root. **Fix:** Always
pass `--rootdir`/`INTEGRATION_ROOT` and only ever add filters. Or skip the value of known
value-taking options (`--ignore`, `--deselect`, `-k`, `-m`, `-p`, `-c`, `--rootdir`) when
classifying selectors.

### IN-03 (LOW): Preserved payload asides accumulate and "remove EVERYTHING" uninstall leaves them

**File:** `src/kitty_setup/config_updater.py:249-282`, `src/kitty_setup/installer.py:487-547`, `tools/uninstall.sh:52-80`

By design, `kitty-setup.rollback.<ts>[.N]` directories, and a live `kitty-setup.rollback`, survive
`prune` and `uninstall`. But `make uninstall`'s help, the `cli_uninstall` docstring and the
will-remove list all promise to remove everything we created, and none of them mentions these
directories. Doctor does not report them either. **Fix:** List them in the will-remove output and
the uninstall report ("kept: …, delete by hand"), or remove them on a full uninstall. Add a doctor
line when one exists.

### IN-04 (LOW): A failed commit step after a successful install aborts the rest of `cli_install`

**File:** `src/kitty_setup/config_updater.py:353-355`

`shutil.rmtree(previous)` runs after the payload and conf were accepted. When it raises, `install()`
propagates the error. `cli_install` then prints `install failed: …` and returns 1 *before* the rc
edit and the completion write. Causes include a symlinked `kitty-setup` payload directory, which
`rmtree` refuses, or an unremovable file. **Evidence (hermetic, symlinked payload dir):**
`RAISED after commit: OSError [Errno None] None: …/kitty-setup.rollback`, even though the new
payload and the block were in place. **Fix:** Treat a commit failure as a warning: catch `OSError`
and print that the aside was kept at `<path>`. Or unlink a symlink aside instead of calling
`rmtree` on it.

### IN-05 (LOW): Bandit's skips are global while their justification is per call site

**File:** `pyproject.toml` `[tool.bandit] skips = ["B404", "B603", "B604", "B607", "B310"]`

Ruff's equivalents are scoped per file. Bandit's skips cover all of `src/`, so a future
`urlopen` with a user-supplied URL (B310), a new partial-path executable (B607), or a wrapper
called with `shell=True` (B604) goes unreported. **Fix:** Keep B404 and B603 global. Drop B310,
B604 and B607 from `skips`, and baseline the known sites instead (for example `bandit -b
baseline.json`), so new sites still fail.

### IN-06 (LOW): The https-only guard in `_download_installer` does not cover redirects, and a failed download leaks a temp file and an fd

**File:** `src/kitty_setup/installer.py:161-171`

The scheme check runs on the initial URL only. `urllib`'s `HTTPRedirectHandler` follows an
https→http redirect, so the ASVS V12 comment and the S310/B310 rationale in `pyproject.toml`
overstate the control. In addition, `mkstemp`'s fd is discarded and never closed. If `urlopen`
raises, the `kitty-installer-*.sh` file stays in `/tmp`, because `install()`'s `finally` only
covers the run. **Fix:** Use an opener with a redirect handler that rejects non-https `newurl`.
Close the fd (`os.close(fd)`), and unlink the file on download failure.

### IN-07 (LOW): `make clean`'s `|| true` hides every uninstall failure, not only a missing binary

**File:** `Makefile:28-30`

The comment justifies the `|| true` for a missing `my-kitty`, but it also turns a traceback or a
partial removal into a green `make clean`. **Fix:** `@if command -v my-kitty >/dev/null 2>&1; then
my-kitty uninstall --keep-kitty --keep-backups; fi`. That is still 2 lines, within the five-line
rule.

### IN-08 (LOW): Two unit tests reach real host state

**File:** `tests/unit/test_doctor.py:129-145`, `tests/unit/test_kitty_session_env.py:69-77`

- `test_run_checks_uses_supplied_home_root` patches only `shutil.which`. `installer.SYMLINK_PATH`
  and `kitty_bin_path` still point at the real `~/.local/bin/kitty`, so the test runs the real
  `kitty --version`. No window opens, but the result depends on the host.
- `test_guard_runtime_dir_kept_when_set` sets `XDG_RUNTIME_DIR=/run/user/1000`, so
  `_make_socket_dir` creates, and later removes, a real directory in the developer's live runtime
  dir. On uid 1000 hosts that is the real one.

**Fix:** Patch `SYMLINK_PATH`, `DESKTOP_PATH` and `kitty_bin_path` as `test_run_checks_reports_each_check`
does. Use a `tmp_path` runtime dir and assert on it, rather than a literal `/run/user/1000`.

## Checked and found sound

- The payload aside lifecycle for copy failure, parse rejection, restore failure, a missing previous
  payload, and stale-aside suffixing. The tests cover each branch.
- `_non_negative_int`, the launcher's `_window_id_from`, and `accent`/`background` absent-colour
  handling.
- The `rgb:` fullmatch.
- The uninstall.sh log-to-stderr fix and its sandboxed tests: complete replacement env, no real
  HOME or PATH.
- The runner's process-group teardown and its status-file verdict.
- The kitty_session socket-dir cleanup on startup failure.
- No changed test lacks an assertion: an AST scan of all 30 changed test files found none.

---

_Reviewed: 2026-09-24T13:42:54Z_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: deep_

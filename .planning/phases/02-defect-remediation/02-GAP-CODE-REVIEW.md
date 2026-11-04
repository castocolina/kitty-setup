---
phase: 02-defect-remediation
scope: gap-closure plans 02-12..02-15 (diff 8f8f23e..4093b55)
reviewed: 2026-11-04T03:58:00Z
depth: deep
files_reviewed: 22
files_reviewed_list:
  - Makefile
  - pyproject.toml
  - src/kitty_setup/cli.py
  - src/kitty_setup/config_updater.py
  - src/kitty_setup/doctor.py
  - src/kitty_setup/harness/integration_runner.py
  - src/kitty_setup/installer.py
  - src/kitty_setup/path_integration.py
  - src/kitty_setup/scenes/launcher.py
  - src/kitty_setup/scenes/recipe.py
  - tools/uninstall.sh
  - tests/conftest.py
  - tests/unit/conftest.py
  - tests/integration/conftest.py
  - tests/integration/test_home_sandbox.py
  - tests/integration/test_scene_fill_tab_e2e.py
  - tests/unit/test_bandit_scope.py
  - tests/unit/test_makefile_clean.py
  - tests/unit/test_unit_hermeticity.py
  - tests/unit/test_integration_runner.py
  - tests/unit/test_installer_download.py
  - tests/unit/test_path_integration.py
findings:
  critical: 0
  warning: 3
  info: 11
  total: 14
status: issues_found
---

# Phase 2 gap closure (02-12..02-15): Code Review Report

**Reviewed:** 2026-11-04T03:58:00Z
**Depth:** deep
**Files Reviewed:** 22
**Status:** issues_found

Severity scale: the user's BLOCKER/HIGH/MEDIUM/LOW. Mapping to the GSD tiers: BLOCKER/HIGH are
Critical (`CR-`), MEDIUM is Warning (`WR-`), LOW is Info (`IN-`).

## Summary

I reviewed the source and test changes in `8f8f23e..4093b55`. I checked them by reading the code,
reading pytest 9.0.3's own source in `.venv`, and running one probe script over temp-dir homes
(`probe1.py`, path below). Unit suite: `make test` gives `619 passed, 88 skipped in 11.55s`.
`vulture src tests vulture_allowlist.py` is clean.

I found no BLOCKER or HIGH. These areas held up under the edge cases I tried:

- **Launcher pane-0 quoting.** `_typeable` refuses a quote, a backslash and non-printables. Pane 0
  is typed only inside single quotes; anything else falls back to the argv path.
- **Recipe NUL refusal.** Every recipe string goes through `_require_str`.
- **Installer download.** The https-only redirect handler sees every hop. The fd is entered first
  in the `with`, so it is closed on a failed fetch, and the temp file is unlinked on
  `BaseException`.
- **Runner selector rules.** The `-o=`/`-c=` and clustered forms match argparse. `@file`,
  `--child`, `-o addopts=` and `--confcutdir` are refused. `-p no:<conftest>` is refused by pytest
  itself (`consider_pluginarg`, `_pytest/config/__init__.py:817`). `--rootdir` cannot move
  confcutdir off the repo root, because it stays `inipath.parent` (`:1555-1560`).
- **`-c _CHILD_PROGRAM`.** The child entry is reachable only from `run()`.
- **Payload asides.** The aside regex never matches a look-alike name, and a symlinked aside is
  unlinked, not followed.

What remains:

- Three MEDIUM data and behaviour issues:
  - non-atomic rewrites of the user's rc and conf files;
  - uninstall restoring a stale, older backup;
  - a doctor zsh PASS that its own evidence (h41 row C8) shows can be false.
- A set of LOW edge cases, test-guard gaps and small cleanups.

## Warnings

### WR-01 (MEDIUM): rc and kitty.conf are rewritten in place, non-atomically; no rc backup exists

**File:** `src/kitty_setup/path_integration.py:171-172`, `src/kitty_setup/config_updater.py:460`, `:511`, `src/kitty_setup/installer.py:559-589`

**Issue:** `_write_rc` is `path.write_bytes(...)`, which opens with `O_TRUNC` and then writes.
`config_updater` does the same with `write_text`. If the write fails after the truncate (ENOSPC on
a full or btrfs-COW home, EDQUOT, or a SIGKILL or power loss during the write), `~/.zshrc` or
`~/.bashrc` is left empty or partial. `path_integration` never takes a backup of the rc, so the
user's shell config is gone.

The conf has a related window. In a full `my-kitty uninstall`, `cli_uninstall` deletes every
`kitty.conf.bak.*` first (`installer.py:559-565`). Only then does it rewrite the conf in place
(`config_updater.py:511`). A failed write there loses the conf with no backup left.

Scope: this predates the range. The range rewrote this exact I/O as the "byte-exact rc I/O" fix
(02-14) and kept the truncate-then-write shape.

**Fix:** write to a sibling temp file and atomically replace the resolved target, so a symlinked
dotfile keeps its link:
```python
def _write_rc(path: Path, text: str) -> None:
    target = path.resolve()  # keep a dotfiles symlink pointing where it points
    fd, tmp = tempfile.mkstemp(dir=target.parent, prefix=f".{target.name}.")
    try:
        with os.fdopen(fd, "wb") as out:
            out.write(text.encode("utf-8", "surrogateescape"))
            out.flush()
            os.fsync(out.fileno())
        shutil.copymode(target, tmp) if target.exists() else None
        os.replace(tmp, target)
    except BaseException:
        Path(tmp).unlink(missing_ok=True)
        raise
```
Use the same helper for the conf writes in `config_updater`. That also gives one place to fix
IN-03.

### WR-02 (MEDIUM): uninstall can restore an arbitrarily old backup and skip newer ones

**File:** `src/kitty_setup/config_updater.py:201-211`, `:502-506`

**Issue:** 02-15 made `_latest_backup` skip every backup that holds a marker line. A backup holds
the old block whenever install repaired a drifted block, and in that case it also holds the
user's newer content. Uninstall then falls back to the oldest pre-block snapshot and silently
drops everything newer.

Measured with `probe1.py`:
1. Install over `font_size 10`. This writes the January backup.
2. The user changes to `font_size 14` and edits inside the block.
3. Reinstall. This writes the June backup, which holds `font_size 14` and the old block.
4. The conf is left as only our block, and uninstall runs.

Result: `restored from: kitty.conf.bak.20260101T000000Z`, conf `'font_size 10\n'`. The newer
`font_size 14` state is ignored.

**Fix:** keep the newest backup and strip the block from what is restored, instead of skipping
to an older file:
```python
latest = list_backups(conf)[-1] if list_backups(conf) else None
if latest is not None:
    text = latest.read_text(encoding="utf-8", errors="surrogateescape")
    bounds = _find_block(text)
    if bounds is not None:
        lines = text.splitlines(keepends=True); del lines[bounds[0]:bounds[1]]
        text = "".join(lines)
    conf.write_text(text, encoding="utf-8", errors="surrogateescape")  # via WR-01's atomic helper
```
This converges just as well: the restored file holds no block. It also restores the newest user
state.

### WR-03 (MEDIUM): doctor's zsh PASS ignores the compaudit-rejected parent, and its text contradicts the evidence

**File:** `src/kitty_setup/doctor.py:293-304`, `src/kitty_setup/path_integration.py:95-107`

**Issue:** The 02-14 body puts `$HOME/.local/share/kitty-setup` on `fpath`, which brings it under
`compaudit`. compaudit also checks the parent (`${^fpath:h}`).

The 02-14 evidence (`tmp/h41-zsh-fpath-completion/repro.md` rows C8 and C9) shows this case: on a
host without per-user groups and with `~/.local/share` at 0775, or with it world-writable,
registration fails ("nothing"), and a later plain `compinit` prints `compinit: initialization
aborted` or asks at every shell start. Rows C10 and C11 show that the 02-02 block-last layout
registered on the same host. So for that host class, this is a regression that the fpath line
introduced.

Doctor still returns PASS, and its detail says "The one shape that drops the registration is a
later `compinit -C`…". `README.md:155` names two shapes, so the doctor text is false by the
repo's own documentation. T-2-89 accepted the regression. A doctor PASS that is known to be false
is a separate defect, and it is cheap to detect.

**Fix:** in `_check_completion`, for zsh, compute compaudit's predicate on the fpath directory and
its parent. FAIL with the measured fix when either is group- or world-writable and not exempt
under a per-user group:
```python
for d in (script.parent, script.parent.parent):
    st = d.stat()
    if st.st_mode & 0o002 or (st.st_mode & 0o020 and not _per_user_group(st.st_gid)):
        return CheckResult("completion", False,
            f"{d} is group/world-writable, so zsh's compaudit rejects {script.parent}; "
            f"run `chmod go-w {d}`")
```
Then reword the PASS detail to name both shapes, or drop the "one shape" claim.

## Info

### IN-01 (LOW): overlapping legacy and current blocks delete user lines; duplicate legacy blocks need two installs

**File:** `src/kitty_setup/path_integration.py:254-269`, `:306-316`, `:159-163`

**Issue:** `_remove_blocks` assumes the spans do not overlap. A legacy span that interleaves with
the current one is not caught. Measured cases:

| Case | rc content | First-install result |
|---|---|---|
| interleave | `B, LB, E, USER_LINE_KEEP, LE, after` | `'# >>> my-kitty PATH >>>\nafter\n'` |
| enclose | `pre, LB, B, old, E, LE, post` | `'pre\npost\n'` |
| two_legacy | two legacy blocks | first block migrated, second left in place |

- **interleave:** the user line and the end marker are deleted, and an orphan begin marker stays.
- **enclose:** the result has no block at all, yet the run reports `changed=True` with "removed
  duplicate legacy marker". The PATH export and the completion source line are both missing until
  the next install.
- **two_legacy:** it converges only on the second run. That contradicts "duplicates converge" in
  02-14.

Each of these needs hand-mangled input, hence LOW.

**Fix:** in the legacy path, drop any legacy span that overlaps a current span. Removing every
legacy block, `_find_blocks(rc_text, _LEGACY_MARKER_BEGIN, _LEGACY_MARKER_END)`, the same way as
current duplicates makes the run converge in one pass:
```python
legacy = [s for s in _find_blocks(rc_text, LB, LE)
          if not any(s[0] < b[1] and b[0] < s[1] for b in blocks)]
```

### IN-02 (LOW): a failed first write deletes a dangling-symlink `kitty.conf`

**File:** `src/kitty_setup/config_updater.py:441-443`, `:415-421`

**Issue:** `conf.exists()` is False for a dangling symlink, for example a dotfiles link whose
target is not checked out yet. The code sets `created_conf = True`, and `write_text` follows the
link. On any failure, which 02-12 widened to `BaseException`, `_restore_conf` calls
`conf.unlink()`. That removes the user's symlink. On a parse rejection, the target file that the
write created is also left behind.

**Fix:** treat `conf.is_symlink()` as "exists". Or restore by unlinking only the file this install
created (`conf.resolve()`), never the link.

### IN-03 (LOW): kitty.conf still loses CRLF and lone-CR line endings

**File:** `src/kitty_setup/config_updater.py:445`, `:460`, `:496`, `:511`

**Issue:** `read_text`/`write_text` with surrogateescape still apply universal newlines.
Measured: `b"font_size 10\r\nbold_font auto\r\n"` becomes LF after install, and stays LF after
uninstall. 02-12 accepted this and states it, but it is the same defect 02-14 fixed for the rc.

**Fix:** reuse `_read_rc`/`_write_rc` (bytes plus surrogateescape) for the conf.

### IN-04 (LOW): doctor PASSes rc states that install then rewrites

**File:** `src/kitty_setup/doctor.py:241-242`, `:267-272`

**Issue:** The docstring says doctor "FAILs exactly the blocks the next `my-kitty install`
rewrites". That is not true for two cases: duplicate current blocks, and a legacy block beside a
current one. In both, doctor PASSes, because `find_block` sees only the first block. Install then
changes the file ("removed duplicate rc block" or "removed duplicate legacy marker").

**Fix:** use `_find_blocks` and the legacy `find_block` in doctor, and FAIL on more than one block.
Or narrow the docstring claim.

### IN-05 (LOW): the runner does not model `--`, and its option table can drift from pytest

**File:** `src/kitty_setup/harness/integration_runner.py:90-152`, `:257-259`, `:313-324`

**Issue:** There are two gaps:

- **`--` is not modelled.** `_split_options("--")` returns `[("--", None)]`, so the loop treats
  every later dash-prefixed argument as an option, while argparse treats it as a path. Today this
  fails safe: the path is not found, or the backstop refuses the item.
- **The option table can drift.** `_VALUE_OPTIONS` and `_CONFTEST_BYPASS_OPTIONS` are hand copies
  of pytest 9.0.3 plus pytest-cov 7.1.0, while `pyproject.toml` allows `pytest>=8.3.0`. Nothing
  checks the table against the installed parser. A future option that bypasses the conftest would
  pass unrefused, and with the conftest not loaded the backstop is gone too.

**Fix:** after `--`, treat every argument as a selector candidate. Add a unit test that builds
pytest's parser and asserts that the set of options taking a value equals the table:
```python
cfg = _pytest.config.get_config(); p = cfg._parser._getparser()
live = {s for a in p._actions if a.nargs not in (0,) and a.option_strings for s in a.option_strings}
assert live == rt._VALUE_OPTIONS | rt._OPTIONAL_VALUE_OPTIONS
```

### IN-06 (LOW): gaps in the unit audit guard

**File:** `tests/unit/conftest.py:51-56`, `:81`, `:90`, `:344-355`

**Issue:** The guard misses or mis-roots several things:

- **Unaudited events.** `os.truncate` is not in `_MUTATIONS`, and it destroys data. Neither are
  `os.link`, `os.utime`, `os.chown` or `os.system`.
- **A process-wide busy flag.** `_BUSY` is one flag for the whole process. An event from a second
  thread that arrives while the first is inside `_check` returns silently, which is a false
  negative.
- **Roots follow `$HOME`.** `_REAL_HOME` comes from `$HOME`. A run with an overridden HOME guards
  the wrong tree.

**Fix:** add `os.truncate` and `os.link` (dst) to `_MUTATIONS`, and treat `os.system` like
`subprocess.Popen` with a shell. Use a `threading.local()` re-entry flag. Derive the real home
from `pwd.getpwuid(os.getuid()).pw_dir`.

### IN-07 (LOW): the child-env AST rule is opt-in, and the guard docstring overclaims

**File:** `tests/unit/test_unit_hermeticity.py:500-502`, `tests/unit/conftest.py:20-25`, `tests/unit/test_bandit_scope.py:75-93`

**Issue:** The guard docstring says a child process "is held at the subprocess boundary instead,
by the committed child-env AST rule". That rule runs only over two hard-coded modules. 02-15's new
`test_bandit_scope.py` spawns bandit with the inherited env, real HOME included. The inventory
records this as accepted, and running `_sandbox_violations` over that module would flag it. The
same applies to `test_git_hooks.py` (`env=dict(os.environ)`).

**Fix:** run the rule over every `tests/unit/test_*.py`, with an explicit per-module exemption
list that carries the inventory reason. Or reword the docstring to say the rule covers the listed
modules only.

### IN-08 (LOW): dropping B310 made the fetch invisible to both linters

**File:** `pyproject.toml:163-164`, `src/kitty_setup/installer.py:200-206`, `tests/unit/test_bandit_scope.py:172-186`

**Issue:** The comment says the URL-fetch site "is gone". The fetch still exists. It moved from
`urlopen` to `build_opener(...).open`, which neither ruff S310 nor bandit B310 recognises. The
in-code control is real (scheme check plus redirect handler), so this is not a vulnerability.

The compensating-control note was deleted, though, and
`test_network_fetch_lives_only_in_installer` checks only `urllib.request` imports. That leaves
`http.client`, `socket` and `importlib`, so "a second fetch cannot hide" overstates what it
proves.

**Fix:** reword the pyproject comment to name `opener.open` as the fetch and the handler as its
control. Widen the AST fence to `http.client`, `socket` and `urllib3`, or narrow its docstring.

### IN-09 (LOW): the integration sandbox leaves kitty's own directory variables and `BASH_ENV`

**File:** `tests/integration/conftest.py:29-45`

**Issue:** HOME and XDG are sandboxed, but `KITTY_CONFIG_DIRECTORY`, `KITTY_CACHE_DIRECTORY`,
`KITTY_RUNTIME_DIRECTORY` and `BASH_ENV` pass through from the developer's environment. A
developer who exports one of them gets a test kitty or shell that reads or writes the real
location, the same class of leak as T-2-79.

**Fix:** add `monkeypatch.delenv(name, raising=False)` for each of them in
`sandbox_integration_home`.

### IN-10 (LOW): dead indirection, a duplicated fixture and a garbled docstring

**File:** `src/kitty_setup/path_integration.py:127-128`, `tests/integration/test_scene_fill_tab_e2e.py:40-61`, `src/kitty_setup/config_updater.py:309-311`

**Issue:** Three small cleanups:

- **Dead indirection.** After 02-14, `_block_is_current` is a one-line alias of
  `_block_body_matches_template`.
- **Duplicated fixture.** `sandbox_fill_tab_home` repeats the whole HOME, XDG and HISTFILE loop
  that the conftest's autouse fixture already ran. Only `INPUTRC` is new.
- **Garbled docstring.** "Neither ``prune`` never touches the preserved copy" in
  `_preserve_stale_aside`.

**Fix:** inline `_block_is_current`. Reduce the module fixture to the `INPUTRC` setenv. Fix the
sentence ("``prune`` never touches…").

### IN-11 (LOW): two uncaught exception paths end in a traceback, not one line

**File:** `src/kitty_setup/installer.py:490-499`, `src/kitty_setup/config_updater.py:208-209`

**Issue:** `response.read()` can raise `http.client.IncompleteRead`, which is an
`HTTPException` and not an `OSError`. `cli_install` does not catch it, so the user sees a
traceback (the temp file is still removed). Separately, 02-15's `_latest_backup` now reads every
backup. One unreadable `kitty.conf.bak.*` (EACCES, or a directory with that name) raises an
`OSError` out of `cli_uninstall`, which does not catch it.

**Fix:** add `http.client.HTTPException` to `cli_install`'s except tuple. In `_latest_backup`,
skip a backup that cannot be read, or report it in one line.

---

Probe used for WR-02, IN-01 and IN-03:
`/tmp/claude-1000/-var-home-bazzite-git-personal-kitty-setup/b7bd9520-ad75-4c17-a790-515c764c11ab/scratchpad/scripts/review02/probe1.py`.
It wrote only under a fresh `mkdtemp` directory and never touched `$HOME`.

_Reviewed: 2026-11-04T03:58:00Z_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: deep_

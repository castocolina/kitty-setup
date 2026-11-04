---
phase: 02-defect-remediation
plan: 07
subsystem: installer
status: complete
tags: [R1.7, D-11, D-13, installer, path-report, tdd]
requires: [02-06]
provides:
  - "`_record_install_log` and its one call in `install()` are gone. `_repo_root` stays, with two callers: `installer.py:100` (`_payload_source`) and `:114` (`_scenes_source`)"
  - "`_print_path_result`'s changed branch prints `result.reason`, the reason `ensure_local_bin_in_path` computed, as `PATH: <rc>: <reason>; run \\`source <rc>\\` or restart shell`. The generic `appended block to` wording is gone"
  - "the skipped branch prints a header that names the shell, then each `manual_lines` entry on its own line, verbatim, instead of joining them with `'; '`"
  - "`cli_install` catches an `OSError` from `ensure_local_bin_in_path()`, prints one stderr line (`install failed: cannot update the shell rc file: <OSError>`) and returns 1, before the PATH report and before the completion script is written"
affects: [02-09, 02-10]
tech-stack:
  added: []
  patterns:
    - "a report prints the outcome the callee computed. It does not print a fixed sentence per branch"
    - "an OSError at each install step that touches the user's files is caught at its own call site in `cli_install`, printed as one line, and returns exit 1"
key-files:
  created:
    - .planning/phases/02-defect-remediation/02-07-SUMMARY.md
  modified:
    - src/kitty_setup/installer.py
    - tests/unit/test_installer_uninstall.py
    - tests/unit/test_path_integration.py
    - tests/unit/test_installer_completion.py
decisions:
  - "The report cases go in `tests/unit/test_path_integration.py`, next to the one existing `_print_path_result` case at `:385` (now `:388`). The rc-state helpers they drive (`_legacy_block`, `_new_block`, `_USER_COMPINIT`) are already in that module. No third test module was created"
  - "The changed line is `PATH: <rc_file>: <reason>; run \\`source <rc_file>\\` or restart shell`. With the rc file first, each of the five reasons reads as a sentence, and the `source` guidance is kept"
  - "The no-change branch is unchanged (`PATH: already configured`)"
  - "`_repo_root` only works under an editable install, as its docstring says. That limitation was observed here and deliberately not acted on. No plan has scoped it"
metrics:
  duration: "~12 min"
  completed: 2026-09-24
actuals:
  tokens: 3500
  tasks: 2
  commits: 2
plan_head_before: abf75303a1dab6db0d941d6a751999f9be8da29e
---

# Phase 2 Plan 07: the install report says what happened, and the dead install log is gone (summary)

Before this plan, the install's report path had three untrue outputs and one uncaught error:

- `_record_install_log` wrote a file that nothing reads.
- `_print_path_result` printed `appended block to <rc>` for every change. `path_integration` had
  already computed which of five things happened, and that reason was thrown away.
- The unsupported-shell hint joined its rc lines with `'; '` onto one line.
- An `OSError` from the rc edit escaped `cli_install` as a traceback. It was printed after an
  install report that read as a success.

All four are fixed. Vulture's `path_integration.py:78: unused variable 'reason'` finding is gone
as a side effect, before `02-09` runs.

Scope anchor (pre-work `HEAD`): `abf75303a1dab6db0d941d6a751999f9be8da29e` (`abf7530`, the tip of
`gsd/phase-02-defect-remediation`). The harness worktree started at `23aeaa1` (origin/master, with
no `.planning/`). Before any work it was reset to the phase branch with
`git reset --hard gsd/phase-02-defect-remediation`, as instructed. `git config --get
core.hooksPath` read `tools/hooks` (relative) throughout. This agent did not change it. The
`post-commit` hook ran on both commits (`[post-commit] CodeGraph index synchronised`).

## Commits

| Kind | SHA | Subject |
|------|-----|---------|
| RED | `372b8bf` | `test(02-07): RED — install log tombstone, PATH report prints the computed reason and each hint line, rc-edit OSError is one line (R1.7)` |
| GREEN | (this commit) | `feat(02-07): GREEN — install log removed, PATH report prints the computed reason and each hint line, rc-edit OSError is one line (R1.7)` |

RED contains only the three test modules. GREEN contains `src/kitty_setup/installer.py` and this
SUMMARY, and no file under `tests/`. `path_integration.py` is untouched by both.

## Step 0: `tmp/h36-install-log/`, written before any test or source edit

Order of work: the search (10:59Z), then the pre-install host snapshot, then the one real
`make install`, then the post-install snapshot, then `install-run.md` and `repro.md`. After that,
gate g01 exited 0 at `abf7530`. Only then did the first test edit happen. `tmp/` is gitignored,
so the three files are quoted here verbatim.

### `search.txt`

```
$ rg -n 'install_log|install\.log' src tests tools docs Makefile
src/kitty_setup/installer.py:209:def _record_install_log(version: str) -> None:
src/kitty_setup/installer.py:212:    (log_dir / "install.log").write_text(version + "\n", encoding="utf-8")
src/kitty_setup/installer.py:239:    _record_install_log(version)
(rg exit status: 0; measured at HEAD abf7530)

$ rg -n --hidden -g '!.git' -g '!.planning/**' -g '!tmp/**' -g '!.venv/**' 'install_log|install\.log' .   (supplementary, whole repo)
./src/kitty_setup/installer.py:209:def _record_install_log(version: str) -> None:
./src/kitty_setup/installer.py:212:    (log_dir / "install.log").write_text(version + "\n", encoding="utf-8")
./src/kitty_setup/installer.py:239:    _record_install_log(version)

Verdict: one definition (:209), its one write (:212), its one call (:239). docs/ holds no mention. Nothing opens or reads the file.
```

### `install-run.md`

````
# h36 — one real `make install`, and where `install.log` lands

Run from this worktree at `abf7530` (before any 02-07 test or source edit), 2026-09-24T10:59Z.
Full transcript: `make-install.out` (exit 0). Host snapshots: `host-before/`, `host-after/`
(`state.txt` plus copies of `~/.bashrc`, `~/.zshrc`, `~/.config/kitty/kitty.conf`).

## `my-kitty install` output (tail of `make install`)

```
kitty version: kitty 0.49.0 created by Kovid Goyal
kitty.app:     /home/bazzite/.local/kitty.app
symlink:       /home/bazzite/.local/bin/kitty -> /home/bazzite/.local/kitty.app/bin/kitty
desktop entry: /home/bazzite/.local/share/applications/kitty.desktop
status:        kitty already installed; skipped upstream installer
config:        already up to date (/home/bazzite/.config/kitty/kitty.conf)
scenes:        seeded 0, kept 4 existing
PATH:          already configured
completion:    wrote /home/bazzite/.local/share/kitty-setup/my-kitty-completion.bash
[setup] done
exit=0
```

## Where the file landed

`$ fd -H -t f install.log ~/.local/share/uv/tools/kitty-setup`

| when | path | size | mtime | content |
|------|------|------|-------|---------|
| before | `~/.local/share/uv/tools/kitty-setup/lib/python3.12/tmp/install.log` | 36 bytes | 2026-09-24 06:45:08 -0300 | `kitty 0.49.0 created by Kovid Goyal` |
| after  | `~/.local/share/uv/tools/kitty-setup/lib/python3.12/tmp/install.log` | 36 bytes | 2026-09-24 07:59:14 -0300 | `kitty 0.49.0 created by Kovid Goyal` |

Under `uv tool install` (non-editable), `_repo_root()` is `Path(__file__).resolve().parents[2]`
of `<tool venv>/lib/python3.12/site-packages/kitty_setup/installer.py`, i.e.
`<tool venv>/lib/python3.12`, so the log lands in `<tool venv>/lib/python3.12/tmp/install.log`:
inside uv's own tool venv, a directory no user and no code of ours looks at. The mtime moved
with this run, so this run wrote it.

The repo's own `tmp/`:

- this worktree's `tmp/`: no `install.log` before or after (`fd -H -t f install.log tmp` → empty);
  `make install` uses the tool install, not the editable one.
- the main checkout's `tmp/install.log`
  (`/var/home/bazzite/git/personal/kitty-setup/tmp/install.log`): 36 bytes, mtime
  2026-07-14 11:04:37 -0400, content `kitty 0.46.2 created by Kovid Goyal` — two months stale
  and two kitty versions behind the installed 0.49.0, from an old editable run. Nothing has
  noticed, because nothing reads it.

## Nothing reads it

`search.txt`: `rg -n 'install_log|install\.log' src tests tools docs Makefile` returns only the
definition (`installer.py:209`), its write (`:212`) and its one call (`:239`). A supplementary
whole-repo search (excluding `.planning/`, `tmp/`, `.venv/`) returns the same three lines.
No reader exists.

## Host safety comparison (the only real install in this plan)

| file | sha256 before | sha256 after | `cmp` |
|------|---------------|--------------|-------|
| `~/.bashrc` | `c59f1b27adb41250fd061a17e583f883f7ffd5f6ebeef4298ff80fc413f8222b` | same | identical (0) |
| `~/.zshrc` | `aa07cc3f1509d4968deac0fd4c96669b15e13ba2a2095833614867dbb4eb0627` | same | identical (0) |
| `~/.config/kitty/kitty.conf` | `66ef36518abd0f0390f217ab9570a0874af4e178ae56b321ab04f88dbb7d0b0b` | same | identical (0) |

Both rc files and kitty.conf are byte-identical overall (so identical outside the sentinel block
too). The completion file `~/.local/share/kitty-setup/my-kitty-completion.bash` was rewritten
(mtime 06:45 → 07:59, size 2685 unchanged); `~/.local/bin/my-kitty` was re-linked by
`uv tool install --reinstall --force .`.
````

### `repro.md`

```
# h36 — conclusion

`_record_install_log` writes the kitty version to `<_repo_root()>/tmp/install.log`, which under
the shipped `uv tool install` lands inside uv's tool venv (`lib/python3.12/tmp/install.log`,
36 bytes, rewritten by the real run in `install-run.md`), and no code in `src/`, `tests/`,
`tools/`, `docs/` or the Makefile reads it (`search.txt`). It is dead output from a frozen spec,
so D-11 removes it outright rather than relocating it.

CONTEXT question — does `InstallReport` / `_print_install_report` read the version from the
file? **No.** `InstallReport.version` is assigned from `_capture_version(kitty_bin)` in
`install()` (`installer.py:225` and `:232` at `abf7530`), and `_print_install_report` prints
`report.version` (`:377`). `_record_install_log(version)` at `:239` is a pure side effect.
```

### Real-install safety record (the only real install, uninstall or clean in this plan)

Before the run, this was recorded: `sha256sum ~/.bashrc ~/.zshrc` (plus
`~/.config/kitty/kitty.conf`), copies of all three files into `tmp/h36-install-log/host-before/`,
and `ls -la ~/.config/kitty ~/.local/share/kitty-setup ~/.local/bin/my-kitty`. The same set was
recorded after the run into `host-after/`. **All three files are byte-identical overall**
(`cmp` exit 0 for each), so they are also identical outside the my-kitty sentinel block, and
`kitty.conf`'s hash did not change. The rc block was already current (`PATH: already
configured`). The run changed only these: the tool venv (reinstalled), the `my-kitty` symlink
(re-linked), the completion file (rewritten with the same 2685 bytes) and the tool venv's
`install.log`. It did not run `uv tool uninstall`.

The installed binary is therefore the pre-change `abf7530` code. It still contains
`_record_install_log`, twice, as measured by `rg -c` on the tool venv's `installer.py`. This plan
ran no second install after GREEN (see "make doctor" below).

## RED state, proven from the RED commit's own tree

Gate g15 materialises `372b8bf`'s tree through a throwaway index and runs the defect-case
selector. It gives **10 failed, 0 passed, 0 errors** (the floor is 5), and the gate status is 0.
The same gate, with a trailer that prints `$OUT` (`gates/g15show.sh`, gate text unchanged), is
saved in `tmp/h36-install-log/red-state.txt`:

```
FAILED tests/unit/test_installer_uninstall.py::test_install_log_producer_is_gone
FAILED tests/unit/test_installer_uninstall.py::test_install_log_not_written_by_mocked_install
FAILED tests/unit/test_path_integration.py::test_path_report_reason_printed[removed-duplicate]
FAILED tests/unit/test_path_integration.py::test_path_report_reason_printed[migrated-legacy]
FAILED tests/unit/test_path_integration.py::test_path_report_reason_printed[moved-zsh]
FAILED tests/unit/test_path_integration.py::test_path_report_reason_printed[rewrote-body]
FAILED tests/unit/test_path_integration.py::test_path_report_reason_printed[appended]
FAILED tests/unit/test_path_integration.py::test_path_report_reason_lines_distinct
FAILED tests/unit/test_path_integration.py::test_path_report_hint_prints_each_manual_line_on_its_own
FAILED tests/unit/test_installer_completion.py::test_cli_install_path_rc_oserror_is_one_clean_line
10 failed, 51 deselected in 0.15s
--- gate status: 0; N=10 ---
```

Each case failed for its defect, and none failed on a setup error:

- `test_install_log_producer_is_gone`: `assert '_record_install_log' not in vars(installer)`.
- `test_install_log_not_written_by_mocked_install`: the scratch root held `repo/tmp/install.log`.
- `test_path_report_reason_printed[*]`: the reason was absent from `PATH: appended block to …`.
  For `appended`, the computed reason `appended sentinel-bracketed block` is not a substring of
  the generic wording either.
- `test_path_report_reason_lines_distinct`: the five runs printed one line in total, not five.
- `test_path_report_hint_prints_each_manual_line_on_its_own`: no entry was a whole line.
- `test_cli_install_path_rc_oserror_is_one_clean_line`: `IsADirectoryError` escaped from
  `path_integration.py:305` through `installer.py:441`. It was reported as a test failure, not a
  collection or fixture error.

The two guards, `test_guard_path_report_unchanged_says_nothing_needed` and
`test_guard_path_report_keeps_source_guidance`, are in the RED commit and pass there (`-k
guard_path_report`: `2 passed`). No defect-case token selects them.

Freshness (step 1): before any test was written, `pytest … --collect-only -q -k 'install_log or
path_report_reason or path_report_hint or path_rc_oserror'` returned `no tests collected (49
deselected)`, exit 5.

## Where the new cases went, and why

| Case(s) | Module | Why |
|---|---|---|
| `test_install_log_producer_is_gone`, `test_install_log_not_written_by_mocked_install` (tombstones) | `tests/unit/test_installer_uninstall.py` | The plan names this module and its `calls` fixture. The mocked-install case takes `calls` as a parameter, so a stray reach into the uninstall helpers is recorded and asserted empty |
| `test_path_report_reason_printed[5]`, `test_path_report_reason_lines_distinct`, `test_path_report_hint_…`, both guards | `tests/unit/test_path_integration.py` | The one existing `_print_path_result` case is here (`:385` at `abf7530`), along with the rc-state helpers the five states need (`_legacy_block`, `_new_block`, `_USER_COMPINIT`). `test_installer_uninstall.py` has no report case. No third module was created |
| `test_cli_install_path_rc_oserror_is_one_clean_line` | `tests/unit/test_installer_completion.py` | Placed next to `test_cli_install_completion_write_failure_is_one_clean_line` and written in the same shape. It uses the autouse `fake_home`, `_redirect_default_dir` and `_fake_report`. Only `install()` is stubbed, and the rc edit runs for real |

Both tombstone docstrings open with **"Tombstone (D-11): pins a deletion, not a behaviour."**
The mocked install points `_repo_root` at a scratch root. It stubs `_capture_version`,
`_ensure_symlink`, `_write_desktop_entry` and `seed_scenes` with typed local functions, not
lambdas. This matters for two reasons: `SYMLINK_PATH` and `DESKTOP_PATH` are bound to the real
`HOME` at import time, and pyright strict flags lambda parameters as unknown. The case then
asserts four things:

- `report.version == "kitty 9.9.9 stub"`, so the version still comes from `_capture_version`.
- `tmp_path` contains no `install.log` anywhere.
- `_payload_source()` and `_scenes_source()` still resolve through `_repo_root`, or to their
  bundled wheel directories.

Every new case reaches a private name through `vars(module)["_name"]` or `monkeypatch.setattr` by
string. No case contains a suppression comment. The new cases never pass `env_path`, the keyword
that `02-09` deletes.

## `_repo_root` survives, with two callers

```
$ rg -n '_repo_root' src/kitty_setup/
src/kitty_setup/installer.py:80:def _repo_root() -> Path:
src/kitty_setup/installer.py:100:    return _repo_root() / "config" / "kitty"
src/kitty_setup/installer.py:114:    return _repo_root() / "examples" / "scenes"
```

- `:100` is `_payload_source()`, the kitty config payload in an editable install.
- `:114` is `_scenes_source()`, the seeded example scenes in an editable install.

`_repo_root`'s docstring says it works only because `uv sync` installs the package in editable
mode. The h36 run shows the consequence: under `uv tool install` it resolves to
`<tool venv>/lib/python3.12`. Both remaining callers check for a bundled `_payload`/`_scenes`
directory first, so the wheel path does not depend on `_repo_root`. **This limitation was
observed and deliberately not acted on.** It is a separate concern, and no plan has scoped it.

## PATH report: the five reasons, before and after

Printed by `tmp/h36-install-log/report_probe.py`. Every state is a real `~/.zshrc` in one scratch
`HOME`, driven through `ensure_local_bin_in_path(home=…, shell="zsh")`. The scratch path is
replaced with `<home>`. Before: `report-before.txt` (source at `372b8bf`). After:
`report-after.txt` (GREEN source).

| rc state | computed `reason` | before (one generic line for all five) | after |
|---|---|---|---|
| legacy block + current-marker block | `removed duplicate legacy marker` | ``PATH:          appended block to <home>/.zshrc; run `source <home>/.zshrc` or restart shell`` | ``PATH:          <home>/.zshrc: removed duplicate legacy marker; run `source <home>/.zshrc` or restart shell`` |
| legacy block alone | `migrated legacy marker` | (same line) | ``PATH:          <home>/.zshrc: migrated legacy marker; run `source <home>/.zshrc` or restart shell`` |
| current zsh block, then `autoload -Uz compinit && compinit` | `moved rc block to end of file` | (same line) | ``PATH:          <home>/.zshrc: moved rc block to end of file; run `source <home>/.zshrc` or restart shell`` |
| current-marker block with the obsolete export-only body | `rewrote rc block body to current template` | (same line) | ``PATH:          <home>/.zshrc: rewrote rc block body to current template; run `source <home>/.zshrc` or restart shell`` |
| no block | `appended sentinel-bracketed block` | (same line) | ``PATH:          <home>/.zshrc: appended sentinel-bracketed block; run `source <home>/.zshrc` or restart shell`` |
| current block (no change, guard) | `rc block already matches current template` | `PATH:          already configured` | `PATH:          already configured` (unchanged) |

Before the fix, the five states printed one distinct line between them. After it, they print five.
That is what `test_path_report_reason_lines_distinct` asserts as a set. The generic wording was
replaced, not joined by a reason. It is gone from `_print_path_result` (gate g06). The `source
<rc>` guidance is still printed (guard `test_guard_path_report_keeps_source_guidance`).

The measured count of reasons: `path_integration.py` has seven `reason=` values. One is the skip
(`unsupported shell: …`), one is no-change (`rc block already matches current template`), and
five are on the changed branch, as tabulated. All five were reached from real rc states.

## Unsupported-shell hint, before and after (`shell="fish"`)

`manual_lines` = `('export PATH="$HOME/.local/bin:$PATH"', '# completion is not set up for fish:
my-kitty generates completion for bash and zsh only')`. This is the PATH export plus an explicit
statement that completion is not set up. That matches amended D-13 and R1.7, and `02-02-SUMMARY.md`
records the same content (`:147`). The two agree, so no precedence call was needed.

Before (one joined line):

```
PATH:          shell fish not auto-handled; add manually: export PATH="$HOME/.local/bin:$PATH"; # completion is not set up for fish: my-kitty generates completion for bash and zsh only
```

After (a header, then one entry per line, verbatim):

```
PATH:          shell fish not auto-handled; add these lines to your shell rc yourself:
                   export PATH="$HOME/.local/bin:$PATH"
                   # completion is not set up for fish: my-kitty generates completion for bash and zsh only
```

Neither line is a bash `source` line. `test_path_report_hint_prints_each_manual_line_on_its_own`
asserts three things: no printed line contains `completion_source_line("bash")`, no
`my-kitty-completion` appears, and the header names `fish`.

## rc-edit `OSError`: the stderr line

The `path_rc_oserror` case makes `~/.zshrc` a directory under the case's `HOME`, with
`SHELL=/bin/zsh`. The same scenario in `report_probe.py`:

- before: the call raised, and `IsADirectoryError: [Errno 21] Is a directory: '<home>/.zshrc'`
  escaped `cli_install` as a traceback, after the install report had printed.
- after: `rc=1`, and stderr is exactly one line:

```
install failed: cannot update the shell rc file: [Errno 21] Is a directory: '<home>/.zshrc'
```

No completion directory was created (`completion dir exists: False`). The case asserts five things:
the return value is 1, stderr has exactly one non-blank line, that line contains the rc path and
`os.strerror(errno.EISDIR)`, neither stream contains `Traceback`, and the completion directory
does not exist. The handler is in `cli_install`, in the same shape as the completion-write handler
below it. `path_integration.py` is unchanged.

## R0.11 side effect: one vulture finding removed

| measure | `abf7530` | after | delta |
|---|---|---|---|
| `uv run vulture src` lines | 16 | 15 | **−1**: `src/kitty_setup/path_integration.py:78: unused variable 'reason' (60% confidence)` is gone. The only other diff line is `installer.py:272 → :265` for `uninstall_config_only`, shifted by the deletion |
| `uv run vulture src tests` lines | 15 | 15 | 0: in this scope `reason` was never reported, because the tests already read `result.reason`. The only changes are three line shifts in `test_installer_completion.py` |

`02-09` therefore starts with one fewer R0.11 finding, measured with `vulture src`, the scope
that R0.11's "`src/` clean" requires.

## Baselines and lint (repo-wide counts must not grow)

Measured with `tmp/h36-install-log/lint-counts.sh` at `abf7530` before any edit, and again on the
GREEN tree:

| measure | `abf7530` | GREEN | delta |
|---|---|---|---|
| `ruff check .` findings | 25 | 25 | 0 |
| `black --check .` files to reformat | 10 | 10 | 0 |
| `bandit -c pyproject.toml -r src` issues | 33 | 33 | 0 (7 in `installer.py` both times) |
| `pyright` errors (project config) | 559 | 559 | 0 (0 in `installer.py` both times) |
| `vulture src` lines | 16 | 15 | −1 |
| `vulture src tests` lines | 15 | 15 | 0 |
| `pyright` on the three touched test files | 17 | 17 | 0. This is the plan's no-regress ceiling (≤ 17). All 17 are pre-existing: `_LEGACY_MARKER_*` and `_print_path_result` private use at `test_path_integration.py`, and the untyped lambda stubs in `test_installer_uninstall.py` |

Touched files:

- black is clean on all four (`4 files would be left unchanged`).
- ruff is clean on the three test modules (`All checks passed!`). On `installer.py` it reports
  only the pre-existing `S607` at `:170` (`["sh", …]` in `_run_upstream_installer`). That line
  is unchanged and is reported identically at `abf7530`. See the deviations.
- bandit reports no new finding.

## `make test`

```
======================= 461 passed, 78 skipped in 8.25s ========================
exit=0
```

461 = 449 at `abf7530` + 12 new: 2 tombstones, 5 reason parametrisations, the distinct-lines
case, the hint case, 2 guards and the rc-error case. That is at or above the floor of 314, with
no failures and no errors.

## `make doctor`

`make doctor` runs the installed `my-kitty`. **The installed binary is the pre-change code**, from
the one step-0 install at `abf7530`. Under the hard rule of one real install only, `make install`
was not re-run after GREEN. So the spine was also run from this worktree's GREEN code with `uv run
my-kitty doctor` (read-only: `doctor.py` has no write, mkdir or unlink). Both give the same nine
lines and exit 0:

```
PASS kitty binary: /home/bazzite/.local/bin/kitty -> kitty 0.49.0 created by Kovid Goyal
PASS symlink: /home/bazzite/.local/bin/kitty -> /var/home/bazzite/.local/kitty.app/bin/kitty
PASS desktop entry: /home/bazzite/.local/share/applications/kitty.desktop
PASS config payload: /home/bazzite/.config/kitty/kitty-setup/kitty-setup.conf
PASS sentinel block: present in /home/bazzite/.config/kitty/kitty.conf
PASS parse check: /home/bazzite/.local/bin/kitty +runpy 'import sys; from kitty.config import load_config; bad = []; load_config(sys.argv[-1], accumulate_bad_lines=bad); [print(b, file=sys.stderr) for b in bad]; sys.exit(1 if bad else 0)' /home/bazzite/.config/kitty/kitty.conf exit=0
PASS bindings: 22 ours, 79 defaults, 0 conflicts
PASS completion: /home/bazzite/.local/share/kitty-setup/my-kitty-completion.bash is current and sourced by the my-kitty block in /home/bazzite/.bashrc
SKIP remote-control: no running kitty
exit=0
```

## Gates

Every `<automated>` gate was extracted verbatim from `02-07-PLAN.md` (HTML-unescaped) into
`tmp/h36-install-log/gates/gNN.sh` by `extract.py`. The only addition is a `cd <worktree>` line.
The runs were logged to `gates/gates.log` by `run.sh`. **No gate was changed.** The shell guard
blocks one-liners that mention `git`, so every gate ran from its script file.

| Gate | What | When | Exit |
|---|---|---|---|
| g01 | T1: step-0 evidence dir and its three files | step 0 (`abf7530`), and again pre-GREEN | **0**, **0** |
| g02 | T1: `_repo_root` survives, and no `_record_install_log`/`install.log` in `installer.py` | pre-GREEN | **0** |
| g03 | T1: `_record_install_log` absent outside `.planning/`, `tests/` and `docs/` | pre-GREEN | **0** |
| g04 | T1: `-k install_log` passes, none failed | pre-GREEN | **0** |
| g05 | T2: `result.reason` and `manual_lines` inside `_print_path_result` | pre-GREEN | **0** |
| g06 | T2: `appended block to` gone from `_print_path_result` | pre-GREEN | **0** |
| g07 | T2: every fish `manual_lines` entry is a whole printed line | pre-GREEN | **0** |
| g08 | T2: the three case names exist, and `-k 'reason or manual or hint or unsupported'` passes | pre-GREEN | **0** |
| g09 | T2: `-k path_rc_oserror` passes | pre-GREEN | **0** |
| g10 | T2: the three installer-facing modules all pass | pre-GREEN | **0** |
| g11 | T2: `make test` ≥ 314 passed, no fail/error | pre-GREEN | **0** (461 passed) |
| g12 | T2: `make doctor` exit 0, ≥ 9 PASS/SKIP, no FAIL | pre-GREEN | **0** |
| g13 | T2: topology: one `test(02-07)`, one `feat(02-07)`, RED is an ancestor of GREEN, 2 from RED onward | after GREEN | **0** |
| g14 | T2: RED is tests-only and holds both named modules | after RED; after GREEN | **0**; **0** |
| g15 | T2: RED tree, ≥ 5 failed, none passed/errored | after RED; after GREEN | **0** (N=10); **0** (N=10) |
| g16 | T2: GREEN holds the SUMMARY and not `path_integration.py` | after GREEN | **0** |
| g17 | T2: GREEN holds no `tests/` path | after GREEN | **0** |

`<verification>` item 8 (`gates/v08.sh`): `uv run ruff check src/kitty_setup/installer.py && uv
run black --check src/kitty_setup/installer.py` exits **1**. The cause is the pre-existing `S607`
at `installer.py:170` (see the deviations). The pyright half reports `17 errors`, which is within
the ≤ 17 ceiling.

## Deviations from Plan

**1. [Recorded, not a gate change] Verification item 8's literal ruff command exits 1 on a
pre-existing finding.** `uv run ruff check src/kitty_setup/installer.py` reports `S607 Starting a
process with a partial executable path` at `installer.py:170:9`. That is `["sh",
str(installer_script), …]` in `_run_upstream_installer`, a line this plan does not touch. The
repo-wide ruff output at `abf7530` (`lint-base-abf7530/ruff.txt`) lists the same finding at the
same line, and ruff's total is 25 before and after. The item states its own criterion: "no new
finding in the one source file this plan edits". That criterion holds, and the command is recorded
with its real exit status. R0.11 (`02-09`) owns the finding. Item 8 is a `<verification>` prose
item. It is not an `<automated>` gate and has no `02-VALIDATION.md` row, so neither file was
edited.

**2. [Scope note] `make doctor` was not preceded by a post-GREEN `make install`.** Task 2's action
says "Run `make install`, then `make doctor`". The orchestrator's hard rule allows one real
install, and that was the step-0 run. So `make doctor` ran against the `abf7530` binary. The same
nine lines were also measured from the GREEN code with `uv run my-kitty doctor`. Gate g12's own
note asks which binary was used to be recorded, and that is done above.

**3. [Test design] More RED cases than the plan's minimum.** `path_report_reason` is five
parametrised cases plus one set-comparison case, not one case. Each state therefore fails on its
own at RED, and the set assertion is still one case. RED has 10 failures, not the minimum of 5.
The plan's floor is a floor, and the selector tokens are exactly the plan's.

**4. [Wording choice, within the plan's latitude] The changed line reads `PATH: <rc>: <reason>;
run …`.** The plan asks that `result.reason` be printed and the `source` guidance kept. It does
not set the order. With the rc file first, "appended sentinel-bracketed block" and "moved rc
block to end of file" read correctly. `<reason> in <rc>` did not. The no-change branch is
unchanged.

No gate was defective, so `02-07-PLAN.md` and `02-VALIDATION.md` were not edited.

## Known limits and notes

- `_repo_root` works only under an editable install. This was observed and deliberately not acted
  on (see above).
- The tool venv's `lib/python3.12/tmp/install.log` and the main checkout's stale `tmp/install.log`
  are still on disk. Both are gitignored or outside the repo, and this plan's scope is the
  producer. The next `uv tool install --reinstall` replaces the tool venv, and the new code never
  writes the file again. Deleting either by hand is a host action this plan does not take. The
  plan's `<verification>` also states that the file's on-disk absence is not gated.
- No kitty window was spawned, and no integration run was needed. `$XDG_RUNTIME_DIR/kitti-*`
  count: 0. `cage` processes: 0.

## Known Stubs

None.

## Threat Flags

None new. T-2-25 is mitigated: the reason is printed, and the rc-edit `OSError` is one line and
exit 1. T-2-26 is mitigated: one hint entry per line. T-2-27 is mitigated: the write is removed.
T-2-28 is mitigated: `_repo_root` survives, as gate g02 confirms. T-2-SC: no package was
installed.

## Post-commit gate results

These gates ran against the first GREEN commit, `51ffbe4` (`gates.log`, "# after-GREEN"). All
exited **0**:

- g13: the topology gate.
- g14: RED is tests-only and holds both named modules.
- g15: the RED tree gives N=10 failed, with nothing passed or errored.
- g16: GREEN holds the SUMMARY and not `path_integration.py`.
- g17: GREEN holds no `tests/` path.
- Re-runs of g01, g02, g03, g05, g06 and g07.

For `51ffbe4`, `git diff-tree` lists exactly `A
.planning/phases/02-defect-remediation/02-07-SUMMARY.md` and `M src/kitty_setup/installer.py`.
For `372b8bf` (RED) it lists `M` for the three test modules and nothing else. Neither commit
contains a deletion. `git rev-list --count abf7530..HEAD` = 2.

GREEN was then amended once, while unpushed, to record this section and the Self-Check. The amend
changes only this file. The commit-dependent gates were re-run on the amended SHA (see the
Self-Check).

## Self-Check: PASSED

- Found: this SUMMARY, `src/kitty_setup/installer.py`, the three test modules, and
  `tmp/h36-install-log/{search.txt,install-run.md,repro.md}`. Gate g01 exits 0.
- Found commits: `372b8bf` (RED) and the GREEN commit (`feat(02-07)`, the current `HEAD`).
- Exactly two `(02-07)` subjects exist from RED onward (g13).
- No `$XDG_RUNTIME_DIR/kitti-*` directory and no `cage` process is left. No kitty window was
  spawned.
- `core.hooksPath` = `tools/hooks`, unchanged.

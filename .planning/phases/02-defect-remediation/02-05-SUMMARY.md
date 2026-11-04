---
phase: 02-defect-remediation
plan: 05
subsystem: config
status: complete
tags: [R1.5, R1.7, config-parse-check, rollback, doctor, data-safety, tdd]
requires: [02-04]
provides:
  - "`ParseCheckResult(ok, command, stderr)`: a frozen, slotted dataclass that `_parse_check` returns on every path. `command` is the complete `shlex.join` of the argv that ran, so `shlex.split(command)` gives the argv back"
  - "the `ConfigUpdaterError` on a parser rejection names the real, untruncated command and carries the parser's stderr"
  - "`install()` rolls back the payload directory through a rename-aside state machine. The previous payload is renamed to `kitty-setup.rollback` and restored on any failure (`except BaseException`, so Ctrl-C too). The aside is kept and named when a restore step fails, and dropped only after the check passes"
  - "a stale `kitty-setup.rollback` from an interrupted install is preserved at a unique `kitty-setup.rollback.<UTC-ts>[.N]`. One stderr line names it. It is never deleted and never blocks the install"
  - "doctor's parse-check detail is built from `ParseCheckResult.command`, with the parser's stderr on a FAIL and its warnings on a PASS, on one line"
  - "doctor's three 'skipped — …' FAILs are real SKIPs with no doubled word. A kitty-less host still exits 1"
affects: [02-10]
tech-stack:
  added: []
  patterns:
    - "rename-aside, not delete-then-copy: the only copy of a user's previous state is moved to a same-filesystem sibling and deleted only after the new state is accepted"
    - "the rollback handler is `except BaseException` plus a bare `raise`, so a Ctrl-C mid-copy restores instead of stranding the aside"
    - "unit tests reach the private `_parse_check` via `vars(config_updater)[\"_parse_check\"]`, and replace private doctor helpers with `monkeypatch.setattr(module, \"name\", …)`. Tests then add no pyright `reportPrivateUsage` finding, and ruff's B009 rules out `getattr` with a literal"
key-files:
  created:
    - .planning/phases/02-defect-remediation/02-05-SUMMARY.md
  modified:
    - src/kitty_setup/config_updater.py
    - src/kitty_setup/doctor.py
    - tests/unit/test_config_updater.py
    - tests/unit/test_doctor.py
decisions:
  - "The parse-check snippet is now one line: the same statements, joined with `;`. `command` and doctor's PASS/FAIL detail stay on one copyable line, and doctor keeps one line per check. A real kitty gives the same verdict and exit code on all ten payloads, before and after. See Deviations 1."
  - "Doctor's PASS detail also carries the parser's warnings. A missing `include` passes the check (T-2-19) and shows up on stderr only, so this is the one place a user can see it. It is surfaced; it is not made fatal. See Deviations 2."
  - "A stale aside is preserved under a dated name, never restored and never deleted. There are three reasons, all from the code. `install()` always replaces the payload. No journal records which step was interrupted. And preserving needs one path with no branch."
  - "`_parse_check` keeps its private name. The rename is R0.11's work in 02-10."
  - "`InstallResult.parse_ok` stays `bool | None`. It is derived from `ParseCheckResult.ok`."
metrics:
  duration: "~20 min"
  completed: 2026-09-24
actuals:
  tokens: 9100
  tasks: 3
  commits: 2
plan_head_before: 35c30cbe295364ae92346f2e6c1379622c5657e2
---

# Phase 2 Plan 05: the parse check reports what it ran, the payload rolls back, doctor SKIPs are real (summary)

Before this plan, the parse check behind `my-kitty install` had three defects. It named a
flag kitty has not had since 0.46 (`kitty --debug-config`). It threw away the parser's stderr,
which names the file, the line and the reason. And a rejected install restored `kitty.conf`
but left the **rejected** payload on disk, because `install()` deleted the previous payload
before copying the new one.

All three are fixed. The command is reported in full. The stderr reaches the user. The payload
directory rolls back through a rename-aside state machine that survives Ctrl-C and a failed
restore, and never deletes the only good copy. Doctor's three "skipped — …" FAILs are now real
SKIPs, and a test over the real `run_checks` shows that a kitty-less host still exits 1.

Scope anchor (pre-work `HEAD`): `35c30cbe295364ae92346f2e6c1379622c5657e2` (`35c30cb`, tip of
`gsd/phase-02-defect-remediation`). The harness worktree started at `23aeaa1`. It was reset
to the phase branch before any work, as instructed. The pre-work `skipped=True` count in
`doctor.py` was **4**: three in the remote-control check and one in the unsupported-shell
completion SKIP. After this plan it is **7**. `core.hooksPath` is `tools/hooks` (relative). It
was reported and not changed.

## Commits

| Kind | SHA | Subject |
|------|-----|---------|
| RED | `ac98089` | `test(02-05): RED — parse check returns its diagnostics, payload dir rolls back on every failure path, doctor's three skipped results are real SKIPs (R1.5, R1.7)` |
| GREEN | (this commit) | `feat(02-05): GREEN — …` |

RED holds only the two test modules. GREEN holds `config_updater.py`, `doctor.py` and this
SUMMARY, and no file under `tests/`. RED was amended once while unpushed, before GREEN existed
(see Deviations 4). The first RED SHA was `c0b044b`. GREEN was amended once, also while unpushed,
and only to record the commit-dependent gate results (g14, g17, g18) and the Self-Check in
this file.

## Step 0: h34 reproduction, before any test or source edit (`tmp/h34-parse-check/`)

`tmp/h34-parse-check/` was created first. It holds `repro.md`, `run.py` and `actual.json`, plus
`run-before.txt`, `actual-before.json` and `rename-facts.txt`. `run.py` uses a scratch HOME
under `tempfile` and the **real** kitty 0.49.0 (`/home/bazzite/.local/bin/kitty`), through
`kitty +runpy` only, which opens no window. Command: `timeout 120 uv run python
tmp/h34-parse-check/run.py <label>`.

### Ten-payload truth table (real kitty 0.49.0)

| payload line | `_parse_check` ok (before → after) | exit | stderr, first line |
|---|---|---|---|
| `this_is_not_a_kitty_directive yes` | True → True | 0 | `[0.009] Ignoring unknown config key: this_is_not_a_kitty_directive` |
| `map ctrl+shift+zzz nonexistent_action` | True → True | 0 | `[0.010] Shortcut: ctrl+shift+zzz has unknown key, ignoring` |
| `font_size` | True → True | 0 | `[0.009] Ignoring invalid config line: 'font_size'` |
| `!!!!` | True → True | 0 | `[0.008] Ignoring invalid config line: '!!!!'` |
| `map` | True → True | 0 | `[0.009] Ignoring invalid config line: 'map'` |
| **`include no-such-file.conf`** | **True → True** | 0 | `[0.009] Could not find included config file: /tmp/h34-…/tt-5/no-such-file.conf, ignoring` |
| `font_size not-a-number` | False → False | 1 | `BadLine(number=1, line='font_size not-a-number', exception=ValueError("could not convert string to float: 'not-a-number'"), …` |
| `confirm_os_window_close maybe` | False → False | 1 | `BadLine(number=1, line='confirm_os_window_close maybe', exception=ValueError("invalid literal for int() with base 10: 'maybe'"), …` |
| `background notacolor` | False → False | 1 | `BadLine(number=1, line='background notacolor', exception=ValueError("Invalid color name: 'notacolor'"), …` |
| `cursor_shape banana` | False → False | 1 | `BadLine(number=1, line='cursor_shape banana', exception=ValueError('Invalid cursor shape: banana allowed values are block, beam, underline'), …` |

`stderr_returned_by_parse_check` is `false` on all ten rows before the fix and `true` on all ten
after. Before the fix, the driver captured the stderr shown above by re-running the same argv
itself.

### `run.py` transcript, before (step 0, at `35c30cb`), verbatim apart from the truth table above

```
"parse_check_signature": "bool",
"has_ParseCheckResult": false,
"rollback": {
  "before": {"layout": ["kitty-setup", "kitty.conf"],
             "payload": {"kitty-setup.conf": "# PREVIOUS good payload\n",
                         "previous-marker.conf": "# previous marker\n"}},
  "error": {"raised": "ConfigUpdaterError",
            "message": "kitty --debug-config rejected the mutated kitty.conf; rolled back"},
  "after": {"layout": ["kitty-setup", "kitty.conf", "kitty.conf.bak.20260924T120000Z"],
            "conf": "font_size 12\n",
            "payload": {"kitty-setup.conf": "cursor_shape banana\n"}},
  "d09": {"a_error_names_debug_config": true, "a_error_names_runpy": false,
          "b_error_carries_parser_stderr": false, "c_conf_restored": true,
          "c_rejected_payload_left_on_disk": true, "c_previous_payload_restored": false}
},
"stale_aside": {"raised": null,
  "layout_after": ["kitty-setup", "kitty-setup.rollback", "kitty.conf", "kitty.conf.bak.20260924T120000Z"],
  "payload_after": {"kitty-setup.conf": "font_size 13\n"},
  "stale_marker_locations": ["kitty-setup.rollback/stale-marker.conf"]}
```

### `run.py` transcript, after the fixes, verbatim apart from the truth table above

```
config: preserved a payload aside from an interrupted install at /tmp/h34-_itxumec/home-stale/.config/kitty/kitty-setup.rollback.20260924T120000Z
"parse_check_signature": "ParseCheckResult",
"has_ParseCheckResult": true,
"rollback": {
  "before": {"layout": ["kitty-setup", "kitty.conf"],
             "payload": {"kitty-setup.conf": "# PREVIOUS good payload\n",
                         "previous-marker.conf": "# previous marker\n"}},
  "error": {"raised": "ConfigUpdaterError",
            "message": "kitty's config parser rejected the mutated kitty.conf; kitty.conf was restored.\ncommand: /home/bazzite/.local/bin/kitty +runpy 'import sys; from kitty.config import load_config; bad = []; load_config(sys.argv[-1], accumulate_bad_lines=bad); [print(b, file=sys.stderr) for b in bad]; sys.exit(1 if bad else 0)' /tmp/h34-_itxumec/home-rollback/.config/kitty/kitty.conf\nparser stderr:\nBadLine(number=1, line='cursor_shape banana', exception=ValueError('Invalid cursor shape: banana allowed values are block, beam, underline'), file='/tmp/h34-_itxumec/home-rollback/.config/kitty/kitty-setup/kitty-setup.conf')"},
  "after": {"layout": ["kitty-setup", "kitty.conf", "kitty.conf.bak.20260924T120000Z"],
            "conf": "font_size 12\n",
            "payload": {"kitty-setup.conf": "# PREVIOUS good payload\n",
                        "previous-marker.conf": "# previous marker\n"}},
  "d09": {"a_error_names_debug_config": false, "a_error_names_runpy": true,
          "b_error_carries_parser_stderr": true, "c_conf_restored": true,
          "c_rejected_payload_left_on_disk": false, "c_previous_payload_restored": true}
},
"stale_aside": {"raised": null,
  "layout_after": ["kitty-setup", "kitty-setup.rollback.20260924T120000Z", "kitty.conf", "kitty.conf.bak.20260924T120000Z"],
  "payload_after": {"kitty-setup.conf": "font_size 13\n"},
  "stale_marker_locations": ["kitty-setup.rollback.20260924T120000Z/stale-marker.conf"]}
```

### Supporting measurements (`rename-facts.txt`)

```
rename onto non-empty: OSError(39, 'Directory not empty')
rename onto empty dir: ok, c holds ['x']
issubclass(KeyboardInterrupt, Exception) = False
issubclass(SystemExit, Exception) = False
```

## `ConfigUpdaterError` on a parser rejection, before and after

Before:
```
kitty --debug-config rejected the mutated kitty.conf; rolled back
```
After (real kitty, from `run-after.txt`):
```
kitty's config parser rejected the mutated kitty.conf; kitty.conf was restored.
command: /home/bazzite/.local/bin/kitty +runpy 'import sys; from kitty.config import load_config; bad = []; load_config(sys.argv[-1], accumulate_bad_lines=bad); [print(b, file=sys.stderr) for b in bad]; sys.exit(1 if bad else 0)' /tmp/h34-_itxumec/home-rollback/.config/kitty/kitty.conf
parser stderr:
BadLine(number=1, line='cursor_shape banana', exception=ValueError('Invalid cursor shape: banana allowed values are block, beam, underline'), file='/tmp/h34-_itxumec/home-rollback/.config/kitty/kitty-setup/kitty-setup.conf')
```

## RED state, proven from the RED commit's own tree (gate g16)

The gate materialises `ac98089` through a throwaway index and runs the plan's defect-case
selector. Transcript tail, verbatim (`tmp/h34-parse-check/g16-transcript.txt`):

```
FAILED tests/unit/test_config_updater.py::test_parse_result_carries_ok_command_and_stderr_fields
FAILED tests/unit/test_config_updater.py::test_parse_result_command_names_runpy_not_debug_config
FAILED tests/unit/test_config_updater.py::test_parse_result_failure_carries_parser_stderr_verbatim
FAILED tests/unit/test_config_updater.py::test_parse_result_success_passes_stderr_through
FAILED tests/unit/test_config_updater.py::test_parse_result_command_is_the_complete_argv_executed
FAILED tests/unit/test_config_updater.py::test_install_parse_result_error_carries_command_and_stderr
FAILED tests/unit/test_config_updater.py::test_rollback_copy_fails_restores_previous_payload[oserror]
FAILED tests/unit/test_config_updater.py::test_rollback_copy_fails_restores_previous_payload[ctrl_c]
FAILED tests/unit/test_config_updater.py::test_rollback_parse_fails_restores_previous_payload
FAILED tests/unit/test_config_updater.py::test_rollback_restore_fails_keeps_and_names_the_aside[rename_back]
FAILED tests/unit/test_config_updater.py::test_rollback_restore_fails_keeps_and_names_the_aside[remove_target]
FAILED tests/unit/test_config_updater.py::test_rollback_no_previous_payload_leaves_no_payload_dir
FAILED tests/unit/test_config_updater.py::test_rollback_stale_aside_preserved_under_a_dated_name
FAILED tests/unit/test_config_updater.py::test_rollback_stale_aside_preserved_under_the_smallest_free_suffix
FAILED tests/unit/test_doctor.py::test_skip_state_parse_check_without_kitty_binary
FAILED tests/unit/test_doctor.py::test_skip_state_bindings_without_kitty_binary
FAILED tests/unit/test_doctor.py::test_skip_state_bindings_when_introspection_fails
FAILED tests/unit/test_doctor.py::test_parse_detail_names_the_command_from_the_result
FAILED tests/unit/test_doctor.py::test_parse_detail_surfaces_parser_stderr_on_failure
FAILED tests/unit/test_doctor.py::test_parse_detail_pass_carries_parser_warnings
20 failed, 47 deselected in 0.20s
captured status=1
```

**RED counts: 20 failed, 0 passed, 0 errors** under the defect-case selector. The floor is 18.
The breakdown is 6 `parse_result`, 8 `rollback_*` items, 3 `skip_state` and 3 `parse_detail`.
That is two more than the plan's 18, one `rollback_stale_aside` uniqueness item and one
`parse_detail` warnings item (see Deviations 2).

Every failure has a defect reason: `AttributeError: 'bool' object has no attribute 'ok'`, no
`ParseCheckResult`, the rejected or partial payload in place of the previous one, `__cause__`
is `None`, the injected `OSError` escaping instead of a named-aside error, a stale aside still at
`kitty-setup.rollback`, `FAIL` instead of `SKIP`, and `kitty --debug-config exit=…` details.

The three guards pass at RED by construction: `guard_success_leaves_no_aside`,
`guard_kitty_less_host_exits_nonzero` and `guard_all_pass_or_skip_exits_zero`. The whole RED
tree gives `20 failed, 47 passed` over the two modules (44 pre-existing cases plus 3 guards).

## What was built

`src/kitty_setup/config_updater.py`:
- `ParseCheckResult`, a frozen, slotted dataclass with `ok: bool`, `command: str` and
  `stderr: str`.
- `_parse_check` returns it from its one `return`. `command` is `shlex.join(argv)` of the exact
  list passed to `subprocess.run`. `stderr` is passed through untouched. The `FileNotFoundError`
  branch is unchanged. The docstring now says what the function runs and no longer mentions a
  flag.
- `_PARSE_SNIPPET` is one line: the same statements, joined with `;` (Deviations 1).
- `ROLLBACK_SUFFIX = ".rollback"` is one module constant.
- `install()` is now an explicit state machine:
  0. `_preserve_stale_aside` renames any existing `kitty-setup.rollback` to
     `kitty-setup.rollback.<UTC-ts>`, adding the smallest free `.N` when that name exists.
     "Exists" includes an empty directory and a symlink. It prints one stderr line. If the
     rename fails, it raises `ConfigUpdaterError` naming both paths before anything else has
     been touched.
  1. The previous payload, if any, is renamed to the aside.
  2. and 3. `copytree`, `_select_clear_variant` and `_write_block_and_check` run inside `try`
     / `except BaseException`. `_write_block_and_check` holds the conf mutation and parse check
     that were previously inline, with the same conf-restore order: restore, then raise.
  4. Commit: the aside is `rmtree`d after the `try`, outside the checked region.
  5. and 6. `_restore_payload` removes the partial target and renames the aside back. If
     either step raises `OSError` while an aside exists, it raises `ConfigUpdaterError` `from`
     that `OSError`. The message names the aside and the payload path and repeats the original
     failure's type and message. With no aside, the `OSError` propagates as is. The handler
     re-raises the original with a bare `raise`.
- The rejection message is `_rejection_message(check)`. It gives the full command on its own
  line and the parser's stderr (right-stripped), or `(the parser wrote nothing to stderr)`.

`src/kitty_setup/doctor.py`:
- `_check_parse(…, None)` and `_check_bindings(…, None)` return `CheckResult(name, False,
  "kitty binary not available", skipped=True)`. The introspection-error branch returns
  `CheckResult("bindings", False, str(exc), skipped=True)`. `render()` and `CheckResult` are
  unchanged.
- The parse-check detail is built from the result object, using `_one_line`, which joins
  lines with ` | `:
  - PASS: `{result.command} exit=0`, plus `; parser warnings: …` when stderr is non-empty.
  - FAIL: `{result.command} exit=non-0: {stderr}`.
  There is no `+runpy` literal and no `--debug-config` anywhere in `doctor.py`.

### The three `CheckResult`s, before and after (`kittyless.py`, scratch HOME, no real kitty)

Before (`35c30cb`):
```
_check_parse(p, None): CheckResult(name='parse check', passed=False, detail='skipped — kitty binary not available', skipped=False)
    render: FAIL parse check: skipped — kitty binary not available
_check_bindings(p, None): CheckResult(name='bindings', passed=False, detail='skipped — kitty binary not available', skipped=False)
    render: FAIL bindings: skipped — kitty binary not available
_check_bindings(p, <kitty>) raising: CheckResult(name='bindings', passed=False, detail='skipped — probe', skipped=False)
    render: FAIL bindings: skipped — probe
```
After:
```
_check_parse(p, None): CheckResult(name='parse check', passed=False, detail='kitty binary not available', skipped=True)
    render: SKIP parse check: kitty binary not available
_check_bindings(p, None): CheckResult(name='bindings', passed=False, detail='kitty binary not available', skipped=True)
    render: SKIP bindings: kitty binary not available
_check_bindings(p, <kitty>) raising: CheckResult(name='bindings', passed=False, detail='probe', skipped=True)
    render: SKIP bindings: probe
```

### Exit status on a kitty-less home, over the real `run_checks`

After the fix, verbatim. Before the fix, the output is identical except that the parse-check
and bindings lines read `FAIL … skipped — kitty binary not available`.
```
FAIL kitty binary: no kitty on PATH or under ~/.local
FAIL symlink: missing: /tmp/tmp86xrspqd/missing-link
FAIL desktop entry: missing: /tmp/tmp86xrspqd/missing.desktop
FAIL config payload: missing: /tmp/tmp86xrspqd/home/.config/kitty/kitty-setup/kitty-setup.conf
FAIL sentinel block: absent from /tmp/tmp86xrspqd/home/.config/kitty/kitty.conf
SKIP parse check: kitty binary not available
SKIP bindings: kitty binary not available
FAIL completion: the my-kitty block in /tmp/tmp86xrspqd/home/.bashrc does not match the current template that sources /home/bazzite/.local/share/kitty-setup/my-kitty-completion.bash; run `my-kitty install` to rewrite it
SKIP remote-control: managed remote-control.conf not installed (run `make install`)
exit status: 1
```
The exit status is 1 both before and after, because `_check_kitty_binary` FAILs on its own.
`guard_kitty_less_host_exits_nonzero` pins this through `cli_doctor()`.

## One rollback transcript per state-machine path (`paths.py` → `paths-after.txt`)

Each path runs in a scratch HOME with a fake kitty. Failures are injected by wrapping the
exact call. Verbatim, except that temporary directory prefixes are shortened to `…`:

```
### copy fails (OSError)
  outcome: raised OSError: [Errno 28] injected
  entries: ['kitty-setup', 'kitty.conf']
  payload: {'kitty-setup.conf': '# PREVIOUS\n'}
  conf: 'font_size 12\n'

### copy fails (Ctrl-C)
  outcome: raised KeyboardInterrupt:
  entries: ['kitty-setup', 'kitty.conf']
  payload: {'kitty-setup.conf': '# PREVIOUS\n'}
  conf: 'font_size 12\n'

### parser rejects
  outcome: raised ConfigUpdaterError: kitty's config parser rejected the mutated kitty.conf; kitty.conf was restored.
command: …/kitty-1 +runpy 'import sys; … sys.exit(1 if bad else 0)' …/home/.config/kitty/kitty.conf
parser stderr:
BadLine(number=1, line='cursor_shape banana', exception=ValueError('Invalid cursor shape'))
  entries: ['kitty-setup', 'kitty.conf', 'kitty.conf.bak.20260924T120000Z']
  payload: {'kitty-setup.conf': '# PREVIOUS\n'}
  conf: 'font_size 12\n'

### restore fails: rename back
  outcome: raised ConfigUpdaterError: install failed and the previous payload could not be put back: [Errno 5] injected rename_back failure
The previous payload is kept, untouched, at …/home/.config/kitty/kitty-setup.rollback; move it back to …/home/.config/kitty/kitty-setup by hand.
Original failure (ConfigUpdaterError): kitty's config parser rejected the mutated kitty.conf; kitty.conf was restored.
command: …
parser stderr:
BadLine(number=1, line='cursor_shape banana', exception=ValueError('Invalid cursor shape'))
    __cause__ = OSError(5, 'injected rename_back failure')
  entries: ['kitty-setup.rollback', 'kitty.conf', 'kitty.conf.bak.20260924T120000Z']
  payload: {}
  kitty-setup.rollback: {'kitty-setup.conf': '# PREVIOUS\n'}
  conf: 'font_size 12\n'

### restore fails: remove partial target
  outcome: raised ConfigUpdaterError: install failed and the previous payload could not be put back: [Errno 5] injected remove_target failure
The previous payload is kept, untouched, at …/kitty-setup.rollback; move it back to …/kitty-setup by hand.
Original failure (ConfigUpdaterError): kitty's config parser rejected … (command and parser stderr as above)
    __cause__ = OSError(5, 'injected remove_target failure')
  entries: ['kitty-setup', 'kitty-setup.rollback', 'kitty.conf', 'kitty.conf.bak.20260924T120000Z']
  payload: {'kitty-setup.conf': '# NEW\n'}
  kitty-setup.rollback: {'kitty-setup.conf': '# PREVIOUS\n'}
  conf: 'font_size 12\n'

### no previous payload, parser rejects
  outcome: raised ConfigUpdaterError: kitty's config parser rejected … (as above)
  entries: ['kitty.conf', 'kitty.conf.bak.20260924T120000Z']
  payload: {}
  conf: 'font_size 12\n'

### stale aside, successful install
  outcome: returned
  stderr lines: ['config: preserved a payload aside from an interrupted install at …/home/.config/kitty/kitty-setup.rollback.20260924T120000Z']
  entries: ['kitty-setup', 'kitty-setup.rollback.20260924T120000Z', 'kitty.conf', 'kitty.conf.bak.20260924T120000Z']
  payload: {'kitty-setup.conf': '# NEW\n'}
  kitty-setup.rollback.20260924T120000Z: {'stale-marker.conf': '# STALE\n'}

### success, no stale aside
  outcome: returned
  stderr lines: []
  entries: ['kitty-setup', 'kitty.conf', 'kitty.conf.bak.20260924T120000Z']
  payload: {'kitty-setup.conf': '# NEW\n'}
```

In the remove-partial-target path, the rejected `# NEW` payload stays at `kitty-setup/`. It
cannot be removed; that is the injected failure. The conf was restored to its pre-install
bytes first, and the error tells the user where the good copy is.

## Stated facts (recorded, not changed)

- **The stale-aside decision.** A stale aside is preserved under a dated name, never restored
  and never deleted, for three reasons from the code:
  1. `install()` always replaces the payload with `payload_source`. A restored aside would be
     moved aside again at once and dropped on success.
  2. `install()` keeps no journal. The commit step's `rmtree` unlinks entry by entry, so an
     interrupted commit leaves a partial aside that looks whole.
  3. Preserving is one path with no branch on whether the payload exists.
- **A preserved aside survives `prune` and `my-kitty uninstall`, by design.** `BACKUP_NAME_RE`
  (`^kitty\.conf\.bak\.\d{8}T\d{6}Z$`) does not match `kitty-setup.rollback.<ts>`, so
  `list_backups` and `prune` never touch it. `uninstall()` removes only `paths.payload_dir`. It
  is the user's to delete, and the stderr line names it.
- **Hidden Coupling #8, second half.** The backup that `_backup` creates in the drifted-block
  branch stays on disk after a failed install. See `kitty.conf.bak.20260924T120000Z` in the
  "parser rejects" path and in `test_rollback_parse_fails_restores_previous_payload`'s asserted
  layout. `--keep-backups` then preserves it. This is unchanged and now stated.
- **`_parse_check` keeps its private name** for 02-10 (R0.11). The pyright
  `reportPrivateUsage` at `doctor.py:104` (previously `:99`) is the same pre-existing finding,
  moved.

## T-2-19: the missing-`include` gap is recorded here and was **not** implemented

**Measurement** (real kitty 0.49.0, row 6 of the truth table): a `kitty.conf` holding `include
no-such-file.conf` gives `_parse_check` → ok **True**, exit **0**, with the diagnosis only on
stderr: `Could not find included config file: …/no-such-file.conf, ignoring`. The cause is that
`kitty.config.load_config(…, accumulate_bad_lines=bad)` fills `bad` only on value-conversion
failures. Unknown keys, unknown shortcut keys, malformed lines and missing includes all pass.

**Why it matters (ASVS V14).** The parse check is the control that validates the config we
wrote before the user's terminal trusts it. A missing include is the single most likely
real-world failure of our own injection: the payload directory deleted, moved, or not
force-included in the wheel. That control cannot see it.

**What this plan did.** It surfaced the diagnosis without failing on it. The warning is now in
`ParseCheckResult.stderr` and in doctor's PASS line (`; parser warnings: …`). The check's
verdict is **unchanged**: a missing include still passes, and `install()` still accepts it.
Failing on a warning would change install behaviour on a decision nobody has taken, and that is
outside D-09.

**Related gap found while measuring, also not implemented.** The parse check runs only when
`install()` changed the conf (`created_conf or updated_block`). On an ordinary reinstall the
conf already holds the correct block, so a new payload is never parse-checked at all, and the
new rollback only applies when the conf changed. The real `make install` in this plan took
exactly that path: `config: already up to date`.

**Proposed owner.** Raise a new requirement, "the install-time config check fails, or at least
warns loudly, on a missing `include` of our own payload, and runs on every payload replacement,
not only on a conf change". Place it with the next phase that touches `config_updater`, or with
Phase 8 (R6.x) accuracy work if none does. It needs its own decision, because it changes
whether `my-kitty install` exits non-zero.

## Real install and `make doctor` (host-state gate g13)

The installed `my-kitty` predated this plan (`rg -c ParseCheckResult` on the installed
`config_updater.py` → no match), so the plan's `make install` was run once against the real
HOME. Beforehand, `tmp/h34-parse-check/hostsnap.py before` recorded `ls -laR ~/.config/kitty |
head -50`, the sha256 of every file, `kitty.conf` included
(`66ef3651…0b0b  kitty.conf`), and the payload listing. It also made a full safety copy in the
session scratchpad.

`make install`: exit 0. `config: already up to date (/home/bazzite/.config/kitty/kitty.conf)`
and `status: kitty already installed; skipped upstream installer`.

After the install, the sha256 of every file under `~/.config/kitty` and the payload listing are
**identical**. Only mtimes changed, because the payload is re-copied on every install, as
before. No `kitty-setup.rollback*` sibling was left and no backup was created.

`make doctor` before the reinstall (old binary): exit 0, with `PASS parse check: kitty
--debug-config exit=0`.

`make doctor` after the reinstall, all nine lines, **exit 0**:
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
```
The real `kitty.conf` produces no parser warnings, so the PASS line has no `; parser warnings`
suffix.

## Gates

Every `<automated>` gate was extracted verbatim from the plan (HTML-unescaped) into
`tmp/h34-parse-check/gates/gNN.sh` by `extract_gates.py`, prefixed only with `cd <worktree>`.
Each was run by `rungates.py`, which logs to `gates.log`. The verification-section commands and
the VALIDATION 02-05-T1 name-agnostic variant were extracted the same way by
`extract_vgates.py`. No gate was changed.

| # | Gate | When run | Exit |
|---|------|----------|------|
| g01 | T1: AST — `ParseCheckResult` frozen+slots, fields `ok/command/stderr`, `_parse_check` returns it on every path | pre-work: 1 (expected); after fix | **0** |
| g02 | T1: no `--debug-config` in `config_updater.py` | pre-work: 1; after fix | **0** |
| g03 | T1: `pytest -k parse_result` passed, no fail/error | pre-work: 5 (no match); after fix | **0** |
| g04 | T1: `tmp/h34-parse-check/{repro.md,run.py,actual.json}` exist | from step 0 on | **0** |
| g05 | T2: AST — a `.rename(` outside `_select_clear_variant` and a `".rollback"` constant | pre-work: 1; after fix | **0** |
| g06 | T2: the six named rollback cases, one pytest run each | pre-work: 1; after fix | **0** |
| g07 | T2: whole `test_config_updater.py` green | after fix | **0** |
| g08 | T3: per-site SKIP probe (three sites, no "skipped" after the prefix) | pre-work: 1; after fix | **0** |
| g09 | T3: `doctor.py` reads `.command`, has no `+runpy` literal | pre-work: 1; after fix | **0** |
| g10 | T3: whole `test_doctor.py` green | after fix | **0** |
| g11 | T3: `pytest test_doctor.py -k 'skip or exits'` green | after fix | **0** |
| g12 | T3: `make test` ≥ 314 passed, no fail/error | after fix | **0** (423 passed) |
| g13 | T3: `make doctor` exit 0, ≥9 PASS/SKIP, no FAIL | after `make install` | **0** |
| g14 | topology: one `test(02-05)`, one `feat(02-05)`, RED ancestor of GREEN, exactly two `(02-05)` from RED^ | after GREEN | **0** |
| g15 | RED is tests-only and holds both modules | after RED (and amended RED) | **0** |
| g16 | RED tree: status 1, ≥18 failed, nothing passed/errored | after RED (and amended RED) | **0** (20 failed) |
| g17 | GREEN contains `02-05-SUMMARY.md` | after GREEN | **0** |
| g18 | GREEN holds no path under `tests/` | after GREEN | **0** |
| v02 | no `--debug-config` in `config_updater.py` or `doctor.py` | after fix | **0** |
| v04 | both modules green | after fix | **0** |
| v08 | `ruff check` + `black --check` on both source files | after fix | **0** |
| vT1 | VALIDATION 02-05-T1's name-agnostic AST gate | after fix | **0** |

g14 through g18 were run against the first GREEN commit, `46b1418`. All five exited 0.
`git diff-tree` for that commit lists exactly `A .planning/.../02-05-SUMMARY.md`,
`M src/kitty_setup/config_updater.py` and `M src/kitty_setup/doctor.py`. The one unpushed
amend that records these results changes only this file, so the gates hold for the amended SHA
too. They were re-run on it.

## Baselines and lint

`make test`: exit 0. `======================= 423 passed, 77 skipped in 8.08s ========================`.
That is 400 at 02-04 plus this plan's 23 new unit items: 20 defect items and 3 guards. The
floor is 314.

Integration: this plan runs no integration module. Its cases are hermetic unit tests with a
fake kitty, and the real-kitty evidence came from `run.py`. `make test-integration` was not
needed and was not run.

Repo-wide counts come from `tmp/h34-parse-check/lintcounts.py`, using the same venv tools on
both trees. `35c30cb` was materialised through a throwaway index:

| Tool | `35c30cb` | after | delta |
|------|-----------|-------|-------|
| `ruff check .` findings | 25 | 25 | 0 |
| `black --check .` files to reformat | 10 | 10 | 0 |
| `bandit -c pyproject.toml -r src` issues | 33 | 33 | 0 |
| `pyright` errors | 559 | 559 | 0 |
| `vulture src tests` lines | 15 | 15 | 0 |

Per touched file, using `uv run pyright <file>`:
- `config_updater.py`: ruff, black and pyright are all clean (0 before, 0 after). bandit
  reports the same two pre-existing items (B404 import and B603 on the existing `# noqa:
  S603` call).
- `doctor.py`: ruff and black are clean, with no E501. pyright reports 4 before and 4 after:
  the same pre-existing `reportPrivateUsage` set, and the `_parse_check` one moved from `:99`
  to `:104`.
- `test_config_updater.py`: ruff and black are clean. pyright reports 2 before and 2 after, the
  pre-existing `_block_text` and `_latest_backup`.
- `test_doctor.py`: black is clean, and ruff has only the pre-existing S105 at `:34`. pyright
  reports 22 before and 22 after, all pre-existing lambda and `_check_kitty_binary` lines. The
  new cases are fully typed and add none.

## Deviations from Plan

**1. [Rule 2 - keeps doctor's one-line-per-check contract] `_PARSE_SNIPPET` is now a single
line.** The multi-line snippet made the complete, `shlex.join`ed command span seven physical
lines. That was fine in the error message, but doctor's PASS/FAIL detail must now carry the
command (task 3), and doctor prints one line per check (`02-CONTEXT.md` Established Patterns).
The command could not be truncated or escaped without breaking "complete, copyable". The snippet
runs the same statements, joined with `;`. `print(b, file=sys.stderr)` writes `str(b) + "\n"`,
the same bytes as the old `sys.stderr.write(str(b) + '\n')`.

Evidence, per the research-then-experiment rule: against real kitty 0.49.0, `run.py`'s
ten-payload truth table gives the same `ok` and the same exit code on every row before and after
(table above), and the `cursor_shape banana` stderr is the same `BadLine(...)` line.
`test_parse_detail_surfaces_parser_stderr_on_failure` and
`…_pass_carries_parser_warnings` assert `"\n" not in result.render()`.

**2. [Rule 2 - surfacing stderr where it can be seen] Two cases beyond the plan's list, both in
RED.**
- `test_parse_detail_pass_carries_parser_warnings`: doctor's PASS detail includes the parser's
  warnings. The plan's flagged assumption says this plan "prints it and records the gap".
  Because a missing include passes, a stderr surfaced only on rejection could never show it.
  The check's verdict is unchanged.
- `test_rollback_stale_aside_preserved_under_the_smallest_free_suffix` pins the "never rename
  onto an existing path" rule. It covers an existing **empty** dated directory, which a bare
  rename would silently replace, and a taken `.1`. The result is `.2`.

Both are selected by the plan's defect selector and failed at RED, so the RED count is 20
rather than 18. Every gate still passes as written.

**3. [convention] How tests reach private names.** The plan requires the tests to add no
`reportPrivateUsage` finding, and the repo-wide pyright count must not grow.
- `test_config_updater.py` calls `_parse_check` through `vars(config_updater)["_parse_check"]`,
  in one helper. `getattr` with a literal is ruff B009. 02-10 updates the one string.
- `test_doctor.py` drives the public `run_checks` and replaces `_check_kitty_binary`,
  `_parse_check` and `enumerate_bindings` with `monkeypatch.setattr(module, "name", …)`, as
  02-04 did.

**4. [Rule 1 - my own RED test, fixed inside the unpushed RED commit] RED amended once.** In
`test_parse_result_carries_ok_command_and_stderr_fields`, the `FrozenInstanceError`
assignment came after `assert type(result) is config_updater.ParseCheckResult`. Once GREEN
defined the class, pyright narrowed `result` and reported `Cannot assign to attribute "ok"`.
That is one new error in the file. The assignment was moved above the type assertion. It still
fails at RED (`AttributeError` on a `bool` is not a `FrozenInstanceError`) and passes at GREEN.
The plan says a RED case is fixed "inside the RED commit while it is unpushed, never in GREEN".
RED `c0b044b` became `ac98089`, and g15 and g16 were re-run on it: both **0**, 20 failed.

**5. [structure] `install()`'s conf mutation and parse check moved into
`_write_block_and_check`, which returns the `InstallResult`.** This keeps the `try` region to
three calls. The conf logic and its restore-then-raise order are unchanged, as the 27
pre-existing cases show.

**6. Gate execution method (no gate was changed).** This agent's shell guard refuses compound
lines that mention `git`, or that `rtk` rewrites into `git`. Gates therefore ran from extracted
script files. Git commands went through `/usr/bin/git` or `tmp/h34-parse-check/g.py`, a
`subprocess` wrapper pinned to the worktree root.

No gate was defective. No edit to `02-05-PLAN.md` or `02-VALIDATION.md` was needed.

## Known limits and notes

- **The dated-name choice has a check-then-rename window.** `_preserve_stale_aside` picks the
  first name that does not exist, then renames. A second process creating that exact name in
  between would be replaced. Python's stdlib does not expose `renameat2(RENAME_NOREPLACE)`, and
  a single-user CLI runs one install at a time, so the window is accepted and stated.
- A Ctrl-C that lands exactly between step 1's rename and the `try` leaves an aside. That is
  the stale-aside case, and the next install preserves and reports it.
- `_parse_check`'s `subprocess.TimeoutExpired` is still unhandled. This is pre-existing and
  outside D-09. Inside `install()` it now triggers a full payload rollback, because it is a
  `BaseException` in the checked region.
- STATE.md and ROADMAP.md were not updated. The orchestrator integrates them, and a third
  `(02-05)` commit would break the two-commit topology.
- `tmp/h34-parse-check/` is kept for the orchestrator. It contains no copy of the user's config:
  the safety copy went to the session scratchpad.

## Known Stubs

None.

## Threat Flags

None new. T-2-16 is mitigated by the rename-aside state machine, with one test per path and
the transcripts above. T-2-17 is mitigated: `ParseCheckResult.stderr` reaches both the error
and doctor. T-2-18 is mitigated: the label is derived from the argv that ran. T-2-19 is
accepted and recorded, with a proposed owner. T-2-20 is accepted. T-2-SC: no package was
installed.

## Self-Check: PASSED

- FOUND: `src/kitty_setup/config_updater.py`, `src/kitty_setup/doctor.py`,
  `tests/unit/test_config_updater.py`, `tests/unit/test_doctor.py`, this SUMMARY, and
  `tmp/h34-parse-check/{repro.md,run.py,actual.json}`.
- FOUND commits: `ac98089` (RED) and `46b1418` (first GREEN SHA; this amend replaces it).
  `git rev-list --count 35c30cb..HEAD` gives `2`.
- No `$XDG_RUNTIME_DIR/kitti-*` directory and no kitty process was left behind. No kitty
  window was opened: the real kitty ran only as `kitty +runpy` under `timeout`.

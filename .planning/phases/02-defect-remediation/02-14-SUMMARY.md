---
phase: 02-defect-remediation
plan: 14
subsystem: shell-integration
tags: [zsh, fpath, compinit, completion, rc-file, bytes, surrogateescape, WR-05, WR-06, IN-01, A-4, tdd, real-kitty]
type: tdd

requires:
  - phase: 02-defect-remediation
    provides: plan 02-02 (completion script generated in-process, sentinel-bracketed rc block, doctor completion check) and plan 02-13 (real-kitty probe pattern, materialised-tree runs)
provides:
  - zsh completion registers through fpath: the rc block puts ~/.local/share/kitty-setup on fpath, starts compinit -i itself when compdef is missing, and sources _my-kitty behind a compdef guard
  - install never moves a zsh block; it rewrites a retained block's body in place and removes duplicate blocks (IN-01)
  - rc I/O is bytes with surrogateescape (WR-06, rc half): non-UTF-8 bytes, CR and lone-CR line endings survive, and a removed unterminated block keeps the byte before it
  - doctor compares the completion file's bytes with the generated shellcode (A-4), and has no rc position check
  - zsh completion file is _my-kitty (#compdef header); the legacy my-kitty-completion.zsh is removed on a zsh install only
affects: [02-15, phase-close, /gsd-secure-phase 02]

actuals:
  tasks: 3
  commits: 2       # RED test(02-14) and GREEN feat(02-14), counted after GREEN: git rev-list --count a855012..HEAD
plan_head_before: a8550127c065424b2618dc5d1cc8f2d8a062622e

tech-stack:
  added: []
  patterns:
    - "fpath registration: a zsh body that adds the script directory to fpath registers the completion wherever the block sits, so install never reorders the user's rc"
    - "rc I/O as bytes with surrogateescape on decode and encode; _splice_lines trims only a newline its own replacement added"
    - "duplicate sentinel blocks: keep the first, remove the rest, report once; a second install is a no-op"
    - "real-kitty probe run headless through make test-integration from a materialised tree, red at HEAD and green at the prototype, before any shipping edit"

key-files:
  created:
    - tmp/h41-zsh-fpath-completion/ (gitignored evidence: matrix.py, matrix.json, matrix.txt, tab.py, tab.json, tab.txt, timing.txt, rc.py, rc.json, rc.txt, run.py, kitty-head.txt, kitty-prototype.txt, repro.md, expected.json, actual.json, red-state.txt, red-state-integration.txt, guards-at-red.txt, lint-vs-red.txt, make-test.txt, make-doctor.txt, prototype/)
  modified:
    - src/kitty_setup/path_integration.py
    - src/kitty_setup/installer.py
    - src/kitty_setup/doctor.py
    - tools/uninstall.sh
    - README.md
    - pyproject.toml
    - tests/unit/test_path_integration.py
    - tests/unit/test_installer_completion.py
    - tests/unit/test_doctor.py
    - tests/unit/test_tools_uninstall_sh.py
    - tests/integration/test_completion_e2e.py
    - .planning/phases/02-defect-remediation/02-CONTEXT.md
    - .planning/phases/02-defect-remediation/02-VALIDATION.md

key-decisions:
  - "Register zsh completion through fpath, not by moving the block. The four-line body puts the script directory on fpath, so _my-kitty registers wherever the block sits. Rejected: a guarded PATH append as the last line (O1, registers nothing), a guarded PATH prepend after a sdkman line (O1b, registers nothing), and keeping the 02-02 move (O2 and O2b: position-dependent, and a completion block above compinit registers nothing)."
  - "The zsh completion file is _my-kitty with a #compdef header, so fpath autoloads it. The legacy my-kitty-completion.zsh is removed on a zsh install only; a bash install leaves it alone."
  - "The position FAIL in doctor is deleted. Doctor's verdict is measured equal to real zsh registration across five e2e shapes (three register, two do not). The one shape it cannot see, a compinit -C over a stale dump, is named in the zsh PASS detail and in the README."
  - "rc I/O is bytes (read_bytes, write_bytes, surrogateescape). Rejected: read_text with newline=, which does not exist on Path.read_text, and universal-newline text I/O, which translates CRLF and lone CR."
  - "Duplicate current blocks converge: keep the first, remove the rest, report removed duplicate rc block. Measured at HEAD: zsh installs left two markers after three runs."
  - "Doctor compares script.read_bytes() with generate_completion_script(shell).encode('utf-8') (A-4). A CRLF-only change is now stale."
  - "02-SECURITY.md is not edited. Its T-2-04, T-2-05 and A-4 rows are superseded in this summary and routed to /gsd-secure-phase 02."

patterns-established:
  - "Probe-first: a hypothesis directory under tmp/ holds the matrix, the TAB-press table, the rc measurements and a real-kitty run that is red at HEAD and green at the prototype, before any file under src/ is edited."

requirements-completed: [WR-05, WR-06 (rc half), IN-01, A-4]

duration: not measured (no start timestamp was recorded for this run)
completed: 2026-11-03
status: complete
---

# Phase 2 Plan 14: zsh completion registers through fpath, rc I/O is bytes, duplicate blocks converge, doctor compares bytes Summary

zsh completion now registers through `fpath` wherever the rc block sits, so install no longer moves a user's zsh block; rc I/O is byte-exact, duplicate blocks converge on a second install, and doctor's completion check compares bytes.

## Performance

- **Duration:** not measured (no start timestamp was recorded for this run)
- **Started:** not recorded
- **Completed:** 2026-11-03
- **Tasks:** 3 (Task 1 probe and RED, Task 2 GREEN implementation, Task 3 planning amendments, make captures and this SUMMARY)
- **Commits:** 2 (RED `test(02-14)`, GREEN `feat(02-14)`, the commit that carries this file)
- **Pre-work HEAD:** `a8550127c065424b2618dc5d1cc8f2d8a062622e` (the 02-13 docs commit `a855012`)

## Accomplishments

- A zsh block above `compinit` stays where the user put it and still registers `_my-kitty` (headless kitty TAB-press proof and the e2e module).
- Install rewrites a retained block's obsolete body in place (the 02-02-era body becomes the four-line fpath body) and changes no byte outside the markers.
- IN-01: two or three current blocks converge in one install; the second install is a no-op.
- WR-06 (rc half): a Latin-1 byte, CRLF and lone CR in the rc survive; an unterminated duplicate or legacy block removed at the end of the file no longer takes the newline of the line before it.
- A-4: doctor compares `script.read_bytes()` with the generated shellcode, so a CRLF-only change is reported as stale.
- The zsh script is `_my-kitty` with a `#compdef my-kitty` header; the legacy `my-kitty-completion.zsh` is removed on a zsh install only; zsh install clears group and world write on `~/.local/share/kitty-setup` (compaudit).

## Task Commits

1. **Task 1: probe and RED set** - `b097c66` (test) `test(02-14): RED set for fpath registration, in-place zsh upgrade, duplicate convergence and byte-exact rc I/O`. This commit was amended once from `3af96f6` to fix one E501 line in `tests/integration/test_completion_e2e.py` (deviation f). RED touches five test modules only.
2. **Task 2: GREEN implementation** - the commit whose subject begins `feat(02-14)`, which carries the source, tools, README, pyproject, the two planning amendments and this SUMMARY. Its hash is the `feat(02-14)` line in `git log`; a SUMMARY cannot name its own commit.
3. **Task 3: planning amendments and captures** - `02-CONTEXT.md` (additive dated bullet), `02-VALIDATION.md` (rows and a correction) and the make captures, all in GREEN.

## Evidence

Every capture is under `tmp/h41-zsh-fpath-completion/` (gitignored). The tables below quote the result of each run.

### Zsh shape matrix (`matrix.txt`, `matrix.json`)

zsh 5.9.2 at `/home/linuxbrew/.linuxbrew/bin/zsh`. Each shape runs two interactive starts; `registered` is the name zsh reports for `my-kitty`.

| Shape | Start 1 | Start 2 | Note |
| ----- | ------- | ------- | ---- |
| Z1 today: 02-02 block first, pyenv tail, no compinit | `_python_argcomplete` | `_python_argcomplete` | argcomplete's own function answers |
| Z2 today: 02-02 block first, then compinit | none | none | HEAD fails |
| Z3 today: 02-02 block first, then a framework file that runs compinit | none | none | HEAD fails |
| Z5 today: compinit, then 02-02 block last | `_python_argcomplete` | `_python_argcomplete` | |
| Z6 today: 02-02 block alone | `_python_argcomplete` | `_python_argcomplete` | |
| O3-1 first, then pyenv tail, no compinit | `_python_argcomplete` | `_python_argcomplete` | |
| O3-2 first, then compinit | `_my-kitty` | `_my-kitty` | |
| O3-3 first, then a framework file that runs compinit | `_my-kitty` | `_my-kitty` | |
| O3-4 last, after compinit | `_python_argcomplete` | `_python_argcomplete` | |
| O3-5 alone | `_python_argcomplete` | `_python_argcomplete` | |
| O3-6 first, then `compinit -C` over the default dump | `_my-kitty` | `_my-kitty` | |
| O1 guarded PATH append as the last line | none | none | rejected |
| O1b guarded PATH prepend after a sdkman line | none | none | rejected |
| O2 PATH block, then a completion block last (02-02 lines) | `_python_argcomplete` | `_python_argcomplete` | rejected: still position-dependent |
| O2b completion block above a compinit | none | none | rejected |

The `_python_argcomplete` rows show that argcomplete's own completion function answers for `my-kitty` in those shapes. The probe checks that TAB completes, not which function answers.

### Stale dump (`matrix.txt`)

| Shape | Start 1 | Start 2 |
| ----- | ------- | ------- |
| NC-A-O3 stale dump: O3 first, then `compinit -C -d` over a dump without `_my-kitty` | none | none |
| NC-A-02 stale dump: 02-02 block first, then `compinit -C -d` over a dump without it | none | none |
| NC-B-O3 stale dump: compinit, O3 block (self-init skipped), then `compinit -C` default | none | none |
| NC-B-02 stale dump: compinit, 02-02 block, then `compinit -C` default | none | none |
| FIX-1-O3: NC-A-O3 after deleting the `-d` dump once | `_python_argcomplete` | `_python_argcomplete` |
| FIX-2-O3: O3 block above the first compinit, then `compinit -C` default | `_my-kitty` | `_my-kitty` |

The stale-dump shapes register nothing. This is the disclosed limitation: a `compinit -C` over a dump written without `_my-kitty` drops the registration. The fixes are deleting the `-d` dump once, or moving the block above the first `compinit`. Doctor cannot see this shape; its zsh PASS detail names it.

### Compaudit (`matrix.txt`)

zsh rejects a group- or world-writable fpath directory or parent, except group-writable with a per-user group. Measured:

| Row | Permissions | Start 1 | Start 2 |
| --- | ----------- | ------- | ------- |
| C1 | our dir 0775, no per-user group | none | none |
| C2 | our dir 0777, no per-user group | none | none |
| C3 | our dir 0777, per-user group | none | none |
| C4 | our dir 0755, no per-user group | `_my-kitty` | `_my-kitty` |
| C5 | our dir 0775, per-user group (exempt) | `_my-kitty` | `_my-kitty` |
| C6 | our file 0664 in a 0755 dir, no per-user group | `_my-kitty` | `_my-kitty` |
| C7 | our dir 0775, no per-user group, the block alone | `_python_argcomplete` | `_python_argcomplete` |
| C8 | `~/.local/share` 0775, no per-user group | none (compinit aborted) | none (compinit aborted) |
| C9 | `~/.local/share` 0777, per-user group | none (compinit aborted) | none (compinit aborted) |
| C10 | `~/.local/share` 0775, no per-user group, the block last | `_python_argcomplete` | `_python_argcomplete` |
| C11 | 02-02 body last, `~/.local/share` 0775, no per-user group | `_python_argcomplete` | `_python_argcomplete` |

The write path clears group and world write on `~/.local/share/kitty-setup` (`path.parent.chmod(stat.S_IMODE(path.parent.stat().st_mode) & ~0o022)`). `~/.local/share` is not ours: where it is group- or world-writable, the measured fix is `chmod go-w ~/.local/share`, which the README now states.

### TAB presses (`tab.txt`, `tab.json`)

Real zsh under a pty, two TAB presses per shape, with a `my-kitty` symlink in `$HOME/.local/bin` for the sandbox:

| Shape | Completes to doctor |
| ----- | ------------------- |
| today-block-first-compinit | False |
| today-block-last-deferred-compinit | False |
| today-block-first-deferred-compinit | False (not gated) |
| O3-first-compinit | True |
| O3-last-after-compinit | True |
| O3-alone | True |
| O3-first-deferred-compinit | True |
| O3-first-compinitC-stale-default-dump | True |

Every O3 shape completes. Every 02-02-era shape that places the block before a `compinit` does not.

### Timing (`timing.txt`)

- `today_user_compinit_then_02_02_block_last`: 7.1 ms median of 30 (`zsh -i -c true`)
- `O3_first_then_user_compinit`: 12.0 ms median of 30 (`zsh -i -c true`)

The plan's figures were 8.7 ms and 11.9 ms. The measured values are recorded here (deviation d).

### rc measurements (`rc.txt`, `rc.json`) at HEAD

- WR-06 non-UTF-8: `read_text` raises `UnicodeDecodeError` on `# caf\xe9 alias` for both bash and zsh.
- WR-06 newline round trip: `read_text`/`write_text` with surrogateescape is not byte-exact (CR is lost); `read_bytes`/`write_bytes` is byte-exact. `Path.read_text` takes no `newline` keyword.
- WR-06 unterminated tail: HEAD `_splice_lines` loses the byte before an unterminated removed tail, for LF and for CRLF (the line ends `alias keep=yes` and the `\n` or `\r\n` is gone).
- IN-01: HEAD zsh, three installs over a duplicated block: `markers_left: 2` after each run, reason `moved rc block to end of file` each time. HEAD bash: `rc block already matches current template` with two markers left.
- Review scenario at HEAD: the zsh block sat above `export PATH="/opt/sdkman/bin:$PATH"` and `eval "$(pyenv init -)"`; HEAD moved it to the end, below both lines. The bytes outside the markers are otherwise unchanged.

### Kitty probe (`kitty-head.txt`, `kitty-prototype.txt`)

Headless real kitty through `make test-integration` from a materialised tree (`git read-tree` and `checkout-index` with a throwaway `GIT_INDEX_FILE`). The probe spawns kitty itself, one sandbox `HOME` per case.

- HEAD (`kitty-head.txt`): `2 failed, 5 passed in 30.15s`. The two failures are `test_h41_tab_completes[first_then_compinit]` (TAB did not complete `my-kitty doc` to `my-kitty doctor` on screen) and `test_h41_install_keeps_path_order` (install moved the block, so `~/.local/bin` precedes the user's `~/sdk/bin`). `test-integration: pytest exit status 1 (read from the child's status file; compositor exited 1)`. `head make status: 2`.
- Prototype (`kitty-prototype.txt`): `7 passed in 5.81s`. `test-integration: pytest exit status 0 (read from the child's status file; compositor exited 0)`. `prototype make status: 0`.

The probe file was materialised as `tests/integration/test_h41_probe.py` in the throwaway tree only. It is not in GREEN.

### O1, O2 and O3 comparison

- **O1 (guarded PATH append last):** registers nothing. Rejected.
- **O1b (guarded PATH prepend after sdkman):** registers nothing. Rejected.
- **O2 (PATH block then 02-02 completion block last):** registers `_python_argcomplete`, but depends on the block being last. Rejected.
- **O2b (completion block above compinit):** registers nothing. Rejected.
- **O3 (chosen; fpath body):** TAB completes in every O3 shape measured. The matrix names `_my-kitty` in the shapes where our block precedes `compinit` (O3-2, O3-3, O3-6) and `_python_argcomplete` in the others (O3-1, O3-4, O3-5). Costs 12.0 ms against 7.1 ms. Loses only the stale-dump shape, which is disclosed and fixed by deleting the dump once or moving the block above `compinit`.

## Install handoff at phase close

The installed `my-kitty` on this host predates 02-14. The plan says not to run `make install` in this run, so the handoff is a `my-kitty install` by the user. Expected effect, checked on a scratch HOME by `gate_upgrade.py`:

- the rc block between the markers is rewritten in place to the four-line fpath body;
- `~/.local/share/kitty-setup/_my-kitty` is written;
- `~/.local/share/kitty-setup/my-kitty-completion.zsh` is removed on a zsh install only; a bash install keeps it;
- no byte outside the markers changes;
- `~/.local/share/kitty-setup` loses group and world write on a zsh install;
- doctor's completion check PASSes, and a second install is a no-op.

On this host, `make doctor` (the installed pre-02-14 tool, read-only) reports `FAIL completion` because the installed rc body is the 02-02 template. That FAIL is expected until `my-kitty install` runs. It is not fixed by this plan's GREEN.

## make test

```text
make test exit status: 0
make: Entering directory '/var/home/bazzite/git/personal/kitty-setup'
============================= test session starts ==============================
platform linux -- Python 3.12.12, pytest-9.0.3, pluggy-1.6.0
rootdir: /var/home/bazzite/git/personal/kitty-setup
configfile: pyproject.toml
plugins: cov-7.1.0

collected 659 items

tests/integration/test_client_socket_discovery.py s                      [  0%]
tests/integration/test_color_normalization_e2e.py ssss                   [  0%]
tests/integration/test_completion_e2e.py ssssssss                        [  1%]
tests/integration/test_h01_cwd.py sss                                    [  2%]
tests/integration/test_h02_clear.py sss                                  [  2%]
tests/integration/test_h03_introspection.py sss                          [  3%]
tests/integration/test_h11_bindings_tab_nav.py ssss                      [  3%]
tests/integration/test_h12_bindings_window_nav.py sss                    [  4%]
tests/integration/test_h13_bindings_font_zoom.py ssss                    [  5%]
tests/integration/test_h14_bindings_detach.py sss                        [  5%]
tests/integration/test_h15_bindings_broadcast.py sss                     [  5%]
tests/integration/test_h16_bindings_url_hints.py sss                     [  6%]
tests/integration/test_h19_bindings_revert.py sss                        [  6%]
tests/integration/test_h21_doctor_remote_control.py s                    [  6%]
tests/integration/test_h21_remote_control_foundation.py ss               [  7%]
tests/integration/test_h22_window_title.py sssssss                       [  8%]
tests/integration/test_h23_styling.py ssssssss                           [  9%]
tests/integration/test_h24_layout_mirrored.py ssss                       [ 10%]
tests/integration/test_h25_scene_launcher.py ssssss                      [ 11%]
tests/integration/test_home_sandbox.py s                                 [ 11%]
tests/integration/test_scene_fill_tab_e2e.py ssssssssss                  [ 12%]
tests/integration/test_scene_recipe_e2e.py ssss                          [ 13%]
tests/unit/test_binding_introspection.py .....................           [ 16%]
tests/unit/test_cli.py .......................................           [ 22%]
tests/unit/test_config_updater.py ...................................... [ 28%]
....................                                                     [ 31%]
tests/unit/test_doctor.py ...............................                [ 35%]
tests/unit/test_doctor_remote_control.py .........                       [ 37%]
tests/unit/test_git_hooks.py .....................                       [ 40%]
tests/unit/test_harness_teardown.py ...                                  [ 40%]
tests/unit/test_installer_completion.py ......................           [ 44%]
tests/unit/test_installer_download.py ....                               [ 44%]
tests/unit/test_installer_seed_scenes.py .....                           [ 45%]
tests/unit/test_installer_uninstall.py ...........                       [ 47%]
tests/unit/test_integration_env_hygiene.py ....                          [ 47%]
tests/unit/test_integration_runner.py .........................          [ 51%]
tests/unit/test_kitty_session_env.py ..                                  [ 52%]
tests/unit/test_kitty_session_socket.py .....                            [ 52%]
tests/unit/test_makefile_clean.py ...                                    [ 53%]
tests/unit/test_makefile_targets.py ..                                   [ 53%]
tests/unit/test_path_integration.py .................................... [ 59%]
........                                                                 [ 60%]
tests/unit/test_pruner.py ..................                             [ 62%]
tests/unit/test_scenes_accent.py ...........                             [ 64%]
tests/unit/test_scenes_background.py .........                           [ 66%]
tests/unit/test_scenes_client.py ........                                [ 67%]
tests/unit/test_scenes_colors.py ....................................... [ 73%]
..........................                                               [ 77%]
tests/unit/test_scenes_font.py ........                                  [ 78%]
tests/unit/test_scenes_launcher.py ..................................... [ 83%]
..........................                                               [ 87%]
tests/unit/test_scenes_opacity.py .....                                  [ 88%]
tests/unit/test_scenes_recipe.py ...............................         [ 93%]
tests/unit/test_scenes_title.py .......                                  [ 94%]
tests/unit/test_tools_uninstall_sh.py ........                           [ 95%]
tests/unit/test_unit_hermeticity.py .............................        [100%]

=========================== short test summary info ============================
SKIPPED [1] tests/integration/test_client_socket_discovery.py: set KITTI_INTEGRATION=1 to run integration tests
SKIPPED [4] tests/integration/test_color_normalization_e2e.py: set KITTI_INTEGRATION=1 to run integration tests
SKIPPED [8] tests/integration/test_completion_e2e.py: set KITTI_INTEGRATION=1 to run integration tests
SKIPPED [3] tests/integration/test_h01_cwd.py:34: set KITTI_INTEGRATION=1 to run integration tests
SKIPPED [3] tests/integration/test_h02_clear.py: set KITTI_INTEGRATION=1 to run integration tests
SKIPPED [3] tests/integration/test_h03_introspection.py: set KITTI_INTEGRATION=1 to run integration tests
SKIPPED [4] tests/integration/test_h11_bindings_tab_nav.py: set KITTI_INTEGRATION=1 to run integration tests
SKIPPED [3] tests/integration/test_h12_bindings_window_nav.py: set KITTI_INTEGRATION=1 to run integration tests
SKIPPED [4] tests/integration/test_h13_bindings_font_zoom.py: set KITTI_INTEGRATION=1 to run integration tests
SKIPPED [3] tests/integration/test_h14_bindings_detach.py: set KITTI_INTEGRATION=1 to run integration tests
SKIPPED [3] tests/integration/test_h15_bindings_broadcast.py: set KITTI_INTEGRATION=1 to run integration tests
SKIPPED [3] tests/integration/test_h16_bindings_url_hints.py: set KITTI_INTEGRATION=1 to run integration tests
SKIPPED [3] tests/integration/test_h19_bindings_revert.py: set KITTI_INTEGRATION=1 to run integration tests
SKIPPED [1] tests/integration/test_h21_doctor_remote_control.py: set KITTI_INTEGRATION=1 to run integration tests
SKIPPED [2] tests/integration/test_h21_remote_control_foundation.py: set KITTI_INTEGRATION=1 to run integration tests
SKIPPED [7] tests/integration/test_h22_window_title.py: set KITTI_INTEGRATION=1 to run integration tests
SKIPPED [8] tests/integration/test_h23_styling.py: set KITTI_INTEGRATION=1 to run integration tests
SKIPPED [4] tests/integration/test_h24_layout_mirrored.py: set KITTI_INTEGRATION=1 to run integration tests
SKIPPED [6] tests/integration/test_h25_scene_launcher.py: set KITTI_INTEGRATION=1 to run integration tests
SKIPPED [1] tests/integration/test_home_sandbox.py: set KITTI_INTEGRATION=1 to run integration tests
SKIPPED [7] tests/integration/test_scene_fill_tab_e2e.py: set KITTI_INTEGRATION=1 to run integration tests
SKIPPED [3] tests/integration/test_scene_fill_tab_e2e.py:278: set KITTI_INTEGRATION=1 to run integration tests
SKIPPED [4] tests/integration/test_scene_recipe_e2e.py: set KITTI_INTEGRATION=1 to run integration tests
======================= 571 passed, 88 skipped in 11.08s =======================
make: Leaving directory '/var/home/bazzite/git/personal/kitty-setup'
```

## make doctor

`make doctor` runs the installed `my-kitty`, which predates 02-14. It is read-only evidence and was not run through `make install`.

```text
make doctor exit status: 2
make: Entering directory '/var/home/bazzite/git/personal/kitty-setup'
PASS kitty binary: /home/bazzite/.local/bin/kitty -> kitty 0.49.2 created by Kovid Goyal
PASS symlink: /home/bazzite/.local/bin/kitty -> /var/home/bazzite/.local/kitty.app/bin/kitty
PASS desktop entry: /home/bazzite/.local/share/applications/kitty.desktop
PASS config payload: /home/bazzite/.config/kitty/kitty-setup/kitty-setup.conf
PASS sentinel block: present in /home/bazzite/.config/kitty/kitty.conf
PASS parse check: /home/bazzite/.local/bin/kitty +runpy 'import sys; from kitty.config import load_config; bad = []; load_config(sys.argv[-1], accumulate_bad_lines=bad); [print(b, file=sys.stderr) for b in bad]; sys.exit(1 if bad else 0)' /home/bazzite/.config/kitty/kitty.conf exit=0
PASS bindings: 22 ours, 79 defaults, 0 conflicts
FAIL completion: the my-kitty block in /home/bazzite/.bashrc does not match the current template that sources /home/bazzite/.local/share/kitty-setup/my-kitty-completion.bash; run `my-kitty install` to rewrite it
SKIP remote-control: no running kitty
make: *** [Makefile:34: doctor] Error 1
make: Leaving directory '/var/home/bazzite/git/personal/kitty-setup'
```

## RED evidence

The RED commit is `b097c66`. Its tree was materialised in a throwaway index and run from there, so the counts are the RED tree's own. The full captures are under `tmp/h41-zsh-fpath-completion/`. This section quotes each capture's status and count lines and, for the failing runs, the `FAILED` list.

**red-state.txt (unit RED, exit 1):**

```text
pytest exit status: 1
FAILED tests/unit/test_path_integration.py::test_zsh_block_stays_in_place[pyenv_sdkman]
FAILED tests/unit/test_path_integration.py::test_zsh_block_stays_in_place[compinit_after]
FAILED tests/unit/test_path_integration.py::test_zsh_block_stays_in_place[framework_after]
FAILED tests/unit/test_path_integration.py::test_zsh_block_stays_in_place[stale_body_rewritten]
FAILED tests/unit/test_path_integration.py::test_zsh_body_adds_fpath - assert...
FAILED tests/unit/test_path_integration.py::test_zsh_upgrade_rewrites_in_place
FAILED tests/unit/test_path_integration.py::test_duplicate_rc_blocks_converge[bash]
FAILED tests/unit/test_path_integration.py::test_duplicate_rc_blocks_converge[zsh]
FAILED tests/unit/test_path_integration.py::test_rc_non_utf8_survives[bash-.bashrc]
FAILED tests/unit/test_path_integration.py::test_rc_non_utf8_survives[zsh-.zshrc]
FAILED tests/unit/test_path_integration.py::test_rc_line_endings_kept[bash_append]
FAILED tests/unit/test_path_integration.py::test_rc_line_endings_kept[zsh_rewrite_in_place]
FAILED tests/unit/test_path_integration.py::test_rc_unterminated_tail_removal[duplicate_lf]
FAILED tests/unit/test_path_integration.py::test_rc_unterminated_tail_removal[duplicate_crlf]
FAILED tests/unit/test_path_integration.py::test_rc_unterminated_tail_removal[legacy_crlf]
FAILED tests/unit/test_path_integration.py::test_path_report_reason_printed[removed_duplicate_rc]
FAILED tests/unit/test_installer_completion.py::test_zsh_script_written_as_fpath_function
FAILED tests/unit/test_installer_completion.py::test_legacy_zsh_script_removed_on_zsh_write
FAILED tests/unit/test_installer_completion.py::test_legacy_zsh_script_removed_on_uninstall
FAILED tests/unit/test_installer_completion.py::test_zsh_script_dir_not_group_or_world_writable
FAILED tests/unit/test_installer_completion.py::test_cli_install_writes_zsh_script_for_detected_shell
FAILED tests/unit/test_doctor.py::test_completion_block_position_is_not_a_failure
FAILED tests/unit/test_doctor.py::test_completion_rc_non_utf8_passes[bash] - ...
FAILED tests/unit/test_doctor.py::test_completion_rc_non_utf8_passes[zsh] - U...
FAILED tests/unit/test_doctor.py::test_completion_byte_compare_flags_crlf_only_as_stale
FAILED tests/unit/test_doctor.py::test_completion_zsh_pass_detail_names_fpath
FAILED tests/unit/test_tools_uninstall_sh.py::test_will_remove_list_names_the_completion_file_unless_keep_kitty
27 failed, 78 deselected in 0.27s
```

**red-state-integration.txt (integration RED, make status 2, runner status 1):**

```text
make test-integration exit status: 2
FAILED tests/integration/test_completion_e2e.py::test_zsh_block_above_compinit_stays_and_registers
FAILED tests/integration/test_completion_e2e.py::test_zsh_block_first_keeps_path_order
FAILED tests/integration/test_completion_e2e.py::test_doctor_verdict_matches_real_zsh_registration
3 failed, 5 deselected in 0.31s
test-integration: pytest exit status 1 (read from the child's status file; compositor exited 1)
make: *** [Makefile:40: test-integration] Error 1
```

**guards-at-red.txt (guards that must pass at RED):**

```text
pytest exit status: 0
3 passed, 102 deselected in 0.03s
make test-integration exit status: 0
5 passed, 3 deselected in 0.59s
test-integration: pytest exit status 0 (read from the child's status file; compositor exited 0)
```

**lint-vs-red.txt (ruff and pyright counts, RED against now):**

```text
tests/unit/test_path_integration.py pyright RED^=9 now=9 ruff RED^=0 now=0
tests/unit/test_installer_completion.py pyright RED^=0 now=0 ruff RED^=0 now=0
tests/unit/test_doctor.py pyright RED^=22 now=22 ruff RED^=1 now=1
tests/unit/test_tools_uninstall_sh.py pyright RED^=0 now=0 ruff RED^=0 now=0
tests/integration/test_completion_e2e.py pyright RED^=0 now=0 ruff RED^=0 now=0
```

The RED tree's unit failures are the 27 items above; the guards that already hold at HEAD (three unit, five integration) pass at RED.

## Planning documents

- **02-CONTEXT.md:** one additive dated bullet, `**Amended 2026-11-03 (02-14, gap closure of WR-05, WR-06, IN-01, A-4).**`, after the D-03 sub-bullet. Its numstat against RED is `1	0	.planning/phases/02-defect-remediation/02-CONTEXT.md` (one insertion, zero deletions). Line 26 keeps its original text; the dated bullet supersedes it.
- **02-VALIDATION.md:** rows 02-02-T1 and 02-02-T2 re-targeted (their predicate and reason checks now name the fpath body and `read_bytes`), rows 02-02-T3 and 02-07-T2 and the R1.1 Manual-Only row reworded, correction 22 added with the header `*(2026-11-03, 02-14 gap closure)*`. Re-run from the working tree: 02-02-T1 (four commands) and 02-02-T2 (three commands) all exit 0.
- **README.md:** the completion note is one paragraph covering `_my-kitty`, `fpath`, the `compinit -C` shape, `compaudit` and `chmod go-w ~/.local/share`.

## Gates

- Task 2 gates: all pass, including the doctor AST gate, the uninstall will-remove line, the README note, the pyproject B604 counts (x8 / x7 / x1, checked against bandit), the doctor and uninstall tokens, the absence re-run, the completion e2e module (8 passed), and the five settled tools (ruff, black, pyright, bandit, vulture).
- Task 3 static gates: all pass, including the scratch-home upgrade gate (`gate_upgrade.py`).
- Completion e2e module on the working tree, through `make test-integration` under `timeout`: `8 passed in 1.27s`, `test-integration: pytest exit status 0 (read from the child's status file; compositor exited 0)`, make status 0.
- `make test`: exit status 0, `571 passed, 88 skipped` (above).
- `make doctor`: exit status 2 from the installed pre-02-14 tool (above). Recorded, not fixed by this plan's GREEN.

## Deviations

- **(a)** The stale-dump probe is parametrised into two items (`dash_d`, `skipped_self_init`), so the headless probe has 7 items, not 6.
- **(b)** A `make` status line is appended to the two kitty captures (`head make status: 2`, `prototype make status: 0`).
- **(c)** The O1, O1b, O2 and O2b definitions are this run's own, written in `matrix.py`; the labels are the matrix's labels.
- **(d)** Timing is 7.1 ms (today) and 12.0 ms (O3), against the plan's 8.7 ms and 11.9 ms. The measured values are recorded.
- **(e)** `first_then_deferred_compinit` passed at HEAD, so it is recorded but not gated as RED.
- **(f)** RED was amended once, from `3af96f6` to `b097c66`, to wrap one E501 line in `test_completion_e2e.py`. The subject and five paths are unchanged.
- **(g)** `import stat` was removed from `src/kitty_setup/path_integration.py` (ruff F401). The prototype copy still has it; GREEN does not.
- **(h)** Pyright was run as `uv run --project <worktree> pyright src`, because `.venv/bin/pyright` could not resolve argcomplete.
- **(i)** `02-CONTEXT.md`, `02-VALIDATION.md` and this SUMMARY are written after the evidence run, as the plan requires, and committed in GREEN.
- **(j)** The materialised HEAD tree for the kitty runs is in `/tmp/tmp.gqQ6KXKv4p`, not inside the repository, and is removed in cleanup.
- **(k)** The RED captures are quoted as status and count lines plus the failing-item list, not as the full 889-line `red-state.txt`. The full files stay under `tmp/h41-zsh-fpath-completion/`.
- **(l)** No broken-windows ledger entries were appended: no stub, skipped test or unrun `<verify>` was left. The stale-dump shape is a disclosed limitation recorded in the README and in correction 22, not a defect entry.

## Known Stubs

None.

02-SECURITY.md follow-up: T-2-04 and T-2-05 superseded by T-2-60, T-2-62, T-2-63 and T-2-64 (02-14); /gsd-secure-phase 02 must re-verify them against GREEN

Stale citations under that follow-up (`02-SECURITY.md` is not edited):

- `02-SECURITY.md:51` (T-2-04) cites "the zsh block is moved to the end — `:146-155`" and the exact-equality tests `test_path_integration.py:72,346,367`. The move is deleted; the tests at `:72` and `:367` are deleted by RED. Superseded by T-2-60 (no move), T-2-62 (byte I/O) and T-2-63 (duplicate convergence). The `path_integration.py:166-191` and `:56` cites are the find-block mechanism and the `compinit -i` line, which still exist at other line numbers.
- `02-SECURITY.md:52` (T-2-05) cites doctor's decoded-text comparison at `doctor.py:278-288` and `test_doctor.py:201`. Superseded by T-2-64 (byte comparison).
- `02-SECURITY.md:139` (advisory A-4) cites the decoded-text comparison at `doctor.py:278-288`. Superseded by T-2-64.
- `02-CONTEXT.md:26` still calls the zsh position load-bearing; the dated 02-14 bullet supersedes it, and the line is kept as history.
- Frozen history that still describes the 02-02 design, not edited: `02-02-SUMMARY.md:478`, `02-02-PLAN.md:697-698`, `02-GAP-REVIEWS.md:691-692` and `:829`.

## Self-Check

- RED `b097c66` exists on `gsd/phase-02-defect-remediation` and touches five test modules only.
- The rc-block body, the `_my-kitty` file and the rc I/O behaviour were checked by the gates above.
- Working tree before GREEN: exactly the eight modified paths reported by `git status --short`, plus this SUMMARY.

## Self-Check: PASSED

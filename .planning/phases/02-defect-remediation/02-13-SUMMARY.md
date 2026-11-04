---
phase: 02-defect-remediation
plan: 13
subsystem: scenes
tags: [scene-launcher, send-text, shell-quoting, kitten, WR-02, WR-03, R1.4, tdd, real-kitty]
type: tdd

requires:
  - phase: 02-defect-remediation
    provides: plan 02-12 (integration HOME sandbox, sandbox_integration_home autouse fixture, unit host-state guard)
provides:
  - pane-0 typeable rule: pane 0's cwd and cmd are typed into the reused shell only as single-quoted literals of printable values with no single quote and no backslash, and a typed cwd is absolute and $-free
  - argv fallback to the new-tab path for every untypeable pane 0, with one stderr line
  - recipe loader refuses a NUL in any recipe string before any kitten call (SceneRecipeError, one my-kitty scene launch line, exit 1)
  - real-kitty evidence for the fish injection, the kitten escape injection, cross-pane cwd agreement, the zsh magicequalsubst literal and the fish typeable fill
affects: [02-14, 02-15, phase-close, /gsd-secure-phase 02]

actuals:
  tokens: 6821     # chars/4 over the added lines of the realised diff since ed4e717 (src, tests, the three planning amendments)
  tasks: 3
  commits: 2       # RED test(02-13) and GREEN feat(02-13), counted after GREEN: git rev-list --count ed4e717..HEAD
plan_head_before: ed4e7173e3cc2c62a26d6d5905ec9c5f9df6f962

tech-stack:
  added: []
  patterns:
    - "single-quoted send-text literals of values that pass a typeable predicate (printable, no quote, no backslash)"
    - "untypeable pane 0 falls back to the argv path, which kitty resolves in its own process, so pane 0's cwd means what every other pane's cwd means"
    - "real-kitty probe run headless through make test-integration from a materialised tree, red at HEAD and green at the prototype, before any shipping edit"

key-files:
  created:
    - tmp/h40-pane0-send-text/ (gitignored evidence: fake_sock.py, fishq.py, pty_line.py, run.py, prototype_launcher.py, prototype_recipe.py, decoded-lines.json, fishq-results.json, pty-results.json, expected.json, actual.json, repro.md, kitty-before.txt, kitty-prototype.txt, red-state.txt, red-state-integration.txt, lint-vs-red.txt, make-test.txt, make-doctor.txt, make-test-integration.txt)
  modified:
    - src/kitty_setup/scenes/launcher.py
    - src/kitty_setup/scenes/recipe.py
    - tests/unit/test_scenes_launcher.py
    - tests/unit/test_scenes_recipe.py
    - tests/integration/test_scene_fill_tab_e2e.py
    - .planning/phases/02-defect-remediation/02-CONTEXT.md
    - .planning/phases/02-defect-remediation/02-VALIDATION.md
    - .planning/REQUIREMENTS.md

key-decisions:
  - "Type pane 0 only when typeable: every character isprintable(), no single quote, no backslash. Rejected: shlex.quote, whose bare safe-word form lets zsh expand =bash and fish expand %self, and magicequalsubst rewrite /x/a==bash."
  - "Always single-quote a typed value (cd -- '<path>', bash -lc '<cmd>'). Inside single quotes bash and zsh expand nothing, and fish processes only backslash-quote and double backslash, which the rule excludes."
  - "A typed cwd is absolute, free of $, and normpath-normalised (kitty's abspath of an absolute path). Rejected: launcher-side expansion of ~ and $VAR, since kitty expands in its own environment and resolves relative paths against its own working directory (kitty/child.py), which the launcher cannot see."
  - "An untypeable pane 0 opens the scene in a new tab through argv (--cwd=<raw>, bash -lc <cmd>), with one stderr line. Rejected: shell detection (the foreground process is the querying kitten and cmdline names the login shell, measured), --stdin (fixes the decoding only), and refusing the scene."
  - "Refuse a NUL in recipe._require_str, before any kitten call. argv cannot carry a NUL; at HEAD subprocess.run raised an uncaught ValueError."
  - "D-08 amended in 02-CONTEXT.md on its own line, in D-12's format. No other line of that file changed."

patterns-established:
  - "Probe-first: a hypothesis directory under tmp/ holds the measurements and a real-kitty run that is red at HEAD and green at the prototype, before any file under src/ is edited."

requirements-completed: [R1.4]

duration: not measured (no start timestamp was recorded for this run)
completed: 2026-11-03
status: complete
---

# Phase 02 Plan 13: pane-0 typeable rule, argv fallback and NUL refusal Summary

**Pane 0 reaches the reused shell only as a single-quoted literal of a printable value with no quote or backslash; anything else opens the scene through argv in a new tab, and a NUL in a recipe is refused before any kitten call**

## Performance

- **Duration:** not measured (no start timestamp was recorded for this run)
- **Tasks:** 3 (Step 0 measurement and real-kitty proof, then RED, then GREEN)
- **Commits:** 2 (`test(02-13)` RED, `feat(02-13)` GREEN). The RED commit was amended three times, see Deviations.

## Accomplishments

- Step 0 proved the decision before any shipping edit. Against HEAD's launcher and loader, a real headless kitty showed the fish injection and the kitten-escape injection creating their sentinels, the cross-pane cases filling one tab, the zsh literal landing in the wrong directory, and the NUL probe dying with `ValueError: embedded null byte`. Against the prototype, all nine cases passed.
- `launcher.py`: `_typeable` (printable, no `'`, no `\`), `_pane0_typeable` (absolute `$`-free normalised `cwd`, typeable `cmd`), a one-line `_UNTYPEABLE_NOTE` on stderr, and `_fill_current_tab`'s two payloads are now `cd -- '<normpath>'` and `bash -lc '<cmd>'`. `import shlex` is gone.
- `recipe.py`: `_require_str` refuses a NUL with `SceneRecipeError`, so `_launch_named_scene` prints one `my-kitty scene launch:` line and returns 1 before any kitten call.
- `_launch_argv` is byte-identical to `1cbcaaa`. A typeable `cmd` still runs as `bash -lc`.
- Integration: all ten cases of `test_scene_fill_tab_e2e.py` pass headless with fish, zsh and bash present, none skipped, under the HOME sandbox.

## Step 0 evidence (`tmp/h40-pane0-send-text/`)

Measured before any shipping edit. Full outputs are in the directory and cited by path.

- `decoded-lines.json` (kitten 0.49.2 against a fake socket): `\x01` arrives as byte 0x01, `\\` as one backslash, `\'` as `'`, `\\'` as `\'`. For the two-backslash value, `cd`'s delivered form is `cd '…/a\'"'"'"; touch PWNED; #'`, and the one-backslash value's delivered form is one word.
- `fishq-results.json`: only the kitten-delivered two-backslash line runs its payload, and only in fish. The launcher-built one-backslash line also runs in fish when typed straight in, which round 1 already recorded. Bare `=bash` expands in zsh (`/usr/bin/bash`), bare `%self` in fish (its PID), and bare `/x/a==bash` under magicequalsubst (`/x/a=/usr/bin/bash`). Every single-quoted value prints identically in bash, zsh and fish. The `cd` rows match the plan's table.
- `pty-results.json`: the decoded Ctrl-A/Ctrl-E line creates the sentinel in bash, zsh and fish, with a control line typed first. `bash --noprofile --norc -i` leaves `.bash_history` after `exit` and after SIGHUP, and fish creates `.cache/fish`, `.config/fish` and `.local/share/fish`.
- Foreground measurement (`actual.json`): with fish running in the bash window, kitty reports the origin window's `cmdline` as `['bash', '--posix']` and its foreground process as `kitten @ … ls`. Shell detection from either is unsound.

## Real kitty, headless (`make test-integration`, materialised from HEAD)

Captured status and summary lines, verbatim:

```
E           AssertionError: injected command ran (fish): /tmp/pytest-of-bazzite/pytest-606/test_fill_tab_fish_injection_f0/PWNED
E           AssertionError: injected command ran (bash-escape): /tmp/pytest-of-bazzite/pytest-606/test_fill_tab_escape_sequence_0/PWNED
E                       ValueError: embedded null byte
7 failed, 2 passed in 28.67s
test-integration: pytest exit status 1 (read from the child's status file; compositor exited 1)
```

```
9 passed in 18.31s
test-integration: pytest exit status 0 (read from the child's status file; compositor exited 0)
```

The before run exited with make status 2 (make reports the failing child as a recipe error) and the prototype run with make status 0.

## Files Created/Modified

- `src/kitty_setup/scenes/launcher.py` - the typeable predicate, the pane-0 predicate, the fallback note and fallback decision in `launch_scene`, single-quoted payloads, `shlex` import removed.
- `src/kitty_setup/scenes/recipe.py` - `_require_str` refuses a NUL.
- `tests/unit/test_scenes_launcher.py` - fourteen fallback items, three typed-literal items, one normalisation case, the updated injection case; the roundtrip case is deleted and inverted to `cmd_quote`.
- `tests/unit/test_scenes_recipe.py` - three NUL items, with no kitten call allowed.
- `tests/integration/test_scene_fill_tab_e2e.py` - autouse `sandbox_fill_tab_home` (adds INPUTRC), seven new real-kitty cases beside the three existing ones.
- `.planning/phases/02-defect-remediation/02-CONTEXT.md` - D-08 amended on its own line.
- `.planning/phases/02-defect-remediation/02-VALIDATION.md` - row `02-04-T1`'s first command and description, prohibition guard 2, the T-2-12 and T-2-13 Control cells, the scope-honesty sentence, correction 21.
- `.planning/REQUIREMENTS.md` - R1.4 reworded, still `[x]`.

## D-08 amendment (as written in 02-CONTEXT.md)

The amendment is appended to the D-08 bullet's own line, in D-12's format, with the date and `02-13`. It states the typeable rule, the single quotes, the `\\'` shift through `send-text`, the absolute `$`-free normalised cwd, the argv fallback with its stderr line, the NUL refusal, the compatibility cost, the scope (bash, zsh and fish measured), and the rejected alternatives. No other line of the file changed.

## Payload, before and after

| Pane-0 value | HEAD (`shlex.quote`) | After 02-13 |
|--------------|----------------------|-------------|
| `cwd` `/a b/c` (typeable, absolute) | `cd '/a b/c'` | `cd -- '/a b/c'` (filled in place) |
| `cwd` `/x/a==bash` | `cd /x/a==bash` (bare; zsh magicequalsubst rewrites it) | `cd -- '/x/a==bash'` |
| `cwd` `/tmp/x/../y//z` | `cd /tmp/x/../y//z` | `cd -- '/tmp/y/z'` |
| `cwd` `~/d` | `cd '~/d'` (fails) | argv `--cwd=~/d`, kitty expands it, new tab |
| `cwd` `$KS_PANE0_DIR/sub` | typed as `cd '$KS_PANE0_DIR/sub'`, which the shell never expands, so the `cd` fails | argv `--cwd=$KS_PANE0_DIR/sub`, kitty expands it, new tab |
| `cwd` `-x`, `-`, `sub/dir` | typed bare by `shlex.quote` (`cd -x` is an option error, `cd -` is OLDPWD) | argv, new tab |
| `cwd` with a `'` or a `\` | typed (fish injection) | argv, new tab |
| `cmd` `=bash` | `bash -lc =bash` (zsh expands it) | `bash -lc '=bash'` |
| `cmd` `%self` | `bash -lc %self` (fish expands it) | `bash -lc '%self'` |
| `cmd` `echo "a b" 'c'` | typed, shlex-quoted | argv `bash -lc <raw>`, new tab |
| `cmd` with a backslash or a control character | typed (Ctrl-A reorder) | argv, new tab |
| `cwd` `/tmp/my dir; touch /tmp/PWNED` | `cd '/tmp/my dir; touch /tmp/PWNED'` | `cd -- '/tmp/my dir; touch /tmp/PWNED'` |
| recipe string with a NUL | uncaught `ValueError: embedded null byte` | `my-kitty scene launch: key 'pane.cwd' holds a NUL character, which no argv element can carry`, exit 1 |

The fallback stderr line, verbatim from `_UNTYPEABLE_NOTE`:

```
my-kitty scene launch: pane 0's cwd or cmd cannot be typed into the current shell unchanged (a quote, a backslash, a control or format character, or a cwd that is not an absolute path free of $); opening the scene in a new tab instead
```

## Unit and integration gates (captured)

Status and summary lines for the captures, verbatim:

```
make test exit status: 0
======================= 551 passed, 86 skipped in 11.13s =======================
```

```
make doctor exit status: 2
PASS kitty binary: /home/bazzite/.local/bin/kitty -> kitty 0.49.2 created by Kovid Goyal
PASS symlink: /home/bazzite/.local/bin/kitty -> /var/home/bazzite/.local/kitty.app/bin/kitty
PASS desktop entry: /home/bazzite/.local/share/applications/kitty.desktop
PASS config payload: /home/bazzite/.config/kitty/kitty-setup/kitty-setup.conf
PASS sentinel block: present in /home/bazzite/.config/kitty/kitty.conf
PASS parse check: /home/bazzite/.local/bin/kitty +runpy 'import sys; from kitty.config import load_config; bad = []; load_config(sys.argv[-1], accumulate_bad_lines=bad); [print(b, file=sys.stderr) for b in bad]; sys.exit(1 if bad else 0)' /home/bazzite/.config/kitty/kitty.conf exit=0
PASS bindings: 22 ours, 79 defaults, 0 conflicts
FAIL completion: the my-kitty block in /home/bazzite/.bashrc does not match the current template that sources /home/bazzite/.local/share/kitty-setup/my-kitty-completion.bash; run `my-kitty install` to rewrite it
SKIP remote-control: no running kitty
```

`make doctor` ran the already-installed `my-kitty`, not this branch's code. Its FAIL line is the stale installed completion block, which is 02-14's scope and was not fixed here. The gate that reads this capture records the exit status, and the plan does not assert it green.

```
make test-integration (test_scene_fill_tab_e2e.py) exit status: 0
10 passed in 18.99s
test-integration: pytest exit status 0 (read from the child's status file; compositor exited 0)
```

## RED evidence

Captured after the RED commit and before this SUMMARY. Full transcripts stay under `tmp/h40-pane0-send-text/` (gitignored); each required line is copied verbatim above or here.

```
pytest exit status: 1
22 failed, 72 deselected in 0.18s
```

```
make test-integration (RED) exit status: 2
E           AssertionError: injected command ran (fish): /tmp/pytest-of-bazzite/pytest-614/test_fill_tab_fish_injection_f0/PWNED
E           AssertionError: injected command ran (bash-escape): /tmp/pytest-of-bazzite/pytest-614/test_fill_tab_escape_sequence_0/PWNED
6 failed, 4 deselected in 24.41s
test-integration: pytest exit status 1 (read from the child's status file; compositor exited 1)
```

Per-file pyright and ruff counts, RED^ against the tree (`lint-vs-red.txt`):

```
tests/unit/test_scenes_launcher.py pyright RED^=43 now=43 ruff RED^=0 now=0
tests/unit/test_scenes_recipe.py pyright RED^=29 now=29 ruff RED^=0 now=0
tests/integration/test_scene_fill_tab_e2e.py pyright RED^=40 now=8 ruff RED^=0 now=0
```

The integration module's count fell from 40 to 8 because the RED test helpers now type the `kitten @ ls` JSON as `Any`. No count grew.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] RED test code added pyright findings, so the RED commit was amended three times**
- **Found during:** the lint-vs-RED gate after the RED commit.
- **Issue:** `_contains_run`'s `list[str]` annotation rejected a tuple (launcher, 43 to 44); `monkeypatch.setattr(launcher._client, ...)` raised `reportPrivateUsage` (recipe, 29 to 30); the new helpers and the `ls`-typed `_tabs` raised about 25 unknown-type findings (integration, 40 to 65).
- **Fix:** `Sequence[str]`; the string target `"kitty_setup.scenes._client.kitten_at"`, the form the launcher module already uses; `_tabs` parses the JSON as `Any` with an explicit return type, and the `ls` import is dropped.
- **Commits:** the RED commit moved `3cf3bed` to `6cbbabe` to `ea4ce73` to `2a92120`, each with `git commit --amend --no-edit -- <explicit path>`. The subject and the three-module file set are unchanged. The amendment was allowed because RED was never pushed.
- **Verified by:** the RED-scope, RED-state, RED-integration and lint gates, all re-run against `2a92120`.

**2. [Rule 3 - Blocking] pyright ran with `--pythonpath <venv>/bin/python`**
- **Found during:** the lint and tools gates. Without it pyright resolved the wrong interpreter. This matches 02-12's deviation 4.

**3. [Rule 3 - Blocking] The Step 0 fake socket lives in a `mktemp -d` directory under the default temp root**
- **Reason:** the plan requires a short `mktemp -d` directory for `sun_path`. The scratchpad path is too long for a unix socket.
- **Effect:** the directory is removed by the driver's `finally`. No kitty was spawned against it.

### Deviations from the plan's capture form

**4. Full RED and capture transcripts are cited by path, not inlined.** The plan asks for each to be inlined verbatim. They run to tens of kilobytes, so this SUMMARY copies every line the SUMMARY gate requires, verbatim, and cites the file for the rest. Nothing was retyped.

**5. The `make test` count of 86 skipped** includes integration modules that skip without `KITTI_INTEGRATION=1`, such as `test_scene_recipe_e2e.py`. That is pre-existing behaviour, not an effect of this plan.

### Process notes

- **Probe-only cases.** `test_h40_nul_recipe_refused_before_kitten` and `test_h40_foreground_is_the_querying_process` were run in the Step 0 probe only. The NUL behaviour is covered by the three unit items, and the foreground finding is recorded in `actual.json`.
- **Launcher-built fish injection.** Step 0 showed the launcher-built one-backslash line, typed straight into fish, runs `touch`. The plan's expectation covered only the kitten-delivered lines. The shipping rule refuses that value regardless, so no behaviour changed.
- **Duration** was not measured. No start timestamp was recorded for this run.

## Known Stubs

None.

## Threat Flags

None beyond the plan's threat register. The register's T-2-56 to T-2-59 and T-2-77 to T-2-78 are mitigated as stated, and T-2-SC installs nothing.

## 02-SECURITY.md follow-up

02-SECURITY.md follow-up: T-2-12 and T-2-13 superseded by T-2-56, T-2-57 and T-2-58 (02-13); /gsd-secure-phase 02 must re-verify them against GREEN

The three stale citations the re-verification must replace:
- T-2-12 cites `launcher.py:269` `cd {shlex.quote(...)}`, which GREEN removes. Superseded by T-2-56, T-2-57 and T-2-58.
- T-2-13 cites `launcher.py:280` `bash -lc {shlex.quote(...)}`, which GREEN removes. Superseded by T-2-56 and T-2-57.
- The audit trail's `shlex.quote(` count in `_fill_current_tab` now reads 0.

This plan does not edit `02-SECURITY.md`. The re-run of `/gsd-secure-phase 02` is the route for the refresh.

## Self-Check

- The RED commit holds exactly the three test modules (`gate_red_scope.sh`, exit 0).
- The RED unit selection fails 22 items and passes none (`red-state.txt`). The integration selection fails 6 and skips none (`red-state-integration.txt`).
- The GREEN implementation passes its gates: the AST predicate, the payload AST gate, the fourteen fallback items, the typed-literal and normalisation items, the NUL items, the guards, and `_launch_argv` identical to `1cbcaaa`.
- The five settled tools are clean on `src/`. `make test` passes 551, and the integration module passes 10 with none skipped.

## Self-Check: PASSED

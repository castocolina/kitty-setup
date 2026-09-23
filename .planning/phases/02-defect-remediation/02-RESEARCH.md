# Phase 2: Defect Remediation — Research

**Researched:** 2026-09-23
**Researcher:** gsd-phase-researcher (no commit, no stage — one file written)
**Domain:** Python CLI packaging (uv tool install), shell completion (argcomplete), kitty remote
control, bash bootstrap scripts, five-tool Python quality gate
**Confidence:** HIGH for every R1.x behaviour (all measured live on this host); HIGH for the
R0.11 sizing (all five tools run); MEDIUM only where noted in the Assumptions Log.

**Host of record for every measurement below:** Bazzite, `Linux 7.2.4-ogc3.1.fc44.x86_64`,
bash 5.3.9, zsh 5.9.2, kitty 0.49.0, `$SHELL=/bin/bash`, argcomplete 3.6.3 in the repo venv and
**3.7.2** in the installed uv tool venv. Repo at `27a152a`.

**Re-verified at `c288c46`.** Phase 1 finished and committed in the primary worktree *while* this
research ran, moving `HEAD` from `27a152a` to `c288c46` on `gsd/phase-01-governance-freeze`. The
delta is `AGENTS.md` (+16/−10) and `tests/unit/test_git_hooks.py` (+28/−9) only —
`git diff --stat 27a152a..HEAD -- src/ tests/ tools/ Makefile pyproject.toml .claude/conventions.md`
touches nothing else. All 13 spot-checked defect-site lines still hold verbatim at `c288c46`
(`doctor.py:98,205`, `installer.py:180`, `config_updater.py:194`, `launcher.py:238`,
`colors.py:79`, `pruner.py:28`, `kitty_session.py:292`, `Makefile:27`, `uninstall.sh:17`,
`test_h25_scene_launcher.py:394`, `test_scene_recipe_e2e.py:75`, `test_path_integration.py:151`),
and every `AGENTS.md` rule quoted in §"Project Constraints" survives the rewrite.
One addition is directly load-bearing for R1.1 — `AGENTS.md` now states: *"Phase 1's branch merges
after Phase 2's R1.1 turns `make doctor` green."* `[VERIFIED: git diff 27a152a..c288c46, 2026-09-23]`

---

## ⚠ STOP HERE FIRST — findings that make a locked decision unworkable

The planner cannot reopen a locked decision; the user can. These three items are not
preferences — they are measured facts that contradict the text of D-12, D-13 and D-03. Nothing
else in this document is blocked on them.

### U-1 — D-13's `close-os-window` verb **does not exist**. BLOCKING.

D-13: *"harness teardown issues `close-os-window` instead of `close-window` (`kitty_session.py:292`)"*.

```
$ kitten @ --to=unix:<harness-sock> close-os-window --match=all
Error: close-os-window is not a known subcommand for @. Use --help to get a list of valid subcommands.
exit=1
```
`[VERIFIED: h32/live-evidence-3.txt]`

The full `kitten @` subcommand list on kitty 0.49.0 contains `close-tab`, `close-window`,
`resize-os-window`, `set-os-window-title` — and **no** `close-os-window`
`[VERIFIED: h32/live-evidence-4-verbs.txt]`.

Worse, the verb it would replace works correctly, including in the multi-OS-window case the
change is presumably meant to fix:

```
[close-window]    before: os-windows=2 windows=3
[close-window]    close-window --match=all -> exit=0 err=''
[close-window]    after: socket gone (kitty exited)   process poll=0
[close-os-window] before: os-windows=2 windows=3
[close-os-window] close-os-window --match=all -> exit=1 err='... not a known subcommand ...'
[close-os-window] after: STILL ALIVE os-windows=2 windows=3   process poll=None
```
`[VERIFIED: h32/live-evidence-3.txt]`

Implementing D-13 literally makes teardown *worse*: `_close_window_then_terminate` wraps the
call in `except HarnessCommandError: pass` (`kitty_session.py:293-294`), so the error is
swallowed, kitty is left running, and teardown falls through to `_process.wait(timeout=...)` →
SIGTERM → SIGKILL on every single integration test.

**Two viable alternatives, both measured:**

| Option | Command | Evidence |
|---|---|---|
| A — keep `close-window` | no change; drop this item from D-13 | `close-window --match=all` exits 0 and kitty exits cleanly with 2 OS windows / 3 windows |
| B — use the mappable action | `kitten @ action close_os_window` | `close_os_window` **is** a mappable kitty action `[VERIFIED: h32/live-evidence-5.txt]` |

Option B carries a caveat the planner must know: `kitten @ action` has no `--match`, so it acts
on the active OS window only and would need a loop over `ls` output. **Recommendation: Option A**
— drop the verb change, and instead spend the edit on `contextlib.suppress`, which the same line
needs for R0.11 (`ruff SIM105 kitty_session.py:291`). That converts a regression into two wins.

### U-2 — D-12's passthrough list names three forms kitty 0.49.0 rejects. NOT blocking, but wrong.

D-12: *"Passthrough is narrowed from 'contains `:` or `(`' to real `rgb:`/`rgba:`/functional
forms"*. Measured against the live kitten, which is the code path `normalize_color` feeds:

| value | `set-colors background=` | `set-tab-color active_bg=` |
|---|---|---|
| `#0a7` | exit 0 | exit 0 |
| `red` | exit 0 | exit 0 |
| `teal` | exit 1 `teal is not a valid color` | exit 1 |
| `rgb:00/ff/00` | **exit 0** | **exit 0** |
| `rgb:0/f/0` | **exit 0** | **exit 0** |
| `rgba:00/ff/00/80` | **exit 1** `not a valid color` | **exit 1** |
| `rgb(1,2,3)` | **exit 1** | **exit 1** |
| `rgba(1,2,3,0.5)` | **exit 1** | **exit 1** |
| `hsl(120,50%,50%)` | **exit 1** | **exit 1** |
| `foo:bar` | exit 1 | exit 1 |
| `""` / `" "` | exit 1 ` is not a valid color` | exit 1 |
| `NONE` / `none` | **exit 1** `The color background cannot be set to none` | **exit 0** |

`[VERIFIED: h32/live-evidence.txt, h32/live-evidence-2.txt]`

So the only passthrough form kitty accepts is **`rgb:`**. Narrowing to
"`rgb:`/`rgba:`/functional" would keep three dead forms alive and let them reach kitten, which is
exactly the failure D-12 exists to stop. The narrow-to-`rgb:`-only reading satisfies D-12's
stated *purpose* ("so `foo:bar` is rejected up front") strictly better.

Consequence for the existing suite: `tests/unit/test_scenes_colors.py:124` asserts
`normalize_color("rgba(1,2,3,0.5)") == "rgba(1,2,3,0.5)"` — a value kitty rejects. That test
encodes the wrong contract and must be inverted (expect `ColorError`), not preserved.
`test_scenes_colors.py:123` (`rgb:00/ff/00`) survives unchanged.

**Recommendation:** narrow to `rgb:` (case-insensitive prefix, `rgb:H{1,4}/H{1,4}/H{1,4}`) and
reject everything else. If the user wants `rgb()`/`hsl()` support, that is a *new feature*
(translate to hex client-side), not a passthrough, and belongs outside Phase 2.

### U-3 — D-03's rationale is factually false. The instruction survives; the test must change.

D-03: *"The generated file must be regenerated whenever the CLI surface changes."*

```
$ for n in doctor prune keys scene uninstall install; do grep -c -w "$n" gen-bash.sh; done
0
0
0
0
0
0
$ grep -o 'my-kitty' gen-bash.sh | sort | uniq -c
      3 my-kitty
```
`[VERIFIED: h30/evidence/12-staleness-and-producer.txt]`

The generated script contains **zero** subcommand names. It is a generic dispatcher that re-execs
`my-kitty` with `_ARGCOMPLETE=1` and reads the candidate list off fd 8 at completion time
(`gen-bash.sh:37,60`). A CLI-surface change therefore cannot stale it.

What *can* stale it: (a) the installed argcomplete version changing its shellcode — real, since
the tool venv resolves **3.7.2** while `uv.lock` pins **3.6.3**
`[VERIFIED: h30/evidence/03-argcomplete-version.txt]`; (b) the executable name changing (the
`my-kitty-setup` → `my-kitty` rename already happened once).

**D-03's instruction — "generation belongs to the install path, not a one-off script" — is
correct and should be implemented as written.** Only its *reason* changes, and with it the
regression test: do **not** write a test asserting "add a subcommand ⇒ file changes" (it will
fail). Assert instead that the on-disk file is byte-identical to a freshly generated
`argcomplete.shellcode(["my-kitty"], shell=<shell>)`. That is also the honest doctor check (see
R1.1 §6).

---

<user_constraints>
## User Constraints (from `02-CONTEXT.md`)

### Locked Decisions

**R1.1 — shell completion on a uv-tool install**
- **D-01:** Ship a **generated static completion file** instead of relying on a runtime helper. At install time, produce the shell-specific script (`register-python-argcomplete --shell bash|zsh my-kitty`) into `~/.local/share/kitty-setup/`, and make the rc block **source** that file rather than `eval`-ing a helper lookup. Doctor then checks a file we own plus the rc source line. — **Reversibility:** reversible — install step, rc block body, one doctor check.
- **D-02:** Root cause, already diagnosed (no research needed, only verification): the helper **does** exist at `~/.local/share/uv/tools/kitty-setup/bin/register-python-argcomplete`, but `uv tool install` exposes only the package's own entry point (`my-kitty`), so it is never on PATH. The rc block in `~/.bashrc` is correct and guards with `command -v register-python-argcomplete`, which is why completion fails silently while doctor reports it. Rejected alternatives: hardcoding the uv-internal venv path (uv owns it and may move it), and `uv tool install argcomplete` as a second global tool (installs something unrelated on the host).
- **D-03:** The generated file must be regenerated whenever the CLI surface changes, so generation belongs to the install path, not to a one-off script. Planner: verify the argcomplete invocation and the sourcing form by experiment on both `bash` and `zsh` before wiring it (the host's `$SHELL` is `/bin/bash`; `~/.zshrc` exists with no block).

**R1.2 — `make clean`**
- **D-04:** `clean` is made to match its help text: strip our config block and wipe `./tmp/`, **keeping** `kitty.app`, the `~/.local/bin/kitty` symlink, the desktop entry and every backup. Implement with the flags that already exist (`my-kitty uninstall --keep-kitty --keep-backups`). `make uninstall` remains the destructive path. Rejected: renaming the target to `purge` — that leaves no safe "reset my config" verb.
- **D-05:** The Makefile ≤5-lines-per-target rule holds; if the invocation grows past it, dispatch into `tools/` or a `my-kitty` subcommand per the stack rule.

**R1.3 — `tools/uninstall.sh`**
- **D-06:** `log` writes to **stderr** inside `resolve_binary` so its output never contaminates `$(resolve_binary)`, and the error branch's message becomes visible. The legacy-binary branch works afterwards.
- **D-07:** Regression tests for the shell script are **pytest subprocess tests** with a fake `HOME`/`PATH` — not bats, not shellcheck-as-a-test. Forced by the stack rule (Python is the stack; shell exists only inside `tools/`), so this is a constraint, not a preference. The script cannot be ported into `my-kitty` wholesale: its whole purpose is to work when the binary is missing or legacy.

**R1.4 — scene fill-current-tab**
- **D-08:** Shell-quote pane-0's `cwd` (`shlex.quote`) before it is sent via `send-text` (`launcher.py:238`), and give pane-0's `cmd` the same `bash -lc` semantics every other pane gets (`launcher.py:242-246` vs `_launch_argv`). Regression test: a scene whose `cwd` contains a space and a shell metacharacter.

**R1.5 — config parse check**
- **D-09:** The check reports the command it actually runs (`kitty +runpy load_config`, not `--debug-config`), surfaces the parser's stderr on failure instead of discarding it, and rolls the payload directory back — currently only the conf file is rolled back (`config_updater.py:194-212,271-281`). The doctor label is corrected (`doctor.py:98`).

**R1.6 — environment-dependent tests**
- **D-10:** `tests/integration/test_h25_scene_launcher.py` and `test_scene_recipe_e2e.py` strip `KITTY_WINDOW_ID` from the copied environment, as `test_color_normalization_e2e.py` already does. Otherwise a run from inside a kitty window takes the fill-current-tab path and the new-tab assertions fail.

**R1.7 — minor defects**
- **D-11:** **Install log: deleted, not relocated.** `_record_install_log` (`installer.py:180-183`) is removed entirely — nothing reads it, and the kitty-install spec that required it is frozen history as of Phase 1. R1.7's wording is updated from "relocate" to "remove", and the ROADMAP criterion with it.
- **D-12:** **Colors:** an empty or whitespace-only color is treated as **absent** — no kitten argument is emitted for it — matching the recipe loader's existing empty-string→`None` convention (`recipe.py:_normalise`). This replaces today's `normalize_color(c) or c` fallback, which lets `background=` reach kitten. Passthrough is narrowed from "contains `:` or `(`" to real `rgb:`/`rgba:`/functional forms, so `foo:bar` is rejected up front instead of half-building a scene. Rejected: raising on empty — it would break a recipe that spells out `bg = ""`.
- **D-13:** Remaining minors, each with a regression test: guard `int(result.stdout.strip())` in the launcher (`:258,373,396`) into a clean error instead of a traceback; `prune --keep <0` becomes an argparse error rather than an uncaught `ValueError` (`pruner.py:28-29`); harness teardown issues `close-os-window` instead of `close-window` (`kitty_session.py:292`); doctor's three "skipped — …" results return a real SKIP state instead of `passed=False` (`doctor.py:91,103,111` — `CheckResult` already has the `skipped` field); the PATH-migration messages ("migrated legacy marker" / "removed duplicate legacy marker") are actually printed (`installer.py:308-320` ignores the reason `path_integration` computes); and the unsupported-shell hint prints **both** the PATH export line and the completion line (`path_integration.py:59`).

### Claude's Discretion
- Whether the completion file is generated by a `my-kitty` subcommand or inline in the install path (D-01/D-03).
- Test placement per defect (unit vs integration) and how the fake-HOME fixture for the shell tests is built (D-07).
- Whether `doctor`'s SKIP refactor changes `CheckResult.__str__` or only the call sites (D-13).
- Plan decomposition: `granularity: fine` is configured, so splitting these into several small plans is expected — but every plan in this phase must keep `make test` green on its own.

### Deferred Ideas (OUT OF SCOPE)
- **R1.8 macOS chord attribution** — assigned to Phase 3, where it is a prerequisite of the oracle's attribution assertion. Not touched here.
- **Kitty never upgraded on reinstall** (`installer.py:194-196` skips whenever the binary exists) — explicitly out of scope for this milestone per PROJECT.md.
- **`doctor` remote-control FAIL format and the missing `make setup` hint** — doc/message accuracy, owned by Phase 8 (R6.1) unless a plan here touches the same line anyway.
- **Test-suite duplication** between `tests/conftest.py:23-41` and `tests/integration/_helpers.py` — noticed during the audit, not a defect; candidate for Phase 8 or a later cleanup.
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description (from `.planning/REQUIREMENTS.md`) | Research support |
|----|-----|-----|
| R1.1 | `my-kitty doctor`'s shell-completion check passes on a uv-tool install; static file + rc source line. **Release gate for Phase 1's merge.** | §R1.1 — full hypothesis h30, GREEN on bash and zsh with a real TAB keypress. Correction U-3. |
| R1.2 | `make clean` behaviour and help text agree; MUST NOT delete `kitty.app` or backups. | §R1.2 — current recipe measured to delete both. |
| R1.3 | `tools/uninstall.sh` logs to stderr inside `resolve_binary`; legacy branch works; errors visible. | §R1.3 — reproduced (exit 127; silent exit 1). D-07 test shape given verbatim. |
| R1.4 | Pane-0 `cwd` shell-quoted; pane-0 `cmd` honours `bash -lc`. | §R1.4 — injection reproduced in-process. |
| R1.5 | Parse check reports the real command, surfaces stderr, rolls back the payload dir; doctor label fixed. | §R1.5 — reproduced, plus a stronger finding about what the check silently misses. |
| R1.6 | Integration tests strip `KITTY_WINDOW_ID` (h25, `scene_recipe_e2e`). | §R1.6 — both sites confirmed, plus five more un-stripped sites triaged. |
| R1.7 | Install log removed; `int(stdout)` guarded; empty colors absent + passthrough narrowed; `prune --keep <0` argparse error; harness teardown verb; doctor SKIP; PATH-migration messages; unsupported-shell hint prints both lines. | §R1.7 — each item measured. Corrections U-1 and U-2. |
| R0.11 | `src/` clean under ruff, black, pyright, bandit, vulture — hard gate from this phase onward. | §R0.11 — all five tools run; per-shape breakdown and a sizing verdict. |
</phase_requirements>

## Summary

Every one of the seven R1 defects reproduces on this host, and all but two of the 32 file:line
references in `02-CONTEXT.md` still point at the code they claim (§Drift audit). The phase is
therefore well-scoped and low-risk — **with three exceptions flagged above**, one of which (U-1)
would actively regress the integration harness if implemented literally.

R1.1, the one item that gates two phases' merges, is **solved and proven**. A static completion
file generated at install time and sourced from the rc block yields working TAB completion on
both bash 5.3.9 and zsh 5.9.2, demonstrated with a real keypress on a pty inside a fake `HOME`
(§R1.1). Two facts the locked decisions did not anticipate shape the implementation: the bash and
zsh outputs of `register-python-argcomplete` are **byte-identical** in argcomplete 3.7.2, and the
zsh path needs `compinit` to have run **before** our source line or it errors loudly on every
shell start. Both are handled by making the rc block body shell-dependent, which the current
static `_BLOCK_BODY_LINES` tuple cannot express.

R0.11 is the phase's largest single piece of work and is **not** what the recorded baseline
suggests. `src/` carries 15 pyright errors (not 19) in three shapes, 9 ruff findings in five
shapes, 2 black files, 27 bandit findings, and 16 vulture findings of which roughly nine are
false positives created by scanning `src` alone. The majority of the remaining work is
*tool-configuration policy* — and `.claude/conventions.md` forbids `# noqa`, so each suppression
needs a justified `pyproject.toml` entry. Six of the eight bandit MEDIUM findings are a single
false positive: bandit reads the `shell=detected_shell` keyword in a `PathEditResult(...)`
constructor as `shell=True`.

**Primary recommendation:** five plans. `02-01` R1.1 (the merge gate, TDD, largest); `02-02`
R1.2+R1.3 (Makefile + shell script, one pytest-subprocess test module); `02-03` R1.4+R1.5
(launcher quoting + parse check); `02-04` R1.6+R1.7 (the minors — with U-1 and U-2 resolved by
the user before this plan is written); `02-05` R0.11 **last**, because three of its findings sit
on lines the earlier plans edit.

## Architectural Responsibility Map

| Capability | Primary tier | Secondary tier | Rationale |
|---|---|---|---|
| Generate the completion script | Python install path (`installer.py`) | — | Must run inside the installed tool venv, where argcomplete lives; `tools/setup.sh` already hands off to `my-kitty install` (`tools/setup.sh:13`) |
| Write / migrate the rc block | Python (`path_integration.py`) | — | Already owns sentinel-bracketed rc editing, including legacy migration |
| Own the completion file on disk | Filesystem `~/.local/share/kitty-setup/` | `installer.remove_kitty_install` | Nothing else writes under that path today (§R1.1 ¶5) |
| Consume the completion script | Shell runtime (bash readline / zsh zle) | — | Not observable from Python; doctor can only check structure + the producer protocol |
| Validate install health | Python (`doctor.py`) | subprocess into `my-kitty` | Doctor can run the `_ARGCOMPLETE` producer protocol out-of-band (measured) |
| Bootstrap when the binary is missing | Bash (`tools/uninstall.sh`) | — | Its purpose is to work when `my-kitty` is absent or legacy — cannot be a subcommand (D-07) |
| Colour validation | Python (`scenes/colors.py`) | kitty (final authority) | Client-side rejection before any kitten call; kitty 0.49.0's accepted set is now measured |
| Remote-control verbs | kitty 0.49.0 `kitten @` | — | The verb vocabulary is kitty's, not ours (U-1) |

## Canonical reference drift audit

`02-CONTEXT.md` was gathered 2026-09-22; this audit is 2026-09-23 at `27a152a`. **32 references
checked, 2 drifted, both off-by-one and non-substantive.**

| Reference | Status | Measured |
|---|---|---|
| `doctor.py:205-238` `_check_completion` | ✅ | `def _check_completion` is line 205; body ends 238 |
| `doctor.py:91,103,111` false-FAIL "skipped" | ✅ ×3 | all three exact |
| `doctor.py:98` wrong parse-check label | ✅ | `f"kitty --debug-config exit=…"` |
| `doctor.py:26` `CheckResult.skipped` | ✅ | `skipped: bool = False` |
| `path_integration.py:19-42` rc block body | ✅ | markers 19-20, `COMPLETION_LINE` 27, `_BLOCK_BODY_LINES` 37-42 |
| `path_integration.py:59` unsupported-shell hint | ✅ | `manual_line: str = EXPORT_LINE` |
| `installer.py:180-183` `_record_install_log` | ✅ | exact; sole call site is `:210` |
| `installer.py:308-320` PATH-migration messages | ✅ | `_print_path_result`, exact |
| `config_updater.py:194-212` `_parse_check` | ✅ | exact |
| `config_updater.py:271-281` rollback | ✅ | `parse_ok` at 271, `raise` text at 280 |
| `launcher.py:238` unquoted `cd` | ✅ | `f"cd {p0.cwd}\n"` |
| `launcher.py:242-246` pane-0 `cmd` | ✅ | `if p0.cmd is not None:` 242, `send-text` 244 (region 242-245) |
| `launcher.py:258,373,396` `int(stdout)` | ✅ ×3 | all three exact |
| `colors.py:64-88` `normalize_color` | ✅ | exact; passthrough at 79-80 |
| `accent.py:32`, `background.py:30` `or c` | ✅ ×2 | both exact |
| `pruner.py:28-29` `--keep` ValueError | ✅ | `if n < 0:` 28, `raise` 29 |
| `kitty_session.py:292` teardown verb | ✅ | `self._kctl("close-window", "--match=all")` |
| `Makefile:12` help | ✅ | `clean  strip our config block + wipe ./tmp/ scratch (keeps kitty + binary)` |
| `Makefile:26-28` clean recipe | ❌ **DRIFT** | `clean:` is **27**; the recipe is **28-29**. Line 26 is blank. Corrected range: **`Makefile:27-29`** |
| `tools/uninstall.sh:17` `log` to stdout | ✅ | `log() { printf '[uninstall] %s\n' "$*"; }` |
| `tools/uninstall.sh:28-40` legacy + error branches | ✅ | exact |
| `tools/uninstall.sh:97` `$(resolve_binary)` | ✅ | `binary="$(resolve_binary)"` |
| `test_h25_scene_launcher.py:393` env not stripped | ❌ **DRIFT** | `env = dict(os.environ)` is **394**; 393 is the trailing comment line. Corrected: **`:394`** |
| `test_scene_recipe_e2e.py:75` env not stripped | ✅ | exact |
| `test_color_normalization_e2e.py:33` correct pattern | ✅ | `env.pop("KITTY_WINDOW_ID", None)` |
| `test_path_integration.py:226` migration tested | ✅ | `def test_idempotent_after_migration` |
| `recipe.py:_normalise` empty→None convention | ✅ | line 75-77 |

`[VERIFIED: rg/sed over the working tree at 27a152a, all reads performed this session]`

Two additional baseline drifts, both in `.planning/`, both worth correcting when R0.11 lands:

- `REQUIREMENTS.md:88` and `ROADMAP.md:35` record **19** pyright errors in `src/`.
  `uv run pyright src` → `15 errors, 0 warnings, 0 informations`. `[VERIFIED: measured 2026-09-23]`
- `REQUIREMENTS.md:111` records `make doctor` exit **2**. Confirmed — but note the distinction:
  `my-kitty doctor` exits **1** (`doctor.py:263`), and `make` turns a failed recipe into its own
  exit **2**. `make doctor >/dev/null; echo $?` → `2`. `[VERIFIED: h30/evidence/02]`
  No one should chase a phantom exit-2 path in `doctor.py`.

## Locked decision → measured fact

| Decision | Claim | Measured verdict |
|---|---|---|
| D-01 | file under `~/.local/share/kitty-setup/`, rc sources it | ✅ works; the dir is unowned; bash and zsh outputs are identical so the "shell-specific" split is optional but recommended |
| D-02 | helper exists in the tool venv, not on PATH; rc guards on `command -v` | ✅ exactly as stated, verbatim below |
| D-03 | generation belongs to the install path | ✅ instruction correct; ❌ rationale false → **U-3** |
| D-04 | `--keep-kitty --keep-backups` matches the help text | ✅ `cli_uninstall` flag semantics confirm it |
| D-05 | ≤5-line Makefile target holds | ✅ the fixed recipe is 2 lines |
| D-06 | `log` → stderr fixes both branches | ✅ both failures reproduced |
| D-07 | pytest-subprocess with fake HOME/PATH | ✅ shape proven; exact commands in §R1.3 |
| D-08 | quote pane-0 `cwd`; give pane-0 `cmd` `bash -lc` | ✅ injection reproduced; one caveat on `exec bash` idioms |
| D-09 | wrong command name, discarded stderr, payload not rolled back | ✅ all three; **plus** the check is far weaker than assumed |
| D-10 | strip `KITTY_WINDOW_ID` in two files | ✅ both sites; five more sites triaged as harmless |
| D-11 | delete `_record_install_log`; nothing reads it | ✅ verified — no test, no doctor check, no report field |
| D-12 | empty → absent; narrow passthrough | ✅ empty→absent confirmed live; ❌ passthrough list wrong → **U-2** |
| D-13 | six minors | 5 of 6 ✅; `close-os-window` ❌ → **U-1** |

---

## R1.1 — shell completion on a uv-tool install (the merge gate)

**Hypothesis directory:** `/tmp/claude-1000/-var-home-bazzite-git-personal-kitty-setup/b7bd9520-ad75-4c17-a790-515c764c11ab/scratchpad/h-phase2/h30-argcomplete-static/`
(with `README.md` + 13 evidence files).

> **The executing plan must recreate this as `tmp/h30-argcomplete-static/` inside the repo** per
> `docs/agent-iteration.md` R1/R5 and Universal Phase Gate step 2. This researcher deliberately
> wrote nothing into the working tree, because a concurrent agent holds Phase 1's last plan and
> its branch must stay fast-forward-mergeable.

**Safety boundary honoured.** The real `~/.bashrc` / `~/.zshrc` were read only; every write went
into a fake `HOME` under the scratch dir. **No `uv tool install` or `uv tool uninstall` was run at
all**, so `UV_TOOL_DIR` / `UV_TOOL_BIN_DIR` were never needed — the already-installed tool venv was
only read from (`ls`, `python -c`, and running its `register-python-argcomplete`, which writes
nothing). `fakehome/.local/bin/my-kitty` is a symlink to the existing real binary.

### 1. D-02's diagnosis — confirmed verbatim

```
$ command -v my-kitty
/home/bazzite/.local/bin/my-kitty
$ command -v register-python-argcomplete
exit=1
$ ls -1 ~/.local/share/uv/tools/kitty-setup/bin/
activate … activate-global-python-argcomplete … my-kitty … register-python-argcomplete
$ awk '/# >>> my-kitty PATH >>>/,/# <<< my-kitty PATH <<</' ~/.bashrc
# >>> my-kitty PATH >>>
if command -v register-python-argcomplete >/dev/null 2>&1; then
    eval "$(register-python-argcomplete my-kitty)"
fi
# <<< my-kitty PATH <<<
$ my-kitty doctor
…
FAIL completion: register-python-argcomplete not on PATH
SKIP remote-control: no running kitty
exit=1
```
`[VERIFIED: h30/evidence/01-diagnosis.txt]`

The helper exists in the tool venv's `bin/`; `uv tool install` exposes only the package's own
`[project.scripts]` entry point, so it is never on `PATH`; the `command -v` guard at
`path_integration.py:28-30` therefore skips the `eval` silently, and only `doctor` ever says so.
Exactly D-02.

**Two extra facts the planner needs.**

(a) **This host's rc block is already out of template shape.** `grep -n` shows the block body is
only three lines (guard / eval / `fi`) at `~/.bashrc:70-74` — it does **not** contain
`EXPORT_LINE`, which `_BLOCK_BODY_LINES[0]` renders. `_block_body_matches_template` will therefore
return `False` and the next `my-kitty install` rewrites the block in place. Good — the D-01
migration path is already exercised on this host. The user's own PATH export lives separately at
`~/.bashrc:9-10` and is untouched by our splice.
`[VERIFIED: h30/evidence/02-bashrc-and-make-exit.txt]`

(b) **`doctor` exits 1, `make doctor` exits 2.** See the drift audit.

### 2. The exact generation command

```
$ ~/.local/share/uv/tools/kitty-setup/bin/python -c "from importlib.metadata import version; print(version('argcomplete'))"
3.7.2                                            # installed tool venv
$ uv run python -c "from importlib.metadata import version; print(version('argcomplete'))"
3.6.3                                            # repo venv (uv.lock pins 3.6.3)
```
`argcomplete` has **no `__version__` attribute** — use `importlib.metadata.version`.
`[VERIFIED: h30/evidence/03-argcomplete-version.txt]`

The flag surface in 3.7.2:

```
$ ~/.local/share/uv/tools/kitty-setup/bin/register-python-argcomplete --help
usage: register-python-argcomplete [-h] [--no-defaults] [--complete-arguments ...]
                                   [-s {bash,zsh,tcsh,fish,powershell}]
                                   [-e EXTERNAL_ARGCOMPLETE_SCRIPT]
                                   executable [executable ...]
  -s {bash,zsh,tcsh,fish,powershell}, --shell {bash,zsh,tcsh,fish,powershell}
```
So **`--shell bash` / `--shell zsh` is the correct spelling** in the version this repo actually
resolves. D-01's wording is right. `[VERIFIED: h30/evidence/03]`

Four generation routes, all **byte-identical at 2685 bytes**:

| route | bytes | identical to `--shell bash`? |
|---|---|---|
| `register-python-argcomplete --shell bash my-kitty` | 2685 | — (reference) |
| `register-python-argcomplete --shell zsh my-kitty` | 2685 | **IDENTICAL** |
| `register-python-argcomplete my-kitty` (no flag) | 2685 | IDENTICAL |
| `python -m argcomplete.scripts.register_python_argcomplete --shell bash my-kitty` | 2685 | IDENTICAL |
| the same via argcomplete **3.6.3** | 2685 | IDENTICAL |

`[VERIFIED: h30/evidence/04-generation.txt, 06-cli-wiring-and-version-skew.txt]`

**Why identical:** the script dispatches on `$ZSH_VERSION` at *runtime* (`gen-bash.sh:29,68`), so
one file serves both shells. Its first line is `#compdef my-kitty`, a zsh compdef header that
bash treats as a comment.

**Recommended invocation — no `PATH` lookup at all:**

```python
import argcomplete
script: str = argcomplete.shellcode(["my-kitty"], shell=shell)   # shell in {"bash","zsh"}
```
`inspect.signature(argcomplete.shellcode)` in the tool venv →
`(executables: Iterable[str], use_defaults: bool = True, shell: str = 'bash', complete_arguments: Iterable[str] | None = None, argcomplete_script: str | None = None) -> str`
`[VERIFIED: h30/evidence/04-generation.txt §A]`

This is strictly better than shelling out: it runs in the same interpreter as `my-kitty install`,
needs no `register-python-argcomplete` on `PATH` (the very thing D-02 is about), and returns a
`str` that can be compared byte-for-byte by doctor. It also cannot be spoofed by a `PATH` entry.

`cli.py:471` already calls `argcomplete.autocomplete(parser)` and `cli.py:16` documents the
`PYTHON_ARGCOMPLETE_OK` comment — the producer side needs no change. `[VERIFIED: rg over cli.py]`

### 3. Sourcing works — demonstrated with a real TAB keypress

**Registration, with the host's own rc (copied into the fake HOME):**

```
$ env -i HOME=$FAKEHOME TERM=dumb PATH=/usr/bin:/bin bash -i -c 'complete -p my-kitty; type -t _python_argcomplete'
complete -o bashdefault -o default -o nospace -F _python_argcomplete my-kitty
function
```
`complete -p` is bash's own completion registry reporting the binding TAB consults.
`[VERIFIED: h30/evidence/07-bash-demo.txt]`

**Real TAB on a pty, interactive bash, fake HOME** (`pty.fork()` → `bash --noprofile --rcfile
<minimal rc carrying only the D-01 block> -i`, then a literal `\t` written to the master fd):

```
typed: my-kitty doc<TAB>
my-kitty doctor

typed: my-kitty <TAB><TAB>
--help     doctor     install    os-window  scene      uninstall
-h         help       keys       prune      tab        window
```
`[VERIFIED: h30/evidence/08-bash-real-tab.txt]`

**Real TAB on a pty, interactive zsh 5.9.2, fake HOME containing a copy of the host's actual
`~/.zshrc` with our block appended:**

```
typed: my-kitty doc<TAB>
my-kitty doctor

typed: my-kitty <TAB>
--help     -h  -- show this help message and exit
doctor         -- diagnose install + config-include health
help           -- print this help banner
install        -- install kitty + inject config + ensure ~/.local/bin on PATH
keys           -- list active key bindings, grouped by source, with conflicts
os-window      -- scene primitives that act on the OS window (font-size, opaci
prune          -- list / delete accumulated kitty.conf.bak.* backups (opt-in)
scene          -- composition primitives (launch a tab with layout + N pre-sty
tab            -- scene primitives that act on a kitty tab (title, …)
uninstall      -- remove our entire footprint (default); --keep-* flags preser
window         -- scene primitives that act on a kitty window (title, …)
```
`[VERIFIED: h30/evidence/11-zsh-real-tab.txt]`

**How it was demonstrated, and the limits.** A real TTY was synthesised with Python's `pty.fork()`
and a genuine `\t` byte written to the master descriptor; readline (bash) and zle (zsh) performed
the completion, so this is **not** a hook invoked by hand — it is the real keypress path. Three
honest limits:

1. **The bash TAB run used a minimal rc**, not the full copied `~/.bashrc`. With the full copy the
   pty session's own shell-integration OSC sequences and MOTD swallowed the injected keystrokes,
   so the demonstration would have been unreadable. Registration *with* the full copied rc is
   nevertheless proven independently by `complete -p my-kitty` (above). The zsh TAB run **did**
   use the full copy of the host's real `~/.zshrc`.
2. **No GUI terminal was driven.** The pty is a pseudo-terminal, not kitty. Nothing in the
   completion path is terminal-emulator-specific, but that is reasoning, not measurement.
3. **The candidate list is produced by the installed `my-kitty`**, i.e. argcomplete 3.7.2 talking
   to whatever `my-kitty` is on `PATH`. A different `my-kitty` on `PATH` would silently answer
   instead; the completion file names the executable, not a path.

### 4. zsh specifics — `compinit` is required, `bashcompinit` is not

| rc shape | result |
|---|---|
| source the file, **no** `compinit` | `my-kitty-completion.zsh:79: command not found: compdef` printed on every shell start; `_comps[my-kitty]=<unset>` |
| `compinit` **before** the source line | `_comps[my-kitty]=_python_argcomplete`; `bashcompinit` reported `none`; `complete` builtin reported `none` |
| source the line, `compinit` **after** | same failure as the first row — `command not found: compdef` |

`[VERIFIED: h30/evidence/10-zsh-compinit-matrix.txt]`

So:
- **`compinit` is mandatory and must run first.** `compdef` is defined *by* `compinit`.
- **`bashcompinit` is NOT required.** The generated script's zsh branch uses native `compdef` +
  `_describe` (`gen-bash.sh:46,79`), not `complete -F`. `whence -w bashcompinit` → `none` while
  the completion was live.
- **The failure is loud, not silent** — a `command not found` on every new shell.

**The host is safe today** but not by construction: `~/.zshrc:12` is
`fpath=(… ) ; autoload -Uz compinit && compinit`, and oh-my-zsh at `:15` runs `compinit` again.
Since `ensure_local_bin_in_path` **appends** the block to the end of the file
(`path_integration.py:196-197`), our line lands after both. `[VERIFIED: h30/evidence/09-host-zshrc.txt]`
A user whose rc runs `compinit` last (zinit / zplug / a manually late `compinit`) would get the
error. Guard against it — measured working:

```
# zsh body — silently skips when compinit has not run yet, no error spam
[ -f "$HOME/.local/share/kitty-setup/my-kitty-completion.zsh" ] && command -v compdef >/dev/null 2>&1 && . "$HOME/.local/share/kitty-setup/my-kitty-completion.zsh"
```
- no `compinit` → `_comps[my-kitty]=<unset>`, **no error printed**
- `compinit` present → `_comps[my-kitty]=_python_argcomplete`

`[VERIFIED: h30/evidence/13-zsh-guard.txt]`

**That guard must NOT be reused for bash:** `command -v compdef` exits 1 in bash
(`bash --noprofile --norc -c 'command -v compdef >/dev/null 2>&1; echo $?'` → `1`), so a shared
body would disable bash completion entirely. `[VERIFIED: h30/evidence/13-zsh-guard.txt §Z8]`
**This is the structural consequence of D-01:** `_BLOCK_BODY_LINES` (a module-level
`Final[tuple[str, ...]]` at `path_integration.py:37-42`) must become a
`_block_body_lines(shell: str) -> tuple[str, ...]` function, and `_block_body_matches_template`
(`:67`) must take the shell too.

### 5. Where the file lives

Nothing in the codebase owns any path under `~/.local/share/kitty-setup/`:

```
$ rg -n 'local/share|XDG_DATA|share/kitty-setup|DATA_HOME' src/ tools/ tests/ Makefile
tools/uninstall.sh:75:  printf '  - ~/.local/share/applications/kitty.desktop\n'
src/kitty_setup/installer.py:7:* ``~/.local/share/applications/kitty.desktop`` — desktop entry.
$ ls -1 ~/.local/share/ | grep -i kitty
(no output — the directory does not exist yet)
```
`[VERIFIED: measured 2026-09-23]`

`installer.py` owns `DEFAULT_DEST = ~/.local` (`:31`), `SYMLINK_PATH = ~/.local/bin/kitty` (`:33`)
and `DESKTOP_PATH = ~/.local/share/applications/kitty.desktop` (`:34`). The new constant belongs
beside them. Two observations, neither of which reopens D-01:

- `XDG_DATA_HOME` is **not** honoured anywhere in `src/`, while `XDG_CONFIG_HOME` **is**
  (`scenes/recipe.py:49-53`). A literal `Path.home() / ".local" / "share" / "kitty-setup"` is
  consistent with the three existing installer constants; honouring `XDG_DATA_HOME` would be
  consistent with `recipe.py`. D-01 names the literal path — follow it, but the
  `home: Path | None = None` injection point that every other module offers is needed anyway for
  the tests.
- `~/.local/share/bash-completion/` already exists on this host, and
  `~/.local/share/zsh/site-functions` is already in the host's zsh `fpath`
  (`~/.zshrc:12`). Those are the FHS/zsh-idiomatic drop-in locations, requiring **no rc line at
  all**. D-01 chose an owned directory plus an explicit source line — a defensible trade (we own
  it end-to-end, and doctor can check both halves). Recorded only so a later reader does not
  mistake it for an oversight.

**Uninstall coupling (not in D-01, and it must not be forgotten):**
`remove_kitty_install` (`installer.py:261-286`) removes `kitty.app`, the symlink and the desktop
entry. Nothing removes a file under `~/.local/share/kitty-setup/`. Left as is, `my-kitty
uninstall` orphans the completion file and the rc source line then points at nothing — harmless
because the rc body is `[ -f … ] &&`-guarded, but still litter. And under D-04, `make clean`
(`--keep-kitty --keep-backups`) must **keep** the completion file, since the binary survives and
its completion should too. The planner should place completion-file removal in the
config/`do_config` branch of `cli_uninstall` or in a new branch — and state which.

### 6. What doctor can honestly check

Four checks, in increasing strength. All are implementable; the planner should take 1+2+3 and
consider 4.

1. **The file we own exists** at the D-01 path for the detected shell.
   Cheap, structural. Cannot detect a stale or truncated file.
2. **The rc source line is present inside our sentinel block** for the detected shell. This is
   the same `_find_block` + body-substring shape `_check_completion` already uses
   (`doctor.py:215-222`) — reuse it.
3. **Staleness, honestly, by byte comparison.** `argcomplete.shellcode(["my-kitty"],
   shell=<shell>) == file.read_text()`. This catches the real staleness cause (an argcomplete
   upgrade changing the shellcode, or the executable name changing) — and it catches it *exactly*,
   with no subprocess. This is the check that replaces D-03's false premise (U-3).
4. **End-to-end truthfulness (optional, strongest).** Doctor can drive the producer protocol
   itself in a subprocess, with no shell involved:

```
$ env _ARGCOMPLETE=1 _ARGCOMPLETE_SHELL=bash _ARGCOMPLETE_IFS=$'\013' \
      COMP_LINE="my-kitty " COMP_POINT=9 COMP_TYPE=9 my-kitty 8>&1 1>/dev/null | tr '\013' '\n'
-h
--help
install
uninstall
doctor
prune
keys
window
tab
os-window
scene
help
exit=0
```
`[VERIFIED: h30/evidence/12-staleness-and-producer.txt §S3]`

A non-empty candidate list proves the binary's own completion machinery works — the half that the
static file cannot guarantee. Cost: one ~100 ms subprocess. Note the `8>&1 1>/dev/null` redirect;
argcomplete writes candidates to **fd 8**, not stdout.

**What doctor cannot check, and must not claim to.** Whether `compinit` ran before our source line
in the user's zsh is a shell-runtime property invisible to Python. Doctor can at most report
"zsh: completion requires `compinit` before our block — verify with `echo
${_comps[my-kitty]}`". Do not silently PASS as if it had checked.

**One pre-existing dishonesty in the same function to fix while there.** `_check_completion`
defaults to `.zshrc` when `$SHELL` is unrecognised (`doctor.py:211-212`: `rc_basename = ".zshrc"
# default when shell is unknown`). On a fish host that produces a FAIL about a file fish never
reads. The honest result is a **SKIP** naming the unsupported shell — consistent with D-13's SKIP
work and with `path_integration`'s own `skipped=True` for unsupported shells (`:130-136`).

### R1.1 change shape

| Site | Change |
|---|---|
| `installer.py` | new `COMPLETION_DIR: Final[Path] = Path.home()/".local"/"share"/"kitty-setup"`; new `write_completion_script(shell: str, *, home: Path \| None = None) -> Path` using `argcomplete.shellcode`; call it from `cli_install` (`:346-350`) for the detected shell |
| `path_integration.py` | `_BLOCK_BODY_LINES` tuple → `_block_body_lines(shell)` function; bash body = export + `[ -f … ] && . …`; zsh body = export + `[ -f … ] && command -v compdef … && . …`; `_block_body_matches_template(rc_text, bounds, shell)`; `PathEditResult.manual_line` → both lines (D-13) |
| `doctor.py:205-238` | rewrite `_check_completion`: file exists + rc source line + shellcode byte-match; SKIP on unsupported shell; drop `shutil.which("register-python-argcomplete")` |
| `installer.py` uninstall | remove the completion file (and decide: config branch or its own) |

### R1.1 test shape

| Test | Placement | Asserts |
|---|---|---|
| `test_installer_completion.py::test_writes_bash_and_zsh_scripts` | unit | generated file == `argcomplete.shellcode(["my-kitty"], shell=…)`, under a `tmp_path` home |
| `…::test_generated_script_contains_no_subcommand_names` | unit | pins U-3: the file is surface-independent, so no one re-adds a surface-change test |
| `test_path_integration.py::test_bash_body_sources_the_file` | unit | bash body has no `command -v compdef` |
| `…::test_zsh_body_guards_on_compdef` | unit | zsh body has the guard |
| `…::test_unsupported_shell_hint_prints_both_lines` | unit | **replaces** the existing `:151` assertion (see Hidden Coupling) |
| `test_doctor.py` — 3 completion tests | unit | **rewrite** the three at `:173`, `:192`, `:208`; they assert the old `shutil.which` mechanism |
| `…::test_completion_skips_on_unsupported_shell` | unit | SKIP, not FAIL |
| `test_completion_e2e.py::test_bash_registers_completion` | integration, `KITTI_INTEGRATION` | `bash -i -c 'complete -p my-kitty'` in a `tmp_path` HOME → contains `_python_argcomplete` |
| `…::test_zsh_registers_completion` | integration | `zsh -i -c 'echo ${_comps[my-kitty]}'` with `ZDOTDIR` → `_python_argcomplete`; **skip if `command -v zsh` fails** (zsh is a linuxbrew install here, not guaranteed) |
| `…::test_producer_protocol_returns_candidates` | integration | the fd-8 protocol from §6 item 4 |

Do **not** attempt a pty TAB test in the suite. It worked here only with a minimal rc and careful
timing; it is inherently flaky. The registration assertions above cover the same contract
deterministically.

---

## R1.2 — `make clean`

**Current behaviour, measured by reading the recipe and the handler it calls** (not run — it is
destructive):

```
Makefile:12  @echo "  clean                    strip our config block + wipe ./tmp/ scratch (keeps kitty + binary)"
Makefile:27  clean:
Makefile:28  	@my-kitty uninstall || true
Makefile:29  	@rm -rf tmp/
```

`cli_uninstall` (`installer.py:367-377`) with no flags:

```python
do_config  = not args.keep_config    # True
do_backups = not args.keep_config and not args.keep_backups   # True
do_kitty   = not args.keep_kitty     # True
```

→ deletes every `kitty.conf.bak.*` (`:385-391`), strips the block and removes the payload dir
(`:393-404`), then `remove_kitty_install()` deletes `~/.local/kitty.app/`, `~/.local/bin/kitty`
and `~/.local/share/applications/kitty.desktop` (`:406`, `installer.py:261-286`).
`[VERIFIED: installer.py:367-412, read this session]`

`make clean` therefore destroys kitty.app, the symlink, the desktop entry and every backup —
the exact opposite of its help text — **with no confirmation prompt**, because it calls
`my-kitty uninstall` directly rather than `tools/uninstall.sh` (which is the script that
confirms). The `|| true` then hides any failure.

### Change shape

```make
clean:
	@my-kitty uninstall --keep-kitty --keep-backups || true
	@rm -rf tmp/
```
Two recipe lines → D-05 satisfied with no dispatch needed. `--keep-kitty` and `--keep-backups`
both already exist (`cli.py:69-86`), so no new flags (confirms the CONTEXT's "Reusable Assets").

**Consider dropping `|| true`.** It exists so `clean` succeeds when nothing is installed, but it
also hides a real failure. If it is kept, say why in the recipe; a comment costs no lines against
the ≤5 rule since `.PHONY` and the banner already count.

### Test shape

| Test | Placement | Asserts |
|---|---|---|
| `tests/unit/test_makefile_targets.py::test_clean_keeps_kitty_and_backups` | unit | parse `Makefile`, find the `clean:` recipe, assert it contains both `--keep-kitty` and `--keep-backups` |
| `…::test_clean_help_matches_recipe` | unit | the `Makefile:12` help string and the recipe flags agree — this is the "behaviour and help text agree" half of R1.2, and it is the part that actually rots |
| `test_installer_uninstall.py::test_keep_kitty_and_backups_preserves_both` | unit (exists as a file) | `cli_uninstall` with both flags leaves `kitty.app`, the symlink, the desktop entry and the `.bak.*` files on a `tmp_path` home |

A text-level Makefile assertion is unusual but correct here: the defect *is* a text mismatch, and
executing `make clean` in a test would require faking `~/.local` and `PATH` for a real
`my-kitty` — far more machinery for a weaker guarantee.

---

## R1.3 — `tools/uninstall.sh`

**Both failures reproduced in a fake `HOME` + fake `PATH`; the real install untouched.**

```
$ env -i HOME=$FAKEHOME PATH=$FAKEBIN:/usr/bin:/bin KITTI_FORCE=1 bash ./tools/uninstall.sh
[uninstall] KITTI_FORCE=1 set; skipping interactive confirm
./tools/uninstall.sh: line 99: $'[uninstall] using legacy binary \'my-kitty-setup\'; run \'uv tool uninstall my-kitty-setup\' after this completes\nmy-kitty-setup': command not found
exit=127
```
(`$FAKEBIN` held only a stub `my-kitty-setup`.) `$(resolve_binary)` captured the `log` line
together with the binary name and the script tried to exec the whole string.
`[VERIFIED: h31/evidence.txt §U1,U2]`

```
$ env -i HOME=$FAKEHOME PATH=/usr/bin:/bin KITTI_FORCE=1 bash ./tools/uninstall.sh 2>err >out
exit=1
--- stdout --- [uninstall] KITTI_FORCE=1 set; skipping interactive confirm
--- stderr --- (empty)
```
The error branch (`tools/uninstall.sh:38-40`) printed **nothing** the user can see: both
diagnostic lines went to the captured stdout of `$(resolve_binary)` and were discarded when the
substitution's value was never used. Exit 1 with zero explanation.
`[VERIFIED: h31/evidence.txt §U3]`

Mechanism note for the planner: `exit 1` inside `$( )` exits only the subshell; the script dies
because `set -euo pipefail` (`:12`) propagates the assignment's non-zero status at `:97`.

### Change shape

One line:

```bash
log() { printf '[uninstall] %s\n' "$*" >&2; }
```

`log` is used at `:29,34,38,39,83,91,101`. Sending **all** of it to stderr is the right call, not
just the three inside `resolve_binary`: the script is a bootstrap diagnostic, its "real" stdout is
the forwarded `my-kitty uninstall` output, and a future `$( )` capture of any other helper would
hit the same trap. D-06 says "inside `resolve_binary`" — a global redirect satisfies that
strictly and removes the class. State the widening in the plan.

### D-07 test shape — the concrete pytest-subprocess-with-fake-HOME test

This is the least obvious test in the phase, so here it is in full. Place at
`tests/unit/test_tools_uninstall_sh.py` (unit: no kitty, no network, ~50 ms/case).

```python
"""Subprocess tests for tools/uninstall.sh. Python is the stack (AGENTS.md
"Stack"), so the shell script is exercised from pytest, not bats. Every run is
sandboxed by a fake HOME and a fake PATH: the script never sees the developer's
real install."""
from __future__ import annotations

import os
import subprocess
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT = REPO_ROOT / "tools" / "uninstall.sh"

STUB = "#!/usr/bin/env bash\nprintf 'STUB %s invoked: %s\\n' \"$0\" \"$*\"\nexit 0\n"


@pytest.fixture
def sandbox(tmp_path: Path) -> tuple[Path, Path]:
    """(fake_home, fake_bin) — fake_bin is the ONLY dir on PATH besides /usr/bin."""
    home = tmp_path / "home"
    (home / ".local" / "bin").mkdir(parents=True)
    fake_bin = tmp_path / "bin"
    fake_bin.mkdir()
    return home, fake_bin


def _stub(directory: Path, name: str) -> Path:
    p = directory / name
    p.write_text(STUB, encoding="utf-8")
    p.chmod(0o755)
    return p


def _run(home: Path, fake_bin: Path, **env_extra: str) -> subprocess.CompletedProcess[str]:
    env = {
        "HOME": str(home),
        "PATH": f"{fake_bin}:/usr/bin:/bin",
        "KITTI_FORCE": "1",          # skip the interactive confirm
        **env_extra,
    }
    return subprocess.run(  # noqa-free: fixed argv, sandboxed env
        ["bash", str(SCRIPT)],
        capture_output=True,
        text=True,
        check=False,
        timeout=30,
        env=env,
        cwd=str(REPO_ROOT),
    )


def test_legacy_binary_branch_invokes_the_legacy_binary(sandbox) -> None:
    """Before the D-06 fix this exits 127: the log line contaminates $(resolve_binary)."""
    home, fake_bin = sandbox
    _stub(fake_bin, "my-kitty-setup")          # only the legacy name exists
    r = _run(home, fake_bin)
    assert r.returncode == 0, f"stdout={r.stdout!r} stderr={r.stderr!r}"
    assert "STUB" in r.stdout and "uninstall" in r.stdout
    assert "using legacy binary" in r.stderr   # the notice is VISIBLE, on stderr
    assert "using legacy binary" not in r.stdout


def test_error_branch_message_is_visible_on_stderr(sandbox) -> None:
    """No binary anywhere: exit 1 AND a diagnostic the user can actually read."""
    home, fake_bin = sandbox
    r = _run(home, fake_bin)
    assert r.returncode == 1
    assert "neither my-kitty nor my-kitty-setup found" in r.stderr
    assert "make install" in r.stderr


def test_preferred_binary_wins_over_legacy(sandbox) -> None:
    home, fake_bin = sandbox
    _stub(fake_bin, "my-kitty")
    _stub(fake_bin, "my-kitty-setup")
    r = _run(home, fake_bin)
    assert r.returncode == 0
    assert "using legacy binary" not in r.stderr


def test_home_local_bin_fallback_is_used(sandbox) -> None:
    home, fake_bin = sandbox
    _stub(home / ".local" / "bin", "my-kitty")   # not on PATH, only in ~/.local/bin
    r = _run(home, fake_bin)
    assert r.returncode == 0
    assert "STUB" in r.stdout


@pytest.mark.parametrize(
    ("env", "flag"),
    [({"KEEP_BACKUPS": "1"}, "--keep-backups"),
     ({"KEEP_CONFIG": "1"}, "--keep-config"),
     ({"KEEP_KITTY": "1"}, "--keep-kitty")],
)
def test_keep_env_vars_forward_as_flags(sandbox, env, flag) -> None:
    home, fake_bin = sandbox
    _stub(fake_bin, "my-kitty")
    r = _run(home, fake_bin, **env)
    assert flag in r.stdout          # the stub echoes its argv
```

Five properties that make this correct rather than merely passing:

1. **`env=` is a complete replacement dict, not `os.environ | {...}`.** That is what guarantees
   the real `~` and the real `my-kitty` are unreachable. `os.environ` is imported above but never
   merged — deliberately.
2. **`KITTI_FORCE=1`** skips `confirm`'s `read -r reply`, which would otherwise hang on a closed
   stdin (`tools/uninstall.sh:81-93`).
3. **The stub echoes its argv**, which is how the flag-forwarding cases assert without a real
   binary.
4. **`test_legacy_binary_branch_…` is the RED test** — it fails at exit 127 today. With
   `workflow.tdd_mode: true` and one-commit-per-plan, this plan must be `type: tdd` and make
   exactly two commits, RED then GREEN (AGENTS.md "Commit granularity").
5. **`cwd=REPO_ROOT`** because the script does `cd "$(dirname $0)/.."` at `:14-15` and then
   `rm`s nothing — but a stray cwd would still make `REPO_ROOT` resolution confusing to debug.

**Do not add shellcheck as a test.** D-07 forecloses it, and it would not have caught this bug:
`$(...)` capturing a function that also logs is idiomatic-looking shell.

---

## R1.4 — scene fill-current-tab

**Reproduced in-process with `_client.kitten_at` stubbed** (no kitty needed):

```
$ Pane(cwd="/tmp/my dir; touch /tmp/PWNED", cmd="echo hi") ×2 → _fill_current_tab(...)
   ('send-text', '--match', 'id:1', 'cd /tmp/my dir; touch /tmp/PWNED\n')
   ('send-text', '--match', 'id:1', 'echo hi\n')
   ('launch', '--type=window', '--hold', '--cwd=/tmp/my dir; touch /tmp/PWNED', 'bash', '-lc', 'echo hi')
```
`[VERIFIED: h33/evidence.txt §M1]`

Three facts in one run:

1. **Pane 0's `cwd` is a shell-injection sink.** The reused shell runs `cd /tmp/my` *and then*
   `touch /tmp/PWNED`. A scene TOML — user data, but also anything seeded or shared — becomes
   arbitrary code execution in the user's own shell. This is the most security-relevant defect in
   the phase, and R1.4 does not say so; the planner should treat it as such.
2. **Pane 1+ is already safe**: `--cwd=<raw>` is a separate argv element in a `subprocess` list
   (`launcher.py:135-137`, `_client.kitten_at`), so no shell parses it. Only the `send-text`
   string path is vulnerable. Do not "fix" `_launch_argv`.
3. **The `bash -lc` asymmetry is real**: pane 1+ gets `bash -lc 'echo hi'`
   (`launcher.py:138`); pane 0 gets `echo hi` typed into whatever interactive shell already
   occupies that window.

`Pane` field order, for writing the test: `['title', 'cmd', 'cwd', 'bg']`
`[VERIFIED: h33/evidence.txt §M3]`. `_fill_current_tab`'s signature is
`(layout, tab_title, tab_accent, panes, *, to, default_cwd, origin_window)`
(`launcher.py:201-210`) — positional, easy to get wrong.

### Change shape

```python
# launcher.py:236-241
if p0.cwd is not None:
    first_error = _fail_soft(
        _client.kitten_at(
            "send-text", "--match", f"id:{origin_window}",
            f"cd {shlex.quote(p0.cwd)}\n", to=to,
        ),
        first_error,
    )
# launcher.py:242-246
if p0.cmd is not None:
    first_error = _fail_soft(
        _client.kitten_at(
            "send-text", "--match", f"id:{origin_window}",
            f"bash -lc {shlex.quote(p0.cmd)}\n", to=to,
        ),
        first_error,
    )
```
`import shlex` is new in this module (`rg -n shlex src/kitty_setup/scenes/launcher.py` → only a
docstring mention at `:52`).

**One behavioural caveat D-08 does not mention.** `bash -lc <cmd>` spawns a *child* bash in the
reused window. The seeded examples use the `… ; exec bash` idiom
(`examples/scenes/dev.toml`, `docker.toml`, `edit.toml`) — under `bash -lc` that `exec` replaces
the **child**, so when the user exits it they land back in the original shell rather than losing
the pane. For pane 1+ (`--hold`) the pane holds instead. The behaviours are close but not
identical, and the difference is visible. Record it in the SUMMARY; the alternative (keep pane 0's
`cmd` typed raw) would fail R1.4's explicit `bash -lc` requirement.

### Test shape

| Test | Placement | Asserts |
|---|---|---|
| `test_scenes_launcher.py::test_pane0_cwd_is_shell_quoted` | unit | with `cwd="/tmp/my dir; touch /tmp/PWNED"` the payload is `cd '/tmp/my dir; touch /tmp/PWNED'\n` — assert on `shlex.quote`'s output, and separately that `"; touch"` never appears unquoted |
| `…::test_pane0_cmd_uses_bash_lc` | unit | payload is `bash -lc 'echo hi'\n` |
| `…::test_pane0_cmd_with_quotes_survives` | unit | `cmd="""echo "a b" 'c'"""` round-trips |
| `test_scene_fill_tab_e2e.py` (exists) | integration | add a scene whose `cwd` has a space; assert the reused window's cwd via `kitten @ ls` — and assert `/tmp/PWNED`-equivalent sentinel file was **not** created |

The integration half matters: the unit test pins the payload string, but only a real shell proves
the quoting is the *right* quoting.

---

## R1.5 — config parse check

Three claims in D-09, all confirmed, plus a fourth finding that makes the fix more valuable than
D-09 assumes.

**(a) The error names a flag kitty does not have.**
```
ConfigUpdaterError text : kitty --debug-config rejected the mutated kitty.conf; rolled back
```
`config_updater.py:280`. The code's own docstring at `:197` says "Kitty 0.46+ does not expose a
`--debug-config` flag"; the actual command is `kitty +runpy <snippet> <conf>` (`:203-209`). The
same wrong string is echoed by doctor at `doctor.py:98` and in the `install()` docstring at
`:230`. `[VERIFIED: h34/evidence.txt §P3]`

**(b) The parser's stderr is discarded.** `_parse_check` returns `result.returncode == 0`
(`:212`) and never touches `result.stderr`. For the rejected payload:
```
stderr: BadLine(number=1, line='cursor_shape banana', exception=ValueError('Invalid cursor shape: banana allowed value…
```
That text names the file, the line number, the line and the reason — everything a user needs, and
it is thrown away. `[VERIFIED: h34/evidence.txt §P3]`

**(c) The payload dir is NOT rolled back.**
```
conf rolled back to original? True  'font_size 12\n'
payload_dir still on disk?     True
payload_dir contents         : ['kitty-setup.conf']       # the REJECTED content
backups left behind          : ['kitty.conf.bak.20260923T224019Z']
```
`[VERIFIED: h34/evidence.txt §P3]`. `install()` `shutil.rmtree` + `copytree`s the payload at
`:236-239`, *before* the conf mutation and long before the parse check at `:271-281`. The rollback
branch restores only `conf`.

**(d) The new finding: the check is much weaker than it looks, and stderr is the only channel
carrying the difference.** `kitty.config.load_config(..., accumulate_bad_lines=bad)` populates
`bad` **only** for value-conversion failures:

| payload line | `_parse_check` | exit | stderr |
|---|---|---|---|
| `this_is_not_a_kitty_directive yes` | **True** | 0 | `Ignoring unknown config key: …` |
| `map ctrl+shift+zzz nonexistent_action` | **True** | 0 | `Shortcut: ctrl+shift+zzz has unknown key, ignoring` |
| `font_size` (no value) | **True** | 0 | `Ignoring invalid config line: 'font_size'` |
| `!!!!` | **True** | 0 | `Ignoring invalid config line: '!!!!'` |
| `map` | **True** | 0 | `Ignoring invalid config line: 'map'` |
| **`include no-such-file.conf`** | **True** | 0 | `Could not find included config file: …` |
| `font_size not-a-number` | False | 1 | `BadLine(number=1, …ValueError("could not convert string to float…"))` |
| `confirm_os_window_close maybe` | False | 1 | `BadLine(… invalid literal for int()…)` |
| `background notacolor` | False | 1 | `BadLine(… Invalid color name: 'notacolor'…)` |
| `cursor_shape banana` | False | 1 | `BadLine(… Invalid cursor shape: banana…)` |

`[VERIFIED: h34/evidence.txt §P2]`

**A missing `include` passes the check.** That is the single most likely real-world failure of our
own payload injection (payload dir deleted, moved, or not force-included in the wheel), and the
gate is blind to it. Surfacing stderr is therefore not cosmetic polish — it is the only way the
check sees its own most probable failure. Whether to *fail* on a warning is a design call outside
D-09; at minimum print it.

### Change shape

```python
@dataclasses.dataclass(frozen=True, slots=True)
class ParseCheckResult:
    ok: bool
    command: str          # the argv actually run, shell-quoted
    stderr: str

def _parse_check(conf_file: Path, kitty_bin: str | Path) -> ParseCheckResult: ...
```
- return the diagnostics instead of a bare `bool`;
- in `install()`'s failure branch (`:272-281`) also `shutil.rmtree(paths.payload_dir,
  ignore_errors=True)` — and decide whether to restore the previous payload (there is none kept
  today; `:236-238` deletes it before copying, so a *true* rollback needs a temp move. Say which
  in the plan: a `Path.rename` to a sibling `.rollback` before `copytree`, restored on failure, is
  the honest form);
- the `ConfigUpdaterError` message names the real command and embeds the stderr;
- `doctor.py:98` reports the same command string, taken from `ParseCheckResult.command` rather
  than a second hard-coded literal — that is what stops the label re-rotting.

Note `_parse_check`'s name is one of pyright's six `reportPrivateUsage` findings (called from
`doctor.py:95`) — see the Hidden Coupling matrix.

### Test shape

| Test | Placement | Asserts |
|---|---|---|
| `test_config_updater.py::test_parse_check_reports_its_own_command` | unit, real `kitty` (skip if absent) | `result.command` contains `+runpy`, not `--debug-config` |
| `…::test_parse_check_surfaces_stderr_on_failure` | unit, real `kitty` | payload `cursor_shape banana` → `result.ok is False` and `"Invalid cursor shape"` in `result.stderr` |
| `…::test_install_rolls_back_payload_dir_on_parse_failure` | unit, real `kitty` | after the raise: conf restored **and** `payload_dir` no longer contains the rejected file |
| `…::test_error_message_names_the_real_command` | unit | `"--debug-config" not in str(exc)` |
| `test_doctor.py::test_parse_check_label_matches_the_command_run` | unit | doctor's detail string contains `+runpy` |

Use `cursor_shape banana` as the rejected payload — measured to actually fail. Do **not** use an
unknown key or a missing include: those pass.

---

## R1.6 — environment-dependent tests

Both named sites confirmed (with one off-by-one, see the drift audit):

```
$ rg -n 'dict\(os.environ\)|os\.environ\.copy' tests/
tests/integration/test_color_normalization_e2e.py:31     ← strips at :33 (the pattern to copy)
tests/integration/test_scene_recipe_e2e.py:75            ← DOES NOT STRIP
tests/integration/test_scene_recipe_e2e.py:119           ← already strips at :122
tests/integration/_kitty_subprocess.py:58                ← does not strip
tests/integration/_kitty_subprocess.py:121               ← does not strip
tests/integration/test_h21_doctor_remote_control.py:51    ← does not strip
tests/integration/test_h21_remote_control_foundation.py:54,95 ← does not strip
tests/integration/test_client_socket_discovery.py:50      ← does not strip
tests/integration/test_h25_scene_launcher.py:394          ← DOES NOT STRIP
tests/unit/test_git_hooks.py:97,113                       ← irrelevant (no kitty)
```
`[VERIFIED: measured 2026-09-23]`

**Triage of the five extra sites.** `KITTY_WINDOW_ID` is read in exactly one place in `src/`:
`launcher.py:171` (`_origin_window_id`), consumed by the fill-current-tab branch decision at
`:289`. `rg -n 'KITTY_WINDOW_ID' src/` returns only `launcher.py:166,171,213,289`. The five extra
sites subprocess `doctor`, `_client` socket discovery and remote-control helpers — none of which
branch on it. **They are harmless; D-10's two sites are the complete set.** Noted so a reviewer
does not flag the asymmetry as an oversight, and so a future phase that adds a scene assertion to
`_kitty_subprocess.py` knows to strip there too.

Note that `test_scene_recipe_e2e.py` already has the *correct* pattern at `:119-125` in
`_run_scene_launch` — including the deliberate `env["KITTY_WINDOW_ID"] = str(window_id)`
re-injection for the inside-kitty case at `:123-125`. The defect is only the *other* env builder
at `:75`. Do not "simplify" the two into one; the second one's re-injection is load-bearing for
`test_scene_recipe_e2e.py:201`'s fill-current-tab assertion.

### Change shape

One line in each of two files, after the `env = dict(os.environ)`:

```python
env.pop("KITTY_WINDOW_ID", None)
```
at `tests/integration/test_h25_scene_launcher.py:395` and
`tests/integration/test_scene_recipe_e2e.py:76`.

### Test shape

R1.6 is a fix *to* tests, so the "regression test" is a meta-assertion. Two options; take the
second:

1. Run the suite from inside a kitty window. Not reproducible in CI and not scriptable here.
2. **A static assertion** at `tests/integration/test_env_hygiene.py`: walk the AST of
   `tests/integration/*.py`, find every `dict(os.environ)` / `os.environ.copy()` assignment that
   is later passed as `env=` to a `subprocess` call in a module that also references `scene`, and
   assert a `KITTY_WINDOW_ID` pop appears in the same function. This mirrors the AST-walking
   enforcement pattern Phase 5's D-11 already commits to for R3.3, so the technique is
   pre-blessed by the roadmap rather than invented here.

If option 2 is judged over-engineered for two lines, the honest minimum is a comment at each site
naming the hazard plus `test_scene_recipe_e2e.py:201`'s existing assertion as the canary. Say
which was chosen and why.

---

## R1.7 — the minors

### D-11 — delete `_record_install_log`

```
$ rg -n 'install_log|install\.log' src/ tests/ tools/ Makefile
src/kitty_setup/installer.py:180:def _record_install_log(version: str) -> None:
src/kitty_setup/installer.py:210:    _record_install_log(version)
```
**Nothing else references it, in `src/`, `tests/`, `tools/` or the Makefile.**
`[VERIFIED: measured 2026-09-23]`

The CONTEXT's "verify before removing" question — does `InstallReport`/`_print_install_report`
read the version from there? — answered: **no.** `InstallReport.version` (`:44`) is assigned from
`_capture_version(kitty_bin)` at `:196` / `:202`, and `_record_install_log(version)` at `:210` is a
pure side effect. `_print_install_report` (`:289-305`) reads `report.version`, not the file.
`[VERIFIED: installer.py:38-49, 186-235, 289-305, read this session]`

Change shape: delete `:180-183` and the call at `:210`. No test touches it, so **no test breaks
and no new test is needed** — but R1.7 asks for a regression test per item. The honest pin is a
one-line assertion that `installer` has no `_record_install_log` attribute and that no file named
`install.log` appears under the repo `tmp/` after a mocked install. State plainly that this is a
tombstone test, not a behaviour test.

Bonus: this also removes one of the two live uses of `_repo_root()` (`:51-56`), a function whose
docstring admits it only works under an editable `uv sync` install. Check whether `_repo_root` has
another caller before deleting it too (`rg -n '_repo_root' src/`).

### D-12 — colors

**Empty-color defect confirmed end-to-end against a real kitty:**

```
$ my-kitty window background ''
Error:  is not a valid color            exit=1
$ my-kitty tab accent ''
Error:  is not a valid color            exit=1
$ my-kitty window background 'rgba(1,2,3,0.5)'
Error: rgba(1,2,3,0.5) is not a valid color   exit=1
$ my-kitty window background 'rgb:00/ff/00'
exit=0
$ my-kitty window background 'teal'
exit=0
```
`[VERIFIED: h32/live-evidence-2.txt]`

That is `normalize_color(c) or c` (`background.py:30`, `accent.py:32`) sending the empty original
straight through to `background=`, exactly as D-12 says. The full accepted/rejected matrix is in
§U-2, which also corrects D-12's passthrough list.

Change shape:

```python
# background.py
normalized = normalize_color(color)
if normalized is None:
    return 0                       # absent: no kitten call at all
args.append(f"background={normalized}")
```
```python
# accent.py — the color may be absent while the fg overrides are present
normalized = normalize_color(color)
args: list[str] = []
if match is not None:
    args.extend(("--match", match))
if normalized is not None:
    args.append(f"active_bg={normalized}")
    args.append(f"inactive_bg={normalized}")
…
if not args or all(a in ("--match", match) for a in args):
    return 0                       # nothing to set
```
```python
# colors.py:79-80 — replace the broad passthrough
_RGB_COLON_RE = re.compile(r"rgb:[0-9a-f]{1,4}/[0-9a-f]{1,4}/[0-9a-f]{1,4}")
…
if _RGB_COLON_RE.fullmatch(low):
    return v
```
(`rgb:0/f/0` and `rgb:00/ff/00` both measured accepted by kitty, hence `{1,4}`.)

The launcher path already handles absence correctly — `launcher.py:336-337` normalizes and
`_apply_bg` (`:142-145`) returns early on `None`. No change there. `[VERIFIED: launcher.py read this session]`

Test shape:

| Test | Placement | Asserts |
|---|---|---|
| `test_scenes_background.py::test_empty_color_makes_no_kitten_call` | unit | stub `kitten_at`, assert it was **not** called, return 0 |
| `test_scenes_accent.py::test_empty_color_omits_bg_args_keeps_fg` | unit | `active_bg=` absent, `active_fg=` present |
| `test_scenes_colors.py::test_rgb_colon_passes_through` | unit | `rgb:00/ff/00`, `rgb:0/f/0` |
| `test_scenes_colors.py::test_rejected_pseudo_colors` | unit | `foo:bar`, `a(b`, `rgba:00/ff/00/80`, `rgb(1,2,3)`, `hsl(…)` all raise `ColorError` — **each value is measured-rejected by kitty** |
| `test_scenes_colors.py:124` | unit | **invert** the existing `rgba(1,2,3,0.5)` passthrough assertion (see U-2) |
| `test_color_normalization_e2e.py` (exists) | integration | add `my-kitty window background ''` → exit 0, no kitten error |

### D-13 — remaining minors

**`int(stdout)` guard.** `rg -n 'int\(' src/kitty_setup/scenes/launcher.py` → `:172` (already
guarded: `int(raw) if raw and raw.isdigit() else None`), `:258`, `:373`, `:396` (unguarded).
On empty stdout: `ValueError: invalid literal for int() with base 10: ''`
`[VERIFIED: h33/evidence.txt §M3]`. Change shape: one module-level helper reusing `:172`'s own
predicate, so the four sites share one rule:

```python
def _window_id_from(result: _client.KittenResult, *, verb: str) -> int:
    raw = result.stdout.strip()
    if not raw.isdigit():
        raise SceneLaunchError(
            f"kitten @ {verb} returned no window id (stdout={result.stdout!r}, "
            f"stderr={result.stderr!r})"
        )
    return int(raw)
```
Test: unit, stub `kitten_at` returning `stdout=""` / `stdout="not-an-id"` / `stdout="\n"`, assert
the clean error at each of the three call sites and that it names the verb.

**`prune --keep <0`.** Reproduced:
```
$ my-kitty prune --backups --keep -1      (parsed, then)
   argparse accepted it: keep = -1
   then: ValueError: --keep must be >= 0, got -1
```
`[VERIFIED: h33/evidence.txt §M2]` — argparse accepts `-1` as a value (no negative-number-looking
options are registered), so `pruner.prune_by_keep`'s guard (`:28-29`) surfaces as an uncaught
traceback. Change shape: a `type=` callable on the argument, not a check in the handler:

```python
def _non_negative_int(raw: str) -> int:
    value = int(raw)                              # ValueError → argparse handles it
    if value < 0:
        raise argparse.ArgumentTypeError(f"must be >= 0, got {value}")
    return value
```
Wire at `cli.py:108-113` (`--keep`) **and `cli.py:114-120` (`--older-than`)**, which carries the
identical defect at `pruner.py:37-38` (`raise ValueError(f"--older-than must be >= 0, …")`). D-13
names only `--keep`; fixing one and not its twin, three lines away, is the kind of thing that
reads as an oversight in review. Keep the `prune_by_keep`/`prune_by_age` guards as a library-level
invariant — they are the contract for direct callers. Test: `parser.parse_args([...])` raises
`SystemExit(2)` for both flags, and the library guards still raise `ValueError` when called
directly.

**Harness teardown verb.** See **U-1** — blocked.

**Doctor SKIP.** `doctor.py:91,103,111` return `CheckResult(name, False, "skipped — …")`.
`CheckResult` already has `skipped: bool = False` (`:26`) and `render()` already prints
`SKIP name: detail` when it is set (`:28-33`). Change shape: `CheckResult(name, False, "kitty
binary not available", skipped=True)` — and **drop the "skipped — " prefix from the detail**, or
`render()` produces `SKIP parse check: skipped — kitty binary not available`. Also strip the
prefix at `:111` (`f"skipped — {exc}"` → `str(exc)`). Per the CONTEXT's discretion note, prefer
changing only the call sites; `render()` needs no change.

**Exit-status consequence, stated explicitly.** `cli_doctor` returns
`0 if all(r.passed or r.skipped …) else 1` (`:263`). Today "kitty binary not available" produces
three FAILs (`_check_kitty_binary`, parse check, bindings). After the change it produces one FAIL
plus two SKIPs — so `doctor` still exits 1, because `_check_kitty_binary` itself still FAILs
(`:56`). The change removes double-reporting; it does **not** let a kitty-less host pass. Verify
that in the test rather than asserting it here.

**PATH-migration messages.** `path_integration` computes five distinct `reason` values
(`:154`, `:168`, `:181`, `:191`, `:208`) and `_print_path_result` (`installer.py:308-320`) ignores
every one, printing `"appended block to {rc_file}"` for any `changed=True`. Change shape: print
`result.reason` in the `changed` branch. Vulture already flags this defect independently —
`src/kitty_setup/path_integration.py:58: unused variable 'reason' (60% confidence)` — so fixing
D-13 removes one R0.11 finding. Test: unit, four reason values → four distinct stdout lines.

**Unsupported-shell hint prints both lines.** `PathEditResult.manual_line: str = EXPORT_LINE`
(`:59`) carries only the PATH line; `_print_path_result` prints only it (`:310-313`). Change
shape: `manual_lines: tuple[str, ...]` (or keep `manual_line` and add the completion line to it),
printed one per line. Under D-01 the second line is the **source** line, not the old `eval` line —
and it is shell-dependent, which for an *unsupported* shell means there is no correct form. The
honest hint for fish is "kitty-setup does not generate fish completion; add `~/.local/bin` to
`$PATH` yourself" — say so rather than printing a bash line to a fish user. Flag this to the user
if the planner reads D-13 as requiring a literal bash line.

---

## R0.11 — `src/` clean under all five tools: measured, and sized

Gate commands, taken from `ROADMAP.md:121`. All run at `27a152a`, 2026-09-23.

### ruff — 9 findings, 5 shapes

```
$ uv run ruff check src --output-format concise
src/kitty_setup/cli.py:321:56: RUF001 String contains ambiguous `–` (EN DASH). Did you mean `-` (HYPHEN-MINUS)?
src/kitty_setup/doctor.py:122:101: E501 Line too long (109 > 100)
src/kitty_setup/doctor.py:148:101: E501 Line too long (106 > 100)
src/kitty_setup/doctor.py:168:101: E501 Line too long (101 > 100)
src/kitty_setup/harness/kitty_session.py:291:9: SIM105 Use `contextlib.suppress(HarnessCommandError)` instead of `try`-`except`-`pass`
src/kitty_setup/harness/kitty_session.py:312:13: SIM105 Use `contextlib.suppress(ProcessLookupError)` instead of `try`-`except`-`pass`
src/kitty_setup/installer.py:141:9: S607 Starting a process with a partial executable path
src/kitty_setup/scenes/_client.py:43:35: RUF100 [*] Unused `noqa` directive (unused: `S603`)
src/kitty_setup/scenes/_client.py:44:13: S607 Starting a process with a partial executable path
Found 9 errors.
```

**How much is automatic?** Measured in a scratch copy of `src/` (the repo was not touched):

```
$ black -q src && ruff check src --output-format concise      # 8 remain (E501 doctor.py:168 fixed by black)
$ ruff check src --fix -q && ruff check src --output-format concise
… Found 7 errors.     # RUF100 auto-fixed; nothing else is fixable
```
`[VERIFIED: r011-sizing/evidence.txt]`

So: **`black src` fixes 1, `ruff --fix` fixes 1, and 7 need a human**, in four shapes:

| Shape | Sites | Fix |
|---|---|---|
| RUF001 en-dash | `cli.py:321` | one character, or a `ruff` config entry if the dash is deliberate typography |
| E501 | `doctor.py:122,148` | manual wrap (black won't split these — they are long f-strings) |
| SIM105 | `kitty_session.py:291,312` | `contextlib.suppress` — **`:291` is the D-13 teardown line** |
| S607 partial executable path | `installer.py:141`, `_client.py:44` | design call: absolutise (`shutil.which("pgrep")`) or configure ruff with rationale |

### black — 2 files, 2 hunks

```
$ uv run black --check src
would reformat src/kitty_setup/scenes/_client.py
would reformat src/kitty_setup/doctor.py
2 files would be reformatted, 19 files would be left unchanged.
```
`black --diff` shows one hunk each: joining a 3-line `raise` into one line (`_client.py:95-97`)
and splitting a long `CheckResult(...)` (`doctor.py:168`). Fully mechanical: `uv run black src`.
`[VERIFIED: measured 2026-09-23]`

### pyright — 15 findings (**not 19**), 3 shapes

```
$ uv run pyright src
15 errors, 0 warnings, 0 informations
```

| Count | Rule | Sites | Shape |
|---|---|---|---|
| 8 | `reportUnusedImport` | `scenes/__init__.py:6-13` | **one file, one fix.** The module deliberately re-exports 8 submodules for `monkeypatch.setattr` targets and already carries `# noqa: F401`, which pyright ignores. Add `__all__ = ["accent", …]` or use `as`-re-export form |
| 6 | `reportPrivateUsage` | `doctor.py:18` ×2, `doctor.py:36,95,215`, `binding_introspection.py:143` | cross-module private access: `_parse_listen_on_base`, `_pgrep_kitty_pids`, `installer._kitty_bin` ×2, `config_updater._parse_check`, `path_integration._find_block` |
| 1 | `reportUnnecessaryComparison` | `kitty_session.py:179` | **a real latent bug**, not noise |

`[VERIFIED: pyright.json, generated this session]`

`kitty_session.py:179` is `if value is True or value == "":` inside
`def launch(self, **kwargs: str)`. Pyright is right: `value` is annotated `str`, so `value is
True` can never hold. Either the annotation is wrong (callers pass `True` for flag-style options)
or the branch is dead. `rg` finds one caller: `tests/integration/test_h01_cwd.py:62`
`session.launch(**kwargs)`. Read that call before choosing — and note vulture flags the same
method as unused, so "delete it" is on the table.

**The `reportPrivateUsage` six are Phase 5's territory and must be handled without preempting it.**
R3.3 removes exactly these cross-imports (`doctor.py:18`→`scenes._client`,
`installer.py:98`→`scenes.recipe`, `scenes/_client.py:18`→`config_updater`/`installer`) via a
neutral module, and Phase 5's D-11 commits to an AST test enforcing it. Phase 2 must **not**
invent that neutral module. The cheapest non-conflicting fix is renaming the five symbols to
public names in place (`_parse_check` → `parse_check` etc.) and updating the call sites; R3.3 then
deletes the cross-import entirely and the public name is either kept or moved. Say so in the plan
so a reviewer does not read it as scope creep.

### bandit — 27 findings, 0 high / 8 medium / 19 low

```
$ uv run bandit -q -r src
Run metrics — Total issues (by severity):  Undefined: 0  Low: 19  Medium: 8  High: 0
```
The recorded baseline (0 high / 8 medium / 19 low) is **exactly reproduced**, and the
`REQUIREMENTS.md:89-90` note about "20 high" being a misread confidence column is confirmed
(by confidence: Low 6, Medium 1, High 20).

By severity and test id:

| Sev | Count | Test | Sites | Assessment |
|---|---|---|---|---|
| MEDIUM | **6** | B604 `shell=True` | `path_integration.py:134,153,167,180,190,207` | **FALSE POSITIVE.** Every one of those six lines is `shell=detected_shell,` — a keyword argument to the `PathEditResult(...)` dataclass constructor. Bandit sees a `shell=` kwarg and calls it a shell injection. There is no `subprocess` call in `path_integration.py` at all |
| MEDIUM | 1 | B310 `urlopen` scheme audit | `installer.py:133` | real-ish: the kitty installer URL. A scheme assertion (`url.startswith("https://")`) satisfies it honestly |
| MEDIUM | 1 | B108 hardcoded tmp | `kitty_session.py:230` | `env.setdefault("XDG_RUNTIME_DIR", "/tmp")` — already carries `# noqa: S108` with a rationale; bandit does not read ruff's noqa |
| LOW | 10 | B603 subprocess-without-shell | across `src/` | the whole point of this codebase is driving `kitty`/`kitten`; all argv are lists |
| LOW | 7 | B404 import subprocess | 7 modules | unavoidable |
| LOW | 2 | B607 partial path | `installer.py:141`, `_client.py:44` | same two sites as ruff S607 — fix once, both tools clear |

`[VERIFIED: measured 2026-09-23, bandit -f json parsed]`

**The policy question the planner must decide and the user may want to see.** ROADMAP criterion 6
says `uv run bandit -q -r src` must "report clean", i.e. **zero findings at any severity**. That
requires suppressing 24 findings that are correct-by-design. `.claude/conventions.md:22-24`
forbids `# noqa` / `# nosec` and says *"if a tool is wrong, configure it explicitly with rationale
in the config file"*. So the fix is a `[tool.bandit]` block with per-test rationale — today
`[tool.bandit]` contains only `exclude_dirs = ["tests", "tmp"]`. Concretely: `skips = ["B404",
"B603", "B604", "B607"]` with a comment per id, plus real code fixes for B310 and B108. Six of the
eight mediums disappear on a single line of config because they are one false positive.

### vulture — 16 findings, and the tool is being run with the wrong scope

```
$ uv run vulture src
src/kitty_setup/cli.py:197,250,385,404: unused attribute 'completer' (60%)
src/kitty_setup/harness/kitty_session.py:124: unused property 'session_dir' (60%)
src/kitty_setup/harness/kitty_session.py:147: unused variable 'exc_type' (100%)
src/kitty_setup/harness/kitty_session.py:149: unused variable 'tb' (100%)
src/kitty_setup/harness/kitty_session.py:161,166,170,174,192: unused method 'ls'/'send_key'/'send_text'/'launch'/'get_text' (60%)
src/kitty_setup/installer.py:243: unused function 'uninstall_config_only' (60%)
src/kitty_setup/path_integration.py:32: unused variable 'TARGET_DIR_REL' (60%)
src/kitty_setup/path_integration.py:58: unused variable 'reason' (60%)
src/kitty_setup/path_integration.py:114: unused variable 'env_path' (100%)
```

Triage, by `rg` over `src/ tests/ tools/`:

| Finding | Really dead? | Evidence |
|---|---|---|
| `completer` ×4 (`cli.py`) | **No — framework API.** argcomplete reads `action.completer` at runtime | `rg completer` → `colors.py`, `recipe.py`, `cli.py`, and 14 test references |
| `ls`, `send_key`, `send_text`, `launch`, `get_text` | **No — used from `tests/integration/`** | `test_h02_clear.py:76,79,85,89,95,97`, `test_h01_cwd.py:55,62,63`, `test_h25_scene_launcher.py` ×3 |
| `uninstall_config_only` | **No — used from `tests/`** | `test_installer_uninstall.py`, `test_installer_seed_scenes.py` ×2 |
| `exc_type`, `tb` (100%) | No — mandatory `__exit__` signature | `kitty_session.py:145-149` |
| `session_dir` property | **Yes** — defined, never read | `rg session_dir` → `kitty_session.py` only |
| `TARGET_DIR_REL` | **Yes** — defined, never read | `rg TARGET_DIR_REL` → `path_integration.py:32` only |
| `env_path` (100%) | **Yes** — the docstring says "kept for kwarg back-compat; no longer consulted" (`:114`); tests still pass it | 15 call sites, all in `test_path_integration.py` |
| `reason` | **No — this IS defect D-13.** Vulture found it independently | `_print_path_result` never reads `result.reason` |

**So ~9 of 16 are false positives caused by scanning `src` alone.** That is a *gate design*
problem, not a code problem: the ROADMAP's own command (`uv run vulture src`) cannot see test
usage, so any `src` symbol whose only consumer is a test looks dead forever. Three ways out; the
planner must pick one and record it, because it changes the gate command that every later phase
inherits:

1. `uv run vulture src tests` — kills all 9 false positives, but pulls in `tests/` findings that
   criterion 6 explicitly scopes out.
2. `uv run vulture src vulture_allowlist.py` — the form `.claude/conventions.md:41` already
   assumes. **Note `vulture_allowlist.py` does not exist in the repo** (`ls vulture_allowlist*` →
   nothing, and there is no `[tool.vulture]` in `pyproject.toml`), so creating it is part of this
   work. Conventions warn it is "reserved for near-term public APIs with a referenced task ID —
   never a dumping ground", and 9 framework/test-only entries is arguably exactly the dumping
   ground being warned about.
3. `[tool.vulture] min_confidence = 80` in `pyproject.toml` — drops every 60% finding (12 of 16),
   keeping only the three 100% ones. Defensible and honest if documented, but it also silences
   `session_dir` and `TARGET_DIR_REL`, which are genuinely dead.

Recommendation: **(1) plus (2)** — scan `src tests vulture_allowlist.py`, allowlist only
`exc_type`/`tb`, and *delete* `session_dir`, `TARGET_DIR_REL` and the `env_path` parameter. That
yields a genuinely clean run with no policy fiction. It does require updating 15 test call sites
that pass `env_path=""`, which is mechanical.

### R0.11 sizing verdict

**Not "19 pyright errors of one shape". ~59 findings across five tools in ~16 distinct shapes,
and the majority of the remaining effort is tool-configuration policy rather than code.**

| Tool | Findings | Distinct shapes | Auto-fixable | Human decisions |
|---|---|---|---|---|
| black | 2 files | 1 | **2** (`black src`) | 0 |
| ruff | 9 | 5 | 2 | 4 shapes / 7 sites |
| pyright | 15 | 3 | 0 | 3 shapes (8 of the 15 are one file, one edit) |
| bandit | 27 | 6 | 0 | 2 code fixes + 1 config block covering 24 |
| vulture | 16 | ~5 | 0 | 1 gate-scope decision + 3 deletions + 1 allowlist file to create |

**Give R0.11 its own plan, and schedule it LAST.** Three reasons, all measured:

1. **Three of its findings sit on lines the defect plans also edit.** `kitty_session.py:291`
   (ruff SIM105) is D-13's teardown line. `path_integration.py:58` (vulture `reason`) is D-13's
   migration-message defect. `config_updater._parse_check` (pyright `reportPrivateUsage`) is
   D-09's function. Running R0.11 first guarantees rework; running it last lets it absorb the
   three for free.
2. **It contains policy, not just cleanup.** Every bandit/vulture/ruff-S607 suppression needs a
   written rationale in `pyproject.toml` under the no-`# noqa` rule. That is reviewable content a
   reviewer will want to see in one place.
3. **It changes the gate command every later phase inherits** (the vulture scope decision). That
   deserves its own SUMMARY entry, not a footnote inside a defect plan.

Estimated split if `granularity: fine` pushes further: `02-05a` mechanical (`black src`,
`ruff --fix`, the 8 `scenes/__init__.py` imports, the 2 E501, the 2 SIM105, the 3 vulture
deletions) and `02-05b` policy (`[tool.bandit]` skips with rationale, the vulture gate scope +
allowlist file, the S607 decision, the `reportPrivateUsage` renames, the `kitty_session.py:179`
latent bug).

### Corrected R0.11 baseline for `ROADMAP.md`/`REQUIREMENTS.md`

| Tool | Recorded at `5452f54` | Measured at `27a152a`, `src/` only |
|---|---|---|
| ruff | 28 (src+tests+tools) | **9** in `src` |
| black | 11 files (src+tests+tools) | **2** files in `src` |
| pyright | 571 total, **19** in `src` | 576 total, **15** in `src` |
| bandit | 0 high / 8 medium / 19 low | **identical** — 0 / 8 / 19 |
| vulture | 12 | **16** in `src` |

Correcting these two numbers (pyright 19→15, vulture 12→16) is a `.planning/` edit and belongs in
whichever plan closes R0.11, not in a research file.

---

## Hidden coupling matrix

The four questions asked, answered, plus five more found while measuring.

| # | Question | Answer | Evidence |
|---|---|---|---|
| 1 | Does deleting `_record_install_log` (D-11) break any test or doctor check that reads it? | **No.** `rg install_log\|install\.log src/ tests/ tools/ Makefile` returns only the definition (`:180`) and its single call (`:210`). `InstallReport.version` comes from `_capture_version`, not the file | measured 2026-09-23 |
| 2 | Does the `doctor` SKIP change (D-13) alter `doctor`'s exit status or any test asserting on its output? | **Exit status: yes, but harmlessly.** `cli_doctor` is `0 if all(r.passed or r.skipped)` (`:263`); the two converted checks stop contributing FAILs, but `_check_kitty_binary` still FAILs at `:56`, so a kitty-less host still exits 1. **Tests: no.** `test_doctor.py:82` is already `assert not r.passed or r.skipped`; `test_main_exits_non_zero_on_any_fail` (`:184-206`) uses a synthetic list. **But** the detail strings must drop the `"skipped — "` prefix or `render()` prints `SKIP parse check: skipped — …` | `doctor.py:26-33,91,103,111,263`; `tests/unit/test_doctor.py:77-82,184-206` |
| 3 | Does narrowing the color passthrough (D-12) break a seeded example scene or a test fixture? | **No seeded scene.** All four `examples/scenes/*.toml` use hex (`#e2663d`, `#464343c8`, `#2ecc40`, `#0b1f0b`) or names (`blue`, `cyan`, `orange`, `teal`) — zero `:` or `(` in any color. `layout = "tall:mirrored=true"` contains a `:` but is not a color. **One test fixture breaks by design:** `test_scenes_colors.py:124` asserts `rgba(1,2,3,0.5)` passes through, a value kitty rejects (§U-2) | all four TOMLs read this session; `h32/live-evidence.txt` |
| 4 | Does the `close-os-window` teardown change (D-13) affect the integration harness's own assertions? | **It breaks teardown outright — the verb does not exist (§U-1).** No test asserts on the teardown verb (`rg close-window\|_close_window_then_terminate src/ tests/` → only `kitty_session.py:153,290,292`), so nothing would go *red*; every integration test would just get slower and leak a kitty process, because `except HarnessCommandError: pass` swallows the error and teardown falls through to SIGTERM/SIGKILL | `h32/live-evidence-3.txt`; `kitty_session.py:290-315` |
| 5 | **NEW** — does D-13's "unsupported-shell hint prints both lines" break an existing test? | **Yes.** `tests/unit/test_path_integration.py:151` asserts `result.manual_line == path_integration.EXPORT_LINE`. Any change to `manual_line` fails it. It must be rewritten in the same plan | read this session |
| 6 | **NEW** — do the three `_check_completion` tests survive D-01? | **No — all three must be rewritten.** `test_doctor.py:173` (`…passes_when_helper_and_rc_line_present`), `:192` (`…fails_when_helper_missing`), `:208` (`…fails_when_rc_eval_line_missing`) all monkeypatch `doctor.shutil.which` and assert on the `register-python-argcomplete`/`eval` mechanism D-01 deletes | read this session |
| 7 | **NEW** — does D-01 force a structural change beyond the rc block body? | **Yes.** `_BLOCK_BODY_LINES` is a module-level `Final[tuple[str, ...]]`; the bash and zsh bodies must differ (the zsh `compdef` guard breaks bash — §R1.1 ¶4), so it becomes a function of the shell, and `_block_body_matches_template` must take the shell too. Every `test_path_integration.py` test that renders a block (9 of them, all with `shell="zsh"`) inherits that | `h30/evidence/13-zsh-guard.txt`; `path_integration.py:37-42,67-72` |
| 8 | **NEW** — does D-09's rollback interact with `make clean`/`uninstall`? | **Indirectly.** `install()` deletes the payload dir at `:236-238` *before* copying, so there is no previous payload to restore — a true rollback needs a temp rename first. And the backup created at `:270` is left on disk after a failed install (measured), which `--keep-backups` then preserves. Neither is wrong; both should be stated | `h34/evidence.txt §P3` |
| 9 | **NEW** — is `my-kitty window background none` broken, and does it reach a later phase? | **Broken, and yes.** `normalize_color("none") → "NONE"` → `set-colors background=NONE` → kitty exit 1 `The color background cannot be set to none`, while `set-tab-color active_bg=NONE` exits 0. **Phase 6's R4.1/R4.2 require `none` to reset *both*** the pane background and the tab accent. Out of scope for R1.7 as written, but Phase 6 will be blocked by it. Route it to Phase 6's discussion, or fold it into D-12 if the user prefers | `h32/live-evidence-2.txt` |

## Runtime State Inventory

Phase 2 is a defect-fix phase, not a rename, but it *creates* a new on-disk artefact
(`~/.local/share/kitty-setup/`) and *changes* the rc block, so the inventory applies.

| Category | Items found | Action required |
|---|---|---|
| Stored data | **None.** No database, no datastore. The only persistent state is files under `~/.config/kitty/` and `~/.local/`. Verified by `rg -n 'sqlite\|chroma\|redis\|mem0' src/ tools/` → no matches | none |
| Live service config | **The user's shell rc files.** `~/.bashrc:70-74` holds our block in a **pre-D-01 shape missing `EXPORT_LINE`**; `~/.zshrc` has **no block of ours** (`grep -c my-kitty ~/.zshrc` → 0). Both migrate in place on the next `my-kitty install` via the existing `_block_body_matches_template` rewrite path (`path_integration.py:171-192`), which `test_path_integration.py:226` already covers | none beyond D-01's body change — the migration path exists and is tested |
| OS-registered state | `~/.local/share/applications/kitty.desktop` (written by `installer._write_desktop_entry`, `:150-177`). Untouched by Phase 2 | none |
| Secrets / env vars | **None.** No secret, no `.env`, no SOPS. The env vars Phase 2 touches are all test-scoped (`KITTI_INTEGRATION`, `KITTI_FORCE`, `KITTY_WINDOW_ID`, `KITTY_LISTEN_ON`, `KEEP_*`) | none |
| Build artifacts | The installed uv tool venv at `~/.local/share/uv/tools/kitty-setup/` carries **argcomplete 3.7.2** while `uv.lock` pins **3.6.3**. After R1.1 lands, the generated completion file is produced by whichever version the *installed* venv has. A `uv tool install --reinstall --force .` (which `tools/setup.sh:55` already does on every `make install`) may change that version and therefore the file — which is exactly why doctor's byte-comparison check (§R1.1 ¶6 item 3) is the right staleness test | re-run `make install` after Phase 2 so the completion file is regenerated; doctor will then confirm |

**Nothing found in a category is stated explicitly above rather than left blank.**

## Environment Availability

| Dependency | Required by | Available | Version | Fallback |
|---|---|---|---|---|
| `uv` | everything | ✓ | via `~/.local/bin/uv`; `uv run` works | none needed |
| Python | the stack | ✓ | 3.12 (`pyproject` `pythonVersion = "3.12"`) | — |
| `kitty` | R1.5 parse check, D-12 colour probes, integration suite | ✓ | **0.49.0** (`kitty 0.49.0 created by Kovid Goyal`) | — |
| `kitten` | remote control | ✓ | `~/.local/kitty.app/bin/kitten` — **not on `PATH`** (`command -v kitten` fails; use the absolute path or `installer.DEFAULT_DEST/...`, as `doctor.py:163` already does) | absolute path |
| `bash` | R1.3 tests, R1.1 bash completion | ✓ | 5.3.9 at `/usr/bin/bash` | — |
| `zsh` | R1.1 zsh completion test | ✓ **but fragile** | 5.9.2 at `/home/linuxbrew/.linuxbrew/bin/zsh` — a **linuxbrew** install, not system | any zsh integration test MUST `pytest.skip` when `shutil.which("zsh")` is None |
| Wayland/X display | the `KittySession` harness | ✓ | `WAYLAND_DISPLAY=wayland-0`, `XDG_SESSION_TYPE=wayland`; harness spawns `--start-as=minimized` | integration tests are already `KITTI_INTEGRATION`-gated |
| `argcomplete` | R1.1 | ✓ | **3.6.3** repo venv / **3.7.2** tool venv; declared `>=3.5,<4` | — |
| network | `installer._download_installer` | not exercised | — | `install()` skips the download when `kitty.app` already exists (`:194-196`) |

**Missing dependencies with no fallback:** none.
**Missing with fallback:** `kitten` on `PATH` (use the absolute path); `zsh` is present but must be
treated as optional in tests.

## Validation Architecture

`workflow.nyquist_validation: true` in `.planning/config.json`, so this section applies.

### Test framework

| Property | Value |
|---|---|
| Framework | pytest ≥8.3.0 + pytest-cov ≥5.0.0 (`pyproject.toml` `[dependency-groups] dev`) |
| Config | `pyproject.toml` `[tool.pytest.ini_options]`: `testpaths = ["tests"]`, `addopts = "-ra --strict-markers"`, marker `integration` |
| Quick run | `uv run pytest tests/unit -q` |
| Full suite | `uv run pytest tests/ -q` (= `make test`); `KITTI_INTEGRATION=1 uv run pytest tests/ -q` for the real-kitty half |
| **Measured baseline** | `uv run pytest tests/ -q` → **311 passed, 0 failed, 70 skipped** `[VERIFIED: measured 2026-09-23]` |

The 70 skips are the integration suite, gated on `KITTI_INTEGRATION=1`. Every plan in this phase
must leave 311+ passing and 0 failing (CONTEXT: "every plan in this phase must keep `make test`
green on its own").

### Requirement → test map

| Req | Behaviour | Type | Automated command | File exists? |
|---|---|---|---|---|
| R1.1 | completion registers in bash | integration | `KITTI_INTEGRATION=1 uv run pytest tests/integration/test_completion_e2e.py -x` | ❌ Wave 0 |
| R1.1 | completion registers in zsh | integration | same file, `::test_zsh_registers_completion` | ❌ Wave 0 |
| R1.1 | generated file == `shellcode()` | unit | `uv run pytest tests/unit/test_installer_completion.py -x` | ❌ Wave 0 |
| R1.1 | doctor checks file + rc line + staleness | unit | `uv run pytest tests/unit/test_doctor.py -k completion -x` | ✅ (3 tests to **rewrite**) |
| R1.2 | `clean` keeps kitty + backups | unit | `uv run pytest tests/unit/test_makefile_targets.py -x` | ❌ Wave 0 |
| R1.2 | help text matches recipe | unit | same file | ❌ Wave 0 |
| R1.3 | legacy branch works; errors on stderr | unit (subprocess) | `uv run pytest tests/unit/test_tools_uninstall_sh.py -x` | ❌ Wave 0 |
| R1.4 | pane-0 `cwd` quoted; `cmd` via `bash -lc` | unit | `uv run pytest tests/unit/test_scenes_launcher.py -k pane0 -x` | ✅ (add cases) |
| R1.4 | space-in-cwd fills the current tab | integration | `KITTI_INTEGRATION=1 uv run pytest tests/integration/test_scene_fill_tab_e2e.py -x` | ✅ (add case) |
| R1.5 | real command, stderr surfaced, payload rolled back | unit | `uv run pytest tests/unit/test_config_updater.py -k parse -x` | ✅ (add cases) |
| R1.6 | env hygiene | unit (AST) | `uv run pytest tests/integration/test_env_hygiene.py -x` | ❌ Wave 0 (or the comment-only fallback) |
| R1.7 | install log gone | unit | `uv run pytest tests/unit/test_installer_uninstall.py -k install_log -x` | ✅ (add case) |
| R1.7 | `int(stdout)` clean error | unit | `uv run pytest tests/unit/test_scenes_launcher.py -k window_id -x` | ✅ (add cases) |
| R1.7 | empty colour absent; passthrough narrowed | unit | `uv run pytest tests/unit/test_scenes_colors.py tests/unit/test_scenes_background.py tests/unit/test_scenes_accent.py -x` | ✅ (add + **invert `:124`**) |
| R1.7 | `--keep`/`--older-than` < 0 → argparse error | unit | `uv run pytest tests/unit/test_pruner.py -k negative -x` | ✅ (add cases) |
| R1.7 | doctor SKIP state | unit | `uv run pytest tests/unit/test_doctor.py -k skip -x` | ✅ (add cases) |
| R1.7 | PATH-migration + both-line hint printed | unit | `uv run pytest tests/unit/test_path_integration.py tests/unit/test_installer_uninstall.py -x` | ✅ (**rewrite `:151`**) |
| R0.11 | `src/` clean under five tools | gate, not pytest | `uv run ruff check src && uv run black --check src && uv run pyright src && uv run bandit -q -r src && uv run vulture src` | n/a |

### Sampling rate

- **Per task commit:** `uv run pytest tests/unit -q` (fast, no kitty).
- **Per wave merge:** `uv run pytest tests/ -q` — must stay at 311+ passed / 0 failed.
- **Phase gate:** `KITTI_INTEGRATION=1 uv run pytest tests/ -q` **and** `make doctor` exiting 0
  with every check PASS or SKIP (this is also Phase 1's merge precondition), **and** the five-tool
  `src/` gate above.

### Wave 0 gaps

- [ ] `tests/unit/test_installer_completion.py` — R1.1
- [ ] `tests/integration/test_completion_e2e.py` — R1.1 (must skip when `zsh` is absent)
- [ ] `tests/unit/test_makefile_targets.py` — R1.2
- [ ] `tests/unit/test_tools_uninstall_sh.py` — R1.3 (skeleton given verbatim in §R1.3)
- [ ] `tests/integration/test_env_hygiene.py` — R1.6, if option 2 is chosen
- [ ] `vulture_allowlist.py` — R0.11; referenced by `.claude/conventions.md:41`, **does not exist**
- [ ] No `[tool.vulture]` section in `pyproject.toml` — R0.11

No framework install is needed; pytest and all five tools already resolve under `uv run`.

## Security Domain

`security_enforcement: true`, `security_asvs_level: 1` in `.planning/config.json`, so this section
applies. This is a local CLI with no network listener and no user accounts, so most ASVS chapters
are vacuous — but two are directly in scope and one defect is a genuine vulnerability.

| ASVS category | Applies | Standard control in this phase |
|---|---|---|
| V2 Authentication | no | no accounts, no credentials |
| V3 Session management | no | no sessions (the "session" in `KittySession` is a kitty process) |
| V4 Access control | no | single-user local tool; the only authority boundary is the filesystem |
| V5 **Input validation / sanitisation** | **yes** | **R1.4**: `shlex.quote` on the `send-text` `cd` payload (D-08). **R1.7/D-12**: `normalize_color` rejects before any kitten call. Both are the standard controls; neither is hand-rolled |
| V6 Cryptography | no | nothing encrypted or signed |
| V12 File / resource | **yes** | `installer.py:133` fetches the upstream kitty installer over `urlopen` — bandit B310 MEDIUM. A `https://`-only assertion is the standard control; the URL is a constant today, so the risk is theoretical, but R0.11 forces the question |
| V14 Configuration | **yes** | D-09's parse check is exactly this: validate the config we wrote before trusting it. The measured finding that it misses a **missing `include`** (§R1.5 d) is an ASVS-V14 relevant gap |

### Threat patterns for this stack

| Pattern | STRIDE | Standard mitigation | Status in Phase 2 |
|---|---|---|---|
| **Shell command injection via `send-text`** | Tampering / Elevation | `shlex.quote` every interpolated value | **LIVE DEFECT.** `launcher.py:238` sends `cd /tmp/my dir; touch /tmp/PWNED` and the reused shell executes both halves. Reproduced `[h33/evidence.txt §M1]`. R1.4 fixes it — **treat it as a security fix, not a formatting nicety** |
| Argument injection into `kitten @` | Tampering | argv lists, never a shell string | already correct everywhere (`_client.kitten_at` uses a list; `subprocess` with `shell=False`) |
| Unvalidated value reaching an external parser | Tampering | client-side allow-list before the call | R1.7/D-12; the allow-list is now measured against kitty 0.49.0 (§U-2) |
| rc-file injection | Tampering | sentinel-bracketed splice, never append-blind | already correct (`path_integration._find_block`/`_splice_lines`); D-01 changes the body, not the mechanism |
| TOCTOU on the completion file | Tampering | the file is under `$HOME`, same trust domain as the rc that sources it | acceptable; note that a writable `~/.local/share/kitty-setup/` means anything that can write there can run code in the user's shell — the same property the rc file already has |
| Supply chain | Tampering | pinned `uv.lock`; `argcomplete>=3.5,<4` | **note the skew**: the installed tool venv resolves outside `uv.lock` (3.7.2 vs 3.6.3). Not a Phase 2 defect, but it is the mechanism by which an unreviewed argcomplete ends up generating shell code that the user's rc sources on every login. Worth one sentence in the SUMMARY |

**No secret, credential, retention policy or compliance requirement exists in this codebase**, so
nothing in this section rests on an assumed standard.

## Standard Stack

No new runtime dependency is needed for any part of Phase 2. Everything below is already declared.

### Core

| Library | Version | Purpose | Why standard |
|---|---|---|---|
| `argcomplete` | `>=3.5,<4` declared; **3.6.3** locked, **3.7.2** installed | shell completion for `argparse` | already the project's mechanism (`cli.py:26,471`); `shellcode()` is its documented programmatic API `[VERIFIED: signature introspected in the installed venv]` |
| `shlex` (stdlib) | 3.12 | quote the `send-text` payload | D-08 names it; the stdlib answer to shell quoting |
| `contextlib.suppress` (stdlib) | 3.12 | replace `try/except/pass` | what ruff SIM105 asks for at the two sites |
| `argparse` (stdlib) | 3.12 | `type=` validator for `--keep` | the correct layer for a CLI range check |
| `pytest` | `>=8.3.0` | R1.3's subprocess tests | D-07 forecloses bats |

### Supporting

| Library | Version | Purpose | When |
|---|---|---|---|
| `pytest-cov` | `>=5.0.0` | ≥80% coverage floor (`.claude/conventions.md:76`) | already wired |
| `black` / `ruff` / `pyright` / `bandit` / `vulture` | see `[dependency-groups] dev` | the R0.11 gate | already wired |

### Alternatives considered

| Instead of | Could use | Trade-off |
|---|---|---|
| `argcomplete.shellcode()` in-process | `subprocess` on `register-python-argcomplete` | needs the helper on `PATH` — the exact D-02 failure. Byte-identical output measured, so the subprocess buys nothing |
| an owned dir + rc source line (D-01) | `$XDG_DATA_HOME/bash-completion/completions/my-kitty` + zsh `fpath` | idiomatic and needs **no rc line**; both dirs already exist on this host. Costs the "we own it end-to-end" property D-01 chose. **Locked — recorded only** |
| per-shell completion files | one shared file | outputs are byte-identical in 3.6.3 **and** 3.7.2, so one file works today. Per-shell is version-proof and lets doctor check the shell it is actually in. Recommended |
| `shellcheck` as R1.3's test | pytest subprocess | D-07 forecloses it, and it would not catch this bug |
| a bare `bool` from `_parse_check` | a `ParseCheckResult` dataclass | `.claude/conventions.md:26` prefers dataclasses over tuples for structured data |

**Installation:** nothing to install. `uv sync` is already satisfied.

## Package Legitimacy Audit

**Phase 2 installs no external package.** Every library named above is already declared in
`pyproject.toml` and locked in `uv.lock` at `27a152a`, and the audit is therefore a verification
of the existing pins rather than an approval of new ones.

| Package | Registry | Declared | Locked | Verdict | Disposition |
|---|---|---|---|---|---|
| `argcomplete` | PyPI | `>=3.5,<4` (`pyproject.toml:10`) | `3.6.3` (`uv.lock:6-8`, sha256 `62e8ed4f…`) | OK | pre-existing; no change |
| `black`, `ruff`, `pyright`, `bandit`, `vulture`, `pytest`, `pytest-cov` | PyPI | `[dependency-groups] dev` | `uv.lock` | OK | pre-existing; no change |

**Packages removed due to a SLOP verdict:** none — none were proposed.
**Packages flagged suspicious:** none.

`gsd-tools query package-legitimacy check` was **not run**, because the gate applies to packages a
phase *installs* and Phase 2 installs none. If the planner adds a dependency, the gate applies to
that addition. `[ASSUMED: that "installs external packages" means new additions, not existing pins]`

One supply-chain observation that is a *fact*, not a package recommendation: the installed uv tool
venv resolves argcomplete **3.7.2**, outside `uv.lock`'s **3.6.3**, because `uv tool install`
resolves fresh (`tools/setup.sh:55` runs `uv tool install --reinstall --force .`). Under R1.1 that
unreviewed version generates the shell code the user's rc sources on every login. The byte
comparison in doctor's staleness check (§R1.1 ¶6 item 3) is the control that makes a change
visible.

## Don't Hand-Roll

| Problem | Don't build | Use instead | Why |
|---|---|---|---|
| Shell-quoting a path for `send-text` | manual `"` wrapping or a `replace()` chain | `shlex.quote` | the measured payload `cd /tmp/my dir; touch /tmp/PWNED` needs `'`-quoting *and* embedded-quote escaping; getting it wrong is a shell injection, not a cosmetic bug |
| Generating completion shell code | hand-written `complete -F` / `compdef` snippets | `argcomplete.shellcode()` | the generated script is 81 lines handling `ARGCOMPLETE_USE_TEMPFILES`, `_ARC_DEBUG`, fd-8 IPC, `nosort`/`nospace` and a zsh/bash runtime split. Re-implementing any of it guarantees drift from the producer side in `my-kitty` |
| Deciding which color forms are valid | a regex invented from the docs | the measured kitten matrix in §U-2 | `rgba:`, `rgb()`, `rgba()` and `hsl()` all *look* valid and are all rejected by kitty 0.49.0. Only a live probe distinguishes them |
| Range-checking a CLI integer | `if args.keep < 0: print(...); return 1` in the handler | `argparse` `type=` raising `ArgumentTypeError` | argparse then produces the standard usage message and exit 2; a handler check produces a bespoke error and a different exit code |
| Swallowing an expected exception | `try: … except X: pass` | `contextlib.suppress(X)` | ruff SIM105 at two sites; also makes the intent explicit at the teardown line U-1 touches |
| Rolling back a directory | delete-then-hope | rename-aside, restore on failure | `install()` `rmtree`s the payload *before* copying (`:236-238`), so there is nothing to restore — a real rollback needs the aside copy (§R1.5) |
| Structured returns | tuples | `dataclass` | `.claude/conventions.md:26`; `CheckResult`, `PathEditResult`, `InstallReport` are the existing precedent |
| Shell-script testing | bats, or shellcheck-as-a-test | pytest + `subprocess` + fake `HOME`/`PATH` | D-07, forced by the stack rule |

**Key insight:** every defect in this phase is an interface-boundary defect — a string crossing
into a shell, a value crossing into kitty's parser, an exit code crossing out of a subshell. The
correct fix at every one of them is the stdlib or library primitive that *owns* that boundary,
never a bespoke check. Two of the seven defects exist precisely because a boundary was crossed
with string formatting (`f"cd {p0.cwd}"`) or a truthiness fallback (`normalize_color(c) or c`).

## Architecture Patterns

### Where Phase 2's changes land

```
tools/setup.sh ──(:55)──> uv tool install --reinstall --force .
      │                        └─> ~/.local/share/uv/tools/kitty-setup/  (argcomplete 3.7.2)
      └──(:13)──> my-kitty install
                      │
                      ├─> installer.install()
                      │      ├─ _download_installer / _run_upstream_installer   (skipped if kitty.app exists)
                      │      ├─ _ensure_symlink, _write_desktop_entry
                      │      ├─ _record_install_log            ◄── R1.7/D-11  DELETE
                      │      ├─ config_updater.install()
                      │      │     ├─ rmtree+copytree payload  ◄── R1.5/D-09  needs rename-aside
                      │      │     ├─ splice sentinel block, backup
                      │      │     └─ _parse_check  ──> kitty +runpy <snippet>
                      │      │           ▲ stderr DISCARDED   ◄── R1.5/D-09
                      │      │           ▲ "--debug-config" in the error text
                      │      └─ seed_scenes()
                      │
                      ├─> write_completion_script(shell)       ◄── R1.1/D-01  NEW
                      │       argcomplete.shellcode(["my-kitty"], shell=shell)
                      │           └─> ~/.local/share/kitty-setup/my-kitty-completion.<shell>
                      │
                      ├─> path_integration.ensure_local_bin_in_path()
                      │       └─ splice block into ~/.bashrc | ~/.zshrc
                      │             body: export PATH + SOURCE the file  ◄── R1.1/D-01
                      │             (bash and zsh bodies DIFFER — compdef guard)
                      │
                      └─> _print_path_result()                 ◄── R1.7/D-13
                              ▲ ignores result.reason
                              ▲ manual_line carries one line

my-kitty doctor ──> run_checks()
      ├─ _check_parse      "skipped — …" as FAIL   ◄── R1.7/D-13 → SKIP
      ├─ _check_bindings   "skipped — …" as FAIL   ◄── R1.7/D-13 → SKIP  (×2)
      ├─ _check_parse      label "kitty --debug-config"  ◄── R1.5/D-09
      └─ _check_completion shutil.which(helper)    ◄── R1.1/D-01 → file + rc line + shellcode match

my-kitty scene launch <name>
      └─ launcher.launch_scene()
            ├─ normalize_color(tab_accent), normalize_color(p.bg)   (already correct)
            └─ KITTY_WINDOW_ID set?
                 ├─ yes ─> _fill_current_tab()
                 │            ├─ send-text "cd {p0.cwd}"      ◄── R1.4/D-08  INJECTION
                 │            ├─ send-text "{p0.cmd}"         ◄── R1.4/D-08  no bash -lc
                 │            └─ int(stdout)                  ◄── R1.7/D-13
                 └─ no  ─> new tab: _launch_argv() → --cwd=<argv element>  (safe)

my-kitty window background / tab accent
      └─ normalize_color(c) or c      ◄── R1.7/D-12  lets "" reach kitten

make clean ──> my-kitty uninstall            ◄── R1.2/D-04  destroys kitty.app + backups
make uninstall ──> tools/uninstall.sh
                      └─ $(resolve_binary)   ◄── R1.3/D-06  log() contaminates stdout
```

### Pattern 1 — injection-safe `send-text`

**What:** any value interpolated into a string that a shell will parse must be `shlex.quote`d.
**When:** every `send-text` payload in `launcher.py`. Never for a `subprocess` argv element.

```python
# Source: h33 measurement + Python stdlib shlex
import shlex

# WRONG — the reused shell parses this (measured: `; touch /tmp/PWNED` executes)
_client.kitten_at("send-text", "--match", f"id:{w}", f"cd {p0.cwd}\n", to=to)

# RIGHT
_client.kitten_at("send-text", "--match", f"id:{w}", f"cd {shlex.quote(p0.cwd)}\n", to=to)

# ALSO RIGHT, and needs no quoting: a separate argv element, no shell involved
_client.kitten_at("launch", f"--cwd={pane.cwd}", "bash", "-lc", pane.cmd, to=to)
```

### Pattern 2 — generate, then verify by byte comparison

**What:** an artefact we generate is checked by regenerating it and comparing, not by inspecting it.
**When:** the completion file (R1.1). Replaces D-03's false CLI-surface premise.

```python
# Source: h30/evidence/04 + 12; argcomplete.shellcode signature introspected in the tool venv
import argcomplete

def generate(shell: str) -> str:
    return argcomplete.shellcode(["my-kitty"], shell=shell)

def is_current(path: Path, shell: str) -> bool:
    return path.is_file() and path.read_text(encoding="utf-8") == generate(shell)
```

### Pattern 3 — log to stderr in anything whose stdout may be captured

```bash
# Source: h31 measurement
log() { printf '[uninstall] %s\n' "$*" >&2; }   # RIGHT
# log() { printf '[uninstall] %s\n' "$*"; }     # WRONG: $(resolve_binary) eats it (exit 127)
```

### Pattern 4 — a shell-runtime precondition is guarded in the shell, not in Python

```sh
# bash body — no compdef guard (measured: `command -v compdef` exits 1 in bash)
[ -f "$F" ] && . "$F"

# zsh body — compinit must have run first; guard silently, no error spam
[ -f "$F" ] && command -v compdef >/dev/null 2>&1 && . "$F"
```

### Anti-patterns to avoid

- **Truthiness as a fallback for a validator.** `normalize_color(c) or c` turns a deliberate
  `None` ("absent") back into the raw input. Measured consequence: `background=` reaches kitten.
  If a function returns `T | None` meaningfully, branch on `is None`.
- **A validated-then-discarded diagnostic.** `_parse_check` computes `result.stderr` and returns
  a bare `bool`. The information the caller needs is generated and dropped one line before it is
  needed.
- **Trusting a doc/CHANGELOG for an external CLI's verb list.** D-13's `close-os-window` looks
  entirely plausible and does not exist. `kitten @ --help` is the authority.
- **"Should work" on a shell mechanism.** The zsh `compinit` ordering hazard is invisible to
  reading and obvious to a 3-second probe.
- **Widening a suppression to silence a tool.** `.claude/conventions.md:22-24` forbids `# noqa`;
  the measured `tests/**` per-file-ignore history at `pyproject.toml:63-72` shows a previous
  attempt to widen one and the measured reason it was narrowed instead.

## Common Pitfalls

### Pitfall 1 — writing a test that asserts the completion file tracks the CLI surface
**What goes wrong:** the test fails immediately and looks like a bug in the implementation.
**Why:** D-03's rationale is false — the generated script contains zero subcommand names
(§U-3).
**How to avoid:** assert the byte match against `argcomplete.shellcode(...)` instead.
**Warning sign:** a test named `test_adding_a_subcommand_regenerates_the_file`.

### Pitfall 2 — one rc block body for both shells
**What goes wrong:** either zsh errors `command not found: compdef` on every shell start, or the
`compdef` guard silently disables completion in bash.
**Why:** `command -v compdef` exits 0 in zsh (after `compinit`) and 1 in bash — measured.
**How to avoid:** `_BLOCK_BODY_LINES` becomes `_block_body_lines(shell)`; `_block_body_matches_template`
takes the shell too.
**Warning sign:** a single `Final[tuple[str, ...]]` still at module scope after R1.1.

### Pitfall 3 — implementing `close-os-window` because the decision says so
**What goes wrong:** every integration test leaks a kitty process and pays the SIGTERM grace
period; nothing turns red, because `except HarnessCommandError: pass` hides it.
**Why:** the verb does not exist in kitty 0.49.0 (§U-1).
**How to avoid:** get U-1 resolved before writing plan `02-04`.
**Warning sign:** integration suite wall-clock time rising with no test failures.

### Pitfall 4 — using an unknown config key as the parse-check regression payload
**What goes wrong:** the test asserts a failure that never happens; `_parse_check` returns `True`.
**Why:** `accumulate_bad_lines` collects only value-conversion errors (§R1.5 d). Unknown keys,
unknown shortcut keys, invalid lines and **missing includes** all pass.
**How to avoid:** use `cursor_shape banana`, `background notacolor`, `font_size not-a-number` or
`confirm_os_window_close maybe` — each measured to fail.
**Warning sign:** a passing test that never exercised the rollback branch.

### Pitfall 5 — trusting `normalize_color`'s docstring about functional forms
**What goes wrong:** `rgba(...)` / `hsl(...)` are allowed through and fail at the kitten with a
half-built scene — the exact failure D-12 exists to prevent.
**Why:** `colors.py:21-22` claims "functional `rgb()` forms pass through unchanged (kitty
validates those)". kitty 0.49.0 rejects them (§U-2).
**How to avoid:** narrow to `rgb:` only and invert `test_scenes_colors.py:124`.
**Warning sign:** `test_functional_and_rgb_forms_pass_through` still green after D-12.

### Pitfall 6 — `git commit` in the wrong shape
**What goes wrong:** the `tools/hooks/pre-push` guard rejects the push, or `tdd_mode`'s harness
gate blocks the implementation step.
**Why:** AGENTS.md "Commit granularity" — one commit per plan, **except** a `type: tdd` plan which
makes exactly two (`RED` then `GREEN`, scoped `(<phase>-<plan>)`), and `workflow.tdd_mode: true`
makes the RED commit mandatory for any behaviour-adding task.
**How to avoid:** mark the R1.3 and R1.4 plans `type: tdd` (both have a clean failing test to
write first) and give every plan `cross_ai: true` per AGENTS.md "Cross-AI by default".
**Warning sign:** a plan with three commits and no stated independence reason.

### Pitfall 7 — running R0.11 first
**What goes wrong:** rework. `kitty_session.py:291`, `path_integration.py:58` and
`config_updater._parse_check` are simultaneously R0.11 findings and defect sites.
**How to avoid:** schedule R0.11 last; let it absorb the three for free.
**Warning sign:** a `black`/`ruff` plan numbered `02-01`.

### Pitfall 8 — asserting `doctor` exits 0 too early
**What goes wrong:** R1.1's plan claims Phase 1's merge gate is open when it is not.
**Why:** `make doctor` is exit **2** and `my-kitty doctor` is exit **1**; and the gate is "exit 0
with every check PASS or SKIP", which on this host also needs the `remote-control` SKIP (already
true: "no running kitty") and the D-13 SKIP conversions.
**How to avoid:** capture the full `my-kitty doctor` output, all nine lines, plus `echo $?`, in
the SUMMARY — as AGENTS.md "Verify before declaring done" requires.
**Warning sign:** a SUMMARY that says "doctor green" without the nine lines.

### Pitfall 9 — a zsh test on a host without zsh
**What goes wrong:** the suite fails on any machine where zsh is absent.
**Why:** zsh here is a **linuxbrew** install at `/home/linuxbrew/.linuxbrew/bin/zsh`, not system.
**How to avoid:** `pytest.mark.skipif(shutil.which("zsh") is None, reason="zsh not installed")`.

### Pitfall 10 — merging Phase 2 before the numbers in `.planning/` are corrected
**What goes wrong:** the Universal Phase Gate's step-5 "tests must not regress against the
recorded baseline" is measured against numbers that are already wrong (pyright 19→15,
vulture 12→16).
**How to avoid:** the plan that closes R0.11 updates `REQUIREMENTS.md:88-91` and `ROADMAP.md:35-37`
in the same commit, with the measured command beside each number.

## Project Constraints (from `AGENTS.md` and `.claude/conventions.md`)

Directives extracted for the planner to verify each plan against. These carry the same authority
as the locked decisions.

**From `AGENTS.md`:**
- **English everywhere** — code, comments, commits, PR text.
- **Research → experiment → decide → implement**, non-negotiable, with recorded evidence under
  `tmp/h<NN>-<slug>/` **before** the decision. No "should work" — only "verified by `<command>` →
  `<output>`". *This research file's hypothesis dirs must be recreated inside the repo by the
  executing plans.*
- **Hypothesis before implementation.** Every shipped behaviour starts in `tmp/h<NN>-<slug>/`.
- **Git policy.** Phase worktree on `gsd/phase-2-defect-remediation`; merge into `master` only
  once `make doctor` and `make test` are green. Never force-push or amend a pushed commit.
  `tools/hooks/pre-push` enforces it.
- **Commit granularity.** One commit per plan, not per task. A `type: tdd` plan makes exactly two:
  RED (tests only, failing) then GREEN (implementation + SUMMARY), scoped `(<phase>-<plan>)`.
- **Re-read before edit.** Never trust in-memory file contents.
- **Skill outputs land on disk** under `.planning/` or `docs/`.
- **Research tooling first** — `codegraph_explore` / `codegraph explore` before opening files;
  size a file (`wc -l`, `rg -n`) and read only the relevant range. Prefer `rg`, `fd`, `wc`, `bat`,
  `sd`, `eza`.
- **Cross-AI by default** — every new plan carries `cross_ai: true`.
- **Verify before declaring done** — `make doctor` **and** `make test` output captured.
- **Stack:** Python. Bash allowed **only** in `tools/setup.sh`, `tools/uninstall.sh` and
  `tools/hooks/{pre-push,post-commit,post-checkout}`. Everything else is a `my-kitty` subcommand.
  Makefile targets are ≤5 lines including the banner and dispatch when they grow.
  *Consequence for Phase 2: no new shell script may be added; R1.3's tests are pytest (D-07).*

**From `.claude/conventions.md`:**
- Python 3.12+, always via `uv run python` — never raw `python`/`python3`. Always from the repo
  root. `uv add` + `uv sync`, never `pip install`.
- **No conditional imports** except `if TYPE_CHECKING:`.
- Type hints on every function, method and class attribute. **Pyright strict, no suppressions.**
- **Never** `# noqa` / `# type: ignore` / `# pylint: disable`. Fix the root cause; if a tool is
  wrong, configure it in the config file **with rationale**.
  *Consequence for R0.11: `config_updater.py:203`, `_client.py:43,123`, `kitty_session.py:230,232`
  and `test_color_normalization_e2e.py:36` all carry `# noqa` today. `_client.py:43`'s is already
  flagged RUF100 (unused). Removing them is in scope; adding more is not.*
- Prefer classes with behaviour over free functions when state is involved; `dataclass`/pydantic
  over raw dicts and tuples; `enum` over string constants for closed option sets.
  *Consequence: `ParseCheckResult` (R1.5) should be a frozen slotted dataclass like its
  neighbours; a `shell` argument that is bash-or-zsh is a closed option set and wants a `StrEnum`.*
- `black` is the only formatter; `ruff format` is deliberately excluded.
- `vulture_allowlist.py` is for **near-term public APIs with a referenced task ID — never a
  dumping ground**. *It does not exist yet.*
- `tests/unit/` fast and mocked; `tests/integration/` real kitty. TDD is the default for new
  modules. Coverage floor ≥80%.
- **Never commit code that fails `make validate`** — note that `make validate`, `make format`,
  `make test-unit` and `make test-integration` are all documented at `conventions.md:59-67` but
  **absent from the Makefile** (`.PHONY` lists only `help install setup clean doctor test uninstall
  prune hooks`). R0.11 needs a repeatable gate command; whether that becomes a `validate` target is
  the planner's call, but the gap should be named rather than silently inherited.

**From `docs/agent-iteration.md`:**
- **R6 probe before assume** — any dependence on an external CLI's behaviour or a config format we
  do not own needs a probe artefact in `tmp/probes/<change-id>/<NN>-<slug>.md` with six fields
  (assumption, command, exit code, output, verdict, the design decision using it) *before* the task
  runs. *§U-1, §U-2 and §R1.5 d are exactly R6 findings and should be transcribed into probe
  artefacts by the executing plans.*
- **R7** — a unit stub of an external system needs a probe confirming its real shape **and** an
  integration test on the same path, and the stub must name the probe (`_per_probe_<NN>` suffix or
  a docstring). *The existing `_check_remote_control_per_probe_04` and
  `# noqa: S603 — fixed argv` comments are the precedent.*

## Assumptions Log

| # | Claim | Section | Risk if wrong |
|---|---|---|---|
| A1 | The pty TAB demonstration generalises from a pseudo-terminal to a real kitty/GNOME terminal window | R1.1 §3 limit 2 | Low. Nothing in readline/zle completion is emulator-specific, but this is reasoning, not measurement. A user-facing check after `make install` closes it |
| A2 | Naming the completion files per shell (`my-kitty-completion.bash` / `.zsh`) is preferable to one shared file | R1.1 §2, Alternatives | Low. Outputs are byte-identical in 3.6.3 and 3.7.2, so a single file works today; per-shell is a version-proofing judgement, not a measured requirement |
| A3 | `bash -lc <quoted-cmd>` via `send-text` is acceptably close to pane 1+'s `bash -lc` semantics | R1.4 caveat | Medium. The `… ; exec bash` idiom in three seeded examples behaves slightly differently (the `exec` replaces the child, not the pane's shell). Only a real run with those examples settles it — worth an integration assertion |
| A4 | The five un-stripped `KITTY_WINDOW_ID` sites beyond D-10's two are harmless | R1.6 | Low. Grounded: `rg` shows `KITTY_WINDOW_ID` is read only in `launcher.py`, and none of the five subprocess a scene launch. A future test added to `_kitty_subprocess.py` would invalidate it |
| A5 | The intent behind D-13's `close-os-window` was cleaner OS-window teardown rather than something else | U-1 | Medium. The verb does not exist, so the *intent* must be inferred. This is exactly why U-1 goes to the user rather than being resolved by the planner |
| A6 | "Reports clean" in ROADMAP criterion 6 means **zero findings at any severity** for bandit | R0.11 bandit | **High impact.** If it means "zero HIGH", bandit is already clean and 24 findings of work vanish. The wording is `all report clean for src/`, which reads as zero. **Worth one sentence of user confirmation before plan `02-05` is written** |
| A7 | The package-legitimacy gate applies to newly added packages, not to existing pins | Package Legitimacy Audit | Low. Phase 2 adds none either way |
| A8 | `vulture src tests vulture_allowlist.py` is an acceptable change to the ROADMAP's stated gate command | R0.11 vulture | Medium. It changes a command every later phase inherits, and criterion 6 explicitly scopes `tests/` out. Alternative readings (min_confidence, or a larger allowlist) are all defensible. The planner must choose and record; the user may want to weigh in |

## Open Questions

1. **U-1: what should the harness teardown do?** (user decision)
   - Known: `close-os-window` is not a `kitten @` verb; `close-window --match=all` works, including
     with 2 OS windows; `close_os_window` is a mappable action reachable via `kitten @ action`.
   - Unclear: what the D-13 item was meant to fix. No test asserts on it and no failure was
     observed with the current verb.
   - Recommendation: **drop the item**; spend the edit on `contextlib.suppress` at the same line,
     which R0.11 needs anyway. Record the probe as the reason.

2. **U-2: narrow the passthrough to `rgb:` only?** (user decision)
   - Known: `rgba:`, `rgb()`, `rgba()`, `hsl()` are all rejected by kitty 0.49.0 at both
     `set-colors` and `set-tab-color`. `rgb:HH/HH/HH` and `rgb:H/H/H` are accepted.
   - Unclear: whether the user wants functional-form *support* (translate to hex client-side) as
     opposed to passthrough. That would be a feature, not a defect fix.
   - Recommendation: narrow to `rgb:`; invert `test_scenes_colors.py:124`; note the feature idea
     as deferred.

3. **A6: does "bandit reports clean" mean zero findings or zero HIGH?** (user decision, cheap)
   - Known: 0 high / 8 medium / 19 low, six of the eight mediums being one false positive on a
     `shell=` dataclass kwarg. Zero-at-any-severity needs a `[tool.bandit] skips` block with
     per-id rationale, because `conventions.md` forbids `# nosec`.
   - Recommendation: confirm the reading before plan `02-05`; it is the difference between a
     one-line config change and a policy document.

4. **`my-kitty window background none` fails (Hidden Coupling #9).** Route to Phase 6, or fold
   into D-12?
   - Known: `set-colors background=NONE` → exit 1; `set-tab-color active_bg=NONE` → exit 0;
     Phase 6's R4.1/R4.2 need `none` to reset **both**.
   - Recommendation: record it against Phase 6 now so its discussion inherits the measurement.
     Folding it into D-12 is also reasonable and cheap — one branch in `background.py`.

5. **`make validate` / `make format` are documented but absent.** R0.11 needs a repeatable gate
   command that every later phase can run. Does the planner add the targets (≤5 lines each, per
   D-05) or does the gate stay as five separate `uv run` invocations in the SUMMARY?
   - Recommendation: add `validate` as a 5-line target; it is the only thing that makes "never
     commit code that fails `make validate`" (`conventions.md:69`) executable.

6. **Could not measure: the real `~/.bashrc`'s completion after the fix.** The safety boundary
   forbade writing to the user's rc, so the *migration* of this host's block (which currently lacks
   `EXPORT_LINE`) was proven only in a fake HOME. The first `make install` after R1.1 lands is the
   real test. State that in the SUMMARY rather than claiming it was verified.

7. **Could not measure: macOS anything.** No Mac is reachable from here. Phase 10 owns it. Nothing
   in Phase 2 is macOS-specific, but the completion mechanism has never been exercised there
   (macOS ships bash 3.2 and zsh as the default shell — `command -v compdef` behaves the same, but
   bash 3.2's `compopt` does not exist, and the generated script calls `compopt +o nospace 2>/dev/null`
   defensively at `gen-bash.sh:49`). Recorded for Phase 10, not actionable now.

## Sources

### Primary (HIGH confidence — measured on this host, 2026-09-23)
- Working tree at `27a152a`: every file:line in the drift audit read with `sed`/`rg` this session.
- `h30-argcomplete-static/` — 13 evidence files: D-02 diagnosis, argcomplete versions and flag
  surface, four generation routes, the generated script verbatim, bash `complete -p`, real TAB on
  a pty for bash and zsh, the zsh `compinit` matrix, the zsh guard, the staleness grep and the
  fd-8 producer protocol.
- `h31-uninstall-sh/evidence.txt` — the exit-127 and silent-exit-1 reproductions.
- `h32-color-forms/` — kitty `to_color`, live `kitten @ set-colors`/`set-tab-color` for 16 values,
  `my-kitty window background`/`tab accent` end-to-end, the `close-window` vs `close-os-window`
  comparison with 2 OS windows, the full `kitten @` verb list, `close_os_window` as a mappable
  action.
- `h33-minors/evidence.txt` — the pane-0 send-text payloads, `Pane` field order, `--keep -1`.
- `h34-parse-check/evidence.txt` — the `accumulate_bad_lines` truth table over ten payloads, and
  the un-rolled-back payload dir.
- `r011-sizing/evidence.txt` + `pyright.json` — the five-tool runs and the
  `black`-then-`ruff --fix` sizing in a scratch copy.
- `kitty +runpy` introspection of kitty 0.49.0 (`kitty.rgb.to_color`, `kitty.boss.Boss`,
  `kitty.actions.get_all_actions`, `kitty.config.load_config`).

### Secondary (MEDIUM confidence)
- `argcomplete.shellcode` signature and `register-python-argcomplete --help`, read from the
  installed 3.7.2 venv — authoritative for the installed version, not necessarily for 3.8+.
- `.planning/REQUIREMENTS.md`, `.planning/ROADMAP.md`, `02-CONTEXT.md`, `AGENTS.md`,
  `.claude/conventions.md`, `docs/agent-iteration.md`, `.planning/config.json` — all read this
  session.

### Tertiary (LOW confidence)
- None. **No web search and no Context7 lookup was performed or needed**: every question in this
  phase is answerable by measuring the software installed on this host, which is a strictly
  stronger source than documentation for "what does this version actually do".

## Metadata

**Confidence breakdown:**
- Standard stack: **HIGH** — no new dependency; every version read from the installed venvs.
- Defect reproduction (R1.1–R1.7): **HIGH** — all seven reproduced with the command and its output.
- Reference drift audit: **HIGH** — 32 of 32 references opened this session.
- R0.11 sizing: **HIGH** — all five tools run; the auto-fixable portion measured in a scratch copy.
- Architecture / change shapes: **MEDIUM-HIGH** — grounded in read source, but they are
  recommendations, not measurements. A3 (`bash -lc` semantics) is the weakest.
- Locked-decision corrections (U-1, U-2, U-3): **HIGH** — each rests on a live command's output,
  not on inference.
- macOS: **not assessed.** Phase 10 owns it.

**Research date:** 2026-09-23
**Valid until:** 2026-10-23 for the architectural findings. **Shorter for two specific facts:**
the `close-os-window` verdict is tied to kitty **0.49.0** and the completion-script bytes to
argcomplete **3.7.2** — re-measure both if either is upgraded before the phase executes.

**Scope discipline note for the reader:** this researcher wrote exactly one file into the
repository (`.planning/phases/02-defect-remediation/02-RESEARCH.md`), made no commit, no stage, no
branch and no push, and left `.planning/config.json`'s pre-existing modification untouched. All
hypothesis and probe artefacts live under the session scratchpad and must be recreated inside
`tmp/` by the executing plans.

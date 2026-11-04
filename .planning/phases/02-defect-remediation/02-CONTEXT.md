# Phase 2: Defect Remediation - Context

**Gathered:** 2026-09-22
**Status:** Ready for planning

<domain>
## Phase Boundary

The seven audit defects R1.1–R1.7, each fixed and pinned by a regression test, so that
`my-kitty doctor` is all PASS/SKIP on a fresh Bazzite uv-tool install and later phases inherit a
green baseline. Behaviour changes are confined to the defect sites — no keybinding work (Phases
3–4), no component split (Phase 5), no new features. R1.8 (macOS chord attribution) belongs to
Phase 3, not here.

</domain>

<decisions>
## Implementation Decisions

### R1.1 — shell completion on a uv-tool install
- **D-01:** Ship a **generated static completion file** instead of relying on a runtime helper. At install time, produce the shell-specific script (`register-python-argcomplete --shell bash|zsh my-kitty`) into `~/.local/share/kitty-setup/`, and make the rc block **source** that file rather than `eval`-ing a helper lookup. Doctor then checks a file we own plus the rc source line. — **Reversibility:** reversible — install step, rc block body, one doctor check.
- **D-02:** Root cause, already diagnosed (no research needed, only verification): the helper **does** exist at `~/.local/share/uv/tools/kitty-setup/bin/register-python-argcomplete`, but `uv tool install` exposes only the package's own entry point (`my-kitty`), so it is never on PATH. The rc block in `~/.bashrc` is correct and guards with `command -v register-python-argcomplete`, which is why completion fails silently while doctor reports it. Rejected alternatives: hardcoding the uv-internal venv path (uv owns it and may move it), and `uv tool install argcomplete` as a second global tool (installs something unrelated on the host).
- **D-03:** Generation belongs to the install path, not to a one-off script. **The instruction stands; its stated rationale was false and is corrected here (U-3, 2026-09-23).** The original reason — "the generated file must be regenerated whenever the CLI surface changes" — does not hold: the generated shellcode contains **zero subcommand names** (it dispatches to the program at completion time), so a CLI-surface change cannot stale it. The real reasons generation belongs to install are that the file must exist before the rc block sources it, and that its content tracks the *argcomplete version*, not the CLI. Consequence for the regression test: assert a **byte match against freshly generated shellcode**, not that the file mentions any subcommand.
  The experiment this decision asked for was run (h30, evidence recreated under `tmp/h30-argcomplete-static/` by the executing plan) and is **green** — real TAB completion on bash 5.3.9 and zsh 5.9.2, driven through a pty in a fake `HOME`. Three measured facts the decision did not anticipate:
  - `--shell bash` and `--shell zsh` produce **byte-identical** output in argcomplete 3.7.2; the script dispatches on `$ZSH_VERSION` at runtime. One generated file serves both shells.
  - zsh requires `compinit` to have run **before** our source line, or every shell start prints `command not found: compdef`. `bashcompinit` is **not** required. The rc block's *position* is therefore load-bearing for zsh.
  - The best invocation is in-process `argcomplete.shellcode(["my-kitty"], shell=…)`, which sidesteps the PATH lookup D-02 is about instead of working around it.

### R1.2 — `make clean`
- **D-04:** `clean` is made to match its help text: strip our config block and wipe `./tmp/`, **keeping** `kitty.app`, the `~/.local/bin/kitty` symlink, the desktop entry and every backup. Implement with the flags that already exist (`my-kitty uninstall --keep-kitty --keep-backups`). `make uninstall` remains the destructive path. Rejected: renaming the target to `purge` — that leaves no safe "reset my config" verb.
- **D-05:** The Makefile ≤5-lines-per-target rule holds; if the invocation grows past it, dispatch into `tools/` or a `my-kitty` subcommand per the stack rule.

### R1.3 — `tools/uninstall.sh`
- **D-06:** `log` writes to **stderr** inside `resolve_binary` so its output never contaminates `$(resolve_binary)`, and the error branch's message becomes visible. The legacy-binary branch works afterwards.
- **D-07:** Regression tests for the shell script are **pytest subprocess tests** with a fake `HOME`/`PATH` — not bats, not shellcheck-as-a-test. Forced by the stack rule (Python is the stack; shell exists only inside `tools/`), so this is a constraint, not a preference. The script cannot be ported into `my-kitty` wholesale: its whole purpose is to work when the binary is missing or legacy.

### R1.4 — scene fill-current-tab
- **D-08:** Shell-quote pane-0's `cwd` (`shlex.quote`) before it is sent via `send-text` (`launcher.py:238`), and give pane-0's `cmd` the same `bash -lc` semantics every other pane gets (`launcher.py:242-246` vs `_launch_argv`). Regression test: a scene whose `cwd` contains a space and a shell metacharacter. **Amended 2026-11-03 (02-13, WR-02/WR-03), from measurement:** the `shlex.quote` form is replaced. A pane-0 value is typed only when it is typeable: every character `isprintable()`, and no `'` and no `\` (fish reads a backslash-quote and a double backslash inside single quotes as escapes; kitten's `send-text` decodes Python escapes, so a decoded Ctrl-A reorders the typed line in bash, zsh and fish; zsh expands a bare `=word`, and fish a bare `%self`). Through `send-text` the fish shift therefore needs two backslashes before the quote in the recipe value, since kitten decodes `\\` to `\` and `\'` to `'`, and refusing every backslash covers it. A typed value is always **single-quoted** (`cd -- '<path>'`, `bash -lc '<cmd>'`), never `shlex.quote`d, because `shlex.quote` leaves `=bash`, `%self` and `/x/a==bash` bare and those expand. A typed `cwd` must also be **absolute** and free of `$`, and is typed normalised by `os.path.normpath`, which is what kitty's own `abspath` makes of an absolute path. Every `~`, `$`, relative or `-`-leading `cwd` takes the argv path, where kitty expands and resolves it in its own process, so kitty gives pane 0 the same meaning as every other pane (`kitty/child.py`). Anything untypeable opens the scene in a **new tab** through argv (`--cwd=<raw>`, `bash -lc <cmd>`) and prints one stderr line starting `my-kitty scene launch: pane 0's cwd or cmd cannot be typed`. `recipe._require_str` refuses a NUL with `SceneRecipeError`, since `subprocess.run` cannot pass a NUL in an argv element (`ValueError: embedded null byte` at HEAD). Cost: a pane-0 `cmd` with a quote, a backslash or a control character, or a `~`, `$` or relative pane-0 `cwd`, opens a new tab; no shipped example is affected. Scope: measured in bash, zsh and fish. For any other shell the typed words hold no quote, backslash or control character inside single quotes, so the residual risk there is a failed `cd`, not a run command, which is not claimed as measured. Rejected: shell detection (the foreground process is the querying kitten, and `cmdline` names the login shell), `--stdin` (it fixes only the decoding), refusing the scene, launcher-side expansion, and a shared expansion context. Evidence and the follow-up route: `.planning/phases/02-defect-remediation/02-13-SUMMARY.md`.

### R1.5 — config parse check
- **D-09:** The check reports the command it actually runs (`kitty +runpy load_config`, not `--debug-config`), surfaces the parser's stderr on failure instead of discarding it, and rolls the payload directory back — currently only the conf file is rolled back (`config_updater.py:194-212,271-281`). The doctor label is corrected (`doctor.py:98`).

### R1.6 — environment-dependent tests
- **D-10:** `tests/integration/test_h25_scene_launcher.py` and `test_scene_recipe_e2e.py` strip `KITTY_WINDOW_ID` from the copied environment, as `test_color_normalization_e2e.py` already does. Otherwise a run from inside a kitty window takes the fill-current-tab path and the new-tab assertions fail.

### R1.7 — minor defects
- **D-11:** **Install log: deleted, not relocated.** `_record_install_log` (`installer.py:180-183`) is removed entirely — nothing reads it, and the kitty-install spec that required it is frozen history as of Phase 1. R1.7's wording is updated from "relocate" to "remove", and the ROADMAP criterion with it.
- **D-12:** **Colors:** an empty or whitespace-only color is treated as **absent** — no kitten argument is emitted for it — matching the recipe loader's existing empty-string→`None` convention (`recipe.py:_normalise`). This replaces today's `normalize_color(c) or c` fallback, which lets `background=` reach kitten. Passthrough is narrowed from "contains `:` or `(`" to **`rgb:` only**, so `foo:bar` is rejected up front instead of half-building a scene. **Amended 2026-09-23 (U-2), from measurement:** the original wording named `rgba:`/functional forms as well, but kitty 0.49.0's own parser accepts only `rgb:` — `timeout 30 kitty +runpy 'from kitty.options.utils import to_color; to_color(c)'` → `rgb:ff/00/00` ACCEPTED, `rgba:ff/00/00/80` / `rgb(1,2,3)` / `rgba(1,2,3,0.5)` / `hsl(1,2%,3%)` all `ValueError: Invalid color name`. Allowing a form kitty rejects is the same defect D-12 exists to fix, one layer further in. Consequence for the executor: `tests/unit/test_scenes_colors.py:124` currently asserts `rgba(1,2,3,0.5)` passes through and must be **inverted**, not extended. Rejected: raising on empty — it would break a recipe that spells out `bg = ""`.
- **D-13:** Remaining minors, each with a regression test: guard `int(result.stdout.strip())` in the launcher (`:258,373,396`) into a clean error instead of a traceback; `prune --keep <0` becomes an argparse error rather than an uncaught `ValueError` (`pruner.py:28-29`); **the harness teardown verb stays `close-window`** (`kitty_session.py:292`) — **amended 2026-09-23 (U-1), from measurement:** `close-os-window` is not a `kitten @` subcommand in kitty 0.49.0 (`kitten @ --help` lists `close-tab` and `close-window` and no `close-os-window`; the name exists only as a mappable action). Because the teardown call is wrapped in `except HarnessCommandError: pass`, making the swap would leak one kitty process per integration test **silently** — strictly worse than the status quo, which was measured correct with 2 OS windows and 3 windows. The item is dropped, not deferred; if the "close the whole OS window" intent must be preserved it needs a different mechanism and its own requirement; doctor's three "skipped — …" results return a real SKIP state instead of `passed=False` (`doctor.py:91,103,111` — `CheckResult` already has the `skipped` field); the PATH-migration messages ("migrated legacy marker" / "removed duplicate legacy marker") are actually printed (`installer.py:308-320` ignores the reason `path_integration` computes); and the unsupported-shell hint prints every manual line the result carries — the PATH export, and, because no completion file is generated for a shell outside bash/zsh, an explicit statement that completion is not set up for that shell, **never** a completion line in another shell's syntax (amended 2026-09-23: the original "prints both lines" predates R1.1's static completion file, and taken literally would hand a fish user a bash `source` line — the class of untruth R1.1 exists to remove) (`path_integration.py:59`).

### Claude's Discretion
- Whether the completion file is generated by a `my-kitty` subcommand or inline in the install path (D-01/D-03).
- Test placement per defect (unit vs integration) and how the fake-HOME fixture for the shell tests is built (D-07).
- Whether `doctor`'s SKIP refactor changes `CheckResult.__str__` or only the call sites (D-13).
- Plan decomposition: `granularity: fine` is configured, so splitting these into several small plans is expected — but every plan in this phase must keep `make test` green on its own.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Phase intent and requirements
- `.planning/REQUIREMENTS.md` R1.1–R1.7 — the requirement text (R1.1 and R1.7 reworded per D-01/D-11).
- `.planning/ROADMAP.md` "Phase 2" + "Universal Phase Gate" — success criteria and the per-phase gate.
- `.planning/phases/01-governance-freeze/01-CONTEXT.md` — Phase 1 decisions that bind this phase: the mantra, `AGENTS.md` as canonical rules, the worktree/merge git model, tooling discipline (`codegraph_explore` before opening files), and the CodeGraph index lifecycle.
- `docs/prds/kitty-setup-remediation-v1.0-prd.md` §R1 — source PRD text for these defects.

### Process
- `docs/agent-iteration.md` — hypothesis/probe playbook; each behaviour change needs a recorded experiment under `tmp/h<NN>-<slug>/`.
- `.claude/conventions.md` — ruff, black, pyright, bandit, vulture; the gate every plan must pass.

### Defect sites (verified during this discussion)
- `src/kitty_setup/doctor.py:205-238` (`_check_completion`), `:91,103,111` (false-FAIL "skipped"), `:98` (wrong parse-check label).
- `src/kitty_setup/path_integration.py:19-42` (rc block body, `COMPLETION_LINE`), `:59` (unsupported-shell hint).
- `src/kitty_setup/installer.py:180-183` (`_record_install_log`, to be deleted), `:308-320` (PATH-migration messages).
- `src/kitty_setup/config_updater.py:194-212,271-281` (parse check + rollback).
- `src/kitty_setup/scenes/launcher.py:238` (unquoted `cd`), `:242-246` (pane-0 `cmd` path), `:258,373,396` (`int(stdout)`).
- `src/kitty_setup/scenes/colors.py:64-88` (`normalize_color` passthrough), `accent.py:32`, `background.py:30` (`or c` fallback).
- `src/kitty_setup/pruner.py:28-29` (`--keep` ValueError).
- `src/kitty_setup/harness/kitty_session.py:292` (teardown verb).
- `Makefile:12` (help) and `:26-28` (`clean` recipe); `tools/uninstall.sh:17,28-40,97` (`log` to stdout inside `$(resolve_binary)`).
- `tests/integration/test_h25_scene_launcher.py:393`, `test_scene_recipe_e2e.py:75` (env not stripped); `test_color_normalization_e2e.py:33` (the correct pattern to copy).

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `CheckResult` already carries a `skipped` field (`doctor.py:26`) — the SKIP fix is wiring, not new structure.
- `--keep-kitty` / `--keep-backups` already exist on `my-kitty uninstall`, so D-04 needs no new flags.
- `recipe.py:_normalise` is the existing empty-string→`None` convention D-12 aligns the color path with.
- `tests/integration/test_color_normalization_e2e.py:33` already strips `KITTY_WINDOW_ID` — the pattern D-10 copies.
- `KittySession` harness (`KITTI_INTEGRATION=1`) is the vehicle for any test needing a real kitty.

### Established Patterns
- Python is the stack; shell only inside `tools/` — this is what forces D-07's pytest-subprocess approach.
- Makefile targets are ≤5 lines and dispatch into `tools/` or `my-kitty` when they grow (D-05).
- Doctor reports one line per check with a PASS/FAIL/SKIP prefix; new states must keep that shape.

### Integration Points
- The rc block body is rendered on every install (`path_integration._BLOCK_BODY_LINES`), so D-01 changes the block contents and existing hosts migrate in place on the next install — the migration path already exists and is tested (`test_path_integration.py:226`).
- Deleting the install log (D-11) touches `InstallReport`/`_print_install_report` only if the version is reported from there; verify before removing.

</code_context>

<specifics>
## Specific Ideas

- The user's framing for R1.1: prefer a mechanism we own end-to-end over a PATH lookup that depends on uv's internals.
- `make clean` should stay the safe verb; destructive behaviour belongs to `uninstall`.
- Delete dead features rather than carefully relocating them — the install log exists only because a now-frozen spec asked for it.

</specifics>

<deferred>
## Deferred Ideas

- **R1.8 macOS chord attribution** — assigned to Phase 3, where it is a prerequisite of the oracle's attribution assertion. Not touched here.
- **Kitty never upgraded on reinstall** (`installer.py:194-196` skips whenever the binary exists) — explicitly out of scope for this milestone per PROJECT.md.
- **`doctor` remote-control FAIL format and the missing `make setup` hint** — doc/message accuracy, owned by Phase 8 (R6.1) unless a plan here touches the same line anyway.
- **Test-suite duplication** between `tests/conftest.py:23-41` and `tests/integration/_helpers.py` — noticed during the audit, not a defect; candidate for Phase 8 or a later cleanup.

</deferred>

---

*Phase: 2-Defect Remediation*
*Context gathered: 2026-09-22*

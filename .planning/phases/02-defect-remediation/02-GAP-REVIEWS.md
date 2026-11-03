# Phase 02 gap-closure plans — cross-AI plan review

Reviewer: `opencode run --model router-env/my-referee-one` (read-only), 2026-11-03. The configured `router-env/my-plan-review` reported "Model unavailable". Findings below are the reviewer's, verbatim; each plan's revision records which were applied or rejected.

## 02-12 — round 1

- [BLOCKER] `02-12-PLAN.md:595–596,625–626` — Task 3 explicitly requires `make install` against the developer’s live installation. That writes real `~/.local`, `~/.config/kitty` and shell rc files, violating the stated safety boundary; `make doctor` also invokes real kitty/kitten outside the integration runner — Remove the live-install step and replace it with scratch-HOME validation, routing real-kitty execution exclusively through `make test-integration PYTEST_ARGS=...`. Record live-install verification as deferred rather than requiring it to pass.

- [HIGH] `02-12-PLAN.md:397–416` — Comparing only `realpath` results loses protection for footprint entries symlinked outside the listed roots. On this host, `~/.local/bin/my-kitty` resolves into `~/.local/share/uv/tools/kitty-setup/bin/my-kitty`, outside every proposed root, so the guard permits executing the real installed CLI. The same issue permits removing a protected rc-file symlink whose target lies elsewhere — Check both the normalized original pathname and its resolved target against protected roots. Add self-tests for an executable symlink pointing outside the footprint and removal of a protected symlink.

- [HIGH] `02-12-PLAN.md:404–415,424–440` — The audit hook does not monitor subprocess effects. It sees Python launch `/bin/bash` or the interpreter, but a child can then write real rc/config files or access the network without invoking the parent’s hook. The proposed subprocess-based self-tests install another conftest in the child, so they do not expose this gap. T-2-55 acknowledges C-extension bypasses, not this ordinary subprocess path — Enforce explicit sandbox HOME/XDG/PATH environments at subprocess boundaries and add child-process write/network negative controls. If arbitrary child effects must be prevented, use process-level isolation; otherwise narrow the claimed guarantee and document this limitation.

- [HIGH] `02-12-PLAN.md:635–657` — The RED replay and guard-negative-control gates capture `$?` after the entire preflight `&&` chain, not just pytest. If commit lookup or tree materialization fails with status 1, execution still reaches the “pytest exited 1” checks. With a previously populated `OUT` containing the expected failure summary, both gates return 0 without running pytest; this is reproducible from the written commands — Fail immediately on every preflight error, then capture pytest’s status separately. Initialize `OUT` before execution and add a negative control demonstrating that a failed preflight cannot pass.

- [MEDIUM] `02-12-PLAN.md:398–400` — The proposed footprint omits an actual product write destination: `installer.seed_scenes()` writes through `recipe.scenes_dir()` to `~/.config/kitty-setup/scenes`, or `$XDG_CONFIG_HOME/kitty-setup/scenes`. A test accidentally reaching this real path would pass the guard despite the “no unit test reaches host state” claim — Protect these scene roots too, capturing the real XDG location before test monkeypatching, and add a blocked scene-write self-test.

- [MEDIUM] `02-12-PLAN.md:627–634` — The topology gate counts matching commit subjects, not the commits between RED and GREEN. `test(02-12)`, an extra unscoped implementation commit, and `feat(02-12)` satisfy every check while violating the exactly-two-commits requirement — Verify that GREEN’s parent is RED and that the fixed interval `RED^..GREEN` contains exactly two commits. Keep the check bounded at GREEN so later sibling plans cannot invalidate it.

- [MEDIUM] `02-12-PLAN.md:658–661` — GREEN is checked only for containing the SUMMARY and touching no tests. All behavioral gates run against the working tree, so implementation accidentally left uncommitted can make verification pass while GREEN contains only the SUMMARY — Require GREEN to contain the declared implementation/config paths and verify that those paths match the committed tree, or replay the GREEN checks from GREEN’s own materialized tree.

Not run: test execution or live-install gates; conflicts with the unwritten `02-15` plan remain unchecked.
VERDICT: REVISE

## 02-13 — round 1

- [HIGH] `02-13-PLAN.md:187–194, 283–287, 511–512` — WR-03’s claimed cross-pane equivalence is not established. The proposed expansion uses the launcher’s environment and the reused shell’s directory, whereas `_launch_argv` sends raw `--cwd` to the already-running kitty, which expands and resolves it in its own process. The tilde test deliberately changes `HOME` after kitty starts but never compares pane 1 — Route expansion-sensitive/relative targets through the argv fallback unless equivalence is demonstrated, or establish one shared expansion context; add a two-pane regression with different client/kitty HOME, variables and working directories.

- [HIGH] `02-13-PLAN.md:120–143, 340–349` — The “portable values parse identically” claim is false because `shlex.quote` leaves some shell-sensitive words unquoted. Read-only checks show accepted `cmd="=bash"` reaches bash as `=bash` but zsh as `/usr/bin/bash`; fish expands accepted `%self` to its PID — Always single-quote accepted literals rather than relying on `shlex.quote`’s safe-word shortcut, or fall back for these forms; add cross-shell RED regressions and update the structural gates accordingly.

- [HIGH] `02-13-PLAN.md:269–289` — The new integration cases are not fully HOME-isolated. `spawn_kitty` inherits the environment, and the headless runner scrubs display/kitty variables but retains HOME and XDG paths. Fish’s two redirects protect its own state, not kitty’s cache; bash’s `--noprofile --norc` does not disable history persistence — Sandbox HOME and XDG config/data/cache before spawning, explicitly isolate bash history and readline configuration, and retain the already-resolved kitty/kitten binary paths.

- [HIGH] `02-13-PLAN.md:234–247, 297–303, 352–359` — Step 0 contains only fake-socket/PTY experiments; the first required real-kitty run occurs after editing the shipping integration tests, and the corrected behavior is not proven in kitty until after implementation. This violates AGENTS.md’s real-kitty experiment-before-decision/promotion requirement — Require a headless hypothesis/prototype run through the sanctioned integration runner in Step 0, record its actual output under `tmp/h40-pane0-send-text/`, and stop rather than substitute prose when the runner is unavailable.

- [HIGH] `02-13-PLAN.md:200–201, 398–400` — The D-08 amendment described as already written does not exist: `02-CONTEXT.md:38` still contains only the original quoting decision. Merely “confirming” it can leave the fallback policy and changed cwd semantics undocumented in the binding context — Explicitly author the evidence-backed amendment, including the fallback rule, expansion policy and compatibility cost, and require its inclusion in GREEN while preserving sibling amendments.

- [MEDIUM] `02-13-PLAN.md:320, 425–453` — The commit gates do not enforce the promised TDD shape. The topology gate allows an intervening unscoped implementation commit, and both GREEN-content gates accept a SUMMARY-only commit; tests run against the working tree, so implementation can remain uncommitted while verification passes — Require `GREEN^ == RED`, exact commit path allowlists, `launcher.py` plus SUMMARY in GREEN, and confirmation that GREEN contains the implementation actually tested.

- [MEDIUM] `02-13-PLAN.md:219–224, 258–263` — No RED case proves that typeability is checked **after expansion**. An implementation checking only raw `~/d` or `$KS_PANE0_DIR` would pass the specified cases while allowing an expanded quote, backslash or control character into `send-text` — Add parametrized expansion-to-unsafe-value cases asserting no `send-text`, raw argv fallback and one diagnostic; include them in RED and its replay gate.

- [MEDIUM] `02-13-PLAN.md:486–537` — Verification and SUMMARY requirements omit a fresh `make doctor` capture, although AGENTS.md requires both `make doctor` and `make test` output for completion claims — Add a read-only doctor capture, including its exit status and all result lines, to verification and SUMMARY; do not introduce `make install` or HOME writes merely to obtain a green result.

VERDICT: REVISE

## 02-14 — round 1

- [BLOCKER] `02-14-PLAN.md:457–459,469,551–552,638–640` — Task 3 explicitly requires `make install` to rewrite the developer’s real rc and install files under `~/.local`; its acceptance criteria require those host mutations. This violates the requested safety boundary — replace this with hermetic fake-HOME verification, revise the host-dependent gates, and defer any live-host installation to a separately authorized step.

- [HIGH] `02-14-PLAN.md:33,122–127,143–156,449–454` — The guarantee that **any** later `compinit`, including `-C` over a stale dump, discovers `_my-kitty` is false. Installed zsh 5.9.2’s `compinit:491–517` sources an existing dump without scanning `fpath` under `-C`; that dump replaces `_comps`. Self-init can refresh the default dump, but not a different dump selected by a later `compinit -C -d …`, or a stale dump when an earlier initialization made the block skip self-init. Completion can disappear while doctor PASSes — add committed RED cases for these shapes, then implement cache-safe registration or explicitly narrow the guarantee and retain the unsupported-shape caveat.

- [HIGH] `02-14-PLAN.md:176–177,372` — Unlinking the legacy zsh file on **every** `write_completion_script` breaks a bash install on a home that also has the old zsh setup. `cli_install` updates only the detected shell’s rc, so writing bash completion would delete the file still sourced by the untouched `.zshrc` — remove the legacy file only after a successful **zsh** completion write; retain full legacy cleanup on uninstall and add a RED-stage guard proving bash writes preserve it.

- [HIGH] `02-14-PLAN.md:36,65,196–203,383,400–414,610` — `errors="surrogateescape"` preserves undecodable bytes but does **not** preserve line endings. The existing `read_text` calls still translate CRLF to LF, so appending or rewriting a block changes bytes outside the sentinels despite the plan’s byte-exact guarantee. An in-memory round trip confirmed this — use lossless newline handling (`open(..., newline="")` or explicit byte decoding/encoding), adjust the AST gate accordingly, and add mixed-line-ending/non-UTF-8 preservation cases to RED.

- [HIGH] `02-14-PLAN.md:193–194,227–229,429,459–462` — The supposedly completed planning amendments do not exist. Current `02-CONTEXT.md` still declares zsh position load-bearing, and `02-VALIDATION.md` has no correction 21; its `02-02-T1/T2` gates still require the predicate and move reason this plan deletes. Merely “confirming” the amendments leaves binding context inconsistent and the phase-close sweep guaranteed red — explicitly amend both documents after the evidence run, add `02-VALIDATION.md` to `files_modified`, and stage both amendments in GREEN while preserving 02-13’s context changes.

- [MEDIUM] `02-14-PLAN.md:519–520,532–533` — Both RED replay gates capture `$?` after the entire setup-and-test `&&` chain, then interpret setup failure as an expected failing test run. With a retained `OUT`, a failed setup can pass using an earlier RED transcript; a read-only shell reproduction returned gate status 0 without executing pytest — terminate on any history/materialization/environment setup failure, clear `OUT`, and capture/invert only the actual pytest or integration-runner invocation’s status.

- [LOW] `files_modified` / sibling-review coverage — `02-15-PLAN.md` is not yet present, so its shared-file compatibility remains unchecked; runtime gates were not executed in this read-only review — recheck the completed 02-12 → 02-15 sequence before execution, especially overlapping installer, doctor, configuration and validation changes.

VERDICT: REVISE

## 02-15 — round 1

- [HIGH] `02-15-PLAN.md:200–202, 522–527` — The collection backstop can be disabled by arguments the runner forwards unchanged. Both `--noconftest --pyargs tests.unit.test_pruner` and `--confcutdir=tests/integration --pyargs tests.unit.test_pruner` bypass `tests/conftest.py`; read-only collection at HEAD returned status 0 with 18 unit and 78 integration items. Adding the proposed hook cannot fix a run that never loads it — Reject conftest-disabling/restricting options, including their environment/config equivalents, or load the backstop independently of conftest discovery. Add bad-case gates through `make test-integration` for both demonstrated bypasses.

- [HIGH] `02-15-PLAN.md:431–439, 807, 841–842` — Counting findings per `(filename, rule)` is not a per-site baseline and does not fully close IN-05. Removing one legitimate B604 call and adding a dangerous `shell=True` wrapper elsewhere in the same file preserves the count and passes the proposed fence. An in-memory Bandit control confirmed that replacing installer’s shellcode call this way leaves its B604 count unchanged — Identify allowed sites by normalized call/site identity, not just counts, and add a negative control that replaces an allowed site with a forbidden call in the same file.

- [MEDIUM] `02-15-PLAN.md:187–202, 515–518` — The proposed parser incorrectly treats optional-value options as requiring the following token. Pytest’s `--cov`, `--debug`, and `--cache-show` use `nargs="?"`. For example, pytest parses `--cov -k tests` correctly, but the planning prototype consumes `-k` as the coverage value and then rejects `tests` as an outside selector. The harmless-filter defect therefore remains for valid option combinations — Distinguish mandatory from optional values, preserve option recognition after an omitted optional value, and add RED cases such as `--cov -k tests`.

- [MEDIUM] `02-15-PLAN.md:339–346` — Step 0 requires replaying the commands behind `backstop.out`, which explicitly invoke pytest with `KITTI_INTEGRATION=1` set by hand. That contradicts this plan’s prohibition at line 94 and the required integration entry point — Replace those commands with `make test-integration` invocations, or reproduce the synthetic hook behavior by calling the hook directly in an isolated unit-style probe without launching pytest under the integration variable.

- [MEDIUM] `02-15-PLAN.md:381–386, 716–717` — The required fake handlers introduce dynamically dispatched `https_open` and `http_open` methods, but no handling for their Vulture findings is planned. Scanning equivalent subclasses alongside the current tree reports both methods as unused. The existing whitelist covers neither, while GREEN forbids test-module edits and the declared scope omits `vulture_allowlist.py` — Make legitimate method references part of the RED fixture/tests, or explicitly include narrowly justified protocol-method whitelist entries in GREEN’s files and staging instructions.

- [MEDIUM] `02-15-PLAN.md:84, 603–605, 810` — The safety prohibition says `install` must never remove an aside, while Task 3 explicitly makes its successful commit step call `discard_payload_aside(previous)`. The real source already deletes that transaction’s previous-payload aside, and sibling 02-12 deliberately preserves that behavior with safer error handling — Restrict the prohibition to pre-existing/preserved interrupted-install asides, explicitly exempting cleanup of the current transaction’s aside after successful acceptance.

- [MEDIUM] `02-15-PLAN.md:700, 714` — The leftover-directory gates convert a failing `find` into success: `test -z "$(find …)"` checks empty stdout, not `find`’s status. A missing or unreadable runtime directory can therefore satisfy “nothing left”; a read-only control using an invalid directory returned shell status 0 despite `find` reporting an error — Capture and require the search status before checking its output, for example `LEFT="$(find …)" && test -z "$LEFT"`.

- [MEDIUM] `02-15-PLAN.md:775–776` — Both collection-count pipelines discard pytest’s exit status because their status is `tail`’s. Collection errors can still print a matching count: a read-only negative control produced pytest status 2 and `442 tests collected, 1 error`. A failed baseline collection can consequently lower `B` and make the floor easier to satisfy — Capture each pytest transcript and require status 0 before extracting its count; reject collection-error summaries independently.

- [MEDIUM] `02-15-PLAN.md:771–772` — The topology gate counts only subjects containing `(02-15)`, so an extra unscoped implementation commit between RED and GREEN passes despite the exactly-two-commits requirement. Ancestry alone does not establish the required two-commit shape — Require GREEN’s parent to equal RED and count all commits in `RED^..GREEN`, while retaining the RED/GREEN content checks.

VERDICT: REVISE

### 02-12 round 1 — disposition

Each finding below was checked against the source and the plan at `3d249dd` before it was applied.

| # | Sev | Finding | Disposition | Evidence |
|---|-----|---------|-------------|----------|
| 1 | BLOCKER | live `make install` in Task 3 | applied (orchestrator decision) | Step 4 now runs this tree's CLI `uninstall --keep-kitty --keep-backups` twice under `env -i` with a scratch HOME and `XDG_*`, never `make install`. The new gate exits 1 at `3d249dd` because the first run printed `restored from …bak.20250101T000000Z` (WR-04). `make doctor` is a read-only capture, with its status recorded and not asserted. Measured: exit 2, 8 PASS/SKIP lines plus a stale `FAIL completion:` from the installed tool. The PASS is deferred to the phase-close install. |
| 2 | HIGH | realpath-only comparison misses outward symlinks | applied | `readlink -f ~/.local/bin/my-kitty` gives `/var/home/bazzite/.local/share/uv/tools/kitty-setup/bin/my-kitty`. Roots and event paths are now compared in an as-written form (parent resolved) and a resolved form. `.local/bin` is narrowed to the product's four entries, because it also holds `uv` and `codegraph`. Self-tests added: `hermetic_guard_blocks_symlinked_exec` and `…_protected_symlink_removal`. |
| 3 | HIGH | hook cannot see child-process effects | applied (narrowed, per the reviewer's alternative) | `test_git_hooks.py:97-108` starts `git` with `dict(os.environ)` across the module, so a hook-level HOME rule, or process isolation, would hit benign children outside `files_modified`. The truth and T-2-55 are narrowed to "the test's own process". The A-2 rule's env part now also covers `test_makefile_clean.py` and `test_unit_hermeticity.py` (`hermetic_child_env_rule_holds`). Step 0 records an inventory of every child spawner. A child's own network use is accepted residual risk. |
| 4 | HIGH | RED replay and negative control read the `&&` chain's status | applied | Reproduced: with no RED commit and `OUT` exported, both old gates exit 0 without running pytest. Rewritten: `OUT=''` first, `\|\| exit 1` on every preflight step, and `ST=0; OUT="$(pytest …)" \|\| ST=$?`. The same shell now exits 1. The gate shape is also applied to the hermeticity, vulture, doctor and GREEN-replay gates. |
| 5 | MEDIUM | scene roots missing from the footprint | applied | `recipe.py:46-55`: `scenes_dir()` is `$XDG_CONFIG_HOME/kitty-setup/scenes`, else `~/.config/kitty-setup/scenes`, which exists on this host. Both are now roots, with `XDG_CONFIG_HOME` captured at conftest import. Self-test added: `hermetic_guard_blocks_scene_write[home_config\|xdg_config]`, where `xdg_config` monkeypatches first. The unit tests that call `seed_scenes` already set `XDG_CONFIG_HOME` to `tmp_path`. |
| 6 | MEDIUM | topology counts subjects, not commits | applied | Scratch repo `test(02-12)`, `fix:`, `feat(02-12)`: the old gate exits 0, the new one exits 1, and exits 0 once the `fix:` commit is dropped. New form: `git rev-parse "$GREEN^1"` must equal RED, and `git rev-list --count "$RED^..$GREEN"` must be 2, bounded at GREEN. |
| 7 | MEDIUM | GREEN may be SUMMARY-only while the working tree passes | applied | GREEN must contain `config_updater.py`, `Makefile`, `pyproject.toml` and the SUMMARY. Its paths are on an allowlist: those four plus `STATE`/`ROADMAP`/`REQUIREMENTS`. The inverted `rg` matches a `tests/` path. A new frozen gate replays the five touched modules from GREEN's own materialised tree. `test_makefile_clean.py` and `test_unit_hermeticity.py` now read the `Makefile` and conftest relative to `Path(__file__)`. |

Drive-by: the WR-06 truth now says LF line endings, because the plan already states that CRLF is translated. `verify.plan-structure`: valid, no errors and no warnings. `frontmatter.validate --schema plan-gap-closure`: valid.

### 02-14 round 1 — disposition

| # | Severity | Finding | Disposition | Evidence |
|---|----------|---------|-------------|----------|
| 1 | BLOCKER | Task 3 ran `make install` on the real HOME | applied | Task 3 step 5 ran `make install`, which rewrites the real rc and `~/.local`. `Makefile` `doctor:` is `@my-kitty doctor`, so it runs the installed tool, not the working tree. Replaced by a scratch-home upgrade gate, which exits 1 at `3d249dd` on the WR-06 `UnicodeDecodeError`, and by a read-only `make doctor` capture that is not gated on green. Added an R1.1 safety prohibition and T-2-76. |
| 2 | HIGH | "any later `compinit`, including `-C` over a stale dump" is false | applied, by narrowing | zsh 5.9.2 `compinit:491-517`: under `-C` an existing dump is sourced unchecked. Probed `${_comps[my-kitty]}` with `zsh -f` in a scratch HOME, two starts each. None registered for the block first then `compinit -C -d <stale dump>`, or for `compinit`, the block, then `compinit -C`, and both also register nothing under 02-02's body. The block first then `compinit` or `compinit -C` over the default dump gave `_my-kitty`. Deleting the `-d` dump gave `_python_argcomplete`, and moving the block above the first `compinit` gave `_my-kitty`. The guarantee is narrowed and disclosed in README, in doctor's PASS detail and in the amendment, and a committed real-zsh guard pins it. Cache-safe re-registration was rejected: it writes outside the block or adds a new mechanism. |
| 3 | HIGH | legacy zsh file unlinked on every write | applied | `installer.py:451,462`: `cli_install` writes only `path_result.shell`'s script. The legacy file is now unlinked only after a successful zsh write. Guard `test_bash_write_leaves_legacy_zsh_file` is green at RED and matches no RED `-k` token, and the scratch-home gate does a bash write first. T-2-74. |
| 4 | HIGH | surrogateescape does not keep line endings | applied | Python 3.12.12 round trip of `b"# caf\xe9 alias\r\nexport A=1\r\nlone\rcr\n…"`. `read_text`/`write_text` with surrogateescape returned all `\n`. `Path.read_text(newline="")` raises `TypeError` on 3.12, the floor. A bytes decode then encode was byte-exact, and `_splice_lines` kept the CRLF prefix and suffix. The plan now mandates `read_bytes`/`write_bytes` helpers. The AST gate forbids text-mode I/O: it exits 1 on HEAD, 0 on a good file, 1 on a strict codec. RED adds `rc_line_endings_kept` x2, pure ASCII, so the unit floor goes 21 to 23. |
| 5 | HIGH | CONTEXT and VALIDATION amendments do not exist | applied | `rg 'fpath\|_my-kitty' 02-CONTEXT.md` finds nothing, and `:26` still calls the position load-bearing. In `02-VALIDATION.md` the last correction is 20, and rows `:161-162` still require `_block_followed_only_by_comments` and the move reason. Task 3 step 6 makes the executor write an additive CONTEXT amendment and correction 21, with exact row re-targets, and `02-VALIDATION.md` joins `files_modified`. The gates: CONTEXT `numstat` deletions must be 0 and it must name `_my-kitty`, `fpath` and `compinit -C`, all absent at HEAD. The VALIDATION check is row-scoped: its absence half matches HEAD's rows, and it needs `fpath=`, the new reason, `read_bytes` and a `02-14` correction header. |
| 6 | MEDIUM | RED replays pass on a failed preflight | applied | Reproduced with `OUT="tests: 23 failed"` and an empty `RED`: the old chain idiom exits 0 and a fail-fast brace group exits 1. Both replays now clear `OUT`, exit 1 on any preflight failure, and capture only pytest's or the runner's own status. |
| 7 | LOW | 02-15 overlap unchecked | noted | 02-15 is wave 15, `depends_on: [02-14]`, with a `feat(02-14)`-ancestor precondition. The shared files (`installer.py`, `doctor.py`, `tools/uninstall.sh`, `README.md`, `pyproject.toml`, `test_doctor.py`, `test_tools_uninstall_sh.py`) are therefore sequential, not same-wave. 02-15 reads 02-14's B604 shape and its count of path_integration x7 and installer x1. This revision leaves both unchanged, because bytes I/O adds no `shell=` keyword, and 02-15 leaves 02-14's README note alone. 02-12 (wave 12: `pyproject.toml`, `test_doctor.py`) and 02-13 (wave 13: `02-CONTEXT.md`) come earlier, and the additive gate keeps 02-13's D-08 text. New threat ids start at T-2-74, because 02-15 holds T-2-66..73. |

Drive-by, under the gate rules:
- Topology is now `GREEN^` = RED, with `rev-list --count RED^..GREEN` = 2.
- GREEN must hold the nine declared paths and no `tests/` path, and the working tree must equal GREEN for `src/`, `tools/`, `README.md` and `pyproject.toml`.
- The RED-scope gate counts exactly five distinct paths.
- The e2e floor is 8, up from 7.
- The hypothesis directory stays h41.

`verify.plan-structure`: valid, no errors, no warnings, 3 tasks. `frontmatter.validate --schema plan-gap-closure`: valid. Not run: the commit-dependent gates and the integration runner. Planning makes no commits.

### 02-13 round 1 — disposition

Each finding was checked against source, upstream kitty and read-only shell runs in a fake HOME at `3d249dd`, on 2026-11-03. No kitty ran, and nothing was written to the real HOME.

| # | Sev | Finding | Disposition | Evidence |
|---|-----|---------|-------------|----------|
| 1 | HIGH | WR-03 cross-pane equivalence not established | applied (the reviewer's argv route) | Upstream `kitty/child.py` expands with kitty's own `os.environ`, then `abspath`s against kitty's cwd. The launcher sees neither, and the old tilde test changed HOME after the spawn. Now only an absolute, `$`-free, `normpath`'d cwd is typed; `~`, `$` and relative values go to argv, so kitty expands them. Client-side expansion and a shared context were both rejected. Added: a no-expansion prohibition, enforced by the AST payload gate, and a real-kitty cross-pane case (tilde, var, relative) with client and kitty HOME, variable and cwd set apart. |
| 2 | HIGH | `shlex.quote` bare safe words are not portable | applied | Measured: `=bash` gave `/usr/bin/bash` in zsh 5.9.2; `/x/a==bash` gave `/x/a=/usr/bin/bash` under zsh `magicequalsubst`; `%self` gave the PID in fish 4.6.0; all three were literal when single-quoted. Payloads are now always `'<value>'`, with no `shlex`. Added three unit RED items and a real-kitty zsh `magicequalsubst` case. The `02-04-T1` row, which pins `import shlex` and two `shlex.quote` lines, is amended in GREEN. |
| 3 | HIGH | integration cases not HOME-isolated | applied | Measured: `bash --noprofile --norc -i` wrote `$HOME/.bash_history` on `exit` and on SIGHUP, and `fish --no-config --private` created `~/.cache/fish`, `~/.config/fish` and `~/.local/share/fish`. An autouse fixture now sets HOME, four XDG directories, `HISTFILE` and an empty `INPUTRC` for every case in the module. The real `KITTY`, `KITTEN` and `installer.DEFAULT_DEST` are kept, because all three are import-time constants (read in source). |
| 4 | HIGH | no real-kitty experiment before the decision | applied | `docs/agent-iteration.md` R1 requires a green real-kitty hypothesis run before code lands in `tests/integration/`. Step 0 now runs `run.py` headless through `make test-integration`, from a tree materialised from HEAD. It must be red against HEAD's launcher, with both sentinel messages, and green against `prototype_launcher.py`, including a foreground-process probe. A stop rule covers an unavailable runner. |
| 5 | HIGH | D-08 amendment described as written but absent | applied | `02-CONTEXT.md:38` holds only the original D-08 at `3d249dd`. Task 3 step 3 has the executor write it on the D-08 line in D-12's format: the rule, the quoting, the cwd policy, the cost and the rejected alternatives. A GREEN gate requires it there and allows only that one line to be removed, so sibling amendments survive. `02-CONTEXT.md` is not edited now. |
| 6 | MEDIUM | commit gates do not enforce the TDD shape | applied | The new gates: `GREEN^` = RED; `rev-list --count RED^..GREEN` = 2; exact RED and GREEN path lists; the working tree equal to GREEN, with nothing uncommitted, for the files 02-13 tests. Run as written in the plan against 7 throwaway repos: the good case exits 0. An unscoped commit between RED and GREEN, a SUMMARY-only GREEN, a post-GREEN edit, a dropped sibling amendment, a RED touching `src/` and a missing GREEN each exit 1. |
| 7 | MEDIUM | no RED case for unsafe values after expansion | applied | The 7 original items were all unsafe before expansion. Added `cwd_var_expands_to_quote` and `cwd_tilde_home_backslash`; the fallback set is now 14 items and RED 19 in total. A throwaway copy failed 19/19 on `1cbcaaa`'s launcher and passed 19/19 on the prototype. Under finding 1 nothing is expanded, so these items pin that property. |
| 8 | MEDIUM | no `make doctor` capture | applied | Neither `<verification>` nor `<output>` named doctor. Task 3 step 5 now captures `make doctor exit status: <N>` plus every PASS/FAIL/SKIP line into the SUMMARY, and a gate reads them from GREEN. It is recorded rather than required green, because doctor runs the installed `my-kitty`. There is no `make install`. |

No finding was rejected. Every one held against source or a measurement.

Drive-bys:
- Every RED replay clears `OUT`, exits 2 on any preflight error and captures only pytest's own status. With no RED commit and `OUT='19 failed'` exported, the unit gate exits 2.
- The integration gates now also require zsh. The integration floor is 10, up from 7; the RED floors are 19 unit items, up from 13, and 6 integration items, up from 3.
- `02-VALIDATION.md` joins `files_modified`, taking correction 21. 02-14 already takes "the next free number".
- The new threat is T-2-77, because 02-14 holds T-2-74..76.
- `execution_context` was `@~/.claude/gsd-core/…`, a path that does not exist here because GSD is installed per project; it is now `@.claude/gsd-core/…`. 02-12, 02-14 and 02-15 still carry the old path.
- The hypothesis directory stays h40.

`verify.plan-structure`: valid, no errors, no warnings, 3 tasks. `frontmatter.validate --schema plan-gap-closure`: valid. Not run: the commit-dependent gates, the integration runner and kitty. Planning makes no commits.

### 02-15 round 1 — disposition

Each finding was checked against the source at `3d249dd` and, where it was cheap, by a read-only experiment. Evidence is in `tmp/h43-runner-selectors/`, `tmp/h44-rollback-asides/`, `tmp/h45-bandit-scope/` and `tmp/h46-installer-download/`, and each `repro.md` gained a "Revision" section.

| # | Severity | Finding | Disposition | Evidence |
|---|----------|---------|-------------|----------|
| 1 | HIGH | Forwarded options can switch off the conftest backstop | Applied | Through `make test-integration`, `--noconftest` and `--confcutdir=` each collected 18 unit and 78 integration items with status 0 (`bypass-e2e-head.out`). A scratch tree also found `-c`, `--config-file`, `-o addopts=` in every spelling, and `PYTEST_ADDOPTS` (`bypass.out`). |
| 2 | HIGH | Counting per (file, id) does not fence individual sites | Applied | Swapping installer.py's `_ARGCOMPLETE_SHELLCODE` call for a planted `shell=True` call left every per-(file, id) count unchanged, but the site keys differed (`site_gate.out`). |
| 3 | MEDIUM | The parser treats optional-value options as mandatory | Applied | pytest has 55 mandatory-value and 3 optional-value options (`nargs.out`). pytest reads `--cov -k tests` as `cov=True, keyword=tests`, while the skip-next rule refused it (`proto2.out`). |
| 4 | MEDIUM | Step 0 replays commands that set `KITTI_INTEGRATION=1` by hand | Applied | Every command in `backstop.out` sets `KITTI_INTEGRATION=1 pytest` by hand. They are replaced by `backstop_probe.py`, which calls the hook directly without starting a pytest session (`backstop_probe.out`). |
| 5 | MEDIUM | Vulture reports the fake handlers' methods as unused | Applied | Vulture reports `unused method 'https_open'` and `'http_open'` and exits 3 (`vulture.out`). `msg` and `redirect_request` are not reported. |
| 6 | MEDIUM | The R1.5 prohibition contradicts `install()`'s commit step | Applied | `config_updater.install` removes `kitty-setup.rollback` after a successful commit (`:339`, `:353-354`). |
| 7 | MEDIUM | `test -z "$(find …)"` hides a `find` failure | Applied | With `$XDG_RUNTIME_DIR` missing, the old form exits 0 and the new form exits 1 (`gate-controls.out`). |
| 8 | MEDIUM | The collection-count pipelines drop pytest's status | Applied | On a broken module, pytest exits 2 and prints `1 test collected, 1 error`. The old pipeline reads that as a count of 1 with status 0 (`gate-controls.out`). |
| 9 | MEDIUM | The topology gate counts subjects instead of checking adjacency | Applied | With an unscoped commit between RED and GREEN, the old gate exits 0 and the new one exits 1. With a later commit after GREEN, the new gate still exits 0 (`gate-controls.out`). |

How each fix was made:

- **1. The runner refuses the bypass options and drops `PYTEST_ADDOPTS`.**
  - `--noconftest`, `--confcutdir`, `-c`/`--config-file` and `-o`/`--override-ini addopts=` are usage errors in every spelling: exact, `=`, glued, or inside a short cluster. The runner exits 64 before any compositor starts.
  - `PYTEST_ADDOPTS` joins `SCRUBBED_VARIABLES`.
  - These are not bypasses, so the runner does not refuse them: `-o confcutdir=`, `--rootdir`, `--import-mode`, `-p no:<conftest>` (pytest refuses it), and abbreviations (pytest sets `allow_abbrev=False`).
  - A `-p`/`PYTEST_PLUGINS` backstop was rejected. The fake-compositor tests run the child in a `tmp_path` cwd, where loading the backstop with `-p` fails with `ImportError` (`plugin-route.out`).
  - RED adds 10 refusal cases and one `PYTEST_ADDOPTS` case. The headless gate adds both bypass runs, and each bad case is shown matching.
- **2. The fence keys each site.**
  - The key is `(path, test_id, enclosing def, callee)`. Bandit's `line_range[0]` and `col_offset` locate the call.
  - The allowlist becomes a `Counter` of site keys.
  - The guard `test_bandit_fence_sees_a_replaced_site` is the negative control.
- **3. Option values follow argparse's rules.**
  - `_VALUE_OPTIONS` (55) and `_OPTIONAL_VALUE_OPTIONS` (3) are separate sets. A token starting with `-` is never an optional value.
  - Short clusters and glued values are handled too. The planner found that the original `-xk tests` was still refused and that `-xc file` bypassed the backstop.
  - RED adds 4 cases.
- **5. Allowlist entries.** GREEN adds `_.https_open` and `_.http_open` to `vulture_allowlist.py`'s framework-idiom block. The file is now in `files_modified`, Task 2 and the GREEN-contents gate.
- **6. The prohibition is narrowed.** It now covers only pre-existing or preserved asides. The exemption is stated in R1.5, the IN-03 notes, Task 3 and T-2-72.
- **7.** The gate is now `LEFT="$(find …)" && test -z "$LEFT"`, in both runner gates.
- **8.** Each transcript is captured first and must have status 0. The count is read only from the exact no-error summary line. Warnings are allowed.
- **9.** The gate now requires `GREEN^ == RED` and `rev-list --count RED^..GREEN == 2`.

Also fixed under the gate rules:

- **Preflight short-circuits.** These gates ran `preflight && …; ST=$?`, which `gate-controls.out` shows passing with no RED commit and a stale `OUT`: the RED-state, guards-at-RED and pyright/ruff gates. In the pyright/ruff gate, a failed preflight also skipped the loop and left the trailing check to pass alone. They now start `OUT=;` and use `preflight || exit 1`. Each command's own status is captured.
- **GREEN contents.** GREEN must contain all eleven implementation paths and the SUMMARY.
- **New GREEN-replay gate.** It re-runs the 34 RED items and 13 guards from GREEN's own tree.
- **Five-tools gate.** Its `OUT=…; ST=$?` swallowed earlier failures. It is now a plain `&&` chain.
- **`make doctor` gate.** The empty output that `rg -c` gives on zero matches is now handled. The gate no longer assumes 02-14 ran `make install`.
- **`execution_context`.** It now points at `.claude/gsd-core/`, as 02-13 noted.

Rejected: none. The new floors are 34 RED items, 13 guards, 47 items replayed on GREEN, and a collect floor of `RED^ + 34`. No new threat ID is needed, because T-2-69, T-2-71 and T-2-72 were widened instead. 02-14 holds T-2-74..76 and 02-13 holds T-2-77.

Every revised gate was dry-run at `3d249dd` (`plan-gates-head.out`). All exit 1 as their `fails_when` text states, except the five-tools invariant gate, which exits 0. Three gates were not run: the whole-suite gate (it starts kitty), `make test` and `make doctor`. `verify.plan-structure`: valid, no errors, no warnings, 3 tasks. `frontmatter.validate --schema plan-gap-closure`: valid. Planning makes no commits.

## Round 2 (2026-11-03, same reviewer, after the round-1 revisions in 6e6b863)

02-12: the review timed out at 2400 s (exit 124) with no findings; re-run below.

## 02-13 — round 2

- [MEDIUM] `02-13-PLAN.md:624–658,673–675` — The revision removes `shlex.quote` and amends D-08 and the validation map, but `.planning/REQUIREMENTS.md:146–147` still explicitly specifies `shlex.quote` for R1.4. The binding requirement would contradict the shipped implementation — Add an evidence-backed R1.4 amendment describing the portable-literal rule and argv fallback; include that file in `files_modified`, GREEN staging and the exact GREEN-path gate.

- [MEDIUM] `02-13-PLAN.md:172–190,561–576,847–850` — The “anything else falls back and exits 0” contract includes NUL, which cannot cross the proposed argv boundary. TOML accepts an escaped NUL in `cwd` or `cmd`; forwarding it through `_client.kitten_at` makes `subprocess.run` raise `ValueError: embedded null byte`, which neither scene CLI wrapper catches — Reject NUL through the existing clean CLI error path before remote calls, add RED cases for both fields, and limit the successful-fallback promise to argv-representable values.

- [MEDIUM] `02-13-PLAN.md:754–758` — The GREEN cleanliness gate still converts an erroring negative check into success: `test -z "$(git status …)"` returns 0 when `git status` fails with empty stdout. A read-only shell control reproduced this with status 128 — Capture and require the command’s status separately: `STATUS="$(git status --porcelain --untracked-files=all -- $T)" && test -z "$STATUS"`. Add a negative control showing that status-inspection failure cannot pass.

VERDICT: REVISE

## 02-14 — round 2

- [HIGH] `02-14-PLAN.md:249–267,484–488` — Bytes-only I/O does not make the existing `_splice_lines` lossless during duplicate removal. If the final duplicate ends without LF, removing it strips the newline from the preceding user-authored line; a read-only reproduction changed `alias keep=yes\r\n` into `alias keep=yes\r`. The proposed tests do not cover this combination — Fix `_splice_lines` so it never trims surviving user bytes, and add RED cases combining duplicate removal, an unterminated final block and LF/CRLF user lines.

- [HIGH] `02-14-PLAN.md:326–348` — Step 0 requires standalone shell and PTY experiments only. Neither is a real kitty session, so promotion into `src/` and `tests/integration/` still violates AGENTS.md’s experiment-before-implementation rule and `docs/agent-iteration.md:17–20`. Later shell tests inside the runner do not supply the missing pre-edit experiment — Require a green, scratch-HOME, real-kitty hypothesis run through `make test-integration PYTEST_ARGS=...` before shipping-file edits, and stop if that experiment cannot run.

- [MEDIUM] `02-14-PLAN.md:555–560` — The instruction to delete the `is_zsh` test because it “only served” the position failure overlooks the surviving zsh PASS branch: `doctor.py:290` also reads `is_zsh`. Removing its definition leaves valid completion checks raising `NameError` — Explicitly retain the discriminator for the PASS branch, or replace that branch’s condition with the equivalent shell comparison.

- [MEDIUM] `02-14-PLAN.md:722–729` — The GREEN-content gate checks working-tree equality for implementation files but excludes the five test modules. Uncommitted test edits can therefore make the behavioral gates pass while the committed GREEN tree still fails its committed tests — Include all five test modules in the equality/cleanliness checks, including untracked files in the tested paths, or replay the behavioral checks from GREEN’s materialized tree.

- [MEDIUM] `02-14-PLAN.md:679–680,846–865` — `make test` output is captured only into a shell variable and inspected; the SUMMARY requirements never require retaining its exit status and transcript. Unlike the explicit doctor capture, this leaves AGENTS.md’s required two-command completion evidence incomplete — Add the `make test` exit status and output to the SUMMARY requirements and include that evidence in GREEN.

- [MEDIUM] `02-14-PLAN.md:600–615` / sibling `02-15-PLAN.md:620` — The coordinated validation corrections miss a deterministic later-plan failure: `02-15` adds `_.https_open` and `_.http_open` to `vulture_allowlist.py`, taking the count checked by `02-VALIDATION.md` row `02-10-T3` from seven to nine, while that row still requires at most seven. Neither plan schedules its correction, so the final validation sweep remains red — Make `02-15` own an additional validation-map correction that explicitly permits the two justified methods, preserving the preceding `02-13` and `02-14` amendments.

VERDICT: REVISE

## 02-15 — round 2

- [HIGH] `02-15-PLAN.md:623–650, 991–994` — Pytest argument files still bypass the revised conftest protections. Installed pytest enables `fromfile_prefix_chars="@"`, but the proposed parser forwards `@file` unchanged. A read-only check of `proto2.py` confirmed that pytest expands such a token into `--noconftest --pyargs tests.unit.test_pruner`, disabling the backstop and widening collection. Expansion also occurs when the token follows a value-taking option — Reject every standalone argv token beginning with `@` before option/value classification, or recursively expand and validate argument files. Add RED cases and a sanctioned runner bad-case gate.

- [HIGH] `02-15-PLAN.md:837–850` — The `--pyargs` gate rejects the correct backstop implementation. Pytest calls `pytest_collection_finish` in a `finally` block after `pytest_collection_modifyitems` raises; under `--collect-only -q`, it therefore prints collected unit node IDs before exiting 4. A read-only collection control returned status 4 while printing all 18 pruner node IDs. The required absence grep consequently fails even when the backstop works — Remove that node-ID absence requirement for the backstop run. Require pytest’s own status 4 and the expected diagnostic, and verify separately that no test body executes.

- [HIGH] `02-15-PLAN.md:620–622, 789–797; files_modified` — The Vulture revision breaks two existing phase-close gates without planning their correction. Adding `_.https_open` and `_.http_open` increases `vulture_allowlist.py`’s counted code lines from seven to nine, violating `02-VALIDATION.md` row `02-10-T3`’s `<= 7` limit. Row `02-09-T3` also scans without the allowlist and permits only the original five names, so both new methods fail it. Neither sibling plan corrects these rows — Include `02-VALIDATION.md` in this plan’s scope and GREEN commit, re-target both gates to the justified protocol methods, and append the next free correction after 02-13 and 02-14 while preserving their amendments.

- [HIGH] `02-15-PLAN.md:781–788, 853–854` — The mandatory whole-suite integration run is not HOME-isolated. `tests/integration/_kitty_subprocess.py:56–70` passes the real HOME and XDG paths to kitty and its interactive bash; several integration modules use this helper. The runner preserves those variables, and 02-13’s new sandbox fixture applies only to `test_scene_fill_tab_e2e.py`. Thus this gate can write real shell history and application state despite the plan’s no-real-HOME-writes guarantee — Apply scratch HOME/XDG/history isolation across every integration case exercised by this gate, retaining already-resolved kitty/kitten binary paths. Include the necessary fixtures, regression coverage and scope updates in the TDD instructions.

- [MEDIUM] `02-15-PLAN.md:859–860` — The doctor gate still requires the unchanged installed tool to exit zero with nine PASS/SKIP lines, although sibling evidence records that tool failing its completion check and every preceding gap plan defers reinstalling it until phase close. This plan likewise prohibits reinstalling, so compliant implementation cannot resolve that gate’s recorded failure — Use the sibling plans’ capture-only doctor gate: retain the exit status and all nine PASS/FAIL/SKIP lines in SUMMARY, and defer the green installed-tool requirement to the separately authorized phase-close installation.

VERDICT: REVISE

### 02-13 round 2 — disposition

Each finding was checked against the source and the plan at `6e6b863` on 2026-11-03, using read-only runs in the scratchpad. No kitty ran, and nothing was written to the real HOME.

| # | Sev | Finding | Disposition | Evidence |
|---|-----|---------|-------------|----------|
| 1 | MEDIUM | R1.4 still specifies `shlex.quote` | applied | `REQUIREMENTS.md:146-147` reads "shell-quotes pane-0 `cwd` (`shlex.quote`)". Task 3 step 5 has the executor reword the R1.4 bullet in R1.7's `reworded <date> from "…"` format; it stays `[x]`. The file joins `files_modified`, Task 3's files, GREEN's staging and the exact GREEN-path list. A new GREEN gate is presence-only, because the rewording quotes the old text. It needs `reworded <date>`, `02-13`, `single-quot`, `new tab` and `NUL` in the bullet, and every removed line must belong to the old bullet. Throwaway repos: a good rewording exits 0; SUMMARY-only, untouched, missing `single-quoted` and also-deletes-R1.5 each exit 1. `.planning/intel/requirements.md:26` is a synthesized ingest snapshot, not an AGENTS.md authoritative source, so it is left alone. |
| 2 | MEDIUM | NUL cannot cross argv, so "falls back and exits 0" is false | applied | In a scratch `XDG_CONFIG_HOME`, with `_resolve_kitten_binary` pointed at `/bin/true`, `tomllib` read `\u0000` as a NUL and `load_scene` accepted it. `cli_scene_launch` then raised an uncaught `ValueError: embedded null byte` for both `cwd` and `cmd`. This was already true at HEAD, on both paths and for every pane. Now `recipe._require_str`, which every recipe string goes through, refuses a NUL. `_launch_named_scene`'s existing `except SceneRecipeError` turns that into one line and exit 1, before any kitten call. Inline `--pane` values come from the process argv, which cannot hold a NUL. RED gains `recipe_nul_refused` x3 (`pane_cwd`, `pane_cmd`, `tab_title`) in `test_scenes_recipe.py`. In a tree materialised from HEAD these failed 3/3, and with only the refusal added the module passed 31/31; ruff, black, pyright and bandit were clean. Step 0 gains `prototype_recipe.py` and a real-kitty NUL probe: red with the `ValueError`, then green. The fallback truth and success criterion now say "every value an argv element can carry". New threat T-2-78, taken because 02-13 held only T-2-77 and T-2-78 was unclaimed. |
| 3 | MEDIUM | the GREEN cleanliness gate reads `test -z "$(git status …)"` | applied | Reproduced outside a repository: the old form exits 0 while `git status` exits 128, and `WS="$(git status …)" && test -z "$WS"` exits 128. The gate now uses the captured form. That negative control is recorded in its `fails_when`. |

No finding was rejected.

Gate-rule sweep:
- No other `test -z "$(…)"` or `test -n "$(…)"` remains.
- The `test "$(cmd)" = N` comparisons all fail closed on an empty result.
- Every RED replay still exits 2 on a preflight error.
- The topology gate still requires `GREEN^` = RED and `rev-list --count RED^..GREEN` = 2.

What follows from findings 1 and 2:
- RED holds three test modules.
- The unit RED floor is 22, up from 19. At HEAD the `-k` expression selects only `pane0_injection`.
- Step 0's before-run needs 7 failed, and its prototype run needs 9 passed.
- GREEN holds six paths.
- The touched-tests loop and the cleanliness paths include `test_scenes_recipe.py`.
- The integration floors are unchanged.

The six changed gates were extracted from the plan and confirmed byte-identical to the scripts exercised above. At `6e6b863`, each commit-dependent one exits 1, or 2 for the RED replay. `verify.plan-structure`: valid, no errors, no warnings, 3 tasks. `frontmatter.validate --schema plan-gap-closure`: valid. Not run: the integration runner, kitty, `make test` and `make doctor`. Planning makes no commits.

### 02-14 round 2 — disposition

Each finding was checked at `6e6b863` against the source, the installed kitty 0.49.2 (read only) and scratch-directory runs. No kitty ran, and nothing was written to the real HOME.

| # | Sev | Finding | Disposition | Evidence |
|---|-----|---------|-------------|----------|
| 1 | HIGH | `_splice_lines` trims the user line before a removed unterminated block | applied | HEAD's module was run in a scratch directory. Removing a final duplicate block that has no trailing LF turned `alias keep=yes\r\n` into `alias keep=yes\r`, and `alias keep=yes\n` into `alias keep=yes`. HEAD's legacy-marker removal loses the byte the same way. The fix is in `_splice_lines` (Task 2): it trims only a newline its own replacement added. Measured: the removal then keeps `\r\n`, and two in-place rewrites match HEAD's output. RED adds `rc_unterminated_tail_removal`, bash, three items: `duplicate_lf`, `duplicate_crlf`, `legacy_crlf`. Lossless I/O alone cannot pass them. The unit RED floor is now 26 (was 23). T-2-62 is widened. |
| 2 | HIGH | no real-kitty experiment before shipping edits | applied | It falls under the rule by its wording. `AGENTS.md` covers removing a code path, and this plan removes the zsh move and the position FAIL. `docs/agent-iteration.md` R1 lets no code land in `src/` or `tests/integration/` until a run is green against a real kitty session. It also falls under the rule in substance. kitty's zsh integration swaps `ZDOTDIR` (`.zshenv:6-12`), and its `precmd` hook prepends kitty's completions directory to `fpath` and calls `compdef` (`kitty-integration:81-82,108-130`). No shipped conf disables it. Step 0 now writes `prototype/` and a pytest probe, `run.py`, with six items. It runs through `make test-integration` from a scratch tree materialised from HEAD, which is 02-13's route. The probe spawns kitty itself with `HOME`, `ZDOTDIR`, four `XDG_*` and `HISTFILE` under `tmp_path`, because `spawn_kitty` passes `dict(os.environ)` (`:57`). Against HEAD the run must be red on `first_then_compinit` and on the PATH order. Against the prototype it must be green. A stop rule covers a runner `FAILED —`, a HEAD run that is not red, and a prototype run that is not green. The old `run.py` matrix is renamed `matrix.py`. The kitty probe is not promoted, a deliberate R5 deviation recorded in the SUMMARY. T-2-76 is widened. |
| 3 | MEDIUM | deleting `is_zsh` breaks the PASS branch | applied | `doctor.py:290` reads `if is_zsh:`. Task 3 now deletes only the predicate `if` and its result, and keeps `is_zsh`. |
| 4 | MEDIUM | the working-tree equality skips the test modules | applied | The GREEN-content gate now covers `src tools tests README.md pyproject.toml vulture_allowlist.py Makefile`. It uses `git diff --quiet "$GREEN"` plus `U="$(git status --porcelain --untracked-files=all …)" && test -z "$U"`. Dry-run in a scratch repo: clean exits 0. An edited test module, an untracked `tests/unit/test_stray.py` and an edited allowlist each exit 1. At HEAD the status over those paths is empty, with status 0. |
| 5 | MEDIUM | `make test` evidence not kept in the SUMMARY | applied | The `make test` and `make doctor` gates now take `make`'s own status (`|| ST=$?`). They write `make-test.txt` and `make-doctor.txt` before any verdict. The SUMMARY copies both under `## make test` and `## make doctor`. A new commit-dependent gate requires every status, result and summary line of both captures, verbatim, in GREEN's SUMMARY. Dry-runs: both capture gates were run with a stub `make`. The SUMMARY gate exits 0 when both captures are kept. It exits 1 on a missing doctor line, on a missing capture, and on a different `make test` run. |
| 6 | MEDIUM | `02-10-T3`/`02-09-T3` break on 02-15's vulture entries | not taken: routed to 02-15 | 02-15 owns `vulture_allowlist.py` and that correction, and its round-2 reviser is handling it. 02-14 adds no allowlist entry and leaves both rows alone. Its own correction keeps the "next free number" rule, so 02-15's correction follows it. |

Drive-bys, under the gate rules:
- The five-tools gate is a plain `&&` chain, so vulture's own status decides.
- The Step-0 transcript gate anchors `^FAILED` on pytest's `-ra` lines, which the runner passes through verbatim. Dry-runs on synthetic transcripts: the expected pair exits 0. A compositor-only `FAILED —`, a skipped item, a missing HEAD failure and a missing `prototype/` file each exit 1.
- `estimate` is 150000. `estimate-calibration` gives factor 1, with 0 samples.

No finding was rejected. No new threat ID is needed: T-2-62 and T-2-76 were widened, and 02-14 keeps T-2-74..76. The five new or changed gates were extracted from the plan and are byte-identical to the dry-run scripts, and all 23 `<automated>` blocks pass `bash -n`. `verify.plan-structure`: valid, no errors, no warnings, 3 tasks. `frontmatter.validate --schema plan-gap-closure`: valid. Not run: the integration runner, kitty, `make test` and `make doctor`. Planning makes no commits.

### 02-15 round 2 — disposition

Each finding was checked at `6e6b863`, whose code is byte-identical to `3d249dd`. The checks were read-only: scratch pytest trees, one `--collect-only` run through `make test-integration`, and `rg -c`/`stat` of the real HOME. No kitty ran, and nothing under the real HOME was written. Evidence is in `tmp/h43-runner-selectors/round2-*`, `tmp/h46-installer-download/round2*` and the new `tmp/h47-integration-home/`.

| # | Severity | Finding | Disposition | Evidence |
|---|----------|---------|-------------|----------|
| 1 | HIGH | `@file` argument files bypass the conftest protections | applied | pytest builds its parser with `fromfile_prefix_chars="@"`. In `round2_proto/`, `@args.txt` and `-k @val2.txt` both skipped the hook, ran unit bodies and exited 0. Through the runner, `@<argfile> --collect-only -q` collected 18 unit and 78 integration items, status 0 (`round2-argfile-e2e-head.out`). |
| 2 | HIGH | the `--pyargs` gate rejects a correct backstop | applied | `_pytest/main.py:859-867` calls `pytest_collection_finish` in a `finally`. With a raising hook, `--collect-only -q` listed all 3 ids, status 4. Without `--collect-only` it printed `no tests ran`, status 4 (`round2-pytest.out`). |
| 3 | HIGH | the two allowlist names break `02-10-T3` and `02-09-T3` | applied, by avoidance | `rg -c '^[a-zA-Z_]' vulture_allowlist.py` is 7, the row's cap. The fixture now patches the stock `HTTPSHandler.https_open`/`HTTPHandler.http_open` with `monkeypatch.setattr`, so there is no subclass. Vulture is clean under the canonical scan and `02-09-T3`'s scan, and pyright reports 0 errors. The same 5 in-memory cases pass for RED's `urlopen` and GREEN's opener (`round2-vulture.out`). No allowlist edit and no validation correction. This also settles 02-14's cross-plan item. |
| 4 | HIGH | the whole-suite integration run is not HOME-isolated | applied | The real `~/.bash_history` holds 143 lines typed by integration cases, at lines 747-889 of 1010: 120 from `test_h22_window_title.py` and 23 `touch …/PWNED` payloads from `test_scene_fill_tab_e2e.py` (`real-home.out`). |
| 5 | MEDIUM | the doctor gate requires the unreinstalled tool to pass | applied | The gate takes the siblings' capture-only form. |

How each fix was made:

- **1.** `build_pytest_args` refuses every argument whose first character is `@`, before it classifies anything, so value slots are covered. A glued `-k@x` is not expanded by argparse and passes.
  - RED adds `argfile` and `argfile_as_value`, taking the unit RED floor from 34 to 36.
  - The headless gate's bypass loop adds `@tmp/h43-runner-selectors/argfile.txt`, and Step 0 replays the bad case.
  - T-2-71 is widened.
  - Rejected: expanding and validating argument files, which would re-implement argparse's reader.
- **2.** The node-id absence check is gone. The collect-only `--pyargs` run requires status 4 and the backstop's message. A second `--pyargs` run without `--collect-only` follows it, and requires status 4, the message and `^no tests ran in `.
- **3.** `vulture_allowlist.py` leaves `files_modified`, Task 2 and the GREEN list, and GREEN must not touch it. Prohibition R0.11 forbids editing it.
- **4.** A new `tests/integration/conftest.py` holds one autouse fixture, `sandbox_integration_home`, for every integration case.
  - It sets HOME, the four XDG base directories and `HISTFILE` under `tmp_path_factory.mktemp("home")`, and drops `ZDOTDIR`.
  - It prepends the real kitty bin directory to PATH, for child `my-kitty` processes, which re-resolve `installer.DEFAULT_DEST` from the sandbox HOME.
  - The import-time `KITTY`/`KITTEN`/`DEFAULT_DEST` keep the real binaries.
  - The name has no leading underscore: pyright strict reports `_name` as `reportUnusedFunction`, measured on `conftest_shape.py`.
  - Step 0 runs `tmp/h47-integration-home/test_h47_probe.py` through the runner before the decision. That is the real-kitty experiment, and it sandboxes itself.
  - RED adds `tests/integration/test_home_sandbox.py`, so RED now holds seven modules. The case refuses to spawn unless sandboxed, then requires a typed nonce in the sandbox `HISTFILE`. Its RED failure is recorded through the runner in `red-run.txt`.
  - The whole-suite gate runs only after that case passes, and its floor is 70 passed.
  - Prohibition R1.2 now bounds which integration runs may execute a test body.
  - New threat **T-2-78**. 02-13's T-2-77 covers only its own module.
  - Rejected: HOME in the runner's `headless_env` (kitty would no longer be found at import), a sandbox in each module, and wrapping only this plan's gates.
- **5.** The doctor gate is now `OUT=''; OUT="$(make doctor 2>&1)"; ST=$?; printf 'make doctor exit status %s\n%s\n' …; test "${N:-0}" -ge 9` over PASS/FAIL/SKIP.
  - `make test` now prints `make test exit status <N>`.
  - The GREEN-contents gate requires both lines, line-anchored, in GREEN's own SUMMARY.

Also fixed: the rerun-before-RED gate had a `;` after its preflight chain, so a missing RED commit did not end the gate. It now ends with `|| exit 1`, and the dry run exits 1. Floors: 36 unit RED items, 13 guards, 49 on GREEN replay, and a collect floor of `RED^ + 37`. GREEN still holds eleven implementation paths: `tests/integration/conftest.py` replaces `vulture_allowlist.py`.

Rejected: none. One threat ID is new, T-2-78, the first after 02-13's T-2-77. 02-15 keeps T-2-66..73.

All 27 `<automated>` blocks pass `bash -n`. The 20 that start no compositor and run neither `make test` nor `make doctor` were dry-run at `6e6b863`, and each exits 1 except the five-tools gate, which exits 0 (`round2-plan-gates-head.out`). The new conftest AST gate exits 0 on `conftest_shape.py`. `verify.plan-structure`: valid, no errors, no warnings, 3 tasks. `frontmatter.validate --schema plan-gap-closure`: valid. Not run: the runner gates, kitty, `make test` and `make doctor`. Planning makes no commits.

For the orchestrator: every `make test-integration` run so far has passed the real HOME to kitty and its `bash --noprofile --norc`. That covers the `02-09-T3`/`02-10-T3` whole-suite sweeps, 02-11's runs and the planned 02-13/02-14 runs. The 143 history lines above are the measured result. bash runs without `histappend` here, so it rewrites `~/.bash_history` on SIGHUP. History was not truncated only because this host exports `HISTSIZE=50000`; elsewhere the default would cut it to 500 lines. No kitty cache write was seen (`~/.cache/kitty/main.json` is dated 2026-10-24). 02-15's fixture closes this for every run from its GREEN on. Until then, any integration run, 02-13's and 02-14's included, still writes the real history unless it is collect-only.

## 02-12 — round 2 (re-run, my-referee-one)

The 10:05 launch died at 11:10 with `Combo has no executable targets` (exit 1, no findings). Re-run 2026-11-03 on my-referee-one, with my-referee-three as fallback (not needed).

- [HIGH] `02-12-PLAN.md:334–380` — Step 0 never requires a green prototype against a real kitty session before implementation. Patched subprocess calls, scratch-HOME uninstalls and a standalone `load_config` verdict do not satisfy `AGENTS.md:33–41` and `docs/agent-iteration.md:17–20`; the kitty probe also lacks the required integration entry point — Add an isolated, headless hypothesis/prototype run through `make test-integration PYTEST_ARGS=...`, record its green output under `tmp/h38-conf-lifecycle/` before shipping-file edits, and stop if the runner is unavailable.

- [HIGH] `02-12-PLAN.md:470–482` — The guard resolves event paths against the test process’s working directory, ignoring the operation’s own path context. For example, `Popen(["./my-kitty"], cwd=<real HOME>/.local/bin)` reports executable `./my-kitty` separately from `cwd`; `_forms` checks the wrong file and permits the protected executable. Relative mutations using `dir_fd` have the same gap. These are ordinary audited Python operations, not the accepted child-process limitation — Resolve executable paths using `Popen.cwd`, honor directory descriptors on mutation events, fail closed when their context cannot be resolved, and add sandboxed negative controls for both cases.

- [MEDIUM] `02-12-PLAN.md:731–732,870–884` — `make test` is captured only into a temporary shell variable, and the SUMMARY requirements omit its exit status and transcript. Later gates overwrite `OUT`, leaving only doctor’s evidence explicitly retained despite the binding requirement to preserve both commands — Require the fresh `make test` exit status and output in `02-12-SUMMARY.md`, include them in GREEN, and verify their presence alongside the doctor capture.

- [MEDIUM] Sibling threat registers, `02-13-PLAN.md:965` and `02-15-PLAN.md:1186` — Both revisions allocate `T-2-78` to unrelated threats: recipe NUL handling and integration HOME isolation. Sequential execution does not resolve the identifier collision, so later security reconciliation cannot identify either threat unambiguously — Keep `T-2-78` with the earlier `02-13` plan and renumber `02-15`’s HOME-isolation threat to the next unused ID, updating all corresponding references.

VERDICT: REVISE

### 02-12 round 2 — disposition

Not applied yet: all four findings are carried into the next revision pass (round 3) together with the open cross-plan items in the handoff. The `T-2-78` collision (finding 4) is resolved there by renumbering 02-15's HOME-isolation threat to `T-2-79`.

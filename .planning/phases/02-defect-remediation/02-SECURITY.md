---
phase: "02"
slug: "defect-remediation"
status: verified
# threats_open = count of OPEN threats at or above workflow.security_block_on severity (the blocking gate)
threats_open: 0
asvs_level: 1
block_on: high
audited_commit: "4093b55"
created: "2026-09-24"
---

# Phase 02 — Security

> Per-phase security contract: threat register, accepted risks, and audit trail.
> Audited read-only at `d4a3a8c` (plans 02-01…02-11) and re-audited at `4093b55` (gap plans
> 02-12…02-15) on branch `gsd/phase-02-defect-remediation`, ASVS level 1,
> `security_block_on: high`. Each verdict below is backed by code in the tree and the command
> that shows it. Plan and SUMMARY statements were not accepted as evidence on their own.

---

## Trust Boundaries

| Boundary | Description | Data Crossing |
|----------|-------------|---------------|
| scene TOML `cwd`/`cmd` → pane-0 `send-text` → user's interactive shell | The only place in the module where a value is parsed by a shell (02-04) | untrusted-shaped user/seeded data → shell code |
| scene TOML → `_launch_argv` → `subprocess` list argv (`shell=False`) | Already safe, and must stay unquoted (02-04) | file paths |
| `installer._download_installer` → upstream `installer.sh` over the network → `sh` | The one network fetch; the script is executed (02-10) | remote code |
| argcomplete (tool venv) → generated completion file → sourced by user rc | Generated shell code runs at every shell start (02-01/02-02) | shell code under `$HOME` |
| `path_integration` → user's `~/.bashrc` / `~/.zshrc` | Sentinel-bracketed edits; bytes outside the markers must survive (02-02/02-07) | user rc content |
| `my-kitty uninstall` / `make clean` / `tools/uninstall.sh` → files under `$HOME` | Destructive verbs; the confirm prompt is the user's consent (02-01/02-03) | user data deletion |
| mutated `kitty.conf` + payload dir → kitty parser at next start | Parse check and payload rollback (02-05) | config |
| colour arg / scene TOML → `normalize_color` → `kitten @ set-colors`/`set-tab-color` | Client-side allow-list (02-06) | untrusted-shaped strings |
| developer env → integration child inside the nested compositor | Env scrub, detached stdin, new session (02-08/02-11) | env vars, tty, sockets |
| compositor exit status → gate verdict | The status file written by the child is authoritative (02-11) | pass/fail signal |

---

## Threat Register

Sources: `<threat_model>` blocks in `02-01`…`02-15-PLAN.md` and the Threat Ref column of
`02-VALIDATION.md` (every ID there also appears in a plan register; no orphan IDs). 81 numbered
threats (T-2-01…T-2-79, T-2-88, T-2-89; T-2-80…87 unallocated) plus `T-2-SC`, which is declared
the same way in all 15 plans and is counted once, for 82 entries.

| Threat ID | Category | Component | Severity | Disposition | Mitigation — evidence (file:line) | Status |
|-----------|----------|-----------|----------|-------------|-----------------------------------|--------|
| T-2-01 | Tampering | completion generator | medium | mitigate | In-process `argcomplete.shellcode` via `_ARGCOMPLETE_SHELLCODE` — `src/kitty_setup/installer.py:44,371-380`; no `shutil.which`/`register-python-argcomplete` call (the one match is the `:374` docstring) | closed |
| T-2-02 | Tampering | `remove_completion_script` | medium | mitigate | Only the named basenames are unlinked (`missing_ok=True`), and the directory is removed with `rmdir` only when it is empty — `installer.py:403-419`; no `rmtree` in it; tests `test_installer_completion.py:264,274,279` | closed |
| T-2-03 | DoS | `make clean` vs completion | low | mitigate | Removal guarded by `do_kitty` — `installer.py:551,617-618`; tests `test_installer_completion.py:340,351,363` | closed |
| T-2-04 | Tampering | rc-file editing | medium | mitigate | Superseded by T-2-60, T-2-62, T-2-63 (02-14). Sentinel mechanism kept: `find_block` `path_integration.py:183-193`, `_find_blocks` `:145-156`, `_splice_lines` `:196-212` (trims only a newline its replacement added); `compinit -i` `:55-57`; the zsh block is rewritten in place, never moved — `_render_block` `:136-142`; bytes-level rc I/O `:166-172`; outside-marker exact-equality tests `test_path_integration.py:85-124,360,382,403,454-516` | closed |
| T-2-05 | Tampering | completion file bytes | medium | mitigate | Superseded by T-2-64 (02-14). Doctor compares `script.read_bytes()` with `generate_completion_script(...).encode("utf-8")` — `doctor.py:281-291`; tests `test_doctor.py:209` (stale), `:291` (CRLF-only change FAILed). Advisory A-4 closed | closed |
| T-2-06 | Spoofing | unexpected `$SHELL` | low | mitigate | Unsupported shell skips — `path_integration.py:232-245`, `doctor.py:247-256` (no silent `.zshrc` default); tests `test_path_integration.py:151`, `test_doctor.py:231` | closed |
| T-2-07 | Info disclosure | doctor detail strings | low | accept | Accepted Risks Log AR-01 | closed |
| T-2-08 | DoS | `make clean` destructiveness | **high** | mitigate | `Makefile:30` `my-kitty uninstall --keep-kitty --keep-backups`; help `Makefile:12` and `README.md:46` say "(keeps kitty + backups)"; tests `test_makefile_targets.py:49,59`, `test_installer_uninstall.py:141` | closed |
| T-2-09 | Tampering | uninstall test sandbox | **high** | mitigate | `tests/unit/test_tools_uninstall_sh.py:59-77`: replacement `env=` with a fake `HOME`/`PATH`, plus `timeout=` and `cwd=`; `KITTI_FORCE=1` by default; AST gate re-run → `runs 1 env_reads 0`, exit 0 (see advisory A-2) | closed |
| T-2-10 | Info disclosure | uninstall.sh diagnostics on stderr | low | accept | Accepted Risks Log AR-02 | closed |
| T-2-11 | EoP | captured log line executed as a command | medium | mitigate | `tools/uninstall.sh:17` `log()` writes to `>&2`; `resolve_binary` puts only the binary name on stdout — `:19-41`; test `test_tools_uninstall_sh.py:108` | closed |
| T-2-12 | Tampering/EoP | pane-0 `cwd` in `send-text` | **high** | mitigate | Superseded by T-2-56, T-2-57, T-2-58 (02-13). Typed only when absolute, `$`-free and typeable (`isprintable()`, no `'`, no `\`) — `scenes/launcher.py:229-252`; typed as `cd -- '<normpath>'` — `:296-306`; otherwise one stderr line and the new-tab argv path — `:417-428`; the only `send-text` sites in `src/` are `:299,:310`; no `shlex.quote`/`expanduser`/`expandvars` in `src/`; tests `test_scenes_launcher.py:594-601,617-719`; real kitty `tests/integration/test_scene_fill_tab_e2e.py:157` (space + `;` sentinel), `:215` (fish), `:244` (bash `\x01`), `:278` (cross-pane), `:328` (zsh) | closed |
| T-2-13 | Tampering | pane-0 `cmd` in `send-text` | **high** | mitigate | Superseded by T-2-56, T-2-57 (02-13). `bash -lc '<cmd>'` typed only when `_typeable(cmd)` — `launcher.py:252,307-317`; otherwise argv `bash -lc <cmd>` in a new tab — `:417-428`, `_launch_argv` `:116-140`; tests `test_scenes_launcher.py:604-606,647-655,704-705` | closed |
| T-2-14 | DoS | unguarded `int(stdout)` | low | mitigate | `_window_id_from` raises `SceneClientError` — `launcher.py:168-181`, used at `:329,:446,:469`; CLI catches at `:539-541,:571-573`; test `test_scenes_launcher.py:679` | closed |
| T-2-15 | Tampering | quoting spreading to the argv path | medium | mitigate | `_launch_argv` (`launcher.py:116-140`) has no `shlex` (AST region check → `False`); test `test_scenes_launcher.py:621` | closed |
| T-2-16 | Tampering | payload dir across a failed install | medium | mitigate | Rename-aside before the copy, and the aside is deleted only after success — `config_updater.py:388-399`; the handler catches `BaseException` — `:397`; a failed restore keeps the aside and names it — `:334-356`; a stale aside is kept under a dated name and never deleted — `:298-331`; tests `test_config_updater.py:542-702` (includes `ctrl_c`) (see advisory A-5) | closed |
| T-2-17 | Repudiation | discarded parser stderr | medium | mitigate | `ParseCheckResult.stderr` — `config_updater.py:114-125,227-258`; in the error — `:261-267`; in doctor — `doctor.py:108-123` | closed |
| T-2-18 | Spoofing | wrong command name in error text | low | mitigate | `command=shlex.join(argv)` built from the argv actually executed — `config_updater.py:239,257`; used in `doctor.py:120,122`; no `--debug-config` literal remains | closed |
| T-2-19 | Tampering | parse check blind to a missing `include` | medium | accept | Accepted Risks Log AR-03 (routed to Phase 5) | closed |
| T-2-20 | Info disclosure | parser stderr in user-facing message | low | accept | Accepted Risks Log AR-04 | closed |
| T-2-21 | Tampering | unvalidated colour to kitty | medium | mitigate | Allow-list: `#hex`, names, anchored `rgb:`, `NONE` — `scenes/colors.py:50,55,75-99`; `rgba`/`hsl` absent from the source; tests `test_scenes_colors.py:122-189` | closed |
| T-2-22 | Tampering | truthiness fallback | medium | mitigate | Explicit `is None` — `scenes/background.py:32-34`, `scenes/accent.py:36-49`; no `normalize_color(...) or` anywhere in `src/` | closed |
| T-2-23 | DoS | half-built scene | low | mitigate | All colours normalised before the first kitten call — `launcher.py:405-408`; test `test_scenes_colors.py:264` | closed |
| T-2-24 | Tampering | prefix-matched `rgb:` | low | mitigate | `_RGB_COLON_RE.fullmatch` — `colors.py:90`; tests `test_scenes_colors.py:177-189` (`rgb:xyz/00/00`, `rgb:0/0/0/0`) | closed |
| T-2-25 | Repudiation | PATH report / rc `OSError` | medium | mitigate | `result.reason` printed — `installer.py:441-462`; `OSError` → one stderr line, exit 1 — `installer.py:503-508`; tests `test_path_integration.py:454,464`, `test_installer_completion.py:228` | closed |
| T-2-26 | Repudiation | single-line manual hint | low | mitigate | One `manual_lines` entry per line — `installer.py:454-455`; test `test_path_integration.py:479` | closed |
| T-2-27 | Tampering | install log written into the repo | low | mitigate | `_record_install_log` and `install.log` absent from `src/`; tombstone tests `test_installer_uninstall.py:259,307` | closed |
| T-2-28 | DoS | deleting `_repo_root` | medium | mitigate | `_repo_root` survives — `installer.py:90`, callers `:110,:124` | closed |
| T-2-29 | Tampering | ambient `KITTY_WINDOW_ID` | low | mitigate | Pops in `tests/integration/test_scene_recipe_e2e.py:80,125`, `test_color_normalization_e2e.py:33`, `test_h25_scene_launcher.py:393`; AST rule in the unit tree `tests/unit/test_integration_env_hygiene.py:225` | closed |
| T-2-30 | DoS | `prune --keep -1` | low | mitigate | `_non_negative_int` → `ArgumentTypeError` — `cli.py:36-49,127,135`; library guards kept — `pruner.py:29,38`; test `test_cli.py:133` | closed |
| T-2-31 | Repudiation | non-existent teardown verb suppressed | medium | mitigate | Verb stays `close-window` — `harness/kitty_session.py:323-324`; `close-os-window` absent from `src/`; pin `tests/unit/test_harness_teardown.py` | closed |
| T-2-32 | DoS | later refactor of the teardown | low | mitigate | The pin above existed before 02-09 and passes after it | closed |
| T-2-33 | DoS | `contextlib.suppress` rewrite | medium | mitigate | `kitty_session.py:323` `contextlib.suppress(HarnessCommandError)` keeps the verb; the pin passes | closed |
| T-2-34 | DoS | deleting vulture-flagged symbols | medium | mitigate | Only the four named symbols are gone (`rg` over `src/ tests/ tools/` → none); survivors `session_dir` `kitty_session.py:148`, `_make_socket_dir` `:95`, `_remove_socket_dir` `:338`, `_find_window_by_id` `tests/integration/test_h25_scene_launcher.py:43` | closed |
| T-2-35 | DoS | partial signature update | low | mitigate | `env_path` removed in one commit `35f9cc7`; no reference left; 369 targeted unit tests pass | closed |
| T-2-36 | Repudiation | partial gate recorded as pass | medium | mitigate | `02-09-SUMMARY.md:134-139,234-250` records the three gates as **red until 02-10** | closed |
| T-2-37 | Tampering | installer-script fetch | medium | mitigate | `installer.py:193-199` raises `ValueError` for a non-`https` scheme before `build_opener` (`:200`), `mkstemp` (`:201`) and `opener.open` (`:205`); every redirect hop refused unless https — `_HttpsOnlyRedirectHandler` `:170-189` (T-2-66); fd owned by `os.fdopen`, temp file unlinked on any failure `:203-209` (T-2-67); `cli_install` catches `ValueError` `:492-499` (T-2-68); no `assert` in the function; tests `test_installer_download.py:128,154,171,186,197,216`. Advisory A-1 closed | closed |
| T-2-38 | Tampering | hardcoded temp path | low | mitigate | `tempfile.gettempdir()` — `kitty_session.py:103,261`; no `"/tmp` literal in `src/`; test `test_kitty_session_env.py:61` | closed |
| T-2-39 | Repudiation | over-broad tool suppression | medium | mitigate | Bandit rationale per id `pyproject.toml:148-164`, `skips = ["B404","B603","B604","B607"]` (`:164`, B310 removed with its only site); B604/B607 fenced per site with `skips` pinned — `tests/unit/test_bandit_scope.py:31-48,128-141`, negative control `:144-169` (T-2-69); `urllib.request` only in `installer.py` — `:172-186` (T-2-70); ruff `src/` entries per file with reasons `pyproject.toml:117-137` (`installer.py` = `S603`,`S607`); zero `# noqa`/`# nosec`/`# type: ignore` in `src/`. Advisory A-3 closed | closed |
| T-2-40 | Repudiation | vulture scope hiding findings | medium | mitigate | `[tool.vulture]` holds only `ignore_decorators` — `pyproject.toml:160-165`; `vulture_allowlist.py` has 5 names in 7 code lines | closed |
| T-2-41 | Repudiation | wrong recorded baseline | medium | mitigate | pyright `src/` = **15** — `ROADMAP.md:35-36`, `REQUIREMENTS.md:88`; vulture scope named; no `999` placeholder remains | closed |
| T-2-42 | DoS | whole-file ROADMAP write | **high** | mitigate | `rg -c '^### Phase [0-9]+(\.[0-9]+)?:' .planning/ROADMAP.md` → **11**, including `Phase 8.5` (`:226`) | closed |
| T-2-43 | Repudiation | wrapper status replacing pytest's | **high** | mitigate | Verdict comes from the child's status file — `harness/integration_runner.py:362,396,419-423`; the compositor's status is only logged; test `test_integration_runner.py:341` | closed |
| T-2-44 | Repudiation | a run that didn't happen reported green | **high** | mitigate | No compositor → 69 `:455-462`; bad `XDG_RUNTIME_DIR` → 69 `:464-471`; missing status → 70 `:406-412`; timeout → 70 `:385-392`; tests `test_integration_runner.py:285,317,353,439` | closed |
| T-2-45 | Info disclosure/Tampering | integration test reaching the live kitty | medium | mitigate | `SCRUBBED_VARIABLES` `:55-65` applied by `headless_env` `:339-343`; `stdin=DEVNULL`, `start_new_session=True` `:373-380`; test `test_integration_runner.py:207` | closed |
| T-2-46 | DoS | orphaned cage/kitty | medium | mitigate | Process group killed in `finally` — `:382-395`, `_CompositorGroup.terminate` `:200-212`; leftover → 70 `:398-405`; SIGTERM/SIGHUP handlers `:473-485`; socket dir 0700 removed on every exit path — `kitty_session.py:95-104,169-172,185-186,338-343`; tests `test_integration_runner.py:370,388,409`, `test_kitty_session_socket.py:63,77,91` | closed |
| T-2-47 | Tampering | log text confusing the summary parser | low | mitigate | Compositor stderr goes to `tmp/test-integration/compositor.log` (`:76,360,378`); test `test_integration_runner.py:455` | closed |
| T-2-SC | Tampering | dependency installs (all 15 plans) | low | accept | Accepted Risks Log AR-05; verified: `git diff 5452f54 d4a3a8c -- uv.lock` and `git diff --stat 8f8f23e 4093b55 -- uv.lock` are empty, and the `pyproject.toml` diffs touch only `[tool.*]` sections | closed |
| T-2-48 | Tampering | conf restore on a failed install | medium | mitigate | One `try` from the first conf write through the parse check, `except BaseException` → `_restore_conf` → re-raise — `config_updater.py:415-421,440-470`; payload rollback `:393-399`; tests `test_config_updater.py:747-801` (timeout, ctrl_c, unrunnable, missing_binary, write_oserror; first install) | closed |
| T-2-49 | DoS | parse check that cannot finish | low | mitigate | `FileNotFoundError`/`TimeoutExpired`/`OSError` → `ConfigUpdaterError` — `config_updater.py:248-255`; caught `doctor.py:113-116`, `installer.py:492-499`; tests `test_config_updater.py:804-820`, `test_doctor.py:529-541` | closed |
| T-2-50 | Tampering | uninstall restoring a block-bearing backup | medium | mitigate | `_latest_backup` skips marker-bearing backups — `config_updater.py:197-211`; none → conf deleted `:502-509`; tests `test_config_updater.py:823-847` | closed |
| T-2-51 | Tampering | non-UTF-8 `kitty.conf` | medium | mitigate | `errors="surrogateescape"` on all 7 conf I/O calls — `config_updater.py:209,443,445,460,496,511,531`; tests `test_config_updater.py:850-864`, `test_doctor.py:544-552` (see A-7) | closed |
| T-2-52 | DoS | commit-step `rmtree` failure | low | mitigate | Symlinked aside unlinked — `config_updater.py:286-295`; `OSError` → one stderr line naming the kept aside `:400-411`; next install preserves it `:298-331`; tests `test_config_updater.py:867-902` | closed |
| T-2-53 | Repudiation | `make clean` masking a failed uninstall | low | mitigate | `command -v` guard, no `\|\| true` — `Makefile:28-31`; tests `test_makefile_clean.py:60,68,76` | closed |
| T-2-54 | Tampering/Info disclosure | unit tests reaching host state | medium | mitigate | Autouse audit-hook guard (exec in its context, write-open, mutations with `dir_fd`, non-loopback connect and lookups, all prefix forms, fail-closed, teardown failure) — `tests/unit/conftest.py:38-371`; self-tests `test_unit_hermeticity.py:79-434`; A-2 rule `:437-521` (see U-3, A-7) | closed |
| T-2-55 | Tampering | effects the audit hook cannot see | low | mitigate | Limits named `tests/unit/conftest.py:20-25`; no allow-list; child-env AST rule over three modules `test_unit_hermeticity.py:437-521`; bandit child recorded `02-15-SUMMARY.md:173-180`; residual AR-06 | closed |
| T-2-56 | Tampering/EoP | pane-0 `send-text` parsed differently by the reused shell | **high** | mitigate | Typeable rule `scenes/launcher.py:229-252`, sole call site `:417-428`, single quotes `:302,313`; tests `test_scenes_launcher.py:617-712`; real kitty `test_scene_fill_tab_e2e.py:215` (fish), `:328` (zsh) | closed |
| T-2-57 | Tampering/EoP | kitten Python-escape decoding | **high** | mitigate | No `\` admitted — `launcher.py:238`; tests `test_scenes_launcher.py:619-621,653-655`; real kitty `test_scene_fill_tab_e2e.py:244-267` | closed |
| T-2-58 | Tampering | pane-0 `cwd` meaning | medium | mitigate | Absolute, `$`-free, `normpath`, `cd -- '…'` — `launcher.py:248-250,302`; tests `test_scenes_launcher.py:625-640,715-719`; real kitty `test_scene_fill_tab_e2e.py:278-326` | closed |
| T-2-59 | DoS | untypeable pane 0 opens a new tab | low | accept | AR-08 | closed |
| T-2-60 | Tampering | install moving the zsh block | medium | mitigate | In-place splice `path_integration.py:136-142`; fpath body `:95-108`; tests `test_path_integration.py:85-124`, `test_completion_e2e.py:147-161` | closed |
| T-2-61 | DoS/Repudiation | doctor FAILing on block position | medium | mitigate | No position check `doctor.py:236-307`; tests `test_doctor.py:262`, `test_completion_e2e.py:164-204` | closed |
| T-2-62 | DoS/Tampering | rc bytes (non-UTF-8, CRLF, lone CR, unterminated tail) | medium | mitigate | `read_bytes`/`write_bytes` + surrogateescape `path_integration.py:166-172`; `_splice_lines` `:196-212`; tests `test_path_integration.py:442-516`, `test_doctor.py:280` (see A-7, U-2) | closed |
| T-2-63 | Tampering | duplicate blocks never converging | low | mitigate | `path_integration.py:254-283`; test `test_path_integration.py:420-439` | closed |
| T-2-64 | Tampering | decoded-text staleness check | low | mitigate | `doctor.py:281-291`; test `test_doctor.py:291` | closed |
| T-2-65 | EoP | planted `_*` in our fpath dir | low | accept | AR-09 (see U-1) | closed |
| T-2-66 | Tampering/EoP | https→http redirect | medium | mitigate | `installer.py:170-189,200`; tests `test_installer_download.py:154-168,216` | closed |
| T-2-67 | DoS/Info disclosure | fd and temp-file leak | low | mitigate | `installer.py:201-209`; tests `test_installer_download.py:171-194` | closed |
| T-2-68 | Repudiation | refused URL as traceback | low | mitigate | `installer.py:492-499`; test `test_installer_download.py:197-213` | closed |
| T-2-69 | Repudiation | global bandit skips | medium | mitigate | `pyproject.toml:164`; `tests/unit/test_bandit_scope.py:31-48,128-169` | closed |
| T-2-70 | Tampering | second fetch outside `installer.py` | low | mitigate | `test_bandit_scope.py:172-186` (an import fence only) | closed |
| T-2-71 | Repudiation/DoS | integration run widened to the unit tree | low | mitigate | `harness/integration_runner.py:90-152,250-336,339-343,363-372,426-485`; backstop `tests/conftest.py:48-68`; tests `test_integration_runner.py:505-674` | closed |
| T-2-72 | Tampering (data loss) | uninstall vs payload asides | medium | mitigate | `installer.py:549-586`; `config_updater.py:270-295`; `tools/uninstall.sh:68-71`; tests `test_installer_uninstall.py:332-431` | closed |
| T-2-73 | Repudiation | kept asides unannounced | low | mitigate | `installer.py:571-576`; `doctor.py:83-88`; `tools/uninstall.sh:70`; tests `test_installer_uninstall.py:383-404`, `test_doctor.py:558-574` | closed |
| T-2-74 | Tampering | bash install deleting the legacy zsh script | medium | mitigate | Unlink only after a zsh write `installer.py:396-399`, and on uninstall `:411`; tests `test_installer_completion.py:82-111` | closed |
| T-2-75 | Repudiation | doctor PASS under a later `compinit -C` | low | accept | AR-10 | closed |
| T-2-76 | Tampering | plan step rewriting the real rc / `~/.local` | **high** | mitigate | No committed test runs `make install`/`setup.sh`; real shells with `HOME`/`ZDOTDIR` = case home `test_completion_e2e.py:44-69`; `home=`-scoped calls `:140,157,201`; integration sandbox (T-2-79); unit-guard roots `tests/unit/conftest.py:38-50`. Phase-close install sha256 check owed by the orchestrator | closed |
| T-2-77 | Tampering | 02-13 module shells writing real HOME | medium | mitigate | Per-case HOME, XDG, `HISTFILE`, empty `INPUTRC` — `test_scene_fill_tab_e2e.py:40-61` | closed |
| T-2-78 | DoS | NUL in a recipe string | low | mitigate | `scenes/recipe.py:80-88,106,144-153`; one line, exit 1 `launcher.py:521-525`; tests `test_scenes_recipe.py:329-359` | closed |
| T-2-79 | Tampering/Info disclosure | integration cases writing real HOME | medium | mitigate | `tests/integration/conftest.py:26-45`; `test_home_sandbox.py:37-70`; no scoped fixtures in `tests/integration/`; residual AR-07 | closed |
| T-2-88 | DoS/EoP | group/world-writable fpath dir | medium | mitigate | `installer.py:397-398`; test `test_installer_completion.py:114-120` (see U-1) | closed |
| T-2-89 | DoS | permissive `~/.local/share` | low | accept | AR-11 | closed |

*Status: open · closed · open — below high threshold (non-blocking)*
*Severity: critical > high > medium > low — only open threats at or above workflow.security_block_on count toward threats_open*
*Disposition: mitigate (implementation required) · accept (documented risk) · transfer (third-party)*

### Unregistered Flags

None. The only Threat Flag in a SUMMARY, `02-11-SUMMARY.md` "file-access: control sockets in
`mkdtemp` 0700 dirs under `$XDG_RUNTIME_DIR`", maps to T-2-46 (0700 socket dir removed on every
exit path) and T-2-38 (temp-dir fallback). Informational only. `02-09-SUMMARY.md` and
`02-10-SUMMARY.md` have no `## Threat Flags` section. The auditor found no new surface in
either plan outside T-2-33…T-2-42.

Gap-closure plans 02-12…02-15 (audit at `4093b55`): the four SUMMARYs declare no unmapped flags
(02-12 and 02-14 have no `## Threat Flags` section; 02-13 and 02-15 say "none beyond"). The
auditor found three, none covered by a threat ID:

- **U-1 (low, non-blocking): the completion file mode is not hardened.** `write_completion_script` writes `_my-kitty` and `my-kitty-completion.bash` with `write_text`, under the umask (`installer.py:394-396`). An overwrite also keeps the mode an older file already had. T-2-88 clears go-w on the directory only. 02-14's own matrix row C6 shows a 0664 file in a 0755 directory still registers. So on a host without per-user groups and with umask 002, any member of the group can edit shell code that the rc sources at every shell start. Fix: also clear go-w on `path` after the write. Follow-up: `.planning/todos/pending/2026-11-04-phase2-gap-review-followups.md`.
- **U-2 (low, non-blocking): an rc write is truncate-then-write with no backup.** `_write_rc` is a bare `write_bytes` (`path_integration.py:171-172`). An ENOSPC or EIO partway through leaves a truncated `~/.bashrc` or `~/.zshrc`. kitty.conf got restore-on-failure (T-2-48); the rc files did not. This is a pre-existing pattern that 02-14's byte-I/O rewrite carried over. Fix: write to a sibling of the *resolved* path, then `os.replace`, so a dotfiles symlink is kept. Follow-up: `.planning/todos/pending/2026-11-04-phase2-gap-review-followups.md`.
- **U-3 (low, non-blocking): fail-open edges in the unit guard (next to T-2-54).** Follow-up: `.planning/todos/pending/2026-11-04-phase2-gap-review-followups.md`.
  - Events not audited: `os.link`, `os.truncate`, `os.chown`, `os.utime`, `socket.sendto`/`bind`, and `os.chmod(fd)` on an fd opened read-only.
  - `shutil.rmtree`'s `dir_fd` is ignored.
  - `_BUSY` is process-global, so an event on another thread during a check is not inspected.
  - An exception other than IndexError, TypeError or ValueError raised inside `_check` aborts the operation but is not recorded.
  - The roots are computed from `$HOME` at import.
  - The guard is armed only for function-scoped tests, so session or module fixtures and import-time code are not guarded.
  - Most relevant: the live kitty listens on `unix:/tmp/kitty` (`config/kitty/remote-control.conf:22`), and `/tmp` is never a root. So a unit test reaching the live kitty is stopped only at the exec of a footprint `kitten`. A system `kitten` found through the PATH fallback (`scenes/_client.py:57`, `doctor.py:193-200`) would get through.

---

## Accepted Risks Log

| Risk ID | Threat Ref | Rationale | Accepted By | Date |
|---------|------------|-----------|-------------|------|
| AR-01 | T-2-07 | Doctor details name `$HOME` paths and the detected shell. It is a local, single-user diagnostic with no network sink, and neighbouring checks already print the same paths. | Phase 2 plan register (`02-02-PLAN.md` threat_model) | logged 2026-09-24 |
| AR-02 | T-2-10 | uninstall.sh diagnostics name binaries and a `make install` hint. Nothing sensitive; moving them to stderr only makes them visible. | `02-03-PLAN.md` threat_model | logged 2026-09-24 |
| AR-03 | T-2-19 | Measured on kitty 0.49.0: `load_config(accumulate_bad_lines=…)` collects only value-conversion failures, so `include no-such-file.conf` passes the parse check. **Surfaced, not failed**: the diagnosis now reaches `ParseCheckResult.stderr` and doctor's PASS line (`doctor.py:112`). Failing on it changes when `my-kitty install` exits non-zero and needs its own decision (outside D-09). The related gap: the parse check and payload rollback run only when the conf changed (`config_updater.py:396`), so an ordinary reinstall never parse-checks a new payload. **Routed to Phase 5** as a Pending Todo in `.planning/STATE.md` ("[Phase 5 — found by 02-05 …]"). Evidence: `02-05-SUMMARY.md` § "T-2-19". | `02-05-PLAN.md` threat_model; `02-05-SUMMARY.md:399-427`; `STATE.md` Pending Todos | logged 2026-09-24 |
| AR-04 | T-2-20 | The parser's stderr names paths and lines on the user's own machine, shown in a local CLI with no network sink. | `02-05-PLAN.md` threat_model | logged 2026-09-24 |
| AR-05 | T-2-SC | No package was installed in any plan. `argcomplete`, `shlex`, `re`, `tempfile`, `contextlib`, `ast`, `argparse` and the five dev tools are pre-existing or stdlib. `cage` is a pre-existing host binary. | all 15 plan registers; verified by `uv.lock` diff (empty); 02-12…02-15 re-verified by `git diff --stat 8f8f23e 4093b55 -- uv.lock` (empty) | logged 2026-09-24; extended 2026-11-04 |
| AR-06 | T-2-55 | The guard is a tripwire for the test's own process: a child's own effects after exec, C-extension syscalls and `ctypes` are not seen, and no process-level isolation is provided. Named in `tests/unit/conftest.py:20-25`. | `02-12-PLAN.md` threat_model | logged 2026-11-04 |
| AR-07 | T-2-79 | uv, black, pyright and `cage` start outside pytest and may write under the real HOME (prohibition R1.2). | `02-12-PLAN.md` threat_model | logged 2026-11-04 |
| AR-08 | T-2-59 | An untypeable pane-0 `cmd`/`cwd` opens a new tab instead of filling; one stderr line (`launcher.py:222-226,428`); every value still reaches its pane through argv; no shipped example affected. | `02-13-PLAN.md`; D-08 amendment `02-CONTEXT.md:39` | logged 2026-11-04 |
| AR-09 | T-2-65 | A `_*` file planted in `~/.local/share/kitty-setup` needs the same write authority as `~/.zshrc`; the block adds only our directory and a zsh write clears its go-w (T-2-88). | `02-14-PLAN.md` threat_model | logged 2026-11-04 |
| AR-10 | T-2-75 | A later `compinit -C` over a dump without `_my-kitty` drops registration; doctor cannot observe a live shell and its zsh PASS detail names the shape (`doctor.py:299-303`); `README.md:155`; pinned by `test_completion_e2e.py:207-239`. | `02-14-PLAN.md`; `02-CONTEXT.md:28` | logged 2026-11-04 |
| AR-11 | T-2-89 | `~/.local/share` belongs to other tools; a permissive mode makes `compaudit` reject our fpath parent. Disclosed with the fix `chmod go-w ~/.local/share` in `README.md:155`, `02-CONTEXT.md:28`, `02-VALIDATION.md:413`. | `02-14-PLAN.md` threat_model | logged 2026-11-04 |

*Accepted risks do not resurface in future audit runs.*

**Follow-up on AR-03:** the Phase 5 routing exists only as a STATE.md Pending Todo. It is not
yet a criterion in `ROADMAP.md`'s Phase 5 section or a requirement in `REQUIREMENTS.md`. Promote
it when Phase 5 is planned, or the acceptance has no owner.

---

## Advisories (non-blocking; no register threat is open)

These are residual paths or gaps in how a mitigation is enforced, found while verifying the
declared controls. None of them reopens a threat at ASVS L1, and none reaches `block_on: high`.

| ID | Relates to | Observation | Suggested hardening |
|----|------------|-------------|---------------------|
| A-1 | T-2-37 (medium) | **Closed by T-2-66 and T-2-68 (02-15).** Every redirect hop goes through `_HttpsOnlyRedirectHandler.redirect_request` (`installer.py:170-189`); an https→http redirect raises before any plain-http request (`test_installer_download.py:154`, `http_open` never called). `cli_install` catches `ValueError` (`:492-499`, test `:197`). | None. |
| A-2 | T-2-09 (high) | **Closed by T-2-54 (02-12).** The sandbox AST rule is a committed unit test: `tests/unit/test_unit_hermeticity.py:464-497` (`_uninstall_violations`, `test_hermetic_uninstall_sandbox_rule_holds`), rejection controls `:516-521`; `make test` runs it. | None. |
| A-3 | T-2-39 (medium) | **Closed by T-2-69 and T-2-70 (02-15).** B310 is no longer skipped; B604/B607 are fenced per site by `tests/unit/test_bandit_scope.py` (run by `make test`); `urllib.request` is fenced to `installer.py`. Residual: the fence runs only `-t B310,B604,B607`; the canonical `uv run bandit -c pyproject.toml -q -r src` is still no Makefile target, and B404/B603 stay repo-wide skips (ruff S603 stays per file). | Optional: a unit case running the canonical bandit command and asserting exit 0. |
| A-4 | T-2-05 (medium) | **Closed by T-2-64 (02-14).** `doctor.py:281-291` compares raw bytes; a CRLF-only change is FAILed (`test_doctor.py:291`). | None. |
| A-5 | T-2-16 (medium) | The declared threat (a *failed* install) is mitigated. On the unchanged-conf path no parse check runs (`config_updater.py:396`), so the aside is committed (deleted) without the new payload ever being validated. This is AR-03's related gap, routed to Phase 5. The code never deletes the only good payload on any failure path. | Covered by the AR-03 follow-up. |
| A-6 | docs | `02-03-PLAN.md`'s register has the T-2-09 and T-2-10 rows fused onto one line (`…single-key read. \|\| T-2-10 …`), so T-2-10 does not render as its own row. The content is intact. | Split the row. |
| A-7 | T-2-51, T-2-54, T-2-58, T-2-62 | The conf-codec AST gate, the rc-I/O AST gate, the launcher payload AST gate (VALIDATION 02-04-T1) and the guard's negative control are plan/VALIDATION gates, not committed tests. The code satisfies each at `4093b55`. | Port them into `tests/unit/` as A-2 was. |

---

## Security Audit Trail

| Audit Date | Threats Total | Closed | Open | Run By |
|------------|---------------|--------|------|--------|
| 2026-09-24 | 48 (43 mitigate, 5 accept, 0 transfer) | 48 | 0 (0 blocking, 0 non-blocking) | gsd-security-auditor (Claude), read-only at `d4a3a8c` |
| 2026-11-04 | 82 (73 mitigate, 9 accept, 0 transfer) | 82 | 0 (0 blocking, 0 non-blocking) | gsd-security-auditor (Claude), read-only at 4093b55 |

Commands run, all read-only, from the primary checkout (no kitty window, no `kitten @`, no
`KITTI_INTEGRATION=1`, nothing written outside this file):

- `rg`/`sed` over the eleven `<threat_model>` blocks and `02-VALIDATION.md` rows 153-184 → 47 numbered IDs + `T-2-SC`, no orphan IDs.
- `env -u KITTI_INTEGRATION uv run pytest -q -p no:cacheprovider tests/unit/{test_scenes_launcher,test_installer_download,test_installer_completion,test_installer_uninstall,test_config_updater,test_scenes_colors,test_scenes_background,test_scenes_accent,test_path_integration,test_doctor,test_tools_uninstall_sh,test_makefile_targets,test_cli,test_pruner,test_harness_teardown,test_integration_env_hygiene,test_kitty_session_env,test_kitty_session_socket,test_integration_runner}.py` → **369 passed in 5.28s**; `pgrep -xc kitty`/`cage` before and after → 0/0.
- The T-2-09 AST gate, copied verbatim from `02-VALIDATION.md` row 02-03-T1 → `runs 1 env_reads 0`, exit 0.
- `shlex.quote(` anywhere in `src/` → 0 (`shlex` only in the `launcher.py:52` docstring); `_download_installer` order → scheme `If` `:194` before `build_opener` `:200` before `mkstemp` `:201` before `opener.open` `:205`; `assert` → 0.
- `uv run bandit -c pyproject.toml -q -r src` → exit 0; `uv run ruff check src` → "All checks passed!"; `rg '# noqa|# nosec|# type: ignore' src/` → none.
- Prohibition guards: `close-os-window` absent from `src/`; `rgba`/`hsl` absent from `colors.py`; no `"/tmp` literal in `src/`; `TARGET_DIR_REL|env_path|send_key|_find_tab_with_window` absent from `src/ tests/ tools/`.
- `rg -c '^### Phase [0-9]+(\.[0-9]+)?:' .planning/ROADMAP.md` → 11.
- `git diff 5452f54 HEAD -- uv.lock` → empty; the `pyproject.toml` diff touches only `[tool.*]` sections.
- The Python 3.12.12 source of `HTTPRedirectHandler.http_error_302` (via `inspect`), for advisory A-1.

`make doctor` and `make test` were not run as part of this audit. They are the phase gate's
evidence, not the auditor's. Per `02-10-SUMMARY.md`, the phase's own record says both are green.

---

## Sign-Off

- [x] All threats have a disposition (mitigate / accept / transfer)
- [x] Accepted risks documented in Accepted Risks Log
- [x] `threats_open: 0` confirmed
- [x] `status: verified` set in frontmatter

**Approval:** verified 2026-09-24 (plans 02-01…02-11) and re-verified 2026-11-04 at `4093b55` (gap plans 02-12…02-15); auditor verdict SECURED both times. A-1…A-4 closed; A-5…A-7 and U-1…U-3 are non-blocking follow-ups (`.planning/todos/pending/2026-11-04-phase2-gap-review-followups.md`).

---
phase: "02"
slug: "defect-remediation"
status: verified
# threats_open = count of OPEN threats at or above workflow.security_block_on severity (the blocking gate)
threats_open: 0
asvs_level: 1
block_on: high
audited_commit: "d4a3a8c"
created: "2026-09-24"
---

# Phase 02 — Security

> Per-phase security contract: threat register, accepted risks, and audit trail.
> Audited read-only at `d4a3a8c` (branch `gsd/phase-02-defect-remediation`), ASVS level 1,
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

Sources: `<threat_model>` blocks in `02-01`…`02-11-PLAN.md` and the Threat Ref column of
`02-VALIDATION.md` (every ID there also appears in a plan register; no orphan IDs). 47 numbered
threats plus `T-2-SC`, which is declared the same way in all 11 plans and is counted once, for
48 entries.

| Threat ID | Category | Component | Severity | Disposition | Mitigation — evidence (file:line) | Status |
|-----------|----------|-----------|----------|-------------|-----------------------------------|--------|
| T-2-01 | Tampering | completion generator | medium | mitigate | In-process `argcomplete.shellcode` via `_ARGCOMPLETE_SHELLCODE` — `src/kitty_setup/installer.py:41,332-341`; no `shutil.which`/`register-python-argcomplete` call (the one match is the `:335` docstring) | closed |
| T-2-02 | Tampering | `remove_completion_script` | medium | mitigate | Only the named basenames are unlinked (`missing_ok=True`), and the directory is removed with `rmdir` only when it is empty — `installer.py:358-373`; no `rmtree` in it; tests `test_installer_completion.py:264,274,279` | closed |
| T-2-03 | DoS | `make clean` vs completion | low | mitigate | Removal guarded by `do_kitty` — `installer.py:497,542-544`; tests `test_installer_completion.py:340,351,363` | closed |
| T-2-04 | Tampering | rc-file editing | medium | mitigate | The sentinel `find_block`/`_splice_lines` mechanism is kept — `path_integration.py:166-191`; `compinit -i` — `:56`; the zsh block is moved to the end — `:146-155`; outside-marker exact-equality tests `test_path_integration.py:72,346,367` | closed |
| T-2-05 | Tampering | completion file bytes | medium | mitigate | Doctor compares the file with freshly generated shellcode — `doctor.py:278-288`; test `test_doctor.py:201` (see advisory A-4) | closed |
| T-2-06 | Spoofing | unexpected `$SHELL` | low | mitigate | Unsupported shell skips — `path_integration.py:208-224`, `doctor.py:239-248` (no silent `.zshrc` default); tests `test_path_integration.py:151`, `test_doctor.py:231` | closed |
| T-2-07 | Info disclosure | doctor detail strings | low | accept | Accepted Risks Log AR-01 | closed |
| T-2-08 | DoS | `make clean` destructiveness | **high** | mitigate | `Makefile:30` `my-kitty uninstall --keep-kitty --keep-backups`; help `Makefile:12` and `README.md:46` say "(keeps kitty + backups)"; tests `test_makefile_targets.py:49,59`, `test_installer_uninstall.py:141` | closed |
| T-2-09 | Tampering | uninstall test sandbox | **high** | mitigate | `tests/unit/test_tools_uninstall_sh.py:59-77`: replacement `env=` with a fake `HOME`/`PATH`, plus `timeout=` and `cwd=`; `KITTI_FORCE=1` by default; AST gate re-run → `runs 1 env_reads 0`, exit 0 (see advisory A-2) | closed |
| T-2-10 | Info disclosure | uninstall.sh diagnostics on stderr | low | accept | Accepted Risks Log AR-02 | closed |
| T-2-11 | EoP | captured log line executed as a command | medium | mitigate | `tools/uninstall.sh:17` `log()` writes to `>&2`; `resolve_binary` puts only the binary name on stdout — `:19-41`; test `test_tools_uninstall_sh.py:108` | closed |
| T-2-12 | Tampering/EoP | pane-0 `cwd` in `send-text` | **high** | mitigate | `src/kitty_setup/scenes/launcher.py:269` `f"cd {shlex.quote(p0.cwd)}\n"`; the only `send-text` sites in `src/` are `:266,:277`; tests `test_scenes_launcher.py:573-601` (`/tmp/my dir; touch /tmp/PWNED`), real-kitty sentinel `tests/integration/test_scene_fill_tab_e2e.py:120` | closed |
| T-2-13 | Tampering | pane-0 `cmd` in `send-text` | **high** | mitigate | `launcher.py:280` `f"bash -lc {shlex.quote(p0.cmd)}\n"`; tests `test_scenes_launcher.py:605-613` (`shlex.split` round-trip) | closed |
| T-2-14 | DoS | unguarded `int(stdout)` | low | mitigate | `_window_id_from` raises `SceneClientError` — `launcher.py:169-182`, used at `:296,:411,:434`; CLI catches at `:504,:536`; test `test_scenes_launcher.py:679` | closed |
| T-2-15 | Tampering | quoting spreading to the argv path | medium | mitigate | `_launch_argv` (`launcher.py:117-140`) has no `shlex` (AST region check → `False`); test `test_scenes_launcher.py:621` | closed |
| T-2-16 | Tampering | payload dir across a failed install | medium | mitigate | Rename-aside before the copy, and the aside is deleted only after success — `config_updater.py:339-355`; the handler catches `BaseException` — `:348`; a failed restore keeps the aside and names it — `:285-307`; a stale aside is kept under a dated name and never deleted — `:249-282`; tests `test_config_updater.py:542-702` (includes `ctrl_c`) (see advisory A-5) | closed |
| T-2-17 | Repudiation | discarded parser stderr | medium | mitigate | `ParseCheckResult.stderr` — `config_updater.py:114-125,235-237`; in the error — `:240-246`; in doctor — `doctor.py:110-116` | closed |
| T-2-18 | Spoofing | wrong command name in error text | low | mitigate | `command=shlex.join(argv)` built from the argv actually executed — `config_updater.py:224,236`; used in `doctor.py:113,115`; no `--debug-config` literal remains | closed |
| T-2-19 | Tampering | parse check blind to a missing `include` | medium | accept | Accepted Risks Log AR-03 (routed to Phase 5) | closed |
| T-2-20 | Info disclosure | parser stderr in user-facing message | low | accept | Accepted Risks Log AR-04 | closed |
| T-2-21 | Tampering | unvalidated colour to kitty | medium | mitigate | Allow-list: `#hex`, names, anchored `rgb:`, `NONE` — `scenes/colors.py:50,55,75-99`; `rgba`/`hsl` absent from the source; tests `test_scenes_colors.py:122-189` | closed |
| T-2-22 | Tampering | truthiness fallback | medium | mitigate | Explicit `is None` — `scenes/background.py:32-34`, `scenes/accent.py:36-49`; no `normalize_color(...) or` anywhere in `src/` | closed |
| T-2-23 | DoS | half-built scene | low | mitigate | All colours normalised before the first kitten call — `launcher.py:372-375`; test `test_scenes_colors.py:264` | closed |
| T-2-24 | Tampering | prefix-matched `rgb:` | low | mitigate | `_RGB_COLON_RE.fullmatch` — `colors.py:90`; tests `test_scenes_colors.py:177-189` (`rgb:xyz/00/00`, `rgb:0/0/0/0`) | closed |
| T-2-25 | Repudiation | PATH report / rc `OSError` | medium | mitigate | `result.reason` printed — `installer.py:412-416`; `OSError` → one stderr line, exit 1 — `installer.py:447-454`; tests `test_path_integration.py:454,464`, `test_installer_completion.py:228` | closed |
| T-2-26 | Repudiation | single-line manual hint | low | mitigate | One `manual_lines` entry per line — `installer.py:408-409`; test `test_path_integration.py:479` | closed |
| T-2-27 | Tampering | install log written into the repo | low | mitigate | `_record_install_log` and `install.log` absent from `src/`; tombstone tests `test_installer_uninstall.py:259,307` | closed |
| T-2-28 | DoS | deleting `_repo_root` | medium | mitigate | `_repo_root` survives — `installer.py:81`, callers `:101,:115` | closed |
| T-2-29 | Tampering | ambient `KITTY_WINDOW_ID` | low | mitigate | Pops in `tests/integration/test_scene_recipe_e2e.py:80,125`, `test_color_normalization_e2e.py:33`, `test_h25_scene_launcher.py:393`; AST rule in the unit tree `tests/unit/test_integration_env_hygiene.py:225` | closed |
| T-2-30 | DoS | `prune --keep -1` | low | mitigate | `_non_negative_int` → `ArgumentTypeError` — `cli.py:36-49,127,135`; library guards kept — `pruner.py:29,38`; test `test_cli.py:133` | closed |
| T-2-31 | Repudiation | non-existent teardown verb suppressed | medium | mitigate | Verb stays `close-window` — `harness/kitty_session.py:323-324`; `close-os-window` absent from `src/`; pin `tests/unit/test_harness_teardown.py` | closed |
| T-2-32 | DoS | later refactor of the teardown | low | mitigate | The pin above existed before 02-09 and passes after it | closed |
| T-2-33 | DoS | `contextlib.suppress` rewrite | medium | mitigate | `kitty_session.py:323` `contextlib.suppress(HarnessCommandError)` keeps the verb; the pin passes | closed |
| T-2-34 | DoS | deleting vulture-flagged symbols | medium | mitigate | Only the four named symbols are gone (`rg` over `src/ tests/ tools/` → none); survivors `session_dir` `kitty_session.py:148`, `_make_socket_dir` `:95`, `_remove_socket_dir` `:338`, `_find_window_by_id` `tests/integration/test_h25_scene_launcher.py:43` | closed |
| T-2-35 | DoS | partial signature update | low | mitigate | `env_path` removed in one commit `35f9cc7`; no reference left; 369 targeted unit tests pass | closed |
| T-2-36 | Repudiation | partial gate recorded as pass | medium | mitigate | `02-09-SUMMARY.md:134-139,234-250` records the three gates as **red until 02-10** | closed |
| T-2-37 | Tampering | `urlopen` of the installer script | medium | mitigate | `installer.py:162-167` raises `ValueError` for a non-`https` scheme before `mkstemp` (`:168`) and `urlopen` (`:169`); no `assert` in the function (AST); tests `test_installer_download.py:43-65` (http/file/ftp) (see advisory A-1) | closed |
| T-2-38 | Tampering | hardcoded temp path | low | mitigate | `tempfile.gettempdir()` — `kitty_session.py:103,261`; no `"/tmp` literal in `src/`; test `test_kitty_session_env.py:61` | closed |
| T-2-39 | Repudiation | over-broad tool suppression | medium | mitigate | Rationale per ID for bandit — `pyproject.toml:141-158`; ruff `src/` entries are per-file with reasons — `:106-133`; zero `# noqa`/`# nosec`/`# type: ignore` in `src/` (see advisory A-3) | closed |
| T-2-40 | Repudiation | vulture scope hiding findings | medium | mitigate | `[tool.vulture]` holds only `ignore_decorators` — `pyproject.toml:160-165`; `vulture_allowlist.py` has 5 names in 7 code lines | closed |
| T-2-41 | Repudiation | wrong recorded baseline | medium | mitigate | pyright `src/` = **15** — `ROADMAP.md:35-36`, `REQUIREMENTS.md:88`; vulture scope named; no `999` placeholder remains | closed |
| T-2-42 | DoS | whole-file ROADMAP write | **high** | mitigate | `rg -c '^### Phase [0-9]+(\.[0-9]+)?:' .planning/ROADMAP.md` → **11**, including `Phase 8.5` (`:226`) | closed |
| T-2-43 | Repudiation | wrapper status replacing pytest's | **high** | mitigate | Verdict comes from the child's status file — `harness/integration_runner.py:225,260,283-287,290-300`; the compositor's status is only logged; test `test_integration_runner.py:341` | closed |
| T-2-44 | Repudiation | a run that didn't happen reported green | **high** | mitigate | No compositor → 69 `:316-322`; bad `XDG_RUNTIME_DIR` → 69 `:324-331`; missing status → 70 `:270-276`; timeout → 70 `:249-256`; tests `test_integration_runner.py:285,317,353,439` | closed |
| T-2-45 | Info disclosure/Tampering | integration test reaching the live kitty | medium | mitigate | `SCRUBBED_VARIABLES` `:51-59` applied by `headless_env` `:202-206`; `stdin=DEVNULL`, `start_new_session=True` `:241-243`; test `test_integration_runner.py:207` | closed |
| T-2-46 | DoS | orphaned cage/kitty | medium | mitigate | Process group killed in `finally` — `:246-259`, `_CompositorGroup.terminate` `:127-139`; leftover → 70 `:262-269`; SIGTERM/SIGHUP handlers `:333-345`; socket dir 0700 removed on every exit path — `kitty_session.py:95-104,169-172,185-186,338-343`; tests `test_integration_runner.py:370,388,409`, `test_kitty_session_socket.py:63,77,91` | closed |
| T-2-47 | Tampering | log text confusing the summary parser | low | mitigate | Compositor stderr goes to `tmp/test-integration/compositor.log` (`:70,242`); test `test_integration_runner.py:455` | closed |
| T-2-SC | Tampering | dependency installs (all 11 plans) | low | accept | Accepted Risks Log AR-05; verified: `git diff 5452f54 HEAD -- uv.lock` is empty, and the `pyproject.toml` diff touches only `[tool.*]` sections | closed |

*Status: open · closed · open — below high threshold (non-blocking)*
*Severity: critical > high > medium > low — only open threats at or above workflow.security_block_on count toward threats_open*
*Disposition: mitigate (implementation required) · accept (documented risk) · transfer (third-party)*

### Unregistered Flags

None. The only Threat Flag in a SUMMARY, `02-11-SUMMARY.md` "file-access: control sockets in
`mkdtemp` 0700 dirs under `$XDG_RUNTIME_DIR`", maps to T-2-46 (0700 socket dir removed on every
exit path) and T-2-38 (temp-dir fallback). Informational only. `02-09-SUMMARY.md` and
`02-10-SUMMARY.md` have no `## Threat Flags` section. The auditor found no new surface in
either plan outside T-2-33…T-2-42.

---

## Accepted Risks Log

| Risk ID | Threat Ref | Rationale | Accepted By | Date |
|---------|------------|-----------|-------------|------|
| AR-01 | T-2-07 | Doctor details name `$HOME` paths and the detected shell. It is a local, single-user diagnostic with no network sink, and neighbouring checks already print the same paths. | Phase 2 plan register (`02-02-PLAN.md` threat_model) | logged 2026-09-24 |
| AR-02 | T-2-10 | uninstall.sh diagnostics name binaries and a `make install` hint. Nothing sensitive; moving them to stderr only makes them visible. | `02-03-PLAN.md` threat_model | logged 2026-09-24 |
| AR-03 | T-2-19 | Measured on kitty 0.49.0: `load_config(accumulate_bad_lines=…)` collects only value-conversion failures, so `include no-such-file.conf` passes the parse check. **Surfaced, not failed**: the diagnosis now reaches `ParseCheckResult.stderr` and doctor's PASS line (`doctor.py:112`). Failing on it changes when `my-kitty install` exits non-zero and needs its own decision (outside D-09). The related gap: the parse check and payload rollback run only when the conf changed (`config_updater.py:396`), so an ordinary reinstall never parse-checks a new payload. **Routed to Phase 5** as a Pending Todo in `.planning/STATE.md` ("[Phase 5 — found by 02-05 …]"). Evidence: `02-05-SUMMARY.md` § "T-2-19". | `02-05-PLAN.md` threat_model; `02-05-SUMMARY.md:399-427`; `STATE.md` Pending Todos | logged 2026-09-24 |
| AR-04 | T-2-20 | The parser's stderr names paths and lines on the user's own machine, shown in a local CLI with no network sink. | `02-05-PLAN.md` threat_model | logged 2026-09-24 |
| AR-05 | T-2-SC | No package was installed in any plan. `argcomplete`, `shlex`, `re`, `tempfile`, `contextlib`, `ast`, `argparse` and the five dev tools are pre-existing or stdlib. `cage` is a pre-existing host binary. | all 11 plan registers; verified by `uv.lock` diff (empty) | logged 2026-09-24 |

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
| A-1 | T-2-37 (medium) | The scheme check covers the **initial** URL only. On Python 3.12.12, `urllib.request.HTTPRedirectHandler.http_error_302` follows redirects to `http`, `https` and `ftp`, so an upstream `https`→`http` redirect would be followed, and `installer.py` does no post-redirect check (`rg 'geturl\|redirect' installer.py` → none). Separately, `cli_install` (`installer.py:444`) does not catch `ValueError`, so a rejected URL fails closed but prints a traceback. | Before `tmp.write_bytes`, check that `urlparse(response.geturl()).scheme == "https"`, or install an opener whose redirect handler refuses non-https. Add `ValueError` to the `cli_install` except-tuple. |
| A-2 | T-2-09 (high) | The AST sandbox gate lives only in the plan's `<verify>` and in `02-VALIDATION.md`. It is not a committed unit test, so `make test` would not catch a regression such as a future `os.environ` merge. T-2-29's equivalent rule does live in the unit tree. | Move the gate into `tests/unit/` next to `test_integration_env_hygiene.py`. |
| A-3 | T-2-39 (medium) | bandit `skips` (`pyproject.toml:158`) are repo-wide per ID, because bandit's pyproject config cannot scope them per file. The B310 skip therefore blinds bandit to any future `urlopen` elsewhere in `src/`. ruff's `S310` entry is per-file (`installer.py` only) and still flags other files. No Makefile target runs bandit. | Keep ruff `S310` per-file, as now. Consider a gate asserting `urlopen` appears only in `installer.py`. |
| A-4 | T-2-05 (medium) | The staleness check compares **decoded text** from `read_text` (universal newlines), not raw bytes, so a change to line endings only (`\n`→`\r\n`) is not detected. Added or changed commands still differ, so this cannot hide injected code. | Compare `script.read_bytes()` with `generate_completion_script(...).encode()` to make it a true byte comparison. |
| A-5 | T-2-16 (medium) | The declared threat (a *failed* install) is mitigated. On the unchanged-conf path no parse check runs (`config_updater.py:396`), so the aside is committed (deleted) without the new payload ever being validated. This is AR-03's related gap, routed to Phase 5. The code never deletes the only good payload on any failure path. | Covered by the AR-03 follow-up. |
| A-6 | docs | `02-03-PLAN.md`'s register has the T-2-09 and T-2-10 rows fused onto one line (`…single-key read. \|\| T-2-10 …`), so T-2-10 does not render as its own row. The content is intact. | Split the row. |

---

## Security Audit Trail

| Audit Date | Threats Total | Closed | Open | Run By |
|------------|---------------|--------|------|--------|
| 2026-09-24 | 48 (43 mitigate, 5 accept, 0 transfer) | 48 | 0 (0 blocking, 0 non-blocking) | gsd-security-auditor (Claude), read-only at `d4a3a8c` |

Commands run, all read-only, from the primary checkout (no kitty window, no `kitten @`, no
`KITTI_INTEGRATION=1`, nothing written outside this file):

- `rg`/`sed` over the eleven `<threat_model>` blocks and `02-VALIDATION.md` rows 153-184 → 47 numbered IDs + `T-2-SC`, no orphan IDs.
- `env -u KITTI_INTEGRATION uv run pytest -q -p no:cacheprovider tests/unit/{test_scenes_launcher,test_installer_download,test_installer_completion,test_installer_uninstall,test_config_updater,test_scenes_colors,test_scenes_background,test_scenes_accent,test_path_integration,test_doctor,test_tools_uninstall_sh,test_makefile_targets,test_cli,test_pruner,test_harness_teardown,test_integration_env_hygiene,test_kitty_session_env,test_kitty_session_socket,test_integration_runner}.py` → **369 passed in 5.28s**; `pgrep -xc kitty`/`cage` before and after → 0/0.
- The T-2-09 AST gate, copied verbatim from `02-VALIDATION.md` row 02-03-T1 → `runs 1 env_reads 0`, exit 0.
- AST region checks: `shlex` in `_launch_argv` → `False`; `shlex.quote(` in `_fill_current_tab` → 2; `_download_installer` statement order → scheme `If` before `mkstemp` before `urlopen`; `assert` count → 0.
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

**Approval:** verified 2026-09-24 (auditor verdict SECURED; advisories A-1…A-6 are non-blocking follow-ups)

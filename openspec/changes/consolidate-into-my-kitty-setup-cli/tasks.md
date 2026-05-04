## 1. Probes (already done — see tmp/probes/consolidate-into-my-kitty-setup-cli/)

- [x] 1.1 Probe 01 — `uv tool install .` (non-editable) lands real entries at `~/.local/bin/<entry>` in 177 ms. Verdict: holds. → enables D1.
- [x] 1.2 Probe 02 — source code is COPIED into the tool venv at `~/.local/share/uv/tools/<pkg>/lib/python*/site-packages/`. Verdict: holds. → enables D1 binary independence.
- [x] 1.3 Probe 03 — installed binary continues working after the source repo is moved/deleted. Verdict: holds. → satisfies "delete the repo after install" requirement.
- [x] 1.4 Probe 04 — `uv tool uninstall <pkg>` removes entries + tool venv cleanly. Verdict: holds. → enables D2 `--self` print-the-command flow.

## 2. CLI dispatcher

- [ ] 2.1 Create `src/kitty_setup/cli.py` with `main(argv: list[str] | None = None) -> int`. Argparse-based subparser dispatch. Subparsers: `install`, `uninstall`, `doctor`, `help`. Each subparser delegates to existing module-level `main()` (or a renamed `run()`) inside `installer.py`, `doctor.py`. `help` prints the top-level help and exits 0. Unknown subcommand prints an error + help and exits non-zero.
- [ ] 2.2 Update `src/kitty_setup/installer.py`: split current `main()` into `cli_install(args) -> int` (the install subcommand) and `cli_uninstall(args) -> int` (the uninstall subcommand owning the new `--kitty` and `--self` flags). The legacy `--uninstall-config` is removed (it now lives behind `cli_uninstall` default scope).
- [ ] 2.3 Update `src/kitty_setup/doctor.py`: rename `main()` to `cli_doctor(args) -> int`. Keep the `argv` shape compatible with cli.py's dispatch.
- [ ] 2.4 Author `tests/unit/test_cli.py` with cases: top-level help renders all 4 subcommands; unknown subcommand exits non-zero; each subcommand routes to the expected handler (mocks `cli_install` / `cli_uninstall` / `cli_doctor` and asserts the right one is called with the parsed args).

## 3. PATH integration

- [ ] 3.1 Create `src/kitty_setup/path_integration.py` with `ensure_local_bin_in_path(home: Path | None = None, shell: str | None = None) -> PathEditResult`. Detect target rc via `$SHELL` (zsh → `~/.zshrc`, bash → `~/.bashrc`, anything else → emit a `PathEditResult` with `skipped=True` and the manual line to print). Detect existing PATH entries by scanning current `os.environ["PATH"]` AND parsing the rc file's existing `export PATH=...` lines. If `~/.local/bin` already on PATH (either source), return `PathEditResult(changed=False, reason="already on PATH")`. Otherwise append the sentinel-bracketed block to the rc file. Idempotent re-runs detect the block and skip.
- [ ] 3.2 Author `tests/unit/test_path_integration.py` covering: rc missing → block written; rc has unrelated content → block appended; rc already has our block → no-op; rc has user's own `export PATH=...:$HOME/.local/bin:` → no-op (detected via parse); current process env already has it → no-op; unsupported shell → returns `skipped=True` with the manual line. Use pytest tmp_path; no real shell invocation needed.
- [ ] 3.3 Wire `cli_install` to call `path_integration.ensure_local_bin_in_path()` after the kitty install + config inject succeed. Print the result line: "PATH: already configured" / "PATH: appended block to ~/.zshrc, run `source ~/.zshrc` or restart shell" / "PATH: shell <name> not auto-handled, add `export PATH=...` to your config".

## 4. Pyproject + tools/ rewiring

- [ ] 4.1 Update `pyproject.toml`: replace the three `[project.scripts]` entries with a single `my-kitty-setup = "kitty_setup.cli:main"`. Run `uv sync` (the local `.venv` reflects the change so dev tests run against the new entry).
- [ ] 4.2 Update `tools/setup.sh`: after `uv sync`, run `uv tool install --force .` to provision the deployable. Then `my-kitty-setup install` (NOT the old `uv run kitty-setup-install`).
- [ ] 4.3 Update `tools/uninstall.sh`: drop the kitty-removal logic and the `uv run kitty-setup-install --uninstall-config` call. New shape: `my-kitty-setup uninstall ${UNINSTALL_FLAGS:-}`. The Makefile passes the appropriate flags.
- [ ] 4.4 Update `Makefile`: `install` calls `tools/setup.sh`; `uninstall` calls `my-kitty-setup uninstall` (or `tools/uninstall.sh` which then calls it); `uninstall ALL=1` passes `--kitty --self`. Each target ≤ 5 lines per R3.

## 5. Documentation

- [ ] 5.1 Update `docs/agent-iteration.md`: change every reference to `tmp/probes/<NN>-<slug>.md` to `tmp/probes/<change-id>/<NN>-<slug>.md` and explicitly note the per-change subdirectory rule. Add a one-line note in "The loop" step 3 stating that the probe pass writes into `tmp/probes/<active-change>/`.
- [ ] 5.2 Update `docs/probe-template.md`: update the path examples to use the per-change subdirectory.
- [ ] 5.3 Update `README.md`: replace `make setup` references with `make install` (the alias still resolves), update the quickstart command list to show `my-kitty-setup install`, `my-kitty-setup doctor`, `my-kitty-setup uninstall`, `my-kitty-setup uninstall --kitty`, `my-kitty-setup uninstall --self`. Add a note that the binary survives repo deletion. Add a one-paragraph "Updates" section ("`git pull && make install`").
- [ ] 5.4 Update `CLAUDE.md`: clarify the bash boundary now also covers `tools/uninstall.sh`'s tiny dispatch logic. The "Stack" paragraph stays accurate; touch up wording if needed.

## 6. Verify

- [ ] 6.1 Run `make uninstall ALL=1` to fully reset the local box (config gone, kitty gone, prints the manual self-removal command). Run the printed `uv tool uninstall my-kitty-setup` to confirm the `--self` story.
- [ ] 6.2 Run `make install` end-to-end on the now-clean box. Capture the output (uv sync, uv tool install timings, kitty download, config inject, PATH check). Expect <30 s total wall time on cached uv/python downloads.
- [ ] 6.3 Run `my-kitty-setup doctor`. Expect 6/6 PASS, exit 0.
- [ ] 6.4 Run `KITTI_INTEGRATION=1 make test`. Expect 35/35 (the existing 4 integration + 31 unit) plus the new tests for cli + path_integration. Aim ~45 total.
- [ ] 6.5 Source-deletion check: `mv kitty-setup /tmp/x; cd /tmp; my-kitty-setup doctor; mv /tmp/x kitty-setup`. Doctor must exit 0 with the source repo not at its original path.
- [ ] 6.6 Run `openspec validate consolidate-into-my-kitty-setup-cli --strict`. Expect "Change is valid".

## 7. Probe-finding durability check (R6)

- [ ] 7.1 For each of probes 01–04, encode the finding into a durable location:
  - 01 finding → inline comment in `tools/setup.sh` at the `uv tool install --force .` line referencing `probe-consolidate-into-my-kitty-setup-cli-01`.
  - 02 finding → `Why:` line on D1 in design.md (already in place via "the source is COPIED").
  - 03 finding → `Why:` line on D1 (already in place via probe ref) AND a one-line note in README.md's "Updates" section.
  - 04 finding → inline comment in `cli.py`'s uninstall handler near the `--self` print path referencing `probe-consolidate-into-my-kitty-setup-cli-04`.
- [ ] 7.2 Confirm `tmp/probes/consolidate-into-my-kitty-setup-cli/` will disappear cleanly when this change archives (gitignored; no special action needed).

## 8. Commit + archive

- [ ] 8.1 Two or three commits: `chore(cli): consolidate three entry points into my-kitty-setup with subcommands` (cli + pyproject + installer/doctor refactor), `chore(install): make install uses uv tool install + ensures local bin on PATH` (Makefile + tools/setup.sh + tools/uninstall.sh + path_integration), and `docs: update probe convention + quickstart` (docs).
- [ ] 8.2 `openspec archive consolidate-into-my-kitty-setup-cli -y` syncs the new `my-kitty-setup-cli` capability + the `agent-iteration-discipline` MODIFIED requirements into `openspec/specs/`.
- [ ] 8.3 Confirm `openspec list` reports zero active changes (the parked `phase1-binding-introspection` was committed and then its directory will need recreating — see 8.4).
- [ ] 8.4 Re-create the parked `phase1-binding-introspection` change directory from commit `ad6dd2d` if openspec state requires it (the openspec CLI may have removed it during this change's apply phase if both were active simultaneously; verify and restore).

## 9. Hand-off back to phase1-binding-introspection

- [ ] 9.1 Re-target the parked change: rename `kitty-setup-bindings` → `my-kitty-setup keys` (a new subcommand) throughout proposal/design/spec/tasks. Drop the `[project.scripts]` add (the entry point already exists; this is just a new subparser). Update the doctor 7th check to invoke the introspection module via the same in-process call (not as an entry point invocation).
- [ ] 9.2 Resume the apply phase of `phase1-binding-introspection` per its retargeted tasks.md.

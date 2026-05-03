## 1. Repo hygiene and stack declaration

- [ ] 1.1 Update `.gitignore` to add `tmp/`, `*.bak.*`, and `.kitty-setup-test/`.
- [ ] 1.2 Replace `.claude/workflow.md` reference in `CLAUDE.md` with one pointing at the OpenSpec workflow (or remove the link if no replacement file is added in this change). Note that prior `.claude/conventions.md` and the missing `workflow.md` came from another framework and are advisory at most.
- [ ] 1.3 Add the bash → python boundary statement to `README.md` and `CLAUDE.md`: "Python is the stack. Bash exists only inside `tools/setup.sh` for prerequisite bootstrap. No new shell scripts."
- [ ] 1.4 Expand `README.md` with: prerequisites (Pop!_OS 24.04, curl, bash), quickstart (`make setup`, `make doctor`, `make test`, `make uninstall`), the `tmp/` vs `src/` vs `tools/` vs `config/` layout, pointers to `docs/requirements.md` and `docs/propossal_roadmap.md`.
- [ ] 1.5 Author `docs/agent-iteration.md` codifying the hypothesis workflow: pick the next item from `docs/requirements.md`, drop scratch into `tmp/h<NN>-<slug>/`, write `repro.md` + `run.py` + `expected.json`, run autonomously, promote on green to `src/` + `config/` + `docs/repro/` + `tests/integration/`. State the rule that the agent that writes a hypothesis is not the agent that promotes it.

## 2. Python project skeleton

- [ ] 2.1 Create `pyproject.toml` declaring Python 3.12+, the `kitty-setup` project, and dev dependencies for black, ruff, pyright, bandit, vulture, pytest. Configure black at 100 cols and pyright in strict mode per `.claude/conventions.md`.
- [ ] 2.2 Declare `[project.scripts]` entry points: `kitty-setup-install = "kitty_setup.installer:main"`, `kitty-setup-doctor = "kitty_setup.doctor:main"`, `kitty-setup-harness = "kitty_setup.harness.cli:main"`.
- [ ] 2.3 Create `src/kitty_setup/__init__.py` (empty) and `src/kitty_setup/harness/__init__.py` (empty) so the package is importable.
- [ ] 2.4 Run `uv sync` and confirm a `.venv/` is created and `uv run python -c "import kitty_setup"` exits 0.

## 3. Makefile and tools/ scaffolding

- [ ] 3.1 Author the `Makefile` with `.PHONY` targets `help` (default), `setup`, `clean`, `doctor`, `test`, `uninstall`. Each target is at most five lines including its banner. Anything longer dispatches into `tools/` or a `[project.scripts]` entry point.
- [ ] 3.2 Author `tools/setup.sh`: detect `uv` via `command -v uv`; if missing, install via `curl -LsSf https://astral.sh/uv/install.sh | sh`; then `uv sync`; then `uv run kitty-setup-install`. The script MUST exit non-zero on any step failure. No other tasks live in this script.
- [ ] 3.3 Author `tools/uninstall.sh`: confirm with the caller (skippable via `KITTI_FORCE=1`), then call `uv run kitty-setup-install --uninstall-config` and remove `~/.local/kitty.app`, `~/.local/bin/kitty`, and the `.desktop` entry.
- [ ] 3.4 Run `make help` and confirm it lists every target on its own line.

## 4. Hypothesis H00 — bootstrap dogfood

- [ ] 4.1 Create `tmp/h00-bootstrap/repro.md` documenting the manual repro (clean shell, run `make setup`, expected exit code, expected paths created).
- [ ] 4.2 Create `tmp/h00-bootstrap/run.sh` that runs `make help`, `make doctor` (allowed to fail, install not done yet), then asserts `tools/setup.sh` and `Makefile` are present and parsable (`bash -n tools/setup.sh`, `make -n setup`).
- [ ] 4.3 Run `tmp/h00-bootstrap/run.sh` and capture output. On green, record the resolved Make + uv versions to `tmp/h00-bootstrap/actual.json`.

## 5. Implement and prove `kitty-config-management`

- [ ] 5.1 Implement `src/kitty_setup/config_updater.py` covering: sentinel-bracketed include injection, idempotent re-runs, timestamped backup before mutation, parse-check via `kitty --debug-config`, and uninstall path that strips between markers and restores backup when the file would otherwise be content-empty.
- [ ] 5.2 Author `tests/unit/test_config_updater.py` with cases for: missing source file, empty source file, source with prior user content, source with our block already present, parse-check failure triggers rollback, uninstall preserves backups. Use pytest `tmp_path`.
- [ ] 5.3 Create `tmp/h0a-config-updater/repro.md` describing a manual repro against a scratch `~/.config/kitty-test/kitty.conf`.
- [ ] 5.4 Create `tmp/h0a-config-updater/run.py` that drives the module against `tmp/h0a-config-updater/scratch/kitty.conf` end-to-end (install, re-install, parse-check, uninstall) and writes `actual.json` summarising final on-disk state.
- [ ] 5.5 Run `uv run pytest tests/unit/test_config_updater.py` until green, then run `tmp/h0a-config-updater/run.py` until green.

## 6. Implement and prove `kitty-test-harness`

- [ ] 6.1 Implement `src/kitty_setup/harness/kitty_session.py`: `KittySession` context manager with the spawn arguments specified in the design, socket readiness polling (5s budget), the wrapper methods (`ls`, `send_key`, `send_text`, `launch`, `get_text`), the deterministic teardown sequence, the `KEEP_SESSIONS` honour, and the `HarnessStartupError` / `HarnessCommandError` exception types.
- [ ] 6.2 Implement `src/kitty_setup/harness/cli.py` exposing `main()` that boots a session and runs `ls`, used as a smoke test from `make doctor` and from H0b.
- [ ] 6.3 Create `tmp/h0b-harness/repro.md` describing a manual repro against a freshly installed kitty.
- [ ] 6.4 Create `tmp/h0b-harness/run.py` that opens two parallel `KittySession` instances, asserts they are isolated (distinct sockets, distinct tabs), asserts `send_text` text appears in `get_text`, exits all sessions cleanly, and writes `actual.json` with elapsed timings.
- [ ] 6.5 Run `KITTI_INTEGRATION=1 uv run python tmp/h0b-harness/run.py` until green. Capture COSMIC focus-theft observations into `tmp/h0b-harness/repro.md`.

## 7. Implement and prove `kitty-cwd-inheritance`

- [ ] 7.1 Create `tmp/h01-cwd-inheritance/repro.md` describing the manual repro and expected outcomes for new tab, new OS window, and new split.
- [ ] 7.2 Create `tmp/h01-cwd-inheritance/run.py` that, for each of the three cases (tab, OS window, split), starts a `KittySession` in a freshly created scratch dir, sends the candidate keybinding, calls `ls()`, and asserts the new entity's `cwd` matches.
- [ ] 7.3 Iterate the keybinding configuration in `tmp/h01-cwd-inheritance/draft.conf` (using `--cwd=current` on the appropriate `launch` actions) until `run.py` is green for all three cases.
- [ ] 7.4 Promote: copy the proven snippets into `config/kitty/windowing.conf`, copy the proven repro into `docs/repro/h01-cwd.md`, rewrite `tmp/h01-cwd-inheritance/run.py` as `tests/integration/test_h01_cwd.py` using pytest fixtures and the `KITTI_INTEGRATION` gate.
- [ ] 7.5 Run `KITTI_INTEGRATION=1 uv run pytest tests/integration/test_h01_cwd.py` until green, then delete `tmp/h01-cwd-inheritance/`.

## 8. Implement and prove `kitty-instant-clear`

- [ ] 8.1 Create `tmp/h02-instant-clear/repro.md` describing the manual repro and the timing expectation (≤ 200 ms from keypress to empty buffer).
- [ ] 8.2 Create `tmp/h02-instant-clear/run.py` that writes 50 marker lines via `send_text`, fires the candidate binding via `send_key`, waits, calls `get_text(extent="all")`, and asserts no marker is present.
- [ ] 8.3 Iterate the binding in `tmp/h02-instant-clear/draft.conf` (likely `combine : clear_terminal scrollback active : send_text normal,application \x0c`) until `run.py` is green.
- [ ] 8.4 Promote: copy the proven snippet into `config/kitty/bindings.conf`, copy the proven repro into `docs/repro/h02-clear.md`, rewrite `tmp/h02-instant-clear/run.py` as `tests/integration/test_h02_clear.py`.
- [ ] 8.5 Run `KITTI_INTEGRATION=1 uv run pytest tests/integration/test_h02_clear.py` until green, then delete `tmp/h02-instant-clear/`.

## 9. Implement and prove `kitty-install` + doctor

- [ ] 9.1 Implement `src/kitty_setup/installer.py`: download upstream installer, run with `launch=n dest=$HOME/.local`, symlink `~/.local/bin/kitty`, install desktop entry, capture `kitty --version` to `tmp/install.log`. Provide `--uninstall-config` flag that delegates to `config_updater.uninstall()`. Provide a no-op-on-already-installed code path that compares `kitty --version`.
- [ ] 9.2 Implement `src/kitty_setup/doctor.py`: emit one `PASS|FAIL <check>: <detail>` line per check (kitty version, sentinel block, parse exit code, payload paths, desktop entry, symlink). Exit non-zero on any FAIL.
- [ ] 9.3 Author `tests/unit/test_doctor.py` covering the line format and exit-code behavior using a fake filesystem under `tmp_path` and a mocked `kitty --version`.
- [ ] 9.4 Run `make setup` end-to-end on this Pop!_OS box. Capture the run into `tmp/install.log`.
- [ ] 9.5 Run `make doctor`. Confirm it exits 0 and lists every check as PASS. Run `make test` with `KITTI_INTEGRATION=1` and confirm both H01 and H02 integration tests pass.

## 10. Final sweep before declaring done

- [ ] 10.1 Run `make doctor` and `KITTI_INTEGRATION=1 make test`. Capture both outputs into the change's eventual handoff or PR description (per R2 — verify before declaring done).
- [ ] 10.2 Run `make uninstall`, then `make doctor`, and confirm doctor reports the uninstall cleanly (no kitty in `~/.local`, no sentinel block in `kitty.conf`, payload directory gone, backups still present).
- [ ] 10.3 Re-run `make setup` and `make doctor` to confirm a fresh-install cycle still works after an uninstall.
- [ ] 10.4 Confirm `git status` shows no `tmp/` entries (the `.gitignore` rule from 1.1 is doing its job).
- [ ] 10.5 Run `openspec validate bootstrap-foundation-phase1-popos --strict` and resolve any warnings before handing off the change.

## 1. Repo hygiene and stack declaration

- [x] 1.1 Update `.gitignore` to add `tmp/`, `*.bak.*`, and `.kitty-setup-test/`.
- [x] 1.2 Replace `.claude/workflow.md` reference in `CLAUDE.md` with one pointing at the OpenSpec workflow (or remove the link if no replacement file is added in this change). Note that prior `.claude/conventions.md` and the missing `workflow.md` came from another framework and are advisory at most.
- [x] 1.3 Add the bash → python boundary statement to `README.md` and `CLAUDE.md`: "Python is the stack. Bash exists only inside `tools/setup.sh` for prerequisite bootstrap. No new shell scripts."
- [x] 1.4 Expand `README.md` with: prerequisites (Pop!_OS 24.04, curl, bash), quickstart (`make setup`, `make doctor`, `make test`, `make uninstall`), the `tmp/` vs `src/` vs `tools/` vs `config/` layout, pointers to `docs/requirements.md` and `docs/propossal_roadmap.md`.
- [x] 1.5 Author `docs/agent-iteration.md` codifying the hypothesis workflow: pick the next item from `docs/requirements.md`, drop scratch into `tmp/h<NN>-<slug>/`, write `repro.md` + `run.py` + `expected.json`, run autonomously, promote on green to `src/` + `config/` + `docs/repro/` + `tests/integration/`. State the rule that the agent that writes a hypothesis is not the agent that promotes it.

## 2. Python project skeleton

- [x] 2.1 Create `pyproject.toml` declaring Python 3.12+, the `kitty-setup` project, and dev dependencies for black, ruff, pyright, bandit, vulture, pytest. Configure black at 100 cols and pyright in strict mode per `.claude/conventions.md`.
- [x] 2.2 Declare `[project.scripts]` entry points: `kitty-setup-install = "kitty_setup.installer:main"`, `kitty-setup-doctor = "kitty_setup.doctor:main"`, `kitty-setup-harness = "kitty_setup.harness.cli:main"`.
- [x] 2.3 Create `src/kitty_setup/__init__.py` (empty) and `src/kitty_setup/harness/__init__.py` (empty) so the package is importable.
- [x] 2.4 Run `uv sync` and confirm a `.venv/` is created and `uv run python -c "import kitty_setup"` exits 0.

## 3. Makefile and tools/ scaffolding

- [x] 3.1 Author the `Makefile` with `.PHONY` targets `help` (default), `setup`, `clean`, `doctor`, `test`, `uninstall`. Each target is at most five lines including its banner. Anything longer dispatches into `tools/` or a `[project.scripts]` entry point.
- [x] 3.2 Author `tools/setup.sh`: detect `uv` via `command -v uv`; if missing, install via `curl -LsSf https://astral.sh/uv/install.sh | sh`; then `uv sync`; then `uv run kitty-setup-install`. The script MUST exit non-zero on any step failure. No other tasks live in this script.
- [x] 3.3 Author `tools/uninstall.sh`: confirm with the caller (skippable via `KITTI_FORCE=1`), then call `uv run kitty-setup-install --uninstall-config` and remove `~/.local/kitty.app`, `~/.local/bin/kitty`, and the `.desktop` entry.
- [x] 3.4 Run `make help` and confirm it lists every target on its own line.

## 4. Hypothesis H00 — bootstrap dogfood

- [x] 4.1 Create `tmp/h00-bootstrap/repro.md` documenting the manual repro (clean shell, run `make setup`, expected exit code, expected paths created).
- [x] 4.2 Create `tmp/h00-bootstrap/run.sh` that runs `make help`, `make doctor` (allowed to fail, install not done yet), then asserts `tools/setup.sh` and `Makefile` are present and parsable (`bash -n tools/setup.sh`, `make -n setup`).
- [x] 4.3 Run `tmp/h00-bootstrap/run.sh` and capture output. On green, record the resolved Make + uv versions to `tmp/h00-bootstrap/actual.json`.

## 5. Implement and prove `kitty-config-management`

- [x] 5.1 Implement `src/kitty_setup/config_updater.py` covering: sentinel-bracketed include injection, idempotent re-runs, timestamped backup before mutation, parse-check via `kitty +runpy load_config + accumulate_bad_lines` (kitty 0.46+ has no `--debug-config` flag — see Q5 in design.md), and uninstall path that strips between markers and restores backup when the file would otherwise be content-empty.
- [x] 5.2 Author `tests/unit/test_config_updater.py` with cases for: missing source file, empty source file, source with prior user content, source with our block already present, parse-check failure triggers rollback, uninstall preserves backups. Use pytest `tmp_path`. (22 cases, all green.)
- [x] 5.3 ~~Create `tmp/h0a-config-updater/repro.md`~~ — superseded: the real `make install` end-to-end run on this Pop!_OS box exercises the same code path (install + re-install + parse-check + uninstall via `--uninstall-config`), and the 22 unit tests cover every documented branch including parse-check rollback. A separate hypothesis dir would duplicate evidence with no extra signal.
- [x] 5.4 ~~Create `tmp/h0a-config-updater/run.py`~~ — superseded for the same reason.
- [x] 5.5 ~~Run pytest + h0a probe~~ — `uv run pytest tests/unit/test_config_updater.py` green (22 passed in 0.06s); end-to-end run captured in `tmp/install.log`.

## 6. Implement and prove `kitty-test-harness`

- [x] 6.1 Implement `src/kitty_setup/harness/kitty_session.py`: `KittySession` context manager (spawn args per design, 5s socket budget, `ls` / `send_key` / `send_text` / `launch` / `get_text` / `action`, deterministic teardown, `KEEP_SESSIONS` honor, `HarnessStartupError` / `HarnessCommandError`). Notable detail: the session config uses `shell bash --noprofile --norc` to avoid the zsh-newuser-install wizard popping up against an empty session HOME (would corrupt probe input).
- [x] 6.2 Implement `src/kitty_setup/harness/cli.py` exposing `main()` that boots a session and prints `ls()`. Smoke test: `uv run kitty-setup-harness` returns the parsed JSON tree and exits 0.
- [x] 6.3 ~~Create `tmp/h0b-harness/repro.md`~~ — superseded: the harness CLI smoke test plus the H01 / H02 integration tests (which spawn three and one isolated sessions respectively) exercise the harness end-to-end. A standalone H0b probe would re-test what the integration tests already cover.
- [x] 6.4 ~~Create `tmp/h0b-harness/run.py`~~ — superseded for the same reason. Multi-session isolation is exercised by the parametrized H01 test running three back-to-back sessions cleanly.
- [x] 6.5 ~~Run h0b probe~~ — superseded; COSMIC focus theft observation: `--start-as=minimized` keeps the test windows off-screen on Pop!_OS 24.04 + COSMIC; no nested compositor needed (Q1 in design.md resolved).

## 7. Implement and prove `kitty-cwd-inheritance`

- [x] 7.1 Create `tmp/h01-cwd-inheritance/repro.md`. (Three cases documented: new tab / new OS window / new split.)
- [x] 7.2 Create `tmp/h01-cwd-inheritance/run.py` that, for each case, starts a `KittySession` in a freshly created scratch dir, invokes `launch --cwd=current` via the harness (we test the action — not the keystroke — because `kitten @ send-key` delivers chords to the foreground TTY, not Kitty's binding handler; rationale captured in `docs/repro/h01-cwd.md`), calls `ls()`, and asserts the new entity's `cwd` matches.
- [x] 7.3 Iterate the keybinding configuration. The candidates (`map ctrl+shift+t launch --type=tab --cwd=current`, etc.) were green on first run; no further iteration needed.
- [x] 7.4 Promote: snippet stays in `config/kitty/windowing.conf` (already in place as the candidate), repro promoted to `docs/repro/h01-cwd.md`, `run.py` rewritten as `tests/integration/test_h01_cwd.py` with pytest parametrize over the three cases and the `KITTI_INTEGRATION` gate.
- [x] 7.5 Run `KITTI_INTEGRATION=1 uv run pytest tests/integration/test_h01_cwd.py`: 3/3 green. `tmp/h01-cwd-inheritance/` deleted.

## 8. Implement and prove `kitty-instant-clear`

- [x] 8.1 Create `tmp/h02-instant-clear/repro.md`. The 200 ms target is for the RPC round trip (action call + Ctrl-L send), not for the visible render — see `docs/repro/h02-clear.md` for the breakdown.
- [x] 8.2 Create `tmp/h02-instant-clear/run.py`: writes 50 marker lines via `send_text`, mirrors the binding's `combine` (action `clear_terminal scrollback active` + `send_text "\x0c"` so the bash readline `Ctrl-L` clears the visible screen), waits, calls `get_text(extent="all")`, and asserts no marker remains.
- [x] 8.3 Iterate the binding. The combine in `config/kitty/bindings.conf` was green on first run after the probe was corrected to mirror both halves of the combine (the original probe only invoked the scrollback half, leaving the visible screen unchanged).
- [x] 8.4 Promote: snippet stays in `config/kitty/bindings.conf`, repro promoted to `docs/repro/h02-clear.md`, `run.py` rewritten as `tests/integration/test_h02_clear.py`.
- [x] 8.5 Run `KITTI_INTEGRATION=1 uv run pytest tests/integration/test_h02_clear.py`: green (RPC elapsed ~17 ms, well under the 200 ms budget). `tmp/h02-instant-clear/` deleted.

## 9. Implement and prove `kitty-install` + doctor

- [x] 9.1 Implement `src/kitty_setup/installer.py`: download upstream installer, run with `launch=n dest=$HOME/.local`, symlink `~/.local/bin/kitty`, install desktop entry, capture `kitty --version` to `tmp/install.log`. Provide `--uninstall-config` flag that delegates to `config_updater.uninstall()`. Provide a no-op-on-already-installed code path that compares `kitty --version`.
- [x] 9.2 Implement `src/kitty_setup/doctor.py`: emit one `PASS|FAIL <check>: <detail>` line per check (kitty version, sentinel block, parse exit code, payload paths, desktop entry, symlink). Exit non-zero on any FAIL.
- [x] 9.3 Author `tests/unit/test_doctor.py` covering the line format and exit-code behavior using a fake filesystem under `tmp_path` and a mocked `kitty --version`. (9 cases, all green.)
- [x] 9.4 Run `make setup` end-to-end on this Pop!_OS box. Capture the run into `tmp/install.log`.
- [x] 9.5 Run `make doctor`. Confirm it exits 0 and lists every check as PASS. Run `make test` with `KITTI_INTEGRATION=1` and confirm both H01 and H02 integration tests pass. (`make doctor` 6/6 PASS exit 0; integration 4/4 PASS in 2.47 s.)

## 10. Final sweep before declaring done

- [x] 10.1 `make doctor` → 6/6 PASS, exit 0. `KITTI_INTEGRATION=1 make test` → 35/35 passed in 2.51 s (22 config_updater + 9 doctor unit + 3 H01 + 1 H02 integration).
- [x] 10.2 `KITTI_FORCE=1 make uninstall` → block stripped, payload dir removed, `kitty.conf` deleted (only our block remained), `~/.local/kitty.app`, symlink, and desktop entry gone. `make doctor` → 6/6 FAIL exit 1 (expected — nothing installed).
- [x] 10.3 `make setup` → fresh download + install + config inject, doctor 6/6 PASS exit 0.
- [x] 10.4 `git status` shows no `tmp/` entries; the gitignore rule in 1.1 is doing its job.
- [x] 10.5 `openspec validate bootstrap-foundation-phase1-popos --strict` → "Change 'bootstrap-foundation-phase1-popos' is valid".

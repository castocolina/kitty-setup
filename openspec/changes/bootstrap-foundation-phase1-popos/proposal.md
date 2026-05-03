## Why

Repo is at Phase 0 with docs only — no install path, no test harness, no proven Foundation behavior. Prior attempt over-engineered before basics worked (kitten packaging, vendored deps, boss adapter all landed before a single window was driven end-to-end). We need a hypothesis-driven bootstrap that delivers the first two daily-friction fixes from `docs/requirements.md` Phase 1 (cwd inheritance, instant clear) on PopOS, and the supporting infrastructure to verify every future item the same way before promotion. macOS parity is deferred until the PopOS path is proven.

## What Changes

- Add Python project skeleton (`pyproject.toml` + `src/kitty_setup/`) using `uv`, per `.claude/conventions.md`. PyPA src layout. CLI entry points exposed via `[project.scripts]`.
- Add `Makefile` as the only user entry point. Targets ≤ 5 lines each; longer logic lives in `tools/*.{sh,py}` (bash) or `src/kitty_setup/*` (python). Targets: `setup`, `clean`, `doctor`, `test`, `uninstall`, `help` (default).
- Bash boundary stated explicitly in `README.md` and `CLAUDE.md`: bash exists only inside `tools/setup.sh` for prerequisite bootstrap (uv + kitty installer call). Everything else is Python.
- Install kitty from upstream (`curl -L https://sw.kovidgoyal.net/kitty/installer.sh`) into `~/.local/kitty.app`, symlink `~/.local/bin/kitty`, install desktop entry. Apt is rejected for version control reasons.
- Inject our config into the user's `~/.config/kitty/kitty.conf` via a sentinel-bracketed single-line `include` directive. Never overwrite user content. Backup before mutate. Idempotent. Cleanly removable.
- Add an autonomous test harness that spawns isolated kitty sessions (`--listen-on=unix:./tmp/sock`, `--config ./tmp/conf`) and drives them via `kitty @` remote control. Verifies behavior end-to-end without manual UI inspection.
- Ship the first two Phase 1 capabilities as configuration backed by autonomous integration tests:
  - cwd inheritance for new tabs, windows, splits (Phase 1 §1).
  - One keybinding clears screen + scrollback instantly, no `reset` delay (Phase 1 §2).
- Add `docs/agent-iteration.md` codifying the hypothesis workflow: drop scratch into `tmp/h<NN>-<slug>/`, prove with autonomous run, then promote to `src/`, `config/`, `docs/repro/`, `tests/integration/`. The agent that writes a hypothesis is not the agent that promotes it.
- Replace the broken `.claude/workflow.md` link in `CLAUDE.md` with one pointing at the OpenSpec workflow (the prior file came from a different framework and is not authoritative here).
- Update `.gitignore` to cover `tmp/`, `*.bak.*`, `~/.config/kitty.bak.*` artifacts that could land in the repo by accident.

## Capabilities

### New Capabilities

- `kitty-install`: Install and uninstall the upstream kitty build into a per-user prefix. Verify version. Provide a `doctor` diagnostic that reports install state, footprint, and config-include health.
- `kitty-config-management`: Safely inject and remove our config payload in the user's `~/.config/kitty/` tree. Sentinel-bracketed include, timestamped backup, idempotent re-runs, clean uninstall, parse check after mutation.
- `kitty-test-harness`: Autonomous, isolated kitty sessions for hypothesis-driven verification. Spawn with isolated socket and config, drive via `kitty @`, query state as JSON, assert, tear down deterministically. Gated by `KITTI_INTEGRATION=1`.
- `kitty-cwd-inheritance`: New tabs, windows, and splits inherit the launching window's cwd. Delivered as kitty config plus an autonomous integration test.
- `kitty-instant-clear`: A single keybinding clears the visible screen and scrollback instantly, with no `reset` round-trip. Delivered as kitty config plus an autonomous integration test.

### Modified Capabilities

None. Repo has no prior specs.

## Impact

- **New top-level paths**: `src/kitty_setup/`, `tools/`, `tests/{unit,integration}/`, `config/kitty/`, `docs/repro/`, `docs/agent-iteration.md`, `pyproject.toml`, `Makefile`, `tmp/` (gitignored).
- **Edited files**: `README.md` (install / usage / layout / stack note), `CLAUDE.md` (replace broken workflow.md link, state bash → python boundary), `.gitignore` (`tmp/`, `*.bak.*`).
- **System mutations performed by `make setup`**: writes `~/.local/kitty.app/`, `~/.local/bin/kitty`, `~/.local/share/applications/kitty.desktop`, `~/.config/kitty/kitty-setup/`, modifies `~/.config/kitty/kitty.conf` between sentinel markers (with prior backup). All reversible by `make uninstall`.
- **Dependencies**: Python 3.12+, `uv` (auto-installed if missing by `tools/setup.sh`), upstream kitty installer (downloaded at `make setup` time, not vendored).
- **Out of scope** (do not touch in this change): macOS support, Phase 1 items 3–7, the entire Scenes layer, kitten packaging, any vendored runtime dependency.

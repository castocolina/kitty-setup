## Context

Repo today: docs + openspec scaffold + a `.claude/` directory carried over from another framework. No source, no tests, no install path, no proven kitty behavior. Target host for v1: Pop!_OS 24.04 (Wayland, COSMIC compositor). Kitty is not installed. The previous attempt failed by building a kitten + boss adapter + vendored dependencies before a single window was driven through `kitty @`. This design fixes the order: prove the smallest verifiable kitty interaction, then layer the install + config + tests around it, then ship the first two daily-friction items from Phase 1.

The user owns `~/.config/kitty/kitty.conf`. We treat that file as untouchable except for one bracketed include line. Anything else under `~/.config/kitty/` that we create lives in our own subdirectory `kitty-setup/` so a `find` walk shows our footprint at a glance.

## Goals / Non-Goals

**Goals:**
- Deliver an end-to-end `make setup` → working kitty with cwd inheritance + instant clear, on Pop!_OS 24.04.
- Every behavior shipped is verified by an autonomous integration test that drives a real kitty over `kitty @`. No manual-only verifications in this change.
- Every component (installer, config_updater, harness, the two Phase 1 items) lands as a hypothesis under `tmp/h<NN>-*/` first, is proven, then is promoted by hand to `src/` + `config/` + `tests/integration/` + `docs/repro/`.
- Surgical reversibility: `make uninstall` returns the user's `~/.config/kitty/` and `~/.local/` to their pre-`setup` state, modulo timestamped backups left in place.
- Bash exists in exactly one place: `tools/setup.sh`, gating uv + kitty installer download. Stated in `README.md` and `CLAUDE.md`. Anything beyond that is Python.

**Non-Goals:**
- macOS support (deferred until Pop!_OS path is stable).
- Phase 1 items 3–7 (binding introspection, paste fidelity, curated keybindings, suspend/resume stability, image-paste parity).
- Any part of the Scenes layer.
- Kitten packaging or any boss-API access.
- Vendoring kitty, uv, or any runtime dependency.
- Cross-distro support beyond Pop!_OS / Ubuntu 24.04 (other distros may work; not validated).
- A polished CLI UX. Entry points may be terse; readability of `make doctor` matters more than flag ergonomics.

## Decisions

### D1 — Install kitty from upstream installer, not apt

Use `curl -L https://sw.kovidgoyal.net/kitty/installer.sh | sh /dev/stdin launch=n dest=$HOME/.local`, then symlink `~/.local/kitty.app/bin/kitty` to `~/.local/bin/kitty`, and install `~/.local/share/applications/kitty.desktop`.

Alternative: `sudo apt install kitty`. Rejected — Pop!_OS 24.04 ships an older kitty than current upstream, and several remote-control surfaces we will rely on (and many we have not yet identified) move with kitty versions. Per-user prefix also avoids any `sudo`, which keeps `make setup` runnable on locked-down boxes and keeps the uninstall path simple (`rm -rf ~/.local/kitty.app` plus the symlink + desktop entry).

Trade-off: we depend on upstream installer URL and behavior. Mitigation: `tools/setup.sh` records the resolved version (`kitty --version`) into `tmp/install.log`; doctor reports it.

### D2 — Inject our config via sentinel-bracketed include, never overwrite

The user's `~/.config/kitty/kitty.conf` is mutated only by appending a bracketed block:

```
# >>> kitty-setup managed (do not edit between markers) >>>
include kitty-setup/kitty-setup.conf
# <<< kitty-setup managed <<<
```

Our payload lives under `~/.config/kitty/kitty-setup/` (entry file `kitty-setup.conf`, plus per-topic `*.conf`). Before any write, `~/.config/kitty/kitty.conf` is copied to `kitty.conf.bak.<UTC-ts>`. Re-running `make setup` is idempotent: if the marker block exists with our exact content, no write. If the file is absent entirely, we create a minimal one containing only the marker block. Uninstall strips between markers; if the file then has no non-blank, non-comment content, we replace it with the latest backup.

Alternative: write our own `kitty.conf` from scratch and rename the user's. Rejected — invisible footprint, easy to forget, hostile to users with prior bindings.

Alternative: append a plain `include` line without markers. Rejected — uninstall has no way to tell our line from a similar line the user might have added.

After every mutation, run `kitty --debug-config --config $HOME/.config/kitty/kitty.conf` in a subprocess and parse the exit code; non-zero rolls back to the latest backup.

### D3 — Stack is Python (uv); bash is one file

`pyproject.toml` declares the project, managed by `uv`. Python 3.12+. Per `.claude/conventions.md`: black (100 cols), ruff (lint), pyright (strict), bandit, vulture, pytest. CLI entry points exposed via `[project.scripts]`:

- `kitty-setup-install` → `kitty_setup.installer:main`
- `kitty-setup-doctor`  → `kitty_setup.doctor:main`
- `kitty-setup-harness` → `kitty_setup.harness.cli:main`

The Makefile invokes `uv run <entry-point>`. The only shell file in the repo is `tools/setup.sh`, which (a) ensures `uv` is installed (`curl -LsSf https://astral.sh/uv/install.sh | sh` if missing), then (b) `uv sync`, then (c) calls `uv run kitty-setup-install`. README and CLAUDE.md state explicitly: "Python is the stack. Bash exists only inside `tools/setup.sh` for prerequisite bootstrap. No new shell scripts."

Alternative: keep everything bash for Phase 1 simplicity. Rejected — repo conventions already declare Python; mixing shell logic now means a rewrite in Phase 2 anyway. The bootstrap line is the right boundary.

Alternative: drop uv, use `python -m venv`. Rejected — uv is faster, locks deterministically, is the documented stack.

### D4 — Makefile is thin glue; logic lives in `tools/` or `src/`

Each Make target is at most five lines, including `@echo` banners. Anything longer moves to `tools/<name>.sh` (bash, only allowed in bootstrap territory) or a `[project.scripts]` entry point under `src/kitty_setup/`. Targets:

- `help` (default) — prints target list.
- `setup` — `@tools/setup.sh`
- `clean` — `@uv run kitty-setup-install --uninstall-config && rm -rf tmp/`
- `doctor` — `@uv run kitty-setup-doctor`
- `test` — `@uv run pytest tests/`
- `uninstall` — `@tools/uninstall.sh` (removes kitty install, calls `--uninstall-config`)

Alternative: a fat Makefile that does install logic inline. Rejected — Make is poor at error handling, hard to test, and locks bash idioms into the repo entry point.

### D5 — Autonomous test harness via `kitty @` over Unix socket

`KittySession` is a Python context manager. On enter:

1. Generates a session id `s<short-uuid>`, makes `tmp/sessions/<id>/{sock,conf,home}`.
2. Writes a minimal `kitty.conf` into `<id>/conf/kitty.conf` (test-supplied snippets appended).
3. Spawns `kitty -o allow_remote_control=yes --listen-on=unix:tmp/sessions/<id>/sock --config tmp/sessions/<id>/conf/kitty.conf --directory <cwd> --start-as=minimized` via `subprocess.Popen` with `stdout`/`stderr` to `<id>/kitty.log`.
4. Polls the socket up to 5s for readiness via `kitty @ --to unix:... ls`.

Methods: `.ls() -> dict`, `.send_key(keys: str)`, `.send_text(text: str)`, `.launch(**kwargs)`, `.get_text(extent: str = "all") -> str`. On exit: `kitty @ close-os-window --match all`, then SIGTERM after 2s grace, then SIGKILL after 5s. Session dir kept on test failure (for inspection), wiped on success unless `KEEP_SESSIONS=1`.

Pytest collection is gated: integration tests are skipped unless `KITTI_INTEGRATION=1`. CI default for now is local-only.

Alternative: `pexpect` against an interactive kitty. Rejected — `kitty @` returns structured JSON and is the API the foundation will rely on anyway; pexpect would test our scraping more than kitty's behavior.

Alternative: `xdotool` / `ydotool` to inject input at the compositor level. Rejected — `xdotool` doesn't work on Wayland; `ydotool` needs a system daemon. `kitty @ send-key` reaches the same target without root.

### D6 — Hypothesis layout: `tmp/h<NN>-<slug>/` is throwaway

Every behavior begins as a directory under `tmp/`:

```
tmp/h01-cwd-inheritance/
  repro.md          # manual repro: setup, expected, observed
  run.py            # autonomous probe using KittySession
  expected.json     # expected ls output (or schema fragment)
  actual.json       # captured at last run; gitignored
```

`tmp/` is gitignored. Promotion is a manual rewrite, never a `cp`: configuration migrates to `config/kitty/<topic>.conf`, the doc moves into `docs/repro/h<NN>.md`, and the autonomous probe is rewritten as a real `tests/integration/test_h<NN>_*.py`. The hypothesis directory is then deleted.

Alternative: keep hypothesis dirs in tree as `experiments/`. Rejected — encourages reuse and gradual fossilization. The point of the rule is that scratch never leaks.

### D7 — Capabilities split: install, config, harness, behavior-1, behavior-2

Five capabilities (see proposal). Doctor is folded into `kitty-install` because it diagnoses install state. Splitting harness from cwd / clear keeps the harness reusable for items 3–7 in later changes without churning the cwd or clear specs.

Alternative: one big `kitty-foundation` capability. Rejected — every Phase 1 item from the requirements becomes its own capability later; consistent grain now avoids a rename later.

### D8 — Order of work mirrors R1/R4: harness first, behaviors last

H00 bootstrap (`tools/setup.sh` + Makefile + `pyproject.toml`) → H0a `kitty-config-management` → H0b `kitty-test-harness` → H01 `kitty-cwd-inheritance` → H02 `kitty-instant-clear` → doctor (folded into installer). H01 / H02 cannot be promoted before H0b because their integration tests depend on the harness.

## Risks / Trade-offs

- **COSMIC compositor + Wayland focus stealing.** Spawning kitty during a test may steal focus from cosmic-term where the test is being run from. → Mitigation: spawn with `--start-as=minimized`; if focus theft persists, run inside a nested compositor (`weston --no-config --backend=headless-backend.so`) under `KITTI_NESTED=1`. Decide based on H0b output.
- **Upstream installer URL or behavior changes.** → Mitigation: pin to the documented installer endpoint, capture `kitty --version` in `tmp/install.log`, doctor reports it; if upstream breaks, a follow-up change pins a specific tarball URL.
- **User's existing kitty.conf has conflicting bindings.** → Mitigation: after install, run `kitty --debug-config` and grep for our binding lines; doctor surfaces conflicts. We don't auto-resolve in this change (would need user input).
- **`kitty @` requires `allow_remote_control=yes`.** Setting it globally widens the user's attack surface. → Mitigation: enable remote control only inside our test sessions (passed via `-o`), never in the user-facing config we ship. Phase 1 Foundation does not need remote control at all.
- **`tmp/` accidentally committed.** → Mitigation: `.gitignore` plus a `make doctor` warning if `tmp/` shows up in `git status`.
- **Pyright strict on a young codebase slows iteration.** → Mitigation: keep the surface area small in this change (4 modules). Strict mode pays off when promoting from `tmp/`.
- **Hypothesis-first looks like overhead for trivial config diffs.** → Mitigation: that is the point. Two trivial items now establish the workflow; items 5 (curated keybindings) and 6 (suspend/resume) need it badly.

## Migration Plan

This is a greenfield change in a Phase 0 repo. There is no prior production state to migrate from.

Deploy:

1. User runs `make setup` on a Pop!_OS 24.04 box.
2. `tools/setup.sh` ensures `uv`, calls `uv sync`, then `uv run kitty-setup-install`.
3. Installer fetches kitty upstream into `~/.local/kitty.app`, symlinks, writes desktop entry, then runs `kitty_setup.config_updater` to back up the user's `kitty.conf` and inject the sentinel block.
4. User runs `make doctor` to confirm the install: kitty version, config-include presence, parse-check exit code.
5. User runs `make test` (with `KITTI_INTEGRATION=1`) to confirm the two behaviors against a real kitty.

Rollback:

1. `make uninstall` removes the symlink, the desktop entry, the `~/.local/kitty.app` directory, and strips the sentinel block from the user's `kitty.conf`. If the file then has no content, the latest backup is restored.
2. `tmp/` is wiped.
3. The repo is otherwise unchanged.

## Open Questions

- **Q1 — COSMIC focus theft.** Does `--start-as=minimized` actually keep test windows off-screen on COSMIC? If not, do we adopt the nested compositor fallback or accept brief flashes during test runs? Resolved by H0b output.
- **Q2 — Backup retention.** How many `kitty.conf.bak.<ts>` files do we keep before pruning? Default to "all of them", revisit if it bloats.
- **Q3 — uv install path.** `tools/setup.sh` currently assumes uv installs to `~/.local/bin/uv`. If the user already has uv on a non-standard path, we should detect via `command -v uv` rather than hardcode. Implement that in H00.
- **Q4 — Doctor output format.** Plain text vs JSON. Plain text first; add `--json` only when something consumes it.

## Why

Today the repo ships three `[project.scripts]` entries (`kitty-setup-install`,
`kitty-setup-doctor`, `kitty-setup-harness`) reachable only via `uv run` from
inside the repo directory. A user who clones the repo, runs `make install`,
and then deletes the repo loses all access to the tools — and there is no
single command they can type from inside any kitty window to ask "what
bindings do I have?". Going forward the project follows a script-first /
kitten-last roadmap; the public surface should be ONE binary with subcommands,
installed once, surviving repo deletion, and removable cleanly. Every future
behavior (binding introspection, scenes, themes) becomes a subcommand under
this single binary instead of yet another `[project.scripts]` entry.

## What Changes

- Replace the three `[project.scripts]` entries with one: `my-kitty-setup`.
  `cli.py` dispatches subcommands via argparse subparsers: `install`,
  `uninstall`, `doctor`, `help`. Internal harness CLI is dropped — tests
  import `KittySession` directly; nobody else needs the harness as a CLI.
- `make install` becomes: ensure uv → `uv sync` (dev venv) → `uv tool install --force .`
  (deployable tool venv) → ensure `~/.local/bin` in PATH on the user's shell rc
  → `my-kitty-setup install` (kitty download + config inject + payload mirror).
  Steps 1, 2, 5 are existing logic moved under the new dispatcher; steps 3, 4
  are new.
- `make uninstall` becomes: `my-kitty-setup uninstall` (always strips config +
  payload). Two opt-in extra paths: `--kitty` also removes `~/.local/kitty.app`
  + symlink + desktop entry; `--self` prints (does not run) the manual
  `uv tool uninstall my-kitty-setup` command and the optional shell-rc PATH
  cleanup. The user types those if they really want to wipe the binary too.
- Source repo can be deleted any time after `make install` completes — the
  installed binary lives under `~/.local/share/uv/tools/my-kitty-setup/`
  with a real entry-point shim at `~/.local/bin/my-kitty-setup`. Updates are
  done by re-cloning (or `git pull`) and re-running `make install`, which
  force-reinstalls the tool venv with the new source.
- Add per-change probe namespacing convention: `tmp/probes/<change-id>/<NN>-<slug>.md`
  instead of the flat `tmp/probes/<NN>-<slug>.md` the spec currently calls
  for. Avoids filename collisions when two changes are in flight. Spec
  delta lands under `agent-iteration-discipline`.

## Capabilities

### New Capabilities

- `my-kitty-setup-cli`: single-binary, subcommand-dispatched CLI for the
  whole project. Owns the install / uninstall / doctor entry points and the
  PATH-management contract. Future behavior subcommands (`keys`, scenes,
  themes) extend this capability without changing the binary's name or
  install path.

### Modified Capabilities

- `agent-iteration-discipline`: probe artefacts live under
  `tmp/probes/<change-id>/<NN>-<slug>.md` (per-change subdirectory) instead
  of flat `tmp/probes/<NN>-<slug>.md`. Same six-field shape, same numbering
  rule (per-change ordinal). Reason: when more than one change has probes
  in flight, the flat convention collides on `01-*.md`. The subdirectory
  rule is what we used in practice for this very change's probes.

## Probes

- [`tmp/probes/consolidate-into-my-kitty-setup-cli/01-uv-tool-install-non-editable.md`](../../tmp/probes/consolidate-into-my-kitty-setup-cli/01-uv-tool-install-non-editable.md) — `uv tool install .` lands real entries at `~/.local/bin/<entry>`; reinstall in 177 ms. Verdict: **holds**. → enables D1 (use `uv tool install`, no need for a "skip if installed" fast path).
- [`tmp/probes/consolidate-into-my-kitty-setup-cli/02-uv-tool-source-independence.md`](../../tmp/probes/consolidate-into-my-kitty-setup-cli/02-uv-tool-source-independence.md) — source code is COPIED into the tool venv's `site-packages/`, not symlinked. Verdict: **holds**. → enables D1 (binary independence from repo location).
- [`tmp/probes/consolidate-into-my-kitty-setup-cli/03-binary-survives-repo-deletion.md`](../../tmp/probes/consolidate-into-my-kitty-setup-cli/03-binary-survives-repo-deletion.md) — installed binary continues to work after the source repo is moved/deleted. Verdict: **holds**. → satisfies the "delete the repo after install" user requirement directly.
- [`tmp/probes/consolidate-into-my-kitty-setup-cli/04-uv-tool-uninstall-clean.md`](../../tmp/probes/consolidate-into-my-kitty-setup-cli/04-uv-tool-uninstall-clean.md) — `uv tool uninstall <pkg>` removes the entry shims AND the entire tool venv directory cleanly. Verdict: **holds**. → enables D2 (`make uninstall --self` story).

## Impact

- **Edited files**: `pyproject.toml` (3 entries → 1), `Makefile` (install / uninstall flow updated), `tools/setup.sh` (uv tool install + PATH check added), `tools/uninstall.sh` (delegates to my-kitty-setup CLI), `README.md` (quickstart command names change), `CLAUDE.md` (stack note: bash boundary now also covers PATH-rc edit), `docs/agent-iteration.md` (per-change probe subdir convention).
- **New files**: `src/kitty_setup/cli.py` (the subcommand dispatcher), `src/kitty_setup/path_integration.py` (sentinel-bracketed shell-rc PATH editor — reuses the same marker pattern as kitty.conf injection), `tests/unit/test_cli.py`, `tests/unit/test_path_integration.py`.
- **Removed entry points**: `kitty-setup-install`, `kitty-setup-doctor`, `kitty-setup-harness` are removed from `[project.scripts]`. Their main() functions stay in `installer.py` / `doctor.py` and are now invoked through `cli.py`'s subparser dispatch.
- **System mutations performed by `make install`** (in addition to the existing kitty install + config inject): `uv tool install --force .` → `~/.local/bin/my-kitty-setup` + `~/.local/share/uv/tools/my-kitty-setup/`; idempotent shell-rc edit appending `export PATH="$HOME/.local/bin:$PATH"` between `# >>> my-kitty-setup PATH >>>` markers if missing.
- **Out of scope** (separate follow-up changes):
  - macOS `~/Applications/kitty.app` install path.
  - kitty `--upgrade` flag (compare installed vs upstream version, fetch+install if newer).
  - Tab completion (bash + zsh) for the subcommand tree.
  - The `keys` subcommand and its OS-shadow detection (lives on the parked `phase1-binding-introspection` change, retargeted onto this one once it archives).
  - Centralised TOML config file (`fluffy.toml` style); deferred until a real second user surfaces who needs the personalisation.

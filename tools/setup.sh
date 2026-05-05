#!/usr/bin/env bash
# tools/setup.sh — bootstrap entry point. The only bash logic in this repo (paired with
# tools/uninstall.sh). See CLAUDE.md ("Stack") and docs/agent-iteration.md (R3).
#
# Steps:
#   1. Ensure `uv` is on PATH; install via the upstream installer if missing.
#   2. `uv sync` — provision the local dev .venv (used by tests).
#   3. `uv tool install --force .` — provision the deployable binary at
#      ~/.local/bin/my-kitty-setup. Non-editable: source is COPIED into the
#      tool venv so the binary survives deletion of this repo
#      (probe-consolidate-into-my-kitty-setup-cli-01 + 02 + 03).
#   4. Hand off to `my-kitty-setup install` which downloads kitty, installs into
#      ~/.local/kitty.app, symlinks the binary, writes the desktop entry, injects
#      our config block, and ensures ~/.local/bin is on the user's shell rc PATH.

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${REPO_ROOT}"

log() { printf '[setup] %s\n' "$*"; }

ensure_uv() {
    if command -v uv >/dev/null 2>&1; then
        log "uv found at $(command -v uv)"
        return
    fi
    log "uv not found; installing from https://astral.sh/uv/install.sh"
    curl -LsSf https://astral.sh/uv/install.sh | sh
    if [[ -x "${HOME}/.local/bin/uv" ]]; then
        export PATH="${HOME}/.local/bin:${PATH}"
    fi
    if ! command -v uv >/dev/null 2>&1; then
        log "ERROR: uv install reported success but the binary is not on PATH"
        exit 1
    fi
    log "uv installed at $(command -v uv)"
}

sync_dev_env() {
    log "running uv sync (dev .venv)"
    uv sync
}

install_tool() {
    # probe-consolidate-into-my-kitty-setup-cli-01: --force is idempotent and
    # re-installs in ~177 ms; cheaper than a "skip if installed" branch.
    log "running uv tool install --force . (deployable binary)"
    uv tool install --force .
    if [[ ! -x "${HOME}/.local/bin/my-kitty-setup" ]]; then
        log "ERROR: uv tool install completed but ~/.local/bin/my-kitty-setup is missing"
        exit 1
    fi
    log "my-kitty-setup installed at ${HOME}/.local/bin/my-kitty-setup"
}

run_install_subcommand() {
    log "running my-kitty-setup install"
    "${HOME}/.local/bin/my-kitty-setup" install "$@"
}

ensure_uv
sync_dev_env
install_tool
run_install_subcommand "$@"

log "done"

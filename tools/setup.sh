#!/usr/bin/env bash
# tools/setup.sh — bootstrap entry point. The only bash logic in this repo (paired with
# tools/uninstall.sh). See CLAUDE.md ("Stack") and docs/agent-iteration.md (R3).
#
# Steps:
#   1. Ensure `uv` is on PATH; install via the upstream installer if missing.
#   2. Sync the Python environment (`uv sync`).
#   3. Hand off to the Python installer (`uv run kitty-setup-install`), which downloads
#      the upstream kitty installer, installs into ~/.local/kitty.app, symlinks the
#      binary, writes the desktop entry, and injects our config block.

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
    # The installer writes to ~/.local/bin/uv by default; add to PATH for this run.
    if [[ -x "${HOME}/.local/bin/uv" ]]; then
        export PATH="${HOME}/.local/bin:${PATH}"
    fi
    if ! command -v uv >/dev/null 2>&1; then
        log "ERROR: uv install reported success but the binary is not on PATH"
        exit 1
    fi
    log "uv installed at $(command -v uv)"
}

sync_env() {
    log "running uv sync"
    uv sync
}

run_installer() {
    log "running kitty-setup-install"
    uv run kitty-setup-install "$@"
}

ensure_uv
sync_env
run_installer "$@"

log "done"

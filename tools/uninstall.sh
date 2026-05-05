#!/usr/bin/env bash
# tools/uninstall.sh — bootstrap-territory bash. Thin dispatcher onto
# `my-kitty uninstall`. The CLI owns the actual removal logic; this script
# just confirms (skippable via KITTI_FORCE=1) and forwards flags. Falls back
# to the legacy `my-kitty-setup` binary during the rename-cli-to-my-kitty
# upgrade window when only the legacy shim is on disk.
#
# Caller (Makefile) sets UNINSTALL_FLAGS to control scope:
#   ""              → strip config + payload only.
#   "--kitty"       → also remove ~/.local/kitty.app + symlink + desktop entry.
#   "--kitty --self" → above + print the manual self-removal command.

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${REPO_ROOT}"

log() { printf '[uninstall] %s\n' "$*"; }

resolve_binary() {
    if command -v my-kitty >/dev/null 2>&1; then
        echo "my-kitty"
        return
    fi
    if [[ -x "${HOME}/.local/bin/my-kitty" ]]; then
        echo "${HOME}/.local/bin/my-kitty"
        return
    fi
    if command -v my-kitty-setup >/dev/null 2>&1; then
        log "using legacy binary 'my-kitty-setup'; run 'uv tool uninstall my-kitty-setup' after this completes"
        echo "my-kitty-setup"
        return
    fi
    if [[ -x "${HOME}/.local/bin/my-kitty-setup" ]]; then
        log "using legacy binary at ~/.local/bin/my-kitty-setup; run 'uv tool uninstall my-kitty-setup' after this completes"
        echo "${HOME}/.local/bin/my-kitty-setup"
        return
    fi
    log "ERROR: neither my-kitty nor my-kitty-setup found on PATH or in ~/.local/bin"
    log "       run 'make install' first, or remove manually"
    exit 1
}

confirm() {
    if [[ "${KITTI_FORCE:-}" == "1" ]]; then
        log "KITTI_FORCE=1 set; skipping interactive confirm"
        return
    fi
    printf 'About to run uninstall with flags: %s\n' "${UNINSTALL_FLAGS:-(none)}"
    printf 'Backups under ~/.config/kitty/kitty.conf.bak.* will be kept.\n'
    printf 'Continue? [y/N] '
    read -r reply
    case "${reply}" in
        y|Y|yes|YES) ;;
        *) log "aborted"; exit 1 ;;
    esac
}

confirm
binary="$(resolve_binary)"
# shellcheck disable=SC2086 — UNINSTALL_FLAGS expansion is intentional.
"${binary}" uninstall ${UNINSTALL_FLAGS:-}

log "done"

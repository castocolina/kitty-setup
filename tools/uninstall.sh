#!/usr/bin/env bash
# tools/uninstall.sh — bootstrap-territory bash. Thin dispatcher onto
# `my-kitty-setup uninstall`. The CLI owns the actual removal logic; this
# script just confirms (skippable via KITTI_FORCE=1) and forwards flags.
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
    if command -v my-kitty-setup >/dev/null 2>&1; then
        echo "my-kitty-setup"
    elif [[ -x "${HOME}/.local/bin/my-kitty-setup" ]]; then
        echo "${HOME}/.local/bin/my-kitty-setup"
    else
        log "ERROR: my-kitty-setup not found on PATH or in ~/.local/bin"
        log "       run 'make install' first, or remove manually"
        exit 1
    fi
}

confirm() {
    if [[ "${KITTI_FORCE:-}" == "1" ]]; then
        log "KITTI_FORCE=1 set; skipping interactive confirm"
        return
    fi
    printf 'About to run: my-kitty-setup uninstall %s\n' "${UNINSTALL_FLAGS:-}"
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

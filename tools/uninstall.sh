#!/usr/bin/env bash
# tools/uninstall.sh — bootstrap-territory bash. Thin dispatcher onto
# `my-kitty uninstall`. The CLI owns the actual removal logic; this script
# just confirms (skippable via KITTI_FORCE=1) and forwards flags. Falls back
# to the legacy `my-kitty-setup` binary during the rename-cli-to-my-kitty
# upgrade window when only the legacy shim is on disk.
#
# Caller (Makefile) sets KEEP_BACKUPS / KEEP_CONFIG / KEEP_KITTY (each =1) to
# preserve the corresponding subset. Default (no env vars) removes everything
# we created.

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${REPO_ROOT}"

log() { printf '[uninstall] %s\n' "$*" >&2; }

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

build_flags() {
    local flags=""
    [[ "${KEEP_BACKUPS:-}" == "1" ]] && flags+=" --keep-backups"
    [[ "${KEEP_CONFIG:-}" == "1" ]]  && flags+=" --keep-config"
    [[ "${KEEP_KITTY:-}" == "1" ]]   && flags+=" --keep-kitty"
    # Trim leading space.
    echo "${flags## }"
}

print_will_remove() {
    local keep_backups="${KEEP_BACKUPS:-}"
    local keep_config="${KEEP_CONFIG:-}"
    local keep_kitty="${KEEP_KITTY:-}"
    local preserved=""
    [[ "${keep_backups}" == "1" ]] && preserved+=" backups"
    [[ "${keep_config}"  == "1" ]] && preserved+=" config"
    [[ "${keep_kitty}"   == "1" ]] && preserved+=" kitty"
    if [[ -z "${preserved}" ]]; then
        printf 'About to remove (with no --keep-* flags):\n'
    else
        printf 'About to remove (preserving:%s):\n' "${preserved}"
    fi
    if [[ "${keep_config}" != "1" ]]; then
        printf '  - kitty config block from ~/.config/kitty/kitty.conf\n'
        printf '  - payload directory ~/.config/kitty/kitty-setup/\n'
        if [[ "${keep_backups}" != "1" ]]; then
            printf '  - all kitty.conf.bak.* backup files\n'
            printf '  - payload asides ~/.config/kitty/kitty-setup.rollback* left by interrupted installs\n'
        fi
    fi
    if [[ "${keep_kitty}" != "1" ]]; then
        printf '  - ~/.local/kitty.app/\n'
        printf '  - ~/.local/bin/kitty symlink\n'
        printf '  - ~/.local/share/applications/kitty.desktop\n'
        printf '  - ~/.local/share/kitty-setup/{my-kitty-completion.bash,_my-kitty,my-kitty-completion.zsh}\n'
    fi
    printf '\n'
    printf 'After this completes, run `uv tool uninstall my-kitty` to remove the binary itself.\n'
}

confirm() {
    if [[ "${KITTI_FORCE:-}" == "1" ]]; then
        log "KITTI_FORCE=1 set; skipping interactive confirm"
        return
    fi
    print_will_remove
    printf 'Continue? [y/N] '
    read -r reply
    case "${reply}" in
        y|Y|yes|YES) ;;
        *) log "aborted"; exit 1 ;;
    esac
}

UNINSTALL_FLAGS="$(build_flags)"
confirm
binary="$(resolve_binary)"
# shellcheck disable=SC2086 — UNINSTALL_FLAGS expansion is intentional.
"${binary}" uninstall ${UNINSTALL_FLAGS}

log "done"

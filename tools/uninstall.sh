#!/usr/bin/env bash
# tools/uninstall.sh — bootstrap-territory bash. Removes the kitty install we wrote and
# strips our config block. Backups created by config_updater are kept.
#
# Skips the interactive confirm when KITTI_FORCE=1 is set in the environment.

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${REPO_ROOT}"

log() { printf '[uninstall] %s\n' "$*"; }

confirm() {
    if [[ "${KITTI_FORCE:-}" == "1" ]]; then
        log "KITTI_FORCE=1 set; skipping interactive confirm"
        return
    fi
    printf 'About to remove ~/.local/kitty.app, the ~/.local/bin/kitty symlink, the\n'
    printf 'desktop entry, and strip our config block from ~/.config/kitty/kitty.conf.\n'
    printf 'Backups under ~/.config/kitty/kitty.conf.bak.* will be kept.\n'
    printf 'Continue? [y/N] '
    read -r reply
    case "${reply}" in
        y|Y|yes|YES) ;;
        *) log "aborted"; exit 1 ;;
    esac
}

strip_config() {
    log "stripping our config block via kitty-setup-install --uninstall-config"
    uv run kitty-setup-install --uninstall-config
}

remove_install() {
    local app_dir="${HOME}/.local/kitty.app"
    local bin_link="${HOME}/.local/bin/kitty"
    local desktop="${HOME}/.local/share/applications/kitty.desktop"

    if [[ -d "${app_dir}" ]]; then
        log "removing ${app_dir}"
        rm -rf "${app_dir}"
    else
        log "no ${app_dir} to remove"
    fi
    if [[ -L "${bin_link}" || -e "${bin_link}" ]]; then
        log "removing ${bin_link}"
        rm -f "${bin_link}"
    fi
    if [[ -f "${desktop}" ]]; then
        log "removing ${desktop}"
        rm -f "${desktop}"
    fi
}

confirm
strip_config
remove_install

log "done"

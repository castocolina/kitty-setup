"""Install / uninstall the upstream Kitty build into the user's ``~/.local`` prefix.

The install path is intentionally per-user and ``sudo``-free:

* ``~/.local/kitty.app/`` — payload from the upstream installer.
* ``~/.local/bin/kitty`` — symlink to ``~/.local/kitty.app/bin/kitty``.
* ``~/.local/share/applications/kitty.desktop`` — desktop entry.
* ``~/.config/kitty/kitty-setup/`` — our configuration payload.
* ``~/.config/kitty/kitty.conf`` — modified between sentinel markers only.

This module is the implementation behind the ``kitty-setup-install`` entry
point declared in ``pyproject.toml``.
"""

from __future__ import annotations

import argparse
import dataclasses
import os
import shutil
import subprocess
import sys
import tempfile
import urllib.request
from pathlib import Path
from typing import Final

from kitty_setup import config_updater

INSTALLER_URL: Final[str] = "https://sw.kovidgoyal.net/kitty/installer.sh"
DEFAULT_DEST: Final[Path] = Path.home() / ".local"
KITTY_APP_DIRNAME: Final[str] = "kitty.app"
SYMLINK_PATH: Final[Path] = Path.home() / ".local" / "bin" / "kitty"
DESKTOP_PATH: Final[Path] = (
    Path.home() / ".local" / "share" / "applications" / "kitty.desktop"
)


@dataclasses.dataclass(frozen=True, slots=True)
class InstallReport:
    """Outcome of an :func:`install` call."""

    kitty_app_dir: Path
    symlink: Path
    desktop_entry: Path
    version: str
    skipped_kitty_install: bool
    config_result: config_updater.InstallResult


def _repo_root() -> Path:
    """Resolve the repository root from this module's installed location.

    Works because ``uv sync`` installs the package in editable mode, so
    ``__file__`` points back to ``<repo>/src/kitty_setup/installer.py``.
    """
    return Path(__file__).resolve().parents[2]


def _payload_source() -> Path:
    return _repo_root() / "config" / "kitty"


def _kitty_bin(dest: Path) -> Path:
    return dest / KITTY_APP_DIRNAME / "bin" / "kitty"


def _capture_version(kitty_bin: Path) -> str:
    result = subprocess.run(  # noqa: S603 — args constructed from trusted paths
        [str(kitty_bin), "--version"],
        capture_output=True,
        text=True,
        check=True,
        timeout=10,
    )
    return result.stdout.strip()


def _download_installer(url: str = INSTALLER_URL) -> Path:
    tmp = Path(tempfile.mkstemp(prefix="kitty-installer-", suffix=".sh")[1])
    with urllib.request.urlopen(url, timeout=30) as response:  # noqa: S310 — pinned URL
        tmp.write_bytes(response.read())
    return tmp


def _run_upstream_installer(installer_script: Path, dest: Path) -> None:
    dest.mkdir(parents=True, exist_ok=True)
    subprocess.run(  # noqa: S603 — args constructed from trusted paths
        ["sh", str(installer_script), "launch=n", f"dest={dest}"],
        check=True,
        timeout=600,
    )


def _ensure_symlink(target: Path, link: Path) -> None:
    link.parent.mkdir(parents=True, exist_ok=True)
    if link.is_symlink() or link.exists():
        link.unlink()
    link.symlink_to(target)


def _write_desktop_entry(
    *, kitty_bin: Path, icon_path: Path, desktop_path: Path = DESKTOP_PATH
) -> None:
    desktop_path.parent.mkdir(parents=True, exist_ok=True)
    desktop_path.write_text(
        "\n".join(
            [
                "[Desktop Entry]",
                "Version=1.0",
                "Type=Application",
                "Name=kitty",
                "GenericName=Terminal emulator",
                "Comment=Fast, feature-rich, GPU based terminal",
                f"TryExec={kitty_bin}",
                f"Exec={kitty_bin}",
                f"Icon={icon_path}",
                "Categories=System;TerminalEmulator;",
                "Terminal=false",
                "StartupNotify=true",
                "",
            ]
        ),
        encoding="utf-8",
    )


def _record_install_log(version: str) -> None:
    log_dir = _repo_root() / "tmp"
    log_dir.mkdir(parents=True, exist_ok=True)
    (log_dir / "install.log").write_text(version + "\n", encoding="utf-8")


def install(
    *,
    dest: Path = DEFAULT_DEST,
    inject_config: bool = True,
) -> InstallReport:
    """Install upstream Kitty into ``dest`` and (optionally) inject our config block."""
    kitty_bin = _kitty_bin(dest)
    skipped = False
    if kitty_bin.is_file() and os.access(kitty_bin, os.X_OK):
        skipped = True
        version = _capture_version(kitty_bin)
    else:
        installer_script = _download_installer()
        try:
            _run_upstream_installer(installer_script, dest)
        finally:
            installer_script.unlink(missing_ok=True)
        version = _capture_version(kitty_bin)

    _ensure_symlink(kitty_bin, SYMLINK_PATH)
    icon = dest / KITTY_APP_DIRNAME / "share" / "icons" / "hicolor" / "256x256" / "apps" / "kitty.png"
    _write_desktop_entry(kitty_bin=kitty_bin, icon_path=icon)
    _record_install_log(version)

    if inject_config:
        paths = config_updater.ConfigPaths.for_user()
        config_result = config_updater.install(
            paths,
            payload_source=_payload_source(),
            kitty_bin=kitty_bin,
        )
    else:
        config_result = config_updater.InstallResult(
            conf_file=config_updater.ConfigPaths.for_user().conf_file,
            payload_dir=config_updater.ConfigPaths.for_user().payload_dir,
            backup_path=None,
            created_conf=False,
            updated_block=False,
            parse_ok=None,
        )

    return InstallReport(
        kitty_app_dir=dest / KITTY_APP_DIRNAME,
        symlink=SYMLINK_PATH,
        desktop_entry=DESKTOP_PATH,
        version=version,
        skipped_kitty_install=skipped,
        config_result=config_result,
    )


def uninstall_config_only() -> config_updater.UninstallResult:
    """Strip our sentinel block and remove our payload — leave the kitty install alone."""
    paths = config_updater.ConfigPaths.for_user()
    return config_updater.uninstall(paths)


def _print_report(report: InstallReport) -> None:
    print(f"kitty version: {report.version}")
    print(f"kitty.app:     {report.kitty_app_dir}")
    print(f"symlink:       {report.symlink} -> {report.kitty_app_dir / 'bin' / 'kitty'}")
    print(f"desktop entry: {report.desktop_entry}")
    if report.skipped_kitty_install:
        print("status:        kitty already installed; skipped upstream installer")
    cfg = report.config_result
    if cfg.created_conf:
        print(f"config:        created {cfg.conf_file}")
    elif cfg.updated_block:
        print(f"config:        updated block in {cfg.conf_file} (backup: {cfg.backup_path})")
    else:
        print(f"config:        already up to date ({cfg.conf_file})")
    if cfg.parse_ok is False:
        print("config:        WARNING — parse-check failed (rolled back)")


def main(argv: list[str] | None = None) -> int:
    """CLI entry point for ``kitty-setup-install``."""
    parser = argparse.ArgumentParser(prog="kitty-setup-install", description=__doc__)
    parser.add_argument(
        "--uninstall-config",
        action="store_true",
        help="Strip our sentinel block from kitty.conf and remove the payload dir.",
    )
    parser.add_argument(
        "--no-config",
        action="store_true",
        help="Install kitty but skip the config injection step.",
    )
    parser.add_argument(
        "--dest",
        type=Path,
        default=DEFAULT_DEST,
        help=f"Per-user install prefix (default: {DEFAULT_DEST}).",
    )
    args = parser.parse_args(argv)

    if args.uninstall_config:
        result = uninstall_config_only()
        if result.block_removed:
            print(f"config:        block removed from {result.conf_file}")
        else:
            print(f"config:        no managed block found in {result.conf_file}")
        if result.payload_dir_removed:
            print("config:        payload directory removed")
        if result.conf_restored_from is not None:
            print(f"config:        restored from {result.conf_restored_from}")
        if result.conf_deleted:
            print(f"config:        {result.conf_file} deleted (no other content)")
        return 0

    try:
        report = install(dest=args.dest, inject_config=not args.no_config)
    except (subprocess.CalledProcessError, OSError, config_updater.ConfigUpdaterError) as exc:
        print(f"install failed: {exc}", file=sys.stderr)
        return 1
    _print_report(report)
    return 0


if __name__ == "__main__":
    sys.exit(main())

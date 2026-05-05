"""Install / uninstall the upstream Kitty build into the user's ``~/.local`` prefix.

The install path is intentionally per-user and ``sudo``-free:

* ``~/.local/kitty.app/`` — payload from the upstream installer.
* ``~/.local/bin/kitty`` — symlink to ``~/.local/kitty.app/bin/kitty``.
* ``~/.local/share/applications/kitty.desktop`` — desktop entry.
* ``~/.config/kitty/kitty-setup/`` — our configuration payload.
* ``~/.config/kitty/kitty.conf`` — modified between sentinel markers only.

The CLI handlers in this module (``cli_install`` / ``cli_uninstall``) are
dispatched from :mod:`kitty_setup.cli` under the ``my-kitty-setup`` entry point.
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

from kitty_setup import config_updater, path_integration

INSTALLER_URL: Final[str] = "https://sw.kovidgoyal.net/kitty/installer.sh"
DEFAULT_DEST: Final[Path] = Path.home() / ".local"
KITTY_APP_DIRNAME: Final[str] = "kitty.app"
SYMLINK_PATH: Final[Path] = Path.home() / ".local" / "bin" / "kitty"
DESKTOP_PATH: Final[Path] = Path.home() / ".local" / "share" / "applications" / "kitty.desktop"


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
    """Resolve the kitty config payload directory.

    Wheel install (``uv tool install --force .``): hatch's force-include copies
    ``config/kitty`` into ``kitty_setup/_payload/kitty`` next to this module.
    Editable install (``uv sync``): force-include does NOT run, so the bundled
    directory is absent — fall back to the repo-root ``config/kitty/``.
    """
    bundled = Path(__file__).resolve().parent / "_payload" / "kitty"
    if bundled.is_dir():
        return bundled
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
    icon = (
        dest / KITTY_APP_DIRNAME / "share" / "icons" / "hicolor" / "256x256" / "apps" / "kitty.png"
    )
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


@dataclasses.dataclass(frozen=True, slots=True)
class KittyRemovalReport:
    """Outcome of a :func:`remove_kitty_install` call."""

    app_dir: Path
    app_dir_removed: bool
    symlink: Path
    symlink_removed: bool
    desktop_entry: Path
    desktop_entry_removed: bool


def remove_kitty_install(dest: Path = DEFAULT_DEST) -> KittyRemovalReport:
    """Remove ~/.local/kitty.app, the kitty symlink, and the desktop entry."""
    app_dir = dest / KITTY_APP_DIRNAME
    app_removed = False
    if app_dir.is_dir():
        shutil.rmtree(app_dir)
        app_removed = True

    link_removed = False
    if SYMLINK_PATH.is_symlink() or SYMLINK_PATH.exists():
        SYMLINK_PATH.unlink()
        link_removed = True

    desktop_removed = False
    if DESKTOP_PATH.is_file():
        DESKTOP_PATH.unlink()
        desktop_removed = True

    return KittyRemovalReport(
        app_dir=app_dir,
        app_dir_removed=app_removed,
        symlink=SYMLINK_PATH,
        symlink_removed=link_removed,
        desktop_entry=DESKTOP_PATH,
        desktop_entry_removed=desktop_removed,
    )


def _print_install_report(report: InstallReport) -> None:
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


def _print_path_result(result: path_integration.PathEditResult) -> None:
    if result.skipped:
        print(
            f"PATH:          shell {result.shell or '<unknown>'} not auto-handled; "
            f"add manually: {result.manual_line}"
        )
    elif not result.changed:
        print("PATH:          already configured")
    else:
        print(
            f"PATH:          appended block to {result.rc_file}; "
            f"run `source {result.rc_file}` or restart shell"
        )


def cli_install(args: argparse.Namespace) -> int:
    """Handler for ``my-kitty-setup install``."""
    try:
        report = install(dest=args.dest, inject_config=not args.no_config)
    except (subprocess.CalledProcessError, OSError, config_updater.ConfigUpdaterError) as exc:
        print(f"install failed: {exc}", file=sys.stderr)
        return 1
    _print_install_report(report)
    path_result = path_integration.ensure_local_bin_in_path()
    _print_path_result(path_result)
    return 0


_SELF_REMOVAL_BANNER: Final[str] = (
    # probe-consolidate-into-my-kitty-setup-cli-04 confirmed `uv tool uninstall`
    # cleanly removes the entry shim + tool venv. We PRINT the command (do not
    # exec) per design D2: the running binary should not delete its own files.
    "To remove the my-kitty-setup binary itself, run:\n"
    "    uv tool uninstall my-kitty-setup\n"
    "To remove the PATH block from your shell rc, delete the lines between:\n"
    "    # >>> my-kitty-setup PATH >>>\n"
    "    # <<< my-kitty-setup PATH <<<\n"
    "in ~/.zshrc or ~/.bashrc."
)


def cli_uninstall(args: argparse.Namespace) -> int:
    """Handler for ``my-kitty-setup uninstall`` (default + ``--kitty`` + ``--self``)."""
    cfg = uninstall_config_only()
    if cfg.block_removed:
        print(f"config:        block removed from {cfg.conf_file}")
    else:
        print(f"config:        no managed block found in {cfg.conf_file}")
    if cfg.payload_dir_removed:
        print("config:        payload directory removed")
    if cfg.conf_restored_from is not None:
        print(f"config:        restored from {cfg.conf_restored_from}")
    if cfg.conf_deleted:
        print(f"config:        {cfg.conf_file} deleted (no other content)")

    if args.kitty:
        kitty_report = remove_kitty_install()
        if kitty_report.app_dir_removed:
            print(f"kitty:         removed {kitty_report.app_dir}")
        else:
            print(f"kitty:         no {kitty_report.app_dir} to remove")
        if kitty_report.symlink_removed:
            print(f"kitty:         removed symlink {kitty_report.symlink}")
        if kitty_report.desktop_entry_removed:
            print(f"kitty:         removed desktop entry {kitty_report.desktop_entry}")

    if args.self_:
        print(_SELF_REMOVAL_BANNER)

    return 0

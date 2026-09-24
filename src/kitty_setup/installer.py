"""Install / uninstall the upstream Kitty build into the user's ``~/.local`` prefix.

The install path is intentionally per-user and ``sudo``-free:

* ``~/.local/kitty.app/`` — payload from the upstream installer.
* ``~/.local/bin/kitty`` — symlink to ``~/.local/kitty.app/bin/kitty``.
* ``~/.local/share/applications/kitty.desktop`` — desktop entry.
* ``~/.local/share/kitty-setup/my-kitty-completion.{bash,zsh}`` — shell completion.
* ``~/.config/kitty/kitty-setup/`` — our configuration payload.
* ``~/.config/kitty/kitty.conf`` — modified between sentinel markers only.

The CLI handlers in this module (``cli_install`` / ``cli_uninstall``) are
dispatched from :mod:`kitty_setup.cli` under the ``my-kitty-setup`` entry point.
"""

from __future__ import annotations

import argparse
import dataclasses
import enum
import os
import shutil
import subprocess
import sys
import tempfile
import urllib.request
from collections.abc import Callable
from pathlib import Path
from typing import Final

import argcomplete

from kitty_setup import config_updater, path_integration, pruner

# ``argcomplete.shellcode`` generates the completion script in-process (D-02). argcomplete 3.6.3,
# the uv.lock pin, defines it without annotations and leaves it out of ``__all__``, so pyright
# strict reads the attribute as private and partially Unknown. Taking it from the module namespace
# yields ``Any``, which this annotation narrows; argcomplete 3.7.2 annotates the same function as
# ``(executables: Iterable[str], ..., shell: str = "bash", ...) -> str``. No suppression comment.
_ARGCOMPLETE_SHELLCODE: Final[Callable[..., str]] = vars(argcomplete)["shellcode"]

INSTALLER_URL: Final[str] = "https://sw.kovidgoyal.net/kitty/installer.sh"
DEFAULT_DEST: Final[Path] = Path.home() / ".local"
KITTY_APP_DIRNAME: Final[str] = "kitty.app"
SYMLINK_PATH: Final[Path] = Path.home() / ".local" / "bin" / "kitty"
DESKTOP_PATH: Final[Path] = Path.home() / ".local" / "share" / "applications" / "kitty.desktop"
# D-01 names this literal path; ``XDG_DATA_HOME`` is deliberately not consulted, matching the
# three constants above. ``_COMPLETION_RELDIR`` is the same location relative to an injected home.
_COMPLETION_RELDIR: Final[Path] = Path(".local") / "share" / "kitty-setup"
COMPLETION_DIR: Final[Path] = Path.home() / _COMPLETION_RELDIR
COMPLETION_BASENAME: Final[str] = "my-kitty-completion.{shell}"
COMPLETION_PROG: Final[str] = "my-kitty"


class CompletionShell(enum.StrEnum):
    """Shells we generate a completion script for.

    argcomplete's own ``--shell`` choices, narrowed to the two shells whose rc file
    ``path_integration`` edits.
    """

    BASH = "bash"
    ZSH = "zsh"


@dataclasses.dataclass(frozen=True, slots=True)
class InstallReport:
    """Outcome of an :func:`install` call."""

    kitty_app_dir: Path
    symlink: Path
    desktop_entry: Path
    version: str
    skipped_kitty_install: bool
    config_result: config_updater.InstallResult
    scenes_seeded: int = 0
    scenes_kept: int = 0


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


def _scenes_source() -> Path:
    """Resolve the bundled example-scenes directory.

    Wheel install: hatch force-includes ``examples/scenes`` as
    ``kitty_setup/_scenes`` next to this module. Editable ``uv sync``: the
    bundled dir is absent — fall back to the repo-root ``examples/scenes/``.
    Mirrors :func:`_payload_source`.
    """
    bundled = Path(__file__).resolve().parent / "_scenes"
    if bundled.is_dir():
        return bundled
    return _repo_root() / "examples" / "scenes"


def seed_scenes() -> tuple[int, int]:
    """Copy bundled example recipes into the user scenes dir, copy-if-absent.

    Each bundled ``*.toml`` is copied only when a file of that name does not
    already exist in ``scenes_dir()`` — an existing (possibly user-edited) file
    is NEVER overwritten. The directory is created if missing. Returns
    ``(seeded, kept)``: how many recipes were newly copied vs left untouched.
    Idempotent. Seeded files become user data; uninstall never removes them.
    """
    # Local import avoids a load-time cycle (recipe imports from scenes.launcher).
    from kitty_setup.scenes.recipe import scenes_dir

    source = _scenes_source()
    target = scenes_dir()
    if not source.is_dir():
        return (0, 0)
    target.mkdir(parents=True, exist_ok=True)
    seeded = kept = 0
    for recipe in sorted(source.glob("*.toml")):
        dest = target / recipe.name
        if dest.exists():
            kept += 1
            continue
        shutil.copy(recipe, dest)
        seeded += 1
    return (seeded, kept)


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

    scenes_seeded, scenes_kept = seed_scenes()

    return InstallReport(
        kitty_app_dir=dest / KITTY_APP_DIRNAME,
        symlink=SYMLINK_PATH,
        desktop_entry=DESKTOP_PATH,
        version=version,
        skipped_kitty_install=skipped,
        config_result=config_result,
        scenes_seeded=scenes_seeded,
        scenes_kept=scenes_kept,
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


def _completion_dir(home: Path | None) -> Path:
    return COMPLETION_DIR if home is None else home / _COMPLETION_RELDIR


def completion_script_path(shell: str, *, home: Path | None = None) -> Path:
    """Where the completion script for ``shell`` lives. Pure path arithmetic, no I/O.

    Raises :class:`ValueError` for a shell that is not a :class:`CompletionShell`,
    because no script is ever written for it.
    """
    member = CompletionShell(shell)
    return _completion_dir(home) / COMPLETION_BASENAME.format(shell=member.value)


def generate_completion_script(shell: str) -> str:
    """Return the completion shellcode for ``my-kitty``, generated in-process.

    Deliberately not ``register-python-argcomplete``: ``uv tool install`` exposes only
    ``my-kitty``, so that helper is never on PATH (D-02). The in-process call runs in the
    interpreter that owns ``argcomplete`` and cannot be substituted by a PATH entry. The
    output names no subcommand (U-3): its currency is a byte match against a fresh call.
    """
    member = CompletionShell(shell)
    return _ARGCOMPLETE_SHELLCODE([COMPLETION_PROG], shell=member.value)


def write_completion_script(shell: str | None, *, home: Path | None = None) -> Path | None:
    """Write the completion script for ``shell`` and return its path.

    Returns ``None`` and creates nothing when ``shell`` is ``None`` or unsupported —
    a bash script a fish user never reads is not written. Idempotent.
    """
    if shell is None or shell not in {member.value for member in CompletionShell}:
        return None
    path = completion_script_path(shell, home=home)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(generate_completion_script(shell), encoding="utf-8")
    return path


def remove_completion_script(*, home: Path | None = None) -> list[Path]:
    """Delete every per-shell completion script we own; return the paths removed.

    The directory is removed only when it is left empty — never recursively, since a
    user may keep something else there.
    """
    removed: list[Path] = []
    for member in CompletionShell:
        path = completion_script_path(member.value, home=home)
        if path.is_file() or path.is_symlink():
            path.unlink(missing_ok=True)
            removed.append(path)
    directory = _completion_dir(home)
    if directory.is_dir() and not any(directory.iterdir()):
        directory.rmdir()
    return removed


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
    print(f"scenes:        seeded {report.scenes_seeded}, " f"kept {report.scenes_kept} existing")


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


def _print_completion_result(shell: str | None, written: Path | None) -> None:
    if written is None:
        print(f"completion:    shell {shell or '<unknown>'} not supported; no script written")
    else:
        print(f"completion:    wrote {written}")


LEGACY_BINARY_PATH: Final[Path] = Path.home() / ".local" / "bin" / "my-kitty-setup"


def _print_legacy_shim_notice() -> None:
    """Print the upgrade notice when the pre-rename binary is still on disk.

    Per design D3 of rename-cli-to-my-kitty: detect, print, do NOT auto-remove
    (mirrors the print-don't-execute pattern from consolidate D2).
    """
    if LEGACY_BINARY_PATH.is_file() or LEGACY_BINARY_PATH.is_symlink():
        print(
            f"legacy:        {LEGACY_BINARY_PATH} detected; remove it with:\n"
            f"                   uv tool uninstall my-kitty-setup"
        )


def cli_install(args: argparse.Namespace) -> int:
    """Handler for ``my-kitty install``."""
    try:
        report = install(dest=args.dest, inject_config=not args.no_config)
    except (subprocess.CalledProcessError, OSError, config_updater.ConfigUpdaterError) as exc:
        print(f"install failed: {exc}", file=sys.stderr)
        return 1
    _print_install_report(report)
    path_result = path_integration.ensure_local_bin_in_path()
    _print_path_result(path_result)
    # The rc block is read only at the next shell start, so generating after the rc edit
    # within one install is sound; what matters is that both land in the same install.
    completion = write_completion_script(path_result.shell)
    _print_completion_result(path_result.shell, completion)
    _print_legacy_shim_notice()
    return 0


_SELF_REMOVAL_BANNER: Final[str] = (
    # probe-consolidate-into-my-kitty-setup-cli-04 confirmed `uv tool uninstall`
    # cleanly removes the entry shim + tool venv. We PRINT the command (do not
    # exec) per design D2 of consolidate: the running binary should not delete
    # its own files. Always-on after simplify-uninstall-defaults D2.
    "binary:        the my-kitty binary itself was NOT removed. To remove it:\n"
    "    uv tool uninstall my-kitty\n"
    "To remove the PATH block from your shell rc, delete the lines between:\n"
    "    # >>> my-kitty PATH >>>\n"
    "    # <<< my-kitty PATH <<<\n"
    "in ~/.zshrc or ~/.bashrc."
)


def cli_uninstall(args: argparse.Namespace) -> int:
    """Handler for ``my-kitty uninstall`` — remove everything by default.

    ``--keep-config`` preserves the entire ``~/.config/kitty/`` footprint we
    created (block + payload + backups). ``--keep-backups`` preserves only the
    backup files. ``--keep-kitty`` preserves kitty.app + symlink + desktop
    entry. Flags compose; the self-removal banner always prints.
    """
    do_config = not args.keep_config
    do_backups = not args.keep_config and not args.keep_backups
    do_kitty = not args.keep_kitty

    paths = config_updater.ConfigPaths.for_user()

    # Order matters: delete backups BEFORE stripping the block. If kitty.conf
    # contained only our block, config_updater.uninstall's restore-from-backup
    # branch will find no backups (correct — we just deleted them) and fall
    # through to deleting the empty file.
    if do_backups:
        backups = config_updater.list_backups(paths.conf_file)
        deleted = pruner.delete_each(backups)
        if backups:
            print(f"backups:       deleted {deleted} file(s) under {paths.kitty_dir}/")
        else:
            print(f"backups:       nothing to delete under {paths.kitty_dir}/")

    if do_config:
        cfg = config_updater.uninstall(paths)
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

    if do_kitty:
        kitty_report = remove_kitty_install()
        if kitty_report.app_dir_removed:
            print(f"kitty:         removed {kitty_report.app_dir}")
        else:
            print(f"kitty:         no {kitty_report.app_dir} to remove")
        if kitty_report.symlink_removed:
            print(f"kitty:         removed symlink {kitty_report.symlink}")
        if kitty_report.desktop_entry_removed:
            print(f"kitty:         removed desktop entry {kitty_report.desktop_entry}")

    # The completion script belongs to the *binary*, not to the ~/.config/kitty footprint, so
    # it is guarded by do_kitty: --keep-kitty is the only flag that preserves binary-adjacent
    # state, and `make clean` passes --keep-kitty --keep-backups (D-04) but not --keep-config.
    # Guarding by do_config would make the safe verb delete the completion of a binary that
    # survives. Its own step, not a line in remove_kitty_install(), whose name means kitty.app.
    if do_kitty:
        for path in remove_completion_script():
            print(f"completion:    removed {path}")

    print(_SELF_REMOVAL_BANNER)
    return 0

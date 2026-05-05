"""Sentinel-bracketed kitty.conf injection with backup, idempotency, and rollback.

Implements the kitty-config-management capability. The user's
``~/.config/kitty/kitty.conf`` is mutated only by inserting a single ``include``
directive between two sentinel comment lines. Our payload (the file referenced
by that include) lives entirely under ``~/.config/kitty/kitty-setup/``.
"""

from __future__ import annotations

import dataclasses
import datetime as _dt
import re
import shutil
import subprocess
from pathlib import Path
from typing import Final

MARKER_BEGIN: Final[str] = "# >>> kitty-setup managed (do not edit between markers) >>>"
MARKER_END: Final[str] = "# <<< kitty-setup managed <<<"
INCLUDE_LINE: Final[str] = "include kitty-setup/kitty-setup.conf"
BACKUP_SUFFIX_FMT: Final[str] = "%Y%m%dT%H%M%SZ"
# Strict pattern guarding prune from touching anything we did not write.
# See add-backup-pruning design D4 + risk #3 (no glob, exact regex).
BACKUP_NAME_RE: Final[re.Pattern[str]] = re.compile(r"^kitty\.conf\.bak\.\d{8}T\d{6}Z$")


@dataclasses.dataclass(frozen=True, slots=True)
class ConfigPaths:
    """Resolved paths for the user's kitty config layout."""

    kitty_dir: Path
    conf_file: Path
    payload_dir: Path
    payload_entry: Path

    @classmethod
    def for_user(cls, home: Path | None = None) -> ConfigPaths:
        """Resolve the standard ``~/.config/kitty`` layout for the current user."""
        base = (home or Path.home()) / ".config" / "kitty"
        return cls(
            kitty_dir=base,
            conf_file=base / "kitty.conf",
            payload_dir=base / "kitty-setup",
            payload_entry=base / "kitty-setup" / "kitty-setup.conf",
        )


@dataclasses.dataclass(frozen=True, slots=True)
class InstallResult:
    """Outcome of an :func:`install` call."""

    conf_file: Path
    payload_dir: Path
    backup_path: Path | None
    created_conf: bool
    updated_block: bool
    parse_ok: bool | None

    @property
    def changed(self) -> bool:
        return self.created_conf or self.updated_block


@dataclasses.dataclass(frozen=True, slots=True)
class UninstallResult:
    """Outcome of an :func:`uninstall` call."""

    conf_file: Path
    block_removed: bool
    payload_dir_removed: bool
    conf_restored_from: Path | None
    conf_deleted: bool


class ConfigUpdaterError(RuntimeError):
    """Raised on unrecoverable config-update failures (e.g. parse-check fail)."""


def _utc_timestamp(now: _dt.datetime | None = None) -> str:
    moment = now or _dt.datetime.now(_dt.UTC)
    return moment.strftime(BACKUP_SUFFIX_FMT)


def _block_text() -> str:
    return f"{MARKER_BEGIN}\n{INCLUDE_LINE}\n{MARKER_END}\n"


def _find_block(content: str) -> tuple[int, int] | None:
    """Return (start_line_idx, end_line_idx_exclusive) of the marker block, or None."""
    lines = content.splitlines(keepends=False)
    begin_idx: int | None = None
    for idx, line in enumerate(lines):
        stripped = line.rstrip()
        if stripped == MARKER_BEGIN:
            begin_idx = idx
        elif stripped == MARKER_END and begin_idx is not None:
            return begin_idx, idx + 1
    return None


def _has_correct_block(content: str) -> bool:
    bounds = _find_block(content)
    if bounds is None:
        return False
    start, end = bounds
    block_lines = content.splitlines(keepends=False)[start:end]
    expected = [MARKER_BEGIN, INCLUDE_LINE, MARKER_END]
    return [line.rstrip() for line in block_lines] == expected


def _is_content_empty(content: str) -> bool:
    """True when stripping comments and blank lines leaves nothing."""
    for raw in content.splitlines():
        stripped = raw.strip()
        if not stripped:
            continue
        if stripped.startswith("#"):
            continue
        return False
    return True


def _backup(conf_file: Path, *, now: _dt.datetime | None = None) -> Path:
    suffix = _utc_timestamp(now)
    backup = conf_file.with_name(f"{conf_file.name}.bak.{suffix}")
    shutil.copy2(conf_file, backup)
    return backup


def list_backups(conf_file: Path) -> list[Path]:
    """Return all valid `kitty.conf.bak.<UTC-ts>` files next to ``conf_file``.

    Sorted lexicographically (== chronological order, since the timestamp is
    embedded in the filename). Files in the same directory that do not match
    the strict :data:`BACKUP_NAME_RE` pattern are excluded — prune must never
    touch a file we did not write.
    """
    parent = conf_file.parent
    if not parent.is_dir():
        return []
    return sorted(p for p in parent.iterdir() if BACKUP_NAME_RE.match(p.name))


def _latest_backup(conf_file: Path) -> Path | None:
    backups = list_backups(conf_file)
    return backups[-1] if backups else None


_PARSE_SNIPPET: Final[str] = (
    "import sys\n"
    "from kitty.config import load_config\n"
    "bad = []\n"
    "load_config(sys.argv[-1], accumulate_bad_lines=bad)\n"
    "for b in bad:\n"
    "    sys.stderr.write(str(b) + '\\n')\n"
    "sys.exit(1 if bad else 0)\n"
)


def _parse_check(conf_file: Path, kitty_bin: str | Path) -> bool:
    """Validate ``conf_file`` via ``kitty +runpy`` (returns True iff no bad lines).

    Kitty 0.46+ does not expose a ``--debug-config`` flag; the equivalent
    introspection runs ``kitty.config.load_config`` and checks the
    ``accumulate_bad_lines`` collector. Exit code 0 means no malformed lines;
    non-zero means at least one was rejected.
    """
    try:
        result = subprocess.run(  # noqa: S603 — args are constructed from trusted paths
            [str(kitty_bin), "+runpy", _PARSE_SNIPPET, str(conf_file)],
            capture_output=True,
            text=True,
            check=False,
            timeout=15,
        )
    except FileNotFoundError as exc:
        raise ConfigUpdaterError(f"kitty binary not found at {kitty_bin}") from exc
    return result.returncode == 0


def install(
    paths: ConfigPaths,
    payload_source: Path,
    *,
    kitty_bin: str | Path | None = None,
    now: _dt.datetime | None = None,
) -> InstallResult:
    """Install our payload and inject the sentinel-bracketed include.

    ``payload_source`` is a directory whose contents are mirrored into
    ``paths.payload_dir`` (overwriting). The user's ``paths.conf_file`` is
    mutated only by appending the marker block when the block is missing or
    has drifted. A timestamped backup is created before any mutating write.

    When ``kitty_bin`` is provided the resulting ``conf_file`` is parsed with
    ``kitty --debug-config``; on a non-zero exit code the latest backup is
    restored and :class:`ConfigUpdaterError` is raised.
    """
    if not payload_source.is_dir():
        raise FileNotFoundError(f"payload source not a directory: {payload_source}")

    paths.kitty_dir.mkdir(parents=True, exist_ok=True)
    if paths.payload_dir.exists():
        shutil.rmtree(paths.payload_dir)
    shutil.copytree(payload_source, paths.payload_dir)

    conf = paths.conf_file
    backup_path: Path | None = None
    created_conf = False
    updated_block = False

    if not conf.exists():
        conf.write_text(_block_text(), encoding="utf-8")
        created_conf = True
    else:
        original = conf.read_text(encoding="utf-8")
        if _has_correct_block(original):
            new_content = original
        else:
            backup_path = _backup(conf, now=now)
            bounds = _find_block(original)
            if bounds is None:
                separator = "" if original.endswith("\n") or original == "" else "\n"
                new_content = f"{original}{separator}{_block_text()}"
            else:
                lines = original.splitlines(keepends=True)
                lines[bounds[0] : bounds[1]] = [
                    f"{MARKER_BEGIN}\n",
                    f"{INCLUDE_LINE}\n",
                    f"{MARKER_END}\n",
                ]
                new_content = "".join(lines)
            conf.write_text(new_content, encoding="utf-8")
            updated_block = True

    parse_ok: bool | None = None
    if kitty_bin is not None and (created_conf or updated_block):
        parse_ok = _parse_check(conf, kitty_bin)
        if not parse_ok:
            if backup_path is not None:
                shutil.copy2(backup_path, conf)
            elif created_conf:
                conf.unlink()
            raise ConfigUpdaterError(
                "kitty --debug-config rejected the mutated kitty.conf; rolled back"
            )

    return InstallResult(
        conf_file=conf,
        payload_dir=paths.payload_dir,
        backup_path=backup_path,
        created_conf=created_conf,
        updated_block=updated_block,
        parse_ok=parse_ok,
    )


def uninstall(paths: ConfigPaths) -> UninstallResult:
    """Remove the sentinel block and our payload directory.

    If stripping the block leaves the conf file with no non-blank, non-comment
    content, the file is replaced with the most recent backup if one exists,
    or deleted outright.
    """
    conf = paths.conf_file
    block_removed = False
    payload_dir_removed = False
    conf_restored_from: Path | None = None
    conf_deleted = False

    if conf.exists():
        original = conf.read_text(encoding="utf-8")
        bounds = _find_block(original)
        if bounds is not None:
            lines = original.splitlines(keepends=True)
            del lines[bounds[0] : bounds[1]]
            stripped_content = "".join(lines)
            if _is_content_empty(stripped_content):
                latest = _latest_backup(conf)
                if latest is not None:
                    shutil.copy2(latest, conf)
                    conf_restored_from = latest
                else:
                    conf.unlink()
                    conf_deleted = True
            else:
                conf.write_text(stripped_content, encoding="utf-8")
            block_removed = True

    if paths.payload_dir.exists():
        shutil.rmtree(paths.payload_dir)
        payload_dir_removed = True

    return UninstallResult(
        conf_file=conf,
        block_removed=block_removed,
        payload_dir_removed=payload_dir_removed,
        conf_restored_from=conf_restored_from,
        conf_deleted=conf_deleted,
    )


def is_block_present(paths: ConfigPaths) -> bool:
    """Status query: True iff the sentinel block is present in the user's kitty.conf."""
    if not paths.conf_file.exists():
        return False
    return _has_correct_block(paths.conf_file.read_text(encoding="utf-8"))

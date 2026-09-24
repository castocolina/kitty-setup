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
import shlex
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Final


def _select_clear_variant(payload_dir: Path) -> None:
    """Materialise ``clear.conf`` from the host-matching ``clear-*.conf`` variant.

    The repo carries ``clear-linux.conf`` and ``clear-mac.conf`` as full,
    self-contained variants of the instant-clear payload. The deployed
    ``kitty-setup.conf`` `include`s a single ``clear.conf``; this helper
    picks the matching variant, renames it to ``clear.conf``, and removes
    the other variant from the payload dir. See
    ``openspec/changes/phase1-curated-bindings-revert-defaults/notes/clear-chord-os-mechanism.md``
    for the rationale.

    No-op if neither variant exists (older payload layouts) or if
    ``clear.conf`` is already in place.
    """
    linux_variant = payload_dir / "clear-linux.conf"
    mac_variant = payload_dir / "clear-mac.conf"
    target = payload_dir / "clear.conf"

    if sys.platform == "darwin":
        chosen, other = mac_variant, linux_variant
    else:
        chosen, other = linux_variant, mac_variant

    if chosen.is_file():
        if target.exists():
            target.unlink()
        chosen.rename(target)
    if other.is_file():
        other.unlink()


MARKER_BEGIN: Final[str] = "# >>> kitty-setup managed (do not edit between markers) >>>"
MARKER_END: Final[str] = "# <<< kitty-setup managed <<<"
INCLUDE_LINE: Final[str] = "include kitty-setup/kitty-setup.conf"
BACKUP_SUFFIX_FMT: Final[str] = "%Y%m%dT%H%M%SZ"
# Strict pattern guarding prune from touching anything we did not write.
# See add-backup-pruning design D4 + risk #3 (no glob, exact regex).
BACKUP_NAME_RE: Final[re.Pattern[str]] = re.compile(r"^kitty\.conf\.bak\.\d{8}T\d{6}Z$")
# Suffix of the sibling the previous payload is renamed to while an install is in flight. A
# sibling of ``payload_dir`` shares its filesystem, so every rename between the two is atomic.
ROLLBACK_SUFFIX: Final[str] = ".rollback"


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


@dataclasses.dataclass(frozen=True, slots=True)
class ParseCheckResult:
    """Outcome of the config parse check.

    ``command`` is the complete, shell-quoted argv that ran — ``shlex.split(command)`` gives the
    argv back — so it can be copied and re-run. ``stderr`` is the parser's output, untouched: on a
    rejection it names the file, line and reason; on a pass it may still carry warnings, such as
    a missing ``include``, that do not fail the check.
    """

    ok: bool
    command: str
    stderr: str


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


# One line, so the command built from it is one copyable line and doctor keeps one line per check.
# The statements are the multi-line original's, joined with ``;``: ``print(b, file=sys.stderr)``
# writes ``str(b)`` plus a newline, the same bytes as ``sys.stderr.write(str(b) + '\n')``.
_PARSE_SNIPPET: Final[str] = (
    "import sys; "
    "from kitty.config import load_config; "
    "bad = []; "
    "load_config(sys.argv[-1], accumulate_bad_lines=bad); "
    "[print(b, file=sys.stderr) for b in bad]; "
    "sys.exit(1 if bad else 0)"
)


def _parse_check(conf_file: Path, kitty_bin: str | Path) -> ParseCheckResult:
    """Validate ``conf_file`` by loading it in kitty's own interpreter.

    Runs ``kitty +runpy`` with a snippet that calls ``kitty.config.load_config`` with an
    ``accumulate_bad_lines`` collector and exits non-zero when it collected anything. That
    collector only sees value-conversion failures: an unknown key, a malformed line or a missing
    ``include`` exits 0 and shows up on stderr only, which is why ``stderr`` is returned on a pass
    as well as on a rejection.
    """
    argv = [str(kitty_bin), "+runpy", _PARSE_SNIPPET, str(conf_file)]
    try:
        result = subprocess.run(  # noqa: S603 — args are constructed from trusted paths
            argv,
            capture_output=True,
            text=True,
            check=False,
            timeout=15,
        )
    except FileNotFoundError as exc:
        raise ConfigUpdaterError(f"kitty binary not found at {kitty_bin}") from exc
    return ParseCheckResult(
        ok=result.returncode == 0, command=shlex.join(argv), stderr=result.stderr
    )


def _rejection_message(check: ParseCheckResult) -> str:
    stderr = check.stderr.rstrip() or "(the parser wrote nothing to stderr)"
    return (
        "kitty's config parser rejected the mutated kitty.conf; kitty.conf was restored.\n"
        f"command: {check.command}\n"
        f"parser stderr:\n{stderr}"
    )


def _preserve_stale_aside(aside: Path, kitty_dir: Path, *, now: _dt.datetime | None) -> None:
    """Move an aside left behind by an interrupted install out of the way. Never delete it.

    An install interrupted between moving the previous payload aside and committing or restoring
    it (Ctrl-C, a kill, a power loss) leaves ``aside`` behind, and renaming a directory onto a
    non-empty one fails, so without this every later install would stop at the aside step. The
    aside is preserved rather than restored: :func:`install` always replaces the payload, so a
    restored aside would be moved aside again at once; no journal says which step was
    interrupted, and an interrupted commit leaves a partial aside that looks whole; and preserving
    needs no branch on whether the payload exists. The dated name sits beside the conf backups,
    on the same filesystem, and a taken name — anything that exists, since renaming onto an empty
    directory silently replaces it — gets the smallest free ``.N`` suffix instead. Neither
    ``prune`` nor ``uninstall`` touches the preserved copy; it is the user's to delete, which is
    why the one stderr line names it.
    """
    if not (aside.exists() or aside.is_symlink()):
        return
    base = kitty_dir / f"{aside.name}.{_utc_timestamp(now)}"
    destination = base
    suffix = 0
    while destination.exists() or destination.is_symlink():
        suffix += 1
        destination = base.with_name(f"{base.name}.{suffix}")
    try:
        aside.rename(destination)
    except OSError as exc:
        raise ConfigUpdaterError(
            f"a payload aside from an interrupted install is at {aside} and could not be moved "
            f"to {destination}: {exc}. Nothing was changed; move it out of the way by hand."
        ) from exc
    print(
        f"config: preserved a payload aside from an interrupted install at {destination}",
        file=sys.stderr,
    )


def _restore_payload(payload_dir: Path, aside: Path | None, failure: BaseException) -> None:
    """Undo a failed install's payload copy: remove the partial target, rename the aside back.

    Runs inside the ``except`` block that caught ``failure``, so anything raised here chains to
    it. With an aside, a failed step keeps the aside — the only copy of the previous payload —
    and raises :class:`ConfigUpdaterError` naming it and repeating ``failure``, so a parser's
    diagnosis is not lost behind the restore error. With no aside nothing of the user's is at
    risk, and the ``OSError`` propagates as is.
    """
    try:
        if payload_dir.exists():
            shutil.rmtree(payload_dir)
        if aside is not None:
            aside.rename(payload_dir)
    except OSError as exc:
        if aside is None:
            raise
        raise ConfigUpdaterError(
            f"install failed and the previous payload could not be put back: {exc}\n"
            f"The previous payload is kept, untouched, at {aside}; move it back to "
            f"{payload_dir} by hand.\n"
            f"Original failure ({type(failure).__name__}): {failure}"
        ) from exc


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

    When ``kitty_bin`` is provided the resulting ``conf_file`` is loaded by
    kitty's own config parser (see :func:`_parse_check`); on a rejection the
    latest backup is restored and :class:`ConfigUpdaterError` is raised, naming
    the command that ran and carrying the parser's stderr.

    The previous payload is never destroyed before the new one is accepted. It
    is renamed to a ``.rollback`` sibling first; the sibling is deleted only
    after the copy, the conf mutation and the parse check all succeed. On any
    failure of those — ``KeyboardInterrupt`` and ``SystemExit`` included — the
    partial payload is removed and the sibling renamed back.
    """
    if not payload_source.is_dir():
        raise FileNotFoundError(f"payload source not a directory: {payload_source}")

    paths.kitty_dir.mkdir(parents=True, exist_ok=True)
    aside = paths.payload_dir.with_name(paths.payload_dir.name + ROLLBACK_SUFFIX)
    _preserve_stale_aside(aside, paths.kitty_dir, now=now)
    previous = aside if paths.payload_dir.exists() else None
    if previous is not None:
        paths.payload_dir.rename(previous)
    try:
        shutil.copytree(payload_source, paths.payload_dir)
        _select_clear_variant(paths.payload_dir)
        result = _write_block_and_check(paths, kitty_bin=kitty_bin, now=now)
    except BaseException as exc:
        _restore_payload(paths.payload_dir, previous, exc)
        raise
    # Commit, outside the checked region: a failure here cannot roll back an accepted payload,
    # and the aside it leaves is the stale case the next install preserves and reports.
    if previous is not None:
        shutil.rmtree(previous)
    return result


def _write_block_and_check(
    paths: ConfigPaths, *, kitty_bin: str | Path | None, now: _dt.datetime | None
) -> InstallResult:
    """Inject the marker block into the conf, then parse-check it when it changed.

    On the parser's rejection the conf is restored (or the created conf deleted) *before*
    :class:`ConfigUpdaterError` is raised, so the payload rollback that follows never races it.
    """
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
        check = _parse_check(conf, kitty_bin)
        parse_ok = check.ok
        if not check.ok:
            if backup_path is not None:
                shutil.copy2(backup_path, conf)
            elif created_conf:
                conf.unlink()
            raise ConfigUpdaterError(_rejection_message(check))

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

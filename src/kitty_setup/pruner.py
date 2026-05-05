"""Prune accumulated ``kitty.conf.bak.<UTC-ts>`` backup files.

Backed by the ``my-kitty-setup prune`` subcommand. Three opt-in policies
(``--keep N`` / ``--older-than DAYS`` / ``--all``); default invocation is a
dry-run listing with no filesystem mutation. See the ``add-backup-pruning``
OpenSpec change for the full requirement set.
"""

from __future__ import annotations

import argparse
import datetime as _dt
from collections.abc import Iterable
from pathlib import Path

from kitty_setup import config_updater


def _describe(path: Path) -> tuple[str, _dt.datetime, int]:
    """Return (filename, mtime UTC, byte size) for a backup path."""
    stat = path.stat()
    mtime = _dt.datetime.fromtimestamp(stat.st_mtime, tz=_dt.UTC)
    return path.name, mtime, stat.st_size


def prune_by_keep(backups: list[Path], n: int) -> list[Path]:
    """Return the paths to delete when keeping the ``n`` most recent backups."""
    if n < 0:
        raise ValueError(f"--keep must be >= 0, got {n}")
    if n >= len(backups):
        return []
    return list(backups[: len(backups) - n])


def prune_by_age(backups: list[Path], days: int, now: _dt.datetime | None = None) -> list[Path]:
    """Return paths whose mtime is older than ``days`` days from ``now``."""
    if days < 0:
        raise ValueError(f"--older-than must be >= 0, got {days}")
    cutoff = (now or _dt.datetime.now(_dt.UTC)) - _dt.timedelta(days=days)
    cutoff_ts = cutoff.timestamp()
    return [p for p in backups if p.stat().st_mtime < cutoff_ts]


def prune_all(backups: list[Path]) -> list[Path]:
    """Return every backup path (most aggressive policy)."""
    return list(backups)


def delete_each(paths: Iterable[Path]) -> int:
    """Unlink each path; return count actually deleted.

    ``FileNotFoundError`` is swallowed so a concurrent prune (or a manual ``rm``
    between listing and deletion) does not crash the caller.
    """
    count = 0
    for p in paths:
        try:
            p.unlink()
            count += 1
        except FileNotFoundError:
            continue
    return count


def _format_listing(backups: list[Path]) -> tuple[list[str], int]:
    """Return (per-file lines, total byte size)."""
    lines: list[str] = []
    total = 0
    for path in backups:
        name, mtime, size = _describe(path)
        total += size
        lines.append(f"{name}  {mtime.isoformat(timespec='seconds')}  {size:>10,d} bytes")
    return lines, total


def _select_for_deletion(backups: list[Path], args: argparse.Namespace) -> list[Path]:
    if args.all:
        return prune_all(backups)
    if args.older_than is not None:
        return prune_by_age(backups, args.older_than)
    keep = args.keep if args.keep is not None else 3
    return prune_by_keep(backups, keep)


def _policy_summary(args: argparse.Namespace) -> str:
    if args.all:
        return "policy: --all"
    if args.older_than is not None:
        return f"policy: --older-than {args.older_than}"
    keep = args.keep if args.keep is not None else 3
    return f"policy: --keep {keep}"


def cli_prune(args: argparse.Namespace) -> int:
    """Handler for ``my-kitty-setup prune``."""
    paths = config_updater.ConfigPaths.for_user()
    backups = config_updater.list_backups(paths.conf_file)

    if not backups:
        print(f"no backups under {paths.kitty_dir}/")
        return 0

    lines, total = _format_listing(backups)

    if not args.backups:
        print(f"backups in {paths.kitty_dir}/ (dry run; pass --backups to delete):")
        for line in lines:
            print(f"  {line}")
        print(f"summary: {len(backups)} backup(s), {total:,d} bytes total")
        return 0

    to_delete = _select_for_deletion(backups, args)
    print(f"backups in {paths.kitty_dir}/ ({_policy_summary(args)}):")
    for backup in backups:
        marker = "DELETE" if backup in to_delete else "keep  "
        name, mtime, size = _describe(backup)
        print(f"  {marker}  {name}  {mtime.isoformat(timespec='seconds')}  {size:>10,d}")

    deleted = delete_each(to_delete)
    surviving = len(backups) - deleted
    print(f"summary: deleted {deleted} of {len(backups)} backup(s); " f"{surviving} remaining")
    return 0

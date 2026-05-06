"""Single binary, subcommand-dispatched CLI for kitty-setup.

Owned by the ``my-kitty`` entry point declared in ``pyproject.toml``.
Subparsers route to handlers defined in their respective modules:

* ``install``   → :func:`kitty_setup.installer.cli_install`
* ``uninstall`` → :func:`kitty_setup.installer.cli_uninstall`
* ``doctor``    → :func:`kitty_setup.doctor.cli_doctor`
* ``prune``     → :func:`kitty_setup.pruner.cli_prune`
* ``help``      → top-level help, identical to ``--help``

Per design D4: argparse subparsers, no Click. Per spec: this is the ONLY entry
point under ``[project.scripts]``.
"""

from __future__ import annotations

import argparse
import sys
from collections.abc import Callable
from pathlib import Path

from kitty_setup import binding_introspection, doctor, installer, pruner

PROG: str = "my-kitty"

Handler = Callable[[argparse.Namespace], int]


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog=PROG,
        description="Install, uninstall, and diagnose the kitty-setup foundation.",
    )
    sub = parser.add_subparsers(dest="command", metavar="<command>")

    p_install = sub.add_parser(
        "install",
        help="install kitty + inject config + ensure ~/.local/bin on PATH",
    )
    p_install.add_argument(
        "--no-config",
        action="store_true",
        help="install kitty but skip config injection",
    )
    p_install.add_argument(
        "--dest",
        type=Path,
        default=installer.DEFAULT_DEST,
        help=f"per-user install prefix (default: {installer.DEFAULT_DEST})",
    )
    p_install.set_defaults(func=installer.cli_install)

    p_uninstall = sub.add_parser(
        "uninstall",
        help="remove our entire footprint (default); --keep-* flags preserve subsets",
        description=(
            "Remove our entire footprint by default. Use --keep-* flags to preserve "
            "specific subsets. The my-kitty binary itself is never removed; the "
            "manual `uv tool uninstall my-kitty` command is always printed at the end."
        ),
    )
    p_uninstall.add_argument(
        "--keep-backups",
        dest="keep_backups",
        action="store_true",
        help="preserve every kitty.conf.bak.* file under ~/.config/kitty/",
    )
    p_uninstall.add_argument(
        "--keep-config",
        dest="keep_config",
        action="store_true",
        help="preserve the entire ~/.config/kitty/ footprint (block + payload + backups)",
    )
    p_uninstall.add_argument(
        "--keep-kitty",
        dest="keep_kitty",
        action="store_true",
        help="preserve ~/.local/kitty.app, the kitty symlink, and the desktop entry",
    )
    p_uninstall.set_defaults(func=installer.cli_uninstall)

    p_doctor = sub.add_parser("doctor", help="diagnose install + config-include health")
    p_doctor.set_defaults(func=doctor.cli_doctor)

    p_prune = sub.add_parser(
        "prune",
        help="list / delete accumulated kitty.conf.bak.* backups (opt-in)",
        description=(
            "List or delete accumulated kitty.conf.bak.* files. Without --backups, "
            "only lists (dry run). With --backups, applies one of three policies "
            "(--keep / --older-than / --all). NOTE: pruning --all immediately before "
            "an install reduces rollback safety to the same-process backup."
        ),
    )
    p_prune.add_argument(
        "--backups",
        action="store_true",
        help="actually delete backup files (without this flag the command only lists)",
    )
    policy = p_prune.add_mutually_exclusive_group()
    policy.add_argument(
        "--keep",
        type=int,
        default=None,
        metavar="N",
        help="keep the N most recent backups (default 3 when --backups is passed alone)",
    )
    policy.add_argument(
        "--older-than",
        dest="older_than",
        type=int,
        default=None,
        metavar="DAYS",
        help="delete backups whose mtime is older than DAYS days",
    )
    policy.add_argument(
        "--all",
        action="store_true",
        help="delete every backup file (most aggressive)",
    )
    p_prune.set_defaults(func=pruner.cli_prune)

    p_keys = sub.add_parser(
        "keys",
        help="list active key bindings, grouped by source, with conflicts flagged",
        description=(
            "Enumerate every chord active in the parsed kitty config. Groups "
            "bindings by source file (windowing, bindings, etc., plus a "
            "kitty defaults bucket). Annotates intentional overrides and flags "
            "real conflicts."
        ),
    )
    p_keys.add_argument(
        "--json",
        action="store_true",
        help="emit machine-readable JSON instead of grouped plain text",
    )
    p_keys.add_argument(
        "--config-path",
        dest="config_path",
        default=None,
        help="path to the kitty config file to load (default: ~/.config/kitty/kitty.conf)",
    )
    p_keys.set_defaults(func=binding_introspection.cli_keys)

    def _help_handler(_args: argparse.Namespace) -> int:
        parser.print_help()
        return 0

    p_help = sub.add_parser("help", help="print this help banner")
    p_help.set_defaults(func=_help_handler)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)
    func: Handler | None = getattr(args, "func", None)
    if func is None:
        parser.print_help()
        return 0
    return func(args)


if __name__ == "__main__":
    sys.exit(main())

"""Single binary, subcommand-dispatched CLI for kitty-setup.

Owned by the ``my-kitty-setup`` entry point declared in ``pyproject.toml``.
Subparsers route to handlers defined in their respective modules:

* ``install``   → :func:`kitty_setup.installer.cli_install`
* ``uninstall`` → :func:`kitty_setup.installer.cli_uninstall`
* ``doctor``    → :func:`kitty_setup.doctor.cli_doctor`
* ``help``      → top-level help, identical to ``--help``

Per design D4: argparse subparsers, no Click. Per spec: this is the ONLY entry
point under ``[project.scripts]``.
"""

from __future__ import annotations

import argparse
import sys
from collections.abc import Callable
from pathlib import Path

from kitty_setup import doctor, installer

PROG: str = "my-kitty-setup"

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
        help="strip our config block (default) + optional --kitty / --self",
    )
    p_uninstall.add_argument(
        "--kitty",
        action="store_true",
        help="also remove ~/.local/kitty.app, the kitty symlink, and the desktop entry",
    )
    p_uninstall.add_argument(
        "--self",
        dest="self_",
        action="store_true",
        help="print (do NOT execute) the manual self-removal command and PATH cleanup",
    )
    p_uninstall.set_defaults(func=installer.cli_uninstall)

    p_doctor = sub.add_parser("doctor", help="diagnose install + config-include health")
    p_doctor.set_defaults(func=doctor.cli_doctor)

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

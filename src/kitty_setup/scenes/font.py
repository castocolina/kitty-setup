"""Scene primitive: set OS-window font size via `kitten @ set-font-size`.

Phase 2 §10 of docs/requirements.md. OS-window scoped because kitty's
architecture binds font size to the OS window (``kitten @ set-font-size --help``:
"in kitty all sub-windows in the same OS window must have the same font size").
Value is passed verbatim — kitten accepts absolute (``14``), relative
(``+2``, ``-2``, ``*1.1``, ``/2``), and reset (``0``).
"""

from __future__ import annotations

import argparse
import sys

from kitty_setup.scenes import _client
from kitty_setup.scenes._client import SceneClientError


def set_os_window_font_size(
    value: str,
    *,
    all_: bool = False,
    to: str | None = None,
) -> int:
    """Set OS-window font size; return kitten's exit code."""
    args: list[str] = []
    if all_:
        args.append("--all")
    args.append(value)
    result = _client.kitten_at("set-font-size", *args, to=to)
    if result.returncode != 0:
        sys.stderr.write(result.stderr)
    return result.returncode


def cli_set_os_window_font_size(args: argparse.Namespace) -> int:
    """CLI handler for ``my-kitty os-window font-size``."""
    try:
        return set_os_window_font_size(
            args.value,
            all_=args.all,
            to=args.to,
        )
    except SceneClientError as exc:
        sys.stderr.write(f"{exc}\n")
        return 1

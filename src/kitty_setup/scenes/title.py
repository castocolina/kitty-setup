"""Scene primitive: set kitty window/tab titles via the remote-control socket.

Phase 2 §8 of docs/requirements.md. Two callables, one per noun:

* :func:`set_window_title` — `kitten @ set-window-title`, default `--temporary` ON
  (programs running inside the window may override via OSC-2).
* :func:`set_tab_title` — `kitten @ set-tab-title`, always permanent (kitten
  exposes no ``--temporary`` flag for tabs; OSC-2 escapes do not route to tab
  titles anyway).

CLI handler wrappers ``cli_set_window_title`` / ``cli_set_tab_title`` are
exported for ``cli.py`` to register via ``set_defaults(func=…)``.
"""

from __future__ import annotations

import argparse
import sys

from kitty_setup.scenes import _client
from kitty_setup.scenes._client import SceneClientError


def set_window_title(
    text: str,
    *,
    temporary: bool = True,
    match: str | None = None,
    to: str | None = None,
) -> int:
    """Set the kitty window title; return kitten's exit code."""
    args: list[str] = []
    if temporary:
        args.append("--temporary")
    if match is not None:
        args.extend(("--match", match))
    args.append(text)
    result = _client.kitten_at("set-window-title", *args, to=to)
    if result.returncode != 0:
        sys.stderr.write(result.stderr)
    return result.returncode


def set_tab_title(
    text: str,
    *,
    match: str | None = None,
    to: str | None = None,
) -> int:
    """Set the kitty tab title; return kitten's exit code.

    No ``temporary`` parameter — ``kitten @ set-tab-title`` does not expose
    a ``--temporary`` flag, and OSC-2 escapes from programs inside the tab
    do not affect tab titles. Tabs always stick.
    """
    args: list[str] = []
    if match is not None:
        args.extend(("--match", match))
    args.append(text)
    result = _client.kitten_at("set-tab-title", *args, to=to)
    if result.returncode != 0:
        sys.stderr.write(result.stderr)
    return result.returncode


def cli_set_window_title(args: argparse.Namespace) -> int:
    """CLI handler for ``my-kitty window title``."""
    try:
        return set_window_title(
            args.text,
            temporary=args.temporary,
            match=args.match,
            to=args.to,
        )
    except SceneClientError as exc:
        sys.stderr.write(f"{exc}\n")
        return 1


def cli_set_tab_title(args: argparse.Namespace) -> int:
    """CLI handler for ``my-kitty tab title``."""
    try:
        return set_tab_title(
            args.text,
            match=args.match,
            to=args.to,
        )
    except SceneClientError as exc:
        sys.stderr.write(f"{exc}\n")
        return 1

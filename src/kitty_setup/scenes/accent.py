"""Scene primitive: set kitty tab accent color via `kitten @ set-tab-color`.

Phase 2 §9 of docs/requirements.md. A single user-supplied color satisfies the
focused-AND-unfocused invariant by setting `active_bg` and `inactive_bg` to
the same value in one kitten call.
"""

from __future__ import annotations

import argparse
import sys

from kitty_setup.scenes import _client
from kitty_setup.scenes._client import SceneClientError


def set_tab_accent(
    color: str,
    *,
    active_fg: str | None = None,
    inactive_fg: str | None = None,
    match: str | None = None,
    to: str | None = None,
) -> int:
    """Set tab accent (active_bg + inactive_bg); return kitten's exit code."""
    args: list[str] = []
    if match is not None:
        args.extend(("--match", match))
    args.append(f"active_bg={color}")
    args.append(f"inactive_bg={color}")
    if active_fg is not None:
        args.append(f"active_fg={active_fg}")
    if inactive_fg is not None:
        args.append(f"inactive_fg={inactive_fg}")
    result = _client.kitten_at("set-tab-color", *args, to=to)
    if result.returncode != 0:
        sys.stderr.write(result.stderr)
    return result.returncode


def cli_set_tab_accent(args: argparse.Namespace) -> int:
    """CLI handler for ``my-kitty tab accent``."""
    try:
        return set_tab_accent(
            args.color,
            active_fg=args.active_fg,
            inactive_fg=args.inactive_fg,
            match=args.match,
            to=args.to,
        )
    except SceneClientError as exc:
        sys.stderr.write(f"{exc}\n")
        return 1

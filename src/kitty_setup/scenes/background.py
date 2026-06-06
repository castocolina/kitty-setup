"""Scene primitive: set per-pane background via `kitten @ set-colors`.

Phase 2 §10 of docs/requirements.md. Scoped to a single kitty sub-window (pane);
the default selector is the active window. Probe-verified pane isolation: pane A
bg = #001a33, pane B bg = #000000 after a single matched call.
"""

from __future__ import annotations

import argparse
import sys

from kitty_setup.scenes import _client
from kitty_setup.scenes._client import SceneClientError
from kitty_setup.scenes.colors import ColorError, normalize_color


def set_window_background(
    color: str,
    *,
    match: str | None = None,
    to: str | None = None,
) -> int:
    """Set pane background; return kitten's exit code.

    The color is normalized client-side (:func:`.colors.normalize_color`)
    before the kitten call; an unrecognized value raises
    :class:`.colors.ColorError` and makes no kitten call.
    """
    color = normalize_color(color) or color
    args: list[str] = []
    if match is not None:
        args.extend(("--match", match))
    args.append(f"background={color}")
    result = _client.kitten_at("set-colors", *args, to=to)
    if result.returncode != 0:
        sys.stderr.write(result.stderr)
    return result.returncode


def cli_set_window_background(args: argparse.Namespace) -> int:
    """CLI handler for ``my-kitty window background``."""
    try:
        return set_window_background(
            args.color,
            match=args.match,
            to=args.to,
        )
    except ColorError as exc:
        sys.stderr.write(f"my-kitty window background: {exc}\n")
        return 1
    except SceneClientError as exc:
        sys.stderr.write(f"{exc}\n")
        return 1

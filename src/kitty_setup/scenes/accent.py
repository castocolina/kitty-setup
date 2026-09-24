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
from kitty_setup.scenes.colors import ColorError, normalize_color


def set_tab_accent(
    color: str | None,
    *,
    active_fg: str | None = None,
    inactive_fg: str | None = None,
    match: str | None = None,
    to: str | None = None,
) -> int:
    """Set tab accent (active_bg + inactive_bg); return kitten's exit code.

    The color and the optional fg overrides are normalized client-side
    (:func:`.colors.normalize_color`) before the kitten call; an unrecognized
    value raises :class:`.colors.ColorError` and makes no kitten call. An
    absent value (``None``, empty or whitespace-only) emits no argument: an
    absent color omits ``active_bg``/``inactive_bg`` but keeps the fg
    overrides, and when nothing at all is left to set no kitten call is made
    and 0 is returned.
    """
    normalized = normalize_color(color)
    active_fg = normalize_color(active_fg)
    inactive_fg = normalize_color(inactive_fg)
    # An absent color contributes no bg arguments; the fg overrides still apply.
    settings: list[str] = (
        [] if normalized is None else [f"active_bg={normalized}", f"inactive_bg={normalized}"]
    )
    if active_fg is not None:
        settings.append(f"active_fg={active_fg}")
    if inactive_fg is not None:
        settings.append(f"inactive_fg={inactive_fg}")
    if not settings:
        return 0
    args: list[str] = []
    if match is not None:
        args.extend(("--match", match))
    args.extend(settings)
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
    except ColorError as exc:
        sys.stderr.write(f"my-kitty tab accent: {exc}\n")
        return 1
    except SceneClientError as exc:
        sys.stderr.write(f"{exc}\n")
        return 1

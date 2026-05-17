"""Scene primitive: set OS-window background opacity via `kitten @ set-background-opacity`.

Phase 2 §10 of docs/requirements.md. OS-window scoped because kitty's
architecture binds opacity to the OS window (``kitten @ set-background-opacity
--help``: "the background opacity affects all kitty windows in a single OS
window"). Precondition: ``dynamic_background_opacity yes`` must be set in the
kitty config — shipped by this change as `config/kitty/dynamic-opacity.conf`.
"""

from __future__ import annotations

import argparse
import sys

from kitty_setup.scenes import _client
from kitty_setup.scenes._client import SceneClientError


def set_os_window_opacity(
    value: float,
    *,
    toggle: bool = False,
    all_: bool = False,
    to: str | None = None,
) -> int:
    """Set OS-window opacity; return kitten's exit code.

    Implementation invariant (D3, probe-grounded): when ``toggle`` is true, the
    kitten argv MUST be ``["--toggle", "<value>"]`` — flag BEFORE positional.
    The reverse order fails with ``"Must specify exactly 1 argument(s)"``
    because kitten consumes the positional first and treats trailing
    ``--toggle`` as a stray arg.
    """
    args: list[str] = []
    if toggle:
        args.append("--toggle")
    if all_:
        args.append("--all")
    args.append(str(value))
    result = _client.kitten_at("set-background-opacity", *args, to=to)
    if result.returncode != 0:
        sys.stderr.write(result.stderr)
    return result.returncode


def cli_set_os_window_opacity(args: argparse.Namespace) -> int:
    """CLI handler for ``my-kitty os-window opacity``."""
    try:
        return set_os_window_opacity(
            args.value,
            toggle=args.toggle,
            all_=args.all,
            to=args.to,
        )
    except SceneClientError as exc:
        sys.stderr.write(f"{exc}\n")
        return 1

"""Smoke-test entry point for the kitty test harness.

Boots a single :class:`~kitty_setup.harness.kitty_session.KittySession`,
calls ``ls()``, prints the parsed structure, and exits 0 on success. Used by
``make doctor`` (eventually) and by ``tmp/h0b-harness/`` as a hand probe.
"""

from __future__ import annotations

import json
import sys

from kitty_setup.harness.kitty_session import (
    HarnessCommandError,
    HarnessStartupError,
    KittySession,
)


def main(argv: list[str] | None = None) -> int:
    """CLI entry point for ``kitty-setup-harness``."""
    del argv
    try:
        with KittySession() as session:
            print(json.dumps(session.ls(), indent=2))
    except (HarnessStartupError, HarnessCommandError) as exc:
        print(f"harness failed: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())

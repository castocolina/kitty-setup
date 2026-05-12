"""Shared helpers for integration tests.

Kept out of conftest because conftest contains pytest fixtures + the
KITTI_INTEGRATION gate, and we want callable helpers importable from
test modules without fixture indirection.
"""

from __future__ import annotations

import shutil
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
PAYLOAD_SOURCE = REPO_ROOT / "config" / "kitty"


def clear_variant_name() -> str:
    """Return the OS-matching ``clear-*.conf`` basename in the repo's payload source.

    The repo carries two self-contained variants (``clear-linux.conf`` /
    ``clear-mac.conf``); the installer picks one and renames it to
    ``clear.conf`` at install time. Tests need the same mapping.
    """
    return "clear-mac.conf" if sys.platform == "darwin" else "clear-linux.conf"


def copy_clear_payload(dest_dir: Path) -> Path:
    """Copy the OS-matching ``clear-*.conf`` source into ``dest_dir/clear.conf``.

    Mirrors the installer's `_select_clear_variant` step for test scratch
    directories. Returns the destination path.
    """
    src = PAYLOAD_SOURCE / clear_variant_name()
    dst = dest_dir / "clear.conf"
    shutil.copy(src, dst)
    return dst

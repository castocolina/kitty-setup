"""Sentinel-bracketed PATH editor for the user's shell rc file.

Mirrors the kitty.conf injection pattern: detect ``$SHELL``, pick the right rc
file (``~/.zshrc`` for zsh, ``~/.bashrc`` for bash), and append a sentinel-
bracketed ``export PATH`` line iff ``~/.local/bin`` is not already on PATH.

Idempotent: re-runs detect either our block or any user-authored ``export PATH``
that already mentions ``~/.local/bin`` (and the current process env) and skip
the write.
"""

from __future__ import annotations

import dataclasses
import os
import re
from pathlib import Path
from typing import Final

MARKER_BEGIN: Final[str] = "# >>> my-kitty-setup PATH >>>"
MARKER_END: Final[str] = "# <<< my-kitty-setup PATH <<<"
EXPORT_LINE: Final[str] = 'export PATH="$HOME/.local/bin:$PATH"'
TARGET_DIR_REL: Final[str] = ".local/bin"

_RC_BY_SHELL: Final[dict[str, str]] = {
    "zsh": ".zshrc",
    "bash": ".bashrc",
}


@dataclasses.dataclass(frozen=True, slots=True)
class PathEditResult:
    """Outcome of an :func:`ensure_local_bin_in_path` call."""

    changed: bool
    skipped: bool
    rc_file: Path | None
    shell: str | None
    reason: str
    manual_line: str = EXPORT_LINE


def _block_text() -> str:
    return f"{MARKER_BEGIN}\n{EXPORT_LINE}\n{MARKER_END}\n"


def _detect_shell(explicit: str | None, env_shell: str | None) -> str | None:
    if explicit is not None:
        return explicit
    if env_shell is None:
        return None
    return Path(env_shell).name or None


def _process_env_has_target(target: Path, env_path: str) -> bool:
    try:
        target_resolved = target.resolve()
    except OSError:
        target_resolved = target
    for entry in env_path.split(os.pathsep):
        if not entry:
            continue
        candidate = Path(entry)
        try:
            candidate_resolved = candidate.resolve()
        except OSError:
            candidate_resolved = candidate
        if candidate_resolved == target_resolved or str(candidate) == str(target):
            return True
        if str(candidate) == f"~/{TARGET_DIR_REL}":
            return True
    return False


_PATH_LINE_RE: Final[re.Pattern[str]] = re.compile(r"^\s*export\s+PATH\s*=", re.MULTILINE)


def _rc_already_exports_target(rc_text: str, target: Path) -> bool:
    if MARKER_BEGIN in rc_text and MARKER_END in rc_text:
        return True
    target_str = str(target)
    home_rel = f"$HOME/{TARGET_DIR_REL}"
    tilde_rel = f"~/{TARGET_DIR_REL}"
    for match in _PATH_LINE_RE.finditer(rc_text):
        line_end = rc_text.find("\n", match.start())
        line = rc_text[match.start() : line_end if line_end != -1 else len(rc_text)]
        if home_rel in line or tilde_rel in line or target_str in line:
            return True
    return False


def ensure_local_bin_in_path(
    home: Path | None = None,
    shell: str | None = None,
    env_path: str | None = None,
) -> PathEditResult:
    """Append the sentinel-bracketed PATH block to the user's shell rc if missing."""
    home_dir = home or Path.home()
    target = home_dir / TARGET_DIR_REL
    detected_shell = _detect_shell(shell, os.environ.get("SHELL"))
    rc_basename = _RC_BY_SHELL.get(detected_shell or "")

    if rc_basename is None:
        return PathEditResult(
            changed=False,
            skipped=True,
            rc_file=None,
            shell=detected_shell,
            reason=f"unsupported shell: {detected_shell or '<unknown>'}",
        )

    rc_file = home_dir / rc_basename
    current_env_path = env_path if env_path is not None else os.environ.get("PATH", "")

    if _process_env_has_target(target, current_env_path):
        return PathEditResult(
            changed=False,
            skipped=False,
            rc_file=rc_file,
            shell=detected_shell,
            reason="already on $PATH in current environment",
        )

    if rc_file.is_file():
        rc_text = rc_file.read_text(encoding="utf-8")
        if _rc_already_exports_target(rc_text, target):
            return PathEditResult(
                changed=False,
                skipped=False,
                rc_file=rc_file,
                shell=detected_shell,
                reason="rc file already exports ~/.local/bin",
            )
        separator = "" if rc_text.endswith("\n") or rc_text == "" else "\n"
        new_text = f"{rc_text}{separator}{_block_text()}"
    else:
        new_text = _block_text()

    rc_file.parent.mkdir(parents=True, exist_ok=True)
    rc_file.write_text(new_text, encoding="utf-8")
    return PathEditResult(
        changed=True,
        skipped=False,
        rc_file=rc_file,
        shell=detected_shell,
        reason="appended sentinel-bracketed block",
    )

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
from pathlib import Path
from typing import Final

MARKER_BEGIN: Final[str] = "# >>> my-kitty PATH >>>"
MARKER_END: Final[str] = "# <<< my-kitty PATH <<<"
# Legacy markers from the pre-rename my-kitty-setup era. Recognised so an
# upgrade does not append a duplicate block. See rename-cli-to-my-kitty
# design D2 + the new "PATH block migration" requirement.
_LEGACY_MARKER_BEGIN: Final[str] = "# >>> my-kitty-setup PATH >>>"
_LEGACY_MARKER_END: Final[str] = "# <<< my-kitty-setup PATH <<<"
EXPORT_LINE: Final[str] = 'export PATH="$HOME/.local/bin:$PATH"'
COMPLETION_LINE: Final[str] = 'eval "$(register-python-argcomplete my-kitty)"'
COMPLETION_GUARD_BEGIN: Final[str] = (
    "if command -v register-python-argcomplete >/dev/null 2>&1; then"
)
COMPLETION_GUARD_END: Final[str] = "fi"
TARGET_DIR_REL: Final[str] = ".local/bin"

# Block body lines (between the sentinel markers). Render-replaced on every
# install; hosts running an older PATH-only block migrate in place to this
# shape (see add-shell-completion design D4).
_BLOCK_BODY_LINES: Final[tuple[str, ...]] = (
    EXPORT_LINE,
    COMPLETION_GUARD_BEGIN,
    f"    {COMPLETION_LINE}",
    COMPLETION_GUARD_END,
)

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
    body = "\n".join(_BLOCK_BODY_LINES)
    return f"{MARKER_BEGIN}\n{body}\n{MARKER_END}\n"


def _block_body_matches_template(rc_text: str, bounds: tuple[int, int]) -> bool:
    """True iff the block body between markers equals the current template."""
    lines = rc_text.splitlines(keepends=False)
    body = [line.rstrip() for line in lines[bounds[0] + 1 : bounds[1] - 1]]
    expected = [line.rstrip() for line in _BLOCK_BODY_LINES]
    return body == expected


def _detect_shell(explicit: str | None, env_shell: str | None) -> str | None:
    if explicit is not None:
        return explicit
    if env_shell is None:
        return None
    return Path(env_shell).name or None


def _find_block(rc_text: str, begin: str, end: str) -> tuple[int, int] | None:
    """Return (start_line_idx, end_line_idx_exclusive) for a marker block, or None."""
    lines = rc_text.splitlines(keepends=False)
    begin_idx: int | None = None
    for idx, line in enumerate(lines):
        stripped = line.rstrip()
        if stripped == begin:
            begin_idx = idx
        elif stripped == end and begin_idx is not None:
            return begin_idx, idx + 1
    return None


def _splice_lines(rc_text: str, start: int, end: int, replacement: list[str]) -> str:
    """Replace lines [start, end) in ``rc_text`` with ``replacement`` (no trailing newline)."""
    lines = rc_text.splitlines(keepends=True)
    has_final_newline = rc_text.endswith("\n") if rc_text else False
    new_lines = [
        *lines[:start],
        *(line + "\n" for line in replacement),
        *lines[end:],
    ]
    out = "".join(new_lines)
    if not has_final_newline and out.endswith("\n"):
        out = out[:-1]
    return out


def ensure_local_bin_in_path(
    home: Path | None = None,
    shell: str | None = None,
    env_path: str | None = None,  # kept for kwarg back-compat; no longer consulted
) -> PathEditResult:
    """Ensure the sentinel-bracketed block is present in the user's shell rc.

    Block carries two concerns: PATH export AND register-python-argcomplete
    eval. Short-circuiting on "PATH already on $PATH" or "user has manual
    export" would drop the completion line, so block injection is
    unconditional given a supported shell. Splice helpers find/replace by
    sentinel marker — user-authored PATH lines elsewhere in the rc are
    untouched.
    """
    home_dir = home or Path.home()
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

    if rc_file.is_file():
        rc_text = rc_file.read_text(encoding="utf-8")
        new_block = _find_block(rc_text, MARKER_BEGIN, MARKER_END)
        legacy_block = _find_block(rc_text, _LEGACY_MARKER_BEGIN, _LEGACY_MARKER_END)

        if new_block is not None and legacy_block is not None:
            # Degenerate: both blocks present. Remove the legacy one.
            new_text = _splice_lines(rc_text, legacy_block[0], legacy_block[1], [])
            rc_file.write_text(new_text, encoding="utf-8")
            return PathEditResult(
                changed=True,
                skipped=False,
                rc_file=rc_file,
                shell=detected_shell,
                reason="removed duplicate legacy marker",
            )

        if new_block is None and legacy_block is not None:
            # Migration: rewrite the legacy marker lines in place with the
            # current block body (PATH export + completion eval guard).
            replacement = [MARKER_BEGIN, *_BLOCK_BODY_LINES, MARKER_END]
            new_text = _splice_lines(rc_text, legacy_block[0], legacy_block[1], replacement)
            rc_file.write_text(new_text, encoding="utf-8")
            return PathEditResult(
                changed=True,
                skipped=False,
                rc_file=rc_file,
                shell=detected_shell,
                reason="migrated legacy marker",
            )

        if new_block is not None:
            # Block exists with current markers. Short-circuit iff body matches
            # template; otherwise rewrite body in place (e.g. host on
            # PATH-only block migrating to PATH + completion).
            if _block_body_matches_template(rc_text, new_block):
                return PathEditResult(
                    changed=False,
                    skipped=False,
                    rc_file=rc_file,
                    shell=detected_shell,
                    reason="rc block already matches current template",
                )
            replacement = [MARKER_BEGIN, *_BLOCK_BODY_LINES, MARKER_END]
            new_text = _splice_lines(rc_text, new_block[0], new_block[1], replacement)
            rc_file.write_text(new_text, encoding="utf-8")
            return PathEditResult(
                changed=True,
                skipped=False,
                rc_file=rc_file,
                shell=detected_shell,
                reason="rewrote rc block body to current template",
            )

        # No block (new or legacy) in the rc; append a fresh one. Any
        # user-authored PATH lines elsewhere in the file are left untouched.
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

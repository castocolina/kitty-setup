"""Sentinel-bracketed PATH and completion block in the user's shell rc file.

Mirrors the kitty.conf injection pattern: detect ``$SHELL``, pick the right rc
file (``~/.zshrc`` for zsh, ``~/.bashrc`` for bash), and keep one sentinel-
bracketed block in it. The block exports ``~/.local/bin`` onto PATH and sources
the completion script ``installer`` generates (R1.1, D-01). Its body is a
function of the shell, because zsh needs ``compinit`` before ``compdef`` exists
and bash has neither.

In ``~/.zshrc`` the block must also be the last thing that runs: a ``compinit``
after it resets the registration. Install moves a zsh block to the end of the
file when anything but blanks or comments follows it; bash blocks are rewritten
in place. Idempotent: a block that already matches is left byte-identical.
"""

from __future__ import annotations

import dataclasses
import os
from pathlib import Path
from typing import Final

from kitty_setup import installer

# The names ``doctor`` and the tests share with install, so all three judge a block with the
# same functions. ``installer`` imports this module too; the cycle resolves because every use
# of an ``installer`` name here happens at call time, never at import time.
__all__ = [
    "EXPORT_LINE",
    "MARKER_BEGIN",
    "MARKER_END",
    "TARGET_DIR_REL",
    "ZSH_COMPINIT_LINE",
    "PathEditResult",
    "_block_body_lines",
    "_block_body_matches_template",
    "_block_followed_only_by_comments",
    "_block_text",
    "_find_block",
    "completion_source_line",
    "ensure_local_bin_in_path",
]

MARKER_BEGIN: Final[str] = "# >>> my-kitty PATH >>>"
MARKER_END: Final[str] = "# <<< my-kitty PATH <<<"
# Legacy markers from the pre-rename my-kitty-setup era. Recognised so an
# upgrade does not append a duplicate block. See rename-cli-to-my-kitty
# design D2 + the new "PATH block migration" requirement.
_LEGACY_MARKER_BEGIN: Final[str] = "# >>> my-kitty-setup PATH >>>"
_LEGACY_MARKER_END: Final[str] = "# <<< my-kitty-setup PATH <<<"
EXPORT_LINE: Final[str] = 'export PATH="$HOME/.local/bin:$PATH"'
# zsh only. Starts zsh's completion system when nothing before the block has, so ``compdef``
# exists. ``-i`` skips insecure completion directories instead of loading them (``-u`` would);
# no ``-D``, because without the dump file a shell start took 54.6 ms instead of 7.2 ms
# (measured 2026-09-24, see 02-02-PLAN.md).
ZSH_COMPINIT_LINE: Final[str] = (
    "(( $+functions[compdef] )) || { autoload -Uz compinit && compinit -i; }"
)
TARGET_DIR_REL: Final[str] = ".local/bin"
# The rc is text a user reads and may copy between machines, so the completion file is named
# through ``$HOME`` rather than the path resolved at install time.
_RC_HOME: Final[Path] = Path("$HOME")

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
    # What the user adds by hand when the shell is not handled (amended D-13, R1.7): the PATH
    # export and, for a shell we generate no completion for, a line saying so — never a
    # completion line in another shell's syntax.
    manual_lines: tuple[str, ...] = (EXPORT_LINE,)


def completion_source_line(shell: str) -> str:
    """The rc line that sources the completion script ``installer`` writes for ``shell``.

    bash sources it unguarded. zsh also requires ``compdef`` to be defined. Measured:
    ``command -v compdef`` exits 1 in bash, so the zsh guard would disable bash completion.
    """
    script = f'"{installer.completion_script_path(shell, home=_RC_HOME)}"'
    if shell == installer.CompletionShell.ZSH:
        return f"[ -f {script} ] && command -v compdef >/dev/null 2>&1 && . {script}"
    return f"[ -f {script} ] && . {script}"


def _block_body_lines(shell: str) -> tuple[str, ...]:
    """The lines between the markers for ``shell``, rendered on every install (D-01)."""
    if shell == installer.CompletionShell.ZSH:
        return (EXPORT_LINE, ZSH_COMPINIT_LINE, completion_source_line(shell))
    return (EXPORT_LINE, completion_source_line(shell))


def _block_lines(shell: str) -> list[str]:
    return [MARKER_BEGIN, *_block_body_lines(shell), MARKER_END]


def _block_text(shell: str) -> str:
    return "\n".join(_block_lines(shell)) + "\n"


def _block_body_matches_template(rc_text: str, bounds: tuple[int, int], shell: str) -> bool:
    """True iff the block body between markers equals the current template for ``shell``."""
    lines = rc_text.splitlines(keepends=False)
    body = [line.rstrip() for line in lines[bounds[0] + 1 : bounds[1] - 1]]
    expected = [line.rstrip() for line in _block_body_lines(shell)]
    return body == expected


def _block_followed_only_by_comments(rc_text: str, bounds: tuple[int, int]) -> bool:
    """True iff every line after the block's end marker is blank or a comment.

    For zsh this is what keeps the registration: a ``compinit`` that runs after the block —
    including one a sourced framework file runs, which no scan of the rc text can see —
    resets it.
    """
    trailing = rc_text.splitlines(keepends=False)[bounds[1] :]
    return all(not line.strip() or line.lstrip().startswith("#") for line in trailing)


def _needs_end_placement(rc_text: str, bounds: tuple[int, int], shell: str) -> bool:
    if shell != installer.CompletionShell.ZSH:
        return False
    return not _block_followed_only_by_comments(rc_text, bounds)


def _block_is_current(rc_text: str, bounds: tuple[int, int], shell: str) -> bool:
    if not _block_body_matches_template(rc_text, bounds, shell):
        return False
    return not _needs_end_placement(rc_text, bounds, shell)


def _append_block(rc_text: str, shell: str) -> str:
    separator = "" if rc_text.endswith("\n") or rc_text == "" else "\n"
    return f"{rc_text}{separator}{_block_text(shell)}"


def _render_block(rc_text: str, bounds: tuple[int, int], shell: str) -> str:
    """Replace the block at ``bounds`` with the current one for ``shell``.

    In place, except for a zsh block that something executable follows: its lines are
    removed and the block is appended at the end. Every line outside the block keeps its
    bytes and its relative order.
    """
    if _needs_end_placement(rc_text, bounds, shell):
        return _append_block(_splice_lines(rc_text, bounds[0], bounds[1], []), shell)
    return _splice_lines(rc_text, bounds[0], bounds[1], _block_lines(shell))


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
    """Ensure the sentinel-bracketed block is present and current in the user's shell rc.

    Block carries two concerns: the PATH export AND the line sourcing the
    generated completion script. Short-circuiting on "PATH already on $PATH" or
    "user has manual export" would drop the completion line, so block injection
    is unconditional given a supported shell. Splice helpers find/replace by
    sentinel marker — user-authored PATH lines elsewhere in the rc are
    untouched. A zsh block ends up last in the file (see the module docstring).
    """
    home_dir = home or Path.home()
    detected_shell = _detect_shell(shell, os.environ.get("SHELL"))
    rc_basename = _RC_BY_SHELL.get(detected_shell or "")

    if detected_shell is None or rc_basename is None:
        shell_name = detected_shell or "<unknown>"
        return PathEditResult(
            changed=False,
            skipped=True,
            rc_file=None,
            shell=detected_shell,
            reason=f"unsupported shell: {shell_name}",
            manual_lines=(
                EXPORT_LINE,
                f"# completion is not set up for {shell_name}: "
                "my-kitty generates completion for bash and zsh only",
            ),
        )

    rc_file = home_dir / rc_basename

    if rc_file.is_file():
        rc_text = rc_file.read_text(encoding="utf-8")
        new_block = _find_block(rc_text, MARKER_BEGIN, MARKER_END)
        legacy_block = _find_block(rc_text, _LEGACY_MARKER_BEGIN, _LEGACY_MARKER_END)

        if new_block is not None and legacy_block is not None:
            # Degenerate: both blocks present. Remove the legacy one, then put the retained
            # block through the same template check and placement as the single-block path
            # (H3), so an obsolete body cannot survive the upgrade. Re-find it: its lines
            # shift when the legacy block came first.
            new_text = _splice_lines(rc_text, legacy_block[0], legacy_block[1], [])
            retained = _find_block(new_text, MARKER_BEGIN, MARKER_END)
            if retained is not None and not _block_is_current(new_text, retained, detected_shell):
                new_text = _render_block(new_text, retained, detected_shell)
            rc_file.write_text(new_text, encoding="utf-8")
            return PathEditResult(
                changed=True,
                skipped=False,
                rc_file=rc_file,
                shell=detected_shell,
                reason="removed duplicate legacy marker",
            )

        if new_block is None and legacy_block is not None:
            # Migration: replace the legacy marker lines with the current block
            # (in place, or last for zsh when something executable follows).
            new_text = _render_block(rc_text, legacy_block, detected_shell)
            rc_file.write_text(new_text, encoding="utf-8")
            return PathEditResult(
                changed=True,
                skipped=False,
                rc_file=rc_file,
                shell=detected_shell,
                reason="migrated legacy marker",
            )

        if new_block is not None:
            # Block exists with current markers. Short-circuit iff the body matches the
            # template and, for zsh, nothing executable follows it. Otherwise rewrite it
            # (e.g. a host on an older body), moving a zsh block to the end of the file.
            if _block_is_current(rc_text, new_block, detected_shell):
                return PathEditResult(
                    changed=False,
                    skipped=False,
                    rc_file=rc_file,
                    shell=detected_shell,
                    reason="rc block already matches current template",
                )
            body_current = _block_body_matches_template(rc_text, new_block, detected_shell)
            new_text = _render_block(rc_text, new_block, detected_shell)
            rc_file.write_text(new_text, encoding="utf-8")
            if body_current:
                return PathEditResult(
                    changed=True,
                    skipped=False,
                    rc_file=rc_file,
                    shell=detected_shell,
                    reason="moved rc block to end of file",
                )
            return PathEditResult(
                changed=True,
                skipped=False,
                rc_file=rc_file,
                shell=detected_shell,
                reason="rewrote rc block body to current template",
            )

        # No block (new or legacy) in the rc; append a fresh one. Any
        # user-authored PATH lines elsewhere in the file are left untouched.
        new_text = _append_block(rc_text, detected_shell)
    else:
        new_text = _block_text(detected_shell)

    rc_file.parent.mkdir(parents=True, exist_ok=True)
    rc_file.write_text(new_text, encoding="utf-8")
    return PathEditResult(
        changed=True,
        skipped=False,
        rc_file=rc_file,
        shell=detected_shell,
        reason="appended sentinel-bracketed block",
    )

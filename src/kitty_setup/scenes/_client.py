"""Internal `kitten @` wrapper + socket discovery for scene primitives.

Holds the helpers `_pgrep_kitty_pids` and `_parse_listen_on_base` that were
previously defined in `doctor.py` and are still re-exported there (the
remote-control doctor check uses them too). Adds `_resolve_kitten_binary`,
`_resolve_socket`, `kitten_at`, and the `SceneClientError` exception so every
future §9-§14 primitive shares one socket-discovery code path.
"""

from __future__ import annotations

import os
import re
import shutil
import subprocess
from pathlib import Path

from kitty_setup import config_updater, installer

_LISTEN_ON_RE = re.compile(r"^\s*listen_on\s+unix:(?P<path>\S+)", re.MULTILINE)


class SceneClientError(RuntimeError):
    """Raised by `_resolve_kitten_binary` / `_resolve_socket` on unrecoverable failures."""


def _parse_listen_on_base(remote_control_conf: Path) -> str | None:
    """Return the `listen_on unix:<path>` base path from the managed `remote-control.conf`.

    The resolved per-instance socket appends `-<PID>` to this base (kitty's documented
    behaviour, verified by probe 01 of phase2-remote-control-foundation). Returns
    ``None`` when the file is absent or contains no ``listen_on`` directive.
    """
    if not remote_control_conf.is_file():
        return None
    match = _LISTEN_ON_RE.search(remote_control_conf.read_text(encoding="utf-8"))
    return match.group("path") if match else None


def _pgrep_kitty_pids() -> list[int]:
    """Return the PIDs of running kitty processes (`pgrep -x kitty`)."""
    try:
        result = subprocess.run(
            ["pgrep", "-x", "kitty"],
            capture_output=True,
            text=True,
            check=False,
            timeout=2,
        )
    except (FileNotFoundError, subprocess.SubprocessError):
        return []
    if result.returncode not in (0, 1):  # 1 = no matches; that is not an error
        return []
    return [int(line) for line in result.stdout.split() if line.isdigit()]


def _resolve_kitten_binary() -> Path:
    """Resolve the `kitten` binary path, mirroring `doctor.py`'s two-step pattern."""
    primary = installer.DEFAULT_DEST / "kitty.app" / "bin" / "kitten"
    if primary.is_file():
        return primary
    fallback = shutil.which("kitten")
    if fallback:
        return Path(fallback)
    raise SceneClientError(
        f"kitten binary not found at {primary} and not on $PATH; run `make install`"
    )


def _resolve_socket(to: str | None) -> str:
    """Resolve the kitty remote-control socket per the spec's 3-step data flow.

    Always returns a `unix:`-prefixed string. Steps 1 and 2 pass the caller-supplied
    value unchanged. Step 3 reads the base from the managed `remote-control.conf`
    and appends `-<PID>` from `_pgrep_kitty_pids()`.

    Raises `SceneClientError` for: missing config, zero kitties, multiple kitties.
    """
    if to is not None:
        return to
    listen_on = os.environ.get("KITTY_LISTEN_ON")
    if listen_on:
        return listen_on

    rc_conf = config_updater.ConfigPaths.for_user().payload_dir / "remote-control.conf"
    base = _parse_listen_on_base(rc_conf)
    if base is None:
        raise SceneClientError(
            "remote-control.conf missing or has no listen_on directive; "
            "run `make install` or pass --to unix:<path>"
        )

    pids = _pgrep_kitty_pids()
    if not pids:
        raise SceneClientError("no kitty process found; run kitty first or pass --to unix:<path>")
    if len(pids) > 1:
        pid_list = ", ".join(str(p) for p in pids)
        raise SceneClientError(
            f"multiple kitty processes (PIDs: {pid_list}); "
            f"pass --to unix:{base}-<pid> to disambiguate"
        )
    return f"unix:{base}-{pids[0]}"


def kitten_at(
    verb: str,
    *args: str,
    to: str | None = None,
) -> subprocess.CompletedProcess[str]:
    """Run `kitten @ --to=<socket> <verb> <args...>`.

    Resolves the kitten binary and socket per `_resolve_kitten_binary` and
    `_resolve_socket`. `to` is passed through to `_resolve_socket`. Callers
    that need `--match <expr>` pass `"--match", expr` through `*args`.

    Returns the `CompletedProcess` so callers can propagate exit codes and
    stderr verbatim. Does NOT raise on non-zero exit.
    """
    kitten_bin = _resolve_kitten_binary()
    socket_path = _resolve_socket(to)
    return subprocess.run(  # noqa: S603 — trusted paths, fixed verb
        [str(kitten_bin), "@", f"--to={socket_path}", verb, *args],
        capture_output=True,
        text=True,
        check=False,
        timeout=5,
    )
